import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Request, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from bson import ObjectId
from app.services.mongo import mongodb_service
from app.services.auth import require_auth
from app.services.audit_logger import audit_logger
from app.utils.json_encoder import serialize_mongodb_response
from app.utils.error_definitions import create_error_response, create_success_response
from config import settings, logger

router = APIRouter(prefix="/api/kati", tags=["Kati Watch"])

class KatiDataRequest(BaseModel):
    timestamp: datetime
    device_id: str  # IMEI
    type: str  # "SPO2", "STEPS", "SLEEP", "TEMPERATURE", etc.
    data: Dict[str, Any]

class KatiDataResponse(BaseModel):
    success: bool
    message: str
    observation_id: Optional[str] = None

class PatientBasicInfo(BaseModel):
    """Patient basic information for Kati watch mapping"""
    patient_id: str
    first_name: str
    last_name: str
    nickname: Optional[str] = None
    gender: str
    birth_date: Optional[datetime] = None
    id_card: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    province_code: Optional[str] = None
    district_code: Optional[str] = None
    sub_district_code: Optional[str] = None
    postal_code: Optional[str] = None
    blood_type: Optional[str] = None
    height: Optional[float] = None
    weight: Optional[float] = None
    bmi: Optional[float] = None
    watch_mac_address: Optional[str] = None
    is_active: bool = True

