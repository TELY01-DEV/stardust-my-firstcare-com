"""
Kati Transaction API Routes
Provides endpoints for Kati Watch transaction monitoring and statistics
"""

from fastapi import APIRouter, Request, HTTPException, Depends, Query
from fastapi.responses import JSONResponse
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, timezone
from bson import ObjectId
import json

from app.services.mongo import mongodb_service
from app.utils.error_definitions import create_success_response, create_error_response, SuccessResponse, ErrorResponse
from app.utils.structured_logging import get_structured_logger

logger = get_structured_logger()
router = APIRouter(prefix="/api/kati-transactions", tags=["Kati Transaction Monitoring"])

@router.get("/",
    response_model=SuccessResponse,
    responses={
        200: {
            "description": "Kati Watch transaction data with enhanced analysis",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Kati transactions retrieved successfully",
                        "data": {
                            "transactions": [
                                {
                                    "_id": "687a355838cce63787428f27",
                                    "patient_id": "623c133cf9e69c3b67a9af64",
                                    "patient_name": "TELY 01 DEV",
                                    "device_id": "861265061486269",
                                    "device_type": "Kati_Watch",
                                    "topic": "iMEDE_watch/hb",
                                    "event_type": "heartbeat",
                                    "data": {
                                        "step_count": 1158,
                                        "battery": 67,
                                        "signal_gsm": 80,
                                        "working_mode": 1
                                    },
                                    "timestamp": "2025-07-18T11:45:23.456789+00:00",
                                    "status": "success"
                                }
                            ],
                            "statistics": {
                                "total_transactions": 500,
                                "active_devices": 13,
                                "success_rate": 100,
                                "topic_distribution": {
                                    "iMEDE_watch/hb": 341,
                                    "iMEDE_watch/location": 117,
                                    "iMEDE_watch/AP55": 34,
                                    "iMEDE_watch/sleepdata": 28,
                                    "iMEDE_watch/SOS": 2,
                                    "iMEDE_watch/fallDown": 1,
                                    "iMEDE_watch/onlineTrigger": 5
                                },
                                "emergency_count": 3,
                                "last_updated": "2025-07-18T11:51:52.681741+00:00"
                            }
                        },
                        "request_id": "kati-transactions-123",
                        "timestamp": "2025-07-18T11:51:52.681741+00:00"
                    }
                }
            }
        },
        503: {
            "description": "Database connection not available",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "error_count": 1,
                        "errors": [{
                            "error_code": "DATABASE_UNAVAILABLE",
                            "error_type": "system_error",
                            "message": "Database connection not available",
                            "field": None,
                            "value": None,
                            "suggestion": "Please try again later"
                        }],
                        "request_id": "kati-transactions-error-123",
                        "timestamp": "2025-07-18T11:51:52.681741+00:00"
                    }
                }
            }
        }
    })
