"""
ISMS Docs — Routes

4-phase interview + AI document generation endpoint.
"""

import json
import logging
from datetime import datetime

from flask import (abort, current_app, flash, jsonify, make_response, redirect,
                   render_template, request, send_file, url_for)
from services.security_helpers import require_plan
from flask_login import current_user, login_required

from crm.models import db
from ..models import ISMSDocument, ISMSInterview, ISMS_DOC_TYPES_MAP
from .generator import ISMSDocumentGenerator, get_phase_definitions

logger = logging.getLogger(__name__)

_NUM_PHASES = 4


def register_isms_routes(bp):
    # ── Overview ─────────────────────────────────────────────────
    @bp.route('/isms/')
    @login_required
    @require_plan("professional")
    def isms_overview():
        interviews = ISMSInterview.query.filter_by(user_id=current_user.id)\
            .order_by(ISMSInterview.updated_at.desc()).all()
        return render_template('nis2/isms_docs/overview.html',
                               interviews=interviews,
                               doc_types=ISMS_DOC_TYPES_MAP)

    # ── Start new interview ───────────────────────────────────────
    @bp.route('/isms/interview/start', methods=['POST'])
    @login_required
    @require_plan("professional")
    def isms_start():
        interview = ISMSInterview(
            user_id=current_user.id,
            company_name=request.form.get('company_name', ''),
            current_phase=1,
        )
        db.session.add(interview)
        db.session.commit()
        return redirect(url_for('nis2.isms_phase', interview_id=interview.id, phase=1))

    # ── Phase form ───────────────────────────────────────────────
    @bp.route('/isms/interview/<int:interview_id>/phase/<int:phase>',
              methods=['GET', 'POST'])
    @login_required
    @require_plan("professional")
    def isms_phase(interview_id: int, phase: int):
        interview = ISMSInterview.query.get_or_404(interview_id)
        if interview.user_id != current_user.id:
            abort(403)
        if phase < 1 or phase > _NUM_PHASES:
            abort(404)

        phases = get_phase_definitions()
        phase_def = phases[phase]

        if request.method == 'POST':
            # Save answers for this phase
            answers = _collect_phase_answers(request.form, phase_def['questions'])
            interview.set_phase_data(phase, answers)
            interview.current_phase = max(interview.current_phase, phase)
            interview.updated_at = datetime.utcnow()
            db.session.commit()

            next_phase = phase + 1
            if next_phase > _NUM_PHASES:
                return redirect(url_for('nis2.isms_review', interview_id=interview_id))
            return redirect(url_for('nis2.isms_phase', interview_id=interview_id,
                                    phase=next_phase))

        # Pre-fill previously saved answers
        saved = interview.get_phase_data(phase) or {}
        return render_template(
            'nis2/isms_docs/interview_phase.html',
            interview=interview,
            phase=phase,
            phase_def=phase_def,
            phases=phases,
            saved=saved,
            total_phases=_NUM_PHASES,
        )

    # ── Review & confirm ─────────────────────────────────────────
    @bp.route('/isms/interview/<int:interview_id>/review')
    @login_required
    @require_plan("professional")
    def isms_review(interview_id: int):
        interview = ISMSInterview.query.get_or_404(interview_id)
        if interview.user_id != current_user.id:
            abort(403)

        all_data = interview.get_all_data()
        phase4 = interview.get_phase_data(4) or {}
        selected_docs = _parse_selected_docs(phase4.get('documents_to_generate', []))

        return render_template(
            'nis2/isms_docs/review.html',
            interview=interview,
            all_data=all_data,
            selected_docs=selected_docs,
            doc_types=ISMS_DOC_TYPES_MAP,
        )

    # ── Generate documents (AJAX) ─────────────────────────────────
    @bp.route('/isms/interview/<int:interview_id>/generate', methods=['POST'])
    @login_required
    @require_plan("professional")
    def isms_generate(interview_id: int):
        """Legacy bulk-generate — kept for back-compat. Returns list of doc_types to generate."""
        interview = ISMSInterview.query.get_or_404(interview_id)
        if interview.user_id != current_user.id:
            abort(403)
        phase4 = interview.get_phase_data(4) or {}
        selected_docs = _parse_selected_docs(phase4.get('documents_to_generate', []))
        return jsonify({'doc_types': selected_docs})

    @bp.route('/isms/interview/<int:interview_id>/generate-one', methods=['POST'])
    @login_required
    @require_plan("professional")
    def isms_generate_one(interview_id: int):
        """Generate a single document. Called sequentially by JS to avoid worker timeout."""
        interview = ISMSInterview.query.get_or_404(interview_id)
        if interview.user_id != current_user.id:
            abort(403)

        data = request.get_json() or {}
        doc_type_key = data.get('doc_type', '').strip()
        if not doc_type_key:
            return jsonify({'error': 'doc_type required'}), 400

        all_data = interview.get_all_data()
        doc_meta = ISMS_DOC_TYPES_MAP.get(doc_type_key, {})
        doc_name = doc_meta.get('title', doc_type_key) if isinstance(doc_meta, dict) else str(doc_meta)

        existing = ISMSDocument.query.filter_by(
            interview_id=interview_id,
            doc_type=doc_type_key,
        ).first()

        if existing and not data.get('regenerate'):
            return jsonify({'doc_type': doc_type_key, 'id': existing.id, 'cached': True})

        generator = ISMSDocumentGenerator()
        content, error = generator.generate_document(doc_type_key, all_data)
        if error:
            return jsonify({'doc_type': doc_type_key, 'error': error}), 500

        if existing:
            existing.content_md = content
            existing.content = content
            doc = existing
        else:
            doc = ISMSDocument(
                user_id=current_user.id,
                interview_id=interview_id,
                doc_type=doc_type_key,
                title=doc_name,
                content_md=content,
                content=content,
                is_generated=True,
            )
            db.session.add(doc)

        interview.completed_at = datetime.utcnow()
        db.session.commit()
        return jsonify({'doc_type': doc_type_key, 'id': doc.id, 'cached': False})

    # ── Document list ─────────────────────────────────────────────
    @bp.route('/isms/interview/<int:interview_id>/documents')
    @login_required
    @require_plan("professional")
    def isms_documents(interview_id: int):
        interview = ISMSInterview.query.get_or_404(interview_id)
        if interview.user_id != current_user.id:
            abort(403)
        docs = ISMSDocument.query.filter_by(interview_id=interview_id).all()
        return render_template('nis2/isms_docs/documents.html',
                               interview=interview,
                               docs=docs,
                               doc_types=ISMS_DOC_TYPES_MAP)

    # ── Document detail / view ────────────────────────────────────
    @bp.route('/isms/documents/<int:doc_id>')
    @login_required
    @require_plan("professional")
    def isms_document_view(doc_id: int):
        doc = ISMSDocument.query.get_or_404(doc_id)
        if doc.user_id != current_user.id:
            abort(403)
        return render_template('nis2/isms_docs/document_view.html', doc=doc)

    # ── Document download (Markdown) ──────────────────────────────
    @bp.route('/isms/documents/<int:doc_id>/download')
    @login_required
    @require_plan("professional")
    def isms_document_download(doc_id: int):
        doc = ISMSDocument.query.get_or_404(doc_id)
        if doc.user_id != current_user.id:
            abort(403)

        import io
        filename = f'{doc.doc_type}_{datetime.utcnow().strftime("%Y%m%d")}.md'
        buf = io.BytesIO(doc.content.encode('utf-8'))
        buf.seek(0)
        return send_file(
            buf,
            as_attachment=True,
            download_name=filename,
            mimetype='text/markdown; charset=utf-8',
        )

    # ── Document download (HTML — print-friendly) ─────────────────
    @bp.route('/isms/documents/<int:doc_id>/download.html')
    @login_required
    @require_plan("professional")
    def isms_document_download_html(doc_id: int):
        doc = ISMSDocument.query.get_or_404(doc_id)
        if doc.user_id != current_user.id:
            abort(403)
        html = render_template('nis2/isms_docs/document_export.html',
                               doc=doc, user=current_user)
        filename = f'{doc.doc_type}_{datetime.utcnow().strftime("%Y%m%d")}.html'
        response = make_response(html)
        response.headers['Content-Type'] = 'text/html; charset=utf-8'
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    # ── Delete interview ──────────────────────────────────────────
    @bp.route('/isms/interview/<int:interview_id>/delete', methods=['POST'])
    @login_required
    @require_plan("professional")
    def isms_delete_interview(interview_id: int):
        interview = ISMSInterview.query.get_or_404(interview_id)
        if interview.user_id != current_user.id:
            abort(403)
        # Cascade delete documents
        ISMSDocument.query.filter_by(interview_id=interview_id).delete()
        db.session.delete(interview)
        db.session.commit()
        flash('Interview und alle zugehörigen Dokumente wurden gelöscht.', 'success')
        return redirect(url_for('nis2.isms_overview'))


# ─────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────

def _collect_phase_answers(form_data, questions: list) -> dict:
    """Extract question answers from form data, handling checkboxes correctly."""
    answers = {}
    for q in questions:
        key = q['key']
        if q['type'] == 'checkboxes':
            answers[key] = form_data.getlist(key)
        else:
            answers[key] = form_data.get(key, '')
    return answers


def _parse_selected_docs(raw) -> list:
    """
    The documents_to_generate field is a list of 'doc_type_key|Label' strings.
    Returns a list of just the doc_type_keys.
    """
    if isinstance(raw, str):
        raw = [raw]
    result = []
    for item in (raw or []):
        key = item.split('|')[0] if '|' in item else item
        if key:
            result.append(key)
    return result
