"""
Organization Management Routes
Handles creation, management, and administration of organizations
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from models import db, OrganizationType, Organization, OrganizationMember, OrganizationContent, OrganizationHistory, User
from utils.permissions import require_permission
from utils.data_collection import collection_engine
from datetime import datetime
import re
import uuid
import json

organizations_bp = Blueprint('organizations', __name__)

def create_slug(name):
    """Create a URL-friendly slug from organization name"""
    slug = re.sub(r'[^\w\s-]', '', name.lower())
    slug = re.sub(r'[-\s]+', '-', slug)
    return slug[:50]  # Limit length

def check_user_organization_limit(user_id, organization_type_id):
    """Check if user can create more organizations of this type"""
    organization_type = OrganizationType.query.get(organization_type_id)
    if not organization_type:
        return False, "Invalid organization type"
    
    # Count existing organizations of this type by this user
    existing_count = db.session.query(Organization).join(OrganizationMember).filter(
        Organization.organization_type_id == organization_type_id,
        OrganizationMember.user_id == user_id,
        OrganizationMember.role == 'owner',
        Organization.status == 'active'
    ).count()
    
    if existing_count >= organization_type.max_profiles_per_user:
        return False, f"You can only create {organization_type.max_profiles_per_user} {organization_type.display_name.lower()} organizations"
    
    return True, "OK"

@organizations_bp.route('/organizations')
@login_required
@require_permission('organizations', 'view')
def index():
    """List user's organizations"""
    # Get organizations where user is a member
    organizations = db.session.query(Organization).join(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.status == 'active'
    ).order_by(Organization.created_at.desc()).all()
    
    return render_template('organizations/index.html', organizations=organizations)

@organizations_bp.route('/organizations/create')
@login_required
@require_permission('organizations', 'create')
def create():
    """Show organization creation wizard"""
    organization_types = OrganizationType.query.filter_by(is_active=True).order_by(OrganizationType.order_index, OrganizationType.display_name).all()
    return render_template('organizations/create.html', organization_types=organization_types)

@organizations_bp.route('/organizations/test', methods=['POST'])
def test_create():
    """Test organization creation without permissions"""
    try:
        print("=== Test Organization Creation ===")
        return jsonify({'success': True, 'message': 'Test route working'})
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Test error: {error_details}")
        return jsonify({'success': False, 'error': str(e)}), 500

@organizations_bp.route('/organizations/simple', methods=['POST'])
def simple_create():
    """Simple organization creation test"""
    return jsonify({'success': True, 'message': 'Simple route working'})

@organizations_bp.route('/organizations/create-post', methods=['POST'])
def create_organization_new():
    """Handle organization creation"""
    try:
        print("=== ORGANIZATION CREATION ROUTE CALLED ===")
        
        # Get form data
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        organization_type_id = request.form.get('organization_type_id')
        is_public = request.form.get('is_public') == 'true'
        photo_file = request.files.get('photo')
        
        print(f"Name: '{name}'")
        print(f"Description: '{description}'")
        print(f"Organization Type ID: '{organization_type_id}'")
        print(f"Is Public: {is_public}")
        print(f"Photo file: {photo_file}")
        print(f"Request form data: {dict(request.form)}")
        
        # Basic validation
        if not name:
            return jsonify({'success': False, 'error': 'Organization name is required'}), 400
        
        if not organization_type_id:
            return jsonify({'success': False, 'error': 'Organization type is required'}), 400
        
        # Get organization type
        org_type = OrganizationType.query.get(organization_type_id)
        if not org_type:
            return jsonify({'success': False, 'error': 'Invalid organization type'}), 400
        
        # Create organization
        organization = Organization(
            name=name,
            description=description,
            organization_type_id=int(organization_type_id),
            is_public=is_public,
            created_by=current_user.id if current_user.is_authenticated else 1,  # Fallback for testing
            slug=create_slug(name)
        )
        
        db.session.add(organization)
        db.session.flush()  # Get the organization ID
        
        # Create organization member record to make the creator a member
        organization_member = OrganizationMember(
            organization_id=organization.id,
            user_id=current_user.id if current_user.is_authenticated else 1,
            role='owner',
            status='active',
            joined_at=datetime.utcnow()
        )
        
        db.session.add(organization_member)
        db.session.commit()
        
        print(f"Organization created successfully: {organization.id}")
        print(f"Organization member created: {organization_member.id}")
        
        return jsonify({
            'success': True, 
            'message': 'Organization created successfully',
            'organization_id': organization.id,
            'slug': organization.slug
        })
        
    except Exception as e:
        print(f"=== ERROR IN ORGANIZATION CREATION ===")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@organizations_bp.route('/organizations/<slug>')
