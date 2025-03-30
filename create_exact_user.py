"""
Script to create a user with the exact email that matches the login attempt
"""

from app import app, db
from models import User
from werkzeug.security import generate_password_hash

def create_user(username, email, password, is_admin=False):
    """Create a new user with the exact username, email, and password"""
    with app.app_context():
        # Check if user with this email already exists
        existing_user = None
        for u in User.query.all():
            if u.email.lower() == email.lower():
                existing_user = u
                break
        
        if existing_user:
            print(f"User already exists with ID {existing_user.id}: {existing_user.username}, {existing_user.email}")
            print(f"Updating this user to have exact email: {email}")
            existing_user.email = email  # Update email to match exactly what's being entered
            db.session.commit()
            print(f"Updated user email. New user info: {existing_user.username}, {existing_user.email}")
            return existing_user
        
        # Create new user if doesn't exist
        print(f"Creating new user: {username}, {email}")
        new_user = User(
            username=username,
            email=email,
            is_admin=is_admin
        )
        new_user.set_password(password)
        
        db.session.add(new_user)
        db.session.commit()
        
        print(f"Created new user with ID {new_user.id}: {new_user.username}, {new_user.email}")
        return new_user

if __name__ == "__main__":
    # Create EXACT case match for capitalized email
    user = create_user(
        username="Obed S",
        email="OSandoval@tbn.tv",  # Exact email with capitalization as entered
        password="PlexEngineering2024",
        is_admin=True
    )