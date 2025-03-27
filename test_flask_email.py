from app import app
from flask import url_for
import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content

def test_email_with_url():
    """Test email sending with Flask URL generation"""
    with app.app_context():
        print("Testing email with Flask URL generation...")
        
        # Check for API key
        api_key = os.environ.get('SENDGRID_API_KEY')
        if not api_key:
            print("ERROR: SendGrid API key is not set in environment variables")
            return
            
        # Generate a URL using Flask's url_for
        try:
            tickets_url = url_for('tickets.tickets_dashboard', _external=True)
            print(f"Generated URL: {tickets_url}")
        except Exception as e:
            print(f"Error generating URL: {str(e)}")
            return
            
        # Create message with the URL
        message = Mail(
            from_email='alerts@obedtv.com',
            to_emails='engsched-alerts@tbn.tv',
            subject='Flask URL Test Email',
            html_content=f'<p>This is a test email with a Flask URL: <a href="{tickets_url}">View Tickets</a></p>'
        )
        
        try:
            # Initialize SendGrid client
            sg = SendGridAPIClient(api_key)
            
            # Send message
            print("Sending email...")
            response = sg.send(message)
            
            # Check response
            if response.status_code == 202:
                print("SUCCESS: Email sent successfully!")
            else:
                print(f"ERROR: Failed to send email. Status code: {response.status_code}")
                
        except Exception as e:
            print(f"EXCEPTION: {str(e)}")
            
if __name__ == "__main__":
    test_email_with_url()