async def get_kati_transactions(
    request: Request,
    limit: int = Query(500, description="Maximum number of transactions to return", ge=1, le=1000),
    hours: int = Query(24, description="Hours of data to retrieve", ge=1, le=168)
):
    """
    Get Kati Watch transaction data with enhanced analysis
    
    Retrieves Kati Watch device transactions from the last specified hours,
    including both regular medical data and emergency alerts.
    
    **Features:**
    - Last 24 hours of data (configurable)
    - Topic distribution analysis
    - Emergency count tracking
    - Success rate calculation
    - Active device counting
    """
    try:
        # Check if MongoDB connection is available
        if mongodb_service.client is None or mongodb_service.main_db is None:
            return create_error_response(
                error_code="DATABASE_UNAVAILABLE",
                custom_message="Database connection not available",
                request_id=str(request.state.request_id)
            )
        
        # Calculate time range
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=hours)
        
        # Get Kati Watch data from medical_data collection
        medical_data_collection = mongodb_service.main_db.medical_data
        
        # Get Kati Watch transactions
        kati_cursor = medical_data_collection.find({
            'device_type': 'Kati_Watch',
            'timestamp': {'$gte': start_time}
        }).sort('timestamp', -1).limit(limit)
        kati_transactions = await kati_cursor.to_list(length=limit)
        
        # Also get emergency alarms for Kati devices
        emergency_collection = mongodb_service.main_db.emergency_alarm
        emergency_cursor = emergency_collection.find({
            'timestamp': {'$gte': start_time},
            'device_type': 'Kati_Watch'
        }).sort('timestamp', -1).limit(limit // 2 if limit else 250)  # Limit emergency alarms to half the limit
        emergency_alarms = await emergency_cursor.to_list(length=limit // 2 if limit else 250)
        
        # Convert emergency alarms to transaction format
        for alarm in emergency_alarms:
            alarm['_id'] = str(alarm['_id'])
            alarm['topic'] = alarm.get('topic', 'iMEDE_watch/SOS')
            alarm['event_type'] = 'emergency_sos' if 'SOS' in alarm.get('topic', '') else 'fall_detection'
            alarm['status'] = 'success'
            alarm['device_type'] = 'Kati_Watch'
        
        # Combine and sort all transactions
        all_transactions = kati_transactions + emergency_alarms
        all_transactions.sort(key=lambda x: x.get('timestamp', datetime.min), reverse=True)
        
        # Convert ObjectIds to strings
        def convert_objectids(obj):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if isinstance(value, dict):
                        convert_objectids(value)
                    elif isinstance(value, list):
                        for item in value:
                            convert_objectids(item)
                    elif hasattr(value, '__class__') and value.__class__.__name__ == 'ObjectId':
                        obj[key] = str(value)
                    elif hasattr(value, 'isoformat'):  # Handle datetime objects
                        obj[key] = value.isoformat()
            elif isinstance(obj, list):
                for item in obj:
                    convert_objectids(item)
            return obj
        
        all_transactions = convert_objectids(all_transactions)
        
        # Calculate statistics
        statistics = {
            'total_transactions': len(all_transactions),
            'active_devices': len(set(t.get('device_id') for t in all_transactions if t.get('device_id'))),
            'success_rate': 100,  # All stored transactions are successful
            'topic_distribution': {},
            'emergency_count': len(emergency_alarms),
            'last_updated': datetime.now(timezone.utc).isoformat(),
            'time_range': {
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat(),
                'hours': hours
            }
        }
        
        # Calculate topic distribution
        for transaction in all_transactions:
            topic = transaction.get('topic', 'unknown')
            if topic not in statistics['topic_distribution']:
                statistics['topic_distribution'][topic] = 0
            statistics['topic_distribution'][topic] += 1
        
        return create_success_response(
            request_id=str(request.state.request_id),
            message="Kati transactions retrieved successfully",
            data={
                "transactions": all_transactions,
                "statistics": statistics
            }
        )
        
    except Exception as e:
        logger.error(f"Error getting Kati transactions: {e}")
        return create_error_response(
            error_code="KATI_TRANSACTIONS_ERROR",
            custom_message=f"Failed to retrieve Kati transactions: {str(e)}",
            request_id=str(request.state.request_id)
        )

@router.get("/stats",
    response_model=SuccessResponse,
    responses={
        200: {
            "description": "Detailed Kati Watch transaction statistics",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Kati transaction statistics retrieved successfully",
                        "data": {
                            "last_hour": {
                                "transactions": 122,
                                "emergencies": 0
                            },
                            "last_24_hours": {
                                "transactions": 1431,
                                "emergencies": 0
                            },
                            "last_week": {
                                "transactions": 1548,
                                "emergencies": 0
                            },
                            "active_devices": 13,
                            "last_updated": "2025-07-18T11:51:58.148783+00:00"
                        },
                        "request_id": "kati-stats-123",
                        "timestamp": "2025-07-18T11:51:58.148783+00:00"
                    }
                }
            }
        },
        503: {
            "description": "Database connection not available",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "error_count": 1,
                        "errors": [{
                            "error_code": "DATABASE_UNAVAILABLE",
                            "error_type": "system_error",
                            "message": "Database connection not available",
                            "field": None,
                            "value": None,
                            "suggestion": "Please try again later"
                        }],
                        "request_id": "kati-stats-error-123",
                        "timestamp": "2025-07-18T11:51:58.148783+00:00"
                    }
                }
            }
        }
    })
