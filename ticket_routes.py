from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from forms import TicketForm, TicketCommentForm, TicketCategoryForm
from models import db, Ticket, TicketCategory, TicketComment, TicketHistory, User, TicketStatus
from datetime import datetime
import pytz

tickets = Blueprint('tickets', __name__)

@tickets.route('/tickets/dashboard')
@login_required
def tickets_dashboard():
    """Display all tickets with filtering options"""
    status_filter = request.args.get('status', 'all')
    category_filter = request.args.get('category', 'all')

    # Base query
    query = Ticket.query

    # Apply filters
    if status_filter != 'all':
        query = query.filter(Ticket.status == status_filter)
    if category_filter != 'all':
        query = query.filter(Ticket.category_id == category_filter)

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
    # Convert TicketStatus class attributes to a list of status values
    ticket_statuses = [status for status in vars(TicketStatus).values() 
                      if isinstance(status, str) and not status.startswith('_')]

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
        ticket = Ticket(
            title=form.title.data,
            description=form.description.data,
            category_id=form.category_id.data,
            priority=form.priority.data,
            created_by=current_user.id,
            assigned_to=form.assigned_to.data if current_user.is_admin else None,
            due_date=form.due_date.data
        )
        db.session.add(ticket)
        ticket.log_history(current_user, "created")
        db.session.commit()
        flash('Ticket created successfully', 'success')
        return redirect(url_for('tickets.view_ticket', ticket_id=ticket.id))
    
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
    
    comment_form = TicketCommentForm()
    return render_template('tickets/view.html', 
                         ticket=ticket,
                         comment_form=comment_form,
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