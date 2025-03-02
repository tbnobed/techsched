from app import app, db
from models import User

def create_admin():
    with app.app_context():
        admin = User(
            username='admin',
            email='admin@techscheduler.com',
            is_admin=True,
            color='#FF0000'
        )
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()

if __name__ == '__main__':
    create_admin()
