import os
import logging
from datetime import timedelta
from flask import Flask, jsonify, redirect, url_for, request, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_required, current_user
from sqlalchemy.orm import DeclarativeBase
import pytz
from flask_wtf.csrf import CSRFProtect  # Add CSRF protection

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()
csrf = CSRFProtect()  # Create CSRF protection instance

# create the app
app = Flask(__name__)

# setup a secret key, required by sessions
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or "a secret key"
# configure the database, relative to the app instance folder
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Set session configuration - Enhanced for better security and state management
app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)
app.config['SESSION_REFRESH_EACH_REQUEST'] = True
app.config['REMEMBER_COOKIE_DURATION'] = timedelta(days=7)
app.config['REMEMBER_COOKIE_HTTPONLY'] = True
app.config['REMEMBER_COOKIE_SECURE'] = False  # Set to True in production
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax' # Added for CSRF protection


# Set default timezone
app.config['TIMEZONE'] = pytz.timezone('UTC')  # Default to UTC

# initialize the app with the extension, flask-sqlalchemy >= 3.0.x
db.init_app(app)
login_manager.init_app(app)
csrf.init_app(app)  # Initialize CSRF protection
login_manager.login_view = 'login'  # Set to main route
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    from models import User
    logger.debug(f"Loading user with ID: {user_id}")
    logger.debug(f"Current session data: {session}")
    logger.debug(f"Request cookies: {request.cookies}")
    user = User.query.get(int(user_id))
    logger.debug(f"User loaded: {user.username if user else None}")
    return user

@login_manager.unauthorized_handler
def unauthorized():
    logger.debug(f"Unauthorized access to path: {request.path}")
    logger.debug(f"Current user authenticated: {current_user.is_authenticated}")
    logger.debug(f"Session data: {session}")
    logger.debug(f"Request cookies: {request.cookies}")

    if request.path.startswith('/api/'):
        return jsonify({'error': 'Authentication required'}), 401
    return redirect(url_for('login', next=request.url))

with app.app_context():
    # Make sure to import the models here or their tables won't be created
    import models  # noqa: F401

    db.create_all()

# Import and register blueprints
from routes import *
from ticket_routes import tickets  # Import the tickets blueprint
app.register_blueprint(tickets)  # Register the tickets blueprint

# API Routes -  Added CSRF token verification
@app.route('/api/active_users', methods=['GET']) #specified methods for better security
@login_required
def api_active_users():
    """Get list of active users for the application"""
    logger.debug(f"Active users API called by user: {current_user.username if current_user.is_authenticated else 'Not authenticated'}")
    logger.debug(f"Session data: {session}")
    logger.debug(f"Request cookies: {request.cookies}")

    # CSRF Token Validation
    csrf_token = request.form.get('csrf_token') or request.args.get('csrf_token') or request.headers.get('X-CSRF-Token')

    if not csrf_token or not csrf.validate_token(csrf_token):
        return jsonify({'error': 'Invalid CSRF token'}), 400


    if not current_user.is_authenticated:
        logger.warning("Unauthenticated access to active_users API")
        return jsonify({'error': 'Authentication required'}), 401

    try:
        users = User.query.all()
        logger.debug(f"Found {len(users)} active users")
        return jsonify([{
            'id': user.id,
            'username': user.username,
            'color': user.color
        } for user in users])
    except Exception as e:
        logger.error(f"Error in active_users API: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)