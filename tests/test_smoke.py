"""
Smoke tests — verify the application starts and basic routes respond.
"""


class TestPublicRoutes:
    def test_landing_page(self, client):
        """GET / returns 200."""
        response = client.get('/')
        assert response.status_code == 200

    def test_login_page(self, client):
        """GET /auth/login returns 200."""
        response = client.get('/auth/login')
        assert response.status_code == 200

    def test_register_page(self, client):
        """GET /auth/register returns 200."""
        response = client.get('/auth/register')
        assert response.status_code == 200

    def test_healthz(self, client):
        """GET /healthz returns 200 with ok status."""
        response = client.get('/healthz')
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'ok'

    def test_readyz(self, client):
        """GET /readyz returns 200 when DB is available."""
        response = client.get('/readyz')
        # May be 200 or 503 depending on DB; just ensure JSON response
        assert response.content_type == 'application/json'
        data = response.get_json()
        assert 'status' in data
        assert 'checks' in data

    def test_robots_txt(self, client):
        """GET /robots.txt returns a response."""
        response = client.get('/robots.txt')
        assert response.status_code in (200, 404)  # 404 if static file missing in test env


class TestAuthRequired:
    def test_dashboard_redirects_unauthenticated(self, client):
        """GET /dashboard redirects to login when not authenticated."""
        response = client.get('/dashboard', follow_redirects=False)
        assert response.status_code in (302, 401)

    def test_verify_requires_auth(self, client):
        """POST /verify returns 401 when not authenticated."""
        response = client.post(
            '/verify',
            json={'company_vat': 'DE123456789', 'company_name': 'Test GmbH'},
        )
        assert response.status_code == 401

    def test_history_requires_auth(self, client):
        """GET /history redirects to login when not authenticated."""
        response = client.get('/history', follow_redirects=False)
        assert response.status_code in (302, 401)


class TestMakeAdminRouteRemoved:
    def test_make_admin_route_does_not_exist(self, client):
        """The /make-admin/<email> vulnerability has been removed."""
        response = client.get('/make-admin/attacker@evil.com')
        assert response.status_code == 404


class TestNoMakeAdminRoute:
    """Regression test — confirm privilege escalation route is gone."""

    def test_cannot_make_admin_via_get(self, client):
        """Even unauthenticated GET returns 404 — route is gone."""
        response = client.get('/make-admin/victim@example.com')
        assert response.status_code == 404


class TestProductionConfigGuards:
    def test_production_blocks_insecure_secret_key(self, app, monkeypatch):
        """ProductionConfig must reject the default insecure SECRET_KEY."""
        import pytest
        from application import create_app  # module already loaded by session fixture
        monkeypatch.setenv('SECRET_KEY', 'dev-secret-key-change-in-production')
        monkeypatch.setenv('DATABASE_URL', 'postgresql://x:y@localhost:5432/z')
        monkeypatch.setenv('MAILGUARD_ENCRYPTION_KEY', 'somekey')
        # ProductionConfig.__init__ detects insecure SECRET_KEY → RuntimeError
        with pytest.raises(RuntimeError, match='(?i)insecure|SECRET_KEY'):
            create_app('production')


class TestChatbotOriginProtection:
    def test_sales_chatbot_blocks_foreign_origin(self, client):
        """POST from a foreign Origin is rejected with 403."""
        response = client.post(
            '/api/sales-chat',
            json={'message': 'hello'},
            headers={'Origin': 'https://evil.example.com'},
        )
        assert response.status_code == 403

    def test_sales_chatbot_blocks_missing_origin(self, client):
        """POST without any Origin header is also rejected."""
        response = client.post(
            '/api/sales-chat',
            json={'message': 'hello'},
        )
        assert response.status_code == 403
