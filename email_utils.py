import os
import logging
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content
from typing import List, Optional
from models import Schedule, EmailSettings, Ticket, User, TicketComment
from flask import current_app, url_for

logger = logging.getLogger(__name__)

def get_email_settings() -> EmailSettings:
    """Get the current email settings or create default settings if none exist"""
    settings = EmailSettings.query.first()
    if not settings:
        settings = EmailSettings()
        current_app.db.session.add(settings)
        current_app.db.session.commit()
    return settings

def send_email(
    to_emails: List[str],
    subject: str,
    html_content: str,
    from_email: str = 'alerts@obedtv.com'
) -> bool:
    """
    Send an email using SendGrid
    Returns True if successful, False otherwise
    """
    current_app.logger.info(f"Attempting to send email to {to_emails} with subject: {subject}")
    
    try:
        api_key = os.environ.get('SENDGRID_API_KEY')
        if not api_key:
            current_app.logger.error("SendGrid API key is not set")
            return False
        
        # Log first few characters of API key to confirm it's available (safely)
        key_preview = api_key[:4] + '...' if len(api_key) > 4 else '***'
        current_app.logger.info(f"Using SendGrid API key starting with: {key_preview}")

        sg = SendGridAPIClient(api_key)
        message = Mail(
            from_email=from_email,
            to_emails=to_emails,
            subject=subject,
            html_content=html_content
        )
        
        current_app.logger.info(f"Sending email from {from_email} to {to_emails}")
        response = sg.send(message)
        success = response.status_code == 202

        if success:
            current_app.logger.info(f"Email sent successfully with status code {response.status_code}")
        else:
            current_app.logger.error(f"SendGrid error: Status code {response.status_code}")
            current_app.logger.error(f"Response body: {response.body}")

        return success
    except Exception as e:
        error_message = str(e)
        current_app.logger.error(f"Exception while sending email: {error_message}")
        
        if "The from address does not match a verified Sender Identity" in error_message:
            current_app.logger.error(f"SendGrid error: Sender email '{from_email}' is not verified. Please verify this domain in your SendGrid account.")
        else:
            current_app.logger.error(f"SendGrid error: {error_message}")
        return False

def send_schedule_notification(
    schedule: Schedule,
    action: str,
    additional_info: Optional[str] = None
) -> None:
    """
    Send a notification about a schedule change
    action should be one of: 'created', 'updated', 'deleted'
    """
    try:
        settings = get_email_settings()

        # Check if notifications are enabled for this action
        if (action == 'created' and not settings.notify_on_create or
            action == 'updated' and not settings.notify_on_update or
            action == 'deleted' and not settings.notify_on_delete):
            return

        # Build recipient list
        recipients = [settings.admin_email_group]
        if schedule.technician.email not in recipients:
            recipients.append(schedule.technician.email)

        # Build email content
        action_past = {'created': 'created', 'updated': 'updated', 'deleted': 'deleted'}[action]

        location_info = f" at {schedule.location.name}" if schedule.location else ""
        time_info = (f"from {schedule.start_time.strftime('%Y-%m-%d %H:%M')} "
                    f"to {schedule.end_time.strftime('%Y-%m-%d %H:%M')}")

        subject = f"Schedule {action_past} for {schedule.technician.username}"

        html_content = f"""
        <h3>Schedule {action_past}</h3>
        <p>A schedule has been {action_past} with the following details:</p>
        <ul>
            <li><strong>Technician:</strong> {schedule.technician.username}</li>
            <li><strong>Time:</strong> {time_info}</li>
            <li><strong>Location:</strong> {schedule.location.name if schedule.location else 'No location'}</li>
            <li><strong>Description:</strong> {schedule.description or 'No description'}</li>
        </ul>
        """

        if additional_info:
            html_content += f"<p><strong>Additional Information:</strong> {additional_info}</p>"

        success = send_email(
            to_emails=recipients,
            subject=subject,
            html_content=html_content
        )

        if not success:
            current_app.logger.warning(f"Failed to send email notification for schedule {action}")

    except Exception as e:
        current_app.logger.error(f"Error in send_schedule_notification: {str(e)}")
        
