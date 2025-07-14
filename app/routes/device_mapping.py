import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, Depends, Query, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field, ValidationError
from bson import ObjectId
from app.services.mongo import mongodb_service
from app.services.auth import require_auth
from app.services.audit_logger import audit_logger
from app.utils.json_encoder import serialize_mongodb_response
from app.utils.error_definitions import (
    create_error_response, 
    create_success_response, 
    ErrorResponse, 
    SuccessResponse
)

router = APIRouter(prefix="/admin/device-mapping", tags=["device-mapping"])

# Note: Error definitions are now imported from app.utils.error_definitions

# Pydantic Models for Device Mapping
class DeviceMappingCreate(BaseModel):
    patient_id: str = Field(..., description="Patient ID to assign devices to", min_length=24, max_length=24)
    ava4_box_id: Optional[str] = Field(None, description="AVA4 Box ID", min_length=24, max_length=24)
    kati_watch_id: Optional[str] = Field(None, description="Kati Watch ID", min_length=24, max_length=24)
    medical_devices: Optional[Dict[str, str]] = Field(None, description="Medical device MAC addresses")

class DeviceMappingUpdate(BaseModel):
    ava4_box_id: Optional[str] = Field(None, description="AVA4 Box ID", min_length=24, max_length=24)
    kati_watch_id: Optional[str] = Field(None, description="Kati Watch ID", min_length=24, max_length=24)
    medical_devices: Optional[Dict[str, str]] = Field(None, description="Medical device MAC addresses")

class MedicalDeviceCreate(BaseModel):
    patient_id: str = Field(..., description="Patient ID", min_length=24, max_length=24)
    device_type: str = Field(..., description="Device type (mac_gw, mac_dusun_bps, mac_oxymeter, etc.)")
    mac_address: str = Field(..., description="Device MAC address", min_length=1, max_length=17)
    device_name: Optional[str] = Field(None, description="Device name", max_length=100)
    notes: Optional[str] = Field(None, description="Additional notes", max_length=500)

class MedicalDeviceUpdate(BaseModel):
    device_type: Optional[str] = Field(None, description="Device type")
    mac_address: Optional[str] = Field(None, description="Device MAC address", min_length=1, max_length=17)
    device_name: Optional[str] = Field(None, description="Device name", max_length=100)
    notes: Optional[str] = Field(None, description="Additional notes", max_length=500)

class AVA4BoxAssignment(BaseModel):
    patient_id: str = Field(..., description="Patient ID", min_length=24, max_length=24)
    box_id: str = Field(..., description="AVA4 Box ID", min_length=24, max_length=24)
    location: Optional[str] = Field(None, description="Installation location", max_length=200)
    notes: Optional[str] = Field(None, description="Assignment notes", max_length=500)

class KatiWatchAssignment(BaseModel):
    patient_id: str = Field(..., description="Patient ID", min_length=24, max_length=24)
    watch_id: str = Field(..., description="Kati Watch ID", min_length=24, max_length=24)
    notes: Optional[str] = Field(None, description="Assignment notes", max_length=500)

# Device Type Mapping
DEVICE_TYPES = {
    "mac_gw": "AVA4 Gateway",
    "mac_dusun_bps": "Blood Pressure Monitor",
    "mac_oxymeter": "Oximeter",
    "mac_mgss_oxymeter": "MGSS Oximeter",
    "mac_weight": "Weight Scale",
    "mac_gluc": "Glucose Meter",
    "mac_body_temp": "Body Temperature Sensor",
    "mac_chol": "Cholesterol Meter",
    "mac_ua": "Uric Acid Meter",
    "mac_salt_meter": "Salt Meter",
    "mac_watch": "Smart Watch"
}

# Helper Functions
def validate_object_id(object_id: str, field_name: str) -> ObjectId:
    """Validate and convert string to ObjectId"""
    try:
        return ObjectId(object_id)
    except Exception:
        raise HTTPException(
            status_code=400,
            detail=create_error_response(
                "INVALID_OBJECT_ID",
                field=field_name,
                value=object_id,
                custom_message=f"Invalid ObjectId format for {field_name}"
            ).dict()
        )

def validate_device_type(device_type: str) -> None:
    """Validate device type"""
    if device_type not in DEVICE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=create_error_response(
                "INVALID_DEVICE_TYPE",
                field="device_type",
                value=device_type,
                custom_message=f"Invalid device type '{device_type}'. Supported types: {', '.join(DEVICE_TYPES.keys())}"
            ).dict()
        )

