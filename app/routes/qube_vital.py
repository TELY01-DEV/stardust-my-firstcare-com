from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from bson import ObjectId
from app.services.mongo import mongodb_service
from app.services.auth import require_auth
from app.services.audit_logger import audit_logger
from app.utils.json_encoder import serialize_mongodb_response
from app.utils.error_definitions import create_error_response, create_success_response
from config import settings, logger

router = APIRouter(prefix="/api/qube-vital", tags=["Qube-Vital"])

class QubeVitalDataRequest(BaseModel):
    timestamp: datetime
    device_id: str  # IMEI
    type: str  # "BLOOD_PRESSURE", "BLOOD_SUGAR", "SPO2", etc.
    data: Dict[str, Any]

class QubeVitalDataResponse(BaseModel):
    success: bool
    message: str
    observation_id: Optional[str] = None

@router.post("/data", response_model=QubeVitalDataResponse)
async def receive_qube_vital_data(
    data: QubeVitalDataRequest,
    request: Request,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Receive data from Qube-Vital device"""
    try:
        request_id = request.headers.get("X-Request-ID")
        
        # Validate device exists
        collection = mongodb_service.get_collection("mfc_hv01_boxes")
        device = await collection.find_one({"imei_of_hv01_box": data.device_id})
        
        if not device:
            raise HTTPException(
                status_code=404,
                detail=create_error_response(
                    "DEVICE_NOT_FOUND",
                    field="device_id",
                    value=data.device_id,
                    custom_message=f"Qube-Vital device with IMEI '{data.device_id}' not found",
                    request_id=request_id
                ).dict()
            )
        
        # Get hospital info
        hospital_collection = mongodb_service.get_collection("hospitals")
        hospital = await hospital_collection.find_one({"_id": device.get("hospital_id")})
        
        if not hospital:
            raise HTTPException(
                status_code=404,
                detail=create_error_response(
                    "HOSPITAL_NOT_FOUND",
                    field="hospital_id",
                    value=str(device.get("hospital_id")),
                    custom_message=f"Hospital not found for device '{data.device_id}'",
                    request_id=request_id
                ).dict()
            )
        
        # Create observation document
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
                        "code": data.type,
                        "display": data.type
                    }
                ]
            },
            "subject": {
                "reference": f"Organization/{hospital.get('_id')}"
            },
            "effectiveDateTime": data.timestamp.isoformat() + "Z",
            "issued": datetime.utcnow().isoformat() + "Z",
            "valueQuantity": {
                "value": data.data.get("value"),
                "unit": data.data.get("unit", ""),
                "system": "http://unitsofmeasure.org",
                "code": data.data.get("unit_code", "")
            },
            "device": {
                "reference": f"Device/{data.device_id}"
            },
            "meta": {
                "source": "https://opera.my-firstcare.com",
                "profile": ["http://hl7.org/fhir/StructureDefinition/Observation"]
            }
        }
        
        # Save observation
        obs_collection = mongodb_service.get_collection("fhir_observations")
        result = await obs_collection.insert_one(observation)
        observation_id = str(result.inserted_id)
        
        # Route to appropriate medical history collection
        await route_to_medical_history(data, hospital.get("_id"))
        
        # Log audit trail
        username = current_user.get("username", "unknown")
        await audit_logger.log_device_data_received(
            device_id=data.device_id,
            device_type="Qube-Vital",
            data_type=data.type,
            observation_id=observation_id,
            user_id=username
        )
        
        # Create success response
        success_response = create_success_response(
            message="Qube-Vital data received successfully",
            data={
                "observation_id": observation_id,
                "device_id": data.device_id,
                "data_type": data.type,
                "timestamp": data.timestamp.isoformat(),
                "hospital_id": str(hospital.get("_id"))
            },
            request_id=request_id
        )
        return success_response.dict()
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                "INTERNAL_SERVER_ERROR",
                custom_message=f"Failed to process Qube-Vital data: {str(e)}",
                request_id=request.headers.get("X-Request-ID")
            ).dict()
        )

async def route_to_medical_history(data: QubeVitalDataRequest, hospital_id: str):
    """Route data to appropriate medical history collection"""
    try:
        collection_name = None
        
        # Map data type to collection
        if data.type == "BLOOD_PRESSURE":
            collection_name = "blood_pressure_histories"
        elif data.type == "BLOOD_SUGAR":
            collection_name = "blood_sugar_histories"
        elif data.type == "SPO2":
            collection_name = "spo2_histories"
        elif data.type == "TEMPERATURE":
            collection_name = "temprature_data_histories"
        
        if collection_name:
            collection = mongodb_service.get_collection(collection_name)
            
            # Create history entry
            history_entry = {
                "hospital_id": ObjectId(hospital_id),
                "data": [{
                    **data.data,
                    "timestamp": data.timestamp,
                    "device_id": data.device_id,
                    "device_type": "Qube-Vital"
                }],
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            await collection.insert_one(history_entry)
            
    except Exception as e:
        pass

@router.get("/devices")
async def get_qube_vital_devices(
    limit: int = 100,
    skip: int = 0,
    active_only: bool = True,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get Qube-Vital devices"""
    try:
        collection = mongodb_service.get_collection("mfc_hv01_boxes")
        
        filter_query = {}
        if active_only:
            filter_query["is_active"] = True
            filter_query["is_deleted"] = False
        
        cursor = collection.find(filter_query).skip(skip).limit(limit)
        devices = await cursor.to_list(length=limit)
        
        # Serialize ObjectIds
        serialized_devices = serialize_mongodb_response(devices)
        response_data = {"devices": serialized_devices, "total": len(devices)}
        
        return JSONResponse(content=response_data)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/devices/{device_id}")
async def get_qube_vital_device(
    device_id: str,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get specific Qube-Vital device"""
    try:
        collection = mongodb_service.get_collection("mfc_hv01_boxes")
        device = await collection.find_one({"_id": ObjectId(device_id)})
        
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")
        
        # Serialize ObjectIds
        serialized_device = serialize_mongodb_response(device)
        return JSONResponse(content=serialized_device)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/devices/{device_id}")
async def delete_qube_vital_device(
    device_id: str,
    request: Request,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Delete (soft delete) a Qube-Vital device"""
    try:
        request_id = request.headers.get("X-Request-ID")
        
        # Convert device_id to ObjectId
        try:
            device_obj_id = ObjectId(device_id)
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=create_error_response(
                    "INVALID_DEVICE_ID",
                    field="device_id",
                    value=device_id,
                    custom_message=f"Invalid device ID format: {str(e)}",
                    request_id=request_id
                ).dict()
            )
        
        # Check if device exists
        device_collection = mongodb_service.get_collection("mfc_hv01_boxes")
        device = await device_collection.find_one({"_id": device_obj_id})
        
        if not device:
            raise HTTPException(
                status_code=404,
                detail=create_error_response(
                    "DEVICE_NOT_FOUND",
                    field="device_id",
                    value=device_id,
                    custom_message=f"Qube-Vital device with ID '{device_id}' not found",
                    request_id=request_id
                ).dict()
            )
        
        # Soft delete the device
        update_result = await device_collection.update_one(
            {"_id": device_obj_id},
            {
                "$set": {
                    "is_deleted": True,
                    "is_active": False,
                    "deleted_at": datetime.utcnow(),
                    "deleted_by": current_user.get("username")
                }
            }
        )
        
        if update_result.modified_count == 0:
            raise HTTPException(
                status_code=500,
                detail=create_error_response(
                    "DELETE_FAILED",
                    custom_message="Failed to delete device",
                    request_id=request_id
                ).dict()
            )
        
        # Log audit trail
        await audit_logger.log_admin_action(
            action="DELETE",
            resource_type="QubevitalDevice",
            resource_id=device_id,
            user_id=current_user.get("username") or "unknown",
            details={
                "device_imei": device.get("imei_of_hv01_box"),
                "hospital_id": str(device.get("hospital_id")) if device.get("hospital_id") else None
            }
        )
        
        success_response = create_success_response(
            message="Qube-Vital device deleted successfully",
            data={"device_id": device_id},
            request_id=request_id
        )
        
        return success_response.dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting Qube-Vital device: {e}")
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                "INTERNAL_SERVER_ERROR",
                custom_message=f"Failed to delete device: {str(e)}",
                request_id=request.headers.get("X-Request-ID")
            ).dict()
        )

