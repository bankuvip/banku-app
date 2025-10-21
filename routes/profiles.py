from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
from models import Profile, Item, Project, ProjectContributor, User, db, Need, Activity, ProductCategory, ItemType, ChatbotFlow, Organization, OrganizationMember, SavedItem
from utils.permissions import require_permission
from utils.file_utils import validate_uploaded_file_comprehensive, sanitize_filename
from forms import ProfileForm
from datetime import datetime, timedelta
import os
import logging
from werkzeug.utils import secure_filename

profiles_bp = Blueprint('profiles', __name__)

@profiles_bp.route('/')
@login_required
@require_permission('profiles', 'view_own')
def index():
    profiles = Profile.query.filter_by(user_id=current_user.id).all()
    return render_template('profiles/index.html', profiles=profiles)

# NEW DYNAMIC ITEM CREATION SYSTEM
@profiles_bp.route('/create-item')
@login_required
@require_permission('items', 'create')
def create_item_redirect():
    """Redirect to dynamic item creation based on ItemTypes"""
    # Get all active item types
    item_types = ItemType.query.filter_by(is_active=True, is_visible=True).order_by(ItemType.order_index, ItemType.name).all()
    
    # Check if user has a profile
    profile = Profile.query.filter_by(user_id=current_user.id).first()
    if not profile:
        flash('Please create a profile first', 'error')
        return redirect(url_for('profiles.create'))
    
    return render_template('profiles/create_item_dynamic.html', profile=profile, item_types=item_types)

@profiles_bp.route('/create-<item_type_name>')
@login_required  
def create_item_by_type(item_type_name):
    """Dynamic item creation route - redirects to assigned chatbot"""
    # Find the item type
    item_type = ItemType.query.filter_by(name=item_type_name, is_active=True, is_visible=True).first()
    
    if not item_type:
        flash(f'Item type "{item_type_name}" not found', 'error')
        return redirect(url_for('profiles.create_item_redirect'))
    
    # Check if there's a data storage mapping for this item type
    from models import DataStorageMapping
    mapping = DataStorageMapping.query.filter_by(
        item_type_id=item_type.id,
        is_active=True
    ).first()
    
    if not mapping:
        flash(f'No chatbot configured for "{item_type.display_name}" item type. Please contact admin to set up Data Storage Mapping.', 'error')
        return redirect(url_for('profiles.create_item_redirect'))
    
    # Check if chatbot exists and is active
    chatbot = ChatbotFlow.query.filter_by(id=mapping.chatbot_id, is_active=True).first()
    if not chatbot:
        flash(f'Assigned chatbot for "{item_type.display_name}" is not available', 'error')
        return redirect(url_for('profiles.create_item_redirect'))
    
    # Redirect to chatbot flow
    return redirect(url_for('chatbot.start_flow', flow_id=chatbot.id))

# LEGACY ROUTE REDIRECTS REMOVED
# All item creation now uses the dynamic system above

