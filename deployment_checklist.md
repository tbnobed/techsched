# Deployment Checklist

# Complete Deployment Files Structure

## Required Files and Structure:
```
your-project-directory/
├── app.py                 # Flask application configuration
├── main.py               # Application entry point
├── models.py             # Database models
├── routes.py             # Application routes
├── forms.py              # Form definitions
├── .env                  # Environment variables (DO NOT COMMIT)
├── Dockerfile            # Container configuration
├── docker-compose.yml    # Container orchestration
├── pyproject.toml        # Python dependencies
├── static/               # Static files directory
│   ├── css/
│   │   └── style.css    # Custom styles
│   └── js/
│       └── calendar.js   # Calendar functionality
└── templates/            # Template files directory
    ├── base.html        # Base template
    ├── calendar.html    # Calendar view
    ├── login.html       # Login page
    ├── profile.html     # User profile
    ├── register.html    # Registration page
    └── admin/
        └── dashboard.html  # Admin dashboard
```

## Required Environment Variables (.env):
```env
# Database Configuration
POSTGRES_USER=your_database_username
POSTGRES_PASSWORD=your_secure_password
POSTGRES_DB=technician_scheduler
POSTGRES_HOST=db
POSTGRES_PORT=5432

# Flask Configuration
FLASK_SECRET_KEY=your_secure_secret_key
FLASK_ENV=production

# Database URL (constructed from above variables)
DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}
```

## Important Notes:
1. Generate a secure FLASK_SECRET_KEY using Python:
   ```python
   import secrets
   print(secrets.token_hex(32))
   ```

2. Use strong, unique passwords for database credentials

3. Never commit the .env file to version control

4. Ensure all template files maintain proper Jinja2 syntax

5. The static directory must contain all CSS and JavaScript files

6. All Python files must use proper imports and follow the project structure


## Deployment Steps
1. Create a new directory for your application
2. Copy all files maintaining the directory structure above
3. Create .env file with secure credentials
4. Build and start containers:
   ```bash
   docker-compose up -d
   ```

## Security Best Practices:
1. Keep all credentials in .env file
2. Use strong passwords for database
3. Generate a secure random key for FLASK_SECRET_KEY
4. Keep Docker and dependencies updated
5. Regularly backup database data
6. Monitor container logs for issues