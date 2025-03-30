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
            app.logger.debug(f"Login form submitted for input: {login_input}")
            
            # EVEN SIMPLER LOGIN LOGIC - Check with exact matches for database values first
            if '@' in login_input:
                # Email login attempt - find the user by exact email, case-insensitive
                app.logger.debug(f"Looking for exact email match: {login_input}")
                
                # The issue is likely that the OSandoval@tbn.tv is being entered but
                # the database has osandoval@tbn.tv (lowercase)
                desired_email = login_input.lower()
                app.logger.debug(f"Normalized input email to lowercase: {desired_email}")
                
                # Find direct matches
                all_users = User.query.all()
                app.logger.debug(f"Total users in database: {len(all_users)}")
                
                for user in all_users:
                    db_email = user.email.lower() if user.email else ""
                    app.logger.debug(f"Comparing DB email: '{db_email}' with input: '{desired_email}'")
                    if db_email == desired_email:
                        app.logger.info(f"Found exact email match for {user.username}")
                        
                        # Verify password
                        password = form.password.data
                        password_correct = user.check_password(password)
                        app.logger.debug(f"Password check result: {password_correct}")
                        
                        if password_correct:
                            # Login successful
                            app.logger.info(f"User {user.username} ({user.email}) logged in successfully")
                            login_user(user, remember=form.remember_me.data)
                            next_page = request.args.get('next')
                            app.logger.debug(f"Session after login: {session}")
                            app.logger.debug(f"Redirecting to: {next_page if next_page else 'tickets.tickets_dashboard'}")
                            return redirect(next_page if next_page else url_for('tickets.tickets_dashboard'))
                        else:
                            app.logger.warning(f"Password incorrect for user: {user.username}")
                            flash('Invalid username/email or password')
                            return render_template('login.html', form=form)
                
                # If we get here, no email match was found
                app.logger.warning(f"No matching email found for: {desired_email}")
                flash('Invalid username/email or password')
            else:
                # Username login attempt - find the user by exact username, case-insensitive
                app.logger.debug(f"Looking for exact username match: {login_input}")
                
                desired_username = login_input.lower()
                app.logger.debug(f"Normalized input username to lowercase: {desired_username}")
                
                # Find direct matches
                all_users = User.query.all()
                for user in all_users:
                    db_username = user.username.lower() if user.username else ""
                    app.logger.debug(f"Comparing DB username: '{db_username}' with input: '{desired_username}'")
                    if db_username == desired_username:
                        app.logger.info(f"Found exact username match for {user.username}")
                        
                        # Verify password
                        password = form.password.data
                        password_correct = user.check_password(password)
                        app.logger.debug(f"Password check result: {password_correct}")
                        
                        if password_correct:
                            # Login successful
                            app.logger.info(f"User {user.username} ({user.email}) logged in successfully")
                            login_user(user, remember=form.remember_me.data)
                            next_page = request.args.get('next')
                            app.logger.debug(f"Session after login: {session}")
                            app.logger.debug(f"Redirecting to: {next_page if next_page else 'tickets.tickets_dashboard'}")
                            return redirect(next_page if next_page else url_for('tickets.tickets_dashboard'))
                        else:
                            app.logger.warning(f"Password incorrect for user: {user.username}")
                            flash('Invalid username/email or password')
                            return render_template('login.html', form=form)
                
                # If we get here, no username match was found
                app.logger.warning(f"No matching username found for: {desired_username}")
                flash('Invalid username/email or password')
                
        except Exception as e:
            app.logger.error(f"Error during login: {str(e)}")
            app.logger.exception("Exception details:")
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
