#!/usr/bin/env python3
"""
Scoring System for BankU Items
Implements visibility, credibility, and review scoring
"""

from datetime import datetime
from models import (
    db, Item, ItemField, ItemVisibilityScore, ItemCredibilityScore, 
    ItemReviewScore, ItemInteraction, User, Profile, Review
)

class ScoringSystem:
    """Main scoring system class"""
    
    @staticmethod
    def calculate_question_based_score(item):
        """
        Calculate visibility score based on chatbot question points
        This method looks at which questions were answered and their point values
        """
        try:
            # For now, we'll use a simplified approach based on item data completeness
            # In a full implementation, you'd track the relationship between items and chatbot completions
            
            # Calculate score based on how much data the item has
            score = 0
            
            # Check for essential fields
            if hasattr(item, 'title') and item.title and len(item.title.strip()) > 0:
                score += 25  # Title is worth 25 points
            
            if hasattr(item, 'short_description') and item.short_description and len(item.short_description.strip()) > 0:
                score += 20  # Short description is worth 20 points
            
            if hasattr(item, 'detailed_description') and item.detailed_description and len(item.detailed_description.strip()) > 50:
                score += 20  # Detailed description is worth 20 points
            
            if hasattr(item, 'category') and item.category and len(item.category.strip()) > 0:
                score += 15  # Category is worth 15 points
            
            # Check for additional fields
            additional_fields = ItemField.query.filter_by(item_id=item.id).all()
            if additional_fields:
                score += min(20, len(additional_fields) * 2)  # Up to 20 points for additional fields
            
            # Check for media/attachments
            if hasattr(item, 'images') and item.images:
                score += 10
            if hasattr(item, 'files') and item.files:
                score += 10
            if hasattr(item, 'attachments') and item.attachments:
                score += 10
            
            # Check for location
            if hasattr(item, 'location') and item.location:
                score += 5
            
            # Check for pricing
            if hasattr(item, 'price') and item.price:
                score += 5
            
            return min(100, score)
            
        except Exception as e:
            print(f"Error calculating question-based score for item {item.id}: {e}")
            return 0
    
    @staticmethod
    def calculate_visibility_score(item):
        """
        Calculate visibility score based on data completeness and question points
        Returns: ItemVisibilityScore object
        """
        try:
            # Get or create visibility score record
            visibility_score = ItemVisibilityScore.query.filter_by(item_id=item.id).first()
            if not visibility_score:
                visibility_score = ItemVisibilityScore(item_id=item.id)
                db.session.add(visibility_score)
            
            # Essential Fields Score (0-100) - Based on core item fields
            essential_score = 0
            essential_fields = ['title', 'short_description', 'detailed_description', 'category']
            
            for field in essential_fields:
                if hasattr(item, field) and getattr(item, field):
                    if field == 'detailed_description' and len(str(getattr(item, field))) > 50:
                        essential_score += 25
                    elif field == 'short_description' and len(str(getattr(item, field))) > 20:
                        essential_score += 25
                    else:
                        essential_score += 25
            
            # Additional Fields Score (0-100) - Based on chatbot question points
            additional_score = ScoringSystem.calculate_question_based_score(item)
            
            # Media Score (0-100)
            media_score = 0
            if hasattr(item, 'images') and item.images:
                media_score += 30
            if hasattr(item, 'files') and item.files:
                media_score += 20
            if hasattr(item, 'videos') and item.videos:
                media_score += 30
            if hasattr(item, 'attachments') and item.attachments:
                media_score += 20
            
            # Detail Score (0-100)
            detail_score = 0
            if hasattr(item, 'detailed_description') and item.detailed_description:
                desc_length = len(item.detailed_description)
                if desc_length > 500:
                    detail_score += 40
                elif desc_length > 200:
                    detail_score += 30
                elif desc_length > 100:
                    detail_score += 20
                else:
                    detail_score += 10
            
            # Tags and keywords
            if hasattr(item, 'tags') and item.tags and len(item.tags) > 0:
                detail_score += 20
            
            # Location information
            if hasattr(item, 'location') and item.location:
                detail_score += 20
            
            # Pricing information
            if hasattr(item, 'price') and item.price:
                detail_score += 20
            
            # Update scores
            visibility_score.essential_fields_score = min(100, essential_score)
            visibility_score.additional_fields_score = min(100, additional_score)
            visibility_score.media_score = min(100, media_score)
            visibility_score.detail_score = min(100, detail_score)
            
            # Calculate total score (0-400)
            total_score = (visibility_score.essential_fields_score + 
                          visibility_score.additional_fields_score + 
                          visibility_score.media_score + 
                          visibility_score.detail_score)
            
            visibility_score.total_visibility_score = total_score
            visibility_score.visibility_percentage = (total_score / 400) * 100
            
            # Determine visibility level
            if visibility_score.visibility_percentage >= 80:
                visibility_score.visibility_level = 'premium'
            elif visibility_score.visibility_percentage >= 60:
                visibility_score.visibility_level = 'high'
            elif visibility_score.visibility_percentage >= 40:
                visibility_score.visibility_level = 'medium'
            else:
                visibility_score.visibility_level = 'low'
            
            visibility_score.last_calculated = datetime.utcnow()
            visibility_score.calculation_version = '1.0'
            
            db.session.commit()
            return visibility_score
            
        except Exception as e:
            print(f"Error calculating visibility score for item {item.id}: {e}")
            db.session.rollback()
            return None
    
    @staticmethod
    def calculate_credibility_score(item):
        """
        Calculate credibility score based on user verification
        Returns: ItemCredibilityScore object
        """
        try:
            # Get or create credibility score record
            credibility_score = ItemCredibilityScore.query.filter_by(item_id=item.id).first()
            if not credibility_score:
                credibility_score = ItemCredibilityScore(item_id=item.id)
                db.session.add(credibility_score)
            
            # Get the item's creator (user)
            creator = None
            if hasattr(item, 'profile_id') and item.profile_id:
                profile = Profile.query.get(item.profile_id)
                if profile and profile.user_id:
                    creator = User.query.get(profile.user_id)
            
            if not creator:
                # No creator found, set default low scores
                credibility_score.total_credibility_score = 0
                credibility_score.credibility_percentage = 0.0
                credibility_score.trust_level = 'low'
                credibility_score.last_calculated = datetime.utcnow()
                db.session.commit()
                return credibility_score
            
            # User Verification (0-200 points)
            user_verification_score = 0
            verification_badges = []
            
            if creator.email_verified:
                user_verification_score += 50
                verification_badges.append('email_verified')
            
            if creator.phone_verified:
                user_verification_score += 50
                verification_badges.append('phone_verified')
            
            if creator.is_verified:
                user_verification_score += 50
                verification_badges.append('id_verified')
            
            # Social verification (placeholder for future implementation)
            social_verified = False  # This would be implemented later
            if social_verified:
                user_verification_score += 50
                verification_badges.append('social_verified')
            
            # Item Verification (0-150 points)
            item_verification_score = 0
            
            if hasattr(item, 'is_verified') and item.is_verified:
                item_verification_score += 50
                credibility_score.item_verified = True
            
            # Admin approval (placeholder)
            admin_approved = False  # This would be set by admin actions
            if admin_approved:
                item_verification_score += 50
                credibility_score.admin_approved = True
            
            # Quality check (placeholder)
            quality_checked = False  # This would be set by quality checks
            if quality_checked:
                item_verification_score += 50
                credibility_score.quality_checked = True
            
            # Profile Completeness (0-100 points)
            profile_completeness_score = 0
            
            # Check if user has complete profile
            if creator.first_name and creator.last_name and creator.email:
                profile_completeness_score += 30
                credibility_score.profile_complete = True
            
            if creator.bio and len(creator.bio) > 20:
                profile_completeness_score += 20
                credibility_score.bio_complete = True
            
            if creator.location:
                profile_completeness_score += 20
                credibility_score.location_added = True
            
            # Additional profile fields
            if creator.phone:
                profile_completeness_score += 15
            
            if creator.avatar:
                profile_completeness_score += 15
            
            # Trust Indicators (0-50 points)
            trust_score = 0
            
            # Account age (older accounts are more trusted)
            if creator.created_at:
                days_old = (datetime.utcnow() - creator.created_at).days
                if days_old > 365:
                    trust_score += 20
                elif days_old > 180:
                    trust_score += 15
                elif days_old > 90:
                    trust_score += 10
                elif days_old > 30:
                    trust_score += 5
            
            # Activity level (more active users are more trusted)
            # This would be calculated based on user activity
            activity_score = 0  # Placeholder for future implementation
            trust_score += activity_score
            
            # Update scores
            credibility_score.email_verified = creator.email_verified
            credibility_score.phone_verified = creator.phone_verified
            credibility_score.id_verified = creator.is_verified
            credibility_score.social_verified = social_verified
            credibility_score.verification_badges = verification_badges
            
            # Calculate total score (0-500)
            total_score = (user_verification_score + item_verification_score + 
                          profile_completeness_score + trust_score)
            
            credibility_score.total_credibility_score = min(500, total_score)
            credibility_score.credibility_percentage = (credibility_score.total_credibility_score / 500) * 100
            
            # Determine trust level
            if credibility_score.credibility_percentage >= 80:
                credibility_score.trust_level = 'verified'
            elif credibility_score.credibility_percentage >= 60:
                credibility_score.trust_level = 'high'
            elif credibility_score.credibility_percentage >= 40:
                credibility_score.trust_level = 'medium'
            else:
                credibility_score.trust_level = 'low'
            
            credibility_score.last_calculated = datetime.utcnow()
            credibility_score.calculation_version = '1.0'
            
            db.session.commit()
            return credibility_score
            
        except Exception as e:
            print(f"Error calculating credibility score for item {item.id}: {e}")
            db.session.rollback()
            return None
    
    @staticmethod
    def calculate_review_score(item):
        """
        Calculate review score based on ratings and reviews
        Returns: ItemReviewScore object
        """
        try:
            # Get or create review score record
            review_score = ItemReviewScore.query.filter_by(item_id=item.id).first()
            if not review_score:
                review_score = ItemReviewScore(item_id=item.id)
                db.session.add(review_score)
            
            # Get all reviews for this item
            reviews = Review.query.filter_by(reviewee_id=item.id).all()
            
            if not reviews:
                # No reviews, set default scores
                review_score.total_reviews = 0
                review_score.average_rating = 0.0
                review_score.rating_distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
                review_score.total_review_score = 0
                review_score.review_level = 'none'
                review_score.review_percentage = 0.0
                review_score.last_calculated = datetime.utcnow()
                db.session.commit()
                return review_score
            
            # Calculate review metrics
            total_reviews = len(reviews)
            ratings = [review.rating for review in reviews if review.rating]
            
            if ratings:
                average_rating = sum(ratings) / len(ratings)
                
                # Calculate rating distribution
                rating_distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
                for rating in ratings:
                    if 1 <= rating <= 5:
                        rating_distribution[rating] += 1
            else:
                average_rating = 0.0
                rating_distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
            
            # Review Quality Score (0-100 points)
            quality_score = 0
            
            # Score based on number of reviews
            if total_reviews >= 20:
                quality_score += 40
            elif total_reviews >= 10:
                quality_score += 30
            elif total_reviews >= 5:
                quality_score += 20
            elif total_reviews >= 1:
                quality_score += 10
            
            # Score based on average rating
            if average_rating >= 4.5:
                quality_score += 30
            elif average_rating >= 4.0:
                quality_score += 25
            elif average_rating >= 3.5:
                quality_score += 20
            elif average_rating >= 3.0:
                quality_score += 15
            elif average_rating >= 2.0:
                quality_score += 10
            elif average_rating > 0:
                quality_score += 5
            
            # Score based on review content quality
            detailed_reviews = sum(1 for review in reviews if review.comment and len(review.comment) > 50)
            if detailed_reviews > 0:
                quality_score += min(30, (detailed_reviews / total_reviews) * 30)
            
            # Response Rate (placeholder for future implementation)
            response_rate = 0.0  # This would be calculated based on user responses to reviews
            dispute_rate = 0.0   # This would be calculated based on disputed reviews
            
            # Update scores
            review_score.total_reviews = total_reviews
            review_score.average_rating = average_rating
            review_score.rating_distribution = rating_distribution
            review_score.review_quality_score = min(100, quality_score)
            review_score.response_rate = response_rate
            review_score.dispute_rate = dispute_rate
            
            # Calculate total review score (0-300)
            total_score = (review_score.review_quality_score + 
                          (response_rate * 100) + 
                          ((1 - dispute_rate) * 100))
            
            review_score.total_review_score = min(300, total_score)
            review_score.review_percentage = (review_score.total_review_score / 300) * 100
            
            # Determine review level
            if review_score.review_percentage >= 80:
                review_score.review_level = 'excellent'
            elif review_score.review_percentage >= 60:
                review_score.review_level = 'high'
            elif review_score.review_percentage >= 40:
                review_score.review_level = 'medium'
            elif review_score.review_percentage >= 20:
                review_score.review_level = 'low'
            else:
                review_score.review_level = 'none'
            
            review_score.last_calculated = datetime.utcnow()
            review_score.calculation_version = '1.0'
            
            db.session.commit()
            return review_score
            
        except Exception as e:
            print(f"Error calculating review score for item {item.id}: {e}")
            db.session.rollback()
            return None
    
    @staticmethod
    def calculate_all_scores(item):
        """
        Calculate all scores for an item
        Returns: dict with all score objects
        """
        try:
            visibility_score = ScoringSystem.calculate_visibility_score(item)
            credibility_score = ScoringSystem.calculate_credibility_score(item)
            review_score = ScoringSystem.calculate_review_score(item)
            
            return {
                'visibility': visibility_score,
                'credibility': credibility_score,
                'review': review_score
            }
        except Exception as e:
            print(f"Error calculating all scores for item {item.id}: {e}")
            return None
    
    @staticmethod
    def update_all_item_scores():
        """
        Update scores for all items in the database
        Returns: dict with statistics
        """
        try:
            items = Item.query.all()
            stats = {
                'total_items': len(items),
                'successful_updates': 0,
                'failed_updates': 0,
                'errors': []
            }
            
            for item in items:
                try:
                    ScoringSystem.calculate_all_scores(item)
                    stats['successful_updates'] += 1
                except Exception as e:
                    stats['failed_updates'] += 1
                    stats['errors'].append(f"Item {item.id}: {str(e)}")
            
            return stats
            
        except Exception as e:
            print(f"Error updating all item scores: {e}")
            return None
    
    @staticmethod
    def get_item_total_score(item):
        """
        Get the total weighted score for an item
        Returns: float (0.0-100.0)
        """
        try:
            visibility_score = ItemVisibilityScore.query.filter_by(item_id=item.id).first()
            credibility_score = ItemCredibilityScore.query.filter_by(item_id=item.id).first()
            review_score = ItemReviewScore.query.filter_by(item_id=item.id).first()
            
            if not all([visibility_score, credibility_score, review_score]):
                return 0.0
            
            # Weighted scoring (visibility: 40%, credibility: 35%, review: 25%)
            total_score = (
                visibility_score.visibility_percentage * 0.40 +
                credibility_score.credibility_percentage * 0.35 +
                review_score.review_percentage * 0.25
            )
            
            return min(100.0, total_score)
            
        except Exception as e:
            print(f"Error getting total score for item {item.id}: {e}")
            return 0.0
