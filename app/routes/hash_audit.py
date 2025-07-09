"""
Hash Audit Log API Routes
========================
RESTful API endpoints for querying and managing blockchain hash audit logs.
Provides comprehensive audit trail access for compliance, forensic analysis,
and operational monitoring.

Endpoints:
- Query audit logs with advanced filtering
- Get audit statistics and analytics
- User-specific audit trails
- Resource-specific audit trails
- Audit log cleanup and maintenance
"""

import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, Depends, Query, Path, HTTPException, Request
from pydantic import BaseModel, Field

from app.services.auth import require_auth
from app.services.hash_audit_log import (
    hash_audit_service, HashAuditOperation, HashAuditStatus, 
    HashAuditSeverity, HashAuditMetrics, HashAuditContext
)
from app.utils.performance_decorators import api_endpoint_timing
from app.utils.structured_logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/audit/hash", tags=["Hash Audit"])

# =============== Request/Response Models ===============

class AuditLogQuery(BaseModel):
    """Query parameters for audit log search"""
    start_date: Optional[datetime] = Field(None, description="Start date for filtering")
    end_date: Optional[datetime] = Field(None, description="End date for filtering")
    operation_types: Optional[List[HashAuditOperation]] = Field(None, description="Filter by operation types")
    status_filter: Optional[List[HashAuditStatus]] = Field(None, description="Filter by status")
    severity_filter: Optional[List[HashAuditSeverity]] = Field(None, description="Filter by severity")
    user_id: Optional[str] = Field(None, description="Filter by user ID")
    fhir_resource_type: Optional[str] = Field(None, description="Filter by FHIR resource type")
    fhir_resource_id: Optional[str] = Field(None, description="Filter by FHIR resource ID")
    patient_id: Optional[str] = Field(None, description="Filter by patient ID")
    blockchain_hash: Optional[str] = Field(None, description="Filter by blockchain hash")
    has_errors_only: bool = Field(False, description="Show only logs with errors")
    limit: int = Field(100, ge=1, le=1000, description="Maximum number of results")
    offset: int = Field(0, ge=0, description="Offset for pagination")
    sort_by: str = Field("timestamp", description="Field to sort by")
    sort_order: int = Field(-1, description="Sort order: 1 for ascending, -1 for descending")

class CleanupRequest(BaseModel):
    """Request for audit log cleanup"""
    retention_days: int = Field(2555, ge=1, le=3650, description="Retention period in days (default 7 years)")
    dry_run: bool = Field(True, description="Perform dry run without actual deletion")

# =============== Audit Log Query Endpoints ===============