async def validate_patient_exists(patient_id: str) -> Dict[str, Any]:
    """Validate patient exists"""
    try:
        object_id = validate_object_id(patient_id, "patient_id")
        patients_collection = mongodb_service.get_collection("patients")
        patient = await patients_collection.find_one({"_id": object_id})
        
        if not patient:
            raise HTTPException(
                status_code=404,
                detail=create_error_response(
                    "PATIENT_NOT_FOUND",
                    field="patient_id",
                    value=patient_id
                ).dict()
            )
        
        return patient
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                "DATABASE_ERROR",
                custom_message=f"Failed to validate patient: {str(e)}"
            ).dict()
        )

async def validate_ava4_box_exists(box_id: str) -> Dict[str, Any]:
    """Validate AVA4 box exists"""
    try:
        object_id = validate_object_id(box_id, "box_id")
        boxes_collection = mongodb_service.get_collection("amy_boxes")
        box = await boxes_collection.find_one({"_id": object_id})
        
        if not box:
            raise HTTPException(
                status_code=404,
                detail=create_error_response(
                    "AVA4_BOX_NOT_FOUND",
                    field="box_id",
                    value=box_id
                ).dict()
            )
        
        return box
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                "DATABASE_ERROR",
                custom_message=f"Failed to validate AVA4 box: {str(e)}"
            ).dict()
        )

async def validate_kati_watch_exists(watch_id: str) -> Dict[str, Any]:
    """Validate Kati watch exists"""
    try:
        object_id = validate_object_id(watch_id, "watch_id")
        watches_collection = mongodb_service.get_collection("watches")
        watch = await watches_collection.find_one({"_id": object_id})
        
        if not watch:
            raise HTTPException(
                status_code=404,
                detail=create_error_response(
                    "KATI_WATCH_NOT_FOUND",
                    field="watch_id",
                    value=watch_id
                ).dict()
            )
        
        return watch
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                "DATABASE_ERROR",
                custom_message=f"Failed to validate Kati watch: {str(e)}"
            ).dict()
        )

@router.get("/device-types", response_model=Dict[str, Any])
async def get_device_types(
    request: Request,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get available device types with their descriptions"""
    try:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        success_response = create_success_response(
            message="Device types retrieved successfully",
            data={
                "device_types": DEVICE_TYPES,
                "total_types": len(DEVICE_TYPES)
            },
            request_id=request_id
        )
        return success_response.dict()
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                "INTERNAL_SERVER_ERROR",
                custom_message=f"Failed to get device types: {str(e)}",
                request_id=request.headers.get("X-Request-ID") or str(uuid.uuid4())
            ).dict()
        )

@router.get("/available/ava4-boxes", response_model=Dict[str, Any])
async def get_available_ava4_boxes(
    request: Request,
    limit: int = Query(100, ge=1, le=1000),
    skip: int = Query(0, ge=0),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get available AVA4 boxes (not assigned to any patient)"""
    try:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        boxes_collection = mongodb_service.get_collection("amy_boxes")
        
        # Find boxes without patient_id or with null patient_id
        query = {"$or": [{"patient_id": {"$exists": False}}, {"patient_id": None}]}
        
        boxes_cursor = boxes_collection.find(query).skip(skip).limit(limit)
        boxes = await boxes_cursor.to_list(length=limit)
        
        total = await boxes_collection.count_documents(query)
        
        success_response = create_success_response(
            message="Available AVA4 boxes retrieved successfully",
            data={
                "available_boxes": serialize_mongodb_response(boxes),
                "total": total,
                "limit": limit,
                "skip": skip
            },
            request_id=request_id
        )
        return success_response.dict()
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                "INTERNAL_SERVER_ERROR",
                custom_message=f"Failed to get available AVA4 boxes: {str(e)}",
                request_id=request.headers.get("X-Request-ID") or str(uuid.uuid4())
            ).dict()
        )

