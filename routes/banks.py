from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from models import Item, Bank, Tag, Profile, ProductCategory, SearchAnalytics, ItemVisibilityScore, ItemCredibilityScore, ItemReviewScore, ItemType, OrganizationType, Organization, User, db
from utils.permissions import require_permission
from sqlalchemy import or_, and_
from datetime import datetime

banks_bp = Blueprint('banks', __name__)

@banks_bp.route('/')
@login_required
@require_permission('banks', 'view')
def index():
    banks = Bank.query.filter_by(is_active=True, is_public=True).order_by(Bank.sort_order.asc(), Bank.name.asc()).all()
    
    # Icon and color mapping for each bank type
    bank_icons = {
        'products': 'fas fa-box',
        'services': 'fas fa-cogs',
        'ideas': 'fas fa-lightbulb',
        'projects': 'fas fa-project-diagram',
        'funders': 'fas fa-dollar-sign',
        'events': 'fas fa-calendar-alt',
        'auctions': 'fas fa-gavel',
        'experiences': 'fas fa-star',
        'opportunities': 'fas fa-briefcase',
        'information': 'fas fa-database',
        'observations': 'fas fa-eye',
        'hidden_gems': 'fas fa-gem',
        'needs': 'fas fa-heart',
        'people': 'fas fa-users'
    }
    
    bank_colors = {
        'products': '#007bff',
        'services': '#28a745',
        'ideas': '#ffc107',
        'projects': '#17a2b8',
        'funders': '#28a745',
        'events': '#dc3545',
        'auctions': '#ffc107',
        'experiences': '#6f42c1',
        'opportunities': '#17a2b8',
        'information': '#007bff',
        'observations': '#6c757d',
        'hidden_gems': '#ffc107',
        'needs': '#dc3545',
        'people': '#28a745'
    }
    
    # Add item counts, icons, and colors for each bank
    for bank in banks:
        # Map bank types to item categories
        category_map = {
            'items': 'all_items',  # Special case: count all items
            'products': 'product',
            'services': 'service', 
            'ideas': 'idea',
            'projects': 'project',
            'funders': 'fund',
            'events': 'event',
            'auctions': 'auction',
            'experiences': 'experience',
            'opportunities': 'opportunity',
            'information': 'information',
            'observations': 'observation',
            'hidden_gems': 'hidden_gem',
            'needs': 'need',
            'people': 'people'
        }
        
        # Use smart filtering for item count
        if bank.bank_type == 'items':
            if bank.item_type_id:
                # Bank is configured for a specific item type
                item_type = ItemType.query.get(bank.item_type_id)
                if item_type:
                    # CORRECT: Use item_type_id for core classification, not category
                    bank.item_count = Item.query.filter_by(item_type_id=bank.item_type_id, is_available=True).count()
                else:
                    bank.item_count = Item.query.filter_by(is_available=True).count()
            else:
                # Show all items if no specific type configured
                bank.item_count = Item.query.filter_by(is_available=True).count()
        elif bank.bank_type == 'organizations':
            # Count organizations based on filter
            base_query = Organization.query.filter_by(status='active')
            
            # Apply privacy filter
            if bank.privacy_filter == 'public':
                base_query = base_query.filter_by(is_public=True)
            elif bank.privacy_filter == 'private':
                base_query = base_query.filter_by(is_public=False)
            # If privacy_filter is 'all', no additional filter
            
            # Apply organization type filter
            if bank.organization_type_id:
                base_query = base_query.filter_by(organization_type_id=bank.organization_type_id)
            
            bank.item_count = base_query.count()
        elif bank.bank_type == 'users':
            # Count users based on filter
            if bank.user_filter:
                base_query = User.query.join(Profile, User.id == Profile.user_id).filter(
                    User.is_active == True,
                    Profile.profile_type == bank.user_filter
                )
            else:
                base_query = User.query.join(Profile, User.id == Profile.user_id).filter(
                    User.is_active == True
                )
            
            # Apply privacy filter
            if bank.privacy_filter == 'public':
                base_query = base_query.filter(Profile.is_public == True)
            elif bank.privacy_filter == 'private':
                base_query = base_query.filter(Profile.is_public == False)
            # If privacy_filter is 'all', no additional filter
            
            bank.item_count = base_query.count()
        else:
            # Fallback to old system for backward compatibility
            category = category_map.get(bank.bank_type, bank.bank_type)
            if category == 'all_items':
                bank.item_count = Item.query.filter_by(is_available=True).count()
            else:
                bank.item_count = Item.query.filter_by(category=category, is_available=True).count()
        
        # Use database icon and color, fallback to defaults if not set
        if not bank.icon:
            bank.icon = bank_icons.get(bank.bank_type, 'fas fa-database')
        if not bank.color:
            bank.color = bank_colors.get(bank.bank_type, '#007bff')
    
    return render_template('banks/index.html', banks=banks)

