from flask import Blueprint, render_template, request, jsonify, session, current_app
from flask_login import current_user, login_required
from models import DataCollector, Bank, Item, Organization, db
from utils.permissions import require_admin_role
from datetime import datetime
import json

data_collectors_bp = Blueprint('data_collectors', __name__)

@data_collectors_bp.route('/')
@login_required
@require_admin_role()
def index():
    """List all active data collectors - Admin only"""
    collectors = DataCollector.query.filter_by(is_active=True).order_by(DataCollector.created_at.desc()).all()
    
    # Get statistics
    total_collectors = DataCollector.query.count()
    active_collectors = DataCollector.query.filter_by(is_active=True).count()
    inactive_collectors = DataCollector.query.filter_by(is_active=False).count()
    
    # Get recent activity
    recent_collectors = DataCollector.query.order_by(DataCollector.updated_at.desc()).limit(5).all()
    
    stats = {
        'total': total_collectors,
        'active': active_collectors,
        'inactive': inactive_collectors
    }
    
    return render_template('data_collectors/index.html', 
                         collectors=collectors, 
                         stats=stats,
                         recent_collectors=recent_collectors)

@data_collectors_bp.route('/<int:collector_id>')
@login_required
@require_admin_role()
def view(collector_id):
    """View a specific data collector"""
    collector = DataCollector.query.get_or_404(collector_id)
    
    # Get collected data count
    data_count = 0
    if collector.data_type == 'items':
        data_count = Item.query.filter_by(creator_name='Data Collector').count()
    elif collector.data_type == 'organizations':
        data_count = Organization.query.filter_by(created_by=collector.id).count()
    
    return render_template('data_collectors/view.html', 
                         collector=collector, 
                         data_count=data_count)

@data_collectors_bp.route('/run/<int:collector_id>', methods=['POST'])
@login_required
@require_admin_role()
def run_collector(collector_id):
    """Run a specific data collector"""
    collector = DataCollector.query.get_or_404(collector_id)
    
    try:
        from utils.advanced_data_collector import advanced_collector
        result = advanced_collector.run_collector(collector.id)
        
        return jsonify({
            'success': True,
            'message': f'Data collector "{collector.name}" started successfully!',
            'result': result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error running data collector: {str(e)}'
        }), 500

@data_collectors_bp.route('/toggle/<int:collector_id>', methods=['POST'])
@login_required
@require_admin_role()
def toggle_collector(collector_id):
    """Toggle data collector active status"""
    collector = DataCollector.query.get_or_404(collector_id)
    collector.is_active = not collector.is_active
    collector.updated_at = datetime.utcnow()
    db.session.commit()
    
    status = 'activated' if collector.is_active else 'deactivated'
    return jsonify({
        'success': True,
        'message': f'Data collector "{collector.name}" {status} successfully!',
        'is_active': collector.is_active
    })

@data_collectors_bp.route('/data/<int:collector_id>')
@login_required
@require_admin_role()
def view_data(collector_id):
    """View data collected by a specific collector"""
    collector = DataCollector.query.get_or_404(collector_id)
    
    # Get collected data based on collector type
    collected_data = []
    if collector.data_type == 'items':
        collected_data = Item.query.filter_by(creator_name='Data Collector').limit(50).all()
    elif collector.data_type == 'organizations':
        collected_data = Organization.query.filter_by(created_by=collector.id).limit(50).all()
    
    return render_template('data_collectors/data.html', 
                         collector=collector, 
                         collected_data=collected_data)

