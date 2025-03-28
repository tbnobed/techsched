from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, session, after_this_request
from flask_login import login_required, current_user
from forms import TicketForm, TicketCommentForm, TicketCategoryForm
from models import db, Ticket, TicketCategory, TicketComment, TicketHistory, User, TicketStatus
from datetime import datetime
import pytz
from sqlalchemy import text, or_
from app import app  # Import app for logging
from email_utils import send_ticket_assigned_notification, send_ticket_comment_notification, send_ticket_status_notification

# Update Blueprint to use the correct template directory
tickets = Blueprint('tickets', __name__)

# Create function that will be registered with the main app context
def get_active_sidebar_tickets():
    """
    This function always returns active tickets for the sidebar
    regardless of any filtering applied in the main dashboard.
    """
    app.logger.debug("Getting active tickets for sidebar from global context")
    
    # Get all active tickets (open, in_progress, pending) for sidebar
    query = Ticket.query.filter(
        Ticket.status.in_([TicketStatus.OPEN, TicketStatus.IN_PROGRESS, TicketStatus.PENDING])
    ).order_by(
        # Order by priority (highest first) and then creation date (newest first)
        Ticket.priority.desc(),
        Ticket.created_at.desc()
    ).limit(5)
    
    tickets = query.all()
    app.logger.debug(f"Found {len(tickets)} active tickets for sidebar")
    
    return tickets

@tickets.route('/tickets/standalone_dashboard')
@login_required
def standalone_dashboard():
    """A clean standalone version of the dashboard for testing filtering"""
    app.logger.debug(f"STANDALONE DASHBOARD - Raw request URL: {request.url}")
    app.logger.debug(f"STANDALONE DASHBOARD - Raw query args: {request.args}")
    
    # Get filter params from the request
    status_filter = request.args.get('status', 'all')
    priority_filter = request.args.get('priority', 'all')
    category_filter = request.args.get('category', 'all')
    
    app.logger.debug(f"STANDALONE DASHBOARD - Filters: status={status_filter}, priority={priority_filter}, category={category_filter}")
    
    # Start with all tickets
    query = Ticket.query
    
    # Apply filters based on request parameters
    if status_filter != 'all':
        query = query.filter(Ticket.status == status_filter)
    
    if priority_filter != 'all':
        try:
            priority_value = int(priority_filter)
            query = query.filter(Ticket.priority == priority_value)
        except (ValueError, TypeError):
            app.logger.error(f"Invalid priority value: {priority_filter}")
    
    if category_filter != 'all':
        try:
            category_id = int(category_filter)
            query = query.filter(Ticket.category_id == category_id)
        except (ValueError, TypeError):
            app.logger.error(f"Invalid category value: {category_filter}")
            
    # Get tickets based on filters
    tickets = query.order_by(Ticket.created_at.desc()).all()
    app.logger.debug(f"STANDALONE DASHBOARD - Found {len(tickets)} tickets")
    
    # Convert to dictionaries for the template
    ticket_dicts = []
    for ticket in tickets:
        t = {
            'id': ticket.id,
            'title': ticket.title,
            'status': ticket.status,
            'priority': ticket.priority,
            'assigned_to': ticket.assigned_to,
            'created_by': ticket.created_by,
            'created_at': ticket.created_at,
            'updated_at': ticket.updated_at,
            'category': {
                'id': ticket.category.id,
                'name': ticket.category.name
            }
        }
        
        # Add assigned technician info if available
        if ticket.assigned_technician:
            t['assigned_technician'] = {
                'username': ticket.assigned_technician.username
            }
        else:
            t['assigned_technician'] = None
            
        ticket_dicts.append(t)
    
    # Get data for dropdowns
    categories = [
        {
            'id': category.id,
            'name': category.name
        }
        for category in TicketCategory.query.all()
    ]
    
    ticket_statuses = [
        TicketStatus.OPEN,
        TicketStatus.IN_PROGRESS,
        TicketStatus.PENDING,
        TicketStatus.RESOLVED,
        TicketStatus.CLOSED
    ]
    
    # Create filter_info for the template
    filter_info = {
        'status': status_filter,
        'priority': priority_filter,
        'category': category_filter,
        'timestamp': int(datetime.now().timestamp() * 1000)
    }
    
    # Disable caching for this request
    @after_this_request
    def add_no_cache(response):
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
    
    # Use the standalone template
    return render_template('tickets/standalone_dashboard.html',
                           tickets=ticket_dicts,
                           categories=categories,
                           ticket_statuses=ticket_statuses,
                           ticket_count=len(ticket_dicts),
                           filter_info=filter_info,
                           timestamp=filter_info['timestamp'])

