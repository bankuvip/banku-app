from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

# Association tables for many-to-many relationships

user_tags = db.Table('user_tags',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'), primary_key=True)
)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(20))
    location = db.Column(db.String(100))
    bio = db.Column(db.Text)
    avatar = db.Column(db.String(200))
    is_active = db.Column(db.Boolean, default=True)
    is_verified = db.Column(db.Boolean, default=False)
    email_verified = db.Column(db.Boolean, default=False)
    email_verification_token = db.Column(db.String(100), unique=True)
    email_verification_sent_at = db.Column(db.DateTime)
    email_resend_count = db.Column(db.Integer, default=0)
    email_resend_cooldown_until = db.Column(db.DateTime)
    phone_verified = db.Column(db.Boolean, default=False)
    phone_verification_code = db.Column(db.String(10))
    phone_verification_sent_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    last_welcome_popup = db.Column(db.DateTime)  # Track when user last saw welcome popup
    
    # Relationships
    profiles = db.relationship('Profile', backref='user', lazy=True, cascade='all, delete-orphan')
    roles = db.relationship('Role', secondary='user_role_assignments', lazy='dynamic', foreign_keys='[UserRole.user_id, UserRole.role_id]')
    tags = db.relationship('Tag', secondary=user_tags, backref='users')
    deals_as_provider = db.relationship('Deal', foreign_keys='Deal.provider_id')
    deals_as_consumer = db.relationship('Deal', foreign_keys='Deal.consumer_id')
    reviews_given = db.relationship('Review', foreign_keys='Review.reviewer_id', backref='reviewer')
    reviews_received = db.relationship('Review', foreign_keys='Review.reviewee_id', backref='reviewee')
    earnings = db.relationship('Earning', backref='user', lazy=True)
    notifications = db.relationship('Notification', backref='user', lazy=True, cascade='all, delete-orphan')
    wallet = db.relationship('Wallet', backref='user', lazy=True, cascade='all, delete-orphan', uselist=False)
    created_organizations = db.relationship('Organization', foreign_keys='Organization.created_by', backref='creator', lazy=True)
    owned_organizations = db.relationship('Organization', foreign_keys='Organization.current_owner', backref='owner', lazy=True)
    created_buttons = db.relationship('ButtonConfiguration', backref='creator', lazy=True, cascade='all, delete-orphan')
    created_item_types = db.relationship('ItemType', backref='creator', lazy=True, cascade='all, delete-orphan')
    created_information = db.relationship('Information', foreign_keys='Information.created_by', backref='creator', lazy=True, cascade='all, delete-orphan')
    assigned_information = db.relationship('Information', foreign_keys='Information.assigned_to', backref='assignee', lazy=True)
    
    def set_password(self, password):
        """Set password hash"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check password against hash"""
        return check_password_hash(self.password_hash, password)

class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.Text)
    permissions = db.Column(db.JSON)  # Store permissions as JSON
    is_internal = db.Column(db.Boolean, default=False)  # Internal staff vs external users
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    users = db.relationship('User', secondary='user_role_assignments', lazy='dynamic', overlaps="roles", foreign_keys='[UserRole.user_id, UserRole.role_id]')

# Permission System Models
class Permission(db.Model):
    """Individual permissions that can be assigned to roles"""
    __tablename__ = 'permissions'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(50), nullable=False)  # e.g., 'pages', 'features', 'data'
    resource = db.Column(db.String(100), nullable=False)  # e.g., 'users', 'items', 'organizations'
    action = db.Column(db.String(50), nullable=False)  # e.g., 'view', 'create', 'edit', 'delete'
    is_system = db.Column(db.Boolean, default=False)  # System-defined permissions
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class RolePermission(db.Model):
    """Many-to-many relationship between roles and permissions"""
    __tablename__ = 'role_permissions'
    id = db.Column(db.Integer, primary_key=True)
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'), nullable=False)
    permission_id = db.Column(db.Integer, db.ForeignKey('permissions.id'), nullable=False)
    granted = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    role = db.relationship('Role', backref='role_permissions')
    permission = db.relationship('Permission', backref='role_permissions')
    
    # Unique constraint
    __table_args__ = (db.UniqueConstraint('role_id', 'permission_id'),)

class UserRole(db.Model):
    """Many-to-many relationship between users and roles"""
    __tablename__ = 'user_role_assignments'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'), nullable=False)
    assigned_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    user = db.relationship('User', foreign_keys=[user_id], overlaps="roles,users")
    role = db.relationship('Role', overlaps="roles,users")
    assigned_by_user = db.relationship('User', foreign_keys=[assigned_by])
    
    # Unique constraint
    __table_args__ = (db.UniqueConstraint('user_id', 'role_id'),)

