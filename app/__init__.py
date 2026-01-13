from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from config import Config
import os

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Create upload folder if it doesn't exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    # Register blueprints
    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from app.main import bp as main_bp
    app.register_blueprint(main_bp)

    from app.expenses import bp as expenses_bp
    app.register_blueprint(expenses_bp, url_prefix='/expenses')

    from app.investments import bp as investments_bp
    app.register_blueprint(investments_bp, url_prefix='/investments')

    from app.chat import bp as chat_bp
    app.register_blueprint(chat_bp, url_prefix='/chat')

    # Add context processor for currency symbols
    @app.context_processor
    def utility_processor():
        def get_currency_symbol(currency_code=None):
            from flask_login import current_user
            if currency_code is None and current_user.is_authenticated:
                currency_code = current_user.currency
            
            currency_symbols = {
                'USD': '$',
                'EUR': '€',
                'GBP': '£',
                'JPY': '¥',
                'CAD': 'CA$',
                'AUD': 'A$',
                'INR': '₹'
            }
            return currency_symbols.get(currency_code, currency_code or '$')
        
        return dict(get_currency_symbol=get_currency_symbol)

    return app

from app import models