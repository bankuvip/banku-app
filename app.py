from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, make_response
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
import logging
import atexit
import signal
import sys
from functools import wraps

app = Flask(__name__)

# CORS Configuration for Mobile App Support
from flask_cors import CORS
CORS(app, 
     origins=[
         "capacitor://localhost",  # iOS
         "http://localhost",        # Android local
         "https://localhost",       # Android local HTTPS
         "ionic://localhost",       # Ionic
         "http://localhost:*",      # Any local port
     ],
     supports_credentials=True,
     allow_headers=["Content-Type", "Authorization", "X-Requested-With", "X-CSRFToken"],
     expose_headers=["Content-Type", "X-CSRFToken"],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"]
)

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('SQLALCHEMY_DATABASE_URI') or os.environ.get('DATABASE_URL', 'mysql+pymysql://root@localhost:3300/banku')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')

# File upload configuration
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Security and robustness configurations
app.config['WTF_CSRF_ENABLED'] = True
app.config['WTF_CSRF_TIME_LIMIT'] = 3600  # 1 hour

# JSON encoding configuration to handle Unicode characters
app.config['JSON_AS_ASCII'] = False
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False

# Database connection pooling and optimization
from sqlalchemy.pool import QueuePool
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'poolclass': QueuePool,
    'pool_size': 20,  # Increased from 10 to handle more concurrent requests
    'pool_recycle': 600,  # Recycle connections every 10 minutes (was 3600 = 1 hour)
    'pool_pre_ping': True,  # Verify connections before use
    'max_overflow': 10,  # Reduced from 20 (total capacity now 30 connections)
    'pool_timeout': 30,
    'pool_reset_on_return': 'rollback'  # Always rollback transactions on return
}

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Security headers and caching middleware
@app.after_request
def add_security_headers(response):
    """Add security headers and caching for static files"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    
    # Add caching headers for static files
    if request.endpoint == 'static':
        response.headers['Cache-Control'] = 'public, max-age=31536000'  # 1 year
        response.headers['Expires'] = 'Thu, 31 Dec 2025 23:59:59 GMT'
    
    # Add caching for HTML pages (shorter duration)
    if response.content_type and 'text/html' in response.content_type:
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'  # No caching during development
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    
    return response

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    """Handle 404 errors"""
    logger.warning(f"404 error: {request.url}")
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    import traceback
    error_details = traceback.format_exc()
    logger.error(f"500 error: {str(error)}")
    logger.error(f"Error details: {error_details}")
    
    # Print to console for debugging
    print(f"=== 500 ERROR ===")
    print(f"Error: {str(error)}")
    print(f"Request path: {request.path}")
    print(f"Request method: {request.method}")
    print(f"Error details: {error_details}")
    print(f"==================")
    
    try:
        db.session.rollback()
    except Exception as db_error:
        logger.error(f"Database rollback failed: {str(db_error)}")

    # Return JSON for API requests, HTML for regular requests
    if request.is_json or request.path.startswith('/api/') or request.headers.get('Content-Type', '').startswith('application/json'):
        return jsonify({
            'success': False,
            'message': 'An unexpected error occurred',
            'error': str(error),
            'debug_info': error_details,
            'request_path': request.path,
            'request_method': request.method
        }), 500

    return render_template('errors/500.html'), 500

@app.errorhandler(403)
def forbidden_error(error):
    """Handle 403 errors"""
    logger.warning(f"403 error: {request.url}")
    return render_template('errors/403.html'), 403

@app.errorhandler(413)
def file_too_large_error(error):
    """Handle file upload size errors"""
    logger.warning(f"File too large: {request.url}")
    if request.is_json:
        return jsonify({'success': False, 'error': 'File is too large. Maximum size is 16MB.'}), 413
    # Show error on the same page instead of redirecting
    return render_template('errors/413.html', error_message='File is too large. Maximum size is 16MB.'), 413

# Exception handler is now handled by utils/error_handling.py

# CRITICAL FIX: Always cleanup database sessions after each request/context
@app.teardown_appcontext
def shutdown_session(exception=None):
    """Remove database session at the end of each request/app context"""
    try:
        db.session.remove()
    except Exception as e:
        logger.warning(f"Error removing session in teardown: {e}")

@app.teardown_request
def teardown_request(exception=None):
    """Cleanup after each request"""
    try:
        if exception:
            db.session.rollback()
        db.session.remove()
    except Exception as e:
        logger.warning(f"Error in request teardown: {e}")

# Request logging middleware
@app.before_request
def log_request_info():
    """Log request information for debugging"""
    logger.info(f"Request: {request.method} {request.url} from {request.remote_addr}")

# Import models first to initialize db
from models import db, User, Role, Tag, Profile, Item, Project, ProjectContributor, Deal, DealItem, DealMessage, Review, Earning, Notification, Bank, Information, ProductCategory, ButtonConfiguration, ItemType, DataStorageMapping, ChatbotCompletion, AnalyticsEvent, ABTest, ABTestAssignment, PerformanceMetric

# Import error handling and health monitoring
from utils.error_handling import register_error_handlers
from utils.health_monitor import initialize_health_monitoring

# Initialize extensions
db.init_app(app)

# Initialize Flask-Mail
from flask_mail import Mail
mail = Mail(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'

# Initialize CSRF protection
csrf = CSRFProtect(app)

# Disable CSRF for admin API routes
@csrf.exempt
def exempt_admin_api():
    """Exempt admin API routes from CSRF protection"""
    pass
from routes.auth import auth_bp
from routes.dashboard import dashboard_bp
from routes.banks import banks_bp
from routes.deals import deals_bp
from routes.profiles import profiles_bp
from routes.admin import admin_bp
from routes.simulations import simulations_bp
from routes.chatbot import chatbot_bp
from routes.data_collectors import data_collectors_bp
from routes.analytics import analytics_bp
from routes.ai_matching import ai_matching_bp
from routes.organizations import organizations_bp
from routes.feedback import feedback_bp
from routes.scoring_admin import scoring_admin_bp
from routes.wallet import wallet_bp

# Try to import API blueprint, make it optional
try:
    from routes.api import api_bp
    API_AVAILABLE = True
except ImportError as e:
    print(f"API module not available: {e}")
    API_AVAILABLE = False

# Register blueprints
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(dashboard_bp, url_prefix='/dashboard')
app.register_blueprint(banks_bp, url_prefix='/banks')
app.register_blueprint(deals_bp, url_prefix='/deals')
app.register_blueprint(profiles_bp, url_prefix='/profiles')
app.register_blueprint(admin_bp, url_prefix='/admin')

# Exempt admin chatbot routes from CSRF
csrf.exempt(admin_bp)

app.register_blueprint(simulations_bp, url_prefix='/simulations')
app.register_blueprint(chatbot_bp, url_prefix='/chatbot')
app.register_blueprint(data_collectors_bp, url_prefix='/data-collectors')
app.register_blueprint(analytics_bp, url_prefix='/analytics')
app.register_blueprint(ai_matching_bp, url_prefix='/ai-matching')
app.register_blueprint(organizations_bp, url_prefix='')
app.register_blueprint(feedback_bp, url_prefix='')
app.register_blueprint(scoring_admin_bp, url_prefix='/admin')
app.register_blueprint(wallet_bp, url_prefix='/wallet')

# Register API blueprint if available
if API_AVAILABLE:
    app.register_blueprint(api_bp)  # API documentation and endpoints
    print("API module loaded successfully")
else:
    print("WARNING: API module not available - API features disabled")

# Register error handlers and health monitoring
register_error_handlers(app)

# DISABLED: Health monitor background thread holds database connections
# This causes connections to sleep for extended periods (600+ seconds)
# The /health endpoint still works, just no background monitoring
# initialize_health_monitoring(app)
print("INFO: Background health monitoring disabled to prevent connection leaks")

# Register template filters
from utils.template_filters import register_template_filters
from utils.location_formatter import format_location_simple, format_location_with_link

register_template_filters(app)

# Register simple location formatter
@app.template_filter('format_location')
def format_location_filter(location_string):
    """Simple location formatter without external API calls"""
    return format_location_simple(location_string)

@app.template_filter('format_location_with_link')
def format_location_with_link_filter(location_string):
    """Format location with optional clickable link"""
    return format_location_with_link(location_string)

@app.template_filter('safe_json')
def safe_json_filter(obj):
    """Safely convert object to JSON, handling Unicode characters"""
    try:
        import json
        return json.dumps(obj, ensure_ascii=False, separators=(',', ':'))
    except (TypeError, ValueError) as e:
        # Fallback for objects that can't be serialized
        return json.dumps(str(obj), ensure_ascii=False, separators=(',', ':'))
    except Exception as e:
        # Ultimate fallback - return empty object
        return '{}'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/api-docs')
def api_docs():
    """API Documentation Page"""
    if not API_AVAILABLE:
        return render_template('api_docs_unavailable.html')
    return render_template('api_docs.html')

@app.route('/analytics/track', methods=['POST'])
def track_analytics():
    """Track analytics events from frontend"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Log the analytics event (you can extend this to store in database)
        print(f"Analytics Event: {data.get('event_type', 'unknown')} - {data.get('event_name', 'unknown')}")
        
        # For now, just return success
        # In the future, you can store this in the AnalyticsEvent model
        return jsonify({'status': 'success', 'message': 'Event tracked'}), 200
        
    except Exception as e:
        print(f"Analytics tracking error: {str(e)}")
        return jsonify({'error': 'Failed to track event'}), 500

