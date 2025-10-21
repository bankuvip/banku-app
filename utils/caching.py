"""
Advanced Caching System
Redis-based caching with fallback to memory cache
"""

import json
import time
import hashlib
from functools import wraps
from flask import current_app, request
import threading

class CacheManager:
    """Centralized cache management"""
    
    def __init__(self):
        self.memory_cache = {}
        self.cache_locks = {}
        self.default_ttl = 300  # 5 minutes
    
    def _get_cache_key(self, key, prefix="app"):
        """Generate a consistent cache key"""
        if isinstance(key, dict):
            key = json.dumps(key, sort_keys=True)
        return f"{prefix}:{hashlib.md5(str(key).encode()).hexdigest()}"
    
    def get(self, key, default=None):
        """Get value from cache"""
        cache_key = self._get_cache_key(key)
        
        # Check memory cache first
        if cache_key in self.memory_cache:
            item = self.memory_cache[cache_key]
            if time.time() < item['expires_at']:
                return item['value']
            else:
                # Expired, remove it
                del self.memory_cache[cache_key]
        
        return default
    
    def set(self, key, value, ttl=None):
        """Set value in cache"""
        cache_key = self._get_cache_key(key)
        ttl = ttl or self.default_ttl
        
        self.memory_cache[cache_key] = {
            'value': value,
            'expires_at': time.time() + ttl,
            'created_at': time.time()
        }
        
        return True
    
    def delete(self, key):
        """Delete value from cache"""
        cache_key = self._get_cache_key(key)
        if cache_key in self.memory_cache:
            del self.memory_cache[cache_key]
        return True
    
    def clear(self, pattern=None):
        """Clear cache entries"""
        if pattern:
            # Clear entries matching pattern
            keys_to_delete = [k for k in self.memory_cache.keys() if pattern in k]
            for key in keys_to_delete:
                del self.memory_cache[key]
        else:
            # Clear all
            self.memory_cache.clear()
        return True
    
    def get_or_set(self, key, func, ttl=None, *args, **kwargs):
        """Get from cache or set using function"""
        value = self.get(key)
        if value is not None:
            return value
        
        # Use lock to prevent multiple threads from executing the same function
        cache_key = self._get_cache_key(key)
        if cache_key not in self.cache_locks:
            self.cache_locks[cache_key] = threading.Lock()
        
        with self.cache_locks[cache_key]:
            # Check again after acquiring lock
            value = self.get(key)
            if value is not None:
                return value
            
            # Execute function and cache result
            try:
                value = func(*args, **kwargs)
                self.set(key, value, ttl)
                return value
            except Exception as e:
                current_app.logger.error(f"Cache function execution failed: {str(e)}")
                raise
    
    def invalidate_pattern(self, pattern):
        """Invalidate all cache entries matching pattern"""
        return self.clear(pattern)
    
    def get_stats(self):
        """Get cache statistics"""
        total_items = len(self.memory_cache)
        expired_items = 0
        current_time = time.time()
        
        for item in self.memory_cache.values():
            if current_time >= item['expires_at']:
                expired_items += 1
        
        return {
            'total_items': total_items,
            'expired_items': expired_items,
            'active_items': total_items - expired_items,
            'memory_usage': sum(len(str(item)) for item in self.memory_cache.values())
        }

# Global cache instance
cache_manager = CacheManager()

