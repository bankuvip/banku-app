#!/usr/bin/env python3
"""
File cleanup utilities for deleting associated files when items are deleted
"""

import os
import json
from typing import List, Optional
from flask import current_app

def delete_item_files(item) -> dict:
    """
    Delete all files associated with an item
    
    Args:
        item: Item object with files to delete
        
    Returns:
        Dictionary with deletion results
    """
    deleted_files = []
    failed_deletions = []
    upload_folder = current_app.config['UPLOAD_FOLDER']
    
    try:
        # 1. Delete images from images_media field
        if hasattr(item, 'images_media') and item.images_media:
            images = item.images_media
            if isinstance(images, str):
                # Handle JSON string
                try:
                    images = json.loads(images)
                except (json.JSONDecodeError, TypeError):
                    images = []
            
            if isinstance(images, list):
                for image_filename in images:
                    if image_filename:
                        # Handle both old format (just filename) and new format (full path)
                        if image_filename.startswith('uploads/'):
                            # New format: full relative path
                            file_path = os.path.join(current_app.static_folder, image_filename)
                        else:
                            # Old format: just filename
                            file_path = os.path.join(upload_folder, image_filename)
                        
                        if os.path.exists(file_path):
                            try:
                                os.remove(file_path)
                                deleted_files.append(image_filename)
                                print(f"Deleted image file: {image_filename}")
                            except Exception as e:
                                failed_deletions.append(f"{image_filename}: {str(e)}")
                                print(f"Failed to delete image: {image_filename} - {e}")
        
        # 2. Delete photos from photos field (if exists)
        if hasattr(item, 'photos') and item.photos:
            photos = item.photos
            if isinstance(photos, str):
                try:
                    photos = json.loads(photos)
                except (json.JSONDecodeError, TypeError):
                    photos = []
            
            if isinstance(photos, list):
                for photo_filename in photos:
                    if photo_filename:
                        # Handle both old format (just filename) and new format (full path)
                        if photo_filename.startswith('uploads/'):
                            # New format: full relative path
                            file_path = os.path.join(current_app.static_folder, photo_filename)
                        else:
                            # Old format: just filename
                            file_path = os.path.join(upload_folder, photo_filename)
                        
                        if os.path.exists(file_path):
                            try:
                                os.remove(file_path)
                                deleted_files.append(photo_filename)
                                print(f"Deleted photo file: {photo_filename}")
                            except Exception as e:
                                failed_deletions.append(f"{photo_filename}: {str(e)}")
                                print(f"Failed to delete photo: {photo_filename} - {e}")
        
        # 3. Delete files from files field (if exists)
        if hasattr(item, 'files') and item.files:
            files = item.files
            if isinstance(files, str):
                try:
                    files = json.loads(files)
                except (json.JSONDecodeError, TypeError):
                    files = []
            
            if isinstance(files, list):
                for file_filename in files:
                    if file_filename:
                        # Handle both old format (just filename) and new format (full path)
                        if file_filename.startswith('uploads/'):
                            # New format: full relative path
                            file_path = os.path.join(current_app.static_folder, file_filename)
                        else:
                            # Old format: just filename
                            file_path = os.path.join(upload_folder, file_filename)
                        
                        if os.path.exists(file_path):
                            try:
                                os.remove(file_path)
                                deleted_files.append(file_filename)
                                print(f"Deleted file: {file_filename}")
                            except Exception as e:
                                failed_deletions.append(f"{file_filename}: {str(e)}")
                                print(f"Failed to delete file: {file_filename} - {e}")
        
        # 4. Delete media from media field (if exists)
        if hasattr(item, 'media') and item.media:
            media = item.media
            if isinstance(media, str):
                try:
                    media = json.loads(media)
                except (json.JSONDecodeError, TypeError):
                    media = []
            
            if isinstance(media, list):
                for media_filename in media:
                    if media_filename:
                        # Handle both old format (just filename) and new format (full path)
                        if media_filename.startswith('uploads/'):
                            # New format: full relative path
                            file_path = os.path.join(current_app.static_folder, media_filename)
                        else:
                            # Old format: just filename
                            file_path = os.path.join(upload_folder, media_filename)
                        
                        if os.path.exists(file_path):
                            try:
                                os.remove(file_path)
                                deleted_files.append(media_filename)
                                print(f"Deleted media file: {media_filename}")
                            except Exception as e:
                                failed_deletions.append(f"{media_filename}: {str(e)}")
                                print(f"Failed to delete media: {media_filename} - {e}")
        
        return {
            'success': True,
            'deleted_files': deleted_files,
            'failed_deletions': failed_deletions,
            'total_deleted': len(deleted_files),
            'total_failed': len(failed_deletions)
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'deleted_files': deleted_files,
            'failed_deletions': failed_deletions,
            'total_deleted': len(deleted_files),
            'total_failed': len(failed_deletions)
        }

