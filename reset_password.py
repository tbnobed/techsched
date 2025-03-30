"""
Script to reset a specific user's password
"""

from app import app, db
from models import User
from werkzeug.security import generate_password_hash

def reset_password(email, new_password):
    """Reset the password for a user by email"""
    with app.app_context():
        # Normalize email to lowercase
        email = email.lower()
        print(f"Looking for user with email: {email}")
        
        # Find user by email (case-insensitive)
        user = None
        for u in User.query.all():
            if u.email.lower() == email.lower():
                user = u
                break
        
        if not user:
            print(f"No user found with email: {email}")
            return False
        
        # Reset password
        print(f"Resetting password for user: {user.username} ({user.email})")
        user.password_hash = generate_password_hash(new_password)
        db.session.commit()
        
        print(f"Password reset successfully for {user.username}")
        print(f"New password hash: {user.password_hash[:20]}...")
        return True

if __name__ == "__main__":
    # Reset password for Obed S
    user_email = "osandoval@tbn.tv"
    new_password = "PlexEngineering2024"  # Using a secure default
    
    success = reset_password(user_email, new_password)
    if success:
        print(f"Password for {user_email} has been reset to: {new_password}")
        print("Please share this with the user and request they change it after logging in")
    else:
        print(f"Failed to reset password for {user_email}")