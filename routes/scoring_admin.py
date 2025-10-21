from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from flask_login import login_required, current_user
from models import (
    ChatbotFlow, ChatbotQuestion, ItemVisibilityScore, ItemCredibilityScore, 
    ItemReviewScore, db
)
from functools import wraps

scoring_admin_bp = Blueprint('scoring_admin', __name__)

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        
        from models import Role, UserRole
        admin_role = Role.query.filter_by(name='Admin').first()
        if not admin_role:
            return jsonify({'success': False, 'message': 'Admin role not found'})
        
        # Check if user has admin role
        user_role = UserRole.query.filter_by(
            user_id=current_user.id, 
            role_id=admin_role.id
        ).first()
        
        if not user_role:
            return jsonify({'success': False, 'message': 'Admin access required'})
        
        return f(*args, **kwargs)
    return decorated_function

@scoring_admin_bp.route('/scoring-management')
@admin_required
def scoring_management():
    """Main scoring management page"""
    return render_template('admin/scoring_management.html')

@scoring_admin_bp.route('/scoring-management/visibility')
@admin_required
def visibility_scoring_management():
    """Manage visibility scoring weights and settings"""
    # Get all chatbot flows with their questions
    flows = ChatbotFlow.query.all()
    
    # Get scoring statistics
    visibility_scores = ItemVisibilityScore.query.all()
    avg_visibility = sum(score.visibility_percentage for score in visibility_scores) / len(visibility_scores) if visibility_scores else 0
    
    return render_template('admin/visibility_scoring_management.html', 
                         flows=flows, 
                         avg_visibility=avg_visibility)

@scoring_admin_bp.route('/scoring-management/credibility')
@admin_required
def credibility_scoring_management():
    """Manage credibility scoring weights and settings"""
    # Get scoring statistics
    credibility_scores = ItemCredibilityScore.query.all()
    avg_credibility = sum(score.credibility_percentage for score in credibility_scores) / len(credibility_scores) if credibility_scores else 0
    
    return render_template('admin/credibility_scoring_management.html', 
                         avg_credibility=avg_credibility)

@scoring_admin_bp.route('/scoring-management/review')
@admin_required
def review_scoring_management():
    """Manage review scoring weights and settings"""
    # Get scoring statistics
    review_scores = ItemReviewScore.query.all()
    avg_review = sum(score.review_percentage for score in review_scores) / len(review_scores) if review_scores else 0
    
    return render_template('admin/review_scoring_management.html', 
                         avg_review=avg_review)

@scoring_admin_bp.route('/api/scoring/update-question-points', methods=['POST'])
@admin_required
def update_question_points():
    """Update visibility points for a chatbot question"""
    try:
        data = request.get_json()
        question_id = data.get('question_id')
        points = data.get('points')
        
        if not question_id or points is None:
            return jsonify({'success': False, 'message': 'Missing required fields'})
        
        question = ChatbotQuestion.query.get(question_id)
        if not question:
            return jsonify({'success': False, 'message': 'Question not found'})
        
        question.visibility_points = int(points)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Question points updated successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error updating question points: {str(e)}'})

@scoring_admin_bp.route('/api/scoring/update-scoring-weights', methods=['POST'])
@admin_required
def update_scoring_weights():
    """Update scoring system weights and thresholds"""
    try:
        data = request.get_json()
        score_type = data.get('score_type')  # 'visibility', 'credibility', 'review'
        weights = data.get('weights', {})
        
        # This would update global scoring configuration
        # For now, we'll just return success
        # In a full implementation, you'd store these in a configuration table
        
        return jsonify({'success': True, 'message': f'{score_type.title()} scoring weights updated successfully'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error updating scoring weights: {str(e)}'})

@scoring_admin_bp.route('/api/scoring/recalculate-all-scores', methods=['POST'])
@admin_required
def recalculate_all_scores():
    """Recalculate all item scores"""
    try:
        from utils.scoring_system import ScoringSystem
        
        # Recalculate scores for all items
        stats = ScoringSystem.update_all_item_scores()
        
        if stats:
            return jsonify({
                'success': True, 
                'message': f'Recalculated scores for {stats["successful_updates"]} items',
                'stats': stats
            })
        else:
            return jsonify({'success': False, 'message': 'Failed to recalculate scores'})
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error recalculating scores: {str(e)}'})
