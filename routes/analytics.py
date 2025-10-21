from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from models import db, SearchAnalytics, Item, ItemType, ChatbotFlow, User
from utils.permissions import require_permission
from datetime import datetime, timedelta
from sqlalchemy import func, desc
import json

analytics_bp = Blueprint('analytics', __name__)

@analytics_bp.route('/')
@login_required
@require_permission('analytics', 'view')
def dashboard():
    """Main analytics dashboard"""
    return render_template('analytics/dashboard.html')

@analytics_bp.route('/field-usage')
@login_required
@require_permission('analytics', 'view')
def field_usage():
    """Field usage analytics - which fields are searched/filtered most"""
    
    # Get field usage statistics
    field_stats = db.session.query(
        SearchAnalytics.item_type,
        SearchAnalytics.filter_field,
        func.sum(SearchAnalytics.search_count).label('total_searches'),
        func.count(SearchAnalytics.id).label('unique_searches'),
        func.max(SearchAnalytics.last_searched).label('last_used')
    ).group_by(
        SearchAnalytics.item_type,
        SearchAnalytics.filter_field
    ).order_by(desc('total_searches')).all()
    
    # Process data for visualization
    field_usage_data = []
    for stat in field_stats:
        field_usage_data.append({
            'item_type': stat.item_type,
            'field_name': stat.filter_field,
            'total_searches': stat.total_searches,
            'unique_searches': stat.unique_searches,
            'last_used': stat.last_used.isoformat() if stat.last_used else None,
            'search_frequency': stat.total_searches / stat.unique_searches if stat.unique_searches > 0 else 0
        })
    
    # Get top fields by item type
    top_fields_by_type = {}
    for item_type in ['product', 'service', 'event', 'project', 'fund', 'experience', 'opportunity', 'information', 'observation', 'hidden_gem', 'auction', 'need']:
        type_stats = [f for f in field_usage_data if f['item_type'] == item_type]
        top_fields_by_type[item_type] = sorted(type_stats, key=lambda x: x['total_searches'], reverse=True)[:5]
    
    return render_template('analytics/field_usage.html', 
                         field_usage_data=field_usage_data,
                         top_fields_by_type=top_fields_by_type)

@analytics_bp.route('/search-patterns')
@login_required
@require_permission('analytics', 'view')
def search_patterns():
    """Search patterns and trends analysis"""
    
    # Get search trends over time (last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    
    search_trends = db.session.query(
        func.date(SearchAnalytics.last_searched).label('search_date'),
        SearchAnalytics.item_type,
        func.sum(SearchAnalytics.search_count).label('daily_searches')
    ).filter(
        SearchAnalytics.last_searched >= thirty_days_ago
    ).group_by(
        func.date(SearchAnalytics.last_searched),
        SearchAnalytics.item_type
    ).order_by('search_date').all()
    
    # Process trends data
    trends_data = {}
    for trend in search_trends:
        date_str = trend.search_date.isoformat()
        if date_str not in trends_data:
            trends_data[date_str] = {}
        trends_data[date_str][trend.item_type] = trend.daily_searches
    
    # Get popular search terms
    popular_terms = db.session.query(
        SearchAnalytics.search_term,
        SearchAnalytics.item_type,
        func.sum(SearchAnalytics.search_count).label('total_searches')
    ).filter(
        SearchAnalytics.search_term.isnot(None),
        SearchAnalytics.search_term != ''
    ).group_by(
        SearchAnalytics.search_term,
        SearchAnalytics.item_type
    ).order_by(desc('total_searches')).limit(50).all()
    
    return render_template('analytics/search_patterns.html',
                         trends_data=trends_data,
                         popular_terms=popular_terms)

@analytics_bp.route('/optimization-suggestions')
@login_required
@require_permission('analytics', 'view')
def optimization_suggestions():
    """Smart optimization suggestions based on analytics"""
    
    # Get field usage statistics
    field_stats = db.session.query(
        SearchAnalytics.item_type,
        SearchAnalytics.filter_field,
        func.sum(SearchAnalytics.search_count).label('total_searches'),
        func.count(SearchAnalytics.id).label('unique_searches')
    ).group_by(
        SearchAnalytics.item_type,
        SearchAnalytics.filter_field
    ).all()
    
    suggestions = []
    
    # Analyze each field for optimization opportunities
    for stat in field_stats:
        item_type = stat.item_type
        field_name = stat.filter_field
        total_searches = stat.total_searches
        unique_searches = stat.unique_searches
        
        # Calculate metrics
        search_frequency = total_searches / unique_searches if unique_searches > 0 else 0
        
        # Generate suggestions based on usage patterns
        if total_searches >= 100:  # High usage threshold
            if search_frequency >= 5:  # High frequency per user
                suggestions.append({
                    'type': 'promote_to_indexed',
                    'item_type': item_type,
                    'field_name': field_name,
                    'reason': f'High usage ({total_searches} searches) with high frequency ({search_frequency:.1f} searches/user)',
                    'priority': 'high',
                    'action': f'Add database index for {field_name} in {item_type} items'
                })
        
        if total_searches >= 50 and search_frequency >= 3:
            suggestions.append({
                'type': 'promote_to_column',
                'item_type': item_type,
                'field_name': field_name,
                'reason': f'Moderate usage ({total_searches} searches) with good frequency ({search_frequency:.1f} searches/user)',
                'priority': 'medium',
                'action': f'Consider promoting {field_name} from JSON to dedicated column for {item_type}'
            })
        
        if total_searches >= 20 and search_frequency >= 2:
            suggestions.append({
                'type': 'optimize_ui',
                'item_type': item_type,
                'field_name': field_name,
                'reason': f'Growing usage ({total_searches} searches) - users finding this field useful',
                'priority': 'low',
                'action': f'Make {field_name} more prominent in {item_type} search UI'
            })
    
    # Sort by priority and usage
    suggestions.sort(key=lambda x: (x['priority'] == 'high', x['priority'] == 'medium', x['priority'] == 'low'), reverse=True)
    
    # Get current database structure for comparison
    current_columns = []
    try:
        with db.engine.connect() as conn:
            result = conn.execute(db.text("PRAGMA table_info(item)"))
            current_columns = [row[1] for row in result.fetchall()]
    except Exception as e:
        print(f"Error getting current columns: {e}")
    
    return render_template('analytics/optimization_suggestions.html',
                         suggestions=suggestions,
                         current_columns=current_columns)