@router.put("/devices/{device_id}/hospital")
async def assign_device_to_hospital(
    device_id: str,
    hospital_id: str,
    request: Request,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Assign a Qube-Vital device to a hospital"""
    try:
        request_id = request.headers.get("X-Request-ID")
        
        # Convert IDs to ObjectId
        try:
            device_obj_id = ObjectId(device_id)
            hospital_obj_id = ObjectId(hospital_id)
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=create_error_response(
                    "INVALID_ID_FORMAT",
                    custom_message=f"Invalid ID format: {str(e)}",
                    request_id=request_id
                ).dict()
            )
        
        # Verify device exists
        device_collection = mongodb_service.get_collection("mfc_hv01_boxes")
        device = await device_collection.find_one({"_id": device_obj_id})
        
        if not device:
            raise HTTPException(
                status_code=404,
                detail=create_error_response(
                    "DEVICE_NOT_FOUND",
                    field="device_id",
                    value=device_id,
                    custom_message=f"Qube-Vital device not found",
                    request_id=request_id
                ).dict()
            )
        
        # Verify hospital exists
        hospital_collection = mongodb_service.get_collection("hospitals")
        hospital = await hospital_collection.find_one({"_id": hospital_obj_id})
        
        if not hospital:
            raise HTTPException(
                status_code=404,
                detail=create_error_response(
                    "HOSPITAL_NOT_FOUND",
                    field="hospital_id",
                    value=hospital_id,
                    custom_message=f"Hospital not found",
                    request_id=request_id
                ).dict()
            )
        
        # Update device with hospital assignment
        update_result = await device_collection.update_one(
            {"_id": device_obj_id},
            {
                "$set": {
                    "hospital_id": hospital_obj_id,
                    "updated_at": datetime.utcnow(),
                    "updated_by": current_user.get("username")
                }
            }
        )
        
        if update_result.modified_count == 0:
            raise HTTPException(
                status_code=500,
                detail=create_error_response(
                    "ASSIGNMENT_FAILED",
                    custom_message="Failed to assign device to hospital",
                    request_id=request_id
                ).dict()
            )
        
        # Log audit trail
        await audit_logger.log_admin_action(
            action="UPDATE",
            resource_type="QubevitalDevice",
            resource_id=device_id,
            user_id=current_user.get("username") or "unknown",
            details={
                "action": "hospital_assignment",
                "hospital_id": hospital_id,
                "hospital_name": hospital.get("hospital_name"),
                "device_imei": device.get("imei_of_hv01_box")
            }
        )
        
        success_response = create_success_response(
            message="Device assigned to hospital successfully",
            data={
                "device_id": device_id,
                "hospital_id": hospital_id,
                "hospital_name": hospital.get("hospital_name")
            },
            request_id=request_id
        )
        
        return success_response.dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error assigning device to hospital: {e}")
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                "INTERNAL_SERVER_ERROR",
                custom_message=f"Failed to assign device: {str(e)}",
                request_id=request.headers.get("X-Request-ID")
            ).dict()
        )

@router.get("/analytics/hospitals")
async def get_hospital_analytics(
    request: Request,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get hospital analytics for Qube-Vital devices"""
    try:
        request_id = request.headers.get("X-Request-ID")
        
        # Get collections
        device_collection = mongodb_service.get_collection("mfc_hv01_boxes")
        hospital_collection = mongodb_service.get_collection("hospitals")
        
        # Get total counts
        total_devices = await device_collection.count_documents({"is_deleted": {"$ne": True}})
        active_devices = await device_collection.count_documents({"is_active": True, "is_deleted": {"$ne": True}})
        online_devices = await device_collection.count_documents({"status": "online", "is_deleted": {"$ne": True}})
        
        # Get devices with hospital assignments
        devices_with_hospitals = await device_collection.count_documents({
            "hospital_id": {"$exists": True, "$ne": None},
            "is_deleted": {"$ne": True}
        })
        
        # Get total hospitals
        total_hospitals = await hospital_collection.count_documents({"is_active": True})
        
        # Get hospitals with devices
        pipeline = [
            {
                "$match": {
                    "is_deleted": {"$ne": True},
                    "hospital_id": {"$exists": True, "$ne": None}
                }
            },
            {
                "$group": {
                    "_id": "$hospital_id",
                    "device_count": {"$sum": 1},
                    "active_devices": {
                        "$sum": {"$cond": [{"$eq": ["$is_active", True]}, 1, 0]}
                    },
                    "online_devices": {
                        "$sum": {"$cond": [{"$eq": ["$status", "online"]}, 1, 0]}
                    }
                }
            },
            {
                "$lookup": {
                    "from": "hospitals",
                    "localField": "_id",
                    "foreignField": "_id",
                    "as": "hospital"
                }
            },
            {
                "$unwind": "$hospital"
            },
            {
                "$project": {
                    "hospital_id": "$_id",
                    "hospital_name": "$hospital.hospital_name",
                    "hospital_code": "$hospital.hospital_code",
                    "hospital_type": "$hospital.hospital_type",
                    "device_count": 1,
                    "active_devices": 1,
                    "online_devices": 1
                }
            },
            {
                "$sort": {"device_count": -1}
            }
        ]
        
        hospital_stats = await device_collection.aggregate(pipeline).to_list(length=None)
        
        # Calculate mapping percentage
        mapping_percentage = (devices_with_hospitals / total_devices * 100) if total_devices > 0 else 0
        
        # Get top hospitals by device count
        top_hospitals = hospital_stats[:10] if len(hospital_stats) > 10 else hospital_stats
        
        # Serialize the results
        serialized_hospital_stats = serialize_mongodb_response(hospital_stats)
        serialized_top_hospitals = serialize_mongodb_response(top_hospitals)
        
        success_response = create_success_response(
            message="Hospital analytics retrieved successfully",
            data={
                "summary": {
                    "total_devices": total_devices,
                    "active_devices": active_devices,
                    "online_devices": online_devices,
                    "devices_with_hospitals": devices_with_hospitals,
                    "total_hospitals": total_hospitals,
                    "hospitals_with_devices": len(hospital_stats),
                    "mapping_percentage": round(mapping_percentage, 2)
                },
                "hospital_statistics": serialized_hospital_stats,
                "top_hospitals": serialized_top_hospitals
            },
            request_id=request_id
        )
        
        return success_response.dict()
        
    except Exception as e:
        logger.error(f"Error getting hospital analytics: {e}")
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                "INTERNAL_SERVER_ERROR",
                custom_message=f"Failed to retrieve analytics: {str(e)}",
                request_id=request.headers.get("X-Request-ID")
            ).dict()
        )

