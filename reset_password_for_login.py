"""
Script to reset the password for a user with case-insensitive email matching.
This ensures consistent password hashing across all user accounts.
"""

from app import app, db
from models import User
from werkzeug.security import generate_password_hash
from sqlalchemy import func
import sys

def reset_password(email, new_password):
    """
    Reset the password for a user with the given email.
    This uses case-insensitive email matching to find the user.
    """
    with app.app_context():
        # Case insensitive lookup
        user = User.query.filter(func.lower(User.email) == func.lower(email)).first()
        
        if not user:
            print(f"No user found with email: {email}")
            print("Available users:")
            users = User.query.all()
            for i, u in enumerate(users, 1):
                print(f"  {i}. ID={u.id}, username={u.username}, email={u.email}")
            return False
        
        print(f"Found user: ID={user.id}, username={user.username}, email={user.email}")
        
        # Reset the password
        user.password_hash = generate_password_hash(new_password)
        
        # Save to database
        db.session.commit()
        
        print(f"Password has been reset for {user.username} ({user.email})")
        return True

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python reset_password_for_login.py <email> <new_password>")
        sys.exit(1)
        
    email = sys.argv[1]
    password = sys.argv[2]
    
    print(f"Attempting to reset password for: {email}")
    success = reset_password(email, password)
    
    if success:
        print("Password reset successfully.")
    else:
        print("Password reset failed.")