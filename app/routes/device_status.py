"""
Device Status API Routes
Real-time device status monitoring endpoints
"""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, Depends, Query, Request
from fastapi.responses import JSONResponse
from bson import ObjectId
from loguru import logger
logger.info("✅ Device Status Router imported and ready for registration")

from app.services.mongo import mongodb_service
from app.services.auth import require_auth
from app.utils.json_encoder import serialize_mongodb_response
from app.utils.error_definitions import create_error_response, create_success_response
from app.utils.performance_decorators import api_endpoint_timing

router = APIRouter(prefix="/api/devices/status", tags=["device-status"])

def determine_device_status(device_data: Dict[str, Any]) -> str:
    """Enhanced device status determination logic"""
    online_status = device_data.get("online_status")
    last_updated = device_data.get("last_updated")
    
    # If online_status is explicitly set, use it
    if online_status in ["online", "offline"]:
        return online_status
    
    # If we have last_updated, determine status based on recency
    if last_updated:
        try:
            if isinstance(last_updated, str):
                last_updated = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
            elif isinstance(last_updated, datetime):
                pass
            else:
                return "unknown"
            
            # Consider device online if updated within last 5 minutes
            time_threshold = datetime.utcnow() - timedelta(minutes=5)
            return "online" if last_updated > time_threshold else "offline"
        except Exception:
            return "unknown"
    
    return "unknown"