@app.route('/favicon.ico')
def favicon():
    """Serve favicon.ico to prevent 404 errors"""
    return '', 204  # Return empty response with 204 No Content status

def cleanup_on_exit():
    """Cleanup function called when the app exits"""
    try:
        from utils.advanced_data_collector import advanced_collector
        advanced_collector.stop_scheduled_collectors()
        print("INFO: Advanced data collector cleanup completed")
        print("Data collector scheduler stopped gracefully")
    except Exception as e:
        print(f"Warning: Error stopping scheduler: {e}")

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    print(f"\nReceived signal {signum}, shutting down gracefully...")
    cleanup_on_exit()
    sys.exit(0)

if __name__ == '__main__':
    # Register cleanup functions
    atexit.register(cleanup_on_exit)
    signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # Termination signal
    
    with app.app_context():
        db.create_all()
        
        # Create initial admin user if not exists
        from models import User, Role
        from werkzeug.security import generate_password_hash
        from sqlalchemy import text
        
        # Create admin role if not exists
        admin_role = Role.query.filter_by(name='Admin').first()
        if not admin_role:
            admin_role = Role(
                name='Admin',
                description='Administrator role with full access',
                permissions='admin_access,user_management,content_management',
                is_active=True
            )
            db.session.add(admin_role)
            db.session.commit()
            print("Admin role created!")
        
        # Create admin user if not exists
        admin_user = User.query.filter_by(username='admin').first()
        if not admin_user:
            admin_user = User(
                username='admin',
                email='admin@banku.com',
                password_hash=generate_password_hash('admin123'),
                first_name='Admin',
                last_name='User',
                is_active=True,
                email_verified=True
            )
            db.session.add(admin_user)
            db.session.commit()
            print("Admin user created!")
            
            # Assign admin role to user using direct SQL
            if admin_role:
                db.session.execute(
                    text('INSERT INTO user_role_assignments (user_id, role_id) VALUES (:user_id, :role_id)'),
                    {'user_id': admin_user.id, 'role_id': admin_role.id}
                )
                db.session.commit()
                print("Admin role assigned to user!")
        else:
            print("Admin user already exists!")
        
        print("Admin setup complete! Login: admin / admin123")
        
        # DISABLED: Background tasks hold database connections indefinitely
        # This causes connection leaks - connections are held at thread level
        # Even with db.session.remove(), threads keep connections active
        # TODO: Redesign background tasks with proper connection cleanup
        # For now, use external cron jobs if data collection is needed
        
        # try:
        #     from utils.advanced_data_collector import advanced_collector
        #     advanced_collector.start_scheduled_collectors()
        #     print("SUCCESS: Advanced Data Collector scheduler started successfully!")
        # except ImportError as e:
        #     print(f"INFO: Advanced data collector not available: {e}")
        # except Exception as e:
        #     print(f"WARNING: Could not start data collector scheduler: {e}")
        #     logger.error(f"Data collector startup error: {str(e)}", exc_info=True)
        
        print("INFO: Background data collector disabled to prevent connection leaks")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
