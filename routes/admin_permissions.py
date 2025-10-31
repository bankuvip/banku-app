"""
Admin Permission Management Routes
Handles permission management using the new relational system
"""

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
from models import db, Permission, Role, RolePermission, User, UserPermission, UserRole
from utils.permissions_relational import grant_user_permission, revoke_user_permission, get_user_permissions
from utils.permission_catalog import PermissionCatalog
from datetime import datetime, timedelta
from functools import wraps
import json

admin_permissions_bp = Blueprint('admin_permissions', __name__, url_prefix='/admin/permissions')

def admin_required(f):
    """Require admin role"""
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        from utils.permissions_relational import has_permission
        if not has_permission(current_user, 'admin', 'access'):
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

@admin_permissions_bp.route('/')
@login_required
@admin_required
def permission_dashboard():
    """Permission management dashboard"""
    
    # Get permission statistics
    total_permissions = Permission.query.count()
    total_roles = Role.query.count()
    total_users = User.query.count()
    
    # Get permission groups
    permission_groups = PermissionCatalog.get_permission_groups()
    
    # Get recent permissions
    recent_permissions = Permission.query.order_by(Permission.created_at.desc()).limit(10).all()
    
    # Get roles with permission counts
    roles_with_counts = []
    for role in Role.query.all():
        permission_count = RolePermission.query.filter_by(role_id=role.id, granted=True).count()
        roles_with_counts.append({
            'role': role,
            'permission_count': permission_count
        })
    
    return render_template('admin/permission_dashboard.html',
                         total_permissions=total_permissions,
                         total_roles=total_roles,
                         total_users=total_users,
                         permission_groups=permission_groups,
                         recent_permissions=recent_permissions,
                         roles_with_counts=roles_with_counts)

@admin_permissions_bp.route('/catalog')
@login_required
@admin_required
def permission_catalog():
    """View permission catalog"""
    
    # Get all permissions grouped by category
    permissions_by_group = {}
    for group_name, group_data in PermissionCatalog.get_permission_groups().items():
        permissions = PermissionCatalog.get_permissions_by_group(group_name)
        permissions_by_group[group_name] = {
            'data': group_data,
            'permissions': permissions
        }
    
    return render_template('admin/permission_catalog.html',
                         permissions_by_group=permissions_by_group)

