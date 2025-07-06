from datetime import datetime
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, Depends, Request, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from bson import ObjectId
from app.services.mongo import mongodb_service
from app.services.auth import require_auth
from app.services.audit_logger import audit_logger
from app.utils.json_encoder import serialize_mongodb_response
from app.utils.error_definitions import create_error_response, create_success_response
from app.utils.performance_decorators import database_timing, api_endpoint_timing

router = APIRouter(prefix="/admin", tags=["Admin Panel CRUD"])

# Additional Pydantic models for CRUD operations
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
    notes: Optional[str] = None

class DeviceUpdate(BaseModel):
    mac_address: Optional[str] = None
    serial_number: Optional[str] = None
    model: Optional[str] = None
    firmware_version: Optional[str] = None
    hospital_id: Optional[str] = None
    patient_id: Optional[str] = None
    location: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None

class MedicalHistoryCreate(BaseModel):
    patient_id: str
    history_type: str  # blood_pressure, blood_sugar, etc.
    timestamp: Optional[datetime] = None
    device_id: Optional[str] = None
    values: Dict[str, Any]  # Dynamic values based on history type
    notes: Optional[str] = None

class MedicalHistoryUpdate(BaseModel):
    values: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None

class MasterDataCreate(BaseModel):
    data_type: str  # hospitals, provinces, districts, etc.
    name: Optional[Dict[str, Any]] = None
    code: Optional[int] = None
    is_active: Optional[bool] = True
    province_code: Optional[int] = None
    district_code: Optional[int] = None
    sub_district_code: Optional[int] = None
    additional_fields: Optional[Dict[str, Any]] = None

class MasterDataUpdate(BaseModel):
    name: Optional[Dict[str, Any]] = None
    code: Optional[int] = None
    is_active: Optional[bool] = None
    province_code: Optional[int] = None
    district_code: Optional[int] = None
    sub_district_code: Optional[int] = None
    additional_fields: Optional[Dict[str, Any]] = None

# ==================== DEVICE CRUD OPERATIONS ====================

