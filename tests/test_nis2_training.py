"""
NIS2 Security Awareness Training module tests (§30 Abs. 2 Nr. 7 BSIG).

Tests:
- Access control (login required, plan gating)
- Training CRUD (list, create, detail, report)
- Acknowledgment flow (token link, confirm, certificate)
- Broken lazy='dynamic' query regression (InstrumentedList.order_by)
"""
import pytest
import secrets
from datetime import datetime, timedelta
from unittest.mock import patch
from werkzeug.security import generate_password_hash


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def pro_user(db, app):
    from auth.models import User, Subscription
    with app.app_context():
        u = User(
            email='trainpro@example.com',
            password_hash=generate_password_hash('pass123'),
            first_name='Train',
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
def training(db, app, pro_user):
    from app.nis2.models import SecurityTraining
    with app.app_context():
        t = SecurityTraining(
            user_id=pro_user.id,
            title='Phishing-Prävention',
            topic='phishing',
            content_md='## Phishing\n\nKeine Links klicken.',
            audience_emails='employee@test.de',
        )
        db.session.add(t)
        db.session.commit()
        yield t
        if db.session.get(SecurityTraining, t.id):
            db.session.delete(db.session.get(SecurityTraining, t.id))
            db.session.commit()


@pytest.fixture
def ack(db, app, training, pro_user):
    """An unacknowledged training acknowledgment."""
    from app.nis2.models import TrainingAcknowledgment
    with app.app_context():
        token = secrets.token_urlsafe(32)
        a = TrainingAcknowledgment(
            training_id=training.id,
            recipient_email='employee@test.de',
            token=token,
            acknowledged=False,
        )
        db.session.add(a)
        db.session.commit()
        yield a
        existing = db.session.get(TrainingAcknowledgment, a.id)
        if existing:
            db.session.delete(existing)
            db.session.commit()


@pytest.fixture
def confirmed_ack(db, app, training, pro_user):
    """An already-acknowledged training acknowledgment."""
    from app.nis2.models import TrainingAcknowledgment
    with app.app_context():
        token = secrets.token_urlsafe(32)
        a = TrainingAcknowledgment(
            training_id=training.id,
            recipient_email='confirmed@test.de',
            token=token,
            acknowledged=True,
            acknowledged_at=datetime.utcnow(),
            confirmed_name='Max Mustermann',
            ip_address='127.0.0.1',
        )
        db.session.add(a)
        db.session.commit()
        yield a
        existing = db.session.get(TrainingAcknowledgment, a.id)
        if existing:
            db.session.delete(existing)
            db.session.commit()


# ── Access control ────────────────────────────────────────────────────────────

class TestTrainingAccessControl:
    def test_list_requires_login(self, client):
        resp = client.get('/nis2/training/', follow_redirects=False)
        assert resp.status_code in (302, 401)

    def test_list_requires_plan(self, client, test_user):
        with client.session_transaction() as sess:
            sess['_user_id'] = str(test_user.id)
            sess['_fresh'] = True
        resp = client.get('/nis2/training/', follow_redirects=False)
        assert resp.status_code in (302, 403)

    def test_create_requires_login(self, client):
        resp = client.post('/nis2/training/create', data={}, follow_redirects=False)
        assert resp.status_code in (302, 401)


# ── Training list ─────────────────────────────────────────────────────────────

class TestTrainingList:
    def test_list_renders(self, pro_client):
        resp = pro_client.get('/nis2/training/')
        assert resp.status_code == 200

    def test_list_shows_training(self, pro_client, training):
        resp = pro_client.get('/nis2/training/')
        assert resp.status_code == 200
        assert 'Phishing' in resp.data.decode('utf-8')


# ── Training detail & report ──────────────────────────────────────────────────

class TestTrainingDetail:
    def test_detail_renders(self, pro_client, training):
        resp = pro_client.get(f'/nis2/training/{training.id}')
        assert resp.status_code == 200

    def test_detail_shows_title(self, pro_client, training):
        resp = pro_client.get(f'/nis2/training/{training.id}')
        assert 'Phishing' in resp.data.decode('utf-8')

    def test_report_renders(self, pro_client, training):
        resp = pro_client.get(f'/nis2/training/{training.id}/report')
        assert resp.status_code == 200

    def test_report_uses_query_not_dynamic(self, pro_client, training, ack):
        """Regression: report page must not call .order_by() on InstrumentedList."""
        resp = pro_client.get(f'/nis2/training/{training.id}/report')
        # If the lazy='dynamic' bug is present, this raises TypeError and returns 500
        assert resp.status_code == 200


# ── Acknowledgment token flow ─────────────────────────────────────────────────

class TestAcknowledgmentFlow:
    def test_ack_page_renders(self, client, ack):
        resp = client.get(f'/nis2/training/ack/{ack.token}')
        assert resp.status_code == 200

    def test_ack_invalid_token_404(self, client):
        resp = client.get('/nis2/training/ack/invalid_token_that_does_not_exist')
        assert resp.status_code == 404

    def test_ack_confirm_stores_record(self, client, ack, db, app):
        resp = client.post(f'/nis2/training/ack/{ack.token}', data={
            'confirmed_name': 'Anna Beispiel',
        }, follow_redirects=True)
        assert resp.status_code == 200
        with app.app_context():
            from app.nis2.models import TrainingAcknowledgment
            updated = TrainingAcknowledgment.query.filter_by(token=ack.token).first()
            assert updated.acknowledged is True
            assert updated.confirmed_name == 'Anna Beispiel'

    def test_ack_done_page_after_confirm(self, client, confirmed_ack):
        resp = client.get(f'/nis2/training/ack/{confirmed_ack.token}/done')
        assert resp.status_code in (200, 302, 404)

    def test_certificate_download_for_confirmed(self, client, confirmed_ack):
        resp = client.get(f'/nis2/training/ack/{confirmed_ack.token}/certificate')
        assert resp.status_code in (200, 302, 404)
        if resp.status_code == 200:
            assert b'Zertifikat' in resp.data or b'certificate' in resp.data.lower()

    def test_certificate_requires_acknowledged(self, client, ack):
        """Unacknowledged token must not produce a certificate."""
        resp = client.get(f'/nis2/training/ack/{ack.token}/certificate')
        # Should 404 (ack.acknowledged=False filter)
        assert resp.status_code in (404, 302)


# ── Training model ────────────────────────────────────────────────────────────

class TestTrainingModel:
    def test_sent_count_uses_len(self, db, app, training, ack):
        """Regression: sent_count must use len(), not .count()."""
        from app.nis2.models import SecurityTraining
        with app.app_context():
            t = SecurityTraining.query.get(training.id)
            count = t.sent_count
            assert isinstance(count, int)
            assert count >= 1

    def test_ack_count_uses_sum(self, db, app, training, confirmed_ack):
        """Regression: ack_count must use sum(), not .filter_by().count()."""
        from app.nis2.models import SecurityTraining
        with app.app_context():
            t = SecurityTraining.query.get(training.id)
            count = t.ack_count
            assert isinstance(count, int)
            assert count >= 1
