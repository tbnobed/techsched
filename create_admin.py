from app import app, db
from models import User
import pytz

def create_admin():
    with app.app_context():
        # Check if admin already exists by username
        existing_admin_username = User.query.filter_by(username='admin').first()
        if existing_admin_username:
            print(f"Admin user with username 'admin' already exists.")
            
            # Update the existing admin account
            existing_admin_username.email = 'admin@obedtv.com'
            existing_admin_username.is_admin = True
            existing_admin_username.set_password('TBN@dmin!!')
            existing_admin_username.color = '#3498db'
            existing_admin_username.timezone = 'America/Chicago'
            existing_admin_username.theme_preference = 'dark'
            db.session.commit()
            print("Admin account updated successfully.")
            return
            
        # Check if admin already exists by email
        existing_admin_email = User.query.filter_by(email='admin@obedtv.com').first()
        if existing_admin_email:
            print(f"Admin user with email 'admin@obedtv.com' already exists.")
            
            # Update the existing admin account
            existing_admin_email.username = 'admin'
            existing_admin_email.is_admin = True
            existing_admin_email.set_password('TBN@dmin!!')
            existing_admin_email.color = '#3498db'
            existing_admin_email.timezone = 'America/Chicago'
            existing_admin_email.theme_preference = 'dark'
            db.session.commit()
            print("Admin account updated successfully.")
            return

        # Create new admin user
        admin = User(
            username='admin',
            email='admin@obedtv.com',
            is_admin=True,
            color='#3498db',  # Blue color
            timezone='America/Chicago',  # Default timezone
            theme_preference='dark'  # Default theme
        )
        admin.set_password('TBN@dmin!!')
        db.session.add(admin)
        db.session.commit()
        print(f"Admin user created successfully:")
        print(f"Username: admin")
        print(f"Email: admin@obedtv.com")
        print(f"Password: TBN@dmin!!")

if __name__ == '__main__':
    create_admin()
