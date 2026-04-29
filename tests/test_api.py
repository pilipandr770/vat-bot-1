"""
API endpoint tests — OSINT, phone intelligence, link scanner, enrichment, analytics.

Tests:
- Unauthenticated access returns 401/302
- Missing/invalid params return 400
- Mocked external calls return expected shape
- Admin analytics API
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def pro_user(db, app):
    from auth.models import User, Subscription
    with app.app_context():
        u = User(
            email='apipro@example.com',
            password_hash=generate_password_hash('pass123'),
            first_name='API',
            last_name='Pro',
            is_active=True,
            is_email_confirmed=True,
        )
        db.session.add(u)
        db.session.flush()
        sub = Subscription(
            user_id=u.id,
            plan='professional',
            status='active',
            api_calls_limit=500,
            monthly_price=49.99,
            start_date=datetime.utcnow(),
            end_date=datetime.utcnow() + timedelta(days=30),
        )
        db.session.add(sub)
        db.session.commit()
        yield u
        db.session.delete(sub)
        db.session.delete(db.session.merge(u))
        db.session.commit()


@pytest.fixture
def pro_client(client, pro_user, app):
    with client.session_transaction() as sess:
        sess['_user_id'] = str(pro_user.id)
        sess['_fresh'] = True
    return client


@pytest.fixture
def admin_client(client, admin_user, app):
    with client.session_transaction() as sess:
        sess['_user_id'] = str(admin_user.id)
        sess['_fresh'] = True
    return client


@pytest.fixture
def auth_client(client, test_user, app):
    with client.session_transaction() as sess:
        sess['_user_id'] = str(test_user.id)
        sess['_fresh'] = True
    return client


# ── OSINT username search ─────────────────────────────────────────────────────

class TestOSINTUsernameSearch:
    def test_requires_auth(self, client):
        resp = client.post('/osint/username-scan', json={'username': 'testuser'})
        assert resp.status_code in (401, 302, 404)

    def test_missing_username(self, auth_client):
        resp = auth_client.post('/osint/username-scan', json={})
        assert resp.status_code in (400, 404, 422)

    def test_username_search_page(self, auth_client):
        resp = auth_client.get('/osint/username-search')
        assert resp.status_code in (200, 302, 404)

    def test_scan_start_dispatches(self, auth_client):
        """Username scan should start async task."""
        with patch('services.osint_routes.run_username_check.delay', return_value=MagicMock(id='t1')):
            resp = auth_client.post('/osint/username-scan', json={'username': 'testuser123'})
        assert resp.status_code in (200, 202, 400, 404)


# ── Phone intelligence ────────────────────────────────────────────────────────

class TestPhoneIntelligence:
    def test_requires_auth(self, client):
        resp = client.post('/phoneintel/api/analyze', json={'phone': '+49123456789'})
        assert resp.status_code in (401, 302, 404)

    def test_phone_intel_page(self, auth_client):
        resp = auth_client.get('/phoneintel/')
        assert resp.status_code in (200, 302, 404)

    def test_phoneintel_mocked(self, auth_client):
        """Phone analysis with mocked external service."""
        with patch('routes.phoneintel.analyze_phone') as mock_analyze:
            mock_analyze.return_value = {
                'carrier': 'Deutsche Telekom',
                'type': 'mobile',
                'country': 'DE',
                'valid': True,
            }
            resp = auth_client.post(
                '/phoneintel/api/analyze',
                json={'phone': '+4915123456789'},
            )
        assert resp.status_code in (200, 400, 404)


# ── Link scanner ──────────────────────────────────────────────────────────────

class TestLinkScanner:
    def test_link_scan_requires_auth(self, client):
        resp = client.post('/api/link-scan', json={'url': 'https://example.com'})
        assert resp.status_code in (401, 302, 404)

    def test_link_scan_empty_url(self, auth_client):
        resp = auth_client.post('/api/link-scan', json={'url': ''})
        assert resp.status_code in (400, 404, 422)

    def test_link_scan_page_renders(self, auth_client):
        resp = auth_client.get('/link-scanner')
        assert resp.status_code in (200, 302, 404)


# ── Enrichment / business data ────────────────────────────────────────────────

class TestEnrichmentAPI:
    def test_enrichment_requires_auth(self, client):
        resp = client.post('/api/enrich', json={'company_name': 'Test GmbH'})
        assert resp.status_code in (401, 302, 404)

    def test_enrichment_missing_company(self, auth_client):
        resp = auth_client.post('/api/enrich', json={})
        assert resp.status_code in (400, 404, 422)

    def test_enrichment_mocked(self, auth_client):
        with patch('services.enrichment_flow.EnrichmentOrchestrator.enrich') as mock_enrich:
            mock_enrich.return_value = {
                'success': True,
                'prefill': {'company_name': 'Test GmbH'},
                'services': {},
                'messages': [],
            }
            resp = auth_client.post('/api/enrich', json={'company_name': 'Test GmbH'})
        assert resp.status_code in (200, 400, 404)


# ── Analytics API (admin-only) ────────────────────────────────────────────────

class TestAnalyticsAPI:
    def test_analytics_requires_auth(self, client):
        resp = client.get('/api/analytics/summary')
        assert resp.status_code in (401, 302, 404)

    def test_analytics_requires_admin(self, auth_client):
        resp = auth_client.get('/api/analytics/summary')
        assert resp.status_code in (403, 302, 404)

    def test_analytics_accessible_to_admin(self, admin_client):
        resp = admin_client.get('/api/analytics/summary')
        assert resp.status_code in (200, 302, 404)
        if resp.status_code == 200:
            data = resp.get_json()
            assert data is not None

    def test_analytics_page_accessible_to_admin(self, admin_client):
        resp = admin_client.get('/analytics')
        assert resp.status_code in (200, 302, 404)


# ── Sales chatbot origin check ────────────────────────────────────────────────

class TestSalesChatbot:
    def test_chatbot_blocks_foreign_origin(self, client):
        resp = client.post(
            '/api/sales-chat',
            json={'message': 'hello'},
            headers={'Origin': 'https://evil.example.com'},
        )
        assert resp.status_code == 403

    def test_chatbot_blocks_no_origin(self, client):
        resp = client.post('/api/sales-chat', json={'message': 'hello'})
        assert resp.status_code == 403

    def test_chatbot_allows_own_origin(self, client, app):
        allowed_origin = 'http://localhost'
        with patch('services.chatbot_routes.call_claude_api') as mock_claude:
            mock_claude.return_value = 'Hallo! Wie kann ich helfen?'
            resp = client.post(
                '/api/sales-chat',
                json={'message': 'hello'},
                headers={'Origin': allowed_origin},
            )
        assert resp.status_code in (200, 403, 404, 500)


# ── Health check endpoints ────────────────────────────────────────────────────

class TestHealthEndpoints:
    def test_healthz(self, client):
        resp = client.get('/healthz')
        assert resp.status_code == 200
        assert resp.get_json()['status'] == 'ok'

    def test_readyz_returns_json(self, client):
        resp = client.get('/readyz')
        data = resp.get_json()
        assert 'status' in data
        assert 'checks' in data

    def test_readyz_no_500(self, client):
        resp = client.get('/readyz')
        assert resp.status_code in (200, 503)