class UserPermission(db.Model):
    """Direct user permissions (overrides role permissions)"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    permission_id = db.Column(db.Integer, db.ForeignKey('permissions.id'), nullable=False)
    granted = db.Column(db.Boolean, default=True)
    granted_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    granted_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    user = db.relationship('User', foreign_keys=[user_id], backref='user_permissions')
    permission = db.relationship('Permission', backref='user_permissions')
    granted_by_user = db.relationship('User', foreign_keys=[granted_by])
    
    # Unique constraint
    __table_args__ = (db.UniqueConstraint('user_id', 'permission_id'),)

class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    category = db.Column(db.String(50))  # skiller, producer, consultant, etc.
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Profile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=True)  # URL-friendly identifier (nullable initially)
    profile_type = db.Column(db.String(50), nullable=True)  # Keep for backward compatibility
    profile_type_id = db.Column(db.Integer, db.ForeignKey('profile_types.id'), nullable=True)  # New foreign key
    description = db.Column(db.Text)
    website = db.Column(db.String(200))
    phone = db.Column(db.String(50), nullable=True)  # Phone number with country code
    location = db.Column(db.String(100))
    photo = db.Column(db.String(200))  # Profile photo (replaces logo)
    is_active = db.Column(db.Boolean, default=True)
    is_public = db.Column(db.Boolean, default=True)  # Visibility control for searches
    is_default = db.Column(db.Boolean, default=False)  # True for the user's default profile
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    items = db.relationship('Item', backref='profile', lazy=True, cascade='all, delete-orphan')
    projects = db.relationship('Project', backref='profile', lazy=True, cascade='all, delete-orphan')
    profile_type_rel = db.relationship('ProfileType', back_populates='profiles', lazy=True)

class ProductCategory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    parent_id = db.Column(db.Integer, db.ForeignKey('product_category.id'), nullable=True)
    level = db.Column(db.Integer, nullable=False)  # 1=main category, 2=subcategory, 3=sub-subcategory
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    children = db.relationship('ProductCategory', backref=db.backref('parent', remote_side=[id]))
    items = db.relationship('Item', backref='product_category', lazy=True)

class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    profile_id = db.Column(db.Integer, db.ForeignKey('profile.id'), nullable=False)
    
    # Basic Information
    title = db.Column(db.String(200), nullable=False)
    item_type_id = db.Column(db.Integer, db.ForeignKey('item_types.id'), nullable=False)  # Core classification (idea, product, service, need)
    category = db.Column(db.String(50), nullable=False)  # Search/filter enhancement (Science & Research, Music, Technology, etc.)
    subcategory = db.Column(db.String(50), nullable=False)  # Further classification (Physics, Mobile Apps, Consulting, etc.)
    
    # New hierarchical category system for products
    product_category_id = db.Column(db.Integer, db.ForeignKey('product_category.id'), nullable=True)
    custom_category = db.Column(db.String(100), nullable=True)  # For "Other" categories
    
    tags = db.Column(db.JSON)  # Store tags as JSON array
    short_description = db.Column(db.String(500), nullable=False)
    detailed_description = db.Column(db.Text, nullable=False)
    images_media = db.Column(db.JSON)  # Store image/media URLs as JSON array
    location_raw = db.Column(db.String(500))  # Raw input: coordinates, URL, or text
    location = db.Column(db.String(200))  # Formatted location: "Dubai, UAE" or "Cairo, Egypt"
    
    # Owner/Creator Information
    owner_type = db.Column(db.String(20), nullable=False)  # me, other
    owner_name = db.Column(db.String(200))  # if other
    owner_link = db.Column(db.String(500))  # if other
    
    # Pricing
    pricing_type = db.Column(db.String(20), nullable=False)  # free, paid, hybrid
    price = db.Column(db.Float)
    currency = db.Column(db.String(3), default='USD')
    
    # Status and Metadata
    is_available = db.Column(db.Boolean, default=True)
    is_verified = db.Column(db.Boolean, default=False)
    rating = db.Column(db.Float, default=0.0)
    review_count = db.Column(db.Integer, default=0)
    request_count = db.Column(db.Integer, default=0)
    views = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Product-specific fields (1.1-1.7)
    condition = db.Column(db.String(50))  # for physical products
    quantity = db.Column(db.Integer, default=1)
    shipping = db.Column(db.String(50))  # for physical products
    creator = db.Column(db.String(200))  # for products
    intellectual_property = db.Column(db.String(200))  # for rights/licenses
    patent_number = db.Column(db.String(100))  # for patents
    business_stage = db.Column(db.String(50))  # for ideas
    investment_needed = db.Column(db.Float)  # for ideas/plans
    timeline = db.Column(db.String(100))  # for ideas/plans
    target_market = db.Column(db.String(200))  # for ideas/plans
    collaboration_type = db.Column(db.String(50))  # for ideas/plans
    innovation_type = db.Column(db.String(50))  # for imagination/innovations
    
    # Service-specific fields (2)
    duration = db.Column(db.String(50))
    experience_level = db.Column(db.String(50))
    availability = db.Column(db.String(200))
    service_type = db.Column(db.String(50))  # physical, mental, hybrid
    
    # Experience-specific fields (3)
    experience_type = db.Column(db.String(50))  # business, personal, technical, etc.
    lessons_learned = db.Column(db.Text)
    mistakes_avoided = db.Column(db.Text)
    success_factors = db.Column(db.Text)
    
    # Opportunity-specific fields (4)
    opportunity_type = db.Column(db.String(50))  # business, investment, partnership, etc.
    urgency_level = db.Column(db.String(20))  # low, medium, high, urgent
    deadline = db.Column(db.Date)
    requirements = db.Column(db.Text)
    
    # Event-specific fields (5)
    event_type = db.Column(db.String(50))  # conference, workshop, meeting, social, etc.
    event_date = db.Column(db.DateTime)
    event_location = db.Column(db.String(200))
    max_participants = db.Column(db.Integer)
    registration_required = db.Column(db.Boolean, default=False)
    
    # Information-specific fields (6)
    information_type = db.Column(db.String(50))  # market, technical, personal, business, etc.
    source = db.Column(db.String(200))
    reliability_score = db.Column(db.Float)  # 0-10
    last_updated = db.Column(db.DateTime)
    
    # Observation-specific fields (7)
    observation_type = db.Column(db.String(50))  # market, behavior, trend, pattern, etc.
    context = db.Column(db.Text)
    significance = db.Column(db.Text)
    potential_impact = db.Column(db.String(200))
    
    # Hidden Gems & Resources fields (8)
    gem_type = db.Column(db.String(50))  # person, product, knowledge, expertise, etc.
    recognition_level = db.Column(db.String(20))  # unknown, underrated, emerging, established
    unique_value = db.Column(db.Text)
    promotion_potential = db.Column(db.Text)
    
    # Funder-specific fields (9)
    funding_type = db.Column(db.String(50))  # investment, loan, grant, donation, etc.
    funding_amount_min = db.Column(db.Float)
    funding_amount_max = db.Column(db.Float)
    interest_rate = db.Column(db.Float)
    term_length = db.Column(db.String(100))
    collateral_required = db.Column(db.String(50))
    funding_criteria = db.Column(db.Text)
    
    # HYBRID SYSTEM: Enhanced Category-Specific Fields
    # Enhanced Product fields
    brand = db.Column(db.String(100))
    model = db.Column(db.String(100))
    specifications = db.Column(db.Text)
    warranty = db.Column(db.String(200))
    accessories = db.Column(db.Text)
    
    # Enhanced Service fields
    availability_schedule = db.Column(db.Text)
    service_area = db.Column(db.String(200))
    certifications = db.Column(db.Text)
    portfolio = db.Column(db.Text)
    
    # Enhanced Event fields
    venue = db.Column(db.String(200))
    capacity = db.Column(db.Integer)
    event_type_category = db.Column(db.String(100))
    registration_fee = db.Column(db.Float)
    
    # Enhanced Project fields
    project_status = db.Column(db.String(50))
    team_size = db.Column(db.Integer)
    project_type = db.Column(db.String(100))
    technologies_used = db.Column(db.Text)
    
    # Enhanced Fund fields
    funding_goal = db.Column(db.Float)
    funding_type_category = db.Column(db.String(100))
    investment_terms = db.Column(db.Text)
    roi_expectation = db.Column(db.String(100))
    
    # Enhanced Experience fields
    group_size = db.Column(db.Integer)
    location_type = db.Column(db.String(100))
    difficulty_level = db.Column(db.String(50))
    equipment_needed = db.Column(db.Text)
    
    # Enhanced Opportunity fields
    compensation_type = db.Column(db.String(100))
    compensation_amount = db.Column(db.Float)
    remote_work = db.Column(db.Boolean)
    part_time = db.Column(db.Boolean)
    
    # Enhanced Information fields
    format = db.Column(db.String(100))
    language = db.Column(db.String(50))
    accessibility = db.Column(db.String(100))
    update_frequency = db.Column(db.String(50))
    
    # Enhanced Observation fields
    observation_date = db.Column(db.Date)
    data_source = db.Column(db.String(200))
    confidence_level = db.Column(db.Integer)
    actionable_insights = db.Column(db.Text)
    
    # Enhanced Hidden Gem fields
    discovery_context = db.Column(db.Text)
    rarity_level = db.Column(db.String(50))
    value_type = db.Column(db.String(100))
    promotion_strategy = db.Column(db.Text)
    
    # Enhanced Auction fields
    start_price = db.Column(db.Float)
    end_date = db.Column(db.DateTime)
    bid_increment = db.Column(db.Float)
    reserve_price = db.Column(db.Float)
    
    # Enhanced Need fields
    need_type = db.Column(db.String(100))
    budget_range = db.Column(db.String(100))
    
    # Analytics and Flexible Storage
    search_analytics = db.Column(db.Text)  # JSON for tracking search behavior
    type_data = db.Column(db.Text)         # JSON for flexible additional data
    field_usage_stats = db.Column(db.Text) # JSON for tracking field usage
    
    # Enhanced creator tracking for data collection system
    creator_type = db.Column(db.String(20), default='user')  # 'user' or 'organization'
    creator_id = db.Column(db.Integer)  # ID of user or organization
    creator_name = db.Column(db.String(200))  # Cached name for performance
    
    # Relationships
    item_type = db.relationship('ItemType', backref='items', lazy=True)
    # Note: Reviews are now accessed via review_target_type and review_target_id (polymorphic)
    # Use: Review.query.filter_by(review_target_type='item', review_target_id=self.id)
    deal_items = db.relationship('DealItem', backref='item', lazy=True)

class SearchAnalytics(db.Model):
    """Track user search behavior to identify popular fields for optimization"""
    __tablename__ = 'search_analytics'
    
    id = db.Column(db.Integer, primary_key=True)
    bank_type = db.Column(db.String(50), nullable=True)  # items, users, organizations
    bank_slug = db.Column(db.String(100), nullable=True)  # Specific bank being searched
    search_term = db.Column(db.String(200), nullable=True, index=True)  # The actual search query
    category_filter = db.Column(db.String(200), nullable=True)  # Category filter if used
    location_filter = db.Column(db.String(200), nullable=True)  # Location filter if used
    date_from = db.Column(db.Date, nullable=True)  # Date range from
    date_to = db.Column(db.Date, nullable=True)  # Date range to
    min_price = db.Column(db.Float, nullable=True)  # Price filter min
    max_price = db.Column(db.Float, nullable=True)  # Price filter max
    results_count = db.Column(db.Integer, default=0)  # How many results returned
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True, index=True)  # Who searched
    session_id = db.Column(db.String(255), nullable=True)  # Session ID for anonymous users
    ip_address = db.Column(db.String(45), nullable=True)  # IP address
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)  # When search happened
    
    # Legacy fields (keeping for backward compatibility)
    item_type = db.Column(db.String(50))
    filter_field = db.Column(db.String(100))
    filter_value = db.Column(db.String(200))
    search_count = db.Column(db.Integer, default=1)
    last_searched = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='search_analytics')

class UserNeed(db.Model):
    """Represents a user's expressed need or requirement"""
    __tablename__ = 'user_needs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Need Details
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    need_type = db.Column(db.String(50), nullable=False)  # product, service, experience, etc.
    urgency_level = db.Column(db.String(20), default='medium')  # low, medium, high, urgent
    
    # Requirements
    budget_min = db.Column(db.Float)
    budget_max = db.Column(db.Float)
    location = db.Column(db.String(100))
    timeline = db.Column(db.String(100))  # "ASAP", "1 week", "1 month", etc.
    
    # Flexible Requirements (JSON)
    requirements = db.Column(db.Text)  # JSON for flexible requirements
    
    # Status
    status = db.Column(db.String(20), default='active')  # active, fulfilled, cancelled, expired
    is_public = db.Column(db.Boolean, default=True)  # Can others see this need?
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at = db.Column(db.DateTime)  # When this need expires
    
    # Relationships
    user = db.relationship('User', backref='user_needs')
    matches = db.relationship('NeedItemMatch', backref='need', cascade='all, delete-orphan')

