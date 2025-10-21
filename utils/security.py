"""
Advanced Security System
Rate limiting, input validation, security headers, and threat detection
"""

import time
import hashlib
import re
from functools import wraps
from flask import request, jsonify, current_app, g
from collections import defaultdict, deque
import ipaddress

class SecurityManager:
    """Centralized security management"""
    
    def __init__(self):
        self.rate_limits = defaultdict(lambda: deque())
        self.blocked_ips = set()
        self.suspicious_ips = defaultdict(int)
        self.failed_attempts = defaultdict(int)
    
    def is_rate_limited(self, identifier, limit=100, window=3600):
        """Check if identifier is rate limited"""
        now = time.time()
        identifier = str(identifier)
        
        # Clean old entries
        while self.rate_limits[identifier] and self.rate_limits[identifier][0] <= now - window:
            self.rate_limits[identifier].popleft()
        
        # Check if limit exceeded
        if len(self.rate_limits[identifier]) >= limit:
            return True
        
        # Add current request
        self.rate_limits[identifier].append(now)
        return False
    
    def is_ip_blocked(self, ip):
        """Check if IP is blocked"""
        return ip in self.blocked_ips
    
    def block_ip(self, ip, reason="Suspicious activity"):
        """Block an IP address"""
        self.blocked_ips.add(ip)
        current_app.logger.warning(f"IP {ip} blocked: {reason}")
    
    def is_suspicious_request(self, request):
        """Detect suspicious request patterns"""
        suspicious_score = 0
        
        # Check for SQL injection patterns
        sql_patterns = [
            r'union\s+select', r'drop\s+table', r'delete\s+from',
            r'insert\s+into', r'update\s+set', r'exec\s*\(',
            r'script\s*>', r'<script', r'javascript:',
            r'\.\./', r'\.\.\\', r'%00', r'\x00'
        ]
        
        request_string = f"{request.url} {request.data.decode('utf-8', errors='ignore')}"
        for pattern in sql_patterns:
            if re.search(pattern, request_string, re.IGNORECASE):
                suspicious_score += 10
        
        # Check for XSS patterns
        xss_patterns = [
            r'<script', r'javascript:', r'onload=', r'onerror=',
            r'onclick=', r'onmouseover=', r'<iframe', r'<object'
        ]
        
        for pattern in xss_patterns:
            if re.search(pattern, request_string, re.IGNORECASE):
                suspicious_score += 5
        
        # Check for path traversal
        if '..' in request.path or '//' in request.path:
            suspicious_score += 15
        
        # Check for unusual user agent
        user_agent = request.headers.get('User-Agent', '')
        if not user_agent or len(user_agent) < 10:
            suspicious_score += 5
        
        # Check for unusual request size
        if request.content_length and request.content_length > 10 * 1024 * 1024:  # 10MB
            suspicious_score += 10
        
        return suspicious_score > 20
    
    def validate_input(self, data, input_type="text"):
        """Validate input data based on type"""
        if not data:
            return True, data
        
        if input_type == "email":
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, data):
                return False, "Invalid email format"
        
        elif input_type == "phone":
            phone_pattern = r'^\+?[\d\s\-\(\)]{10,}$'
            if not re.match(phone_pattern, data):
                return False, "Invalid phone format"
        
        elif input_type == "url":
            url_pattern = r'^https?://[^\s/$.?#].[^\s]*$'
            if not re.match(url_pattern, data):
                return False, "Invalid URL format"
        
        elif input_type == "alphanumeric":
            if not data.replace(' ', '').isalnum():
                return False, "Only alphanumeric characters allowed"
        
        elif input_type == "numeric":
            if not data.isdigit():
                return False, "Only numeric characters allowed"
        
        # Check for dangerous characters
        dangerous_chars = ['<', '>', '"', "'", '&', ';', '(', ')', '|', '`']
        if any(char in data for char in dangerous_chars):
            return False, "Dangerous characters detected"
        
        return True, data
    
    def sanitize_input(self, data):
        """Sanitize input data"""
        if not data:
            return data
        
        # Remove HTML tags
        data = re.sub(r'<[^>]+>', '', data)
        
        # Escape special characters
        data = data.replace('&', '&amp;')
        data = data.replace('<', '&lt;')
        data = data.replace('>', '&gt;')
        data = data.replace('"', '&quot;')
        data = data.replace("'", '&#x27;')
        
        return data