@tickets.route('/tickets/dashboard')
@login_required
def tickets_dashboard():
    """Display all tickets with filtering options"""
    # Import the TicketStatus class from models (even though it's imported at the top)
    from models import TicketStatus, Ticket
    
    app.logger.debug(f"Raw request URL: {request.url}")
    app.logger.debug(f"Raw query args: {request.args}")
    
    # Get filters from request args with appropriate defaults
    # Check if no URL parameters or only cache-busting parameters
    cache_params = ['timestamp', 'rand']
    has_only_cache_params = all(k in cache_params for k in request.args.keys()) if request.args else True
    
    # Extract raw filter values from the request (for debugging)
    raw_status_filter = request.args.get('status')
    raw_category_filter = request.args.get('category')
    raw_priority_filter = request.args.get('priority')
    raw_technician_filter = request.args.get('technician')
    
    app.logger.debug(f"Raw filter values from request - status: {raw_status_filter}, category: {raw_category_filter}, priority: {raw_priority_filter}, technician: {raw_technician_filter}")
    
    # Determine final filter values
    if not request.args or has_only_cache_params:
        app.logger.debug("No filters specified or only cache parameters, defaulting to open tickets")
        status_filter = 'open'
        category_filter = 'all'
        priority_filter = 'all'
        technician_filter = 'all'
    else:
        # Use 'all' as default if not provided
        status_filter = raw_status_filter if raw_status_filter not in (None, '') else 'all'
        category_filter = raw_category_filter if raw_category_filter not in (None, '') else 'all'
        priority_filter = raw_priority_filter if raw_priority_filter not in (None, '') else 'all'
        technician_filter = raw_technician_filter if raw_technician_filter not in (None, '') else 'all'
        
        # Log explicit parameter requests for debugging
        app.logger.debug(f"Explicit filter request - status:{status_filter}, category:{category_filter}, priority:{priority_filter}, technician:{technician_filter}")
        
        # Force-convert these to appropriate types for comparison
        status_filter = status_filter.strip().lower()
        app.logger.debug(f"Status filter from request (normalized): {status_filter}")
        app.logger.debug(f"Category filter from request: {category_filter}")
        app.logger.debug(f"Priority filter from request: {priority_filter}")
        app.logger.debug(f"Technician filter from request: {technician_filter}")
    
    # Verify that status filter is valid
    valid_statuses = vars(TicketStatus).values()
    if status_filter != 'all' and status_filter not in valid_statuses:
        app.logger.warning(f"Invalid status filter '{status_filter}', defaulting to 'open'")
        status_filter = 'open'
    
    # If status is explicitly set to 'all', make sure it's respected
    if status_filter == 'all':
        app.logger.debug("Status filter is 'all', showing all tickets")
    
    # Add debug logging to see what filters are being applied
    app.logger.debug(f"Ticket dashboard filters - status: {status_filter}, category: {category_filter}, priority: {priority_filter}, technician: {technician_filter}")

    # Add some diagnostic queries to check database status values
    # Count status distribution in database
    status_counts = db.session.execute(
        text("""
        SELECT status, COUNT(*) as count
        FROM ticket
        GROUP BY status
        ORDER BY status
        """)
    ).fetchall()
    app.logger.debug("Status counts in database:")
    for status, count in status_counts:
        app.logger.debug(f"  {status}: {count} tickets")

    # Get archived filter from the request
    show_archived = request.args.get('archived', 'false').lower() == 'true'
    
    # Base query
    query = Ticket.query
    
    # Apply filters
    app.logger.debug(f"Before filtering, query: {str(query.statement.compile(compile_kwargs={'literal_binds': True}))}")
    
    # By default, don't show archived tickets unless explicitly requested
    if not show_archived:
        query = query.filter(Ticket.archived == False)
        app.logger.debug(f"Filtered to non-archived tickets only")
    
    # For explicit status checking, keep track of raw query string
    raw_status_filter = status_filter
    
    if status_filter != 'all':
        query = query.filter(Ticket.status == status_filter)
        app.logger.debug(f"After status filter ({status_filter}): {str(query.statement.compile(compile_kwargs={'literal_binds': True}))}")
    if category_filter != 'all':
        try:
            category_id = int(category_filter)
            query = query.filter(Ticket.category_id == category_id)
            app.logger.debug(f"After category filter ({category_filter}): {str(query.statement.compile(compile_kwargs={'literal_binds': True}))}")
        except (ValueError, TypeError):
            app.logger.error(f"Invalid category filter value: {category_filter}")

    if priority_filter != 'all':
        try:
            priority_value = int(priority_filter)
            query = query.filter(Ticket.priority == priority_value)
            app.logger.debug(f"After priority filter ({priority_filter}): {str(query.statement.compile(compile_kwargs={'literal_binds': True}))}")
        except (ValueError, TypeError):
            app.logger.error(f"Invalid priority filter value: {priority_filter}")
            
    if technician_filter != 'all':
        try:
            technician_id = int(technician_filter)
            query = query.filter(Ticket.assigned_to == technician_id)
            app.logger.debug(f"After technician filter ({technician_filter}): {str(query.statement.compile(compile_kwargs={'literal_binds': True}))}")
        except (ValueError, TypeError):
            app.logger.error(f"Invalid technician filter value: {technician_filter}")

    # Show all tickets for all users, ordered by creation date (newest first)
    tickets = query.order_by(Ticket.created_at.desc()).all()
    
    # Add special debug logs for status filter
    app.logger.debug(f"Status filter applied: '{raw_status_filter}'")
    app.logger.debug(f"Found {len(tickets)} tickets matching filters: status={status_filter}, category={category_filter}, priority={priority_filter}, technician={technician_filter}")
    
    # Add debug information about each ticket found
    for ticket in tickets:
        app.logger.debug(f"Ticket #{ticket.id}: {ticket.title} - Status: {ticket.status}, Category: {ticket.category_id}, Priority: {ticket.priority}")
        
    # FORCE FILTER - Apply filter directly to the data
    # No need for the force filtering here as the SQL query should handle it correctly
    # We'll keep a debug log of found tickets
    app.logger.debug(f"Found tickets after SQL filtering: {len(tickets)}")
    
    for ticket in tickets:
        app.logger.debug(f"Found ticket: ID={ticket.id}, Title={ticket.title}, Status={ticket.status}, Priority={ticket.priority}")
    
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
        app.logger.debug(f"FINAL Ticket #{ticket.id}: {ticket.title} - Status: {ticket.status} - Priority: {ticket.priority}")
        
    # Double-check all tickets have data in correct format (debug step)
    app.logger.debug(f"Double-checking all tickets in the database:")
    all_tickets = Ticket.query.all()
    for ticket in all_tickets:
        app.logger.debug(f"DB Ticket #{ticket.id}: {ticket.title} - Status: '{ticket.status}' - Priority: {ticket.priority}")
    
    # Get categories and convert to dictionaries
    categories_objects = TicketCategory.query.all()
    categories = [
        {
            'id': category.id,
            'name': category.name,
            'description': category.description
        }
        for category in categories_objects
    ]
    # Get all valid ticket statuses
    ticket_statuses = [
        TicketStatus.OPEN,
        TicketStatus.IN_PROGRESS,
        TicketStatus.PENDING,
        TicketStatus.RESOLVED,
        TicketStatus.CLOSED
    ]

    # For robust filtering, convert SQLAlchemy objects to simple dictionaries
    # This will eliminate any potential SQLAlchemy caching issues
    filtered_tickets = []
    for ticket in tickets:
        # Create a simple dict with only the data we need
        ticket_dict = {
            'id': ticket.id,
            'title': ticket.title,
            'status': ticket.status,
            'priority': ticket.priority,
            'assigned_to': ticket.assigned_to,
            'created_by': ticket.created_by,
            'created_at': ticket.created_at,
            'updated_at': ticket.updated_at,
            'due_date': ticket.due_date,
            'category': {
                'id': ticket.category.id,
                'name': ticket.category.name
            }
        }
        
        # Add assigned technician info if available
        if ticket.assigned_technician:
            ticket_dict['assigned_technician'] = {
                'username': ticket.assigned_technician.username
            }
        else:
            ticket_dict['assigned_technician'] = None
            
        filtered_tickets.append(ticket_dict)
    
    # Final logging to verify what's being sent
    app.logger.debug(f"RENDERING TEMPLATE WITH {len(filtered_tickets)} TICKETS:")
    for idx, ticket in enumerate(filtered_tickets):
        app.logger.debug(f"RENDER TICKET #{idx+1}: ID={ticket['id']}, Title={ticket['title']}, Status={ticket['status']}, Priority={ticket['priority']}")
    
    # Add timestamp to prevent any caching
    timestamp = int(datetime.now().timestamp() * 1000)
    
    # Pass very explicit filtering info to the template
    filter_info = {
        'status': status_filter,
        'category': category_filter,
        'priority': priority_filter,
        'technician': technician_filter,
        'timestamp': timestamp
    }
    
    # Get active tickets for the sidebar
    active_sidebar_tickets = Ticket.query.filter(
        Ticket.status.in_([TicketStatus.OPEN, TicketStatus.IN_PROGRESS, TicketStatus.PENDING])
    ).order_by(
        Ticket.priority.desc(),
        Ticket.created_at.desc()
    ).limit(5).all()
    
    # Get all technicians for the technician filter dropdown
    technicians = User.query.all()
    
    return render_template('tickets/dashboard.html', 
                         tickets=filtered_tickets,
                         categories=categories,
                         ticket_statuses=ticket_statuses,
                         technicians=technicians,
                         ticket_count=len(filtered_tickets),
                         filter_info=filter_info,
                         timestamp=timestamp,
                         active_sidebar_tickets=active_sidebar_tickets)

