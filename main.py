import os
import logging
from app import app

if __name__ == "__main__":
    # Check for important environment variables
    if not os.environ.get('SENDGRID_API_KEY'):
        app.logger.warning("SENDGRID_API_KEY is not set. Email notifications will not be sent.")
    
    app.run(host="0.0.0.0", port=5000, debug=True)