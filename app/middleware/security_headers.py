from typing import Dict, Any, Optional, Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
import hashlib
import secrets
from config import settings, logger

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses
    """
    
    def __init__(self, app, csp_directives: Optional[Dict[str, str]] = None):
        super().__init__(app)
        
        # Content Security Policy directives
        self.csp_directives = csp_directives or {
            "default-src": "'self'",
            "script-src": "'self' 'unsafe-inline' 'unsafe-eval'",  # For development
            "style-src": "'self' 'unsafe-inline'",
            "img-src": "'self' data: https:",
            "font-src": "'self' data:",
            "connect-src": "'self' ws: wss:",  # For WebSocket
            "frame-ancestors": "'none'",
            "base-uri": "'self'",
            "form-action": "'self'"
        }
        
        # Generate nonce for CSP
        self.nonce = None
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add security headers to response"""
        
        # Generate nonce for this request
        request.state.csp_nonce = self._generate_nonce()
        
        # Process request
        response = await call_next(request)
        
        # Add security headers
        self._add_security_headers(response, request)
        
        return response
    
    def _add_security_headers(self, response: Response, request: Request):
        """Add security headers to response"""
        
        # Content Security Policy - use relaxed policy for documentation
        if self._is_docs_endpoint(request.url.path):
            csp_header = self._build_docs_csp_header(request.state.csp_nonce)
        else:
            csp_header = self._build_csp_header(request.state.csp_nonce)
        response.headers["Content-Security-Policy"] = csp_header
        
        # X-Content-Type-Options
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # X-Frame-Options
        response.headers["X-Frame-Options"] = "DENY"
        
        # X-XSS-Protection (legacy but still useful)
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Referrer-Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Permissions-Policy (formerly Feature-Policy)
        response.headers["Permissions-Policy"] = (
            "accelerometer=(), "
            "camera=(), "
            "geolocation=(), "
            "gyroscope=(), "
            "magnetometer=(), "
            "microphone=(), "
            "payment=(), "
            "usb=()"
        )
        
        # Strict-Transport-Security (HSTS) - only for HTTPS
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )
        
        # Cache-Control for sensitive endpoints
        if self._is_sensitive_endpoint(request.url.path):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        
        # Remove server header if present
        if "server" in response.headers:
            del response.headers["server"]
        
        # Add custom security header
        response.headers["X-API-Security"] = "enabled"
    
    def _build_csp_header(self, nonce: str) -> str:
        """Build Content Security Policy header"""
        directives = []
        
        for directive, value in self.csp_directives.items():
            if directive == "script-src" and nonce:
                # Add nonce to script-src
                value = f"{value} 'nonce-{nonce}'"
            directives.append(f"{directive} {value}")
        
        return "; ".join(directives)
    
    def _build_docs_csp_header(self, nonce: str) -> str:
        """Build relaxed Content Security Policy header for documentation endpoints"""
        docs_directives = {
            "default-src": "'self'",
            "script-src": "'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net",
            "style-src": "'self' 'unsafe-inline' https://cdn.jsdelivr.net",
            "img-src": "'self' data: https:",
            "font-src": "'self' data: https://cdn.jsdelivr.net",
            "connect-src": "'self' ws: wss:",
            "frame-ancestors": "'none'",
            "base-uri": "'self'",
            "form-action": "'self'"
        }
        
        directives = []
        for directive, value in docs_directives.items():
            directives.append(f"{directive} {value}")
        
        return "; ".join(directives)
    
    def _generate_nonce(self) -> str:
        """Generate CSP nonce"""
        return secrets.token_urlsafe(16)
    
    def _is_sensitive_endpoint(self, path: str) -> bool:
        """Check if endpoint handles sensitive data"""
        sensitive_patterns = [
            "/admin",
            "/auth",
            "/patients",
            "/medical-history",
            "/api/export"
        ]
        
        return any(path.startswith(pattern) for pattern in sensitive_patterns)
    
    def _is_docs_endpoint(self, path: str) -> bool:
        """Check if endpoint is documentation related"""
        docs_patterns = [
            "/docs",
            "/redoc",
            "/openapi.json"
        ]
        
        return any(path.startswith(pattern) for pattern in docs_patterns)