@router.get("/summary")
@api_endpoint_timing("device_status_get_summary")
async def get_device_status_summary(
    request: Request,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get summary statistics for all devices with enhanced status detection"""
    request_id = getattr(request.state, 'request_id', None)
    
    try:
        # Get real-time device status from latest_devices_status collection
        collection = mongodb_service.get_collection("latest_devices_status")
        
        # Get all devices
        cursor = collection.find({})
        devices = await cursor.to_list(length=None)
        
        # Process each device with enhanced status detection
        total_devices = len(devices)
        online_devices = 0
        offline_devices = 0
        unknown_devices = 0
        
        # Count by type
        type_stats = {}
        
        for device in devices:
            device_type = device.get("device_type", "unknown")
            status = determine_device_status(device)
            
            # Update counts
            if status == "online":
                online_devices += 1
            elif status == "offline":
                offline_devices += 1
            else:
                unknown_devices += 1
            
            # Update type stats
            if device_type not in type_stats:
                type_stats[device_type] = {"total": 0, "online": 0, "offline": 0, "unknown": 0}
            
            type_stats[device_type]["total"] += 1
            type_stats[device_type][status] += 1
        
        # Get devices with low battery (only Kati Watch devices provide battery data)
        low_battery_devices = await collection.count_documents({
            "device_type": "kati",
            "battery_level": {"$lt": 20, "$ne": None}
        })
        
        # Get devices with alerts
        devices_with_alerts = await collection.count_documents({
            "alerts": {"$exists": True, "$ne": []}
        })
        
        # Get devices that haven't reported in the last hour
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        stale_devices = await collection.count_documents({
            "last_updated": {"$lt": one_hour_ago}
        })
        
        summary = {
            "total_devices": total_devices,
            "online_devices": online_devices,
            "offline_devices": offline_devices,
            "unknown_devices": unknown_devices,
            "low_battery_devices": low_battery_devices,
            "devices_with_alerts": devices_with_alerts,
            "stale_devices": stale_devices,
            "online_percentage": round((online_devices / total_devices * 100) if total_devices > 0 else 0, 2),
            "by_type": type_stats,
            "last_updated": datetime.utcnow().isoformat()
        }
        
        success_response = create_success_response(
            message="Device status summary retrieved successfully",
            data=summary,
            request_id=request_id
        )
        return JSONResponse(status_code=200, content=success_response.dict())
        
    except Exception as e:
        logger.error(f"Failed to retrieve device status summary: {e}")
        error_response = create_error_response(
            "INTERNAL_SERVER_ERROR",
            custom_message=f"Failed to retrieve device status summary: {str(e)}",
            request_id=request_id
        )
        return JSONResponse(status_code=500, content=error_response.dict())

@router.get("/recent")
@api_endpoint_timing("device_status_get_recent")
async def get_recent_device_status(
    request: Request,
    device_type: Optional[str] = None,
    status_filter: Optional[str] = Query(None, description="Filter by status: online, offline, unknown"),
    limit: int = Query(50, ge=1, le=200),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get recent device status for all devices or filtered by type with enhanced status detection"""
    request_id = getattr(request.state, 'request_id', None)
    
    try:
        collection = mongodb_service.get_collection("latest_devices_status")
        
        # Build filter
        filter_query = {}
        if device_type:
            filter_query["device_type"] = device_type
        
        # Get recent device status
        cursor = collection.find(filter_query).sort("last_updated", -1).limit(limit)
        devices = await cursor.to_list(length=limit)
        
        # Process results with enhanced status detection
        device_status_list = []
        for device in devices:
            # Determine actual status
            actual_status = determine_device_status(device)
            
            device_status = {
                "device_id": device.get("device_id"),
                "device_type": device.get("device_type"),
                "online_status": actual_status,
                "last_updated": device.get("last_updated"),
                "battery_level": device.get("battery_level"),
                "signal_strength": device.get("signal_strength"),
                "patient_id": device.get("patient_id"),
                "last_reading": device.get("last_reading"),
                "health_metrics": device.get("health_metrics", {}),
                "alerts": device.get("alerts", []),
                "imei": device.get("imei"),
                "mac_address": device.get("mac_address"),
                "message_type": device.get("message_type")
            }
            
            # Apply status filter if specified
            if status_filter and actual_status != status_filter:
                continue
                
            device_status_list.append(device_status)
        
        success_response = create_success_response(
            message="Recent device status retrieved successfully",
            data={
                "devices": device_status_list,
                "count": len(device_status_list),
                "filter": {
                    "device_type": device_type,
                    "status": status_filter
                } if device_type or status_filter else {}
            },
            request_id=request_id
        )
        return JSONResponse(status_code=200, content=success_response.dict())
        
    except Exception as e:
        logger.error(f"Failed to retrieve recent device status: {e}")
        error_response = create_error_response(
            "INTERNAL_SERVER_ERROR",
            custom_message=f"Failed to retrieve device status: {str(e)}",
            request_id=request_id
        )
        return JSONResponse(status_code=500, content=error_response.dict())

@router.get("/alerts")
@api_endpoint_timing("device_status_get_alerts")
async def get_device_alerts(
    request: Request,
    severity: Optional[str] = None,
    device_type: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get active device alerts with enhanced filtering"""
    request_id = getattr(request.state, 'request_id', None)
    
    try:
        collection = mongodb_service.get_collection("latest_devices_status")
        
        # Build filter for devices with alerts
        filter_query = {"alerts": {"$exists": True, "$ne": []}}
        if device_type:
            filter_query["device_type"] = device_type
        
        # Get devices with alerts
        cursor = collection.find(filter_query).sort("last_updated", -1).limit(limit)
        devices = await cursor.to_list(length=limit)
        
        # Extract alerts
        all_alerts = []
        for device in devices:
            device_alerts = device.get("alerts", [])
            for alert in device_alerts:
                # Apply severity filter if specified
                if severity and alert.get("severity") != severity:
                    continue
                    
                alert_info = {
                    "device_id": device.get("device_id"),
                    "device_type": device.get("device_type"),
                    "patient_id": device.get("patient_id"),
                    "alert_type": alert.get("type"),
                    "severity": alert.get("severity"),
                    "message": alert.get("message"),
                    "timestamp": alert.get("timestamp"),
                    "data": alert.get("data", {}),
                    "device_status": determine_device_status(device)
                }
                all_alerts.append(alert_info)
        
        # Sort by timestamp (newest first)
        all_alerts.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        success_response = create_success_response(
            message="Device alerts retrieved successfully",
            data={
                "alerts": all_alerts,
                "count": len(all_alerts),
                "filter": {
                    "severity": severity,
                    "device_type": device_type
                } if severity or device_type else {}
            },
            request_id=request_id
        )
        return JSONResponse(status_code=200, content=success_response.dict())
        
    except Exception as e:
        logger.error(f"Failed to retrieve device alerts: {e}")
        error_response = create_error_response(
            "INTERNAL_SERVER_ERROR",
            custom_message=f"Failed to retrieve device alerts: {str(e)}",
            request_id=request_id
        )
        return JSONResponse(status_code=500, content=error_response.dict())

@router.get("/{device_id}")
@api_endpoint_timing("device_status_get_device")
async def get_device_status(
    request: Request,
    device_id: str,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get specific device status with enhanced status detection"""
    request_id = getattr(request.state, 'request_id', None)
    
    try:
        collection = mongodb_service.get_collection("latest_devices_status")
        
        # Find device by device_id
        device = await collection.find_one({"device_id": device_id})
        if not device:
            # Try alternative ID fields
            device = await collection.find_one({
                "$or": [
                    {"imei": device_id},
                    {"mac_address": device_id}
                ]
            })
        
        if not device:
            error_response = create_error_response(
                "DEVICE_NOT_FOUND",
                custom_message=f"Device with ID {device_id} not found",
                request_id=request_id
            )
            return JSONResponse(status_code=404, content=error_response.dict())
        
        # Determine actual status
        actual_status = determine_device_status(device)
        
        device_status = {
            "device_id": device.get("device_id"),
            "device_type": device.get("device_type"),
            "online_status": actual_status,
            "last_updated": device.get("last_updated"),
            "battery_level": device.get("battery_level"),
            "signal_strength": device.get("signal_strength"),
            "patient_id": device.get("patient_id"),
            "last_reading": device.get("last_reading"),
            "health_metrics": device.get("health_metrics", {}),
            "alerts": device.get("alerts", []),
            "imei": device.get("imei"),
            "mac_address": device.get("mac_address"),
            "message_type": device.get("message_type"),
            "data": device.get("data", {})
        }
        
        success_response = create_success_response(
            message="Device status retrieved successfully",
            data=device_status,
            request_id=request_id
        )
        return JSONResponse(status_code=200, content=success_response.dict())
        
    except Exception as e:
        logger.error(f"Failed to retrieve device status for {device_id}: {e}")
        error_response = create_error_response(
            "INTERNAL_SERVER_ERROR",
            custom_message=f"Failed to retrieve device status: {str(e)}",
            request_id=request_id
        )
        return JSONResponse(status_code=500, content=error_response.dict())

@router.get("/health/overview")
@api_endpoint_timing("device_status_health_overview")
async def get_device_health_overview(
    request: Request,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get comprehensive device health overview"""
    request_id = getattr(request.state, 'request_id', None)
    
    try:
        collection = mongodb_service.get_collection("latest_devices_status")
        
        # Get all devices
        cursor = collection.find({})
        devices = await cursor.to_list(length=None)
        
        # Analyze device health
        health_metrics = {
            "total_devices": len(devices),
            "status_breakdown": {"online": 0, "offline": 0, "unknown": 0},
            "battery_health": {"low": 0, "medium": 0, "good": 0, "unknown": 0},
            "signal_health": {"poor": 0, "fair": 0, "good": 0, "unknown": 0},
            "device_types": {},
            "recent_activity": {"last_hour": 0, "last_24h": 0, "last_week": 0},
            "alerts_summary": {"critical": 0, "warning": 0, "info": 0}
        }
        
        now = datetime.utcnow()
        one_hour_ago = now - timedelta(hours=1)
        one_day_ago = now - timedelta(days=1)
        one_week_ago = now - timedelta(weeks=1)
        
        for device in devices:
            # Status breakdown
            status = determine_device_status(device)
            health_metrics["status_breakdown"][status] += 1
            
            # Battery health
            battery = device.get("battery_level")
            if battery is not None:
                if battery < 20:
                    health_metrics["battery_health"]["low"] += 1
                elif battery < 50:
                    health_metrics["battery_health"]["medium"] += 1
                else:
                    health_metrics["battery_health"]["good"] += 1
            else:
                health_metrics["battery_health"]["unknown"] += 1
            
            # Signal health (for devices that provide it)
            signal = device.get("signal_strength")
            if signal is not None:
                if signal < 30:
                    health_metrics["signal_health"]["poor"] += 1
                elif signal < 60:
                    health_metrics["signal_health"]["fair"] += 1
                else:
                    health_metrics["signal_health"]["good"] += 1
            else:
                health_metrics["signal_health"]["unknown"] += 1
            
            # Device type breakdown
            device_type = device.get("device_type", "unknown")
            if device_type not in health_metrics["device_types"]:
                health_metrics["device_types"][device_type] = 0
            health_metrics["device_types"][device_type] += 1
            
            # Recent activity
            last_updated = device.get("last_updated")
            if last_updated:
                try:
                    if isinstance(last_updated, str):
                        last_updated = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
                    
                    if last_updated > one_hour_ago:
                        health_metrics["recent_activity"]["last_hour"] += 1
                    if last_updated > one_day_ago:
                        health_metrics["recent_activity"]["last_24h"] += 1
                    if last_updated > one_week_ago:
                        health_metrics["recent_activity"]["last_week"] += 1
                except Exception:
                    pass
            
            # Alerts summary
            alerts = device.get("alerts", [])
            for alert in alerts:
                severity = alert.get("severity", "info")
                if severity in health_metrics["alerts_summary"]:
                    health_metrics["alerts_summary"][severity] += 1
        
        success_response = create_success_response(
            message="Device health overview retrieved successfully",
            data=health_metrics,
            request_id=request_id
        )
        return JSONResponse(status_code=200, content=success_response.dict())
        
    except Exception as e:
        logger.error(f"Failed to retrieve device health overview: {e}")
        error_response = create_error_response(
            "INTERNAL_SERVER_ERROR",
            custom_message=f"Failed to retrieve device health overview: {str(e)}",
            request_id=request_id
        )
        return JSONResponse(status_code=500, content=error_response.dict()) 