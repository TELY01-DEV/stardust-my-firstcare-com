from datetime import datetime
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, Depends, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from bson import ObjectId
from loguru import logger
from app.services.mongo import mongodb_service
from app.services.auth import require_auth
from app.services.audit_logger import audit_logger
from app.services.realtime_events import realtime_events
from app.utils.json_encoder import serialize_mongodb_response
from app.utils.error_definitions import create_error_response, create_success_response
from app.utils.performance_decorators import api_endpoint_timing

router = APIRouter(prefix="/api/devices", tags=["device-crud"])

# Device Data Models
class DeviceDataCreate(BaseModel):
    timestamp: datetime
    device_id: str  # MAC address or device identifier
    device_type: str  # ava4, kati, qube-vital
    data_type: str  # blood_pressure, heart_rate, temperature, etc.
    values: Dict[str, Any]  # The actual measurement data
    patient_id: Optional[str] = None
    notes: Optional[str] = None

class DeviceDataUpdate(BaseModel):
    values: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None

class DeviceCreate(BaseModel):
    device_type: str  # ava4, kati, qube-vital
    mac_address: str
    serial_number: Optional[str] = None
    model: Optional[str] = None
    firmware_version: Optional[str] = None
    hospital_id: Optional[str] = None
    patient_id: Optional[str] = None
    location: Optional[str] = None
    status: Optional[str] = "active"
    configuration: Optional[Dict[str, Any]] = None

class DeviceUpdate(BaseModel):
    mac_address: Optional[str] = None
    serial_number: Optional[str] = None
    model: Optional[str] = None
    firmware_version: Optional[str] = None
    hospital_id: Optional[str] = None
    patient_id: Optional[str] = None
    location: Optional[str] = None
    status: Optional[str] = None
    configuration: Optional[Dict[str, Any]] = None

# ==================== DEVICE DATA CRUD OPERATIONS ====================

