"""
User authentication and subscription models for SaaS platform.
Models: User, Subscription, Payment
"""

from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from crm.models import db
import secrets


class User(UserMixin, db.Model):
    """User model with authentication and subscription management."""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    
    # Profile information
    company_name = db.Column(db.String(200))
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    phone = db.Column(db.String(50))
    country = db.Column(db.String(2))  # ISO country code
    
    # Account status
    is_active = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)
    is_email_confirmed = db.Column(db.Boolean, default=False)
    email_confirmation_token = db.Column(db.String(100), unique=True)
    
    # Password reset
    password_reset_token = db.Column(db.String(100), unique=True)
    password_reset_expires = db.Column(db.DateTime)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    last_login = db.Column(db.DateTime)
    
    # Relationships
    subscriptions = db.relationship('Subscription', backref='user', lazy='dynamic', 
                                    cascade='all, delete-orphan')
    verifications = db.relationship('VerificationCheck', backref='user', lazy='dynamic',
                                    foreign_keys='VerificationCheck.user_id')
    payments = db.relationship('Payment', backref='user', lazy='dynamic',
                               cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<User {self.email}>'
    
    def set_password(self, password):
        """Hash and set user password."""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Verify password against hash."""
        return check_password_hash(self.password_hash, password)
    
    def generate_confirmation_token(self):
        """Generate email confirmation token."""
        self.email_confirmation_token = secrets.token_urlsafe(32)
        return self.email_confirmation_token
    
    def confirm_email(self, token):
        """Confirm email with token."""
        if self.email_confirmation_token == token:
            self.is_email_confirmed = True
            self.email_confirmation_token = None
            return True
        return False
    
    @property
    def active_subscription(self):
        """Get current active subscription."""
        return self.subscriptions.filter(
            Subscription.status == 'active',
            Subscription.end_date > datetime.utcnow()
        ).first()
    
    @property
    def subscription_plan(self):
        """Get current subscription plan name."""
        sub = self.active_subscription
        return sub.plan if sub else 'free'
    
    def can_perform_verification(self):
        """Check if user can perform verification based on quota."""
        sub = self.active_subscription
        if not sub:
            # Free plan - check monthly limit
            return self.get_monthly_verification_count() < 5
        
        # Paid plan - check quota
        if sub.api_calls_limit == -1:  # Unlimited
            return True
        
        return sub.api_calls_used < sub.api_calls_limit
    
    def get_monthly_verification_count(self):
        """Get verification count for current month."""
        start_of_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return self.verifications.filter(
            db.func.date(db.column('created_at')) >= start_of_month
        ).count()
    
    def increment_api_usage(self):
        """Increment API call counter for active subscription."""
        sub = self.active_subscription
        if sub and sub.api_calls_limit != -1:
            sub.api_calls_used += 1
            db.session.commit()


class Subscription(db.Model):
    """User subscription model with plan management."""
    __tablename__ = 'subscriptions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Subscription details
    plan = db.Column(db.String(50), nullable=False, index=True)  # free, pro, enterprise
    status = db.Column(db.String(20), default='active', index=True)  # active, canceled, expired
    
    # Billing
    stripe_subscription_id = db.Column(db.String(100), unique=True)
    stripe_customer_id = db.Column(db.String(100))
    
    # Plan limits
    api_calls_limit = db.Column(db.Integer, default=5)  # -1 for unlimited
    api_calls_used = db.Column(db.Integer, default=0)
    
    # Dates
    start_date = db.Column(db.DateTime, default=datetime.utcnow)
    end_date = db.Column(db.DateTime)
    canceled_at = db.Column(db.DateTime)
    
    # Pricing
    monthly_price = db.Column(db.Float, default=0.0)
    currency = db.Column(db.String(3), default='EUR')
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Subscription {self.user_id} - {self.plan}>'
    
    @property
    def is_active(self):
        """Check if subscription is currently active."""
        return (self.status == 'active' and 
                self.end_date and 
                self.end_date > datetime.utcnow())
    
    @property
    def days_remaining(self):
        """Calculate days remaining in subscription."""
        if not self.end_date:
            return 0
        delta = self.end_date - datetime.utcnow()
        return max(0, delta.days)
    
    @property
    def usage_percentage(self):
        """Calculate API usage percentage."""
        if self.api_calls_limit == -1:
            return 0
        if self.api_calls_limit == 0:
            return 100
        return min(100, (self.api_calls_used / self.api_calls_limit) * 100)
    
    def reset_usage(self):
        """Reset monthly API usage counter."""
        self.api_calls_used = 0
        db.session.commit()
    
    @staticmethod
    def get_plan_details(plan_name):
        """Get plan configuration details."""
        plans = {
            'free': {
                'name': 'Kostenlos',
                'price': 0,
                'api_calls': 5,
                'features': [
                    '5 Prüfungen pro Monat',
                    'VIES Validierung',
                    'Basis Sanktionsprüfung',
                    'E-Mail Support'
                ]
            },
            'pro': {
                'name': 'Professional',
                'price': 49.99,
                'api_calls': 200,
                'features': [
                    '200 Prüfungen pro Monat',
                    'Alle Validierungsdienste',
                    'Handelsregister Prüfung',
                    'Erweiterte Sanktionslisten',
                    'API Zugang',
                    'Verlauf & Berichte',
                    'Prioritäts-Support'
                ]
            },
            'enterprise': {
                'name': 'Enterprise',
                'price': 199.99,
                'api_calls': -1,  # Unlimited
                'features': [
                    'Unbegrenzte Prüfungen',
                    'Alle Professional Features',
                    'White-Label Lösung',
                    'Custom API Integration',
                    'Dedizierter Account Manager',
                    '24/7 Premium Support',
                    'SLA Garantie'
                ]
            }
        }
        return plans.get(plan_name, plans['free'])


class Payment(db.Model):
    """Payment transaction history."""
    __tablename__ = 'payments'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    subscription_id = db.Column(db.Integer, db.ForeignKey('subscriptions.id'))
    
    # Stripe details
    stripe_payment_intent_id = db.Column(db.String(100), unique=True)
    stripe_invoice_id = db.Column(db.String(100))
    
    # Payment info
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(3), default='EUR')
    status = db.Column(db.String(20), index=True)  # succeeded, failed, pending, refunded
    
    # Metadata
    description = db.Column(db.Text)
    invoice_url = db.Column(db.String(500))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    def __repr__(self):
        return f'<Payment {self.amount} {self.currency} - {self.status}>'


# Update VerificationCheck model to link to users
from crm.models import VerificationCheck

# Add user_id column to existing VerificationCheck model
if not hasattr(VerificationCheck, 'user_id'):
    VerificationCheck.user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
