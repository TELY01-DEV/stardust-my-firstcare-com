"""
Hash Audit Log Service
=====================
Comprehensive audit logging system for blockchain hash operations.
Tracks all hash transactions, verifications, and related activities
for compliance, forensic analysis, and operational monitoring.

Features:
- Complete transaction trail logging
- Operation type tracking and categorization
- Performance metrics and timing data
- User attribution and source tracking
- Integrity verification audit trails
- Compliance reporting capabilities
"""

import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from dataclasses import dataclass
from bson import ObjectId

from app.services.mongo import mongodb_service
from app.utils.structured_logging import get_logger

logger = get_logger(__name__)

class HashAuditOperation(str, Enum):
    """Types of hash audit operations"""
    HASH_GENERATE = "hash_generate"
    HASH_VERIFY = "hash_verify"
    HASH_UPDATE = "hash_update"
    BATCH_GENERATE = "batch_generate"
    BATCH_VERIFY = "batch_verify"
    CHAIN_VERIFY = "chain_verify"
    CHAIN_EXPORT = "chain_export"
    CHAIN_IMPORT = "chain_import"
    MERKLE_COMPUTE = "merkle_compute"
    INTEGRITY_CHECK = "integrity_check"
    RESOURCE_CREATE = "resource_create"
    RESOURCE_UPDATE = "resource_update"
    RESOURCE_DELETE = "resource_delete"

class HashAuditStatus(str, Enum):
    """Status of hash audit operations"""
    SUCCESS = "success"
    FAILURE = "failure"
    WARNING = "warning"
    IN_PROGRESS = "in_progress"
    CANCELLED = "cancelled"

