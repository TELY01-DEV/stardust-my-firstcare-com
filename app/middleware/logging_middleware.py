import time
import uuid
import json
from datetime import datetime
from typing import Callable, Dict, Any, Optional
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from config import logger
import asyncio

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Comprehensive HTTP request/response logging middleware
    Captures timing, user context, request details, and response metadata
    """
    
    def __init__(self, app, exclude_paths: Optional[list] = None):
        super().__init__(app)
        self.exclude_paths = exclude_paths or ["/health", "/docs", "/openapi.json", "/favicon.ico"]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip logging for excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)
        
        # Generate request ID if not present
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        # Start timing
        start_time = time.time()
        
        # Extract request details
        request_details = await self._extract_request_details(request, request_id)
        
        # Log incoming request
        logger.info(
            "HTTP_REQUEST",
            extra={
                "event_type": "http_request",
                "request_id": request_id,
                "timestamp": datetime.utcnow().isoformat(),
                **request_details
            }
        )
        
        # Add request ID to request state for downstream use
        request.state.request_id = request_id
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate processing time
            process_time = time.time() - start_time
            
            # Extract response details
            response_details = self._extract_response_details(response, process_time)
            
            # Log response
            logger.info(
                "HTTP_RESPONSE",
                extra={
                    "event_type": "http_response",
                    "request_id": request_id,
                    "timestamp": datetime.utcnow().isoformat(),
                    **request_details,
                    **response_details
                }
            )
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except Exception as e:
            # Calculate processing time for errors
            process_time = time.time() - start_time
            
            # Log error
            logger.error(
                "HTTP_ERROR",
                extra={
                    "event_type": "http_error",
                    "request_id": request_id,
                    "timestamp": datetime.utcnow().isoformat(),
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "process_time_ms": round(process_time * 1000, 2),
                    **request_details
                }
            )
            
            # Trigger alert system
            try:
                from app.utils.alert_system import alert_manager
                await alert_manager.process_event({
                    "event_type": "http_error",
                    "status_code": getattr(e, 'status_code', 500),
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "request_id": request_id,
                    "client_ip": request_details.get("client_ip"),
                    "method": request_details.get("method"),
                    "path": request_details.get("path"),
                    "timestamp": datetime.utcnow().isoformat(),
                    "source": "http_middleware"
                })
            except Exception as alert_error:
                logger.error(f"Failed to trigger alert: {alert_error}")
            
            # Re-raise the exception
            raise
    
    async def _extract_request_details(self, request: Request, request_id: str) -> Dict[str, Any]:
        """Extract comprehensive request details"""
        details = {
            "method": request.method,
            "url": str(request.url),
            "path": request.url.path,
            "query_params": dict(request.query_params),
            "headers": dict(request.headers),
            "client_ip": self._get_client_ip(request),
            "user_agent": request.headers.get("user-agent", ""),
            "content_type": request.headers.get("content-type", ""),
            "content_length": request.headers.get("content-length", 0)
        }
        
        # Extract user information if available
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            details["has_auth_token"] = True
            details["token_prefix"] = auth_header[:20] + "..."
        else:
            details["has_auth_token"] = False
            
        return details
    
    def _extract_response_details(self, response: Response, process_time: float) -> Dict[str, Any]:
        """Extract response details"""
        return {
            "status_code": response.status_code,
            "response_headers": dict(response.headers),
            "process_time_ms": round(process_time * 1000, 2),
            "response_size": response.headers.get("content-length", 0)
        }
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address considering proxies"""
        # Check for forwarded headers
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # Fallback to direct connection
        if request.client and hasattr(request.client, "host"):
            return request.client.host
        
        return "unknown"
    
    async def _extract_user_info(self, request: Request) -> Optional[Dict[str, Any]]:
        """Extract user information from request"""
        return None
    
    async def _get_request_body(self, request: Request) -> Optional[str]:
        """Get request body safely"""
        return None
    
    def _sanitize_body(self, body: Dict[str, Any]) -> Dict[str, Any]:
        """Remove sensitive information from request body"""
        sensitive_fields = ["password", "token", "secret", "key", "credential"]
        
        if isinstance(body, dict):
            sanitized = {}
            for key, value in body.items():
                if any(sensitive in key.lower() for sensitive in sensitive_fields):
                    sanitized[key] = "[REDACTED]"
                elif isinstance(value, dict):
                    sanitized[key] = self._sanitize_body(value)
                else:
                    sanitized[key] = value
            return sanitized
        
        return body
    
    def _is_sensitive_endpoint(self, path: str) -> bool:
        """Check if endpoint contains sensitive data"""
        sensitive_paths = ["/auth/", "/login", "/password", "/token"]
        return any(sensitive in path.lower() for sensitive in sensitive_paths)