@router.get("/hospital-info")
async def get_hospital_info_by_device(
    imei: str,
    request: Request,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get hospital information by Qube-Vital device IMEI for hospital mapping"""
    try:
        request_id = request.headers.get("X-Request-ID")
        
        # Find device by IMEI
        device_collection = mongodb_service.get_collection("mfc_hv01_boxes")
        device = await device_collection.find_one({"imei_of_hv01_box": imei})
        
        if not device:
            raise HTTPException(
                status_code=404,
                detail=create_error_response(
                    "DEVICE_NOT_FOUND",
                    field="imei",
                    value=imei,
                    custom_message=f"Qube-Vital device with IMEI '{imei}' not found",
                    request_id=request_id
                ).dict()
            )
        
        # Check if device has hospital assignment
        hospital_id = device.get("hospital_id")
        if not hospital_id:
            raise HTTPException(
                status_code=404,
                detail=create_error_response(
                    "HOSPITAL_NOT_ASSIGNED",
                    field="hospital_id",
                    value=None,
                    custom_message=f"No hospital assigned to Qube-Vital device '{imei}'",
                    request_id=request_id
                ).dict()
            )
        
        # Convert hospital_id to ObjectId properly
        try:
            if isinstance(hospital_id, str):
                hospital_obj_id = ObjectId(hospital_id)
            elif isinstance(hospital_id, dict) and "$oid" in hospital_id:
                hospital_obj_id = ObjectId(hospital_id["$oid"])
            elif isinstance(hospital_id, ObjectId):
                hospital_obj_id = hospital_id
            else:
                raise ValueError(f"Invalid hospital_id format: {type(hospital_id)}")
        except Exception as e:
            logger.error(f"Error converting hospital_id to ObjectId: {e}")
            raise HTTPException(
                status_code=500,
                detail=create_error_response(
                    "INTERNAL_SERVER_ERROR",
                    custom_message=f"Invalid hospital ID format: {str(e)}",
                    request_id=request_id
                ).dict()
            )
        
        # Get hospital information
        hospital_collection = mongodb_service.get_collection("hospitals")
        hospital = await hospital_collection.find_one({"_id": hospital_obj_id})
        
        if not hospital:
            # Device has hospital_id but hospital doesn't exist - data integrity issue
            logger.warning(f"Data integrity issue: Qube-Vital device {imei} references non-existent hospital {hospital_id}")
            
            # Return device info with warning
            device_info = serialize_mongodb_response(device)
            success_response = create_success_response(
                message="Qube-Vital device found but hospital data unavailable",
                data={
                    "device": device_info,
                    "hospital": None,
                    "warning": "Hospital data not found - possible data integrity issue"
                },
                request_id=request_id
            )
            return success_response.dict()
        
        # Check if hospital is active
        if not hospital.get("is_active", True):
            raise HTTPException(
                status_code=404,
                detail=create_error_response(
                    "HOSPITAL_INACTIVE",
                    field="hospital_id",
                    value=str(hospital_id),
                    custom_message=f"Hospital assigned to Qube-Vital device '{imei}' is inactive",
                    request_id=request_id
                ).dict()
            )
        
        # Prepare response data
        device_info = serialize_mongodb_response(device)
        hospital_info = serialize_mongodb_response(hospital)
        
        # Create hospital basic info (excluding sensitive data)
        hospital_basic = {
            "hospital_id": hospital_info.get("_id"),
            "hospital_name": hospital_info.get("hospital_name"),
            "hospital_code": hospital_info.get("hospital_code"),
            "hospital_type": hospital_info.get("hospital_type"),
            "province_code": hospital_info.get("province_code"),
            "district_code": hospital_info.get("district_code"),
            "sub_district_code": hospital_info.get("sub_district_code"),
            "address": hospital_info.get("address"),
            "phone": hospital_info.get("phone"),
            "email": hospital_info.get("email"),
            "is_active": hospital_info.get("is_active", True),
            "created_at": hospital_info.get("created_at"),
            "updated_at": hospital_info.get("updated_at")
        }
        
        # Log audit trail
        await audit_logger.log_admin_action(
            action="READ",
            resource_type="Hospital",
            resource_id=str(hospital_id),
            user_id=current_user.get("username"),
            details={
                "access_method": "qube_vital_device_mapping",
                "device_imei": imei,
                "device_type": "Qube-Vital"
            }
        )
        
        success_response = create_success_response(
            message="Hospital information retrieved successfully",
            data={
                "device": {
                    "device_id": device_info.get("_id"),
                    "imei": device_info.get("imei_of_hv01_box"),
                    "device_name": device_info.get("device_name"),
                    "model": device_info.get("model"),
                    "status": device_info.get("status"),
                    "is_active": device_info.get("is_active"),
                    "hospital_id": device_info.get("hospital_id")
                },
                "hospital": hospital_basic,
                "mapping_info": {
                    "mapped_at": device_info.get("updated_at"),
                    "device_type": "Qube-Vital",
                    "mapping_status": "active"
                }
            },
            request_id=request_id
        )
        
        return success_response.dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting Qube-Vital hospital info: {e}")
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                "INTERNAL_SERVER_ERROR",
                custom_message=f"Failed to retrieve hospital information: {str(e)}",
                request_id=request.headers.get("X-Request-ID")
            ).dict()
        )

@router.get("/hospitals/{hospital_id}/devices")
async def get_hospital_devices(
    hospital_id: str,
    request: Request,
    limit: int = 100,
    skip: int = 0,
    active_only: bool = True,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get all Qube-Vital devices assigned to a specific hospital"""
    try:
        request_id = request.headers.get("X-Request-ID")
        
        # Convert hospital_id to ObjectId
        try:
            hospital_obj_id = ObjectId(hospital_id)
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=create_error_response(
                    "INVALID_HOSPITAL_ID",
                    field="hospital_id",
                    value=hospital_id,
                    custom_message=f"Invalid hospital ID format: {str(e)}",
                    request_id=request_id
                ).dict()
            )
        
        # Verify hospital exists
        hospital_collection = mongodb_service.get_collection("hospitals")
        hospital = await hospital_collection.find_one({"_id": hospital_obj_id})
        
        if not hospital:
            raise HTTPException(
                status_code=404,
                detail=create_error_response(
                    "HOSPITAL_NOT_FOUND",
                    field="hospital_id",
                    value=hospital_id,
                    custom_message=f"Hospital with ID '{hospital_id}' not found",
                    request_id=request_id
                ).dict()
            )
        
        # Get devices for this hospital
        device_collection = mongodb_service.get_collection("mfc_hv01_boxes")
        filter_query = {"hospital_id": hospital_obj_id}
        
        if active_only:
            filter_query["is_active"] = True
            filter_query["is_deleted"] = {"$ne": True}
        
        cursor = device_collection.find(filter_query).skip(skip).limit(limit)
        devices = await cursor.to_list(length=limit)
        
        # Get total count
        total_count = await device_collection.count_documents(filter_query)
        
        # Serialize devices
        serialized_devices = serialize_mongodb_response(devices)
        hospital_info = serialize_mongodb_response(hospital)
        
        # Categorize devices by status
        device_stats = {
            "active": 0,
            "inactive": 0,
            "online": 0,
            "offline": 0,
            "total": len(serialized_devices)
        }
        
        if isinstance(serialized_devices, list):
            for device in serialized_devices:
                if isinstance(device, dict):
                    if device.get("is_active"):
                        device_stats["active"] += 1
                    else:
                        device_stats["inactive"] += 1
                        
                    if device.get("status") == "online":
                        device_stats["online"] += 1
                    else:
                        device_stats["offline"] += 1
        
        success_response = create_success_response(
            message="Hospital devices retrieved successfully",
            data={
                "hospital": {
                    "hospital_id": hospital_info.get("_id"),
                    "hospital_name": hospital_info.get("hospital_name"),
                    "hospital_code": hospital_info.get("hospital_code"),
                    "hospital_type": hospital_info.get("hospital_type")
                },
                "devices": {
                    "total_count": total_count,
                    "returned_count": len(serialized_devices),
                    "statistics": device_stats,
                    "devices": serialized_devices
                },
                "pagination": {
                    "limit": limit,
                    "skip": skip,
                    "has_more": total_count > (skip + len(serialized_devices))
                }
            },
            request_id=request_id
        )
        
        return success_response.dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting hospital devices: {e}")
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                "INTERNAL_SERVER_ERROR",
                custom_message=f"Failed to retrieve hospital devices: {str(e)}",
                request_id=request.headers.get("X-Request-ID")
            ).dict()
        )

