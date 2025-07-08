import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, Depends, Request, Query
from pydantic import BaseModel, Field
from bson import ObjectId
from app.services.mongo import mongodb_service
from app.services.auth import require_auth
from app.services.audit_logger import audit_logger
from app.utils.json_encoder import serialize_mongodb_response
from app.utils.error_definitions import create_error_response, create_success_response
from config import settings, logger

router = APIRouter(prefix="/api/patients", tags=["Patient Medical Devices"])

# Pydantic Models
class PatientDeviceRegistry(BaseModel):
    """Model for patient medical device registry"""
    user_id: Optional[str] = Field(None, description="Healthcare provider managing this patient's devices")
    patient_id: str = Field(..., description="Patient ID these devices belong to")
    group: Optional[str] = Field(None, description="Device group/organization")
    mac_gw: Optional[str] = Field(None, description="Gateway MAC address (AVA4 box)")
    mac_bps: Optional[str] = Field(None, description="Blood pressure monitor MAC address")
    mac_body_temp: Optional[str] = Field(None, description="Body temperature sensor MAC address")
    mac_watch: Optional[str] = Field(None, description="Smart watch MAC address")
    mac_oxymeter: Optional[str] = Field(None, description="Oximeter MAC address")
    mac_weight: Optional[str] = Field(None, description="Weight scale MAC address")
    mac_gluc: Optional[str] = Field(None, description="Glucose meter MAC address")
    mac_chol: Optional[str] = Field(None, description="Cholesterol meter MAC address")
    mac_ua: Optional[str] = Field(None, description="Uric acid meter MAC address")
    mac_dusun_bps: Optional[str] = Field(None, description="Dusun blood pressure monitor MAC address")
    mac_mgss_oxymeter: Optional[str] = Field(None, description="MGSS oximeter MAC address")
    mac_salt_meter: Optional[str] = Field(None, description="Salt meter MAC address")

class PatientDeviceRegistryUpdate(BaseModel):
    """Model for updating patient medical device registry"""
    user_id: Optional[str] = Field(None, description="Healthcare provider managing this patient's devices")
    group: Optional[str] = Field(None, description="Device group/organization")
    mac_gw: Optional[str] = Field(None, description="Gateway MAC address (AVA4 box)")
    mac_bps: Optional[str] = Field(None, description="Blood pressure monitor MAC address")
    mac_body_temp: Optional[str] = Field(None, description="Body temperature sensor MAC address")
    mac_watch: Optional[str] = Field(None, description="Smart watch MAC address")
    mac_oxymeter: Optional[str] = Field(None, description="Oximeter MAC address")
    mac_weight: Optional[str] = Field(None, description="Weight scale MAC address")
    mac_gluc: Optional[str] = Field(None, description="Glucose meter MAC address")
    mac_chol: Optional[str] = Field(None, description="Cholesterol meter MAC address")
    mac_ua: Optional[str] = Field(None, description="Uric acid meter MAC address")
    mac_dusun_bps: Optional[str] = Field(None, description="Dusun blood pressure monitor MAC address")
    mac_mgss_oxymeter: Optional[str] = Field(None, description="MGSS oximeter MAC address")
    mac_salt_meter: Optional[str] = Field(None, description="Salt meter MAC address")

class SingleDeviceRegistration(BaseModel):
    """Model for registering a single device to a patient"""
    device_type: str = Field(..., description="Type of device (bps, body_temp, watch, oxymeter, weight, gluc, chol, ua, dusun_bps, mgss_oxymeter, salt_meter)")
    mac_address: str = Field(..., description="MAC address of the device")
    user_id: Optional[str] = Field(None, description="Healthcare provider registering this device")
    group: Optional[str] = Field(None, description="Device group/organization")

# Available device types mapping
DEVICE_TYPE_MAPPING = {
    "gateway": "mac_gw",
    "bps": "mac_bps", 
    "body_temp": "mac_body_temp",
    "watch": "mac_watch",
    "oxymeter": "mac_oxymeter",
    "weight": "mac_weight",
    "gluc": "mac_gluc",
    "chol": "mac_chol",
    "ua": "mac_ua",
    "dusun_bps": "mac_dusun_bps",
    "mgss_oxymeter": "mac_mgss_oxymeter",
    "salt_meter": "mac_salt_meter"
}

DEVICE_TYPE_DESCRIPTIONS = {
    "gateway": "Gateway Device (AVA4 Box)",
    "bps": "Blood Pressure Monitor",
    "body_temp": "Body Temperature Sensor", 
    "watch": "Smart Watch",
    "oxymeter": "Pulse Oximeter",
    "weight": "Weight Scale",
    "gluc": "Glucose Meter",
    "chol": "Cholesterol Meter",
    "ua": "Uric Acid Meter",
    "dusun_bps": "Dusun Blood Pressure Monitor",
    "mgss_oxymeter": "MGSS Pulse Oximeter",
    "salt_meter": "Salt Meter"
} 

