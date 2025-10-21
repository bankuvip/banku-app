"""
Permission checking utilities for the BankU application
Provides decorators and functions for role-based access control
"""

from functools import wraps
from flask import current_app, request, jsonify, redirect, url_for, flash
from flask_login import current_user
from models import Role, UserRole, Permission, RolePermission, UserPermission

def has_permission(user, resource, action):
    """
    Check if a user has permission to perform an action on a resource
    
    Args:
        user: User object
        resource: String resource name (e.g., 'users', 'deals', 'organizations')
        action: String action name (e.g., 'create', 'read', 'update', 'delete')
    
    Returns:
        bool: True if user has permission, False otherwise
    """
    try:
        if not user or not user.is_authenticated:
            return False
        
        # Super admin bypass (if user has Admin role)
        try:
            admin_role = next((role.name for role in user.roles if role.name == 'Admin'), None)
            if admin_role:
                return True
        except Exception as e:
            current_app.logger.warning(f"Error checking admin role: {e}")
        
        # Check user's roles for the required permission using relational system
        try:
            # Find the permission in the database
            permission = Permission.query.filter_by(resource=resource, action=action).first()
            if not permission:
                return False
            
            # Check if user has this permission through any of their roles
            for user_role in user.roles:
                role = user_role.role if hasattr(user_role, 'role') else user_role
                # Check if role has this permission
                role_permission = RolePermission.query.filter_by(
                    role_id=role.id, 
                    permission_id=permission.id, 
                    granted=True
                ).first()
                if role_permission:
                    return True
            
            # Check if user has direct permission override
            user_permission = UserPermission.query.filter_by(
                user_id=user.id, 
                permission_id=permission.id, 
                granted=True
            ).first()
            if user_permission:
                return True
                
        except Exception as e:
            current_app.logger.error(f"Error checking user permissions: {e}")
            return False
        
        return False
    except Exception as e:
        current_app.logger.error(f"Permission check failed: {e}")
        return False

def has_any_permission(user, resource, actions):
    """
    Check if a user has any of the specified permissions for a resource
    
    Args:
        user: User object
        resource: String resource name
        actions: List of action strings
    
    Returns:
        bool: True if user has any of the permissions, False otherwise
    """
    return any(has_permission(user, resource, action) for action in actions)

def has_all_permissions(user, resource, actions):
    """
    Check if a user has all of the specified permissions for a resource
    
    Args:
        user: User object
        resource: String resource name
        actions: List of action strings
    
    Returns:
        bool: True if user has all permissions, False otherwise
    """
    return all(has_permission(user, resource, action) for action in actions)

