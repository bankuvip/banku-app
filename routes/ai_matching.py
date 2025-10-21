"""
AI Matching Routes
Handles user needs, matching, and recommendations
"""

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, Item, User, UserNeed, NeedItemMatch, MatchingFeedback, MatchingSession
from utils.ai_matching import ai_matching_engine
from utils.permissions import require_admin_or_connector, require_permission
from datetime import datetime, timedelta
import json
import re
from difflib import SequenceMatcher

ai_matching_bp = Blueprint('ai_matching', __name__)

def calculate_keyword_match(need_desc, item_desc):
    """Calculate keyword similarity between need and item descriptions"""
    if not need_desc or not item_desc:
        return 0
    
    # Extract keywords (simple word extraction)
    need_words = set(re.findall(r'\b\w+\b', need_desc.lower()))
    item_words = set(re.findall(r'\b\w+\b', item_desc.lower()))
    
    if not need_words or not item_words:
        return 0
    
    # Calculate Jaccard similarity
    intersection = need_words.intersection(item_words)
    union = need_words.union(item_words)
    
    return len(intersection) / len(union) if union else 0

def calculate_category_match(need_type, item_category):
    """Calculate category match score"""
    if not need_type or not item_category:
        return 0
    
    # Simple exact match for now
    return 1.0 if need_type.lower() == item_category.lower() else 0.5

def calculate_location_match(need_location, item_location):
    """Calculate location match score"""
    if not need_location or not item_location:
        return 0.5  # Neutral if no location data
    
    # Simple exact match for now
    return 1.0 if need_location.lower() == item_location.lower() else 0.3

def calculate_price_match(need_budget, item_price):
    """Calculate price compatibility score"""
    if not need_budget or not item_price:
        return 0.5  # Neutral if no price data
    
    try:
        budget = float(need_budget)
        price = float(item_price)
        
        if price <= budget:
            return 1.0  # Perfect match
        elif price <= budget * 1.2:
            return 0.8  # Good match (20% over budget)
        elif price <= budget * 1.5:
            return 0.6  # Acceptable match (50% over budget)
        else:
            return 0.2  # Poor match (over 50% budget)
    except (ValueError, TypeError):
        return 0.5  # Neutral if can't parse prices

def calculate_urgency_match(need_urgency, item_availability):
    """Calculate urgency vs availability match"""
    if not need_urgency or not item_availability:
        return 0.5
    
    urgency_scores = {'low': 0.2, 'medium': 0.5, 'high': 0.8, 'urgent': 1.0}
    availability_scores = {'unavailable': 0.0, 'limited': 0.3, 'available': 0.7, 'immediate': 1.0}
    
    urgency_score = urgency_scores.get(need_urgency.lower(), 0.5)
    availability_score = availability_scores.get(item_availability.lower(), 0.5)
    
    # Higher urgency needs items with better availability
    return min(urgency_score, availability_score) + (0.2 if urgency_score <= availability_score else 0)

@ai_matching_bp.route('/')
@login_required
@require_permission('ai_matching', 'access_dashboard')
def dashboard():
    """AI Matching dashboard"""
    # Get new needs count (recently added needs)
    new_needs_count = UserNeed.query.filter(
        UserNeed.created_at >= datetime.utcnow() - timedelta(days=7)
    ).count()
    
    # Get new items count (recently added items)
    new_items_count = Item.query.filter(
        Item.created_at >= datetime.utcnow() - timedelta(days=7)
    ).count()
    
    # Get recent needs (last 10 needs added to system)
    recent_needs = UserNeed.query.order_by(UserNeed.created_at.desc()).limit(10).all()
    
    # Get recent items (last 10 items added to system)
    recent_items = Item.query.order_by(Item.created_at.desc()).limit(10).all()
    
    # Get AI recommendations for all users
    connector_recommendations = ai_matching_engine.get_user_recommendations(current_user.id, limit=10)
    
    return render_template('ai_matching/dashboard.html',
                         new_needs_count=new_needs_count,
                         new_items_count=new_items_count,
                         recent_needs=recent_needs,
                         recent_items=recent_items,
                         connector_recommendations=connector_recommendations)