@router.get("/{patient_id}/medical-devices")
async def get_patient_medical_devices(
    patient_id: str,
    request: Request,
    include_device_info: bool = False,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get all medical devices registered to a specific patient"""
    try:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        # Validate patient exists
        patients_collection = mongodb_service.get_collection("patients")
        try:
            patient_obj_id = ObjectId(patient_id)
            patient = await patients_collection.find_one({"_id": patient_obj_id})
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=create_error_response(
                    "INVALID_PATIENT_ID",
                    field="patient_id",
                    value=patient_id,
                    custom_message=f"Invalid patient ID format: {str(e)}",
                    request_id=request_id
                ).dict()
            )
        
        if not patient:
            raise HTTPException(
                status_code=404,
                detail=create_error_response(
                    "PATIENT_NOT_FOUND",
                    field="patient_id",
                    value=patient_id,
                    custom_message=f"Patient with ID '{patient_id}' not found",
                    request_id=request_id
                ).dict()
            )
        
        # Get patient's device registry
        devices_collection = mongodb_service.get_collection("amy_devices")
        device_registry = await devices_collection.find_one({"patient_id": patient_obj_id})
        
        if not device_registry:
            # No devices registered yet - return empty registry
            success_response = create_success_response(
                message="No medical devices registered for this patient",
                data={
                    "patient_id": patient_id,
                    "device_registry": None,
                    "registered_devices": [],
                    "device_count": 0,
                    "patient_info": {
                        "name": f"{patient.get('first_name', '')} {patient.get('last_name', '')}".strip(),
                        "hn": patient.get("hn"),
                        "phone": patient.get("phone")
                    }
                },
                request_id=request_id
            )
            return success_response.dict()
        
        # Serialize the registry
        serialized_registry = serialize_mongodb_response(device_registry)
        
        # Extract registered devices with their details
        registered_devices = []
        device_count = 0
        
        for device_type, mac_field in DEVICE_TYPE_MAPPING.items():
            mac_address = serialized_registry.get(mac_field)
            if mac_address and mac_address.strip():
                device_info = {
                    "device_type": device_type,
                    "device_name": DEVICE_TYPE_DESCRIPTIONS[device_type],
                    "mac_address": mac_address,
                    "mac_field": mac_field
                }
                
                # Add additional device info if requested
                if include_device_info:
                    device_info["additional_info"] = {}
                    
                    # Check for device-specific additional fields
                    for field_name, field_value in serialized_registry.items():
                        if field_name.startswith(mac_field + "_") and field_value:
                            device_info["additional_info"][field_name] = field_value
                
                registered_devices.append(device_info)
                device_count += 1
        
        # Get healthcare provider info if available
        provider_info = None
        if serialized_registry.get("user_id"):
            try:
                users_collection = mongodb_service.get_collection("users")
                provider_obj_id = ObjectId(serialized_registry["user_id"])
                provider = await users_collection.find_one({"_id": provider_obj_id})
                if provider:
                    provider_data = serialize_mongodb_response(provider)
                    provider_info = {
                        "user_id": provider_data.get("_id"),
                        "username": provider_data.get("username"),
                        "email": provider_data.get("email"),
                        "name": f"{provider_data.get('first_name', '')} {provider_data.get('last_name', '')}".strip()
                    }
            except Exception:
                provider_info = None
        
        success_response = create_success_response(
            message="Patient medical devices retrieved successfully",
            data={
                "patient_id": patient_id,
                "device_registry": serialized_registry,
                "registered_devices": registered_devices,
                "device_count": device_count,
                "patient_info": {
                    "name": f"{patient.get('first_name', '')} {patient.get('last_name', '')}".strip(),
                    "hn": patient.get("hn"),
                    "phone": patient.get("phone")
                },
                "provider_info": provider_info,
                "group": serialized_registry.get("group"),
                "registry_created_at": serialized_registry.get("created_at"),
                "registry_updated_at": serialized_registry.get("updated_at")
            },
            request_id=request_id
        )
        
        return success_response.dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting patient medical devices: {e}")
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                "INTERNAL_SERVER_ERROR",
                custom_message=f"Failed to retrieve patient medical devices: {str(e)}",
                request_id=request.headers.get("X-Request-ID") or str(uuid.uuid4())
            ).dict()
        ) 

@router.post("/{patient_id}/medical-devices")
async def register_patient_medical_devices(
    patient_id: str,
    device_data: PatientDeviceRegistry,
    request: Request,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Register medical devices to a patient (create new registry)"""
    try:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        # Validate patient exists
        patients_collection = mongodb_service.get_collection("patients")
        try:
            patient_obj_id = ObjectId(patient_id)
            patient = await patients_collection.find_one({"_id": patient_obj_id})
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=create_error_response(
                    "INVALID_PATIENT_ID",
                    field="patient_id",
                    value=patient_id,
                    custom_message=f"Invalid patient ID format: {str(e)}",
                    request_id=request_id
                ).dict()
            )
        
        if not patient:
            raise HTTPException(
                status_code=404,
                detail=create_error_response(
                    "PATIENT_NOT_FOUND",
                    field="patient_id",
                    value=patient_id,
                    custom_message=f"Patient with ID '{patient_id}' not found",
                    request_id=request_id
                ).dict()
            )
        
        # Check if patient already has a device registry
        devices_collection = mongodb_service.get_collection("amy_devices")
        existing_registry = await devices_collection.find_one({"patient_id": patient_obj_id})
        
        if existing_registry:
            raise HTTPException(
                status_code=400,
                detail=create_error_response(
                    "REGISTRY_ALREADY_EXISTS",
                    field="patient_id",
                    value=patient_id,
                    custom_message=f"Patient '{patient_id}' already has a medical device registry. Use PUT to update.",
                    request_id=request_id
                ).dict()
            )
        
        # Validate user_id if provided
        user_obj_id = None
        if device_data.user_id:
            try:
                user_obj_id = ObjectId(device_data.user_id)
                users_collection = mongodb_service.get_collection("users")
                user = await users_collection.find_one({"_id": user_obj_id})
                
                if not user:
                    raise HTTPException(
                        status_code=404,
                        detail=create_error_response(
                            "USER_NOT_FOUND",
                            field="user_id",
                            value=device_data.user_id,
                            custom_message=f"Healthcare provider with ID '{device_data.user_id}' not found",
                            request_id=request_id
                        ).dict()
                    )
            except Exception as e:
                if "USER_NOT_FOUND" not in str(e):
                    raise HTTPException(
                        status_code=400,
                        detail=create_error_response(
                            "INVALID_USER_ID",
                            field="user_id",
                            value=device_data.user_id,
                            custom_message=f"Invalid user ID format: {str(e)}",
                            request_id=request_id
                        ).dict()
                    )
        
        # Check for duplicate MAC addresses in other registries
        mac_conflicts = []
        for device_type, mac_field in DEVICE_TYPE_MAPPING.items():
            mac_address = getattr(device_data, mac_field, None)
            if mac_address and mac_address.strip():
                # Check if this MAC is already registered to another patient
                existing_device = await devices_collection.find_one({
                    mac_field: mac_address,
                    "patient_id": {"$ne": patient_obj_id}
                })
                if existing_device:
                    other_patient_id = str(existing_device.get("patient_id", ""))
                    mac_conflicts.append({
                        "device_type": device_type,
                        "mac_address": mac_address,
                        "existing_patient_id": other_patient_id
                    })
        
        if mac_conflicts:
            raise HTTPException(
                status_code=400,
                detail=create_error_response(
                    "MAC_ADDRESS_CONFLICTS",
                    field="mac_addresses",
                    value=mac_conflicts,
                    custom_message=f"MAC addresses already registered to other patients: {len(mac_conflicts)} conflicts found",
                    request_id=request_id
                ).dict()
            )
        
        # Create device registry document
        registry_doc = {
            "patient_id": patient_obj_id,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "created_by": current_user.get("username")
        }
        
        # Add user_id if provided
        if user_obj_id:
            registry_doc["user_id"] = user_obj_id
        
        # Add all device MAC addresses
        if device_data.group is not None:
            registry_doc["group"] = device_data.group
        if device_data.mac_gw is not None:
            registry_doc["mac_gw"] = device_data.mac_gw
        if device_data.mac_bps is not None:
            registry_doc["mac_bps"] = device_data.mac_bps
        if device_data.mac_body_temp is not None:
            registry_doc["mac_body_temp"] = device_data.mac_body_temp
        if device_data.mac_watch is not None:
            registry_doc["mac_watch"] = device_data.mac_watch
        if device_data.mac_oxymeter is not None:
            registry_doc["mac_oxymeter"] = device_data.mac_oxymeter
        if device_data.mac_weight is not None:
            registry_doc["mac_weight"] = device_data.mac_weight
        if device_data.mac_gluc is not None:
            registry_doc["mac_gluc"] = device_data.mac_gluc
        if device_data.mac_chol is not None:
            registry_doc["mac_chol"] = device_data.mac_chol
        if device_data.mac_ua is not None:
            registry_doc["mac_ua"] = device_data.mac_ua
        if device_data.mac_dusun_bps is not None:
            registry_doc["mac_dusun_bps"] = device_data.mac_dusun_bps
        if device_data.mac_mgss_oxymeter is not None:
            registry_doc["mac_mgss_oxymeter"] = device_data.mac_mgss_oxymeter
        if device_data.mac_salt_meter is not None:
            registry_doc["mac_salt_meter"] = device_data.mac_salt_meter
        
        # Insert the registry
        insert_result = await devices_collection.insert_one(registry_doc)
        registry_id = str(insert_result.inserted_id)
        
        # Count registered devices
        device_count = 0
        registered_devices = []
        for device_type, mac_field in DEVICE_TYPE_MAPPING.items():
            mac_address = registry_doc.get(mac_field)
            if mac_address and mac_address.strip():
                device_count += 1
                registered_devices.append({
                    "device_type": device_type,
                    "device_name": DEVICE_TYPE_DESCRIPTIONS[device_type],
                    "mac_address": mac_address
                })
        
        # Log audit trail
        await audit_logger.log_admin_action(
            action="CREATE",
            resource_type="PatientDeviceRegistry",
            resource_id=registry_id,
            user_id=current_user.get("username") or "unknown",
            details={
                "patient_id": patient_id,
                "device_count": device_count,
                "registered_devices": registered_devices,
                "healthcare_provider": device_data.user_id,
                "group": device_data.group
            }
        )
        
        # Get created registry with serialization
        created_registry = await devices_collection.find_one({"_id": insert_result.inserted_id})
        serialized_registry = serialize_mongodb_response(created_registry)
        
        success_response = create_success_response(
            message="Patient medical device registry created successfully",
            data={
                "registry_id": registry_id,
                "patient_id": patient_id,
                "device_registry": serialized_registry,
                "registered_devices": registered_devices,
                "device_count": device_count,
                "patient_info": {
                    "name": f"{patient.get('first_name', '')} {patient.get('last_name', '')}".strip(),
                    "hn": patient.get("hn"),
                    "phone": patient.get("phone")
                }
            },
            request_id=request_id
        )
        
        return success_response.dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error registering patient medical devices: {e}")
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                "INTERNAL_SERVER_ERROR",
                custom_message=f"Failed to register patient medical devices: {str(e)}",
                request_id=request.headers.get("X-Request-ID") or str(uuid.uuid4())
            ).dict()
        ) 

