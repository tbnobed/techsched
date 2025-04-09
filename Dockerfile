# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirements first to leverage Docker cache
COPY pyproject.toml .

# Install Python packages from pyproject.toml dependencies
RUN pip install --no-cache-dir \
    email-validator>=2.2.0 \
    flask>=3.1.0 \
    flask-login>=0.6.3 \
    flask-sqlalchemy>=3.1.1 \
    flask-wtf>=1.2.2 \
    openpyxl>=3.1.5 \
    psycopg2-binary>=2.9.10 \
    python-dotenv>=1.0.1 \
    pytz>=2024.2 \
    sendgrid>=6.11.0 \
    sqlalchemy>=2.0.36 \
    werkzeug>=3.1.3 \
    wtforms>=3.2.1

# Copy application files
COPY . .

# Set environment variables
ENV FLASK_APP=app.py
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1

# Create required directories
RUN mkdir -p /app/static/uploads /app/static/backups

# Set permissions
RUN chmod -R 755 /app/static \
    && chmod -R 777 /app/static/backups  

# Create a non-root user
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 5000

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# No need to create health.py file as we've added it directly to the codebase

# No need to modify app.py as we've added the health blueprint directly to the code

# Add entrypoint script
COPY docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh

# Run the application with entrypoint
ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["python", "main.py"]