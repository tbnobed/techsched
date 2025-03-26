import os
import logging
from flask import Flask, jsonify, redirect, url_for, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_required
from sqlalchemy.orm import DeclarativeBase
import pytz
from flask_wtf.csrf import CSRFProtect  # Add CSRF protection

# Configure logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()
csrf = CSRFProtect()  # Create CSRF protection instance

# Create the app
app = Flask(__name__)

# Configuration
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or "dev_key_only_for_development"
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Set default timezone
app.config['TIMEZONE'] = pytz.timezone('UTC')  # Default to UTC

# Initialize extensions
db.init_app(app)
login_manager.init_app(app)
csrf.init_app(app)  # Initialize CSRF protection
login_manager.login_view = 'login'

# Custom unauthorized handler
@login_manager.unauthorized_handler
def unauthorized():
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Authentication required'}), 401
    return redirect(url_for('login', next=request.url))

with app.app_context():
    from models import User, Schedule, Ticket, TicketCategory  # Add ticket models
    db.create_all()

# Import and register blueprints
from routes import *
from ticket_routes import tickets  # Import the tickets blueprint
app.register_blueprint(tickets)  # Register the tickets blueprint

# API Routes
@app.route('/api/active_users')
@login_required
def api_active_users():
    users = User.query.all()
    return jsonify([{
        'id': user.id,
        'username': user.username,
        'color': user.color
    } for user in users])