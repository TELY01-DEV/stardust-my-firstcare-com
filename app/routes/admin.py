from datetime import datetime
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, Depends, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from bson import ObjectId
from loguru import logger
from app.services.mongo import mongodb_service
from app.services.auth import require_auth
from app.services.audit_logger import audit_logger
from app.utils.json_encoder import serialize_mongodb_response
from app.utils.error_definitions import create_error_response, create_success_response
from config import settings

router = APIRouter(prefix="/admin", tags=["Admin Panel"])

# Pydantic models for admin operations
class PatientCreate(BaseModel):
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
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    emergency_contact_relationship: Optional[str] = None
    blood_type: Optional[str] = None
    height: Optional[float] = None
    weight: Optional[float] = None
    bmi: Optional[float] = None
    watch_mac_address: Optional[str] = None
    ava_mac_address: Optional[str] = None
    new_hospital_ids: Optional[List[str]] = None

class PatientUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    nickname: Optional[str] = None
    gender: Optional[str] = None
    birth_date: Optional[datetime] = None
    id_card: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    province_code: Optional[str] = None
    district_code: Optional[str] = None
    sub_district_code: Optional[str] = None
    postal_code: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    emergency_contact_relationship: Optional[str] = None
    blood_type: Optional[str] = None
    height: Optional[float] = None
    weight: Optional[float] = None
    bmi: Optional[float] = None
    watch_mac_address: Optional[str] = None
    ava_mac_address: Optional[str] = None
    new_hospital_ids: Optional[List[str]] = None

# Device Models
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

# Medical History Models
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

# Master Data Models
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

