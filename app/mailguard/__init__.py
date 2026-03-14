from flask import Blueprint

mailguard_bp = Blueprint(
    'mailguard', 
    __name__, 
    url_prefix='/mailguard',
    template_folder='templates'
)

from . import views, oauth