"""
Relational Permission System
Updated permission checking utilities for the BankU application
Uses the new relational permission tables instead of JSON
"""

from functools import wraps
from flask import current_app, request, jsonify, redirect, url_for, flash
from flask_login import current_user
from models import Role, UserRole, Permission, RolePermission, UserPermission
from datetime import datetime

def has_permission(user, resource, action):
    """
    Check if a user has permission to perform an action on a resource
    Uses the new relational permission system
    
    Args:
        user: User object
        resource: String resource name (e.g., 'users', 'deals', 'organizations')
        action: String action name (e.g., 'create', 'view', 'edit', 'delete')
    
    Returns:
        bool: True if user has permission, False otherwise
    """
    try:
        if not user or not user.is_authenticated:
            return False
        
        # Super admin bypass (if user has Admin role)
        try:
            admin_role = Role.query.filter_by(name='Admin').first()
            if admin_role:
                user_role = UserRole.query.filter_by(
                    user_id=user.id, 
                    role_id=admin_role.id, 
                    is_active=True
                ).first()
                if user_role:
                    return True
        except Exception as e:
            current_app.logger.warning(f"Error checking admin role: {e}")
        
        # Check for direct user permission overrides (expired permissions are ignored)
        try:
            direct_permission = UserPermission.query.join(Permission).filter(
                UserPermission.user_id == user.id,
                Permission.resource == resource,
                Permission.action == action,
                UserPermission.granted == True,
                (UserPermission.expires_at.is_(None)) | (UserPermission.expires_at > datetime.utcnow())
            ).first()
            
            if direct_permission:
                return True
        except Exception as e:
            current_app.logger.error(f"Error checking direct user permissions: {e}")
        
        # Check user's roles for the required permission
        try:
            # Get all active user roles
            user_roles = UserRole.query.filter_by(
                user_id=user.id, 
                is_active=True
            ).all()
            
            for user_role in user_roles:
                # Check if this role has the required permission
                role_permission = RolePermission.query.join(Permission).filter(
                    RolePermission.role_id == user_role.role_id,
                    Permission.resource == resource,
                    Permission.action == action,
                    RolePermission.granted == True
                ).first()
                
                if role_permission:
                    return True
                    
        except Exception as e:
            current_app.logger.error(f"Error checking user role permissions: {e}")
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

def get_user_permissions(user):
    """
    Get all permissions for a user (from roles and direct assignments)
    
    Args:
        user: User object
    
    Returns:
        dict: Dictionary with resource as key and list of actions as value
    """
    try:
        if not user or not user.is_authenticated:
            return {}
        
        permissions = {}
        
        # Get permissions from roles
        user_roles = UserRole.query.filter_by(user_id=user.id, is_active=True).all()
        
        for user_role in user_roles:
            role_permissions = RolePermission.query.join(Permission).filter(
                RolePermission.role_id == user_role.role_id,
                RolePermission.granted == True
            ).all()
            
            for role_permission in role_permissions:
                resource = role_permission.permission.resource
                action = role_permission.permission.action
                
                if resource not in permissions:
                    permissions[resource] = []
                if action not in permissions[resource]:
                    permissions[resource].append(action)
        
        # Get direct user permissions (not expired)
        direct_permissions = UserPermission.query.join(Permission).filter(
            UserPermission.user_id == user.id,
            UserPermission.granted == True,
            (UserPermission.expires_at.is_(None)) | (UserPermission.expires_at > datetime.utcnow())
        ).all()
        
        for direct_permission in direct_permissions:
            resource = direct_permission.permission.resource
            action = direct_permission.permission.action
            
            if resource not in permissions:
                permissions[resource] = []
            if action not in permissions[resource]:
                permissions[resource].append(action)
        
        return permissions
        
    except Exception as e:
        current_app.logger.error(f"Error getting user permissions: {e}")
        return {}

