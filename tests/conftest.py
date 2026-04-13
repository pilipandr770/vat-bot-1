"""
Pytest configuration and shared fixtures for VAT Bot test suite.
"""
import os
import pytest

os.environ.setdefault('FLASK_ENV', 'testing')
os.environ.setdefault('SECRET_KEY', 'test-secret-key')
os.environ.setdefault('MAILGUARD_ENCRYPTION_KEY', '')
# Use no schema for SQLite — empty string resolves to None in auth/models.py
os.environ['DB_SCHEMA'] = ''


@pytest.fixture(scope='session')
def app():
    """Create application for testing."""
    from application import create_app
    flask_app = create_app('testing')
    flask_app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'WTF_CSRF_ENABLED': False,
        'SERVER_NAME': 'localhost',
    })
    yield flask_app


@pytest.fixture(scope='session')
def db(app):
    """Set up test database."""
    from crm.models import db as _db
    with app.app_context():
        _db.create_all()
        yield _db
        _db.drop_all()


@pytest.fixture
def client(app):
    """Flask test client."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Flask CLI test runner."""
    return app.test_cli_runner()


@pytest.fixture
def test_user(db, app):
    """Create a basic test user."""
    from auth.models import User
    from werkzeug.security import generate_password_hash
    with app.app_context():
        user = User(
            email='test@example.com',
            password_hash=generate_password_hash('testpass123'),
            first_name='Test',
            last_name='User',
            is_active=True,
        )
        db.session.add(user)
        db.session.commit()
        yield user
        db.session.delete(user)
        db.session.commit()


@pytest.fixture
def admin_user(db, app):
    """Create an admin test user."""
    from auth.models import User
    from werkzeug.security import generate_password_hash
    with app.app_context():
        user = User(
            email='admin@example.com',
            password_hash=generate_password_hash('adminpass123'),
            first_name='Admin',
            last_name='User',
            is_active=True,
            is_admin=True,
        )
        db.session.add(user)
        db.session.commit()
        yield user
        db.session.delete(user)
        db.session.commit()


@pytest.fixture
def auth_client(client, test_user, app):
    """Test client with authenticated user session."""
    with app.app_context():
        with client.session_transaction() as sess:
            sess['_user_id'] = str(test_user.id)
            sess['_fresh'] = True
    return client