# Global security manager
security_manager = SecurityManager()

def rate_limit(limit=100, window=3600, per='ip'):
    """Rate limiting decorator"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if per == 'ip':
                identifier = request.remote_addr
            elif per == 'user':
                identifier = getattr(g, 'user', {}).get('id', request.remote_addr)
            else:
                identifier = request.remote_addr
            
            if security_manager.is_rate_limited(identifier, limit, window):
                return jsonify({
                    'error': 'Rate limit exceeded',
                    'message': f'Too many requests. Limit: {limit} per {window} seconds'
                }), 429
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def security_headers(f):
    """Add security headers decorator"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        response = f(*args, **kwargs)
        
        if hasattr(response, 'headers'):
            response.headers['X-Content-Type-Options'] = 'nosniff'
            response.headers['X-Frame-Options'] = 'DENY'
            response.headers['X-XSS-Protection'] = '1; mode=block'
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
            response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
            response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"
        
        return response
    return decorated_function

def validate_input(input_type="text", required=True):
    """Input validation decorator"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if request.method == 'POST':
                data = request.get_json() or request.form
                
                for field, value in data.items():
                    if required and not value:
                        return jsonify({
                            'error': 'Validation failed',
                            'message': f'Field {field} is required'
                        }), 400
                    
                    if value:
                        is_valid, error_msg = security_manager.validate_input(value, input_type)
                        if not is_valid:
                            return jsonify({
                                'error': 'Validation failed',
                                'message': f'Field {field}: {error_msg}'
                            }), 400
                        
                        # Sanitize the input
                        data[field] = security_manager.sanitize_input(value)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def threat_detection(f):
    """Threat detection decorator"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        client_ip = request.remote_addr
        
        # Check if IP is blocked
        if security_manager.is_ip_blocked(client_ip):
            return jsonify({
                'error': 'Access denied',
                'message': 'Your IP address has been blocked'
            }), 403
        
        # Check for suspicious request
        if security_manager.is_suspicious_request(request):
            security_manager.suspicious_ips[client_ip] += 1
            
            # Block IP if too many suspicious requests
            if security_manager.suspicious_ips[client_ip] > 5:
                security_manager.block_ip(client_ip, "Multiple suspicious requests")
                return jsonify({
                    'error': 'Access denied',
                    'message': 'Suspicious activity detected'
                }), 403
            
            current_app.logger.warning(f"Suspicious request from {client_ip}: {request.url}")
        
        return f(*args, **kwargs)
    return decorated_function

def csrf_protection(f):
    """CSRF protection decorator"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method in ['POST', 'PUT', 'DELETE', 'PATCH']:
            # Check CSRF token
            csrf_token = request.headers.get('X-CSRF-Token') or request.form.get('csrf_token')
            session_token = request.cookies.get('csrf_token')
            
            if not csrf_token or not session_token or csrf_token != session_token:
                return jsonify({
                    'error': 'CSRF validation failed',
                    'message': 'Invalid or missing CSRF token'
                }), 403
        
        return f(*args, **kwargs)
    return decorated_function

def generate_csrf_token():
    """Generate CSRF token"""
    import secrets
    return secrets.token_hex(32)

def log_security_event(event_type, details, user_id=None, ip=None):
    """Log security events"""
    from utils.analytics import AnalyticsService
    
    AnalyticsService.track_event(
        event_type='security_event',
        event_name=event_type,
        properties={
            'details': details,
            'user_id': user_id,
            'ip': ip or request.remote_addr,
            'timestamp': time.time()
        },
        user_id=user_id
    )

def check_password_strength(password):
    """Check password strength"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    
    if not re.search(r'\d', password):
        return False, "Password must contain at least one number"
    
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "Password must contain at least one special character"
    
    return True, "Password is strong"

def hash_password(password):
    """Hash password securely"""
    try:
        import bcrypt
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    except ImportError:
        # Fallback to simple hash if bcrypt not available
        import hashlib
        return hashlib.sha256(password.encode('utf-8')).hexdigest()

def verify_password(password, hashed):
    """Verify password against hash"""
    try:
        import bcrypt
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except ImportError:
        # Fallback to simple hash if bcrypt not available
        import hashlib
        return hashlib.sha256(password.encode('utf-8')).hexdigest() == hashed