@router.get("/available/kati-watches", response_model=Dict[str, Any])
async def get_available_kati_watches(
    request: Request,
    limit: int = Query(100, ge=1, le=1000),
    skip: int = Query(0, ge=0),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get available Kati watches (not assigned to any patient)"""
    try:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        watches_collection = mongodb_service.get_collection("watches")
        
        # Find watches without patient_id or with null patient_id
        query = {"$or": [{"patient_id": {"$exists": False}}, {"patient_id": None}]}
        
        watches_cursor = watches_collection.find(query).skip(skip).limit(limit)
        watches = await watches_cursor.to_list(length=limit)
        
        total = await watches_collection.count_documents(query)
        
        success_response = create_success_response(
            message="Available Kati watches retrieved successfully",
            data={
                "available_watches": serialize_mongodb_response(watches),
                "total": total,
                "limit": limit,
                "skip": skip
            },
            request_id=request_id
        )
        return success_response.dict()
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                "INTERNAL_SERVER_ERROR",
                custom_message=f"Failed to get available Kati watches: {str(e)}",
                request_id=request.headers.get("X-Request-ID") or str(uuid.uuid4())
            ).dict()
        )

@router.get("/", response_model=Dict[str, Any])
async def get_device_mappings(
    patient_id: Optional[str] = Query(None, description="Filter by patient ID"),
    device_type: Optional[str] = Query(None, description="Filter by device type"),
    limit: int = Query(100, ge=1, le=1000),
    skip: int = Query(0, ge=0),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get device mappings with filtering and pagination"""
    try:
        mappings = []
        
        # Get patient filter
        patient_filter = {}
        if patient_id:
            patient_filter["_id"] = ObjectId(patient_id)
        
        # Get patients with their device mappings
        patients_collection = mongodb_service.get_collection("patients")
        patients_cursor = patients_collection.find(patient_filter).sort("_id", 1).skip(skip).limit(limit)
        patients = await patients_cursor.to_list(length=limit)
        
        for patient in patients:
            patient_id_str = str(patient["_id"])
            
            # Get AVA4 boxes for this patient
            ava4_boxes = []
            if "ava_mac_address" in patient and patient["ava_mac_address"]:
                boxes_collection = mongodb_service.get_collection("amy_boxes")
                boxes_cursor = boxes_collection.find({"patient_id": patient["_id"]})
                boxes = await boxes_cursor.to_list(length=None)
                ava4_boxes = serialize_mongodb_response(boxes)
            
            # Get Kati watches for this patient
            kati_watches = []
            if "watch_mac_address" in patient and patient["watch_mac_address"]:
                watches_collection = mongodb_service.get_collection("watches")
                watches_cursor = watches_collection.find({"patient_id": patient["_id"]})
                watches = await watches_cursor.to_list(length=None)
                kati_watches = serialize_mongodb_response(watches)
            
            # Get medical devices for this patient
            medical_devices = []
            devices_collection = mongodb_service.get_collection("amy_devices")
            devices_cursor = devices_collection.find({"patient_id": patient["_id"]})
            devices = await devices_cursor.to_list(length=None)
            medical_devices = serialize_mongodb_response(devices)
            
            mapping = {
                "patient_id": patient_id_str,
                "patient_name": f"{patient.get('first_name', '')} {patient.get('last_name', '')}".strip(),
                "ava4_boxes": ava4_boxes,
                "kati_watches": kati_watches,
                "medical_devices": medical_devices,
                "created_at": patient.get("created_at"),
                "updated_at": patient.get("updated_at")
            }
            mappings.append(mapping)
        
        # Get total count
        total = await patients_collection.count_documents(patient_filter)
        
        response_data = {
            "mappings": mappings,
            "total": total,
            "limit": limit,
            "skip": skip,
            "device_types": DEVICE_TYPES
        }
        
        return JSONResponse(content=response_data)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get device mappings: {str(e)}")

@router.get("/{patient_id}", response_model=Dict[str, Any])
async def get_patient_device_mapping(
    patient_id: str,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get device mapping for a specific patient"""
    try:
        # Validate patient exists
        patients_collection = mongodb_service.get_collection("patients")
        patient = await patients_collection.find_one({"_id": ObjectId(patient_id)})
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")
        
        # Get AVA4 boxes
        boxes_collection = mongodb_service.get_collection("amy_boxes")
        boxes_cursor = boxes_collection.find({"patient_id": ObjectId(patient_id)})
        ava4_boxes = await boxes_cursor.to_list(length=None)
        
        # Get Kati watches
        watches_collection = mongodb_service.get_collection("watches")
        watches_cursor = watches_collection.find({"patient_id": ObjectId(patient_id)})
        kati_watches = await watches_cursor.to_list(length=None)
        
        # Get medical devices
        devices_collection = mongodb_service.get_collection("amy_devices")
        devices_cursor = devices_collection.find({"patient_id": ObjectId(patient_id)})
        medical_devices = await devices_cursor.to_list(length=None)
        
        mapping = {
            "patient_id": patient_id,
            "patient_name": f"{patient.get('first_name', '')} {patient.get('last_name', '')}".strip(),
            "patient_details": serialize_mongodb_response(patient),
            "ava4_boxes": serialize_mongodb_response(ava4_boxes),
            "kati_watches": serialize_mongodb_response(kati_watches),
            "medical_devices": serialize_mongodb_response(medical_devices),
            "device_types": DEVICE_TYPES
        }
        
        return JSONResponse(content=mapping)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get patient device mapping: {str(e)}")

@router.post("/ava4-box", response_model=Dict[str, Any])
async def assign_ava4_box(
    assignment: AVA4BoxAssignment,
    request: Request,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Assign AVA4 box to patient"""
    try:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        # Validate patient exists
        patient = await validate_patient_exists(assignment.patient_id)
        
        # Validate box exists and is available
        box = await validate_ava4_box_exists(assignment.box_id)
        
        # Check if box is already assigned
        if box.get("patient_id") and str(box["patient_id"]) != assignment.patient_id:
            raise HTTPException(
                status_code=409,
                detail=create_error_response(
                    "DEVICE_ALREADY_ASSIGNED",
                    field="box_id",
                    value=assignment.box_id,
                    custom_message=f"AVA4 box is already assigned to patient {str(box['patient_id'])}",
                    request_id=request_id
                ).dict()
            )
        
        # Update box assignment
        boxes_collection = mongodb_service.get_collection("amy_boxes")
        update_data = {
            "patient_id": ObjectId(assignment.patient_id),
            "updated_at": datetime.utcnow()
        }
        if assignment.location:
            update_data["location"] = assignment.location
        
        await boxes_collection.update_one(
            {"_id": ObjectId(assignment.box_id)},
            {"$set": update_data}
        )
        
        # Update patient's ava_mac_address
        patients_collection = mongodb_service.get_collection("patients")
        await patients_collection.update_one(
            {"_id": ObjectId(assignment.patient_id)},
            {"$set": {
                "ava_mac_address": box.get("mac_address"),
                "updated_at": datetime.utcnow()
            }}
        )
        
        # Log the assignment
        await audit_logger.log_admin_action(
            user_id=current_user.get("user_id", "system"),
            action="assign_ava4_box",
            resource_type="device_mapping",
            resource_id=assignment.box_id,
            details={
                "patient_id": assignment.patient_id,
                "box_id": assignment.box_id,
                "location": assignment.location,
                "notes": assignment.notes
            }
        )
        
        # Create success response
        success_response = create_success_response(
            message="AVA4 box assigned successfully",
            data={
                "patient_id": assignment.patient_id,
                "box_id": assignment.box_id,
                "mac_address": box.get("mac_address"),
                "location": assignment.location
            },
            request_id=request_id
        )
        
        return JSONResponse(content=success_response.dict())
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                "INTERNAL_SERVER_ERROR",
                custom_message=f"Failed to assign AVA4 box: {str(e)}",
                request_id=request_id
            ).dict()
        )