@ai_matching_bp.route('/create-need', methods=['GET', 'POST'])
@login_required
@require_admin_or_connector()
def create_need():
    """Create a new user need"""
    if request.method == 'POST':
        try:
            data = request.get_json() if request.is_json else request.form
            
            # Create new need
            need = UserNeed(
                user_id=current_user.id,
                title=data.get('title'),
                description=data.get('description'),
                need_type=data.get('need_type'),
                urgency_level=data.get('urgency_level', 'medium'),
                budget_min=float(data.get('budget_min')) if data.get('budget_min') else None,
                budget_max=float(data.get('budget_max')) if data.get('budget_max') else None,
                location=data.get('location'),
                timeline=data.get('timeline'),
                is_public=data.get('is_public', 'true').lower() == 'true'
            )
            
            # Set flexible requirements
            requirements = {}
            for key, value in data.items():
                if key not in ['title', 'description', 'need_type', 'urgency_level', 
                              'budget_min', 'budget_max', 'location', 'timeline', 'is_public']:
                    if value:
                        requirements[key] = value
            
            if requirements:
                need.set_requirements_dict(requirements)
            
            # Set expiration date based on timeline
            if need.timeline == 'ASAP':
                need.expires_at = datetime.utcnow() + timedelta(days=1)
            elif need.timeline == '1 week':
                need.expires_at = datetime.utcnow() + timedelta(weeks=1)
            elif need.timeline == '1 month':
                need.expires_at = datetime.utcnow() + timedelta(days=30)
            else:
                need.expires_at = datetime.utcnow() + timedelta(days=7)  # Default
            
            db.session.add(need)
            db.session.commit()
            
            # Find matches immediately
            matches = ai_matching_engine.find_matches(need, limit=10)
            
            if request.is_json:
                return jsonify({
                    'success': True,
                    'need_id': need.id,
                    'matches_found': len(matches),
                    'message': f'Need created successfully! Found {len(matches)} potential matches.'
                })
            else:
                return redirect(url_for('ai_matching.view_need', need_id=need.id))
                
        except Exception as e:
            db.session.rollback()
            if request.is_json:
                return jsonify({'success': False, 'message': f'Error creating need: {str(e)}'})
            else:
                return render_template('ai_matching/create_need.html', error=str(e))
    
    return render_template('ai_matching/create_need.html')

@ai_matching_bp.route('/need/<int:need_id>')
@login_required
@require_admin_or_connector()
def view_need(need_id):
    """View a specific need and its matches"""
    need = UserNeed.query.filter(
        UserNeed.id == need_id,
        UserNeed.user_id == current_user.id
    ).first_or_404()
    
    # Get matches for this need
    matches = NeedItemMatch.query.filter(
        NeedItemMatch.need_id == need_id,
        NeedItemMatch.is_active == True
    ).order_by(NeedItemMatch.match_score.desc()).all()
    
    return render_template('ai_matching/view_need.html',
                         need=need,
                         matches=matches)

@ai_matching_bp.route('/matches/<int:need_id>')
@login_required
@require_admin_or_connector()
def get_matches(need_id):
    """Get matches for a need (AJAX endpoint)"""
    need = UserNeed.query.filter(
        UserNeed.id == need_id,
        UserNeed.user_id == current_user.id
    ).first_or_404()
    
    # Find new matches
    matches = ai_matching_engine.find_matches(need, limit=20)
    
    # Format matches for JSON response
    matches_data = []
    for item, score, reason in matches:
        matches_data.append({
            'id': item.id,
            'title': item.title,
            'description': item.short_description,
            'price': item.price,
            'location': item.location,
            'category': item.category,
            'match_score': round(score, 2),
            'match_reason': reason,
            'url': url_for('profiles.item_detail', item_id=item.id)
        })
    
    return jsonify({
        'success': True,
        'matches': matches_data,
        'count': len(matches_data)
    })

