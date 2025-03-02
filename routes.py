from flask import render_template, redirect, url_for, flash, request, jsonify, send_file, make_response, Response
from flask_login import login_user, logout_user, login_required, current_user
from app import app, db
from models import User, Schedule, QuickLink, Location
from forms import (
    LoginForm, RegistrationForm, ScheduleForm, AdminUserForm, 
    EditUserForm, ChangePasswordForm, QuickLinkForm, LocationForm
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
from flask import current_app

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('calendar'))
    return redirect(url_for('login'))

@app.route('/api/active_users')
@login_required
def get_active_users():
    """Get users who have schedules active at the current time"""
    try:
        # Get current time in UTC since our database stores times in UTC
        current_time = datetime.now(pytz.UTC)

        # Single optimized query to get active users with their schedules and locations
        active_users = (db.session.query(
                User, Schedule, Location
            )
            .join(Schedule, User.id == Schedule.technician_id)
            .outerjoin(Location, Schedule.location_id == Location.id)
            .filter(
                Schedule.start_time <= current_time,
                Schedule.end_time > current_time,
                ~Schedule.time_off  # Exclude time off entries
            )
            .all())

        # Convert times to user's timezone and format response
        user_tz = pytz.timezone(current_user.timezone or 'UTC')
        result = []

        for user, schedule, location in active_users:
            try:
                # Ensure times are timezone-aware
                start_time = schedule.start_time if schedule.start_time.tzinfo else pytz.UTC.localize(schedule.start_time)
                end_time = schedule.end_time if schedule.end_time.tzinfo else pytz.UTC.localize(schedule.end_time)

                # Convert to user's timezone
                start_time = start_time.astimezone(user_tz)
                end_time = end_time.astimezone(user_tz)

                result.append({
                    'username': user.username,
                    'color': user.color or '#3498db',
                    'schedule': {
                        'start_time': start_time.strftime('%H:%M'),
                        'end_time': end_time.strftime('%H:%M'),
                        'description': schedule.description or ''
                    },
                    'location': {
                        'name': location.name if location else 'No Location',
                        'description': location.description if location else ''
                    }
                })
            except Exception as e:
                app.logger.error(f"Error processing user {user.username}: {str(e)}")
                continue

        return jsonify(result)

    except Exception as e:
        app.logger.error(f"Error in get_active_users: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/profile')
@login_required
def profile():
    form = EditUserForm(obj=current_user)
    password_form = ChangePasswordForm()
    return render_template('profile.html', form=form, password_form=password_form)

@app.route('/profile/update', methods=['POST'])
@login_required
def update_profile():
    color = request.form.get('color')
    if color:
        try:
            current_user.color = color
            db.session.commit()
            flash('Profile updated successfully!')
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error updating profile: {str(e)}")
            flash('Error updating profile. Please try again.')
    return redirect(url_for('profile'))

@app.route('/profile/change-password', methods=['POST'])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if current_user.check_password(form.current_password.data):
            current_user.set_password(form.new_password.data)
            db.session.commit()
            flash('Password updated successfully!')
            return redirect(url_for('profile'))
        flash('Current password is incorrect')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{getattr(form, field).label.text}: {error}')
    return redirect(url_for('profile'))


@app.route('/admin/locations', methods=['GET', 'POST'])
@login_required
def admin_locations():
    if not current_user.is_admin:
        flash('Access denied.')
        return redirect(url_for('calendar'))

    form = LocationForm()
    if form.validate_on_submit():
        try:
            location = Location(
                name=form.name.data,
                description=form.description.data,
                active=form.active.data
            )
            db.session.add(location)
            db.session.commit()
            flash('Location added successfully!')
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error creating location: {str(e)}")
            flash('Error creating location. Please try again.')

    locations = Location.query.order_by(Location.name).all()
    return render_template('admin/locations.html', locations=locations, form=form)

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

@app.route('/schedule/new', methods=['GET', 'POST'])
@login_required
def new_schedule():
    form = ScheduleForm()

    # Set up technician choices
    if current_user.is_admin:
        form.technician.choices = [(u.id, u.username) for u in User.query.all()]
    else:
        form.technician.choices = [(current_user.id, current_user.username)]
        form.technician.data = current_user.id

    # Set up location choices
    locations = Location.query.filter_by(active=True).order_by(Location.name).all()
    form.location_id.choices = [(l.id, l.name) for l in locations]
    # Add an empty choice if no locations exist
    if not locations:
        form.location_id.choices = [(0, 'No locations available')]

    if form.validate_on_submit():
        try:
            app.logger.debug(f"Form data received: {request.form}")
            app.logger.debug(f"Time off value: {form.time_off.data}")

            schedule_id = request.form.get('schedule_id')
            technician_id = form.technician.data if current_user.is_admin else current_user.id

            user_tz = current_user.get_timezone()
            start_time = user_tz.localize(form.start_time.data)
            end_time = user_tz.localize(form.end_time.data)

            start_time_utc = start_time.astimezone(pytz.UTC)
            end_time_utc = end_time.astimezone(pytz.UTC)

            if end_time.hour == 0 and end_time.minute == 0:
                end_time_utc = end_time_utc + timedelta(days=1)

            if end_time_utc <= start_time_utc:
                flash('End time must be after start time.')
                return redirect(url_for('calendar'))

            overlapping_query = Schedule.query.filter(
                Schedule.technician_id == technician_id,
                Schedule.id != (int(schedule_id) if schedule_id else None),
                Schedule.start_time < end_time_utc,
                Schedule.end_time > start_time_utc
            )

            overlapping_schedules = overlapping_query.first()

            if overlapping_schedules and not form.time_off.data:
                flash('Schedule conflicts with existing appointments.')
                return redirect(url_for('calendar'))

            if schedule_id:
                schedule = Schedule.query.get_or_404(schedule_id)
                if schedule.technician_id != current_user.id and not current_user.is_admin:
                    flash('You do not have permission to edit this schedule.')
                    return redirect(url_for('calendar'))

                schedule.start_time = start_time_utc
                schedule.end_time = end_time_utc
                schedule.description = form.description.data
                schedule.time_off = bool(form.time_off.data)  # Ensure boolean conversion
                schedule.location_id = form.location_id.data if form.location_id.data != 0 else None
                if current_user.is_admin:
                    schedule.technician_id = technician_id
            else:
                schedule = Schedule(
                    technician_id=technician_id,
                    start_time=start_time_utc,
                    end_time=end_time_utc,
                    description=form.description.data,
                    time_off=bool(form.time_off.data),  # Ensure boolean conversion
                    location_id=form.location_id.data if form.location_id.data != 0 else None
                )
                db.session.add(schedule)

            db.session.commit()
            flash('Schedule updated successfully!' if schedule_id else 'Schedule created successfully!')
            return redirect(url_for('calendar'))

        except Exception as e:
            db.session.rollback()
            flash('Error saving schedule. Please check the time entries.')
            app.logger.error(f"Error saving schedule: {str(e)}")
            return redirect(url_for('calendar'))

    return redirect(url_for('calendar'))

@app.route('/schedule/delete/<int:schedule_id>')
@login_required
def delete_schedule(schedule_id):
    schedule = Schedule.query.get_or_404(schedule_id)

    if schedule.technician_id != current_user.id and not current_user.is_admin:
        flash('You do not have permission to delete this schedule.')
        return redirect(url_for('calendar'))

    try:
        db.session.delete(schedule)
        db.session.commit()
        flash('Schedule deleted successfully!')
    except Exception as e:
        db.session.rollback()
        flash('Error deleting schedule.')
        app.logger.error(f"Error deleting schedule: {str(e)}")

    return redirect(url_for('calendar'))

@app.route('/schedule/copy_previous_week', methods=['POST'])
@login_required
def copy_previous_week_schedules():
    if not current_user.is_admin:
        flash('Access denied.')
        return redirect(url_for('calendar'))

    try:
        if not request.form.get('csrf_token') or not request.form.get('csrf_token') == request.form.get('csrf_token'):
            flash('Invalid request. Please try again.')
            return redirect(url_for('calendar'))

        target_week_start_str = request.form.get('target_week_start')
        if not target_week_start_str:
            flash('Invalid week start date.')
            return redirect(url_for('calendar'))

        user_tz = current_user.get_timezone()

        # Convert target week start to user's timezone
        target_week_start = user_tz.localize(
            datetime.strptime(target_week_start_str, '%Y-%m-%d')
        )
        previous_week_start = target_week_start - timedelta(days=7)

        # Convert to UTC for database operations
        target_week_start_utc = target_week_start.astimezone(pytz.UTC)
        target_week_end_utc = (target_week_start + timedelta(days=7)).astimezone(pytz.UTC)
        previous_week_start_utc = previous_week_start.astimezone(pytz.UTC)
        previous_week_end_utc = (previous_week_start + timedelta(days=7)).astimezone(pytz.UTC)

        app.logger.debug(f"Copying schedules from {previous_week_start_utc} to {previous_week_end_utc}")
        app.logger.debug(f"To target week: {target_week_start_utc} to {target_week_end_utc}")

        # Get previous week's schedules
        previous_schedules = Schedule.query.filter(
            Schedule.start_time >= previous_week_start_utc,
            Schedule.start_time < previous_week_end_utc
        ).all()

        if not previous_schedules:
            flash('No schedules found in previous week to copy.')
            return redirect(url_for('calendar'))

        try:
            # Delete existing schedules in target week
            Schedule.query.filter(
                Schedule.start_time >= target_week_start_utc,
                Schedule.start_time < target_week_end_utc
            ).delete()

            # Copy schedules to new week
            time_difference = target_week_start_utc - previous_week_start_utc

            for schedule in previous_schedules:
                new_schedule = Schedule(
                    technician_id=schedule.technician_id,
                    start_time=schedule.start_time + time_difference,
                    end_time=schedule.end_time + time_difference,
                    description=schedule.description,
                    time_off=schedule.time_off,
                    location_id=schedule.location_id
                )
                db.session.add(new_schedule)

            db.session.commit()
            flash(f'Successfully copied {len(previous_schedules)} schedules from previous week!')

        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Database error in copy_previous_week_schedules: {str(e)}")
            flash('Error copying schedules from previous week.')

    except Exception as e:
        app.logger.error(f"Error in copy_previous_week_schedules: {str(e)}")
        flash('Error copying schedules from previous week.')

    return redirect(url_for('calendar', week_start=target_week_start_str))

@app.route('/update_timezone', methods=['POST'])
@login_required
def update_timezone():
    timezone = request.form.get('timezone')
    if timezone in pytz.all_timezones:
        current_user.timezone = timezone
        db.session.commit()
        flash('Timezone updated successfully!')
    else:
        flash('Invalid timezone')
    return redirect(request.referrer or url_for('calendar'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('calendar'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            next_page = request.args.get('next')
            # Ensure the next page is safe (relative URL)
            if not next_page or not next_page.startswith('/'):
                next_page = url_for('calendar')
            return redirect(next_page)
        flash('Invalid email or password')
    return render_template('login.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('calendar'))

    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Registration successful!')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/admin/dashboard', methods=['GET', 'POST'])
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash('Access denied.')
        return redirect(url_for('calendar'))

    users = User.query.all()
    quick_links = QuickLink.query.order_by(QuickLink.order.asc()).all()
    form = AdminUserForm()
    edit_form = EditUserForm()
    return render_template('admin/dashboard.html', 
                         users=users, 
                         form=form, 
                         edit_form=edit_form,
                         quick_links=quick_links)

@app.route('/admin/create_user', methods=['POST'])
@login_required
def admin_create_user():
    if not current_user.is_admin:
        flash('Access denied.')
        return redirect(url_for('calendar'))

    form = AdminUserForm()
    if form.validate_on_submit():
        try:
            # Check if user already exists
            existing_user = User.query.filter_by(email=form.email.data).first()
            if existing_user:
                flash('Email already registered.')
                return redirect(url_for('admin_dashboard'))

            # Create new user
            user = User(
                username=form.username.data,
                email=form.email.data,
                color=form.color.data or '#3498db',  # Default color if none provided
                is_admin=form.is_admin.data,
                timezone=form.timezone.data or 'America/Los_Angeles'  # Default timezone
            )
            user.set_password(form.password.data)

            # Log the creation attempt
            app.logger.info(f"Creating new user with username: {user.username}, email: {user.email}")

            db.session.add(user)
            db.session.commit()
            flash('User created successfully!')

        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error creating user: {str(e)}")
            flash('Error creating user. Please check the form and try again.')
    else:
        # Log form validation errors
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{field}: {error}")
                app.logger.error(f"Form validation error - {field}: {error}")

    return redirect(url_for('admin_dashboard'))

@app.route('/admin/edit_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
def admin_edit_user(user_id):
    if not current_user.is_admin:
        flash('Access denied.')
        return redirect(url_for('calendar'))

    user = User.query.get_or_404(user_id)
    form = EditUserForm()

    # Debug log for incoming request
    app.logger.debug(f"Edit user request for user_id {user_id}")
    app.logger.debug(f"Request method: {request.method}")
    app.logger.debug(f"Form data: {request.form}")

    if request.method == 'GET':
        form.username.data = user.username
        form.email.data = user.email
        form.color.data = user.color
        form.is_admin.data = user.is_admin
        return render_template('admin/dashboard.html', 
                            users=User.query.all(),
                            form=AdminUserForm(),
                            edit_form=form)

    if request.method == 'POST':
        # Get form data directly from request.form
        username = request.form.get('username')
        email = request.form.get('email')
        color = request.form.get('color')
        password = request.form.get('password')
        is_admin = request.form.get('is_admin') == 'on'

        app.logger.debug(f"Processed form data: username={username}, email={email}, color={color}, is_admin={is_admin}")

        try:
            # Update user fields
            user.username = username
            user.email = email
            user.color = color
            user.is_admin = is_admin

            if password:
                user.set_password(password)

            # Commit changes and verify
            db.session.commit()

            # Verify the changes were saved
            updated_user = User.query.get(user_id)
            app.logger.debug(f"Updated user values: username={updated_user.username}, email={updated_user.email}, color={updated_user.color}, is_admin={updated_user.is_admin}")

            flash('User updated successfully!')
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error updating user: {str(e)}")
            flash('Error updating user. Please try again.')

    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_user/<int:user_id>')
@login_required
def admin_delete_user(user_id):
    if not current_user.is_admin:
        flash('Access denied.')
        return redirect(url_for('calendar'))

    if current_user.id == user_id:
        flash('Cannot delete your own account.')
        return redirect(url_for('admin_dashboard'))

    user = User.query.get_or_404(user_id)
    try:
        # Delete associated schedules first
        Schedule.query.filter_by(technician_id=user_id).delete()
        db.session.delete(user)
        db.session.commit()
        flash('User and associated schedules deleted successfully!')
    except Exception as e:
        db.session.rollback()
        flash('Error deleting user.')
        app.logger.error(f"Error deleting user: {str(e)}")

    return redirect(url_for('admin_dashboard'))

@app.route('/personal_schedule')
@login_required
def personal_schedule():
    week_start = request.args.get('week_start')
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

    # Query schedules in UTC
    schedules = Schedule.query.filter(
        Schedule.technician_id == current_user.id,
        Schedule.start_time >= week_start_utc,
        Schedule.start_time < week_end_utc
    ).all()

    # Convert schedule times to user's timezone
    user_tz = current_user.get_timezone()
    for schedule in schedules:
        # Ensure times are timezone-aware in UTC
        if schedule.start_time.tzinfo is None:
            schedule.start_time = pytz.UTC.localize(schedule.start_time)
        if schedule.end_time.tzinfo is None:
            schedule.end_time = pytz.UTC.localize(schedule.end_time)

        # Convert to user's timezone
        schedule.start_time = schedule.start_time.astimezone(user_tz)
        schedule.end_time = schedule.end_time.astimezone(user_tz)

    form = ScheduleForm()
    form.technician.choices = [(current_user.id, current_user.username)]
    form.technician.data = current_user.id

    return render_template('calendar.html', 
                         schedules=schedules,
                         week_start=week_start,
                         week_end=week_start + timedelta(days=7),
                         form=form,
                         today=datetime.now(current_user.get_timezone()),
                         datetime=datetime,
                         timedelta=timedelta,
                         personal_view=True)

@app.route('/admin/export_schedules')
@login_required
def export_schedules():
    if not current_user.is_admin:
        flash('Access denied.')
        return redirect(url_for('calendar'))

    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        if not start_date or not end_date:
            flash('Please select both start and end dates.')
            return redirect(url_for('admin_dashboard'))

        # Convert dates to UTC datetime objects
        start_datetime = pytz.timezone('America/Chicago').localize(
            datetime.strptime(start_date, '%Y-%m-%d')
        ).astimezone(pytz.UTC)
        end_datetime = (pytz.timezone('America/Chicago').localize(
            datetime.strptime(end_date, '%Y-%m-%d')
        ) + timedelta(days=1)).astimezone(pytz.UTC)

        # Create a new Excel workbook
        wb = Workbook()
        # Remove the default sheet
        wb.remove(wb.active)

        # Get all users sorted by username
        users = User.query.order_by(User.username).all()

        header_font = Font(bold=True)
        header_fill = PatternFill(start_color='CCCCCC', end_color='CCCCCC', fill_type='solid')

        for user in users:
            # Get user's schedules for the date range
            schedules = Schedule.query.filter(
                Schedule.technician_id == user.id,
                Schedule.start_time >= start_datetime,
                Schedule.start_time < end_datetime
            ).order_by(Schedule.start_time).all()

            if not schedules:
                continue

            # Create a new worksheet for each user
            ws = wb.create_sheet(title=user.username[:31])  # Excel limits sheet names to 31 chars

            # Write header
            ws['A1'] = f'Schedule Export - {user.username}'
            ws['A2'] = f'Period: {start_date} to {end_date}'

            # Calculate total hours
            user_tz = pytz.timezone('America/Chicago')
            total_minutes = 0

            for schedule in schedules:
                start_time = schedule.start_time.astimezone(user_tz)
                end_time = schedule.end_time.astimezone(user_tz)
                duration = (end_time - start_time).total_seconds() / 60
                total_minutes += duration

            total_hours = total_minutes // 60
            ws['A4'] = 'Total Hours:'
            ws['B4'] = f"{total_hours:.0f}:00:00"

            # Write column headers
            headers = ['Day', 'Date', 'Clock In', 'Clock Out', 'Total', 'Type', 'Notes']
            for col, header in enumerate(headers, 1):
                cell = ws.cell(row=6, column=col)
                cell.value = header
                cell.font = header_font
                cell.fill = header_fill

            row = 7
            date_cursor = start_datetime.astimezone(user_tz)
            end_date = end_datetime.astimezone(user_tz)

            while date_cursor.date() < end_date.date():
                day_schedules = [s for s in schedules 
                               if s.start_time.astimezone(user_tz).date() == date_cursor.date()]

                if day_schedules:
                    for schedule in sorted(day_schedules, key=lambda s: s.start_time):
                        start_time = schedule.start_time.astimezone(user_tz)
                        end_time = schedule.end_time.astimezone(user_tz)
                        minutes = int((end_time - start_time).total_seconds() / 60)
                        hours = minutes // 60

                        # Determine the type and notes
                        entry_type = "Time Off" if schedule.time_off else "Work"
                        notes = []
                        if schedule.location:
                            notes.append(f"Location: {schedule.location.name}")
                        if schedule.time_off:
                            notes.append("TIME OFF")
                        if schedule.description:
                            if "ON-CALL" in schedule.description.upper():
                                notes.append("ON-CALL")
                            elif "PLEX" in schedule.description.upper():
                                notes.append("PLEX")
                            else:
                                notes.append(schedule.description)

                        # Write schedule data
                        ws.cell(row=row, column=1).value = start_time.strftime('%A')
                        ws.cell(row=row, column=2).value = start_time.strftime('%-m/%-d/%Y')
                        ws.cell(row=row, column=3).value = start_time.strftime('%-I:%M %p')
                        ws.cell(row=row, column=4).value = end_time.strftime('%-I:%M %p')
                        ws.cell(row=row, column=5).value = f"{hours}:00"
                        ws.cell(row=row, column=6).value = entry_type
                        ws.cell(row=row, column=7).value = " | ".join(notes) if notes else ""
                        row += 1
                else:
                    # Write empty row for days with no schedule
                    ws.cell(row=row, column=1).value = date_cursor.strftime('%A')
                    ws.cell(row=row, column=2).value = date_cursor.strftime('%-m/%-d/%Y')
                    ws.cell(row=row, column=3).value = "0"
                    ws.cell(row=row, column=4).value = "0"
                    ws.cell(row=row, column=5).value = "0:00"
                    row += 1
                date_cursor += timedelta(days=1)

            # Auto-adjust column widths
            for column in ws.columns:
                max_length = 0
                column_cells = [cell for cell in column]
                for cell in column_cells:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = (max_length + 2)
                ws.column_dimensions[column[0].column_letter].width = adjusted_width

            # Save to BytesIO
            excel_file = BytesIO()
            wb.save(excel_file)
            excel_file.seek(0)

        # Save to BytesIO
        excel_file = BytesIO()
        wb.save(excel_file)
        excel_file.seek(0)

        return send_file(
            excel_file,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'timesheets_{start_date}_to_{end_date}.xlsx'
        )

    except Exception as e:
        app.logger.error(f"Error exporting schedules: {str(e)}")
        flash('Error exporting schedules. Please try again.')
        return redirect(url_for('admin_dashboard'))

@app.route('/admin/quick_links')
@login_required
def admin_quick_links():
    if not current_user.is_admin:
        flash('Access denied.')
        return redirect(url_for('calendar'))

    form = QuickLinkForm()
    quick_links = QuickLink.query.order_by(QuickLink.order.asc()).all()
    return render_template('admin/quick_links.html', quick_links=quick_links, form=form)

@app.route('/admin/quick_links/create', methods=['POST'])
@login_required
def admin_create_quick_link():
    if not current_user.is_admin:
        flash('Access denied.')
        return redirect(url_for('calendar'))

    try:
        # Create new quick link
        link = QuickLink(
            title=request.form.get('title'),
            url=request.form.get('url'),
            icon=request.form.get('icon', 'link'),
            category=request.form.get('category'),
            order=request.form.get('order', 0)
        )

        db.session.add(link)
        db.session.commit()
        flash('Quick link created successfully!')
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error creating quick link: {str(e)}")
        flash('Error creating quick link. Please try again.')

    return redirect(url_for('admin_quick_links'))

@app.route('/admin/quick_links/edit/<int:link_id>', methods=['POST'])
@login_required
def admin_edit_quick_link(link_id):
    if not current_user.is_admin:
        flash('Access denied.')
        return redirect(url_for('calendar'))

    link = QuickLink.query.get_or_404(link_id)
    try:
        link.title = request.form.get('title')
        link.url = request.form.get('url')
        link.icon = request.form.get('icon')
        link.category = request.form.get('category')
        link.order = request.form.get('order', 0)

        db.session.commit()
        flash('Quick link updated successfully!')
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error updating quick link: {str(e)}")
        flash('Error updating quick link. Please try again.')

    return redirect(url_for('admin_quick_links'))

@app.route('/admin/quick_links/delete/<int:link_id>')
@login_required
def admin_delete_quick_link(link_id):
    if not current_user.is_admin:
        flash('Access denied.')
        return redirect(url_for('calendar'))

    link = QuickLink.query.get_or_404(link_id)
    try:
        db.session.delete(link)
        db.session.commit()
        flash('Quick link deleted successfully!')
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error deleting quick link: {str(e)}")
        flash('Error deleting quick link.')

    return redirect(url_for('admin_quick_links'))

@app.route('/admin/quick_links/reorder', methods=['POST'])
@login_required
def admin_reorder_quick_links():
    """Handle reordering of quick links via AJAX"""
    if not current_user.is_authenticated or not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        new_order = request.json
        if not new_order or not isinstance(new_order, list):
            return jsonify({'error': 'Invalid data format'}), 400

        # Update order for each quick link
        for item in new_order:
            link_id = item.get('id')
            new_position = item.get('order')

            if link_id is None or new_position is None:
                continue

            link = QuickLink.query.get(link_id)
            if link:
                link.order = new_position

        db.session.commit()
        return jsonify({'success': True})

    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Error reordering quick links: {str(e)}')
        return jsonify({'error': 'Server error'}), 500

@app.context_processor
def inject_quick_links():
    def get_quick_links():
        return QuickLink.query.order_by(QuickLink.order.asc(), QuickLink.category).all()
    return dict(get_quick_links=get_quick_links)

@app.route('/api/upcoming_time_off')
def get_upcoming_time_off():
    """Get upcoming time off schedules"""
    if not current_user.is_authenticated:
        return jsonify({'error': 'Authentication required'}), 401

    try:
        # Get current time in UTC
        current_time = datetime.now(pytz.UTC)
        end_time = current_time + timedelta(days=30)  # Look ahead 30 days

        # Query upcoming time off schedules
        time_off_schedules = (
            Schedule.query
            .join(User, Schedule.technician_id == User.id)
            .filter(
                Schedule.time_off == True,
                Schedule.start_time >= current_time,
                Schedule.start_time <= end_time
            )
            .order_by(Schedule.start_time)
            .all()
        )

        # Format response
        result = []
        user_tz = pytz.timezone(current_user.timezone or 'UTC')

        for schedule in time_off_schedules:
            try:
                start_time = schedule.start_time if schedule.start_time.tzinfo else pytz.UTC.localize(schedule.start_time)
                end_time = schedule.end_time if schedule.end_time.tzinfo else pytz.UTC.localize(schedule.end_time)

                start_time = start_time.astimezone(user_tz)
                end_time = end_time.astimezone(user_tz)

                result.append({
                    'username': schedule.technician.username,
                    'start_date': start_time.strftime('%Y-%m-%d'),
                    'end_date': end_time.strftime('%Y-%m-%d'),
                    'description': schedule.description or 'Time Off'
                })
            except Exception as e:
                app.logger.error(f"Error processing time off schedule: {str(e)}")
                continue

        return jsonify(result)

    except Exception as e:
        app.logger.error(f"Error in get_upcoming_time_off: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/admin/backup')
@login_required
def admin_backup():
    """Render the backup/restore interface"""
    if not current_user.is_authenticated or not current_user.is_admin:
        flash('Access denied. Admin privileges required.')
        return redirect(url_for('calendar'))
    return render_template('admin/backup.html')

@app.route('/admin/backup/download')
@login_required
def admin_backup_download():
    """Generate and send a backup file"""
    if not current_user.is_authenticated or not current_user.is_admin:
        flash('Access denied. Admin privileges required.')
        return redirect(url_for('calendar'))

    try:
        # Generate backup data in chunks to reduce memory usage
        def generate():
            # Start JSON object
            yield '{\n'

            # Users
            yield '"users": [\n'
            for i, user in enumerate(User.query.yield_per(100)):
                user_data = {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'password_hash': user.password_hash,
                    'is_admin': user.is_admin,
                    'color': user.color,
                    'timezone': user.timezone
                }
                yield json.dumps(user_data, indent=2)
                if i < User.query.count() - 1:
                    yield ',\n'
            yield '],\n'

            # Locations
            yield '"locations": [\n'
            for i, location in enumerate(Location.query.yield_per(100)):
                location_data = {
                    'id': location.id,
                    'name': location.name,
                    'description': location.description,
                    'active': location.active
                }
                yield json.dumps(location_data, indent=2)
                if i < Location.query.count() - 1:
                    yield ',\n'
            yield '],\n'

            # Quick Links
            yield '"quick_links": [\n'
            for i, link in enumerate(QuickLink.query.yield_per(100)):
                link_data = {
                    'title': link.title,
                    'url': link.url,
                    'icon': link.icon,
                    'category': link.category,
                    'order': link.order
                }
                yield json.dumps(link_data, indent=2)
                if i < QuickLink.query.count() - 1:
                    yield ',\n'
            yield '],\n'

            # Schedules
            yield '"schedules": [\n'
            for i, schedule in enumerate(Schedule.query.yield_per(100)):
                schedule_data = {
                    'technician_id': schedule.technician_id,
                    'start_time': schedule.start_time.isoformat(),
                    'end_time': schedule.end_time.isoformat(),
                    'description': schedule.description,
                    'time_off': schedule.time_off,
                    'location_id': schedule.location_id
                }
                yield json.dumps(schedule_data, indent=2)
                if i < Schedule.query.count() - 1:
                    yield ',\n'
            yield ']\n'

            # End JSON object
            yield '}\n'

        # Generate filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'backup_{timestamp}.json'

        # Return streaming response
        return Response(
            generate(),
            mimetype='application/json',
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"',
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no'  # Disable response buffering
            }
        )

    except Exception as e:
        app.logger.error(f'Error creating backup: {str(e)}')
        flash('Error creating backup. Please try again.')
        return redirect(url_for('admin_backup'))

@app.route('/admin/backup/restore', methods=['POST'])
@login_required
def admin_backup_restore():
    """Restore data from a backup file"""
    if not current_user.is_authenticated or not current_user.is_admin:
        flash('Access denied. Admin privileges required.')
        return redirect(url_for('calendar'))

    if 'backup_file' not in request.files:
        flash('No backup file provided')
        return redirect(url_for('admin_backup'))

    file = request.files['backup_file']
    if file.filename == '':
        flash('No backup file selected')
        return redirect(url_for('admin_backup'))

    if not file.filename.endswith('.json'):
        flash('Invalid file type. Please upload a JSON backup file.')
        return redirect(url_for('admin_backup'))

    try:
        app.logger.info('Starting backup restoration process...')
        backup_content = file.read().decode('utf-8')

        try:
            backup_data = json.loads(backup_content)
            app.logger.info('Backup file loaded and parsed successfully')
        except json.JSONDecodeError as e:
            app.logger.error(f'Invalid JSON format in backup file: {str(e)}')
            flash('Invalid backup file format.')
            return redirect(url_for('admin_backup'))

        # Begin transaction
        try:
            # Step 1: Restore Users first (they have no dependencies)
            user_id_mapping = {}
            for user_data in backup_data.get('users', []):
                email = user_data.get('email')
                if not email:
                    continue

                user = User.query.filter_by(email=email).first()
                if user:
                    user.username = user_data.get('username')
                    user.is_admin = user_data.get('is_admin', False)
                    user.color = user_data.get('color', '#3498db')
                    user.timezone = user_data.get('timezone', 'America/Los_Angeles')
                    user_id_mapping[user_data.get('id')] = user.id
                else:
                    new_user = User(
                        username=user_data.get('username'),
                        email=email,
                        password_hash=user_data.get('password_hash'),
                        is_admin=user_data.get('is_admin', False),
                        color=user_data.get('color', '#3498db'),
                        timezone=user_data.get('timezone', 'America/Los_Angeles')
                    )
                    db.session.add(new_user)
                    db.session.flush()
                    user_id_mapping[user_data.get('id')] = new_user.id

            db.session.commit()
            app.logger.info('Users restored successfully')

            # Step 2: Restore Locations
            location_id_mapping = {}
            for location_data in backup_data.get('locations', []):
                name = location_data.get('name')
                if not name:
                    continue

                location = Location.query.filter_by(name=name).first()
                if location:
                    location.description = location_data.get('description')
                    location.active = location_data.get('active', True)
                    location_id_mapping[location_data.get('id')] = location.id
                else:
                    new_location = Location(
                        name=name,
                        description=location_data.get('description'),
                        active=location_data.get('active', True)
                    )
                    db.session.add(new_location)
                    db.session.flush()
                    location_id_mapping[location_data.get('id')] = new_location.id

            db.session.commit()
            app.logger.info('Locations restored successfully')

            # Step 3: Restore Quick Links
            for link_data in backup_data.get('quick_links', []):
                title = link_data.get('title')
                if not title:
                    continue

                link = QuickLink.query.filter_by(title=title).first()
                if link:
                    link.url = link_data.get('url')
                    link.icon = link_data.get('icon')
                    link.category = link_data.get('category')
                    link.order = link_data.get('order', 0)
                else:
                    new_link = QuickLink(
                        title=title,
                        url=link_data.get('url'),
                        icon=link_data.get('icon'),
                        category=link_data.get('category'),
                        order=link_data.get('order', 0)
                    )
                    db.session.add(new_link)

            db.session.commit()
            app.logger.info('Quick links restored successfully')

            # Step 4: Restore Schedules
            schedules_restored = 0
            schedules_skipped = 0
            schedules_updated = 0

            for schedule_data in backup_data.get('schedules', []):
                try:
                    # Map the technician_id to the new user ID
                    old_tech_id = schedule_data.get('technician_id')
                    new_tech_id = user_id_mapping.get(old_tech_id)

                    if not new_tech_id:
                        app.logger.warning(f'Skipping schedule - technician {old_tech_id} not found')
                        schedules_skipped += 1
                        continue

                    # Map the location_id to the new location ID
                    old_location_id = schedule_data.get('location_id')
                    new_location_id = location_id_mapping.get(old_location_id)

                    # Convert schedule times
                    start_time = datetime.fromisoformat(schedule_data.get('start_time'))
                    end_time = datetime.fromisoformat(schedule_data.get('end_time'))

                    # Check for existing schedule with same criteria
                    existing_schedule = Schedule.query.filter(
                        Schedule.technician_id == new_tech_id,
                        Schedule.start_time == start_time,
                        Schedule.end_time == end_time,
                        Schedule.location_id == new_location_id,
                        Schedule.time_off == schedule_data.get('time_off', False)
                    ).first()

                    if existing_schedule:
                        # Update existing schedule only if description differs
                        if existing_schedule.description != schedule_data.get('description'):
                            existing_schedule.description = schedule_data.get('description')
                            schedules_updated += 1
                    else:
                        # Create new schedule
                        new_schedule = Schedule(
                            technician_id=new_tech_id,
                            start_time=start_time,
                            end_time=end_time,
                            description=schedule_data.get('description'),
                            time_off=schedule_data.get('time_off', False),
                            location_id=new_location_id
                        )
                        db.session.add(new_schedule)
                        schedules_restored += 1

                except (ValueError, KeyError) as e:
                    app.logger.error(f'Error processing schedule: {str(e)}')
                    schedules_skipped += 1
                    continue

            db.session.commit()
            app.logger.info(f'Schedules processed: {schedules_restored} restored, {schedules_updated} updated, {schedules_skipped} skipped')
            flash(f'Backup restored successfully! {schedules_restored} schedules restored, {schedules_updated} updated, {schedules_skipped} skipped.')

        except Exception as e:
            db.session.rollback()
            app.logger.error(f'Database error during restoration: {str(e)}')
            flash('Error restoring backup: Database error occurred.')
            return redirect(url_for('admin_backup'))

    except Exception as e:
        app.logger.error(f'Error restoring backup: {str(e)}')
        flash('Error restoring backup. Please check the file and try again.')

    return redirect(url_for('admin_backup'))

@app.route('/admin/locations/edit/<int:location_id>', methods=['POST'])
@login_required
def admin_edit_location(location_id):
    if not current_user.is_admin:
        flash('Access denied.')
        return redirect(url_for('calendar'))

    location = Location.query.get_or_404(location_id)
    try:
        location.name = request.form.get('name')
        location.description = request.form.get('description')
        location.active = request.form.get('active') == 'on'

        db.session.commit()
        flash('Location updated successfully!')
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error updating location: {str(e)}")
        flash('Error updating location. Please try again.')

    return redirect(url_for('admin_locations'))

@app.route('/admin/locations/delete/<int:location_id>')
@login_required
def admin_delete_location(location_id):
    if not current_user.is_admin:
        flash('Access denied.')
        return redirect(url_for('calendar'))

    location = Location.query.get_or_404(location_id)
    try:
        # Check if location is being used in any schedules
        schedule_count = Schedule.query.filter_by(location_id=location_id).count()
        if schedule_count > 0:
            flash(f'Cannot delete location. It is being used in {schedule_count} schedules.')
            return redirect(url_for('admin_locations'))

        db.session.delete(location)
        db.session.commit()
        flash('Location deleted successfully!')
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error deleting location: {str(e)}")
        flash('Error deleting location.')

    return redirect(url_for('admin_locations'))
@app.route('/admin/locations/toggle/<int:location_id>', methods=['POST'])
@login_required
def admin_toggle_location(location_id):
    """Toggle location active status"""
    app.logger.info(f'Location toggle requested for ID: {location_id} by user: {current_user.username}')

    if not current_user.is_admin:
        app.logger.warning(f'Non-admin user {current_user.username} attempted to toggle location {location_id}')
        flash('Access denied.')
        return redirect(url_for('calendar'))

    try:
        location = Location.query.get_or_404(location_id)
        current_status = location.active
        location.active = not location.active
        location.updated_at = datetime.now(pytz.UTC)

        app.logger.info(f'Toggling location {location_id} ({location.name}) from {current_status} to {location.active}')

        db.session.commit()

        status = 'activated' if location.active else 'deactivated'
        flash(f'Location "{location.name}" {status} successfully!')
        app.logger.info(f'Location {location_id} ({location.name}) successfully {status}')

    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Error toggling location {location_id} status: {str(e)}')
        flash('Error updating location status.')

    return redirect(url_for('admin_locations'))