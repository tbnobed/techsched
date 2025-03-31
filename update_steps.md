# Update Guide for Plex Technician Scheduler

This document provides a step-by-step guide for updating your existing Plex Technician Scheduler installation on Ubuntu with the latest changes.

## Update Steps (Version 1.2.2)

1. **Backup your current installation and database**

```bash
# Navigate to your installation directory
cd /opt/technician-scheduler

# Run backup script
./backup.sh

# Verify the backup was created
ls -l /var/lib/technician-scheduler/backups
```

2. **Pull the latest code**

```bash
# If using Git
cd /opt/technician-scheduler
git pull

# OR, if you're transferring files manually
# First, on your local machine
cd /path/to/local/project
zip -r technician-scheduler.zip *

# Transfer the zip file to your server
scp technician-scheduler.zip user@your-server:/tmp

# Then, on your server
cd /opt/technician-scheduler
unzip /tmp/technician-scheduler.zip -d /tmp/update
cp -r /tmp/update/* .
rm -rf /tmp/update
rm /tmp/technician-scheduler.zip
```

3. **Update database schema (if needed)**

```bash
cd /opt/technician-scheduler
./update_database.sh
```

4. **Restart the application**

```bash
cd /opt/technician-scheduler
docker-compose down
docker-compose up -d --build
```

5. **Verify the application is running properly**

```bash
# Check container status
docker-compose ps

# Check logs for any errors
docker-compose logs -f

# Test the health endpoint
curl http://localhost:5000/health
```

## What's New in Version 1.2.2 (March 31, 2025)

### New Features and Improvements
- **Added favicon and Apple touch icon support**: Implemented browser tab icon support for both desktop and mobile devices.
- **Improved browser compatibility**: Added support for iOS and mobile browser icon requests.

### Bug Fixes
- Fixed 404 errors for favicon.ico and Apple touch icon requests.
- Fixed mobile browser tab icon display issues.

## Troubleshooting

### If the browser tab icon is not displaying correctly:

1. **Clear browser cache**
   - On Chrome: Press Ctrl+Shift+Delete, select "Cached images and files", and click "Clear data"
   - On Firefox: Press Ctrl+Shift+Delete, select "Cache", and click "Clear Now"
   - On Safari: Press Command+Option+E

2. **Verify the image file exists**
   ```bash
   docker-compose exec web ls -l /app/static/images/plex_logo_small.png
   ```

3. **Check logs for any 404 errors related to favicon or Apple touch icon**
   ```bash
   docker-compose logs web | grep -E "favicon|apple-touch-icon"
   ```

4. **Manual fix if icon routes are missing**
   
   If you see errors and the routes are missing, you can manually edit the app.py file:
   
   ```bash
   # Edit app.py file
   nano app.py
   ```
   
   Add these routes before the `with app.app_context():` line:
   
   ```python
   # Favicon and Apple Touch Icon routes
   @app.route('/favicon.ico')
   def favicon():
       return redirect(url_for('static', filename='images/plex_logo_small.png'))
   
   @app.route('/apple-touch-icon.png')
   @app.route('/apple-touch-icon-precomposed.png')
   @app.route('/apple-touch-icon-120x120.png')
   @app.route('/apple-touch-icon-120x120-precomposed.png')
   def apple_touch_icon():
       return redirect(url_for('static', filename='images/plex_logo_small.png'))
   ```
   
   Then restart the application:
   
   ```bash
   docker-compose restart web
   ```

For additional help with deployment or troubleshooting, refer to the full deployment guide in `deployment_steps.md`.