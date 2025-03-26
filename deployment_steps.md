# Deployment Guide for Technician Scheduler

## Prerequisites

### 1. Install Docker and Docker Compose

#### For Ubuntu/Debian:
```bash
# Update package index
sudo apt-get update

# Install required packages
sudo apt-get install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# Add Docker's official GPG key
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Set up stable repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker Engine
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Add your user to docker group (requires logout/login to take effect)
sudo usermod -aG docker $USER

# Verify installations
docker --version
docker-compose --version
```

#### For CentOS/RHEL:
```bash
# Install required packages
sudo yum install -y yum-utils

# Add Docker repository
sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo

# Install Docker Engine
sudo yum install -y docker-ce docker-ce-cli containerd.io

# Start and enable Docker
sudo systemctl start docker
sudo systemctl enable docker

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### 2. Configure SendGrid

1. Verify Domain in SendGrid:
   - Log in to SendGrid dashboard
   - Go to Settings > Sender Authentication
   - Click on "Authenticate Your Domain"
   - Follow the DNS configuration steps for your domain
   - Add DNS records for DKIM authentication
   - Wait for verification (can take up to 48 hours)

2. Verify Sender Email:
   - Ensure alerts@obedtv.com is verified in SendGrid
   - Follow SendGrid's sender verification process
   - Test email sending functionality


### 3. Database Management

#### Regular Backups:
```bash
# Create backup script (save as backup.sh)
#!/bin/bash
BACKUP_DIR="/var/lib/technician-scheduler/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/backup_$TIMESTAMP.sql"

# Create backup
docker-compose exec -T db pg_dump -U $POSTGRES_USER $POSTGRES_DB > $BACKUP_FILE

# Compress backup
gzip $BACKUP_FILE

# Remove backups older than 30 days
find $BACKUP_DIR -name "backup_*.sql.gz" -mtime +30 -delete
```

#### Setup automated backups:
```bash
# Make backup script executable
chmod +x backup.sh

# Add to crontab (run daily at 2 AM)
echo "0 2 * * * /path/to/backup.sh" | sudo tee -a /etc/crontab
```

### 4. Production Deployment Steps

1. Clone repository and set up environment:
```bash
# Create deployment directory
mkdir -p /opt/technician-scheduler
cd /opt/technician-scheduler

# Copy project files
cp -r /path/to/project/* .

# Create and configure .env file
cp .env.example .env

# Generate secure secret key
echo "FLASK_SECRET_KEY=$(openssl rand -hex 32)" >> .env

# Configure database credentials
nano .env  # Set secure database password and other configurations
```

2. Start services:
```bash
# Build and start containers
docker-compose up -d

# Verify services are running
docker-compose ps

# Check logs
docker-compose logs -f
```

3. Monitor and maintenance:
```bash
# Monitor container health
docker-compose ps

# View logs
docker-compose logs -f

# Check database connections
docker-compose exec db psql -U $POSTGRES_USER -d $POSTGRES_DB -c 'SELECT count(*) FROM pg_stat_activity;'
```

### Security Best Practices

1. Network Security:
   - Use UFW or similar firewall to restrict access
   - Only expose necessary ports (5000 for web app)
   - Set up SSL/TLS for secure communication

2. Database Security:
   - Use strong passwords
   - Regular security updates
   - Implement connection pooling
   - Regular backup verification

3. Application Security:
   - Keep dependencies updated
   - Regular security audits
   - Monitor application logs
   - Implement rate limiting

### Troubleshooting

1. Email Issues:
```bash
# Check SendGrid logs
docker-compose logs web | grep "SendGrid"

# Verify SendGrid API key
docker-compose exec web python -c "import os; print(bool(os.environ.get('SENDGRID_API_KEY')))"
```

2. Database Issues:
```bash
# Check database logs
docker-compose logs db

# Verify database connectivity
docker-compose exec web python -c "from app import db; print(db.engine.connect())"
```

3. Common Problems:

- If emails aren't sending:
  - Verify SendGrid API key is set correctly
  - Check domain verification status
  - Review email sending logs

- If database connections fail:
  - Check PostgreSQL logs
  - Verify database credentials
  - Check network connectivity

- If application crashes:
  - Review application logs
  - Check memory usage
  - Verify environment variables