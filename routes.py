from flask import render_template, redirect, url_for, flash, request, jsonify, send_file, make_response
from flask_login import login_user, logout_user, login_required, current_user
from app import app, db
from models import User, Schedule, QuickLink, Location, EmailSettings
from forms import (
    LoginForm, RegistrationForm, ScheduleForm, AdminUserForm, 
    EditUserForm, ChangePasswordForm, QuickLinkForm, LocationForm, EmailSettingsForm
)
from datetime import datetime, timedelta
import pytz
import csv
from io import StringIO
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from io import BytesIO
import json
import os
from werkzeug.utils import secure_filename
from email_utils import send_schedule_notification

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('calendar'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('calendar'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            return redirect(url_for('calendar'))
        flash('Invalid email or password')
    return render_template('login.html', form=form)

@app.route('/admin/email-settings', methods=['GET', 'POST'])
@login_required
def admin_email_settings():
    if not current_user.is_admin:
        flash('Access denied.')
        return redirect(url_for('calendar'))

    # Get or create email settings
    settings = EmailSettings.query.first()
    if not settings:
        settings = EmailSettings()
        db.session.add(settings)
        db.session.commit()

    form = EmailSettingsForm(obj=settings)

    if form.validate_on_submit():
        try:
            settings.admin_email_group = form.admin_email_group.data
            settings.notify_on_create = form.notify_on_create.data
            settings.notify_on_update = form.notify_on_update.data
            settings.notify_on_delete = form.notify_on_delete.data
            db.session.commit()
            flash('Email settings updated successfully!')
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error updating email settings: {str(e)}")
            flash('Error updating email settings.')

    return render_template('admin/email_settings.html', form=form)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/calendar')
@login_required
def calendar():
    week_start = request.args.get('week_start')
    location_filter = request.args.get('location_id', type=int)

    if week_start:
        week_start = datetime.strptime(week_start, '%Y-%m-%d')
        week_start = current_user.get_timezone().localize(
            week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        )
    else:
        week_start = datetime.now(current_user.get_timezone())
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start -= timedelta(days=week_start.weekday())

    # Convert to UTC for database query
    week_start_utc = week_start.astimezone(pytz.UTC)
    week_end_utc = (week_start + timedelta(days=7)).astimezone(pytz.UTC)

    # Query schedules in UTC with optional location filter
    query = Schedule.query.filter(
        Schedule.start_time >= week_start_utc,
        Schedule.start_time < week_end_utc
    )

    if location_filter:
        query = query.filter(Schedule.location_id == location_filter)

    schedules = query.all()

    # Convert schedule times to user's timezone
    user_tz = current_user.get_timezone()
    for schedule in schedules:
        if schedule.start_time.tzinfo is None:
            schedule.start_time = pytz.UTC.localize(schedule.start_time)
        if schedule.end_time.tzinfo is None:
            schedule.end_time = pytz.UTC.localize(schedule.end_time)

        schedule.start_time = schedule.start_time.astimezone(user_tz)
        schedule.end_time = schedule.end_time.astimezone(user_tz)

    form = ScheduleForm()
    if current_user.is_admin:
        form.technician.choices = [(u.id, u.username) for u in User.query.all()]
    else:
        form.technician.choices = [(current_user.id, current_user.username)]
        form.technician.data = current_user.id

    # Add location choices to the form
    form.location_id.choices = [(l.id, l.name) for l in Location.query.filter_by(active=True).order_by(Location.name).all()]

    # Get all active locations for the filter dropdown
    locations = Location.query.filter_by(active=True).order_by(Location.name).all()

    return render_template('calendar.html', 
                         schedules=schedules,
                         week_start=week_start,
                         week_end=week_start + timedelta(days=7),
                         form=form,
                         locations=locations,
                         selected_location=location_filter,
                         today=datetime.now(current_user.get_timezone()),
                         datetime=datetime,
                         timedelta=timedelta)