@profiles_bp.route('/create', methods=['GET', 'POST'])
@login_required
@require_permission('profiles', 'create')
def create():
    form = ProfileForm()
    
    # Get profile types for template
    from models import ProfileType
    profile_types = ProfileType.query.filter_by(is_active=True).order_by(ProfileType.order_index, ProfileType.display_name).all()
    profile_types_dict = {str(pt.id): pt for pt in profile_types}
    
    if form.validate_on_submit():
        # Handle file upload for photo with comprehensive validation
        photo_filename = None
        if form.photo.data and hasattr(form.photo.data, 'filename') and form.photo.data.filename:
            try:
                file = form.photo.data
                
                # Comprehensive file validation
                is_valid, error_message, file_info = validate_uploaded_file_comprehensive(
                    file=file,
                    allowed_extensions=['jpg', 'jpeg', 'png', 'gif', 'webp'],
                    max_size=10 * 1024 * 1024,  # 10MB
                    allowed_categories=['images']
                )
                
                if not is_valid:
                    flash(f'Photo upload error: {error_message}', 'error')
                    return render_template('profiles/create.html', form=form, profile_types=profile_types_dict)
                
                # Sanitize and create unique filename with timestamp + UUID
                original_filename = sanitize_filename(file.filename)
                file_ext = os.path.splitext(original_filename)[1]
                file_base = os.path.splitext(original_filename)[0]
                
                # Create unique identifier to prevent collisions
                from datetime import datetime
                import uuid
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
                unique_id = str(uuid.uuid4())[:8]
                
                # Generate collision-free filename
                photo_filename = f"{current_user.id}_photo_{file_base}_{timestamp}_{unique_id}{file_ext}"
                file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], photo_filename)
                
                # Ensure upload directory exists
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                
                # Save file
                file.save(file_path)
                
                # Log successful upload
                logging.info(f"Photo uploaded successfully: {photo_filename} by user {current_user.id}")
                
            except Exception as e:
                logging.error(f"Photo upload failed: {str(e)}")
                flash('Photo upload failed. Please try again.', 'error')
                return render_template('profiles/create.html', form=form, profile_types=profile_types_dict)
        
        # Handle ProfileType - could be ID (new system) or string (legacy)
        profile_type_value = form.profile_type.data
        profile_type_id = None
        profile_type_string = None
        
        try:
            # Try to convert to int (new ProfileType ID system)
            profile_type_id = int(profile_type_value)
            # Get the ProfileType to also set the string for backward compatibility
            from models import ProfileType
            profile_type_obj = ProfileType.query.get(profile_type_id)
            if profile_type_obj:
                profile_type_string = profile_type_obj.name
        except (ValueError, TypeError):
            # Legacy string system
            profile_type_string = profile_type_value
        
        # Generate slug for the profile
        from utils.slug_utils import generate_profile_slug
        slug = generate_profile_slug(form.name.data, current_user.id)
        
        profile = Profile(
            user_id=current_user.id,
            name=form.name.data,
            slug=slug,  # Add slug field
            profile_type=profile_type_string,  # Keep for backward compatibility
            profile_type_id=profile_type_id,   # New foreign key system
            description=form.description.data,
            phone=form.phone.data if form.phone.data else None,
            website=form.website.data,
            location=form.location.data,
            photo=photo_filename,
            is_public=form.is_public.data
        )
        
        db.session.add(profile)
        db.session.commit()
        
        flash('Profile created successfully', 'success')
        # Redirect to slug-based URL if available, otherwise use ID
        if profile.slug:
            return redirect(url_for('profiles.detail_by_slug', slug=profile.slug))
        else:
            return redirect(url_for('profiles.detail_by_id', profile_id=profile.id))
    
    return render_template('profiles/create.html', form=form, profile_types_dict=profile_types_dict)

