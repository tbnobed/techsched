from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from models import User
from forms import LoginForm, RegistrationForm

auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('tickets.tickets_dashboard'))
    
    # Add debug logging for the session
    from app import app
    from flask import session
    app.logger.debug(f"Login attempt - Method: {request.method}")
    app.logger.debug(f"Session before login: {session}")
    
    form = LoginForm()
    if form.validate_on_submit():
        # Make input lowercase for case-insensitive login
        login_input = form.email.data if form.email.data else ""
        app.logger.debug(f"Login form submitted for email: {login_input}")
        
        # Initialize user to None
        user = None
        
        # Check if this is a username or email login
        if '@' in login_input:
            # Login with email (case-insensitive using SQL LOWER function)
            email_search = login_input.lower()
            app.logger.debug(f"Looking up by email (lowercase): {email_search}")
            user = User.query.filter(db.func.lower(User.email) == email_search).first()
        else:
            # Case-insensitive username search using SQL LOWER function
            app.logger.debug(f"Looking up by username (case-insensitive): {login_input}")
            username_search = login_input.lower()
            user = User.query.filter(db.func.lower(User.username) == username_search).first()
            
        # Debug log what we found
        if user:
            app.logger.debug(f"Found user: {user.username}, {user.email}")
        else:
            app.logger.warning(f"Failed login attempt for email: {login_input}")
            
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            next_page = request.args.get('next')
            app.logger.debug(f"Login successful for user: {user.username}")
            return redirect(next_page if next_page else url_for('tickets.tickets_dashboard'))
            
        app.logger.warning(f"Invalid credentials for login input: {login_input}")
        flash('Invalid username/email or password')
        
    return render_template('login.html', form=form)

# Registration is disabled - only admins can create users
@auth.route('/register', methods=['GET', 'POST'])
def register():
    # Redirect to login page
    flash('Self-registration is disabled. Please contact your administrator for access.', 'warning')
    return redirect(url_for('auth.login'))

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))