class NeedItemMatch(db.Model):
    """Represents a match between a user need and an available item"""
    __tablename__ = 'need_item_matches'
    
    id = db.Column(db.Integer, primary_key=True)
    need_id = db.Column(db.Integer, db.ForeignKey('user_needs.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False)
    
    # Match Quality
    match_score = db.Column(db.Float, nullable=False)  # 0.0 to 1.0
    confidence_level = db.Column(db.String(20), default='medium')  # low, medium, high
    
    # Match Details
    matching_fields = db.Column(db.Text)  # JSON of which fields matched
    match_reason = db.Column(db.Text)  # Human-readable explanation
    
    # User Interaction
    user_viewed = db.Column(db.Boolean, default=False)
    user_liked = db.Column(db.Boolean)  # True = interested, False = not interested, None = no action
    user_contacted = db.Column(db.Boolean, default=False)
    user_feedback = db.Column(db.Text)  # User's feedback on the match
    
    # Status
    status = db.Column(db.String(20), default='pending')  # pending, accepted, rejected, expired
    is_active = db.Column(db.Boolean, default=True)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_presented = db.Column(db.DateTime)  # When last shown to user
    
    # Relationships
    item = db.relationship('Item', backref='need_matches')

class MatchingFeedback(db.Model):
    """Stores user feedback on matches for algorithm improvement"""
    __tablename__ = 'matching_feedback'
    
    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.Integer, db.ForeignKey('need_item_matches.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Feedback Details
    feedback_type = db.Column(db.String(20), nullable=False)  # like, dislike, irrelevant, contacted
    rating = db.Column(db.Integer)  # 1-5 star rating
    comment = db.Column(db.Text)
    
    # Context
    context_data = db.Column(db.Text)  # JSON of additional context
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    match = db.relationship('NeedItemMatch', backref='feedback')
    user = db.relationship('User', backref='matching_feedback')

class MatchingSession(db.Model):
    """Tracks matching sessions for analytics and improvement"""
    __tablename__ = 'matching_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    need_id = db.Column(db.Integer, db.ForeignKey('user_needs.id'), nullable=False)
    algorithm_id = db.Column(db.Integer, db.ForeignKey('matching_algorithms.id'), nullable=True)
    
    # Session Details
    session_type = db.Column(db.String(50), default='search')  # search, recommendation, discovery
    matches_generated = db.Column(db.Integer, default=0)
    matches_viewed = db.Column(db.Integer, default=0)
    matches_liked = db.Column(db.Integer, default=0)
    matches_contacted = db.Column(db.Integer, default=0)
    
    # Performance Metrics
    session_duration = db.Column(db.Integer)  # Duration in seconds
    satisfaction_score = db.Column(db.Float)  # User satisfaction 0.0 to 1.0
    
    # Metadata
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    ended_at = db.Column(db.DateTime)
    
    # Relationships
    user = db.relationship('User', backref='matching_sessions')
    need = db.relationship('UserNeed', backref='matching_sessions')

class MatchingAlgorithm(db.Model):
    """Stores configuration and performance data for matching algorithms"""
    __tablename__ = 'matching_algorithms'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text)
    
    # Algorithm Configuration
    algorithm_type = db.Column(db.String(50), nullable=False)  # keyword, semantic, hybrid, ml
    configuration = db.Column(db.Text)  # JSON configuration
    
    # Performance Metrics
    accuracy_score = db.Column(db.Float, default=0.0)  # 0.0 to 1.0
    precision_score = db.Column(db.Float, default=0.0)
    recall_score = db.Column(db.Float, default=0.0)
    f1_score = db.Column(db.Float, default=0.0)
    
    # Usage Statistics
    total_matches_generated = db.Column(db.Integer, default=0)
    successful_matches = db.Column(db.Integer, default=0)  # Matches that led to user action
    
    # Status
    is_active = db.Column(db.Boolean, default=True)
    is_default = db.Column(db.Boolean, default=False)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    sessions = db.relationship('MatchingSession', backref='algorithm')

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    profile_id = db.Column(db.Integer, db.ForeignKey('profile.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(50), default='planning')  # planning, active, completed, cancelled
    budget = db.Column(db.Float)
    currency = db.Column(db.String(3), default='USD')
    deadline = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    contributors = db.relationship('ProjectContributor', backref='project', lazy=True, cascade='all, delete-orphan')

class ProjectContributor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    role = db.Column(db.String(100))
    contribution_percentage = db.Column(db.Float, default=0.0)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)

class Deal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    provider_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    consumer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    connector_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(50), default='pending')  # pending, in_progress, completed, cancelled
    total_amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(3), default='USD')
    commission_rate = db.Column(db.Float, default=0.1)  # 10% default commission
    escrow_amount = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    
    # Relationships
    provider = db.relationship('User', foreign_keys=[provider_id], overlaps="deals_as_provider")
    consumer = db.relationship('User', foreign_keys=[consumer_id], overlaps="deals_as_consumer")
    connector = db.relationship('User', foreign_keys=[connector_id])
    items = db.relationship('DealItem', backref='deal', lazy=True, cascade='all, delete-orphan')
    messages = db.relationship('DealMessage', backref='deal', lazy=True, cascade='all, delete-orphan')

class DealItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    deal_id = db.Column(db.Integer, db.ForeignKey('deal.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    unit_price = db.Column(db.Float, nullable=False)

class DealMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    deal_id = db.Column(db.Integer, db.ForeignKey('deal.id'), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_system = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    sender = db.relationship('User', foreign_keys=[sender_id], backref='deal_messages')

class DealRequest(db.Model):
    """Deal requests made by users for specific items"""
    __tablename__ = 'deal_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    need_description = db.Column(db.Text, nullable=False)
    budget_min = db.Column(db.Float, nullable=True)
    budget_max = db.Column(db.Float, nullable=True)
    urgency_level = db.Column(db.String(20), default='medium')  # low, medium, high
    category = db.Column(db.String(100), nullable=True)
    tags = db.Column(db.JSON, nullable=True)  # Array of tags
    preferred_connector_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    assigned_connector_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    status = db.Column(db.String(20), default='open')  # open, assigned, in_progress, completed, cancelled
    special_requirements = db.Column(db.Text, nullable=True)
    timeline = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    user = db.relationship('User', foreign_keys=[user_id], backref='deal_requests')
    item = db.relationship('Item', backref='deal_requests')
    preferred_connector = db.relationship('User', foreign_keys=[preferred_connector_id])
    assigned_connector = db.relationship('User', foreign_keys=[assigned_connector_id])
    updates = db.relationship('DealRequestUpdate', backref='deal_request', cascade='all, delete-orphan')

class DealRequestUpdate(db.Model):
    """Updates added to deal requests by users, connectors, or admins"""
    __tablename__ = 'deal_request_updates'
    
    id = db.Column(db.Integer, primary_key=True)
    deal_request_id = db.Column(db.Integer, db.ForeignKey('deal_requests.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    update_text = db.Column(db.Text, nullable=False)
    is_connector_update = db.Column(db.Boolean, default=False)
    is_admin_update = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='deal_request_updates')

class DealRequestCategory(db.Model):
    """Categories for organizing deal requests"""
    __tablename__ = 'deal_request_categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Note: DealRequest.category is a string field, not a foreign key relationship

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reviewer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    reviewee_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    # Polymorphic target: what is being reviewed
    review_target_type = db.Column(db.Enum('item', 'profile', 'organization', name='review_target_type'), nullable=False)
    review_target_id = db.Column(db.Integer, nullable=False, index=True)
    rating = db.Column(db.Integer, nullable=False)  # 1-5 stars
    comment = db.Column(db.Text)
    is_hidden = db.Column(db.Boolean, default=False, nullable=False)  # Hidden reviews only visible to users with permission
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Earning(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    deal_id = db.Column(db.Integer, db.ForeignKey('deal.id'))
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(3), default='USD')
    earning_type = db.Column(db.String(50), nullable=False)  # referral, project_contribution, connector, collector
    description = db.Column(db.Text)
    status = db.Column(db.String(50), default='pending')  # pending, paid, cancelled
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    paid_at = db.Column(db.DateTime)

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    notification_type = db.Column(db.String(50), nullable=False)  # deal_update, match, referral, etc.
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    data = db.Column(db.JSON)  # Additional data for the notification

class Bank(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=True)  # URL-friendly name (optional)
    description = db.Column(db.Text)
    bank_type = db.Column(db.String(50), nullable=False)  # items, organizations, users
    
    # Smart Filtering Configuration
    item_type_id = db.Column(db.Integer, db.ForeignKey('item_types.id'), nullable=True)  # For items banks
    organization_type_id = db.Column(db.Integer, db.ForeignKey('organization_types.id'), nullable=True)  # For organization banks
    user_filter = db.Column(db.String(50), nullable=True)  # 'personal', 'public', 'all' for user banks
    privacy_filter = db.Column(db.String(20), default='all', nullable=False)  # 'public', 'private', 'all' for organizations and profiles
    
    # Legacy fields (for backward compatibility)
    subcategory = db.Column(db.String(50))  # Deprecated - use item_type_id instead
    organization_type = db.Column(db.String(50))  # Deprecated - use organization_type_id instead
    
    is_active = db.Column(db.Boolean, default=True)
    is_public = db.Column(db.Boolean, default=True)
    
    # Visual customization
    icon = db.Column(db.String(50), default='fas fa-database')  # FontAwesome icon class
    color = db.Column(db.String(7), default='#007bff')  # Hex color code
    sort_order = db.Column(db.Integer, default=0)  # Display order (lower numbers first)
    
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Statistics
    content_count = db.Column(db.Integer, default=0)
    last_updated = db.Column(db.DateTime)
    
    # Relationships
    creator = db.relationship('User', backref='created_banks')
    # Note: item_type and org_type relationships can be accessed via queries when needed

class Information(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(100), nullable=False)  # person, company, industry, market, etc.
    source = db.Column(db.String(200))  # Where this info came from
    contact_info = db.Column(db.Text)  # Contact details if available
    location = db.Column(db.String(100))
    priority = db.Column(db.String(20), default='medium')  # low, medium, high, urgent
    status = db.Column(db.String(20), default='pending')  # pending, in_progress, completed, verified
    tags = db.Column(db.JSON)  # Store tags as JSON array
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    assigned_to = db.Column(db.Integer, db.ForeignKey('user.id'))  # Who is working on it
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_public = db.Column(db.Boolean, default=True)  # Can others see this info
    
    # Relationships

class Need(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    profile_id = db.Column(db.Integer, db.ForeignKey('profile.id'), nullable=False)
    
    # Basic Information
    title = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50), nullable=False)  # products, services, experiences, opportunities, events, informations, observations, hidden_gems, funders
    subcategory = db.Column(db.String(50), nullable=False)
    tags = db.Column(db.JSON)  # Store tags as JSON array
    short_description = db.Column(db.String(500), nullable=False)
    detailed_description = db.Column(db.Text, nullable=False)
    location = db.Column(db.String(100))
    
    # Need Specifics
    urgency_level = db.Column(db.String(20), nullable=False)  # low, medium, high, urgent
    budget_min = db.Column(db.Float)
    budget_max = db.Column(db.Float)
    currency = db.Column(db.String(3), default='USD')
    deadline = db.Column(db.Date)
    contact_preference = db.Column(db.String(50))  # email, phone, message, any
    
    # Requirements and Specifications
    requirements = db.Column(db.Text)  # Detailed requirements
    must_have = db.Column(db.Text)  # Must-have features/qualities
    nice_to_have = db.Column(db.Text)  # Nice-to-have features/qualities
    deal_breakers = db.Column(db.Text)  # Things that would disqualify
    
    # Status and Metadata
    status = db.Column(db.String(20), default='active')  # active, fulfilled, cancelled, expired
    is_public = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='needs')
    profile = db.relationship('Profile', backref='needs')


class Activity(db.Model):
    __tablename__ = 'activity'
    
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    activity_type = db.Column(db.String(50), nullable=False)  # created, edited, verified, connected, used_in_project
    description = db.Column(db.Text, nullable=False)
    activity_data = db.Column(db.JSON)  # Store additional data as JSON
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    item = db.relationship('Item', backref=db.backref('activities', lazy=True, order_by='Activity.created_at.desc()'))
    user = db.relationship('User', backref=db.backref('activities', lazy=True))


# Chatbot Management Models
class ChatbotFlow(db.Model):
    __tablename__ = 'chatbot_flow'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    flow_config = db.Column(db.JSON)  # Store the complete flow configuration
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # OPTION 4 PHASE 2: DATABASE IMPROVEMENTS
    version = db.Column(db.Integer, default=1)  # Version control for flow changes
    meta_json = db.Column(db.JSON)  # Additional metadata for extensibility
    performance_config = db.Column(db.JSON)  # Performance optimization settings
    analytics_config = db.Column(db.JSON)  # Analytics and tracking configuration
    
    # PERFORMANCE OPTIMIZATIONS
    cached_questions_count = db.Column(db.Integer, default=0)  # Cache question count
    cached_completion_rate = db.Column(db.Float, default=0.0)  # Cache completion rate
    last_performance_update = db.Column(db.DateTime)  # Track when performance was last calculated
    
    # Relationships
    creator = db.relationship('User', backref='created_flows')
    questions = db.relationship('ChatbotQuestion', back_populates='flow', lazy=True, cascade='all, delete-orphan', order_by='ChatbotQuestion.order_index')
    responses = db.relationship('ChatbotResponse', backref='flow', lazy=True, cascade='all, delete-orphan')
    step_blocks = db.relationship('ChatbotStepBlock', back_populates='flow', lazy=True, cascade='all, delete-orphan')
    completions = db.relationship('ChatbotCompletion', back_populates='chatbot', lazy=True, cascade='all, delete-orphan')
    
    # INDEXES FOR PERFORMANCE
    __table_args__ = (
        db.Index('idx_flow_active_created', 'is_active', 'created_at'),
        db.Index('idx_flow_creator', 'created_by'),
        db.Index('idx_flow_updated', 'updated_at'),
    )


class ChatbotQuestion(db.Model):
    __tablename__ = 'chatbot_question'
    
    id = db.Column(db.Integer, primary_key=True)
    flow_id = db.Column(db.Integer, db.ForeignKey('chatbot_flow.id'), nullable=False)
    step_block_id = db.Column(db.Integer, db.ForeignKey('chatbot_step_block.id'), nullable=True)  # Reference to step block
    question_text = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.String(50), nullable=False)  # text, select, radio, checkbox, email, phone, number, date, file
    options = db.Column(db.JSON)  # For select, radio, checkbox options
    validation_rules = db.Column(db.JSON)  # Required, min/max length, regex patterns, etc.
    conditional_logic = db.Column(db.JSON)  # Show/hide based on previous answers
    cascading_config = db.Column(db.JSON)  # Configuration for cascading dropdowns
    number_unit_config = db.Column(db.JSON)  # Configuration for number + unit questions
    media_upload_config = db.Column(db.JSON)  # Configuration for media upload questions
    branching_logic = db.Column(db.JSON)  # If-then logic for step navigation
    order_index = db.Column(db.Integer, nullable=False)
    is_required = db.Column(db.Boolean, default=True)
    placeholder = db.Column(db.String(200))
    help_text = db.Column(db.Text)
    default_view = db.Column(db.String(10), default='show')  # 'show' or 'hide'
    
    # NEW FIELDS FOR SCORING SYSTEM (Phase 2)
    question_classification = db.Column(db.String(20), default='additional')  # 'essential' or 'additional'
    field_mapping = db.Column(db.String(100))  # Field name to map to (e.g., 'title', 'price', 'feasibility')
    ai_weight = db.Column(db.Float, default=1.0)  # Importance for AI matching (0.0-1.0)
    semantic_keywords = db.Column(db.JSON)  # Keywords for AI processing
    
    # SCORING POINTS (NEW)
    visibility_points = db.Column(db.Integer, default=10)  # Points this question contributes to visibility score
    is_scoring_question = db.Column(db.Boolean, default=True)  # Whether this question affects scoring
    
    # OPTION 4 PHASE 2: DATABASE IMPROVEMENTS
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)  # Soft delete capability
    version = db.Column(db.Integer, default=1)  # Version control for question changes
    meta_json = db.Column(db.JSON)  # Additional metadata for extensibility
    
    # HIERARCHICAL ORGANIZATION SYSTEM
    hierarchical_id = db.Column(db.String(50))  # Format: "flow_id.step_id.question_id"
    step_sequence = db.Column(db.Integer, nullable=False, default=1)  # Step number within flow
    question_sequence = db.Column(db.Integer, nullable=False, default=1)  # Question number within step
    full_path = db.Column(db.String(200))  # Full path for display: "Chatbot1 > Step2 > Question3"
    
    # PERFORMANCE OPTIMIZATIONS
    cached_branching_result = db.Column(db.JSON)  # Cache complex branching logic results
    last_branching_calculation = db.Column(db.DateTime)  # Track when branching was last calculated
    
    # Relationships
    flow = db.relationship('ChatbotFlow', back_populates='questions', lazy=True)
    step_block = db.relationship('ChatbotStepBlock', back_populates='questions', lazy=True)
    
    # INDEXES FOR PERFORMANCE (will be added via migration)
    __table_args__ = (
        db.Index('idx_flow_order', 'flow_id', 'order_index'),
        db.Index('idx_flow_active', 'flow_id', 'is_active'),
        db.Index('idx_question_type', 'question_type'),
        db.Index('idx_field_mapping', 'field_mapping'),
        db.Index('idx_created_at', 'created_at'),
        # HIERARCHICAL ORGANIZATION INDEXES
        db.Index('idx_hierarchical_id', 'hierarchical_id'),
        db.Index('idx_step_sequence', 'flow_id', 'step_sequence'),
        db.Index('idx_question_sequence', 'flow_id', 'step_sequence', 'question_sequence'),
        db.Index('idx_full_path', 'full_path'),
    )


class ChatbotResponse(db.Model):
    __tablename__ = 'chatbot_response'
    
    id = db.Column(db.Integer, primary_key=True)
    flow_id = db.Column(db.Integer, db.ForeignKey('chatbot_flow.id'), nullable=False)
    session_id = db.Column(db.String(100), nullable=False)  # Track user session
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Optional user association
    responses = db.Column(db.JSON, nullable=False)  # Store all answers as JSON
    completed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    
    # Relationships
    user = db.relationship('User', backref='chatbot_responses')


# Content Management System Models
class Page(db.Model):
    __tablename__ = 'page'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(200), unique=True, nullable=False)
    content = db.Column(db.Text)
    meta_description = db.Column(db.String(300))
    meta_keywords = db.Column(db.String(500))
    is_published = db.Column(db.Boolean, default=True)
    is_homepage = db.Column(db.Boolean, default=False)
    template = db.Column(db.String(100), default='page.html')
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Relationships
    creator = db.relationship('User', backref='created_pages')
    content_blocks = db.relationship('ContentBlock', backref='page', lazy=True, cascade='all, delete-orphan', order_by='ContentBlock.sort_order')


