from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, session, after_this_request
from flask_login import login_required, current_user
from forms import TicketForm, TicketCommentForm, TicketCategoryForm
from models import db, Ticket, TicketCategory, TicketComment, TicketHistory, User, TicketStatus
from datetime import datetime
import pytz
from app import app  # Import app for logging
from email_utils import send_ticket_assigned_notification, send_ticket_comment_notification, send_ticket_status_notification

# Update Blueprint to use the correct template directory
tickets = Blueprint('tickets', __name__)

@tickets.route('/tickets/dashboard')
@login_required
def tickets_dashboard():
    """Display all tickets with filtering options"""
    app.logger.debug(f"Raw request URL: {request.url}")
    app.logger.debug(f"Raw query args: {request.args}")
    
    # Get filters from request args with appropriate defaults
    # If no URL parameters, default to showing only open tickets
    if not request.args:
        app.logger.debug("No filters specified, defaulting to open tickets")
        status_filter = 'open'
        category_filter = 'all'
        priority_filter = 'all'
    else:
        status_filter = request.args.get('status', 'open')
        category_filter = request.args.get('category', 'all')
        priority_filter = request.args.get('priority', 'all')
        
        app.logger.debug(f"Status filter from request: {status_filter}")
        app.logger.debug(f"Category filter from request: {category_filter}")
        app.logger.debug(f"Priority filter from request: {priority_filter}")
    
    # If status is explicitly set to 'all', make sure it's respected
    if status_filter == 'all':
        app.logger.debug("Status filter is 'all', showing all tickets")
    
    # Add debug logging to see what filters are being applied
    app.logger.debug(f"Ticket dashboard filters - status: {status_filter}, category: {category_filter}, priority: {priority_filter}")

    # Base query
    query = Ticket.query

    # Apply filters
    app.logger.debug(f"Before filtering, query: {str(query.statement.compile(compile_kwargs={'literal_binds': True}))}")
    
    if status_filter != 'all':
        query = query.filter(Ticket.status == status_filter)
        app.logger.debug(f"After status filter ({status_filter}): {str(query.statement.compile(compile_kwargs={'literal_binds': True}))}")
    if category_filter != 'all':
        query = query.filter(Ticket.category_id == category_filter)
        app.logger.debug(f"After category filter ({category_filter}): {str(query.statement.compile(compile_kwargs={'literal_binds': True}))}")
    if priority_filter != 'all':
        query = query.filter(Ticket.priority == int(priority_filter))
        app.logger.debug(f"After priority filter ({priority_filter}): {str(query.statement.compile(compile_kwargs={'literal_binds': True}))}")

    # Show all tickets for all users
    tickets = query.order_by(Ticket.created_at.desc()).all()
    app.logger.debug(f"Found {len(tickets)} tickets matching filters: status={status_filter}, category={category_filter}, priority={priority_filter}")
    
    # Add debug information about each ticket found
    for ticket in tickets:
        app.logger.debug(f"Ticket #{ticket.id}: {ticket.title} - Status: {ticket.status}, Category: {ticket.category_id}, Priority: {ticket.priority}")
        
    # FORCE FILTER - Apply filter directly to the data
    # Force status filter first
    if status_filter != 'all':
        app.logger.debug(f"FORCE FILTERING: Filtering tickets by status={status_filter}")
        # Filter by status in Python
        tickets = [t for t in tickets if t.status == status_filter]
        app.logger.debug(f"AFTER STATUS FORCE FILTERING: {len(tickets)} tickets remain")
    
    # Force category filter if needed
    if category_filter != 'all':
        app.logger.debug(f"FORCE FILTERING: Filtering tickets by category={category_filter}")
        # Filter by category in Python
        tickets = [t for t in tickets if t.category_id == int(category_filter)]
        app.logger.debug(f"AFTER CATEGORY FORCE FILTERING: {len(tickets)} tickets remain")
    
    # Force priority filter if needed
    if priority_filter != 'all':
        app.logger.debug(f"FORCE FILTERING: Filtering tickets by priority={priority_filter}")
        # Filter by priority in Python
        tickets = [t for t in tickets if t.priority == int(priority_filter)]
        app.logger.debug(f"AFTER PRIORITY FORCE FILTERING: {len(tickets)} tickets remain")
    
    # Disable caching for this request to make sure we're getting fresh data
    @after_this_request
    def add_no_cache(response):
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
        
    # Add a temporary filter to show exactly what's going to the template
    app.logger.debug(f"FINAL TICKETS TO TEMPLATE:")
    for ticket in tickets:
        app.logger.debug(f"FINAL Ticket #{ticket.id}: {ticket.title} - Priority: {ticket.priority}")

    categories = TicketCategory.query.all()
    # Get all valid ticket statuses
    ticket_statuses = [
        TicketStatus.OPEN,
        TicketStatus.IN_PROGRESS,
        TicketStatus.PENDING,
        TicketStatus.RESOLVED,
        TicketStatus.CLOSED
    ]

    # Final debug check before rendering
    app.logger.debug(f"RENDERING TEMPLATE WITH {len(tickets)} TICKETS:")
    for idx, ticket in enumerate(tickets):
        app.logger.debug(f"RENDER TICKET #{idx+1}: ID={ticket.id}, Title={ticket.title}, Status={ticket.status}, Priority={ticket.priority}")
    
    # Pass ticket IDs as a separate variable to confirm what's being sent
    ticket_ids = [t.id for t in tickets]
    app.logger.debug(f"TICKET IDS PASSED TO TEMPLATE: {ticket_ids}")
    
    return render_template('tickets/dashboard.html', 
                         tickets=tickets,
                         categories=categories,
                         ticket_statuses=ticket_statuses,
                         ticket_count=len(tickets))