async def get_kati_transaction_stats(request: Request):
    """
    Get detailed Kati Watch transaction statistics
    
    Provides comprehensive statistics for different time periods:
    - Last hour
    - Last 24 hours  
    - Last week
    
    **Metrics:**
    - Transaction counts per period
    - Emergency alert counts
    - Active device count
    - Last update timestamp
    """
    try:
        # Check if MongoDB connection is available
        if mongodb_service.client is None or mongodb_service.main_db is None:
            return create_error_response(
                error_code="DATABASE_UNAVAILABLE",
                custom_message="Database connection not available",
                request_id=str(request.state.request_id)
            )
        
        # Get statistics for different time periods
        now = datetime.now(timezone.utc)
        one_hour_ago = now - timedelta(hours=1)
        one_day_ago = now - timedelta(days=1)
        one_week_ago = now - timedelta(days=7)
        
        medical_data_collection = mongodb_service.main_db.medical_data
        emergency_collection = mongodb_service.main_db.emergency_alarm
        
        # Get transaction counts for different periods
        stats = {
            'last_hour': {
                'transactions': await medical_data_collection.count_documents({
                    'device_type': 'Kati_Watch',
                    'timestamp': {'$gte': one_hour_ago}
                }),
                'emergencies': await emergency_collection.count_documents({
                    'device_type': 'Kati_Watch',
                    'timestamp': {'$gte': one_hour_ago}
                })
            },
            'last_24_hours': {
                'transactions': await medical_data_collection.count_documents({
                    'device_type': 'Kati_Watch',
                    'timestamp': {'$gte': one_day_ago}
                }),
                'emergencies': await emergency_collection.count_documents({
                    'device_type': 'Kati_Watch',
                    'timestamp': {'$gte': one_day_ago}
                })
            },
            'last_week': {
                'transactions': await medical_data_collection.count_documents({
                    'device_type': 'Kati_Watch',
                    'timestamp': {'$gte': one_week_ago}
                }),
                'emergencies': await emergency_collection.count_documents({
                    'device_type': 'Kati_Watch',
                    'timestamp': {'$gte': one_week_ago}
                })
            }
        }
        
        # Get active devices (devices with activity in last 24 hours)
        active_devices = await medical_data_collection.distinct('device_id', {
            'device_type': 'Kati_Watch',
            'timestamp': {'$gte': one_day_ago}
        })
        
        stats['active_devices'] = len(active_devices)
        stats['last_updated'] = now.isoformat()
        
        return create_success_response(
            request_id=str(request.state.request_id),
            message="Kati transaction statistics retrieved successfully",
            data=stats
        )
        
    except Exception as e:
        logger.error(f"Error getting Kati transaction stats: {e}")
        return create_error_response(
            error_code="KATI_STATS_ERROR",
            custom_message=f"Failed to retrieve Kati transaction statistics: {str(e)}",
            request_id=str(request.state.request_id)
        )

@router.get("/topics",
    response_model=SuccessResponse,
    responses={
        200: {
            "description": "Kati Watch topic distribution and analysis",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Kati topic distribution retrieved successfully",
                        "data": {
                            "topic_distribution": {
                                "iMEDE_watch/hb": {
                                    "count": 341,
                                    "percentage": 68.2,
                                    "description": "Heartbeat with step count, battery, signal"
                                },
                                "iMEDE_watch/location": {
                                    "count": 117,
                                    "percentage": 23.4,
                                    "description": "GPS and location data"
                                },
                                "iMEDE_watch/AP55": {
                                    "count": 34,
                                    "percentage": 6.8,
                                    "description": "Batch vital signs data"
                                },
                                "iMEDE_watch/sleepdata": {
                                    "count": 28,
                                    "percentage": 5.6,
                                    "description": "Sleep monitoring data with sleep stages and patterns"
                                },
                                "iMEDE_watch/SOS": {
                                    "count": 2,
                                    "percentage": 0.4,
                                    "description": "Emergency SOS alerts"
                                },
                                "iMEDE_watch/fallDown": {
                                    "count": 1,
                                    "percentage": 0.2,
                                    "description": "Fall detection alerts"
                                }
                            },
                            "total_transactions": 500,
                            "last_updated": "2025-07-18T11:51:52.681741+00:00"
                        },
                        "request_id": "kati-topics-123",
                        "timestamp": "2025-07-18T11:51:52.681741+00:00"
                    }
                }
            }
        }
    })
