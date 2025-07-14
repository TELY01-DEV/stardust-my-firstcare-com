from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from enum import Enum
import hashlib
import json
from bson import ObjectId
from app.services.mongo import mongodb_service
from app.services.realtime_events import realtime_events
from config import logger, settings

class SecurityEventType(Enum):
    """Security event types for audit logging"""
    # Authentication events
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILED = "login_failed"
    LOGOUT = "logout"
    TOKEN_REFRESH = "token_refresh"
    TOKEN_EXPIRED = "token_expired"
    TOKEN_INVALID = "token_invalid"
    
    # Authorization events
    ACCESS_GRANTED = "access_granted"
    ACCESS_DENIED = "access_denied"
    PERMISSION_CHANGED = "permission_changed"
    ROLE_CHANGED = "role_changed"
    
    # Data access events
    DATA_READ = "data_read"
    DATA_CREATED = "data_created"
    DATA_UPDATED = "data_updated"
    DATA_DELETED = "data_deleted"
    DATA_EXPORTED = "data_exported"
    SENSITIVE_DATA_ACCESS = "sensitive_data_access"
    
    # API security events
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    API_KEY_CREATED = "api_key_created"
    API_KEY_REVOKED = "api_key_revoked"
    
    # System security events
    SECURITY_CONFIG_CHANGED = "security_config_changed"
    ENCRYPTION_KEY_ROTATED = "encryption_key_rotated"
    BACKUP_CREATED = "backup_created"
    SYSTEM_ACCESS = "system_access"
    
    # Threat detection
    BRUTE_FORCE_ATTEMPT = "brute_force_attempt"
    SQL_INJECTION_ATTEMPT = "sql_injection_attempt"
    XSS_ATTEMPT = "xss_attempt"
    UNAUTHORIZED_ACCESS_ATTEMPT = "unauthorized_access_attempt"

