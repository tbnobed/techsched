import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
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

with app.app_context():
    # Import all models here to ensure they're registered with SQLAlchemy
    from models import User, Schedule, Location, QuickLink, EmailSettings
    db.create_all()

from routes import *