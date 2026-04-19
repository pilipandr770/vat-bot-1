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
