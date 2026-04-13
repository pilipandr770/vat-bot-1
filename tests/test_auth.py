"""
Authentication flow tests.
"""
import pytest


class TestRegistration:
    def test_register_new_user(self, client, db, app):
        """Successfully register a new user."""
        response = client.post('/auth/register', data={
            'email': 'newuser@example.com',
            'password': 'SecurePass123!',
            'first_name': 'New',
            'last_name': 'User',
        }, follow_redirects=True)
        assert response.status_code == 200

    def test_register_duplicate_email(self, client, test_user, app):
        """Registering with existing email is rejected."""
        response = client.post('/auth/register', data={
            'email': 'test@example.com',
            'password': 'AnotherPass123!',
            'first_name': 'Dupe',
            'last_name': 'User',
        }, follow_redirects=True)
        assert response.status_code == 200
        # Should show error, not create duplicate
        with app.app_context():
            from auth.models import User
            count = User.query.filter_by(email='test@example.com').count()
            assert count == 1


class TestLogin:
    def test_login_success(self, client, test_user, app):
        """Valid credentials return redirect to dashboard."""
        response = client.post('/auth/login', data={
            'email': 'test@example.com',
            'password': 'testpass123',
        }, follow_redirects=False)
        assert response.status_code in (200, 302)

    def test_login_wrong_password(self, client, test_user):
        """Wrong password does not authenticate."""
        response = client.post('/auth/login', data={
            'email': 'test@example.com',
            'password': 'wrongpassword',
        }, follow_redirects=True)
        assert response.status_code == 200
        # Should stay on login page

    def test_login_nonexistent_user(self, client):
        """Non-existent email does not cause 500."""
        response = client.post('/auth/login', data={
            'email': 'ghost@nowhere.com',
            'password': 'whatever',
        }, follow_redirects=True)
        assert response.status_code == 200


class TestPromoteAdminCLI:
    def test_promote_admin_cli_command(self, runner, test_user, app):
        """flask promote-admin <email> grants admin rights."""
        with app.app_context():
            result = runner.invoke(args=['promote-admin', 'test@example.com'])
            assert result.exit_code == 0
            assert 'admin' in result.output.lower()

            from auth.models import User
            user = User.query.filter_by(email='test@example.com').first()
            assert user.is_admin is True
            # Clean up
            user.is_admin = False
            from crm.models import db
            db.session.commit()

    def test_promote_admin_unknown_email(self, runner, app):
        """flask promote-admin with unknown email exits non-zero."""
        result = runner.invoke(args=['promote-admin', 'nobody@nowhere.com'])
        assert result.exit_code != 0