@tickets.route('/tickets/create', methods=['GET', 'POST'])
@login_required
def create_ticket():
    """Create a new ticket"""
    # Get active tickets for the sidebar
    active_sidebar_tickets = Ticket.query.filter(
        Ticket.status.in_([TicketStatus.OPEN, TicketStatus.IN_PROGRESS, TicketStatus.PENDING])
    ).order_by(
        Ticket.priority.desc(),
        Ticket.created_at.desc()
    ).limit(5).all()
    
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
            # Handle due date - ensure it has proper timezone if provided
            due_date = None
            if form.due_date.data:
                app.logger.debug(f"Processing due date from form: {form.due_date.data}")
                # Make sure we create a proper datetime object at midnight in UTC
                date_obj = form.due_date.data
                due_date = datetime(
                    year=date_obj.year,
                    month=date_obj.month,
                    day=date_obj.day,
                    tzinfo=pytz.UTC
                )
                app.logger.debug(f"Processed due date: {due_date}")
            
            ticket = Ticket(
                title=form.title.data,
                description=form.description.data,
                category_id=form.category_id.data,
                priority=form.priority.data,
                created_by=current_user.id,
                assigned_to=form.assigned_to.data,
                due_date=due_date
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
            return render_template('tickets/create.html', form=form, active_sidebar_tickets=active_sidebar_tickets)

        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error creating ticket: {str(e)}")
            flash('Error creating ticket. Please try again.', 'error')
            return render_template('tickets/create.html', form=form, active_sidebar_tickets=active_sidebar_tickets)

    return render_template('tickets/create.html', form=form, active_sidebar_tickets=active_sidebar_tickets)

@tickets.route('/tickets/<int:ticket_id>')
@login_required
def view_ticket(ticket_id):
    """View a specific ticket"""
    ticket_obj = Ticket.query.get_or_404(ticket_id)

    # All users can view all tickets

    # Create forms for comments and editing
    comment_form = TicketCommentForm()
    form = TicketForm()
    
    # Get categories and technicians for the modal forms
    categories_objects = TicketCategory.query.all()
    # Convert categories to dictionaries
    categories = [
        {
            'id': category.id,
            'name': category.name,
            'description': category.description
        }
        for category in categories_objects
    ]
    technicians = User.query.all()

    # Convert ticket to dictionary to avoid SQLAlchemy caching issues
    ticket = {
        'id': ticket_obj.id,
        'title': ticket_obj.title,
        'description': ticket_obj.description,
        'category_id': ticket_obj.category_id,
        'status': ticket_obj.status,
        'priority': ticket_obj.priority,
        'assigned_to': ticket_obj.assigned_to,
        'created_by': ticket_obj.created_by,
        'created_at': ticket_obj.created_at,
        'updated_at': ticket_obj.updated_at,
        'due_date': ticket_obj.due_date,
        'category': {
            'id': ticket_obj.category.id,
            'name': ticket_obj.category.name
        },
        'comments': [{
            'id': comment.id,
            'content': comment.content,
            'created_at': comment.created_at,
            'user': {
                'id': comment.user.id,
                'username': comment.user.username,
                'color': comment.user.color
            }
        } for comment in ticket_obj.comments],
        'history': [{
            'id': history.id,
            'action': history.action,
            'details': history.details,
            'created_at': history.created_at,
            'user': {
                'id': history.user.id,
                'username': history.user.username
            }
        } for history in ticket_obj.history]
    }
    
    # Add creator and assigned technician info
    ticket['creator'] = {
        'id': ticket_obj.creator.id,
        'username': ticket_obj.creator.username
    }
    
    if ticket_obj.assigned_technician:
        ticket['assigned_technician'] = {
            'id': ticket_obj.assigned_technician.id,
            'username': ticket_obj.assigned_technician.username
        }
    else:
        ticket['assigned_technician'] = None

    # Populate form with current ticket data
    if request.method == 'GET':
        form.title.data = ticket_obj.title
        form.description.data = ticket_obj.description
        form.category_id.data = ticket_obj.category_id
        form.priority.data = ticket_obj.priority
        form.due_date.data = ticket_obj.due_date

        # Populate category choices
        form.category_id.choices = [(c['id'], c['name']) for c in categories]

        # Populate technician choices for admin users and ticket creators
        if current_user.is_admin or current_user.id == ticket_obj.created_by:
            form.assigned_to.choices = [(u.id, u.username) for u in technicians]

    # Get active tickets for the sidebar
    active_sidebar_tickets = Ticket.query.filter(
        Ticket.status.in_([TicketStatus.OPEN, TicketStatus.IN_PROGRESS, TicketStatus.PENDING])
    ).order_by(
        Ticket.priority.desc(),
        Ticket.created_at.desc()
    ).limit(5).all()
    
    return render_template('tickets/view.html', 
                         ticket=ticket,
                         comment_form=comment_form,
                         form=form,
                         categories=categories,
                         technicians=technicians,
                         active_sidebar_tickets=active_sidebar_tickets,
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
    
    app.logger.debug(f"Updating ticket #{ticket_id} status from '{ticket.status}' to '{new_status}'")
    
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
    
    # Force the status change by marking it as modified
    db.session.add(ticket)
    
    try:
        db.session.commit()
        app.logger.debug(f"Successfully updated ticket #{ticket_id} status to '{new_status}'")
        # Verify the update took effect
        db.session.refresh(ticket)
        app.logger.debug(f"After commit, ticket status is now '{ticket.status}'")
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error updating ticket status: {str(e)}")
        flash('Error updating ticket status', 'error')
    
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
    app.logger.debug(f"Editing ticket #{ticket_id}")

    # Check if user has permission to edit
    if not (current_user.is_admin or ticket.created_by == current_user.id):
        flash('You do not have permission to edit this ticket', 'error')
        return redirect(url_for('tickets.tickets_dashboard'))

    if request.method == 'POST':
        # Log all form data for debugging
        app.logger.debug(f"Form data received: {request.form}")
        
        # Get form data directly
        old_title = ticket.title
        old_description = ticket.description
        old_category_id = ticket.category_id
        old_priority = ticket.priority
        old_due_date = ticket.due_date
        app.logger.debug(f"Original due date: {old_due_date}")

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
                # HTML date inputs return YYYY-MM-DD format, so we use strptime
                app.logger.debug(f"Processing due date: {due_date_val}")
                date_obj = datetime.strptime(due_date_val, '%Y-%m-%d')
                
                # Create a datetime at midnight in UTC for the given date
                # This ensures we have a timezone-aware datetime object
                ticket.due_date = datetime(
                    year=date_obj.year,
                    month=date_obj.month,
                    day=date_obj.day,
                    tzinfo=pytz.UTC
                )
                app.logger.debug(f"New due date set to: {ticket.due_date}")
            except ValueError as e:
                # If there's a parsing error, keep the existing date
                app.logger.warning(f"Invalid due date format: {due_date_val}, error: {str(e)}")
        else:
            ticket.due_date = None
            app.logger.debug("Due date cleared/not provided")

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
            
        # Check for due date changes
        if old_due_date != ticket.due_date:
            old_date_str = old_due_date.strftime('%Y-%m-%d') if old_due_date else 'None'
            new_date_str = ticket.due_date.strftime('%Y-%m-%d') if ticket.due_date else 'None'
            changes.append(f"Due date changed from {old_date_str} to {new_date_str}")
            app.logger.debug(f"Due date changed from {old_due_date} to {ticket.due_date}")

        # Always mark the ticket as modified to ensure due date changes are saved
        db.session.add(ticket)
        
        if changes:
            ticket.log_history(current_user, "edited", ", ".join(changes))
            
        # Always commit changes
        db.session.commit()
        
        if changes:
            flash('Ticket updated successfully', 'success')
        else:
            flash('No changes made to ticket', 'info')

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
            priority_level=form.priority_level.data
        )
        db.session.add(category)
        db.session.commit()
        flash('Category added successfully', 'success')
        return redirect(url_for('tickets.manage_categories'))

    categories = TicketCategory.query.order_by(TicketCategory.name).all()
    
    # Get active tickets for the sidebar
    active_sidebar_tickets = Ticket.query.filter(
        Ticket.status.in_([TicketStatus.OPEN, TicketStatus.IN_PROGRESS, TicketStatus.PENDING])
    ).order_by(
        Ticket.priority.desc(),
        Ticket.created_at.desc()
    ).limit(5).all()
    
    return render_template('tickets/manage_categories.html', 
                         categories=categories,
                         active_sidebar_tickets=active_sidebar_tickets,
                         form=form)

@tickets.route('/tickets/categories/edit/<int:category_id>', methods=['GET', 'POST'])
@login_required
def edit_category(category_id):
    """Edit an existing ticket category"""
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('tickets.tickets_dashboard'))
        
    category = TicketCategory.query.get_or_404(category_id)
    
    form = TicketCategoryForm(obj=category)
    if form.validate_on_submit():
        category.name = form.name.data
        category.description = form.description.data
        category.priority_level = form.priority_level.data
        
        db.session.commit()
        flash('Category updated successfully', 'success')
        return redirect(url_for('tickets.manage_categories'))
        
    # Get active tickets for the sidebar
    active_sidebar_tickets = Ticket.query.filter(
        Ticket.status.in_([TicketStatus.OPEN, TicketStatus.IN_PROGRESS, TicketStatus.PENDING])
    ).order_by(
        Ticket.priority.desc(),
        Ticket.created_at.desc()
    ).limit(5).all()
    
    return render_template('tickets/edit_category.html',
                           category=category,
                           form=form,
                           active_sidebar_tickets=active_sidebar_tickets)
                           
