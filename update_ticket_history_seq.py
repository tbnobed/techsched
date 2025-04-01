"""
Update the ticket_history table to use a new sequence starting from 1000.
This script creates a new sequence and sets the default value of the id column.
"""
import os
from sqlalchemy import text
from app import app, db

def update_ticket_history_sequence():
    """Update the ticket_history ID sequence to start from 1000"""
    with app.app_context():
        # Get the database URL from environment or app config
        db_url = os.environ.get("DATABASE_URL") or app.config.get("SQLALCHEMY_DATABASE_URI")
        
        if not db_url:
            print("Error: Database URL not found in environment or app config")
            return False
        
        try:
            print("Starting ticket history sequence update")
            
            # First, we find the current max ID value to make sure our new sequence starts higher
            result = db.session.execute(text("SELECT MAX(id) FROM ticket_history")).scalar()
            max_id = result or 0
            print(f"Current maximum ticket_history ID: {max_id}")
            
            # Create a sequence that starts higher than the max ID
            start_value = max(1000, max_id + 100)
            print(f"Setting new sequence to start from: {start_value}")
            
            # Create a new sequence
            db.session.execute(text(f"CREATE SEQUENCE IF NOT EXISTS ticket_history_id_seq START WITH {start_value}"))
            
            # Set the column default to use the new sequence
            db.session.execute(text("ALTER TABLE ticket_history ALTER COLUMN id SET DEFAULT nextval('ticket_history_id_seq')"))
            
            # Set the sequence as owned by the column to ensure it's dropped if the column is dropped
            db.session.execute(text("ALTER SEQUENCE ticket_history_id_seq OWNED BY ticket_history.id"))
            
            # Commit changes
            db.session.commit()
            
            print("Successfully updated ticket_history sequence")
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"Error updating ticket_history sequence: {str(e)}")
            import traceback
            print(f"Exception traceback: {traceback.format_exc()}")
            return False

if __name__ == "__main__":
    success = update_ticket_history_sequence()
    if success:
        print("✅ Ticket history sequence updated successfully")
    else:
        print("❌ Failed to update ticket history sequence")