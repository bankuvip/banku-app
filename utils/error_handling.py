"""
Comprehensive Error Handling Utilities
Provides centralized error handling, logging, and recovery mechanisms
"""

import logging
import traceback
from functools import wraps
from flask import current_app, request, jsonify, redirect, url_for, flash
from flask_login import current_user
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, OperationalError
from werkzeug.exceptions import HTTPException

# Configure logging
logger = logging.getLogger(__name__)

class ErrorHandler:
    """Centralized error handling class"""
    
    @staticmethod
    def handle_database_error(error, context="Database operation"):
        """Handle database-related errors"""
        try:
            if isinstance(error, IntegrityError):
                logger.warning(f"{context} - Integrity constraint violation: {str(error)}")
                return "Data integrity error. Please check your input and try again."
            elif isinstance(error, OperationalError):
                logger.error(f"{context} - Database connection error: {str(error)}")
                return "Database connection error. Please try again in a moment."
            elif isinstance(error, SQLAlchemyError):
                logger.error(f"{context} - Database error: {str(error)}")
                return "Database error occurred. Please try again."
            else:
                logger.error(f"{context} - Unknown database error: {str(error)}")
                return "An unexpected database error occurred."
        except Exception as e:
            logger.error(f"Error in error handler: {str(e)}")
            return "An unexpected error occurred."
    
    @staticmethod
    def handle_file_upload_error(error, context="File upload"):
        """Handle file upload related errors"""
        try:
            error_str = str(error).lower()
            if "permission denied" in error_str:
                logger.warning(f"{context} - Permission denied: {str(error)}")
                return "Permission denied. Please check file permissions."
            elif "no space left" in error_str or "disk full" in error_str:
                logger.error(f"{context} - Disk space error: {str(error)}")
                return "Insufficient disk space. Please contact administrator."
            elif "file too large" in error_str:
                logger.warning(f"{context} - File too large: {str(error)}")
                return "File is too large. Please choose a smaller file."
            elif "invalid file" in error_str:
                logger.warning(f"{context} - Invalid file: {str(error)}")
                return "Invalid file type. Please check the file format."
            else:
                logger.error(f"{context} - File upload error: {str(error)}")
                return "File upload failed. Please try again."
        except Exception as e:
            logger.error(f"Error in file upload error handler: {str(e)}")
            return "File upload error occurred."
    
    @staticmethod
    def handle_permission_error(error, context="Permission check"):
        """Handle permission related errors"""
        try:
            logger.warning(f"{context} - Permission error: {str(error)}")
            return "You don't have permission to perform this action."
        except Exception as e:
            logger.error(f"Error in permission error handler: {str(e)}")
            return "Permission error occurred."
    
    @staticmethod
    def handle_network_error(error, context="Network operation"):
        """Handle network related errors"""
        try:
            error_str = str(error).lower()
            if "timeout" in error_str:
                logger.warning(f"{context} - Timeout error: {str(error)}")
                return "Request timed out. Please try again."
            elif "connection" in error_str:
                logger.error(f"{context} - Connection error: {str(error)}")
                return "Connection error. Please check your network and try again."
            else:
                logger.error(f"{context} - Network error: {str(error)}")
                return "Network error occurred. Please try again."
        except Exception as e:
            logger.error(f"Error in network error handler: {str(e)}")
            return "Network error occurred."
    
    @staticmethod
    def handle_generic_error(error, context="Operation"):
        """Handle generic errors"""
        try:
            logger.error(f"{context} - Generic error: {str(error)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return "An unexpected error occurred. Please try again."
        except Exception as e:
            logger.error(f"Error in generic error handler: {str(e)}")
            return "An error occurred."

def safe_database_operation(operation_func, context="Database operation", default_return=None):
    """Decorator for safe database operations"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except SQLAlchemyError as e:
                error_message = ErrorHandler.handle_database_error(e, context)
                if current_app and hasattr(current_app, 'logger'):
                    current_app.logger.error(f"{context} failed: {str(e)}")
                return default_return
            except Exception as e:
                error_message = ErrorHandler.handle_generic_error(e, context)
                if current_app and hasattr(current_app, 'logger'):
                    current_app.logger.error(f"{context} failed: {str(e)}")
                return default_return
        return decorated_function
    return decorator

def safe_file_operation(operation_func, context="File operation", default_return=None):
    """Decorator for safe file operations"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except (OSError, IOError, PermissionError) as e:
                error_message = ErrorHandler.handle_file_upload_error(e, context)
                if current_app and hasattr(current_app, 'logger'):
                    current_app.logger.error(f"{context} failed: {str(e)}")
                return default_return
            except Exception as e:
                error_message = ErrorHandler.handle_generic_error(e, context)
                if current_app and hasattr(current_app, 'logger'):
                    current_app.logger.error(f"{context} failed: {str(e)}")
                return default_return
        return decorated_function
    return decorator

def safe_route_handler(redirect_url=None, json_response=False):
    """Decorator for safe route handlers"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except HTTPException:
                # Re-raise HTTP exceptions (404, 403, etc.)
                raise
            except SQLAlchemyError as e:
                error_message = ErrorHandler.handle_database_error(e, f"Route {f.__name__}")
                if json_response:
                    return jsonify({'success': False, 'message': error_message}), 500
                else:
                    flash(error_message, 'error')
                    return redirect(redirect_url or request.referrer or url_for('index'))
            except Exception as e:
                error_message = ErrorHandler.handle_generic_error(e, f"Route {f.__name__}")
                if json_response:
                    return jsonify({'success': False, 'message': error_message}), 500
                else:
                    flash(error_message, 'error')
                    return redirect(redirect_url or request.referrer or url_for('index'))
        return decorated_function
    return decorator

def log_errors(func):
    """Decorator to log all errors with context"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # Log error with context
            context = {
                'function': func.__name__,
                'args': str(args)[:200],  # Limit length
                'kwargs': str(kwargs)[:200],  # Limit length
                'user_id': current_user.id if current_user.is_authenticated else None,
                'request_url': request.url if request else None,
                'request_method': request.method if request else None,
                'error': str(e),
                'traceback': traceback.format_exc()
            }
            
            logger.error(f"Error in {func.__name__}: {context}")
            
            # Re-raise the exception
            raise
    
    return wrapper

def retry_on_failure(max_retries=3, delay=1, backoff=2):
    """Decorator to retry operations on failure"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        wait_time = delay * (backoff ** attempt)
                        logger.warning(f"Attempt {attempt + 1} failed for {func.__name__}, retrying in {wait_time}s: {str(e)}")
                        import time
                        time.sleep(wait_time)
                    else:
                        logger.error(f"All {max_retries} attempts failed for {func.__name__}: {str(e)}")
            
            # If we get here, all retries failed
            raise last_exception
        
        return wrapper
    return decorator

def validate_request_data(required_fields=None, optional_fields=None):
    """Decorator to validate request data"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                if request.is_json:
                    data = request.get_json()
                else:
                    data = request.form.to_dict()
                
                # Check required fields
                if required_fields:
                    missing_fields = [field for field in required_fields if field not in data or not data[field]]
                    if missing_fields:
                        error_message = f"Missing required fields: {', '.join(missing_fields)}"
                        if request.is_json:
                            return jsonify({'success': False, 'message': error_message}), 400
                        else:
                            flash(error_message, 'error')
                            return redirect(request.referrer or url_for('index'))
                
                # Add validated data to kwargs
                kwargs['validated_data'] = data
                return func(*args, **kwargs)
                
            except Exception as e:
                error_message = ErrorHandler.handle_generic_error(e, "Request validation")
                if request.is_json:
                    return jsonify({'success': False, 'message': error_message}), 400
                else:
                    flash(error_message, 'error')
                    return redirect(request.referrer or url_for('index'))
        
        return wrapper
    return decorator

# This function is deprecated - use the one below that shows error details
    
def register_error_handlers(app):
    @app.errorhandler(Exception)
    def handle_exception(error):
        logger.error(f"Unhandled exception: {str(error)}", exc_info=True)
        try:
            from models import db
            db.session.rollback()
        except Exception as db_error:
            logger.error(f"Database rollback failed: {str(db_error)}")
        
        if request.is_json:
            return jsonify({'success': False, 'message': 'An unexpected error occurred'}), 500
        
        # Check if user is authenticated, if not redirect to login
        from flask_login import current_user
        if not current_user.is_authenticated:
            flash('Please log in to continue.', 'error')
            return redirect(url_for('auth.login'))
        
        # Always show error details for debugging - no redirects!
        import traceback
        print(f"ERROR HANDLER: {str(error)}")
        print(f"ERROR TYPE: {type(error).__name__}")
        print(f"ERROR URL: {request.url}")
        print(f"ERROR TRACEBACK: {traceback.format_exc()}")
        
        error_details = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Error Details</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                .error-box {{ background: #f8d7da; border: 1px solid #f5c6cb; padding: 20px; border-radius: 5px; }}
                .traceback {{ background: #f8f9fa; border: 1px solid #dee2e6; padding: 15px; border-radius: 5px; font-family: monospace; white-space: pre-wrap; }}
                a {{ color: #007bff; text-decoration: none; }}
            </style>
        </head>
        <body>
            <h1>Error Details</h1>
            <div class="error-box">
                <p><strong>Error:</strong> {str(error)}</p>
                <p><strong>Type:</strong> {type(error).__name__}</p>
                <p><strong>URL:</strong> {request.url}</p>
                <p><strong>Method:</strong> {request.method}</p>
            </div>
            <h3>Traceback:</h3>
            <div class="traceback">{traceback.format_exc()}</div>
            <p><a href="{url_for('dashboard.index')}">← Back to Dashboard</a></p>
        </body>
        </html>
        """
        return error_details, 500
