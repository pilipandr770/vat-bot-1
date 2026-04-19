"""
Incident Response — Routes

Incident management with BSI Meldepflicht tracking.
"""

import json
import logging
from datetime import datetime

from flask import (abort, flash, jsonify, redirect, render_template,
                   request, url_for)
from flask_login import current_user, login_required

from crm.models import db
from ..models import Incident, IncidentDraft, IncidentTimeline, INCIDENT_CATEGORIES
from .bsi_draft import generate_bsi_draft, STAGE_META

logger = logging.getLogger(__name__)


def register_incident_routes(bp):

    # ── Dashboard ─────────────────────────────────────────────────
    @bp.route('/incidents/')
    @login_required
    def incidents_list():
        incidents = Incident.query.filter_by(user_id=current_user.id)\
            .order_by(Incident.detected_at.desc()).all()
        return render_template('nis2/incident_response/list.html',
                               incidents=incidents,
                               categories=INCIDENT_CATEGORIES,
                               now=datetime.utcnow())

    # ── Create incident ───────────────────────────────────────────
    @bp.route('/incidents/create', methods=['GET', 'POST'])
    @login_required
    def incident_create():
        if request.method == 'POST':
            detected_str = request.form.get('detected_at', '')
            occurred_str = request.form.get('occurred_at', '')

            detected_at = _parse_dt(detected_str) or datetime.utcnow()
            occurred_at = _parse_dt(occurred_str)

            incident = Incident(
                user_id=current_user.id,
                title=request.form['title'],
                category=request.form['category'],
                severity=request.form.get('severity', 'medium'),
                description=request.form.get('description', ''),
                affected_systems=request.form.get('affected_systems', ''),
                affected_data=request.form.get('affected_data', ''),
                detected_at=detected_at,
                occurred_at=occurred_at,
            )
            db.session.add(incident)
            db.session.flush()  # get ID before log

            incident.log('Incident erstellt', performed_by=str(current_user.id))
            db.session.commit()

            flash('Sicherheitsvorfall erfasst. BSI-Meldefristen wurden berechnet.', 'success')
            return redirect(url_for('nis2.incident_detail', incident_id=incident.id))

        return render_template('nis2/incident_response/create.html',
                               categories=INCIDENT_CATEGORIES,
                               now=datetime.utcnow())

    # ── Incident detail ───────────────────────────────────────────
    @bp.route('/incidents/<int:incident_id>')
    @login_required
    def incident_detail(incident_id: int):
        incident = Incident.query.get_or_404(incident_id)
        if incident.user_id != current_user.id:
            abort(403)
        drafts = IncidentDraft.query.filter_by(incident_id=incident_id)\
            .order_by(IncidentDraft.created_at.asc()).all()
        timeline = IncidentTimeline.query.filter_by(incident_id=incident_id)\
            .order_by(IncidentTimeline.timestamp.asc()).all()
        return render_template(
            'nis2/incident_response/detail.html',
            incident=incident,
            drafts=drafts,
            timeline=timeline,
            stage_meta=STAGE_META,
            now=datetime.utcnow(),
        )

    # ── Update incident ───────────────────────────────────────────
    @bp.route('/incidents/<int:incident_id>/update', methods=['POST'])
    @login_required
    def incident_update(incident_id: int):
        incident = Incident.query.get_or_404(incident_id)
        if incident.user_id != current_user.id:
            abort(403)

        old_status = incident.status
        incident.status = request.form.get('status', incident.status)
        incident.mitigation_steps = request.form.get('mitigation_steps', incident.mitigation_steps)
        incident.root_cause = request.form.get('root_cause', incident.root_cause)

        resolved_str = request.form.get('resolved_at', '')
        if resolved_str:
            incident.resolved_at = _parse_dt(resolved_str)

        if old_status != incident.status:
            incident.log(f'Status geändert: {old_status} → {incident.status}',
                         performed_by=str(current_user.id))
        db.session.commit()
        flash('Vorfall aktualisiert.', 'success')
        return redirect(url_for('nis2.incident_detail', incident_id=incident_id))

    # ── Generate BSI Meldung draft (AJAX) ─────────────────────────
    @bp.route('/incidents/<int:incident_id>/generate-draft', methods=['POST'])
    @login_required
    def incident_generate_draft(incident_id: int):
        incident = Incident.query.get_or_404(incident_id)
        if incident.user_id != current_user.id:
            abort(403)

        stage = request.json.get('stage') if request.json else request.form.get('stage')
        if not stage or stage not in STAGE_META:
            return jsonify({'error': 'Ungültige Meldungsstufe'}), 400

        # Build context for AI
        incident_data = {
            'company_name': request.json.get('company_name', '') if request.json else '',
            'sector': request.json.get('sector', '') if request.json else '',
            'contact_name': request.json.get('contact_name', '') if request.json else '',
            'contact_email': request.json.get('contact_email', '') if request.json else '',
            'title': incident.title,
            'category': incident.category,
            'description': incident.description,
            'affected_systems': incident.affected_systems or '',
            'affected_data': incident.affected_data or '',
            'detected_at': incident.detected_at.strftime('%d.%m.%Y %H:%M') if incident.detected_at else '',
            'occurred_at': incident.occurred_at.strftime('%d.%m.%Y %H:%M') if incident.occurred_at else '',
            'resolved_at': incident.resolved_at.strftime('%d.%m.%Y %H:%M') if incident.resolved_at else '',
            'mitigation_steps': incident.mitigation_steps or '',
            'root_cause': incident.root_cause or '',
            'bsi_reference': request.json.get('bsi_reference', '') if request.json else '',
        }

        content, error = generate_bsi_draft(stage, incident_data)
        if error:
            return jsonify({'error': error}), 500

        draft = IncidentDraft(
            incident_id=incident_id,
            stage=stage,
            content=content,
            generated_by_ai=True,
            created_at=datetime.utcnow(),
        )
        db.session.add(draft)
        incident.log(f'BSI-Meldungsentwurf generiert: {STAGE_META[stage]["label"]}',
                     performed_by=str(current_user.id))
        db.session.commit()

        return jsonify({'draft_id': draft.id, 'content': content})

    # ── View / edit draft ─────────────────────────────────────────
    @bp.route('/incidents/<int:incident_id>/draft/<int:draft_id>')
    @login_required
    def incident_draft_view(incident_id: int, draft_id: int):
        incident = Incident.query.get_or_404(incident_id)
        if incident.user_id != current_user.id:
            abort(403)
        draft = IncidentDraft.query.get_or_404(draft_id)
        return render_template('nis2/incident_response/draft_view.html',
                               incident=incident,
                               draft=draft,
                               stage_meta=STAGE_META)

    # ── Save edited draft ─────────────────────────────────────────
    @bp.route('/incidents/<int:incident_id>/draft/<int:draft_id>/save', methods=['POST'])
    @login_required
    def incident_draft_save(incident_id: int, draft_id: int):
        incident = Incident.query.get_or_404(incident_id)
        if incident.user_id != current_user.id:
            abort(403)
        draft = IncidentDraft.query.get_or_404(draft_id)
        draft.content = request.form.get('content', draft.content)
        draft.updated_at = datetime.utcnow()
        db.session.commit()
        flash('Entwurf gespeichert.', 'success')
        return redirect(url_for('nis2.incident_draft_view',
                                incident_id=incident_id, draft_id=draft_id))

    # ── Mark draft as submitted ───────────────────────────────────
    @bp.route('/incidents/<int:incident_id>/draft/<int:draft_id>/submit', methods=['POST'])
    @login_required
    def incident_draft_submit(incident_id: int, draft_id: int):
        incident = Incident.query.get_or_404(incident_id)
        if incident.user_id != current_user.id:
            abort(403)
        draft = IncidentDraft.query.get_or_404(draft_id)
        draft.submitted_at = datetime.utcnow()
        draft.bsi_reference = request.form.get('bsi_reference', '')
        incident.log(
            f'BSI-Meldung eingereicht: {STAGE_META.get(draft.stage, {}).get("label", draft.stage)} '
            f'(Referenz: {draft.bsi_reference or "unbekannt"})',
            performed_by=str(current_user.id),
        )
        db.session.commit()
        flash('Meldung als eingereicht markiert.', 'success')
        return redirect(url_for('nis2.incident_detail', incident_id=incident_id))

    # ── Add timeline entry ────────────────────────────────────────
    @bp.route('/incidents/<int:incident_id>/timeline/add', methods=['POST'])
    @login_required
    def incident_timeline_add(incident_id: int):
        incident = Incident.query.get_or_404(incident_id)
        if incident.user_id != current_user.id:
            abort(403)
        note = request.form.get('note', '').strip()
        if note:
            incident.log(note, performed_by=str(current_user.id))
            db.session.commit()
        return redirect(url_for('nis2.incident_detail', incident_id=incident_id))

    # ── Delete incident ───────────────────────────────────────────
    @bp.route('/incidents/<int:incident_id>/delete', methods=['POST'])
    @login_required
    def incident_delete(incident_id: int):
        incident = Incident.query.get_or_404(incident_id)
        if incident.user_id != current_user.id:
            abort(403)
        IncidentTimeline.query.filter_by(incident_id=incident_id).delete()
        IncidentDraft.query.filter_by(incident_id=incident_id).delete()
        db.session.delete(incident)
        db.session.commit()
        flash('Vorfall gelöscht.', 'success')
        return redirect(url_for('nis2.incidents_list'))


def _parse_dt(value: str) -> datetime | None:
    for fmt in ('%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M', '%d.%m.%Y %H:%M', '%d.%m.%Y'):
        try:
            return datetime.strptime(value.strip(), fmt)
        except (ValueError, AttributeError):
            continue
    return None
