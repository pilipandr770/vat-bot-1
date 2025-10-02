"""
Stripe Payment Integration Routes
Handles subscription checkout, success/cancel callbacks
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
import stripe
from datetime import datetime, timedelta
from auth.models import db, Subscription

payments_bp = Blueprint('payments', __name__)


@payments_bp.route('/subscribe/<plan_name>')
@login_required
def subscribe(plan_name):
    """
    Create Stripe Checkout session for subscription upgrade
    
    Plans:
    - pro: €49/month, 500 checks/month
    - enterprise: €149/month, unlimited checks
    """
    # Validate plan
    if plan_name not in ['pro', 'enterprise']:
        flash('Ungültiger Abonnementplan.', 'danger')
        return redirect(url_for('index'))
    
    # Check if user already has active subscription
    if current_user.active_subscription:
        if current_user.active_subscription.plan != 'free':
            flash('Sie haben bereits ein aktives Abonnement. Bitte kündigen Sie zuerst Ihr aktuelles Abonnement.', 'warning')
            return redirect(url_for('auth.profile'))
    
    # Configure Stripe
    stripe.api_key = current_app.config['STRIPE_SECRET_KEY']
    
    # Plan pricing
    plan_prices = {
        'pro': {
            'price': 4900,  # €49.00 in cents
            'name': 'Professional Plan',
            'description': '500 Prüfungen pro Monat',
            'api_limit': 500
        },
        'enterprise': {
            'price': 14900,  # €149.00 in cents
            'name': 'Enterprise Plan', 
            'description': 'Unbegrenzte Prüfungen',
            'api_limit': 999999
        }
    }
    
    plan_config = plan_prices[plan_name]
    
    try:
        # Create Stripe Checkout Session
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'eur',
                    'unit_amount': plan_config['price'],
                    'recurring': {
                        'interval': 'month'
                    },
                    'product_data': {
                        'name': plan_config['name'],
                        'description': plan_config['description'],
                    },
                },
                'quantity': 1,
            }],
            mode='subscription',
            success_url=url_for('payments.success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=url_for('payments.cancel', _external=True),
            customer_email=current_user.email,
            client_reference_id=str(current_user.id),
            metadata={
                'user_id': current_user.id,
                'plan_name': plan_name
            }
        )
        
        return redirect(checkout_session.url, code=303)
        
    except stripe.error.StripeError as e:
        current_app.logger.error(f"Stripe error creating checkout session: {str(e)}")
        flash('Fehler beim Erstellen der Checkout-Sitzung. Bitte versuchen Sie es später erneut.', 'danger')
        return redirect(url_for('index'))


@payments_bp.route('/success')
@login_required
def success():
    """
    Handle successful payment
    Stripe session ID provided as query parameter
    """
    session_id = request.args.get('session_id')
    
    if not session_id:
        flash('Ungültige Zahlungssitzung.', 'danger')
        return redirect(url_for('index'))
    
    stripe.api_key = current_app.config['STRIPE_SECRET_KEY']
    
    try:
        # Retrieve checkout session
        session = stripe.checkout.Session.retrieve(session_id)
        
        # Verify user matches
        if str(current_user.id) != session.metadata.get('user_id'):
            flash('Zahlungssitzung stimmt nicht mit Ihrem Konto überein.', 'danger')
            return redirect(url_for('index'))
        
        # Get plan details
        plan_name = session.metadata.get('plan_name')
        
        # Update or create subscription
        subscription = current_user.active_subscription
        if subscription:
            # Update existing subscription
            subscription.plan = plan_name
            subscription.stripe_subscription_id = session.subscription
            subscription.stripe_customer_id = session.customer
            subscription.status = 'active'
            subscription.current_period_start = datetime.utcnow()
            subscription.current_period_end = datetime.utcnow() + timedelta(days=30)
            
            # Update API limits
            if plan_name == 'pro':
                subscription.api_calls_limit = 500
            elif plan_name == 'enterprise':
                subscription.api_calls_limit = 999999
            
            # Reset monthly usage
            subscription.api_calls_used = 0
            
        else:
            # Create new subscription
            api_limit = 500 if plan_name == 'pro' else 999999
            subscription = Subscription(
                user_id=current_user.id,
                plan=plan_name,
                status='active',
                stripe_subscription_id=session.subscription,
                stripe_customer_id=session.customer,
                current_period_start=datetime.utcnow(),
                current_period_end=datetime.utcnow() + timedelta(days=30),
                api_calls_limit=api_limit,
                api_calls_used=0
            )
            db.session.add(subscription)
        
        db.session.commit()
        
        flash(f'Zahlung erfolgreich! Ihr {plan_name.upper()}-Abonnement ist jetzt aktiv.', 'success')
        return redirect(url_for('dashboard'))
        
    except stripe.error.StripeError as e:
        current_app.logger.error(f"Stripe error retrieving session: {str(e)}")
        flash('Fehler beim Abrufen der Zahlungsinformationen.', 'danger')
        return redirect(url_for('index'))


@payments_bp.route('/cancel')
@login_required
def cancel():
    """
    Handle cancelled payment
    """
    flash('Zahlungsvorgang abgebrochen. Ihr Abonnement wurde nicht geändert.', 'info')
    return redirect(url_for('index'))


@payments_bp.route('/portal')
@login_required
def customer_portal():
    """
    Redirect to Stripe Customer Portal for subscription management
    Allows users to update payment method, cancel subscription, view invoices
    """
    # Check if user has Stripe customer ID
    subscription = current_user.active_subscription
    if not subscription or not subscription.stripe_customer_id:
        flash('Keine aktive Abonnement gefunden.', 'warning')
        return redirect(url_for('auth.profile'))
    
    stripe.api_key = current_app.config['STRIPE_SECRET_KEY']
    
    try:
        # Create portal session
        portal_session = stripe.billing_portal.Session.create(
            customer=subscription.stripe_customer_id,
            return_url=url_for('auth.profile', _external=True)
        )
        
        return redirect(portal_session.url, code=303)
        
    except stripe.error.StripeError as e:
        current_app.logger.error(f"Stripe error creating portal session: {str(e)}")
        flash('Fehler beim Öffnen des Kundenportals.', 'danger')
        return redirect(url_for('auth.profile'))


@payments_bp.route('/pricing')
def pricing():
    """
    Display pricing page with plan comparison
    """
    plans = [
        {
            'name': 'free',
            'display_name': 'Kostenlos',
            'price': 0,
            'period': 'für immer',
            'api_calls': 5,
            'features': [
                '5 Prüfungen pro Monat',
                'VIES VAT-Validierung',
                'Sanktionslisten-Check',
                'Email-Support'
            ],
            'cta': 'Jetzt starten',
            'cta_url': 'auth.register',
            'featured': False
        },
        {
            'name': 'pro',
            'display_name': 'Professional',
            'price': 49,
            'period': 'pro Monat',
            'api_calls': 500,
            'features': [
                '500 Prüfungen pro Monat',
                'Alle kostenlosen Features',
                'Handelsregister-Prüfung',
                'Insolvenzverfahren-Check',
                'OpenCorporates-Daten',
                'PDF-Berichte',
                'Prioritäts-Support'
            ],
            'cta': 'Upgrade auf Pro',
            'cta_url': 'payments.subscribe',
            'cta_params': {'plan_name': 'pro'},
            'featured': True
        },
        {
            'name': 'enterprise',
            'display_name': 'Enterprise',
            'price': 149,
            'period': 'pro Monat',
            'api_calls': 'Unbegrenzt',
            'features': [
                'Unbegrenzte Prüfungen',
                'Alle Pro Features',
                'API-Zugang',
                'Batch-Verarbeitung',
                'Benutzerdefinierte Integrationen',
                'Dedizierter Account Manager',
                'SLA-Garantie'
            ],
            'cta': 'Upgrade auf Enterprise',
            'cta_url': 'payments.subscribe',
            'cta_params': {'plan_name': 'enterprise'},
            'featured': False
        }
    ]
    
    return render_template('payments/pricing.html', plans=plans)
