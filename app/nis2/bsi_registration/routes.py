"""
BSI-Registrierungs-Assistent — Routes

Wizard for §33 BSIG registration via BSI MUK-Portal.
- Betroffenheits-Check (no login required)
- 5-step registration wizard
- PDF/JSON export
"""

import json
import secrets
from datetime import datetime

from flask import render_template, request, jsonify, redirect, url_for, flash, send_file
from flask_login import login_required, current_user
from crm.models import db

from ..models import BSIRegistration, NIS2_SECTORS, NIS2_SECTOR_GROUPS, LEGAL_FORMS


def register_bsi_routes(bp):

    # ── Public: Betroffenheits-Check ─────────────────────────────────────

    @bp.route('/bsi-registration/')
    def bsi_registration_landing():
        """Landing page — BSI registration overview."""
        reg = None
        if current_user.is_authenticated:
            reg = BSIRegistration.query.filter_by(user_id=current_user.id).order_by(
                BSIRegistration.created_at.desc()
            ).first()
        return render_template('nis2/bsi_registration/landing.html',
                               registration=reg,
                               sectors=NIS2_SECTORS,
                               sector_groups=NIS2_SECTOR_GROUPS,
                               legal_forms=LEGAL_FORMS)

    @bp.route('/bsi-registration/check', methods=['GET', 'POST'])
    def bsi_check():
        """
        Public Betroffenheits-Check.
        Determines if the company is subject to NIS2 without requiring login.
        """
        if request.method == 'GET':
            return redirect(url_for('nis2.bsi_registration_landing'))

        data = request.get_json(silent=True) or request.form
        sector = data.get('sector', '')
        is_dns_tld = data.get('is_dns_tld') in (True, 'true', '1', 'on')

        # Form sends string values from select dropdowns
        emp_str = data.get('employees', 'under50')
        rev_str = data.get('revenue', 'under10')
        employees = _parse_employees(emp_str)
        revenue = _parse_revenue(rev_str)

        result = _determine_betroffenheit(sector, employees, revenue, is_dns_tld)

        if request.is_json:
            return jsonify(result)

        return render_template(
            'nis2/bsi_registration/check_result.html',
            result=result,
            sectors=NIS2_SECTORS,
        )

    # ── Wizard ────────────────────────────────────────────────────────────

    @bp.route('/bsi-registration/wizard/start', methods=['POST'])
    @login_required
    def bsi_wizard_start():
        """Create a new registration and redirect to step 1."""
        # Reuse existing incomplete registration or create new
        reg = BSIRegistration.query.filter_by(
            user_id=current_user.id, is_complete=False
        ).order_by(BSIRegistration.created_at.desc()).first()

        if not reg:
            reg = BSIRegistration(user_id=current_user.id)
            db.session.add(reg)
            db.session.commit()

        return redirect(url_for('nis2.bsi_wizard_step', reg_id=reg.id, step=1))

    @bp.route('/bsi-registration/wizard/<int:reg_id>/step/<int:step>',
              methods=['GET', 'POST'])
    @login_required
    def bsi_wizard_step(reg_id, step):
        """Handle individual wizard steps 1–5."""
        reg = BSIRegistration.query.filter_by(
            id=reg_id, user_id=current_user.id
        ).first_or_404()

        if step < 1 or step > 5:
            return redirect(url_for('nis2.bsi_wizard_step', reg_id=reg_id, step=1))

        if request.method == 'POST':
            error = _save_wizard_step(reg, step, request.form)
            if error:
                flash(error, 'danger')
                return redirect(url_for('nis2.bsi_wizard_step', reg_id=reg_id, step=step))

            if step < 5:
                reg.wizard_step = max(reg.wizard_step, step + 1)
                db.session.commit()
                return redirect(url_for('nis2.bsi_wizard_step', reg_id=reg_id, step=step + 1))
            else:
                # Step 5 = finish
                reg.is_complete = True
                reg.wizard_step = 5
                db.session.commit()
                flash('Registrierungsdaten erfolgreich gespeichert!', 'success')
                return redirect(url_for('nis2.bsi_export', reg_id=reg_id))

        return render_template(
            f'nis2/bsi_registration/wizard_step{step}.html',
            reg=reg,
            step=step,
            sectors=NIS2_SECTORS,
            legal_forms=LEGAL_FORMS,
            contacts=reg.get_contacts(),
            technical=reg.get_technical(),
        )

    @bp.route('/bsi-registration/<int:reg_id>/export')
    @login_required
    def bsi_export(reg_id):
        reg = BSIRegistration.query.filter_by(
            id=reg_id, user_id=current_user.id
        ).first_or_404()
        return render_template(
            'nis2/bsi_registration/export.html',
            reg=reg,
            contacts=reg.get_contacts(),
            technical=reg.get_technical(),
        )

    @bp.route('/bsi-registration/<int:reg_id>/export/json')
    @login_required
    def bsi_export_json(reg_id):
        reg = BSIRegistration.query.filter_by(
            id=reg_id, user_id=current_user.id
        ).first_or_404()
        reg.exported_at = datetime.utcnow()
        db.session.commit()

        export_data = {
            'export_format': 'NIS2-BSI-Registrierung-v1',
            'exported_at': datetime.utcnow().isoformat(),
            'company': {
                'name': reg.company_name,
                'legal_form': reg.legal_form,
                'hrb_number': reg.hrb_number,
                'registry_court': reg.registry_court,
                'vat_id': reg.vat_id,
                'address': {
                    'street': reg.street,
                    'postal_code': reg.postal_code,
                    'city': reg.city,
                },
                'employees': reg.employee_count,
                'annual_revenue_eur': reg.annual_revenue_eur,
            },
            'nis2_classification': {
                'sector': reg.sector,
                'subsector': reg.subsector,
                'entity_type': reg.entity_type,
                'entity_type_label': reg.entity_type_label,
            },
            'contacts': reg.get_contacts(),
            'technical': reg.get_technical(),
        }

        from flask import make_response
        resp = make_response(json.dumps(export_data, ensure_ascii=False, indent=2))
        resp.headers['Content-Type'] = 'application/json; charset=utf-8'
        resp.headers['Content-Disposition'] = \
            f'attachment; filename="BSI-Registrierung-{reg.company_name}.json"'
        return resp

    @bp.route('/bsi-registration/<int:reg_id>/delete', methods=['POST'])
    @login_required
    def bsi_delete(reg_id):
        reg = BSIRegistration.query.filter_by(
            id=reg_id, user_id=current_user.id
        ).first_or_404()
        db.session.delete(reg)
        db.session.commit()
        flash('Registrierung gelöscht.', 'info')
        return redirect(url_for('nis2.bsi_registration_landing'))