@banks_bp.route('/product-categories')
@login_required
@require_permission('banks', 'view')
def product_categories():
    # Get main product categories (level 1)
    main_categories = ProductCategory.query.filter_by(level=1, is_active=True).all()
    
    # Convert to the format expected by the template
    categories = []
    for cat in main_categories:
        categories.append({
            'id': cat.id,
            'name': cat.name,
            'description': cat.description,
            'icon': get_category_icon(cat.name),
            'color': get_category_color(cat.name)
        })
    
    return render_template('banks/product_categories.html', categories=categories)

def get_category_icon(category_name):
    """Get appropriate icon for category"""
    icon_map = {
        'Physical Products': 'fas fa-cube',
        'Digital Products': 'fas fa-laptop-code',
        'Knowledge Products': 'fas fa-graduation-cap',
        'Ideas': 'fas fa-lightbulb',
        'Plans & Strategies': 'fas fa-project-diagram',
        'Imaginations & Innovations': 'fas fa-rocket',
        'Rights & Licenses': 'fas fa-certificate'
    }
    return icon_map.get(category_name, 'fas fa-box')

def get_category_color(category_name):
    """Get appropriate color for category"""
    color_map = {
        'Physical Products': 'primary',
        'Digital Products': 'info',
        'Knowledge Products': 'warning',
        'Ideas': 'danger',
        'Plans & Strategies': 'secondary',
        'Imaginations & Innovations': 'purple',
        'Rights & Licenses': 'success'
    }
    return color_map.get(category_name, 'primary')