@analytics_bp.route('/api/field-usage-data')
@login_required
@require_permission('analytics', 'view')
def api_field_usage_data():
    """API endpoint for field usage data"""
    
    # Get field usage by item type
    field_usage = db.session.query(
        SearchAnalytics.item_type,
        SearchAnalytics.filter_field,
        func.sum(SearchAnalytics.search_count).label('total_searches')
    ).group_by(
        SearchAnalytics.item_type,
        SearchAnalytics.filter_field
    ).all()
    
    # Format for charts
    chart_data = {
        'labels': [],
        'datasets': []
    }
    
    item_types = list(set([f.item_type for f in field_usage]))
    colors = ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40']
    
    for i, item_type in enumerate(item_types):
        type_data = [f for f in field_usage if f.item_type == item_type]
        chart_data['datasets'].append({
            'label': item_type.title(),
            'data': [f.total_searches for f in type_data],
            'backgroundColor': colors[i % len(colors)]
        })
        
        if not chart_data['labels']:
            chart_data['labels'] = [f.filter_field for f in type_data]
    
    return jsonify(chart_data)

@analytics_bp.route('/api/search-trends')
@login_required
@require_permission('analytics', 'view')
def api_search_trends():
    """API endpoint for search trends data"""
    
    # Get last 30 days of search data
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    
    trends = db.session.query(
        func.date(SearchAnalytics.last_searched).label('search_date'),
        SearchAnalytics.item_type,
        func.sum(SearchAnalytics.search_count).label('daily_searches')
    ).filter(
        SearchAnalytics.last_searched >= thirty_days_ago
    ).group_by(
        func.date(SearchAnalytics.last_searched),
        SearchAnalytics.item_type
    ).order_by('search_date').all()
    
    # Format for time series chart
    dates = list(set([t.search_date for t in trends]))
    dates.sort()
    
    chart_data = {
        'labels': [d.isoformat() for d in dates],
        'datasets': []
    }
    
    item_types = list(set([t.item_type for t in trends]))
    colors = ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40']
    
    for i, item_type in enumerate(item_types):
        type_trends = {t.search_date: t.daily_searches for t in trends if t.item_type == item_type}
        chart_data['datasets'].append({
            'label': item_type.title(),
            'data': [type_trends.get(d, 0) for d in dates],
            'borderColor': colors[i % len(colors)],
            'backgroundColor': colors[i % len(colors)] + '20',
            'fill': False
        })
    
    return jsonify(chart_data)

@analytics_bp.route('/track-search', methods=['POST'])
def track_search():
    """Track a search event for analytics"""
    try:
        data = request.get_json()
        
        item_type = data.get('item_type')
        search_term = data.get('search_term', '')
        filter_field = data.get('filter_field')
        filter_value = data.get('filter_value', '')
        
        if not item_type:
            return jsonify({'success': False, 'message': 'Item type required'})
        
        # Check if this search already exists
        existing = SearchAnalytics.query.filter_by(
            item_type=item_type,
            search_term=search_term,
            filter_field=filter_field,
            filter_value=filter_value
        ).first()
        
        if existing:
            existing.search_count += 1
            existing.last_searched = datetime.utcnow()
        else:
            analytics = SearchAnalytics(
                item_type=item_type,
                search_term=search_term,
                filter_field=filter_field,
                filter_value=filter_value,
                search_count=1,
                user_id=current_user.id if current_user.is_authenticated else None
            )
            db.session.add(analytics)
        
        db.session.commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@analytics_bp.route('/export-analytics')
@login_required
@require_permission('analytics', 'export')
def export_analytics():
    """Export analytics data as CSV"""
    import csv
    from flask import Response
    
    # Get all search analytics data
    analytics_data = SearchAnalytics.query.order_by(SearchAnalytics.last_searched.desc()).all()
    
    # Create CSV response
    output = []
    output.append(['Item Type', 'Search Term', 'Filter Field', 'Filter Value', 'Search Count', 'Last Searched', 'User ID'])
    
    for data in analytics_data:
        output.append([
            data.item_type,
            data.search_term or '',
            data.filter_field or '',
            data.filter_value or '',
            data.search_count,
            data.last_searched.isoformat() if data.last_searched else '',
            data.user_id or ''
        ])
    
    # Create CSV string
    csv_string = '\n'.join([','.join([str(cell) for cell in row]) for row in output])
    
    return Response(
        csv_string,
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=search_analytics.csv'}
    )