@login_required
@require_permission('organizations', 'view')
def view(slug):
    """View organization details"""
    from utils.permissions import has_permission
    
    organization = Organization.query.filter_by(slug=slug).first_or_404()
    
    # Check if user has permission to view private organizations
    can_view_private = has_permission(current_user, 'organizations', 'view_private')
    
    # Always check for actual membership for content management
    membership = OrganizationMember.query.filter_by(
        organization_id=organization.id,
        user_id=current_user.id,
        status='active'
    ).first()
    
    # Check access permissions
    if can_view_private:
        # Users with private access can view any organization
        pass  # Allow access
    else:
        # Check if user has access
        if not membership and not organization.is_public:
            flash('You do not have access to this organization', 'error')
            return redirect(url_for('organizations.index'))
    
    # Get members
    members = OrganizationMember.query.filter_by(
        organization_id=organization.id,
        status='active'
    ).order_by(OrganizationMember.joined_at.asc()).all()
    
    # Get content (items and needs)
    content = OrganizationContent.query.filter_by(
        organization_id=organization.id,
        status='active'
    ).order_by(OrganizationContent.added_at.desc()).limit(20).all()
    
    # Get recent history
    history = OrganizationHistory.query.filter_by(
        organization_id=organization.id
    ).order_by(OrganizationHistory.occurred_at.desc()).limit(10).all()
    
    # Check About tab permissions
    is_owner = organization.created_by == current_user.id
    can_view_about = False
    
    if is_owner:
        # Owner can always see their own About tab
        can_view_about = True
    elif membership:
        # Active members can see About tab
        can_view_about = True
    else:
        # Others need view_about_others permission
        can_view_about = has_permission(current_user, 'organizations', 'view_about_others')
    
    # Check Members tab permissions
    can_view_members = False
    
    if is_owner:
        # Owner can always see their own Members tab
        can_view_members = True
    elif membership:
        # Active members can see Members tab
        can_view_members = True
    else:
        # Others need view_members_others permission
        can_view_members = has_permission(current_user, 'organizations', 'view_members_others')
    
    # Check Activity tab permissions
    can_view_activity = False
    
    if is_owner:
        # Owner can always see their own Activity tab
        can_view_activity = True
    elif membership:
        # Active members can see Activity tab
        can_view_activity = True
    else:
        # Others need view_activity_others permission
        can_view_activity = has_permission(current_user, 'organizations', 'view_activity_others')
    
    return render_template('organizations/view.html', 
                         organization=organization,
                         membership=membership,
                         members=members,
                         content=content,
                         history=history,
                         can_view_about=can_view_about,
                         can_view_members=can_view_members,
                         can_view_activity=can_view_activity,
                         is_owner=is_owner)

@organizations_bp.route('/organizations/<slug>/members')
@login_required
def members(slug):
    """Manage organization members"""
    organization = Organization.query.filter_by(slug=slug).first_or_404()
    
    # Check if user has admin access
    membership = OrganizationMember.query.filter_by(
        organization_id=organization.id,
        user_id=current_user.id,
        status='active'
    ).first()
    
    if not membership or membership.role not in ['owner', 'admin']:
        flash('You do not have permission to manage members', 'error')
        return redirect(url_for('organizations.view', slug=slug))
    
    members = OrganizationMember.query.filter_by(
        organization_id=organization.id
    ).order_by(OrganizationMember.joined_at.desc()).all()
    
    return render_template('organizations/members.html', 
                         organization=organization,
                         members=members,
                         current_member=membership)

