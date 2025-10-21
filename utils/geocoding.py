#!/usr/bin/env python3
"""
Geocoding utilities for extracting city and country from coordinates
"""

import requests
import json
import re
from typing import Dict, Optional, Tuple

def extract_coordinates_from_url(url: str) -> Optional[Tuple[float, float]]:
    """
    Extract latitude and longitude from Google Maps URL
    
    Args:
        url: Google Maps URL string
        
    Returns:
        Tuple of (latitude, longitude) or None if not found
    """
    if not url or not isinstance(url, str):
        return None
    
    # Pattern to match coordinates in Google Maps URLs
    # Examples: @25.2618616,55.3254198 or !3d25.2651264!4d55.3151191
    patterns = [
        r'@(-?\d+\.?\d*),(-?\d+\.?\d*)',  # @lat,lng format
        r'!3d(-?\d+\.?\d*)!4d(-?\d+\.?\d*)',  # !3dlat!4dlng format
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            try:
                if pattern.startswith('@'):
                    lat, lng = float(match.group(1)), float(match.group(2))
                else:  # !3d!4d format
                    lat, lng = float(match.group(1)), float(match.group(2))
                return (lat, lng)
            except (ValueError, IndexError):
                continue
    
    return None

def reverse_geocode(latitude: float, longitude: float) -> Optional[Dict[str, str]]:
    """
    Reverse geocode coordinates to get city and country information
    
    Args:
        latitude: Latitude coordinate
        longitude: Longitude coordinate
        
    Returns:
        Dictionary with 'city', 'country', 'formatted' keys or None if failed
    """
    try:
        # Using Nominatim (OpenStreetMap) - free and reliable
        url = "https://nominatim.openstreetmap.org/reverse"
        params = {
            'lat': latitude,
            'lon': longitude,
            'format': 'json',
            'addressdetails': 1,
            'zoom': 10,  # City level detail
            'accept-language': 'en'  # Prefer English names
        }
        
        headers = {
            'User-Agent': 'BankU-App/1.0'  # Required by Nominatim
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=5)
        response.raise_for_status()
        
        data = response.json()
        
        if not data or 'address' not in data:
            return None
        
        address = data['address']
        
        # Extract city name (try different fields)
        city = (
            address.get('city') or 
            address.get('town') or 
            address.get('village') or 
            address.get('municipality') or
            address.get('suburb') or
            'Unknown City'
        )
        
        # If city is in Arabic or non-Latin script, try to get English name from display_name
        if data.get('display_name'):
            display_parts = data['display_name'].split(', ')
            for part in display_parts:
                # Look for English city names (contains Latin characters)
                if re.match(r'^[A-Za-z\s]+$', part.strip()) and len(part.strip()) > 2:
                    if any(keyword in part.lower() for keyword in ['city', 'town', 'district', 'area']):
                        city = part.strip()
                        break
        
        # Extract country
        country = address.get('country', 'Unknown Country')
        country_code = address.get('country_code', '').upper()
        
        # Create formatted location string
        if country_code == 'AE':
            country = 'UAE'
            # Special handling for Dubai coordinates
            if 25.0 <= latitude <= 25.5 and 55.0 <= longitude <= 55.5:
                city = 'Dubai'
        elif country_code == 'US':
            country = 'USA'
        elif country_code == 'GB':
            country = 'UK'
        
        formatted = f"{city}, {country}"
        
        return {
            'city': city,
            'country': country,
            'country_code': country_code,
            'formatted': formatted,
            'coordinates': f"{latitude:.6f}, {longitude:.6f}"
        }
        
    except Exception as e:
        print(f"Reverse geocoding failed: {e}")
        return None

def parse_location(location: str) -> Dict[str, str]:
    """
    Parse location string to extract and format city/country information
    
    Args:
        location: Location string (URL, coordinates, or plain text)
        
    Returns:
        Dictionary with location information
    """
    if not location:
        return {'formatted': 'Location not specified', 'coordinates': None}
    
    # Check if it's a raw coordinate string (lat,lng format)
    # Support formats like: 25.2685839,55.3192154 or 25.2685839, 55.3192154
    coordinate_pattern = r'^-?\d+\.?\d*\s*,\s*-?\d+\.?\d*$'
    if re.match(coordinate_pattern, location.strip()):
        try:
            lat, lng = map(float, location.split(','))
            geocode_result = reverse_geocode(lat, lng)
            
            if geocode_result:
                return {
                    'formatted': geocode_result['formatted'],
                    'city': geocode_result['city'],
                    'country': geocode_result['country'],
                    'coordinates': geocode_result['coordinates'],
                    'original_url': None
                }
            else:
                # Fallback to coordinates if geocoding fails
                return {
                    'formatted': f"{lat:.4f}, {lng:.4f}",
                    'coordinates': f"{lat:.6f}, {lng:.6f}",
                    'original_url': None
                }
        except ValueError:
            # If parsing fails, continue with normal processing
            pass
    
    # If it's already a simple city, country format, return as is
    if ',' in location and not location.startswith('http') and not re.search(r'\d+\.\d+', location):
        return {'formatted': location, 'coordinates': None}
    
    # Extract coordinates from URL
    coordinates = extract_coordinates_from_url(location)
    
    if coordinates:
        lat, lng = coordinates
        geocode_result = reverse_geocode(lat, lng)
        
        if geocode_result:
            return {
                'formatted': geocode_result['formatted'],
                'city': geocode_result['city'],
                'country': geocode_result['country'],
                'coordinates': geocode_result['coordinates'],
                'original_url': location if location.startswith('http') else None
            }
        else:
            # Fallback to coordinates if geocoding fails
            return {
                'formatted': f"{lat:.4f}, {lng:.4f}",
                'coordinates': f"{lat:.6f}, {lng:.6f}",
                'original_url': location if location.startswith('http') else None
            }
    
    # If no coordinates found, return original location
    return {'formatted': location, 'coordinates': None}

# Test function
def test_geocoding():
    """Test the geocoding functionality"""
    test_cases = [
        "https://www.google.com/maps/place/Day+To+Day+-+Union/@25.2618616,55.3254198,3163m/data=!3m1!1e3!4m6!3m5!1s0x3e5f5ccb45eb1411:0xbd43cd2bd77d2486!8m2!3d25.2651264!4d55.3151191!16s%2Fg%2F11b67xbl3t?entry=ttu&g_ep=EgoyMDI1MTAwMS4wIKXMDSoASAFQAw%3D%3D",
        "25.2685839,55.3192154",
        "Dubai, UAE"
    ]
    
    print("Testing geocoding...")
    for test_input in test_cases:
        result = parse_location(test_input)
        print(f"Input: {test_input}")
        print(f"Result: {result}")
        print()
    
    return result

if __name__ == "__main__":
    test_geocoding()