# ─────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────

def _parse_employees(value: str) -> int:
    """Convert select dropdown string value to numeric employees count."""
    mapping = {'under50': 10, '50to249': 100, '250plus': 500}
    return mapping.get(str(value), _safe_int(value, 0))


def _parse_revenue(value: str) -> int:
    """Convert select dropdown string value to numeric revenue (EUR)."""
    mapping = {'under10': 5_000_000, '10to50': 20_000_000, 'over50': 100_000_000}
    return mapping.get(str(value), _safe_int(value, 0))


def _safe_int(value, default=0):
    try:
        return int(str(value).replace('.', '').replace(',', '').strip())
    except (ValueError, TypeError):
        return default


def _sector_group(sector: str) -> str:
    """Map specific subsector key to its parent NIS2 sector group."""
    if sector.startswith('energie_') or sector == 'energie':
        return 'energie'
    if sector.startswith('transport_') or sector == 'transport':
        return 'transport'
    if sector.startswith('gesundheit_') or sector == 'gesundheit':
        return 'gesundheit'
    if sector.startswith('digital_') or sector == 'digitale_infrastruktur':
        return 'digitale_infrastruktur'
    if sector.startswith('verarbeitendes_') or sector == 'verarbeitendes_gewerbe':
        return 'verarbeitendes_gewerbe'
    if sector.startswith('digitale_dienste') or sector == 'digitale_dienste':
        return 'digitale_dienste'
    return sector