@profiles_bp.route('/<slug>')
@login_required
@require_permission('profiles', 'view_own')
def detail_by_slug(slug):
    """View profile by slug (new preferred method)"""
    from utils.permissions import has_permission
    
    # Check if user has permission to view private profiles
    can_view_private = has_permission(current_user, 'profiles', 'view_private')
    
    if can_view_private:
        # Users with private access can view any profile
        profile = Profile.query.filter_by(slug=slug).first_or_404()
    else:
        # Regular users: Allow viewing own profiles OR public profiles of other users
        profile = Profile.query.filter(
            db.and_(
                Profile.slug == slug,
                db.or_(
                    Profile.user_id == current_user.id,
                    Profile.is_public == True
                )
            )
        ).first_or_404()
    
    # Check About tab permissions
    can_view_about = False
    is_owner = profile.user_id == current_user.id
    
    if is_owner:
        can_view_about = has_permission(current_user, 'profiles', 'view_about_own')
    else:
        can_view_about = has_permission(current_user, 'profiles', 'view_about_others')
    
    # Check Activity tab permissions
    can_view_activity = False
    if is_owner:
        can_view_activity = has_permission(current_user, 'profiles', 'view_activity_own')
    else:
        can_view_activity = has_permission(current_user, 'profiles', 'view_activity_others')
    
    # Get profile's items with pagination
    page = request.args.get('page', 1, type=int)
    per_page = 12
    items = Item.query.filter_by(profile_id=profile.id, is_available=True).order_by(Item.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # Get all profile's items for needs/saved items tabs (not paginated)
    all_items = Item.query.filter_by(profile_id=profile.id, is_available=True).order_by(Item.created_at.desc()).all()
    
    # Separate items and needs based on category or content_type
    items_list = [item for item in all_items if item.category != 'need' and getattr(item, 'content_type', None) != 'need']
    needs = [item for item in all_items if item.category == 'need' or getattr(item, 'content_type', None) == 'need']
    
    # Get profile's projects
    projects = Project.query.filter_by(profile_id=profile.id).order_by(Project.created_at.desc()).all()
    
    # Get user's saved items
    saved_items = Item.query.options(
        db.joinedload(Item.item_type),
        db.joinedload(Item.profile)
    ).join(SavedItem).filter(
        SavedItem.user_id == current_user.id
    ).order_by(SavedItem.saved_at.desc()).all()
    
    return render_template('profiles/detail_new.html', 
                         profile=profile, 
                         items=items,
                         items_list=items_list,  # For template length checks
                         needs=needs,
                         projects=projects,
                         saved_items=saved_items,
                         can_view_about=can_view_about,
                         can_view_activity=can_view_activity,
                         is_owner=is_owner)

@profiles_bp.route('/id/<int:profile_id>')
@login_required
@require_permission('profiles', 'view_own')
def detail_by_id(profile_id):
    """View profile by ID (backward compatibility)"""
    from utils.permissions import has_permission
    
    # Check if user has permission to view private profiles
    can_view_private = has_permission(current_user, 'profiles', 'view_private')
    
    if can_view_private:
        # Users with private access can view any profile
        profile = Profile.query.filter_by(id=profile_id).first_or_404()
    else:
        # Regular users: Allow viewing own profiles OR public profiles of other users
        profile = Profile.query.filter(
            db.and_(
                Profile.id == profile_id,
                db.or_(
                    Profile.user_id == current_user.id,
                    Profile.is_public == True
                )
            )
        ).first_or_404()
    
    # If profile has a slug, redirect to slug-based URL
    if profile.slug:
        return redirect(url_for('profiles.detail_by_slug', slug=profile.slug))
    
    # Check About tab permissions
    can_view_about = False
    is_owner = profile.user_id == current_user.id
    
    if is_owner:
        can_view_about = has_permission(current_user, 'profiles', 'view_about_own')
    else:
        can_view_about = has_permission(current_user, 'profiles', 'view_about_others')
    
    # Check Activity tab permissions
    can_view_activity = False
    if is_owner:
        can_view_activity = has_permission(current_user, 'profiles', 'view_activity_own')
    else:
        can_view_activity = has_permission(current_user, 'profiles', 'view_activity_others')
    
    # Get profile's items with pagination
    page = request.args.get('page', 1, type=int)
    per_page = 12
    items = Item.query.filter_by(profile_id=profile.id, is_available=True).order_by(Item.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # Get all profile's items for needs/saved items tabs (not paginated)
    all_items = Item.query.filter_by(profile_id=profile.id, is_available=True).order_by(Item.created_at.desc()).all()
    
    # Separate items and needs based on category or content_type
    items_list = [item for item in all_items if item.category != 'need' and getattr(item, 'content_type', None) != 'need']
    needs = [item for item in all_items if item.category == 'need' or getattr(item, 'content_type', None) == 'need']
    
    # Get profile's projects
    projects = Project.query.filter_by(profile_id=profile.id).order_by(Project.created_at.desc()).all()
    
    # Get user's saved items
    saved_items = Item.query.options(
        db.joinedload(Item.item_type),
        db.joinedload(Item.profile)
    ).join(SavedItem).filter(
        SavedItem.user_id == current_user.id
    ).order_by(SavedItem.saved_at.desc()).all()
    
    return render_template('profiles/detail_new.html', 
                         profile=profile, 
                         items=items,
                         items_list=items_list,  # For template length checks
                         needs=needs,
                         projects=projects,
                         saved_items=saved_items,
                         can_view_about=can_view_about,
                         can_view_activity=can_view_activity,
                         is_owner=is_owner)

# Keep the old route for backward compatibility (will redirect to slug-based URL)
@profiles_bp.route('/<int:profile_id>')
@login_required
@require_permission('profiles', 'view_own')
def detail(profile_id):
    """Legacy route - redirects to slug-based URL for better SEO and UX"""
    # Find the profile by ID
    profile = Profile.query.filter_by(id=profile_id).first_or_404()
    
    # If profile has a slug, redirect to slug-based URL
    if profile.slug:
        return redirect(url_for('profiles.detail_by_slug', slug=profile.slug))
    else:
        # If no slug yet, use the new ID-based route
        return redirect(url_for('profiles.detail_by_id', profile_id=profile_id))

@profiles_bp.route('/<int:profile_id>/edit', methods=['GET', 'POST'])
@login_required
@require_permission('profiles', 'edit_own')
def edit(profile_id):
    profile = Profile.query.filter_by(id=profile_id, user_id=current_user.id).first_or_404()
    form = ProfileForm()
    
    if request.method == 'GET':
        # Pre-populate form with existing data
        form.name.data = profile.name
        form.description.data = profile.description
        form.phone.data = profile.phone
        form.website.data = profile.website
        form.location.data = profile.location
        form.is_public.data = profile.is_public
    
    if form.validate_on_submit():
        # Handle file upload for photo
        if form.photo.data and hasattr(form.photo.data, 'filename') and form.photo.data.filename:
            file = form.photo.data
            filename = secure_filename(file.filename)
            photo_filename = f"{current_user.id}_photo_{filename}"
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], photo_filename)
            file.save(file_path)
            profile.photo = photo_filename
        
        # Update profile fields
        old_name = profile.name
        profile.name = form.name.data
        profile.description = form.description.data
        profile.phone = form.phone.data if form.phone.data else None
        profile.website = form.website.data
        profile.location = form.location.data
        profile.is_public = form.is_public.data
        
        # Regenerate slug if name changed
        if old_name != profile.name:
            from utils.slug_utils import generate_profile_slug
            profile.slug = generate_profile_slug(profile.name, profile.user_id, profile.id)
        
        db.session.commit()
        flash('Profile updated successfully', 'success')
        # Redirect to slug-based URL if available, otherwise use ID
        if profile.slug:
            return redirect(url_for('profiles.detail_by_slug', slug=profile.slug))
        else:
            return redirect(url_for('profiles.detail_by_id', profile_id=profile.id))
    
    return render_template('profiles/edit.html', profile=profile, form=form)

