"""
File utility functions for media upload categorization
"""
import os
import mimetypes
from typing import Dict, List, Optional, Tuple

# File type categories
FILE_CATEGORIES = {
    'images': {
        'name': 'Images',
        'description': 'Photos, graphics, and visual content',
        'extensions': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif', '.webp', '.svg', '.ico', '.heic', '.heif'],
        'mime_types': ['image/jpeg', 'image/png', 'image/gif', 'image/bmp', 'image/tiff', 'image/webp', 'image/svg+xml', 'image/x-icon', 'image/heic', 'image/heif'],
        'max_size': 10 * 1024 * 1024,  # 10MB
        'icon': 'fas fa-image'
    },
    'videos': {
        'name': 'Videos',
        'description': 'Video files and multimedia content',
        'extensions': ['.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm', '.mkv', '.m4v', '.3gp', '.ogv'],
        'mime_types': ['video/mp4', 'video/avi', 'video/quicktime', 'video/x-ms-wmv', 'video/x-flv', 'video/webm', 'video/x-matroska', 'video/mp4', 'video/3gpp', 'video/ogg'],
        'max_size': 100 * 1024 * 1024,  # 100MB
        'icon': 'fas fa-video'
    },
    'audio': {
        'name': 'Audio',
        'description': 'Audio files and sound recordings',
        'extensions': ['.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma', '.m4a', '.opus', '.aiff', '.au'],
        'mime_types': ['audio/mpeg', 'audio/wav', 'audio/flac', 'audio/aac', 'audio/ogg', 'audio/x-ms-wma', 'audio/mp4', 'audio/opus', 'audio/aiff', 'audio/basic'],
        'max_size': 50 * 1024 * 1024,  # 50MB
        'icon': 'fas fa-music'
    },
    'documents': {
        'name': 'Documents & PDFs',
        'description': 'Text documents, PDFs, and office files',
        'extensions': ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt', '.rtf', '.odt', '.ods', '.odp'],
        'mime_types': ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'application/vnd.ms-powerpoint', 'application/vnd.openxmlformats-officedocument.presentationml.presentation', 'text/plain', 'application/rtf', 'application/vnd.oasis.opendocument.text', 'application/vnd.oasis.opendocument.spreadsheet', 'application/vnd.oasis.opendocument.presentation'],
        'max_size': 25 * 1024 * 1024,  # 25MB
        'icon': 'fas fa-file-alt'
    },
    'archives': {
        'name': 'Archives',
        'description': 'Compressed files and archives',
        'extensions': ['.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz'],
        'mime_types': ['application/zip', 'application/x-rar-compressed', 'application/x-7z-compressed', 'application/x-tar', 'application/gzip', 'application/x-bzip2', 'application/x-xz'],
        'max_size': 50 * 1024 * 1024,  # 50MB
        'icon': 'fas fa-file-archive'
    }
}

def get_file_category(filename: str, mime_type: Optional[str] = None) -> Tuple[str, Dict]:
    """
    Determine the category of a file based on its extension and MIME type.
    
    Args:
        filename: The name of the file
        mime_type: Optional MIME type of the file
        
    Returns:
        Tuple of (category_key, category_info)
    """
    # Get file extension
    _, ext = os.path.splitext(filename.lower())
    
    # If MIME type is provided, try to match it first
    if mime_type:
        for category_key, category_info in FILE_CATEGORIES.items():
            if mime_type.lower() in [mt.lower() for mt in category_info['mime_types']]:
                return category_key, category_info
    
    # Fall back to extension matching
    for category_key, category_info in FILE_CATEGORIES.items():
        if ext in category_info['extensions']:
            return category_key, category_info
    
    # Default to documents if no match found
    return 'documents', FILE_CATEGORIES['documents']

def is_file_type_allowed(filename: str, allowed_categories: List[str], mime_type: Optional[str] = None) -> bool:
    """
    Check if a file type is allowed based on the specified categories.
    
    Args:
        filename: The name of the file
        allowed_categories: List of allowed category keys
        mime_type: Optional MIME type of the file
        
    Returns:
        True if file type is allowed, False otherwise
    """
    if not allowed_categories:
        return True
    
    category_key, _ = get_file_category(filename, mime_type)
    return category_key in allowed_categories

def get_file_size_limit(category_key: str) -> int:
    """
    Get the maximum file size limit for a category.
    
    Args:
        category_key: The category key
        
    Returns:
        Maximum file size in bytes
    """
    return FILE_CATEGORIES.get(category_key, {}).get('max_size', 10 * 1024 * 1024)

def format_file_size(size_bytes: int) -> str:
    """
    Format file size in bytes to human readable format.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted size string (e.g., "1.5 MB")
    """
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"

def get_media_upload_config(categories: List[str] = None, max_files_per_category: int = 5) -> Dict:
    """
    Generate media upload configuration for chatbot questions.
    
    Args:
        categories: List of allowed categories (None for all)
        max_files_per_category: Maximum files allowed per category
        
    Returns:
        Configuration dictionary for media upload questions
    """
    if categories is None:
        categories = list(FILE_CATEGORIES.keys())
    
    config = {
        'enabled_categories': categories,
        'max_files_per_category': max_files_per_category,
        'categories': {}
    }
    
    for category_key in categories:
        if category_key in FILE_CATEGORIES:
            category_info = FILE_CATEGORIES[category_key].copy()
            config['categories'][category_key] = {
                'name': category_info['name'],
                'description': category_info['description'],
                'extensions': category_info['extensions'],
                'mime_types': category_info['mime_types'],
                'max_size': category_info['max_size'],
                'max_size_formatted': format_file_size(category_info['max_size']),
                'icon': category_info['icon'],
                'max_files': max_files_per_category
            }
    
    return config

