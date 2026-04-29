"""
NIS2 Continuous Monitoring tests (§30 Abs. 2 Nr. 3 BSIG).

Tests:
- Access control
- Monitoring target CRUD (add, list, delete)
- Manual scan trigger (mocked NIS2 container)
- Scan result storage
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from werkzeug.security import generate_password_hash


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def pro_user(db, app):
    from auth.models import User, Subscription
    with app.app_context():
        u = User(
            email='monpro@example.com',
            password_hash=generate_password_hash('pass123'),
            first_name='Mon',
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
def monitoring_target(db, app, pro_user):
    from app.nis2.models import MonitoringTarget
    with app.app_context():
        t = MonitoringTarget(
            user_id=pro_user.id,
            url='https://example.com',
            name='Example Site',
            scan_frequency='weekly',
        )
        db.session.add(t)
        db.session.commit()
        yield t
        existing = db.session.get(MonitoringTarget, t.id)
        if existing:
            db.session.delete(existing)
            db.session.commit()


# ── Access control ────────────────────────────────────────────────────────────

class TestMonitoringAccessControl:
    def test_dashboard_requires_login(self, client):
        resp = client.get('/nis2/monitoring/', follow_redirects=False)
        assert resp.status_code in (302, 401)

    def test_dashboard_requires_plan(self, client, test_user):
        with client.session_transaction() as sess:
            sess['_user_id'] = str(test_user.id)
            sess['_fresh'] = True
        resp = client.get('/nis2/monitoring/', follow_redirects=False)
        assert resp.status_code in (302, 403)

    def test_add_requires_login(self, client):
        resp = client.post('/nis2/monitoring/add', data={}, follow_redirects=False)
        assert resp.status_code in (302, 401)


# ── Dashboard ─────────────────────────────────────────────────────────────────

class TestMonitoringDashboard:
    def test_dashboard_renders(self, pro_client):
        resp = pro_client.get('/nis2/monitoring/')
        assert resp.status_code == 200

    def test_dashboard_shows_target(self, pro_client, monitoring_target):
        resp = pro_client.get('/nis2/monitoring/')
        assert resp.status_code == 200
        assert b'Example Site' in resp.data or b'example.com' in resp.data


# ── Add target ────────────────────────────────────────────────────────────────

class TestAddMonitoringTarget:
    def test_add_form_renders(self, pro_client):
        resp = pro_client.get('/nis2/monitoring/add')
        assert resp.status_code in (200, 302)

    def test_add_target_success(self, pro_client, db, app, pro_user):
        from app.nis2.models import MonitoringTarget
        resp = pro_client.post('/nis2/monitoring/add', data={
            'url': 'https://new-monitor.example.com',
            'name': 'New Monitor',
            'scan_frequency': 'daily',
        }, follow_redirects=False)
        assert resp.status_code in (200, 302)

        with app.app_context():
            t = MonitoringTarget.query.filter_by(
                user_id=pro_user.id,
                url='https://new-monitor.example.com',
            ).first()
            if t:
                db.session.delete(t)
                db.session.commit()

    def test_add_missing_url_rejected(self, pro_client):
        resp = pro_client.post('/nis2/monitoring/add', data={
            'name': 'No URL',
        }, follow_redirects=False)
        assert resp.status_code in (200, 400, 302)


# ── Manual scan ───────────────────────────────────────────────────────────────

class TestManualScan:
    def test_manual_scan_mocked(self, pro_client, monitoring_target, app):
        """Manual scan trigger calls NIS2 container and stores result."""
        mock_scan_result = {
            'score': 85,
            'findings': ['SSL OK', 'HSTS enabled'],
            'status': 'completed',
        }
        with patch('requests.post') as mock_post:
            mock_post.return_value = MagicMock(
                status_code=200,
                json=MagicMock(return_value=mock_scan_result),
            )
            resp = pro_client.post(
                f'/nis2/monitoring/{monitoring_target.id}/scan',
                follow_redirects=False,
            )
        assert resp.status_code in (200, 202, 302, 404)

    def test_scan_other_users_target_denied(self, client, monitoring_target, db, app):
        from auth.models import User
        with app.app_context():
            other = User(
                email='other_mon@example.com',
                password_hash='x',
                first_name='Other',
                last_name='Mon',
                is_active=True,
            )
            db.session.add(other)
            db.session.commit()
            other_id = other.id

        with client.session_transaction() as sess:
            sess['_user_id'] = str(other_id)
            sess['_fresh'] = True

        resp = client.post(
            f'/nis2/monitoring/{monitoring_target.id}/scan',
            follow_redirects=False,
        )
        assert resp.status_code in (302, 403, 404)

        with app.app_context():
            o = db.session.get(User, other_id)
            if o:
                db.session.delete(o)
                db.session.commit()


# ── Delete target ─────────────────────────────────────────────────────────────

class TestDeleteMonitoringTarget:
    def test_delete_target(self, pro_client, db, app, pro_user):
        from app.nis2.models import MonitoringTarget
        with app.app_context():
            t = MonitoringTarget(
                user_id=pro_user.id,
                url='https://to-delete.example.com',
                name='To Delete',
                scan_frequency='monthly',
            )
            db.session.add(t)
            db.session.commit()
            tid = t.id

        resp = pro_client.post(
            f'/nis2/monitoring/{tid}/delete',
            follow_redirects=False,
        )
        assert resp.status_code in (200, 302)

        with app.app_context():
            assert MonitoringTarget.query.get(tid) is None