@router.post("/data")
@api_endpoint_timing("device_crud_create_data")
async def create_device_data(
    request: Request,
    data: DeviceDataCreate,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Create new device data entry"""
    request_id = getattr(request.state, 'request_id', None)
    
    try:
        # Validate device exists
        device = await get_device_by_mac(data.device_id, data.device_type)
        if not device:
            error_response = create_error_response(
                "DEVICE_NOT_FOUND",
                custom_message=f"Device with MAC {data.device_id} not found",
                field="device_id",
                value=data.device_id,
                request_id=request_id
            )
            return JSONResponse(status_code=404, content=error_response.dict())
        
        # Create FHIR Observation
        observation_id = await create_fhir_observation(data, device)
        
        # Route to medical history
        if device.get("patient_id"):
            await route_to_medical_history(data, str(device.get("patient_id")))
        
        # Log audit trail
        await audit_logger.log_device_data_received(
            device_id=data.device_id,
            device_type=data.device_type.upper(),
            data_type=data.data_type,
            observation_id=observation_id,
            user_id=current_user.get("username")
        )
        
        # Publish real-time event
        if device.get("patient_id"):
            patient_id = str(device.get("patient_id"))
            
            # Publish device data update
            await realtime_events.publish_device_data(
                device_type=data.device_type,
                device_id=data.device_id,
                data_type=data.data_type,
                values=data.values
            )
            
            # Publish patient vitals update if applicable
            if data.data_type in ["blood_pressure", "heart_rate", "temperature", "spo2"]:
                await realtime_events.publish_patient_vitals(
                    patient_id=patient_id,
                    vitals_data={
                        data.data_type: data.values,
                        "device_id": data.device_id,
                        "device_type": data.device_type,
                        "timestamp": data.timestamp.isoformat()
                    }
                )
                
            # Check for alerts (example: high blood pressure)
            if data.data_type == "blood_pressure":
                systolic = data.values.get("systolic", 0)
                diastolic = data.values.get("diastolic", 0)
                if systolic > 140 or diastolic > 90:
                    await realtime_events.publish_patient_alert(
                        patient_id=patient_id,
                        alert_type="high_blood_pressure",
                        severity="warning",
                        message=f"High blood pressure detected: {systolic}/{diastolic}",
                        data={
                            "systolic": systolic,
                            "diastolic": diastolic,
                            "device_id": data.device_id
                        }
                    )
        
        success_response = create_success_response(
            message="Device data created successfully",
            data={
                "observation_id": observation_id,
                "device_id": data.device_id,
                "data_type": data.data_type
            },
            request_id=request_id
        )
        return JSONResponse(status_code=201, content=success_response.dict())
        
    except Exception as e:
        error_response = create_error_response(
            "INTERNAL_SERVER_ERROR",
            custom_message=f"Failed to create device data: {str(e)}",
            request_id=request_id
        )
        return JSONResponse(status_code=500, content=error_response.dict())

@router.get("/data")
@api_endpoint_timing("device_crud_get_data")
async def get_device_data(
    request: Request,
    device_id: Optional[str] = None,
    device_type: Optional[str] = None,
    data_type: Optional[str] = None,
    patient_id: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = Query(100, ge=1, le=1000),
    skip: int = Query(0, ge=0),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get device data with filtering"""
    request_id = getattr(request.state, 'request_id', None)
    
    try:
        collection = mongodb_service.get_fhir_collection("fhir_observations")
        
        # Build filter
        filter_query = {"resourceType": "Observation"}
        
        if device_id:
            filter_query["device.reference"] = f"Device/{device_id}"
        
        if patient_id:
            if not ObjectId.is_valid(patient_id):
                error_response = create_error_response(
                    "INVALID_PATIENT_ID",
                    custom_message="Invalid patient ID format",
                    field="patient_id",
                    value=patient_id,
                    request_id=request_id
                )
                return JSONResponse(status_code=400, content=error_response.dict())
            filter_query["subject.reference"] = f"Patient/{patient_id}"
        
        if data_type:
            filter_query["code.coding.code"] = data_type.upper()
        
        if start_date or end_date:
            date_filter = {}
            if start_date:
                date_filter["$gte"] = start_date.isoformat() + "Z"
            if end_date:
                date_filter["$lte"] = end_date.isoformat() + "Z"
            filter_query["effectiveDateTime"] = date_filter
        
        # Get total count
        total = await collection.count_documents(filter_query)
        
        # Get data
        cursor = collection.find(filter_query).sort("effectiveDateTime", -1).skip(skip).limit(limit)
        observations = await cursor.to_list(length=limit)
        
        # Serialize ObjectIds
        observations = serialize_mongodb_response(observations)
        
        success_response = create_success_response(
            message="Device data retrieved successfully",
            data={
                "observations": observations,
                "total": total,
                "limit": limit,
                "skip": skip,
                "filters": {
                    "device_id": device_id,
                    "device_type": device_type,
                    "data_type": data_type,
                    "patient_id": patient_id
                }
            },
            request_id=request_id
        )
        return JSONResponse(content=success_response.dict())
        
    except Exception as e:
        error_response = create_error_response(
            "INTERNAL_SERVER_ERROR",
            custom_message=f"Failed to retrieve device data: {str(e)}",
            request_id=request_id
        )
        return JSONResponse(status_code=500, content=error_response.dict())

@router.get("/data/{observation_id}")
@api_endpoint_timing("device_crud_get_data_record")
async def get_device_data_record(
    request: Request,
    observation_id: str,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get specific device data record"""
    request_id = getattr(request.state, 'request_id', None)
    
    try:
        if not ObjectId.is_valid(observation_id):
            error_response = create_error_response(
                "INVALID_OBSERVATION_ID",
                custom_message="Invalid observation ID format",
                field="observation_id",
                value=observation_id,
                request_id=request_id
            )
            return JSONResponse(status_code=400, content=error_response.dict())
        
        collection = mongodb_service.get_fhir_collection("fhir_observations")
        observation = await collection.find_one({"_id": ObjectId(observation_id)})
        
        if not observation:
            error_response = create_error_response(
                "OBSERVATION_NOT_FOUND",
                custom_message=f"Observation with ID {observation_id} not found",
                field="observation_id",
                value=observation_id,
                request_id=request_id
            )
            return JSONResponse(status_code=404, content=error_response.dict())
        
        observation = serialize_mongodb_response(observation)
        
        success_response = create_success_response(
            message="Observation retrieved successfully",
            data={"observation": observation},
            request_id=request_id
        )
        return JSONResponse(content=success_response.dict())
        
    except Exception as e:
        error_response = create_error_response(
            "INTERNAL_SERVER_ERROR",
            custom_message=f"Failed to retrieve observation: {str(e)}",
            request_id=request_id
        )
        return JSONResponse(status_code=500, content=error_response.dict())

@router.put("/data/{observation_id}")
async def update_device_data(
    observation_id: str,
    data: DeviceDataUpdate,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Update device data record"""
    try:
        collection = mongodb_service.get_fhir_collection("fhir_observations")
        
        update_data = {}
        if data.values:
            update_data["valueQuantity"] = {
                "value": data.values.get("value"),
                "unit": data.values.get("unit", ""),
                "system": "http://unitsofmeasure.org",
                "code": data.values.get("unit_code", "")
            }
        
        if data.notes:
            update_data["note"] = [{"text": data.notes}]
        
        update_data["meta.lastUpdated"] = datetime.utcnow().isoformat() + "Z"
        
        result = await collection.update_one(
            {"_id": ObjectId(observation_id)},
            {"$set": update_data}
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Observation not found")
        
        # Log audit trail
        username = current_user.get("username", "unknown")
        await audit_logger.log_admin_action(
            action="UPDATE",
            resource_type="DeviceData",
            resource_id=observation_id,
            user_id=username
        )
        
        return {"success": True, "message": "Device data updated successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/data/{observation_id}")
async def delete_device_data(
    observation_id: str,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Soft delete device data record"""
    try:
        collection = mongodb_service.get_fhir_collection("fhir_observations")
        
        update_data = {
            "status": "cancelled",
            "meta.lastUpdated": datetime.utcnow().isoformat() + "Z",
            "note": [{"text": f"Deleted by {current_user.get('username', 'unknown')} at {datetime.utcnow().isoformat()}"}]
        }
        
        result = await collection.update_one(
            {"_id": ObjectId(observation_id)},
            {"$set": update_data}
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Observation not found")
        
        # Log audit trail
        username = current_user.get("username", "unknown")
        await audit_logger.log_admin_action(
            action="DELETE",
            resource_type="DeviceData",
            resource_id=observation_id,
            user_id=username
        )
        
        return {"success": True, "message": "Device data deleted successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== DEVICE MANAGEMENT CRUD ====================

@router.post("/")
@api_endpoint_timing("device_crud_create_device")
async def api_create_device(
    request: Request,
    device: DeviceCreate,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Create new device"""
    request_id = getattr(request.state, 'request_id', None)
    
    try:
        collection_name = get_device_collection_name(device.device_type, request_id)
        collection = mongodb_service.get_collection(collection_name)
        
        # Check if device already exists
        existing_device = await collection.find_one({"mac_address": device.mac_address})
        if existing_device:
            error_response = create_error_response(
                "DUPLICATE_DEVICE",
                custom_message="Device with this MAC address already exists",
                field="mac_address",
                value=device.mac_address,
                request_id=request_id
            )
            return JSONResponse(status_code=409, content=error_response.dict())
        
        # Prepare device data
        device_data = device.dict()
        device_data["created_at"] = datetime.utcnow()
        device_data["updated_at"] = datetime.utcnow()
        device_data["is_active"] = True
        
        # Convert IDs to ObjectIds
        if device.hospital_id:
            if not ObjectId.is_valid(device.hospital_id):
                error_response = create_error_response(
                    "INVALID_HOSPITAL_ID",
                    custom_message="Invalid hospital ID format",
                    field="hospital_id",
                    value=device.hospital_id,
                    request_id=request_id
                )
                return JSONResponse(status_code=400, content=error_response.dict())
            device_data["hospital_id"] = ObjectId(device.hospital_id)
            
        if device.patient_id:
            if not ObjectId.is_valid(device.patient_id):
                error_response = create_error_response(
                    "INVALID_PATIENT_ID",
                    custom_message="Invalid patient ID format",
                    field="patient_id",
                    value=device.patient_id,
                    request_id=request_id
                )
                return JSONResponse(status_code=400, content=error_response.dict())
            device_data["patient_id"] = ObjectId(device.patient_id)
        
        # Set device type specific fields
        if device.device_type == "ava4":
            device_data["is_deleted"] = False
            device_data["box_type"] = "AMY"
        elif device.device_type == "kati":
            device_data["watch_type"] = "KATI"
        elif device.device_type == "qube-vital":
            device_data["is_deleted"] = False
            device_data["box_type"] = "QUBE"
        
        result = await collection.insert_one(device_data)
        
        # Create FHIR Device resource
        await create_fhir_device(device, str(result.inserted_id))
        
        # Log audit trail
        username = current_user.get("username", "unknown")
        await audit_logger.log_admin_action(
            action="CREATE",
            resource_type="Device",
            resource_id=str(result.inserted_id),
            user_id=username,
            details={"device_type": device.device_type, "mac_address": device.mac_address}
        )
        
        success_response = create_success_response(
            message="Device created successfully",
            data={
                "device_id": str(result.inserted_id),
                "device_type": device.device_type,
                "mac_address": device.mac_address
            },
            request_id=request_id
        )
        return JSONResponse(status_code=201, content=success_response.dict())
        
    except ValueError as e:
        error_response = create_error_response(
            "INVALID_DEVICE_TYPE",
            custom_message=str(e),
            field="device_type",
            value=device.device_type,
            request_id=request_id
        )
        return JSONResponse(status_code=400, content=error_response.dict())
    except Exception as e:
        error_response = create_error_response(
            "INTERNAL_SERVER_ERROR",
            custom_message=f"Failed to create device: {str(e)}",
            request_id=request_id
        )
        return JSONResponse(status_code=500, content=error_response.dict())

@router.get("/")
async def get_devices(
    device_type: Optional[str] = None,
    hospital_id: Optional[str] = None,
    patient_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000),
    skip: int = Query(0, ge=0),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get devices with filtering"""
    try:
        devices = []
        total = 0
        
        if device_type:
            # Get devices of specific type
            collection_name = get_device_collection_name(device_type)
            collection = mongodb_service.get_collection(collection_name)
            
            filter_query = build_device_filter(device_type, hospital_id, patient_id, status)
            
            total = await collection.count_documents(filter_query)
            cursor = collection.find(filter_query).skip(skip).limit(limit)
            devices = await cursor.to_list(length=limit)
            
        else:
            # Get devices from all collections
            for dt in ["ava4", "kati", "qube-vital"]:
                collection_name = get_device_collection_name(dt)
                collection = mongodb_service.get_collection(collection_name)
                
                filter_query = build_device_filter(dt, hospital_id, patient_id, status)
                
                cursor = collection.find(filter_query).skip(skip).limit(limit)
                device_batch = await cursor.to_list(length=limit)
                
                # Add device type to each device
                for device in device_batch:
                    device["device_type"] = dt
                
                devices.extend(device_batch)
                total += await collection.count_documents(filter_query)
        
        # Serialize ObjectIds
        devices = serialize_mongodb_response(devices)
        
        return {
            "devices": devices,
            "total": total,
            "limit": limit,
            "skip": skip,
            "filters": {
                "device_type": device_type,
                "hospital_id": hospital_id,
                "patient_id": patient_id,
                "status": status
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== DEVICE STATUS ENDPOINTS ====================

@router.get("/status/recent")
@api_endpoint_timing("device_crud_get_status_recent")
async def get_recent_device_status(
    request: Request,
    device_type: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get recent device status for all devices or filtered by type"""
    request_id = getattr(request.state, 'request_id', None)
    
    try:
        collection = mongodb_service.get_collection("device_status")
        
        # Build filter
        filter_query = {}
        if device_type:
            filter_query["device_type"] = device_type
        
        # Get recent device status
        cursor = collection.find(filter_query).sort("last_updated", -1).limit(limit)
        devices = await cursor.to_list(length=limit)
        
        # Process results
        device_status_list = []
        for device in devices:
            device_status = {
                "device_id": device.get("device_id"),
                "device_type": device.get("device_type"),
                "online_status": device.get("online_status", "unknown"),
                "last_updated": device.get("last_updated"),
                "battery_level": device.get("battery_level"),
                "signal_strength": device.get("signal_strength"),
                "patient_id": device.get("patient_id"),
                "last_reading": device.get("last_reading"),
                "health_metrics": device.get("health_metrics", {}),
                "alerts": device.get("alerts", [])
            }
            device_status_list.append(device_status)
        
        success_response = create_success_response(
            message="Recent device status retrieved successfully",
            data={
                "devices": device_status_list,
                "count": len(device_status_list),
                "filter": {"device_type": device_type} if device_type else {}
            },
            request_id=request_id
        )
        return JSONResponse(status_code=200, content=success_response.dict())
        
    except Exception as e:
        error_response = create_error_response(
            "INTERNAL_SERVER_ERROR",
            custom_message=f"Failed to retrieve device status: {str(e)}",
            request_id=request_id
        )
        return JSONResponse(status_code=500, content=error_response.dict())

@router.get("/status/{device_id}")
@api_endpoint_timing("device_crud_get_device_status")
async def get_device_status(
    request: Request,
    device_id: str,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get detailed status for a specific device"""
    request_id = getattr(request.state, 'request_id', None)
    
    try:
        collection = mongodb_service.get_collection("device_status")
        
        # Find device status
        device = await collection.find_one({"device_id": device_id})
        
        if not device:
            error_response = create_error_response(
                "DEVICE_NOT_FOUND",
                custom_message=f"Device status not found for device ID: {device_id}",
                field="device_id",
                value=device_id,
                request_id=request_id
            )
            return JSONResponse(status_code=404, content=error_response.dict())
        
        # Format response
        device_status = {
            "device_id": device.get("device_id"),
            "device_type": device.get("device_type"),
            "online_status": device.get("online_status", "unknown"),
            "last_updated": device.get("last_updated"),
            "battery_level": device.get("battery_level"),
            "signal_strength": device.get("signal_strength"),
            "patient_id": device.get("patient_id"),
            "last_reading": device.get("last_reading"),
            "health_metrics": device.get("health_metrics", {}),
            "alerts": device.get("alerts", []),
            "metadata": device.get("metadata", {})
        }
        
        success_response = create_success_response(
            message="Device status retrieved successfully",
            data=device_status,
            request_id=request_id
        )
        return JSONResponse(status_code=200, content=success_response.dict())
        
    except Exception as e:
        error_response = create_error_response(
            "INTERNAL_SERVER_ERROR",
            custom_message=f"Failed to retrieve device status: {str(e)}",
            request_id=request_id
        )
        return JSONResponse(status_code=500, content=error_response.dict())

@router.get("/status/summary")
@api_endpoint_timing("device_crud_get_status_summary")
async def get_device_status_summary(
    request: Request,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get summary statistics for all devices"""
    request_id = getattr(request.state, 'request_id', None)
    
    try:
        collection = mongodb_service.get_collection("device_status")
        
        # Get total device count
        total_devices = await collection.count_documents({})
        
        # Get online devices count
        online_devices = await collection.count_documents({"online_status": "online"})
        
        # Get offline devices count
        offline_devices = await collection.count_documents({"online_status": "offline"})
        
        # Get devices by type
        pipeline = [
            {"$group": {
                "_id": "$device_type",
                "count": {"$sum": 1},
                "online": {"$sum": {"$cond": [{"$eq": ["$online_status", "online"]}, 1, 0]}},
                "offline": {"$sum": {"$cond": [{"$eq": ["$online_status", "offline"]}, 1, 0]}}
            }}
        ]
        
        type_stats = await collection.aggregate(pipeline).to_list(length=None)
        
        # Get devices with low battery
        low_battery_devices = await collection.count_documents({
            "battery_level": {"$lt": 20}
        })
        
        # Get devices with alerts
        devices_with_alerts = await collection.count_documents({
            "alerts": {"$exists": True, "$ne": []}
        })
        
        summary = {
            "total_devices": total_devices,
            "online_devices": online_devices,
            "offline_devices": offline_devices,
            "low_battery_devices": low_battery_devices,
            "devices_with_alerts": devices_with_alerts,
            "online_percentage": round((online_devices / total_devices * 100) if total_devices > 0 else 0, 2),
            "by_type": {stat["_id"]: {
                "total": stat["count"],
                "online": stat["online"],
                "offline": stat["offline"]
            } for stat in type_stats}
        }
        
        success_response = create_success_response(
            message="Device status summary retrieved successfully",
            data=summary,
            request_id=request_id
        )
        return JSONResponse(status_code=200, content=success_response.dict())
        
    except Exception as e:
        error_response = create_error_response(
            "INTERNAL_SERVER_ERROR",
            custom_message=f"Failed to retrieve device status summary: {str(e)}",
            request_id=request_id
        )
        return JSONResponse(status_code=500, content=error_response.dict())

@router.get("/status/alerts")
@api_endpoint_timing("device_crud_get_status_alerts")
async def get_device_alerts(
    request: Request,
    severity: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get active device alerts"""
    request_id = getattr(request.state, 'request_id', None)
    
    try:
        collection = mongodb_service.get_collection("device_status")
        
        # Build filter for devices with alerts
        filter_query = {"alerts": {"$exists": True, "$ne": []}}
        if severity:
            filter_query["alerts.severity"] = severity
        
        # Get devices with alerts
        cursor = collection.find(filter_query).sort("last_updated", -1).limit(limit)
        devices = await cursor.to_list(length=limit)
        
        # Extract alerts
        all_alerts = []
        for device in devices:
            device_alerts = device.get("alerts", [])
            for alert in device_alerts:
                alert_info = {
                    "device_id": device.get("device_id"),
                    "device_type": device.get("device_type"),
                    "patient_id": device.get("patient_id"),
                    "alert_type": alert.get("type"),
                    "severity": alert.get("severity"),
                    "message": alert.get("message"),
                    "timestamp": alert.get("timestamp"),
                    "data": alert.get("data", {})
                }
                all_alerts.append(alert_info)
        
        # Sort by timestamp (newest first)
        all_alerts.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        success_response = create_success_response(
            message="Device alerts retrieved successfully",
            data={
                "alerts": all_alerts[:limit],
                "count": len(all_alerts[:limit]),
                "filter": {"severity": severity} if severity else {}
            },
            request_id=request_id
        )
        return JSONResponse(status_code=200, content=success_response.dict())
        
    except Exception as e:
        error_response = create_error_response(
            "INTERNAL_SERVER_ERROR",
            custom_message=f"Failed to retrieve device alerts: {str(e)}",
            request_id=request_id
        )
        return JSONResponse(status_code=500, content=error_response.dict())

@router.get("/{device_id}")
async def api_get_device(
    device_id: str,
    device_type: str = Query(..., description="Device type: ava4, kati, qube-vital"),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get specific device"""
    try:
        collection_name = get_device_collection_name(device_type)
        collection = mongodb_service.get_collection(collection_name)
        
        device = await collection.find_one({"_id": ObjectId(device_id)})
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")
        
        device = serialize_mongodb_response(device)
        device["device_type"] = device_type
        
        return JSONResponse(content=device)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{device_id}")
async def api_update_device(
    device_id: str,
    device: DeviceUpdate,
    device_type: str = Query(..., description="Device type: ava4, kati, qube-vital"),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Update device"""
    try:
        collection_name = get_device_collection_name(device_type)
        collection = mongodb_service.get_collection(collection_name)
        
        update_data = device.dict(exclude_unset=True)
        update_data["updated_at"] = datetime.utcnow()
        
        # Convert IDs to ObjectIds
        if "hospital_id" in update_data and update_data["hospital_id"]:
            update_data["hospital_id"] = ObjectId(update_data["hospital_id"])
        if "patient_id" in update_data and update_data["patient_id"]:
            update_data["patient_id"] = ObjectId(update_data["patient_id"])
        
        result = await collection.update_one(
            {"_id": ObjectId(device_id)},
            {"$set": update_data}
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Device not found")
        
        # Update FHIR Device resource
        await update_fhir_device(device_id, device)
        
        # Log audit trail
        username = current_user.get("username", "unknown")
        await audit_logger.log_admin_action(
            action="UPDATE",
            resource_type="Device",
            resource_id=device_id,
            user_id=username,
            details={"device_type": device_type}
        )
        
        return {"success": True, "message": "Device updated successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{device_id}")
async def api_delete_device(
    device_id: str,
    device_type: str = Query(..., description="Device type: ava4, kati, qube-vital"),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Soft delete device"""
    try:
        collection_name = get_device_collection_name(device_type)
        collection = mongodb_service.get_collection(collection_name)
        
        update_data = {
            "updated_at": datetime.utcnow(),
            "deleted_at": datetime.utcnow(),
            "deleted_by": current_user.get("username", "unknown")
        }
        
        # Set deletion fields based on device type
        if device_type == "ava4" or device_type == "qube-vital":
            update_data["is_deleted"] = True
        elif device_type == "kati":
            update_data["status"] = "deleted"
        
        result = await collection.update_one(
            {"_id": ObjectId(device_id)},
            {"$set": update_data}
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Device not found")
        
        # Update FHIR Device resource
        await deactivate_fhir_device(device_id)
        
        # Log audit trail
        username = current_user.get("username", "unknown")
        await audit_logger.log_admin_action(
            action="DELETE",
            resource_type="Device",
            resource_id=device_id,
            user_id=username,
            details={"device_type": device_type}
        )
        
        return {"success": True, "message": "Device deleted successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== HELPER FUNCTIONS ====================

def get_device_collection_name(device_type: str, request_id: Optional[str] = None) -> str:
    """Get collection name for device type"""
    collection_mapping = {
        "ava4": "amy_boxes",
        "kati": "watches",
        "qube-vital": "mfc_hv01_boxes"
    }
    
    collection_name = collection_mapping.get(device_type)
    if not collection_name:
        raise ValueError(f"Invalid device type: {device_type}. Supported types: {list(collection_mapping.keys())}")
    
    return collection_name

def build_device_filter(device_type: str, hospital_id: str = None, patient_id: str = None, status: str = None) -> Dict[str, Any]:
    """Build filter query for device search"""
    filter_query = {}
    
    # Base filters by device type
    if device_type == "ava4" or device_type == "qube-vital":
        filter_query["is_deleted"] = {"$ne": True}
    elif device_type == "kati":
        filter_query["status"] = {"$ne": "deleted"}
    
    # Additional filters
    if hospital_id:
        filter_query["hospital_id"] = ObjectId(hospital_id)
    
    if patient_id:
        filter_query["patient_id"] = ObjectId(patient_id)
    
    if status and device_type == "kati":
        filter_query["status"] = status
    elif status and device_type in ["ava4", "qube-vital"]:
        filter_query["is_active"] = (status == "active")
    
    return filter_query

async def get_device_by_mac(mac_address: str, device_type: str) -> Optional[Dict[str, Any]]:
    """Get device by MAC address"""
    try:
        collection_name = get_device_collection_name(device_type)
        collection = mongodb_service.get_collection(collection_name)
        return await collection.find_one({"mac_address": mac_address})
    except:
        return None

async def create_fhir_observation(data: DeviceDataCreate, device: Dict[str, Any]) -> str:
    """Create FHIR Observation resource"""
    observation = {
        "resourceType": "Observation",
        "status": "final",
        "category": [
            {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                        "code": "vital-signs",
                        "display": "Vital Signs"
                    }
                ]
            }
        ],
        "code": {
            "coding": [
                {
                    "system": "https://my-firstcare.com/observations",
                    "code": data.data_type.upper(),
                    "display": data.data_type.replace("_", " ").title()
                }
            ]
        },
        "subject": {
            "reference": f"Patient/{device.get('patient_id', 'unknown')}"
        },
        "effectiveDateTime": data.timestamp.isoformat() + "Z",
        "issued": datetime.utcnow().isoformat() + "Z",
        "valueQuantity": {
            "value": data.values.get("value"),
            "unit": data.values.get("unit", ""),
            "system": "http://unitsofmeasure.org",
            "code": data.values.get("unit_code", "")
        },
        "device": {
            "reference": f"Device/{data.device_id}"
        },
        "note": [{"text": data.notes}] if data.notes else [],
        "meta": {
            "source": "https://opera.my-firstcare.com",
            "profile": ["http://hl7.org/fhir/StructureDefinition/Observation"],
            "lastUpdated": datetime.utcnow().isoformat() + "Z"
        }
    }
    
    collection = mongodb_service.get_fhir_collection("fhir_observations")
    result = await collection.insert_one(observation)
    return str(result.inserted_id)

async def route_to_medical_history(data: DeviceDataCreate, patient_id: str):
    """Route device data to appropriate medical history collection"""
    try:
        collection_mapping = {
            "BLOOD_PRESSURE": "blood_pressure_histories",
            "BLOOD_SUGAR": "blood_sugar_histories",
            "TEMPERATURE": "temprature_data_histories",
            "WEIGHT": "body_data_histories",
            "HEART_RATE": "spo2_histories",
            "SPO2": "spo2_histories",
            "STEPS": "step_histories",
            "SLEEP": "sleep_data_histories"
        }
        
        collection_name = collection_mapping.get(data.data_type.upper())
        if collection_name and patient_id:
            collection = mongodb_service.get_collection(collection_name)
            
            history_entry = {
                "patient_id": ObjectId(patient_id),
                "device_id": data.device_id,
                "device_type": data.device_type.upper(),
                "data": [data.values],
                "timestamp": data.timestamp,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "notes": data.notes
            }
            
            await collection.insert_one(history_entry)
            
    except Exception as e:
        # Log error but don't fail the main operation
        logger.error(f"Failed to route to medical history: {e}")

async def create_fhir_device(device: DeviceCreate, device_id: str):
    """Create FHIR Device resource"""
    try:
        fhir_device = {
            "resourceType": "Device",
            "id": device_id,
            "identifier": [
                {
                    "system": "https://my-firstcare.com/devices",
                    "value": device.mac_address
                }
            ],
            "status": "active",
            "deviceName": [
                {
                    "name": f"{device.device_type.upper()} Device",
                    "type": "user-friendly-name"
                }
            ],
            "type": {
                "coding": [
                    {
                        "system": "https://my-firstcare.com/device-types",
                        "code": device.device_type,
                        "display": device.device_type.upper()
                    }
                ]
            },
            "serialNumber": device.serial_number,
            "modelNumber": device.model,
            "version": [
                {
                    "type": {
                        "coding": [
                            {
                                "system": "http://hl7.org/fhir/device-version-type",
                                "code": "firmware"
                            }
                        ]
                    },
                    "value": device.firmware_version
                }
            ] if device.firmware_version else [],
            "location": {
                "display": device.location
            } if device.location else None,
            "meta": {
                "source": "https://opera.my-firstcare.com",
                "profile": ["http://hl7.org/fhir/StructureDefinition/Device"],
                "lastUpdated": datetime.utcnow().isoformat() + "Z"
            }
        }
        
        collection = mongodb_service.get_fhir_collection("fhir_devices")
        await collection.insert_one(fhir_device)
        
    except Exception as e:
        logger.error(f"Failed to create FHIR device: {e}")

async def update_fhir_device(device_id: str, device: DeviceUpdate):
    """Update FHIR Device resource"""
    try:
        collection = mongodb_service.get_fhir_collection("fhir_devices")
        
        update_data = {
            "meta.lastUpdated": datetime.utcnow().isoformat() + "Z"
        }
        
        if device.serial_number:
            update_data["serialNumber"] = device.serial_number
        if device.model:
            update_data["modelNumber"] = device.model
        if device.location:
            update_data["location.display"] = device.location
        if device.status:
            update_data["status"] = device.status
        
        await collection.update_one(
            {"id": device_id},
            {"$set": update_data}
        )
        
    except Exception as e:
        logger.error(f"Failed to update FHIR device: {e}")

async def deactivate_fhir_device(device_id: str):
    """Deactivate FHIR Device resource"""
    try:
        collection = mongodb_service.get_fhir_collection("fhir_devices")
        
        update_data = {
            "status": "inactive",
            "meta.lastUpdated": datetime.utcnow().isoformat() + "Z"
        }
        
        await collection.update_one(
            {"id": device_id},
            {"$set": update_data}
        )
        
    except Exception as e:
        logger.error(f"Failed to deactivate FHIR device: {e}") 