from typing import Dict, Any, Optional, Callable
from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from app.services.rate_limiter import rate_limiter, RateLimitTier
from app.services.security_audit import security_audit, SecurityEventType, SecuritySeverity
from app.utils.error_definitions import create_error_response
from config import logger

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware for API rate limiting
    """
    
    def __init__(self, app, exclude_paths: Optional[list] = None):
        super().__init__(app)
        self.exclude_paths = exclude_paths or [
            "/docs",
            "/redoc",
            "/openapi.json",
            "/health",
            "/metrics",
            "/favicon.ico"
        ]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with rate limiting"""
        
        # Skip rate limiting for excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)
        
        # Skip OPTIONS requests
        if request.method == "OPTIONS":
            return await call_next(request)
        
        try:
            # Get user info from request state (set by auth middleware)
            user_info = getattr(request.state, "user", None)
            user_id = user_info.get("username") if user_info else None
            
            # Determine rate limit tier
            tier = self._get_user_tier(user_info)
            
            # Check rate limit
            is_allowed, rate_limit_info = await rate_limiter.check_rate_limit(
                request=request,
                user_id=user_id,
                tier=tier
            )
            
            if not is_allowed:
                # Rate limit exceeded
                error_info = rate_limit_info
                retry_after = error_info.get("retry_after", 60)
                
                # Create error response
                error_response = create_error_response(
                    error_code="RATE_LIMIT_EXCEEDED",
                    custom_message=f"Rate limit exceeded. Please retry after {retry_after} seconds.",
                    request_id=getattr(request.state, "request_id", None)
                )
                
                # Return 429 Too Many Requests
                return JSONResponse(
                    status_code=429,
                    content=error_response.dict(),
                    headers={
                        "Retry-After": str(retry_after),
                        "X-RateLimit-Limit": str(error_info.get("limit", 0)),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(retry_after)
                    }
                )
            
            # Process request
            response = await call_next(request)
            
            # Add rate limit headers (only if we have valid rate limit info)
            if "limits" in rate_limit_info:
                # Get the most restrictive limit
                limits = rate_limit_info["limits"]
                
                # Find the limit with least remaining requests
                min_remaining = float('inf')
                limit_info = None
                
                for limit_type, info in limits.items():
                    if info.get("remaining", 0) < min_remaining:
                        min_remaining = info["remaining"]
                        limit_info = info
                
                if limit_info:
                    response.headers["X-RateLimit-Limit"] = str(limit_info.get("limit", 0))
                    response.headers["X-RateLimit-Remaining"] = str(limit_info.get("remaining", 0))
                    # Calculate used from limit and remaining
                    limit_val = limit_info.get("limit", 0)
                    remaining_val = limit_info.get("remaining", 0)
                    used_val = max(0, limit_val - remaining_val)
                    response.headers["X-RateLimit-Used"] = str(used_val)
            elif "limit" in rate_limit_info and "remaining" in rate_limit_info:
                # Handle direct rate limit info structure
                response.headers["X-RateLimit-Limit"] = str(rate_limit_info.get("limit", 0))
                response.headers["X-RateLimit-Remaining"] = str(rate_limit_info.get("remaining", 0))
                # Calculate used from limit and remaining
                limit_val = rate_limit_info.get("limit", 0)
                remaining_val = rate_limit_info.get("remaining", 0)
                used_val = max(0, limit_val - remaining_val)
                response.headers["X-RateLimit-Used"] = str(used_val)
            
            return response
            
        except Exception as e:
            logger.error(f"Rate limit middleware error: {e}")
            # On error, allow request to proceed
            return await call_next(request)
    
    def _get_user_tier(self, user_info: Optional[Dict[str, Any]]) -> RateLimitTier:
        """Determine user's rate limit tier"""
        if not user_info:
            return RateLimitTier.ANONYMOUS
        
        # Check user role/plan
        role = user_info.get("role", "").lower()
        plan = user_info.get("plan", "").lower()
        
        # Map roles to tiers
        if role in ["admin", "superadmin"]:
            return RateLimitTier.UNLIMITED
        elif plan == "enterprise":
            return RateLimitTier.ENTERPRISE
        elif plan == "premium":
            return RateLimitTier.PREMIUM
        elif plan == "basic" or role in ["doctor", "nurse"]:
            return RateLimitTier.BASIC
        else:
            return RateLimitTier.ANONYMOUS


def create_rate_limit_dependency(tier: RateLimitTier = RateLimitTier.BASIC):
    """
    Create a FastAPI dependency for rate limiting specific endpoints
    """
    async def rate_limit_check(request: Request):
        """Check rate limit for endpoint"""
        user_info = getattr(request.state, "user", None)
        user_id = user_info.get("username") if user_info else None
        
        is_allowed, rate_limit_info = await rate_limiter.check_rate_limit(
            request=request,
            user_id=user_id,
            tier=tier
        )
        
        if not is_allowed:
            retry_after = rate_limit_info.get("retry_after", 60)
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Retry after {retry_after} seconds.",
                headers={
                    "Retry-After": str(retry_after)
                }
            )
        
        # Add rate limit info to request state
        request.state.rate_limit_info = rate_limit_info
    
    return rate_limit_check


# Convenience decorators for common rate limits
rate_limit_anonymous = create_rate_limit_dependency(RateLimitTier.ANONYMOUS)
rate_limit_basic = create_rate_limit_dependency(RateLimitTier.BASIC)
rate_limit_premium = create_rate_limit_dependency(RateLimitTier.PREMIUM)
rate_limit_enterprise = create_rate_limit_dependency(RateLimitTier.ENTERPRISE) 