# Patient Management
@router.get("/patients", response_model=Dict[str, Any])
async def get_patients(
    request: Request,
    limit: int = Query(100, ge=1, le=1000),
    skip: int = Query(0, ge=0),
    search: Optional[str] = None,
    hospital_id: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get patients with filtering and pagination"""
    try:
        request_id = request.headers.get("X-Request-ID")
        
        print(f"DEBUG: Starting get_patients with limit={limit}, skip={skip}, search={search}, hospital_id={hospital_id}")
        
        collection = mongodb_service.get_collection("patients")
        print(f"DEBUG: Got collection: {collection}")
        
        # Build filter
        filter_query = {"is_deleted": {"$ne": True}}
        print(f"DEBUG: Initial filter_query: {filter_query}")
        
        if search:
            filter_query["$or"] = [
                {"first_name": {"$regex": search, "$options": "i"}},
                {"last_name": {"$regex": search, "$options": "i"}},
                {"id_card": {"$regex": search, "$options": "i"}},
                {"phone": {"$regex": search, "$options": "i"}}
            ]
            print(f"DEBUG: Added search filter: {filter_query}")
        
        if hospital_id:
            filter_query["new_hospital_ids"] = ObjectId(hospital_id)
            print(f"DEBUG: Added hospital filter: {filter_query}")
        
        # Get total count
        print(f"DEBUG: Counting documents with filter: {filter_query}")
        total = await collection.count_documents(filter_query)
        print(f"DEBUG: Total count: {total}")
        
        # Get patients
        print(f"DEBUG: Finding patients with skip={skip}, limit={limit}")
        cursor = collection.find(filter_query).skip(skip).limit(limit)
        patients = await cursor.to_list(length=limit)
        print(f"DEBUG: Found {len(patients)} patients")
        
        # Serialize ObjectIds to strings
        patients = serialize_mongodb_response(patients)
        
        success_response = create_success_response(
            message="Patients retrieved successfully",
            data={
                "patients": patients,
                "total": total,
                "limit": limit,
                "skip": skip
            },
            request_id=request_id
        )
        return success_response.dict()
        
    except Exception as e:
        print(f"ERROR in get_patients: {type(e).__name__}: {str(e)}")
        import traceback
        print(f"ERROR traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                "INTERNAL_SERVER_ERROR",
                custom_message=f"Failed to retrieve patients: {str(e)}",
                request_id=request.headers.get("X-Request-ID")
            ).dict()
        )

@router.post("/patients/search")
async def search_patients_post(
    search_request: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Search patients using POST request (better for Thai characters)"""
    try:
        limit = search_request.get("limit", 100)
        skip = search_request.get("skip", 0)
        search = search_request.get("search")
        hospital_id = search_request.get("hospital_id")
        
        # Validate limit
        if limit > 1000:
            limit = 1000
        if limit < 1:
            limit = 1
        if skip < 0:
            skip = 0
            
        collection = mongodb_service.get_collection("patients")
        
        # Build filter
        filter_query = {"is_deleted": {"$ne": True}}
        
        if search:
            filter_query["$or"] = [
                {"first_name": {"$regex": search, "$options": "i"}},
                {"last_name": {"$regex": search, "$options": "i"}},
                {"id_card": {"$regex": search, "$options": "i"}},
                {"phone": {"$regex": search, "$options": "i"}},
                {"mobile_no": {"$regex": search, "$options": "i"}}
            ]
        
        if hospital_id:
            filter_query["new_hospital_ids"] = ObjectId(hospital_id)
        
        # Get total count
        total = await collection.count_documents(filter_query)
        
        # Get patients
        cursor = collection.find(filter_query).skip(skip).limit(limit)
        patients = await cursor.to_list(length=limit)
        
        # Serialize ObjectIds to strings
        patients = serialize_mongodb_response(patients)
        
        response_data = {
            "patients": patients,
            "total": total,
            "limit": limit,
            "skip": skip,
            "search_term": search
        }
        
        return JSONResponse(content=response_data)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/patients/{patient_id}", response_model=Dict[str, Any])
async def get_patient(
    patient_id: str,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get specific patient"""
    try:
        collection = mongodb_service.get_collection("patients")
        patient = await collection.find_one({"_id": ObjectId(patient_id)})
        
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")
        
        # Serialize ObjectIds to strings
        patient = serialize_mongodb_response(patient)
        
        return JSONResponse(content=patient)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/test-raw-endpoint")
async def test_raw_endpoint(current_user: Dict[str, Any] = Depends(require_auth())):
    """Simple test endpoint"""
    return {"message": "Raw endpoint test successful", "timestamp": datetime.utcnow().isoformat()}

@router.get(
    "/patients-raw-documents",
    summary="Get Raw Patient Documents",
    description="""
    ## Raw Patient Document Analysis
    
    Access complete MongoDB patient documents without serialization for analysis and debugging.
    
    ### Features:
    - **Complete Raw Structure**: All 269 fields per patient document
    - **Field Analysis**: Automatic data type detection and statistics
    - **Sample Values**: Preview of actual field content
    - **ObjectId Mapping**: MongoDB relationship identification
    - **Pagination Support**: Handle large document sets efficiently
    - **Filtering Options**: Patient ID and deletion status filters
    
    ### Document Structure (269 Fields):
    
    #### **Core Demographics** (15 fields):
    - `first_name`, `last_name`, `gender`, `birth_date`
    - `id_card`, `phone`, `email`, `nickname`
    - `address_1`, `address_2`, `province_code`, `district_code`
    
    #### **Medical Device MAC Addresses** (12 fields):
    - `ava_mac_address`, `watch_mac_address`
    - `blood_pressure_mac_address`, `blood_glucose_mac_address`
    - `body_temperature_mac_address`, `fingertip_pulse_oximeter_mac_address`
    - `cholesterol_mac_address`
    
    #### **Medical Alert Thresholds** (24 fields):
    - Blood Pressure: `bp_sbp_above`, `bp_sbp_below`, `bp_dbp_above`, `bp_dbp_below`
    - Blood Sugar: `glucose_normal_before`, `glucose_normal_after`
    - Temperature: `temperature_normal_above`, `temperature_normal_below`
    - SPO2: `spo2_normal_above`, `spo2_normal_below`
    - Cholesterol: `cholesterol_above`, `cholesterol_below`
    
    #### **Medical History Integration** (50+ fields):
    - Import dates: `blood_preassure_import_date`, `cretinines_import_date`
    - Sources: `blood_preassure_source`, `blood_sugar_source`
    - Symptoms: `blood_sugar_symptoms`, `blood_sugar_other_symptoms`
    - Lab results: `bmi`, `cholesterol`, `bun`, `creatinine`
    
    #### **Hospital & Location Data** (10 fields):
    - `hospital_data`, `new_hospital_ids`
    - `admit_at`, `admit_status`, `date_of_visit`
    
    #### **Audit & Tracking** (8 fields):
    - `created_at`, `updated_at`, `deleted_at`
    - `is_active`, `is_deleted`, `deleted_by`
    
    ### Query Parameters:
    - `limit`: Number of documents to return (1-50, default: 5)
    - `skip`: Number of documents to skip for pagination
    - `patient_id`: Filter by specific patient ObjectId
    - `include_deleted`: Include soft-deleted patients (default: false)
    
    ### Response Features:
    - **Raw Documents**: Complete MongoDB structure preserved
    - **Field Analysis**: Data type detection and usage statistics
    - **Sample Values**: Up to 3 sample values per field
    - **ObjectId Detection**: Automatic relationship mapping
    - **Pagination Info**: Total count and navigation details
    
    ### Use Cases:
    - **Database Analysis**: Understand complete patient data structure
    - **Integration Planning**: Map fields for external system integration
    - **Data Migration**: Analyze field usage and data types
    - **Debugging**: Inspect raw MongoDB documents
    - **API Development**: Understand available patient fields
    
    ### Authentication:
    Requires valid JWT Bearer token with admin privileges.
    """,
    responses={
        200: {
            "description": "Raw patient documents retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Raw patient documents retrieved successfully",
                        "data": {
                            "raw_documents": [
                                {
                                    "_id": {"$oid": "620c83a78ae03f05312cb9b5"},
                                    "first_name": "TEST 001",
                                    "last_name": "Patient 1",
                                    "phone": "789456789",
                                    "ava_mac_address": "",
                                    "blood_pressure_mac_address": "",
                                    "bp_sbp_above": 0,
                                    "bp_sbp_below": 0,
                                    "glucose_normal_before": None,
                                    "created_at": {"$date": "2022-02-16T04:55:03.469000"},
                                    "hospital_data": [],
                                    "amy_id": ""
                                }
                            ],
                            "total_count": 431,
                            "returned_count": 1,
                            "field_analysis": {
                                "_id": {
                                    "count": 1,
                                    "data_types": ["ObjectId"],
                                    "sample_values": ["620c83a78ae03f05312cb9b5"],
                                    "is_object_id": True
                                },
                                "first_name": {
                                    "count": 1,
                                    "data_types": ["str"],
                                    "sample_values": ["TEST 001"],
                                    "is_object_id": False
                                },
                                "bp_sbp_above": {
                                    "count": 1,
                                    "data_types": ["int"],
                                    "sample_values": [0],
                                    "is_object_id": False
                                }
                            },
                            "pagination": {
                                "limit": 5,
                                "skip": 0,
                                "has_more": True
                            },
                            "filters": {
                                "patient_id": None,
                                "include_deleted": False
                            },
                            "metadata": {
                                "collection": "patients",
                                "query_filter": "{'is_deleted': {'$ne': True}}",
                                "timestamp": "2024-01-15T10:30:00.000000Z"
                            }
                        }
                    }
                }
            }
        },
        400: {"description": "Invalid patient ID format"},
        401: {"description": "Authentication required"},
        403: {"description": "Admin privileges required"},
        500: {"description": "Internal server error"}
    },
    tags=["Admin Panel", "Raw Documents"]
)
async def get_raw_patient_documents(
    request: Request,
    limit: int = Query(5, ge=1, le=50, description="Number of raw documents to return"),
    skip: int = Query(0, ge=0, description="Number of documents to skip"),
    patient_id: Optional[str] = Query(None, description="Filter by specific patient ID"),
    include_deleted: bool = Query(False, description="Include soft-deleted patients"),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get raw patient documents from MongoDB without serialization for debugging and analysis"""
    try:
        request_id = request.headers.get("X-Request-ID")
        
        collection = mongodb_service.get_collection("patients")
        
        # Build filter
        filter_query = {}
        if not include_deleted:
            filter_query["is_deleted"] = {"$ne": True}
        
        if patient_id:
            try:
                filter_query["_id"] = ObjectId(patient_id)
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
        
        # Get raw documents without serialization
        cursor = collection.find(filter_query).skip(skip).limit(limit)
        raw_documents = await cursor.to_list(length=limit)
        
        # Get total count
        total_count = await collection.count_documents(filter_query)
        
        # Analyze document structure
        field_analysis: Dict[str, Any] = {}
        for doc in raw_documents:
            for field in doc.keys():
                if field not in field_analysis:
                    field_analysis[field] = {
                        "count": 0,
                        "data_types": set(),
                        "sample_values": [],
                        "is_object_id": False
                    }
                
                field_analysis[field]["count"] += 1
                
                # Analyze data types
                value = doc[field]
                value_type = type(value).__name__
                field_analysis[field]["data_types"].add(value_type)
                
                # Check if it's an ObjectId
                if isinstance(value, ObjectId):
                    field_analysis[field]["is_object_id"] = True
                    
                # Store sample values (limit to 3)
                if len(field_analysis[field]["sample_values"]) < 3:
                    if isinstance(value, ObjectId):
                        field_analysis[field]["sample_values"].append(str(value))
                    elif isinstance(value, datetime):
                        field_analysis[field]["sample_values"].append(value.isoformat())
                    elif isinstance(value, (dict, list)):
                        field_analysis[field]["sample_values"].append(str(value)[:100] + "..." if len(str(value)) > 100 else str(value))
                    else:
                        field_analysis[field]["sample_values"].append(value)
        
        # Convert sets to lists for JSON serialization
        for field_info in field_analysis.values():
            field_info["data_types"] = list(field_info["data_types"])
        
        # Convert raw documents to JSON-serializable format while preserving structure
        json_serializable_docs: List[Dict[str, Any]] = []
        for doc in raw_documents:
            serialized_doc: Dict[str, Any] = {}
            for key, value in doc.items():
                if isinstance(value, ObjectId):
                    serialized_doc[key] = {"$oid": str(value)}
                elif isinstance(value, datetime):
                    serialized_doc[key] = {"$date": value.isoformat()}
                elif isinstance(value, list):
                    serialized_doc[key] = [
                        {"$oid": str(item)} if isinstance(item, ObjectId) 
                        else {"$date": item.isoformat()} if isinstance(item, datetime)
                        else item
                        for item in value
                    ]
                else:
                    serialized_doc[key] = value
            json_serializable_docs.append(serialized_doc)
        
        success_response = create_success_response(
            message="Raw patient documents retrieved successfully",
            data={
                "raw_documents": json_serializable_docs,
                "total_count": total_count,
                "returned_count": len(json_serializable_docs),
                "field_analysis": field_analysis,
                "pagination": {
                    "limit": limit,
                    "skip": skip,
                    "has_more": total_count > (skip + len(json_serializable_docs))
                },
                "filters": {
                    "patient_id": patient_id,
                    "include_deleted": include_deleted
                },
                "metadata": {
                    "collection": "patients",
                    "query_filter": str(filter_query),
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }
            },
            request_id=request_id
        )
        
        return success_response.dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting raw patient documents: {e}")
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                "INTERNAL_SERVER_ERROR",
                custom_message=f"Failed to retrieve raw patient documents: {str(e)}",
                request_id=request.headers.get("X-Request-ID")
            ).dict()
        )