@organizations_bp.route('/organizations/<slug>/content')
@login_required
def content(slug):
    """Manage organization content"""
    from utils.permissions import has_permission
    
    organization = Organization.query.filter_by(slug=slug).first_or_404()
    
    # Check if user has permission to view private organizations
    can_view_private = has_permission(current_user, 'organizations', 'view_private')
    
    # Always check for actual membership for content management
    membership = OrganizationMember.query.filter_by(
        organization_id=organization.id,
        user_id=current_user.id,
        status='active'
    ).first()
    
    # Check access permissions
    if can_view_private:
        # Users with private access can view any organization
        pass  # Allow access
    else:
        # Check if user has access
        if not membership and not organization.is_public:
            flash('You do not have access to this organization', 'error')
            return redirect(url_for('organizations.index'))
    
    # Get all content
    content = OrganizationContent.query.filter_by(
        organization_id=organization.id,
        status='active'
    ).order_by(OrganizationContent.added_at.desc()).all()
    
    return render_template('organizations/content.html', 
                         organization=organization,
                         membership=membership,
                         content=content)

@organizations_bp.route('/organizations/<slug>/create-item')
@login_required
def create_item_redirect(slug):
    """Redirect to item type selection for organization"""
    organization = Organization.query.filter_by(slug=slug).first_or_404()
    
    # Check if user has access to add content
    membership = OrganizationMember.query.filter_by(
        organization_id=organization.id,
        user_id=current_user.id,
        status='active'
    ).first()
    
    if not membership or membership.role not in ['owner', 'admin', 'member']:
        flash('You do not have permission to add items to this organization', 'error')
        return redirect(url_for('organizations.view', slug=slug))
    
    # Get all item types
    from models import ItemType
    item_types = ItemType.query.filter_by(is_active=True).all()
    
    return render_template('organizations/create_item_select.html', 
                         organization=organization,
                         item_types=item_types)

@organizations_bp.route('/organizations/<slug>/create-<item_type_name>')
@login_required
def create_item_by_type(slug, item_type_name):
    """Redirect to chatbot for specific item type within organization"""
    organization = Organization.query.filter_by(slug=slug).first_or_404()
    
    # Check if user has access to add content
    membership = OrganizationMember.query.filter_by(
        organization_id=organization.id,
        user_id=current_user.id,
        status='active'
    ).first()
    
    if not membership or membership.role not in ['owner', 'admin', 'member']:
        flash('You do not have permission to add items to this organization', 'error')
        return redirect(url_for('organizations.view', slug=slug))
    
    # Get the item type and its associated chatbot
    from models import ItemType
    item_type = ItemType.query.filter_by(name=item_type_name, is_active=True).first_or_404()
    
    # Check if there's a data storage mapping for this item type
    from models import DataStorageMapping
    mapping = DataStorageMapping.query.filter_by(
        item_type_id=item_type.id,
        is_active=True
    ).first()
    
    if not mapping:
        flash(f'No chatbot configured for {item_type.display_name}. Please contact admin to set up Data Storage Mapping.', 'error')
        return redirect(url_for('organizations.create_item_redirect', slug=slug))
    
    # Redirect to chatbot with organization context
    return redirect(url_for('chatbot.start_flow', flow_id=mapping.chatbot_id, organization_id=organization.id))

@organizations_bp.route('/organizations/<slug>/settings', methods=['GET', 'POST'])
@login_required
@require_permission('organizations', 'edit')
def settings(slug):
    """Organization settings page"""
    organization = Organization.query.filter_by(slug=slug).first_or_404()
    
    # Check if user has owner access
    membership = OrganizationMember.query.filter_by(
        organization_id=organization.id,
        user_id=current_user.id,
        status='active'
    ).first()
    
    if not membership or membership.role != 'owner':
        flash('Only the organization owner can access settings', 'error')
        return redirect(url_for('organizations.view', slug=slug))
    
    # Handle POST request for general settings
    if request.method == 'POST':
        try:
            # Update organization details
            organization.name = request.form.get('name', organization.name)
            organization.description = request.form.get('description', organization.description)
            organization.is_public = request.form.get('is_public') == '1'
            
            # Update new contact and social media fields
            organization.website = request.form.get('website', '') or None
            organization.phone = request.form.get('phone', '') or None
            organization.location = request.form.get('location', '') or None
            organization.linkedin_url = request.form.get('linkedin_url', '') or None
            organization.youtube_url = request.form.get('youtube_url', '') or None
            organization.facebook_url = request.form.get('facebook_url', '') or None
            organization.instagram_url = request.form.get('instagram_url', '') or None
            organization.tiktok_url = request.form.get('tiktok_url', '') or None
            organization.x_url = request.form.get('x_url', '') or None
            
            db.session.commit()
            flash('Settings updated successfully!', 'success')
            return redirect(url_for('organizations.settings', slug=slug))
        except Exception as e:
            db.session.rollback()
            flash('Error updating settings: ' + str(e), 'error')
    
    return render_template('organizations/settings.html', organization=organization)

