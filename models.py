import pytz
from app import db, login_manager
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask import current_app
from typing import List

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
    assigned_tickets = db.relationship('Ticket', 
                                     foreign_keys='Ticket.assigned_to',
                                     backref='assigned_technician', 
                                     lazy='dynamic')
    created_tickets = db.relationship('Ticket',
                                    foreign_keys='Ticket.created_by',
                                    backref='creator',
                                    lazy='dynamic')

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
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'password_hash': self.password_hash,
            'is_admin': self.is_admin,
            'color': self.color,
            'timezone': self.timezone,
            'created_schedules': [schedule.id for schedule in self.schedules]
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
            'id': self.id,
            'technician_id': self.technician_id,
            'technician_username': self.technician.username,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat(),
            'description': self.description,
            'location_id': self.location_id,
            'location_name': self.location.name if self.location else None,
            'time_off': self.time_off,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class TicketCategory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.String(200))
    icon = db.Column(db.String(50), default='help-circle')  # Feather icon name
    priority_level = db.Column(db.Integer, default=0)  # Higher number = higher priority
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(pytz.UTC))
    tickets = db.relationship('Ticket', backref='category', lazy='dynamic')

    def __repr__(self):
        return f'<TicketCategory {self.name}>'

class TicketStatus:
    OPEN = 'open'
    IN_PROGRESS = 'in_progress'
    PENDING = 'pending'
    RESOLVED = 'resolved'
    CLOSED = 'closed'

class Ticket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('ticket_category.id'), nullable=False)
    status = db.Column(db.String(20), default=TicketStatus.OPEN)
    priority = db.Column(db.Integer, default=0)  # 0=Low, 1=Medium, 2=High, 3=Urgent
    assigned_to = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(pytz.UTC))
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(pytz.UTC), onupdate=lambda: datetime.now(pytz.UTC))
    due_date = db.Column(db.DateTime(timezone=True))

    comments = db.relationship('TicketComment', backref='ticket', lazy='dynamic', cascade='all, delete-orphan')
    history = db.relationship('TicketHistory', backref='ticket', lazy='dynamic', cascade='all, delete-orphan')

    def add_comment(self, user: User, content: str) -> 'TicketComment':
        comment = TicketComment(
            ticket_id=self.id,
            user_id=user.id,
            content=content
        )
        db.session.add(comment)
        return comment

    def log_history(self, user: User, action: str, details: str = None):
        history = TicketHistory(
            ticket_id=self.id,
            user_id=user.id,
            action=action,
            details=details
        )
        db.session.add(history)
        return history

class TicketComment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('ticket.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(pytz.UTC))
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(pytz.UTC), onupdate=lambda: datetime.now(pytz.UTC))

    user = db.relationship('User', backref='ticket_comments')

class TicketHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('ticket.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    action = db.Column(db.String(50), nullable=False)  # e.g., "status_changed", "assigned", etc.
    details = db.Column(db.Text)  # Additional details about the action
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(pytz.UTC))

    user = db.relationship('User', backref='ticket_history_entries')

class EmailSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    admin_email_group = db.Column(db.String(120), nullable=False, default='engsched-alerts@tbn.tv')
    notify_on_create = db.Column(db.Boolean, default=True)
    notify_on_update = db.Column(db.Boolean, default=True)
    notify_on_delete = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(pytz.UTC))
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(pytz.UTC), onupdate=lambda: datetime.now(pytz.UTC))

    def to_dict(self):
        """Serialize email settings data"""
        return {
            'admin_email_group': self.admin_email_group,
            'notify_on_create': self.notify_on_create,
            'notify_on_update': self.notify_on_update,
            'notify_on_delete': self.notify_on_delete
        }