class PerformanceLoggingMiddleware(BaseHTTPMiddleware):
    """
    Performance monitoring middleware
    Tracks response times and identifies slow endpoints
    """
    
    def __init__(self, app, slow_threshold_ms: float = 1000):
        super().__init__(app)
        self.slow_threshold_ms = slow_threshold_ms
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        
        response = await call_next(request)
        
        process_time = time.time() - start_time
        process_time_ms = round(process_time * 1000, 2)
        
        # Log performance metrics
        if process_time_ms > self.slow_threshold_ms:
            logger.warning(
                "SLOW_REQUEST",
                extra={
                    "event_type": "performance_warning",
                    "request_id": getattr(request.state, "request_id", "unknown"),
                    "method": request.method,
                    "path": request.url.path,
                    "process_time_ms": process_time_ms,
                    "threshold_ms": self.slow_threshold_ms,
                    "status_code": response.status_code
                }
            )
        
        # Add performance headers
        response.headers["X-Process-Time"] = str(process_time_ms)
        
        return response


class SecurityLoggingMiddleware(BaseHTTPMiddleware):
    """
    Security event logging middleware
    Monitors for suspicious activities and security violations
    """
    
    def __init__(self, app):
        super().__init__(app)
        self.failed_attempts = {}  # Simple in-memory tracking
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        client_ip = self._get_client_ip(request)
        
        # Monitor for security events
        security_events = []
        
        # Check for suspicious patterns
        if self._is_suspicious_request(request):
            security_events.append("suspicious_request_pattern")
        
        # Check for potential injection attempts
        if self._check_injection_attempts(request):
            security_events.append("potential_injection_attempt")
        
        response = await call_next(request)
        
        # Monitor authentication failures
        if response.status_code == 401:
            self._track_failed_auth(client_ip)
            security_events.append("authentication_failure")
        
        # Log security events
        if security_events:
            logger.warning(
                "SECURITY_EVENT",
                extra={
                    "event_type": "security_event",
                    "request_id": getattr(request.state, "request_id", "unknown"),
                    "client_ip": client_ip,
                    "method": request.method,
                    "path": request.url.path,
                    "security_events": security_events,
                    "user_agent": request.headers.get("user-agent", ""),
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address"""
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        if request.client and hasattr(request.client, "host"):
            return request.client.host
        
        return "unknown"
    
    def _is_suspicious_request(self, request: Request) -> bool:
        """Check for suspicious request patterns"""
        suspicious_patterns = [
            "../", "..\\", "/etc/passwd", "/proc/", "cmd.exe",
            "<script", "javascript:", "onload=", "onerror=",
            "union select", "drop table", "insert into"
        ]
        
        # Check URL and query parameters
        full_url = str(request.url).lower()
        return any(pattern in full_url for pattern in suspicious_patterns)
    
    def _check_injection_attempts(self, request: Request) -> bool:
        """Check for potential injection attempts"""
        injection_patterns = [
            "' or '1'='1", "' or 1=1", "'; drop table",
            "<script>", "javascript:", "onload=",
            "../", "..\\", "/etc/", "/proc/"
        ]
        
        # Check query parameters
        for value in request.query_params.values():
            if any(pattern in value.lower() for pattern in injection_patterns):
                return True
        
        return False
    
    def _track_failed_auth(self, client_ip: str):
        """Track failed authentication attempts"""
        current_time = time.time()
        
        if client_ip not in self.failed_attempts:
            self.failed_attempts[client_ip] = []
        
        # Add current attempt
        self.failed_attempts[client_ip].append(current_time)
        
        # Clean old attempts (older than 1 hour)
        self.failed_attempts[client_ip] = [
            attempt for attempt in self.failed_attempts[client_ip]
            if current_time - attempt < 3600
        ]
        
        # Log if too many failures
        if len(self.failed_attempts[client_ip]) > 5:
            logger.error(
                "BRUTE_FORCE_DETECTED",
                extra={
                    "event_type": "security_alert",
                    "client_ip": client_ip,
                    "failed_attempts": len(self.failed_attempts[client_ip]),
                    "time_window": "1_hour",
                    "timestamp": datetime.utcnow().isoformat()
                }
            ) 