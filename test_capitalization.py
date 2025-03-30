"""
Script to test login with various capitalization patterns for the email
"""

from app import app, db
from models import User

def test_all_capitalizations(base_email, password):
    """Test login with various capitalization patterns"""
    with app.app_context():
        # Create different capitalization patterns
        username, domain = base_email.split('@')
        
        # Create variations
        variations = [
            base_email,                         # Original: OSandoval@tbn.tv
            base_email.lower(),                 # All lowercase: osandoval@tbn.tv
            base_email.upper(),                 # All uppercase: OSANDOVAL@TBN.TV
            username.capitalize() + '@' + domain, # First letter cap: Osandoval@tbn.tv
            username[0].lower() + username[1:] + '@' + domain, # First letter lowercase: oSandoval@tbn.tv
            ''.join([c.upper() if i % 2 == 0 else c.lower() for i, c in enumerate(username)]) + '@' + domain, # Alternating: OsAnDoVaL@tbn.tv
        ]
        
        print(f"Testing {len(variations)} capitalization patterns for {base_email}")
        print("-" * 50)
        
        # Test each variation
        for i, email in enumerate(variations, 1):
            print(f"\n{i}. Testing login with: '{email}'")
            
            # Scan all users to find a match
            found = False
            for u in User.query.all():
                if u.email.lower() == email.lower():
                    print(f"   Found matching user: {u.id}, {u.username}, {u.email}")
                    if u.check_password(password):
                        print("   ✅ Password is correct! Login would succeed.")
                    else:
                        print("   ❌ Password is incorrect. Login would fail.")
                    found = True
                    break
            
            # Report if no match found
            if not found:
                print(f"   ❌ No user found for: {email}")

if __name__ == "__main__":
    test_all_capitalizations("OSandoval@tbn.tv", "PlexEngineering2024")