"""
Script to list all users in the database
"""

from app import app, db
from models import User

def list_users():
    """List all users in the database"""
    with app.app_context():
        print("All users in database:")
        print("-" * 60)
        print(f"{'ID':<4} {'Username':<15} {'Email':<25} {'Admin':<5}")
        print("-" * 60)
        
        for user in User.query.all():
            print(f"{user.id:<4} {user.username:<15} {user.email:<25} {user.is_admin}")
        
        print("\nLooking for email variations of 'osandoval@tbn.tv':")
        
        # Check if we have both upper and lowercase versions
        for user in User.query.all():
            if 'sandoval' in user.email.lower():
                print(f"Found: {user.id}, {user.username}, {user.email}")
        
if __name__ == "__main__":
    list_users()