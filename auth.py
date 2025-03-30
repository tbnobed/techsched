from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from models import User
from forms import LoginForm, RegistrationForm

auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    """
    Handle user login with case-insensitive username/email comparison.
    This function uses SQLAlchemy's func.lower() for proper case-insensitive database queries.
    """
    if current_user.is_authenticated:
        return redirect(url_for('tickets.tickets_dashboard'))
    
    # Initialize logging
    from app import app, db
    from flask import session
    from sqlalchemy import func
    import traceback
    
    app.logger.debug(f"Login attempt - Method: {request.method}")
    app.logger.debug(f"Session before login: {session}")
    
    form = LoginForm()
    if form.validate_on_submit():
        try:
            # Get the email or username from the form
            email_or_username = form.email.data.strip() if form.email.data else ""
            password = form.password.data
            
            app.logger.debug(f"Login form submitted for email: {email_or_username}")
            
            # Find user by email OR username - using case-insensitive matching
            user = None
            
            if '@' in email_or_username:
                # Email login
                user = User.query.filter(func.lower(User.email) == func.lower(email_or_username)).first()
            else:
                # Username login
                user = User.query.filter(func.lower(User.username) == func.lower(email_or_username)).first()
            
            # Log the result of the lookup
            if user:
                app.logger.debug(f"Found user: ID={user.id}, username={user.username}, email={user.email}")
                
                # Check the password
                if user.check_password(password):
                    app.logger.info(f"Successful login for user: {user.username} ({user.email})")
                    login_user(user, remember=form.remember_me.data)
                    
                    # Update session information for debugging
                    app.logger.debug(f"Session after login: {session}")
                    
                    # Redirect to appropriate page
                    next_page = request.args.get('next')
                    return redirect(next_page if next_page else url_for('tickets.tickets_dashboard'))
                else:
                    app.logger.warning(f"Password incorrect for user: {user.username}")
                    app.logger.warning(f"Failed login attempt for email: {email_or_username}")
                    flash('Invalid email or password')
            else:
                app.logger.debug(f"No user found with email/username: {email_or_username}")
                flash('Invalid email or password')
                
        except Exception as e:
            app.logger.error(f"Error during login: {str(e)}")
            app.logger.error(traceback.format_exc())
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
