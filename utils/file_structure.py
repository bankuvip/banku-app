#!/usr/bin/env python3
"""
Advanced File Structure Management
Handles organized file storage with mobile upload support
"""

import os
import uuid
from datetime import datetime
from pathlib import Path
from flask import current_app, request
from werkzeug.utils import secure_filename

def detect_mobile_device():
    """Detect if request is from mobile device"""
    try:
        user_agent = request.headers.get('User-Agent', '').lower()
        mobile_indicators = ['android', 'iphone', 'ipad', 'mobile', 'blackberry', 'windows phone']
        return any(indicator in user_agent for indicator in mobile_indicators)
    except RuntimeError:
        # No request context available, assume desktop
        return False

def get_mobile_file_limits():
    """Get file size limits based on device type"""
    is_mobile = detect_mobile_device()
    return {
        'max_size': 8 * 1024 * 1024 if is_mobile else 10 * 1024 * 1024,  # 8MB mobile, 10MB desktop
        'max_size_mb': 8 if is_mobile else 10,
        'timeout': 45 if is_mobile else 120,  # 45s mobile, 2min desktop
        'is_mobile': is_mobile
    }

def validate_file_for_mobile(file, allowed_extensions=None):
    """Validate file with mobile-specific checks"""
    limits = get_mobile_file_limits()
    
    # Check file size
    file_size = len(file.read())
    file.seek(0)  # Reset file pointer
    
    if file_size > limits['max_size']:
        return {
            'valid': False,
            'error': f'File too large for {"mobile" if limits["is_mobile"] else "desktop"}. Maximum size: {limits["max_size_mb"]}MB. Please compress your photo or use a smaller image.'
        }
    
    # Check for HEIC/HEIF format (iPhone default)
    filename = secure_filename(file.filename)
    file_ext = os.path.splitext(filename)[1][1:].lower()
    
    if file_ext in ['heic', 'heif']:
        return {
            'valid': False,
            'error': 'HEIC/HEIF format not supported. Please convert to JPG or PNG on your device. iPhone users: Settings → Camera → Formats → Most Compatible'
        }
    
    # Check allowed extensions
    if allowed_extensions and file_ext not in allowed_extensions:
        return {
            'valid': False,
            'error': f'File type not allowed on {"mobile" if limits["is_mobile"] else "desktop"}. Allowed types: {", ".join(allowed_extensions)}. Please use JPG or PNG format.'
        }
    
    return {
        'valid': True,
        'file_size': file_size,
        'file_ext': file_ext,
        'limits': limits
    }

def generate_organized_path(user_id, file_type, context_name=None, item_id=None):
    """Generate organized directory path for file storage"""
    # Get static folder without Flask app context
    try:
        base_upload_dir = os.path.join(current_app.static_folder, 'uploads')
    except:
        # Fallback to direct path if no Flask context
        base_upload_dir = os.path.join('static', 'uploads')
    
    users_dir = os.path.join(base_upload_dir, 'users', str(user_id))
    
    # Create date-based subdirectory
    date_str = datetime.now().strftime('%Y-%m-%d')
    
    if file_type == 'profile':
        # For profiles: users/{user_id}/profiles/{profile_name}/{date}/
        profile_dir = os.path.join(users_dir, 'profiles', secure_filename(context_name or 'default'))
        target_dir = os.path.join(profile_dir, date_str)
    elif file_type == 'organization':
        # For organizations: users/{user_id}/organizations/{org_name}/{date}/
        org_dir = os.path.join(users_dir, 'organizations', secure_filename(context_name or 'default'))
        target_dir = os.path.join(org_dir, date_str)
    elif file_type == 'item':
        # For items: users/{user_id}/items/{date}/
        target_dir = os.path.join(users_dir, 'items', date_str)
    else:
        # Default: users/{user_id}/misc/{date}/
        target_dir = os.path.join(users_dir, 'misc', date_str)
    
    # Ensure directory exists
    os.makedirs(target_dir, exist_ok=True)
    
    return target_dir

def generate_unique_filename(user_id, item_id, file_ext, file_type='item'):
    """Generate unique filename with shorter format"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # Include milliseconds
    unique_id = str(uuid.uuid4())[:8]  # Short UUID for uniqueness
    
    # Format: {user_id}_{item_id}_{timestamp}_{uuid}.{ext}
    filename = f"{user_id}_{item_id}_{timestamp}_{unique_id}{file_ext}"
    
    return filename

def save_file_organized(file, user_id, item_id, file_type='item', context_name=None):
    """Save file with organized structure and mobile support"""
    
    # Validate file for mobile compatibility
    validation = validate_file_for_mobile(file)
    if not validation['valid']:
        return {
            'success': False,
            'error': validation['error']
        }
    
    # Generate organized path
    target_dir = generate_organized_path(user_id, file_type, context_name, item_id)
    
    # Generate unique filename
    file_ext = os.path.splitext(secure_filename(file.filename))[1]
    filename = generate_unique_filename(user_id, item_id, file_ext, file_type)
    
    # Full file path
    file_path = os.path.join(target_dir, filename)
    
    # Save file
    try:
        file.save(file_path)
        
        # Verify file was saved
        if not os.path.exists(file_path):
            return {
                'success': False,
                'error': 'File was not saved successfully'
            }
        
        # Generate relative path for database storage
        try:
            relative_path = os.path.relpath(file_path, current_app.static_folder)
        except:
            # Fallback if no Flask context
            relative_path = os.path.relpath(file_path, 'static')
        
        return {
            'success': True,
            'file_info': {
                'filename': filename,
                'relative_path': relative_path,
                'full_path': file_path,
                'size': validation['file_size'],
                'size_formatted': format_file_size(validation['file_size']),
                'file_type': file_type,
                'is_mobile': validation['limits']['is_mobile'],
                'device_type': 'mobile' if validation['limits']['is_mobile'] else 'desktop'
            }
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': f'Failed to save file: {str(e)}'
        }

def format_file_size(size_bytes):
    """Format file size in human readable format"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"

def get_file_url(relative_path):
    """Generate URL for file access"""
    return f"/static/{relative_path.replace(os.sep, '/')}"

def cleanup_old_files(user_id, days_old=30):
    """Clean up old files (optional maintenance function)"""
    base_dir = os.path.join(current_app.static_folder, 'uploads', 'users', str(user_id))
    if not os.path.exists(base_dir):
        return
    
    cutoff_date = datetime.now().timestamp() - (days_old * 24 * 60 * 60)
    
    for root, dirs, files in os.walk(base_dir):
        for file in files:
            file_path = os.path.join(root, file)
            if os.path.getmtime(file_path) < cutoff_date:
                try:
                    os.remove(file_path)
                except:
                    pass