@admin_permissions_bp.route('/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_permission():
    """Add a new permission"""
    
    if request.method == 'POST':
        data = request.get_json()
        
        try:
            # Get form data
            group_name = data.get('group_name')
            resource = data.get('resource')
            action = data.get('action')
            description = data.get('description')
            
            # Validate required fields
            if not all([group_name, resource, action, description]):
                return jsonify({'success': False, 'message': 'All fields are required'})
            
            # Get next available permission ID for the group
            permission_id = PermissionCatalog.get_next_permission_id(group_name)
            if not permission_id:
                return jsonify({'success': False, 'message': f'Group {group_name} is full'})
            
            # Check if permission already exists
            existing_permission = Permission.query.filter_by(name=f"{resource}.{action}").first()
            if existing_permission:
                return jsonify({'success': False, 'message': 'Permission already exists'})
            
            # Create new permission
            permission = Permission(
                id=permission_id,
                name=f"{resource}.{action}",
                description=description,
                category=group_name,
                resource=resource,
                action=action,
                is_system=False,
                created_at=datetime.utcnow()
            )
            
            db.session.add(permission)
            db.session.commit()
            
            return jsonify({'success': True, 'message': 'Permission added successfully'})
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': f'Error adding permission: {str(e)}'})
    
    # GET request - show form
    permission_groups = PermissionCatalog.get_permission_groups()
    return render_template('admin/add_permission.html',
                         permission_groups=permission_groups)

@admin_permissions_bp.route('/edit/<int:permission_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_permission(permission_id):
    """Edit an existing permission"""
    
    permission = Permission.query.get_or_404(permission_id)
    
    if request.method == 'POST':
        data = request.get_json()
        
        try:
            # Update permission
            permission.description = data.get('description', permission.description)
            permission.category = data.get('category', permission.category)
            
            db.session.commit()
            
            return jsonify({'success': True, 'message': 'Permission updated successfully'})
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': f'Error updating permission: {str(e)}'})
    
    # GET request - show form
    permission_groups = PermissionCatalog.get_permission_groups()
    return render_template('admin/edit_permission.html',
                         permission=permission,
                         permission_groups=permission_groups)

@admin_permissions_bp.route('/delete/<int:permission_id>', methods=['POST'])
@login_required
@admin_required
def delete_permission(permission_id):
    """Delete a permission"""
    
    permission = Permission.query.get_or_404(permission_id)
    
    try:
        # Check if permission is system-defined
        if permission.is_system:
            return jsonify({'success': False, 'message': 'Cannot delete system-defined permissions'})
        
        # Check if permission is being used
        role_permissions = RolePermission.query.filter_by(permission_id=permission_id).count()
        user_permissions = UserPermission.query.filter_by(permission_id=permission_id).count()
        
        if role_permissions > 0 or user_permissions > 0:
            return jsonify({'success': False, 'message': 'Cannot delete permission that is currently assigned'})
        
        # Delete permission
        db.session.delete(permission)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Permission deleted successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error deleting permission: {str(e)}'})

@admin_permissions_bp.route('/user-permissions/<int:user_id>')
@login_required
@admin_required
def user_permissions(user_id):
    """View and manage user permissions"""
    
    user = User.query.get_or_404(user_id)
    
    # Get user's roles and permissions
    user_roles = UserRole.query.filter_by(user_id=user_id, is_active=True).all()
    
    # Get all user permissions (from roles and direct)
    all_permissions = get_user_permissions(user)
    
    # Get direct user permissions
    direct_permissions = UserPermission.query.filter_by(user_id=user_id).all()
    
    # Get all available permissions for assignment
    all_available_permissions = Permission.query.order_by(Permission.resource, Permission.action).all()
    
    return render_template('admin/user_permissions.html',
                         user=user,
                         user_roles=user_roles,
                         all_permissions=all_permissions,
                         direct_permissions=direct_permissions,
                         all_available_permissions=all_available_permissions)

@admin_permissions_bp.route('/grant-user-permission', methods=['POST'])
@login_required
@admin_required
def grant_user_permission_route():
    """Grant direct permission to a user"""
    
    data = request.get_json()
    
    try:
        user_id = data.get('user_id')
        permission_id = data.get('permission_id')
        expires_at = data.get('expires_at')
        granted_by = current_user.id
        
        # Parse expiration date if provided
        expires_datetime = None
        if expires_at:
            expires_datetime = datetime.strptime(expires_at, '%Y-%m-%d')
        
        # Grant permission
        success = grant_user_permission(
            user_id=user_id,
            permission_id=permission_id,
            granted_by=granted_by,
            expires_at=expires_datetime
        )
        
        if success:
            return jsonify({'success': True, 'message': 'Permission granted successfully'})
        else:
            return jsonify({'success': False, 'message': 'Failed to grant permission'})
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error granting permission: {str(e)}'})

@admin_permissions_bp.route('/revoke-user-permission', methods=['POST'])
@login_required
@admin_required
def revoke_user_permission_route():
    """Revoke direct permission from a user"""
    
    data = request.get_json()
    
    try:
        user_id = data.get('user_id')
        permission_id = data.get('permission_id')
        
        # Revoke permission
        success = revoke_user_permission(user_id=user_id, permission_id=permission_id)
        
        if success:
            return jsonify({'success': True, 'message': 'Permission revoked successfully'})
        else:
            return jsonify({'success': False, 'message': 'Permission not found or already revoked'})
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error revoking permission: {str(e)}'})

@admin_permissions_bp.route('/role-permissions/<int:role_id>')
@login_required
@admin_required
def role_permissions(role_id):
    """View and manage role permissions"""
    
    role = Role.query.get_or_404(role_id)
    
    # Get all permissions grouped by resource
    permissions_by_resource = {}
    all_permissions = Permission.query.order_by(Permission.resource, Permission.action).all()
    
    for permission in all_permissions:
        if permission.resource not in permissions_by_resource:
            permissions_by_resource[permission.resource] = []
        permissions_by_resource[permission.resource].append(permission)
    
    # Get role's current permissions
    role_permissions = RolePermission.query.filter_by(role_id=role_id).all()
    role_permission_ids = {rp.permission_id: rp.granted for rp in role_permissions}
    
    return render_template('admin/role_permissions.html',
                         role=role,
                         permissions_by_resource=permissions_by_resource,
                         role_permission_ids=role_permission_ids)

@admin_permissions_bp.route('/update-role-permissions/<int:role_id>', methods=['POST'])
@login_required
@admin_required
def update_role_permissions(role_id):
    """Update permissions for a role"""
    
    role = Role.query.get_or_404(role_id)
    data = request.get_json()
    
    try:
        permissions = data.get('permissions', [])
        
        # Clear existing role permissions
        RolePermission.query.filter_by(role_id=role_id).delete()
        
        # Add new permissions
        for perm_data in permissions:
            if perm_data.get('granted', False):
                role_permission = RolePermission(
                    role_id=role_id,
                    permission_id=perm_data['permission_id'],
                    granted=True,
                    created_at=datetime.utcnow()
                )
                db.session.add(role_permission)
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Role permissions updated successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error updating role permissions: {str(e)}'})

@admin_permissions_bp.route('/bulk-import', methods=['POST'])
@login_required
@admin_required
def bulk_import_permissions():
    """Import permissions from catalog"""
    
    imported_count = 0
    updated_count = 0
    errors = []
    
    try:
        # Get all permissions from catalog
        all_permissions = PermissionCatalog.get_all_permissions()
        
        if not all_permissions:
            return jsonify({
                'success': False,
                'message': 'No permissions found in catalog.'
            }), 400
        
        # Process each permission individually with its own transaction handling
        for permission_id, permission_data in all_permissions.items():
            try:
                # Validate permission_data structure
                if not isinstance(permission_data, dict):
                    errors.append(f"Permission {permission_id}: Invalid data structure")
                    continue
                
                if 'name' not in permission_data or 'resource' not in permission_data or 'action' not in permission_data:
                    errors.append(f"Permission {permission_id}: Missing required fields (name, resource, or action)")
                    continue
                
                # Get category
                try:
                    category = PermissionCatalog.get_permission_group_by_id(permission_id)
                except Exception as cat_error:
                    category = 'unknown'
                    errors.append(f"Permission {permission_id}: Could not determine category: {str(cat_error)}")
                
                # Check if permission exists by name or ID
                existing_permission = Permission.query.filter_by(id=permission_id).first()
                
                if not existing_permission:
                    # Also check by name in case ID doesn't match
                    existing_permission = Permission.query.filter_by(name=permission_data['name']).first()
                
                if existing_permission:
                    # Update existing permission (don't change ID if it already exists with different ID)
                    existing_permission.name = permission_data['name']
                    existing_permission.description = permission_data.get('description', '')
                    existing_permission.category = category
                    existing_permission.resource = permission_data['resource']
                    existing_permission.action = permission_data['action']
                    existing_permission.is_system = True
                    # Try to flush to catch any errors early
                    try:
                        db.session.flush()
                    except Exception as flush_error:
                        db.session.rollback()
                        error_msg = f"Permission {permission_id} ({permission_data.get('name', 'unknown')}): Flush error: {str(flush_error)}"
                        errors.append(error_msg)
                        current_app.logger.error(f"Permission {permission_id} flush error: {error_msg}")
                        continue
                    updated_count += 1
                else:
                    # Create new permission
                    permission = Permission(
                        id=permission_id,
                        name=permission_data['name'],
                        description=permission_data.get('description', ''),
                        category=category,
                        resource=permission_data['resource'],
                        action=permission_data['action'],
                        is_system=True,
                        created_at=datetime.utcnow()
                    )
                    db.session.add(permission)
                    # Try to flush to catch any errors early
                    try:
                        db.session.flush()
                    except Exception as flush_error:
                        db.session.rollback()
                        error_msg = f"Permission {permission_id} ({permission_data.get('name', 'unknown')}): Flush error: {str(flush_error)}"
                        errors.append(error_msg)
                        current_app.logger.error(f"Permission {permission_id} flush error: {error_msg}")
                        continue
                    imported_count += 1
                    
            except Exception as perm_error:
                # Catch any other errors (validation, etc.)
                import traceback
                error_trace = traceback.format_exc()
                error_msg = f"Permission {permission_id} ({permission_data.get('name', 'unknown') if isinstance(permission_data, dict) else 'unknown'}): {str(perm_error)}"
                errors.append(error_msg)
                current_app.logger.error(f"Permission {permission_id} error: {error_trace}")
                # Ensure session is clean
                try:
                    db.session.rollback()
                except:
                    pass
                continue
        
        # Commit all successful changes at once
        try:
            db.session.commit()
        except Exception as commit_error:
            db.session.rollback()
            return jsonify({
                'success': False,
                'message': f'Database commit failed: {str(commit_error)}'
            }), 500
        
        # All permissions processed, return results
        if errors:
            # If there are errors, still report success with warnings
            error_msg = f'{imported_count} imported, {updated_count} updated. {len(errors)} error(s) occurred.'
            return jsonify({
                'success': True,
                'message': error_msg,
                'warnings': errors[:10]  # Limit to first 10 errors
            })
        else:
            return jsonify({
                'success': True, 
                'message': f'Bulk import completed: {imported_count} imported, {updated_count} updated'
            })
        
    except Exception as e:
        # Final safety net - rollback everything if something catastrophic happens
        try:
            db.session.rollback()
        except:
            pass
        import traceback
        error_details = traceback.format_exc()
        current_app.logger.error(f'Bulk import error: {str(e)}\n{error_details}')
        return jsonify({
            'success': False, 
            'message': f'Error during bulk import: {str(e)}'
        }), 500

@admin_permissions_bp.route('/validation-report')
@login_required
@admin_required
def validation_report():
    """Generate permission validation report"""
    
    # Check for orphaned permissions
    orphaned_permissions = []
    all_permissions = Permission.query.all()
    
    for permission in all_permissions:
        role_permissions = RolePermission.query.filter_by(permission_id=permission.id).count()
        user_permissions = UserPermission.query.filter_by(permission_id=permission.id).count()
        
        if role_permissions == 0 and user_permissions == 0:
            orphaned_permissions.append(permission)
    
    # Check for roles without permissions
    roles_without_permissions = []
    all_roles = Role.query.all()
    
    for role in all_roles:
        permission_count = RolePermission.query.filter_by(role_id=role.id, granted=True).count()
        if permission_count == 0:
            roles_without_permissions.append(role)
    
    # Check for users without roles
    users_without_roles = []
    all_users = User.query.all()
    
    for user in all_users:
        role_count = UserRole.query.filter_by(user_id=user.id, is_active=True).count()
        if role_count == 0:
            users_without_roles.append(user)
    
    return render_template('admin/permission_validation.html',
                         orphaned_permissions=orphaned_permissions,
                         roles_without_permissions=roles_without_permissions,
                         users_without_roles=users_without_roles)