@ai_matching_bp.route('/feedback', methods=['POST'])
@login_required
@require_admin_or_connector()
def submit_feedback():
    """Submit feedback on a match"""
    try:
        data = request.get_json()
        
        match_id = data.get('match_id')
        feedback_type = data.get('feedback_type')  # like, dislike, contacted
        rating = data.get('rating')
        comment = data.get('comment')
        
        if not match_id or not feedback_type:
            return jsonify({'success': False, 'message': 'Missing required fields'})
        
        # Verify match belongs to user
        match = NeedItemMatch.query.join(UserNeed).filter(
            NeedItemMatch.id == match_id,
            UserNeed.user_id == current_user.id
        ).first()
        
        if not match:
            return jsonify({'success': False, 'message': 'Match not found'})
        
        # Record feedback
        success = ai_matching_engine.record_feedback(
            match_id, current_user.id, feedback_type, rating, comment
        )
        
        if success:
            return jsonify({'success': True, 'message': 'Feedback recorded successfully'})
        else:
            return jsonify({'success': False, 'message': 'Error recording feedback'})
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@ai_matching_bp.route('/recommendations')
@login_required
@require_admin_or_connector()
def get_recommendations():
    """Get personalized recommendations"""
    recommendations = ai_matching_engine.get_recommendations(current_user.id, limit=10)
    
    recommendations_data = []
    for item in recommendations:
        recommendations_data.append({
            'id': item.id,
            'title': item.title,
            'description': item.short_description,
            'price': item.price,
            'location': item.location,
            'category': item.category,
            'url': url_for('profiles.item_detail', item_id=item.id)
        })
    
    return jsonify({
        'success': True,
        'recommendations': recommendations_data,
        'count': len(recommendations_data)
    })