@tickets.route('/tickets/create', methods=['GET', 'POST'])
@login_required
def create_ticket():
    """Create a new ticket"""
    form = TicketForm()

    # Populate category choices
    form.category_id.choices = [(c.id, c.name) for c in TicketCategory.query.all()]

    # Populate technician choices for all users
    form.assigned_to.choices = [(u.id, u.username) for u in User.query.all()]

    if form.validate_on_submit():
        try:
            # Start a transaction
            app.logger.debug("Starting ticket creation transaction")

            # Create the ticket first
            ticket = Ticket(
                title=form.title.data,
                description=form.description.data,
                category_id=form.category_id.data,
                priority=form.priority.data,
                created_by=current_user.id,
                assigned_to=form.assigned_to.data,
                due_date=form.due_date.data
            )

            # Add ticket to session
            db.session.add(ticket)
            db.session.flush()  # This assigns the ID but doesn't commit

            app.logger.debug(f"Created ticket with ID: {ticket.id}")

            if not ticket.id:
                raise ValueError("Failed to generate ticket ID")

            # Create history entry
            history = TicketHistory(
                ticket_id=ticket.id,
                user_id=current_user.id,
                action="created",
                details="Ticket created",
                created_at=datetime.now(pytz.UTC)
            )

            # Add history to session
            db.session.add(history)

            # Verify both objects are valid before committing
            if not history.ticket_id or not history.user_id:
                raise ValueError("Invalid history entry data")

            # Commit both changes
            db.session.commit()
            app.logger.info(f"Successfully created ticket {ticket.id} with history entry")
            
            # Send email notification if the ticket is assigned to someone
            if ticket.assigned_to:
                try:
                    app.logger.info(f"Sending initial assignment notification for ticket #{ticket.id}")
                    technician = User.query.get(ticket.assigned_to)
                    app.logger.info(f"Assigned technician: {technician.username} (ID: {technician.id})")
                    
                    # Now send the notification
                    from email_utils import send_ticket_assigned_notification
                    result = send_ticket_assigned_notification(
                        ticket=ticket,
                        assigned_by=current_user
                    )
                    
                    app.logger.info(f"Initial assignment notification result: {result}")
                    if not result:
                        app.logger.error("Initial ticket assignment notification failed!")
                    else:
                        app.logger.info("Initial ticket assignment notification sent successfully!")
                except Exception as e:
                    app.logger.error(f"Failed to send initial assignment notification: {str(e)}")
                    # Print full exception traceback for debugging
                    import traceback
                    app.logger.error(f"Exception traceback: {traceback.format_exc()}")
            
            flash('Ticket created successfully', 'success')
            return redirect(url_for('tickets.view_ticket', ticket_id=ticket.id))

        except ValueError as ve:
            db.session.rollback()
            app.logger.error(f"Validation error in ticket creation: {str(ve)}")
            flash('Error validating ticket data. Please try again.', 'error')
            return render_template('tickets/create.html', form=form)

        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error creating ticket: {str(e)}")
            flash('Error creating ticket. Please try again.', 'error')
            return render_template('tickets/create.html', form=form)

    return render_template('tickets/create.html', form=form)

