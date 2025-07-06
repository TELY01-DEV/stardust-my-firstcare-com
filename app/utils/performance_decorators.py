import time
import functools
from typing import Callable, Any, Optional, Dict
from datetime import datetime
from config import logger


def timing_decorator(
    operation_name: Optional[str] = None,
    log_slow_threshold_ms: float = 1000,
    include_args: bool = False,
    include_result: bool = False
):
    """
    Decorator to measure and log function execution time
    
    Args:
        operation_name: Custom name for the operation (defaults to function name)
        log_slow_threshold_ms: Log warning if execution exceeds this threshold
        include_args: Whether to include function arguments in logs
        include_result: Whether to include function result in logs
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            operation = operation_name or f"{func.__module__}.{func.__name__}"
            
            try:
                result = await func(*args, **kwargs)
                duration_ms = round((time.time() - start_time) * 1000, 2)
                
                # Prepare log data
                log_data = {
                    "event_type": "performance_timing",
                    "operation": operation,
                    "duration_ms": duration_ms,
                    "success": True,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                if include_args:
                    log_data["args"] = str(args)[:200]  # Truncate for safety
                    log_data["kwargs"] = {k: str(v)[:100] for k, v in kwargs.items()}
                
                if include_result:
                    log_data["result_type"] = type(result).__name__
                    if hasattr(result, '__len__'):
                        log_data["result_size"] = len(result)
                
                # Log based on performance
                if duration_ms > log_slow_threshold_ms:
                    logger.warning(
                        f"Slow operation: {operation} took {duration_ms}ms",
                        extra=log_data
                    )
                else:
                    logger.info(
                        f"Operation completed: {operation} in {duration_ms}ms",
                        extra=log_data
                    )
                
                return result
                
            except Exception as e:
                duration_ms = round((time.time() - start_time) * 1000, 2)
                
                logger.error(
                    f"Operation failed: {operation} after {duration_ms}ms",
                    extra={
                        "event_type": "performance_timing",
                        "operation": operation,
                        "duration_ms": duration_ms,
                        "success": False,
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )
                raise
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            operation = operation_name or f"{func.__module__}.{func.__name__}"
            
            try:
                result = func(*args, **kwargs)
                duration_ms = round((time.time() - start_time) * 1000, 2)
                
                # Prepare log data
                log_data = {
                    "event_type": "performance_timing",
                    "operation": operation,
                    "duration_ms": duration_ms,
                    "success": True,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                if include_args:
                    log_data["args"] = str(args)[:200]
                    log_data["kwargs"] = {k: str(v)[:100] for k, v in kwargs.items()}
                
                if include_result:
                    log_data["result_type"] = type(result).__name__
                    if hasattr(result, '__len__'):
                        log_data["result_size"] = len(result)
                
                # Log based on performance
                if duration_ms > log_slow_threshold_ms:
                    logger.warning(
                        f"Slow operation: {operation} took {duration_ms}ms",
                        extra=log_data
                    )
                else:
                    logger.info(
                        f"Operation completed: {operation} in {duration_ms}ms",
                        extra=log_data
                    )
                
                return result
                
            except Exception as e:
                duration_ms = round((time.time() - start_time) * 1000, 2)
                
                logger.error(
                    f"Operation failed: {operation} after {duration_ms}ms",
                    extra={
                        "event_type": "performance_timing",
                        "operation": operation,
                        "duration_ms": duration_ms,
                        "success": False,
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )
                raise
        
        # Return appropriate wrapper based on function type
        if hasattr(func, '__code__') and func.__code__.co_flags & 0x80:  # CO_COROUTINE
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def database_timing(
    collection_name: Optional[str] = None,
    operation_type: Optional[str] = None,
    slow_threshold_ms: float = 500
):
    """
    Specialized decorator for database operations
    
    Args:
        collection_name: MongoDB collection name
        operation_type: Type of operation (find, insert, update, delete)
        slow_threshold_ms: Threshold for slow query warnings
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                duration_ms = round((time.time() - start_time) * 1000, 2)
                
                # Extract result metadata
                result_count = None
                if hasattr(result, 'inserted_id'):
                    result_count = 1
                elif hasattr(result, 'inserted_ids'):
                    result_count = len(result.inserted_ids)
                elif hasattr(result, 'modified_count'):
                    result_count = result.modified_count
                elif hasattr(result, 'deleted_count'):
                    result_count = result.deleted_count
                elif isinstance(result, list):
                    result_count = len(result)
                
                log_data = {
                    "event_type": "database_performance",
                    "operation": operation_type or func.__name__,
                    "collection": collection_name or "unknown",
                    "duration_ms": duration_ms,
                    "success": True,
                    "record_count": result_count,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                if duration_ms > slow_threshold_ms:
                    logger.warning(
                        f"Slow database query: {log_data['operation']} on {log_data['collection']} took {duration_ms}ms",
                        extra=log_data
                    )
                else:
                    logger.debug(
                        f"Database operation: {log_data['operation']} on {log_data['collection']} in {duration_ms}ms",
                        extra=log_data
                    )
                
                return result
                
            except Exception as e:
                duration_ms = round((time.time() - start_time) * 1000, 2)
                
                logger.error(
                    f"Database operation failed: {operation_type or func.__name__} on {collection_name or 'unknown'}",
                    extra={
                        "event_type": "database_performance",
                        "operation": operation_type or func.__name__,
                        "collection": collection_name or "unknown",
                        "duration_ms": duration_ms,
                        "success": False,
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )
                raise
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                duration_ms = round((time.time() - start_time) * 1000, 2)
                
                log_data = {
                    "event_type": "database_performance",
                    "operation": operation_type or func.__name__,
                    "collection": collection_name or "unknown",
                    "duration_ms": duration_ms,
                    "success": True,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                if duration_ms > slow_threshold_ms:
                    logger.warning(
                        f"Slow database operation: {log_data['operation']} on {log_data['collection']} took {duration_ms}ms",
                        extra=log_data
                    )
                else:
                    logger.debug(
                        f"Database operation: {log_data['operation']} on {log_data['collection']} in {duration_ms}ms",
                        extra=log_data
                    )
                
                return result
                
            except Exception as e:
                duration_ms = round((time.time() - start_time) * 1000, 2)
                
                logger.error(
                    f"Database operation failed: {operation_type or func.__name__} on {collection_name or 'unknown'}",
                    extra={
                        "event_type": "database_performance",
                        "operation": operation_type or func.__name__,
                        "collection": collection_name or "unknown",
                        "duration_ms": duration_ms,
                        "success": False,
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )
                raise
        
        # Return appropriate wrapper based on function type
        if hasattr(func, '__code__') and func.__code__.co_flags & 0x80:  # CO_COROUTINE
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def api_endpoint_timing(
    endpoint_name: Optional[str] = None,
    slow_threshold_ms: float = 2000
):
    """
    Decorator for API endpoint performance monitoring
    
    Args:
        endpoint_name: Custom endpoint name
        slow_threshold_ms: Threshold for slow endpoint warnings
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            endpoint = endpoint_name or func.__name__
            
            try:
                result = await func(*args, **kwargs)
                duration_ms = round((time.time() - start_time) * 1000, 2)
                
                # Extract status code if available
                status_code = None
                if hasattr(result, 'status_code'):
                    status_code = result.status_code
                elif isinstance(result, dict) and 'status_code' in result:
                    status_code = result['status_code']
                
                log_data = {
                    "event_type": "endpoint_performance",
                    "endpoint": endpoint,
                    "duration_ms": duration_ms,
                    "status_code": status_code,
                    "success": True,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                if duration_ms > slow_threshold_ms:
                    logger.warning(
                        f"Slow API endpoint: {endpoint} took {duration_ms}ms",
                        extra=log_data
                    )
                else:
                    logger.info(
                        f"API endpoint: {endpoint} completed in {duration_ms}ms",
                        extra=log_data
                    )
                
                return result
                
            except Exception as e:
                duration_ms = round((time.time() - start_time) * 1000, 2)
                
                logger.error(
                    f"API endpoint failed: {endpoint} after {duration_ms}ms",
                    extra={
                        "event_type": "endpoint_performance",
                        "endpoint": endpoint,
                        "duration_ms": duration_ms,
                        "success": False,
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )
                raise
        
        return wrapper
    
    return decorator


class PerformanceContext:
    """
    Context manager for measuring performance of code blocks
    """
    
    def __init__(self, operation_name: str, log_threshold_ms: float = 1000):
        self.operation_name = operation_name
        self.log_threshold_ms = log_threshold_ms
        self.start_time = None
        self.duration_ms = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.duration_ms = round((time.time() - self.start_time) * 1000, 2)
        
        if exc_type is None:
            # Success case
            log_data = {
                "event_type": "performance_timing",
                "operation": self.operation_name,
                "duration_ms": self.duration_ms,
                "success": True,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            if self.duration_ms > self.log_threshold_ms:
                logger.warning(
                    f"Slow operation: {self.operation_name} took {self.duration_ms}ms",
                    extra=log_data
                )
            else:
                logger.debug(
                    f"Operation completed: {self.operation_name} in {self.duration_ms}ms",
                    extra=log_data
                )
        else:
            # Error case
            logger.error(
                f"Operation failed: {self.operation_name} after {self.duration_ms}ms",
                extra={
                    "event_type": "performance_timing",
                    "operation": self.operation_name,
                    "duration_ms": self.duration_ms,
                    "success": False,
                    "error_type": exc_type.__name__ if exc_type else None,
                    "error_message": str(exc_val) if exc_val else None,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )


class PerformanceMonitor:
    """
    Class for collecting and reporting performance metrics
    """
    
    def __init__(self):
        self.metrics = {}
    
    def record_timing(self, operation: str, duration_ms: float, success: bool = True):
        """Record a timing metric"""
        if operation not in self.metrics:
            self.metrics[operation] = {
                "count": 0,
                "total_time": 0,
                "min_time": float('inf'),
                "max_time": 0,
                "success_count": 0,
                "error_count": 0
            }
        
        metric = self.metrics[operation]
        metric["count"] += 1
        metric["total_time"] += duration_ms
        metric["min_time"] = min(metric["min_time"], duration_ms)
        metric["max_time"] = max(metric["max_time"], duration_ms)
        
        if success:
            metric["success_count"] += 1
        else:
            metric["error_count"] += 1
    
    def get_summary(self) -> Dict[str, Any]:
        """Get performance summary"""
        summary = {}
        
        for operation, metric in self.metrics.items():
            avg_time = metric["total_time"] / metric["count"] if metric["count"] > 0 else 0
            success_rate = metric["success_count"] / metric["count"] if metric["count"] > 0 else 0
            
            summary[operation] = {
                "call_count": metric["count"],
                "average_time_ms": round(avg_time, 2),
                "min_time_ms": metric["min_time"] if metric["min_time"] != float('inf') else 0,
                "max_time_ms": metric["max_time"],
                "success_rate": round(success_rate * 100, 2),
                "error_count": metric["error_count"]
            }
        
        return summary
    
    def log_summary(self):
        """Log performance summary"""
        summary = self.get_summary()
        
        logger.info(
            "Performance summary",
            extra={
                "event_type": "performance_summary",
                "metrics": summary,
                "timestamp": datetime.utcnow().isoformat()
            }
        )


# Global performance monitor instance
performance_monitor = PerformanceMonitor() 