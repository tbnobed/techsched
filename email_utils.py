import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content
from typing import List, Optional
from models import Schedule, EmailSettings
from flask import current_app

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
    try:
        api_key = os.environ.get('SENDGRID_API_KEY')
        if not api_key:
            current_app.logger.error("SendGrid API key is not set")
            return False

        sg = SendGridAPIClient(api_key)
        message = Mail(
            from_email=from_email,
            to_emails=to_emails,
            subject=subject,
            html_content=html_content
        )
        response = sg.send(message)
        success = response.status_code == 202

        if not success:
            current_app.logger.error(f"SendGrid error: Status code {response.status_code}")

        return success
    except Exception as e:
        error_message = str(e)
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