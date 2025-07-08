import json
import sys
from datetime import datetime
from typing import Any, Dict, Optional
from loguru import logger
from pathlib import Path

class JSONFormatter:
    """
    Custom JSON formatter for structured logging
    Converts log records to JSON format for better parsing and analysis
    """
    
    def __init__(self, include_extra: bool = True):
        self.include_extra = include_extra
    
    def format(self, record: Dict[str, Any]) -> str:
        """Format log record as JSON"""
        # Base log structure
        log_entry = {
            "timestamp": record["time"].isoformat(),
            "level": record["level"].name,
            "logger": record["name"],
            "module": record["module"],
            "function": record["function"],
            "line": record["line"],
            "message": record["message"],
            "process_id": record["process"].id,
            "thread_id": record["thread"].id
        }
        
        # Add exception information if present
        if record["exception"]:
            log_entry["exception"] = {
                "type": record["exception"].type.__name__ if record["exception"].type else None,
                "value": str(record["exception"].value) if record["exception"].value else None,
                "traceback": record["exception"].traceback if record["exception"].traceback else None
            }
        
        # Add extra fields from middleware or custom logging
        if self.include_extra and record.get("extra"):
            extra_data = record["extra"]
            
            # Merge extra data into log entry
            for key, value in extra_data.items():
                if key not in log_entry:  # Don't override base fields
                    log_entry[key] = value
        
        # Ensure all values are JSON serializable
        log_entry = self._make_json_serializable(log_entry)
        
        return json.dumps(log_entry, ensure_ascii=False, separators=(',', ':'))
    
    def _make_json_serializable(self, obj: Any) -> Any:
        """Convert objects to JSON serializable format"""
        if isinstance(obj, dict):
            return {key: self._make_json_serializable(value) for key, value in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [self._make_json_serializable(item) for item in obj]
        elif isinstance(obj, datetime):
            return obj.isoformat()
        elif hasattr(obj, '__dict__'):
            return str(obj)
        else:
            try:
                json.dumps(obj)
                return obj
            except (TypeError, ValueError):
                return str(obj)


class StructuredLogger:
    """
    Enhanced structured logger with JSON formatting and multiple outputs
    """
    
    def __init__(self, app_name: str = "opera-panel"):
        self.app_name = app_name
        self.json_formatter = JSONFormatter()
        self._setup_loggers()
    
    def _setup_loggers(self):
        """Setup structured logging configuration"""
        # Remove default logger
        logger.remove()
        
        # Console logger with simple format for development
        logger.add(
            sys.stdout,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}",
            level="INFO",
            enqueue=True,
            backtrace=True,
            diagnose=True
        )
        
        # File logger with JSON-like format
        logger.add(
            "logs/app.json",
            format='{{\"time\":\"{time:YYYY-MM-DD HH:mm:ss.SSS}\",\"level\":\"{level}\",\"logger\":\"{name}\",\"function\":\"{function}\",\"line\":{line},\"message\":\"{message}\",\"extra\":{extra}}}',
            level="DEBUG",
            rotation="1 day",
            retention="30 days",
            compression="gz",
            enqueue=True,
            backtrace=True,
            diagnose=True
        )
        
        # Error-specific logger
        logger.add(
            "logs/errors.json",
            format='{{\"time\":\"{time:YYYY-MM-DD HH:mm:ss.SSS}\",\"level\":\"{level}\",\"logger\":\"{name}\",\"function\":\"{function}\",\"line\":{line},\"message\":\"{message}\",\"extra\":{extra}}}',
            level="ERROR",
            rotation="1 day",
            retention="90 days",
            compression="gz",
            enqueue=True,
            backtrace=True,
            diagnose=True
        )
        
        # Security events logger
        logger.add(
            "logs/security.json",
            format='{{\"time\":\"{time:YYYY-MM-DD HH:mm:ss.SSS}\",\"level\":\"{level}\",\"logger\":\"{name}\",\"function\":\"{function}\",\"line\":{line},\"message\":\"{message}\",\"extra\":{extra}}}',
            level="WARNING",
            filter=lambda record: "security" in str(record.get("extra", {})).lower() or record["level"].name in ["WARNING", "ERROR"],
            rotation="1 day",
            retention="180 days",
            compression="gz",
            enqueue=True
        )
        
        # Performance logger
        logger.add(
            "logs/performance.json",
            format='{{\"time\":\"{time:YYYY-MM-DD HH:mm:ss.SSS}\",\"level\":\"{level}\",\"logger\":\"{name}\",\"function\":\"{function}\",\"line\":{line},\"message\":\"{message}\",\"extra\":{extra}}}',
            level="INFO",
            filter=lambda record: "performance" in str(record.get("extra", {})).lower(),
            rotation="1 day",
            retention="7 days",
            compression="gz",
            enqueue=True
        )
    
    def _json_format(self, record: Dict[str, Any]) -> str:
        """JSON format function for loguru"""
        return self.json_formatter.format(record) + "\n"
    
    def _security_filter(self, record: Dict[str, Any]) -> bool:
        """Filter for security-related logs"""
        extra = record.get("extra", {})
        event_type = extra.get("event_type", "")
        return "security" in event_type.lower() or record["level"].name in ["WARNING", "ERROR"]
    
    def _performance_filter(self, record: Dict[str, Any]) -> bool:
        """Filter for performance-related logs"""
        extra = record.get("extra", {})
        event_type = extra.get("event_type", "")
        return "performance" in event_type.lower() or "process_time_ms" in extra
    
    def get_logger(self) -> Any:
        """Get the configured logger instance"""
        return logger