@router.post("/patients", response_model=Dict[str, Any])
async def create_patient(
    patient: PatientCreate,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Create new patient"""
    try:
        collection = mongodb_service.get_collection("patients")
        
        # Convert hospital IDs to ObjectIds
        hospital_ids = []
        if patient.new_hospital_ids:
            hospital_ids = [ObjectId(hid) for hid in patient.new_hospital_ids]
        
        patient_data = patient.dict()
        patient_data["new_hospital_ids"] = hospital_ids
        patient_data["created_at"] = datetime.utcnow()
        patient_data["updated_at"] = datetime.utcnow()
        patient_data["is_active"] = True
        patient_data["is_deleted"] = False
        
        result = await collection.insert_one(patient_data)
        
        # Log audit trail
        username = current_user.get("username", "unknown")
        await audit_logger.log_admin_action(
            action="CREATE",
            resource_type="Patient",
            resource_id=str(result.inserted_id),
            user_id=username,
            details={"patient_name": f"{patient.first_name} {patient.last_name}"}
        )
        
        return {"success": True, "patient_id": str(result.inserted_id)}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/patients/{patient_id}", response_model=Dict[str, Any])
async def update_patient(
    patient_id: str,
    patient: PatientUpdate,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Update patient"""
    try:
        collection = mongodb_service.get_collection("patients")
        
        # Convert hospital IDs to ObjectIds if provided
        update_data = patient.dict(exclude_unset=True)
        if "new_hospital_ids" in update_data and update_data["new_hospital_ids"]:
            update_data["new_hospital_ids"] = [ObjectId(hid) for hid in update_data["new_hospital_ids"]]
        
        update_data["updated_at"] = datetime.utcnow()
        
        result = await collection.update_one(
            {"_id": ObjectId(patient_id)},
            {"$set": update_data}
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Patient not found")
        
        # Log audit trail
        username = current_user.get("username", "unknown")
        await audit_logger.log_admin_action(
            action="UPDATE",
            resource_type="Patient",
            resource_id=patient_id,
            user_id=username
        )
        
        return {"success": True, "message": "Patient updated successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/patients/{patient_id}", response_model=Dict[str, Any])
async def delete_patient(
    patient_id: str,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Soft delete patient"""
    try:
        collection = mongodb_service.get_collection("patients")
        
        result = await collection.update_one(
            {"_id": ObjectId(patient_id)},
            {
                "$set": {
                    "is_deleted": True,
                    "deleted_at": datetime.utcnow(),
                    "deleted_by": current_user.get("username", "unknown"),
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Patient not found")
        
        # Log audit trail
        username = current_user.get("username", "unknown")
        await audit_logger.log_admin_action(
            action="DELETE",
            resource_type="Patient",
            resource_id=patient_id,
            user_id=username
        )
        
        return {"success": True, "message": "Patient deleted successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Device Management
@router.get("/devices", response_model=Dict[str, Any])
async def get_devices(
    device_type: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000),
    skip: int = Query(0, ge=0),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get devices by type"""
    try:
        collection_name = None
        
        if device_type == "ava4":
            collection_name = "amy_boxes"
        elif device_type == "kati":
            collection_name = "watches"
        elif device_type == "qube-vital":
            collection_name = "mfc_hv01_boxes"
        else:
            raise HTTPException(status_code=400, detail="Invalid device type")
        
        collection = mongodb_service.get_collection(collection_name)
        
        # Build filter
        filter_query = {}
        if device_type == "ava4":
            filter_query["is_deleted"] = {"$ne": True}
        elif device_type == "kati":
            filter_query["status"] = {"$ne": "deleted"}
        elif device_type == "qube-vital":
            filter_query["is_deleted"] = {"$ne": True}
        
        # Get total count
        total = await collection.count_documents(filter_query)
        
        # Get devices
        cursor = collection.find(filter_query).skip(skip).limit(limit)
        devices = await cursor.to_list(length=limit)
        
        # Serialize ObjectIds
        devices = serialize_mongodb_response(devices)
        
        response_data = {
            "devices": devices,
            "total": total,
            "device_type": device_type,
            "limit": limit,
            "skip": skip
        }
        
        return JSONResponse(content=response_data)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/devices/{device_id}")
async def legacy_get_device(
    device_id: str,
    device_type: str = Query(..., description="Device type: ava4, kati, qube-vital"),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get specific device by ID"""
    try:
        collection_name = None
        if device_type == "ava4":
            collection_name = "amy_boxes"
        elif device_type == "kati":
            collection_name = "watches"
        elif device_type == "qube-vital":
            collection_name = "mfc_hv01_boxes"
        else:
            raise HTTPException(status_code=400, detail="Invalid device type")
        
        collection = mongodb_service.get_collection(collection_name)
        device = await collection.find_one({"_id": ObjectId(device_id)})
        
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")
        
        device = serialize_mongodb_response(device)
        return JSONResponse(content=device)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/devices")
async def legacy_create_device(
    device: DeviceCreate,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Create new device"""
    try:
        collection_name = None
        if device.device_type == "ava4":
            collection_name = "amy_boxes"
        elif device.device_type == "kati":
            collection_name = "watches"
        elif device.device_type == "qube-vital":
            collection_name = "mfc_hv01_boxes"
        else:
            raise HTTPException(status_code=400, detail="Invalid device type")
        
        collection = mongodb_service.get_collection(collection_name)
        
        # Check if device with same MAC address already exists
        existing_device = await collection.find_one({"mac_address": device.mac_address})
        if existing_device:
            raise HTTPException(status_code=400, detail="Device with this MAC address already exists")
        
        # Prepare device data based on device type
        device_data = device.dict()
        device_data["created_at"] = datetime.utcnow()
        device_data["updated_at"] = datetime.utcnow()
        device_data["is_active"] = True
        
        # Convert IDs to ObjectIds if provided
        if device.hospital_id:
            device_data["hospital_id"] = ObjectId(device.hospital_id)
        if device.patient_id:
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
        
        return {"success": True, "device_id": str(result.inserted_id)}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/devices/{device_id}")
async def legacy_update_device(
    device_id: str,
    device: DeviceUpdate,
    device_type: str = Query(..., description="Device type: ava4, kati, qube-vital"),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Update device"""
    try:
        collection_name = None
        if device_type == "ava4":
            collection_name = "amy_boxes"
        elif device_type == "kati":
            collection_name = "watches"
        elif device_type == "qube-vital":
            collection_name = "mfc_hv01_boxes"
        else:
            raise HTTPException(status_code=400, detail="Invalid device type")
        
        collection = mongodb_service.get_collection(collection_name)
        
        update_data = device.dict(exclude_unset=True)
        update_data["updated_at"] = datetime.utcnow()
        
        # Convert IDs to ObjectIds if provided
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

@router.delete("/devices/{device_id}")
async def legacy_delete_device(
    device_id: str,
    device_type: str = Query(..., description="Device type: ava4, kati, qube-vital"),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Soft delete device"""
    try:
        collection_name = None
        if device_type == "ava4":
            collection_name = "amy_boxes"
        elif device_type == "kati":
            collection_name = "watches"
        elif device_type == "qube-vital":
            collection_name = "mfc_hv01_boxes"
        else:
            raise HTTPException(status_code=400, detail="Invalid device type")
        
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
        
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Device not found")
        
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

# Medical History
@router.get("/medical-history/{history_type}", response_model=Dict[str, Any])
async def get_medical_history(
    request: Request,
    history_type: str,
    patient_id: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000),
    skip: int = Query(0, ge=0),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get medical history by type"""
    try:
        request_id = request.headers.get("X-Request-ID")
        
        # Map history type to collection
        collection_mapping = {
            "blood_pressure": "blood_pressure_histories",
            "blood_sugar": "blood_sugar_histories",
            "body_data": "body_data_histories",
            "creatinine": "creatinine_histories",
            "lipid": "lipid_histories",
            "sleep_data": "sleep_data_histories",
            "spo2": "spo2_histories",
            "step": "step_histories",
            "temperature": "temprature_data_histories",
            "medication": "medication_histories",
            "allergy": "allergy_histories",
            "underlying_disease": "underlying_disease_histories",
            "admit_data": "admit_data_histories"
        }
        
        collection_name = collection_mapping.get(history_type)
        if not collection_name:
            raise HTTPException(
                status_code=400,
                detail=create_error_response(
                    "INVALID_HISTORY_TYPE",
                    field="history_type",
                    value=history_type,
                    custom_message=f"Invalid history type '{history_type}'. Supported types: {', '.join(collection_mapping.keys())}",
                    request_id=request_id
                ).dict()
            )
        
        collection = mongodb_service.get_collection(collection_name)
        
        # Build filter
        filter_query = {}
        
        if patient_id:
            filter_query["patient_id"] = ObjectId(patient_id)
        
        if start_date or end_date:
            filter_query["created_at"] = {}
            if start_date:
                filter_query["created_at"]["$gte"] = start_date
            if end_date:
                filter_query["created_at"]["$lte"] = end_date
        
        # Get total count
        total = await collection.count_documents(filter_query)
        
        # Get history
        cursor = collection.find(filter_query).sort("created_at", -1).skip(skip).limit(limit)
        history = await cursor.to_list(length=limit)
        
        # Serialize ObjectIds
        history = serialize_mongodb_response(history)
        
        success_response = create_success_response(
            message=f"Medical history ({history_type}) retrieved successfully",
            data={
                "history": history,
                "total": total,
                "history_type": history_type,
                "limit": limit,
                "skip": skip
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
                custom_message=f"Failed to retrieve medical history: {str(e)}",
                request_id=request.headers.get("X-Request-ID")
            ).dict()
        )

# Master Data Management
@router.get("/master-data/{data_type}", response_model=Dict[str, Any])
async def get_master_data(
    data_type: str,
    limit: int = Query(100, ge=1, le=1000),
    skip: int = Query(0, ge=0),
    search: Optional[str] = None,
    province_code: Optional[int] = None,
    district_code: Optional[int] = None,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get master data by type - returns raw document data field by field with relationships"""
    try:
        # Map data type to collection
        collection_mapping = {
            "hospitals": "hospitals",
            "provinces": "provinces", 
            "districts": "districts",
            "sub_districts": "sub_districts",
            "hospital_types": "master_hospital_types"
        }
        
        collection_name = collection_mapping.get(data_type)
        if not collection_name:
            raise HTTPException(status_code=400, detail="Invalid data type")
        
        collection = mongodb_service.get_collection(collection_name)
        
        # Build filter based on data type structure
        filter_query = {}
        
        # Apply entity-specific filters
        if data_type == "provinces":
            filter_query = {"is_deleted": {"$ne": True}}
        elif data_type == "districts":
            filter_query = {"is_deleted": {"$ne": True}}
            # Filter by province if specified
            if province_code:
                filter_query["province_code"] = province_code
        elif data_type == "sub_districts":
            filter_query = {"is_deleted": {"$ne": True}}
            # Filter by province and/or district if specified
            if province_code:
                filter_query["province_code"] = province_code
            if district_code:
                filter_query["district_code"] = district_code
        elif data_type == "hospital_types":
            filter_query = {"active": True}
        elif data_type == "hospitals":
            filter_query = {"is_deleted": {"$ne": True}}
            # Filter by province and/or district if specified
            if province_code:
                filter_query["province_code"] = province_code
            if district_code:
                filter_query["district_code"] = district_code
        
        # Add search functionality
        if search:
            search_conditions = []
            if data_type == "hospitals":
                search_conditions = [
                    {"name.0.name": {"$regex": search, "$options": "i"}},
                    {"name.1.name": {"$regex": search, "$options": "i"}},
                    {"en_name": {"$regex": search, "$options": "i"}}
                ]
            elif data_type in ["provinces", "districts", "sub_districts"]:
                search_conditions = [
                    {"name.0.name": {"$regex": search, "$options": "i"}},
                    {"name.1.name": {"$regex": search, "$options": "i"}},
                    {"en_name": {"$regex": search, "$options": "i"}}
                ]
            elif data_type == "hospital_types":
                search_conditions = [
                    {"name.th": {"$regex": search, "$options": "i"}},
                    {"name.en": {"$regex": search, "$options": "i"}}
                ]
            
            if search_conditions:
                filter_query["$or"] = search_conditions
        
        # Get total count
        total = await collection.count_documents(filter_query)
        
        # Get data with sorting
        sort_field = "created_at" if data_type in ["provinces", "districts", "sub_districts", "hospitals"] else "_id"
        cursor = collection.find(filter_query).sort(sort_field, 1).skip(skip).limit(limit)
        data = await cursor.to_list(length=limit)
        
        # Serialize ObjectIds to maintain raw document structure
        data = serialize_mongodb_response(data)
        
        response_data = {
            "data": data,
            "total": total,
            "data_type": data_type,
            "limit": limit,
            "skip": skip,
            "filters": {
                "search": search,
                "province_code": province_code,
                "district_code": district_code
            },
            "fields_info": get_master_data_fields_info(data_type),
            "relationships": get_master_data_relationships(data_type)
        }
        
        return JSONResponse(content=response_data)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def get_master_data_fields_info(data_type: str) -> Dict[str, Any]:
    """Get field information for master data types"""
    fields_info = {
        "provinces": {
            "description": "Thailand provinces master data",
            "fields": {
                "_id": "MongoDB ObjectId",
                "code": "Province code (integer) - Primary key for relationships",
                "name": "Array of name objects with language codes (en/th)",
                "en_name": "English name (string)",
                "zone": "Zone number (integer)",
                "is_active": "Active status (boolean)",
                "is_deleted": "Deleted status (boolean)",
                "created_at": "Creation timestamp",
                "updated_at": "Last update timestamp",
                "__v": "Version key"
            }
        },
        "districts": {
            "description": "Thailand districts master data",
            "fields": {
                "_id": "MongoDB ObjectId",
                "code": "District code (integer) - Primary key for relationships",
                "name": "Array of name objects with language codes (en/th)",
                "name_short": "Array of short name objects with language codes (en/th)",
                "is_active": "Active status (boolean)",
                "is_deleted": "Deleted status (boolean)",
                "en_name": "English name (string)",
                "areacode": "Area code (integer)",
                "province_code": "Parent province code (integer) - Foreign key to provinces.code",
                "created_at": "Creation timestamp",
                "updated_at": "Last update timestamp",
                "__v": "Version key"
            }
        },
        "sub_districts": {
            "description": "Thailand sub-districts master data",
            "fields": {
                "_id": "MongoDB ObjectId",
                "code": "Sub-district code (integer) - Primary key for relationships",
                "name": "Array of name objects with language codes (en/th)",
                "name_short": "Array of short name objects with language codes (en/th)",
                "is_active": "Active status (boolean)",
                "is_deleted": "Deleted status (boolean)",
                "en_name": "English name (string)",
                "province_code": "Parent province code (integer) - Foreign key to provinces.code",
                "district_code": "Parent district code (integer) - Foreign key to districts.code",
                "created_at": "Creation timestamp",
                "updated_at": "Last update timestamp",
                "__v": "Version key"
            }
        },
        "hospital_types": {
            "description": "Hospital types master data",
            "fields": {
                "_id": "MongoDB ObjectId or String - Primary key",
                "name": "Object with Thai (th) and English (en) names",
                "active": "Active status (boolean)"
            }
        },
        "hospitals": {
            "description": "Hospitals master data with full operational details",
            "fields": {
                "_id": "MongoDB ObjectId",
                "name": "Array of name objects with language codes (en/th)",
                "is_active": "Active status (boolean)",
                "is_deleted": "Deleted status (boolean)",
                "en_name": "English name (string)",
                "province_code": "Province code (integer) - Foreign key to provinces.code",
                "district_code": "District code (integer) - Foreign key to districts.code",
                "sub_district_code": "Sub-district code (integer) - Foreign key to sub_districts.code",
                "organizecode": "Organization code (integer)",
                "hospital_area_code": "Hospital area code (string)",
                "created_at": "Creation timestamp",
                "updated_at": "Last update timestamp",
                "__v": "Version key",
                "bed_capacity": "Number of beds (integer)",
                "image_url": "Hospital image URL (string)",
                "location": "GPS coordinates [latitude, longitude]",
                "auto_login_liff_id": "LINE auto login LIFF ID",
                "disconnect_liff_id": "LINE disconnect LIFF ID", 
                "login_liff_id": "LINE login LIFF ID",
                "mac_hv01_box": "MAC address of HV01 box",
                "notifyToken": "LINE Notify token",
                "service_plan_type": "Service plan type (A, F3, etc.)",
                "rich_menu_token": "LINE rich menu token",
                "telegram_Token": "Telegram notification token",
                "is_acknowledge": "Acknowledgment notifications enabled",
                "is_admit_discard": "Admit/discharge notifications enabled",
                "is_body_data": "Body data monitoring enabled",
                "is_lab_data": "Lab data monitoring enabled",
                "is_status_change": "Status change notifications enabled",
                "is_vs_data": "Vital signs data enabled",
                "is_vs_notify": "Vital signs notifications enabled",
                "is_watch_data": "Watch data monitoring enabled",
                "is_watch_notify": "Watch notifications enabled",
                "is_watch_status_change": "Watch status change notifications enabled",
                "is_default_value": "Use default values",
                "is_line_notify": "LINE notifications enabled",
                "is_telegram_notify": "Telegram notifications enabled"
            }
        }
    }
    
    return fields_info.get(data_type, {"description": "Unknown data type", "fields": {}})

def get_master_data_relationships(data_type: str) -> Dict[str, Any]:
    """Get relationship information for master data types"""
    relationships = {
        "provinces": {
            "children": [
                {"entity": "districts", "relationship": "districts.province_code = provinces.code"},
                {"entity": "sub_districts", "relationship": "sub_districts.province_code = provinces.code"},
                {"entity": "hospitals", "relationship": "hospitals.province_code = provinces.code"}
            ]
        },
        "districts": {
            "parent": {"entity": "provinces", "relationship": "districts.province_code = provinces.code"},
            "children": [
                {"entity": "sub_districts", "relationship": "sub_districts.district_code = districts.code"},
                {"entity": "hospitals", "relationship": "hospitals.district_code = districts.code"}
            ]
        },
        "sub_districts": {
            "parents": [
                {"entity": "provinces", "relationship": "sub_districts.province_code = provinces.code"},
                {"entity": "districts", "relationship": "sub_districts.district_code = districts.code"}
            ],
            "children": [
                {"entity": "hospitals", "relationship": "hospitals.sub_district_code = sub_districts.code"}
            ]
        },
        "hospital_types": {
            "children": [
                {"entity": "hospitals", "relationship": "hospitals.hospital_type = hospital_types._id"}
            ]
        },
        "hospitals": {
            "parents": [
                {"entity": "provinces", "relationship": "hospitals.province_code = provinces.code"},
                {"entity": "districts", "relationship": "hospitals.district_code = districts.code"},
                {"entity": "sub_districts", "relationship": "hospitals.sub_district_code = sub_districts.code"},
                {"entity": "hospital_types", "relationship": "hospitals.hospital_type = hospital_types._id"}
            ]
        }
    }
    
    return relationships.get(data_type, {})

# Audit Log
@router.get("/audit-log", response_model=Dict[str, Any])
async def get_audit_logs(
    request: Request,
    limit: int = Query(100, ge=1, le=1000),
    skip: int = Query(0, ge=0),
    resource_type: Optional[str] = None,
    user_id: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get audit logs"""
    try:
        request_id = request.headers.get("X-Request-ID")
        
        logs = await audit_logger.get_audit_logs(
            limit=limit,
            skip=skip,
            resource_type=resource_type,
            user_id=user_id,
            start_date=start_date,
            end_date=end_date
        )
        # Serialize ObjectIds
        logs = serialize_mongodb_response(logs)
        
        success_response = create_success_response(
            message="Audit logs retrieved successfully",
            data={
                "logs": logs,
                "total": len(logs),
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
                custom_message=f"Failed to retrieve audit logs: {str(e)}",
                request_id=request.headers.get("X-Request-ID")
            ).dict()
        )

# Dashboard Analytics
@router.get("/analytics", response_model=Dict[str, Any])
async def get_analytics(
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get dashboard analytics"""
    try:
        # Get counts
        patients_collection = mongodb_service.get_collection("patients")
        ava4_collection = mongodb_service.get_collection("amy_boxes")
        kati_collection = mongodb_service.get_collection("watches")
        qube_collection = mongodb_service.get_collection("mfc_hv01_boxes")
        
        total_patients = await patients_collection.count_documents({"is_deleted": {"$ne": True}})
        total_ava4 = await ava4_collection.count_documents({"is_deleted": {"$ne": True}})
        total_kati = await kati_collection.count_documents({"status": {"$ne": "deleted"}})
        total_qube = await qube_collection.count_documents({"is_deleted": {"$ne": True}})
        
        # Get recent activity
        audit_collection = mongodb_service.get_collection("fhir_provenance")
        recent_logs = await audit_collection.find().sort("recorded", -1).limit(10).to_list(length=10)
        
        # Serialize ObjectIds
        recent_logs = serialize_mongodb_response(recent_logs)
        
        response_data = {
            "total_patients": total_patients,
            "total_ava4_devices": total_ava4,
            "total_kati_devices": total_kati,
            "total_qube_devices": total_qube,
            "recent_activity": recent_logs
        }
        
        return JSONResponse(content=response_data)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 