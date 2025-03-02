import pytz
from app import db, login_manager
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask import current_app

@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))

class Location(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.String(200))
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(pytz.UTC))
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(pytz.UTC), onupdate=lambda: datetime.now(pytz.UTC))

    def __repr__(self):
        return f'<Location {self.name}>'

    def to_dict(self):
        """Serialize location data for backup"""
        return {
            'id': self.id,  # Include ID for reference
            'name': self.name,
            'description': self.description,
            'active': self.active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class QuickLink(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    url = db.Column(db.String(500), nullable=False)
    icon = db.Column(db.String(50), nullable=False, default='link')  # Feather icon name
    category = db.Column(db.String(100), nullable=False)
    order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(pytz.UTC))
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(pytz.UTC), onupdate=lambda: datetime.now(pytz.UTC))

    def __repr__(self):
        return f'<QuickLink {self.title}>'

    def to_dict(self):
        """Serialize quick link data for backup"""
        return {
            'title': self.title,
            'url': self.url,
            'icon': self.icon,
            'category': self.category,
            'order': self.order
        }

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    is_admin = db.Column(db.Boolean, default=False)
    color = db.Column(db.String(7), default="#3498db")  # Default color for calendar
    timezone = db.Column(db.String(50), default='UTC')  # New timezone field
    schedules = db.relationship('Schedule', backref='technician', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_timezone(self):
        """Get the user's timezone or fallback to app default"""
        try:
            return pytz.timezone(self.timezone)
        except pytz.exceptions.UnknownTimeZoneError:
            return current_app.config['TIMEZONE']

    def to_dict(self):
        """Serialize user data for backup"""
        return {
            'id': self.id,  # Include ID for reference
            'username': self.username,
            'email': self.email,
            'password_hash': self.password_hash,
            'is_admin': self.is_admin,
            'color': self.color,
            'timezone': self.timezone,
            'created_schedules': [schedule.id for schedule in self.schedules]  # Add reference to schedules
        }

class Schedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    technician_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    start_time = db.Column(db.DateTime(timezone=True), nullable=False)
    end_time = db.Column(db.DateTime(timezone=True), nullable=False)
    description = db.Column(db.String(200))
    location_id = db.Column(db.Integer, db.ForeignKey('location.id'))
    location = db.relationship('Location', backref='schedules')
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(current_app.config['TIMEZONE']))
    time_off = db.Column(db.Boolean, default=False)  # For time off entries

    def to_dict(self):
        """Serialize schedule data for backup with reference data"""
        return {
            'id': self.id,  # Include ID for reference
            'technician_id': self.technician_id,
            'technician_username': self.technician.username,  # Add username for mapping
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat(),
            'description': self.description,
            'location_id': self.location_id,
            'location_name': self.location.name if self.location else None,  # Add location name for mapping
            'time_off': self.time_off,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }