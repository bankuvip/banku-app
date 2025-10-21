#!/usr/bin/env python3
"""
API Documentation and REST API Routes for BankU
Phase 1: Comprehensive API documentation with Swagger/OpenAPI
"""

from flask import Blueprint, jsonify, request, current_app
from flask_restx import Api, Resource, fields, Namespace
from flask_login import login_required, current_user
from models import db, User, Item, Profile, Organization, Deal, DealRequest, Notification
from utils.permissions import require_permission
from datetime import datetime
import logging

# Create API blueprint
api_bp = Blueprint('api', __name__, url_prefix='/api/v1')

# Initialize Flask-RESTX
api = Api(
    api_bp,
    version='1.0',
    title='BankU API',
    description='Comprehensive API for BankU - Modern Banking Platform',
    doc='/docs/',  # Swagger UI will be available at /api/v1/docs/
    contact='BankU Support',
    contact_email='support@banku.com',
    license='MIT',
    license_url='https://opensource.org/licenses/MIT'
)

# Define namespaces
users_ns = Namespace('users', description='User management operations')
items_ns = Namespace('items', description='Item management operations')
profiles_ns = Namespace('profiles', description='Profile management operations')
organizations_ns = Namespace('organizations', description='Organization management operations')
deals_ns = Namespace('deals', description='Deal management operations')
notifications_ns = Namespace('notifications', description='Notification management operations')

# Add namespaces to API
api.add_namespace(users_ns)
api.add_namespace(items_ns)
api.add_namespace(profiles_ns)
api.add_namespace(organizations_ns)
api.add_namespace(deals_ns)
api.add_namespace(notifications_ns)

# Define data models for API documentation
user_model = api.model('User', {
    'id': fields.Integer(required=True, description='User ID'),
    'username': fields.String(required=True, description='Username'),
    'email': fields.String(required=True, description='Email address'),
    'created_at': fields.DateTime(description='Creation timestamp'),
    'is_active': fields.Boolean(description='User active status')
})

user_create_model = api.model('UserCreate', {
    'username': fields.String(required=True, description='Username'),
    'email': fields.String(required=True, description='Email address'),
    'password': fields.String(required=True, description='Password')
})

item_model = api.model('Item', {
    'id': fields.Integer(required=True, description='Item ID'),
    'title': fields.String(required=True, description='Item title'),
    'description': fields.String(description='Item description'),
    'category': fields.String(description='Item category'),
    'created_at': fields.DateTime(description='Creation timestamp'),
    'is_available': fields.Boolean(description='Item availability status')
})

item_create_model = api.model('ItemCreate', {
    'title': fields.String(required=True, description='Item title'),
    'description': fields.String(description='Item description'),
    'category': fields.String(required=True, description='Item category'),
    'profile_id': fields.Integer(required=True, description='Profile ID')
})

profile_model = api.model('Profile', {
    'id': fields.Integer(required=True, description='Profile ID'),
    'name': fields.String(required=True, description='Profile name'),
    'description': fields.String(description='Profile description'),
    'user_id': fields.Integer(required=True, description='User ID'),
    'created_at': fields.DateTime(description='Creation timestamp')
})

organization_model = api.model('Organization', {
    'id': fields.Integer(required=True, description='Organization ID'),
    'name': fields.String(required=True, description='Organization name'),
    'slug': fields.String(description='Organization slug'),
    'description': fields.String(description='Organization description'),
    'created_at': fields.DateTime(description='Creation timestamp')
})

deal_model = api.model('Deal', {
    'id': fields.Integer(required=True, description='Deal ID'),
    'title': fields.String(required=True, description='Deal title'),
    'description': fields.String(description='Deal description'),
    'status': fields.String(description='Deal status'),
    'provider_id': fields.Integer(description='Provider user ID'),
    'consumer_id': fields.Integer(description='Consumer user ID'),
    'created_at': fields.DateTime(description='Creation timestamp')
})

deal_request_model = api.model('DealRequest', {
    'id': fields.Integer(required=True, description='Deal request ID'),
    'title': fields.String(required=True, description='Request title'),
    'description': fields.String(description='Request description'),
    'status': fields.String(description='Request status'),
    'priority': fields.String(description='Request priority'),
    'user_id': fields.Integer(required=True, description='User ID'),
    'created_at': fields.DateTime(description='Creation timestamp')
})

notification_model = api.model('Notification', {
    'id': fields.Integer(required=True, description='Notification ID'),
    'title': fields.String(required=True, description='Notification title'),
    'message': fields.String(description='Notification message'),
    'type': fields.String(description='Notification type'),
    'is_read': fields.Boolean(description='Read status'),
    'created_at': fields.DateTime(description='Creation timestamp')
})

error_model = api.model('Error', {
    'error': fields.String(required=True, description='Error message'),
    'code': fields.Integer(description='Error code')
})

# Users API endpoints
@users_ns.route('/')
class UsersList(Resource):
    @api.doc('list_users')
    @api.marshal_list_with(user_model)
    @login_required
    @require_permission('users', 'read')
    def get(self):
        """Get list of all users"""
        try:
            users = User.query.filter_by(is_active=True).all()
            return users, 200
        except Exception as e:
            api.abort(500, f"Failed to retrieve users: {str(e)}")

@users_ns.route('/<int:user_id>')
@api.doc(params={'user_id': 'User ID'})
class UserDetail(Resource):
    @api.doc('get_user')
    @api.marshal_with(user_model)
    @login_required
    def get(self, user_id):
        """Get user by ID"""
        try:
            user = User.query.get_or_404(user_id)
            return user, 200
        except Exception as e:
            api.abort(404, f"User not found: {str(e)}")

# Items API endpoints
@items_ns.route('/')
class ItemsList(Resource):
    @api.doc('list_items')
    @api.marshal_list_with(item_model)
    @login_required
    def get(self):
        """Get list of available items"""
        try:
            items = Item.query.filter_by(is_available=True).all()
            return items, 200
        except Exception as e:
            api.abort(500, f"Failed to retrieve items: {str(e)}")

    @api.doc('create_item')
    @api.expect(item_create_model)
    @api.marshal_with(item_model, code=201)
    @login_required
    @require_permission('items', 'create')
    def post(self):
        """Create a new item"""
        try:
            data = request.json
            
            # Validate required fields
            if not data.get('title') or not data.get('category') or not data.get('profile_id'):
                api.abort(400, "Title, category, and profile_id are required")
            
            # Create new item
            item = Item(
                title=data['title'],
                description=data.get('description', ''),
                category=data['category'],
                profile_id=data['profile_id'],
                created_at=datetime.utcnow(),
                is_available=True
            )
            
            db.session.add(item)
            db.session.commit()
            
            return item, 201
        except Exception as e:
            db.session.rollback()
            api.abort(500, f"Failed to create item: {str(e)}")

@items_ns.route('/<int:item_id>')
@api.doc(params={'item_id': 'Item ID'})
class ItemDetail(Resource):
    @api.doc('get_item')
    @api.marshal_with(item_model)
    @login_required
    def get(self, item_id):
        """Get item by ID"""
        try:
            item = Item.query.get_or_404(item_id)
            return item, 200
        except Exception as e:
            api.abort(404, f"Item not found: {str(e)}")

# Profiles API endpoints
@profiles_ns.route('/')
class ProfilesList(Resource):
    @api.doc('list_profiles')
    @api.marshal_list_with(profile_model)
    @login_required
    def get(self):
        """Get list of profiles"""
        try:
            profiles = Profile.query.filter_by(user_id=current_user.id).all()
            return profiles, 200
        except Exception as e:
            api.abort(500, f"Failed to retrieve profiles: {str(e)}")

@profiles_ns.route('/<int:profile_id>')
@api.doc(params={'profile_id': 'Profile ID'})
class ProfileDetail(Resource):
    @api.doc('get_profile')
    @api.marshal_with(profile_model)
    @login_required
    def get(self, profile_id):
        """Get profile by ID"""
        try:
            profile = Profile.query.filter_by(id=profile_id, user_id=current_user.id).first_or_404()
            return profile, 200
        except Exception as e:
            api.abort(404, f"Profile not found: {str(e)}")

# Organizations API endpoints
@organizations_ns.route('/')
class OrganizationsList(Resource):
    @api.doc('list_organizations')
    @api.marshal_list_with(organization_model)
    @login_required
    @require_permission('organizations', 'read')
    def get(self):
        """Get list of organizations"""
        try:
            organizations = Organization.query.filter_by(is_active=True).all()
            return organizations, 200
        except Exception as e:
            api.abort(500, f"Failed to retrieve organizations: {str(e)}")

@organizations_ns.route('/<int:org_id>')
@api.doc(params={'org_id': 'Organization ID'})
class OrganizationDetail(Resource):
    @api.doc('get_organization')
    @api.marshal_with(organization_model)
    @login_required
    @require_permission('organizations', 'read')
    def get(self, org_id):
        """Get organization by ID"""
        try:
            organization = Organization.query.get_or_404(org_id)
            return organization, 200
        except Exception as e:
            api.abort(404, f"Organization not found: {str(e)}")

# Deals API endpoints
@deals_ns.route('/')
class DealsList(Resource):
    @api.doc('list_deals')
    @api.marshal_list_with(deal_model)
    @login_required
    @require_permission('deals', 'read')
    def get(self):
        """Get list of deals"""
        try:
            deals = Deal.query.filter(
                (Deal.provider_id == current_user.id) | 
                (Deal.consumer_id == current_user.id)
            ).all()
            return deals, 200
        except Exception as e:
            api.abort(500, f"Failed to retrieve deals: {str(e)}")

@deals_ns.route('/<int:deal_id>')
@api.doc(params={'deal_id': 'Deal ID'})
class DealDetail(Resource):
    @api.doc('get_deal')
    @api.marshal_with(deal_model)
    @login_required
    def get(self, deal_id):
        """Get deal by ID"""
        try:
            deal = Deal.query.filter(
                Deal.id == deal_id,
                (Deal.provider_id == current_user.id) | 
                (Deal.consumer_id == current_user.id)
            ).first_or_404()
            return deal, 200
        except Exception as e:
            api.abort(404, f"Deal not found: {str(e)}")

# Deal Requests API endpoints
@deals_ns.route('/requests/')
class DealRequestsList(Resource):
    @api.doc('list_deal_requests')
    @api.marshal_list_with(deal_request_model)
    @login_required
    def get(self):
        """Get list of deal requests"""
        try:
            deal_requests = DealRequest.query.filter_by(user_id=current_user.id).all()
            return deal_requests, 200
        except Exception as e:
            api.abort(500, f"Failed to retrieve deal requests: {str(e)}")

# Notifications API endpoints
@notifications_ns.route('/')
class NotificationsList(Resource):
    @api.doc('list_notifications')
    @api.marshal_list_with(notification_model)
    @login_required
    def get(self):
        """Get list of user notifications"""
        try:
            notifications = Notification.query.filter_by(user_id=current_user.id)\
                .order_by(Notification.created_at.desc()).limit(20).all()
            return notifications, 200
        except Exception as e:
            api.abort(500, f"Failed to retrieve notifications: {str(e)}")

@notifications_ns.route('/<int:notification_id>/read')
@api.doc(params={'notification_id': 'Notification ID'})
class NotificationRead(Resource):
    @api.doc('mark_notification_read')
    @login_required
    def post(self, notification_id):
        """Mark notification as read"""
        try:
            notification = Notification.query.filter_by(
                id=notification_id,
                user_id=current_user.id
            ).first_or_404()
            
            notification.is_read = True
            notification.read_at = datetime.utcnow()
            db.session.commit()
            
            return {'message': 'Notification marked as read'}, 200
        except Exception as e:
            db.session.rollback()
            api.abort(500, f"Failed to mark notification as read: {str(e)}")

# API Health Check
@api_bp.route('/health')
def api_health():
    """API health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'version': '1.0'
    })

# Error handlers - Fixed to handle Flask-RESTX properly
try:
    @api.errorhandler(400)
    def bad_request(error):
        """Handle 400 errors"""
        return {'error': 'Bad Request', 'code': 400}, 400

    @api.errorhandler(401)
    def unauthorized(error):
        """Handle 401 errors"""
        return {'error': 'Unauthorized', 'code': 401}, 401

    @api.errorhandler(403)
    def forbidden(error):
        """Handle 403 errors"""
        return {'error': 'Forbidden', 'code': 403}, 403

    @api.errorhandler(404)
    def not_found(error):
        """Handle 404 errors"""
        return {'error': 'Not Found', 'code': 404}, 404

    @api.errorhandler(500)
    def internal_error(error):
        """Handle 500 errors"""
        db.session.rollback()
        return {'error': 'Internal Server Error', 'code': 500}, 500
except Exception as e:
    print(f"Warning: Could not register API error handlers: {e}")
    # Fallback error handlers using blueprint
    @api_bp.errorhandler(400)
    def bad_request(error):
        return jsonify({'error': 'Bad Request', 'code': 400}), 400

    @api_bp.errorhandler(401)
    def unauthorized(error):
        return jsonify({'error': 'Unauthorized', 'code': 401}), 401

    @api_bp.errorhandler(403)
    def forbidden(error):
        return jsonify({'error': 'Forbidden', 'code': 403}), 403

    @api_bp.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Not Found', 'code': 404}), 404

    @api_bp.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return jsonify({'error': 'Internal Server Error', 'code': 500}), 500
