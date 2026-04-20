"""
Unit tests for NIS2 Supply Chain module.

Tests: add supplier, list dashboard, detail page, delete,
       verify (mocked), access control.
"""
import pytest
from unittest.mock import patch
from werkzeug.security import generate_password_hash


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def logged_client(client, test_user, app):
    """Test client with authenticated user session."""
    with client.session_transaction() as sess:
        # Flask-Login sets _user_id in session
        with app.app_context():
            sess['_user_id'] = str(test_user.id)
            sess['_fresh'] = True
    return client


@pytest.fixture
def supplier(db, test_user, app):
    """Create a test supplier record."""
    from app.nis2.models import Supplier
    with app.app_context():
        s = Supplier(
            user_id=test_user.id,
            company_name='Test GmbH',
            category='cloud',
            criticality='medium',
            country='DE',
            vat_id='DE123456789',
            contact_email='test@testgmbh.de',
            services_provided='Cloud hosting',
            avv_exists=False,
            has_iso27001=False,
        )
        db.session.add(s)
        db.session.commit()
        yield s
        db.session.delete(s)
        db.session.commit()


# ── Access control ────────────────────────────────────────────────────────────

class TestSupplyChainAccessControl:
    def test_dashboard_requires_login(self, client):
        """Unauthenticated GET /nis2/supply-chain/ → redirect to login."""
        resp = client.get('/nis2/supply-chain/', follow_redirects=False)
        assert resp.status_code in (302, 401)

    def test_add_requires_login(self, client):
        """Unauthenticated POST /nis2/supply-chain/add → redirect."""
        resp = client.post('/nis2/supply-chain/add', data={}, follow_redirects=False)
        assert resp.status_code in (302, 401)


# ── Dashboard ─────────────────────────────────────────────────────────────────

class TestSupplyChainDashboard:
    def test_dashboard_renders(self, logged_client):
        """Authenticated GET /nis2/supply-chain/ → 200."""
        resp = logged_client.get('/nis2/supply-chain/')
        assert resp.status_code == 200

    def test_dashboard_shows_supplier(self, logged_client, supplier, app):
        """Dashboard lists the existing test supplier."""
        resp = logged_client.get('/nis2/supply-chain/')
        assert resp.status_code == 200
        assert b'Test GmbH' in resp.data


# ── Add Supplier ──────────────────────────────────────────────────────────────

class TestSupplyChainAdd:
    def test_add_form_renders(self, logged_client):
        """GET /nis2/supply-chain/add → 200."""
        resp = logged_client.get('/nis2/supply-chain/add')
        assert resp.status_code == 200

    def test_add_supplier_success(self, logged_client, db, app):
        """POST valid form data creates a new Supplier."""
        from app.nis2.models import Supplier
        resp = logged_client.post(
            '/nis2/supply-chain/add',
            data={
                'company_name': 'Neue GmbH',
                'category': 'software',
                'criticality': 'low',
                'country': 'DE',
                'vat_number': 'DE987654321',
                'contact_email': 'info@neue.de',
                'services_provided': 'ERP Software',
            },
            follow_redirects=False,
        )
        # Expect redirect to detail page after creation
        assert resp.status_code == 302
        with app.app_context():
            s = Supplier.query.filter_by(company_name='Neue GmbH').first()
            assert s is not None
            assert s.vat_id == 'DE987654321'
            db.session.delete(s)
            db.session.commit()

    def test_add_supplier_missing_name_rejected(self, logged_client):
        """POST without company_name should not silently succeed."""
        resp = logged_client.post(
            '/nis2/supply-chain/add',
            data={'category': 'software'},
            follow_redirects=False,
        )
        # Must not return 200 with success (either 400 or redirect back)
        assert resp.status_code != 200 or b'hinzugef' not in resp.data


# ── Detail & Delete ───────────────────────────────────────────────────────────

class TestSupplyChainDetail:
    def test_detail_page_renders(self, logged_client, supplier):
        """GET /nis2/supply-chain/<id> → 200 with supplier name."""
        resp = logged_client.get(f'/nis2/supply-chain/{supplier.id}')
        assert resp.status_code == 200
        assert b'Test GmbH' in resp.data

    def test_detail_404_for_other_user(self, logged_client, supplier, db, app):
        """Another user should get 404 for a supplier they don't own."""
        # Create a second user and supplier
        from auth.models import User
        from app.nis2.models import Supplier
        with app.app_context():
            other = User(
                email='other@example.com',
                password_hash=generate_password_hash('pass'),
                first_name='Other', last_name='User', is_active=True,
            )
            db.session.add(other)
            db.session.flush()
            s2 = Supplier(
                user_id=other.id,
                company_name='Other GmbH',
                category='cloud',
                criticality='low',
            )
            db.session.add(s2)
            db.session.commit()
            other_supplier_id = s2.id

        resp = logged_client.get(f'/nis2/supply-chain/{other_supplier_id}')
        assert resp.status_code in (403, 404)

        with app.app_context():
            s2 = Supplier.query.get(other_supplier_id)
            if s2:
                db.session.delete(s2)
            other = User.query.filter_by(email='other@example.com').first()
            if other:
                db.session.delete(other)
            db.session.commit()

    def test_delete_supplier(self, logged_client, db, app, test_user):
        """POST /nis2/supply-chain/<id>/delete removes the supplier."""
        from app.nis2.models import Supplier
        with app.app_context():
            s = Supplier(
                user_id=test_user.id,
                company_name='Zu löschende GmbH',
                category='other',
                criticality='low',
            )
            db.session.add(s)
            db.session.commit()
            sid = s.id

        resp = logged_client.post(
            f'/nis2/supply-chain/{sid}/delete',
            follow_redirects=False,
        )
        assert resp.status_code in (302, 200)
        with app.app_context():
            assert Supplier.query.get(sid) is None


# ── Verify (mocked) ───────────────────────────────────────────────────────────

class TestSupplyChainVerify:
    def test_verify_returns_json(self, logged_client, supplier):
        """POST /nis2/supply-chain/<id>/verify → JSON with risk_score."""
        with patch('services.enrichment_flow.EnrichmentOrchestrator.enrich') as mock_enrich, \
             patch('services.sanctions.SanctionsService.check_sanctions') as mock_sanct:
            mock_enrich.return_value = {
                'success': True, 'prefill': {}, 'services': {}, 'messages': []
            }
            mock_sanct.return_value = {
                'status': 'ok', 'sanctions_found': [], 'checked_lists': ['eu', 'ofac', 'uk']
            }
            resp = logged_client.post(
                f'/nis2/supply-chain/{supplier.id}/verify',
                content_type='application/json',
            )
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'risk_score' in data
        assert isinstance(data['risk_score'], (int, float))