@profiles_bp.route('/<int:profile_id>/delete', methods=['POST'])
@login_required
@require_permission('profiles', 'delete')
def delete_profile(profile_id):
    profile = Profile.query.filter_by(id=profile_id, user_id=current_user.id).first_or_404()
    
    # Prevent deletion of default profile
    if profile.is_default:
        flash('Cannot delete your default profile. This profile is required for account management.', 'error')
        return redirect(url_for('profiles.index'))
    
    # Delete all items associated with this profile (with file cleanup)
    from utils.file_cleanup import delete_item_files, delete_profile_files
    
    items = Item.query.filter_by(profile_id=profile_id).all()
    for item in items:
        # Delete files associated with each item
        file_cleanup_result = delete_item_files(item)
        if file_cleanup_result['success']:
            print(f"Deleted {file_cleanup_result['total_deleted']} files for item {item.id}")
    
    # Delete the items
    Item.query.filter_by(profile_id=profile_id).delete()
    
    # Delete profile files (like profile photo)
    profile_cleanup_result = delete_profile_files(profile)
    if profile_cleanup_result['success']:
        print(f"Deleted {profile_cleanup_result['total_deleted']} profile files")
    
    # Delete the profile
    db.session.delete(profile)
    db.session.commit()
    
    flash('Profile deleted successfully', 'success')
    return redirect(url_for('profiles.index'))

