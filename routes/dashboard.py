from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from models import User, Deal, Item, Profile, Notification, Earning, Review, Information, ButtonConfiguration, ItemType, Wallet, db
from utils.wallet_service import WalletService
from utils.analytics import AnalyticsService, track_performance, track_errors
from utils.caching import cached, QueryCache, ViewCache
from utils.security import rate_limit, security_headers, threat_detection, validate_input
from utils.permissions import require_permission
from datetime import datetime, timedelta

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@login_required
@require_permission('dashboard', 'view')
@rate_limit(limit=60, window=3600)  # 60 requests per hour
@security_headers
@threat_detection
@track_performance('dashboard_load', 'ms')
@track_errors
def index():
    # Get user's active deals
    active_deals = Deal.query.filter(
        (Deal.provider_id == current_user.id) | 
        (Deal.consumer_id == current_user.id) |
        (Deal.connector_id == current_user.id)
    ).filter(Deal.status.in_(['pending', 'in_progress'])).all()
    
    # Get recent notifications
    notifications = Notification.query.filter_by(user_id=current_user.id, is_read=False)\
        .order_by(Notification.created_at.desc()).limit(5).all()
    
    # Get recent earnings
    recent_earnings = Earning.query.filter_by(user_id=current_user.id)\
        .order_by(Earning.created_at.desc()).limit(5).all()
    
    # Get user's items
    user_items = Item.query.join(Profile).filter(Profile.user_id == current_user.id)\
        .order_by(Item.created_at.desc()).limit(5).all()
    
    # Dashboard stats
    # Calculate total views for user's items
    total_views = db.session.query(db.func.sum(Item.views)).join(Profile)\
        .filter(Profile.user_id == current_user.id).scalar() or 0
    
    # Calculate coming deals (pending deals)
    coming_deals = Deal.query.filter(
        (Deal.provider_id == current_user.id) | 
        (Deal.consumer_id == current_user.id) |
        (Deal.connector_id == current_user.id)
    ).filter(Deal.status == 'pending').count()
    
    # Get wallet information
    wallet = WalletService.get_or_create_wallet(current_user.id)
    
    stats = {
        'total_views': total_views,
        'coming_deals': coming_deals,
        'active_deals': len(active_deals),
        'total_earnings': db.session.query(db.func.sum(Earning.amount))\
            .filter_by(user_id=current_user.id, status='paid').scalar() or 0,
        'wallet_balance': wallet.balance,
        'pending_earnings': db.session.query(db.func.sum(Earning.amount))\
            .filter_by(user_id=current_user.id, status='pending').scalar() or 0
    }
    
    # Check if user has internal roles
    internal_roles = [role for role in current_user.roles if role.is_internal]
    
    # Get dynamic dashboard buttons
    dashboard_buttons = ButtonConfiguration.query.filter_by(
        is_active=True, 
        is_visible=True
    ).order_by(ButtonConfiguration.order_index, ButtonConfiguration.created_at).all()
    
    return render_template('dashboard/index.html', 
                         active_deals=active_deals,
                         notifications=notifications,
                         recent_earnings=recent_earnings,
                         user_items=user_items,
                         stats=stats,
                         internal_roles=internal_roles,
                         dashboard_buttons=dashboard_buttons,
                         wallet=wallet)

@dashboard_bp.route('/stats')
@login_required
@require_permission('dashboard', 'view')
def stats():
    # Get detailed statistics for the user
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    
    stats = {
        'deals_this_month': Deal.query.filter(
            (Deal.provider_id == current_user.id) | 
            (Deal.consumer_id == current_user.id)
        ).filter(Deal.created_at >= thirty_days_ago).count(),
        'earnings_this_month': db.session.query(db.func.sum(Earning.amount))\
            .filter(Earning.user_id == current_user.id)\
            .filter(Earning.created_at >= thirty_days_ago)\
            .filter(Earning.status == 'paid').scalar() or 0,
        'items_created': Item.query.join(Profile).filter(Profile.user_id == current_user.id).count(),
        'reviews_received': db.session.query(db.func.avg(Review.rating))\
            .filter(Review.reviewee_id == current_user.id).scalar() or 0
    }
    
    return jsonify(stats)

