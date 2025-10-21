from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import Feedback, User, db
from utils.permissions import require_permission
from datetime import datetime

feedback_bp = Blueprint('feedback', __name__)

@feedback_bp.route('/feedback/submit', methods=['GET', 'POST'])
def submit_feedback():
    """Display feedback form and handle submission"""
    if request.method == 'GET':
        return render_template('feedback/submit.html')
    
    # Handle POST request (form submission)
    try:
        # Get form data
        feedback_type = request.form.get('type')
        subject = request.form.get('subject')
        message = request.form.get('message')
        priority = request.form.get('priority', 'medium')
        
        # Validate required fields
        if not all([feedback_type, subject, message]):
            return jsonify({'success': False, 'message': 'All required fields must be filled'})
        
        # Create feedback record
        feedback = Feedback(
            user_id=current_user.id if current_user.is_authenticated else None,
            type=feedback_type,
            subject=subject,
            message=message,
            priority=priority,
            status='pending'
        )
        
        db.session.add(feedback)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Feedback submitted successfully'})
        
    except Exception as e:
        db.session.rollback()
        print(f"Error submitting feedback: {e}")
        return jsonify({'success': False, 'message': 'Error submitting feedback'})

@feedback_bp.route('/admin/feedback')
@login_required
@require_permission('feedback', 'view_all')
def admin_feedback():
    """Admin interface to view and manage feedback"""
    # Check if user is admin
    if not any(role.is_internal for role in current_user.roles):
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('auth.profile'))
    
    # Get filter parameters
    status_filter = request.args.get('status', 'all')
    type_filter = request.args.get('type', 'all')
    priority_filter = request.args.get('priority', 'all')
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Build query
    query = Feedback.query
    
    if status_filter != 'all':
        query = query.filter(Feedback.status == status_filter)
    if type_filter != 'all':
        query = query.filter(Feedback.type == type_filter)
    if priority_filter != 'all':
        query = query.filter(Feedback.priority == priority_filter)
    
    # Order by created date (newest first)
    query = query.order_by(Feedback.created_at.desc())
    
    # Paginate
    feedback_list = query.paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # Get statistics
    total_feedback = Feedback.query.count()
    pending_feedback = Feedback.query.filter_by(status='pending').count()
    resolved_feedback = Feedback.query.filter_by(status='resolved').count()
    
    return render_template('admin/feedback_management.html',
                         feedback_list=feedback_list,
                         total_feedback=total_feedback,
                         pending_feedback=pending_feedback,
                         resolved_feedback=resolved_feedback,
                         current_filters={
                             'status': status_filter,
                             'type': type_filter,
                             'priority': priority_filter
                         })

@feedback_bp.route('/admin/feedback/<int:feedback_id>')
@login_required
@require_permission('feedback', 'view_all')
def view_feedback(feedback_id):
    """View detailed feedback"""
    # Check if user is admin
    if not any(role.is_internal for role in current_user.roles):
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('auth.profile'))
    
    feedback = Feedback.query.get_or_404(feedback_id)
    return render_template('admin/feedback_detail.html', feedback=feedback)

@feedback_bp.route('/admin/feedback/<int:feedback_id>/update', methods=['POST'])
@login_required
def update_feedback(feedback_id):
    """Update feedback status and admin notes"""
    # Check if user is admin
    if not any(role.is_internal for role in current_user.roles):
        return jsonify({'success': False, 'message': 'Access denied'})
    
    try:
        status = request.form.get('status')
        admin_notes = request.form.get('admin_notes', '')
        
        # Validate status
        valid_statuses = ['pending', 'in_progress', 'resolved', 'closed']
        if status not in valid_statuses:
            return jsonify({'success': False, 'message': 'Invalid status provided'})
        
        feedback = Feedback.query.get_or_404(feedback_id)
        
        # Update feedback
        feedback.status = status
        feedback.admin_notes = admin_notes
        feedback.updated_at = datetime.utcnow()
        
        if status == 'resolved':
            feedback.resolved_at = datetime.utcnow()
            feedback.resolved_by = current_user.id
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Feedback updated successfully'})
        
    except Exception as e:
        db.session.rollback()
        print(f"Error updating feedback: {e}")
        return jsonify({'success': False, 'message': f'Error updating feedback: {str(e)}'})

@feedback_bp.route('/admin/feedback/<int:feedback_id>/delete', methods=['POST'])
@login_required
def delete_feedback(feedback_id):
    """Delete feedback"""
    # Check if user is admin
    if not any(role.is_internal for role in current_user.roles):
        return jsonify({'success': False, 'message': 'Access denied'})
    
    try:
        feedback = Feedback.query.get_or_404(feedback_id)
        db.session.delete(feedback)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Feedback deleted successfully'})
        
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting feedback: {e}")
        return jsonify({'success': False, 'message': f'Error deleting feedback: {str(e)}'})