@router.get("/hospitals")
async def get_hospitals_with_devices(
    request: Request,
    limit: int = 50,
    skip: int = 0,
    include_device_count: bool = True,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get hospitals with their Qube-Vital device counts"""
    try:
        request_id = request.headers.get("X-Request-ID")
        
        # Get hospitals
        hospital_collection = mongodb_service.get_collection("hospitals")
        cursor = hospital_collection.find({"is_active": True}).skip(skip).limit(limit)
        hospitals = await cursor.to_list(length=limit)
        
        # Get total count
        total_count = await hospital_collection.count_documents({"is_active": True})
        
        serialized_hospitals = serialize_mongodb_response(hospitals)
        
        # Add device counts if requested
        if include_device_count:
            device_collection = mongodb_service.get_collection("mfc_hv01_boxes")
            
            for hospital in serialized_hospitals:
                hospital_id = hospital.get("_id")
                if hospital_id:
                    try:
                        hospital_obj_id = ObjectId(hospital_id)
                        device_count = await device_collection.count_documents({
                            "hospital_id": hospital_obj_id,
                            "is_active": True,
                            "is_deleted": {"$ne": True}
                        })
                        hospital["device_count"] = device_count
                    except Exception:
                        hospital["device_count"] = 0
                else:
                    hospital["device_count"] = 0
        
        success_response = create_success_response(
            message="Hospitals with device information retrieved successfully",
            data={
                "hospitals": {
                    "total_count": total_count,
                    "returned_count": len(serialized_hospitals),
                    "hospitals": serialized_hospitals
                },
                "pagination": {
                    "limit": limit,
                    "skip": skip,
                    "has_more": total_count > (skip + len(serialized_hospitals))
                }
            },
            request_id=request_id
        )
        
        return success_response.dict()
        
    except Exception as e:
        logger.error(f"Error getting hospitals with devices: {e}")
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                "INTERNAL_SERVER_ERROR",
                custom_message=f"Failed to retrieve hospitals: {str(e)}",
                request_id=request.headers.get("X-Request-ID")
            ).dict()
        ) 