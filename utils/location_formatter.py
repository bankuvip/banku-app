"""
Simple location formatter without external API calls
Formats raw location data into user-friendly display
"""

import re

def format_location_simple(location_string):
    """
    Format location string into user-friendly display without external API calls
    """
    if not location_string:
        return "Location not specified"
    
    # Clean up the string
    location = location_string.strip()
    
    # Handle coordinates (lat, lng format)
    coord_pattern = r'^(-?\d+\.?\d*),\s*(-?\d+\.?\d*)$'
    coord_match = re.match(coord_pattern, location)
    
    if coord_match:
        lat, lng = coord_match.groups()
        try:
            lat_num = float(lat)
            lng_num = float(lng)
            
            # Simple coordinate formatting
            lat_str = f"{abs(lat_num):.4f}{'N' if lat_num >= 0 else 'S'}"
            lng_str = f"{abs(lng_num):.4f}{'E' if lng_num >= 0 else 'W'}"
            
            return f"{lat_str}, {lng_str}"
        except ValueError:
            pass
    
    # Handle URLs
    if location.startswith(('http://', 'https://', 'www.')):
        # Extract domain or location from URL
        if 'maps.google.com' in location or 'google.com/maps' in location:
            return "Google Maps Location"
        elif 'maps.apple.com' in location:
            return "Apple Maps Location"
        elif 'bing.com/maps' in location:
            return "Bing Maps Location"
        elif 'openstreetmap.org' in location:
            return "OpenStreetMap Location"
        else:
            # Extract domain name
            try:
                if location.startswith('www.'):
                    domain = location.split('www.')[1].split('/')[0]
                else:
                    domain = location.split('://')[1].split('/')[0]
                # Capitalize only first letter of domain
                domain_formatted = domain.capitalize()
                return f"{domain_formatted} Location"
            except:
                return "Map Location"
    
    # Handle common location patterns
    if ',' in location:
        parts = location.split(',')
        if len(parts) == 2:
            city, country = parts[0].strip(), parts[1].strip()
            return f"{city}, {country}"
        elif len(parts) >= 3:
            # City, State/Region, Country format
            city = parts[0].strip()
            country = parts[-1].strip()
            return f"{city}, {country}"
    
    # Handle simple city names or addresses
    if len(location) > 50:
        return location[:47] + "..."
    
    return location

def format_location_with_link(location_string):
    """
    Format location with clickable link if it's a URL
    """
    if not location_string:
        return "Location not specified", None
    
    formatted = format_location_simple(location_string)
    
    # Check if original was a URL
    if location_string.startswith(('http://', 'https://')):
        return formatted, location_string
    elif location_string.startswith('www.'):
        return formatted, f"https://{location_string}"
    
    return formatted, None

def is_coordinate_string(location_string):
    """
    Check if location string contains coordinates
    """
    if not location_string:
        return False
    
    coord_pattern = r'^-?\d+\.?\d*,\s*-?\d+\.?\d*$'
    return bool(re.match(coord_pattern, location_string.strip()))
