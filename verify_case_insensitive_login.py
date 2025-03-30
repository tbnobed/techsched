"""
Script to directly verify case-insensitive login without going through the web interface.
This bypasses the form validation and CSRF protection to directly test the authentication logic.
"""

from app import app, db
from models import User
from sqlalchemy import func
from werkzeug.security import check_password_hash
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_login(email, password):
    """Test login with the given email and password"""
    logger.info(f"Testing login with email: '{email}' and password: '{password}'")
    
    with app.app_context():
        # First, check exact match
        user = User.query.filter(User.email == email).first()
        if user:
            logger.info(f"Found exact email match: {user.id}, {user.username}, {user.email}")
            password_match = user.check_password(password)
            if password_match:
                logger.info("✅ Password matches with exact lookup!")
            else:
                logger.error("❌ Password does NOT match with exact lookup!")
                logger.debug(f"User password_hash: {user.password_hash[:20]}...")
        else:
            logger.info(f"No exact match found for email: {email}")
        
        # Next, check with case-insensitive query
        case_insensitive_user = User.query.filter(func.lower(User.email) == func.lower(email)).first()
        if case_insensitive_user:
            logger.info(f"Found case-insensitive match: {case_insensitive_user.id}, {case_insensitive_user.username}, {case_insensitive_user.email}")
            
            # Try with simplified direct hash check (bypassing the check_password method)
            raw_check = check_password_hash(case_insensitive_user.password_hash, password)
            logger.info(f"Direct hash check result: {raw_check}")
            
            # Also try with the check_password method
            password_match = case_insensitive_user.check_password(password)
            if password_match:
                logger.info("✅ Password matches with case-insensitive lookup!")
            else:
                logger.error("❌ Password does NOT match with case-insensitive lookup!")
                logger.debug(f"User password_hash: {case_insensitive_user.password_hash[:20]}...")
        else:
            logger.info(f"No case-insensitive match found for email: {email}")
        
        # Give specific advice based on test results
        if not user and not case_insensitive_user:
            logger.error("❌ TEST FAILED: No user found with this email (exact or case-insensitive)")
            logger.info("Similar users in the database:")
            all_users = User.query.all()
            for i, u in enumerate(all_users, 1):
                logger.info(f"  {i}. ID={u.id}, username={u.username}, email={u.email}")
        elif user and not user.check_password(password):
            logger.error("❌ TEST FAILED: User found but password doesn't match")
            logger.info("You may need to reset the password for this user")

if __name__ == "__main__":
    # Test with uppercase first letter
    test_login("Osandoval@tbn.tv", "PlexEngineering2024")
    print("\n" + "-"*50 + "\n")
    
    # Test with all lowercase
    test_login("osandoval@tbn.tv", "PlexEngineering2024")
    print("\n" + "-"*50 + "\n")
    
    # Test with mixed case
    test_login("OsAnDoVaL@tbn.tv", "PlexEngineering2024")
    print("\n" + "-"*50 + "\n")
    
    # Test with all uppercase
    test_login("OSANDOVAL@TBN.TV", "PlexEngineering2024")