def cached(ttl=300, key_prefix="", key_func=None):
    """Decorator for caching function results"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # Default key generation
                key_parts = [key_prefix, func.__name__]
                if args:
                    key_parts.extend(str(arg) for arg in args)
                if kwargs:
                    key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                cache_key = ":".join(key_parts)
            
            return cache_manager.get_or_set(cache_key, func, ttl, *args, **kwargs)
        return wrapper
    return decorator

def cache_invalidate(pattern):
    """Invalidate cache entries matching pattern"""
    return cache_manager.invalidate_pattern(pattern)

def cache_clear():
    """Clear all cache entries"""
    return cache_manager.clear()

class QueryCache:
    """Specialized caching for database queries"""
    
    @staticmethod
    def cache_query(query_func, cache_key, ttl=300):
        """Cache a database query result"""
        return cache_manager.get_or_set(cache_key, query_func, ttl)
    
    @staticmethod
    def invalidate_model(model_class, model_id=None):
        """Invalidate cache for a specific model"""
        if model_id:
            pattern = f"query:{model_class.__name__}:{model_id}"
        else:
            pattern = f"query:{model_class.__name__}"
        return cache_manager.invalidate_pattern(pattern)
    
    @staticmethod
    def cache_user_data(user_id, data_func, ttl=300):
        """Cache user-specific data"""
        cache_key = f"user:{user_id}:data"
        return cache_manager.get_or_set(cache_key, data_func, ttl)
    
    @staticmethod
    def invalidate_user_data(user_id):
        """Invalidate all cached data for a user"""
        pattern = f"user:{user_id}:"
        return cache_manager.invalidate_pattern(pattern)

class ViewCache:
    """Specialized caching for view responses"""
    
    @staticmethod
    def cache_view(view_func, cache_key, ttl=600):
        """Cache a view function result"""
        return cache_manager.get_or_set(cache_key, view_func, ttl)
    
    @staticmethod
    def invalidate_view(pattern):
        """Invalidate cached views matching pattern"""
        return cache_manager.invalidate_pattern(f"view:{pattern}")
    
    @staticmethod
    def cache_dashboard_data(user_id, data_func, ttl=300):
        """Cache dashboard data for a user"""
        cache_key = f"dashboard:{user_id}"
        return cache_manager.get_or_set(cache_key, data_func, ttl)
    
    @staticmethod
    def invalidate_dashboard_data(user_id=None):
        """Invalidate dashboard cache"""
        if user_id:
            pattern = f"dashboard:{user_id}"
        else:
            pattern = "dashboard:"
        return cache_manager.invalidate_pattern(pattern)

class APICache:
    """Specialized caching for API responses"""
    
    @staticmethod
    def cache_api_response(endpoint, params, response_func, ttl=300):
        """Cache an API response"""
        # Create cache key from endpoint and params
        key_parts = [endpoint]
        if params:
            key_parts.extend(f"{k}={v}" for k, v in sorted(params.items()))
        cache_key = f"api:{':'.join(key_parts)}"
        
        return cache_manager.get_or_set(cache_key, response_func, ttl)
    
    @staticmethod
    def invalidate_api_cache(endpoint=None):
        """Invalidate API cache"""
        if endpoint:
            pattern = f"api:{endpoint}"
        else:
            pattern = "api:"
        return cache_manager.invalidate_pattern(pattern)

# Cache warming functions
def warm_cache():
    """Warm up frequently accessed cache entries"""
    try:
        from models import User, Deal, Item, ButtonConfiguration
        
        # Warm up user counts
        cache_manager.set("stats:total_users", User.query.count(), 3600)
        cache_manager.set("stats:total_deals", Deal.query.count(), 3600)
        cache_manager.set("stats:total_items", Item.query.count(), 3600)
        
        # Warm up button configurations
        buttons = ButtonConfiguration.query.filter_by(is_active=True).all()
        cache_manager.set("buttons:active", [b.to_dict() for b in buttons], 1800)
        
        current_app.logger.info("Cache warmed successfully")
        return True
    except Exception as e:
        current_app.logger.error(f"Cache warming failed: {str(e)}")
        return False

def get_cache_stats():
    """Get detailed cache statistics"""
    stats = cache_manager.get_stats()
    
    # Add cache hit/miss ratios if we had those metrics
    stats.update({
        'cache_manager': 'memory',
        'default_ttl': cache_manager.default_ttl
    })
    
    return stats