def send_ticket_assigned_notification(
    ticket: Ticket,
    assigned_by: User
) -> bool:
    """
    Send a notification when a ticket is assigned to a technician
    """
    try:
        # Make sure the ticket is assigned to someone
        if not ticket.assigned_to:
            current_app.logger.warning("Cannot send notification: ticket is not assigned to anyone")
            return False
            
        # Get the assigned technician
        technician = User.query.get(ticket.assigned_to)
        if not technician or not technician.email:
            current_app.logger.warning(f"Could not find email for technician ID {ticket.assigned_to}")
            return False
            
        settings = get_email_settings()
        current_app.logger.debug(f"Email settings: admin_email_group={settings.admin_email_group}")
        
        # Build recipient list - the assigned technician
        recipients = [technician.email]
        current_app.logger.debug(f"Added technician email to recipients: {technician.email}")
        
        # Add admin email for monitoring
        if settings.admin_email_group not in recipients:
            recipients.append(settings.admin_email_group)
            current_app.logger.debug(f"Added admin email to recipients: {settings.admin_email_group}")
            
        # Build ticket URL - manually constructing because SERVER_NAME causes issues
        domain = current_app.config.get('EMAIL_DOMAIN', 'localhost:5000')
        scheme = current_app.config.get('PREFERRED_URL_SCHEME', 'http')
        
        # Generate the URL path without _external=True to avoid SERVER_NAME issues
        path = url_for('tickets.view_ticket', ticket_id=ticket.id)
        ticket_url = f"{scheme}://{domain}{path}"
        
        current_app.logger.debug(f"Using domain: {domain} for email URLs")
        current_app.logger.debug(f"Generated ticket URL: {ticket_url}")
        
        subject = f"Ticket #{ticket.id} has been assigned to you"
        
        priority_labels = {
            0: 'Low',
            1: 'Medium',
            2: 'High',
            3: 'Urgent'
        }
        
        html_content = f"""
        <h3>Ticket Assigned</h3>
        <p>A ticket has been assigned to you by {assigned_by.username}:</p>
        <ul>
            <li><strong>Ticket ID:</strong> #{ticket.id}</li>
            <li><strong>Title:</strong> {ticket.title}</li>
            <li><strong>Priority:</strong> {priority_labels.get(ticket.priority, 'Unknown')}</li>
            <li><strong>Category:</strong> {ticket.category.name if ticket.category else 'Uncategorized'}</li>
            <li><strong>Status:</strong> {ticket.status.replace('_', ' ').title()}</li>
        </ul>
        <p><strong>Description:</strong><br>
        {ticket.description}
        </p>
        <p>
        <a href="{ticket_url}" style="background-color: #007bff; color: white; padding: 10px 15px; text-decoration: none; border-radius: 4px; display: inline-block;">View Ticket</a>
        </p>
        """
        
        success = send_email(
            to_emails=recipients,
            subject=subject,
            html_content=html_content
        )
        
        if not success:
            current_app.logger.warning(f"Failed to send email notification for ticket assignment")
            return False
            
        return success
            
    except Exception as e:
        current_app.logger.error(f"Error in send_ticket_assigned_notification: {str(e)}")
        return False
        
def send_ticket_comment_notification(
    ticket: Ticket,
    comment: TicketComment,
    commented_by: User
) -> bool:
    """
    Send a notification when a comment is added to a ticket
    """
    try:
        current_app.logger.debug(f"Starting comment notification for ticket #{ticket.id}")
        
        # Get the assigned technician (if any)
        recipients = []
        if ticket.assigned_to:
            technician = User.query.get(ticket.assigned_to)
            if technician and technician.email:
                recipients.append(technician.email)
                current_app.logger.debug(f"Added technician email to recipients: {technician.email}")
            else:
                current_app.logger.warning(f"Could not find valid email for technician ID {ticket.assigned_to}")
        
        # Skip if no recipients
        if not recipients:
            current_app.logger.warning("No recipients for comment notification, skipping")
            return False
            
        settings = get_email_settings()
        current_app.logger.debug(f"Email settings: admin_email_group={settings.admin_email_group}")
            
        # Add admin email for monitoring
        if settings.admin_email_group not in recipients:
            recipients.append(settings.admin_email_group)
            current_app.logger.debug(f"Added admin email to recipients: {settings.admin_email_group}")
        
        # Build ticket URL - manually constructing because SERVER_NAME causes issues
        domain = current_app.config.get('EMAIL_DOMAIN', 'localhost:5000')
        scheme = current_app.config.get('PREFERRED_URL_SCHEME', 'http')
        
        # Generate the URL path without _external=True to avoid SERVER_NAME issues
        path = url_for('tickets.view_ticket', ticket_id=ticket.id)
        ticket_url = f"{scheme}://{domain}{path}"
        
        current_app.logger.debug(f"Using domain: {domain} for email URLs")
        current_app.logger.debug(f"Generated ticket URL: {ticket_url}")
        
        subject = f"New comment on Ticket #{ticket.id}"
        
        html_content = f"""
        <h3>New Comment on Ticket #{ticket.id}</h3>
        <p><strong>{commented_by.username}</strong> added a comment to a ticket assigned to you:</p>
        <div style="background-color: #f8f9fa; padding: 15px; border-left: 4px solid #007bff; margin: 20px 0;">
            {comment.content}
        </div>
        <h4>Ticket Details</h4>
        <ul>
            <li><strong>Title:</strong> {ticket.title}</li>
            <li><strong>Status:</strong> {ticket.status.replace('_', ' ').title()}</li>
        </ul>
        <p>
        <a href="{ticket_url}" style="background-color: #007bff; color: white; padding: 10px 15px; text-decoration: none; border-radius: 4px; display: inline-block;">View Ticket</a>
        </p>
        """
        
        success = send_email(
            to_emails=recipients,
            subject=subject,
            html_content=html_content
        )
        
        if not success:
            current_app.logger.warning(f"Failed to send email notification for ticket comment")
            return False
            
        return success
            
    except Exception as e:
        current_app.logger.error(f"Error in send_ticket_comment_notification: {str(e)}")
        return False
        
