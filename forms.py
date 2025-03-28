from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, DateTimeField, DateField, TextAreaField, ColorField, SelectField, IntegerField
from wtforms.validators import DataRequired, Email, EqualTo, Length, URL, Optional
import pytz

class LocationForm(FlaskForm):
    name = StringField('Location Name', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('Description', validators=[Length(max=200)])
    active = BooleanField('Active', default=True)

class ScheduleForm(FlaskForm):
    technician = SelectField('Technician', coerce=int)
    start_time = DateTimeField('Start Time', validators=[DataRequired()],
                            format='%Y-%m-%d %H:%M')
    end_time = DateTimeField('End Time', validators=[DataRequired()],
                           format='%Y-%m-%d %H:%M')
    description = TextAreaField('Description', validators=[Length(max=200)])
    location_id = SelectField('Location', coerce=int, validators=[Optional()])
    time_off = BooleanField('Time Off')
    repeat_days = StringField('Repeat Days', validators=[Optional()])

class LoginForm(FlaskForm):
    email = StringField('Username or Email', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', 
        validators=[DataRequired(), EqualTo('password')])
    timezone = SelectField('Timezone', choices=[(tz, tz) for tz in pytz.common_timezones])

class AdminUserForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    color = ColorField('Color', default='#3498db')
    is_admin = BooleanField('Is Admin')
    timezone = SelectField('Timezone', 
                         choices=[(tz, tz) for tz in pytz.common_timezones],
                         default='America/Los_Angeles')

class QuickLinkForm(FlaskForm):
    title = StringField('Link Title', validators=[DataRequired(), Length(max=100)])
    url = StringField('URL', validators=[DataRequired(), URL(), Length(max=500)])
    icon = StringField('Feather Icon Name', validators=[DataRequired(), Length(max=50)], default='link')
    category = StringField('Category', validators=[DataRequired(), Length(max=100)])
    order = IntegerField('Display Order', default=0)

class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[DataRequired(), Length(min=6)])
    confirm_new_password = PasswordField('Confirm New Password', 
        validators=[DataRequired(), EqualTo('new_password', message='Passwords must match')])

class EditUserForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    color = ColorField('Color')
    is_admin = BooleanField('Is Admin')
    timezone = SelectField('Timezone', 
                         choices=[(tz, tz) for tz in pytz.common_timezones],
                         default='America/Los_Angeles')
    password = PasswordField('New Password', validators=[Length(min=6)])
    confirm_password = PasswordField('Confirm Password',
        validators=[EqualTo('password')])

class TimezoneForm(FlaskForm):
    timezone = SelectField('Timezone', choices=[(tz, tz) for tz in pytz.common_timezones])

class EmailSettingsForm(FlaskForm):
    admin_email_group = StringField('Admin Email Group', 
                                  validators=[DataRequired(), Email(), Length(max=120)],
                                  default='alerts@obedtv.com')
    notify_on_create = BooleanField('Send notifications for new schedules', default=True)
    notify_on_update = BooleanField('Send notifications for schedule updates', default=True)
    notify_on_delete = BooleanField('Send notifications for schedule deletions', default=True)

class TicketForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(max=200)])
    description = TextAreaField('Description', validators=[DataRequired()])
    category_id = SelectField('Category', coerce=int, validators=[DataRequired()])
    priority = SelectField('Priority', choices=[
        (0, 'Low'),
        (1, 'Medium'),
        (2, 'High'),
        (3, 'Urgent')
    ], coerce=int)
    assigned_to = SelectField('Assign To', coerce=int, validators=[Optional()])
    due_date = DateField('Due Date', format='%Y-%m-%d', validators=[Optional()])

class TicketCommentForm(FlaskForm):
    content = TextAreaField('Comment', validators=[DataRequired()])

class TicketCategoryForm(FlaskForm):
    name = StringField('Category Name', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('Description', validators=[Length(max=200)])
    priority_level = SelectField('Default Priority', choices=[
        (0, 'Low'),
        (1, 'Medium'),
        (2, 'High'),
        (3, 'Urgent')
    ], coerce=int, default=0)