class SecurityCORSMiddleware:
    """
    Enhanced CORS middleware with security considerations
    """
    
    @staticmethod
    def create(
        allowed_origins: Optional[list] = None,
        allowed_methods: Optional[list] = None,
        allowed_headers: Optional[list] = None,
        expose_headers: Optional[list] = None,
        allow_credentials: bool = True,
        max_age: int = 600
    ) -> CORSMiddleware:
        """Create CORS middleware with secure defaults"""
        
        # Default allowed origins (should be configured per environment)
        if allowed_origins is None:
            if settings.environment == "production":
                allowed_origins = [
                    "https://my.firstcare.com",
                    "https://admin.firstcare.com"
                ]
            else:
                allowed_origins = [
                    "http://localhost:3000",
                    "http://localhost:5173",
                    "http://127.0.0.1:3000",
                    "http://127.0.0.1:5173"
                ]
        
        # Default allowed methods
        if allowed_methods is None:
            allowed_methods = ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"]
        
        # Default allowed headers
        if allowed_headers is None:
            allowed_headers = [
                "Content-Type",
                "Authorization",
                "X-Requested-With",
                "X-Request-ID",
                "X-API-Key"
            ]
        
        # Default exposed headers
        if expose_headers is None:
            expose_headers = [
                "X-Request-ID",
                "X-RateLimit-Limit",
                "X-RateLimit-Remaining",
                "X-RateLimit-Reset",
                "X-Total-Count"
            ]
        
        return CORSMiddleware(
            app=None,  # Will be set by FastAPI
            allow_origins=allowed_origins,
            allow_credentials=allow_credentials,
            allow_methods=allowed_methods,
            allow_headers=allowed_headers,
            expose_headers=expose_headers,
            max_age=max_age
        )


class APIKeyValidationMiddleware(BaseHTTPMiddleware):
    """
    Middleware for API key validation on specific endpoints
    """
    
    def __init__(self, app, api_key_endpoints: Optional[list] = None):
        super().__init__(app)
        self.api_key_endpoints = api_key_endpoints or [
            "/api/external",
            "/api/webhook"
        ]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Validate API key for protected endpoints"""
        
        # Check if endpoint requires API key
        if not any(request.url.path.startswith(endpoint) for endpoint in self.api_key_endpoints):
            return await call_next(request)
        
        # Get API key from header
        api_key = request.headers.get("X-API-Key")
        
        if not api_key:
            return Response(
                content='{"error": "API key required"}',
                status_code=401,
                headers={"Content-Type": "application/json"}
            )
        
        # Validate API key (simplified - should check against database)
        if not self._validate_api_key(api_key):
            return Response(
                content='{"error": "Invalid API key"}',
                status_code=401,
                headers={"Content-Type": "application/json"}
            )
        
        # Add API key info to request state
        request.state.api_key = api_key
        request.state.api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()[:16]
        
        return await call_next(request)
    
    def _validate_api_key(self, api_key: str) -> bool:
        """Validate API key format and existence"""
        # Check format
        if not api_key.startswith("mfc_") or len(api_key) < 20:
            return False
        
        # TODO: Check against database
        # This is a placeholder - should query database
        return True


class InputSanitizationMiddleware(BaseHTTPMiddleware):
    """
    Middleware to sanitize input data
    """
    
    def __init__(self, app):
        super().__init__(app)
        self.dangerous_patterns = [
            # SQL injection patterns
            r"(\b(union|select|insert|update|delete|drop|create|alter|exec|execute)\b)",
            # Script injection patterns
            r"<script[^>]*>.*?</script>",
            r"javascript:",
            r"on\w+\s*=",
            # Path traversal
            r"\.\./",
            r"\.\.\\",
        ]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Check for dangerous patterns in request"""
        
        # Skip for trusted endpoints
        if request.url.path in ["/health", "/metrics"]:
            return await call_next(request)
        
        # Check query parameters
        if request.url.query:
            if self._contains_dangerous_pattern(request.url.query):
                logger.warning(f"Dangerous pattern in query: {request.url.query[:100]}")
                return Response(
                    content='{"error": "Invalid input detected"}',
                    status_code=400,
                    headers={"Content-Type": "application/json"}
                )
        
        # For POST/PUT/PATCH requests, we would need to check body
        # This is handled better at the validation layer
        
        return await call_next(request)
    
    def _contains_dangerous_pattern(self, text: str) -> bool:
        """Check if text contains dangerous patterns"""
        import re
        
        text_lower = text.lower()
        for pattern in self.dangerous_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return True
        
        return False 