@banks_bp.route('/<bank_slug>')
@login_required
@require_permission('banks', 'view')
def bank_items(bank_slug):
    """Database-driven bank items with support for items, users, and organizations"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    search = request.args.get('search', '')
    category = request.args.get('category', '')
    location = request.args.get('location', '')
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)
    sort_by = request.args.get('sort_by', 'created_at')
    sort_order = request.args.get('sort_order', 'desc')
    
    # Find bank by slug, name, or bank_type (OPTIMIZED - single query)
    bank = Bank.query.filter(
        Bank.is_active == True,
        Bank.is_public == True,
        or_(
            Bank.slug == bank_slug,
            Bank.name == bank_slug,
            Bank.bank_type == bank_slug
        )
    ).first()
    
    if not bank:
        from flask import abort
        abort(404, f"Bank '{bank_slug}' not found")
    
    # Handle different bank types
    if bank.bank_type == 'users':
        return handle_user_bank(bank, page, per_page, search, sort_by, sort_order)
    elif bank.bank_type == 'organizations':
        return handle_organization_bank(bank, page, per_page, search, sort_by, sort_order)
    else:
        # Default to items bank
        return handle_item_bank(bank, page, per_page, search, category, location, min_price, max_price, sort_by, sort_order)

def handle_item_bank(bank, page, per_page, search, category, location, min_price, max_price, sort_by, sort_order):
    """Handle item banks"""
    # Build query using simple join (FIXED PERFORMANCE ISSUE)
    query = Item.query.join(Profile).filter(Item.is_available == True)
    
    # Apply smart filtering based on bank configuration (CORRECTED LOGIC)
    if bank.item_type_id:
        # CORRECT: Filter by ItemType ID - the core classification system
        query = query.filter(Item.item_type_id == bank.item_type_id)
    elif bank.subcategory:
        # Fallback to old subcategory field
        query = query.filter(Item.subcategory == bank.subcategory)
    else:
        # Use bank_type as fallback (EXACT SAME MAPPING AS OLD ROUTE)
        bank_type_mapping = {
            'items': 'all_items',  # Special case: show all items regardless of category
            'products': 'product',
            'services': 'service', 
            'needs': 'need',  # Changed from 'idea' to 'need' to match your need items
            'ideas': 'idea',
            'projects': 'project',
            'people': 'people',
            'funders': 'fund',
            'information': 'information',
            'experiences': 'experience',
            'opportunities': 'opportunity',
            'events': 'event',
            'auctions': 'auction',
            'observations': 'observation',
            'hidden_gems': 'hidden_gem',
            # Product subcategories
            'physical': 'product',
            'digital': 'product',
            'knowledge': 'product',
            'rights_licenses': 'product',
            'plans_strategies': 'product',
            'imagination_innovations': 'product'
        }
        
        actual_item_type = bank_type_mapping.get(bank.bank_type, bank.bank_type)
        if actual_item_type != 'all_items':
            # CORRECT: Filter by ItemType ID - the core classification system
            query = query.filter(Item.item_type_id == bank.item_type_id)
    
    # If it's a product subcategory, filter by subcategory (EXACT SAME AS OLD ROUTE)
    if bank.bank_type in ['physical', 'digital', 'knowledge', 'rights_licenses', 'plans_strategies', 'imagination_innovations']:
        query = query.filter(Item.subcategory == bank.bank_type)
    
    # Apply filters (EXACT SAME AS OLD ROUTE)
    if search:
        query = query.filter(
            or_(
                Item.title.contains(search),
                Item.description.contains(search)
            )
        )
    
    if category:
        query = query.filter(Item.category == category)
    
    # For products, add product category filtering (EXACT SAME AS OLD ROUTE)
    product_category_id = request.args.get('product_category_id', type=int)
    if bank.bank_type == 'products' and product_category_id:
        query = query.filter(Item.product_category_id == product_category_id)
    
    if location:
        query = query.filter(Item.location.contains(location))
    
    if min_price is not None:
        query = query.filter(Item.price >= min_price)
    
    if max_price is not None:
        query = query.filter(Item.price <= max_price)
    
    # Apply sorting (EXACT SAME AS OLD ROUTE)
    if sort_by == 'price':
        if sort_order == 'asc':
            query = query.order_by(Item.price.asc())
        else:
            query = query.order_by(Item.price.desc())
    elif sort_by == 'rating':
        if sort_order == 'asc':
            query = query.order_by(Item.rating.asc())
        else:
            query = query.order_by(Item.rating.desc())
    else:  # created_at
        if sort_order == 'asc':
            query = query.order_by(Item.created_at.asc())
        else:
            query = query.order_by(Item.created_at.desc())
    
    # Optimized: Only load essential relationships for bank listing
    query = query.options(
        db.joinedload(Item.profile),  # Essential for creator info
        db.joinedload(Item.item_type)  # Essential for item type display
        # Removed scoring relationships - not needed for bank listing
    )
    
    items = query.paginate(page=page, per_page=per_page, error_out=False)
    
    # Debug logging removed for performance
    
    # Optimized: Get filter options with fewer database queries
    if bank.item_type_id:
        # Use the bank's item_type_id directly instead of querying ItemType
        actual_item_type = 'filtered_by_item_type'
    else:
        # Use bank_type mapping
        bank_type_mapping = {
            'items': 'all_items',  # Special case: show all items regardless of category
            'products': 'product',
            'services': 'service', 
            'needs': 'need',
            'ideas': 'idea',
            'projects': 'project',
            'people': 'people',
            'funders': 'fund',
            'information': 'information',
            'experiences': 'experience',
            'opportunities': 'opportunity',
            'events': 'event',
            'auctions': 'auction',
            'observations': 'observation',
            'hidden_gems': 'hidden_gem'
        }
        actual_item_type = bank_type_mapping.get(bank.bank_type, bank.bank_type)
    
    # Optimized: Simplified filter options to reduce database queries
    if actual_item_type == 'all_items':
        # For 'items' bank, show all categories
        categories = []
        locations = []
    elif actual_item_type == 'filtered_by_item_type':
        # For banks with specific item_type_id, use the same filter as main query
        categories = []
        locations = []
    else:
        # For specific bank types, use minimal filtering
        categories = []
        locations = []
    
    # Get product categories for products bank (EXACT SAME AS OLD ROUTE)
    product_categories = []
    if bank.bank_type == 'products':
        product_categories = ProductCategory.query.filter_by(level=1, is_active=True).all()
    
    # Analytics tracking disabled for performance optimization
    # try:
    #     track_search_analytics(actual_item_type, search, category, location, product_category_id)
    # except Exception as e:
    #     print(f"Error tracking search analytics: {e}")
    
    # Support AJAX requests for partial loading
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # Return JSON for AJAX requests (partial loading)
        return jsonify({
            'items': [{
                'id': item.id,
                'title': item.title,
                'category': item.category,
                'subcategory': item.subcategory,
                'item_type': item.item_type.name if item.item_type else 'Unknown',
                'item_type_id': item.item_type_id,
                'price': item.price,
                'rating': item.rating,
                'images_media': item.images_media,
                'location': item.location,
                'profile_name': item.profile.name if item.profile else 'Unknown',
                'created_at': item.created_at.isoformat()
            } for item in items.items],
            'pagination': {
                'page': items.page,
                'pages': items.pages,
                'per_page': items.per_page,
                'total': items.total,
                'has_next': items.has_next,
                'has_prev': items.has_prev
            }
        })
    
    # Use EXACT SAME template and parameters as old route to maintain styling
    return render_template('banks/items.html', 
                         items=items,
                         bank=bank,  # Pass bank object for color access
                         bank_type=bank.bank_type,  # Use bank.bank_type to match old route parameter
                         categories=categories,
                         locations=locations,
                         product_categories=product_categories,
                         search=search,
                         category=category,
                         location=location,
                         min_price=min_price,
                         max_price=max_price,
                         sort_by=sort_by,
                         sort_order=sort_order)

def handle_user_bank(bank, page, per_page, search, sort_by, sort_order):
    """Handle user banks - show users/profiles based on bank configuration"""
    from models import ProfileType
    
    # Build query for users based on bank.user_filter (Profile Type) and privacy_filter
    if bank.user_filter:
        # Filter users by specific profile type
        base_query = User.query.join(Profile, User.id == Profile.user_id).filter(
            User.is_active == True,
            Profile.profile_type == bank.user_filter
        )
    else:
        # Show all users (no profile type filter)
        base_query = User.query.join(Profile, User.id == Profile.user_id).filter(
            User.is_active == True
        )
    
    # Apply privacy filter
    if bank.privacy_filter == 'public':
        query = base_query.filter(Profile.is_public == True)
    elif bank.privacy_filter == 'private':
        query = base_query.filter(Profile.is_public == False)
    else:  # 'all'
        query = base_query  # No privacy filter
    
    # Apply search filter
    if search:
        query = query.filter(
            or_(
                User.first_name.contains(search),
                User.last_name.contains(search),
                User.username.contains(search),
                User.email.contains(search)
            )
        )
    
    # Apply sorting
    if sort_by == 'name':
        if sort_order == 'asc':
            query = query.order_by(User.first_name.asc(), User.last_name.asc())
        else:
            query = query.order_by(User.first_name.desc(), User.last_name.desc())
    else:  # created_at
        if sort_order == 'asc':
            query = query.order_by(User.created_at.asc())
        else:
            query = query.order_by(User.created_at.desc())
    
    users = query.paginate(page=page, per_page=per_page, error_out=False)
    
    # Get profile objects for each user based on privacy filter
    user_profiles = {}
    for user in users.items:
        # Get the appropriate profile based on privacy filter
        if bank.privacy_filter == 'public':
            profile = Profile.query.filter_by(user_id=user.id, is_public=True).first()
        elif bank.privacy_filter == 'private':
            profile = Profile.query.filter_by(user_id=user.id, is_public=False).first()
        else:  # 'all'
            profile = Profile.query.filter_by(user_id=user.id).first()
        
        if profile:
            user_profiles[user.id] = profile  # Store profile object instead of just ID
    
    # Support AJAX requests
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'users': [{
                'id': user.id,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'username': user.username,
                'email': user.email,
                'location': user.location,
                'bio': user.bio,
                'avatar': user.avatar,
                'created_at': user.created_at.isoformat()
            } for user in users.items],
            'pagination': {
                'page': users.page,
                'pages': users.pages,
                'per_page': users.per_page,
                'total': users.total,
                'has_next': users.has_next,
                'has_prev': users.has_prev
            }
        })
    
    return render_template('banks/users.html', 
                         users=users,
                         user_profiles=user_profiles,
                         bank=bank,
                         bank_type=bank.bank_type,
                         search=search,
                         sort_by=sort_by,
                         sort_order=sort_order,
                         page=page)

def handle_organization_bank(bank, page, per_page, search, sort_by, sort_order):
    """Handle organization banks - show organizations based on bank configuration"""
    from models import OrganizationType
    
    # Get filter parameters from request
    org_type_filter = request.args.get('org_type_filter', '')
    privacy_filter = request.args.get('privacy_filter', '')
    
    # Build query for organizations
    query = Organization.query.filter_by(status='active')
    
    # Apply bank's privacy filter
    if bank.privacy_filter == 'public':
        query = query.filter(Organization.is_public == True)
    elif bank.privacy_filter == 'private':
        query = query.filter(Organization.is_public == False)
    # If privacy_filter is 'all', show all organizations
    
    # Apply bank's configured organization type filter
    if bank.organization_type_id:
        query = query.filter(Organization.organization_type_id == bank.organization_type_id)
    
    # Apply search filter
    if search:
        query = query.filter(
            or_(
                Organization.name.contains(search),
                Organization.description.contains(search),
                Organization.location.contains(search)
            )
        )
    
    # Apply sorting
    if sort_by == 'name':
        if sort_order == 'asc':
            query = query.order_by(Organization.name.asc())
        else:
            query = query.order_by(Organization.name.desc())
    else:  # created_at
        if sort_order == 'asc':
            query = query.order_by(Organization.created_at.asc())
        else:
            query = query.order_by(Organization.created_at.desc())
    
    organizations = query.paginate(page=page, per_page=per_page, error_out=False)
    
    # Get all organization types for the filter dropdown
    organization_types = OrganizationType.query.filter_by(is_active=True).order_by(OrganizationType.order_index.asc()).all()
    
    # Support AJAX requests
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'organizations': [{
                'id': org.id,
                'name': org.name,
                'slug': org.slug,
                'description': org.description,
                'organization_type': {
                    'id': org.organization_type.id if org.organization_type else None,
                    'name': org.organization_type.name if org.organization_type else 'Unknown',
                    'display_name': org.organization_type.display_name if org.organization_type else 'Unknown',
                    'icon_class': org.organization_type.icon_class if org.organization_type else 'fas fa-building',
                    'color_class': org.organization_type.color_class if org.organization_type else '#6c757d'
                },
                'website': org.website,
                'location': org.location,
                'logo': org.logo,
                'is_public': org.is_public,
                'created_at': org.created_at.isoformat()
            } for org in organizations.items],
            'pagination': {
                'page': organizations.page,
                'pages': organizations.pages,
                'per_page': organizations.per_page,
                'total': organizations.total,
                'has_next': organizations.has_next,
                'has_prev': organizations.has_prev
            }
        })
    
    return render_template('banks/organizations.html', 
                         organizations=organizations,
                         organization_types=organization_types,
                         bank=bank,
                         bank_type=bank.bank_type,
                         search=search,
                         org_type_filter=org_type_filter,
                         privacy_filter=privacy_filter,
                         sort_by=sort_by,
                         sort_order=sort_order,
                         page=page)


@banks_bp.route('/item/<int:item_id>')
@login_required
@require_permission('banks', 'view')
def item_detail(item_id):
    try:
        print(f"DEBUG: Loading item {item_id}")
        item = Item.query.options(db.joinedload(Item.item_type)).get_or_404(item_id)
        print(f"DEBUG: Item loaded: {item.title}")
        print(f"DEBUG: Item location: {item.location}")
        
        # INCREMENT VIEW COUNT (but not for item owner)
        item_owner_profile = Profile.query.get(item.profile_id)
        if item_owner_profile and item_owner_profile.user_id != current_user.id:
            # Not the owner viewing their own item - increment view count
            item.views += 1
            db.session.commit()
            print(f"DEBUG: View count incremented to {item.views}")
            
            # Also track in ItemInteraction for analytics
            from models import ItemInteraction
            import uuid
            interaction = ItemInteraction(
                item_id=item.id,
                user_id=current_user.id,
                interaction_type='view',
                source='bank',
                referrer=request.referrer or 'direct',
                session_id=request.cookies.get('session', str(uuid.uuid4())),
                ip_address=request.remote_addr
            )
            db.session.add(interaction)
            db.session.commit()
            print(f"DEBUG: View interaction tracked with session: {interaction.session_id}")
        else:
            print(f"DEBUG: Owner viewing own item - view count not incremented")
        
        # Find which bank this item belongs to based on item_type
        bank = None
        if item.item_type:
            bank = Bank.query.filter_by(item_type_id=item.item_type.id, is_active=True).first()
            print(f"DEBUG: Bank found: {bank.name if bank else 'None'}")
        
        # Get similar items
        similar_items = Item.query.filter(
            Item.category == item.category,
            Item.id != item.id,
            Item.is_available == True
        ).limit(6).all()
        print(f"DEBUG: Similar items count: {len(similar_items)}")
        
        print("DEBUG: About to render template")
        return render_template('banks/item_detail.html', 
                             item=item, 
                             bank=bank,
                             similar_items=similar_items)
    except Exception as e:
        print(f"DEBUG: Error in item_detail: {str(e)}")
        print(f"DEBUG: Error type: {type(e).__name__}")
        import traceback
        print(f"DEBUG: Traceback: {traceback.format_exc()}")
        raise

@banks_bp.route('/debug-items')
@login_required
def debug_items():
    items = Item.query.all()
    debug_info = []
    for item in items:
        debug_info.append({
            'id': item.id,
            'title': item.title,
            'category': item.category,
            'subcategory': item.subcategory,
            'is_available': item.is_available,
            'profile_id': item.profile_id
        })
    return jsonify({
        'total_items': len(items),
        'items': debug_info
    })

@banks_bp.route('/search')
@login_required
def search():
    query = request.args.get('q', '')
    bank_type = request.args.get('type', '')
    
    if not query:
        return jsonify({'items': []})
    
    # Search across all items
    search_query = Item.query.join(Profile).filter(
        Item.is_available == True,
        or_(
            Item.title.contains(query),
            Item.description.contains(query),
            Item.category.contains(query)
        )
    )
    
    if bank_type:
        search_query = search_query.filter(Item.category == bank_type)
    
    items = search_query.limit(10).all()
    
    results = []
    for item in items:
        results.append({
            'id': item.id,
            'title': item.title,
            'description': item.short_description[:100] + '...' if len(item.short_description) > 100 else item.short_description,
            'type': item.category,
            'price': item.price,
            'rating': item.rating,
            'profile_name': item.profile.name
        })
    
    return jsonify({'items': results})

@banks_bp.route('/recommendations')
@login_required
def recommendations():
    # Get user's tags and preferences
    user_tags = [tag.name for tag in current_user.tags]
    
    # Find items that match user's tags or are popular
    recommended_items = Item.query.join(Profile).filter(
        Item.is_available == True,
        Item.is_verified == True
    ).order_by(Item.rating.desc(), Item.review_count.desc()).limit(10).all()
    
    return jsonify({
        'items': [{
            'id': item.id,
            'title': item.title,
            'description': item.short_description[:100] + '...' if len(item.short_description) > 100 else item.short_description,
            'type': item.category,
            'price': item.price,
            'rating': item.rating,
            'profile_name': item.profile.name
        } for item in recommended_items]
    })

@banks_bp.route('/stats')
@login_required
def stats():
    # Get bank statistics
    stats = {
        'products': Item.query.filter_by(category='product', is_available=True).count(),
        'services': Item.query.filter_by(category='service', is_available=True).count(),
        'needs': Item.query.filter_by(category='idea', is_available=True).count(),
        'people': Item.query.filter_by(category='people', is_available=True).count(),
        'funders': Item.query.filter_by(category='funding', is_available=True).count(),
        'information': Item.query.filter_by(category='information', is_available=True).count(),
        'experiences': Item.query.filter_by(category='experience', is_available=True).count(),
        'opportunities': Item.query.filter_by(category='opportunity', is_available=True).count(),
        'events': Item.query.filter_by(category='event', is_available=True).count(),
        'observations': Item.query.filter_by(category='observation', is_available=True).count(),
        'hidden_gems': Item.query.filter_by(category='hidden_gem', is_available=True).count()
    }
    return jsonify(stats)

@banks_bp.route('/product-stats')
@login_required
def product_stats():
    # Get product statistics
    total_products = Item.query.filter_by(category='product', is_available=True).count()
    verified_products = Item.query.filter_by(category='product', is_available=True, is_verified=True).count()
    
    # Calculate average rating
    avg_rating_result = db.session.query(db.func.avg(Item.rating)).filter(
        Item.category == 'product',
        Item.is_available == True,
        Item.rating > 0
    ).scalar()
    avg_rating = float(avg_rating_result) if avg_rating_result else 0.0
    
    # Count active sellers (profiles with products)
    active_sellers = db.session.query(Profile).join(Item).filter(
        Item.category == 'product',
        Item.is_available == True
    ).distinct().count()
    
    return jsonify({
        'total_products': total_products,
        'verified_products': verified_products,
        'avg_rating': avg_rating,
        'active_sellers': active_sellers
    })

@banks_bp.route('/product-categories/<int:category_id>')
@login_required
def product_subcategories(category_id):
    # Get the main category
    main_category = ProductCategory.query.get_or_404(category_id)
    
    # Get subcategories (level 2)
    subcategories = ProductCategory.query.filter_by(parent_id=category_id, level=2, is_active=True).all()
    
    return render_template('banks/product_subcategories.html', 
                         main_category=main_category, 
                         subcategories=subcategories)

@banks_bp.route('/product-categories/<int:category_id>/<int:subcategory_id>')
@login_required
def product_sub_subcategories(category_id, subcategory_id):
    # Get the subcategory
    subcategory = ProductCategory.query.get_or_404(subcategory_id)
    
    # Get sub-subcategories (level 3)
    sub_subcategories = ProductCategory.query.filter_by(parent_id=subcategory_id, level=3, is_active=True).all()
    
    return render_template('banks/product_sub_subcategories.html', 
                         subcategory=subcategory, 
                         sub_subcategories=sub_subcategories)

@banks_bp.route('/product-categories/<int:category_id>/<int:subcategory_id>/<int:sub_subcategory_id>')
@login_required
def product_items_by_category(category_id, subcategory_id, sub_subcategory_id):
    # Get the final category
    final_category = ProductCategory.query.get_or_404(sub_subcategory_id)
    
    # Get items for this category
    page = request.args.get('page', 1, type=int)
    per_page = 20
    search = request.args.get('search', '')
    
    # Build query
    query = Item.query.join(Profile).filter(
        Item.category == 'product',
        Item.product_category_id == sub_subcategory_id,
        Item.is_available == True
    )
    
    # Apply search filter
    if search:
        query = query.filter(
            or_(
                Item.title.contains(search),
                Item.description.contains(search)
            )
        )
    
    items = query.paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template('banks/product_items.html', 
                         category=final_category,
                         items=items,
                         search=search)


def track_search_analytics(item_type, search_term, category, location, product_category_id):
    """Track search analytics for optimization"""
    try:
        # Track general search
        if search_term:
            existing = SearchAnalytics.query.filter_by(
                item_type=item_type,
                search_term=search_term,
                filter_field='general_search',
                filter_value='title_description'
            ).first()
            
            if existing:
                existing.search_count += 1
                existing.last_searched = datetime.utcnow()
            else:
                analytics = SearchAnalytics(
                    item_type=item_type,
                    search_term=search_term,
                    filter_field='general_search',
                    filter_value='title_description',
                    search_count=1,
                    user_id=current_user.id if current_user.is_authenticated else None
                )
                db.session.add(analytics)
        
        # Track category filter
        if category:
            existing = SearchAnalytics.query.filter_by(
                item_type=item_type,
                filter_field='category',
                filter_value=category
            ).first()
            
            if existing:
                existing.search_count += 1
                existing.last_searched = datetime.utcnow()
            else:
                analytics = SearchAnalytics(
                    item_type=item_type,
                    filter_field='category',
                    filter_value=category,
                    search_count=1,
                    user_id=current_user.id if current_user.is_authenticated else None
                )
                db.session.add(analytics)
        
        # Track location filter
        if location:
            existing = SearchAnalytics.query.filter_by(
                item_type=item_type,
                filter_field='location',
                filter_value=location
            ).first()
            
            if existing:
                existing.search_count += 1
                existing.last_searched = datetime.utcnow()
            else:
                analytics = SearchAnalytics(
                    item_type=item_type,
                    filter_field='location',
                    filter_value=location,
                    search_count=1,
                    user_id=current_user.id if current_user.is_authenticated else None
                )
                db.session.add(analytics)
        
        # Track product category filter
        if product_category_id:
            existing = SearchAnalytics.query.filter_by(
                item_type=item_type,
                filter_field='product_category_id',
                filter_value=str(product_category_id)
            ).first()
            
            if existing:
                existing.search_count += 1
                existing.last_searched = datetime.utcnow()
            else:
                analytics = SearchAnalytics(
                    item_type=item_type,
                    filter_field='product_category_id',
                    filter_value=str(product_category_id),
                    search_count=1,
                    user_id=current_user.id if current_user.is_authenticated else None
                )
                db.session.add(analytics)
        
        db.session.commit()
        
    except Exception as e:
        print(f"Error in track_search_analytics: {e}")
        db.session.rollback()