@organizations_bp.route('/organizations/<slug>/join')
@login_required
def join(slug):
    """Join a public organization"""
    organization = Organization.query.filter_by(slug=slug).first_or_404()
    
    if not organization.is_public:
        flash('This organization is private', 'error')
        return redirect(url_for('organizations.view', slug=slug))
    
    # Check if already a member
    existing_membership = OrganizationMember.query.filter_by(
        organization_id=organization.id,
        user_id=current_user.id
    ).first()
    
    if existing_membership:
        if existing_membership.status == 'active':
            flash('You are already a member of this organization', 'info')
        elif existing_membership.status == 'left':
            # Rejoin
            existing_membership.status = 'active'
            existing_membership.joined_at = datetime.utcnow()
            existing_membership.left_at = None
            existing_membership.left_reason = None
            db.session.commit()
            flash('Welcome back to the organization!', 'success')
        else:
            flash('Your membership request is pending', 'info')
    else:
        # Create new membership
        member = OrganizationMember(
            organization_id=organization.id,
            user_id=current_user.id,
            role='member',
            status='active'
        )
        db.session.add(member)
        
        # Record in history
        history = OrganizationHistory(
            organization_id=organization.id,
            event_type='member_joined',
            event_description=f"{current_user.username} joined the organization",
            actor_id=current_user.id
        )
        db.session.add(history)
        
        db.session.commit()
        flash('Successfully joined the organization!', 'success')
    
    return redirect(url_for('organizations.view', slug=slug))

@organizations_bp.route('/organizations/<slug>/leave', methods=['POST'])
@login_required
def leave(slug):
    """Leave an organization"""
    organization = Organization.query.filter_by(slug=slug).first_or_404()
    
    membership = OrganizationMember.query.filter_by(
        organization_id=organization.id,
        user_id=current_user.id,
        status='active'
    ).first()
    
    if not membership:
        flash('You are not a member of this organization', 'error')
        return redirect(url_for('organizations.view', slug=slug))
    
    if membership.role == 'owner':
        flash('Organization owners cannot leave. Transfer ownership first.', 'error')
        return redirect(url_for('organizations.settings', slug=slug))
    
    # Leave organization
    membership.status = 'left'
    membership.left_at = datetime.utcnow()
    membership.left_reason = request.form.get('reason', 'No reason provided')
    
    # Record in history
    history = OrganizationHistory(
        organization_id=organization.id,
        event_type='member_left',
        event_description=f"{current_user.username} left the organization",
        event_data={'reason': membership.left_reason},
        actor_id=current_user.id
    )
    db.session.add(history)
    
    db.session.commit()
    flash('You have left the organization', 'success')
    return redirect(url_for('organizations.index'))

@organizations_bp.route('/organizations/<slug>/upload-logo', methods=['POST'])
@login_required
def upload_logo(slug):
    """Upload organization logo"""
    from flask import jsonify
    import os
    import uuid
    from werkzeug.utils import secure_filename
    
    organization = Organization.query.filter_by(slug=slug).first_or_404()
    
    # Check if user has permission to upload logo (owner only)
    membership = OrganizationMember.query.filter_by(
        organization_id=organization.id,
        user_id=current_user.id,
        status='active'
    ).first()
    
    if not membership or membership.role != 'owner':
        return jsonify({'success': False, 'message': 'Only organization owners can upload logos'})
    
    if 'logo' not in request.files:
        return jsonify({'success': False, 'message': 'No file selected'})
    
    file = request.files['logo']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No file selected'})
    
    # Validate file
    if file and file.filename:
        # Check file extension
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
        if '.' not in file.filename or file.filename.rsplit('.', 1)[1].lower() not in allowed_extensions:
            return jsonify({'success': False, 'message': 'Invalid file type. Please upload a PNG, JPG, or GIF image.'})
        
        # Check file size (5MB max)
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        if file_size > 5 * 1024 * 1024:
            return jsonify({'success': False, 'message': 'File too large. Maximum size is 5MB.'})
        
        # Generate unique filename
        filename = secure_filename(file.filename)
        file_extension = filename.rsplit('.', 1)[1].lower()
        unique_filename = f"{organization.slug}_{uuid.uuid4().hex[:8]}.{file_extension}"
        
        # Create uploads directory if it doesn't exist
        upload_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'logos')
        os.makedirs(upload_dir, exist_ok=True)
        
        # Save file
        file_path = os.path.join(upload_dir, unique_filename)
        file.save(file_path)
        
        # Update organization logo path
        logo_url = f"/static/uploads/logos/{unique_filename}"
        organization.logo = logo_url
        organization.updated_at = datetime.utcnow()  # Update timestamp for cache-busting
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Logo uploaded successfully', 'logo_url': logo_url})
    
    return jsonify({'success': False, 'message': 'Invalid file'})