@tickets.route('/tickets/<int:ticket_id>')
@login_required
def view_ticket(ticket_id):
    """View a specific ticket"""
    ticket = Ticket.query.get_or_404(ticket_id)

    # All users can view all tickets

    # Create forms for comments and editing
    comment_form = TicketCommentForm()
    form = TicketForm()
    
    # Get categories and technicians for the modal forms
    categories = TicketCategory.query.all()
    technicians = User.query.all()

    # Populate form with current ticket data
    if request.method == 'GET':
        form.title.data = ticket.title
        form.description.data = ticket.description
        form.category_id.data = ticket.category_id
        form.priority.data = ticket.priority
        form.due_date.data = ticket.due_date

        # Populate category choices
        form.category_id.choices = [(c.id, c.name) for c in categories]

        # Populate technician choices for admin users and ticket creators
        if current_user.is_admin or current_user.id == ticket.created_by:
            form.assigned_to.choices = [(u.id, u.username) for u in technicians]

    return render_template('tickets/view.html', 
                         ticket=ticket,
                         comment_form=comment_form,
                         form=form,
                         categories=categories,
                         technicians=technicians,
                         TicketStatus=TicketStatus)

@tickets.route('/tickets/<int:ticket_id>/comment', methods=['POST'])
@login_required
def add_comment(ticket_id):
    """Add a comment to a ticket"""
    ticket = Ticket.query.get_or_404(ticket_id)
    form = TicketCommentForm()
    
    if form.validate_on_submit():
        # Add comment to the ticket
        comment = ticket.add_comment(current_user, form.content.data)
        ticket.log_history(current_user, "commented")
        db.session.commit()
        
        # Send notification email if the ticket is assigned to someone
        if ticket.assigned_to and ticket.assigned_to != current_user.id:
            try:
                app.logger.debug(f"Sending comment notification for ticket #{ticket.id}")
                # The email function will create an app context if needed
                send_ticket_comment_notification(
                    ticket=ticket,
                    comment=comment,
                    commented_by=current_user
                )
            except Exception as e:
                app.logger.error(f"Failed to send comment notification: {str(e)}")
                import traceback
                app.logger.error(f"Exception traceback: {traceback.format_exc()}")
        
        flash('Comment added successfully', 'success')
    
    return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))

@tickets.route('/tickets/<int:ticket_id>/status', methods=['POST'])
@login_required
def update_status(ticket_id):
    """Update ticket status"""
    ticket = Ticket.query.get_or_404(ticket_id)
    new_status = request.form.get('status')
    comment = request.form.get('comment', '')
    
    if new_status not in vars(TicketStatus).values():
        flash('Invalid ticket status', 'error')
        return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))
    
    old_status = ticket.status
    ticket.status = new_status
    
    # Add status change to history
    details = f"Status changed from {old_status} to {new_status}"
    if comment:
        details += f" - Comment: {comment}"
        
    ticket.log_history(current_user, "status_changed", details)
    
    # If a comment was provided, also add it as a separate comment
    if comment:
        ticket.add_comment(current_user, comment)
        
    db.session.commit()
    
    # Send notification email if the ticket is assigned to someone
    if ticket.assigned_to and ticket.assigned_to != current_user.id:
        try:
            app.logger.info(f"Sending status update notification for ticket #{ticket.id}")
            
            # The email function will create an app context if needed
            result = send_ticket_status_notification(
                ticket=ticket,
                old_status=old_status,
                new_status=new_status,
                updated_by=current_user,
                comment=comment if comment else None
            )
            
            app.logger.info(f"Status notification result: {result}")
            if not result:
                app.logger.error("Ticket status notification failed!")
            else:
                app.logger.info("Ticket status notification sent successfully!")
                
        except Exception as e:
            app.logger.error(f"Failed to send status update notification: {str(e)}")
            import traceback
            app.logger.error(f"Exception traceback: {traceback.format_exc()}")
    
    flash('Ticket status updated successfully', 'success')
    return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))

