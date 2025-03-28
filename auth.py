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
    
    form = LoginForm()
    if form.validate_on_submit():
        # Make email lowercase for case-insensitive login
        email = form.email.data.lower() if form.email.data else ""
        
        # Check if this is a username or email login
        if '@' in email:
            # Login with email
            user = User.query.filter_by(email=email).first()
        else:
            # Case-insensitive username search using SQL LOWER function
            user = User.query.filter(db.func.lower(User.username) == db.func.lower(form.email.data)).first()
        
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            next_page = request.args.get('next')
            return redirect(next_page if next_page else url_for('tickets.tickets_dashboard'))
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