def _determine_betroffenheit(sector, employees, revenue, is_dns_tld):
    """
    Returns entity classification per NIS2UmsuCG §28 BSIG.
    Uses _sector_group() to map subsector keys to parent groups.
    """
    if not sector:
        return {
            'affected': False,
            'entity_type': 'nicht_betroffen',
            'reason': 'Kein Sektor angegeben.',
        }

    group = _sector_group(sector)

    # Auto-classification regardless of size (§28 Abs. 3 BSIG)
    AUTO_CRITICAL = {'digital_dns', 'digital_vertrauen', 'digital_netz'}
    if is_dns_tld or sector in AUTO_CRITICAL or group == 'digitale_infrastruktur':
        return {
            'affected': True,
            'entity_type': 'besonders_wichtig',
            'reason': (
                'DNS-Anbieter, TLD-Registrare, Internet-Austauschpunkte und qualifizierte '
                'Vertrauensdienstanbieter sind unabhängig von Größe und Umsatz betroffen '
                '(§28 Abs. 3 BSIG).'
            ),
            'threshold_hit': 'Automatisch (Sonderregel §28 Abs. 3)',
            'fines': 'bis €10 Mio. oder 2% des weltweiten Jahresumsatzes',
        }

    HIGHLY_CRITICAL = {
        'energie', 'transport', 'bankwesen', 'finanzmarkt', 'gesundheit',
        'trinkwasser', 'abwasser', 'digitale_infrastruktur', 'ikt_management',
        'oeffentliche_verwaltung', 'weltraum',
    }
    IMPORTANT = {
        'post', 'abfallwirtschaft', 'chemie', 'lebensmittel',
        'verarbeitendes_gewerbe', 'digitale_dienste', 'forschung',
    }

    meets_250 = employees >= 250 or revenue >= 50_000_000
    meets_50 = employees >= 50 or revenue >= 10_000_000

    if group in HIGHLY_CRITICAL:
        if not meets_50:
            return {
                'affected': False,
                'entity_type': 'nicht_betroffen',
                'reason': (
                    f'Ihr Unternehmen liegt unterhalb der NIS2-Schwellenwerte '
                    f'(≥50 MA oder ≥€10 Mio.). '
                    'Beachten Sie: Kunden können vertraglich NIS2-Compliance fordern.'
                ),
            }
        entity_type = 'besonders_wichtig' if meets_250 else 'wichtig'
        fines = ('bis €10 Mio. oder 2% Umsatz' if entity_type == 'besonders_wichtig'
                 else 'bis €7 Mio. oder 1,4% Umsatz')
        return {
            'affected': True,
            'entity_type': entity_type,
            'reason': (
                f'Ihr Unternehmen im Sektor „{sector}" fällt unter '
                f'Anlage 1 BSIG und ist als „{entity_type.replace("_", " ")} Einrichtung" eingestuft.'
            ),
            'threshold_hit': f'{employees} MA / €{revenue:,} Jahresumsatz',
            'fines': fines,
            'registration_deadline': '17. Januar 2025 (abgelaufen — sofort registrieren!)',
        }

    if group in IMPORTANT:
        if not meets_50:
            return {
                'affected': False,
                'entity_type': 'nicht_betroffen',
                'reason': (
                    'Ihr Unternehmen liegt unterhalb der Schwellenwerte für Anlage-2-Sektoren '
                    '(≥50 MA oder ≥€10 Mio.). Dennoch kann vertragliche Compliance gefordert werden.'
                ),
            }
        return {
            'affected': True,
            'entity_type': 'wichtig',
            'reason': (
                f'Ihr Unternehmen im Sektor „{sector}" fällt unter '
                'Anlage 2 BSIG und ist als „wichtige Einrichtung" eingestuft.'
            ),
            'threshold_hit': f'{employees} MA / €{revenue:,} Jahresumsatz',
            'fines': 'bis €7 Mio. oder 1,4% des weltweiten Jahresumsatzes',
            'registration_deadline': '17. Januar 2025 (abgelaufen — sofort registrieren!)',
        }

    return {
        'affected': False,
        'entity_type': 'nicht_betroffen',
        'reason': 'Ihr Sektor ist keiner der 18 NIS2-relevanten Sektoren zugeordnet.',
    }


