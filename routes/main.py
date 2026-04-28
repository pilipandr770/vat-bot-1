"""
Main application routes: landing, dashboard, verification workflow.

Extracted from application.py to keep the factory function lean.
Endpoint names are preserved so all existing url_for() calls work unchanged.
"""
from __future__ import annotations

import logging
import traceback

from flask import (
    current_app,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
    flash,
)
from flask_login import current_user, login_required

from crm.models import db, Company, Counterparty, VerificationCheck
from services.vies import VIESService
from services.sanctions import SanctionsService
from crm.save_results import ResultsSaver
from services.business_registry import BusinessRegistryManager
from services.rate_limiter import rate_limiter

logger = logging.getLogger(__name__)

# ── Module-level service singletons (stateless — safe outside app context) ──
_vies_service = VIESService()
_sanctions_service = SanctionsService()
_results_saver = ResultsSaver(db)
_registry_manager = BusinessRegistryManager()


# ── Route handlers ────────────────────────────────────────────────────────────

def landing():
    """Landing page for non-authenticated users."""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    try:
        from crm.models import BlogPost
        latest_blog_posts = (
            BlogPost.query
            .filter_by(is_published=True)
            .order_by(BlogPost.published_at.desc())
            .limit(3)
            .all()
        )
    except Exception:
        latest_blog_posts = []
    return render_template('landing.html', latest_blog_posts=latest_blog_posts)


@login_required
def dashboard():
    """Main verification interface for authenticated users."""
    subscription = current_user.active_subscription
    total_checks = VerificationCheck.query.filter_by(user_id=current_user.id).count()
    monthly_checks = current_user.get_monthly_verification_count()
    recent_checks = (
        VerificationCheck.query
        .filter_by(user_id=current_user.id)
        .order_by(VerificationCheck.check_date.desc())
        .limit(5)
        .all()
    )
    from crm.models import Alert
    recent_alerts = (
        Alert.query.join(VerificationCheck)
        .filter(VerificationCheck.user_id == current_user.id)
        .order_by(Alert.created_at.desc())
        .limit(5)
        .all()
    )
    registry_catalog = _registry_manager.get_catalog_grouped()
    return render_template(
        'index.html',
        subscription=subscription,
        total_checks=total_checks,
        monthly_checks=monthly_checks,
        recent_checks=recent_checks,
        recent_alerts=recent_alerts,
        registry_catalog=registry_catalog,
    )


def set_language(lang: str):
    """Set user language preference and redirect back."""
    if lang in ('de', 'en', 'uk'):
        session['language'] = lang
    return redirect(request.referrer or url_for('dashboard'))


def test_translations():
    """Debug route: inspect active locale. Admin-only in production."""
    locale = session.get('language', request.accept_languages.best_match(['de', 'en', 'uk'], default='de'))
    results = [
        f"Session language: {session.get('language', 'not set')}",
        f"Active locale: {locale}",
        f"Supported locales: {current_app.config.get('BABEL_SUPPORTED_LOCALES')}",
        f"Translation dir: {current_app.config.get('BABEL_TRANSLATION_DIRECTORIES')}",
    ]
    items = "".join(f"<li>{r}</li>" for r in results)
    return (
        f"<h1>Translation Debug</h1><ul>{items}</ul>"
        f"<p><a href='/set-language/de'>DE</a> | "
        f"<a href='/set-language/en'>EN</a> | "
        f"<a href='/set-language/uk'>UA</a></p>"
    )


@login_required
def pentesting_scanner():
    """Website security scanner — PRO/ENTERPRISE or admin only."""
    sub = current_user.active_subscription
    if not current_user.is_admin and (not sub or sub.plan not in ('professional', 'enterprise')):
        flash('Der Website Security Scanner ist ab dem Professional-Plan verfügbar.', 'warning')
        return redirect(url_for('payments.pricing'))
    return render_template('pentesting/scanner.html')