@router.post("/data", response_model=KatiDataResponse)
async def receive_kati_data(
    data: KatiDataRequest,
    request: Request,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Receive data from Kati Watch"""
    try:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        # Validate device exists
        collection = mongodb_service.get_collection("watches")
        device = await collection.find_one({"imei": data.device_id})
        
        if not device:
            raise HTTPException(
                status_code=404,
                detail=create_error_response(
                    "DEVICE_NOT_FOUND",
                    field="device_id",
                    value=data.device_id,
                    custom_message=f"Kati watch with IMEI '{data.device_id}' not found",
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
                "reference": f"Patient/{device.get('patient_id')}"
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
        obs_collection = mongodb_service.get_fhir_collection("fhir_observations")
        result = await obs_collection.insert_one(observation)
        observation_id = str(result.inserted_id)
        
        # Route to appropriate medical history collection
        await route_to_medical_history(data, device.get("patient_id"))
        
        # Log audit trail
        username = current_user.get("username", "unknown")
        await audit_logger.log_device_data_received(
            device_id=data.device_id,
            device_type="Kati",
            data_type=data.type,
            observation_id=observation_id,
            user_id=username
        )
        
        # Create success response
        success_response = create_success_response(
            message="Kati watch data received successfully",
            data={
                "observation_id": observation_id,
                "device_id": data.device_id,
                "data_type": data.type,
                "timestamp": data.timestamp.isoformat()
            },
            request_id=request_id
        )
        return success_response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                "INTERNAL_SERVER_ERROR",
                custom_message=f"Failed to process Kati watch data: {str(e)}",
                request_id=request.headers.get("X-Request-ID") or str(uuid.uuid4())
            ).dict()
        )

async def route_to_medical_history(data: KatiDataRequest, patient_id: str):
    """Route data to appropriate medical history collection"""
    try:
        collection_name = None
        
        # Map data type to collection
        if data.type == "SPO2":
            collection_name = "spo2_histories"
        elif data.type == "STEPS":
            collection_name = "step_histories"
        elif data.type == "SLEEP":
            collection_name = "sleep_data_histories"
        elif data.type == "TEMPERATURE":
            collection_name = "temprature_data_histories"
        
        if collection_name:
            collection = mongodb_service.get_collection(collection_name)
            
            # Create history entry
            history_entry = {
                "patient_id": ObjectId(patient_id),
                "data": [{
                    **data.data,
                    "timestamp": data.timestamp,
                    "device_id": data.device_id,
                    "device_type": "Kati"
                }],
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            await collection.insert_one(history_entry)
            
    except Exception as e:
        pass

@router.get("/test")
async def test_endpoint():
    """Simple test endpoint"""
    return JSONResponse(content={"status": "working", "message": "Kati API is functional"})

@router.get("/test-auth")
async def test_auth_endpoint(current_user: Dict[str, Any] = Depends(require_auth())):
    """Test endpoint that requires authentication"""
    return JSONResponse(content={
        "status": "authenticated", 
        "message": "Authentication working",
        "user": {
            "username": current_user.get("username", "unknown"),
            "role": current_user.get("role", "unknown")
        }
    })

@router.get("/devices")
async def get_kati_devices(
    limit: int = 100,
    skip: int = 0,
    active_only: bool = True,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get Kati Watch devices"""
    try:
        collection = mongodb_service.get_collection("watches")
        
        # Use same filter as admin endpoint
        filter_query = {}
        if active_only:
            filter_query["status"] = {"$ne": "deleted"}
        
        # Get total count
        total = await collection.count_documents(filter_query)
        
        # Get devices
        cursor = collection.find(filter_query).skip(skip).limit(limit)
        devices = await cursor.to_list(length=limit)
        
        logger.info(f"Found {len(devices)} Kati devices")
        
        # Serialize ObjectIds - use same method as admin endpoint
        devices = serialize_mongodb_response(devices)
        
        response_data = {
            "devices": devices,
            "total": total,
            "limit": limit,
            "skip": skip
        }
        
        logger.info("Serialization completed successfully")
        
        return JSONResponse(content=response_data)
        
    except Exception as e:
        logger.error(f"Error in get_kati_devices: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/devices/{device_id}")
async def get_kati_device(
    device_id: str,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get specific Kati Watch device"""
    try:
        collection = mongodb_service.get_collection("watches")
        device = await collection.find_one({"_id": ObjectId(device_id)})
        
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")
        
        # Serialize ObjectIds
        serialized_device = serialize_mongodb_response(device)
        return JSONResponse(content=serialized_device)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/devices/{device_id}")
async def delete_kati_device(
    device_id: str,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Soft delete Kati Watch device"""
    try:
        collection = mongodb_service.get_collection("watches")
        
        result = await collection.update_one(
            {"_id": ObjectId(device_id)},
            {
                "$set": {
                    "status": "deleted",
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Device not found")
        
        # Log audit trail
        username = current_user.get("username", "unknown")
        await audit_logger.log_admin_action(
            action="DELETE",
            resource_type="Device",
            resource_id=device_id,
            user_id=username,
            details={"device_type": "Kati"}
        )
        
        return {"success": True, "message": "Device deleted successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/patient-info", response_model=Dict[str, Any])
async def get_patient_info_by_imei(
    request: Request,
    imei: str = Query(..., description="Kati watch IMEI", min_length=1, max_length=50),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get patient basic information by Kati watch IMEI for device mapping"""
    try:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        # Find watch by IMEI
        watches_collection = mongodb_service.get_collection("watches")
        logger.info(f"Searching for watch with IMEI: {imei}")
        watch = await watches_collection.find_one({"imei": imei})
        logger.info(f"Watch found: {watch is not None}")
        
        if not watch:
            logger.warning(f"Watch not found for IMEI: {imei}")
            raise HTTPException(
                status_code=404,
                detail=create_error_response(
                    "KATI_WATCH_NOT_FOUND",
                    field="imei",
                    value=imei,
                    custom_message=f"Kati watch with IMEI '{imei}' not found",
                    request_id=request_id
                ).dict()
            )
        
        # Check if watch has patient assignment
        patient_id = watch.get("patient_id")
        if not patient_id:
            raise HTTPException(
                status_code=404,
                detail=create_error_response(
                    "PATIENT_NOT_ASSIGNED",
                    field="patient_id",
                    value=None,
                    custom_message=f"No patient assigned to Kati watch '{imei}'",
                    request_id=request_id
                ).dict()
            )
        
        # Convert patient_id to ObjectId properly
        try:
            if isinstance(patient_id, str):
                patient_obj_id = ObjectId(patient_id)
            elif isinstance(patient_id, dict) and "$oid" in patient_id:
                patient_obj_id = ObjectId(patient_id["$oid"])
            elif isinstance(patient_id, ObjectId):
                patient_obj_id = patient_id
            else:
                raise ValueError(f"Invalid patient_id format: {type(patient_id)}")
        except Exception as e:
            logger.error(f"Error converting patient_id to ObjectId: {e}")
            raise HTTPException(
                status_code=500,
                detail=create_error_response(
                    "INTERNAL_SERVER_ERROR",
                    custom_message=f"Invalid patient ID format: {str(e)}",
                    request_id=request_id
                ).dict()
            )
        
        # Get patient information
        patient_collection = mongodb_service.get_collection("patients")
        patient = await patient_collection.find_one({"_id": patient_obj_id})
        
        if not patient:
            # Patient doesn't exist - return watch info with data integrity warning
            watch_info = {
                "watch_id": str(watch["_id"]),
                "imei": watch.get("imei"),
                "model": watch.get("model"),
                "factory": watch.get("factory"),
                "mobile_no": watch.get("mobile_no"),
                "status": watch.get("status", "offline"),
                "battery": watch.get("battery", 0),
                "signal_gsm": watch.get("signalGSM", 0),
                "working_mode": watch.get("working_mode", 0),
                "location_update_minutes": watch.get("location_update_minutes", 0),
                "is_auto_vital_sign": watch.get("is_auto_vital_sign", False),
                "auto_vital_sign_minutes": watch.get("auto_vital_sign_minutes", 0),
                "is_auto_temperature": watch.get("is_auto_temprature", False),
                "auto_temperature_minutes": watch.get("auto_temprature_minutes", 0),
                "is_auto_sleep_monitoring": watch.get("is_auto_sleep_monitoring", False),
                "sleep_setting": watch.get("sleep_setting")
            }
            
            # Log audit trail for data integrity issue
            username = current_user.get("username", "unknown")
            await audit_logger.log_admin_action(
                action="query_patient_info_by_imei_data_integrity_issue",
                resource_type="kati_patient_mapping",
                resource_id=imei,
                user_id=username,
                details={
                    "patient_id": str(patient_obj_id),
                    "imei": imei,
                    "issue": "patient_not_found",
                    "query_type": "patient_basic_info"
                }
            )
            
            # Create warning response
            success_response = create_success_response(
                message="Watch found but patient data is missing (data integrity issue)",
                data={
                    "patient_info": None,
                    "watch_info": watch_info,
                    "mapping_status": "incomplete",
                    "data_integrity_issue": {
                        "issue": "patient_not_found",
                        "description": f"Watch references patient ID '{patient_obj_id}' but patient does not exist in database",
                        "recommendation": "Import patient data or re-assign watch to existing patient"
                    }
                },
                request_id=request_id
            )
            return success_response
        
        # Check if patient is active
        if patient.get("is_deleted") or not patient.get("is_active", True):
            raise HTTPException(
                status_code=404,
                detail=create_error_response(
                    "PATIENT_INACTIVE",
                    field="patient_id",
                    value=str(patient_obj_id),
                    custom_message=f"Patient with ID '{patient_obj_id}' is inactive or deleted",
                    request_id=request_id
                ).dict()
            )
        
        # Prepare patient basic info response
        patient_info = {
            "patient_id": str(patient_obj_id),
            "first_name": patient.get("first_name", ""),
            "last_name": patient.get("last_name", ""),
            "nickname": patient.get("nickname"),
            "gender": patient.get("gender", ""),
            "birth_date": patient.get("birth_date"),
            "id_card": patient.get("id_card"),
            "phone": patient.get("phone"),
            "email": patient.get("email"),
            "address": patient.get("address"),
            "province_code": patient.get("province_code"),
            "district_code": patient.get("district_code"),
            "sub_district_code": patient.get("sub_district_code"),
            "postal_code": patient.get("postal_code"),
            "blood_type": patient.get("blood_type"),
            "height": patient.get("height"),
            "weight": patient.get("weight"),
            "bmi": patient.get("bmi"),
            "watch_mac_address": patient.get("watch_mac_address"),
            "is_active": patient.get("is_active", True)
        }
        
        # Include watch information
        watch_info = {
            "watch_id": str(watch["_id"]),
            "imei": watch.get("imei"),
            "model": watch.get("model"),
            "factory": watch.get("factory"),
            "mobile_no": watch.get("mobile_no"),
            "status": watch.get("status", "offline"),
            "battery": watch.get("battery", 0),
            "signal_gsm": watch.get("signalGSM", 0),
            "working_mode": watch.get("working_mode", 0),
            "location_update_minutes": watch.get("location_update_minutes", 0),
            "is_auto_vital_sign": watch.get("is_auto_vital_sign", False),
            "auto_vital_sign_minutes": watch.get("auto_vital_sign_minutes", 0),
            "is_auto_temperature": watch.get("is_auto_temprature", False),
            "auto_temperature_minutes": watch.get("auto_temprature_minutes", 0),
            "is_auto_sleep_monitoring": watch.get("is_auto_sleep_monitoring", False),
            "sleep_setting": watch.get("sleep_setting")
        }
        
        # Log audit trail
        username = current_user.get("username", "unknown")
        await audit_logger.log_admin_action(
            action="query_patient_info_by_imei",
            resource_type="kati_patient_mapping",
            resource_id=imei,
            user_id=username,
            details={
                "patient_id": str(patient_obj_id),
                "imei": imei,
                "query_type": "patient_basic_info"
            }
        )
        
        # Create success response
        success_response = create_success_response(
            message="Patient information retrieved successfully",
            data={
                "patient_info": patient_info,
                "watch_info": watch_info,
                "mapping_status": "active"
            },
            request_id=request_id
        )
        return success_response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                "INTERNAL_SERVER_ERROR",
                custom_message=f"Failed to retrieve patient information: {str(e)}",
                request_id=request.headers.get("X-Request-ID") or str(uuid.uuid4())
            ).dict()
        )

# =============== NEW KATI WATCH PATIENT FILTERING ENDPOINTS ===============

class KatiPatientInfo(BaseModel):
    """Patient information for Kati watch system"""
    patient_id: str
    first_name: str
    last_name: str
    hospital_name: Optional[str] = None
    watch_imei: Optional[str] = None
    watch_status: Optional[str] = None
    is_active: bool = True

@router.get("/patients/with-watch", 
            response_model=Dict[str, Any],
            summary="Get Patients with Kati Watch Assignment",
            description="""
            ## Patients with Kati Watch Assignment
            
            Get list of patients who have been assigned a Kati Watch device.
            
            ### Response Fields:
            - `patient_id`: Unique patient identifier
            - `first_name`: Patient first name
            - `last_name`: Patient last name (surname)
            - `hospital_name`: Hospital name where patient is registered
            - `watch_imei`: Assigned Kati watch IMEI
            - `watch_status`: Current watch status (online/offline)
            - `is_active`: Patient active status
            
            ### Filtering Options:
            - `search`: Search by patient name
            - `hospital_id`: Filter by specific hospital
            - `watch_status`: Filter by watch status (online/offline)
            - Pagination: `limit` and `skip`
            """)
async def get_patients_with_watch(
    request: Request,
    limit: int = Query(100, ge=1, le=1000, description="Number of patients to return"),
    skip: int = Query(0, ge=0, description="Number of patients to skip"),
    search: Optional[str] = Query(None, description="Search by patient name"),
    hospital_id: Optional[str] = Query(None, description="Filter by hospital ID"),
    watch_status: Optional[str] = Query(None, description="Filter by watch status (online/offline)"),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get patients who have assigned Kati watches with hospital names"""
    try:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        # Check MongoDB connection
        if mongodb_service.client is None or mongodb_service.main_db is None:
            return create_success_response(
                message="Database connection not available in development environment",
                data={
                    "patients": [],
                    "total": 0,
                    "limit": limit,
                    "skip": skip,
                    "filters": {
                        "search": search,
                        "hospital_id": hospital_id,
                        "watch_status": watch_status
                    },
                    "note": "Production database connection required for patient data"
                },
                request_id=request_id
            ).dict()
        
        # Simplified approach: Start with basic patient query first
        patients_collection = mongodb_service.get_collection("patients")
        
        # Build basic match conditions
        match_conditions = {"is_deleted": {"$ne": True}}
        
        # Add search filter
        if search:
            match_conditions["$or"] = [
                {"first_name": {"$regex": search, "$options": "i"}},
                {"last_name": {"$regex": search, "$options": "i"}}
            ]
        
        # Add hospital filter
        if hospital_id:
            try:
                hospital_obj_id = ObjectId(hospital_id)
                match_conditions["new_hospital_ids"] = hospital_obj_id
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid hospital ID format")
        
        # Simple aggregation pipeline without complex nesting
        pipeline = [
            {"$match": match_conditions},
            {
                "$lookup": {
                    "from": "hospitals",
                    "localField": "new_hospital_ids",
                    "foreignField": "_id",
                    "as": "hospitals"
                }
            },
            {
                "$addFields": {
                    "hospital_name": {
                        "$cond": {
                            "if": {"$gt": [{"$size": "$hospitals"}, 0]},
                            "then": {"$arrayElemAt": ["$hospitals.name", 0]},
                            "else": "No Hospital Assigned"
                        }
                    }
                }
            },
            {
                "$project": {
                    "patient_id": {"$toString": "$_id"},
                    "first_name": 1,
                    "last_name": 1,
                    "hospital_name": 1,
                    "watch_mac_address": 1,
                    "is_active": 1
                }
            },
            {"$skip": skip},
            {"$limit": limit}
        ]
        
        # Execute aggregation
        cursor = patients_collection.aggregate(pipeline)
        all_patients = await cursor.to_list(length=None)
        
        # Filter for patients with watches post-aggregation to avoid MongoDB nesting issues
        patients_with_watches = []
        
        # Get watch assignments from watches collection separately
        watches_collection = mongodb_service.get_collection("watches")
        watches_with_patients = await watches_collection.find(
            {"patient_id": {"$exists": True, "$ne": None}}, 
            {"patient_id": 1, "imei": 1, "status": 1}
        ).to_list(length=None)
        
        # Create watch mapping
        watch_mapping = {}
        for watch in watches_with_patients:
            if watch.get("patient_id"):
                patient_id_str = str(watch["patient_id"])
                watch_mapping[patient_id_str] = {
                    "imei": watch.get("imei", ""),
                    "status": watch.get("status", "offline")
                }
        
        # Filter patients and add watch info
        for patient in all_patients:
            patient_id = patient["patient_id"]
            has_watch = False
            
            # Check if patient has watch via MAC address
            if patient.get("watch_mac_address"):
                has_watch = True
            
            # Check if patient has watch via watches collection
            if patient_id in watch_mapping:
                has_watch = True
            
            # Include only patients with watches
            if has_watch:
                watch_info = watch_mapping.get(patient_id, {})
                patient["watch_imei"] = watch_info.get("imei", patient.get("watch_mac_address", ""))
                patient["watch_status"] = watch_info.get("status", "unknown")
                
                # Apply watch status filter if specified
                if not watch_status or patient["watch_status"] == watch_status:
                    patients_with_watches.append(patient)
        
        # Serialize all patient data to ensure ObjectIds are converted
        patients_with_watches = serialize_mongodb_response(patients_with_watches)
        
        # Get total count - simplified count query
        count_pipeline = [{"$match": match_conditions}, {"$count": "total"}]
        count_result = await patients_collection.aggregate(count_pipeline).to_list(length=1)
        total_in_db = count_result[0]["total"] if count_result else 0
        
        # For now, return the filtered count as total (this is approximate)
        total = len(patients_with_watches)
        
        # Log audit trail
        username = current_user.get("username", "unknown")
        await audit_logger.log_admin_action(
            action="query_patients_with_watch",
            resource_type="kati_patient_list",
            resource_id="with_watch",
            user_id=username,
            details={
                "filters": {
                    "search": search,
                    "hospital_id": hospital_id,
                    "watch_status": watch_status
                },
                "result_count": len(patients_with_watches),
                "total_count": total
            }
        )
        
        # Create success response
        success_response = create_success_response(
            message="Patients with Kati watch assignment retrieved successfully",
            data={
                "patients": patients_with_watches,
                "total": total,
                "limit": limit,
                "skip": skip,
                "filters": {
                    "search": search,
                    "hospital_id": hospital_id,
                    "watch_status": watch_status
                }
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
                custom_message=f"Failed to retrieve patients with watch assignment: {str(e)}",
                request_id=request.headers.get("X-Request-ID") or str(uuid.uuid4())
            ).dict()
        )

@router.get("/patients/without-watch", 
            response_model=Dict[str, Any],
            summary="Get Patients without Kati Watch Assignment",
            description="""
            ## Patients without Kati Watch Assignment
            
            Get list of patients who have NOT been assigned a Kati Watch device.
            
            ### Response Fields:
            - `patient_id`: Unique patient identifier
            - `first_name`: Patient first name
            - `last_name`: Patient last name (surname)
            - `hospital_name`: Hospital name where patient is registered
            - `watch_imei`: null (no watch assigned)
            - `watch_status`: null (no watch assigned)
            - `is_active`: Patient active status
            
            ### Filtering Options:
            - `search`: Search by patient name
            - `hospital_id`: Filter by specific hospital
            - Pagination: `limit` and `skip`
            """)
async def get_patients_without_watch(
    request: Request,
    limit: int = Query(100, ge=1, le=1000, description="Number of patients to return"),
    skip: int = Query(0, ge=0, description="Number of patients to skip"),
    search: Optional[str] = Query(None, description="Search by patient name"),
    hospital_id: Optional[str] = Query(None, description="Filter by hospital ID"),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get patients who do NOT have assigned Kati watches with hospital names"""
    try:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        # Check MongoDB connection
        if mongodb_service.client is None or mongodb_service.main_db is None:
            return create_success_response(
                message="Database connection not available in development environment",
                data={
                    "patients": [],
                    "total": 0,
                    "limit": limit,
                    "skip": skip,
                    "filters": {
                        "search": search,
                        "hospital_id": hospital_id
                    },
                    "note": "Production database connection required for patient data"
                },
                request_id=request_id
            ).dict()
        
        # Get patient IDs that have watch assignment from watches collection
        watches_collection = mongodb_service.get_collection("watches")
        assigned_watches = await watches_collection.find(
            {"patient_id": {"$exists": True, "$ne": None}}, 
            {"patient_id": 1}
        ).to_list(length=None)
        
        # Convert patient IDs to ObjectId format consistently
        assigned_patient_ids = []
        for watch in assigned_watches:
            if watch.get("patient_id"):
                try:
                    # Ensure all patient IDs are ObjectId format
                    if isinstance(watch["patient_id"], str):
                        assigned_patient_ids.append(ObjectId(watch["patient_id"]))
                    elif isinstance(watch["patient_id"], ObjectId):
                        assigned_patient_ids.append(watch["patient_id"])
                except Exception:
                    continue  # Skip invalid ObjectIds
        
        # Build match conditions for patients WITHOUT watch assignment
        match_conditions = {"is_deleted": {"$ne": True}}
        
        # Build all conditions in a clean structure
        all_conditions = []
        
        # Condition 1: No MAC address AND not in watches collection
        no_watch_condition = {
            "$and": [
                {
                    "$or": [
                        {"watch_mac_address": {"$exists": False}},
                        {"watch_mac_address": None},
                        {"watch_mac_address": ""}
                    ]
                }
            ]
        }
        
        # Only add the $nin condition if we have valid patient IDs
        if assigned_patient_ids:
            no_watch_condition["$and"].append({"_id": {"$nin": assigned_patient_ids}})
        
        all_conditions.append(no_watch_condition)
        
        # Add search filter if specified
        if search:
            all_conditions.append({
                "$or": [
                    {"first_name": {"$regex": search, "$options": "i"}},
                    {"last_name": {"$regex": search, "$options": "i"}}
                ]
            })
        
        # Add hospital filter if specified
        if hospital_id:
            try:
                hospital_obj_id = ObjectId(hospital_id)
                all_conditions.append({"new_hospital_ids": hospital_obj_id})
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid hospital ID format")
        
        # Combine all conditions
        if all_conditions:
            match_conditions["$and"] = all_conditions
        
        pipeline = [{"$match": match_conditions}]
        
        # Lookup hospital information
        pipeline.extend([
            {
                "$lookup": {
                    "from": "hospitals",
                    "localField": "new_hospital_ids",
                    "foreignField": "_id",
                    "as": "hospitals"
                }
            },
            {
                "$addFields": {
                    "hospital_name": {
                        "$cond": {
                            "if": {"$gt": [{"$size": "$hospitals"}, 0]},
                            "then": {"$arrayElemAt": ["$hospitals.name", 0]},
                            "else": "No Hospital Assigned"
                        }
                    }
                }
            },
            {
                "$project": {
                    "patient_id": {"$toString": "$_id"},
                    "first_name": 1,
                    "last_name": 1,
                    "hospital_name": 1,
                    "watch_imei": {"$literal": None},
                    "watch_status": {"$literal": None},
                    "is_active": 1
                }
            },
            {"$skip": skip},
            {"$limit": limit}
        ])
        
        # Execute aggregation
        patients_collection = mongodb_service.get_collection("patients")
        cursor = patients_collection.aggregate(pipeline)
        patients = await cursor.to_list(length=None)
        
        # Serialize patient data to ensure ObjectIds are converted
        patients = serialize_mongodb_response(patients)
        
        # Get total count with same filters
        count_match_conditions = {"is_deleted": {"$ne": True}}
        count_all_conditions = []
        
        # Same no-watch condition for count
        count_no_watch_condition = {
            "$and": [
                {
                    "$or": [
                        {"watch_mac_address": {"$exists": False}},
                        {"watch_mac_address": None},
                        {"watch_mac_address": ""}
                    ]
                }
            ]
        }
        
        # Only add the $nin condition if we have valid patient IDs
        if assigned_patient_ids:
            count_no_watch_condition["$and"].append({"_id": {"$nin": assigned_patient_ids}})
        
        count_all_conditions.append(count_no_watch_condition)
        
        if search:
            count_all_conditions.append({
                "$or": [
                    {"first_name": {"$regex": search, "$options": "i"}},
                    {"last_name": {"$regex": search, "$options": "i"}}
                ]
            })
        
        if hospital_id:
            count_all_conditions.append({"new_hospital_ids": ObjectId(hospital_id)})
        
        if count_all_conditions:
            count_match_conditions["$and"] = count_all_conditions
        
        count_pipeline = [{"$match": count_match_conditions}]
        count_pipeline.append({"$count": "total"})
        
        # Execute aggregation
        count_result = await patients_collection.aggregate(count_pipeline).to_list(length=1)
        total = count_result[0]["total"] if count_result else 0
        
        # Log audit trail
        username = current_user.get("username", "unknown")
        await audit_logger.log_admin_action(
            action="query_patients_without_watch",
            resource_type="kati_patient_list",
            resource_id="without_watch",
            user_id=username,
            details={
                "filters": {
                    "search": search,
                    "hospital_id": hospital_id
                },
                "result_count": len(patients),
                "total_count": total
            }
        )
        
        # Create success response
        success_response = create_success_response(
            message="Patients without Kati watch assignment retrieved successfully",
            data={
                "patients": patients,
                "total": total,
                "limit": limit,
                "skip": skip,
                "filters": {
                    "search": search,
                    "hospital_id": hospital_id
                }
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
                custom_message=f"Failed to retrieve patients without watch assignment: {str(e)}",
                request_id=request.headers.get("X-Request-ID") or str(uuid.uuid4())
            ).dict()
        ) 