class ContentBlock(db.Model):
    __tablename__ = 'content_block'
    
    id = db.Column(db.Integer, primary_key=True)
    page_id = db.Column(db.Integer, db.ForeignKey('page.id'), nullable=True)  # Null for global blocks
    title = db.Column(db.String(200))
    content = db.Column(db.Text)
    block_type = db.Column(db.String(50), nullable=False)  # text, image, video, html, form, gallery, etc.
    block_data = db.Column(db.JSON)  # Store additional data as JSON
    css_class = db.Column(db.String(200))
    is_published = db.Column(db.Boolean, default=True)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Relationships
    creator = db.relationship('User', backref='created_content_blocks')


class NavigationMenu(db.Model):
    __tablename__ = 'navigation_menu'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)  # main, footer, sidebar, etc.
    title = db.Column(db.String(200), nullable=False)
    url = db.Column(db.String(500))
    page_id = db.Column(db.Integer, db.ForeignKey('page.id'), nullable=True)
    parent_id = db.Column(db.Integer, db.ForeignKey('navigation_menu.id'), nullable=True)
    icon = db.Column(db.String(100))
    css_class = db.Column(db.String(200))
    is_published = db.Column(db.Boolean, default=True)
    sort_order = db.Column(db.Integer, default=0)
    requires_auth = db.Column(db.Boolean, default=False)
    required_roles = db.Column(db.JSON)  # Array of role names
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Relationships
    creator = db.relationship('User', backref='created_menus')
    page = db.relationship('Page', backref='menu_items')
    parent = db.relationship('NavigationMenu', remote_side=[id], backref='children')