@tickets.route('/tickets/categories/delete/<int:category_id>')
@login_required
def delete_category(category_id):
    """Delete a ticket category"""
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('tickets.tickets_dashboard'))
        
    category = TicketCategory.query.get_or_404(category_id)
    
    # Check if the category is in use by any tickets
    if Ticket.query.filter_by(category_id=category_id).first():
        flash('Cannot delete category that is used by existing tickets', 'error')
        return redirect(url_for('tickets.manage_categories'))
    
    try:
        db.session.delete(category)
        db.session.commit()
        flash('Category deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error deleting category: {str(e)}")
        flash('Error deleting category', 'error')
        
    return redirect(url_for('tickets.manage_categories'))
    
    
@tickets.route('/tickets/<int:ticket_id>/archive')
@login_required
def archive_ticket(ticket_id):
    """Archive a ticket (mark it as archived)"""
    ticket = Ticket.query.get_or_404(ticket_id)
    
    # Check if the user is allowed to archive the ticket
    if not current_user.is_admin and current_user.id != ticket.created_by and current_user.id != ticket.assigned_to:
        flash('You do not have permission to archive this ticket', 'error')
        return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))
    
    try:
        # Mark the ticket as archived
        ticket.archived = True
        
        # Add a history entry
        history = TicketHistory(
            ticket_id=ticket.id,
            user_id=current_user.id,
            action="archived",
            details="Ticket was archived",
            created_at=datetime.now(pytz.UTC)
        )
        db.session.add(history)
        
        db.session.commit()
        flash('Ticket archived successfully', 'success')
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error archiving ticket: {str(e)}")
        flash('Error archiving ticket', 'error')
    
    # Redirect back to the tickets dashboard
    return redirect(url_for('tickets.tickets_dashboard'))


