"""
Script to ensure we have both format users in the database (uppercase and lowercase)
"""

from app import app, db
from models import User
from werkzeug.security import generate_password_hash

def ensure_both_formats(email, password):
    """Ensure we have both lowercase and uppercase version of an email in the database"""
    with app.app_context():
        # Get uppercase and lowercase versions of the email
        upper_email = email
        lower_email = email.lower()
        
        print(f"Checking for users with email variations of {email}")
        
        # Find users with either version
        upper_user = None
        lower_user = None
        
        for u in User.query.all():
            if u.email == upper_email:
                upper_user = u
            elif u.email == lower_email:
                lower_user = u
        
        # Report what we found
        if upper_user:
            print(f"Found uppercase user: {upper_user.id}, {upper_user.username}, {upper_user.email}")
        if lower_user:
            print(f"Found lowercase user: {lower_user.id}, {lower_user.username}, {lower_user.email}")
        
        if not upper_user and not lower_user:
            print(f"No users found with email {email} in either case variant")
            return
        
        if upper_user and lower_user:
            print(f"Both uppercase and lowercase users exist. No action needed.")
            return
        
        # If we only have one version, create the other
        if upper_user and not lower_user:
            print(f"Creating lowercase email twin...")
            # Create lowercase user with a slightly different username
            new_user = User(
                username=f"{upper_user.username}_lowercase",
                email=lower_email,
                is_admin=upper_user.is_admin,
                color=upper_user.color,
                timezone=upper_user.timezone
            )
            new_user.password_hash = upper_user.password_hash  # Direct copy of password hash
            db.session.add(new_user)
            db.session.commit()
            print(f"Created lowercase twin: {new_user.id}, {new_user.username}, {new_user.email}")
            
        elif lower_user and not upper_user:
            print(f"Creating uppercase email twin...")
            # Create uppercase user with a slightly different username
            new_user = User(
                username=f"{lower_user.username}_uppercase",
                email=upper_email,
                is_admin=lower_user.is_admin,
                color=lower_user.color,
                timezone=lower_user.timezone
            )
            new_user.password_hash = lower_user.password_hash  # Direct copy of password hash
            db.session.add(new_user)
            db.session.commit()
            print(f"Created uppercase twin: {new_user.id}, {new_user.username}, {new_user.email}")

if __name__ == "__main__":
    # Ensure we have both uppercase and lowercase versions
    ensure_both_formats("OSandoval@tbn.tv", "PlexEngineering2024")