class SiteSetting(db.Model):
    __tablename__ = 'site_setting'
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text)
    setting_type = db.Column(db.String(50), default='text')  # text, number, boolean, json, image, color
    category = db.Column(db.String(50), default='general')  # general, appearance, email, social, etc.
    description = db.Column(db.Text)
    is_public = db.Column(db.Boolean, default=False)  # Can be accessed via API
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Relationships
    updater = db.relationship('User', backref='updated_settings')


class EmailTemplate(db.Model):
    __tablename__ = 'email_template'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    body_html = db.Column(db.Text)
    body_text = db.Column(db.Text)
    template_type = db.Column(db.String(50), nullable=False)  # welcome, reset_password, notification, etc.
    variables = db.Column(db.JSON)  # Available template variables
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Relationships
    creator = db.relationship('User', backref='created_email_templates')


# Enhanced CMS Models for Complex Pages
class PageWidget(db.Model):
    __tablename__ = 'page_widget'
    
    id = db.Column(db.Integer, primary_key=True)
    page_id = db.Column(db.Integer, db.ForeignKey('page.id'), nullable=False)
    widget_type = db.Column(db.String(50), nullable=False)  # stats, chart, table, form, list, etc.
    widget_config = db.Column(db.JSON, nullable=False)  # Widget configuration
    position = db.Column(db.String(20), default='main')  # main, sidebar, header, footer
    sort_order = db.Column(db.Integer, default=0)
    is_published = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Relationships
    page = db.relationship('Page', backref='widgets')
    creator = db.relationship('User', backref='created_widgets')


class PageLayout(db.Model):
    __tablename__ = 'page_layout'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    layout_config = db.Column(db.JSON, nullable=False)  # Layout structure and grid
    is_system = db.Column(db.Boolean, default=False)  # System layouts vs custom
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Relationships
    creator = db.relationship('User', backref='created_layouts')


class WidgetTemplate(db.Model):
    __tablename__ = 'widget_template'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    widget_type = db.Column(db.String(50), nullable=False)
    template_config = db.Column(db.JSON, nullable=False)  # Default configuration
    description = db.Column(db.Text)
    category = db.Column(db.String(50), default='general')  # dashboard, banks, forms, etc.
    is_system = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Relationships
    creator = db.relationship('User', backref='created_widget_templates')


