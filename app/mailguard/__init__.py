from flask import Blueprint

mailguard_bp = Blueprint('mailguard', __name__, url_prefix='/mailguard')

from . import views, oauth