@router.put("/{patient_id}/medical-devices")
async def update_patient_medical_devices(
    patient_id: str,
    device_data: PatientDeviceRegistryUpdate,
    request: Request,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Update medical devices registry for a patient"""
    try:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        # Validate patient exists
        patients_collection = mongodb_service.get_collection("patients")
        try:
            patient_obj_id = ObjectId(patient_id)
            patient = await patients_collection.find_one({"_id": patient_obj_id})
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=create_error_response(
                    "INVALID_PATIENT_ID",
                    field="patient_id",
                    value=patient_id,
                    custom_message=f"Invalid patient ID format: {str(e)}",
                    request_id=request_id
                ).dict()
            )
        
        if not patient:
            raise HTTPException(
                status_code=404,
                detail=create_error_response(
                    "PATIENT_NOT_FOUND",
                    field="patient_id",
                    value=patient_id,
                    custom_message=f"Patient with ID '{patient_id}' not found",
                    request_id=request_id
                ).dict()
            )
        
        # Check if patient has a device registry
        devices_collection = mongodb_service.get_collection("amy_devices")
        existing_registry = await devices_collection.find_one({"patient_id": patient_obj_id})
        
        if not existing_registry:
            raise HTTPException(
                status_code=404,
                detail=create_error_response(
                    "REGISTRY_NOT_FOUND",
                    field="patient_id",
                    value=patient_id,
                    custom_message=f"No medical device registry found for patient '{patient_id}'. Use POST to create.",
                    request_id=request_id
                ).dict()
            )
        
        # Validate user_id if provided
        user_obj_id = None
        if device_data.user_id is not None:
            if device_data.user_id.strip():  # Not empty string
                try:
                    user_obj_id = ObjectId(device_data.user_id)
                    users_collection = mongodb_service.get_collection("users")
                    user = await users_collection.find_one({"_id": user_obj_id})
                    
                    if not user:
                        raise HTTPException(
                            status_code=404,
                            detail=create_error_response(
                                "USER_NOT_FOUND",
                                field="user_id",
                                value=device_data.user_id,
                                custom_message=f"Healthcare provider with ID '{device_data.user_id}' not found",
                                request_id=request_id
                            ).dict()
                        )
                except Exception as e:
                    if "USER_NOT_FOUND" not in str(e):
                        raise HTTPException(
                            status_code=400,
                            detail=create_error_response(
                                "INVALID_USER_ID",
                                field="user_id",
                                value=device_data.user_id,
                                custom_message=f"Invalid user ID format: {str(e)}",
                                request_id=request_id
                            ).dict()
                        )
        
        # Check for duplicate MAC addresses in other registries (exclude current patient)
        mac_conflicts = []
        for device_type, mac_field in DEVICE_TYPE_MAPPING.items():
            mac_address = getattr(device_data, mac_field, None)
            if mac_address is not None and mac_address.strip():  # Only check if explicitly provided
                # Check if this MAC is already registered to another patient
                existing_device = await devices_collection.find_one({
                    mac_field: mac_address,
                    "patient_id": {"$ne": patient_obj_id}
                })
                if existing_device:
                    other_patient_id = str(existing_device.get("patient_id", ""))
                    mac_conflicts.append({
                        "device_type": device_type,
                        "mac_address": mac_address,
                        "existing_patient_id": other_patient_id
                    })
        
        if mac_conflicts:
            raise HTTPException(
                status_code=400,
                detail=create_error_response(
                    "MAC_ADDRESS_CONFLICTS",
                    field="mac_addresses",
                    value=mac_conflicts,
                    custom_message=f"MAC addresses already registered to other patients: {len(mac_conflicts)} conflicts found",
                    request_id=request_id
                ).dict()
            )
        
        # Build update document
        update_fields = {
            "updated_at": datetime.utcnow(),
            "updated_by": current_user.get("username")
        }
        unset_fields = {}
        
        # Handle user_id
        if device_data.user_id is not None:
            if device_data.user_id.strip():
                update_fields["user_id"] = user_obj_id
            else:
                unset_fields["user_id"] = ""
        
        # Handle all device MAC addresses
        for device_type, mac_field in DEVICE_TYPE_MAPPING.items():
            mac_address = getattr(device_data, mac_field, None)
            if mac_address is not None:
                if mac_address.strip():
                    update_fields[mac_field] = mac_address
                else:
                    unset_fields[mac_field] = ""
        
        # Handle group
        if device_data.group is not None:
            if device_data.group.strip():
                update_fields["group"] = device_data.group
            else:
                unset_fields["group"] = ""
        
        # Build MongoDB update operation
        update_operation = {}
        if update_fields:
            update_operation["$set"] = update_fields
        if unset_fields:
            update_operation["$unset"] = unset_fields
        
        if not update_operation:
            raise HTTPException(
                status_code=400,
                detail=create_error_response(
                    "NO_CHANGES",
                    custom_message="No changes provided to update",
                    request_id=request_id
                ).dict()
            )
        
        # Update the registry
        update_result = await devices_collection.update_one(
            {"_id": existing_registry["_id"]},
            update_operation
        )
        
        if update_result.modified_count == 0:
            raise HTTPException(
                status_code=500,
                detail=create_error_response(
                    "UPDATE_FAILED",
                    custom_message="Failed to update device registry",
                    request_id=request_id
                ).dict()
            )
        
        # Get updated registry
        updated_registry = await devices_collection.find_one({"_id": existing_registry["_id"]})
        serialized_registry = serialize_mongodb_response(updated_registry)
        
        # Count registered devices
        device_count = 0
        registered_devices = []
        for device_type, mac_field in DEVICE_TYPE_MAPPING.items():
            mac_address = serialized_registry.get(mac_field)
            if mac_address and mac_address.strip():
                device_count += 1
                registered_devices.append({
                    "device_type": device_type,
                    "device_name": DEVICE_TYPE_DESCRIPTIONS[device_type],
                    "mac_address": mac_address
                })
        
        # Log audit trail
        changed_fields = list(update_fields.keys()) + list(unset_fields.keys())
        await audit_logger.log_admin_action(
            action="UPDATE",
            resource_type="PatientDeviceRegistry",
            resource_id=str(existing_registry["_id"]),
            user_id=current_user.get("username") or "unknown",
            details={
                "patient_id": patient_id,
                "changed_fields": changed_fields,
                "device_count": device_count,
                "registered_devices": registered_devices,
                "healthcare_provider": device_data.user_id
            }
        )
        
        success_response = create_success_response(
            message="Patient medical device registry updated successfully",
            data={
                "registry_id": str(existing_registry["_id"]),
                "patient_id": patient_id,
                "device_registry": serialized_registry,
                "registered_devices": registered_devices,
                "device_count": device_count,
                "changed_fields": changed_fields,
                "patient_info": {
                    "name": f"{patient.get('first_name', '')} {patient.get('last_name', '')}".strip(),
                    "hn": patient.get("hn"),
                    "phone": patient.get("phone")
                }
            },
            request_id=request_id
        )
        
        return success_response.dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating patient medical devices: {e}")
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                "INTERNAL_SERVER_ERROR",
                custom_message=f"Failed to update patient medical devices: {str(e)}",
                request_id=request.headers.get("X-Request-ID") or str(uuid.uuid4())
            ).dict()
        ) 

@router.delete("/{patient_id}/medical-devices/{device_type}")
async def unregister_patient_device(
    patient_id: str,
    device_type: str,
    request: Request,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Unregister a specific device type from a patient"""
    try:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        # Validate device type
        if device_type not in DEVICE_TYPE_MAPPING:
            raise HTTPException(
                status_code=400,
                detail=create_error_response(
                    "INVALID_DEVICE_TYPE",
                    field="device_type",
                    value=device_type,
                    custom_message=f"Invalid device type. Valid types: {list(DEVICE_TYPE_MAPPING.keys())}",
                    request_id=request_id
                ).dict()
            )
        
        # Validate patient exists
        patients_collection = mongodb_service.get_collection("patients")
        try:
            patient_obj_id = ObjectId(patient_id)
            patient = await patients_collection.find_one({"_id": patient_obj_id})
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=create_error_response(
                    "INVALID_PATIENT_ID",
                    field="patient_id",
                    value=patient_id,
                    custom_message=f"Invalid patient ID format: {str(e)}",
                    request_id=request_id
                ).dict()
            )
        
        if not patient:
            raise HTTPException(
                status_code=404,
                detail=create_error_response(
                    "PATIENT_NOT_FOUND",
                    field="patient_id",
                    value=patient_id,
                    custom_message=f"Patient with ID '{patient_id}' not found",
                    request_id=request_id
                ).dict()
            )
        
        # Check if patient has a device registry
        devices_collection = mongodb_service.get_collection("amy_devices")
        existing_registry = await devices_collection.find_one({"patient_id": patient_obj_id})
        
        if not existing_registry:
            raise HTTPException(
                status_code=404,
                detail=create_error_response(
                    "REGISTRY_NOT_FOUND",
                    field="patient_id",
                    value=patient_id,
                    custom_message=f"No medical device registry found for patient '{patient_id}'",
                    request_id=request_id
                ).dict()
            )
        
        # Get the MAC field for this device type
        mac_field = DEVICE_TYPE_MAPPING[device_type]
        
        # Check if device is registered
        if not existing_registry.get(mac_field):
            raise HTTPException(
                status_code=404,
                detail=create_error_response(
                    "DEVICE_NOT_REGISTERED",
                    field="device_type",
                    value=device_type,
                    custom_message=f"No {DEVICE_TYPE_DESCRIPTIONS[device_type]} device registered for this patient",
                    request_id=request_id
                ).dict()
            )
        
        # Store device info for audit
        device_mac = existing_registry.get(mac_field)
        device_name = DEVICE_TYPE_DESCRIPTIONS[device_type]
        
        # Remove the device field
        unset_fields = {mac_field: ""}
        
        # Also remove any related fields (like device name, model, etc.)
        for field_name in existing_registry.keys():
            if field_name.startswith(mac_field + "_"):
                unset_fields[field_name] = ""
        
        # Update the registry
        update_result = await devices_collection.update_one(
            {"_id": existing_registry["_id"]},
            {
                "$unset": unset_fields,
                "$set": {
                    "updated_at": datetime.utcnow(),
                    "updated_by": current_user.get("username")
                }
            }
        )
        
        if update_result.modified_count == 0:
            raise HTTPException(
                status_code=500,
                detail=create_error_response(
                    "UNREGISTER_FAILED",
                    custom_message="Failed to unregister device",
                    request_id=request_id
                ).dict()
            )
        
        # Get updated registry
        updated_registry = await devices_collection.find_one({"_id": existing_registry["_id"]})
        serialized_registry = serialize_mongodb_response(updated_registry)
        
        # Count remaining registered devices
        device_count = 0
        registered_devices = []
        for dt, mf in DEVICE_TYPE_MAPPING.items():
            mac_address = serialized_registry.get(mf)
            if mac_address and mac_address.strip():
                device_count += 1
                registered_devices.append({
                    "device_type": dt,
                    "device_name": DEVICE_TYPE_DESCRIPTIONS[dt],
                    "mac_address": mac_address
                })
        
        # Log audit trail
        await audit_logger.log_admin_action(
            action="DELETE",
            resource_type="PatientDeviceRegistry",
            resource_id=str(existing_registry["_id"]),
            user_id=current_user.get("username") or "unknown",
            details={
                "patient_id": patient_id,
                "unregistered_device_type": device_type,
                "unregistered_device_name": device_name,
                "unregistered_mac_address": device_mac,
                "remaining_device_count": device_count,
                "remaining_devices": registered_devices
            }
        )
        
        success_response = create_success_response(
            message=f"{device_name} unregistered successfully from patient",
            data={
                "registry_id": str(existing_registry["_id"]),
                "patient_id": patient_id,
                "unregistered_device": {
                    "device_type": device_type,
                    "device_name": device_name,
                    "mac_address": device_mac
                },
                "device_registry": serialized_registry,
                "remaining_devices": registered_devices,
                "remaining_device_count": device_count,
                "patient_info": {
                    "name": f"{patient.get('first_name', '')} {patient.get('last_name', '')}".strip(),
                    "hn": patient.get("hn"),
                    "phone": patient.get("phone")
                }
            },
            request_id=request_id
        )
        
        return success_response.dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error unregistering patient device: {e}")
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                "INTERNAL_SERVER_ERROR",
                custom_message=f"Failed to unregister patient device: {str(e)}",
                request_id=request.headers.get("X-Request-ID") or str(uuid.uuid4())
            ).dict()
        ) 