@router.post("/kati-watch", response_model=Dict[str, Any])
async def assign_kati_watch(
    assignment: KatiWatchAssignment,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Assign Kati watch to patient"""
    try:
        # Validate patient exists
        patients_collection = mongodb_service.get_collection("patients")
        patient = await patients_collection.find_one({"_id": ObjectId(assignment.patient_id)})
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")
        
        # Validate watch exists and is available
        watches_collection = mongodb_service.get_collection("watches")
        watch = await watches_collection.find_one({"_id": ObjectId(assignment.watch_id)})
        if not watch:
            raise HTTPException(status_code=404, detail="Kati watch not found")
        
        # Check if watch is already assigned
        if watch.get("patient_id") and str(watch["patient_id"]) != assignment.patient_id:
            raise HTTPException(status_code=400, detail="Kati watch is already assigned to another patient")
        
        # Update watch assignment
        await watches_collection.update_one(
            {"_id": ObjectId(assignment.watch_id)},
            {"$set": {
                "patient_id": ObjectId(assignment.patient_id),
                "updated_at": datetime.utcnow()
            }}
        )
        
        # Update patient's watch_mac_address
        await patients_collection.update_one(
            {"_id": ObjectId(assignment.patient_id)},
            {"$set": {
                "watch_mac_address": watch.get("imei"),
                "updated_at": datetime.utcnow()
            }}
        )
        
        # Log the assignment
        await audit_logger.log_action(
            user_id=current_user.get("user_id"),
            action="assign_kati_watch",
            resource_type="device_mapping",
            resource_id=assignment.watch_id,
            details={
                "patient_id": assignment.patient_id,
                "watch_id": assignment.watch_id,
                "notes": assignment.notes
            }
        )
        
        return JSONResponse(content={
            "message": "Kati watch assigned successfully",
            "patient_id": assignment.patient_id,
            "watch_id": assignment.watch_id,
            "imei": watch.get("imei")
        })
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to assign Kati watch: {str(e)}")

@router.post("/medical-device", response_model=Dict[str, Any])
async def assign_medical_device(
    device: MedicalDeviceCreate,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Assign medical device to patient"""
    try:
        # Validate patient exists
        patients_collection = mongodb_service.get_collection("patients")
        patient = await patients_collection.find_one({"_id": ObjectId(device.patient_id)})
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")
        
        # Validate device type
        if device.device_type not in DEVICE_TYPES:
            raise HTTPException(status_code=400, detail=f"Invalid device type. Must be one of: {list(DEVICE_TYPES.keys())}")
        
        # Check if patient already has a device record
        devices_collection = mongodb_service.get_collection("amy_devices")
        existing_device = await devices_collection.find_one({"patient_id": ObjectId(device.patient_id)})
        
        if existing_device:
            # Update existing device record
            update_data = {
                device.device_type: device.mac_address,
                "updated_at": datetime.utcnow()
            }
            
            await devices_collection.update_one(
                {"_id": existing_device["_id"]},
                {"$set": update_data}
            )
            device_id = str(existing_device["_id"])
        else:
            # Create new device record
            device_data = {
                "patient_id": ObjectId(device.patient_id),
                "user_id": None,
                "group": "",
                device.device_type: device.mac_address,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            # Initialize all other device types as empty
            for device_type in DEVICE_TYPES.keys():
                if device_type not in device_data:
                    device_data[device_type] = ""
            
            result = await devices_collection.insert_one(device_data)
            device_id = str(result.inserted_id)
        
        # Log the assignment
        await audit_logger.log_action(
            user_id=current_user.get("user_id"),
            action="assign_medical_device",
            resource_type="device_mapping",
            resource_id=device_id,
            details={
                "patient_id": device.patient_id,
                "device_type": device.device_type,
                "mac_address": device.mac_address,
                "device_name": device.device_name,
                "notes": device.notes
            }
        )
        
        return JSONResponse(content={
            "message": "Medical device assigned successfully",
            "patient_id": device.patient_id,
            "device_id": device_id,
            "device_type": device.device_type,
            "device_name": DEVICE_TYPES[device.device_type],
            "mac_address": device.mac_address
        })
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to assign medical device: {str(e)}")

@router.put("/medical-device/{device_id}", response_model=Dict[str, Any])
async def update_medical_device(
    device_id: str,
    device_update: MedicalDeviceUpdate,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Update medical device assignment"""
    try:
        devices_collection = mongodb_service.get_collection("amy_devices")
        device = await devices_collection.find_one({"_id": ObjectId(device_id)})
        if not device:
            raise HTTPException(status_code=404, detail="Device record not found")
        
        # Build update data
        update_data = {"updated_at": datetime.utcnow()}
        
        if device_update.device_type and device_update.mac_address:
            # Validate device type
            if device_update.device_type not in DEVICE_TYPES:
                raise HTTPException(status_code=400, detail=f"Invalid device type. Must be one of: {list(DEVICE_TYPES.keys())}")
            
            # Clear old device type and set new one
            for device_type in DEVICE_TYPES.keys():
                if device.get(device_type) == device.get(device_update.device_type):
                    update_data[device_type] = ""
            
            update_data[device_update.device_type] = device_update.mac_address
        
        # Update device record
        await devices_collection.update_one(
            {"_id": ObjectId(device_id)},
            {"$set": update_data}
        )
        
        # Log the update
        await audit_logger.log_action(
            user_id=current_user.get("user_id"),
            action="update_medical_device",
            resource_type="device_mapping",
            resource_id=device_id,
            details={
                "patient_id": str(device["patient_id"]),
                "device_type": device_update.device_type,
                "mac_address": device_update.mac_address,
                "device_name": device_update.device_name,
                "notes": device_update.notes
            }
        )
        
        return JSONResponse(content={
            "message": "Medical device updated successfully",
            "device_id": device_id,
            "device_type": device_update.device_type,
            "mac_address": device_update.mac_address
        })
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update medical device: {str(e)}")

@router.delete("/ava4-box/{box_id}", response_model=Dict[str, Any])
async def unassign_ava4_box(
    box_id: str,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Unassign AVA4 box from patient"""
    try:
        boxes_collection = mongodb_service.get_collection("amy_boxes")
        box = await boxes_collection.find_one({"_id": ObjectId(box_id)})
        if not box:
            raise HTTPException(status_code=404, detail="AVA4 box not found")
        
        patient_id = box.get("patient_id")
        if not patient_id:
            raise HTTPException(status_code=400, detail="AVA4 box is not assigned to any patient")
        
        # Remove assignment from box
        await boxes_collection.update_one(
            {"_id": ObjectId(box_id)},
            {"$unset": {"patient_id": ""}, "$set": {"updated_at": datetime.utcnow()}}
        )
        
        # Remove from patient record
        patients_collection = mongodb_service.get_collection("patients")
        await patients_collection.update_one(
            {"_id": patient_id},
            {"$unset": {"ava_mac_address": ""}, "$set": {"updated_at": datetime.utcnow()}}
        )
        
        # Log the unassignment
        await audit_logger.log_action(
            user_id=current_user.get("user_id"),
            action="unassign_ava4_box",
            resource_type="device_mapping",
            resource_id=box_id,
            details={
                "patient_id": str(patient_id),
                "box_id": box_id
            }
        )
        
        return JSONResponse(content={
            "message": "AVA4 box unassigned successfully",
            "box_id": box_id,
            "patient_id": str(patient_id)
        })
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to unassign AVA4 box: {str(e)}")

@router.delete("/kati-watch/{watch_id}", response_model=Dict[str, Any])
async def unassign_kati_watch(
    watch_id: str,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Unassign Kati watch from patient"""
    try:
        watches_collection = mongodb_service.get_collection("watches")
        watch = await watches_collection.find_one({"_id": ObjectId(watch_id)})
        if not watch:
            raise HTTPException(status_code=404, detail="Kati watch not found")
        
        patient_id = watch.get("patient_id")
        if not patient_id:
            raise HTTPException(status_code=400, detail="Kati watch is not assigned to any patient")
        
        # Remove assignment from watch
        await watches_collection.update_one(
            {"_id": ObjectId(watch_id)},
            {"$unset": {"patient_id": 1}, "$set": {"updated_at": datetime.utcnow()}}
        )
        
        # Remove from patient record
        patients_collection = mongodb_service.get_collection("patients")
        await patients_collection.update_one(
            {"_id": patient_id},
            {"$unset": {"watch_mac_address": 1}, "$set": {"updated_at": datetime.utcnow()}}
        )
        
        # Log the unassignment
        await audit_logger.log_action(
            user_id=current_user.get("user_id"),
            action="unassign_kati_watch",
            resource_type="device_mapping",
            resource_id=watch_id,
            details={
                "patient_id": str(patient_id),
                "watch_id": watch_id
            }
        )
        
        return JSONResponse(content={
            "message": "Kati watch unassigned successfully",
            "watch_id": watch_id,
            "patient_id": str(patient_id)
        })
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to unassign Kati watch: {str(e)}")

@router.delete("/medical-device/{device_id}", response_model=Dict[str, Any])
async def remove_medical_device(
    device_id: str,
    device_type: str = Query(..., description="Device type to remove"),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Remove medical device assignment"""
    try:
        # Validate device type
        if device_type not in DEVICE_TYPES:
            raise HTTPException(status_code=400, detail=f"Invalid device type. Must be one of: {list(DEVICE_TYPES.keys())}")
        
        devices_collection = mongodb_service.get_collection("amy_devices")
        device = await devices_collection.find_one({"_id": ObjectId(device_id)})
        if not device:
            raise HTTPException(status_code=404, detail="Device record not found")
        
        # Remove specific device type
        await devices_collection.update_one(
            {"_id": ObjectId(device_id)},
            {"$unset": {device_type: 1}, "$set": {"updated_at": datetime.utcnow()}}
        )
        
        # Log the removal
        await audit_logger.log_action(
            user_id=current_user.get("user_id"),
            action="remove_medical_device",
            resource_type="device_mapping",
            resource_id=device_id,
            details={
                "patient_id": str(device["patient_id"]),
                "device_type": device_type,
                "device_name": DEVICE_TYPES[device_type]
            }
        )
        
        return JSONResponse(content={
            "message": "Medical device removed successfully",
            "device_id": device_id,
            "device_type": device_type,
            "device_name": DEVICE_TYPES[device_type]
        })
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to remove medical device: {str(e)}")

 