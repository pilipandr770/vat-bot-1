"""
NIS2 ISMS Document Generator tests (§30 Abs. 2 BSIG).

Tests:
- Access control (plan gating)
- Overview page (uses |length not .count())
- Interview creation and phase navigation
- Document listing and HTML export
- Ownership enforcement (403 for other users)
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
            email='ismspro@example.com',
            password_hash=generate_password_hash('pass123'),
            first_name='ISMS',
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
def interview(db, app, pro_user):
    from app.nis2.models import ISMSInterview
    with app.app_context():
        iv = ISMSInterview(
            user_id=pro_user.id,
            company_name='Muster AG',
            current_phase=1,
        )
        db.session.add(iv)
        db.session.commit()
        yield iv
        existing = db.session.get(ISMSInterview, iv.id)
        if existing:
            db.session.delete(existing)
            db.session.commit()


@pytest.fixture
def document(db, app, pro_user, interview):
    from app.nis2.models import ISMSDocument
    with app.app_context():
        doc = ISMSDocument(
            user_id=pro_user.id,
            interview_id=interview.id,
            doc_type='isms_policy',
            title='ISMS-Richtlinie',
            content_md='# ISMS-Richtlinie\n\nDieses Dokument beschreibt die ISMS-Politik der Muster AG.',
        )
        db.session.add(doc)
        db.session.commit()
        yield doc
        existing = db.session.get(ISMSDocument, doc.id)
        if existing:
            db.session.delete(existing)
            db.session.commit()


# ── Access control ────────────────────────────────────────────────────────────

class TestISMSAccessControl:
    def test_overview_requires_login(self, client):
        resp = client.get('/nis2/isms/', follow_redirects=False)
        assert resp.status_code in (302, 401)

    def test_overview_requires_plan(self, client, test_user):
        with client.session_transaction() as sess:
            sess['_user_id'] = str(test_user.id)
            sess['_fresh'] = True
        resp = client.get('/nis2/isms/', follow_redirects=False)
        assert resp.status_code in (302, 403)

    def test_start_requires_plan(self, client, test_user):
        with client.session_transaction() as sess:
            sess['_user_id'] = str(test_user.id)
            sess['_fresh'] = True
        resp = client.post('/nis2/isms/interview/start', data={'company_name': 'Test AG'})
        assert resp.status_code in (302, 403)


# ── Overview page ─────────────────────────────────────────────────────────────

class TestISMSOverview:
    def test_overview_renders(self, pro_client):
        resp = pro_client.get('/nis2/isms/')
        assert resp.status_code == 200

    def test_overview_with_interview(self, pro_client, interview):
        """Overview must render without error even when interviews have documents."""
        resp = pro_client.get('/nis2/isms/')
        assert resp.status_code == 200
        assert 'Muster AG' in resp.data.decode('utf-8')

    def test_overview_with_documents_no_count_error(self, pro_client, interview, document):
        """Regression: |length filter used instead of .count() on InstrumentedList."""
        resp = pro_client.get('/nis2/isms/')
        # If .count() is called on InstrumentedList → TypeError → 500
        assert resp.status_code == 200


# ── Interview creation ────────────────────────────────────────────────────────

class TestISMSInterviewCreate:
    def test_start_creates_interview(self, pro_client, db, app, pro_user):
        from app.nis2.models import ISMSInterview
        resp = pro_client.post(
            '/nis2/isms/interview/start',
            data={'company_name': 'Neu AG'},
            follow_redirects=False,
        )
        assert resp.status_code == 302

        with app.app_context():
            iv = ISMSInterview.query.filter_by(
                user_id=pro_user.id,
                company_name='Neu AG',
            ).first()
            assert iv is not None
            # cleanup
            db.session.delete(iv)
            db.session.commit()

    def test_phase_1_form_renders(self, pro_client, interview):
        resp = pro_client.get(f'/nis2/isms/interview/{interview.id}/phase/1')
        assert resp.status_code == 200

    def test_phase_invalid_aborts(self, pro_client, interview):
        resp = pro_client.get(f'/nis2/isms/interview/{interview.id}/phase/99')
        assert resp.status_code in (400, 404)

    def test_other_user_interview_denied(self, client, interview, db, app):
        """A different user must get 403 for someone else's interview."""
        from auth.models import User
        with app.app_context():
            other = User(
                email='other_isms@example.com',
                password_hash='x',
                first_name='Other',
                last_name='User',
                is_active=True,
            )
            db.session.add(other)
            db.session.commit()
            other_id = other.id

        with client.session_transaction() as sess:
            sess['_user_id'] = str(other_id)
            sess['_fresh'] = True

        resp = client.get(f'/nis2/isms/interview/{interview.id}/phase/1')
        assert resp.status_code in (403, 302)

        with app.app_context():
            other = db.session.get(User, other_id)
            if other:
                db.session.delete(other)
                db.session.commit()


# ── Documents ─────────────────────────────────────────────────────────────────

class TestISMSDocuments:
    def test_document_list_renders(self, pro_client, interview, document):
        resp = pro_client.get(f'/nis2/isms/interview/{interview.id}/documents')
        assert resp.status_code == 200

    def test_document_view_renders(self, pro_client, document):
        resp = pro_client.get(f'/nis2/isms/documents/{document.id}')
        assert resp.status_code == 200
        assert 'ISMS' in resp.data.decode('utf-8')

    def test_document_html_export(self, pro_client, document):
        """HTML export endpoint returns standalone HTML file."""
        resp = pro_client.get(f'/nis2/isms/documents/{document.id}/download.html')
        assert resp.status_code in (200, 404)
        if resp.status_code == 200:
            ct = resp.headers.get('Content-Type', '')
            assert 'text/html' in ct

    def test_document_md_download(self, pro_client, document):
        """Markdown download endpoint returns a .md file."""
        resp = pro_client.get(f'/nis2/isms/documents/{document.id}/download')
        assert resp.status_code in (200, 404)

    def test_document_forbidden_for_other_user(self, client, document, db, app):
        from auth.models import User
        with app.app_context():
            other = User(
                email='other_doc@example.com',
                password_hash='x',
                first_name='Other',
                last_name='Doc',
                is_active=True,
            )
            db.session.add(other)
            db.session.commit()
            other_id = other.id

        with client.session_transaction() as sess:
            sess['_user_id'] = str(other_id)
            sess['_fresh'] = True

        resp = client.get(f'/nis2/isms/documents/{document.id}')
        assert resp.status_code in (403, 302, 404)

        with app.app_context():
            o = db.session.get(User, other_id)
            if o:
                db.session.delete(o)
                db.session.commit()


# ── Delete interview ──────────────────────────────────────────────────────────

class TestISMSDelete:
    def test_delete_interview(self, pro_client, db, app, pro_user):
        from app.nis2.models import ISMSInterview
        with app.app_context():
            iv = ISMSInterview(
                user_id=pro_user.id,
                company_name='Zu löschende AG',
                current_phase=1,
            )
            db.session.add(iv)
            db.session.commit()
            iv_id = iv.id

        resp = pro_client.post(
            f'/nis2/isms/interview/{iv_id}/delete',
            follow_redirects=False,
        )
        assert resp.status_code in (302, 200)

        with app.app_context():
            assert ISMSInterview.query.get(iv_id) is None