@router.get("/medical-devices/table")
async def get_patient_devices_table(
    request: Request,
    page: int = 1,
    limit: int = 25,
    search: Optional[str] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    columns: Optional[str] = None,
    export_format: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get patient medical device registries in table format"""
    try:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        # Calculate skip from page
        skip = (page - 1) * limit if page > 0 else 0
        
        # Define available columns
        available_columns = [
            "patient_info", "registry_id", "device_count", "registered_devices",
            "healthcare_provider", "group", "created_at", "updated_at"
        ]
        
        # Parse requested columns
        selected_columns = available_columns
        if columns:
            requested_cols = [col.strip() for col in columns.split(",")]
            selected_columns = [col for col in requested_cols if col in available_columns]
        
        devices_collection = mongodb_service.get_collection("amy_devices")
        
        # Build filter query
        filter_query = {}
        
        # Search functionality
        if search:
            # Need to search across patient info, so we'll do this after getting data
            pass
        
        # Build sort
        sort_direction = 1 if sort_order.lower() == "asc" else -1
        valid_sort_fields = ["created_at", "updated_at", "unique_id"]
        if sort_by not in valid_sort_fields:
            sort_by = "created_at"
        
        # Get total count
        total_count = await devices_collection.count_documents(filter_query)
        
        # Get device registries
        cursor = devices_collection.find(filter_query).sort(sort_by, sort_direction).skip(skip).limit(limit)
        registries = await cursor.to_list(length=limit)
        
        # Serialize registries
        serialized_registries = serialize_mongodb_response(registries)
        
        # Get patient and user info for each registry
        patients_collection = mongodb_service.get_collection("patients")
        users_collection = mongodb_service.get_collection("users")
        
        # Prepare table data
        table_data = []
        if isinstance(serialized_registries, list):
            for registry in serialized_registries:
                if isinstance(registry, dict):
                    row = {}
                    
                    # Get patient info
                    patient_info = None
                    if registry.get("patient_id"):
                        try:
                            patient_obj_id = ObjectId(registry["patient_id"])
                            patient = await patients_collection.find_one({"_id": patient_obj_id})
                            if patient:
                                patient_data = serialize_mongodb_response(patient)
                                patient_info = {
                                    "patient_id": registry["patient_id"],
                                    "name": f"{patient_data.get('first_name', '')} {patient_data.get('last_name', '')}".strip(),
                                    "hn": patient_data.get("hn"),
                                    "phone": patient_data.get("phone")
                                }
                        except Exception:
                            patient_info = {"patient_id": registry["patient_id"], "name": "Unknown", "hn": None, "phone": None}
                    
                    # Get healthcare provider info
                    provider_info = None
                    if registry.get("user_id"):
                        try:
                            user_obj_id = ObjectId(registry["user_id"])
                            user = await users_collection.find_one({"_id": user_obj_id})
                            if user:
                                user_data = serialize_mongodb_response(user)
                                provider_info = {
                                    "user_id": registry["user_id"],
                                    "username": user_data.get("username"),
                                    "name": f"{user_data.get('first_name', '')} {user_data.get('last_name', '')}".strip()
                                }
                        except Exception:
                            provider_info = {"user_id": registry["user_id"], "username": "Unknown", "name": "Unknown"}
                    
                    # Count registered devices
                    device_count = 0
                    registered_devices = []
                    for device_type, mac_field in DEVICE_TYPE_MAPPING.items():
                        mac_address = registry.get(mac_field)
                        if mac_address and mac_address.strip():
                            device_count += 1
                            registered_devices.append({
                                "device_type": device_type,
                                "device_name": DEVICE_TYPE_DESCRIPTIONS[device_type],
                                "mac_address": mac_address
                            })
                    
                    # Add selected columns
                    for col in selected_columns:
                        if col == "patient_info":
                            row["patient_info"] = patient_info
                        elif col == "registry_id":
                            row["registry_id"] = registry.get("_id")
                        elif col == "device_count":
                            row["device_count"] = device_count
                        elif col == "registered_devices":
                            row["registered_devices"] = registered_devices
                        elif col == "healthcare_provider":
                            row["healthcare_provider"] = provider_info
                        else:
                            row[col] = registry.get(col)
                    
                    # Apply search filter if specified
                    if search:
                        search_text = search.lower()
                        searchable_text = ""
                        if patient_info:
                            searchable_text += f"{patient_info.get('name', '')} {patient_info.get('hn', '')} {patient_info.get('phone', '')} "
                        if provider_info:
                            searchable_text += f"{provider_info.get('username', '')} {provider_info.get('name', '')} "
                        searchable_text += f"{registry.get('group', '')} "
                        
                        if search_text not in searchable_text.lower():
                            continue
                    
                    table_data.append(row)
        
        # If we applied search filter, we need to recalculate pagination
        if search:
            total_count = len(table_data)
            # Re-paginate the filtered results
            start_idx = skip
            end_idx = skip + limit
            table_data = table_data[start_idx:end_idx]
        
        # Calculate pagination
        total_pages = (total_count + limit - 1) // limit if limit > 0 else 1
        has_next = page < total_pages
        has_prev = page > 1
        
        # Handle export if requested
        export_data = None
        if export_format:
            export_data = {
                "format": export_format,
                "total_records": total_count,
                "generated_at": datetime.utcnow().isoformat(),
                "download_url": f"/api/patients/medical-devices/export?format={export_format}&filters={request.url.query}"
            }
        
        success_response = create_success_response(
            message="Patient medical device registries table retrieved successfully",
            data={
                "table": {
                    "data": table_data,
                    "columns": selected_columns,
                    "available_columns": available_columns
                },
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total": total_count,
                    "total_pages": total_pages,
                    "has_next": has_next,
                    "has_prev": has_prev,
                    "returned_count": len(table_data)
                },
                "filters": {
                    "search": search,
                    "sort_by": sort_by,
                    "sort_order": sort_order
                },
                "export": export_data
            },
            request_id=request_id
        )
        
        return success_response.dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting patient devices table: {e}")
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                "INTERNAL_SERVER_ERROR",
                custom_message=f"Failed to retrieve patient devices table: {str(e)}",
                request_id=request.headers.get("X-Request-ID") or str(uuid.uuid4())
            ).dict()
        ) 

# Change the router prefix to handle both routes
router_lookup = APIRouter(prefix="/api/medical-devices", tags=["Medical Device Lookup"])

@router_lookup.get("/patient/{mac_address}")
async def find_patient_by_device_mac(
    mac_address: str,
    request: Request,
    include_patient_info: bool = True,
    include_device_details: bool = False,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Find which patient a medical device belongs to by MAC address"""
    try:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        # Clean MAC address
        mac_address = mac_address.strip().lower()
        
        if not mac_address:
            raise HTTPException(
                status_code=400,
                detail=create_error_response(
                    "INVALID_MAC_ADDRESS",
                    field="mac_address",
                    value=mac_address,
                    custom_message="MAC address cannot be empty",
                    request_id=request_id
                ).dict()
            )
        
        devices_collection = mongodb_service.get_collection("amy_devices")
        
        # Search across all MAC address fields
        search_conditions = []
        found_device_type = None
        found_mac_field = None
        
        for device_type, mac_field in DEVICE_TYPE_MAPPING.items():
            search_conditions.append({mac_field: mac_address})
        
        # Find the device registry containing this MAC address
        device_registry = await devices_collection.find_one({
            "$or": search_conditions
        })
        
        if not device_registry:
            raise HTTPException(
                status_code=404,
                detail=create_error_response(
                    "DEVICE_NOT_FOUND",
                    field="mac_address",
                    value=mac_address,
                    custom_message=f"No patient found with medical device MAC address '{mac_address}'",
                    request_id=request_id
                ).dict()
            )
        
        # Determine which device type was found
        for device_type, mac_field in DEVICE_TYPE_MAPPING.items():
            if device_registry.get(mac_field) and device_registry.get(mac_field).lower() == mac_address:
                found_device_type = device_type
                found_mac_field = mac_field
                break
        
        # Serialize the registry
        serialized_registry = serialize_mongodb_response(device_registry)
        
        # Get patient information
        patient_info = None
        if include_patient_info and serialized_registry.get("patient_id"):
            try:
                patients_collection = mongodb_service.get_collection("patients")
                patient_obj_id = ObjectId(serialized_registry["patient_id"])
                patient = await patients_collection.find_one({"_id": patient_obj_id})
                
                if patient:
                    patient_data = serialize_mongodb_response(patient)
                    patient_info = {
                        "patient_id": serialized_registry["patient_id"],
                        "name": f"{patient_data.get('first_name', '')} {patient_data.get('last_name', '')}".strip(),
                        "first_name": patient_data.get("first_name"),
                        "last_name": patient_data.get("last_name"),
                        "hn": patient_data.get("hn"),
                        "phone": patient_data.get("phone"),
                        "email": patient_data.get("email"),
                        "birth_date": patient_data.get("birth_date"),
                        "gender": patient_data.get("gender"),
                        "is_active": patient_data.get("is_active", True)
                    }
            except Exception as e:
                logger.warning(f"Failed to get patient info for device lookup: {e}")
                patient_info = {
                    "patient_id": serialized_registry["patient_id"],
                    "name": "Unknown Patient",
                    "error": "Failed to load patient details"
                }
        
        # Get healthcare provider info
        provider_info = None
        if serialized_registry.get("user_id"):
            try:
                users_collection = mongodb_service.get_collection("users")
                user_obj_id = ObjectId(serialized_registry["user_id"])
                user = await users_collection.find_one({"_id": user_obj_id})
                
                if user:
                    user_data = serialize_mongodb_response(user)
                    provider_info = {
                        "user_id": serialized_registry["user_id"],
                        "username": user_data.get("username"),
                        "name": f"{user_data.get('first_name', '')} {user_data.get('last_name', '')}".strip(),
                        "email": user_data.get("email")
                    }
            except Exception:
                provider_info = None
        
        # Get all registered devices if requested
        all_devices = []
        if include_device_details:
            for device_type, mac_field in DEVICE_TYPE_MAPPING.items():
                device_mac = serialized_registry.get(mac_field)
                if device_mac and device_mac.strip():
                    device_info = {
                        "device_type": device_type,
                        "device_name": DEVICE_TYPE_DESCRIPTIONS[device_type],
                        "mac_address": device_mac,
                        "is_queried_device": device_mac.lower() == mac_address
                    }
                    
                    # Add any additional device-specific fields
                    for field_name, field_value in serialized_registry.items():
                        if field_name.startswith(mac_field + "_") and field_value:
                            device_info[field_name] = field_value
                    
                    all_devices.append(device_info)
        
        # Log audit trail for device lookup
        await audit_logger.log_admin_action(
            action="READ",
            resource_type="PatientDeviceLookup",
            resource_id=str(device_registry["_id"]),
            user_id=current_user.get("username") or "unknown",
            details={
                "lookup_mac_address": mac_address,
                "found_device_type": found_device_type,
                "patient_id": serialized_registry.get("patient_id"),
                "access_method": "mac_address_lookup"
            }
        )
        
        success_response = create_success_response(
            message="Patient found by medical device MAC address",
            data={
                "mac_address": mac_address,
                "device_type": found_device_type,
                "device_name": DEVICE_TYPE_DESCRIPTIONS.get(found_device_type, "Unknown Device"),
                "mac_field": found_mac_field,
                "patient_info": patient_info,
                "healthcare_provider": provider_info,
                "registry_id": serialized_registry.get("_id"),
                "group": serialized_registry.get("group"),
                "all_patient_devices": all_devices if include_device_details else None,
                "registry_created_at": serialized_registry.get("created_at"),
                "registry_updated_at": serialized_registry.get("updated_at")
            },
            request_id=request_id
        )
        
        return success_response.dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error finding patient by device MAC: {e}")
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                "INTERNAL_SERVER_ERROR",
                custom_message=f"Failed to find patient by device MAC: {str(e)}",
                request_id=request.headers.get("X-Request-ID") or str(uuid.uuid4())
            ).dict()
        ) 