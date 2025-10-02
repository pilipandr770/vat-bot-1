"""
Stripe Webhook Handler
Processes Stripe webhook events for subscription lifecycle management
"""
from flask import Blueprint, request, jsonify, current_app
import stripe
from auth.models import db, User, Subscription, Payment
from datetime import datetime, timedelta
import hmac
import hashlib

webhooks_bp = Blueprint('webhooks', __name__)


@webhooks_bp.route('/stripe', methods=['POST'])
def stripe_webhook():
    """
    Handle Stripe webhook events
    
    Events handled:
    - checkout.session.completed: New subscription created
    - customer.subscription.created: Subscription activated
    - customer.subscription.updated: Subscription plan changed
    - customer.subscription.deleted: Subscription cancelled
    - invoice.payment_succeeded: Monthly payment received
    - invoice.payment_failed: Payment failed
    """
    payload = request.get_data()
    sig_header = request.headers.get('Stripe-Signature')
    webhook_secret = current_app.config['STRIPE_WEBHOOK_SECRET']
    
    try:
        # Verify webhook signature
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
    except ValueError as e:
        # Invalid payload
        current_app.logger.error(f"Stripe webhook invalid payload: {str(e)}")
        return jsonify({'error': 'Invalid payload'}), 400
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        current_app.logger.error(f"Stripe webhook invalid signature: {str(e)}")
        return jsonify({'error': 'Invalid signature'}), 400
    
    # Handle the event
    event_type = event['type']
    event_data = event['data']['object']
    
    current_app.logger.info(f"Received Stripe webhook: {event_type}")
    
    # Route to appropriate handler
    if event_type == 'checkout.session.completed':
        handle_checkout_completed(event_data)
    
    elif event_type == 'customer.subscription.created':
        handle_subscription_created(event_data)
    
    elif event_type == 'customer.subscription.updated':
        handle_subscription_updated(event_data)
    
    elif event_type == 'customer.subscription.deleted':
        handle_subscription_deleted(event_data)
    
    elif event_type == 'invoice.payment_succeeded':
        handle_payment_succeeded(event_data)
    
    elif event_type == 'invoice.payment_failed':
        handle_payment_failed(event_data)
    
    else:
        current_app.logger.info(f"Unhandled event type: {event_type}")
    
    return jsonify({'status': 'success'}), 200


def handle_checkout_completed(session):
    """
    Handle checkout.session.completed event
    Called when user completes Stripe Checkout
    """
    user_id = session['metadata'].get('user_id')
    plan_name = session['metadata'].get('plan_name')
    
    if not user_id or not plan_name:
        current_app.logger.error("Missing user_id or plan_name in checkout session metadata")
        return
    
    user = User.query.get(int(user_id))
    if not user:
        current_app.logger.error(f"User {user_id} not found for checkout session")
        return
    
    # Update or create subscription
    subscription = user.active_subscription
    if subscription:
        subscription.stripe_subscription_id = session.get('subscription')
        subscription.stripe_customer_id = session.get('customer')
        subscription.plan = plan_name
        subscription.status = 'active'
        subscription.current_period_start = datetime.utcnow()
        subscription.current_period_end = datetime.utcnow() + timedelta(days=30)
        
        # Update API limits
        if plan_name == 'pro':
            subscription.api_calls_limit = 500
        elif plan_name == 'enterprise':
            subscription.api_calls_limit = 999999
        
        subscription.api_calls_used = 0
    else:
        api_limit = 500 if plan_name == 'pro' else 999999
        subscription = Subscription(
            user_id=user.id,
            plan=plan_name,
            status='active',
            stripe_subscription_id=session.get('subscription'),
            stripe_customer_id=session.get('customer'),
            current_period_start=datetime.utcnow(),
            current_period_end=datetime.utcnow() + timedelta(days=30),
            api_calls_limit=api_limit,
            api_calls_used=0
        )
        db.session.add(subscription)
    
    db.session.commit()
    
    current_app.logger.info(f"Checkout completed for user {user_id}, plan: {plan_name}")


def handle_subscription_created(subscription_data):
    """
    Handle customer.subscription.created event
    Called when subscription is activated
    """
    stripe_subscription_id = subscription_data['id']
    customer_id = subscription_data['customer']
    
    # Find subscription by stripe_subscription_id
    subscription = Subscription.query.filter_by(
        stripe_subscription_id=stripe_subscription_id
    ).first()
    
    if subscription:
        subscription.status = 'active'
        subscription.current_period_start = datetime.fromtimestamp(
            subscription_data['current_period_start']
        )
        subscription.current_period_end = datetime.fromtimestamp(
            subscription_data['current_period_end']
        )
        db.session.commit()
        
        current_app.logger.info(f"Subscription {stripe_subscription_id} activated")
    else:
        current_app.logger.warning(f"Subscription {stripe_subscription_id} not found in database")


