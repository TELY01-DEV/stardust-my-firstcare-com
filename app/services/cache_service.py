import asyncio
import hashlib
import json
import pickle
from datetime import timedelta
from functools import wraps
from typing import Any, Dict, List, Optional, Union

import redis.asyncio as redis
from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.utils.json_encoder import MongoJSONEncoder
from config import logger, settings

class CacheService:
    """
    Redis-based caching service with support for various data types and TTL management
    """
    
    def __init__(self):
        self.redis_client: Optional[Redis] = None
        self.default_ttl = 3600  # 1 hour default TTL
        self.cache_prefix = "mfc:opera:"  # MyFirstCare Opera Panel prefix
        
        # Cache configuration by data type
        self.cache_configs = {
            "patient": {"ttl": 1800, "version": 1},  # 30 minutes
            "hospital": {"ttl": 3600, "version": 1},  # 1 hour
            "master_data": {"ttl": 86400, "version": 1},  # 24 hours
            "medical_history": {"ttl": 900, "version": 1},  # 15 minutes
            "device_data": {"ttl": 300, "version": 1},  # 5 minutes
            "statistics": {"ttl": 600, "version": 1},  # 10 minutes
            "user_session": {"ttl": 3600, "version": 1},  # 1 hour
        }
    
    async def connect(self):
        """Connect to Redis server with retry logic"""
        max_retries = 3
        retry_delay = 1  # Start with 1 second delay
        
        for attempt in range(max_retries):
            try:
                # Use the same connection configuration as other working services
                self.redis_client = await redis.from_url(
                    settings.redis_url,
                    encoding="utf-8",
                    decode_responses=True  # Changed to match working services
                )
                
                # Test connection
                await self.redis_client.ping()
                logger.info("✅ Connected to Redis cache")
                return
                
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"⚠️ Redis connection attempt {attempt + 1}/{max_retries} failed: {e}")
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    logger.error(f"❌ Redis connection failed after {max_retries} attempts: {e}")
                    # Don't raise - allow app to work without cache
                    self.redis_client = None
    
    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Disconnected from Redis cache")
    
    def _generate_key(self, key_type: str, identifier: str, **kwargs) -> str:
        """Generate a cache key with namespace and versioning"""
        config = self.cache_configs.get(key_type, {"version": 1})
        version = config["version"]
        
        # Build key components
        key_parts = [self.cache_prefix, key_type, f"v{version}", identifier]
        
        # Add optional parameters to key
        if kwargs:
            param_str = ":".join(f"{k}={v}" for k, v in sorted(kwargs.items()))
            key_parts.append(hashlib.md5(param_str.encode()).hexdigest()[:8])
        
        return ":".join(key_parts)
    
    async def get(self, key_type: str, identifier: str, **kwargs) -> Optional[Any]:
        """Get value from cache"""
        if not self.redis_client:
            return None
        
        try:
            key = self._generate_key(key_type, identifier, **kwargs)
            value = await self.redis_client.get(key)
            
            if value:
                # Try JSON first, then pickle
                try:
                    return json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    try:
                        return pickle.loads(value)
                    except:
                        return None
                        
            return None
            
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None
    
    async def set(self, key_type: str, identifier: str, value: Any, 
                  ttl: Optional[int] = None, **kwargs) -> bool:
        """Set value in cache with TTL"""
        if not self.redis_client:
            return False
        
        try:
            key = self._generate_key(key_type, identifier, **kwargs)
            
            # Get TTL from config or use provided/default
            if ttl is None:
                ttl = self.cache_configs.get(key_type, {}).get("ttl", self.default_ttl)
            
            # Serialize value
            try:
                # Try JSON serialization first (with MongoDB encoder)
                serialized = json.dumps(value, cls=MongoJSONEncoder)
            except (TypeError, ValueError):
                # Fall back to pickle for complex objects
                serialized = pickle.dumps(value)
            
            # Set with expiration
            await self.redis_client.setex(key, ttl, serialized)
            return True
            
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False
    
    async def delete(self, key_type: str, identifier: str, **kwargs) -> bool:
        """Delete value from cache"""
        if not self.redis_client:
            return False
        
        try:
            key = self._generate_key(key_type, identifier, **kwargs)
            result = await self.redis_client.delete(key)
            return result > 0
            
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False
    
    async def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching a pattern"""
        if not self.redis_client:
            return 0
        
        try:
            # Use SCAN to find keys (more efficient than KEYS)
            deleted_count = 0
            async for key in self.redis_client.scan_iter(match=f"{self.cache_prefix}{pattern}*"):
                await self.redis_client.delete(key)
                deleted_count += 1
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Cache delete pattern error: {e}")
            return 0
    
    async def invalidate_patient_cache(self, patient_id: str):
        """Invalidate all cache entries for a patient"""
        patterns = [
            f"patient:*:{patient_id}",
            f"medical_history:*:{patient_id}",
            f"device_data:*:{patient_id}"
        ]
        
        for pattern in patterns:
            await self.delete_pattern(pattern)
    
    async def invalidate_hospital_cache(self, hospital_id: str):
        """Invalidate all cache entries for a hospital"""
        patterns = [
            f"hospital:*:{hospital_id}",
            f"statistics:*:hospital_{hospital_id}"
        ]
        
        for pattern in patterns:
            await self.delete_pattern(pattern)
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        if not self.redis_client:
            return {"status": "disconnected"}
        
        try:
            info = await self.redis_client.info()
            
            return {
                "status": "connected",
                "used_memory": info.get("used_memory_human", "N/A"),
                "connected_clients": info.get("connected_clients", 0),
                "total_commands_processed": info.get("total_commands_processed", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "hit_rate": self._calculate_hit_rate(
                    info.get("keyspace_hits", 0),
                    info.get("keyspace_misses", 0)
                ),
                "evicted_keys": info.get("evicted_keys", 0),
                "expired_keys": info.get("expired_keys", 0)
            }
            
        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {"status": "error", "error": str(e)}
    
    def _calculate_hit_rate(self, hits: int, misses: int) -> float:
        """Calculate cache hit rate percentage"""
        total = hits + misses
        if total == 0:
            return 0.0
        return round((hits / total) * 100, 2)
    
    async def health_check(self) -> bool:
        """Check if Redis is healthy"""
        if not self.redis_client:
            return False
        
        try:
            await self.redis_client.ping()
            return True
        except:
            return False


# Cache decorator for easy caching
def cache_result(key_type: str, ttl: Optional[int] = None):
    """
    Decorator to cache function results
    
    Usage:
        @cache_result("patient", ttl=1800)
        async def get_patient(patient_id: str):
            # ... expensive operation
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            cache_key_parts = [func.__name__]
            cache_key_parts.extend(str(arg) for arg in args)
            cache_key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
            identifier = ":".join(cache_key_parts)
            
            # Try to get from cache
            cached_value = await cache_service.get(key_type, identifier)
            if cached_value is not None:
                logger.debug(f"Cache hit for {func.__name__}")
                return cached_value
            
            # Call the actual function
            result = await func(*args, **kwargs)
            
            # Cache the result
            await cache_service.set(key_type, identifier, result, ttl=ttl)
            logger.debug(f"Cached result for {func.__name__}")
            
            return result
        
        return wrapper
    return decorator


# Global cache service instance
cache_service = CacheService() 