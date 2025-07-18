from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import hashlib
from enum import Enum
import redis.asyncio as redis
from fastapi import HTTPException, Request
from app.services.security_audit import security_audit, SecurityEventType, SecuritySeverity
from app.services.rate_limit_monitor import rate_limit_monitor
from config import settings
import logging

logger = logging.getLogger(__name__)

class RateLimitType(Enum):
    """Rate limit types"""
    GLOBAL = "global"  # Global rate limit per IP
    USER = "user"  # Per-user rate limit
    ENDPOINT = "endpoint"  # Per-endpoint rate limit
    API_KEY = "api_key"  # Per API key rate limit

class RateLimitTier(Enum):
    """Rate limit tiers for different user types"""
    ANONYMOUS = "anonymous"
    BASIC = "basic"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"
    UNLIMITED = "unlimited"

class RateLimiter:
    """
    Redis-based API rate limiting service
    """
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        
        # Rate limit configurations (requests per minute)
        self.rate_limits = {
            RateLimitTier.ANONYMOUS: {
                "global": 60,  # 60 requests per minute
                "endpoint": 20,  # 20 requests per endpoint per minute
                "burst": 10  # 10 burst requests
            },
            RateLimitTier.BASIC: {
                "global": 300,  # 300 requests per minute
                "endpoint": 100,  # 100 requests per endpoint per minute
                "burst": 50  # 50 burst requests
            },
            RateLimitTier.PREMIUM: {
                "global": 1000,  # 1000 requests per minute
                "endpoint": 300,  # 300 requests per endpoint per minute
                "burst": 100  # 100 burst requests
            },
            RateLimitTier.ENTERPRISE: {
                "global": 5000,  # 5000 requests per minute
                "endpoint": 1000,  # 1000 requests per endpoint per minute
                "burst": 500  # 500 burst requests
            },
            RateLimitTier.UNLIMITED: {
                "global": float('inf'),
                "endpoint": float('inf'),
                "burst": float('inf')
            }
        }
        
        # Special endpoint limits (override tier limits)
        self.endpoint_limits = {
            "/auth/login": 5,  # 5 login attempts per minute
            "/auth/register": 3,  # 3 registration attempts per minute
            "/auth/forgot-password": 3,  # 3 password reset requests per minute
            "/api/export": 10,  # 10 export requests per minute
            "/admin/backup": 1,  # 1 backup request per minute
        }
        
        # Whitelist (no rate limiting)
        self.whitelist = set([
            "127.0.0.1",
            "localhost",
            "49.0.81.155",  # Your external IP
            "172.18.0.0/16",  # Docker network range
            "172.19.0.0/16",  # Additional Docker network range
            "172.20.0.0/16",  # Additional Docker network range
            "10.0.0.0/8",     # Private network range
            "192.168.0.0/16", # Private network range
            # MQTT Listener containers
            "stardust-ava4-listener",
            "stardust-kati-listener", 
            "stardust-qube-listener",
            "stardust-mqtt-panel",
            "stardust-mqtt-websocket",
            # Add more trusted IPs here
        ])
        
        # Blacklist (immediate block)
        self.blacklist = set()
    
    async def connect(self):
        """Connect to Redis"""
        try:
            self.redis_client = await redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            logger.info("✅ Rate limiter connected to Redis")
        except Exception as e:
            logger.error(f"❌ Rate limiter Redis connection failed: {e}")
            self.redis_client = None
    
    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Rate limiter disconnected from Redis")
    
    async def check_rate_limit(
        self,
        request: Request,
        user_id: Optional[str] = None,
        api_key: Optional[str] = None,
        tier: RateLimitTier = RateLimitTier.ANONYMOUS
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if request is within rate limits
        
        Returns:
            Tuple[bool, Dict]: (is_allowed, rate_limit_info)
        """
        if not self.redis_client:
            # If Redis is not available, allow request but log warning
            logger.warning("Rate limiter not available - allowing request")
            return True, {"warning": "rate_limiter_unavailable"}
        
        # Get client IP
        client_ip = self._get_client_ip(request)
        endpoint = request.url.path
        method = request.method
        
        # Check blacklist
        if client_ip in self.blacklist:
            await self._log_rate_limit_exceeded(client_ip, endpoint, "blacklisted")
            return False, {"error": "ip_blacklisted", "ip": client_ip}
        
        # Check whitelist
        if self._is_whitelisted(client_ip):
            return True, {"status": "whitelisted", "ip": client_ip}
        
        # Get rate limits for tier
        limits = self.rate_limits[tier]
        
        # Check special endpoint limits
        endpoint_limit = self.endpoint_limits.get(endpoint)
        if endpoint_limit:
            limits = {
                "global": limits["global"],
                "endpoint": min(endpoint_limit, limits["endpoint"]),
                "burst": limits["burst"]
            }
        
        # Check multiple rate limits
        checks = []
        
        # Global IP rate limit
        ip_key = f"rate_limit:ip:{client_ip}"
        ip_allowed, ip_info = await self._check_limit(
            ip_key, limits["global"], 60  # 60 seconds window
        )
        checks.append(("ip", ip_allowed, ip_info))
        
        # Per-endpoint rate limit
        endpoint_key = f"rate_limit:endpoint:{client_ip}:{method}:{endpoint}"
        endpoint_allowed, endpoint_info = await self._check_limit(
            endpoint_key, limits["endpoint"], 60
        )
        checks.append(("endpoint", endpoint_allowed, endpoint_info))
        
        # Per-user rate limit (if authenticated)
        if user_id:
            user_key = f"rate_limit:user:{user_id}"
            user_allowed, user_info = await self._check_limit(
                user_key, limits["global"], 60
            )
            checks.append(("user", user_allowed, user_info))
        
        # Per API key rate limit
        if api_key:
            api_key_hash = self._hash_api_key(api_key)
            api_key_key = f"rate_limit:api_key:{api_key_hash}"
            api_allowed, api_info = await self._check_limit(
                api_key_key, limits["global"], 60
            )
            checks.append(("api_key", api_allowed, api_info))
        
        # Check if any limit is exceeded
        for check_type, allowed, info in checks:
            if not allowed:
                await self._log_rate_limit_exceeded(
                    client_ip, endpoint, check_type, user_id, api_key
                )
                
                # Record rate limit event for monitoring
                await rate_limit_monitor.record_rate_limit_event(
                    ip_address=client_ip,
                    endpoint=endpoint,
                    limit_type=check_type,
                    limit=info["limit"],
                    window=info["window"],
                    user_id=user_id,
                    api_key=api_key
                )
                
                return False, {
                    "error": "rate_limit_exceeded",
                    "type": check_type,
                    "limit": info["limit"],
                    "window": info["window"],
                    "retry_after": info["retry_after"]
                }
        
        # All checks passed
        rate_limit_info = {
            "tier": tier.value,
            "limits": {
                check_type: {
                    "used": info["used"],
                    "limit": info["limit"],
                    "remaining": info["remaining"]
                }
                for check_type, _, info in checks
            }
        }
        
        return True, rate_limit_info
    
    async def _check_limit(
        self,
        key: str,
        limit: int,
        window: int
    ) -> Tuple[bool, Dict[str, Any]]:
        """Check rate limit using sliding window algorithm"""
        try:
            now = datetime.utcnow().timestamp()
            window_start = now - window
            
            # Remove old entries
            await self.redis_client.zremrangebyscore(key, 0, window_start)
            
            # Count requests in current window
            current_count = await self.redis_client.zcard(key)
            
            if current_count >= limit:
                # Get oldest request timestamp to calculate retry_after
                oldest = await self.redis_client.zrange(key, 0, 0, withscores=True)
                if oldest:
                    retry_after = int(oldest[0][1] + window - now + 1)
                else:
                    retry_after = window
                
                return False, {
                    "used": current_count,
                    "limit": limit,
                    "window": window,
                    "remaining": 0,
                    "retry_after": retry_after
                }
            
            # Add current request
            await self.redis_client.zadd(key, {str(now): now})
            await self.redis_client.expire(key, window + 1)
            
            return True, {
                "used": current_count + 1,
                "limit": limit,
                "window": window,
                "remaining": limit - current_count - 1,
                "retry_after": 0
            }
            
        except Exception as e:
            logger.error(f"Rate limit check error: {e}")
            # On error, allow request but log
            return True, {"error": str(e)}
    
    async def reset_rate_limit(
        self,
        identifier: str,
        limit_type: RateLimitType = RateLimitType.GLOBAL
    ) -> bool:
        """Reset rate limit for an identifier"""
        try:
            if not self.redis_client:
                return False
            
            if limit_type == RateLimitType.GLOBAL:
                pattern = f"rate_limit:ip:{identifier}*"
            elif limit_type == RateLimitType.USER:
                pattern = f"rate_limit:user:{identifier}*"
            elif limit_type == RateLimitType.API_KEY:
                pattern = f"rate_limit:api_key:{identifier}*"
            else:
                pattern = f"rate_limit:*:{identifier}*"
            
            # Find and delete matching keys
            cursor = 0
            deleted = 0
            
            while True:
                cursor, keys = await self.redis_client.scan(
                    cursor, match=pattern, count=100
                )
                
                if keys:
                    deleted += await self.redis_client.delete(*keys)
                
                if cursor == 0:
                    break
            
            logger.info(f"Reset rate limit for {identifier}, deleted {deleted} keys")
            return True
            
        except Exception as e:
            logger.error(f"Failed to reset rate limit: {e}")
            return False
    
    async def add_to_whitelist(self, ip_address: str, reason: str = "", user_id: str = "system") -> Dict[str, Any]:
        """Add IP to whitelist with response message"""
        try:
            # Add to in-memory whitelist
            self.whitelist.add(ip_address)
            
            # Store in Redis for persistence
            if self.redis_client:
                await self.redis_client.sadd("rate_limit:whitelist", ip_address)
                await self.redis_client.hset(
                    "rate_limit:whitelist:reasons",
                    ip_address,
                    f"{reason}:{datetime.utcnow().isoformat()}:{user_id}"
                )
            
            logger.info(f"✅ Added {ip_address} to whitelist: {reason} (by {user_id})")
            
            return {
                "success": True,
                "message": f"IP {ip_address} successfully added to whitelist",
                "ip_address": ip_address,
                "reason": reason,
                "added_by": user_id,
                "timestamp": datetime.utcnow().isoformat(),
                "total_whitelisted": len(self.whitelist)
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to add {ip_address} to whitelist: {e}")
            return {
                "success": False,
                "message": f"Failed to add IP {ip_address} to whitelist: {str(e)}",
                "ip_address": ip_address,
                "error": str(e)
            }
    
    async def remove_from_whitelist(self, ip_address: str, user_id: str = "system") -> Dict[str, Any]:
        """Remove IP from whitelist with response message"""
        try:
            # Remove from in-memory whitelist
            removed = ip_address in self.whitelist
            self.whitelist.discard(ip_address)
            
            # Remove from Redis
            if self.redis_client:
                await self.redis_client.srem("rate_limit:whitelist", ip_address)
                await self.redis_client.hdel("rate_limit:whitelist:reasons", ip_address)
            
            if removed:
                logger.info(f"✅ Removed {ip_address} from whitelist (by {user_id})")
                return {
                    "success": True,
                    "message": f"IP {ip_address} successfully removed from whitelist",
                    "ip_address": ip_address,
                    "removed_by": user_id,
                    "timestamp": datetime.utcnow().isoformat(),
                    "total_whitelisted": len(self.whitelist)
                }
            else:
                return {
                    "success": False,
                    "message": f"IP {ip_address} was not in whitelist",
                    "ip_address": ip_address
                }
                
        except Exception as e:
            logger.error(f"❌ Failed to remove {ip_address} from whitelist: {e}")
            return {
                "success": False,
                "message": f"Failed to remove IP {ip_address} from whitelist: {str(e)}",
                "ip_address": ip_address,
                "error": str(e)
            }
    
    async def get_whitelist_status(self) -> Dict[str, Any]:
        """Get current whitelist status with detailed information"""
        try:
            whitelist_details = []
            
            # Get reasons from Redis if available
            reasons = {}
            if self.redis_client:
                try:
                    reasons = await self.redis_client.hgetall("rate_limit:whitelist:reasons")
                except Exception:
                    pass
            
            for ip in self.whitelist:
                reason_data = reasons.get(ip, "::system")
                parts = reason_data.split(":")
                reason = parts[0] if len(parts) > 0 else "No reason"
                timestamp = parts[1] if len(parts) > 1 else "Unknown"
                added_by = parts[2] if len(parts) > 2 else "system"
                
                whitelist_details.append({
                    "ip_address": ip,
                    "reason": reason,
                    "added_by": added_by,
                    "timestamp": timestamp
                })
            
            return {
                "success": True,
                "message": f"Retrieved whitelist with {len(self.whitelist)} IP addresses",
                "total_count": len(self.whitelist),
                "whitelist": whitelist_details,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get whitelist status: {e}")
            return {
                "success": False,
                "message": f"Failed to retrieve whitelist: {str(e)}",
                "error": str(e)
            }
    
    async def load_whitelist(self):
        """Load whitelist from Redis with logging"""
        if self.redis_client:
            try:
                whitelist = await self.redis_client.smembers("rate_limit:whitelist")
                self.whitelist.update(set(whitelist))
                logger.info(f"✅ Loaded {len(whitelist)} IPs from Redis whitelist")
            except Exception as e:
                logger.error(f"❌ Failed to load whitelist from Redis: {e}")

    async def add_to_blacklist(self, ip_address: str, reason: str = "", user_id: str = "system") -> Dict[str, Any]:
        """Add IP to blacklist with response message"""
        try:
            # Add to in-memory blacklist
            self.blacklist.add(ip_address)
            
            # Store in Redis for persistence
            if self.redis_client:
                await self.redis_client.sadd("rate_limit:blacklist", ip_address)
                await self.redis_client.hset(
                    "rate_limit:blacklist:reasons",
                    ip_address,
                    f"{reason}:{datetime.utcnow().isoformat()}:{user_id}"
                )
            
            logger.warning(f"⚠️ Added {ip_address} to blacklist: {reason} (by {user_id})")
    
            return {
                "success": True,
                "message": f"IP {ip_address} successfully added to blacklist",
                "ip_address": ip_address,
                "reason": reason,
                "added_by": user_id,
                "timestamp": datetime.utcnow().isoformat(),
                "total_blacklisted": len(self.blacklist)
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to add {ip_address} to blacklist: {e}")
            return {
                "success": False,
                "message": f"Failed to add IP {ip_address} to blacklist: {str(e)}",
                "ip_address": ip_address,
                "error": str(e)
            }

    async def remove_from_blacklist(self, ip_address: str, user_id: str = "system") -> Dict[str, Any]:
        """Remove IP from blacklist with response message"""
        try:
            # Remove from in-memory blacklist
            removed = ip_address in self.blacklist
            self.blacklist.discard(ip_address)
            
            # Remove from Redis
            if self.redis_client:
                await self.redis_client.srem("rate_limit:blacklist", ip_address)
                await self.redis_client.hdel("rate_limit:blacklist:reasons", ip_address)
            
            if removed:
                logger.info(f"✅ Removed {ip_address} from blacklist (by {user_id})")
                return {
                    "success": True,
                    "message": f"IP {ip_address} successfully removed from blacklist",
                    "ip_address": ip_address,
                    "removed_by": user_id,
                    "timestamp": datetime.utcnow().isoformat(),
                    "total_blacklisted": len(self.blacklist)
                }
            else:
                return {
                    "success": False,
                    "message": f"IP {ip_address} was not in blacklist",
                    "ip_address": ip_address
                }
                
        except Exception as e:
            logger.error(f"❌ Failed to remove {ip_address} from blacklist: {e}")
            return {
                "success": False,
                "message": f"Failed to remove IP {ip_address} from blacklist: {str(e)}",
                "ip_address": ip_address,
                "error": str(e)
            }
    
    async def load_blacklist(self):
        """Load blacklist from Redis"""
        if self.redis_client:
            try:
                blacklist = await self.redis_client.smembers("rate_limit:blacklist")
                self.blacklist = set(blacklist)
                logger.info(f"Loaded {len(self.blacklist)} IPs in blacklist")
            except Exception as e:
                logger.error(f"Failed to load blacklist: {e}")
    
    async def get_rate_limit_status(
        self,
        identifier: str,
        limit_type: RateLimitType = RateLimitType.GLOBAL
    ) -> Dict[str, Any]:
        """Get current rate limit status for an identifier"""
        try:
            if not self.redis_client:
                return {"error": "redis_not_available"}
            
            if limit_type == RateLimitType.GLOBAL:
                pattern = f"rate_limit:ip:{identifier}*"
            elif limit_type == RateLimitType.USER:
                pattern = f"rate_limit:user:{identifier}*"
            else:
                pattern = f"rate_limit:*{identifier}*"
            
            status = {
                "identifier": identifier,
                "type": limit_type.value,
                "limits": {}
            }
            
            # Find matching keys
            cursor = 0
            while True:
                cursor, keys = await self.redis_client.scan(
                    cursor, match=pattern, count=100
                )
                
                for key in keys:
                    count = await self.redis_client.zcard(key)
                    ttl = await self.redis_client.ttl(key)
                    
                    key_parts = key.split(":")
                    limit_name = ":".join(key_parts[2:])
                    
                    status["limits"][limit_name] = {
                        "current": count,
                        "ttl": ttl
                    }
                
                if cursor == 0:
                    break
            
            return status
            
        except Exception as e:
            logger.error(f"Failed to get rate limit status: {e}")
            return {"error": str(e)}
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request"""
        # Check for proxy headers
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # Get first IP in chain
            return forwarded.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fall back to direct connection
        if request.client:
            return request.client.host
        
        return "unknown"
    
    def _is_whitelisted(self, ip_address: str) -> bool:
        """Check if IP address is whitelisted (including CIDR ranges)"""
        import ipaddress
        
        # Check exact IP match
        if ip_address in self.whitelist:
            return True
        
        # Check CIDR ranges
        try:
            ip = ipaddress.ip_address(ip_address)
            for whitelist_entry in self.whitelist:
                if "/" in whitelist_entry:  # CIDR range
                    try:
                        network = ipaddress.ip_network(whitelist_entry, strict=False)
                        if ip in network:
                            return True
                    except ValueError:
                        continue  # Skip invalid CIDR ranges
        except ValueError:
            pass  # Invalid IP address
        
        return False
    
    def _hash_api_key(self, api_key: str) -> str:
        """Hash API key for storage"""
        return hashlib.sha256(api_key.encode()).hexdigest()[:16]
    
    async def _log_rate_limit_exceeded(
        self,
        ip_address: str,
        endpoint: str,
        limit_type: str,
        user_id: Optional[str] = None,
        api_key: Optional[str] = None
    ):
        """Log rate limit exceeded event"""
        await security_audit.log_api_security_event(
            event_type=SecurityEventType.RATE_LIMIT_EXCEEDED,
            api_key=api_key,
            endpoint=endpoint,
            ip_address=ip_address,
            details={
                "limit_type": limit_type,
                "user_id": user_id
            }
        )


# Global rate limiter instance
rate_limiter = RateLimiter() 