@profiles_bp.route('/item/<int:item_id>/edit', methods=['GET', 'POST'])
@login_required
@require_permission('items', 'edit')
def edit_item(item_id):
    item = Item.query.get_or_404(item_id)
    
    # Check if user owns this item
    if item.profile.user_id != current_user.id:
        flash('You do not have permission to edit this item', 'error')
        return redirect(request.referrer or url_for('profiles.index'))
    
    if request.method == 'POST':
        item.title = request.form.get('title')
        item.description = request.form.get('description')
        item.category = request.form.get('category')
        item.location = request.form.get('location')
        price = request.form.get('price')
        if price == '' or price is None:
            item.price = None
        else:
            try:
                item.price = float(price)
            except (ValueError, TypeError):
                item.price = None
        item.currency = request.form.get('currency', 'USD')
        
        db.session.commit()
        flash('Item updated successfully', 'success')
        return redirect(url_for('auth.profile'))
    
    return render_template('profiles/edit_item.html', item=item)

@profiles_bp.route('/item/<int:item_id>/delete', methods=['POST'])
@login_required
@require_permission('items', 'delete')
def delete_item(item_id):
    item = Item.query.get_or_404(item_id)
    
    # Check if user owns this item
    if item.profile.user_id != current_user.id:
        if request.is_json:
            return jsonify({'success': False, 'message': 'Permission denied'})
        flash('You do not have permission to delete this item', 'error')
        return redirect(request.referrer or url_for('profiles.index'))
    
    # Delete all related records first (cascading deletion)
    from models import (ItemCredibilityScore, ItemReviewScore, ItemVisibilityScore, 
                       ItemInteraction, ItemField, SavedItem, Activity, DealItem, Review)
    from utils.file_cleanup import delete_item_files
    
    try:
        # Delete associated files first
        file_cleanup_result = delete_item_files(item)
        if file_cleanup_result['success']:
            print(f"Deleted {file_cleanup_result['total_deleted']} files for item {item_id}")
        else:
            print(f"File cleanup had issues: {file_cleanup_result.get('error', 'Unknown error')}")
        
        # Delete all related records in proper order
        # Delete item interactions first
        ItemInteraction.query.filter_by(item_id=item_id).delete()
        
        # Delete item fields
        ItemField.query.filter_by(item_id=item_id).delete()
        
        # Delete saved items
        SavedItem.query.filter_by(item_id=item_id).delete()
        
        # Delete activities
        Activity.query.filter_by(item_id=item_id).delete()
        
        # Delete deal items
        DealItem.query.filter_by(item_id=item_id).delete()
        
        # Delete reviews
        Review.query.filter_by(item_id=item_id).delete()
        
        # Delete credibility scores
        ItemCredibilityScore.query.filter_by(item_id=item_id).delete()
        
        # Delete review scores
        ItemReviewScore.query.filter_by(item_id=item_id).delete()
        
        # Delete visibility scores
        ItemVisibilityScore.query.filter_by(item_id=item_id).delete()
        
        # Finally delete the item itself
        db.session.delete(item)
        db.session.commit()
        
        if request.is_json:
            return jsonify({'success': True, 'message': 'Item deleted successfully'})
        
        flash('Item deleted successfully', 'success')
        return redirect(request.referrer or url_for('profiles.index'))
        
    except Exception as e:
        db.session.rollback()
        if request.is_json:
            return jsonify({'success': False, 'message': f'Error deleting item: {str(e)}'})
        
        flash(f'Error deleting item: {str(e)}', 'error')
        return redirect(request.referrer or url_for('profiles.index'))