@login_required
def verify_counterparty():
    """Process verification request."""
    # Rate limiting
    identifier = f"user_{current_user.id}"
    allowed_min, info_min = rate_limiter.is_allowed(identifier, 30, 60)
    if not allowed_min:
        logger.warning("Rate limit exceeded for user %s", current_user.id)
        return jsonify({
            'success': False,
            'error': 'Zu viele Anfragen. Bitte versuchen Sie es in einigen Sekunden erneut.',
            'rate_limit': True,
            'retry_after': info_min['retry_after'],
        }), 429

    # Quota check
    if not current_user.can_perform_verification():
        sub = current_user.active_subscription
        if not sub:
            current_usage = current_user.get_monthly_verification_count()
            limit, plan_name = 5, 'Free'
        else:
            current_usage = sub.api_calls_used
            limit = sub.api_calls_limit if sub.api_calls_limit != -1 else 'unlimited'
            plan_name = sub.plan
        return jsonify({
            'success': False,
            'error': f'Sie haben Ihr Prüfungslimit erreicht ({current_usage}/{limit}). Bitte upgraden Sie Ihren Plan.',
            'current_plan': plan_name,
            'current_usage': current_usage,
            'limit': limit,
            'upgrade_required': True,
        }), 403

    try:
        if request.is_json:
            data = request.get_json()
            company_data = {
                'vat_number': data.get('company_vat'),
                'company_name': data.get('company_name'),
                'legal_address': data.get('company_address'),
                'email': data.get('company_email'),
                'phone': data.get('company_phone'),
            }
            counterparty_data = {
                'vat_number': data.get('counterparty_vat'),
                'company_name': data.get('counterparty_name'),
                'address': data.get('counterparty_address'),
                'email': data.get('counterparty_email'),
                'domain': data.get('counterparty_domain'),
                'contact_person': data.get('counterparty_contact'),
                'country': data.get('counterparty_country'),
            }
        else:
            company_data = {
                'vat_number': request.form.get('company_vat', ''),
                'company_name': request.form.get('company_name', ''),
                'legal_address': request.form.get('company_address', ''),
                'email': request.form.get('company_email', ''),
                'phone': request.form.get('company_phone', ''),
            }
            counterparty_data = {
                'vat_number': request.form.get('counterparty_vat', ''),
                'company_name': request.form.get('counterparty_name', ''),
                'address': request.form.get('counterparty_address', ''),
                'email': request.form.get('counterparty_email', ''),
                'domain': request.form.get('counterparty_domain', ''),
                'contact_person': request.form.get('counterparty_contact', ''),
                'country': request.form.get('counterparty_country', ''),
            }

        if not company_data.get('vat_number') or not company_data.get('company_name'):
            return jsonify({'success': False, 'error': 'Company VAT and name are required'}), 400

        if not counterparty_data.get('company_name') or not counterparty_data.get('country'):
            return jsonify({'success': False, 'error': 'Counterparty name and country are required'}), 400

        company = _get_or_create_company(company_data, current_user.id)
        counterparty = _get_or_create_counterparty(counterparty_data, current_user.id)

        verification_check = VerificationCheck(
            company_id=company.id,
            counterparty_id=counterparty.id,
            user_id=current_user.id,
            overall_status='pending',
        )
        db.session.add(verification_check)
        db.session.commit()

        verification_results = _run_verification_services(counterparty_data)
        current_user.increment_api_usage()

        overall_status, confidence = _results_saver.save_verification_results(
            verification_check.id, verification_results
        )
        verification_check.overall_status = overall_status
        verification_check.confidence_score = confidence
        db.session.commit()

        return jsonify({
            'success': True,
            'check_id': verification_check.id,
            'overall_status': overall_status,
            'confidence_score': confidence,
            'results': verification_results,
        })

    except Exception as exc:
        logger.exception("Error in verify_counterparty: %s", exc)
        db.session.rollback()
        error_msg = (
            'Fehler beim VIES-Service. Bitte versuchen Sie es in wenigen Sekunden erneut.'
            if 'vies' in str(exc).lower()
            else 'Ein unerwarteter Fehler ist aufgetreten. Bitte versuchen Sie es später erneut.'
        )
        return jsonify({
            'success': False,
            'error': error_msg,
            'details': str(exc) if current_app.debug else None,
        }), 500


@login_required
def verification_history():
    """Verification history list."""
    page = request.args.get('page', 1, type=int)
    checks = (
        VerificationCheck.query
        .filter_by(user_id=current_user.id)
        .order_by(VerificationCheck.check_date.desc())
        .paginate(page=page, per_page=20, error_out=False)
    )
    return render_template('history.html', checks=checks)


@login_required
def check_details(check_id: int):
    """Detailed check results page."""
    check = VerificationCheck.query.get_or_404(check_id)
    if check.user_id != current_user.id and not current_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403
    return render_template('check_details.html', check=check)


@login_required
def api_check_results(check_id: int):
    """JSON API — check results for a given verification."""
    check = VerificationCheck.query.get_or_404(check_id)
    if check.user_id != current_user.id and not current_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403
    results = {
        r.service_name: {
            'status': r.status,
            'confidence_score': r.confidence_score,
            'data': r.data,
            'error_message': r.error_message,
            'response_time_ms': r.response_time_ms,
            'created_at': r.created_at.isoformat(),
        }
        for r in check.check_results
    }
    return jsonify({
        'check_id': check.id,
        'overall_status': check.overall_status,
        'confidence_score': check.confidence_score,
        'results': results,
    })


