"""
Script to test direct login by email (case insensitive)
"""

from app import app, db
from models import User

def direct_login(email, password):
    """Test if the user can log in with the given email and password"""
    with app.app_context():
        print(f"Testing login with email: '{email}' and password")
        
        # First, check for exact match
        user = User.query.filter(User.email == email).first()
        if user:
            print(f"Found exact email match: {user.id}, {user.username}, {user.email}")
            if user.check_password(password):
                print("✅ Password is correct! Login would succeed.")
            else:
                print("❌ Password is incorrect. Login would fail.")
            return
        
        # Then, check for case-insensitive match
        lower_email = email.lower()
        all_users = User.query.all()
        
        print("\nScanning all users for case-insensitive match...")
        for u in all_users:
            if u.email.lower() == lower_email:
                print(f"Found case-insensitive match: {u.id}, {u.username}, {u.email}")
                if u.check_password(password):
                    print("✅ Password is correct! Login would succeed.")
                else:
                    print("❌ Password is incorrect. Login would fail.")
                return
        
        # No user found
        print(f"❌ No user found with email: {email} (case-insensitive)")
        print("\nAll users in database:")
        for i, u in enumerate(User.query.all(), 1):
            print(f"{i}. ID: {u.id}, {u.username}, {u.email}")

if __name__ == "__main__":
    # Test login with both uppercase and lowercase versions
    direct_login("OSandoval@tbn.tv", "PlexEngineering2024")
    print("\n" + "-" * 50 + "\n")
    direct_login("osandoval@tbn.tv", "PlexEngineering2024")