class SecuritySeverity(Enum):
    """Security event severity levels"""
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class SecurityAuditLogger:
    """
    Comprehensive security audit logging service
    """
    
    def __init__(self):
        self.collection_name = "security_audit_logs"
        self.alerts_collection = "security_alerts"
        self.failed_login_cache: Dict[str, List[datetime]] = {}
        
    async def log_security_event(
        self,
        event_type: SecurityEventType,
        severity: SecuritySeverity,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None
    ) -> str:
        """Log a security event"""
        try:
            collection = mongodb_service.get_collection(self.collection_name)
            
            # Create security event document
            event_doc = {
                "event_type": event_type.value,
                "severity": severity.value,
                "timestamp": datetime.utcnow(),
                "user_id": user_id,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "details": details or {},
                "request_id": request_id,
                "event_hash": self._generate_event_hash(
                    event_type.value, user_id, ip_address, resource_id
                )
            }
            
            # Insert event
            result = await collection.insert_one(event_doc)
            event_id = str(result.inserted_id)
            
            # Check if alert should be triggered
            await self._check_security_alerts(event_type, severity, event_doc)
            
            # Log to application logger
            logger.info(
                f"Security Event: {event_type.value} | "
                f"Severity: {severity.value} | "
                f"User: {user_id} | "
                f"IP: {ip_address} | "
                f"Resource: {resource_type}/{resource_id}"
            )
            
            return event_id
            
        except Exception as e:
            logger.error(f"Failed to log security event: {e}")
            return ""
    
    async def log_login_attempt(
        self,
        username: str,
        success: bool,
        ip_address: str,
        user_agent: Optional[str] = None,
        failure_reason: Optional[str] = None,
        request_id: Optional[str] = None
    ):
        """Log login attempt"""
        event_type = SecurityEventType.LOGIN_SUCCESS if success else SecurityEventType.LOGIN_FAILED
        severity = SecuritySeverity.INFO if success else SecuritySeverity.MEDIUM
        
        # Track failed login attempts for brute force detection
        if not success:
            await self._track_failed_login(username, ip_address)
        
        await self.log_security_event(
            event_type=event_type,
            severity=severity,
            user_id=username,
            ip_address=ip_address,
            user_agent=user_agent,
            details={
                "success": success,
                "failure_reason": failure_reason
            },
            request_id=request_id
        )
    
    async def log_data_access(
        self,
        action: str,  # read, create, update, delete
        resource_type: str,
        resource_id: str,
        user_id: str,
        ip_address: Optional[str] = None,
        sensitive: bool = False,
        details: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None
    ):
        """Log data access event"""
        event_map = {
            "read": SecurityEventType.DATA_READ,
            "create": SecurityEventType.DATA_CREATED,
            "update": SecurityEventType.DATA_UPDATED,
            "delete": SecurityEventType.DATA_DELETED,
            "export": SecurityEventType.DATA_EXPORTED
        }
        
        event_type = event_map.get(action.lower(), SecurityEventType.DATA_READ)
        
        # Use higher severity for sensitive data
        if sensitive:
            event_type = SecurityEventType.SENSITIVE_DATA_ACCESS
            severity = SecuritySeverity.HIGH
        else:
            severity = SecuritySeverity.INFO if action == "read" else SecuritySeverity.LOW
        
        await self.log_security_event(
            event_type=event_type,
            severity=severity,
            user_id=user_id,
            ip_address=ip_address,
            resource_type=resource_type,
            resource_id=resource_id,
            details={
                "action": action,
                "sensitive": sensitive,
                **(details or {})
            },
            request_id=request_id
        )
    
    async def log_authorization_event(
        self,
        granted: bool,
        user_id: str,
        resource: str,
        permission: str,
        ip_address: Optional[str] = None,
        request_id: Optional[str] = None
    ):
        """Log authorization event"""
        event_type = SecurityEventType.ACCESS_GRANTED if granted else SecurityEventType.ACCESS_DENIED
        severity = SecuritySeverity.INFO if granted else SecuritySeverity.MEDIUM
        
        await self.log_security_event(
            event_type=event_type,
            severity=severity,
            user_id=user_id,
            ip_address=ip_address,
            details={
                "resource": resource,
                "permission": permission,
                "granted": granted
            },
            request_id=request_id
        )
    
    async def log_api_security_event(
        self,
        event_type: SecurityEventType,
        api_key: Optional[str] = None,
        endpoint: Optional[str] = None,
        method: Optional[str] = None,
        ip_address: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None
    ):
        """Log API security event"""
        severity_map = {
            SecurityEventType.RATE_LIMIT_EXCEEDED: SecuritySeverity.MEDIUM,
            SecurityEventType.SUSPICIOUS_ACTIVITY: SecuritySeverity.HIGH,
            SecurityEventType.API_KEY_CREATED: SecuritySeverity.LOW,
            SecurityEventType.API_KEY_REVOKED: SecuritySeverity.MEDIUM
        }
        
        severity = severity_map.get(event_type, SecuritySeverity.MEDIUM)
        
        await self.log_security_event(
            event_type=event_type,
            severity=severity,
            ip_address=ip_address,
            details={
                "api_key": self._mask_api_key(api_key) if api_key else None,
                "endpoint": endpoint,
                "method": method,
                **(details or {})
            },
            request_id=request_id
        )
    
    async def log_threat_detection(
        self,
        threat_type: SecurityEventType,
        ip_address: str,
        user_agent: Optional[str] = None,
        payload: Optional[str] = None,
        endpoint: Optional[str] = None,
        request_id: Optional[str] = None
    ):
        """Log threat detection event"""
        await self.log_security_event(
            event_type=threat_type,
            severity=SecuritySeverity.CRITICAL,
            ip_address=ip_address,
            user_agent=user_agent,
            details={
                "endpoint": endpoint,
                "payload_sample": payload[:200] if payload else None,  # Truncate for safety
                "threat_type": threat_type.value
            },
            request_id=request_id
        )
        
        # Create security alert
        await self._create_security_alert(
            title=f"Threat Detected: {threat_type.value}",
            description=f"Potential {threat_type.value} attempt from IP {ip_address}",
            severity=SecuritySeverity.CRITICAL,
            details={
                "ip_address": ip_address,
                "endpoint": endpoint,
                "threat_type": threat_type.value
            }
        )
    
    async def get_security_events(
        self,
        event_type: Optional[SecurityEventType] = None,
        severity: Optional[SecuritySeverity] = None,
        user_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        skip: int = 0
    ) -> List[Dict[str, Any]]:
        """Query security events"""
        try:
            collection = mongodb_service.get_collection(self.collection_name)
            
            # Build filter
            filter_query = {}
            
            if event_type:
                filter_query["event_type"] = event_type.value
            
            if severity:
                filter_query["severity"] = severity.value
            
            if user_id:
                filter_query["user_id"] = user_id
            
            if start_date or end_date:
                date_filter = {}
                if start_date:
                    date_filter["$gte"] = start_date
                if end_date:
                    date_filter["$lte"] = end_date
                filter_query["timestamp"] = date_filter
            
            # Query events
            cursor = collection.find(filter_query).sort("timestamp", -1).skip(skip).limit(limit)
            events = await cursor.to_list(length=limit)
            
            return events
            
        except Exception as e:
            logger.error(f"Failed to query security events: {e}")
            return []
    
    async def get_security_summary(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get security events summary"""
        try:
            collection = mongodb_service.get_collection(self.collection_name)
            
            # Default to last 24 hours
            if not start_date:
                start_date = datetime.utcnow() - timedelta(days=1)
            if not end_date:
                end_date = datetime.utcnow()
            
            # Aggregation pipeline
            pipeline = [
                {
                    "$match": {
                        "timestamp": {"$gte": start_date, "$lte": end_date}
                    }
                },
                {
                    "$group": {
                        "_id": {
                            "event_type": "$event_type",
                            "severity": "$severity"
                        },
                        "count": {"$sum": 1}
                    }
                },
                {
                    "$group": {
                        "_id": "$_id.severity",
                        "events": {
                            "$push": {
                                "event_type": "$_id.event_type",
                                "count": "$count"
                            }
                        },
                        "total": {"$sum": "$count"}
                    }
                }
            ]
            
            results = await collection.aggregate(pipeline).to_list(length=None)
            
            # Format summary
            summary = {
                "period": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat()
                },
                "by_severity": {},
                "total_events": 0,
                "top_threats": [],
                "active_alerts": await self._get_active_alerts_count()
            }
            
            for result in results:
                severity = result["_id"]
                summary["by_severity"][severity] = {
                    "total": result["total"],
                    "events": result["events"]
                }
                summary["total_events"] += result["total"]
            
            # Get top threats
            threat_events = [
                SecurityEventType.BRUTE_FORCE_ATTEMPT,
                SecurityEventType.SQL_INJECTION_ATTEMPT,
                SecurityEventType.XSS_ATTEMPT,
                SecurityEventType.UNAUTHORIZED_ACCESS_ATTEMPT
            ]
            
            threat_pipeline = [
                {
                    "$match": {
                        "timestamp": {"$gte": start_date, "$lte": end_date},
                        "event_type": {"$in": [e.value for e in threat_events]}
                    }
                },
                {
                    "$group": {
                        "_id": "$event_type",
                        "count": {"$sum": 1}
                    }
                },
                {"$sort": {"count": -1}},
                {"$limit": 5}
            ]
            
            threats = await collection.aggregate(threat_pipeline).to_list(length=5)
            summary["top_threats"] = threats
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to get security summary: {e}")
            return {}
    
    async def _track_failed_login(self, username: str, ip_address: str):
        """Track failed login attempts for brute force detection"""
        key = f"{username}:{ip_address}"
        now = datetime.utcnow()
        
        if key not in self.failed_login_cache:
            self.failed_login_cache[key] = []
        
        # Add current attempt
        self.failed_login_cache[key].append(now)
        
        # Clean old attempts (older than 15 minutes)
        cutoff = now - timedelta(minutes=15)
        self.failed_login_cache[key] = [
            attempt for attempt in self.failed_login_cache[key]
            if attempt > cutoff
        ]
        
        # Check for brute force (5 attempts in 15 minutes)
        if len(self.failed_login_cache[key]) >= 5:
            await self.log_threat_detection(
                threat_type=SecurityEventType.BRUTE_FORCE_ATTEMPT,
                ip_address=ip_address,
                endpoint="/auth/login",
                payload=f"Multiple failed login attempts for user: {username}"
            )
    
    async def _check_security_alerts(
        self,
        event_type: SecurityEventType,
        severity: SecuritySeverity,
        event_doc: Dict[str, Any]
    ):
        """Check if security alert should be triggered"""
        # Alert on critical events
        if severity == SecuritySeverity.CRITICAL:
            await self._create_security_alert(
                title=f"Critical Security Event: {event_type.value}",
                description=f"A critical security event has occurred",
                severity=severity,
                details=event_doc
            )
        
        # Alert on repeated high severity events
        elif severity == SecuritySeverity.HIGH:
            # Check for pattern (3 high severity events in 5 minutes)
            collection = mongodb_service.get_collection(self.collection_name)
            cutoff = datetime.utcnow() - timedelta(minutes=5)
            
            count = await collection.count_documents({
                "event_type": event_type.value,
                "severity": severity.value,
                "timestamp": {"$gte": cutoff}
            })
            
            if count >= 3:
                await self._create_security_alert(
                    title=f"Repeated High Severity Event: {event_type.value}",
                    description=f"Multiple high severity events detected in short time period",
                    severity=severity,
                    details={
                        "event_count": count,
                        "time_period": "5 minutes",
                        "event_type": event_type.value
                    }
                )
    
    async def _create_security_alert(
        self,
        title: str,
        description: str,
        severity: SecuritySeverity,
        details: Dict[str, Any]
    ):
        """Create security alert"""
        try:
            collection = mongodb_service.get_collection(self.alerts_collection)
            
            alert_doc = {
                "title": title,
                "description": description,
                "severity": severity.value,
                "status": "active",
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "details": details,
                "acknowledged": False,
                "acknowledged_by": None,
                "acknowledged_at": None,
                "resolved": False,
                "resolved_by": None,
                "resolved_at": None
            }
            
            result = await collection.insert_one(alert_doc)
            
            # Publish real-time alert
            await realtime_events.publish_system_alert(
                alert_type="security_alert",
                severity=severity.value,
                message=title,
                data={
                    "alert_id": str(result.inserted_id),
                    "details": details
                }
            )
            
            logger.warning(f"Security Alert Created: {title}")
            
        except Exception as e:
            logger.error(f"Failed to create security alert: {e}")
    
    async def acknowledge_alert(self, alert_id: str, user_id: str) -> bool:
        """Acknowledge a security alert"""
        try:
            collection = mongodb_service.get_collection(self.alerts_collection)
            
            result = await collection.update_one(
                {"_id": ObjectId(alert_id), "acknowledged": False},
                {
                    "$set": {
                        "acknowledged": True,
                        "acknowledged_by": user_id,
                        "acknowledged_at": datetime.utcnow(),
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Failed to acknowledge alert: {e}")
            return False
    
    async def resolve_alert(self, alert_id: str, user_id: str, resolution: str) -> bool:
        """Resolve a security alert"""
        try:
            collection = mongodb_service.get_collection(self.alerts_collection)
            
            result = await collection.update_one(
                {"_id": ObjectId(alert_id), "resolved": False},
                {
                    "$set": {
                        "resolved": True,
                        "resolved_by": user_id,
                        "resolved_at": datetime.utcnow(),
                        "resolution": resolution,
                        "status": "resolved",
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Failed to resolve alert: {e}")
            return False
    
    async def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get active security alerts"""
        try:
            collection = mongodb_service.get_collection(self.alerts_collection)
            
            cursor = collection.find(
                {"status": "active"}
            ).sort("created_at", -1)
            
            alerts = await cursor.to_list(length=100)
            return alerts
            
        except Exception as e:
            logger.error(f"Failed to get active alerts: {e}")
            return []
    
    async def _get_active_alerts_count(self) -> int:
        """Get count of active alerts"""
        try:
            collection = mongodb_service.get_collection(self.alerts_collection)
            return await collection.count_documents({"status": "active"})
        except:
            return 0
    
    def _generate_event_hash(self, event_type: str, user_id: str, ip_address: str, resource_id: str) -> str:
        """Generate hash for event deduplication"""
        data = f"{event_type}:{user_id}:{ip_address}:{resource_id}:{datetime.utcnow().strftime('%Y%m%d%H%M')}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]
    
    def _mask_api_key(self, api_key: str) -> str:
        """Mask API key for logging"""
        if not api_key or len(api_key) < 8:
            return "***"
        return f"{api_key[:4]}...{api_key[-4:]}"


# Global security audit logger instance
security_audit = SecurityAuditLogger() 