class HashAuditSeverity(str, Enum):
    """Severity levels for audit events"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class HashAuditMetrics:
    """Performance and operational metrics for hash operations"""
    execution_time_ms: Optional[float] = None
    hash_computation_time_ms: Optional[float] = None
    verification_time_ms: Optional[float] = None
    resources_processed: Optional[int] = None
    hashes_generated: Optional[int] = None
    hashes_verified: Optional[int] = None
    chain_length_before: Optional[int] = None
    chain_length_after: Optional[int] = None
    memory_usage_mb: Optional[float] = None
    cpu_usage_percent: Optional[float] = None

@dataclass
class HashAuditContext:
    """Contextual information for hash operations"""
    fhir_resource_type: Optional[str] = None
    fhir_resource_id: Optional[str] = None
    fhir_resource_version: Optional[str] = None
    patient_id: Optional[str] = None
    organization_id: Optional[str] = None
    device_id: Optional[str] = None
    encounter_id: Optional[str] = None
    batch_id: Optional[str] = None
    batch_size: Optional[int] = None
    source_system: Optional[str] = None
    source_ip: Optional[str] = None
    user_agent: Optional[str] = None
    session_id: Optional[str] = None

class HashAuditLogService:
    """Service for comprehensive hash audit logging and trail management"""
    
    def __init__(self):
        self.collection_name = "hash_audit_logs"
        self.indexes_created = False
        
    async def _ensure_indexes(self):
        """Ensure proper indexes exist for audit log collection"""
        if self.indexes_created:
            return
            
        try:
            collection = mongodb_service.get_collection(self.collection_name)
            
            # Create indexes for efficient querying
            await collection.create_index("timestamp")
            await collection.create_index("operation_type")
            await collection.create_index("status")
            await collection.create_index("user_id")
            await collection.create_index("fhir_resource_type")
            await collection.create_index("fhir_resource_id")
            await collection.create_index("patient_id")
            await collection.create_index("blockchain_hash")
            await collection.create_index("previous_hash")
            await collection.create_index("severity")
            await collection.create_index([("timestamp", -1), ("operation_type", 1)])
            await collection.create_index([("fhir_resource_type", 1), ("timestamp", -1)])
            await collection.create_index([("user_id", 1), ("timestamp", -1)])
            
            self.indexes_created = True
            logger.info("Hash audit log indexes created successfully")
            
        except Exception as e:
            logger.error(f"Failed to create hash audit log indexes: {e}")
    
    async def log_hash_operation(
        self,
        operation_type: HashAuditOperation,
        status: HashAuditStatus,
        blockchain_hash: Optional[str] = None,
        previous_hash: Optional[str] = None,
        user_id: Optional[str] = None,
        request_id: Optional[str] = None,
        message: Optional[str] = None,
        error_details: Optional[Dict[str, Any]] = None,
        metrics: Optional[HashAuditMetrics] = None,
        context: Optional[HashAuditContext] = None,
        severity: HashAuditSeverity = HashAuditSeverity.LOW,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """Log a hash operation with comprehensive details"""
        try:
            await self._ensure_indexes()
            
            # Generate unique audit log ID
            audit_id = str(uuid.uuid4())
            timestamp = datetime.utcnow()
            
            # Create audit log entry
            audit_entry = {
                "_id": audit_id,
                "audit_id": audit_id,
                "timestamp": timestamp,
                "operation_type": operation_type.value,
                "status": status.value,
                "severity": severity.value,
                "message": message or f"{operation_type.value} operation",
                
                # Hash information
                "blockchain_hash": blockchain_hash,
                "previous_hash": previous_hash,
                "hash_length": len(blockchain_hash) if blockchain_hash else None,
                
                # Request and user context
                "user_id": user_id,
                "request_id": request_id or str(uuid.uuid4()),
                "session_id": context.session_id if context else None,
                
                # Error information
                "error_details": error_details,
                "has_error": error_details is not None,
                
                # Performance metrics
                "metrics": {
                    "execution_time_ms": metrics.execution_time_ms if metrics else None,
                    "hash_computation_time_ms": metrics.hash_computation_time_ms if metrics else None,
                    "verification_time_ms": metrics.verification_time_ms if metrics else None,
                    "resources_processed": metrics.resources_processed if metrics else None,
                    "hashes_generated": metrics.hashes_generated if metrics else None,
                    "hashes_verified": metrics.hashes_verified if metrics else None,
                    "chain_length_before": metrics.chain_length_before if metrics else None,
                    "chain_length_after": metrics.chain_length_after if metrics else None,
                    "memory_usage_mb": metrics.memory_usage_mb if metrics else None,
                    "cpu_usage_percent": metrics.cpu_usage_percent if metrics else None
                } if metrics else {},
                
                # FHIR context
                "fhir_resource_type": context.fhir_resource_type if context else None,
                "fhir_resource_id": context.fhir_resource_id if context else None,
                "fhir_resource_version": context.fhir_resource_version if context else None,
                "patient_id": context.patient_id if context else None,
                "organization_id": context.organization_id if context else None,
                "device_id": context.device_id if context else None,
                "encounter_id": context.encounter_id if context else None,
                
                # Batch context
                "batch_id": context.batch_id if context else None,
                "batch_size": context.batch_size if context else None,
                
                # Source context
                "source_system": context.source_system if context else None,
                "source_ip": context.source_ip if context else None,
                "user_agent": context.user_agent if context else None,
                
                # Additional data
                "additional_data": additional_data or {},
                
                # Audit metadata
                "audit_version": "1.0",
                "retention_policy": "7_years",  # Healthcare compliance
                "compliance_tags": ["HIPAA", "SOX", "GDPR"],
                
                # Computed fields for analytics
                "hour_of_day": timestamp.hour,
                "day_of_week": timestamp.weekday(),
                "month": timestamp.month,
                "year": timestamp.year,
                "is_business_hours": 9 <= timestamp.hour <= 17,
                "is_weekend": timestamp.weekday() >= 5
            }
            
            # Store audit log
            collection = mongodb_service.get_collection(self.collection_name)
            await collection.insert_one(audit_entry)
            
            # Log to application logger as well
            log_level = "error" if status == HashAuditStatus.FAILURE else "info"
            getattr(logger, log_level)(
                f"Hash audit: {operation_type.value} - {status.value} - "
                f"Resource: {context.fhir_resource_type if context else 'N/A'} - "
                f"Hash: {blockchain_hash[:16] if blockchain_hash else 'N/A'}... - "
                f"User: {user_id or 'system'}"
            )
            
            return audit_id
            
        except Exception as e:
            logger.error(f"Failed to log hash audit operation: {e}")
            # Don't raise exception to avoid breaking main operations
            return str(uuid.uuid4())  # Return dummy ID
    
    async def get_audit_logs(
        self,
        filters: Optional[Dict[str, Any]] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        operation_types: Optional[List[HashAuditOperation]] = None,
        status_filter: Optional[List[HashAuditStatus]] = None,
        severity_filter: Optional[List[HashAuditSeverity]] = None,
        user_id: Optional[str] = None,
        fhir_resource_type: Optional[str] = None,
        fhir_resource_id: Optional[str] = None,
        patient_id: Optional[str] = None,
        blockchain_hash: Optional[str] = None,
        has_errors_only: bool = False,
        limit: int = 1000,
        offset: int = 0,
        sort_by: str = "timestamp",
        sort_order: int = -1
    ) -> Dict[str, Any]:
        """Query audit logs with comprehensive filtering options"""
        try:
            await self._ensure_indexes()
            collection = mongodb_service.get_collection(self.collection_name)
            
            # Build query
            query = {}
            
            # Date range filter
            if start_date or end_date:
                date_filter = {}
                if start_date:
                    date_filter["$gte"] = start_date
                if end_date:
                    date_filter["$lte"] = end_date
                query["timestamp"] = date_filter
            
            # Operation type filter
            if operation_types:
                query["operation_type"] = {"$in": [op.value for op in operation_types]}
            
            # Status filter
            if status_filter:
                query["status"] = {"$in": [status.value for status in status_filter]}
            
            # Severity filter
            if severity_filter:
                query["severity"] = {"$in": [sev.value for sev in severity_filter]}
            
            # User filter
            if user_id:
                query["user_id"] = user_id
            
            # FHIR resource filters
            if fhir_resource_type:
                query["fhir_resource_type"] = fhir_resource_type
            
            if fhir_resource_id:
                query["fhir_resource_id"] = fhir_resource_id
            
            if patient_id:
                query["patient_id"] = patient_id
            
            if blockchain_hash:
                query["blockchain_hash"] = blockchain_hash
            
            # Error filter
            if has_errors_only:
                query["has_error"] = True
            
            # Additional filters
            if filters:
                query.update(filters)
            
            # Count total results
            total_count = await collection.count_documents(query)
            
            # Execute query with pagination
            cursor = collection.find(query)
            cursor = cursor.sort(sort_by, sort_order)
            cursor = cursor.skip(offset).limit(limit)
            
            logs = await cursor.to_list(length=limit)
            
            # Convert ObjectId and datetime for JSON serialization
            for log in logs:
                if "_id" in log and isinstance(log["_id"], ObjectId):
                    log["_id"] = str(log["_id"])
                if "timestamp" in log and isinstance(log["timestamp"], datetime):
                    log["timestamp"] = log["timestamp"].isoformat() + "Z"
            
            return {
                "total_count": total_count,
                "returned_count": len(logs),
                "offset": offset,
                "limit": limit,
                "logs": logs,
                "has_more": total_count > offset + len(logs)
            }
            
        except Exception as e:
            logger.error(f"Failed to query audit logs: {e}")
            raise
    
    async def get_audit_statistics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        group_by: str = "operation_type"
    ) -> Dict[str, Any]:
        """Get audit log statistics and analytics"""
        try:
            await self._ensure_indexes()
            collection = mongodb_service.get_collection(self.collection_name)
            
            # Build match stage for date filtering
            match_stage = {}
            if start_date or end_date:
                date_filter = {}
                if start_date:
                    date_filter["$gte"] = start_date
                if end_date:
                    date_filter["$lte"] = end_date
                match_stage["timestamp"] = date_filter
            
            # Aggregation pipeline for statistics
            pipeline = []
            
            if match_stage:
                pipeline.append({"$match": match_stage})
            
            # Group by specified field
            group_stage = {
                "$group": {
                    "_id": f"${group_by}",
                    "count": {"$sum": 1},
                    "success_count": {
                        "$sum": {"$cond": [{"$eq": ["$status", "success"]}, 1, 0]}
                    },
                    "failure_count": {
                        "$sum": {"$cond": [{"$eq": ["$status", "failure"]}, 1, 0]}
                    },
                    "avg_execution_time": {"$avg": "$metrics.execution_time_ms"},
                    "max_execution_time": {"$max": "$metrics.execution_time_ms"},
                    "min_execution_time": {"$min": "$metrics.execution_time_ms"},
                    "total_resources_processed": {"$sum": "$metrics.resources_processed"},
                    "total_hashes_generated": {"$sum": "$metrics.hashes_generated"},
                    "total_hashes_verified": {"$sum": "$metrics.hashes_verified"}
                }
            }
            pipeline.append(group_stage)
            
            # Sort by count descending
            pipeline.append({"$sort": {"count": -1}})
            
            results = await collection.aggregate(pipeline).to_list(length=None)
            
            # Overall statistics
            total_pipeline = []
            if match_stage:
                total_pipeline.append({"$match": match_stage})
            
            total_pipeline.append({
                "$group": {
                    "_id": None,
                    "total_operations": {"$sum": 1},
                    "total_success": {
                        "$sum": {"$cond": [{"$eq": ["$status", "success"]}, 1, 0]}
                    },
                    "total_failures": {
                        "$sum": {"$cond": [{"$eq": ["$status", "failure"]}, 1, 0]}
                    },
                    "avg_execution_time": {"$avg": "$metrics.execution_time_ms"},
                    "unique_users": {"$addToSet": "$user_id"},
                    "unique_resources": {"$addToSet": "$fhir_resource_id"},
                    "date_range": {
                        "$push": {
                            "min": {"$min": "$timestamp"},
                            "max": {"$max": "$timestamp"}
                        }
                    }
                }
            })
            
            overall_stats = await collection.aggregate(total_pipeline).to_list(length=1)
            overall = overall_stats[0] if overall_stats else {}
            
            # Calculate success rate
            success_rate = 0
            if overall.get("total_operations", 0) > 0:
                success_rate = (overall.get("total_success", 0) / overall["total_operations"]) * 100
            
            return {
                "grouped_statistics": results,
                "overall_statistics": {
                    "total_operations": overall.get("total_operations", 0),
                    "success_count": overall.get("total_success", 0),
                    "failure_count": overall.get("total_failures", 0),
                    "success_rate_percent": round(success_rate, 2),
                    "average_execution_time_ms": overall.get("avg_execution_time"),
                    "unique_users_count": len(overall.get("unique_users", [])),
                    "unique_resources_count": len(overall.get("unique_resources", []))
                },
                "group_by": group_by,
                "generated_at": datetime.utcnow().isoformat() + "Z"
            }
            
        except Exception as e:
            logger.error(f"Failed to generate audit statistics: {e}")
            raise
    
    async def get_user_audit_trail(
        self,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> Dict[str, Any]:
        """Get comprehensive audit trail for a specific user"""
        try:
            filters = {"user_id": user_id}
            
            result = await self.get_audit_logs(
                filters=filters,
                start_date=start_date,
                end_date=end_date,
                limit=limit,
                sort_by="timestamp",
                sort_order=-1
            )
            
            # Additional user-specific analytics
            collection = mongodb_service.get_collection(self.collection_name)
            
            # User activity summary
            user_stats_pipeline = [
                {"$match": {"user_id": user_id}},
                {"$group": {
                    "_id": None,
                    "total_operations": {"$sum": 1},
                    "operations_by_type": {"$push": "$operation_type"},
                    "first_activity": {"$min": "$timestamp"},
                    "last_activity": {"$max": "$timestamp"},
                    "unique_resources": {"$addToSet": "$fhir_resource_id"},
                    "unique_resource_types": {"$addToSet": "$fhir_resource_type"}
                }}
            ]
            
            user_stats = await collection.aggregate(user_stats_pipeline).to_list(length=1)
            user_summary = user_stats[0] if user_stats else {}
            
            # Count operations by type
            operation_counts = {}
            for op_type in user_summary.get("operations_by_type", []):
                operation_counts[op_type] = operation_counts.get(op_type, 0) + 1
            
            result["user_summary"] = {
                "user_id": user_id,
                "total_operations": user_summary.get("total_operations", 0),
                "first_activity": user_summary.get("first_activity"),
                "last_activity": user_summary.get("last_activity"),
                "unique_resources_accessed": len(user_summary.get("unique_resources", [])),
                "unique_resource_types": len(user_summary.get("unique_resource_types", [])),
                "operations_by_type": operation_counts
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get user audit trail for {user_id}: {e}")
            raise
    
    async def get_resource_audit_trail(
        self,
        fhir_resource_type: str,
        fhir_resource_id: str,
        include_verification_history: bool = True
    ) -> Dict[str, Any]:
        """Get complete audit trail for a specific FHIR resource"""
        try:
            filters = {
                "fhir_resource_type": fhir_resource_type,
                "fhir_resource_id": fhir_resource_id
            }
            
            result = await self.get_audit_logs(
                filters=filters,
                limit=1000,  # Increase limit for complete resource history
                sort_by="timestamp",
                sort_order=1  # Chronological order
            )
            
            # Resource lifecycle analysis
            logs = result["logs"]
            
            lifecycle_events = {
                "creation": None,
                "updates": [],
                "verifications": [],
                "deletions": [],
                "hash_changes": []
            }
            
            previous_hash = None
            
            for log in logs:
                op_type = log.get("operation_type")
                timestamp = log.get("timestamp")
                
                if op_type == "resource_create":
                    lifecycle_events["creation"] = {
                        "timestamp": timestamp,
                        "user_id": log.get("user_id"),
                        "blockchain_hash": log.get("blockchain_hash")
                    }
                elif op_type == "resource_update":
                    lifecycle_events["updates"].append({
                        "timestamp": timestamp,
                        "user_id": log.get("user_id"),
                        "blockchain_hash": log.get("blockchain_hash"),
                        "previous_hash": log.get("previous_hash")
                    })
                elif op_type in ["hash_verify", "integrity_check"]:
                    if include_verification_history:
                        lifecycle_events["verifications"].append({
                            "timestamp": timestamp,
                            "user_id": log.get("user_id"),
                            "status": log.get("status"),
                            "blockchain_hash": log.get("blockchain_hash")
                        })
                elif op_type == "resource_delete":
                    lifecycle_events["deletions"].append({
                        "timestamp": timestamp,
                        "user_id": log.get("user_id")
                    })
                
                # Track hash changes
                current_hash = log.get("blockchain_hash")
                if current_hash and current_hash != previous_hash:
                    lifecycle_events["hash_changes"].append({
                        "timestamp": timestamp,
                        "operation": op_type,
                        "new_hash": current_hash,
                        "previous_hash": previous_hash
                    })
                    previous_hash = current_hash
            
            result["resource_lifecycle"] = {
                "resource_type": fhir_resource_type,
                "resource_id": fhir_resource_id,
                "creation_info": lifecycle_events["creation"],
                "total_updates": len(lifecycle_events["updates"]),
                "total_verifications": len(lifecycle_events["verifications"]),
                "total_deletions": len(lifecycle_events["deletions"]),
                "hash_change_count": len(lifecycle_events["hash_changes"]),
                "lifecycle_events": lifecycle_events
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get resource audit trail for {fhir_resource_type}/{fhir_resource_id}: {e}")
            raise
    
    async def cleanup_old_audit_logs(
        self,
        retention_days: int = 2555,  # 7 years for healthcare compliance
        dry_run: bool = True
    ) -> Dict[str, Any]:
        """Clean up old audit logs according to retention policy"""
        try:
            collection = mongodb_service.get_collection(self.collection_name)
            
            # Calculate cutoff date
            cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
            
            # Query for old logs
            query = {"timestamp": {"$lt": cutoff_date}}
            
            # Count logs to be deleted
            count_to_delete = await collection.count_documents(query)
            
            result = {
                "retention_days": retention_days,
                "cutoff_date": cutoff_date.isoformat() + "Z",
                "logs_to_delete": count_to_delete,
                "dry_run": dry_run
            }
            
            if not dry_run and count_to_delete > 0:
                # Perform actual deletion
                delete_result = await collection.delete_many(query)
                result["deleted_count"] = delete_result.deleted_count
                
                logger.info(f"Cleaned up {delete_result.deleted_count} old audit logs older than {retention_days} days")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to cleanup old audit logs: {e}")
            raise

# Global hash audit log service instance
hash_audit_service = HashAuditLogService() 