@ai_matching_bp.route('/my-needs')
@login_required
@require_admin_or_connector()
def my_needs():
    """View all user's needs"""
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    needs = UserNeed.query.filter(
        UserNeed.user_id == current_user.id
    ).order_by(UserNeed.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('ai_matching/my_needs.html', needs=needs)

@ai_matching_bp.route('/my-matches')
@login_required
@require_admin_or_connector()
def my_matches():
    """View all user's matches"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    matches = NeedItemMatch.query.join(UserNeed).filter(
        UserNeed.user_id == current_user.id,
        NeedItemMatch.is_active == True
    ).order_by(NeedItemMatch.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('ai_matching/my_matches.html', matches=matches)

@ai_matching_bp.route('/analytics')
@login_required
@require_admin_or_connector()
def matching_analytics():
    """View matching analytics for user"""
    # Get user's matching statistics
    total_needs = UserNeed.query.filter(UserNeed.user_id == current_user.id).count()
    active_needs = UserNeed.query.filter(
        UserNeed.user_id == current_user.id,
        UserNeed.status == 'active'
    ).count()
    
    total_matches = NeedItemMatch.query.join(UserNeed).filter(
        UserNeed.user_id == current_user.id
    ).count()
    
    liked_matches = NeedItemMatch.query.join(UserNeed).filter(
        UserNeed.user_id == current_user.id,
        NeedItemMatch.user_liked == True
    ).count()
    
    contacted_matches = NeedItemMatch.query.join(UserNeed).filter(
        UserNeed.user_id == current_user.id,
        NeedItemMatch.user_contacted == True
    ).count()
    
    # Calculate success rate
    success_rate = (contacted_matches / total_matches * 100) if total_matches > 0 else 0
    
    # Calculate average match score
    avg_score_result = db.session.query(db.func.avg(NeedItemMatch.match_score)).join(UserNeed).filter(
        UserNeed.user_id == current_user.id
    ).scalar()
    average_score = float(avg_score_result) if avg_score_result else 0.0
    
    stats = {
        'total_needs': total_needs,
        'active_needs': active_needs,
        'total_matches': total_matches,
        'liked_matches': liked_matches,
        'contacted_matches': contacted_matches,
        'success_rate': round(success_rate, 1),
        'average_score': average_score
    }
    
    return render_template('ai_matching/analytics.html', stats=stats)

@ai_matching_bp.route('/search-items')
@login_required
@require_permission('ai_matching', 'access_dashboard')
def search_items_page():
    """AI Search Items page"""
    return render_template('ai_matching/search_items.html')

@ai_matching_bp.route('/api/search-items')
@login_required
@require_admin_or_connector()
def search_items():
    """Search for items with AI matching"""
    query = request.args.get('q', '')
    category = request.args.get('category', '')
    location = request.args.get('location', '')
    budget_min = request.args.get('budget_min', type=float)
    budget_max = request.args.get('budget_max', type=float)
    
    # Build search query
    search_query = Item.query.filter(Item.is_available == True)
    
    if query:
        search_query = search_query.filter(
            Item.title.contains(query) | Item.short_description.contains(query)
        )
    
    if category:
        search_query = search_query.filter(Item.category == category)
    
    if location:
        search_query = search_query.filter(Item.location.contains(location))
    
    if budget_min:
        search_query = search_query.filter(Item.price >= budget_min)
    
    if budget_max:
        search_query = search_query.filter(Item.price <= budget_max)
    
    # Get results
    items = search_query.order_by(Item.created_at.desc()).limit(20).all()
    
    # Format results
    results = []
    for item in items:
        results.append({
            'id': item.id,
            'title': item.title,
            'description': item.short_description,
            'price': item.price,
            'location': item.location,
            'category': item.category,
            'url': url_for('profiles.item_detail', item_id=item.id)
        })
    
    return jsonify({
        'success': True,
        'results': results,
        'count': len(results)
    })

@ai_matching_bp.route('/ai-engine')
@login_required
@require_permission('ai_matching', 'access_dashboard')
def ai_engine():
    """Get AI engine view (full recommendations)"""
    try:
        recommendations = ai_matching_engine.get_connector_recommendations(current_user.id, limit=50)
        
        return render_template('ai_matching/connector_recommendations.html',
                             recommendations=recommendations)
    except Exception as e:
        flash(f'Error loading recommendations: {str(e)}', 'error')
        return redirect(url_for('ai_matching.dashboard'))

@ai_matching_bp.route('/connector/recommendations/<int:recommendation_id>/action', methods=['POST'])
@login_required
@require_permission('ai_matching', 'manage_recommendations')
def handle_recommendation_action(recommendation_id):
    """Handle connector action on a recommendation (accept, reject, create deal)"""
    try:
        data = request.get_json()
        action = data.get('action')  # 'accept', 'reject', 'create_deal'
        
        if action not in ['accept', 'reject', 'create_deal']:
            return jsonify({'success': False, 'message': 'Invalid action'})
        
        # Update recommendation status
        success = ai_matching_engine.update_recommendation_status(
            recommendation_id, 
            action, 
            current_user.id
        )
        
        if success:
            if action == 'create_deal':
                # Redirect to create deal page with pre-filled data
                recommendation = NeedItemMatch.query.get(recommendation_id)
                return jsonify({
                    'success': True, 
                    'redirect': url_for('deals.create', 
                                      need_id=recommendation.need_id,
                                      item_id=recommendation.item_id)
                })
            else:
                return jsonify({'success': True, 'message': f'Recommendation {action}ed'})
        else:
            return jsonify({'success': False, 'message': 'Failed to update recommendation'})
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@ai_matching_bp.route('/auto-generate', methods=['POST'])
@login_required
@require_permission('ai_matching', 'manage_recommendations')
def auto_generate_recommendations():
    """Automatically generate recommendations for all active needs"""
    try:
        count = ai_matching_engine.auto_generate_recommendations()
        
        return jsonify({
            'success': True, 
            'message': f'Generated {count} new recommendations',
            'count': count
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@ai_matching_bp.route('/test-report/<int:recommendation_id>')
@login_required
@require_permission('ai_matching', 'view_reports')
def test_report(recommendation_id):
    """Simple test report page"""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Report - BankU</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    </head>
    <body>
        <div class="container-fluid py-4">
            <div class="row">
                <div class="col-12">
                    <div class="d-flex justify-content-between align-items-center mb-4">
                        <h1 class="h2 mb-0">
                            <i class="fas fa-chart-line me-2"></i>Test Report
                        </h1>
                        <a href="/ai-matching/" class="btn btn-outline-secondary">
                            <i class="fas fa-arrow-left me-1"></i>Back to Dashboard
                        </a>
                    </div>
                </div>
            </div>

            <div class="row">
                <div class="col-12">
                    <div class="card">
                        <div class="card-header">
                            <h5 class="mb-0">
                                <i class="fas fa-info-circle me-2"></i>Test Report for ID: {recommendation_id}
                            </h5>
                        </div>
                        <div class="card-body">
                            <div class="alert alert-success">
                                <h4><i class="fas fa-check-circle me-2"></i>Success!</h4>
                                <p>You have successfully navigated to the test report page.</p>
                                <p><strong>Recommendation ID:</strong> {recommendation_id}</p>
                                <p><strong>Current User:</strong> {current_user.first_name if current_user else 'Unknown'}</p>
                            </div>
                            
                            <div class="row">
                                <div class="col-md-6">
                                    <div class="card">
                                        <div class="card-header">
                                            <h6><i class="fas fa-bullhorn me-2"></i>Need Information</h6>
                                        </div>
                                        <div class="card-body">
                                            <p><strong>Title:</strong> Sample Need Title</p>
                                            <p><strong>Type:</strong> Product</p>
                                            <p><strong>Urgency:</strong> Medium</p>
                                            <p><strong>Description:</strong> This is a sample need description for testing purposes.</p>
                                        </div>
                                    </div>
                                </div>
                                <div class="col-md-6">
                                    <div class="card">
                                        <div class="card-header">
                                            <h6><i class="fas fa-box me-2"></i>Item Information</h6>
                                        </div>
                                        <div class="card-body">
                                            <p><strong>Title:</strong> Sample Item Title</p>
                                            <p><strong>Category:</strong> Service</p>
                                            <p><strong>Price:</strong> $100</p>
                                            <p><strong>Description:</strong> This is a sample item description for testing purposes.</p>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <div class="row mt-4">
                                <div class="col-12">
                                    <div class="card">
                                        <div class="card-header">
                                            <h6><i class="fas fa-analytics me-2"></i>Match Analysis</h6>
                                        </div>
                                        <div class="card-body">
                                            <div class="row">
                                                <div class="col-md-6 mb-3">
                                                    <div class="d-flex justify-content-between align-items-center">
                                                        <span><i class="fas fa-key me-2"></i>Keyword Match</span>
                                                        <span class="badge bg-success">85%</span>
                                                    </div>
                                                    <div class="progress mt-2">
                                                        <div class="progress-bar bg-success" style="width: 85%"></div>
                                                    </div>
                                                </div>
                                                <div class="col-md-6 mb-3">
                                                    <div class="d-flex justify-content-between align-items-center">
                                                        <span><i class="fas fa-tags me-2"></i>Category Match</span>
                                                        <span class="badge bg-warning">60%</span>
                                                    </div>
                                                    <div class="progress mt-2">
                                                        <div class="progress-bar bg-warning" style="width: 60%"></div>
                                                    </div>
                                                </div>
                                                <div class="col-md-6 mb-3">
                                                    <div class="d-flex justify-content-between align-items-center">
                                                        <span><i class="fas fa-map-marker-alt me-2"></i>Location Match</span>
                                                        <span class="badge bg-info">90%</span>
                                                    </div>
                                                    <div class="progress mt-2">
                                                        <div class="progress-bar bg-info" style="width: 90%"></div>
                                                    </div>
                                                </div>
                                                <div class="col-md-6 mb-3">
                                                    <div class="d-flex justify-content-between align-items-center">
                                                        <span><i class="fas fa-dollar-sign me-2"></i>Price Match</span>
                                                        <span class="badge bg-success">95%</span>
                                                    </div>
                                                    <div class="progress mt-2">
                                                        <div class="progress-bar bg-success" style="width: 95%"></div>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <div class="row mt-4">
                                <div class="col-12">
                                    <div class="card">
                                        <div class="card-header">
                                            <h6><i class="fas fa-star me-2"></i>Rate This Match</h6>
                                        </div>
                                        <div class="card-body">
                                            <div class="row">
                                                <div class="col-md-8">
                                                    <p class="text-muted">Help improve our AI matching by rating this recommendation:</p>
                                                    <div class="input-group mb-3">
                                                        <input type="range" class="form-range" min="1" max="100" value="75">
                                                        <span class="input-group-text">75%</span>
                                                    </div>
                                                    <button class="btn btn-primary">
                                                        <i class="fas fa-star me-1"></i>Submit Rating
                                                    </button>
                                                </div>
                                                <div class="col-md-4">
                                                    <div class="text-center">
                                                        <h6 class="text-muted">Current Average Rating</h6>
                                                        <h4 class="text-primary">78.5%</h4>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    </body>
    </html>
    """

@ai_matching_bp.route('/match-report/<int:recommendation_id>')
@login_required
@require_permission('ai_matching', 'view_reports')
def match_report(recommendation_id):
    """View detailed match report"""
    try:
        # Get the match record
        match = NeedItemMatch.query.get(recommendation_id)
        if not match:
            flash('Recommendation not found', 'error')
            return redirect(url_for('ai_matching.dashboard'))
        
        # Get match details
        need = match.need
        item = match.item
        need_user = match.need_user
        item_creator = match.item_creator
        
        # Calculate match analysis
        match_analysis = {
            'keyword_match': calculate_keyword_match(need.description if need else '', item.short_description if item else ''),
            'category_match': calculate_category_match(need.need_type if need else '', item.category if item else ''),
            'location_match': calculate_location_match(need.location if need else '', item.location if item else ''),
            'price_match': calculate_price_match(need.budget_range if need else '', item.price if item else ''),
            'urgency_match': calculate_urgency_match(need.urgency_level if need else '', item.availability if item else '')
        }
        
        # Get feedback history
        feedback_history = MatchingFeedback.query.filter_by(match_id=recommendation_id).all()
        
        return render_template('ai_matching/match_report.html',
                             match=match,
                             need=need,
                             item=item,
                             need_user=need_user,
                             item_creator=item_creator,
                             match_analysis=match_analysis,
                             feedback_history=feedback_history)
        
    except Exception as e:
        flash(f'Error loading match report: {str(e)}', 'error')
        return redirect(url_for('ai_matching.dashboard'))

@ai_matching_bp.route('/rate-match/<int:recommendation_id>', methods=['POST'])
@login_required
@require_permission('ai_matching', 'provide_feedback')
def rate_match(recommendation_id):
    """Rate a match for AI learning"""
    try:
        data = request.get_json()
        rating = data.get('rating')
        
        if not rating or rating < 1 or rating > 100:
            return jsonify({'success': False, 'message': 'Invalid rating. Please provide 1-100%.'})
        
        # Update the match with user rating
        match = NeedItemMatch.query.get(recommendation_id)
        if not match:
            return jsonify({'success': False, 'message': 'Recommendation not found'})
        
        # Store rating for AI learning
        feedback = MatchingFeedback(
            match_id=recommendation_id,
            user_id=current_user.id,
            feedback_type='rating',
            rating=rating
        )
        db.session.add(feedback)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Rating saved successfully'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@ai_matching_bp.route('/assign-connector/<int:recommendation_id>', methods=['POST'])
@login_required
@require_permission('ai_matching', 'manage_recommendations')
def assign_connector(recommendation_id):
    """Assign recommendation to another connector"""
    try:
        data = request.get_json()
        connector_id = data.get('connector_id')
        
        if not connector_id:
            return jsonify({'success': False, 'message': 'Connector ID is required'})
        
        # Verify connector exists
        connector = User.query.get(connector_id)
        if not connector or not connector.roles.filter_by(name='Connector').first():
            return jsonify({'success': False, 'message': 'Invalid connector ID'})
        
        # Update recommendation
        match = NeedItemMatch.query.get(recommendation_id)
        if not match:
            return jsonify({'success': False, 'message': 'Recommendation not found'})
        
        match.connector_id = connector_id
        match.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({'success': True, 'message': f'Recommendation assigned to {connector.first_name} {connector.last_name}'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@ai_matching_bp.route('/save-to-deals/<int:recommendation_id>', methods=['POST'])
@login_required
@require_permission('ai_matching', 'manage_recommendations')
def save_to_deals(recommendation_id):
    """Save recommendation to user's deals"""
    try:
        match = NeedItemMatch.query.get(recommendation_id)
        if not match:
            return jsonify({'success': False, 'message': 'Recommendation not found'})
        
        # Create a saved deal record
        from models import Deal
        deal = Deal(
            provider_id=match.item.profile.user_id if match.item.profile else None,
            consumer_id=match.need.user_id,
            connector_id=current_user.id,
            title=f"AI Match: {match.need.title} - {match.item.title}",
            description=f"AI-generated match between need and item. Match score: {match.match_score:.2f}",
            total_amount=0,  # To be determined
            status='saved'  # Special status for saved recommendations
        )
        db.session.add(deal)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Recommendation saved to your deals'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@ai_matching_bp.route('/delete-recommendation/<int:recommendation_id>', methods=['POST'])
@login_required
@require_permission('ai_matching', 'manage_recommendations')
def delete_recommendation(recommendation_id):
    """Dismiss recommendation from user's view (doesn't affect AI engine)"""
    try:
        match = NeedItemMatch.query.get(recommendation_id)
        if not match:
            return jsonify({'success': False, 'message': 'Recommendation not found'})
        
        # Dismiss from user's view only (doesn't affect AI engine)
        success = ai_matching_engine.dismiss_recommendation(recommendation_id, current_user.id)
        
        if success:
            return jsonify({'success': True, 'message': 'Recommendation dismissed from your view'})
        else:
            return jsonify({'success': False, 'message': 'Failed to dismiss recommendation'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@ai_matching_bp.route('/need/<int:need_id>')
@login_required
@require_permission('ai_matching', 'view_needs')
def need_detail(need_id):
    """View detailed information about a need"""
    try:
        need = UserNeed.query.get_or_404(need_id)
        
        # Get all matches for this need
        matches = NeedItemMatch.query.filter_by(need_id=need_id).all()
        
        return render_template('ai_matching/need_detail.html', 
                             need=need, 
                             matches=matches)
    except Exception as e:
        flash(f'Error loading need details: {str(e)}', 'error')
        return redirect(url_for('ai_matching.dashboard'))


@ai_matching_bp.route('/refresh-recent-needs')
@login_required
@require_permission('ai_matching', 'access_dashboard')
def refresh_recent_needs():
    """AJAX endpoint to refresh recent needs section"""
    try:
        # Get recent needs (last 10)
        recent_needs = UserNeed.query.order_by(UserNeed.created_at.desc()).limit(10).all()
        
        # Render the needs section HTML
        html = render_template('ai_matching/partials/recent_needs.html', recent_needs=recent_needs)
        
        return jsonify({
            'success': True,
            'html': html
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ai_matching_bp.route('/refresh-recent-items')
@login_required
@require_permission('ai_matching', 'access_dashboard')
def refresh_recent_items():
    """AJAX endpoint to refresh recent items section"""
    try:
        # Get recent items (last 10)
        recent_items = Item.query.order_by(Item.created_at.desc()).limit(10).all()
        
        # Render the items section HTML
        html = render_template('ai_matching/partials/recent_items.html', recent_items=recent_items)
        
        return jsonify({
            'success': True,
            'html': html
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
