import os
import logging
import re
from datetime import timedelta
from flask import Flask, jsonify, redirect, url_for, request, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_required, current_user
from sqlalchemy.orm import DeclarativeBase
import pytz
from flask_wtf.csrf import CSRFProtect
from markupsafe import Markup

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()
csrf = CSRFProtect()

# Create the app
app = Flask(__name__)

# Custom Jinja2 filters
@app.template_filter('nl2br')
def nl2br_filter(s):
    """Convert newlines to HTML line breaks"""
    if not s:
        return ""
    return Markup(s.replace('\n', '<br>\n'))

# Function to detect mobile devices
def is_mobile_device():
    """Check if the user is using a mobile device"""
    from flask import request
    import re
    
    user_agent = request.headers.get('User-Agent', '').lower()
    # Pattern to match common mobile devices
    pattern = r"android|webos|iphone|ipad|ipod|blackberry|iemobile|opera mini|mobile"
    
    # Debug the detection logic
    app.logger.debug(f"User-Agent: {user_agent}")
    is_mobile = bool(re.search(pattern, user_agent))
    app.logger.debug(f"is_mobile_device detection result: {is_mobile}")
    
    return is_mobile

# Configuration
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or "a secret key"
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
# Configuration for URL generation outside of request context (used in emails)
# We're NOT setting SERVER_NAME directly as it breaks route matching in development
# Instead, we'll use these values in email_utils.py
app.config["APPLICATION_ROOT"] = "/"
app.config["PREFERRED_URL_SCHEME"] = "http"
app.config["EMAIL_DOMAIN"] = os.environ.get("EMAIL_DOMAIN", "localhost:5000")

# Set session configuration
app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_PATH'] = '/'

# Set default timezone
app.config['TIMEZONE'] = pytz.timezone('UTC')

# Initialize extensions
db.init_app(app)
login_manager.init_app(app)
csrf.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    from models import User
    logger.debug(f"Loading user with ID: {user_id}")
    logger.debug(f"Current session data: {session}")
    logger.debug(f"Request cookies: {request.cookies}")
    logger.debug(f"Request path: {request.path}")
    logger.debug(f"Request headers: {request.headers}")

    try:
        user = User.query.get(int(user_id))
        if user:
            logger.debug(f"Successfully loaded user: {user.username}")
            logger.debug(f"User data: id={user.id}, email={user.email}, is_admin={getattr(user, 'is_admin', False)}")
        else:
            logger.warning(f"No user found with ID: {user_id}")
        return user
    except Exception as e:
        logger.error(f"Error loading user {user_id}: {str(e)}")
        return None

# Custom unauthorized handler
@login_manager.unauthorized_handler
def unauthorized():
    logger.debug(f"Unauthorized access to path: {request.path}")
    logger.debug(f"Current user authenticated: {current_user.is_authenticated}")
    logger.debug(f"Session data: {session}")
    logger.debug(f"Request cookies: {request.cookies}")

    if request.path.startswith('/api/'):
        return jsonify({'error': 'Authentication required'}), 401
    return redirect(url_for('login', next=request.url))

# Favicon and Apple Touch Icon routes
@app.route('/favicon.ico')
def favicon():
    return redirect(url_for('static', filename='images/plex_logo_small.png'))

@app.route('/apple-touch-icon.png')
@app.route('/apple-touch-icon-precomposed.png')
@app.route('/apple-touch-icon-120x120.png')
@app.route('/apple-touch-icon-120x120-precomposed.png')
def apple_touch_icon():
    return redirect(url_for('static', filename='images/plex_logo_small.png'))

with app.app_context():
    import models
    db.create_all()

# Import and register blueprints
from routes import *
from ticket_routes import tickets, get_active_sidebar_tickets
# Register health check for container healthchecks
from health import health_bp
app.register_blueprint(tickets)
app.register_blueprint(health_bp)

# Register the get_active_sidebar_tickets function with the app context
@app.context_processor
def inject_active_sidebar_tickets():
    return dict(get_active_sidebar_tickets=get_active_sidebar_tickets)

@app.context_processor
def inject_now():
    from datetime import datetime
    return {'now': datetime.now()}

@app.context_processor
def inject_mobile_detection():
    """Inject mobile device detection function into templates"""
    return {'is_mobile': is_mobile_device}

# API Routes 
# Note: API routes are defined in routes.py

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)