def require_permission(resource, action, redirect_url=None, json_response=False):
    """
    Decorator to require a specific permission for a route
    Uses the new relational permission system
    
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
                    ('deals', 'view'): 'You need permission to view deals. Please contact customer support.',
                    ('deals', 'edit'): 'You need permission to update deals. Please contact customer support.',
                    ('deals', 'delete'): 'You need permission to delete deals. Please contact customer support.',
                    ('banks', 'create'): 'You need permission to create banks. Please contact customer support.',
                    ('banks', 'view'): 'You need permission to view banks. Please contact customer support.',
                    ('organizations', 'create'): 'You need permission to create organizations. Please contact customer support.',
                    ('organizations', 'view'): 'You need permission to view organizations. Please contact customer support.',
                    ('organizations', 'edit'): 'You need permission to modify organizations. Please contact customer support.',
                    ('organizations', 'delete'): 'You need permission to delete organizations. Please contact customer support.',
                    ('ai_matching', 'access_dashboard'): 'You need permission to access AI Matcher. Please contact customer support.',
                    ('profiles', 'create'): 'You need permission to create profiles. Please contact customer support.',
                    ('profiles', 'view'): 'You need permission to view profiles. Please contact customer support.',
                    ('profiles', 'edit'): 'You need permission to edit profiles. Please contact customer support.',
                    ('profiles', 'delete'): 'You need permission to delete profiles. Please contact customer support.',
                    ('users', 'create'): 'You need permission to create users. Please contact customer support.',
                    ('users', 'view'): 'You need permission to view users. Please contact customer support.',
                    ('users', 'edit'): 'You need permission to edit users. Please contact customer support.',
                    ('users', 'delete'): 'You need permission to delete users. Please contact customer support.',
                    ('admin', 'access'): 'You need admin access. Please contact customer support.',
                    ('deal_requests', 'create'): 'You need permission to create deal requests. Please contact customer support.',
                    ('deal_requests', 'view_own'): 'You need permission to view your deal requests. Please contact customer support.',
                    ('deal_requests', 'view_all'): 'You need permission to view all deal requests. Please contact customer support.',
                }
                
                error_message = error_messages.get((resource, action), 
                    f'You need permission to perform "{action}" on "{resource}". Please contact customer support.')
                
                if json_response:
                    return jsonify({
                        'success': False,
                        'message': error_message,
                        'error': 'permission_denied'
                    }), 403
                else:
                    if redirect_url:
                        flash(error_message, 'error')
                        return redirect(redirect_url)
                    else:
                        flash(error_message, 'error')
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
                        return redirect(request.referrer or url_for('index'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def grant_user_permission(user_id, permission_id, granted_by=None, expires_at=None):
    """
    Grant a direct permission to a user (override role permissions)
    
    Args:
        user_id: User ID
        permission_id: Permission ID
        granted_by: User ID who granted the permission
        expires_at: Optional expiration datetime
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Check if permission already exists
        existing = UserPermission.query.filter_by(
            user_id=user_id,
            permission_id=permission_id
        ).first()
        
        if existing:
            # Update existing permission
            existing.granted = True
            existing.granted_by = granted_by
            existing.granted_at = datetime.utcnow()
            existing.expires_at = expires_at
        else:
            # Create new permission
            user_permission = UserPermission(
                user_id=user_id,
                permission_id=permission_id,
                granted=True,
                granted_by=granted_by,
                granted_at=datetime.utcnow(),
                expires_at=expires_at
            )
            db.session.add(user_permission)
        
        db.session.commit()
        return True
        
    except Exception as e:
        current_app.logger.error(f"Error granting user permission: {e}")
        db.session.rollback()
        return False

def revoke_user_permission(user_id, permission_id):
    """
    Revoke a direct permission from a user
    
    Args:
        user_id: User ID
        permission_id: Permission ID
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        user_permission = UserPermission.query.filter_by(
            user_id=user_id,
            permission_id=permission_id
        ).first()
        
        if user_permission:
            db.session.delete(user_permission)
            db.session.commit()
            return True
        
        return False
        
    except Exception as e:
        current_app.logger.error(f"Error revoking user permission: {e}")
        db.session.rollback()
        return False

def get_permission_by_name(permission_name):
    """
    Get permission by name (e.g., 'users.view')
    
    Args:
        permission_name: Permission name string
    
    Returns:
        Permission object or None
    """
    try:
        return Permission.query.filter_by(name=permission_name).first()
    except Exception as e:
        current_app.logger.error(f"Error getting permission by name: {e}")
        return None

def get_permissions_by_resource(resource):
    """
    Get all permissions for a specific resource
    
    Args:
        resource: Resource name string
    
    Returns:
        List of Permission objects
    """
    try:
        return Permission.query.filter_by(resource=resource).all()
    except Exception as e:
        current_app.logger.error(f"Error getting permissions by resource: {e}")
        return []