class LoggingContext:
    """
    Context manager for adding structured context to logs
    """
    
    def __init__(self, **context):
        self.context = context
        self.token = None
    
    def __enter__(self):
        self.token = logger.contextualize(**self.context)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.token:
            self.token.__exit__(exc_type, exc_val, exc_tb)


class PerformanceLogger:
    """
    Specialized logger for performance metrics
    """
    
    @staticmethod
    def log_endpoint_performance(
        endpoint: str,
        method: str,
        duration_ms: float,
        status_code: int,
        request_id: Optional[str] = None,
        user_id: Optional[str] = None,
        **additional_metrics
    ):
        """Log endpoint performance metrics"""
        logger.info(
            f"Endpoint performance: {method} {endpoint}",
            extra={
                "event_type": "endpoint_performance",
                "endpoint": endpoint,
                "method": method,
                "duration_ms": duration_ms,
                "status_code": status_code,
                "request_id": request_id,
                "user_id": user_id,
                **additional_metrics
            }
        )
    
    @staticmethod
    def log_database_performance(
        operation: str,
        collection: str,
        duration_ms: float,
        record_count: Optional[int] = None,
        request_id: Optional[str] = None,
        **additional_metrics
    ):
        """Log database operation performance"""
        logger.info(
            f"Database performance: {operation} on {collection}",
            extra={
                "event_type": "database_performance",
                "operation": operation,
                "collection": collection,
                "duration_ms": duration_ms,
                "record_count": record_count,
                "request_id": request_id,
                **additional_metrics
            }
        )


class SecurityLogger:
    """
    Specialized logger for security events
    """
    
    @staticmethod
    def log_authentication_event(
        event_type: str,
        user_id: Optional[str] = None,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        success: bool = True,
        **additional_data
    ):
        """Log authentication-related events"""
        level = "info" if success else "warning"
        getattr(logger, level)(
            f"Authentication event: {event_type}",
            extra={
                "event_type": "authentication",
                "auth_event": event_type,
                "user_id": user_id,
                "client_ip": client_ip,
                "user_agent": user_agent,
                "success": success,
                **additional_data
            }
        )
    
    @staticmethod
    def log_authorization_event(
        resource: str,
        action: str,
        user_id: Optional[str] = None,
        allowed: bool = True,
        reason: Optional[str] = None,
        **additional_data
    ):
        """Log authorization events"""
        level = "info" if allowed else "warning"
        getattr(logger, level)(
            f"Authorization: {action} on {resource}",
            extra={
                "event_type": "authorization",
                "resource": resource,
                "action": action,
                "user_id": user_id,
                "allowed": allowed,
                "reason": reason,
                **additional_data
            }
        )
    
    @staticmethod
    def log_security_violation(
        violation_type: str,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        **additional_data
    ):
        """Log security violations"""
        logger.error(
            f"Security violation: {violation_type}",
            extra={
                "event_type": "security_violation",
                "violation_type": violation_type,
                "client_ip": client_ip,
                "user_agent": user_agent,
                "details": details or {},
                **additional_data
            }
        )


class AuditLogger:
    """
    Specialized logger for audit events (complementing FHIR audit logging)
    """
    
    @staticmethod
    def log_data_access(
        resource_type: str,
        resource_id: str,
        action: str,
        user_id: Optional[str] = None,
        result: str = "success",
        **additional_data
    ):
        """Log data access events"""
        logger.info(
            f"Data access: {action} {resource_type}/{resource_id}",
            extra={
                "event_type": "data_access",
                "resource_type": resource_type,
                "resource_id": resource_id,
                "action": action,
                "user_id": user_id,
                "result": result,
                **additional_data
            }
        )
    
    @staticmethod
    def log_configuration_change(
        component: str,
        change_type: str,
        old_value: Optional[Any] = None,
        new_value: Optional[Any] = None,
        user_id: Optional[str] = None,
        **additional_data
    ):
        """Log configuration changes"""
        logger.warning(
            f"Configuration change: {change_type} in {component}",
            extra={
                "event_type": "configuration_change",
                "component": component,
                "change_type": change_type,
                "old_value": str(old_value) if old_value is not None else None,
                "new_value": str(new_value) if new_value is not None else None,
                "user_id": user_id,
                **additional_data
            }
        )


# Global structured logger instance
structured_logger = StructuredLogger()
performance_logger = PerformanceLogger()
security_logger = SecurityLogger()
audit_logger_structured = AuditLogger()

# Helper functions for easy import
def get_structured_logger():
    """Get the structured logger instance"""
    return structured_logger.get_logger()

def get_logger(name=None):
    """Get the logger instance (alias for compatibility)"""
    return structured_logger.get_logger()

def log_with_context(**context):
    """Create a logging context"""
    return LoggingContext(**context) 