# Chatbot Step Blocks System
class ChatbotStepBlock(db.Model):
    __tablename__ = 'chatbot_step_block'
    
    id = db.Column(db.Integer, primary_key=True)
    flow_id = db.Column(db.Integer, db.ForeignKey('chatbot_flow.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)  # Step name like "Personal Information", "Preferences", etc.
    description = db.Column(db.Text)  # Optional description of what this step covers
    step_order = db.Column(db.Integer, nullable=False)  # Order of this step in the flow
    is_required = db.Column(db.Boolean, default=True)  # Whether this step is mandatory
    completion_message = db.Column(db.Text)  # Message shown when step is completed
    next_step_condition = db.Column(db.JSON)  # Conditions for which step to go to next
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Relationships
    flow = db.relationship('ChatbotFlow', back_populates='step_blocks')
    creator = db.relationship('User', backref='created_step_blocks')
    questions = db.relationship('ChatbotQuestion', back_populates='step_block', lazy=True, cascade='all, delete-orphan', order_by='ChatbotQuestion.order_index')


# Category System for Cascading Dropdowns
class Category(db.Model):
    __tablename__ = 'category'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Relationships
    creator = db.relationship('User', backref='created_categories')
    subcategories = db.relationship('Subcategory', backref='category', lazy=True, cascade='all, delete-orphan', order_by='Subcategory.sort_order')


class Subcategory(db.Model):
    __tablename__ = 'subcategory'
    
    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Relationships
    creator = db.relationship('User', backref='created_subcategories')

# Dynamic Management System Models

class ButtonConfiguration(db.Model):
    """Manages dashboard buttons dynamically"""
    __tablename__ = 'button_configurations'
    
    id = db.Column(db.Integer, primary_key=True)
    button_key = db.Column(db.String(50), unique=True, nullable=False)  # e.g., 'add_item', 'add_need', 'new_profile'
    button_label = db.Column(db.String(100), nullable=False)  # Display text
    button_description = db.Column(db.String(200))  # Description text
    target_type = db.Column(db.String(20), nullable=False)  # 'page', 'chatbot', 'external'
    target_value = db.Column(db.String(200))  # URL, chatbot_id, or external link
    icon_class = db.Column(db.String(50), default='fas fa-plus')  # FontAwesome icon
    button_color = db.Column(db.String(50), default='primary')  # Bootstrap color class
    is_active = db.Column(db.Boolean, default=True)
    is_visible = db.Column(db.Boolean, default=True)
    order_index = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class ItemType(db.Model):
    """Manages different types of items that can be created - these ARE the categories"""
    __tablename__ = 'item_types'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)  # Internal name (this becomes the category)
    display_name = db.Column(db.String(100), nullable=False)  # Display name
    description = db.Column(db.Text)
    
    # Visual Configuration
    icon_class = db.Column(db.String(50), default='fas fa-box')  # FontAwesome icon class
    button_color = db.Column(db.String(50), default='primary')  # Bootstrap color class
    border_color = db.Column(db.String(50))  # Custom border color
    text_color = db.Column(db.String(50))  # Custom text color
    
    # Configuration
    # chatbot_id and bank_id removed - now managed via Data Storage Mappings
    completion_action = db.Column(db.String(20), default='message')  # 'message', 'redirect', 'both'
    completion_message = db.Column(db.Text, default='Item created successfully!')
    redirect_url = db.Column(db.String(200))  # Where to redirect after completion
    
    # Status
    is_active = db.Column(db.Boolean, default=True)
    is_visible = db.Column(db.Boolean, default=True)
    order_index = db.Column(db.Integer, default=0)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    # chatbot and bank relationships removed - now managed via Data Storage Mappings

class DataStorageMapping(db.Model):
    """Maps chatbot data to storage locations"""
    __tablename__ = 'data_storage_mappings'
    
    id = db.Column(db.Integer, primary_key=True)
    item_type_id = db.Column(db.Integer, db.ForeignKey('item_types.id'), nullable=False)
    chatbot_id = db.Column(db.Integer, db.ForeignKey('chatbot_flow.id'), nullable=False)
    bank_id = db.Column(db.Integer, db.ForeignKey('bank.id'), nullable=False)
    
    # Storage configuration
    storage_config = db.Column(db.JSON)  # Additional storage settings
    data_mapping = db.Column(db.JSON)  # Maps chatbot fields to item fields
    validation_rules = db.Column(db.JSON)  # Data validation rules
    
    # Status
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    creator = db.relationship('User', backref='created_storage_mappings')
    item_type = db.relationship('ItemType', backref='storage_mappings')
    chatbot = db.relationship('ChatbotFlow', backref='storage_mappings')
    bank = db.relationship('Bank', backref='storage_mappings')

class ChatbotCompletion(db.Model):
    """Tracks chatbot completions and data flow"""
    __tablename__ = 'chatbot_completions'
    
    id = db.Column(db.Integer, primary_key=True)
    chatbot_id = db.Column(db.Integer, db.ForeignKey('chatbot_flow.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    item_type_id = db.Column(db.Integer, db.ForeignKey('item_types.id'), nullable=True)
    
    # Data
    collected_data = db.Column(db.JSON)  # All data collected from chatbot
    processed_data = db.Column(db.JSON)  # Processed data ready for storage
    storage_status = db.Column(db.String(20), default='pending')  # pending, stored, failed
    storage_location = db.Column(db.String(200))  # Where data was stored
    
    # Status
    completion_status = db.Column(db.String(20), default='completed')  # completed, failed, partial
    error_message = db.Column(db.Text)
    
    # Timestamps
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    stored_at = db.Column(db.DateTime)
    
    # Relationships
    chatbot = db.relationship('ChatbotFlow', back_populates='completions')
    user = db.relationship('User', backref='chatbot_completions')
    item_type = db.relationship('ItemType', backref='completions')

# Advanced Analytics & Monitoring Models

class AnalyticsEvent(db.Model):
    """Track all user interactions and system events"""
    __tablename__ = 'analytics_events'
    
    id = db.Column(db.Integer, primary_key=True)
    event_type = db.Column(db.String(50), nullable=False)  # 'button_click', 'page_view', 'chatbot_start', etc.
    event_name = db.Column(db.String(100), nullable=False)  # Specific event name
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    session_id = db.Column(db.String(100), nullable=True)
    
    # Event data
    properties = db.Column(db.JSON)  # Additional event properties
    page_url = db.Column(db.String(500))
    referrer = db.Column(db.String(500))
    user_agent = db.Column(db.String(500))
    ip_address = db.Column(db.String(45))
    
    # Context
    button_id = db.Column(db.Integer, db.ForeignKey('button_configurations.id'), nullable=True)
    item_type_id = db.Column(db.Integer, db.ForeignKey('item_types.id'), nullable=True)
    chatbot_id = db.Column(db.Integer, db.ForeignKey('chatbot_flow.id'), nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='analytics_events')
    button = db.relationship('ButtonConfiguration', backref='analytics_events')
    item_type = db.relationship('ItemType', backref='analytics_events')
    chatbot = db.relationship('ChatbotFlow', backref='analytics_events')

class ABTest(db.Model):
    """A/B Testing framework"""
    __tablename__ = 'ab_tests'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    test_type = db.Column(db.String(50), nullable=False)  # 'button_variant', 'page_layout', 'content', etc.
    
    # Test configuration
    variants = db.Column(db.JSON, nullable=False)  # List of variants with their configs
    traffic_split = db.Column(db.JSON, nullable=False)  # Traffic distribution (e.g., {"A": 50, "B": 50})
    target_metric = db.Column(db.String(50), nullable=False)  # 'conversion_rate', 'click_rate', 'completion_rate'
    
    # Status
    status = db.Column(db.String(20), default='draft')  # 'draft', 'active', 'paused', 'completed'
    start_date = db.Column(db.DateTime)
    end_date = db.Column(db.DateTime)
    winner_variant = db.Column(db.String(10))  # 'A', 'B', 'inconclusive'
    
    # Results
    results = db.Column(db.JSON)  # Test results and statistics
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Relationships
    creator = db.relationship('User', backref='created_ab_tests')

class ABTestAssignment(db.Model):
    """Track which users are assigned to which test variants"""
    __tablename__ = 'ab_test_assignments'
    
    id = db.Column(db.Integer, primary_key=True)
    test_id = db.Column(db.Integer, db.ForeignKey('ab_tests.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    variant = db.Column(db.String(10), nullable=False)  # 'A', 'B', 'C', etc.
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    test = db.relationship('ABTest', backref='assignments')
    user = db.relationship('User', backref='ab_test_assignments')

class PerformanceMetric(db.Model):
    """Track system performance metrics"""
    __tablename__ = 'performance_metrics'
    
    id = db.Column(db.Integer, primary_key=True)
    metric_name = db.Column(db.String(50), nullable=False)  # 'response_time', 'memory_usage', 'cpu_usage'
    metric_value = db.Column(db.Float, nullable=False)
    metric_unit = db.Column(db.String(20))  # 'ms', 'MB', '%'
    
    # Context
    endpoint = db.Column(db.String(200))
    method = db.Column(db.String(10))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    
    # Timestamps
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow)


# Data Collection and Bank Management System Models
class DataCollector(db.Model):
    """Data collectors that automatically gather specific types of data"""
    __tablename__ = 'data_collectors'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)  # "Company Collector"
    description = db.Column(db.Text)
    data_type = db.Column(db.String(50), nullable=False)  # 'organizations', 'users', 'items', 'needs'
    subcategory = db.Column(db.String(100), nullable=True)  # 'company', 'nonprofit', 'events', 'products', etc.
    filter_rules = db.Column(db.JSON)  # {"organization_type": "company", "status": "active"}
    is_active = db.Column(db.Boolean, default=True)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Performance tracking
    last_run = db.Column(db.DateTime)
    success_count = db.Column(db.Integer, default=0)
    error_count = db.Column(db.Integer, default=0)
    last_error = db.Column(db.Text)
    
    # Relationships
    creator = db.relationship('User', backref='created_collectors')

class BankCollector(db.Model):
    """Connection between banks and collectors"""
    __tablename__ = 'bank_collectors'
    
    id = db.Column(db.Integer, primary_key=True)
    bank_id = db.Column(db.Integer, db.ForeignKey('bank.id'), nullable=False)
    collector_id = db.Column(db.Integer, db.ForeignKey('data_collectors.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    bank = db.relationship('Bank', backref='collectors')
    collector = db.relationship('DataCollector', backref='banks')

class BankContent(db.Model):
    """Track content in banks"""
    __tablename__ = 'bank_content'
    
    id = db.Column(db.Integer, primary_key=True)
    bank_id = db.Column(db.Integer, db.ForeignKey('bank.id'), nullable=False)
    content_type = db.Column(db.String(20), nullable=False)  # 'item', 'organization', 'user', 'need'
    content_id = db.Column(db.Integer, nullable=False)  # ID of the actual content
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    added_by_collector = db.Column(db.Integer, db.ForeignKey('data_collectors.id'))
    
    # Relationships
    bank = db.relationship('Bank', backref='content')
    collector = db.relationship('DataCollector', backref='collected_content')

# Multi-Organization System Models
class OrganizationType(db.Model):
    """Types of organization profiles: company, team, project, etc."""
    __tablename__ = 'organization_types'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)  # company, team, project
    display_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    
    # Configuration
    requires_verification = db.Column(db.Boolean, default=False)  # companies need admin verification
    max_profiles_per_user = db.Column(db.Integer, default=10)  # admin configurable limit
    max_profiles_can_join = db.Column(db.Integer, default=50)  # max members the organization can have
    default_privacy = db.Column(db.String(20), default='public')  # public, private
    icon_class = db.Column(db.String(50), default='fas fa-users')  # FontAwesome icon
    color_class = db.Column(db.String(50), default='primary')  # Bootstrap color
    
    # Status
    is_active = db.Column(db.Boolean, default=True)
    order_index = db.Column(db.Integer, default=0)  # For ordering in admin interface
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    organizations = db.relationship('Organization', backref='organization_type', lazy=True)


class ProfileType(db.Model):
    """Types of personal profiles: person, professional, freelancer, etc."""
    __tablename__ = 'profile_types'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)  # person, professional, freelancer
    display_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    
    # Configuration
    requires_verification = db.Column(db.Boolean, default=False)  # professionals might need verification
    max_profiles_per_user = db.Column(db.Integer, default=5)  # admin configurable limit
    default_privacy = db.Column(db.String(20), default='public')  # public, private
    icon_class = db.Column(db.String(50), default='fas fa-user')  # FontAwesome icon
    color_class = db.Column(db.String(50), default='primary')  # Bootstrap color
    
    # Status
    is_active = db.Column(db.Boolean, default=True)
    order_index = db.Column(db.Integer, default=0)  # For ordering in admin interface
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships  
    profiles = db.relationship('Profile', back_populates='profile_type_rel', lazy=True)


class Organization(db.Model):
    """Main organization entity - independent organizational unit"""
    __tablename__ = 'organizations'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(200), unique=True, nullable=False)  # URL-friendly identifier
    description = db.Column(db.Text)
    logo = db.Column(db.String(500), nullable=True)  # Path to uploaded logo image
    
    # Type and Configuration
    organization_type_id = db.Column(db.Integer, db.ForeignKey('organization_types.id'), nullable=False)
    
    # Privacy & Visibility
    is_public = db.Column(db.Boolean, default=True)
    is_verified = db.Column(db.Boolean, default=False)  # admin verification for companies
    verification_documents = db.Column(db.JSON)  # store verification files/info
    
    # Status & Lifecycle
    status = db.Column(db.String(20), default='active')  # active, closed, suspended, pending_verification
    closed_at = db.Column(db.DateTime)
    closed_reason = db.Column(db.Text)
    
    # Ownership & Management
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    current_owner = db.Column(db.Integer, db.ForeignKey('user.id'))  # can be app (id=0) if all users leave
    admin_notes = db.Column(db.Text)  # admin notes for verification/management
    
    # Contact Information
    website = db.Column(db.String(500), nullable=True)  # Organization website URL
    phone = db.Column(db.String(50), nullable=True)  # Phone number with country code
    location = db.Column(db.String(200), nullable=True)  # Physical location/address
    
    # Social Media Links
    linkedin_url = db.Column(db.String(500), nullable=True)  # LinkedIn profile URL
    youtube_url = db.Column(db.String(500), nullable=True)  # YouTube channel URL
    facebook_url = db.Column(db.String(500), nullable=True)  # Facebook page URL
    instagram_url = db.Column(db.String(500), nullable=True)  # Instagram profile URL
    tiktok_url = db.Column(db.String(500), nullable=True)  # TikTok profile URL
    x_url = db.Column(db.String(500), nullable=True)  # X (Twitter) profile URL
    
    # Statistics
    member_count = db.Column(db.Integer, default=1)  # cached count
    content_count = db.Column(db.Integer, default=0)  # cached count of items/needs
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    members = db.relationship('OrganizationMember', backref='organization', lazy=True, cascade='all, delete-orphan')
    content = db.relationship('OrganizationContent', backref='organization', lazy=True, cascade='all, delete-orphan')
    history = db.relationship('OrganizationHistory', backref='organization', lazy=True, cascade='all, delete-orphan')


class OrganizationMember(db.Model):
    """Who belongs to which organization with what role and permissions"""
    __tablename__ = 'organization_members'
    
    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Role and Permissions
    role = db.Column(db.String(20), default='member')  # owner, admin, member, viewer
    permissions = db.Column(db.JSON)  # detailed permissions for future flexibility
    
    # Membership Status
    status = db.Column(db.String(20), default='active')  # active, inactive, invited, left
    invited_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    invitation_token = db.Column(db.String(100))  # for private organization invitations
    
    # Timestamps
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    left_at = db.Column(db.DateTime)
    left_reason = db.Column(db.Text)
    last_active = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', foreign_keys=[user_id], backref='organization_memberships')
    inviter = db.relationship('User', foreign_keys=[invited_by])
    
    # Constraints
    __table_args__ = (db.UniqueConstraint('organization_id', 'user_id', name='unique_organization_member'),)


class OrganizationContent(db.Model):
    """Items and needs associated with organizations"""
    __tablename__ = 'organization_content'
    
    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    
    # Content References (only one should be set)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=True)
    need_id = db.Column(db.Integer, db.ForeignKey('user_needs.id'), nullable=True)
    
    # Content Metadata
    content_type = db.Column(db.String(20), nullable=False)  # item, need
    added_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Content Status
    status = db.Column(db.String(20), default='active')  # active, removed, transferred
    removed_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    removed_at = db.Column(db.DateTime)
    removed_reason = db.Column(db.Text)
    
    # Relationships
    item = db.relationship('Item', backref='organization_associations')
    need = db.relationship('UserNeed', backref='organization_associations')
    adder = db.relationship('User', foreign_keys=[added_by], backref='added_organization_content')
    remover = db.relationship('User', foreign_keys=[removed_by])


class OrganizationHistory(db.Model):
    """Timeline of organization events for audit and learning"""
    __tablename__ = 'organization_history'
    
    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    
    # Event Details
    event_type = db.Column(db.String(50), nullable=False)  # created, member_joined, member_left, content_added, status_changed, etc.
    event_description = db.Column(db.Text, nullable=False)
    event_data = db.Column(db.JSON)  # additional event details
    
    # Actor
    actor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # null for system events
    actor_type = db.Column(db.String(20), default='user')  # user, admin, system
    
    # Timestamp
    occurred_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    actor = db.relationship('User', backref='organization_history_actions')

class Feedback(db.Model):
    """User feedback and suggestions"""
    __tablename__ = 'feedback'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Nullable for anonymous feedback
    type = db.Column(db.String(20), nullable=False)  # 'suggestion' or 'problem'
    subject = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    priority = db.Column(db.String(10), default='medium')  # 'low', 'medium', 'high', 'urgent'
    status = db.Column(db.String(20), default='pending')  # 'pending', 'in_progress', 'resolved', 'closed'
    admin_notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    resolved_at = db.Column(db.DateTime, nullable=True)
    resolved_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    
    # Relationships
    user = db.relationship('User', foreign_keys=[user_id], backref='feedback')
    resolved_by_user = db.relationship('User', foreign_keys=[resolved_by], backref='resolved_feedback')

# =============================================================================
# NEW SCORING AND FIELD SYSTEM MODELS (Phase 1 Implementation)
# =============================================================================

class ItemField(db.Model):
    """Additional fields for items (flexible data storage)"""
    __tablename__ = 'item_fields'
    
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False, index=True)
    
    # Field Information
    field_name = db.Column(db.String(100), nullable=False, index=True)
    field_value = db.Column(db.Text, nullable=False)
    field_type = db.Column(db.String(50), nullable=False, index=True)  # text, number, date, boolean, select
    field_label = db.Column(db.String(200))  # Display label for the field
    
    # Search and Display Configuration
    is_searchable = db.Column(db.Boolean, default=True, index=True)
    is_filterable = db.Column(db.Boolean, default=True, index=True)
    is_public = db.Column(db.Boolean, default=True)
    display_priority = db.Column(db.Integer, default=0)  # Higher number = higher priority
    
    # AI Processing
    normalized_value = db.Column(db.Text, index=True)  # For AI matching
    semantic_tags = db.Column(db.JSON)  # AI-generated tags for better search
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    item = db.relationship('Item', backref='additional_fields')

class ItemTypeField(db.Model):
    """Field definitions for different item types"""
    __tablename__ = 'item_type_fields'
    
    id = db.Column(db.Integer, primary_key=True)
    item_type = db.Column(db.String(50), nullable=False, index=True)  # product, idea, event, service
    
    # Field Configuration
    field_name = db.Column(db.String(100), nullable=False)
    field_label = db.Column(db.String(200), nullable=False)
    field_type = db.Column(db.String(50), nullable=False)  # text, number, date, boolean, select
    field_description = db.Column(db.Text)
    
    # Field Rules
    is_required = db.Column(db.Boolean, default=False)
    is_essential = db.Column(db.Boolean, default=False)  # Essential vs additional
    is_searchable = db.Column(db.Boolean, default=True)
    is_filterable = db.Column(db.Boolean, default=True)
    is_public = db.Column(db.Boolean, default=True)
    
    # Validation Rules
    validation_rules = db.Column(db.JSON)  # min_length, max_value, pattern, etc.
    field_options = db.Column(db.JSON)  # For select fields: ["option1", "option2"]
    
    # AI Configuration
    ai_weight = db.Column(db.Float, default=1.0)  # Importance for AI matching (0.0-1.0)
    semantic_keywords = db.Column(db.JSON)  # Keywords for AI processing
    auto_extract = db.Column(db.Boolean, default=False)  # Auto-extract from chatbot data
    
    # Display Configuration
    display_priority = db.Column(db.Integer, default=0)
    display_group = db.Column(db.String(50))  # Group fields together in display
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

class ItemVisibilityScore(db.Model):
    """Visibility scoring based on data completeness"""
    __tablename__ = 'item_visibility_scores'
    
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False, unique=True)
    
    # Scoring Components (0-100 each)
    essential_fields_score = db.Column(db.Integer, default=0)  # Title, description, category
    additional_fields_score = db.Column(db.Integer, default=0)  # Extra fields filled
    media_score = db.Column(db.Integer, default=0)  # Photos, videos, files
    detail_score = db.Column(db.Integer, default=0)  # Description length, quality
    
    # Calculated Scores
    total_visibility_score = db.Column(db.Integer, default=0)  # 0-400
    visibility_level = db.Column(db.String(20), default='low')  # low, medium, high, premium
    visibility_percentage = db.Column(db.Float, default=0.0)  # 0.0-100.0
    
    # Metadata
    last_calculated = db.Column(db.DateTime, default=datetime.utcnow)
    calculation_version = db.Column(db.String(20), default='1.0')
    
    # Relationships
    item = db.relationship('Item', backref='visibility_score', uselist=False)