def send_ticket_status_notification(
    ticket: Ticket,
    old_status: str,
    new_status: str,
    updated_by: User,
    comment: Optional[str] = None
) -> bool:
    """
    Send a notification when a ticket's status is updated
    """
    try:
        current_app.logger.debug(f"Starting status notification for ticket #{ticket.id}: {old_status} -> {new_status}")
        
        # Get the assigned technician (if any)
        recipients = []
        if ticket.assigned_to:
            technician = User.query.get(ticket.assigned_to)
            if technician and technician.email:
                recipients.append(technician.email)
                current_app.logger.debug(f"Added technician email to recipients: {technician.email}")
            else:
                current_app.logger.warning(f"Could not find valid email for technician ID {ticket.assigned_to}")
        
        # Skip if no recipients
        if not recipients:
            current_app.logger.warning("No recipients for status notification, skipping")
            return False
            
        settings = get_email_settings()
        current_app.logger.debug(f"Email settings: admin_email_group={settings.admin_email_group}")
            
        # Add admin email for monitoring
        if settings.admin_email_group not in recipients:
            recipients.append(settings.admin_email_group)
            current_app.logger.debug(f"Added admin email to recipients: {settings.admin_email_group}")
        
        # Build ticket URL - manually constructing because SERVER_NAME causes issues
        domain = current_app.config.get('EMAIL_DOMAIN', 'localhost:5000')
        scheme = current_app.config.get('PREFERRED_URL_SCHEME', 'http')
        
        # Generate the URL path without _external=True to avoid SERVER_NAME issues
        path = url_for('tickets.view_ticket', ticket_id=ticket.id)
        ticket_url = f"{scheme}://{domain}{path}"
        
        current_app.logger.debug(f"Using domain: {domain} for email URLs")
        current_app.logger.debug(f"Generated ticket URL: {ticket_url}")
        
        subject = f"Status changed on Ticket #{ticket.id}"
        
        html_content = f"""
        <h3>Ticket Status Changed</h3>
        <p>The status of ticket #{ticket.id} has been changed:</p>
        <ul>
            <li><strong>Old Status:</strong> {old_status.replace('_', ' ').title()}</li>
            <li><strong>New Status:</strong> {new_status.replace('_', ' ').title()}</li>
            <li><strong>Changed by:</strong> {updated_by.username}</li>
        </ul>
        """
        
        if comment:
            html_content += f"""
            <p><strong>Comment:</strong></p>
            <div style="background-color: #f8f9fa; padding: 15px; border-left: 4px solid #007bff; margin: 20px 0;">
                {comment}
            </div>
            """
            
        html_content += f"""
        <h4>Ticket Details</h4>
        <ul>
            <li><strong>Title:</strong> {ticket.title}</li>
        </ul>
        <p>
        <a href="{ticket_url}" style="background-color: #007bff; color: white; padding: 10px 15px; text-decoration: none; border-radius: 4px; display: inline-block;">View Ticket</a>
        </p>
        """
        
        success = send_email(
            to_emails=recipients,
            subject=subject,
            html_content=html_content
        )
        
        if not success:
            current_app.logger.warning(f"Failed to send email notification for ticket status change")
            return False
            
        return success
            
    except Exception as e:
        current_app.logger.error(f"Error in send_ticket_status_notification: {str(e)}")
        return False