#!/usr/bin/env python3
"""
Custom template filters for Flask
"""

from flask import current_app
from utils.geocoding import parse_location

def register_template_filters(app):
    """Register custom template filters"""
    
    @app.template_filter('format_location_cached')
    def format_location_cached(location_string):
        """
        Format location using cached data for fast performance
        
        Args:
            location_string: Raw location string (URL, coordinates, or plain text)
            
        Returns:
            Formatted location string like "Dubai, UAE"
        """
        if not location_string:
            return "Location not specified"
        
        # Import here to avoid circular imports
        from utils.location_cache import get_formatted_location
        
        try:
            formatted = get_formatted_location(location_string)
            return formatted if formatted else location_string[:50] + ("..." if len(location_string) > 50 else "")
        except Exception as e:
            print(f"Location formatting error: {e}")
            return location_string[:50] + ("..." if len(location_string) > 50 else "")
    
    @app.template_filter('format_location')
    def format_location(location_string):
        """
        Format location string to show city, country format
        
        Args:
            location_string: Raw location string (URL, coordinates, or plain text)
            
        Returns:
            Formatted location string like "Dubai, UAE"
        """
        if not location_string:
            return 'Location not specified'
        
        try:
            result = parse_location(location_string)
            return result.get('formatted', location_string)
        except Exception as e:
            # Fallback to original location if geocoding fails
            print(f"Location formatting failed: {e}")
            return location_string
    
    @app.template_filter('extract_location_details')
    def extract_location_details(location_string):
        """
        Extract detailed location information
        
        Args:
            location_string: Raw location string
            
        Returns:
            Dictionary with location details
        """
        if not location_string:
            return {'formatted': 'Location not specified', 'coordinates': None}
        
        try:
            return parse_location(location_string)
        except Exception as e:
            print(f"Location parsing failed: {e}")
            return {'formatted': location_string, 'coordinates': None}
