"""
Transaction Logging API Routes
=============================
RESTful API endpoints for logging and querying data processing transactions.
Provides transaction logging for MQTT listeners and data processing operations.

Endpoints:
- Log data processing transactions
- Query transaction logs
- Get transaction statistics
"""

import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, Depends, Query, HTTPException, Request
from pydantic import BaseModel, Field

from app.services.auth import require_auth
from app.services.mongo import mongodb_service
from app.utils.performance_decorators import api_endpoint_timing
from app.utils.structured_logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/transactions", tags=["transaction-logging"])

# =============== Request/Response Models ===============

class TransactionLogRequest(BaseModel):
    """Request model for logging a transaction"""
    operation: str = Field(..., description="Transaction operation type")
    data_type: str = Field(..., description="Type of data processed")
    collection: str = Field(..., description="Target database collection")
    patient_id: Optional[str] = Field(None, description="Patient identifier")
    status: str = Field("success", description="Transaction status")
    details: Optional[str] = Field(None, description="Transaction details")
    device_id: Optional[str] = Field(None, description="Device identifier")

# =============== Transaction Logging Endpoints ===============

@router.post("/log", summary="Log Data Processing Transaction")
@api_endpoint_timing("transaction_log")
async def log_transaction(
    request: Request,
    transaction: TransactionLogRequest,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Log a data processing transaction"""
    try:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        # Prepare transaction document
        transaction_doc = {
            "operation": transaction.operation,
            "data_type": transaction.data_type,
            "collection": transaction.collection,
            "patient_id": transaction.patient_id,
            "status": transaction.status,
            "details": transaction.details,
            "device_id": transaction.device_id,
            "timestamp": datetime.utcnow(),
            "created_at": datetime.utcnow(),
            "logged_by": current_user.get("user_id", "system"),
            "request_id": request_id
        }
        
        # Insert into transaction_logs collection
        collection = mongodb_service.get_collection("transaction_logs")
        result = await collection.insert_one(transaction_doc)
        
        logger.info(f"Transaction logged - ID: {result.inserted_id}, Operation: {transaction.operation}, Data Type: {transaction.data_type}")
        
        return {
            "success": True,
            "message": "Transaction logged successfully",
            "data": {
                "transaction_id": str(result.inserted_id),
                "operation": transaction.operation,
                "data_type": transaction.data_type,
                "timestamp": transaction_doc["timestamp"].isoformat()
            },
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
    except Exception as e:
        logger.error(f"Failed to log transaction: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to log transaction: {str(e)}")

@router.get("/logs", summary="Query Transaction Logs")
@api_endpoint_timing("transaction_query_logs")
async def query_transaction_logs(
    request: Request,
    start_date: Optional[datetime] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[datetime] = Query(None, description="End date (ISO format)"),
    operation: Optional[str] = Query(None, description="Filter by operation"),
    data_type: Optional[str] = Query(None, description="Filter by data type"),
    collection_name: Optional[str] = Query(None, description="Filter by collection"),
    patient_id: Optional[str] = Query(None, description="Filter by patient ID"),
    device_id: Optional[str] = Query(None, description="Filter by device ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(100, ge=1, le=1000, description="Limit results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    sort_by: str = Query("timestamp", description="Sort field"),
    sort_order: int = Query(-1, description="Sort order"),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Query transaction logs with filtering options"""
    try:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        # Build query filter
        query_filter = {}
        
        if start_date or end_date:
            date_filter = {}
            if start_date:
                date_filter["$gte"] = start_date
            if end_date:
                date_filter["$lte"] = end_date
            query_filter["timestamp"] = date_filter
        
        if operation:
            query_filter["operation"] = {"$regex": operation, "$options": "i"}
        
        if data_type:
            query_filter["data_type"] = {"$regex": data_type, "$options": "i"}
        
        if collection_name:
            query_filter["collection"] = {"$regex": collection_name, "$options": "i"}
        
        if patient_id:
            query_filter["patient_id"] = patient_id
        
        if device_id:
            query_filter["device_id"] = device_id
        
        if status:
            query_filter["status"] = status
        
        # Get collection
        transaction_collection = mongodb_service.get_collection("transaction_logs")
        
        # Get total count
        total_count = await transaction_collection.count_documents(query_filter)
        
        # Get transactions with pagination and sorting
        cursor = transaction_collection.find(query_filter)
        cursor = cursor.sort(sort_by, sort_order).skip(offset).limit(limit)
        
        transactions = []
        async for doc in cursor:
            # Convert ObjectId to string
            doc["_id"] = str(doc["_id"])
            # Convert datetime to ISO format
            if "timestamp" in doc:
                doc["timestamp"] = doc["timestamp"].isoformat()
            if "created_at" in doc:
                doc["created_at"] = doc["created_at"].isoformat()
            transactions.append(doc)
        
        return {
            "success": True,
            "message": "Transaction logs retrieved successfully",
            "data": {
                "transactions": transactions,
                "total_count": total_count,
                "returned_count": len(transactions),
                "offset": offset,
                "limit": limit
            },
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
    except Exception as e:
        logger.error(f"Failed to query transaction logs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to query transaction logs: {str(e)}")

@router.get("/statistics", summary="Get Transaction Statistics")
@api_endpoint_timing("transaction_statistics")
async def get_transaction_statistics(
    request: Request,
    start_date: Optional[datetime] = Query(None, description="Start date for statistics"),
    end_date: Optional[datetime] = Query(None, description="End date for statistics"),
    group_by: str = Query("operation", description="Group statistics by field"),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get transaction log statistics and analytics"""
    try:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        # Validate group_by parameter
        valid_group_fields = ["operation", "data_type", "collection", "status", "device_id"]
        if group_by not in valid_group_fields:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid group_by field. Must be one of: {', '.join(valid_group_fields)}"
            )
        
        # Build date filter
        date_filter = {}
        if start_date or end_date:
            if start_date:
                date_filter["$gte"] = start_date
            if end_date:
                date_filter["$lte"] = end_date
        
        # Get collection
        transaction_collection = mongodb_service.get_collection("transaction_logs")
        
        # Build aggregation pipeline
        pipeline = []
        
        if date_filter:
            pipeline.append({"$match": {"timestamp": date_filter}})
        
        pipeline.extend([
            {"$group": {
                "_id": f"${group_by}",
                "count": {"$sum": 1},
                "last_transaction": {"$max": "$timestamp"}
            }},
            {"$sort": {"count": -1}}
        ])
        
        # Execute aggregation
        stats = []
        async for doc in transaction_collection.aggregate(pipeline):
            if "last_transaction" in doc:
                doc["last_transaction"] = doc["last_transaction"].isoformat()
            stats.append(doc)
        
        return {
            "success": True,
            "message": "Transaction statistics retrieved successfully",
            "data": {
                "statistics": stats,
                "group_by": group_by,
                "total_groups": len(stats)
            },
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
    except Exception as e:
        logger.error(f"Failed to get transaction statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get transaction statistics: {str(e)}")

@router.get("/recent", summary="Get Recent Transactions")
@api_endpoint_timing("transaction_recent")
async def get_recent_transactions(
    request: Request,
    minutes: int = Query(60, ge=1, le=1440, description="Look back time in minutes"),
    limit: int = Query(50, ge=1, le=500, description="Maximum results"),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get recent transaction activity"""
    try:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        # Calculate time range
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(minutes=minutes)
        
        # Get collection
        transaction_collection = mongodb_service.get_collection("transaction_logs")
        
        # Query recent transactions
        query_filter = {
            "timestamp": {
                "$gte": start_time,
                "$lte": end_time
            }
        }
        
        cursor = transaction_collection.find(query_filter).sort("timestamp", -1).limit(limit)
        
        transactions = []
        async for doc in cursor:
            # Convert ObjectId to string
            doc["_id"] = str(doc["_id"])
            # Convert datetime to ISO format
            if "timestamp" in doc:
                doc["timestamp"] = doc["timestamp"].isoformat()
            if "created_at" in doc:
                doc["created_at"] = doc["created_at"].isoformat()
            transactions.append(doc)
        
        return {
            "success": True,
            "message": "Recent transactions retrieved successfully",
            "data": {
                "transactions": transactions,
                "time_range": {
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "minutes": minutes
                },
                "count": len(transactions)
            },
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
    except Exception as e:
        logger.error(f"Failed to get recent transactions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get recent transactions: {str(e)}") 