@router.get("/logs", summary="Query Audit Logs")
@api_endpoint_timing("hash_audit_query_logs")
async def query_audit_logs(
    start_date: Optional[datetime] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[datetime] = Query(None, description="End date (ISO format)"),
    operation_types: Optional[str] = Query(None, description="Comma-separated operation types"),
    status_filter: Optional[str] = Query(None, description="Comma-separated status values"),
    severity_filter: Optional[str] = Query(None, description="Comma-separated severity levels"),
    user_id: Optional[str] = Query(None, description="User ID"),
    fhir_resource_type: Optional[str] = Query(None, description="FHIR resource type"),
    fhir_resource_id: Optional[str] = Query(None, description="FHIR resource ID"),
    patient_id: Optional[str] = Query(None, description="Patient ID"),
    blockchain_hash: Optional[str] = Query(None, description="Blockchain hash"),
    has_errors_only: bool = Query(False, description="Show only error logs"),
    limit: int = Query(100, ge=1, le=1000, description="Limit results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    sort_by: str = Query("timestamp", description="Sort field"),
    sort_order: int = Query(-1, description="Sort order"),
    request: Request = None,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Query audit logs with comprehensive filtering options"""
    try:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        # Parse comma-separated lists
        parsed_operation_types = None
        if operation_types:
            try:
                parsed_operation_types = [HashAuditOperation(op.strip()) for op in operation_types.split(",")]
            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"Invalid operation type: {e}")
        
        parsed_status_filter = None
        if status_filter:
            try:
                parsed_status_filter = [HashAuditStatus(status.strip()) for status in status_filter.split(",")]
            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"Invalid status: {e}")
        
        parsed_severity_filter = None
        if severity_filter:
            try:
                parsed_severity_filter = [HashAuditSeverity(sev.strip()) for sev in severity_filter.split(",")]
            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"Invalid severity: {e}")
        
        # Query audit logs
        result = await hash_audit_service.get_audit_logs(
            start_date=start_date,
            end_date=end_date,
            operation_types=parsed_operation_types,
            status_filter=parsed_status_filter,
            severity_filter=parsed_severity_filter,
            user_id=user_id,
            fhir_resource_type=fhir_resource_type,
            fhir_resource_id=fhir_resource_id,
            patient_id=patient_id,
            blockchain_hash=blockchain_hash,
            has_errors_only=has_errors_only,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        # Add request metadata
        result["request_metadata"] = {
            "request_id": request_id,
            "requested_by": current_user.get("user_id"),
            "requested_at": datetime.utcnow().isoformat() + "Z",
            "query_parameters": {
                "start_date": start_date.isoformat() + "Z" if start_date else None,
                "end_date": end_date.isoformat() + "Z" if end_date else None,
                "operation_types": operation_types,
                "status_filter": status_filter,
                "severity_filter": severity_filter,
                "user_id": user_id,
                "fhir_resource_type": fhir_resource_type,
                "fhir_resource_id": fhir_resource_id,
                "patient_id": patient_id,
                "blockchain_hash": blockchain_hash,
                "has_errors_only": has_errors_only,
                "limit": limit,
                "offset": offset,
                "sort_by": sort_by,
                "sort_order": sort_order
            }
        }
        
        logger.info(f"Hash audit logs queried - Request: {request_id}, Results: {result['returned_count']}, User: {current_user.get('user_id')}")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to query audit logs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to query audit logs: {str(e)}")

@router.get("/statistics", summary="Get Audit Statistics")
@api_endpoint_timing("hash_audit_statistics")
async def get_audit_statistics(
    start_date: Optional[datetime] = Query(None, description="Start date for statistics"),
    end_date: Optional[datetime] = Query(None, description="End date for statistics"),
    group_by: str = Query("operation_type", description="Group statistics by field"),
    request: Request = None,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get comprehensive audit log statistics and analytics"""
    try:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        # Validate group_by parameter
        valid_group_fields = [
            "operation_type", "status", "severity", "user_id", 
            "fhir_resource_type", "hour_of_day", "day_of_week"
        ]
        if group_by not in valid_group_fields:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid group_by field. Must be one of: {', '.join(valid_group_fields)}"
            )
        
        # Get statistics
        result = await hash_audit_service.get_audit_statistics(
            start_date=start_date,
            end_date=end_date,
            group_by=group_by
        )
        
        # Add request metadata
        result["request_metadata"] = {
            "request_id": request_id,
            "requested_by": current_user.get("user_id"),
            "requested_at": datetime.utcnow().isoformat() + "Z",
            "parameters": {
                "start_date": start_date.isoformat() + "Z" if start_date else None,
                "end_date": end_date.isoformat() + "Z" if end_date else None,
                "group_by": group_by
            }
        }
        
        logger.info(f"Hash audit statistics generated - Request: {request_id}, User: {current_user.get('user_id')}")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate audit statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate audit statistics: {str(e)}")

@router.get("/users/{user_id}/trail", summary="Get User Audit Trail")
@api_endpoint_timing("hash_audit_user_trail")
async def get_user_audit_trail(
    user_id: str = Path(..., description="User ID to get audit trail for"),
    start_date: Optional[datetime] = Query(None, description="Start date for trail"),
    end_date: Optional[datetime] = Query(None, description="End date for trail"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    request: Request = None,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get comprehensive audit trail for a specific user"""
    try:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        # Authorization check - users can only view their own trail unless admin
        current_user_id = current_user.get("user_id")
        user_role = current_user.get("role", "")
        
        if user_id != current_user_id and not user_role.lower() in ["admin", "super_admin"]:
            raise HTTPException(
                status_code=403, 
                detail="Access denied. Users can only view their own audit trail."
            )
        
        # Get user audit trail
        result = await hash_audit_service.get_user_audit_trail(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )
        
        # Add request metadata
        result["request_metadata"] = {
            "request_id": request_id,
            "requested_by": current_user_id,
            "requested_at": datetime.utcnow().isoformat() + "Z",
            "target_user": user_id,
            "parameters": {
                "start_date": start_date.isoformat() + "Z" if start_date else None,
                "end_date": end_date.isoformat() + "Z" if end_date else None,
                "limit": limit
            }
        }
        
        logger.info(f"User audit trail retrieved - Request: {request_id}, Target: {user_id}, Requester: {current_user_id}")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get user audit trail for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get user audit trail: {str(e)}")

@router.get("/resources/{resource_type}/{resource_id}/trail", summary="Get Resource Audit Trail")
@api_endpoint_timing("hash_audit_resource_trail")
async def get_resource_audit_trail(
    resource_type: str = Path(..., description="FHIR resource type"),
    resource_id: str = Path(..., description="FHIR resource ID"),
    include_verification_history: bool = Query(True, description="Include verification history"),
    request: Request = None,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get complete audit trail for a specific FHIR resource"""
    try:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        # Get resource audit trail
        result = await hash_audit_service.get_resource_audit_trail(
            fhir_resource_type=resource_type,
            fhir_resource_id=resource_id,
            include_verification_history=include_verification_history
        )
        
        # Add request metadata
        result["request_metadata"] = {
            "request_id": request_id,
            "requested_by": current_user.get("user_id"),
            "requested_at": datetime.utcnow().isoformat() + "Z",
            "resource_identifier": f"{resource_type}/{resource_id}",
            "parameters": {
                "include_verification_history": include_verification_history
            }
        }
        
        logger.info(f"Resource audit trail retrieved - Request: {request_id}, Resource: {resource_type}/{resource_id}, User: {current_user.get('user_id')}")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get resource audit trail for {resource_type}/{resource_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get resource audit trail: {str(e)}")

# =============== Audit Log Management Endpoints ===============

@router.post("/cleanup", summary="Cleanup Old Audit Logs")
@api_endpoint_timing("hash_audit_cleanup")
async def cleanup_audit_logs(
    cleanup_request: CleanupRequest,
    request: Request = None,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Clean up old audit logs according to retention policy"""
    try:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        # Authorization check - only admins can cleanup logs
        user_role = current_user.get("role", "")
        if not user_role.lower() in ["admin", "super_admin"]:
            raise HTTPException(
                status_code=403,
                detail="Access denied. Only administrators can cleanup audit logs."
            )
        
        # Perform cleanup
        result = await hash_audit_service.cleanup_old_audit_logs(
            retention_days=cleanup_request.retention_days,
            dry_run=cleanup_request.dry_run
        )
        
        # Add request metadata
        result["request_metadata"] = {
            "request_id": request_id,
            "requested_by": current_user.get("user_id"),
            "requested_at": datetime.utcnow().isoformat() + "Z",
            "parameters": {
                "retention_days": cleanup_request.retention_days,
                "dry_run": cleanup_request.dry_run
            }
        }
        
        action = "dry run" if cleanup_request.dry_run else "cleanup"
        logger.info(f"Audit log {action} performed - Request: {request_id}, Retention: {cleanup_request.retention_days} days, User: {current_user.get('user_id')}")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cleanup audit logs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to cleanup audit logs: {str(e)}")

# =============== Real-time Audit Monitoring Endpoints ===============

@router.get("/recent", summary="Get Recent Audit Activity")
@api_endpoint_timing("hash_audit_recent")
async def get_recent_audit_activity(
    minutes: int = Query(60, ge=1, le=1440, description="Look back time in minutes"),
    operation_types: Optional[str] = Query(None, description="Filter by operation types"),
    severity_filter: Optional[str] = Query(None, description="Filter by severity levels"),
    limit: int = Query(50, ge=1, le=500, description="Maximum results"),
    request: Request = None,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get recent audit activity for monitoring and alerting"""
    try:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        # Calculate time range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(minutes=minutes)
        
        # Parse operation types
        parsed_operation_types = None
        if operation_types:
            try:
                parsed_operation_types = [HashAuditOperation(op.strip()) for op in operation_types.split(",")]
            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"Invalid operation type: {e}")
        
        # Parse severity filter
        parsed_severity_filter = None
        if severity_filter:
            try:
                parsed_severity_filter = [HashAuditSeverity(sev.strip()) for sev in severity_filter.split(",")]
            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"Invalid severity: {e}")
        
        # Query recent logs
        result = await hash_audit_service.get_audit_logs(
            start_date=start_date,
            end_date=end_date,
            operation_types=parsed_operation_types,
            severity_filter=parsed_severity_filter,
            limit=limit,
            offset=0,
            sort_by="timestamp",
            sort_order=-1
        )
        
        # Add monitoring metadata
        result["monitoring_metadata"] = {
            "request_id": request_id,
            "requested_by": current_user.get("user_id"),
            "requested_at": datetime.utcnow().isoformat() + "Z",
            "time_range": {
                "start_date": start_date.isoformat() + "Z",
                "end_date": end_date.isoformat() + "Z",
                "minutes_back": minutes
            },
            "filters": {
                "operation_types": operation_types,
                "severity_filter": severity_filter,
                "limit": limit
            }
        }
        
        # Calculate alert indicators
        error_count = sum(1 for log in result["logs"] if log.get("status") == "failure")
        critical_count = sum(1 for log in result["logs"] if log.get("severity") == "critical")
        
        result["alert_indicators"] = {
            "total_events": result["returned_count"],
            "error_count": error_count,
            "critical_count": critical_count,
            "error_rate_percent": round((error_count / max(result["returned_count"], 1)) * 100, 2),
            "requires_attention": error_count > 0 or critical_count > 0
        }
        
        logger.info(f"Recent audit activity retrieved - Request: {request_id}, Events: {result['returned_count']}, Errors: {error_count}, User: {current_user.get('user_id')}")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get recent audit activity: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get recent audit activity: {str(e)}")

@router.get("/health", summary="Get Audit System Health")
@api_endpoint_timing("hash_audit_health")
async def get_audit_system_health(
    request: Request = None,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get health status of the audit logging system"""
    try:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        # Get basic statistics for health check
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(hours=24)  # Last 24 hours
        
        stats = await hash_audit_service.get_audit_statistics(
            start_date=start_date,
            end_date=end_date,
            group_by="status"
        )
        
        # Calculate health metrics
        total_ops = stats["overall_statistics"]["total_operations"]
        success_rate = stats["overall_statistics"]["success_rate_percent"]
        avg_exec_time = stats["overall_statistics"]["average_execution_time_ms"] or 0
        
        # Determine health status
        health_status = "healthy"
        health_issues = []
        
        if success_rate < 95.0:
            health_status = "degraded"
            health_issues.append(f"Low success rate: {success_rate}%")
        
        if avg_exec_time > 1000:  # > 1 second
            health_status = "degraded"
            health_issues.append(f"High average execution time: {avg_exec_time:.2f}ms")
        
        if total_ops == 0:
            health_status = "warning"
            health_issues.append("No audit operations in last 24 hours")
        
        result = {
            "status": health_status,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "metrics": {
                "total_operations_24h": total_ops,
                "success_rate_percent": success_rate,
                "average_execution_time_ms": avg_exec_time,
                "unique_users_24h": stats["overall_statistics"]["unique_users_count"],
                "unique_resources_24h": stats["overall_statistics"]["unique_resources_count"]
            },
            "issues": health_issues,
            "details": stats["grouped_statistics"],
            "request_metadata": {
                "request_id": request_id,
                "requested_by": current_user.get("user_id"),
                "requested_at": datetime.utcnow().isoformat() + "Z"
            }
        }
        
        logger.info(f"Audit system health check - Request: {request_id}, Status: {health_status}, User: {current_user.get('user_id')}")
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to get audit system health: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get audit system health: {str(e)}")

# =============== Audit Log Export Endpoints ===============

@router.get("/export", summary="Export Audit Logs")
@api_endpoint_timing("hash_audit_export")
async def export_audit_logs(
    start_date: Optional[datetime] = Query(None, description="Export start date"),
    end_date: Optional[datetime] = Query(None, description="Export end date"),
    format: str = Query("json", description="Export format: json, csv"),
    operation_types: Optional[str] = Query(None, description="Filter by operation types"),
    max_records: int = Query(10000, ge=1, le=100000, description="Maximum records to export"),
    request: Request = None,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Export audit logs in various formats for compliance and analysis"""
    try:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        # Authorization check - only admins can export logs
        user_role = current_user.get("role", "")
        if not user_role.lower() in ["admin", "super_admin"]:
            raise HTTPException(
                status_code=403,
                detail="Access denied. Only administrators can export audit logs."
            )
        
        # Validate format
        if format not in ["json", "csv"]:
            raise HTTPException(status_code=400, detail="Invalid format. Must be 'json' or 'csv'")
        
        # Parse operation types
        parsed_operation_types = None
        if operation_types:
            try:
                parsed_operation_types = [HashAuditOperation(op.strip()) for op in operation_types.split(",")]
            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"Invalid operation type: {e}")
        
        # Get audit logs for export
        result = await hash_audit_service.get_audit_logs(
            start_date=start_date,
            end_date=end_date,
            operation_types=parsed_operation_types,
            limit=max_records,
            offset=0,
            sort_by="timestamp",
            sort_order=1  # Chronological order for export
        )
        
        # Add export metadata
        export_metadata = {
            "export_id": str(uuid.uuid4()),
            "exported_by": current_user.get("user_id"),
            "exported_at": datetime.utcnow().isoformat() + "Z",
            "request_id": request_id,
            "parameters": {
                "start_date": start_date.isoformat() + "Z" if start_date else None,
                "end_date": end_date.isoformat() + "Z" if end_date else None,
                "format": format,
                "operation_types": operation_types,
                "max_records": max_records
            },
            "record_count": result["returned_count"],
            "total_available": result["total_count"],
            "truncated": result["total_count"] > max_records
        }
        
        # Format response based on requested format
        if format == "json":
            response_data = {
                "metadata": export_metadata,
                "audit_logs": result["logs"]
            }
        else:  # CSV format - simplified for now, could be enhanced
            response_data = {
                "metadata": export_metadata,
                "message": "CSV export format would be implemented with proper CSV serialization",
                "audit_logs": result["logs"]  # In real implementation, convert to CSV
            }
        
        logger.info(f"Audit logs exported - Request: {request_id}, Format: {format}, Records: {result['returned_count']}, User: {current_user.get('user_id')}")
        
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to export audit logs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to export audit logs: {str(e)}") 