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

### 2. Install Git

#### For Ubuntu/Debian:
```bash
sudo apt-get update
sudo apt-get install -y git

# Verify installation
git --version
```

#### For CentOS/RHEL:
```bash
sudo yum install -y git

# Verify installation
git --version
```

### 3. Install PostgreSQL Client

#### For Ubuntu/Debian:
```bash
# Add PostgreSQL repository
sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -

# Update package list
sudo apt-get update

# Install PostgreSQL client
sudo apt-get install -y postgresql-client-15

# Verify installation
psql --version
```

#### For CentOS/RHEL:
```bash
# Install PostgreSQL repository
sudo yum install -y https://download.postgresql.org/pub/repos/yum/reporpms/EL-8-x86_64/pgdg-redhat-repo-latest.noarch.rpm

# Install PostgreSQL client
sudo yum install -y postgresql15

# Verify installation
psql --version
```

## Deployment Steps

### Step 1: Project Setup
1. Create deployment directory:
```bash
mkdir technician-scheduler
cd technician-scheduler
```

2. Clone the repository or copy project files:
```bash
# If using git:
git clone <repository-url> .

# If copying files manually, ensure you have:
# - Dockerfile
# - docker-compose.yml
# - All Python files
# - templates/ directory
# - static/ directory
```

### Step 2: Configuration
1. Create and configure .env file:
```bash
# Copy example file
cp .env.example .env

# Generate secure secret key
echo "FLASK_SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_hex(32))')" >> .env

# Edit .env file with your values
cat << EOF >> .env
# Database Configuration
POSTGRES_USER=your_db_user
POSTGRES_PASSWORD=your_secure_password
POSTGRES_DB=technician_scheduler
POSTGRES_HOST=db
POSTGRES_PORT=5432

# Flask Configuration
FLASK_ENV=production

# Database URL
DATABASE_URL=postgresql://\${POSTGRES_USER}:\${POSTGRES_PASSWORD}@\${POSTGRES_HOST}:\${POSTGRES_PORT}/\${POSTGRES_DB}
EOF
```

### Step 3: Database Setup
1. Create required directories:
```bash
mkdir -p static/backups
chmod -R 777 static/backups
```

2. Start PostgreSQL container:
```bash
docker-compose up -d db

# Wait for database to be ready
docker-compose logs -f db
# Wait until you see "database system is ready to accept connections"
```

3. Initialize the database schema:
```bash
# Connect to the database container
docker-compose exec db psql -U $POSTGRES_USER -d $POSTGRES_DB

# Inside psql, run the update_database.sql commands
\i update_database.sql

# Exit psql
\q
```

### Step 4: Application Deployment
1. Build and start services:
```bash
# Build containers
docker-compose build

# Start all services
docker-compose up -d

# Verify containers are running
docker-compose ps

# Check logs
docker-compose logs -f web
```

### Step 5: Create Admin User
1. Create the first admin user:
```bash
docker-compose exec web python create_admin.py
```

### Step 6: Initial Backup
1. Create initial backup directory:
```bash
mkdir -p /var/lib/technician-scheduler/backups
chown -R 1000:1000 /var/lib/technician-scheduler/backups
```

### Step 7: Verify Deployment
1. Access the application:
   - Open http://your-server-ip:5000 in a web browser
   - Log in with admin credentials
   - Verify calendar functionality
   - Test backup/restore feature

2. Monitor the logs:
```bash
docker-compose logs -f
```

## Maintenance Commands

### Service Management
```bash
# Restart services
docker-compose restart

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Start services
docker-compose up -d
```

### Backup Operations
```bash
# Manual database backup
docker-compose exec db pg_dump -U $POSTGRES_USER $POSTGRES_DB > backup.sql

# Restore from backup
docker-compose exec db psql -U $POSTGRES_USER $POSTGRES_DB < backup.sql
```

### Updates
```bash
# Pull new changes
git pull

# Rebuild and restart
docker-compose down
docker-compose build
docker-compose up -d
```

## Troubleshooting

### Common Issues
1. If containers won't start:
```bash
# Check logs
docker-compose logs

# Verify environment variables
docker-compose config

# Check disk space
df -h
```

2. Database connection issues:
```bash
# Check database container
docker-compose ps db

# View database logs
docker-compose logs db

# Verify DATABASE_URL in .env
cat .env | grep DATABASE_URL
```

3. Permission issues:
```bash
# Fix backup directory permissions
sudo chown -R 1000:1000 /var/lib/technician-scheduler/backups
sudo chmod -R 755 /var/lib/technician-scheduler/backups
```

### Monitoring
```bash
# Check container health
docker-compose ps

# Monitor resource usage
docker stats

# Check database connections
docker-compose exec db psql -U $POSTGRES_USER -d $POSTGRES_DB -c 'SELECT count(*) FROM pg_stat_activity;'