@tickets.route('/tickets/<int:ticket_id>/assign', methods=['POST'])
@login_required
def assign_ticket(ticket_id):
    """Assign ticket to a technician"""
    # Get the ticket first
    ticket = Ticket.query.get_or_404(ticket_id)
    
    # Check if user has permission to assign this ticket
    # Allow if user is admin or if they created the ticket
    if not (current_user.is_admin or ticket.created_by == current_user.id):
        flash('You do not have permission to assign this ticket', 'error')
        return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))
    
    app.logger.info(f"Starting ticket assignment process for ticket #{ticket_id}")
    
    # Get the technician ID from the form - it's named 'assigned_to' in the template
    technician_id = request.form.get('assigned_to')
    note = request.form.get('note', '')
    
    app.logger.info(f"Request form data: technician_id={technician_id}, note={note}")
    
    if technician_id:
        # Assigning ticket to technician
        technician = User.query.get_or_404(technician_id)
        app.logger.info(f"Found technician: {technician.username} (ID: {technician.id}), email: {technician.email}")
        
        # Update ticket
        ticket.assigned_to = technician.id
        details = f"Assigned to {technician.username}"
        if note:
            details += f" - Note: {note}"
        
        app.logger.info(f"Updating ticket #{ticket.id} assigned_to: {ticket.assigned_to}")    
        ticket.log_history(current_user, "assigned", details)
        
        # Commit the assignment to the database
        db.session.commit()
        app.logger.info(f"Committed ticket assignment to database")
        
        # Send notification email to the assigned technician
        try:
            app.logger.info(f"Sending assignment notification for ticket #{ticket.id}")
            
            # Additional debug info
            app.logger.info(f"Ticket assigned to user ID: {ticket.assigned_to}")
            tech = User.query.get(ticket.assigned_to)
            app.logger.info(f"Assigned technician: {tech.username}, Email: {tech.email}")
            app.logger.info(f"Current user (assigner): {current_user.username}, Email: {current_user.email}")
            
            # Check email settings
            from email_utils import get_email_settings
            settings = get_email_settings()
            app.logger.info(f"Email settings: Admin email = {settings.admin_email_group}")
            
            # Check if we're in an application context
            from flask import has_app_context
            app.logger.info(f"Before with clause: has_app_context = {has_app_context()}")
            
            # Instead of using nested app_context, use send_ticket_assigned_notification directly
            app.logger.info("Calling send_ticket_assigned_notification directly")
            from email_utils import send_ticket_assigned_notification
            result = send_ticket_assigned_notification(
                ticket=ticket,
                assigned_by=current_user
            )
            
            app.logger.info(f"Assignment notification result: {result}")
            if not result:
                app.logger.error("Ticket assignment notification failed!")
            else:
                app.logger.info("Ticket assignment notification sent successfully!")
        except Exception as e:
            app.logger.error(f"Failed to send assignment notification: {str(e)}")
            # Print full exception traceback for debugging
            import traceback
            app.logger.error(f"Exception traceback: {traceback.format_exc()}")
    else:
        # Unassigning ticket
        ticket.assigned_to = None
        ticket.log_history(current_user, "unassigned")
        app.logger.info(f"Unassigned ticket #{ticket.id}")
        db.session.commit()
    
    flash('Ticket assigned successfully', 'success')
    return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))

