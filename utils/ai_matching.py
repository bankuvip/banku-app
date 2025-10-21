"""
AI Matching Engine
Core logic for intelligent matching between user needs and available items
"""

from flask import current_app
from models import db, Item, UserNeed, NeedItemMatch, MatchingAlgorithm, MatchingFeedback, MatchingSession, SearchAnalytics
from sqlalchemy import and_, or_, func, desc
from datetime import datetime, timedelta
import json
import re
from typing import List, Dict, Tuple, Optional

class AIMatchingEngine:
    """Main AI matching engine class"""
    
    def __init__(self):
        self.algorithms = self._load_algorithms()
    
    def _load_algorithms(self) -> Dict[str, Dict]:
        """Load available matching algorithms"""
        return {
            'keyword_matching': {
                'name': 'Keyword Matching',
                'description': 'Matches based on keyword similarity in titles and descriptions',
                'weight': 0.3
            },
            'category_matching': {
                'name': 'Category Matching', 
                'description': 'Matches based on item category alignment',
                'weight': 0.2
            },
            'location_matching': {
                'name': 'Location Matching',
                'description': 'Matches based on geographic proximity',
                'weight': 0.15
            },
            'price_matching': {
                'name': 'Price Matching',
                'description': 'Matches based on budget compatibility',
                'weight': 0.15
            },
            'analytics_matching': {
                'name': 'Analytics-Based Matching',
                'description': 'Matches based on user search behavior patterns',
                'weight': 0.2
            }
        }
    
    def find_matches(self, need: UserNeed, limit: int = 10) -> List[Tuple[Item, float, str]]:
        """
        Find the best matches for a user need
        
        Args:
            need: UserNeed object
            limit: Maximum number of matches to return
            
        Returns:
            List of tuples: (Item, match_score, match_reason)
        """
        try:
            # Start matching session
            session = MatchingSession(
                user_id=need.user_id,
                need_id=need.id,
                algorithm_id=1,  # Default algorithm
                session_type='search'
            )
            db.session.add(session)
            db.session.flush()
            
            # Get candidate items
            candidates = self._get_candidate_items(need)
            
            # Calculate match scores for each candidate
            matches = []
            for item in candidates:
                score, reason = self._calculate_match_score(need, item)
                if score > 0.3:  # Minimum threshold
                    matches.append((item, score, reason))
            
            # Sort by score and limit results
            matches.sort(key=lambda x: x[1], reverse=True)
            matches = matches[:limit]
            
            # Store matches in database
            for item, score, reason in matches:
                match = NeedItemMatch(
                    need_id=need.id,
                    item_id=item.id,
                    match_score=score,
                    match_reason=reason,
                    confidence_level=self._get_confidence_level(score)
                )
                db.session.add(match)
            
            # Update session
            session.matches_generated = len(matches)
            session.ended_at = datetime.utcnow()
            
            db.session.commit()
            
            return matches
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error in find_matches: {e}")
            return []
    
    def _get_candidate_items(self, need: UserNeed) -> List[Item]:
        """Get candidate items for matching"""
        query = Item.query.filter(Item.is_available == True)
        
        # Filter by need type (category)
        if need.need_type:
            query = query.filter(Item.category == need.need_type)
        
        # Filter by location if specified
        if need.location:
            query = query.filter(
                or_(
                    Item.location.contains(need.location),
                    Item.location == need.location
                )
            )
        
        # Filter by price range if specified
        if need.budget_min:
            query = query.filter(Item.price >= need.budget_min)
        if need.budget_max:
            query = query.filter(Item.price <= need.budget_max)
        
        # Order by relevance (recent items first, then by views)
        query = query.order_by(desc(Item.created_at), desc(Item.views))
        
        return query.limit(100).all()  # Limit candidates for performance
    
    def _calculate_match_score(self, need: UserNeed, item: Item) -> Tuple[float, str]:
        """Calculate overall match score between need and item"""
        scores = {}
        reasons = []
        
        # Keyword matching
        keyword_score = self._calculate_keyword_score(need, item)
        scores['keyword'] = keyword_score
        if keyword_score > 0.5:
            reasons.append("Strong keyword match")
        
        # Category matching
        category_score = self._calculate_category_score(need, item)
        scores['category'] = category_score
        if category_score > 0.8:
            reasons.append("Perfect category match")
        
        # Location matching
        location_score = self._calculate_location_score(need, item)
        scores['location'] = location_score
        if location_score > 0.7:
            reasons.append("Good location match")
        
        # Price matching
        price_score = self._calculate_price_score(need, item)
        scores['price'] = price_score
        if price_score > 0.8:
            reasons.append("Price within budget")
        
        # Analytics-based matching
        analytics_score = self._calculate_analytics_score(need, item)
        scores['analytics'] = analytics_score
        if analytics_score > 0.6:
            reasons.append("Based on popular searches")
        
        # Calculate weighted overall score
        overall_score = sum(
            scores[algorithm] * self.algorithms[algorithm]['weight']
            for algorithm in scores
        )
        
        # Create match reason
        match_reason = "; ".join(reasons) if reasons else "Basic match"
        
        return overall_score, match_reason
    
    def _calculate_keyword_score(self, need: UserNeed, item: Item) -> float:
        """Calculate keyword similarity score"""
        need_text = f"{need.title} {need.description}".lower()
        item_text = f"{item.title} {item.short_description}".lower()
        
        # Extract keywords (simple word splitting)
        need_words = set(re.findall(r'\b\w+\b', need_text))
        item_words = set(re.findall(r'\b\w+\b', item_text))
        
        if not need_words:
            return 0.0
        
        # Calculate Jaccard similarity
        intersection = len(need_words.intersection(item_words))
        union = len(need_words.union(item_words))
        
        return intersection / union if union > 0 else 0.0
    
    def _calculate_category_score(self, need: UserNeed, item: Item) -> float:
        """Calculate category matching score"""
        if not need.need_type or not item.category:
            return 0.0
        
        # Direct match
        if need.need_type == item.category:
            return 1.0
        
        # Category mappings for similar types
        category_mappings = {
            'product': ['product', 'physical', 'digital'],
            'service': ['service', 'consulting', 'support'],
            'event': ['event', 'experience'],
            'experience': ['experience', 'event'],
            'opportunity': ['opportunity', 'job', 'project'],
            'information': ['information', 'data', 'knowledge']
        }
        
        need_categories = category_mappings.get(need.need_type, [need.need_type])
        item_categories = category_mappings.get(item.category, [item.category])
        
        if any(cat in item_categories for cat in need_categories):
            return 0.8
        
        return 0.0
    
    def _calculate_location_score(self, need: UserNeed, item: Item) -> float:
        """Calculate location matching score"""
        if not need.location or not item.location:
            return 0.5  # Neutral score when location not specified
        
        need_location = need.location.lower()
        item_location = item.location.lower()
        
        # Exact match
        if need_location == item_location:
            return 1.0
        
        # Contains match
        if need_location in item_location or item_location in need_location:
            return 0.8
        
        # City/state matching (simplified)
        need_parts = need_location.split(',')
        item_parts = item_location.split(',')
        
        if len(need_parts) > 0 and len(item_parts) > 0:
            if need_parts[0].strip() == item_parts[0].strip():
                return 0.6
        
        return 0.2
    
    def _calculate_price_score(self, need: UserNeed, item: Item) -> float:
        """Calculate price compatibility score"""
        if not item.price:
            return 0.5  # Neutral score when price not specified
        
        # No budget constraints
        if not need.budget_min and not need.budget_max:
            return 0.7
        
        # Within budget range
        if need.budget_min and need.budget_max:
            if need.budget_min <= item.price <= need.budget_max:
                return 1.0
            elif item.price < need.budget_min:
                return 0.3  # Too cheap might indicate low quality
            else:
                # Calculate how much over budget
                overage = (item.price - need.budget_max) / need.budget_max
                return max(0.0, 1.0 - overage * 2)  # Penalty for being over budget
        
        # Only minimum budget
        if need.budget_min:
            if item.price >= need.budget_min:
                return 1.0
            else:
                return 0.3
        
        # Only maximum budget
        if need.budget_max:
            if item.price <= need.budget_max:
                return 1.0
            else:
                overage = (item.price - need.budget_max) / need.budget_max
                return max(0.0, 1.0 - overage * 2)
        
        return 0.5
    
    def _calculate_analytics_score(self, need: UserNeed, item: Item) -> float:
        """Calculate score based on search analytics"""
        try:
            # Get recent search analytics for this item type
            recent_searches = SearchAnalytics.query.filter(
                SearchAnalytics.item_type == item.category,
                SearchAnalytics.last_searched >= datetime.utcnow() - timedelta(days=30)
            ).order_by(desc(SearchAnalytics.search_count)).limit(20).all()
            
            if not recent_searches:
                return 0.5  # Neutral score if no analytics data
            
            # Check if item matches popular search criteria
            score = 0.0
            total_weight = 0.0
            
            for search in recent_searches:
                weight = min(search.search_count / 10.0, 1.0)  # Normalize weight
                
                if search.filter_field == 'location' and item.location:
                    if search.filter_value.lower() in item.location.lower():
                        score += weight * 0.8
                        total_weight += weight
                
                elif search.filter_field == 'category' and item.category:
                    if search.filter_value == item.category:
                        score += weight * 1.0
                        total_weight += weight
                
                elif search.search_term and item.title:
                    if search.search_term.lower() in item.title.lower():
                        score += weight * 0.6
                        total_weight += weight
            
            return score / total_weight if total_weight > 0 else 0.5
            
        except Exception as e:
            current_app.logger.error(f"Error in analytics scoring: {e}")
            return 0.5
    
    def _get_confidence_level(self, score: float) -> str:
        """Get confidence level based on match score"""
        if score >= 0.8:
            return 'high'
        elif score >= 0.6:
            return 'medium'
        else:
            return 'low'
    
    def record_feedback(self, match_id: int, user_id: int, feedback_type: str, 
                       rating: int = None, comment: str = None) -> bool:
        """Record user feedback on a match"""
        try:
            feedback = MatchingFeedback(
                match_id=match_id,
                user_id=user_id,
                feedback_type=feedback_type,
                rating=rating,
                comment=comment
            )
            db.session.add(feedback)
            
            # Update match status
            match = NeedItemMatch.query.get(match_id)
            if match:
                if feedback_type == 'like':
                    match.user_liked = True
                    match.status = 'accepted'
                elif feedback_type == 'dislike':
                    match.user_liked = False
                    match.status = 'rejected'
                elif feedback_type == 'contacted':
                    match.user_contacted = True
                    match.status = 'accepted'
                elif feedback_type == 'dismissed':
                    # Don't change match status, just record user dismissed it
                    pass
            
            db.session.commit()
            return True
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error recording feedback: {e}")
            return False
    
    def dismiss_recommendation(self, recommendation_id: int, user_id: int) -> bool:
        """Dismiss a recommendation from user's view (doesn't affect AI engine)"""
        try:
            feedback = MatchingFeedback(
                match_id=recommendation_id,
                user_id=user_id,
                feedback_type='dismissed'
            )
            db.session.add(feedback)
            db.session.commit()
            return True
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error dismissing recommendation: {e}")
            return False
    
    def get_recommendations(self, user_id: int, limit: int = 5) -> List[Item]:
        """Get personalized recommendations for a user"""
        try:
            # Get user's search history and preferences
            recent_searches = SearchAnalytics.query.filter(
                SearchAnalytics.user_id == user_id,
                SearchAnalytics.last_searched >= datetime.utcnow() - timedelta(days=7)
            ).order_by(desc(SearchAnalytics.last_searched)).limit(10).all()
            
            if not recent_searches:
                # Fallback to popular items
                return Item.query.filter(
                    Item.is_available == True
                ).order_by(desc(Item.views)).limit(limit).all()
            
            # Find items similar to user's interests
            recommended_items = []
            for search in recent_searches:
                items = Item.query.filter(
                    and_(
                        Item.is_available == True,
                        Item.category == search.item_type
                    )
                ).order_by(desc(Item.views)).limit(2).all()
                recommended_items.extend(items)
            
            # Remove duplicates and limit results
            seen_ids = set()
            unique_items = []
            for item in recommended_items:
                if item.id not in seen_ids:
                    unique_items.append(item)
                    seen_ids.add(item.id)
                    if len(unique_items) >= limit:
                        break
            
            return unique_items
            
        except Exception as e:
            current_app.logger.error(f"Error getting recommendations: {e}")
            return []
    
    def create_recommendation_record(self, need_id: int, item_id: int, score: float, reason: str) -> bool:
        """Create a recommendation record for connectors to review"""
        try:
            # Check if recommendation already exists
            existing = NeedItemMatch.query.filter_by(
                need_id=need_id, 
                item_id=item_id
            ).first()
            
            if existing:
                # Update existing record
                existing.match_score = score
                existing.match_reason = reason
                existing.updated_at = datetime.utcnow()
            else:
                # Create new recommendation record
                recommendation = NeedItemMatch(
                    need_id=need_id,
                    item_id=item_id,
                    match_score=score,
                    match_reason=reason,
                    confidence_level=self._get_confidence_level(score),
                    status='pending',  # Waiting for connector review
                    is_active=True
                )
                db.session.add(recommendation)
            
            db.session.commit()
            return True
            
        except Exception as e:
            current_app.logger.error(f"Error creating recommendation record: {e}")
            db.session.rollback()
            return False
    
    def get_connector_recommendations(self, user_id: int, limit: int = 20) -> List[Dict]:
        """Get AI recommendations for users to review and take actions"""
        try:
            # Get all pending recommendations from the AI engine
            recommendations = NeedItemMatch.query.filter(
                NeedItemMatch.status == 'pending',
                NeedItemMatch.is_active == True,
                NeedItemMatch.match_score >= 0.6  # High confidence matches only
            ).order_by(NeedItemMatch.match_score.desc()).limit(limit).all()
            
            result = []
            for rec in recommendations:
                result.append({
                    'id': rec.id,
                    'need': rec.need,
                    'item': rec.item,
                    'match_score': rec.match_score,
                    'reason': rec.match_reason,
                    'confidence': rec.confidence_level,
                    'created_at': rec.created_at,
                    'need_user': rec.need.user,
                    'item_creator': rec.item.profile.user if rec.item.profile else None
                })
            
            return result
            
        except Exception as e:
            current_app.logger.error(f"Error getting connector recommendations: {e}")
            return []
    
    def get_user_recommendations(self, user_id: int, limit: int = 20) -> List[Dict]:
        """Get personalized recommendations for a specific user (their view only)"""
        try:
            # Get recommendations that user hasn't dismissed
            recommendations = NeedItemMatch.query.filter(
                NeedItemMatch.status == 'pending',
                NeedItemMatch.is_active == True,
                NeedItemMatch.match_score >= 0.6,
                ~NeedItemMatch.id.in_(
                    db.session.query(MatchingFeedback.match_id).filter(
                        MatchingFeedback.user_id == user_id,
                        MatchingFeedback.feedback_type == 'dismissed'
                    )
                )
            ).order_by(NeedItemMatch.match_score.desc()).limit(limit).all()
            
            result = []
            for rec in recommendations:
                result.append({
                    'id': rec.id,
                    'need': rec.need,
                    'item': rec.item,
                    'match_score': rec.match_score,
                    'reason': rec.match_reason,
                    'confidence': rec.confidence_level,
                    'created_at': rec.created_at,
                    'need_user': rec.need.user,
                    'item_creator': rec.item.profile.user if rec.item.profile else None
                })
            
            return result
            
        except Exception as e:
            current_app.logger.error(f"Error getting user recommendations: {e}")
            return []
    
    def update_recommendation_status(self, recommendation_id: int, status: str, connector_id: int = None) -> bool:
        """Update recommendation status (accepted, rejected, etc.)"""
        try:
            recommendation = NeedItemMatch.query.get(recommendation_id)
            if not recommendation:
                return False
            
            recommendation.status = status
            recommendation.updated_at = datetime.utcnow()
            
            if connector_id:
                recommendation.connector_id = connector_id
            
            db.session.commit()
            return True
            
        except Exception as e:
            current_app.logger.error(f"Error updating recommendation status: {e}")
            db.session.rollback()
            return False
    
    def auto_generate_recommendations(self) -> int:
        """Automatically generate recommendations for all active needs"""
        try:
            # Get all active needs
            active_needs = UserNeed.query.filter(
                UserNeed.status == 'active'
            ).all()
            
            recommendations_created = 0
            
            for need in active_needs:
                # Find matches for this need
                matches = self.find_matches(need, limit=5)
                
                # Create recommendation records for high-scoring matches
                for item, score, reason in matches:
                    if score >= 0.6:  # High confidence threshold
                        if self.create_recommendation_record(need.id, item.id, score, reason):
                            recommendations_created += 1
            
            return recommendations_created
            
        except Exception as e:
            current_app.logger.error(f"Error auto-generating recommendations: {e}")
            return 0

# Global instance
ai_matching_engine = AIMatchingEngine()