def handle_subscription_updated(subscription_data):
    """
    Handle customer.subscription.updated event
    Called when subscription plan changes or status updates
    """
    stripe_subscription_id = subscription_data['id']
    new_status = subscription_data['status']
    
    subscription = Subscription.query.filter_by(
        stripe_subscription_id=stripe_subscription_id
    ).first()
    
    if subscription:
        # Update status
        subscription.status = new_status
        
        # Update period dates
        subscription.current_period_start = datetime.fromtimestamp(
            subscription_data['current_period_start']
        )
        subscription.current_period_end = datetime.fromtimestamp(
            subscription_data['current_period_end']
        )
        
        # Check if plan changed (upgrade/downgrade)
        # This would require storing plan_id in metadata
        
        db.session.commit()
        
        current_app.logger.info(f"Subscription {stripe_subscription_id} updated to status: {new_status}")
    else:
        current_app.logger.warning(f"Subscription {stripe_subscription_id} not found for update")


def handle_subscription_deleted(subscription_data):
    """
    Handle customer.subscription.deleted event
    Called when subscription is cancelled
    """
    stripe_subscription_id = subscription_data['id']
    
    subscription = Subscription.query.filter_by(
        stripe_subscription_id=stripe_subscription_id
    ).first()
    
    if subscription:
        # Downgrade to free plan
        subscription.plan = 'free'
        subscription.status = 'cancelled'
        subscription.api_calls_limit = 5  # Free plan limit
        subscription.api_calls_used = 0
        subscription.stripe_subscription_id = None
        
        db.session.commit()
        
        current_app.logger.info(f"Subscription {stripe_subscription_id} cancelled, downgraded to free plan")
        
        # TODO: Send cancellation email to user
    else:
        current_app.logger.warning(f"Subscription {stripe_subscription_id} not found for deletion")


def handle_payment_succeeded(invoice):
    """
    Handle invoice.payment_succeeded event
    Called when monthly payment is successful
    """
    subscription_id = invoice.get('subscription')
    amount_paid = invoice.get('amount_paid')  # in cents
    currency = invoice.get('currency')
    payment_intent_id = invoice.get('payment_intent')
    
    subscription = Subscription.query.filter_by(
        stripe_subscription_id=subscription_id
    ).first()
    
    if subscription:
        # Create payment record
        payment = Payment(
            user_id=subscription.user_id,
            subscription_id=subscription.id,
            stripe_payment_intent_id=payment_intent_id,
            amount=amount_paid / 100.0,  # Convert cents to euros
            currency=currency.upper(),
            status='succeeded',
            created_at=datetime.utcnow()
        )
        db.session.add(payment)
        
        # Reset monthly API usage
        subscription.api_calls_used = 0
        
        # Update period dates
        subscription.current_period_start = datetime.fromtimestamp(
            invoice['period_start']
        )
        subscription.current_period_end = datetime.fromtimestamp(
            invoice['period_end']
        )
        
        db.session.commit()
        
        current_app.logger.info(f"Payment succeeded for subscription {subscription_id}, amount: €{amount_paid/100}")
        
        # TODO: Send payment receipt email
    else:
        current_app.logger.warning(f"Subscription {subscription_id} not found for payment")


def handle_payment_failed(invoice):
    """
    Handle invoice.payment_failed event
    Called when monthly payment fails
    """
    subscription_id = invoice.get('subscription')
    amount_due = invoice.get('amount_due')
    payment_intent_id = invoice.get('payment_intent')
    
    subscription = Subscription.query.filter_by(
        stripe_subscription_id=subscription_id
    ).first()
    
    if subscription:
        # Update subscription status
        subscription.status = 'past_due'
        
        # Create failed payment record
        payment = Payment(
            user_id=subscription.user_id,
            subscription_id=subscription.id,
            stripe_payment_intent_id=payment_intent_id,
            amount=amount_due / 100.0,
            currency=invoice.get('currency', 'eur').upper(),
            status='failed',
            created_at=datetime.utcnow()
        )
        db.session.add(payment)
        db.session.commit()
        
        current_app.logger.warning(f"Payment failed for subscription {subscription_id}, amount: €{amount_due/100}")
        
        # TODO: Send payment failed email to user
    else:
        current_app.logger.warning(f"Subscription {subscription_id} not found for failed payment")