class ItemCredibilityScore(db.Model):
    """Credibility scoring based on user verification"""
    __tablename__ = 'item_credibility_scores'
    
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False, unique=True)
    
    # User Verification (0-200 points)
    email_verified = db.Column(db.Boolean, default=False)
    phone_verified = db.Column(db.Boolean, default=False)
    id_verified = db.Column(db.Boolean, default=False)
    social_verified = db.Column(db.Boolean, default=False)
    
    # Item Verification (0-150 points)
    item_verified = db.Column(db.Boolean, default=False)
    admin_approved = db.Column(db.Boolean, default=False)
    quality_checked = db.Column(db.Boolean, default=False)
    
    # Profile Completeness (0-100 points)
    profile_complete = db.Column(db.Boolean, default=False)
    bio_complete = db.Column(db.Boolean, default=False)
    location_added = db.Column(db.Boolean, default=False)
    
    # Trust Indicators (0-50 points)
    verification_badges = db.Column(db.JSON)  # ["email_verified", "phone_verified", "id_verified"]
    trust_level = db.Column(db.String(20), default='low')  # low, medium, high, verified
    
    # Calculated Scores
    total_credibility_score = db.Column(db.Integer, default=0)  # 0-500
    credibility_percentage = db.Column(db.Float, default=0.0)  # 0.0-100.0
    
    # Metadata
    last_calculated = db.Column(db.DateTime, default=datetime.utcnow)
    calculation_version = db.Column(db.String(20), default='1.0')
    
    # Relationships
    item = db.relationship('Item', backref='credibility_score', uselist=False)

