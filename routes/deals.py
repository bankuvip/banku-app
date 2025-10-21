from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from models import Deal, DealItem, DealMessage, Item, User, UserNeed, UserRole, Role, Earning, Notification, Profile, db, DealRequest, DealRequestUpdate, DealRequestCategory
from utils.permissions import require_permission
from datetime import datetime

deals_bp = Blueprint('deals', __name__)

@deals_bp.route('/')
@login_required
@require_permission('deals', 'view')
def index():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    status_filter = request.args.get('status', 'all')
    
    # Build query based on user's role
    query = Deal.query.filter(
        (Deal.provider_id == current_user.id) | 
        (Deal.consumer_id == current_user.id) |
        (Deal.connector_id == current_user.id)
    )
    
    if status_filter != 'all':
        query = query.filter(Deal.status == status_filter)
    
    deals = query.order_by(Deal.created_at.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template('deals/index.html', deals=deals, status_filter=status_filter)

@deals_bp.route('/create', methods=['GET', 'POST'])
@login_required
@require_permission('deals', 'create')
def create():
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        
        # Get data from form
        consumer_id = data.get('consumer_id')
        provider_id = data.get('provider_id')
        need_url = data.get('need_url')
        item_url = data.get('item_url')
        connector_id = data.get('connector_id')
        title = data.get('title')
        description = data.get('description')
        total_amount = float(data.get('total_amount', 0))
        
        # Set connector to current user if not specified
        if not connector_id:
            connector_id = current_user.id
        
        # Extract IDs from URLs
        need_id = None
        item_id = None
        if need_url:
            need_match = need_url.split('/needs/')[-1].split('/')[0]
            if need_match.isdigit():
                need_id = int(need_match)
        if item_url:
            item_match = item_url.split('/items/')[-1].split('/')[0]
            if item_match.isdigit():
                item_id = int(item_match)
        
        if not provider_id or not consumer_id or not need_url or not item_url or not need_id or not item_id:
            if request.is_json:
                return jsonify({'success': False, 'message': 'Valid need and item URLs are required'})
            flash('Valid need and item URLs are required', 'error')
            return render_template('deals/create.html')
        
        if not title or not description:
            if request.is_json:
                return jsonify({'success': False, 'message': 'Title and description are required'})
            flash('Title and description are required', 'error')
            return render_template('deals/create.html')
        
        if total_amount <= 0:
            if request.is_json:
                return jsonify({'success': False, 'message': 'Total amount must be greater than 0'})
            flash('Total amount must be greater than 0', 'error')
            return render_template('deals/create.html')
        
        # Create deal
        deal = Deal(
            provider_id=provider_id,
            consumer_id=consumer_id,
            connector_id=connector_id,
            title=title,
            description=description,
            total_amount=total_amount,
            currency=data.get('currency', 'USD'),
            escrow_amount=total_amount * 0.1  # 10% escrow
        )
        
        db.session.add(deal)
        db.session.flush()  # Get deal ID
        
        # Add the selected item to deal
        item = Item.query.get(item_id)
        if item:
            deal_item = DealItem(
                deal_id=deal.id,
                item_id=item.id,
                unit_price=item.price or 0
            )
            db.session.add(deal_item)
        
        # Create system message
        system_message = DealMessage(
            deal_id=deal.id,
            sender_id=current_user.id,
            message=f"Deal created by {current_user.first_name} {current_user.last_name}",
            is_system=True
        )
        db.session.add(system_message)
        
        # Create notifications
        provider = User.query.get(provider_id)
        consumer = User.query.get(consumer_id)
        
        if provider:
            notification = Notification(
                user_id=provider.id,
                title="New Deal Created",
                message=f"A new deal '{title}' has been created with you as provider",
                notification_type="deal_created",
                data={'deal_id': deal.id}
            )
            db.session.add(notification)
        
        if consumer and consumer.id != current_user.id:
            notification = Notification(
                user_id=consumer.id,
                title="New Deal Created",
                message=f"A new deal '{title}' has been created for you",
                notification_type="deal_created",
                data={'deal_id': deal.id}
            )
            db.session.add(notification)
        
        db.session.commit()
        
        if request.is_json:
            return jsonify({
                'success': True,
                'message': 'Deal created successfully',
                'deal_id': deal.id
            })
        
        flash('Deal created successfully', 'success')
        return redirect(url_for('deals.detail', deal_id=deal.id))
    
    return render_template('deals/create.html')

@deals_bp.route('/<int:deal_id>')
@login_required
@require_permission('deals', 'view')
def detail(deal_id):
    deal = Deal.query.get_or_404(deal_id)
    
    # Check if user has access to this deal
    if not (deal.provider_id == current_user.id or 
            deal.consumer_id == current_user.id or 
            deal.connector_id == current_user.id):
        flash('You do not have access to this deal', 'error')
        return redirect(url_for('deals.index'))
    
    # Get deal messages
    messages = DealMessage.query.filter_by(deal_id=deal_id)\
        .order_by(DealMessage.created_at.asc()).all()
    
    # Get deal needs (needs associated with this deal)
    # For now, we'll get needs from the consumer - in a real implementation,
    # you might want to store deal-need relationships in the database
    deal_needs = UserNeed.query.filter_by(user_id=deal.consumer_id).limit(5).all()
    
    # Get deal activities (combine messages and deal events)
    deal_activities = []
    
    # Add deal creation activity
    deal_activities.append({
        'type': 'deal_created',
        'title': 'Deal Created',
        'description': f'Deal "{deal.title}" was created',
        'created_at': deal.created_at,
        'user': deal.connector or deal.provider
    })
    
    # Add status change activities from messages
    for message in messages:
        if message.is_system and 'status changed' in message.message.lower():
            deal_activities.append({
                'type': 'status_changed',
                'title': 'Status Updated',
                'description': message.message,
                'created_at': message.created_at,
                'user': message.sender
            })
        elif not message.is_system:
            deal_activities.append({
                'type': 'message_sent',
                'title': 'Message Sent',
                'description': message.message[:100] + ('...' if len(message.message) > 100 else ''),
                'created_at': message.created_at,
                'user': message.sender
            })
    
    # Add item addition activities
    for deal_item in deal.items:
        deal_activities.append({
            'type': 'item_added',
            'title': 'Item Added',
            'description': f'Item "{deal_item.item.title}" was added to the deal',
            'created_at': deal.created_at,  # Use deal creation time as approximation
            'user': deal.provider
        })
    
    # Sort activities by creation time (newest first)
    deal_activities.sort(key=lambda x: x['created_at'], reverse=True)
    
    return render_template('deals/detail.html', deal=deal, messages=messages, deal_needs=deal_needs, deal_activities=deal_activities)

@deals_bp.route('/<int:deal_id>/update-status', methods=['POST'])
@login_required
@require_permission('deals', 'edit')
def update_status(deal_id):
    deal = Deal.query.get_or_404(deal_id)
    
    # Check if user has permission to update status
    if not (deal.provider_id == current_user.id or 
            deal.consumer_id == current_user.id or 
            deal.connector_id == current_user.id):
        return jsonify({'success': False, 'message': 'Permission denied'})
    
    data = request.get_json()
    new_status = data.get('status')
    
    if new_status not in ['pending', 'in_progress', 'completed', 'cancelled']:
        return jsonify({'success': False, 'message': 'Invalid status'})
    
    old_status = deal.status
    deal.status = new_status
    
    if new_status == 'completed':
        deal.completed_at = datetime.utcnow()
        
        # Calculate earnings
        commission = deal.total_amount * deal.commission_rate
        provider_earning = deal.total_amount - commission
        
        # Create earnings records
        if deal.connector_id:
            connector_earning = Earning(
                user_id=deal.connector_id,
                deal_id=deal.id,
                amount=commission * 0.5,  # 50% of commission to connector
                earning_type='connector',
                description=f'Commission from deal: {deal.title}',
                status='pending'
            )
            db.session.add(connector_earning)
        
        provider_earning_record = Earning(
            user_id=deal.provider_id,
            deal_id=deal.id,
            amount=provider_earning,
            earning_type='deal_completion',
            description=f'Payment from deal: {deal.title}',
            status='pending'
        )
        db.session.add(provider_earning_record)
    
    # Create system message
    system_message = DealMessage(
        deal_id=deal.id,
        sender_id=current_user.id,
        message=f"Deal status changed from {old_status} to {new_status}",
        is_system=True
    )
    db.session.add(system_message)
    
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Status updated successfully'})

@deals_bp.route('/<int:deal_id>/message', methods=['POST'])
@login_required
@require_permission('deals', 'edit')
def send_message(deal_id):
    deal = Deal.query.get_or_404(deal_id)
    
    # Check if user has access to this deal
    if not (deal.provider_id == current_user.id or 
            deal.consumer_id == current_user.id or 
            deal.connector_id == current_user.id):
        return jsonify({'success': False, 'message': 'Permission denied'})
    
    data = request.get_json()
    message_text = data.get('message')
    
    if not message_text:
        return jsonify({'success': False, 'message': 'Message cannot be empty'})
    
    message = DealMessage(
        deal_id=deal_id,
        sender_id=current_user.id,
        message=message_text
    )
    
    db.session.add(message)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Message sent successfully'})

@deals_bp.route('/<int:deal_id>/update-status', methods=['POST'])
@login_required
@require_permission('deals', 'edit')
def update_deal_status(deal_id):
    """Update deal status via AJAX"""
    deal = Deal.query.get_or_404(deal_id)
    
    # Check if user has permission to update this deal
    if not (deal.provider_id == current_user.id or 
            deal.consumer_id == current_user.id or 
            deal.connector_id == current_user.id):
        return jsonify({'success': False, 'message': 'Permission denied'})
    
    data = request.get_json()
    new_status = data.get('status')
    
    if not new_status:
        return jsonify({'success': False, 'message': 'Status is required'})
    
    if new_status not in ['pending', 'in_progress', 'completed', 'cancelled']:
        return jsonify({'success': False, 'message': 'Invalid status'})
    
    old_status = deal.status
    deal.status = new_status
    deal.updated_at = datetime.utcnow()
    
    # Create system message
    system_message = DealMessage(
        deal_id=deal.id,
        sender_id=current_user.id,
        message=f"Deal status changed from {old_status} to {new_status} by {current_user.first_name} {current_user.last_name}",
        is_system=True
    )
    db.session.add(system_message)
    
    # Create notifications for other participants
    participants = [deal.provider, deal.consumer]
    if deal.connector:
        participants.append(deal.connector)
    
    for participant in participants:
        if participant and participant.id != current_user.id:
            notification = Notification(
                user_id=participant.id,
                title="Deal Status Updated",
                message=f"Deal '{deal.title}' status changed to {new_status.replace('_', ' ').title()}",
                notification_type="deal_status_update",
                data={'deal_id': deal.id, 'status': new_status}
            )
            db.session.add(notification)
    
    db.session.commit()
    
    return jsonify({
        'success': True, 
        'message': f'Deal status updated to {new_status.replace("_", " ").title()}'
    })

@deals_bp.route('/api/needs/<int:need_id>')
@login_required
@require_permission('deals', 'view')
def api_get_need(need_id):
    """API endpoint to get need data by ID"""
    need = UserNeed.query.get_or_404(need_id)
    
    return jsonify({
        'success': True,
        'need': {
            'id': need.id,
            'title': need.title,
            'description': need.description,
            'user_id': need.user_id,
            'user': {
                'id': need.user.id,
                'first_name': need.user.first_name,
                'last_name': need.user.last_name,
                'email': need.user.email
            }
        }
    })

@deals_bp.route('/api/items/<int:item_id>')
@login_required
@require_permission('deals', 'view')
def api_get_item(item_id):
    """API endpoint to get item data by ID"""
    item = Item.query.get_or_404(item_id)
    
    return jsonify({
        'success': True,
        'item': {
            'id': item.id,
            'title': item.title,
            'description': item.short_description,
            'price': item.price,
            'creator_id': item.creator_id,
            'creator': {
                'id': item.creator.id,
                'first_name': item.creator.first_name,
                'last_name': item.creator.last_name,
                'email': item.creator.email
            }
        }
    })

@deals_bp.route('/api/users/<int:user_id>')
@login_required
@require_permission('deals', 'view')
def api_get_user(user_id):
    """API endpoint to get user data by ID"""
    user = User.query.get_or_404(user_id)
    
    return jsonify({
        'success': True,
        'user': {
            'id': user.id,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email,
            'username': user.username
        }
    })

# =============================================================================
# DEAL REQUESTS ROUTES
# =============================================================================

@deals_bp.route('/my-deal-requests/')
@login_required
@require_permission('deal_requests', 'view_own')
def my_deal_requests():
    """User's own deal requests page"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    status_filter = request.args.get('status', 'all')
    
    # Build query for user's requests
    query = DealRequest.query.filter_by(user_id=current_user.id)
    
    if status_filter != 'all':
        query = query.filter(DealRequest.status == status_filter)
    
    requests = query.order_by(DealRequest.created_at.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)
    
    # Get categories for filter dropdown
    categories = DealRequestCategory.query.filter_by(is_active=True).all()
    
    return render_template('deals/my_deal_requests.html', 
                         requests=requests, 
                         status_filter=status_filter,
                         categories=categories)

@deals_bp.route('/my-deal-requests/create', methods=['GET', 'POST'])
@login_required
@require_permission('deal_requests', 'create')
def create_deal_request():
    """Create a new deal request"""
    if request.method == 'POST':
        try:
            # Handle both JSON and form data
            if request.is_json:
                data = request.get_json()
            else:
                data = request.form
            
            # Get form data
            item_id = data.get('item_id')
            title = data.get('title')
            need_description = data.get('need_description')
            budget_min = float(data.get('budget_min', 0)) if data.get('budget_min') else None
            budget_max = float(data.get('budget_max', 0)) if data.get('budget_max') else None
            urgency_level = data.get('urgency_level', 'medium')
            category = data.get('category')
            tags = data.get('tags', '').split(',') if data.get('tags') else []
            tags = [tag.strip() for tag in tags if tag.strip()]
            special_requirements = data.get('special_requirements', '')
            timeline = data.get('timeline', '')
            
            # Validation
            if not item_id or not title or not need_description:
                return jsonify({'success': False, 'message': 'Title and description are required'})
            
            # Check if item exists
            item = Item.query.get(item_id)
            if not item:
                return jsonify({'success': False, 'message': 'Item not found'})
            
            # Create deal request
            deal_request = DealRequest(
                user_id=current_user.id,
                item_id=item_id,
                title=title,
                need_description=need_description,
                budget_min=budget_min,
                budget_max=budget_max,
                urgency_level=urgency_level,
                category=category,
                tags=tags,
                special_requirements=special_requirements,
                timeline=timeline
            )
            
            db.session.add(deal_request)
            db.session.flush()  # Get the ID
            
            # Update item request count
            item.request_count = (item.request_count or 0) + 1
            
            # Create initial update
            initial_update = DealRequestUpdate(
                deal_request_id=deal_request.id,
                user_id=current_user.id,
                update_text=f"Request created: {title}",
                is_connector_update=False
            )
            db.session.add(initial_update)
            
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Deal request created successfully',
                'request_id': deal_request.id
            })
            
        except Exception as e:
            import traceback
            print(f"Error creating deal request: {e}")
            print(f"Traceback: {traceback.format_exc()}")
            db.session.rollback()
            return jsonify({'success': False, 'message': f'Error creating request: {str(e)}'})
    
    # GET request - show form
    item_id = request.args.get('item_id')
    item = None
    if item_id:
        item = Item.query.get(item_id)
    
    try:
        categories = DealRequestCategory.query.filter_by(is_active=True).all()
    except Exception as e:
        print(f"Error fetching categories: {e}")
        categories = []
    
    return render_template('deals/create_deal_request.html', 
                         item=item, 
                         categories=categories)

@deals_bp.route('/my-deal-requests/<int:request_id>')
@login_required
@require_permission('deal_requests', 'view_own')
def view_deal_request(request_id):
    """View deal request details"""
    try:
        deal_request = DealRequest.query.get_or_404(request_id)
        
        # Check if user has access to this request
        if deal_request.user_id != current_user.id:
            flash('You do not have access to this request', 'error')
            return redirect(url_for('deals.my_deal_requests'))
        
        # Check if item exists and is accessible
        if not deal_request.item:
            flash('The requested item is no longer available', 'error')
            return redirect(url_for('deals.my_deal_requests'))
        
        # Get updates
        updates = DealRequestUpdate.query.filter_by(deal_request_id=request_id)\
            .order_by(DealRequestUpdate.created_at.asc()).all()
        
        # Calculate days open
        from datetime import datetime
        days_open = (datetime.utcnow() - deal_request.created_at).days
        
        return render_template('deals/deal_request_detail.html', 
                             deal_request=deal_request, 
                             updates=updates,
                             days_open=days_open)
    except Exception as e:
        import traceback
        print(f"Error viewing deal request {request_id}: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        flash(f'Error loading deal request: {str(e)}', 'error')
        return redirect(url_for('deals.my_deal_requests'))

@deals_bp.route('/my-deal-requests/<int:request_id>/add-update', methods=['POST'])
@login_required
@require_permission('deal_requests', 'add_update')
def add_request_update(request_id):
    """Add update to deal request"""
    deal_request = DealRequest.query.get_or_404(request_id)
    
    # Check if user has access
    if deal_request.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Permission denied'})
    
    data = request.get_json()
    update_text = data.get('update_text')
    
    if not update_text:
        return jsonify({'success': False, 'message': 'Update text is required'})
    
    # Create update
    update = DealRequestUpdate(
        deal_request_id=request_id,
        user_id=current_user.id,
        update_text=update_text,
        is_connector_update=False
    )
    
    db.session.add(update)
    deal_request.updated_at = datetime.utcnow()
    db.session.commit()
    
    # Send notifications to assigned connector if any
    if deal_request.assigned_connector_id:
        notification = Notification(
            user_id=deal_request.assigned_connector_id,
            title="New Update on Deal Request",
            message=f"User added an update to request: {deal_request.title}",
            notification_type="deal_request_update",
            data={'request_id': request_id}
        )
        db.session.add(notification)
        db.session.commit()
    
    return jsonify({'success': True, 'message': 'Update added successfully'})

@deals_bp.route('/my-deal-requests/<int:request_id>/delete', methods=['POST'])
@login_required
@require_permission('deal_requests', 'delete_own')
def delete_deal_request(request_id):
    """Delete deal request"""
    deal_request = DealRequest.query.get_or_404(request_id)
    
    # Check if user has access and request can be deleted
    if deal_request.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Permission denied'})
    
    if deal_request.status != 'open':
        return jsonify({'success': False, 'message': 'Only open requests can be deleted'})
    
    # Update item request count
    item = Item.query.get(deal_request.item_id)
    if item and item.request_count > 0:
        item.request_count -= 1
    
    db.session.delete(deal_request)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Request deleted successfully'})

# =============================================================================
# CONNECTOR/STAFF DEAL REQUESTS ROUTES
# =============================================================================

@deals_bp.route('/deal-requests/')
@login_required
@require_permission('deal_requests', 'view_all')
def all_deal_requests():
    """All deal requests page for connectors and staff"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    status_filter = request.args.get('status', 'all')
    category_filter = request.args.get('category', 'all')
    urgency_filter = request.args.get('urgency', 'all')
    
    # Build query
    query = DealRequest.query
    
    if status_filter != 'all':
        query = query.filter(DealRequest.status == status_filter)
    
    if category_filter != 'all':
        query = query.filter(DealRequest.category == category_filter)
    
    if urgency_filter != 'all':
        query = query.filter(DealRequest.urgency_level == urgency_filter)
    
    requests = query.order_by(DealRequest.created_at.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)
    
    # Get categories for filter dropdown
    categories = DealRequestCategory.query.filter_by(is_active=True).all()
    
    return render_template('deals/all_deal_requests.html', 
                         requests=requests, 
                         status_filter=status_filter,
                         category_filter=category_filter,
                         urgency_filter=urgency_filter,
                         categories=categories)

@deals_bp.route('/deal-requests/<int:request_id>')
@login_required
@require_permission('deal_requests', 'view_all')
def view_deal_request_staff(request_id):
    """View deal request details for connectors/staff"""
    deal_request = DealRequest.query.get_or_404(request_id)
    
    # Get updates
    updates = DealRequestUpdate.query.filter_by(deal_request_id=request_id)\
        .order_by(DealRequestUpdate.created_at.asc()).all()
    
    # Calculate days open
    from datetime import datetime
    days_open = (datetime.utcnow() - deal_request.created_at).days
    
    return render_template('deals/deal_request_staff_detail.html', 
                         deal_request=deal_request, 
                         updates=updates,
                         days_open=days_open)

@deals_bp.route('/deal-requests/<int:request_id>/take', methods=['POST'])
@login_required
@require_permission('deal_requests', 'take_request')
def take_deal_request(request_id):
    """Take/assign deal request to current user"""
    deal_request = DealRequest.query.get_or_404(request_id)
    
    # Check if request is available
    if deal_request.status != 'open':
        return jsonify({'success': False, 'message': 'Request is not available'})
    
    # Assign to current user
    deal_request.assigned_connector_id = current_user.id
    deal_request.status = 'assigned'
    deal_request.updated_at = datetime.utcnow()
    
    # Create system update
    system_update = DealRequestUpdate(
        deal_request_id=request_id,
        user_id=current_user.id,
        update_text=f"Request assigned to {current_user.first_name} {current_user.last_name}",
        is_connector_update=True
    )
    db.session.add(system_update)
    
    # Send notification to user
    notification = Notification(
        user_id=deal_request.user_id,
        title="Deal Request Assigned",
        message=f"Your request '{deal_request.title}' has been assigned to a connector",
        notification_type="deal_request_assigned",
        data={'request_id': request_id}
    )
    db.session.add(notification)
    
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Request assigned successfully'})

@deals_bp.route('/deal-requests/<int:request_id>/unassign', methods=['POST'])
@login_required
@require_permission('deal_requests', 'assign_request')
def unassign_deal_request(request_id):
    """Unassign deal request from current user"""
    deal_request = DealRequest.query.get_or_404(request_id)
    
    # Check if current user is assigned to this request
    if deal_request.assigned_connector_id != current_user.id:
        return jsonify({'success': False, 'message': 'You are not assigned to this request'})
    
    if deal_request.status not in ['assigned', 'in_progress']:
        return jsonify({'success': False, 'message': 'Request cannot be unassigned in its current status'})
    
    # Unassign the request
    deal_request.assigned_connector_id = None
    deal_request.status = 'open'
    deal_request.updated_at = datetime.utcnow()
    
    # Create system update
    system_update = DealRequestUpdate(
        deal_request_id=request_id,
        user_id=current_user.id,
        update_text=f"Request unassigned by {current_user.first_name} {current_user.last_name}",
        is_connector_update=True
    )
    db.session.add(system_update)
    
    # Send notification to user
    notification = Notification(
        user_id=deal_request.user_id,
        title="Deal Request Unassigned",
        message=f"Your request '{deal_request.title}' has been unassigned and is available again",
        notification_type="deal_request_unassigned",
        data={'request_id': request_id}
    )
    db.session.add(notification)
    
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Request unassigned successfully'})

@deals_bp.route('/deal-requests/<int:request_id>/add-update', methods=['POST'])
@login_required
@require_permission('deal_requests', 'add_update')
def add_connector_update(request_id):
    """Add connector update to deal request"""
    deal_request = DealRequest.query.get_or_404(request_id)
    
    # Check if user is assigned to this request
    if deal_request.assigned_connector_id != current_user.id:
        return jsonify({'success': False, 'message': 'You are not assigned to this request'})
    
    data = request.get_json()
    update_text = data.get('update_text')
    
    if not update_text:
        return jsonify({'success': False, 'message': 'Update text is required'})
    
    # Create update
    update = DealRequestUpdate(
        deal_request_id=request_id,
        user_id=current_user.id,
        update_text=update_text,
        is_connector_update=True
    )
    
    db.session.add(update)
    deal_request.updated_at = datetime.utcnow()
    db.session.commit()
    
    # Send notification to user
    notification = Notification(
        user_id=deal_request.user_id,
        title="New Update on Your Request",
        message=f"Connector added an update to your request: {deal_request.title}",
        notification_type="deal_request_update",
        data={'request_id': request_id}
    )
    db.session.add(notification)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Update added successfully'})

@deals_bp.route('/deal-requests/<int:request_id>/create-deal', methods=['POST'])
@login_required
@require_permission('deals', 'create')
def create_deal_from_request(request_id):
    """Create deal from request"""
    deal_request = DealRequest.query.get_or_404(request_id)
    
    # Check if user is assigned to this request
    if deal_request.assigned_connector_id != current_user.id:
        return jsonify({'success': False, 'message': 'You are not assigned to this request'})
    
    # Redirect to deal creation with pre-filled data
    return redirect(url_for('deals.create', 
                          consumer_id=deal_request.user_id,
                          item_id=deal_request.item_id,
                          connector_id=current_user.id,
                          title=deal_request.title,
                          description=deal_request.need_description))
