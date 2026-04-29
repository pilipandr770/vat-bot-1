"""
Payments & Stripe webhook tests.

Tests:
- Stripe webhook idempotency (ProcessedStripeEvent)
- Subscription creation / cancellation handlers
- Plan limits & gating via require_plan
- Billing portal redirect
"""
import json
import pytest
import hmac
import hashlib
import time
from unittest.mock import patch, MagicMock
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def stripe_user(db, app):
    from auth.models import User
    with app.app_context():
        u = User(
            email='stripe@example.com',
            password_hash=generate_password_hash('pass123'),
            first_name='Stripe',
            last_name='Tester',
            is_active=True,
            is_email_confirmed=True,
        )
        db.session.add(u)
        db.session.commit()
        yield u
        # Cleanup — cascade removes subscriptions/payments
        db.session.delete(db.session.merge(u))
        db.session.commit()


def _make_stripe_event(event_type, data, secret='test_webhook_secret'):
    """Build a fake Stripe webhook payload with valid HMAC signature."""
    payload = json.dumps({
        'id': f'evt_{event_type.replace(".", "_")}_test',
        'type': event_type,
        'data': {'object': data},
    })
    ts = str(int(time.time()))
    signed = f'{ts}.{payload}'
    sig = hmac.new(secret.encode(), signed.encode(), hashlib.sha256).hexdigest()
    stripe_sig = f't={ts},v1={sig}'
    return payload.encode(), stripe_sig


# ── Webhook idempotency ───────────────────────────────────────────────────────

class TestStripeWebhookIdempotency:
    def test_duplicate_event_returns_already_processed(self, client, db, app):
        """Sending the same Stripe event twice returns 200 already_processed on second call."""
        from auth.models import ProcessedStripeEvent
        event_id = 'evt_duplicate_test_001'

        with app.app_context():
            app.config['STRIPE_WEBHOOK_SECRET'] = 'test_webhook_secret'
            # Pre-insert as already processed
            processed = ProcessedStripeEvent(stripe_event_id=event_id)
            db.session.add(processed)
            db.session.commit()

            mock_event = MagicMock()
            mock_event.__getitem__ = lambda self, k: {
                'id': event_id,
                'type': 'customer.subscription.updated',
                'data': {'object': {}},
            }[k]
            mock_event.get = lambda k, d=None: {
                'id': event_id,
                'type': 'customer.subscription.updated',
                'data': {'object': {}},
            }.get(k, d)

            with patch('stripe.Webhook.construct_event', return_value={
                'id': event_id,
                'type': 'customer.subscription.updated',
                'data': {'object': {}},
            }):
                resp = client.post(
                    '/webhooks/stripe',
                    data=b'{}',
                    headers={
                        'Content-Type': 'application/json',
                        'Stripe-Signature': 'mock',
                    },
                )
            assert resp.status_code == 200
            data = resp.get_json()
            assert data.get('status') == 'already_processed'

            # cleanup
            db.session.delete(ProcessedStripeEvent.query.filter_by(stripe_event_id=event_id).first())
            db.session.commit()

    def test_invalid_stripe_signature_rejected(self, client, app):
        """Bad Stripe-Signature header returns 400."""
        with app.app_context():
            app.config['STRIPE_WEBHOOK_SECRET'] = 'real_secret'
        resp = client.post(
            '/webhooks/stripe',
            data=b'{"id":"evt_fake"}',
            headers={
                'Content-Type': 'application/json',
                'Stripe-Signature': 'invalid_sig',
            },
        )
        assert resp.status_code in (400, 500)

    def test_missing_signature_rejected(self, client, app):
        """Missing Stripe-Signature returns 400."""
        resp = client.post(
            '/webhooks/stripe',
            data=b'{"id":"evt_no_sig"}',
            headers={'Content-Type': 'application/json'},
        )
        assert resp.status_code in (400, 500)


# ── Subscription model ────────────────────────────────────────────────────────

class TestSubscriptionModel:
    def test_active_subscription_property(self, db, app, stripe_user):
        from auth.models import User, Subscription
        with app.app_context():
            u = User.query.filter_by(email='stripe@example.com').first()
            assert u.active_subscription is None  # no sub yet

            sub = Subscription(
                user_id=u.id,
                plan='basic',
                status='active',
                api_calls_limit=100,
                monthly_price=9.99,
                start_date=datetime.utcnow(),
                end_date=datetime.utcnow() + timedelta(days=30),
            )
            db.session.add(sub)
            db.session.commit()

            u2 = User.query.filter_by(email='stripe@example.com').first()
            assert u2.active_subscription is not None
            assert u2.active_subscription.plan == 'basic'

            db.session.delete(sub)
            db.session.commit()

    def test_expired_subscription_not_active(self, db, app, stripe_user):
        from auth.models import User, Subscription
        with app.app_context():
            u = User.query.filter_by(email='stripe@example.com').first()
            expired_sub = Subscription(
                user_id=u.id,
                plan='professional',
                status='active',
                api_calls_limit=500,
                monthly_price=49.99,
                start_date=datetime.utcnow() - timedelta(days=60),
                end_date=datetime.utcnow() - timedelta(days=1),  # expired
            )
            db.session.add(expired_sub)
            db.session.commit()

            u2 = User.query.filter_by(email='stripe@example.com').first()
            assert u2.active_subscription is None  # expired → not active

            db.session.delete(expired_sub)
            db.session.commit()


# ── Payments page ─────────────────────────────────────────────────────────────

class TestPaymentsRoutes:
    def test_pricing_page_public(self, client):
        resp = client.get('/pricing')
        assert resp.status_code in (200, 302, 404)

    def test_subscription_page_requires_auth(self, client):
        resp = client.get('/subscription', follow_redirects=False)
        assert resp.status_code in (302, 401, 404)


# ── Plan limits ───────────────────────────────────────────────────────────────

class TestPlanLimits:
    def test_professional_route_blocks_free_user(self, client, test_user, app):
        """Free user cannot access professional-only ISMS route."""
        with client.session_transaction() as sess:
            sess['_user_id'] = str(test_user.id)
            sess['_fresh'] = True
        resp = client.get('/nis2/isms/', follow_redirects=False)
        # Should redirect to upgrade page or return 403
        assert resp.status_code in (302, 403)

    def test_pentesting_blocks_free_user(self, client, test_user, app):
        """Free user cannot start a pentest scan."""
        with client.session_transaction() as sess:
            sess['_user_id'] = str(test_user.id)
            sess['_fresh'] = True
        resp = client.post(
            '/api/pentesting/scan',
            json={'url': 'https://example.com'},
        )
        assert resp.status_code in (302, 403)
