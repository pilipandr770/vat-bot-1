"""
Stripe Webhook Handler
Processes Stripe webhook events for subscription lifecycle management
"""
from flask import Blueprint, request, jsonify, current_app
import stripe
from auth.models import db, User, Subscription, Payment, ProcessedStripeEvent
from datetime import datetime, timedelta
from notifications.alerts import send_email
import hmac
import hashlib

webhooks_bp = Blueprint('webhooks', __name__)

# Plan API limits configuration
PLAN_LIMITS = {
    'basic': 100,           # €9.99/month
    'professional': 500,    # €49.99/month
    'enterprise': 999999,   # €149.99/month
    'free': 5               # Free tier
}


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
    except stripe.SignatureVerificationError as e:
        # Invalid signature
        current_app.logger.error(f"Stripe webhook invalid signature: {str(e)}")
        return jsonify({'error': 'Invalid signature'}), 400
    
    # Handle the event
    event_type = event['type']
    event_data = event['data']['object']
    event_id = event['id']

    current_app.logger.info(f"Received Stripe webhook: {event_type} ({event_id})")

    # Idempotency check — skip already-processed events
    if ProcessedStripeEvent.query.filter_by(stripe_event_id=event_id).first():
        current_app.logger.info(f"Skipping duplicate Stripe event: {event_id}")
        return jsonify({'status': 'already_processed'}), 200

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

    # Mark event as processed
    try:
        processed = ProcessedStripeEvent(stripe_event_id=event_id, event_type=event_type)
        db.session.add(processed)
        db.session.commit()
    except Exception:
        db.session.rollback()

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
    
    stripe_subscription_id = session.get('subscription')
    stripe_customer_id = session.get('customer')
    api_limit = PLAN_LIMITS.get(plan_name, PLAN_LIMITS['free'])

    subscription = user.active_subscription
    if subscription:
        subscription.stripe_subscription_id = stripe_subscription_id
        subscription.stripe_customer_id = stripe_customer_id
        subscription.plan = plan_name
        subscription.status = 'active'
        subscription.start_date = datetime.utcnow()
        subscription.end_date = datetime.utcnow() + timedelta(days=30)
        subscription.api_calls_limit = api_limit
        subscription.api_calls_used = 0
    else:
        subscription = Subscription(
            user_id=user.id,
            plan=plan_name,
            status='active',
            stripe_subscription_id=stripe_subscription_id,
            stripe_customer_id=stripe_customer_id,
            start_date=datetime.utcnow(),
            end_date=datetime.utcnow() + timedelta(days=30),
            api_calls_limit=api_limit,
            api_calls_used=0,
        )
        db.session.add(subscription)

    db.session.commit()
    current_app.logger.info(f"Checkout completed for user {user_id}, plan: {plan_name}")


def handle_subscription_created(subscription_data):
    """
    Handle customer.subscription.created event
    Called when Stripe confirms subscription activation
    """
    stripe_subscription_id = subscription_data['id']
    subscription = Subscription.query.filter_by(
        stripe_subscription_id=stripe_subscription_id
    ).first()
    if subscription:
        subscription.status = 'active'
        if subscription_data.get('current_period_start'):
            subscription.start_date = datetime.fromtimestamp(subscription_data['current_period_start'])
        if subscription_data.get('current_period_end'):
            subscription.end_date = datetime.fromtimestamp(subscription_data['current_period_end'])
        db.session.commit()
        current_app.logger.info(f"Subscription {stripe_subscription_id} confirmed via subscription.created")
    else:
        current_app.logger.warning(f"subscription.created: no local record for {stripe_subscription_id}")


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
        subscription.api_calls_limit = PLAN_LIMITS['free']  # Free plan limit from config
        subscription.api_calls_used = 0
        subscription.stripe_subscription_id = None

        db.session.commit()


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

        user = User.query.get(subscription.user_id)
        if user:
            send_email(
                subject='Zahlungsbestätigung – Ihr Abonnement',
                recipient=user.email,
                text_body=f'Vielen Dank! Zahlung von €{amount_paid/100:.2f} für Plan „{subscription.plan}" erfolgreich verarbeitet.'
            )
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

        user = User.query.get(subscription.user_id)
        if user:
            send_email(
                subject='Zahlungsproblem – Bitte aktualisieren Sie Ihre Zahlungsdaten',
                recipient=user.email,
                text_body=f'Die Zahlung von €{amount_due/100:.2f} für Ihr Abonnement ist fehlgeschlagen. Bitte aktualisieren Sie Ihre Zahlungsdaten unter /payments/billing.'
            )
    else:
        current_app.logger.warning(f"Subscription {subscription_id} not found for failed payment")