@tickets.route('/tickets/<int:ticket_id>/unarchive')
@login_required
def unarchive_ticket(ticket_id):
    """Unarchive a ticket (mark it as not archived)"""
    ticket = Ticket.query.get_or_404(ticket_id)
    
    # Check if the user is allowed to unarchive the ticket
    if not current_user.is_admin and current_user.id != ticket.created_by and current_user.id != ticket.assigned_to:
        flash('You do not have permission to unarchive this ticket', 'error')
        return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))
    
    try:
        # Mark the ticket as not archived
        ticket.archived = False
        
        # Add a history entry
        history = TicketHistory(
            ticket_id=ticket.id,
            user_id=current_user.id,
            action="unarchived",
            details="Ticket was unarchived",
            created_at=datetime.now(pytz.UTC)
        )
        db.session.add(history)
        
        db.session.commit()
        flash('Ticket unarchived successfully', 'success')
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error unarchiving ticket: {str(e)}")
        flash('Error unarchiving ticket', 'error')
    
    # Redirect back to the tickets dashboard
    return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))


@tickets.route('/tickets/archived')
@login_required
def archived_tickets():
    """View archived tickets"""
    # Get all archived tickets, ordered by creation date (newest first)
    tickets = Ticket.query.filter(Ticket.archived == True).order_by(Ticket.created_at.desc()).all()
    
    # Convert SQLAlchemy objects to simple dictionaries
    archived_tickets = []
    for ticket in tickets:
        ticket_dict = {
            'id': ticket.id,
            'title': ticket.title,
            'status': ticket.status,
            'priority': ticket.priority,
            'assigned_to': ticket.assigned_to,
            'created_by': ticket.created_by,
            'created_at': ticket.created_at,
            'updated_at': ticket.updated_at,
            'due_date': ticket.due_date,
            'category': {
                'id': ticket.category.id,
                'name': ticket.category.name
            }
        }
        
        # Add assigned technician info if available
        if ticket.assigned_technician:
            ticket_dict['assigned_technician'] = {
                'username': ticket.assigned_technician.username
            }
        else:
            ticket_dict['assigned_technician'] = None
            
        archived_tickets.append(ticket_dict)
    
    # Get active tickets for the sidebar
    active_sidebar_tickets = Ticket.query.filter(
        Ticket.status.in_([TicketStatus.OPEN, TicketStatus.IN_PROGRESS, TicketStatus.PENDING])
    ).order_by(
        Ticket.priority.desc(),
        Ticket.created_at.desc()
    ).limit(5).all()
    
    return render_template('tickets/archived.html', 
                         tickets=archived_tickets,
                         ticket_count=len(archived_tickets),
                         active_sidebar_tickets=active_sidebar_tickets)
                         
                         
