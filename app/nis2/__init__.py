"""
NIS2 Compliance Platform — Main Blueprint

Modular compliance suite for NIS2UmsuCG (since 6 Dec 2025, Germany).
Covers §30 Abs. 2 BSIG (10 measures) + §32/§33/§38/§39 obligations.

Sub-modules:
  - bsi_registration      : BSI-Registrierungs-Assistent (§33 BSIG)
  - continuous_monitoring : Automated security monitoring (§30 Nr. 5/6)
  - isms_docs             : ISMS Document Generator (§30 Nr. 1-10)
  - incident_response     : BSI Meldungen + IRP (§30 Nr. 2, §32)
  - supply_chain          : Supply Chain Security (§30 Nr. 4)
  - executive_training    : GF-Schulung (§38 BSIG)
  - awareness             : Mitarbeiter-Schulung (§30 Nr. 7)
"""

from flask import Blueprint

nis2_bp = Blueprint(
    'nis2',
    __name__,
    url_prefix='/nis2',
    template_folder='../../templates/nis2',
)

# ── Access control: Professional plan only ────────────────────────────────────
from flask import redirect, url_for, flash, render_template
from flask_login import current_user


@nis2_bp.before_request
def require_professional_plan():
    """Block NIS2 access for non-professional users (except public ack pages)."""
    from flask import request as _req
    from flask_login import current_user as cu

    # Public routes — acknowledgment links sent to team members (no login needed)
    if _req.endpoint and 'training_ack' in _req.endpoint:
        return None

    # Must be authenticated
    if not cu.is_authenticated:
        return redirect(url_for('auth.login'))

    # Admins always have access
    if cu.is_admin:
        return None

    # Check plan
    plan = cu.subscription_plan  # 'free', 'basic', 'professional'
    if plan != 'professional':
        flash(
            'Das NIS2 Compliance-Modul ist nur im Professional-Tarif verfügbar. '
            'Bitte upgraden Sie Ihr Abonnement.',
            'warning'
        )
        return redirect(url_for('payments.pricing'))


# Register sub-module routes
from .dashboard import register_dashboard_routes
register_dashboard_routes(nis2_bp)

from .bsi_registration.routes import register_bsi_routes
register_bsi_routes(nis2_bp)

from .continuous_monitoring.routes import register_monitoring_routes
register_monitoring_routes(nis2_bp)

from .isms_docs.routes import register_isms_routes
register_isms_routes(nis2_bp)

from .incident_response.routes import register_incident_routes
register_incident_routes(nis2_bp)

from .supply_chain.routes import register_supply_chain_routes
register_supply_chain_routes(nis2_bp)

from .training.routes import register_training_routes
register_training_routes(nis2_bp)

from .site_audit.routes import register_site_audit_routes
register_site_audit_routes(nis2_bp)