@organizations_bp.route('/organizations/<slug>/remove-logo', methods=['POST'])
@login_required
def remove_logo(slug):
    """Remove organization logo"""
    from flask import jsonify
    import os
    
    organization = Organization.query.filter_by(slug=slug).first_or_404()
    
    # Check if user has permission to remove logo (owner only)
    membership = OrganizationMember.query.filter_by(
        organization_id=organization.id,
        user_id=current_user.id,
        status='active'
    ).first()
    
    if not membership or membership.role != 'owner':
        return jsonify({'success': False, 'message': 'Only organization owners can remove logos'})
    
    if organization.logo:
        # Remove file from filesystem
        logo_path = os.path.join(current_app.root_path, organization.logo.lstrip('/'))
        if os.path.exists(logo_path):
            try:
                os.remove(logo_path)
            except OSError:
                pass  # Continue even if file removal fails
        
        # Clear logo from database
        organization.logo = None
        organization.updated_at = datetime.utcnow()  # Update timestamp for cache-busting
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Logo removed successfully'})
    
    return jsonify({'success': False, 'message': 'No logo to remove'})


@organizations_bp.route('/organizations/<slug>/close', methods=['POST'])
@login_required
@require_permission('organizations', 'delete')
def close_organization(slug):
    """Close organization"""
    from flask import jsonify
    
    organization = Organization.query.filter_by(slug=slug).first_or_404()
    
    # Check if user has permission to close organization (owner only)
    membership = OrganizationMember.query.filter_by(
        organization_id=organization.id,
        user_id=current_user.id,
        status='active'
    ).first()
    
    if not membership or membership.role != 'owner':
        return jsonify({'success': False, 'message': 'Only organization owners can close the organization'})
    
    try:
        print(f"DEBUG: Closing organization {organization.name} (ID: {organization.id})")
        print(f"DEBUG: Current status: {organization.status}")
        print(f"DEBUG: User: {current_user.username} (ID: {current_user.id})")
        
        # Update organization status
        organization.status = 'closed'
        organization.closed_at = datetime.utcnow()
        organization.closed_reason = request.json.get('reason', '') if request.json else ''
        
        print(f"DEBUG: New status: {organization.status}")
        print(f"DEBUG: Closed at: {organization.closed_at}")
        print(f"DEBUG: Closed reason: {organization.closed_reason}")
        
        # Create history entry
        history_entry = OrganizationHistory(
            organization_id=organization.id,
            event_type='organization_closed',
            event_description=f'Organization closed by {current_user.username}',
            event_data={'reason': organization.closed_reason},
            actor_id=current_user.id,
            actor_type='user'
        )
        db.session.add(history_entry)
        
        print("DEBUG: About to commit changes")
        db.session.commit()
        print("DEBUG: Changes committed successfully")
        
        return jsonify({'success': True, 'message': 'Organization closed successfully'})
        
    except Exception as e:
        print(f"DEBUG: Error occurred: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error closing organization: {str(e)}'})

@organizations_bp.route('/organizations/<slug>/reopen', methods=['POST'])
@login_required
@require_permission('organizations', 'edit')
def reopen_organization(slug):
    """Reopen organization"""
    from flask import jsonify
    
    organization = Organization.query.filter_by(slug=slug).first_or_404()
    
    # Check if user has permission to reopen organization (owner only)
    membership = OrganizationMember.query.filter_by(
        organization_id=organization.id,
        user_id=current_user.id,
        status='active'
    ).first()
    
    if not membership or membership.role != 'owner':
        return jsonify({'success': False, 'message': 'Only organization owners can reopen the organization'})
    
    # Check if organization is actually closed
    if organization.status != 'closed':
        return jsonify({'success': False, 'message': 'Organization is not closed'})
    
    try:
        print(f"DEBUG: Reopening organization {organization.name} (ID: {organization.id})")
        print(f"DEBUG: Current status: {organization.status}")
        print(f"DEBUG: User: {current_user.username} (ID: {current_user.id})")
        
        # Update organization status
        organization.status = 'active'
        organization.closed_at = None
        organization.closed_reason = None
        
        print(f"DEBUG: New status: {organization.status}")
        print(f"DEBUG: Closed at: {organization.closed_at}")
        print(f"DEBUG: Closed reason: {organization.closed_reason}")
        
        # Create history entry
        history_entry = OrganizationHistory(
            organization_id=organization.id,
            event_type='organization_reopened',
            event_description=f'Organization reopened by {current_user.username}',
            event_data={'previous_status': 'closed'},
            actor_id=current_user.id,
            actor_type='user'
        )
        db.session.add(history_entry)
        
        print("DEBUG: About to commit changes")
        db.session.commit()
        print("DEBUG: Changes committed successfully")
        
        return jsonify({'success': True, 'message': 'Organization reopened successfully'})
        
    except Exception as e:
        print(f"DEBUG: Error occurred: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error reopening organization: {str(e)}'})

@organizations_bp.route('/<slug>/remove-item/<int:item_id>')
@login_required
@require_permission('organizations', 'edit')
def remove_item(slug, item_id):
    """Remove an item from organization"""
    organization = Organization.query.filter_by(slug=slug).first_or_404()
    
    # Check if user is a member with appropriate permissions
    membership = OrganizationMember.query.filter_by(
        organization_id=organization.id,
        user_id=current_user.id,
        status='active'
    ).first()
    
    if not membership or membership.role not in ['owner', 'admin', 'member']:
        flash('You do not have permission to remove items from this organization.', 'error')
        return redirect(url_for('organizations.view', slug=slug))
    
    # Find the organization content entry
    content = OrganizationContent.query.filter_by(
        organization_id=organization.id,
        item_id=item_id,
        content_type='item'
    ).first()
    
    if not content:
        flash('Item not found in this organization.', 'error')
        return redirect(url_for('organizations.view', slug=slug))
    
    try:
        # Remove the content entry
        db.session.delete(content)
        
        # Create history entry
        history_entry = OrganizationHistory(
            organization_id=organization.id,
            event_type='item_removed',
            event_description=f'Item removed by {current_user.username}',
            event_data={'item_id': item_id},
            actor_id=current_user.id,
            actor_type='user'
        )
        db.session.add(history_entry)
        
        db.session.commit()
        flash('Item removed from organization successfully.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error removing item: {str(e)}', 'error')
    
    return redirect(url_for('organizations.view', slug=slug))

@organizations_bp.route('/<slug>/remove-need/<int:need_id>')
@login_required
@require_permission('organizations', 'edit')
def remove_need(slug, need_id):
    """Remove a need from organization"""
    organization = Organization.query.filter_by(slug=slug).first_or_404()
    
    # Check if user is a member with appropriate permissions
    membership = OrganizationMember.query.filter_by(
        organization_id=organization.id,
        user_id=current_user.id,
        status='active'
    ).first()
    
    if not membership or membership.role not in ['owner', 'admin', 'member']:
        flash('You do not have permission to remove needs from this organization.', 'error')
        return redirect(url_for('organizations.view', slug=slug))
    
    # Find the organization content entry
    content = OrganizationContent.query.filter_by(
        organization_id=organization.id,
        need_id=need_id,
        content_type='need'
    ).first()
    
    if not content:
        flash('Need not found in this organization.', 'error')
        return redirect(url_for('organizations.view', slug=slug))
    
    try:
        # Remove the content entry
        db.session.delete(content)
        
        # Create history entry
        history_entry = OrganizationHistory(
            organization_id=organization.id,
            event_type='need_removed',
            event_description=f'Need removed by {current_user.username}',
            event_data={'need_id': need_id},
            actor_id=current_user.id,
            actor_type='user'
        )
        db.session.add(history_entry)
        
        db.session.commit()
        flash('Need removed from organization successfully.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error removing need: {str(e)}', 'error')
    
    return redirect(url_for('organizations.view', slug=slug))