class ItemReviewScore(db.Model):
    """Review scoring based on ratings and reviews"""
    __tablename__ = 'item_review_scores'
    
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False, unique=True)
    
    # Review Metrics
    total_reviews = db.Column(db.Integer, default=0)
    average_rating = db.Column(db.Float, default=0.0)
    rating_distribution = db.Column(db.JSON)  # {1: 0, 2: 1, 3: 2, 4: 5, 5: 10}
    
    # Quality Indicators (0-100 points)
    review_quality_score = db.Column(db.Integer, default=0)  # Based on review length, detail
    response_rate = db.Column(db.Float, default=0.0)  # How often user responds to reviews
    dispute_rate = db.Column(db.Float, default=0.0)  # How often reviews are disputed
    
    # Calculated Scores
    total_review_score = db.Column(db.Integer, default=0)  # 0-300
    review_level = db.Column(db.String(20), default='none')  # none, low, medium, high, excellent
    review_percentage = db.Column(db.Float, default=0.0)  # 0.0-100.0
    
    # Metadata
    last_calculated = db.Column(db.DateTime, default=datetime.utcnow)
    calculation_version = db.Column(db.String(20), default='1.0')
    
    # Relationships
    item = db.relationship('Item', backref='review_score', uselist=False)

class ItemInteraction(db.Model):
    """Track user interactions with items (for trending, not scoring)"""
    __tablename__ = 'item_interactions'
    
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True, index=True)  # Nullable for anonymous
    
    # Interaction Types
    interaction_type = db.Column(db.String(20), nullable=False, index=True)  # view, click, save, share, contact
    session_id = db.Column(db.String(100), index=True)  # For anonymous tracking
    ip_address = db.Column(db.String(45))  # For anonymous tracking
    
    # Context
    source = db.Column(db.String(50))  # bank, search, recommendation, direct
    referrer = db.Column(db.String(200))  # Where they came from
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    item = db.relationship('Item', backref='interactions')
    user = db.relationship('User', backref='item_interactions')

class ContentModeration(db.Model):
    """AI content analysis and moderation reports"""
    __tablename__ = 'content_moderation'
    
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False, index=True)
    
    # Analysis Results
    analysis_type = db.Column(db.String(50), nullable=False)  # spam, quality, inappropriate, duplicate
    confidence_score = db.Column(db.Float, default=0.0)  # 0.0-1.0
    risk_level = db.Column(db.String(20), default='low')  # low, medium, high, critical
    
    # Detected Issues
    detected_issues = db.Column(db.JSON)  # List of specific issues found
    suggested_actions = db.Column(db.JSON)  # Recommended actions
    auto_resolved = db.Column(db.Boolean, default=False)
    
    # Admin Review
    admin_reviewed = db.Column(db.Boolean, default=False)
    admin_decision = db.Column(db.String(20))  # approve, reject, flag, ignore
    admin_notes = db.Column(db.Text)
    reviewed_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    reviewed_at = db.Column(db.DateTime)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    analysis_version = db.Column(db.String(20), default='1.0')
    
    # Relationships
    item = db.relationship('Item', backref='moderation_reports')
    reviewer = db.relationship('User', foreign_keys=[reviewed_by], backref='moderation_reviews')

class LocationCache(db.Model):
    """Cache for location geocoding results to avoid repeated API calls"""
    __tablename__ = 'location_cache'
    
    id = db.Column(db.Integer, primary_key=True)
    location_string = db.Column(db.String(500), unique=True, nullable=False, index=True)
    city = db.Column(db.String(100))
    country = db.Column(db.String(100))
    formatted_location = db.Column(db.String(200))  # e.g., "Dubai, UAE"
    coordinates_lat = db.Column(db.Float)
    coordinates_lng = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_used = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<LocationCache {self.location_string[:50]} -> {self.formatted_location}>'

class SavedItem(db.Model):
    """Track items saved by users"""
    __tablename__ = 'saved_items'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False)
    saved_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='saved_items')
    item = db.relationship('Item', backref='saved_by_users')
    
    # Unique constraint to prevent duplicate saves
    __table_args__ = (db.UniqueConstraint('user_id', 'item_id'),)
    
    def __repr__(self):
        return f'<SavedItem user_id={self.user_id} item_id={self.item_id}>'


class Wallet(db.Model):
    """User wallet for managing earnings and transactions"""
    __tablename__ = 'wallets'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)
    balance = db.Column(db.Float, default=0.0, nullable=False)
    currency = db.Column(db.String(3), default='USD', nullable=False)
    
    # Wallet settings
    is_active = db.Column(db.Boolean, default=True)
    auto_withdraw_enabled = db.Column(db.Boolean, default=False)
    withdrawal_threshold = db.Column(db.Float, default=100.0)  # Auto-withdraw when balance reaches this amount
    
    # Payment information
    payment_method = db.Column(db.String(50))  # bank_transfer, paypal, stripe, crypto
    payment_details = db.Column(db.JSON)  # Encrypted payment information
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_withdrawal_at = db.Column(db.DateTime)
    
    # Relationships
    transactions = db.relationship('WalletTransaction', backref='wallet', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Wallet user_id={self.user_id} balance={self.balance}>'


class WalletTransaction(db.Model):
    """Wallet transaction history"""
    __tablename__ = 'wallet_transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    wallet_id = db.Column(db.Integer, db.ForeignKey('wallets.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # Denormalized for easier querying
    
    # Transaction details
    transaction_type = db.Column(db.String(50), nullable=False)  # deposit, withdrawal, transfer, fee, refund
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(3), default='USD', nullable=False)
    balance_before = db.Column(db.Float, nullable=False)
    balance_after = db.Column(db.Float, nullable=False)
    
    # Transaction metadata
    description = db.Column(db.Text)
    reference_id = db.Column(db.String(100))  # External reference (deal_id, earning_id, etc.)
    reference_type = db.Column(db.String(50))  # deal, earning, withdrawal, deposit, fee
    
    # Status and processing
    status = db.Column(db.String(50), default='pending')  # pending, completed, failed, cancelled
    processing_fee = db.Column(db.Float, default=0.0)
    
    # External payment info
    external_transaction_id = db.Column(db.String(200))  # Payment processor transaction ID
    payment_method = db.Column(db.String(50))
    payment_details = db.Column(db.JSON)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    processed_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    
    # Relationships
    user = db.relationship('User', backref='wallet_transactions')
    
    def __repr__(self):
        return f'<WalletTransaction {self.transaction_type} {self.amount} {self.currency}>'


class WithdrawalRequest(db.Model):
    """User withdrawal requests"""
    __tablename__ = 'withdrawal_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    wallet_id = db.Column(db.Integer, db.ForeignKey('wallets.id'), nullable=False)
    
    # Withdrawal details
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(3), default='USD', nullable=False)
    requested_balance = db.Column(db.Float, nullable=False)  # Balance when request was made
    
    # Payment information
    payment_method = db.Column(db.String(50), nullable=False)
    payment_details = db.Column(db.JSON, nullable=False)  # Encrypted payment information
    
    # Status and processing
    status = db.Column(db.String(50), default='pending')  # pending, approved, processing, completed, rejected, cancelled
    admin_notes = db.Column(db.Text)
    processing_fee = db.Column(db.Float, default=0.0)
    
    # External processing
    external_transaction_id = db.Column(db.String(200))  # Payment processor transaction ID
    processed_by_admin_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    processed_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    
    # Relationships
    user = db.relationship('User', foreign_keys=[user_id], backref='withdrawal_requests')
    wallet = db.relationship('Wallet', backref='withdrawal_requests')
    processed_by_admin = db.relationship('User', foreign_keys=[processed_by_admin_id])
    
    def __repr__(self):
        return f'<WithdrawalRequest user_id={self.user_id} amount={self.amount} status={self.status}>'