def delete_profile_files(profile) -> dict:
    """
    Delete files associated with a profile (like profile photos)
    
    Args:
        profile: Profile object with files to delete
        
    Returns:
        Dictionary with deletion results
    """
    deleted_files = []
    failed_deletions = []
    upload_folder = current_app.config['UPLOAD_FOLDER']
    
    try:
        # Delete profile photo
        if hasattr(profile, 'photo') and profile.photo:
            # Handle both old format (just filename) and new format (full path)
            if profile.photo.startswith('uploads/'):
                # New format: full relative path
                file_path = os.path.join(current_app.static_folder, profile.photo)
            else:
                # Old format: just filename
                file_path = os.path.join(upload_folder, profile.photo)
            
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    deleted_files.append(profile.photo)
                    print(f"Deleted profile photo: {profile.photo}")
                except Exception as e:
                    failed_deletions.append(f"{profile.photo}: {str(e)}")
                    print(f"Failed to delete profile photo: {profile.photo} - {e}")
        
        return {
            'success': True,
            'deleted_files': deleted_files,
            'failed_deletions': failed_deletions,
            'total_deleted': len(deleted_files),
            'total_failed': len(failed_deletions)
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'deleted_files': deleted_files,
            'failed_deletions': failed_deletions,
            'total_deleted': len(deleted_files),
            'total_failed': len(failed_deletions)
        }

def cleanup_orphaned_files(upload_folder: Optional[str] = None) -> dict:
    """
    Find and optionally delete orphaned files that are not referenced by any items
    
    Args:
        upload_folder: Path to upload folder (optional)
        
    Returns:
        Dictionary with cleanup results
    """
    if not upload_folder:
        upload_folder = current_app.config['UPLOAD_FOLDER']
    
    try:
        from models import Item, Profile
        
        # Get all referenced filenames from database
        referenced_files = set()
        
        # Get files from items
        items = Item.query.all()
        for item in items:
            # Check images_media
            if item.images_media:
                images = item.images_media
                if isinstance(images, str):
                    try:
                        images = json.loads(images)
                    except:
                        continue
                if isinstance(images, list):
                    referenced_files.update(images)
            
            # Check other file fields if they exist (only check actual Item model fields)
            actual_media_fields = ['images_media']  # Only check fields that exist on Item model
            for field in actual_media_fields:
                if hasattr(item, field):
                    field_value = getattr(item, field)
                    if field_value:
                        if isinstance(field_value, str):
                            try:
                                field_value = json.loads(field_value)
                            except:
                                continue
                        if isinstance(field_value, list):
                            referenced_files.update(field_value)
        
        # Get files from profiles
        profiles = Profile.query.all()
        for profile in profiles:
            if profile.photo:
                referenced_files.add(profile.photo)
        
        # Get all files in upload folder
        if os.path.exists(upload_folder):
            all_files = set(os.listdir(upload_folder))
            # Filter out directories
            all_files = {f for f in all_files if os.path.isfile(os.path.join(upload_folder, f))}
            
            # Find orphaned files
            orphaned_files = all_files - referenced_files
            
            return {
                'success': True,
                'total_files': len(all_files),
                'referenced_files': len(referenced_files),
                'orphaned_files': list(orphaned_files),
                'orphaned_count': len(orphaned_files)
            }
        else:
            return {
                'success': False,
                'error': 'Upload folder does not exist'
            }
            
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }





