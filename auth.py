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
        try:
            # Make input lowercase for case-insensitive login
            login_input = form.email.data.strip() if form.email.data else ""
            app.logger.debug(f"Login form submitted for email: {login_input}")
            
            # Initialize user to None
            user = None
            
            # ***** SIMPLIFIED LOGIN LOGIC *****
            # Check if this is a username or email login
            if '@' in login_input:
                # Get all users and do direct string comparison with lowercase emails
                app.logger.debug(f"Email login attempt: {login_input}")
                
                # Try direct string comparison instead of SQLAlchemy query
                for u in User.query.all():
                    if u.email.lower() == login_input.lower():
                        user = u
                        app.logger.debug(f"Found user {u.username} with matching email (case-insensitive)")
                        break
            else:
                # Username login attempt
                app.logger.debug(f"Username login attempt: {login_input}")
                
                # Try direct string comparison instead of SQLAlchemy query
                for u in User.query.all():
                    if u.username.lower() == login_input.lower():
                        user = u
                        app.logger.debug(f"Found user with matching username (case-insensitive)")
                        break
            
            # Log the user found (or not)
            if user:
                app.logger.debug(f"Found user: {user.username}, {user.email}")
            else:
                app.logger.warning(f"Failed login attempt - no matching user for: {login_input}")
                
            # Try password check if we found a user
            if user and user.check_password(form.password.data):
                # Log the successful login with more details
                app.logger.info(f"User {user.username} ({user.email}) logged in successfully")
                login_user(user, remember=form.remember_me.data)
                next_page = request.args.get('next')
                app.logger.debug(f"Session after login: {session}")
                app.logger.debug(f"Redirecting to: {next_page if next_page else 'tickets.tickets_dashboard'}")
                return redirect(next_page if next_page else url_for('tickets.tickets_dashboard'))
                
            app.logger.warning(f"Invalid credentials for login input: {login_input}")
            flash('Invalid username/email or password')
            
        except Exception as e:
            app.logger.error(f"Error during login: {str(e)}")
            flash('An error occurred during login. Please try again.')
        
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
    
@auth.route('/debug_users')
def debug_users():
    from app import app
    
    # Only allow this in development
    if not app.debug:
        return "Debug mode is disabled", 403
        
    # Get all users and format their info
    users = User.query.all()
    user_info = []
    for user in users:
        user_info.append({
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "is_admin": user.is_admin
        })
        
    import json
    return json.dumps(user_info, indent=2), 200, {'Content-Type': 'application/json'}