def api_vat_lookup():
    """VAT/domain/email enrichment — form auto-fill via EnrichmentOrchestrator."""
    if not current_user.is_authenticated:
        return jsonify({
            'success': False,
            'error': 'Bitte melden Sie sich an',
            'redirect': url_for('auth.login'),
        }), 401

    payload = request.get_json(silent=True) or {}
    vat_number = payload.get('vat_number', '').strip()
    country_code = payload.get('country_code')
    company_name_hint = payload.get('company_name')
    email = payload.get('email', '').strip()
    domain = payload.get('domain', '').strip()

    if not any([vat_number, email, domain, company_name_hint]):
        return jsonify({
            'success': False,
            'error': 'Bitte geben Sie eine VAT-Nummer, E-Mail, Domain oder Firmennamen ein.',
        }), 400

    try:
        from services.enrichment_flow import EnrichmentOrchestrator
        result = EnrichmentOrchestrator().enrich(
            vat_number=vat_number or None,
            email=email or None,
            domain=domain or None,
            company_name=company_name_hint or None,
            country_code_hint=country_code or None,
        )
        current_app.logger.info(
            "User %s enrichment: VAT=%s, sources=%s",
            current_user.id, vat_number, list(result.get('services', {}).keys()),
        )
        return jsonify(result), 200
    except ValueError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400
    except Exception as exc:
        current_app.logger.exception('Enrichment failed: %s', exc)
        return jsonify({'success': False, 'error': 'Interner Fehler bei der Datensuche'}), 500


def robots_txt():
    """Serve static robots.txt."""
    return current_app.send_static_file('robots.txt')


def ads_txt():
    """Serve static ads.txt."""
    return current_app.send_static_file('ads.txt')


# ── Private helpers ───────────────────────────────────────────────────────────

def _get_or_create_company(company_data: dict, user_id: int) -> Company:
    company = Company.query.filter_by(
        vat_number=company_data['vat_number'],
        user_id=user_id,
    ).first()
    if not company:
        company = Company(**{**company_data, 'user_id': user_id})
        db.session.add(company)
        db.session.commit()
    return company


def _get_or_create_counterparty(counterparty_data: dict, user_id: int) -> Counterparty:
    counterparty = None
    if counterparty_data.get('vat_number'):
        counterparty = Counterparty.query.filter_by(
            vat_number=counterparty_data['vat_number'],
            user_id=user_id,
        ).first()
    if not counterparty:
        counterparty = Counterparty.query.filter_by(
            company_name=counterparty_data['company_name'],
            country=counterparty_data['country'],
            user_id=user_id,
        ).first()
    if not counterparty:
        counterparty = Counterparty(**{**counterparty_data, 'user_id': user_id})
        db.session.add(counterparty)
        db.session.commit()
    return counterparty


def _run_verification_services(counterparty_data: dict) -> dict:
    results: dict = {}
    if counterparty_data.get('vat_number'):
        results['vies'] = _vies_service.validate_vat(
            counterparty_data['country'],
            counterparty_data['vat_number'],
        )
    registry_result = _registry_manager.lookup(
        counterparty_data['country'],
        counterparty_data['company_name'],
        vat_number=counterparty_data.get('vat_number'),
    )
    if registry_result:
        key = registry_result.get('source', f"registry_{counterparty_data['country'].lower()}")
        results[key] = registry_result
    results['sanctions'] = _sanctions_service.check_sanctions(
        counterparty_data['company_name'],
        counterparty_data.get('contact_person', ''),
    )
    return results


# ── Registration helper ───────────────────────────────────────────────────────

def register_routes(app):
    """Register all main routes on the Flask app, preserving original endpoint names."""
    rules = [
        ('/',                                 'landing',              landing,              ['GET']),
        ('/dashboard',                        'dashboard',            dashboard,            ['GET']),
        ('/set-language/<lang>',              'set_language',         set_language,         ['GET']),
        ('/test-translations',                'test_translations',    test_translations,    ['GET']),
        ('/pentesting-scanner',               'pentesting_scanner',   pentesting_scanner,   ['GET']),
        ('/verify',                           'verify_counterparty',  verify_counterparty,  ['POST']),
        ('/history',                          'verification_history', verification_history, ['GET']),
        ('/check/<int:check_id>',             'check_details',        check_details,        ['GET']),
        ('/api/check/<int:check_id>/results', 'api_check_results',    api_check_results,    ['GET']),
        ('/api/vat-lookup',                   'api_vat_lookup',       api_vat_lookup,       ['POST']),
        ('/robots.txt',                       'robots',               robots_txt,           ['GET']),
        ('/ads.txt',                          'ads_txt',              ads_txt,              ['GET']),
    ]
    for rule, endpoint, view_func, methods in rules:
        app.add_url_rule(rule, endpoint=endpoint, view_func=view_func, methods=methods)
