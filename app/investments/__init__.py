from flask import Blueprint

bp = Blueprint('investments', __name__)

from app.investments import routes
