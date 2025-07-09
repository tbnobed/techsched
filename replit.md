# Plex Engineering Technician Scheduler

## Overview

This is a comprehensive web application for managing technician schedules and tickets, built with Flask and PostgreSQL. The system provides calendar-based scheduling, ticket management, and user administration with both desktop and mobile-responsive interfaces.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Backend Architecture
- **Framework**: Flask 3.1.0+ with Python 3.11
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Authentication**: Flask-Login for session management
- **Security**: Flask-WTF for CSRF protection
- **Email**: SendGrid API for notifications

### Frontend Architecture
- **UI Framework**: Bootstrap 5.1.3 for responsive design
- **Icons**: Feather Icons for consistent iconography
- **Mobile Support**: Responsive design with dedicated mobile templates
- **Theme System**: Light/dark theme toggle with user preferences

### Data Storage
- **Primary Database**: PostgreSQL with connection pooling
- **Models**: User, Schedule, Ticket, Location, QuickLink, and related entities
- **Backup System**: Automated database backups with JSON exports

## Key Components

### Authentication System
- Case-insensitive email login
- Session management with remember-me functionality
- Admin role-based access control
- Password hashing with Werkzeug security

### Calendar & Scheduling
- Weekly calendar view with timezone support
- Technician schedule management
- Location-based filtering
- Time-off tracking
- Overlap detection and validation

### Ticket Management
- Complete ticket lifecycle (open, in-progress, pending, resolved, closed)
- Priority system (low, medium, high, urgent)
- Category-based organization
- Comment system with history tracking
- Assignment and notification system
- Archive functionality for old tickets

### User Management
- Profile management with timezone preferences
- Theme selection (light/dark)
- Color-coded user identification
- Admin user management interface

### Email Notifications
- Ticket assignment notifications
- Status change alerts
- Comment notifications
- Schedule change notifications

### Mobile Support
- Responsive design for all screen sizes
- Mobile-optimized templates
- Touch-friendly navigation
- Day-by-day calendar view on mobile

## Data Flow

1. **User Authentication**: Login → Session Creation → Role-based Access
2. **Schedule Management**: Form Input → Validation → Database Storage → Email Notifications
3. **Ticket Workflow**: Creation → Assignment → Status Updates → History Tracking → Notifications
4. **Real-time Updates**: AJAX endpoints for active users and system status

## External Dependencies

### Email Service
- **SendGrid**: For all email notifications
- **Configuration**: API key required in environment variables
- **Domain**: Configurable email domain for link generation

### Frontend Libraries
- **Bootstrap**: UI framework and responsive grid
- **Feather Icons**: Scalable icon system
- **jQuery**: DOM manipulation and AJAX requests

### Development Tools
- **Flask-WTF**: Form handling and CSRF protection
- **SQLAlchemy**: Database ORM with migration support
- **pytz**: Timezone handling and conversion

## Deployment Strategy

### Container-based Deployment
- **Docker**: Multi-stage build with Python 3.11-slim base
- **Docker Compose**: PostgreSQL + Flask application stack
- **Health Checks**: Built-in health endpoint for monitoring
- **Volumes**: Persistent storage for database and backups

### Production Configuration
- **Environment Variables**: All sensitive configuration externalized
- **Database**: PostgreSQL with connection pooling
- **Static Files**: Served through Flask with CDN-ready setup
- **Backup Strategy**: Automated database dumps and application data exports

### Database Management
- **Schema Updates**: Automated migration scripts
- **Backup/Restore**: Complete system backup with JSON exports
- **Data Integrity**: Foreign key constraints and validation

### Security Considerations
- **CSRF Protection**: All forms protected with tokens
- **Session Security**: Secure session management
- **Input Validation**: Server-side validation for all inputs
- **SQL Injection Prevention**: Parameterized queries throughout

The application follows a modular architecture with clear separation of concerns, making it maintainable and scalable for team scheduling needs.