@router.get("/devices/{device_id}")
@api_endpoint_timing("admin_crud_get_device")
async def admin_get_device(
    request: Request,
    device_id: str,
    device_type: str = Query(..., description="Device type: ava4, kati, qube-vital"),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get specific device by ID"""
    request_id = getattr(request.state, 'request_id', None)
    
    try:
        # Validate device_id format
        if not ObjectId.is_valid(device_id):
            error_response = create_error_response(
                "INVALID_DEVICE_ID",
                custom_message="Invalid device ID format",
                field="device_id",
                value=device_id,
                request_id=request_id
            )
            return JSONResponse(status_code=400, content=error_response.dict())
        
        collection_name = get_device_collection_name(device_type, request_id)
        collection = mongodb_service.get_collection(collection_name)
        
        device = await collection.find_one({"_id": ObjectId(device_id)})
        
        if not device:
            error_response = create_error_response(
                "DEVICE_NOT_FOUND",
                custom_message=f"Device with ID {device_id} not found",
                field="device_id",
                value=device_id,
                request_id=request_id
            )
            return JSONResponse(status_code=404, content=error_response.dict())
        
        device = serialize_mongodb_response(device)
        
        success_response = create_success_response(
            message="Device retrieved successfully",
            data={"device": device},
            request_id=request_id
        )
        return JSONResponse(content=success_response.dict())
        
    except ValueError as e:
        error_response = create_error_response(
            "INVALID_DEVICE_TYPE",
            custom_message=str(e),
            field="device_type",
            value=device_type,
            request_id=request_id
        )
        return JSONResponse(status_code=400, content=error_response.dict())
    except Exception as e:
        error_response = create_error_response(
            "INTERNAL_SERVER_ERROR",
            custom_message=f"Failed to retrieve device: {str(e)}",
            request_id=request_id
        )
        return JSONResponse(status_code=500, content=error_response.dict())

@router.post("/devices")
@api_endpoint_timing("admin_crud_create_device")
async def admin_create_device(
    request: Request,
    device: DeviceCreate,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Create new device"""
    request_id = getattr(request.state, 'request_id', None)
    
    try:
        collection_name = get_device_collection_name(device.device_type, request_id)
        collection = mongodb_service.get_collection(collection_name)
        
        # Check if device with same MAC address already exists
        existing_device = await collection.find_one({"mac_address": device.mac_address})
        
        if existing_device:
            error_response = create_error_response(
                "DUPLICATE_DEVICE",
                custom_message="Device with this MAC address already exists. Use a different MAC address or update the existing device",
                field="mac_address",
                value=device.mac_address,
                request_id=request_id
            )
            return JSONResponse(status_code=409, content=error_response.dict())
        
        # Prepare device data based on device type
        device_data = device.dict()
        device_data["created_at"] = datetime.utcnow()
        device_data["updated_at"] = datetime.utcnow()
        device_data["is_active"] = True
        
        # Convert IDs to ObjectIds if provided
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
            device_data["status"] = device.status or "active"
            device_data["watch_type"] = "KATI"
        elif device.device_type == "qube-vital":
            device_data["is_deleted"] = False
            device_data["box_type"] = "QUBE"
        
        result = await collection.insert_one(device_data)
        
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

@router.put("/devices/{device_id}")
@api_endpoint_timing("admin_crud_update_device")
async def admin_update_device(
    request: Request,
    device_id: str,
    device: DeviceUpdate,
    device_type: str = Query(..., description="Device type: ava4, kati, qube-vital"),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Update device"""
    request_id = getattr(request.state, 'request_id', None)
    
    try:
        # Validate device_id format
        if not ObjectId.is_valid(device_id):
            error_response = create_error_response(
                "INVALID_DEVICE_ID",
                custom_message="Invalid device ID format",
                field="device_id",
                value=device_id,
                request_id=request_id
            )
            return JSONResponse(status_code=400, content=error_response.dict())
        
        collection_name = get_device_collection_name(device_type, request_id)
        collection = mongodb_service.get_collection(collection_name)
        
        update_data = device.dict(exclude_unset=True)
        if not update_data:
            error_response = create_error_response(
                "NO_UPDATE_DATA",
                custom_message="No valid fields provided for update. Provide at least one field to update",
                request_id=request_id
            )
            return JSONResponse(status_code=400, content=error_response.dict())
            
        update_data["updated_at"] = datetime.utcnow()
        
        # Convert IDs to ObjectIds if provided
        if "hospital_id" in update_data and update_data["hospital_id"]:
            if not ObjectId.is_valid(update_data["hospital_id"]):
                error_response = create_error_response(
                    "INVALID_HOSPITAL_ID",
                    custom_message="Invalid hospital ID format",
                    field="hospital_id",
                    value=update_data["hospital_id"],
                    request_id=request_id
                )
                return JSONResponse(status_code=400, content=error_response.dict())
            update_data["hospital_id"] = ObjectId(update_data["hospital_id"])
            
        if "patient_id" in update_data and update_data["patient_id"]:
            if not ObjectId.is_valid(update_data["patient_id"]):
                error_response = create_error_response(
                    "INVALID_PATIENT_ID",
                    custom_message="Invalid patient ID format",
                    field="patient_id",
                    value=update_data["patient_id"],
                    request_id=request_id
                )
                return JSONResponse(status_code=400, content=error_response.dict())
            update_data["patient_id"] = ObjectId(update_data["patient_id"])
        
        result = await collection.update_one(
            {"_id": ObjectId(device_id)},
            {"$set": update_data}
        )
        
        if result.matched_count == 0:
            error_response = create_error_response(
                "DEVICE_NOT_FOUND",
                custom_message=f"Device with ID {device_id} not found",
                field="device_id",
                value=device_id,
                request_id=request_id
            )
            return JSONResponse(status_code=404, content=error_response.dict())
        
        # Log audit trail
        username = current_user.get("username", "unknown")
        await audit_logger.log_admin_action(
            action="UPDATE",
            resource_type="Device",
            resource_id=device_id,
            user_id=username,
            details={"device_type": device_type, "updated_fields": list(update_data.keys())}
        )
        
        success_response = create_success_response(
            message="Device updated successfully",
            data={
                "device_id": device_id,
                "updated_fields": list(update_data.keys()),
                "modified_count": result.modified_count
            },
            request_id=request_id
        )
        return JSONResponse(content=success_response.dict())
        
    except ValueError as e:
        error_response = create_error_response(
            "INVALID_DEVICE_TYPE",
            custom_message=str(e),
            field="device_type",
            value=device_type,
            request_id=request_id
        )
        return JSONResponse(status_code=400, content=error_response.dict())
    except Exception as e:
        error_response = create_error_response(
            "INTERNAL_SERVER_ERROR",
            custom_message=f"Failed to update device: {str(e)}",
            request_id=request_id
        )
        return JSONResponse(status_code=500, content=error_response.dict())

@router.delete("/devices/{device_id}")
@api_endpoint_timing("admin_crud_delete_device")
async def admin_delete_device(
    request: Request,
    device_id: str,
    device_type: str = Query(..., description="Device type: ava4, kati, qube-vital"),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Soft delete device"""
    request_id = getattr(request.state, 'request_id', None)
    
    try:
        # Validate device_id format
        if not ObjectId.is_valid(device_id):
            error_response = create_error_response(
                "INVALID_DEVICE_ID",
                custom_message="Invalid device ID format",
                field="device_id",
                value=device_id,
                request_id=request_id
            )
            return JSONResponse(status_code=400, content=error_response.dict())
        
        collection_name = get_device_collection_name(device_type, request_id)
        collection = mongodb_service.get_collection(collection_name)
        
        # Set soft delete fields based on device type
        update_data = {
            "updated_at": datetime.utcnow(),
            "deleted_at": datetime.utcnow(),
            "deleted_by": current_user.get("username", "unknown")
        }
        
        if device_type == "ava4" or device_type == "qube-vital":
            update_data["is_deleted"] = True
        elif device_type == "kati":
            update_data["status"] = "deleted"
        
        result = await collection.update_one(
            {"_id": ObjectId(device_id)},
            {"$set": update_data}
        )
        
        if result.matched_count == 0:
            error_response = create_error_response(
                "DEVICE_NOT_FOUND",
                custom_message=f"Device with ID {device_id} not found",
                field="device_id",
                value=device_id,
                request_id=request_id
            )
            return JSONResponse(status_code=404, content=error_response.dict())
        
        # Log audit trail
        username = current_user.get("username", "unknown")
        await audit_logger.log_admin_action(
            action="DELETE",
            resource_type="Device",
            resource_id=device_id,
            user_id=username,
            details={"device_type": device_type}
        )
        
        success_response = create_success_response(
            message="Device deleted successfully",
            data={
                "device_id": device_id,
                "device_type": device_type,
                "deleted_by": current_user.get("username", "unknown")
            },
            request_id=request_id
        )
        return JSONResponse(content=success_response.dict())
        
    except ValueError as e:
        error_response = create_error_response(
            "INVALID_DEVICE_TYPE",
            custom_message=str(e),
            field="device_type",
            value=device_type,
            request_id=request_id
        )
        return JSONResponse(status_code=400, content=error_response.dict())
    except Exception as e:
        error_response = create_error_response(
            "INTERNAL_SERVER_ERROR",
            custom_message=f"Failed to delete device: {str(e)}",
            request_id=request_id
        )
        return JSONResponse(status_code=500, content=error_response.dict())

# ==================== MEDICAL HISTORY CRUD OPERATIONS ====================

@router.get("/medical-history/{history_type}/{record_id}")
@api_endpoint_timing("admin_crud_get_medical_history")
async def get_medical_history_record(
    request: Request,
    history_type: str,
    record_id: str,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get specific medical history record"""
    request_id = getattr(request.state, 'request_id', None)
    
    try:
        # Validate record_id format
        if not ObjectId.is_valid(record_id):
            error_response = create_error_response(
                "INVALID_RECORD_ID",
                custom_message="Invalid record ID format",
                field="record_id",
                value=record_id,
                request_id=request_id
            )
            return JSONResponse(status_code=400, content=error_response.dict())
        
        collection_name = get_medical_history_collection_name(history_type, request_id)
        collection = mongodb_service.get_collection(collection_name)
        
        record = await collection.find_one({"_id": ObjectId(record_id)})
        
        if not record:
            error_response = create_error_response(
                "MEDICAL_HISTORY_NOT_FOUND",
                custom_message=f"Medical history record with ID {record_id} not found",
                field="record_id",
                value=record_id,
                request_id=request_id
            )
            return JSONResponse(status_code=404, content=error_response.dict())
        
        record = serialize_mongodb_response(record)
        
        success_response = create_success_response(
            message="Medical history record retrieved successfully",
            data={"record": record, "history_type": history_type},
            request_id=request_id
        )
        return JSONResponse(content=success_response.dict())
        
    except ValueError as e:
        error_response = create_error_response(
            "INVALID_HISTORY_TYPE",
            custom_message=str(e),
            field="history_type",
            value=history_type,
            request_id=request_id
        )
        return JSONResponse(status_code=400, content=error_response.dict())
    except Exception as e:
        error_response = create_error_response(
            "INTERNAL_SERVER_ERROR",
            custom_message=f"Failed to retrieve medical history: {str(e)}",
            request_id=request_id
        )
        return JSONResponse(status_code=500, content=error_response.dict())

# ==================== MASTER DATA CRUD OPERATIONS ====================

@router.get("/master-data/{data_type}/{record_id}")
async def get_master_data_record(
    data_type: str,
    record_id: str,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get specific master data record"""
    try:
        collection_name = get_master_data_collection_name(data_type)
        collection = mongodb_service.get_collection(collection_name)
        
        record = await collection.find_one({"_id": ObjectId(record_id)})
        if not record:
            raise HTTPException(status_code=404, detail="Master data record not found")
        
        record = serialize_mongodb_response(record)
        return JSONResponse(content=record)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/master-data")
async def create_master_data(
    master_data: MasterDataCreate,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Create new master data record"""
    try:
        collection_name = get_master_data_collection_name(master_data.data_type)
        collection = mongodb_service.get_collection(collection_name)
        
        # Check if record with same code already exists (for data types that use codes)
        if master_data.code:
            existing_record = await collection.find_one({"code": master_data.code})
            if existing_record:
                raise HTTPException(status_code=400, detail="Record with this code already exists")
        
        # Prepare master data
        data = {
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "is_active": master_data.is_active,
            "created_by": current_user.get("username", "unknown")
        }
        
        # Add fields based on data type
        if master_data.name:
            data["name"] = master_data.name
        if master_data.code:
            data["code"] = master_data.code
        if master_data.province_code:
            data["province_code"] = master_data.province_code
        if master_data.district_code:
            data["district_code"] = master_data.district_code
        if master_data.sub_district_code:
            data["sub_district_code"] = master_data.sub_district_code
        
        # Add additional fields
        if master_data.additional_fields:
            data.update(master_data.additional_fields)
        
        # Set data type specific fields
        if master_data.data_type in ["provinces", "districts", "sub_districts", "hospitals"]:
            data["is_deleted"] = False
        elif master_data.data_type == "hospital_types":
            data["active"] = master_data.is_active
        
        result = await collection.insert_one(data)
        
        # Log audit trail
        username = current_user.get("username", "unknown")
        await audit_logger.log_admin_action(
            action="CREATE",
            resource_type="MasterData",
            resource_id=str(result.inserted_id),
            user_id=username,
            details={"data_type": master_data.data_type, "code": master_data.code}
        )
        
        return {"success": True, "record_id": str(result.inserted_id)}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/master-data/{data_type}/{record_id}")
async def update_master_data(
    data_type: str,
    record_id: str,
    master_data: MasterDataUpdate,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Update master data record"""
    try:
        collection_name = get_master_data_collection_name(data_type)
        collection = mongodb_service.get_collection(collection_name)
        
        update_data = master_data.dict(exclude_unset=True)
        update_data["updated_at"] = datetime.utcnow()
        update_data["updated_by"] = current_user.get("username", "unknown")
        
        # Handle special fields for hospital_types
        if data_type == "hospital_types" and "is_active" in update_data:
            update_data["active"] = update_data["is_active"]
            del update_data["is_active"]
        
        result = await collection.update_one(
            {"_id": ObjectId(record_id)},
            {"$set": update_data}
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Master data record not found")
        
        # Log audit trail
        username = current_user.get("username", "unknown")
        await audit_logger.log_admin_action(
            action="UPDATE",
            resource_type="MasterData",
            resource_id=record_id,
            user_id=username,
            details={"data_type": data_type}
        )
        
        return {"success": True, "message": "Master data updated successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/master-data/{data_type}/{record_id}")
async def delete_master_data(
    data_type: str,
    record_id: str,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Soft delete master data record"""
    try:
        collection_name = get_master_data_collection_name(data_type)
        collection = mongodb_service.get_collection(collection_name)
        
        update_data = {
            "updated_at": datetime.utcnow(),
            "deleted_at": datetime.utcnow(),
            "deleted_by": current_user.get("username", "unknown")
        }
        
        # Set deletion fields based on data type
        if data_type in ["provinces", "districts", "sub_districts", "hospitals"]:
            update_data["is_deleted"] = True
        elif data_type == "hospital_types":
            update_data["active"] = False
        
        result = await collection.update_one(
            {"_id": ObjectId(record_id)},
            {"$set": update_data}
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Master data record not found")
        
        # Log audit trail
        username = current_user.get("username", "unknown")
        await audit_logger.log_admin_action(
            action="DELETE",
            resource_type="MasterData",
            resource_id=record_id,
            user_id=username,
            details={"data_type": data_type}
        )
        
        return {"success": True, "message": "Master data deleted successfully"}
        
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

def get_medical_history_collection_name(history_type: str, request_id: Optional[str] = None) -> str:
    """Get collection name for medical history type"""
    collection_mapping = {
        "blood_pressure": "blood_pressure_histories",
        "blood_sugar": "blood_sugar_histories",
        "temperature": "temprature_data_histories",
        "spo2": "spo2_histories",
        "step": "step_histories",
        "sleep": "sleep_data_histories",
        "creatinine": "creatinine_histories",
        "medication": "medication_histories"
    }
    
    collection_name = collection_mapping.get(history_type)
    if not collection_name:
        supported_types = list(collection_mapping.keys())
        raise ValueError(f"Invalid history type: {history_type}. Supported types: {supported_types}")
    
    return collection_name

def get_master_data_collection_name(data_type: str, request_id: Optional[str] = None) -> str:
    """Get collection name for master data type"""
    collection_mapping = {
        "hospitals": "hospitals",
        "provinces": "provinces", 
        "districts": "districts",
        "sub_districts": "sub_districts",
        "hospital_types": "master_hospital_types"
    }
    
    collection_name = collection_mapping.get(data_type)
    if not collection_name:
        supported_types = list(collection_mapping.keys())
        raise ValueError(f"Invalid data type: {data_type}. Supported types: {supported_types}")
    
    return collection_name 