def _save_wizard_step(reg: BSIRegistration, step: int, form) -> str:
    """
    Saves form data for the given wizard step.
    Returns error message string or None on success.
    """
    try:
        if step == 1:
            reg.company_name = form.get('company_name', '').strip()
            if not reg.company_name:
                return 'Firmenname ist erforderlich.'
            reg.legal_form = form.get('legal_form', '').strip()
            reg.hrb_number = form.get('hrb_number', '').strip()
            reg.registry_court = form.get('registry_court', '').strip()
            reg.vat_id = form.get('vat_id', '').strip()
            reg.street = form.get('street', '').strip()
            reg.postal_code = form.get('postal_code', '').strip()
            reg.city = form.get('city', '').strip()
            reg.employee_count = _safe_int(form.get('employee_count'))
            reg.annual_revenue_eur = _safe_int(form.get('annual_revenue_eur'))

        elif step == 2:
            sector = form.get('sector', '').strip()
            if not sector:
                return 'Bitte wählen Sie einen Sektor.'
            reg.sector = sector
            reg.subsector = form.get('subsector', '').strip()
            is_dns = form.get('is_dns_tld') in ('on', '1', 'true')
            result = _determine_betroffenheit(
                sector,
                reg.employee_count or 0,
                reg.annual_revenue_eur or 0,
                is_dns,
            )
            reg.entity_type = result['entity_type']
            reg.is_affected = result['affected']

        elif step == 3:
            contacts = {
                'gf': {
                    'name': form.get('gf_name', '').strip(),
                    'email': form.get('gf_email', '').strip(),
                    'phone': form.get('gf_phone', '').strip(),
                },
                'it_security': {
                    'name': form.get('it_name', '').strip(),
                    'email': form.get('it_email', '').strip(),
                    'phone': form.get('it_phone', '').strip(),
                },
                'meldestelle': {
                    'name': form.get('ms_name', '').strip(),
                    'email': form.get('ms_email', '').strip(),
                    'phone': form.get('ms_phone', '').strip(),
                    'available_24_7': form.get('ms_24h') in ('on', '1', 'true'),
                },
            }
            reg.contacts_json = json.dumps(contacts, ensure_ascii=False)

        elif step == 4:
            ip_ranges_raw = form.get('ip_ranges', '')
            domains_raw = form.get('domains', '')
            cloud_raw = form.get('cloud_providers', '')

            technical = {
                'ip_ranges': [r.strip() for r in ip_ranges_raw.splitlines() if r.strip()],
                'domains': [d.strip() for d in domains_raw.splitlines() if d.strip()],
                'cloud_providers': [c.strip() for c in cloud_raw.splitlines() if c.strip()],
                'it_services': form.get('it_services', '').strip(),
                'employee_count_it': _safe_int(form.get('employee_count_it')),
            }
            reg.technical_json = json.dumps(technical, ensure_ascii=False)

        elif step == 5:
            # Step 5 is summary/confirmation — no data to save, just mark complete
            pass

        db.session.commit()
        return None

    except Exception as e:
        db.session.rollback()
        return f'Fehler beim Speichern: {str(e)}'