def validate_uploaded_file(filename: str, file_size: int, allowed_categories: List[str], mime_type: Optional[str] = None) -> Dict:
    """
    Validate an uploaded file against the allowed categories and size limits.
    
    Args:
        filename: The name of the file
        file_size: Size of the file in bytes
        allowed_categories: List of allowed category keys
        mime_type: Optional MIME type of the file
        
    Returns:
        Dictionary with validation results
    """
    result = {
        'valid': True,
        'category': None,
        'errors': []
    }
    
    # Check if file type is allowed
    if not is_file_type_allowed(filename, allowed_categories, mime_type):
        result['valid'] = False
        result['errors'].append(f"File type not allowed. Allowed types: {', '.join(allowed_categories)}")
        return result
    
    # Get file category
    category_key, category_info = get_file_category(filename, mime_type)
    result['category'] = category_key
    
    # Check file size
    max_size = category_info['max_size']
    if file_size > max_size:
        result['valid'] = False
        result['errors'].append(f"File too large. Maximum size for {category_info['name']}: {format_file_size(max_size)}")
    
    return result

def get_category_display_info(category_key: str) -> Dict:
    """
    Get display information for a file category.
    
    Args:
        category_key: The category key
        
    Returns:
        Dictionary with display information
    """
    return FILE_CATEGORIES.get(category_key, {})

def get_all_categories() -> Dict:
    """
    Get all available file categories.
    
    Returns:
        Dictionary of all categories
    """
    return FILE_CATEGORIES.copy()

def validate_uploaded_file_comprehensive(file, allowed_extensions=None, max_size=None, allowed_categories=None):
    """
    Comprehensive file validation with detailed error reporting.
    
    Args:
        file: Flask file object
        allowed_extensions: List of allowed file extensions (e.g., ['jpg', 'png'])
        max_size: Maximum file size in bytes
        allowed_categories: List of allowed file categories
        
    Returns:
        Tuple of (is_valid, error_message, file_info)
    """
    try:
        # Check if file exists
        if not file or not hasattr(file, 'filename'):
            return False, "No file provided", None
        
        if not file.filename:
            return False, "Empty filename", None
        
        # Get file info
        filename = file.filename
        file_size = getattr(file, 'content_length', 0)
        
        # Check file size
        if max_size and file_size > max_size:
            return False, f"File too large. Maximum size: {format_file_size(max_size)}", None
        
        # Check extension
        if allowed_extensions:
            ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
            if ext not in [e.lower().lstrip('.') for e in allowed_extensions]:
                return False, f"Invalid file type. Allowed extensions: {', '.join(allowed_extensions)}", None
        
        # Check category if specified
        if allowed_categories:
            category_key, category_info = get_file_category(filename)
            if category_key not in allowed_categories:
                return False, f"File type not allowed. Allowed categories: {', '.join(allowed_categories)}", None
            
            # Check category-specific size limit
            if file_size > category_info['max_size']:
                return False, f"File too large for {category_info['name']}. Maximum size: {format_file_size(category_info['max_size'])}", None
        
        # Security checks
        if not is_filename_safe(filename):
            return False, "Filename contains invalid characters", None
        
        # Get file info
        category_key, category_info = get_file_category(filename)
        file_info = {
            'filename': filename,
            'size': file_size,
            'size_formatted': format_file_size(file_size),
            'category': category_key,
            'category_info': category_info
        }
        
        return True, "File is valid", file_info
        
    except Exception as e:
        return False, f"File validation error: {str(e)}", None

def is_filename_safe(filename):
    """
    Check if filename is safe (no path traversal, special characters, etc.)
    
    Args:
        filename: The filename to check
        
    Returns:
        True if filename is safe, False otherwise
    """
    import re
    
    # Check for path traversal attempts
    if '..' in filename or '/' in filename or '\\' in filename:
        return False
    
    # Check for dangerous characters
    dangerous_chars = ['<', '>', ':', '"', '|', '?', '*']
    if any(char in filename for char in dangerous_chars):
        return False
    
    # Check filename length
    if len(filename) > 255:
        return False
    
    # Check for empty or only whitespace
    if not filename.strip():
        return False
    
    return True

def sanitize_filename(filename):
    """
    Sanitize filename to make it safe for storage.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    import re
    import uuid
    
    # Remove path components
    filename = os.path.basename(filename)
    
    # Remove dangerous characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Remove multiple underscores
    filename = re.sub(r'_+', '_', filename)
    
    # Remove leading/trailing underscores and dots
    filename = filename.strip('_.')
    
    # Ensure filename is not empty
    if not filename:
        filename = f"file_{uuid.uuid4().hex[:8]}"
    
    # Truncate if too long
    if len(filename) > 200:
        name, ext = os.path.splitext(filename)
        filename = name[:200-len(ext)] + ext
    
    return filename



