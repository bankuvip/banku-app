#!/usr/bin/env python3
"""
Template Filters for File Path Handling
Handles both old and new file structure paths
"""

def get_file_url(filename):
    """
    Generate proper URL for file, handling both old and new file structures
    
    Args:
        filename: File path from database (could be old or new format)
    
    Returns:
        str: Proper URL for the file
    """
    if not filename:
        return ""
    
    # Normalize path separators (convert backslashes to forward slashes)
    filename = filename.replace('\\', '/')
    
    # If it's already a full path starting with uploads/, use it as is
    if filename.startswith('uploads/'):
        return f"/static/{filename}"
    
    # If it's an old format filename, prepend uploads/
    return f"/static/uploads/{filename}"

def is_old_format(filename):
    """
    Check if filename is in old format (question_id_filename_timestamp_uuid.ext)
    
    Args:
        filename: File path to check
    
    Returns:
        bool: True if old format, False if new format
    """
    if not filename:
        return False
    
    # Old format: question_id_filename_timestamp_uuid.ext
    # New format: uploads/users/user_id/.../user_id_item_id_timestamp_uuid.ext
    return not filename.startswith('uploads/')

def get_file_display_name(filename):
    """
    Get display name for file (without path)
    
    Args:
        filename: Full file path
    
    Returns:
        str: Just the filename without path
    """
    if not filename:
        return ""
    
    return filename.split('/')[-1] if '/' in filename else filename

def register_template_filters(app):
    """Register all template filters with Flask app"""
    from markupsafe import Markup
    import re
    
    @app.template_filter('file_url')
    def file_url_filter(filename):
        """Template filter to get proper file URL"""
        return get_file_url(filename)
    
    @app.template_filter('is_old_file_format')
    def is_old_file_format_filter(filename):
        """Template filter to check if file is in old format"""
        return is_old_format(filename)
    
    @app.template_filter('file_display_name')
    def file_display_name_filter(filename):
        """Template filter to get file display name"""
        return get_file_display_name(filename)
    
    @app.template_filter('highlight')
    def highlight_filter(text, search_term):
        """Highlight search term in text"""
        if not search_term or not text:
            return text
        
        search_term = str(search_term).strip()
        if not search_term:
            return text
        
        # Escape HTML in text first
        from markupsafe import escape
        text_str = str(text)
        escaped_text = escape(text_str)
        
        # Case-insensitive replacement with highlighting
        try:
            pattern = re.compile(re.escape(search_term), re.IGNORECASE)
            highlighted = pattern.sub(
                lambda m: f'<mark style="background-color: #ffeb3b; padding: 2px 4px; border-radius: 3px;">{m.group()}</mark>',
                escaped_text
            )
            return Markup(highlighted)
        except Exception:
            return text