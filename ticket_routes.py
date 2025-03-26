from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from forms import TicketForm, TicketCommentForm, TicketCategoryForm
from models import db, Ticket, TicketCategory, TicketComment, TicketHistory, User, TicketStatus
from datetime import datetime
import pytz
from app import app  # Import app for logging

# Update Blueprint to use the correct template directory
tickets = Blueprint('tickets', __name__)

@tickets.route('/tickets/dashboard')
@login_required
def tickets_dashboard():
    """Display all tickets with filtering options"""
    status_filter = request.args.get('status', 'all')
    category_filter = request.args.get('category', 'all')
    priority_filter = request.args.get('priority', 'all')

    # Base query
    query = Ticket.query

    # Apply filters
    if status_filter != 'all':
        query = query.filter(Ticket.status == status_filter)
    if category_filter != 'all':
        query = query.filter(Ticket.category_id == category_filter)
    if priority_filter != 'all':
        query = query.filter(Ticket.priority == int(priority_filter))

    # Different views based on user role
    if current_user.is_admin:
        tickets = query.order_by(Ticket.created_at.desc()).all()
    else:
        # Show tickets created by or assigned to the user
        tickets = query.filter(
            (Ticket.created_by == current_user.id) | 
            (Ticket.assigned_to == current_user.id)
        ).order_by(Ticket.created_at.desc()).all()

    categories = TicketCategory.query.all()
    # Get all valid ticket statuses
    ticket_statuses = [
        TicketStatus.OPEN,
        TicketStatus.IN_PROGRESS,
        TicketStatus.PENDING,
        TicketStatus.RESOLVED,
        TicketStatus.CLOSED
    ]

    return render_template('tickets/dashboard.html', 
                         tickets=tickets,
                         categories=categories,
                         ticket_statuses=ticket_statuses)

@tickets.route('/tickets/create', methods=['GET', 'POST'])
@login_required
def create_ticket():
    """Create a new ticket"""
    form = TicketForm()

    # Populate category choices
    form.category_id.choices = [(c.id, c.name) for c in TicketCategory.query.all()]

    # Populate technician choices for admin users
    if current_user.is_admin:
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
                assigned_to=form.assigned_to.data if current_user.is_admin else None,
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

    # Check if user has access to this ticket
    if not (current_user.is_admin or 
            ticket.created_by == current_user.id or 
            ticket.assigned_to == current_user.id):
        flash('You do not have permission to view this ticket', 'error')
        return redirect(url_for('tickets.tickets_dashboard'))

    # Create forms for comments and editing
    comment_form = TicketCommentForm()
    form = TicketForm()

    # Populate form with current ticket data
    if request.method == 'GET':
        form.title.data = ticket.title
        form.description.data = ticket.description
        form.category_id.data = ticket.category_id
        form.priority.data = ticket.priority
        form.due_date.data = ticket.due_date

        # Populate category choices
        form.category_id.choices = [(c.id, c.name) for c in TicketCategory.query.all()]

        # Populate technician choices for admin users
        if current_user.is_admin:
            form.assigned_to.choices = [(u.id, u.username) for u in User.query.all()]

    return render_template('tickets/view.html', 
                         ticket=ticket,
                         comment_form=comment_form,
                         form=form,
                         TicketStatus=TicketStatus)

@tickets.route('/tickets/<int:ticket_id>/comment', methods=['POST'])
@login_required
def add_comment(ticket_id):
    """Add a comment to a ticket"""
    ticket = Ticket.query.get_or_404(ticket_id)
    form = TicketCommentForm()
    
    if form.validate_on_submit():
        comment = ticket.add_comment(current_user, form.content.data)
        ticket.log_history(current_user, "commented")
        db.session.commit()
        flash('Comment added successfully', 'success')
    
    return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))

@tickets.route('/tickets/<int:ticket_id>/status', methods=['POST'])
@login_required
def update_status(ticket_id):
    """Update ticket status"""
    ticket = Ticket.query.get_or_404(ticket_id)
    new_status = request.form.get('status')
    
    if new_status not in vars(TicketStatus).values():
        return jsonify({'error': 'Invalid status'}), 400
    
    old_status = ticket.status
    ticket.status = new_status
    ticket.log_history(current_user, "status_changed", 
                      f"Status changed from {old_status} to {new_status}")
    db.session.commit()
    
    return jsonify({'message': 'Status updated successfully'})

@tickets.route('/tickets/<int:ticket_id>/assign', methods=['POST'])
@login_required
def assign_ticket(ticket_id):
    """Assign ticket to a technician"""
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    ticket = Ticket.query.get_or_404(ticket_id)
    technician_id = request.form.get('technician_id')
    
    if technician_id:
        technician = User.query.get_or_404(technician_id)
        ticket.assigned_to = technician.id
        ticket.log_history(current_user, "assigned", 
                         f"Assigned to {technician.username}")
    else:
        ticket.assigned_to = None
        ticket.log_history(current_user, "unassigned")
    
    db.session.commit()
    return jsonify({'message': 'Ticket assigned successfully'})

@tickets.route('/tickets/<int:ticket_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_ticket(ticket_id):
    """Edit an existing ticket"""
    ticket = Ticket.query.get_or_404(ticket_id)

    # Check if user has permission to edit
    if not (current_user.is_admin or ticket.created_by == current_user.id):
        flash('You do not have permission to edit this ticket', 'error')
        return redirect(url_for('tickets.tickets_dashboard'))

    form = TicketForm()

    if form.validate_on_submit():
        old_title = ticket.title
        old_description = ticket.description
        old_category_id = ticket.category_id
        old_priority = ticket.priority

        ticket.title = form.title.data
        ticket.description = form.description.data
        ticket.category_id = form.category_id.data
        ticket.priority = form.priority.data
        ticket.due_date = form.due_date.data

        # Log changes in ticket history
        changes = []
        if old_title != ticket.title:
            changes.append(f"Title changed from '{old_title}' to '{ticket.title}'")
        if old_description != ticket.description:
            changes.append("Description updated")
        if old_category_id != ticket.category_id:
            changes.append(f"Category changed")
        if old_priority != ticket.priority:
            changes.append(f"Priority changed from {old_priority} to {ticket.priority}")

        if changes:
            ticket.log_history(current_user, "edited", ", ".join(changes))
            db.session.commit()
            flash('Ticket updated successfully', 'success')

        return redirect(url_for('tickets.view_ticket', ticket_id=ticket.id))

    return redirect(url_for('tickets.view_ticket', ticket_id=ticket.id))


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