@tickets.route('/tickets/<int:ticket_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_ticket(ticket_id):
    """Edit an existing ticket"""
    ticket = Ticket.query.get_or_404(ticket_id)

    # Check if user has permission to edit
    if not (current_user.is_admin or ticket.created_by == current_user.id):
        flash('You do not have permission to edit this ticket', 'error')
        return redirect(url_for('tickets.tickets_dashboard'))

    if request.method == 'POST':
        # Get form data directly
        old_title = ticket.title
        old_description = ticket.description
        old_category_id = ticket.category_id
        old_priority = ticket.priority

        # Update ticket with form data
        ticket.title = request.form.get('title')
        ticket.description = request.form.get('description')
        ticket.category_id = request.form.get('category_id')
        
        # Handle priority conversion to int
        priority_val = request.form.get('priority')
        ticket.priority = int(priority_val) if priority_val else 0
        
        # Handle due date (could be empty)
        due_date_val = request.form.get('due_date')
        if due_date_val:
            try:
                ticket.due_date = datetime.fromisoformat(due_date_val)
            except ValueError:
                # If there's a parsing error, keep the existing date
                app.logger.warning(f"Invalid due date format: {due_date_val}")
        else:
            ticket.due_date = None

        # Log changes in ticket history
        changes = []
        if old_title != ticket.title:
            changes.append(f"Title changed from '{old_title}' to '{ticket.title}'")
        if old_description != ticket.description:
            changes.append("Description updated")
        if str(old_category_id) != str(ticket.category_id):
            changes.append(f"Category changed")
        if old_priority != ticket.priority:
            changes.append(f"Priority changed from {old_priority} to {ticket.priority}")

        if changes:
            ticket.log_history(current_user, "edited", ", ".join(changes))
            db.session.commit()
            flash('Ticket updated successfully', 'success')

        return redirect(url_for('tickets.view_ticket', ticket_id=ticket.id))

    # GET requests should go to view ticket page
    return redirect(url_for('tickets.view_ticket', ticket_id=ticket.id))


@tickets.route('/tickets/<int:ticket_id>/delete')
@login_required
def delete_ticket(ticket_id):
    """Delete a ticket (admin only)"""
    if not current_user.is_admin:
        flash('You do not have permission to delete tickets', 'error')
        return redirect(url_for('tickets.tickets_dashboard'))
        
    ticket = Ticket.query.get_or_404(ticket_id)
    
    try:
        # Store data for logging
        ticket_title = ticket.title
        ticket_id_copy = ticket.id
        
        # Delete the ticket (comments and history are cascade deleted)
        db.session.delete(ticket)
        db.session.commit()
        
        app.logger.info(f"Ticket #{ticket_id_copy} ('{ticket_title}') deleted by {current_user.username}")
        flash(f'Ticket #{ticket_id_copy} has been deleted', 'success')
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error deleting ticket #{ticket_id}: {str(e)}")
        flash('Error deleting ticket', 'error')
        
    return redirect(url_for('tickets.tickets_dashboard'))
    
@tickets.route('/tickets/comment/<int:comment_id>/delete')
@login_required
def delete_comment(comment_id):
    """Delete a comment"""
    comment = TicketComment.query.get_or_404(comment_id)
    ticket_id = comment.ticket_id
    
    # Check if user has permission to delete this comment
    if not (current_user.is_admin or comment.user_id == current_user.id):
        flash('You do not have permission to delete this comment', 'error')
        return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))
        
    try:
        # Add history entry before deleting the comment
        ticket = Ticket.query.get(ticket_id)
        if ticket:
            ticket.log_history(
                current_user,
                "deleted_comment",
                f"Comment by {comment.user.username} deleted"
            )
            
        # Delete the comment
        db.session.delete(comment)
        db.session.commit()
        
        flash('Comment deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error deleting comment #{comment_id}: {str(e)}")
        flash('Error deleting comment', 'error')
        
    return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))

# Admin routes for managing ticket categories
@tickets.route('/tickets/categories', methods=['GET', 'POST'])
@login_required
def manage_categories():
    """Manage ticket categories (admin only)"""
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('tickets.tickets_dashboard'))

    form = TicketCategoryForm()
    if form.validate_on_submit():
        category = TicketCategory(
            name=form.name.data,
            description=form.description.data,
            icon=form.icon.data,
            priority_level=form.priority_level.data
        )
        db.session.add(category)
        db.session.commit()
        flash('Category added successfully', 'success')
        return redirect(url_for('tickets.manage_categories'))

    categories = TicketCategory.query.order_by(TicketCategory.name).all()
    return render_template('tickets/manage_categories.html', 
                         categories=categories,
                         form=form)