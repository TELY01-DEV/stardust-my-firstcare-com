from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from bson import ObjectId

from app.services.auth import require_auth
from app.services.security_audit import security_audit, SecurityEventType, SecuritySeverity
from app.services.rate_limiter import rate_limiter, RateLimitType
from app.services.encryption import encryption_service
from app.utils.error_definitions import create_error_response, create_success_response
from app.utils.json_encoder import serialize_mongodb_response
from config import logger

router = APIRouter(prefix="/admin/security", tags=["security"])

# ==================== SECURITY AUDIT ENDPOINTS ====================

@router.get("/audit/events")
async def get_security_events(
    request: Request,
    event_type: Optional[str] = None,
    severity: Optional[str] = None,
    user_id: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = Query(100, ge=1, le=1000),
    skip: int = Query(0, ge=0),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get security audit events"""
    request_id = getattr(request.state, 'request_id', None)
    
    # Check admin privileges
    if current_user.get("role") not in ["admin", "superadmin"]:
        raise HTTPException(
            status_code=403,
            detail="Admin privileges required"
        )
    
    try:
        # Parse event type and severity
        event_type_enum = None
        if event_type:
            try:
                event_type_enum = SecurityEventType(event_type)
            except ValueError:
                error_response = create_error_response(
                    "INVALID_EVENT_TYPE",
                    custom_message=f"Invalid event type: {event_type}",
                    field="event_type",
                    value=event_type,
                    request_id=request_id
                )
                return JSONResponse(status_code=400, content=error_response.dict())
        
        severity_enum = None
        if severity:
            try:
                severity_enum = SecuritySeverity(severity)
            except ValueError:
                error_response = create_error_response(
                    "INVALID_SEVERITY",
                    custom_message=f"Invalid severity: {severity}",
                    field="severity",
                    value=severity,
                    request_id=request_id
                )
                return JSONResponse(status_code=400, content=error_response.dict())
        
        # Get events
        events = await security_audit.get_security_events(
            event_type=event_type_enum,
            severity=severity_enum,
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            skip=skip
        )
        
        # Serialize response
        events = serialize_mongodb_response(events)
        
        success_response = create_success_response(
            message="Security events retrieved successfully",
            data={
                "events": events,
                "total": len(events),
                "filters": {
                    "event_type": event_type,
                    "severity": severity,
                    "user_id": user_id,
                    "start_date": start_date.isoformat() if start_date else None,
                    "end_date": end_date.isoformat() if end_date else None
                }
            },
            request_id=request_id
        )
        
        return JSONResponse(content=success_response.dict())
        
    except Exception as e:
        error_response = create_error_response(
            "INTERNAL_SERVER_ERROR",
            custom_message=f"Failed to retrieve security events: {str(e)}",
            request_id=request_id
        )
        return JSONResponse(status_code=500, content=error_response.dict())


@router.get("/audit/summary")
async def get_security_summary(
    request: Request,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get security events summary"""
    request_id = getattr(request.state, 'request_id', None)
    
    # Check admin privileges
    if current_user.get("role") not in ["admin", "superadmin"]:
        raise HTTPException(
            status_code=403,
            detail="Admin privileges required"
        )
    
    try:
        summary = await security_audit.get_security_summary(
            start_date=start_date,
            end_date=end_date
        )
        
        success_response = create_success_response(
            message="Security summary retrieved successfully",
            data=summary,
            request_id=request_id
        )
        
        return JSONResponse(content=success_response.dict())
        
    except Exception as e:
        error_response = create_error_response(
            "INTERNAL_SERVER_ERROR",
            custom_message=f"Failed to retrieve security summary: {str(e)}",
            request_id=request_id
        )
        return JSONResponse(status_code=500, content=error_response.dict())


@router.get("/alerts/active")
async def get_active_alerts(
    request: Request,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get active security alerts"""
    request_id = getattr(request.state, 'request_id', None)
    
    # Check admin privileges
    if current_user.get("role") not in ["admin", "superadmin"]:
        raise HTTPException(
            status_code=403,
            detail="Admin privileges required"
        )
    
    try:
        alerts = await security_audit.get_active_alerts()
        alerts = serialize_mongodb_response(alerts)
        
        success_response = create_success_response(
            message="Active alerts retrieved successfully",
            data={
                "alerts": alerts,
                "total": len(alerts)
            },
            request_id=request_id
        )
        
        return JSONResponse(content=success_response.dict())
        
    except Exception as e:
        error_response = create_error_response(
            "INTERNAL_SERVER_ERROR",
            custom_message=f"Failed to retrieve active alerts: {str(e)}",
            request_id=request_id
        )
        return JSONResponse(status_code=500, content=error_response.dict())


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    request: Request,
    alert_id: str,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Acknowledge a security alert"""
    request_id = getattr(request.state, 'request_id', None)
    
    # Check admin privileges
    if current_user.get("role") not in ["admin", "superadmin"]:
        raise HTTPException(
            status_code=403,
            detail="Admin privileges required"
        )
    
    try:
        if not ObjectId.is_valid(alert_id):
            error_response = create_error_response(
                "INVALID_ALERT_ID",
                custom_message="Invalid alert ID format",
                field="alert_id",
                value=alert_id,
                request_id=request_id
            )
            return JSONResponse(status_code=400, content=error_response.dict())
        
        success = await security_audit.acknowledge_alert(
            alert_id=alert_id,
            user_id=current_user.get("username")
        )
        
        if not success:
            error_response = create_error_response(
                "ALERT_NOT_FOUND",
                custom_message="Alert not found or already acknowledged",
                field="alert_id",
                value=alert_id,
                request_id=request_id
            )
            return JSONResponse(status_code=404, content=error_response.dict())
        
        success_response = create_success_response(
            message="Alert acknowledged successfully",
            data={"alert_id": alert_id},
            request_id=request_id
        )
        
        return JSONResponse(content=success_response.dict())
        
    except Exception as e:
        error_response = create_error_response(
            "INTERNAL_SERVER_ERROR",
            custom_message=f"Failed to acknowledge alert: {str(e)}",
            request_id=request_id
        )
        return JSONResponse(status_code=500, content=error_response.dict())


@router.post("/alerts/{alert_id}/resolve")
async def resolve_alert(
    request: Request,
    alert_id: str,
    resolution: str,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Resolve a security alert"""
    request_id = getattr(request.state, 'request_id', None)
    
    # Check admin privileges
    if current_user.get("role") not in ["admin", "superadmin"]:
        raise HTTPException(
            status_code=403,
            detail="Admin privileges required"
        )
    
    try:
        if not ObjectId.is_valid(alert_id):
            error_response = create_error_response(
                "INVALID_ALERT_ID",
                custom_message="Invalid alert ID format",
                field="alert_id",
                value=alert_id,
                request_id=request_id
            )
            return JSONResponse(status_code=400, content=error_response.dict())
        
        success = await security_audit.resolve_alert(
            alert_id=alert_id,
            user_id=current_user.get("username"),
            resolution=resolution
        )
        
        if not success:
            error_response = create_error_response(
                "ALERT_NOT_FOUND",
                custom_message="Alert not found or already resolved",
                field="alert_id",
                value=alert_id,
                request_id=request_id
            )
            return JSONResponse(status_code=404, content=error_response.dict())
        
        success_response = create_success_response(
            message="Alert resolved successfully",
            data={
                "alert_id": alert_id,
                "resolution": resolution
            },
            request_id=request_id
        )
        
        return JSONResponse(content=success_response.dict())
        
    except Exception as e:
        error_response = create_error_response(
            "INTERNAL_SERVER_ERROR",
            custom_message=f"Failed to resolve alert: {str(e)}",
            request_id=request_id
        )
        return JSONResponse(status_code=500, content=error_response.dict())


# ==================== RATE LIMITING ENDPOINTS ====================

@router.get("/rate-limits/{identifier}")
async def get_rate_limit_status(
    request: Request,
    identifier: str,
    limit_type: str = Query("global", regex="^(global|user|api_key)$"),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get rate limit status for an identifier"""
    request_id = getattr(request.state, 'request_id', None)
    
    # Check admin privileges
    if current_user.get("role") not in ["admin", "superadmin"]:
        raise HTTPException(
            status_code=403,
            detail="Admin privileges required"
        )
    
    try:
        limit_type_enum = RateLimitType(limit_type)
        
        status = await rate_limiter.get_rate_limit_status(
            identifier=identifier,
            limit_type=limit_type_enum
        )
        
        success_response = create_success_response(
            message="Rate limit status retrieved successfully",
            data=status,
            request_id=request_id
        )
        
        return JSONResponse(content=success_response.dict())
        
    except Exception as e:
        error_response = create_error_response(
            "INTERNAL_SERVER_ERROR",
            custom_message=f"Failed to retrieve rate limit status: {str(e)}",
            request_id=request_id
        )
        return JSONResponse(status_code=500, content=error_response.dict())


@router.post("/rate-limits/{identifier}/reset")
async def reset_rate_limit(
    request: Request,
    identifier: str,
    limit_type: str = Query("global", regex="^(global|user|api_key)$"),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Reset rate limit for an identifier"""
    request_id = getattr(request.state, 'request_id', None)
    
    # Check admin privileges
    if current_user.get("role") not in ["admin", "superadmin"]:
        raise HTTPException(
            status_code=403,
            detail="Admin privileges required"
        )
    
    try:
        limit_type_enum = RateLimitType(limit_type)
        
        success = await rate_limiter.reset_rate_limit(
            identifier=identifier,
            limit_type=limit_type_enum
        )
        
        if not success:
            error_response = create_error_response(
                "RATE_LIMIT_RESET_FAILED",
                custom_message="Failed to reset rate limit",
                request_id=request_id
            )
            return JSONResponse(status_code=500, content=error_response.dict())
        
        # Log security event
        await security_audit.log_security_event(
            event_type=SecurityEventType.SECURITY_CONFIG_CHANGED,
            severity=SecuritySeverity.MEDIUM,
            user_id=current_user.get("username"),
            details={
                "action": "rate_limit_reset",
                "identifier": identifier,
                "limit_type": limit_type
            },
            request_id=request_id
        )
        
        success_response = create_success_response(
            message="Rate limit reset successfully",
            data={
                "identifier": identifier,
                "limit_type": limit_type
            },
            request_id=request_id
        )
        
        return JSONResponse(content=success_response.dict())
        
    except Exception as e:
        error_response = create_error_response(
            "INTERNAL_SERVER_ERROR",
            custom_message=f"Failed to reset rate limit: {str(e)}",
            request_id=request_id
        )
        return JSONResponse(status_code=500, content=error_response.dict())


@router.post("/blacklist/{ip_address}")
async def add_to_blacklist(
    request: Request,
    ip_address: str,
    reason: str = Query(..., description="Reason for blacklisting"),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Add IP address to blacklist"""
    request_id = getattr(request.state, 'request_id', None)
    
    # Check admin privileges
    if current_user.get("role") not in ["admin", "superadmin"]:
        raise HTTPException(
            status_code=403,
            detail="Admin privileges required"
        )
    
    try:
        await rate_limiter.add_to_blacklist(ip_address, reason)
        
        # Log security event
        await security_audit.log_security_event(
            event_type=SecurityEventType.SECURITY_CONFIG_CHANGED,
            severity=SecuritySeverity.HIGH,
            user_id=current_user.get("username"),
            details={
                "action": "ip_blacklisted",
                "ip_address": ip_address,
                "reason": reason
            },
            request_id=request_id
        )
        
        success_response = create_success_response(
            message="IP address blacklisted successfully",
            data={
                "ip_address": ip_address,
                "reason": reason
            },
            request_id=request_id
        )
        
        return JSONResponse(content=success_response.dict())
        
    except Exception as e:
        error_response = create_error_response(
            "INTERNAL_SERVER_ERROR",
            custom_message=f"Failed to blacklist IP: {str(e)}",
            request_id=request_id
        )
        return JSONResponse(status_code=500, content=error_response.dict())


@router.delete("/blacklist/{ip_address}")
async def remove_from_blacklist(
    request: Request,
    ip_address: str,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Remove IP address from blacklist"""
    request_id = getattr(request.state, 'request_id', None)
    
    # Check admin privileges
    if current_user.get("role") not in ["admin", "superadmin"]:
        raise HTTPException(
            status_code=403,
            detail="Admin privileges required"
        )
    
    try:
        await rate_limiter.remove_from_blacklist(ip_address)
        
        # Log security event
        await security_audit.log_security_event(
            event_type=SecurityEventType.SECURITY_CONFIG_CHANGED,
            severity=SecuritySeverity.MEDIUM,
            user_id=current_user.get("username"),
            details={
                "action": "ip_unblacklisted",
                "ip_address": ip_address
            },
            request_id=request_id
        )
        
        success_response = create_success_response(
            message="IP address removed from blacklist successfully",
            data={"ip_address": ip_address},
            request_id=request_id
        )
        
        return JSONResponse(content=success_response.dict())
        
    except Exception as e:
        error_response = create_error_response(
            "INTERNAL_SERVER_ERROR",
            custom_message=f"Failed to remove IP from blacklist: {str(e)}",
            request_id=request_id
        )
        return JSONResponse(status_code=500, content=error_response.dict())


# ==================== ENCRYPTION ENDPOINTS ====================

@router.post("/encryption/generate-api-key")
async def generate_api_key(
    request: Request,
    description: str = Query(..., description="Description for the API key"),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Generate new API key"""
    request_id = getattr(request.state, 'request_id', None)
    
    # Check admin privileges
    if current_user.get("role") not in ["admin", "superadmin"]:
        raise HTTPException(
            status_code=403,
            detail="Admin privileges required"
        )
    
    try:
        # Generate API key
        api_key = encryption_service.generate_api_key()
        api_key_hash = encryption_service.hash_api_key(api_key)
        
        # Log security event
        await security_audit.log_api_security_event(
            event_type=SecurityEventType.API_KEY_CREATED,
            api_key=api_key,
            details={
                "description": description,
                "created_by": current_user.get("username"),
                "hash": api_key_hash
            },
            request_id=request_id
        )
        
        success_response = create_success_response(
            message="API key generated successfully",
            data={
                "api_key": api_key,
                "hash": api_key_hash,
                "description": description,
                "created_at": datetime.utcnow().isoformat()
            },
            request_id=request_id
        )
        
        return JSONResponse(content=success_response.dict())
        
    except Exception as e:
        error_response = create_error_response(
            "INTERNAL_SERVER_ERROR",
            custom_message=f"Failed to generate API key: {str(e)}",
            request_id=request_id
        )
        return JSONResponse(status_code=500, content=error_response.dict())


@router.post("/encryption/rotate-keys")
async def rotate_encryption_keys(
    request: Request,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Rotate encryption keys (requires superadmin)"""
    request_id = getattr(request.state, 'request_id', None)
    
    # Check superadmin privileges
    if current_user.get("role") != "superadmin":
        raise HTTPException(
            status_code=403,
            detail="Superadmin privileges required"
        )
    
    try:
        # This is a placeholder - actual implementation would be more complex
        success = encryption_service.rotate_encryption_keys()
        
        if not success:
            error_response = create_error_response(
                "KEY_ROTATION_FAILED",
                custom_message="Failed to rotate encryption keys",
                request_id=request_id
            )
            return JSONResponse(status_code=500, content=error_response.dict())
        
        success_response = create_success_response(
            message="Encryption keys rotated successfully",
            data={
                "rotated_at": datetime.utcnow().isoformat()
            },
            request_id=request_id
        )
        
        return JSONResponse(content=success_response.dict())
        
    except Exception as e:
        error_response = create_error_response(
            "INTERNAL_SERVER_ERROR",
            custom_message=f"Failed to rotate keys: {str(e)}",
            request_id=request_id
        )
        return JSONResponse(status_code=500, content=error_response.dict())


# ==================== SECURITY CONFIGURATION ENDPOINTS ====================

@router.get("/config")
async def get_security_config(
    request: Request,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get current security configuration"""
    request_id = getattr(request.state, 'request_id', None)
    
    # Check admin privileges
    if current_user.get("role") not in ["admin", "superadmin"]:
        raise HTTPException(
            status_code=403,
            detail="Admin privileges required"
        )
    
    try:
        config = {
            "rate_limiting": {
                "enabled": True,
                "tiers": {
                    "anonymous": rate_limiter.rate_limits.get("anonymous", {}),
                    "basic": rate_limiter.rate_limits.get("basic", {}),
                    "premium": rate_limiter.rate_limits.get("premium", {}),
                    "enterprise": rate_limiter.rate_limits.get("enterprise", {})
                },
                "endpoint_limits": rate_limiter.endpoint_limits
            },
            "encryption": {
                "enabled": True,
                "sensitive_fields": encryption_service.sensitive_fields,
                "algorithm": "AES-GCM + Fernet"
            },
            "security_headers": {
                "enabled": True,
                "hsts": True,
                "csp": True,
                "x_frame_options": "DENY"
            },
            "audit_logging": {
                "enabled": True,
                "retention_days": 90
            }
        }
        
        success_response = create_success_response(
            message="Security configuration retrieved successfully",
            data=config,
            request_id=request_id
        )
        
        return JSONResponse(content=success_response.dict())
        
    except Exception as e:
        error_response = create_error_response(
            "INTERNAL_SERVER_ERROR",
            custom_message=f"Failed to retrieve security config: {str(e)}",
            request_id=request_id
        )
        return JSONResponse(status_code=500, content=error_response.dict()) 