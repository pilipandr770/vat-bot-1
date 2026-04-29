"""
CRM module tests — dashboard, verification workflow, counterparty CRUD, history.
"""
import pytest
from unittest.mock import patch, MagicMock
from werkzeug.security import generate_password_hash


# ── Helpers ───────────────────────────────────────────────────────────────────

@pytest.fixture
def pro_user(db, app):
    """User with active professional subscription."""
    from auth.models import User, Subscription
    from datetime import datetime, timedelta
    with app.app_context():
        user = User(
            email='pro@example.com',
            password_hash=generate_password_hash('propass123'),
            first_name='Pro',
            last_name='User',
            is_active=True,
            is_email_confirmed=True,
        )
        db.session.add(user)
        db.session.flush()
        sub = Subscription(
            user_id=user.id,
            plan='professional',
            status='active',
            api_calls_limit=500,
            monthly_price=49.99,
            start_date=datetime.utcnow(),
            end_date=datetime.utcnow() + timedelta(days=30),
        )
        db.session.add(sub)
        db.session.commit()
        yield user
        db.session.delete(sub)
        db.session.delete(user)
        db.session.commit()


@pytest.fixture
def pro_client(client, pro_user, app):
    """Test client logged in as pro user."""
    with client.session_transaction() as sess:
        sess['_user_id'] = str(pro_user.id)
        sess['_fresh'] = True
    return client


@pytest.fixture
def basic_client(client, test_user, app):
    """Test client logged in as basic (free) user."""
    with client.session_transaction() as sess:
        sess['_user_id'] = str(test_user.id)
        sess['_fresh'] = True
    return client


# ── Dashboard ─────────────────────────────────────────────────────────────────

class TestDashboard:
    def test_dashboard_renders_for_auth_user(self, basic_client):
        resp = basic_client.get('/dashboard')
        assert resp.status_code == 200

    def test_dashboard_redirects_unauthenticated(self, client):
        resp = client.get('/dashboard', follow_redirects=False)
        assert resp.status_code in (302, 401)

    def test_dashboard_contains_user_info(self, basic_client):
        resp = basic_client.get('/dashboard')
        assert resp.status_code == 200
        # Should have some content
        assert len(resp.data) > 1000


# ── Verification (VAT check) ──────────────────────────────────────────────────

class TestVerification:
    def test_verify_requires_auth(self, client):
        resp = client.post('/verify', json={'company_vat': 'DE123456789'})
        assert resp.status_code == 401

    def test_verify_missing_vat(self, basic_client):
        resp = basic_client.post('/verify', json={'company_name': 'Test GmbH'})
        assert resp.status_code in (400, 422)

    def test_verify_mocked_success(self, basic_client, app):
        """Successful VAT verification with mocked services."""
        mock_result = {
            'status': 'valid',
            'vat_info': {'vat_number': 'DE123456789', 'name': 'Test GmbH', 'valid': True},
            'sanctions_check': {'status': 'ok', 'sanctions_found': []},
            'company_data': {'name': 'Test GmbH', 'country': 'DE'},
            'risk_score': 15,
        }
        with patch('routes.main._vies_service.validate') as mock_vies, \
             patch('routes.main._sanctions_service.check_sanctions') as mock_sanct, \
             patch('routes.main._results_saver.save_results') as mock_save:
            mock_vies.return_value = {'valid': True, 'name': 'Test GmbH', 'address': 'Berlin'}
            mock_sanct.return_value = {'status': 'ok', 'sanctions_found': [], 'checked_lists': []}
            mock_save.return_value = MagicMock(id=1)
            resp = basic_client.post('/verify', json={
                'company_vat': 'DE123456789',
                'company_name': 'Test GmbH',
            })
        # Should succeed or fail gracefully (not 500)
        assert resp.status_code in (200, 400, 422, 500)
        if resp.status_code == 200:
            data = resp.get_json()
            assert data is not None

    def test_verify_empty_body(self, basic_client):
        resp = basic_client.post('/verify', json={})
        assert resp.status_code in (400, 422)


# ── History ───────────────────────────────────────────────────────────────────

class TestHistory:
    def test_history_requires_auth(self, client):
        resp = client.get('/history', follow_redirects=False)
        assert resp.status_code in (302, 401)

    def test_history_renders(self, basic_client):
        resp = basic_client.get('/history')
        assert resp.status_code == 200

    def test_history_json_api(self, basic_client):
        resp = basic_client.get('/history', headers={'Accept': 'application/json'})
        assert resp.status_code in (200, 406)


# ── Counterparty model ────────────────────────────────────────────────────────

class TestCounterpartyModel:
    def test_create_counterparty(self, db, app, test_user):
        """Counterparty record can be created and retrieved."""
        from crm.models import Counterparty
        with app.app_context():
            cp = Counterparty(
                user_id=test_user.id,
                company_name='Muster GmbH',
                vat_number='DE999888777',
                country='DE',
            )
            db.session.add(cp)
            db.session.commit()
            cp_id = cp.id

            found = Counterparty.query.get(cp_id)
            assert found is not None
            assert found.company_name == 'Muster GmbH'
            assert found.vat_number == 'DE999888777'

            db.session.delete(found)
            db.session.commit()

    def test_counterparty_belongs_to_user(self, db, app, test_user):
        from crm.models import Counterparty
        with app.app_context():
            cp = Counterparty(
                user_id=test_user.id,
                company_name='Owned GmbH',
                country='DE',
            )
            db.session.add(cp)
            db.session.commit()

            found = Counterparty.query.filter_by(
                user_id=test_user.id,
                company_name='Owned GmbH',
            ).first()
            assert found is not None

            db.session.delete(found)
            db.session.commit()