@tickets.route('/tickets/batch-archive', methods=['POST'])
@login_required
def batch_archive_tickets():
    """Batch archive tickets based on criteria"""
    if not current_user.is_admin:
        flash('Only administrators can perform batch archive operations', 'error')
        return redirect(url_for('tickets.tickets_dashboard'))
    
    # Get filter criteria from form
    status = request.form.get('status', 'all')
    date_before_str = request.form.get('date_before')
    
    # Build the query
    query = Ticket.query.filter(Ticket.archived == False)  # Only consider non-archived tickets
    
    # Apply status filter
    if status != 'all':
        query = query.filter(Ticket.status == status)
    
    # Apply date filter if provided
    if date_before_str:
        try:
            # Parse the date string into a datetime object
            date_before = datetime.strptime(date_before_str, '%Y-%m-%d')
            # Set to the end of the day
            date_before = date_before.replace(hour=23, minute=59, second=59, tzinfo=pytz.UTC)
            # Filter tickets updated before this date
            query = query.filter(Ticket.updated_at < date_before)
        except ValueError:
            flash('Invalid date format', 'error')
            return redirect(url_for('tickets.tickets_dashboard'))
    
    # Execute the query to get the tickets to archive
    tickets_to_archive = query.all()
    count = len(tickets_to_archive)
    
    if count == 0:
        flash('No tickets matched the criteria for archiving', 'info')
        return redirect(url_for('tickets.tickets_dashboard'))
    
    try:
        # Archive each ticket and create history entries
        for ticket in tickets_to_archive:
            ticket.archived = True
            
            # Add a history entry
            history = TicketHistory(
                ticket_id=ticket.id,
                user_id=current_user.id,
                action="archived",
                details="Ticket was archived in batch operation",
                created_at=datetime.now(pytz.UTC)
            )
            db.session.add(history)
        
        # Commit all changes at once
        db.session.commit()
        flash(f'Successfully archived {count} tickets', 'success')
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error in batch archiving tickets: {str(e)}")
        flash(f'Error archiving tickets: {str(e)}', 'error')
    
    return redirect(url_for('tickets.tickets_dashboard'))