@profiles_bp.route('/items/<int:item_id>')
@login_required
def item_detail(item_id):
    """View item details with activity history"""
    item = Item.query.options(db.joinedload(Item.item_type)).get_or_404(item_id)
    profile = Profile.query.get_or_404(item.profile_id)
    
    # INCREMENT VIEW COUNT (but not for item owner)
    if profile.user_id != current_user.id:
        # Not the owner viewing their own item - increment view count
        item.views += 1
        db.session.commit()
        print(f"DEBUG: View count incremented to {item.views} in profiles")
        
        # Also track in ItemInteraction for analytics
        from models import ItemInteraction
        import uuid
        interaction = ItemInteraction(
            item_id=item.id,
            user_id=current_user.id,
            interaction_type='view',
            source='profile',
            referrer=request.referrer or 'direct',
            session_id=request.cookies.get('session', str(uuid.uuid4())),
            ip_address=request.remote_addr
        )
        db.session.add(interaction)
        db.session.commit()
        print(f"DEBUG: View interaction tracked in profiles with session: {interaction.session_id}")
    else:
        print(f"DEBUG: Owner viewing own item in profiles - view count not incremented")
    
    # Get activities for this item
    activities = Activity.query.filter_by(item_id=item_id).order_by(Activity.created_at.desc()).all()
    
    return render_template('profiles/item_detail.html', 
                         item=item, 
                         profile=profile, 
                         activities=activities)

@profiles_bp.route('/check-welcome-popup')
@login_required
def check_welcome_popup():
    """Check if user should see welcome popup (once per day)"""
    try:
        now = datetime.utcnow()
        should_show = True
        
        if current_user.last_welcome_popup:
            # Check if it's been at least 24 hours since last popup
            time_diff = now - current_user.last_welcome_popup
            should_show = time_diff >= timedelta(days=1)
        
        return jsonify({'show_popup': should_show})
    except Exception as e:
        return jsonify({'show_popup': False, 'error': str(e)})

@profiles_bp.route('/update-welcome-popup', methods=['POST'])
@login_required
def update_welcome_popup():
    """Update the user's last welcome popup time"""
    try:
        current_user.last_welcome_popup = datetime.utcnow()
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@profiles_bp.route('/users/<username>')
def user_profile(username):
    """User profile page"""
    user = User.query.filter_by(username=username).first_or_404()
    
    # Get user's items
    user_items = Item.query.filter_by(creator_id=user.id, creator_type='user').all()
    
    # Get user's organizations
    user_organizations = Organization.query.join(OrganizationMember).filter(
        OrganizationMember.user_id == user.id,
        OrganizationMember.status == 'active'
    ).all()
    
    return render_template('profiles/user_profile.html', 
                         user=user, 
                         items=user_items, 
                         organizations=user_organizations)

@profiles_bp.route('/save-item/<int:item_id>', methods=['POST'])
@login_required
def save_item(item_id):
    """Save an item to user's saved items"""
    try:
        # Check if item exists
        item = Item.query.get_or_404(item_id)
        
        # Check if already saved
        existing_save = SavedItem.query.filter_by(
            user_id=current_user.id, 
            item_id=item_id
        ).first()
        
        if existing_save:
            return jsonify({
                'success': False, 
                'message': 'Item already saved'
            })
        
        # Create new saved item
        saved_item = SavedItem(
            user_id=current_user.id,
            item_id=item_id
        )
        
        db.session.add(saved_item)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Item saved successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error saving item: {str(e)}'
        }), 500

@profiles_bp.route('/unsave-item/<int:item_id>', methods=['POST'])
@login_required
def unsave_item(item_id):
    """Remove an item from user's saved items"""
    try:
        # Find the saved item
        saved_item = SavedItem.query.filter_by(
            user_id=current_user.id,
            item_id=item_id
        ).first()
        
        if not saved_item:
            return jsonify({
                'success': False,
                'message': 'Item not found in saved items'
            })
        
        # Delete the saved item
        db.session.delete(saved_item)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Item removed from saved items'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error removing item: {str(e)}'
        }), 500