async def get_kati_topic_distribution(
    request: Request,
    hours: int = Query(24, description="Hours of data to analyze", ge=1, le=168)
):
    """
    Get Kati Watch topic distribution and analysis
    
    Provides detailed analysis of MQTT topic distribution for Kati Watch devices,
    including counts, percentages, and descriptions for each topic type.
    
    **Topics Analyzed:**
    - `iMEDE_watch/hb`: Heartbeat with step count, battery, signal
    - `iMEDE_watch/VitalSign`: Vital signs measurements
    - `iMEDE_watch/AP55`: Batch vital signs data
    - `iMEDE_watch/location`: GPS and location data
    - `iMEDE_watch/sleepdata`: Sleep monitoring data with sleep stages and patterns
    - `iMEDE_watch/SOS`: Emergency SOS alerts
    - `iMEDE_watch/fallDown`: Fall detection alerts
    - `iMEDE_watch/onlineTrigger`: Device online/offline status
    """
    try:
        # Check if MongoDB connection is available
        if mongodb_service.client is None or mongodb_service.main_db is None:
            return create_error_response(
                error_code="DATABASE_UNAVAILABLE",
                custom_message="Database connection not available",
                request_id=str(request.state.request_id)
            )
        
        # Calculate time range
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=hours)
        
        medical_data_collection = mongodb_service.main_db.medical_data
        emergency_collection = mongodb_service.main_db.emergency_alarm
        
        # Get all Kati transactions in the time range
        kati_cursor = medical_data_collection.find({
            'device_type': 'Kati_Watch',
            'timestamp': {'$gte': start_time}
        })
        kati_transactions = await kati_cursor.to_list(length=None)
        
        # Get emergency alarms
        emergency_cursor = emergency_collection.find({
            'device_type': 'Kati_Watch',
            'timestamp': {'$gte': start_time}
        })
        emergency_alarms = await emergency_cursor.to_list(length=None)
        
        # Combine all transactions
        all_transactions = kati_transactions + emergency_alarms
        total_transactions = len(all_transactions)
        
        # Topic descriptions
        topic_descriptions = {
            'iMEDE_watch/hb': 'Heartbeat with step count, battery, signal',
            'iMEDE_watch/VitalSign': 'Vital signs measurements',
            'iMEDE_watch/AP55': 'Batch vital signs data',
            'iMEDE_watch/location': 'GPS and location data',
            'iMEDE_watch/SOS': 'Emergency SOS alerts',
            'iMEDE_watch/fallDown': 'Fall detection alerts',
            'iMEDE_watch/onlineTrigger': 'Device online/offline status',
            'iMEDE_watch/sleepdata': 'Sleep monitoring data with sleep stages and patterns'
        }
        
        # Calculate topic distribution
        topic_counts = {}
        for transaction in all_transactions:
            topic = transaction.get('topic', 'unknown')
            topic_counts[topic] = topic_counts.get(topic, 0) + 1
        
        # Create detailed topic distribution
        topic_distribution = {}
        for topic, count in topic_counts.items():
            percentage = (count / total_transactions * 100) if total_transactions > 0 else 0
            topic_distribution[topic] = {
                'count': count,
                'percentage': round(percentage, 1),
                'description': topic_descriptions.get(topic, 'Unknown topic')
            }
        
        return create_success_response(
            request_id=str(request.state.request_id),
            message="Kati topic distribution retrieved successfully",
            data={
                "topic_distribution": topic_distribution,
                "total_transactions": total_transactions,
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "time_range": {
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "hours": hours
                }
            }
        )
        
    except Exception as e:
        logger.error(f"Error getting Kati topic distribution: {e}")
        return create_error_response(
            error_code="KATI_TOPICS_ERROR",
            custom_message=f"Failed to retrieve Kati topic distribution: {str(e)}",
            request_id=str(request.state.request_id)
        ) 