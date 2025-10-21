"""
Location caching system for fast location lookups without API calls
"""

import requests
import time
from datetime import datetime
from models import db, LocationCache
import re

def get_cached_location(location_string):
    """
    Get location data from cache, return None if not found
    """
    if not location_string or not location_string.strip():
        return None
    
    # Normalize the location string
    normalized_location = location_string.strip()
    
    # Try to find in cache
    cached = LocationCache.query.filter_by(location_string=normalized_location).first()
    
    if cached:
        # Update last_used timestamp
        cached.last_used = datetime.utcnow()
        db.session.commit()
        return cached
    
    return None

def cache_location(location_string, city=None, country=None, formatted_location=None, lat=None, lng=None):
    """
    Cache location data in the database
    """
    if not location_string or not location_string.strip():
        return None
    
    normalized_location = location_string.strip()
    
    # Check if already exists
    existing = LocationCache.query.filter_by(location_string=normalized_location).first()
    if existing:
        # Update existing cache entry
        existing.city = city
        existing.country = country
        existing.formatted_location = formatted_location
        existing.coordinates_lat = lat
        existing.coordinates_lng = lng
        existing.last_used = datetime.utcnow()
        db.session.commit()
        return existing
    
    # Create new cache entry
    cached_location = LocationCache(
        location_string=normalized_location,
        city=city,
        country=country,
        formatted_location=formatted_location,
        coordinates_lat=lat,
        coordinates_lng=lng
    )
    
    db.session.add(cached_location)
    db.session.commit()
    return cached_location

def reverse_geocode_coordinates(lat, lng):
    """
    Perform reverse geocoding for coordinates using Nominatim API
    """
    try:
        # Use Nominatim API for reverse geocoding
        url = "https://nominatim.openstreetmap.org/reverse"
        params = {
            'lat': lat,
            'lon': lng,
            'format': 'json',
            'accept-language': 'en',
            'addressdetails': 1
        }
        
        headers = {
            'User-Agent': 'BankU-Location-Service/1.0'
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            address = data.get('address', {})
            
            # Extract city and country
            city = (address.get('city') or 
                   address.get('town') or 
                   address.get('village') or 
                   address.get('hamlet') or 
                   address.get('suburb'))
            
            country = address.get('country')
            
            # Special handling for Dubai
            if city and 'dubai' in city.lower():
                city = 'Dubai'
                country = 'UAE'
            
            if city and country:
                formatted_location = f"{city}, {country}"
                return city, country, formatted_location
        
        return None, None, None
        
    except Exception as e:
        print(f"Reverse geocoding error: {e}")
        return None, None, None

def parse_and_cache_location(location_string):
    """
    Parse location string and cache the result
    Returns cached location data or None
    """
    if not location_string or not location_string.strip():
        return None
    
    # First check cache
    cached = get_cached_location(location_string)
    if cached:
        return cached
    
    location_str = location_string.strip()
    
    # Handle coordinates (lat, lng format)
    coord_match = re.match(r'^(-?\d+\.?\d*),\s*(-?\d+\.?\d*)$', location_str)
    if coord_match:
        try:
            lat = float(coord_match.group(1))
            lng = float(coord_match.group(2))
            
            # Perform reverse geocoding
            city, country, formatted_location = reverse_geocode_coordinates(lat, lng)
            
            if city and country:
                # Cache the result
                return cache_location(location_str, city, country, formatted_location, lat, lng)
            else:
                # Cache with coordinates only
                return cache_location(location_str, None, None, f"{lat:.4f}, {lng:.4f}", lat, lng)
                
        except ValueError:
            pass
    
    # Handle URLs
    if location_str.startswith(('http://', 'https://', 'www.')):
        # Extract coordinates from common map URLs
        if 'maps.google.com' in location_str or 'google.com/maps' in location_str:
            # Try to extract coordinates from Google Maps URL
            coord_pattern = r'@(-?\d+\.?\d*),(-?\d+\.?\d*)'
            match = re.search(coord_pattern, location_str)
            if match:
                try:
                    lat = float(match.group(1))
                    lng = float(match.group(2))
                    
                    city, country, formatted_location = reverse_geocode_coordinates(lat, lng)
                    if city and country:
                        return cache_location(location_str, city, country, formatted_location, lat, lng)
                    else:
                        return cache_location(location_str, None, None, "Google Maps Location", lat, lng)
                except ValueError:
                    pass
        
        # Cache generic URL location
        return cache_location(location_str, None, None, "Map Location", None, None)
    
    # Handle text locations (e.g., "Dubai, UAE")
    if ',' in location_str:
        parts = [p.strip() for p in location_str.split(',')]
        if len(parts) >= 2:
            city = parts[0]
            country = parts[-1]
            formatted_location = f"{city}, {country}"
            return cache_location(location_str, city, country, formatted_location, None, None)
    
    # Cache as-is for other text
    return cache_location(location_str, None, None, location_str[:50], None, None)

def get_formatted_location(location_string):
    """
    Get formatted location string from cache or parse and cache it
    Returns formatted location string or None
    """
    cached = parse_and_cache_location(location_string)
    if cached and cached.formatted_location:
        return cached.formatted_location
    return None

def cleanup_old_cache_entries(days_old=30):
    """
    Clean up old cache entries that haven't been used recently
    """
    from datetime import timedelta
    cutoff_date = datetime.utcnow() - timedelta(days=days_old)
    
    old_entries = LocationCache.query.filter(LocationCache.last_used < cutoff_date).all()
    
    for entry in old_entries:
        db.session.delete(entry)
    
    db.session.commit()
    return len(old_entries)





