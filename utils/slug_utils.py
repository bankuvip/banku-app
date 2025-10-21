"""
Utility functions for generating URL-friendly slugs
"""
import re
import unicodedata
from models import Profile, Organization

def generate_slug(text, model_class=None, exclude_id=None):
    """
    Generate a URL-friendly slug from text
    
    Args:
        text (str): Text to convert to slug
        model_class: Model class to check for uniqueness (optional)
        exclude_id: ID to exclude from uniqueness check (optional)
    
    Returns:
        str: URL-friendly slug
    """
    if not text:
        return None
    
    # Convert to lowercase and normalize unicode
    text = unicodedata.normalize('NFKD', text.lower())
    
    # Remove special characters and replace spaces with hyphens
    slug = re.sub(r'[^\w\s-]', '', text)
    slug = re.sub(r'[-\s]+', '-', slug)
    
    # Remove leading/trailing hyphens
    slug = slug.strip('-')
    
    # Ensure slug is not empty
    if not slug:
        return None
    
    # Check uniqueness if model_class is provided
    if model_class:
        original_slug = slug
        counter = 1
        
        while True:
            # Check if slug already exists
            if exclude_id:
                existing = model_class.query.filter(
                    model_class.slug == slug,
                    model_class.id != exclude_id
                ).first()
            else:
                existing = model_class.query.filter_by(slug=slug).first()
            
            if not existing:
                break
            
            # Add counter to make it unique
            slug = f"{original_slug}-{counter}"
            counter += 1
            
            # Prevent infinite loop
            if counter > 1000:
                slug = f"{original_slug}-{exclude_id or 'unknown'}"
                break
    
    return slug

def generate_profile_slug(name, user_id, exclude_id=None):
    """
    Generate a unique slug for a profile
    
    Args:
        name (str): Profile name
        user_id (int): User ID (for fallback)
        exclude_id (int): Profile ID to exclude from uniqueness check
    
    Returns:
        str: Unique profile slug
    """
    # Try to generate slug from name
    slug = generate_slug(name, Profile, exclude_id)
    
    # If no valid slug from name, use user ID as fallback
    if not slug:
        slug = f"user-{user_id}"
        # Ensure this fallback is unique too
        slug = generate_slug(slug, Profile, exclude_id)
    
    return slug

def generate_organization_slug(name, exclude_id=None):
    """
    Generate a unique slug for an organization
    
    Args:
        name (str): Organization name
        exclude_id (int): Organization ID to exclude from uniqueness check
    
    Returns:
        str: Unique organization slug
    """
    return generate_slug(name, Organization, exclude_id)
