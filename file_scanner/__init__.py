from flask import Blueprint

file_scanner = Blueprint('file_scanner', __name__)

from . import routes