@dashboard_bp.route('/notifications')
@login_required
@require_permission('notifications', 'view')
def notifications():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    notifications = Notification.query.filter_by(user_id=current_user.id)\
        .order_by(Notification.created_at.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template('dashboard/notifications.html', notifications=notifications)

@dashboard_bp.route('/notifications/<int:notification_id>/read', methods=['POST'])
@login_required
@require_permission('notifications', 'edit')
def mark_notification_read(notification_id):
    notification = Notification.query.filter_by(
        id=notification_id, 
        user_id=current_user.id
    ).first_or_404()
    
    notification.is_read = True
    db.session.commit()
    
    return jsonify({'success': True})

@dashboard_bp.route('/notifications/mark-all-read', methods=['POST'])
@login_required
@require_permission('notifications', 'edit')
def mark_all_notifications_read():
    Notification.query.filter_by(user_id=current_user.id, is_read=False)\
        .update({'is_read': True})
    db.session.commit()
    
    return jsonify({'success': True})

@dashboard_bp.route('/add-info')
@login_required
@require_permission('information', 'create')
def add_info():
    """Redirect to the Need chatbot flow based on button configuration"""
    from models import ButtonConfiguration
    
    # Get the Add Need button configuration
    add_need_button = ButtonConfiguration.query.filter_by(
        button_key='add_need', 
        is_active=True
    ).first()
    
    if add_need_button and add_need_button.target_type == 'chatbot':
        flow_id = add_need_button.target_value
    else:
        # Fallback to default Need Form chatbot flow (ID: 15)
        flow_id = 15
    
    return redirect(url_for('chatbot.start_flow', flow_id=flow_id))

@dashboard_bp.route('/add-need')
@login_required
@require_permission('needs', 'create')
def add_need():
    """Dynamic Add Need route that supports profile and organization context"""
    from models import ItemType
    
    # Get the Need item type configuration
    need_item_type = ItemType.query.filter_by(
        name='need', 
        is_active=True
    ).first()
    
    # Check for data storage mapping for need item type
    from models import DataStorageMapping
    need_mapping = DataStorageMapping.query.filter_by(
        item_type_id=need_item_type.id,
        is_active=True
    ).first() if need_item_type else None
    
    if need_mapping:
        flow_id = need_mapping.chatbot_id
    else:
        # Fallback to default Need Form chatbot flow (ID: 15)
        flow_id = 15
    
    # Get context parameters
    profile_id = request.args.get('profile_id')
    organization_id = request.args.get('organization_id')
    
    # Build redirect URL with context
    if profile_id:
        return redirect(url_for('chatbot.start_flow', flow_id=flow_id, profile_id=profile_id))
    elif organization_id:
        return redirect(url_for('chatbot.start_flow', flow_id=flow_id, organization_id=organization_id))
    else:
        return redirect(url_for('chatbot.start_flow', flow_id=flow_id))

@dashboard_bp.route('/edit-info/<int:info_id>', methods=['GET', 'POST'])
@login_required
@require_permission('information', 'edit')
def edit_info(info_id):
    info = Information.query.get_or_404(info_id)
    
    # Check if user owns this information
    if info.created_by != current_user.id:
        flash('You do not have permission to edit this information', 'error')
        return redirect(url_for('dashboard.add_info'))
    
    if request.method == 'POST':
        info.title = request.form.get('title')
        info.description = request.form.get('description')
        info.category = request.form.get('category')
        info.source = request.form.get('source')
        info.contact_info = request.form.get('contact_info')
        info.location = request.form.get('location')
        info.priority = request.form.get('priority', 'medium')
        tags = request.form.get('tags', '').split(',') if request.form.get('tags') else []
        info.tags = [tag.strip() for tag in tags if tag.strip()]
        info.is_public = request.form.get('is_public') == 'on'
        
        db.session.commit()
        flash('Information updated successfully', 'success')
        return redirect(url_for('dashboard.add_info'))
    
    return render_template('dashboard/edit_info.html', info=info)

@dashboard_bp.route('/delete-info/<int:info_id>', methods=['POST'])
@login_required
@require_permission('information', 'delete')
def delete_info(info_id):
    info = Information.query.get_or_404(info_id)
    
    # Check if user owns this information
    if info.created_by != current_user.id:
        if request.is_json:
            return jsonify({'success': False, 'message': 'Permission denied'})
        flash('You do not have permission to delete this information', 'error')
        return redirect(url_for('dashboard.add_info'))
    
    # Also delete the corresponding item if it exists
    item = Item.query.filter_by(
        profile_id=current_user.profiles[0].id if current_user.profiles else None,
        title=info.title,
        item_type='information'
    ).first()
    
    if item:
        db.session.delete(item)
    
    db.session.delete(info)
    db.session.commit()
    
    if request.is_json:
        return jsonify({'success': True, 'message': 'Information deleted successfully'})
    
    flash('Information deleted successfully', 'success')
    return redirect(url_for('dashboard.add_info'))
