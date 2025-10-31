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
    Extract latitude and longitude from map URLs (Google Maps, Apple Maps, Bing Maps, etc.)
    Supports short URLs by resolving them first.
    
    Args:
        url: Map URL string (supports multiple map services)
        
    Returns:
        Tuple of (latitude, longitude) or None if not found
    """
    if not url or not isinstance(url, str):
        return None
    
    # URL decode in case it's encoded
    try:
        from urllib.parse import unquote
        url = unquote(url)
    except:
        pass
    
    url_lower = url.lower()
    
    # Handle Google Maps short URLs (maps.app.goo.gl, goo.gl/maps)
    if 'maps.app.goo.gl' in url_lower or ('goo.gl' in url_lower and '/maps' in url_lower):
        print(f"DEBUG: Detected Google Maps short URL: {url}")
        # Try to resolve the short URL by following redirects
        try:
            resolved_url = resolve_short_url(url)
            if resolved_url and resolved_url != url:
                print(f"DEBUG: Resolved short URL to: {resolved_url[:200]}")
                # Recursively try to extract coordinates from resolved URL
                return extract_coordinates_from_url(resolved_url)
        except Exception as e:
            print(f"DEBUG: Failed to resolve short URL: {e}")
        # If resolution fails, try to extract from original URL (might have embedded data)
        # Continue with normal processing below
    
    # ===== GOOGLE MAPS =====
    # Examples:
    # https://www.google.com/maps/place/.../@25.2618616,55.3254198,...
    # https://maps.google.com/?q=25.2618616,55.3254198
    # https://www.google.com/maps/@25.2618616,55.3254198,15z
    # https://www.google.com/maps/search/?api=1&query=25.2618616,55.3254198
    if 'maps.google.com' in url_lower or 'google.com/maps' in url_lower:
        patterns = [
            r'@(-?\d+\.?\d*),(-?\d+\.?\d*)',  # @lat,lng format (most common) - must be first
            r'!3d(-?\d+\.?\d*)!4d(-?\d+\.?\d*)',  # !3dlat!4dlng format
            r'[?&]query=(-?\d+\.?\d*),(-?\d+\.?\d*)',  # ?query=lat,lng format (new Google Maps)
            r'[?&]q=(-?\d+\.?\d*),(-?\d+\.?\d*)',  # ?q=lat,lng or &q=lat,lng format
            r'[?&]ll=(-?\d+\.?\d*),(-?\d+\.?\d*)',  # ?ll=lat,lng format
            r'[?&]center=(-?\d+\.?\d*),(-?\d+\.?\d*)',  # ?center=lat,lng format
            r'@(-?\d+\.?\d*),(-?\d+\.?\d*),',  # @lat,lng, format (with trailing comma)
            r'/(\d+\.?\d+),(\d+\.?\d+)',  # /lat.lng format (like /maps/25.2618,55.3254)
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url, re.IGNORECASE)
            if match:
                try:
                    lat, lng = float(match.group(1)), float(match.group(2))
                    # Validate coordinates (latitude: -90 to 90, longitude: -180 to 180)
                    if -90 <= lat <= 90 and -180 <= lng <= 180:
                        print(f"DEBUG: Extracted coordinates from Google Maps URL: {lat}, {lng}")
                        return (lat, lng)
                except (ValueError, IndexError) as e:
                    print(f"DEBUG: Failed to parse coordinates from Google Maps URL: {e}")
                    continue
    
    # ===== APPLE MAPS =====
    # Examples:
    # https://maps.apple.com/?ll=25.2618616,55.3254198
    # https://maps.apple.com/?q=25.2618616,55.3254198
    # https://maps.apple.com/?ll=25.2618616,55.3254198&t=m
    elif 'maps.apple.com' in url_lower:
        patterns = [
            r'[?&]ll=(-?\d+\.?\d*),(-?\d+\.?\d*)',  # ?ll=lat,lng format
            r'[?&]q=(-?\d+\.?\d*),(-?\d+\.?\d*)',  # ?q=lat,lng format
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url, re.IGNORECASE)
            if match:
                try:
                    lat, lng = float(match.group(1)), float(match.group(2))
                    if -90 <= lat <= 90 and -180 <= lng <= 180:
                        return (lat, lng)
                except (ValueError, IndexError):
                    continue
    
    # ===== BING MAPS =====
    # Examples:
    # https://www.bing.com/maps?cp=25.2618616~55.3254198
    # https://www.bing.com/maps?where1=25.2618616,55.3254198
    elif 'bing.com/maps' in url_lower:
        patterns = [
            r'[?&]cp=(-?\d+\.?\d*)~(-?\d+\.?\d*)',  # ?cp=lat~lng format
            r'[?&]where1=(-?\d+\.?\d*),(-?\d+\.?\d*)',  # ?where1=lat,lng format
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url, re.IGNORECASE)
            if match:
                try:
                    lat, lng = float(match.group(1)), float(match.group(2))
                    if -90 <= lat <= 90 and -180 <= lng <= 180:
                        return (lat, lng)
                except (ValueError, IndexError):
                    continue
    
    # ===== OPENSTREETMAP / OSM =====
    # Examples:
    # https://www.openstreetmap.org/?mlat=25.2618616&mlon=55.3254198
    # https://www.openstreetmap.org/#map=15/25.2618616/55.3254198
    elif 'openstreetmap.org' in url_lower:
        patterns = [
            r'[?&]mlat=(-?\d+\.?\d*)&mlon=(-?\d+\.?\d*)',  # ?mlat=lat&mlon=lng format
            r'#map=\d+/(-?\d+\.?\d*)/(-?\d+\.?\d*)',  # #map=zoom/lat/lng format
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url, re.IGNORECASE)
            if match:
                try:
                    lat, lng = float(match.group(1)), float(match.group(2))
                    if -90 <= lat <= 90 and -180 <= lng <= 180:
                        return (lat, lng)
                except (ValueError, IndexError):
                    continue
    
    # ===== MAPS.ME / HERE MAPS =====
    # Examples:
    # https://maps.me/?lat=25.2618616&lon=55.3254198
    elif 'maps.me' in url_lower or 'here.com' in url_lower:
        patterns = [
            r'[?&]lat=(-?\d+\.?\d*)&lon=(-?\d+\.?\d*)',  # ?lat=lat&lon=lng format
            r'[?&]latitude=(-?\d+\.?\d*)&longitude=(-?\d+\.?\d*)',  # ?latitude=lat&longitude=lng format
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url, re.IGNORECASE)
            if match:
                try:
                    lat, lng = float(match.group(1)), float(match.group(2))
                    if -90 <= lat <= 90 and -180 <= lng <= 180:
                        return (lat, lng)
                except (ValueError, IndexError):
                    continue
    
    # ===== GENERIC PATTERNS (fallback for other map services) =====
    # Try common coordinate patterns that might work for other services
    generic_patterns = [
        r'[?&]lat=(-?\d+\.?\d*)&lng=(-?\d+\.?\d*)',  # ?lat=lat&lng=lng
        r'[?&]lat=(-?\d+\.?\d*)&lon=(-?\d+\.?\d*)',  # ?lat=lat&lon=lng
        r'[?&]latitude=(-?\d+\.?\d*)&longitude=(-?\d+\.?\d*)',  # ?latitude=lat&longitude=lng
        r'[?&]coordinates=(-?\d+\.?\d*),(-?\d+\.?\d*)',  # ?coordinates=lat,lng
    ]
    
    for pattern in generic_patterns:
        match = re.search(pattern, url, re.IGNORECASE)
        if match:
            try:
                lat, lng = float(match.group(1)), float(match.group(2))
                if -90 <= lat <= 90 and -180 <= lng <= 180:
                    return (lat, lng)
            except (ValueError, IndexError):
                continue
    
    # ===== LAST RESORT: Try to find any two decimal numbers that look like coordinates =====
    # This is a fallback for URLs that don't match standard patterns
    # Look for patterns like: number.number,number.number anywhere in URL
    coord_pattern = r'(\d{1,2}\.\d+),(\d{1,3}\.\d+)'  # Match lat (1-2 digits),lng (1-3 digits) with decimals
    matches = list(re.finditer(coord_pattern, url))
    if matches:
        # Try each match to see if it looks like valid coordinates
        for match in matches:
            try:
                lat = float(match.group(1))
                lng = float(match.group(2))
                # Validate coordinates (latitude: -90 to 90, longitude: -180 to 180)
                if -90 <= lat <= 90 and -180 <= lng <= 180:
                    # Additional validation: if it's in a reasonable range, it's likely coordinates
                    print(f"DEBUG: Fallback pattern matched coordinates: {lat}, {lng}")
                    return (lat, lng)
            except (ValueError, IndexError):
                continue
    
    return None

def resolve_short_url(url: str, max_redirects: int = 5) -> Optional[str]:
    """
    Resolve a short URL by following redirects
    
    Args:
        url: Short URL to resolve
        max_redirects: Maximum number of redirects to follow
        
    Returns:
        Resolved URL or None if failed
    """
    try:
        current_url = url
        redirects = 0
        
        while redirects < max_redirects:
            response = requests.get(
                current_url,
                allow_redirects=False,
                timeout=5,
                headers={'User-Agent': 'BankU-App/1.0'}
            )
            
            # Check if there's a redirect
            if response.status_code in (301, 302, 303, 307, 308):
                location = response.headers.get('Location')
                if location:
                    if location.startswith('http'):
                        current_url = location
                    else:
                        # Relative URL, construct absolute
                        from urllib.parse import urljoin
                        current_url = urljoin(current_url, location)
                    redirects += 1
                    continue
            
            # If we got a final response (not redirect), return the current URL
            if response.status_code == 200:
                return current_url
            
            # If not a redirect and not 200, break
            break
        
        return current_url if redirects > 0 else url
    except Exception as e:
        print(f"DEBUG: Error resolving short URL {url}: {e}")
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
        print(f"DEBUG: Extracted coordinates: {lat}, {lng} from location: {location[:100]}")
        geocode_result = reverse_geocode(lat, lng)
        
        if geocode_result:
            print(f"DEBUG: Reverse geocoded to: {geocode_result.get('formatted')}")
            return {
                'formatted': geocode_result['formatted'],
                'city': geocode_result['city'],
                'country': geocode_result['country'],
                'coordinates': geocode_result['coordinates'],
                'original_url': location if location.startswith('http') else None
            }
        else:
            print(f"DEBUG: Reverse geocoding failed, using coordinates: {lat:.4f}, {lng:.4f}")
            # Fallback to coordinates if geocoding fails
            return {
                'formatted': f"{lat:.4f}, {lng:.4f}",
                'coordinates': f"{lat:.6f}, {lng:.6f}",
                'original_url': location if location.startswith('http') else None
            }
    else:
        print(f"DEBUG: Could not extract coordinates from URL: {location[:100]}")
    
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