def require_permission(resource, action, redirect_url=None, json_response=False):
    """
    Decorator to require a specific permission for a route
    
    Args:
        resource: String resource name
        action: String action name
        redirect_url: URL to redirect to if permission denied
        json_response: If True, return JSON error instead of redirect
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not has_permission(current_user, resource, action):
                # User-friendly error messages
                error_messages = {
                    ('deals', 'create'): 'You need permission to create deals. Please contact customer support.',
                    ('deals', 'read'): 'You need permission to view deals. Please contact customer support.',
                    ('deals', 'update'): 'You need permission to update deals. Please contact customer support.',
                    ('deals', 'delete'): 'You need permission to delete deals. Please contact customer support.',
                    ('banks', 'create'): 'You need permission to create banks. Please contact customer support.',
                    ('banks', 'read'): 'You need permission to view banks. Please contact customer support.',
                    ('organizations', 'create'): 'You need permission to create organizations. Please contact customer support.',
                    ('organizations', 'read'): 'You need permission to view organizations. Please contact customer support.',
                    ('organizations', 'update'): 'You need permission to modify organizations. Please contact customer support.',
                    ('organizations', 'delete'): 'You need permission to delete organizations. Please contact customer support.',
                    ('ai_matching', 'access_dashboard'): 'You need permission to access AI Matcher. Please contact customer support.',
                    ('profiles', 'create'): 'You need permission to create profiles. Please contact customer support.',
                    ('profiles', 'read'): 'You need permission to view profiles. Please contact customer support.',
                    ('profiles', 'update'): 'You need permission to modify profiles. Please contact customer support.',
                    ('profiles', 'delete'): 'You need permission to delete profiles. Please contact customer support.',
                    ('items', 'create'): 'You need permission to create items. Please contact customer support.',
                    ('items', 'read'): 'You need permission to view items. Please contact customer support.',
                    ('items', 'update'): 'You need permission to modify items. Please contact customer support.',
                    ('items', 'delete'): 'You need permission to delete items. Please contact customer support.',
                    ('chatbots', 'read'): 'You need permission to use chatbots. Please contact customer support.',
                    ('admin', 'access'): 'You need admin permissions to access this area. Please contact customer support.',
                    ('admin', 'manage_items'): 'You need admin permissions to manage items. Please contact customer support.',
                    ('admin', 'delete_any_item'): 'You need admin permissions to delete any item. Please contact customer support.',
                    ('admin', 'verify_items'): 'You need admin permissions to verify items. Please contact customer support.'
                }
                
                user_friendly_message = error_messages.get((resource, action), 'You need permission to access this feature. Please contact customer support.')
                
                if json_response:
                    return jsonify({
                        'success': False,
                        'message': user_friendly_message,
                        'error': 'permission_denied'
                    }), 403
                else:
                    if redirect_url:
                        flash(user_friendly_message, 'error')
                        return redirect(redirect_url)
                    else:
                        flash(user_friendly_message, 'error')
                        # Return to previous page instead of dashboard
                        return redirect(request.referrer or url_for('index'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def require_any_permission(resource, actions, redirect_url=None, json_response=False):
    """
    Decorator to require any of the specified permissions for a route
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not has_any_permission(current_user, resource, actions):
                if json_response:
                    return jsonify({
                        'success': False,
                        'message': f'Insufficient permissions. Required: {resource}:{actions}',
                        'error': 'permission_denied'
                    }), 403
                else:
                    if redirect_url:
                        flash('You do not have permission to access this resource.', 'error')
                        return redirect(redirect_url)
                    else:
                        flash('Access denied. Insufficient permissions.', 'error')
                        # Return to previous page instead of dashboard
                        return redirect(request.referrer or url_for('index'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def require_all_permissions(resource, actions, redirect_url=None, json_response=False):
    """
    Decorator to require all of the specified permissions for a route
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not has_all_permissions(current_user, resource, actions):
                if json_response:
                    return jsonify({
                        'success': False,
                        'message': f'Insufficient permissions. Required: {resource}:{actions}',
                        'error': 'permission_denied'
                    }), 403
                else:
                    if redirect_url:
                        flash('You do not have permission to access this resource.', 'error')
                        return redirect(redirect_url)
                    else:
                        flash('Access denied. Insufficient permissions.', 'error')
                        # Return to previous page instead of dashboard
                        return redirect(request.referrer or url_for('index'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def admin_required(f):
    """
    Decorator to require admin role
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user or not current_user.is_authenticated or not any(role.name == 'Admin' for role in current_user.roles):
            flash('Admin access required.', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def require_admin_role():
    """
    Decorator factory to require admin role (alias for admin_required)
    """
    return admin_required


def require_admin_or_connector(f=None):
    """
    Decorator to require admin or connector role
    Can be used with or without parentheses
    """
    def decorator(func):
        @wraps(func)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Authentication required.', 'error')
                return redirect(url_for('auth.login'))
            
            if not (any(role.name == 'Admin' for role in current_user.roles) or any(role.name == 'Connector' for role in current_user.roles)):
                flash('Admin or Connector access required.', 'error')
                return redirect(request.referrer or url_for('index'))
            
            return func(*args, **kwargs)
        return decorated_function
    
    if f is None:
        # Called with parentheses: @require_admin_or_connector()
        return decorator
    else:
        # Called without parentheses: @require_admin_or_connector
        return decorator(f)

def internal_staff_required(f):
    """
    Decorator to require internal staff role (Admin, Connector, Collector, Verifier)
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Authentication required.', 'error')
            return redirect(url_for('auth.login'))
        
        internal_roles = ['Admin', 'Connector', 'Collector', 'Verifier', 'Content Manager', 'Data Analyst', 'System Administrator']
        if not any(any(user_role.name == role for user_role in current_user.roles) for role in internal_roles):
            flash('Internal staff access required.', 'error')
            return redirect(request.referrer or url_for('index'))
        
        return f(*args, **kwargs)
    return decorated_function

def admin_item_management_required(f):
    """
    Decorator to require admin permissions for item management
    This allows admins to manage any item regardless of ownership
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Authentication required.', 'error')
            return redirect(url_for('auth.login'))
        
        # Check if user has admin role
        if not any(role.name == 'Admin' for role in current_user.roles):
            flash('Admin access required for item management.', 'error')
            return redirect(url_for('auth.login'))
        
        return f(*args, **kwargs)
    return decorated_function

def get_user_permissions(user):
    """
    Get all permissions for a user
    
    Args:
        user: User object
    
    Returns:
        dict: Dictionary of resource -> list of actions
    """
    if not user or not user.is_authenticated:
        return {}
    
    permissions = {}
    
    # Get permissions from roles
    for user_role in user.roles:
        role = user_role.role if hasattr(user_role, 'role') else user_role
        # Get role permissions from relational system
        role_permissions = RolePermission.query.filter_by(role_id=role.id, granted=True).all()
        for rp in role_permissions:
            permission = Permission.query.get(rp.permission_id)
            if permission:
                resource = permission.resource
                action = permission.action
                if resource not in permissions:
                    permissions[resource] = set()
                permissions[resource].add(action)
    
    # Get direct user permissions
    user_permissions = UserPermission.query.filter_by(user_id=user.id, granted=True).all()
    for up in user_permissions:
        permission = Permission.query.get(up.permission_id)
        if permission:
            resource = permission.resource
            action = permission.action
            if resource not in permissions:
                permissions[resource] = set()
            permissions[resource].add(action)
    
    # Convert sets to lists for JSON serialization
    return {resource: list(actions) for resource, actions in permissions.items()}

def check_resource_access(user, resource, action, resource_owner_id=None):
    """
    Check if user can access a specific resource, considering ownership
    
    Args:
        user: User object
        resource: String resource name
        action: String action name
        resource_owner_id: ID of the resource owner (for ownership checks)
    
    Returns:
        bool: True if user has access, False otherwise
    """
    # Check basic permission
    if not has_permission(user, resource, action):
        return False
    
    # If it's a read/update/delete action and user is the owner, allow it
    if action in ['read', 'update', 'delete'] and resource_owner_id and user.id == resource_owner_id:
        return True
    
    # If user has admin permissions, allow all actions
    if has_permission(user, resource, action):
        return True
    
    return False

def get_accessible_resources(user, resource_type):
    """
    Get list of resources a user can access based on their permissions
    
    Args:
        user: User object
        resource_type: Type of resource to filter (e.g., 'deals', 'organizations')
    
    Returns:
        list: List of resource IDs the user can access
    """
    if not user or not user.is_authenticated:
        return []
    
    # This would need to be implemented based on specific resource types
    # For now, return empty list as a placeholder
    return []

# Template helper functions
def can_access(user, resource, action):
    """Template helper to check permissions in Jinja2 templates"""
    return has_permission(user, resource, action)

def can_access_any(user, resource, actions):
    """Template helper to check any permission in Jinja2 templates"""
    return has_any_permission(user, resource, actions)

def can_access_all(user, resource, actions):
    """Template helper to check all permissions in Jinja2 templates"""
    return has_all_permissions(user, resource, actions)

# Make functions available in templates
def register_template_helpers(app):
    """Register permission helper functions for use in templates"""
    app.jinja_env.globals.update(
        can_access=can_access,
        can_access_any=can_access_any,
        can_access_all=can_access_all
    )