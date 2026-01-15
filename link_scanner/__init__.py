"""Link Scanner module for URL threat detection."""
from flask import Blueprint

link_scanner = Blueprint('link_scanner', __name__, template_folder='templates')

from . import routes  # noqa: E402, F401
