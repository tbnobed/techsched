"""
Script to test direct login by email (case insensitive)
"""

from app import app, db
from models import User

def direct_login(email, password):
    """Test if the user can log in with the given email and password"""
    from sqlalchemy import func
    
    with app.app_context():
        print(f"Testing login with email: '{email}' and password")
        
        # First, check for exact match
        user = User.query.filter(User.email == email).first()
        if user:
            print(f"Found exact email match: {user.id}, {user.username}, {user.email}")
            if user.check_password(password):
                print("✅ Password is correct! Login would succeed with exact match.")
            else:
                print("❌ Password is incorrect. Login would fail.")
            # We continue to test the case-insensitive method too
        
        # Test the SQLAlchemy func.lower method (this is what we're using in the login function)
        case_insensitive_user = User.query.filter(func.lower(User.email) == func.lower(email)).first()
        if case_insensitive_user:
            print(f"\nFound using SQLAlchemy func.lower: {case_insensitive_user.id}, {case_insensitive_user.username}, {case_insensitive_user.email}")
            if case_insensitive_user.check_password(password):
                print("✅ Password is correct! Login would succeed with case-insensitive match.")
            else:
                print("❌ Password is incorrect. Login would fail.")
            # We continue to show all methods
        
        # For completeness, also check Python-based case-insensitive match
        lower_email = email.lower()
        all_users = User.query.all()
        
        print("\nScanning all users for case-insensitive match using Python...")
        for u in all_users:
            if u.email.lower() == lower_email:
                print(f"Found case-insensitive match with Python: {u.id}, {u.username}, {u.email}")
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
    
    # Add a SQL Alchemy-based test to confirm the fix
    print("\n" + "-" * 50 + "\n")
    print("TESTING SQLAlchemy SOLUTION\n")
    
    from sqlalchemy import func
    
    with app.app_context():
        email_to_check = "osandoval@tbn.tv"
        print(f"Testing SQLAlchemy func.lower for: '{email_to_check}'")
        
        user = User.query.filter(func.lower(User.email) == func.lower(email_to_check)).first()
        
        if user:
            print(f"✅ SUCCESS! Found user with case-insensitive query:")
            print(f"   ID: {user.id}, Username: {user.username}, Email: {user.email}")
            if user.check_password("PlexEngineering2024"):
                print("✅ Password check passed!")
            else:
                print("❌ Password check failed!")
        else:
            print(f"❌ No user found with case-insensitive lookup.")
            
        # Check with different case variation
        email_to_check = "oSaNdOvAl@tBn.Tv"
        print(f"\nTesting mixed case variation: '{email_to_check}'")
        
        user = User.query.filter(func.lower(User.email) == func.lower(email_to_check)).first()
        
        if user:
            print(f"✅ SUCCESS! Found user with mixed case query:")
            print(f"   ID: {user.id}, Username: {user.username}, Email: {user.email}")
        else:
            print(f"❌ No user found with mixed case lookup.")