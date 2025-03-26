from flask import render_template, redirect, url_for, flash, request, jsonify, send_file, make_response
from flask_login import login_required, current_user
from app import app, db
from models import User, Schedule, QuickLink, Location, EmailSettings
from forms import (
    ScheduleForm, AdminUserForm, EditUserForm, ChangePasswordForm, 
    QuickLinkForm, LocationForm, EmailSettingsForm
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
    return redirect(url_for('auth.login'))

@app.route('/api/active_users')
@login_required
def get_active_users():
    """Get users who have schedules active at the current time"""
    if not current_user.is_authenticated:
        return jsonify({'error': 'Authentication required'}), 401

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
        user_tz = current_user.get_timezone()
        result = []
        for user, schedule, location in active_users:
            # Convert schedule times to user's timezone
            start_time = schedule.start_time.astimezone(user_tz)
            end_time = schedule.end_time.astimezone(user_tz)

            result.append({
                'username': user.username,
                'color': user.color,
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

                old_desc = schedule.description
                schedule.start_time = start_time_utc
                schedule.end_time = end_time_utc
                schedule.description = form.description.data
                schedule.time_off = form.time_off.data
                schedule.location_id = form.location_id.data if form.location_id.data != 0 else None
                if current_user.is_admin:
                    schedule.technician_id = technician_id
                send_schedule_notification(schedule, 'updated', f"Schedule updated by {current_user.username}")
            else:
                schedule = Schedule(
                    technician_id=technician_id,
                    start_time=start_time_utc,
                    end_time=end_time_utc,
                    description=form.description.data,
                    time_off=form.time_off.data,
                    location_id=form.location_id.data if form.location_id.data != 0 else None
                )
                db.session.add(schedule)
                send_schedule_notification(schedule, 'created', f"Schedule created by {current_user.username}")

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
        send_schedule_notification(schedule, 'deleted', f"Schedule deleted by {current_user.username}")
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
                column = [cell for cell in column]
                for cell in column:
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

        return send_file(
            excel_file,            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
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
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Access denied'}), 403

    try:
        new_order = request.json
        # First, get all links and set a high order number to avoid conflicts
        links = QuickLink.query.all()
        for link in links:
            link.order = 10000 + link.order

        db.session.commit()

        # Then update with new order
        for item in new_order:
            link = QuickLink.query.get(item['id'])
            if link:
                link.order = int(item['order'])

        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error reordering quick links: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.context_processor
def inject_quick_links():
    def get_quick_links():
        return QuickLink.query.order_by(QuickLink.order.asc(), QuickLink.category).all()
    return dict(get_quick_links=get_quick_links)

@app.route('/api/upcoming_time_off')
@login_required
def get_upcoming_time_off():
    """Get time off entries for the next 2 weeks"""
    try:
        # Get current time in UTC since our database stores times inUTC
        current_time = datetime.now(pytz.UTC)
        two_weeks_later = current_time + timedelta(days=14)

        # Query for upcoming time off entries
        time_off_entries = (Schedule.query
            .join(User)
            .filter(
                Schedule.start_time >= current_time,
                Schedule.start_time <= two_weeks_later,
                Schedule.time_off == True
            )
            .with_entities(
                User.username,
                Schedule.start_time,
                Schedule.end_time,
                Schedule.description
            )
            .order_by(Schedule.start_time)
            .all())

        # Group entries by username and consolidate consecutive dates
        user_entries = {}
        formatted_entries = []
        user_tz = pytz.timezone('America/Los_Angeles')  # Default timezone

        for username, start_time, end_time, description in time_off_entries:
            if username not in user_entries:
                user_entries[username] = []

            start_local = start_time.astimezone(user_tz)
            end_local = end_time.astimezone(user_tz)

            user_entries[username].append({
                'start_date': start_local.date(),
                'end_date': end_local.date(),
                'description': description
            })

        # Consolidate consecutive dates for each user
        for username, entries in user_entries.items():
            entries.sort(key=lambda x: x['start_date'])
            consolidated = []
            current_entry = entries[0]

            for entry in entries[1:]:
                if (entry['start_date'] - current_entry['end_date']).days <= 1:                    # Consecutive days, extend the current entry
                    current_entry['end_date'] = max(current_entry['end_date'], entry['end_date'])
                else:
                    # Non-consecutive, add current entry and start a new one
                    consolidated.append(current_entry)
                    current_entry = entry

            consolidated.append(current_entry)

            # Format consolidated entries
            for entry in consolidated:
                duration = (entry['end_date'] - entry['start_date']).days + 1
                formatted_entries.append({
                    'username': username,
                    'start_date': entry['start_date'].strftime('%b %d'),
                    'end_date': entry['end_date'].strftime('%b %d'),
                    'duration': f"{duration} day{'s' if duration != 1 else ''}",
                    'description': entry.get('description') or 'Time Off'
                })

        return jsonify(formatted_entries)
    except Exception as e:
        app.logger.error(f"Error in get_upcoming_time_off: {str(e)}")
        return jsonify([])

@app.route('/admin/backup')
@login_required
def admin_backup():
    if not current_user.is_admin:
        flash('Access denied.')
        return redirect(url_for('calendar'))
    return render_template('admin/backup.html')

@app.route('/admin/backup/download')
@login_required
def download_backup():
    if not current_user.is_admin:
        flash('Access denied.')
        return redirect(url_for('calendar'))

    try:
        # Collect all data with complete reference information
        backup_data = {
            'users': [user.to_dict() for user in User.query.all()],
            'locations': [location.to_dict() for location in Location.query.all()],
            'schedules': [schedule.to_dict() for schedule in Schedule.query.all()],
            'quick_links': [link.to_dict() for link in QuickLink.query.all()]
        }

        # Create the backup file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_json = json.dumps(backup_data, indent=2, default=str)

        response = make_response(backup_json)
        response.headers['Content-Type'] = 'application/json'
        response.headers['Content-Disposition'] = f'attachment; filename=backup_{timestamp}.json'

        app.logger.info(f"Backup created successfully with {len(backup_data['schedules'])} schedules")
        return response

    except Exception as e:
        app.logger.error(f"Error creating backup: {str(e)}")
        flash('Error creating backup')
        return redirect(url_for('admin_backup'))

@app.route('/admin/restore', methods=['POST'])
@login_required
def restore_backup():
    if not current_user.is_admin:
        flash('Access denied.')
        return redirect(url_for('calendar'))

    if 'backup_file' not in request.files:
        flash('No file uploaded')
        return redirect(url_for('admin_backup'))

    file = request.files['backup_file']
    if not file.filename:
        flash('No file selected')
        return redirect(url_for('admin_backup'))

    try:
        backup_data = json.loads(file.read().decode('utf-8'))
        app.logger.info("Starting backup restoration process...")

        # Initialize mappings for existing data
        existing_users = {user.username.lower(): user for user in User.query.all()}
        existing_locations = {loc.name.lower(): loc for loc in Location.query.all()}
        existing_quick_links = {(link.title.lower(), link.url.lower()): link for link in QuickLink.query.all()}

        try:
            # Process users first
            if 'users' in backup_data:
                app.logger.info("Starting user restoration...")
                for user_data in backup_data['users']:
                    try:
                        username = user_data.get('username')
                        email = user_data.get('email')

                        if not username or not email:
                            app.logger.warning(f"Skipping user with missing data")
                            continue

                        # Check if user exists (case-insensitive)
                        existing_user = existing_users.get(username.lower())
                        if existing_user:
                            app.logger.info(f"User {username} already exists")
                            continue

                        # Create new user
                        user = User(
                            username=username,
                            email=email,
                            password_hash=user_data['password_hash'],
                            color=user_data.get('color', '#3498db'),
                            is_admin=user_data.get('is_admin', False),
                            timezone=user_data.get('timezone', 'America/Los_Angeles')
                        )
                        db.session.add(user)
                        app.logger.info(f"Created new user {username}")

                    except Exception as e:
                        app.logger.error(f"Error processing user {username}: {str(e)}")
                        continue

                db.session.commit()
                app.logger.info("Users committed successfully")

            # Process locations
            if 'locations' in backup_data:
                app.logger.info("Starting location restoration...")
                for loc_data in backup_data['locations']:
                    try:
                        name = loc_data.get('name')
                        if not name:
                            continue

                        # Check if location exists (case-insensitive)
                        existing_location = existing_locations.get(name.lower())
                        if existing_location:
                            app.logger.info(f"Location {name} already exists")
                            continue

                        # Create new location
                        location = Location(
                            name=name,
                            description=loc_data.get('description', ''),
                            active=loc_data.get('active', True)
                        )
                        db.session.add(location)
                        app.logger.info(f"Created new location {name}")

                    except Exception as e:
                        app.logger.error(f"Error processing location {name}: {str(e)}")
                        continue

                db.session.commit()
                app.logger.info("Locations committed successfully")

            # Process schedules
            restored_count = 0
            skipped_count = 0

            if 'schedules' in backup_data:
                app.logger.info("Starting schedule restoration...")

                # Refresh user and location data after commits
                users_by_username = {user.username: user for user in User.query.all()}
                locations_by_name = {loc.name: loc for loc in Location.query.all()}

                for schedule_data in backup_data['schedules']:
                    try:
                        # Get technician by username
                        tech_username = schedule_data.get('technician_username')
                        if not tech_username:
                            app.logger.warning("Schedule missing technician username")
                            skipped_count += 1
                            continue

                        technician = users_by_username.get(tech_username)
                        if not technician:
                            app.logger.warning(f"Could not find technician: {tech_username}")
                            skipped_count += 1
                            continue

                        # Get location by name if specified
                        location_id = None
                        location_name = schedule_data.get('location_name')
                        if location_name:
                            location = locations_by_name.get(location_name)
                            if location:
                                location_id = location.id

                        start_time = datetime.fromisoformat(schedule_data['start_time'])
                        end_time = datetime.fromisoformat(schedule_data['end_time'])

                        # Check for existing schedule with same technician, time, and location
                        existing_schedule = Schedule.query.filter_by(
                            technician_id=technician.id,
                            start_time=start_time,
                            end_time=end_time,
                            location_id=location_id
                        ).first()

                        if existing_schedule:
                            app.logger.info(f"Schedule already exists for {tech_username} at {start_time}")
                            skipped_count += 1
                            continue

                        schedule = Schedule(
                            technician_id=technician.id,
                            location_id=location_id,
                            start_time=start_time,
                            end_time=end_time,
                            description=schedule_data.get('description'),
                            time_off=schedule_data.get('time_off', False)
                        )
                        db.session.add(schedule)
                        restored_count += 1

                    except Exception as e:
                        app.logger.error(f"Error processing schedule: {str(e)}")
                        skipped_count += 1
                        continue

                db.session.commit()
                app.logger.info(f"Schedules committed successfully. Restored: {restored_count}, Skipped: {skipped_count}")

            # Process quick links if present
            if 'quick_links' in backup_data:
                app.logger.info("Starting quick links restoration...")
                for link_data in backup_data['quick_links']:
                    try:
                        title = link_data.get('title', '').lower()
                        url = link_data.get('url', '').lower()

                        # Skip if title or url is missing
                        if not title or not url:
                            continue

                        # Check if link already exists
                        if (title, url) in existing_quick_links:
                            app.logger.info(f"Quick link already exists: {title}")
                            continue

                        link = QuickLink(
                            title=link_data['title'],
                            url=link_data['url'],
                            icon=link_data.get('icon', 'link'),
                            category=link_data['category'],
                            order=link_data.get('order', 0)
                        )
                        db.session.add(link)
                        app.logger.info(f"Created new quick link: {title}")

                    except Exception as e:
                        app.logger.error(f"Error processing quick link: {str(e)}")
                        continue

                db.session.commit()
                app.logger.info("Quick links committed successfully")

            flash(f'Backup restored successfully! {restored_count} schedules restored, {skipped_count} skipped.')
            app.logger.info("Backup restore completed successfully")

        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error in backup restoration: {str(e)}")
            flash('Error restoring backup')
            raise

    except json.JSONDecodeError:
        flash('Invalid backup file format')
    except Exception as e:
        flash('Error restoring backup')
        app.logger.error(f"Unexpected error in restore_backup: {str(e)}")

    return redirect(url_for('admin_backup'))

@app.route('/admin/locations/edit/<int:location_id>', methods=['POST'])
@login_required
def admin_edit_location(location_id):
    if not current_user.is_admin:
        flash('Access denied.')
        return redirect(url_for('calendar'))

    location = Location.query.get_or_404(location_id)
    try:
        # Get form data with proper boolean conversion for active status
        name = request.form.get('name')
        description = request.form.get('description', '')
        # Explicitly check for the checkbox value
        active = 'active' in request.form

        # Validate required fields
        if not name:
            flash('Location name is required.')
            return redirect(url_for('admin_locations'))

        # Track if status changed
        status_changed = location.active != active

        # Update location
        location.name = name
        location.description = description
        location.active = active

        db.session.commit()

        # Log the status change if it occurred
        if status_changed:
            app.logger.info(f"Location '{location.name}' status changed to {'active' if active else 'inactive'}")
            flash(f"Location '{location.name}' has been {'activated' if active else 'deactivated'}.")
        else:
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

    # Check if location is being used in any schedules
    if location.schedules:
        flash('Cannot delete location that has associated schedules.')
        return redirect(url_for('admin_locations'))

    try:
        db.session.delete(location)
        db.session.commit()
        flash('Location deleted successfully!')
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error deleting location: {str(e)}")
        flash('Error deleting location. Please try again.')

    return redirect(url_for('admin_locations'))
@app.route('/admin/email-settings', methods=['GET', 'POST'])
@login_required
def admin_email_settings():
    if not current_user.is_admin:
        flash('Access denied.')
        return redirect(url_for('calendar'))

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