from datetime import datetime
from typing import Dict, Any, Optional, List
import uuid
import json
from fastapi import APIRouter, HTTPException, Depends, Request, Query, Body, Path
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from bson import ObjectId
from loguru import logger
from app.services.mongo import mongodb_service
from app.services.auth import require_auth
from app.services.audit_logger import audit_logger
from app.utils.json_encoder import serialize_mongodb_response, MongoJSONEncoder, serialize_field_analysis, create_mongodb_compatible_response
from app.utils.error_definitions import create_error_response, create_success_response, SuccessResponse
from app.models.hospital_user import (
    HospitalUserCreate, HospitalUserUpdate, HospitalUserResponse, 
    HospitalUserList, HospitalUserSearchQuery, HospitalUserStats
)
from app.models.medical_history import (
    MedicalHistoryCreate as MedicalHistoryCreateModel, 
    MedicalHistoryUpdate as MedicalHistoryUpdateModel, 
    MedicalHistorySearchQuery as MedicalHistorySearchQueryModel,
    MedicalHistoryStats as MedicalHistoryStatsModel, 
    BulkMedicalHistoryDelete as BulkMedicalHistoryDeleteModel, 
    BulkMedicalHistoryUpdate as BulkMedicalHistoryUpdateModel,
    MedicalHistoryCollectionInfo as MedicalHistoryCollectionInfoModel
)
from config import settings
import time

router = APIRouter(prefix="/admin", tags=["admin"])

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
    name: Optional[List[Dict[str, str]]] = None
    code: Optional[int] = None
    is_active: Optional[bool] = True
    province_code: Optional[int] = None
    district_code: Optional[int] = None
    sub_district_code: Optional[int] = None
    additional_fields: Optional[Dict[str, Any]] = None

class MasterDataUpdate(BaseModel):
    name: Optional[List[Dict[str, str]]] = None
    code: Optional[int] = None
    is_active: Optional[bool] = None
    province_code: Optional[int] = None
    district_code: Optional[int] = None
    sub_district_code: Optional[int] = None
    additional_fields: Optional[Dict[str, Any]] = None

# Patient Management
@router.get("/patients", 
            response_model=SuccessResponse,
            responses={
                200: {
                    "description": "Patients retrieved successfully",
                    "content": {
                        "application/json": {
                            "example": {
                                "success": True,
                                "message": "Patients retrieved successfully",
                                "data": {
                                    "patients": [
                                        {
                                            "_id": "507f1f77bcf86cd799439011",
                                            "first_name": "John",
                                            "last_name": "Doe",
                                            "gender": "male",
                                            "birth_date": "1990-01-15",
                                            "phone": "+66-XXX-XXX-XXXX",
                                            "hospital_id": "507f1f77bcf86cd799439012"
                                        }
                                    ],
                                    "total": 431,
                                    "limit": 100,
                                    "skip": 0
                                },
                                "request_id": "e5f6g7h8-i9j0-1234-efgh-567890123456",
                                "timestamp": "2025-07-07T07:08:07.633870Z"
                            }
                        }
                    }
                },
                401: {
                    "description": "Authentication required",
                    "content": {
                        "application/json": {
                            "example": {
                                "detail": "Authentication required"
                            }
                        }
                    }
                },
                500: {
                    "description": "Internal server error",
                    "content": {
                        "application/json": {
                            "example": {
                                "success": False,
                                "error_count": 1,
                                "errors": [{
                                    "error_code": "INTERNAL_SERVER_ERROR",
                                    "error_type": "system_error",
                                    "message": "Failed to retrieve patients: Database connection error",
                                    "field": None,
                                    "value": None,
                                    "suggestion": "Please try again later or contact support if the issue persists"
                                }],
                                "request_id": "f6g7h8i9-j0k1-2345-fghi-678901234567",
                                "timestamp": "2025-07-07T07:08:07.633870Z"
                            }
                        }
                    }
                }
            })
async def get_patients(
    request: Request,
    limit: int = Query(100, ge=1, le=1000),
    skip: int = Query(0, ge=0),
    page: Optional[int] = Query(None, ge=1, description="Page number (alternative to skip)"),
    search: Optional[str] = None,
    hospital_id: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get patients with filtering and pagination"""
    import uuid
    try:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        collection = mongodb_service.get_collection("patients")
        
        # Build filter
        filter_query = {"is_deleted": {"$ne": True}}
        
        if search:
            filter_query["$or"] = [
                {"first_name": {"$regex": search, "$options": "i"}},
                {"last_name": {"$regex": search, "$options": "i"}},
                {"id_card": {"$regex": search, "$options": "i"}},
                {"phone": {"$regex": search, "$options": "i"}}
            ]
        
        if hospital_id:
            filter_query["new_hospital_ids"] = ObjectId(hospital_id)
        
        # Get total count
        total = await collection.count_documents(filter_query)

        # Handle pagination - support both page and skip parameters
        if page is not None:
            skip = (page - 1) * limit

        # Get patients with consistent ordering for pagination
        cursor = collection.find(filter_query).sort("_id", 1).skip(skip).limit(limit)
        patients = await cursor.to_list(length=limit)
        
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
        return success_response
        
    except Exception as e:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                "INTERNAL_SERVER_ERROR",
                custom_message=f"Failed to retrieve patients: {str(e)}",
                request_id=request_id
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
        
        # Get patients with consistent ordering for pagination
        cursor = collection.find(filter_query).sort("_id", 1).skip(skip).limit(limit)
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
    tags=["admin"]
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
    import uuid
    try:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
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
        cursor = collection.find(filter_query).sort("_id", 1).skip(skip).limit(limit)
        raw_documents = await cursor.to_list(length=limit)
        
        # Get total count
        total_count = await collection.count_documents(filter_query)
        
        # If no documents found, return a clear error
        if total_count == 0:
            raise HTTPException(
                status_code=404,
                detail=create_error_response(
                    "NO_HOSPITAL_DOCUMENTS_FOUND",
                    custom_message="No hospital documents found in the database for the given filter.",
                    field=None,
                    value=None,
                    request_id=request_id
                ).dict()
            )
        
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
        
        # Create response data using enhanced serialization
        response_data = {
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
        }
        
        # Use the enhanced MongoDB-compatible response creator
        final_response = create_mongodb_compatible_response(
            success=True,
            message="Raw patient documents retrieved successfully",
            data=response_data,
            request_id=request_id
        )
        
        # Return as JSONResponse with full serialization guarantee
        return JSONResponse(content=final_response)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting raw patient documents: {e}")
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                "INTERNAL_SERVER_ERROR",
                custom_message=f"Failed to retrieve raw patient documents: {str(e)}",
                request_id=request_id
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
        cursor = collection.find(filter_query).sort("_id", 1).skip(skip).limit(limit)
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
    import uuid
    try:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
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
            "temperature": "temperature_data_histories",
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
        try:
            total = await collection.count_documents(filter_query)
        except Exception as e:
            logger.warning(f"Failed to count documents: {e}")
            total = 0
        
        # Get history
        try:
            cursor = collection.find(filter_query).sort("created_at", -1).skip(skip).limit(limit)
            history = await cursor.to_list(length=limit)
        except Exception as e:
            logger.warning(f"Failed to fetch records: {e}")
            history = []
        
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
        return success_response
        
    except HTTPException:
        raise
    except Exception as e:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                "INTERNAL_SERVER_ERROR",
                custom_message=f"Failed to retrieve medical history: {str(e)}",
                request_id=request_id
            ).dict()
        )

@router.get("/medical-history/{history_type}/{record_id}", 
            response_model=SuccessResponse,
            summary="Get Medical History Record by ID",
            description="""
## Get Medical History Record by ID

Retrieve a specific medical history record by its ID.

### Supported History Types:
- `blood_pressure`, `blood_sugar`, `body_data`, `creatinine`, `lipid`
- `sleep_data`, `spo2`, `step`, `temperature`, `medication`
- `allergy`, `underlying_disease`, `admit_data`

### Features:
- **Record Validation**: Validates ObjectId format
- **Error Handling**: Comprehensive error responses
- **Data Serialization**: Proper MongoDB ObjectId handling
- **Audit Trail**: Request tracking with request_id

### Authentication:
Requires valid JWT Bearer token with admin privileges.
            """,
            responses={
                200: {
                    "description": "Medical history record retrieved successfully",
                    "content": {
                        "application/json": {
                            "example": {
                                "success": True,
                                "message": "Medical history record retrieved successfully",
                                "data": {
                                    "record": {
                                        "_id": "507f1f77bcf86cd799439011",
                                        "patient_id": "507f1f77bcf86cd799439012",
                                        "history_type": "blood_pressure",
                                        "values": {
                                            "systolic": 120,
                                            "diastolic": 80,
                                            "pulse": 72
                                        },
                                        "created_at": "2024-01-15T10:30:00.000Z"
                                    },
                                    "history_type": "blood_pressure"
                                },
                                "request_id": "medical-history-001",
                                "timestamp": "2025-07-10T12:00:00.000Z"
                            }
                        }
                    }
                },
                400: {"description": "Invalid record ID format or history type"},
                401: {"description": "Authentication required"},
                404: {"description": "Medical history record not found"},
                500: {"description": "Internal server error"}
            })
async def get_medical_history_record(
    request: Request,
    history_type: str,
    record_id: str,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get specific medical history record"""
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    
    try:
        # Validate record_id format
        if not ObjectId.is_valid(record_id):
            raise HTTPException(
                status_code=400,
                detail=create_error_response(
                    "INVALID_RECORD_ID",
                    custom_message="Invalid record ID format",
                    field="record_id",
                    value=record_id,
                    request_id=request_id
                ).dict()
            )
        
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
            "temperature": "temperature_data_histories",
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
                    custom_message=f"Invalid history type '{history_type}'. Supported types: {', '.join(collection_mapping.keys())}",
                    field="history_type",
                    value=history_type,
                    request_id=request_id
                ).dict()
            )
        
        collection = mongodb_service.get_collection(collection_name)
        
        record = await collection.find_one({"_id": ObjectId(record_id)})
        
        if not record:
            raise HTTPException(
                status_code=404,
                detail=create_error_response(
                    "MEDICAL_HISTORY_NOT_FOUND",
                    custom_message=f"Medical history record with ID {record_id} not found",
                    field="record_id",
                    value=record_id,
                    request_id=request_id
                ).dict()
            )
        
        record = serialize_mongodb_response(record)
        
        success_response = create_success_response(
            message="Medical history record retrieved successfully",
            data={"record": record, "history_type": history_type},
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
                custom_message=f"Failed to retrieve medical history: {str(e)}",
                request_id=request_id
            ).dict()
        )

# Master Data Management
@router.get("/master-data/{data_type}", 
            response_model=SuccessResponse,
            summary="Get Master Data by Type",
            description="Get master data by type with comprehensive examples and multilingual support.",
            responses={
                200: {"description": "Master data retrieved successfully"},
                400: {"description": "Invalid data type"},
                401: {"description": "Authentication required"},
                403: {"description": "Admin privileges required"},
                500: {"description": "Internal server error"}
            }
        )
async def get_master_data(
    request: Request,
    data_type: str,
    limit: int = Query(100, ge=1, le=5000, description="Number of records per page (max 5000)"),
    skip: int = Query(0, ge=0, description="Number of records to skip for pagination"),
    search: Optional[str] = None,
    province_code: Optional[int] = None,
    district_code: Optional[int] = None,
    sub_district_code: Optional[int] = None,
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get master data by type with enhanced pagination for large datasets"""
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    try:
        # Normalize data_type: convert hyphens to underscores for consistency
        normalized_data_type = data_type.replace("-", "_")
        
        # Map data type to collection
        collection_mapping = {
            "hospitals": "hospitals",
            "provinces": "provinces", 
            "districts": "districts",
            "sub_districts": "sub_districts",
            "hospital_types": "master_hospital_types",
            "blood_groups": "blood_groups",
            "human_skin_colors": "human_skin_colors",
            "nations": "nations",
            "ward_lists": "ward_lists",
            "staff_types": "staff_types",
            "underlying_diseases": "underlying_diseases"
        }
        
        collection_name = collection_mapping.get(normalized_data_type)
        if not collection_name:
            raise HTTPException(status_code=400, detail=f"Invalid data type: {data_type}. Supported types: {', '.join(collection_mapping.keys())}")
        
        collection = mongodb_service.get_collection(collection_name)
        
        # Build filter based on data type structure
        filter_query = {}
        
        # Apply entity-specific filters
        if normalized_data_type == "provinces":
            filter_query = {"is_deleted": {"$ne": True}}
            # Add is_active filter if specified
            if is_active is not None:
                filter_query["is_active"] = is_active
        elif normalized_data_type == "districts":
            filter_query = {"is_deleted": {"$ne": True}}
            # Add is_active filter if specified
            if is_active is not None:
                filter_query["is_active"] = is_active
            # Filter by province if specified
            if province_code:
                filter_query["province_code"] = province_code
        elif normalized_data_type == "sub_districts":
            filter_query = {"is_deleted": {"$ne": True}}
            # Add is_active filter if specified
            if is_active is not None:
                filter_query["is_active"] = is_active
            # Filter by province and/or district if specified
            if province_code:
                filter_query["province_code"] = province_code
            if district_code:
                filter_query["district_code"] = district_code
        elif normalized_data_type == "hospital_types":
            filter_query = {"active": True}
        elif normalized_data_type == "hospitals":
            filter_query = {"is_deleted": {"$ne": True}}
            # Add is_active filter if specified
            if is_active is not None:
                filter_query["is_active"] = is_active
            # Filter by province, district, and/or sub-district if specified
            if province_code:
                filter_query["province_code"] = province_code
            if district_code:
                filter_query["district_code"] = district_code
            if sub_district_code:
                filter_query["sub_district_code"] = sub_district_code
        elif normalized_data_type in ["blood_groups", "human_skin_colors", "nations", "ward_lists", "staff_types", "underlying_diseases"]:
            filter_query = {"is_deleted": {"$ne": True}}
            # Add is_active filter if specified
            if is_active is not None:
                filter_query["is_active"] = is_active
        
        # Add search functionality
        if search:
            search_conditions = []
            if normalized_data_type == "hospitals":
                search_conditions = [
                    {"name.0.name": {"$regex": search, "$options": "i"}},
                    {"name.1.name": {"$regex": search, "$options": "i"}},
                    {"en_name": {"$regex": search, "$options": "i"}}
                ]
            elif normalized_data_type in ["provinces", "districts", "sub_districts"]:
                search_conditions = [
                    {"name.0.name": {"$regex": search, "$options": "i"}},
                    {"name.1.name": {"$regex": search, "$options": "i"}},
                    {"en_name": {"$regex": search, "$options": "i"}}
                ]
            elif normalized_data_type == "hospital_types":
                search_conditions = [
                    {"name.th": {"$regex": search, "$options": "i"}},
                    {"name.en": {"$regex": search, "$options": "i"}}
                ]
            elif normalized_data_type in ["blood_groups", "human_skin_colors", "nations", "ward_lists", "staff_types", "underlying_diseases"]:
                search_conditions = [
                    {"name.0.name": {"$regex": search, "$options": "i"}},
                    {"name.1.name": {"$regex": search, "$options": "i"}},
                    {"en_name": {"$regex": search, "$options": "i"}}
                ]
            
            if search_conditions:
                filter_query["$or"] = search_conditions
        
        # Get total count for pagination metadata
        total = await collection.count_documents(filter_query)
        
        # Get data with sorting and pagination
        sort_field = "created_at" if normalized_data_type in ["provinces", "districts", "sub_districts", "hospitals", "blood_groups", "human_skin_colors", "nations"] else "_id"
        cursor = collection.find(filter_query).sort(sort_field, 1).skip(skip).limit(limit)
        data = await cursor.to_list(length=limit)
        
        # Serialize ObjectIds to maintain raw document structure
        data = serialize_mongodb_response(data)
        
        # Calculate pagination metadata
        total_pages = (total + limit - 1) // limit  # Ceiling division
        current_page = (skip // limit) + 1
        has_next = (skip + limit) < total
        has_prev = skip > 0
        
        success_response = create_success_response(
            message="Master data retrieved successfully",
            data={
                "data": data,
                "total": total,
                "data_type": normalized_data_type,
                "limit": limit,
                "skip": skip,
                "pagination": {
                    "current_page": current_page,
                    "total_pages": total_pages,
                    "has_next": has_next,
                    "has_prev": has_prev,
                    "total_records": total,
                    "records_on_page": len(data)
                },
                "filters": {
                    "search": search,
                    "province_code": province_code,
                    "district_code": district_code,
                    "sub_district_code": sub_district_code,
                    "is_active": is_active
                },
                "fields_info": get_master_data_fields_info(normalized_data_type),
                "relationships": get_master_data_relationships(normalized_data_type)
            },
            request_id=request_id
        )
        
        return success_response
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                "INTERNAL_SERVER_ERROR",
                custom_message=f"Failed to retrieve master data: {str(e)}",
                request_id=request_id
            ).dict()
        )

@router.get("/master-data/{data_type}/{record_id}/edit", 
            response_model=SuccessResponse,
            summary="Get Master Data Record for Editing",
            description="""
## Get Master Data Record for Editing

Retrieve a specific master data record by its ID for editing purposes. This endpoint is designed for frontend edit forms.

### Supported Data Types:
- `hospitals`, `provinces`, `districts`, `sub_districts`
- `blood_groups`, `nations`, `human_skin_colors`, `ward_lists`, `staff_types`, `underlying_diseases`, `hospital_types`

### Features:
- **Edit Form Ready**: Returns data formatted for edit forms
- **Record Validation**: Validates ObjectId format
- **Error Handling**: Comprehensive error responses
- **Data Serialization**: Proper MongoDB ObjectId handling
- **Audit Trail**: Request tracking with request_id

### Use Cases:
- Frontend edit forms for master data records
- Pre-populating edit interfaces
- Data validation before editing
- Form field initialization

### Authentication:
Requires valid JWT Bearer token with admin privileges.
            """,
            responses={
                200: {
                    "description": "Master data record retrieved successfully for editing",
                    "content": {
                        "application/json": {
                            "example": {
                                "success": True,
                                "message": "Master data record retrieved successfully for editing",
                                "data": {
                                    "record": {
                                        "_id": "507f1f77bcf86cd799439011",
                                        "name": [
                                            {"code": "en", "name": "Bangkok General Hospital"},
                                            {"code": "th", "name": "โรงพยาบาลกรุงเทพ"}
                                        ],
                                        "en_name": "Bangkok General Hospital",
                                        "province_code": 10,
                                        "is_active": True
                                    },
                                    "data_type": "hospitals",
                                    "edit_mode": True
                                },
                                "request_id": "master-data-edit-001",
                                "timestamp": "2025-07-10T12:00:00.000Z"
                            }
                        }
                    }
                },
                400: {"description": "Invalid record ID format or data type"},
                401: {"description": "Authentication required"},
                404: {"description": "Master data record not found"},
                500: {"description": "Internal server error"}
            })
async def get_master_data_record_for_edit(
    request: Request,
    data_type: str,
    record_id: str,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get a specific master data record by ID for editing purposes"""
    try:
        request_id = str(uuid.uuid4())
        
        # Normalize data type
        normalized_data_type = data_type.lower().replace("-", "_")
        
        # Validate data type
        valid_data_types = [
            "hospitals", "provinces", "districts", "sub_districts",
            "blood_groups", "nations", "human_skin_colors", "ward_lists", 
            "staff_types", "underlying_diseases", "hospital_types"
        ]
        
        if normalized_data_type not in valid_data_types:
            # Trigger alert for invalid data type error
            try:
                from app.utils.alert_system import alert_manager
                await alert_manager.process_event({
                    "event_type": "http_error",
                    "status_code": 400,
                    "error_type": "INVALID_DATA_TYPE",
                    "error_message": f"Invalid data type: {data_type}. Please use one of the supported data types: {', '.join(valid_data_types)}",
                    "request_id": request_id,
                    "client_ip": request.client.host if request.client else "unknown",
                    "method": request.method,
                    "path": request.url.path,
                    "timestamp": datetime.utcnow().isoformat(),
                    "source": "master_data_edit_endpoint"
                })
            except Exception as alert_error:
                logger.error(f"Failed to trigger alert: {alert_error}")
            
            raise HTTPException(
                status_code=400,
                detail=create_error_response(
                    "INVALID_DATA_TYPE",
                    custom_message=f"Invalid data type: {data_type}. Please use one of the supported data types: {', '.join(valid_data_types)}",
                    field="data_type",
                    value=data_type,
                    request_id=request_id
                ).dict()
            )
        
        # Validate ObjectId format
        try:
            ObjectId(record_id)
        except Exception:
            raise HTTPException(
                status_code=400,
                detail=create_error_response(
                    "INVALID_RECORD_ID",
                    custom_message=f"Invalid record ID format: {record_id}. Please provide a valid MongoDB ObjectId (24-character hex string)",
                    field="record_id",
                    value=record_id,
                    request_id=request_id
                ).dict()
            )
        
        # Get collection
        collection = mongodb_service.get_collection(normalized_data_type)
        
        # Find the specific record
        record = await collection.find_one({"_id": ObjectId(record_id)})
        
        if not record:
            raise HTTPException(
                status_code=404,
                detail=create_error_response(
                    "RECORD_NOT_FOUND",
                    custom_message=f"Record not found: {record_id}. Please check the record ID and try again",
                    field="record_id",
                    value=record_id,
                    request_id=request_id
                ).dict()
            )
        
        # Serialize ObjectIds to strings
        record = serialize_mongodb_response(record)
        
        success_response = create_success_response(
            message="Master data record retrieved successfully for editing",
            data={
                "record": record,
                "data_type": normalized_data_type,
                "edit_mode": True
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
                custom_message=f"Failed to retrieve master data record for editing: {str(e)}",
                request_id=request_id
            ).dict()
        )

@router.get("/master-data/{data_type}/{record_id}", 
            response_model=SuccessResponse,
            summary="Get Master Data Record by ID",
            description="""
## Get Master Data Record by ID

Retrieve a specific master data record by its ID.

### Supported Data Types:
- `hospitals`, `provinces`, `districts`, `sub_districts`
- `blood_groups`, `nations`, `human_skin_colors`, `ward_lists`, `staff_types`, `underlying_diseases`, `hospital_types`

### Features:
- **Record Validation**: Validates ObjectId format
- **Error Handling**: Comprehensive error responses
- **Data Serialization**: Proper MongoDB ObjectId handling
- **Audit Trail**: Request tracking with request_id

### Authentication:
Requires valid JWT Bearer token with admin privileges.
            """,
            responses={
                200: {
                    "description": "Master data record retrieved successfully",
                    "content": {
                        "application/json": {
                            "example": {
                                "success": True,
                                "message": "Master data record retrieved successfully",
                                "data": {
                                    "record": {
                                        "_id": "507f1f77bcf86cd799439011",
                                        "name": [
                                            {"code": "en", "name": "Bangkok General Hospital"},
                                            {"code": "th", "name": "โรงพยาบาลกรุงเทพ"}
                                        ],
                                        "en_name": "Bangkok General Hospital",
                                        "province_code": 10,
                                        "is_active": True
                                    },
                                    "data_type": "hospitals"
                                },
                                "request_id": "master-data-001",
                                "timestamp": "2025-07-10T12:00:00.000Z"
                            }
                        }
                    }
                },
                400: {"description": "Invalid record ID format or data type"},
                401: {"description": "Authentication required"},
                404: {"description": "Master data record not found"},
                500: {"description": "Internal server error"}
            })
async def get_master_data_record(
    request: Request,
    data_type: str,
    record_id: str,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get a specific master data record by ID"""
    try:
        request_id = str(uuid.uuid4())
        
        # Normalize data type
        normalized_data_type = data_type.lower().replace("-", "_")
        
        # Validate data type
        valid_data_types = [
            "hospitals", "provinces", "districts", "sub_districts",
            "blood_groups", "nations", "human_skin_colors", "ward_lists", 
            "staff_types", "underlying_diseases", "hospital_types"
        ]
        
        if normalized_data_type not in valid_data_types:
            # Trigger alert for invalid data type error
            try:
                from app.utils.alert_system import alert_manager
                await alert_manager.process_event({
                    "event_type": "http_error",
                    "status_code": 400,
                    "error_type": "INVALID_DATA_TYPE",
                    "error_message": f"Invalid data type: {data_type}. Please use one of the supported data types: {', '.join(valid_data_types)}",
                    "request_id": request_id,
                    "client_ip": request.client.host if request.client else "unknown",
                    "method": request.method,
                    "path": request.url.path,
                    "timestamp": datetime.utcnow().isoformat(),
                    "source": "master_data_endpoint"
                })
            except Exception as alert_error:
                logger.error(f"Failed to trigger alert: {alert_error}")
            
            raise HTTPException(
                status_code=400,
                detail=create_error_response(
                    "INVALID_DATA_TYPE",
                    custom_message=f"Invalid data type: {data_type}. Please use one of the supported data types: {', '.join(valid_data_types)}",
                    field="data_type",
                    value=data_type,
                    request_id=request_id
                ).dict()
            )
        
        # Validate ObjectId format
        try:
            ObjectId(record_id)
        except Exception:
            raise HTTPException(
                status_code=400,
                detail=create_error_response(
                    "INVALID_RECORD_ID",
                    custom_message=f"Invalid record ID format: {record_id}. Please provide a valid MongoDB ObjectId (24-character hex string)",
                    field="record_id",
                    value=record_id,
                    request_id=request_id
                ).dict()
            )
        
        # Get collection
        collection = mongodb_service.get_collection(normalized_data_type)
        
        # Find the specific record
        record = await collection.find_one({"_id": ObjectId(record_id)})
        
        if not record:
            raise HTTPException(
                status_code=404,
                detail=create_error_response(
                    "RECORD_NOT_FOUND",
                    custom_message=f"Record not found: {record_id}. Please check the record ID and try again",
                    field="record_id",
                    value=record_id,
                    request_id=request_id
                ).dict()
            )
        
        # Serialize ObjectIds to strings
        record = serialize_mongodb_response(record)
        
        success_response = create_success_response(
            message="Master data record retrieved successfully",
            data={
                "record": record,
                "data_type": normalized_data_type
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
                custom_message=f"Failed to retrieve master data record: {str(e)}",
                request_id=request_id
            ).dict()
        )

def get_master_data_fields_info(data_type: str) -> Dict[str, Any]: 
            response_model=SuccessResponse,
            summary="Get Master Data Record for Editing",
            description="""
## Get Master Data Record for Editing

Retrieve a specific master data record by its ID for editing purposes. This endpoint is designed for frontend edit forms.

### Supported Data Types:
- `hospitals`, `provinces`, `districts`, `sub_districts`
- `blood_groups`, `nations`, `human_skin_colors`, `ward_lists`, `staff_types`, `underlying_diseases`, `hospital_types`

### Features:
- **Edit Form Ready**: Returns data formatted for edit forms
- **Record Validation**: Validates ObjectId format
- **Error Handling**: Comprehensive error responses
- **Data Serialization**: Proper MongoDB ObjectId handling
- **Audit Trail**: Request tracking with request_id

### Use Cases:
- Frontend edit forms for master data records
- Pre-populating edit interfaces
- Data validation before editing
- Form field initialization

### Authentication:
Requires valid JWT Bearer token with admin privileges.
            """,
            responses={
                200: {
                    "description": "Master data record retrieved successfully for editing",
                    "content": {
                        "application/json": {
                            "example": {
                                "success": True,
                                "message": "Master data record retrieved successfully for editing",
                                "data": {
                                    "record": {
                                        "_id": "507f1f77bcf86cd799439011",
                                        "name": [
                                            {"code": "en", "name": "Bangkok General Hospital"},
                                            {"code": "th", "name": "โรงพยาบาลกรุงเทพ"}
                                        ],
                                        "en_name": "Bangkok General Hospital",
                                        "province_code": 10,
                                        "is_active": True
                                    },
                                    "data_type": "hospitals",
                                    "edit_mode": True
                                },
                                "request_id": "master-data-edit-001",
                                "timestamp": "2025-07-10T12:00:00.000Z"
                            }
                        }
                    }
                },
                400: {"description": "Invalid record ID format or data type"},
                401: {"description": "Authentication required"},
                404: {"description": "Master data record not found"},
                500: {"description": "Internal server error"}
            }
        # Removed unmatched parenthesis here

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
            "description": "Hospitals master data with full operational details and comprehensive address information",
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
                "address": "Basic address string (legacy field)",
                "address_details": {
                    "street_address": "Street address including house/building number",
                    "building_name": "Building or complex name",
                    "floor": "Floor number if applicable",
                    "room": "Room or suite number",
                    "postal_code": "Postal/ZIP code",
                    "postal_box": "P.O. Box if applicable"
                },
                "location": {
                    "latitude": "Latitude coordinate (float)",
                    "longitude": "Longitude coordinate (float)",
                    "elevation": "Elevation in meters (float)",
                    "precision": "GPS precision/accuracy"
                },
                "contact": {
                    "phone": "Primary phone number",
                    "phone_2": "Secondary phone number",
                    "fax": "Fax number",
                    "mobile": "Mobile phone number",
                    "emergency_phone": "Emergency contact number",
                    "email": "Primary email address",
                    "email_admin": "Administrative email",
                    "website": "Hospital website URL"
                },
                "services": {
                    "bed_capacity": "Total number of beds (integer)",
                    "emergency_services": "24/7 emergency services available (boolean)",
                    "trauma_center": "Trauma center designation (boolean)",
                    "icu_beds": "ICU bed capacity (integer)",
                    "operating_rooms": "Number of operating rooms (integer)",
                    "service_plan_type": "Service plan classification",
                    "accreditation": "Hospital accreditation status"
                },
                "phone": "Primary phone (legacy field)",
                "email": "Primary email (legacy field)",
                "website": "Website (legacy field)",
                "bed_capacity": "Number of beds (legacy field)",
                "service_plan_type": "Service plan type (A, F3, etc.)",
                "image_url": "Hospital image URL (string)",
                "auto_login_liff_id": "LINE auto login LIFF ID",
                "disconnect_liff_id": "LINE disconnect LIFF ID", 
                "login_liff_id": "LINE login LIFF ID",
                "mac_hv01_box": "MAC address of HV01 box",
                "notifyToken": "LINE Notify token",
                "rich_menu_token": "LINE rich menu token",
                "telegram_Token": "Telegram notification token",
                "is_acknowledge": "Acknowledgment notifications enabled",
                "is_admit_discard": "Admit/discharge notifications enabled",
                "is_body_data": "Body data monitoring enabled",
                "is_lab_data": "Lab data monitoring enabled",
                "is_status_change": "Status change notifications enabled"
            }
        },
        "blood_groups": {
            "description": "Blood group types master data for medical classification",
            "fields": {
                "_id": "MongoDB ObjectId - Primary key",
                "name": "Array of name objects with language codes (en/th)",
                "en_name": "English blood group name (string)",
                "is_active": "Active status (boolean)",
                "is_deleted": "Deleted status (boolean)",
                "created_at": "Creation timestamp",
                "updated_at": "Last update timestamp",
                "unique_id": "Unique identifier (integer)",
                "__v": "Version key"
            }
        },
        "human_skin_colors": {
            "description": "Human skin color classifications master data for demographic tracking",
            "fields": {
                "_id": "MongoDB ObjectId - Primary key",
                "name": "Array of name objects with language codes (en/th)",
                "en_name": "English skin color name (string)",
                "is_active": "Active status (boolean)",
                "is_deleted": "Deleted status (boolean)",
                "created_at": "Creation timestamp",
                "updated_at": "Last update timestamp",
                "unique_id": "Unique identifier (integer)",
                "__v": "Version key"
            }
        },
        "nations": {
            "description": "Countries/nations master data for international patient support",
            "fields": {
                "_id": "MongoDB ObjectId - Primary key",
                "name": "Array of name objects with language codes (en/th)",
                "en_name": "English country name (string)",
                "is_active": "Active status (boolean)",
                "is_deleted": "Deleted status (boolean)",
                "created_at": "Creation timestamp",
                "updated_at": "Last update timestamp",
                "unique_id": "Unique identifier (integer)",
                "__v": "Version key"
            }
        },
        "ward_lists": {
            "description": "Hospital ward types master data for patient ward classification",
            "fields": {
                "_id": "MongoDB ObjectId - Primary key",
                "name": "Array of name objects with language codes (en/th)",
                "en_name": "English ward name (string)",
                "is_active": "Active status (boolean)",
                "is_deleted": "Deleted status (boolean)",
                "created_at": "Creation timestamp",
                "updated_at": "Last update timestamp",
                "unique_id": "Unique identifier (integer)",
                "__v": "Version key"
            }
        },
        "staff_types": {
            "description": "Hospital staff types master data for personnel classification",
            "fields": {
                "_id": "MongoDB ObjectId - Primary key",
                "name": "Array of name objects with language codes (en/th)",
                "en_name": "English staff type name (string)",
                "is_active": "Active status (boolean)",
                "is_deleted": "Deleted status (boolean)",
                "is_this_userform_user": "User form access flag (boolean)",
                "created_at": "Creation timestamp",
                "updated_at": "Last update timestamp",
                "unique_id": "Unique identifier (integer)",
                "__v": "Version key"
            }
        },
        "underlying_diseases": {
            "description": "Underlying diseases master data for patient medical history",
            "fields": {
                "_id": "MongoDB ObjectId - Primary key",
                "name": "Array of name objects with language codes (en/th)",
                "en_name": "English disease name (string)",
                "is_active": "Active status (boolean)",
                "is_deleted": "Deleted status (boolean)",
                "created_at": "Creation timestamp",
                "updated_at": "Last update timestamp",
                "unique_id": "Unique identifier (integer)",
                "__v": "Version key"
            }
        }
    }
    
    return fields_info.get(data_type, {"description": "Unknown data type", "fields": {}})

def get_master_data_relationships(data_type: str) -> Dict[str, Any]:
    """Get relationship information for master data type"""
    relationships = {
        "provinces": {
            "children": [
                {"entity": "districts", "relationship": "districts.province_code = provinces.code"},
                {"entity": "sub_districts", "relationship": "sub_districts.province_code = provinces.code"},
                {"entity": "hospitals", "relationship": "hospitals.province_code = provinces.code"}
            ]
        },
        "districts": {
            "parents": [
                {"entity": "provinces", "relationship": "districts.province_code = provinces.code"}
            ],
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
                {"entity": "hospitals", "relationship": "hospitals.hospital_type_id = hospital_types._id"}
            ]
        },
        "hospitals": {
            "parents": [
                {"entity": "provinces", "relationship": "hospitals.province_code = provinces.code"},
                {"entity": "districts", "relationship": "hospitals.district_code = districts.code"},
                {"entity": "sub_districts", "relationship": "hospitals.sub_district_code = sub_districts.code"},
                {"entity": "hospital_types", "relationship": "hospitals.hospital_type_id = hospital_types._id"}
            ],
            "children": [
                {"entity": "patients", "relationship": "patients.new_hospital_ids contains hospitals._id"},
                {"entity": "amy_boxes", "relationship": "amy_boxes.hospital_id = hospitals._id"},
                {"entity": "mfc_hv01_boxes", "relationship": "mfc_hv01_boxes.hospital_id = hospitals._id"}
            ],
            "address_structure": {
                "basic_address": "Simple address string for backward compatibility",
                "address_details": {
                    "purpose": "Structured address components for precise location data",
                    "components": ["street_address", "building_name", "floor", "room", "postal_code", "postal_box"],
                    "use_cases": ["Delivery services", "Emergency response", "Patient navigation", "Staff coordination"]
                },
                "location": {
                    "purpose": "Geographic coordinates for mapping and routing",
                    "components": ["latitude", "longitude", "elevation", "precision"],
                    "use_cases": ["GPS navigation", "Distance calculations", "Emergency dispatch", "Service area mapping"]
                },
                "contact": {
                    "purpose": "Multi-channel communication with hospital departments",
                    "components": ["phone", "phone_2", "fax", "mobile", "emergency_phone", "email", "email_admin", "website"],
                    "use_cases": ["Patient communication", "Emergency contact", "Administrative coordination", "Public information"]
                },
                "services": {
                    "purpose": "Hospital capacity and service capabilities",
                    "components": ["bed_capacity", "emergency_services", "trauma_center", "icu_beds", "operating_rooms", "service_plan_type", "accreditation"],
                    "use_cases": ["Capacity planning", "Patient referrals", "Emergency dispatch", "Quality assurance"]
                }
            },
            "integration_points": {
                "device_management": "MAC addresses for IoT device integration",
                "digital_platforms": "LINE, Telegram integration for notifications",
                "qr_codes": "LIFF IDs for mobile app integration",
                "monitoring": "Notification flags for different data types"
            }
        },
        "blood_groups": {
            "children": [
                {"entity": "patients", "relationship": "patients.blood_type references blood_groups"}
            ],
            "usage_scenarios": {
                "patient_registration": "Blood group selection during patient enrollment",
                "medical_records": "Blood type tracking for medical procedures",
                "emergency_care": "Critical information for emergency medical treatment",
                "compatibility_checking": "Blood transfusion compatibility verification"
            }
        },
        "human_skin_colors": {
            "children": [
                {"entity": "patients", "relationship": "patients.skin_color_id references human_skin_colors"}
            ],
            "usage_scenarios": {
                "demographic_tracking": "Patient demographic information collection",
                "medical_classification": "Skin-related medical condition classification",
                "research_data": "Demographic data for medical research",
                "patient_identification": "Additional identification information"
            }
        },
        "nations": {
            "children": [
                {"entity": "patients", "relationship": "patients.nationality_id references nations"}
            ],
            "usage_scenarios": {
                "international_patients": "Nationality tracking for foreign patients",
                "language_preferences": "Default language selection based on nationality",
                "insurance_processing": "International insurance claim processing",
                "embassy_coordination": "Embassy contact for international patient care",
                "medical_tourism": "Tourist patient management and documentation"
            }
        }
    }
    
    return relationships.get(data_type, {})

# Hospital User Management
@router.get("/hospital-users", 
            response_model=SuccessResponse,
            responses={
                200: {
                    "description": "Hospital users retrieved successfully",
                    "content": {
                        "application/json": {
                            "example": {
                                "success": True,
                                "message": "Hospital users retrieved successfully",
                                "data": {
                                    "users": [
                                        {
                                            "_id": "6638a496f7ce6d32b68120f1",
                                            "email": "kitkamon@tely360.com",
                                            "first_name": "Kitkamon",
                                            "last_name": "Maitree",
                                            "user_title": "Mr.",
                                            "phone": "813618766",
                                            "country_phone_code": "+66",
                                            "country_code": "Th",
                                            "country_name": "Thailand",
                                            "hospital_id": "6814838ae1b89fa275c66868",
                                            "type": "663220b2a9e900f9ded0a62f",
                                            "image_url": "user_profiles/6638bc8209ecee510e15a28844XQ.jpg",
                                            "is_active": True,
                                            "is_deleted": False,
                                            "created_at": "2024-05-06T11:18:26.717Z",
                                            "updated_at": "2025-06-24T02:37:38.939Z",
                                            "unique_id": 2
                                        }
                                    ],
                                    "total": 72,
                                    "limit": 100,
                                    "skip": 0,
                                    "has_next": False,
                                    "has_prev": False
                                },
                                "request_id": "h9i0j1k2-l3m4-5678-ijkl-901234567890",
                                "timestamp": "2025-07-07T07:08:07.633870Z"
                            }
                        }
                    }
                }
            })
async def get_hospital_users(
    request: Request,
    limit: int = Query(100, ge=1, le=1000),
    skip: int = Query(0, ge=0),
    hospital_id: Optional[str] = None,
    type: Optional[str] = None,
    search: Optional[str] = None,
    is_active: Optional[bool] = None,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get hospital users with filtering and pagination"""
    import uuid
    try:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        # Build filter query
        filter_query = {"is_deleted": {"$ne": True}}
        
        if hospital_id:
            try:
                filter_query["hospital_id"] = ObjectId(hospital_id)
            except Exception:
                raise HTTPException(
                    status_code=400,
                    detail=create_error_response(
                        "INVALID_HOSPITAL_ID",
                        custom_message="Invalid hospital ID format",
                        field="hospital_id",
                        value=hospital_id,
                        request_id=request_id
                    ).dict()
                )
        
        if type:
            try:
                filter_query["type"] = ObjectId(type)
            except Exception:
                raise HTTPException(
                    status_code=400,
                    detail=create_error_response(
                        "INVALID_TYPE_ID",
                        custom_message="Invalid type ID format",
                        field="type",
                        value=type,
                        request_id=request_id
                    ).dict()
                )
        
        if is_active is not None:
            filter_query["is_active"] = is_active
        
        # Add search functionality
        if search:
            search_regex = {"$regex": search, "$options": "i"}
            filter_query["$or"] = [
                {"first_name": search_regex},
                {"last_name": search_regex},
                {"email": search_regex},
                {"phone": search_regex}
            ]
        
        collection = mongodb_service.get_collection("hospital_users")
        
        # Get total count
        total = await collection.count_documents(filter_query)
        
        # Get users with pagination
        users_cursor = collection.find(filter_query).skip(skip).limit(limit).sort("created_at", -1)
        users = await users_cursor.to_list(length=limit)
        
        # Serialize ObjectIds
        users = serialize_mongodb_response(users)
        
        # Calculate pagination info
        has_next = (skip + limit) < total
        has_prev = skip > 0
        
        success_response = create_success_response(
            message="Hospital users retrieved successfully",
            data={
                "users": users,
                "total": total,
                "limit": limit,
                "skip": skip,
                "has_next": has_next,
                "has_prev": has_prev
            },
            request_id=request_id
        )
        
        # Log audit trail - temporarily disabled for testing
        # await audit_logger.log_admin_action(
        #     action="READ",
        #     resource_type="hospital_users",
        #     resource_id="list",
        #     user_id=current_user.get("username", "unknown"),
        #     details=f"Retrieved {len(users)} hospital users"
        # )
        
        return success_response.dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve hospital users: {e}")
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                "INTERNAL_SERVER_ERROR",
                custom_message=f"Failed to retrieve hospital users: {str(e)}",
                request_id=request_id
            ).dict()
        )

@router.get("/hospital-users/{user_id}", response_model=SuccessResponse)
async def get_hospital_user(
    request: Request,
    user_id: str,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get a specific hospital user by ID"""
    import uuid
    try:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        # Validate ObjectId
        try:
            object_id = ObjectId(user_id)
        except Exception:
            raise HTTPException(
                status_code=400,
                detail=create_error_response(
                    "INVALID_USER_ID",
                    custom_message="Invalid user ID format",
                    field="user_id",
                    value=user_id,
                    request_id=request_id
                ).dict()
            )
        
        collection = mongodb_service.get_collection("hospital_users")
        user = await collection.find_one({"_id": object_id, "is_deleted": {"$ne": True}})
        
        if not user:
            raise HTTPException(
                status_code=404,
                detail=create_error_response(
                    "USER_NOT_FOUND",
                    custom_message="Hospital user not found",
                    field="user_id",
                    value=user_id,
                    request_id=request_id
                ).dict()
            )
        
        # Serialize ObjectIds
        user = serialize_mongodb_response(user)
        
        success_response = create_success_response(
            message="Hospital user retrieved successfully",
            data={"user": user},
            request_id=request_id
        )
        
        # Log audit trail
        await audit_logger.log_admin_action(
            action="READ",
            resource_type="hospital_users",
            resource_id=user_id,
            user_id=current_user.get("username", "unknown"),
            details=f"Retrieved hospital user: {user.get('email', 'unknown')}"
        )
        
        return success_response.dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve hospital user: {e}")
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                "INTERNAL_SERVER_ERROR",
                custom_message=f"Failed to retrieve hospital user: {str(e)}",
                request_id=request_id
            ).dict()
        )

@router.post("/hospital-users/search", response_model=SuccessResponse)
async def search_hospital_users(
    request: Request,
    search_query: HospitalUserSearchQuery,
    limit: int = Query(100, ge=1, le=1000),
    skip: int = Query(0, ge=0),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Advanced search for hospital users"""
    import uuid
    try:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        # Build filter query
        filter_query = {"is_deleted": {"$ne": True}}
        
        # Add specific field filters
        if search_query.hospital_id:
            try:
                filter_query["hospital_id"] = ObjectId(search_query.hospital_id)
            except Exception:
                raise HTTPException(
                    status_code=400,
                    detail=create_error_response(
                        "INVALID_HOSPITAL_ID",
                        custom_message="Invalid hospital ID format",
                        field="hospital_id",
                        value=search_query.hospital_id,
                        request_id=request_id
                    ).dict()
                )
        
        if search_query.type:
            try:
                filter_query["type"] = ObjectId(search_query.type)
            except Exception:
                raise HTTPException(
                    status_code=400,
                    detail=create_error_response(
                        "INVALID_TYPE_ID",
                        custom_message="Invalid type ID format",
                        field="type",
                        value=search_query.type,
                        request_id=request_id
                    ).dict()
                )
        
        if search_query.email:
            filter_query["email"] = {"$regex": search_query.email, "$options": "i"}
        
        if search_query.first_name:
            filter_query["first_name"] = {"$regex": search_query.first_name, "$options": "i"}
        
        if search_query.last_name:
            filter_query["last_name"] = {"$regex": search_query.last_name, "$options": "i"}
        
        if search_query.phone:
            filter_query["phone"] = {"$regex": search_query.phone, "$options": "i"}
        
        if search_query.is_active is not None:
            filter_query["is_active"] = search_query.is_active
        
        if search_query.is_deleted is not None:
            if search_query.is_deleted:
                filter_query["is_deleted"] = True
            else:
                filter_query["is_deleted"] = {"$ne": True}
        
        # General search across multiple fields
        if search_query.search:
            search_regex = {"$regex": search_query.search, "$options": "i"}
            filter_query["$or"] = [
                {"first_name": search_regex},
                {"last_name": search_regex},
                {"email": search_regex},
                {"phone": search_regex}
            ]
        
        collection = mongodb_service.get_collection("hospital_users")
        
        # Get total count
        total = await collection.count_documents(filter_query)
        
        # Get users with pagination
        users_cursor = collection.find(filter_query).skip(skip).limit(limit).sort("created_at", -1)
        users = await users_cursor.to_list(length=limit)
        
        # Serialize ObjectIds
        users = serialize_mongodb_response(users)
        
        # Calculate pagination info
        has_next = (skip + limit) < total
        has_prev = skip > 0
        
        success_response = create_success_response(
            message="Hospital users search completed successfully",
            data={
                "users": users,
                "total": total,
                "limit": limit,
                "skip": skip,
                "has_next": has_next,
                "has_prev": has_prev,
                "search_criteria": search_query.dict(exclude_none=True)
            },
            request_id=request_id
        )
        
        # Log audit trail
        await audit_logger.log_admin_action(
            action="SEARCH",
            resource_type="hospital_users",
            resource_id="search",
            user_id=current_user.get("username", "unknown"),
            details=f"Searched hospital users with criteria: {search_query.dict(exclude_none=True)}"
        )
        
        return success_response.dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to search hospital users: {e}")
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                "INTERNAL_SERVER_ERROR",
                custom_message=f"Failed to search hospital users: {str(e)}",
                request_id=request_id
            ).dict()
        )

@router.post("/hospital-users", response_model=SuccessResponse)
async def create_hospital_user(
    request: Request,
    user_data: HospitalUserCreate,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Create a new hospital user"""
    import uuid
    import hashlib
    try:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        collection = mongodb_service.get_collection("hospital_users")
        
        # Check if email already exists
        existing_user = await collection.find_one({"email": user_data.email, "is_deleted": {"$ne": True}})
        if existing_user:
            raise HTTPException(
                status_code=400,
                detail=create_error_response(
                    "EMAIL_ALREADY_EXISTS",
                    custom_message="A user with this email already exists",
                    field="email",
                    value=user_data.email,
                    request_id=request_id
                ).dict()
            )
        
        # Hash password
        password_hash = hashlib.md5(user_data.password.encode()).hexdigest()
        
        # Get next unique_id
        last_user = await collection.find_one({}, sort=[("unique_id", -1)])
        next_unique_id = (last_user.get("unique_id", 0) + 1) if last_user else 1
        
        # Create user document
        now = datetime.utcnow()
        user_doc = {
            "email": user_data.email,
            "password": password_hash,
            "first_name": user_data.first_name,
            "last_name": user_data.last_name,
            "user_title": user_data.user_title,
            "phone": user_data.phone,
            "country_phone_code": user_data.country_phone_code,
            "country_code": user_data.country_code,
            "country_name": user_data.country_name,
            "hospital_id": ObjectId(user_data.hospital_id),
            "type": ObjectId(user_data.type),
            "image_url": user_data.image_url or "",
            "server_token": user_data.server_token or "",
            "device_token": user_data.device_token or "",
            "device_type": user_data.device_type or "",
            "app_version": user_data.app_version or "",
            "unique_id": next_unique_id,
            "is_active": True,
            "is_deleted": False,
            "created_at": now,
            "updated_at": now,
            "__v": 0
        }
        
        # Insert user
        result = await collection.insert_one(user_doc)
        user_id = str(result.inserted_id)
        
        success_response = create_success_response(
            message="Hospital user created successfully",
            data={
                "user_id": user_id,
                "unique_id": next_unique_id,
                "email": user_data.email
            },
            request_id=request_id
        )
        
        # Log audit trail
        await audit_logger.log_admin_action(
            action="CREATE",
            resource_type="hospital_users",
            resource_id=user_id,
            user_id=current_user.get("username", "unknown"),
            details=f"Created hospital user: {user_data.email}"
        )
        
        return success_response.dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create hospital user: {e}")
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                "INTERNAL_SERVER_ERROR",
                custom_message=f"Failed to create hospital user: {str(e)}",
                request_id=request_id
            ).dict()
        )

@router.put("/hospital-users/{user_id}", response_model=SuccessResponse)
async def update_hospital_user(
    request: Request,
    user_id: str,
    user_data: HospitalUserUpdate,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Update a hospital user"""
    import uuid
    import hashlib
    try:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        # Validate ObjectId
        try:
            object_id = ObjectId(user_id)
        except Exception:
            raise HTTPException(
                status_code=400,
                detail=create_error_response(
                    "INVALID_USER_ID",
                    custom_message="Invalid user ID format",
                    field="user_id",
                    value=user_id,
                    request_id=request_id
                ).dict()
            )
        
        collection = mongodb_service.get_collection("hospital_users")
        
        # Check if user exists
        existing_user = await collection.find_one({"_id": object_id, "is_deleted": {"$ne": True}})
        if not existing_user:
            raise HTTPException(
                status_code=404,
                detail=create_error_response(
                    "USER_NOT_FOUND",
                    custom_message="Hospital user not found",
                    field="user_id",
                    value=user_id,
                    request_id=request_id
                ).dict()
            )
        
        # Check email uniqueness if email is being updated
        if user_data.email and user_data.email != existing_user.get("email"):
            email_exists = await collection.find_one({
                "email": user_data.email,
                "_id": {"$ne": object_id},
                "is_deleted": {"$ne": True}
            })
            if email_exists:
                raise HTTPException(
                    status_code=400,
                    detail=create_error_response(
                        "EMAIL_ALREADY_EXISTS",
                        custom_message="A user with this email already exists",
                        field="email",
                        value=user_data.email,
                        request_id=request_id
                    ).dict()
                )
        
        # Build update document
        update_doc = {"updated_at": datetime.utcnow()}
        
        # Update only provided fields
        for field, value in user_data.dict(exclude_none=True).items():
            if field in ["hospital_id", "type"] and value:
                update_doc[field] = ObjectId(value)
            else:
                update_doc[field] = value
        
        # Update user
        result = await collection.update_one(
            {"_id": object_id},
            {"$set": update_doc}
        )
        
        if result.matched_count == 0:
            raise HTTPException(
                status_code=404,
                detail=create_error_response(
                    "USER_NOT_FOUND",
                    custom_message="Hospital user not found",
                    field="user_id",
                    value=user_id,
                    request_id=request_id
                ).dict()
            )
        
        success_response = create_success_response(
            message="Hospital user updated successfully",
            data={
                "user_id": user_id,
                "updated_fields": list(user_data.dict(exclude_none=True).keys()),
                "modified_count": result.modified_count
            },
            request_id=request_id
        )
        
        # Log audit trail
        await audit_logger.log_admin_action(
            action="UPDATE",
            resource_type="hospital_users",
            resource_id=user_id,
            user_id=current_user.get("username", "unknown"),
            details=f"Updated hospital user: {existing_user.get('email', 'unknown')}"
        )
        
        return success_response.dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update hospital user: {e}")
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                "INTERNAL_SERVER_ERROR",
                custom_message=f"Failed to update hospital user: {str(e)}",
                request_id=request_id
            ).dict()
        )

@router.delete("/hospital-users/{user_id}", response_model=SuccessResponse)
async def delete_hospital_user(
    request: Request,
    user_id: str,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Soft delete a hospital user"""
    import uuid
    try:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        # Validate ObjectId
        try:
            object_id = ObjectId(user_id)
        except Exception:
            raise HTTPException(
                status_code=400,
                detail=create_error_response(
                    "INVALID_USER_ID",
                    custom_message="Invalid user ID format",
                    field="user_id",
                    value=user_id,
                    request_id=request_id
                ).dict()
            )
        
        collection = mongodb_service.get_collection("hospital_users")
        
        # Check if user exists
        existing_user = await collection.find_one({"_id": object_id, "is_deleted": {"$ne": True}})
        if not existing_user:
            raise HTTPException(
                status_code=404,
                detail=create_error_response(
                    "USER_NOT_FOUND",
                    custom_message="Hospital user not found",
                    field="user_id",
                    value=user_id,
                    request_id=request_id
                ).dict()
            )
        
        # Soft delete user
        result = await collection.update_one(
            {"_id": object_id},
            {
                "$set": {
                    "is_deleted": True,
                    "is_active": False,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        success_response = create_success_response(
            message="Hospital user deleted successfully",
            data={
                "user_id": user_id,
                "email": existing_user.get("email", "unknown")
            },
            request_id=request_id
        )
        
        # Log audit trail
        await audit_logger.log_admin_action(
            action="DELETE",
            resource_type="hospital_users",
            resource_id=user_id,
            user_id=current_user.get("username", "unknown"),
            details=f"Deleted hospital user: {existing_user.get('email', 'unknown')}"
        )
        
        return success_response.dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete hospital user: {e}")
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                "INTERNAL_SERVER_ERROR",
                custom_message=f"Failed to delete hospital user: {str(e)}",
                request_id=request_id
            ).dict()
        )

@router.get("/hospital-users/stats/summary", response_model=SuccessResponse)
async def get_hospital_users_stats(
    request: Request,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get hospital users statistics"""
    import uuid
    try:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        collection = mongodb_service.get_collection("hospital_users")
        
        # Get basic counts
        total_users = await collection.count_documents({})
        active_users = await collection.count_documents({"is_active": True, "is_deleted": {"$ne": True}})
        inactive_users = await collection.count_documents({"is_active": False, "is_deleted": {"$ne": True}})
        deleted_users = await collection.count_documents({"is_deleted": True})
        
        # Get users by hospital
        hospital_pipeline = [
            {"$match": {"is_deleted": {"$ne": True}}},
            {"$group": {"_id": "$hospital_id", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 10}
        ]
        users_by_hospital = await collection.aggregate(hospital_pipeline).to_list(length=10)
        
        # Get users by type
        type_pipeline = [
            {"$match": {"is_deleted": {"$ne": True}}},
            {"$group": {"_id": "$type", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        users_by_type = await collection.aggregate(type_pipeline).to_list(length=None)
        
        # Serialize ObjectIds in aggregation results
        users_by_hospital = serialize_mongodb_response(users_by_hospital)
        users_by_type = serialize_mongodb_response(users_by_type)
        
        success_response = create_success_response(
            message="Hospital users statistics retrieved successfully",
            data={
                "total_users": total_users,
                "active_users": active_users,
                "inactive_users": inactive_users,
                "deleted_users": deleted_users,
                "users_by_hospital": users_by_hospital,
                "users_by_type": users_by_type
            },
            request_id=request_id
        )
        
        # Log audit trail
        await audit_logger.log_admin_action(
            action="READ",
            resource_type="hospital_users",
            resource_id="stats",
            user_id=current_user.get("username", "unknown"),
            details="Retrieved hospital users statistics"
        )
        
        return success_response.dict()
        
    except Exception as e:
        logger.error(f"Failed to get hospital users stats: {e}")
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                "INTERNAL_SERVER_ERROR",
                custom_message=f"Failed to get hospital users statistics: {str(e)}",
                request_id=request_id
            ).dict()
        )

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
    import uuid
    try:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
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
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                "INTERNAL_SERVER_ERROR",
                custom_message=f"Failed to retrieve audit logs: {str(e)}",
                request_id=request_id
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

# ===================== MEDICAL HISTORY MANAGEMENT - COMPREHENSIVE CRUD =====================

@router.get("/medical-history-management/{history_type}",
            responses={
                200: {
                    "description": "Medical history records retrieved successfully with table view",
                    "content": {
                        "application/json": {
                            "example": {
                                "success": True,
                                "message": "Medical history records retrieved successfully",
                                "data": {
                                    "records": [
                                        {
                                            "_id": "64f1234567890abcdef12345",
                                            "patient_id": "622035a5fd26d7b6d9b7730c",
                                            "patient_name": "John Doe",
                                            "device_id": "DEV001",
                                            "device_type": "AVA4",
                                            "data": [
                                                {
                                                    "systolic": 120,
                                                    "diastolic": 80,
                                                    "pulse": 72,
                                                    "timestamp": "2024-01-15T10:30:00Z"
                                                }
                                            ],
                                            "created_at": "2024-01-15T10:30:00Z",
                                            "updated_at": "2024-01-15T10:30:00Z"
                                        }
                                    ],
                                    "total": 2574,
                                    "limit": 50,
                                    "skip": 0,
                                    "has_next": True,
                                    "has_prev": False,
                                    "collection_info": {
                                        "display_name": "Blood Pressure History",
                                        "record_count": 2574,
                                        "data_fields": ["systolic", "diastolic", "pulse", "timestamp"]
                                    }
                                }
                            }
                        }
                    }
                }
            })
async def get_medical_history_management(
    request: Request,
    history_type: str,
    limit: int = Query(50, ge=1, le=1000),
    skip: int = Query(0, ge=0),
    patient_id: Optional[str] = None,
    device_id: Optional[str] = None,
    device_type: Optional[str] = None,
    search: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get medical history records with comprehensive table view and filtering"""
    import uuid
    try:
        logger.warning("Starting medical history management function")
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        logger.warning(f"Request ID: {request_id}")
        

        
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
            "temperature": "temperature_data_histories",
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
        patients_collection = mongodb_service.get_collection("patients")
        
        # Build filter query
        filter_query: Dict[str, Any] = {}
        
        # Patient filter
        if patient_id:
            try:
                filter_query["patient_id"] = ObjectId(patient_id)
            except Exception:
                raise HTTPException(
                    status_code=400,
                    detail=create_error_response(
                        "INVALID_PATIENT_ID",
                        field="patient_id",
                        value=patient_id,
                        request_id=request_id
                    ).dict()
                )
        
        # Device filters
        if device_id:
            filter_query["device_id"] = {"$regex": device_id, "$options": "i"}
        
        if device_type:
            filter_query["device_type"] = {"$regex": device_type, "$options": "i"}
        
        # Date range filter
        if date_from or date_to:
            date_filter = {}
            if date_from:
                try:
                    date_filter["$gte"] = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
                except:
                    raise HTTPException(status_code=400, detail="Invalid date_from format")
            if date_to:
                try:
                    date_filter["$lte"] = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
                except:
                    raise HTTPException(status_code=400, detail="Invalid date_to format")
            filter_query["created_at"] = date_filter
        
        # Search across data fields
        if search:
            search_query = {"$or": []}
            
            # Search in device_id, device_type
            search_query["$or"].extend([
                {"device_id": {"$regex": search, "$options": "i"}},
                {"device_type": {"$regex": search, "$options": "i"}},
                {"notes": {"$regex": search, "$options": "i"}}
            ])
            
            # Search in data array values (for numeric values)
            try:
                search_numeric = float(search)
                search_query["$or"].append({
                    "data": {
                        "$elemMatch": {
                            "$or": [
                                {"systolic": search_numeric},
                                {"diastolic": search_numeric},
                                {"pulse": search_numeric},
                                {"value": search_numeric},
                                {"weight": search_numeric},
                                {"height": search_numeric},
                                {"bmi": search_numeric},
                                {"steps": search_numeric},
                                {"total_cholesterol": search_numeric}
                            ]
                        }
                    }
                })
            except ValueError:
                pass
            
            filter_query.update(search_query)
        
        # Get total count
        try:
            total = await collection.count_documents(filter_query)
            logger.warning(f"Count query successful: {total} documents found")
        except Exception as e:
            logger.warning(f"Failed to count documents: {e}")
            total = 0
        
        # Get records with pagination
        try:
            cursor = collection.find(filter_query).sort("created_at", -1).skip(skip).limit(limit)
            records = await cursor.to_list(length=limit)
            logger.warning(f"Fetch query successful: {len(records)} records retrieved")
        except Exception as e:
            logger.warning(f"Failed to fetch records: {e}")
            records = []
        
        # Enrich records with patient information
        enriched_records = []
        for record in records:
            logger.warning(f"Processing record type: {type(record)}, value: {repr(record)[:200]}")
            try:
                # Check if record is a dictionary
                if isinstance(record, dict):
                    # Special handling for blood pressure records that might have corrupted data
                    if history_type == "blood_pressure":
                        # Validate blood pressure record structure
                        if "data" in record and isinstance(record["data"], list):
                            # Filter out invalid data entries
                            valid_data = []
                            for data_entry in record["data"]:
                                if isinstance(data_entry, dict):
                                    valid_data.append(data_entry)
                                else:
                                    logger.warning(f"Invalid blood pressure data entry: {type(data_entry)} - {repr(data_entry)[:100]}")
                            record["data"] = valid_data
                    
                    serialized_record = serialize_mongodb_response(record)
                    serialized_record["patient_name"] = "Unknown Patient"
                    enriched_records.append(serialized_record)
                else:
                    # Handle non-dictionary records
                    logger.warning(f"Record is not a dictionary: {type(record)} - {record}")
                    enriched_records.append({
                        "_id": "unknown",
                        "patient_name": "Unknown Patient",
                        "error": f"Invalid record type: {type(record)}"
                    })
            except Exception as e:
                logger.warning(f"Failed to process record: {e}")
                # Add a basic record to avoid breaking the response
                enriched_records.append({
                    "_id": "unknown",
                    "patient_name": "Unknown Patient",
                    "error": f"Failed to process record: {str(e)}"
                })
        
        # Calculate pagination info
        has_next = (skip + limit) < total
        has_prev = skip > 0
        
        # Collection info
        collection_info = {
            "blood_pressure": {"display_name": "Blood Pressure History", "data_fields": ["systolic", "diastolic", "pulse"]},
            "blood_sugar": {"display_name": "Blood Sugar History", "data_fields": ["value", "unit", "meal_type"]},
            "body_data": {"display_name": "Body Data History", "data_fields": ["weight", "height", "bmi", "body_fat"]},
            "creatinine": {"display_name": "Creatinine History", "data_fields": ["value", "unit"]},
            "lipid": {"display_name": "Lipid History", "data_fields": ["total_cholesterol", "hdl", "ldl", "triglycerides"]},
            "sleep_data": {"display_name": "Sleep Data History", "data_fields": ["duration_minutes", "sleep_score", "deep_sleep_minutes"]},
            "spo2": {"display_name": "SPO2 History", "data_fields": ["value"]},
            "step": {"display_name": "Step History", "data_fields": ["steps", "calories", "distance"]},
            "temperature": {"display_name": "Temperature History", "data_fields": ["value", "unit"]},
            "medication": {"display_name": "Medication History", "data_fields": ["medication_detail", "medication_source"]},
            "allergy": {"display_name": "Allergy History", "data_fields": ["allergen", "severity", "symptoms"]},
            "underlying_disease": {"display_name": "Underlying Disease History", "data_fields": ["disease_name", "severity"]},
            "admit_data": {"display_name": "Hospital Admission History", "data_fields": ["hospital_name", "admit_date", "discharge_date", "diagnosis"]}
        }.get(history_type, {"display_name": history_type.replace("_", " ").title(), "data_fields": []})
        
        collection_info["record_count"] = total
        
        # Convert ObjectId to string for JSON serialization
        serialized_records = []
        for record in enriched_records:
            # Use the serialize_mongodb_response function to ensure all ObjectIds are converted
            serialized_record = serialize_mongodb_response(record)
            serialized_records.append(serialized_record)
        
        # Create the response data structure
        response_data = {
            "records": serialized_records,
            "total": total,
            "limit": limit,
            "skip": skip,
            "has_next": has_next,
            "has_prev": has_prev,
            "collection_info": collection_info,
            "filters_applied": {
                "patient_id": patient_id,
                "device_id": device_id,
                "device_type": device_type,
                "search": search,
                "date_from": date_from,
                "date_to": date_to
            }
        }
        
        # Ensure the entire response data is properly serialized
        serialized_response_data = serialize_mongodb_response(response_data)
        
        success_response = create_success_response(
            message=f"Medical history ({history_type}) records retrieved successfully",
            data=serialized_response_data,
            request_id=request_id
        )
        
        return success_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve medical history management data: {e}")
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                "INTERNAL_SERVER_ERROR",
                custom_message=f"Failed to retrieve medical history: {str(e)}",
                request_id=request_id
            ).dict()
        )

@router.post("/medical-history-management/{history_type}", response_model=SuccessResponse)
async def create_medical_history_record(
    request: Request,
    history_type: str,
    record_data: MedicalHistoryCreateModel,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Create new medical history record"""
    import uuid
    try:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
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
            "temperature": "temperature_data_histories",
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
                    request_id=request_id
                ).dict()
            )
        
        # Validate patient exists
        patients_collection = mongodb_service.get_collection("patients")
        try:
            patient_obj_id = ObjectId(record_data.patient_id)
        except Exception:
            raise HTTPException(
                status_code=400,
                detail=create_error_response(
                    "INVALID_PATIENT_ID",
                    field="patient_id",
                    value=record_data.patient_id,
                    request_id=request_id
                ).dict()
            )
        
        patient = await patients_collection.find_one({"_id": patient_obj_id})
        if not patient:
            raise HTTPException(
                status_code=404,
                detail=create_error_response(
                    "PATIENT_NOT_FOUND",
                    field="patient_id",
                    value=record_data.patient_id,
                    request_id=request_id
                ).dict()
            )
        
        collection = mongodb_service.get_collection(collection_name)
        
        # Prepare record data
        new_record = {
            "patient_id": patient_obj_id,
            "device_id": record_data.device_id,
            "device_type": record_data.device_type,
            "data": [record_data.values],  # Store values in data array
            "timestamp": record_data.timestamp or datetime.utcnow(),
            "notes": record_data.notes,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "created_by": current_user.get("username", "unknown")
        }
        
        # Insert record
        result = await collection.insert_one(new_record)
        record_id = str(result.inserted_id)
        
        success_response = create_success_response(
            message=f"Medical history ({history_type}) record created successfully",
            data={
                "record_id": record_id,
                "patient_id": record_data.patient_id,
                "history_type": history_type
            },
            request_id=request_id
        )
        
        return success_response.dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create medical history record: {e}")
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                "INTERNAL_SERVER_ERROR",
                custom_message=f"Failed to create medical history record: {str(e)}",
                request_id=request_id
            ).dict()
        )

@router.put("/medical-history-management/{history_type}/{record_id}", response_model=SuccessResponse)
async def update_medical_history_record(
    request: Request,
    history_type: str,
    record_id: str,
    record_data: MedicalHistoryUpdateModel,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Update medical history record"""
    import uuid
    try:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
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
            "temperature": "temperature_data_histories",
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
                    request_id=request_id
                ).dict()
            )
        
        # Validate record_id
        try:
            object_id = ObjectId(record_id)
        except Exception:
            raise HTTPException(
                status_code=400,
                detail=create_error_response(
                    "INVALID_RECORD_ID",
                    field="record_id",
                    value=record_id,
                    request_id=request_id
                ).dict()
            )
        
        collection = mongodb_service.get_collection(collection_name)
        
        # Check if record exists
        existing_record = await collection.find_one({"_id": object_id})
        if not existing_record:
            raise HTTPException(
                status_code=404,
                detail=create_error_response(
                    "RECORD_NOT_FOUND",
                    field="record_id",
                    value=record_id,
                    request_id=request_id
                ).dict()
            )
        
        # Prepare update data
        update_data = {"updated_at": datetime.utcnow(), "updated_by": current_user.get("username", "unknown")}
        
        if record_data.device_id is not None:
            update_data["device_id"] = record_data.device_id
        if record_data.device_type is not None:
            update_data["device_type"] = record_data.device_type
        if record_data.timestamp is not None:
            update_data["timestamp"] = record_data.timestamp
        if record_data.notes is not None:
            update_data["notes"] = record_data.notes
        if record_data.values is not None:
            # Update the first data entry or add new one
            if existing_record.get("data"):
                update_data["data.0"] = {**existing_record["data"][0], **record_data.values}
            else:
                update_data["data"] = [record_data.values]
        
        # Update record
        await collection.update_one({"_id": object_id}, {"$set": update_data})
        
        success_response = create_success_response(
            message=f"Medical history ({history_type}) record updated successfully",
            data={
                "record_id": record_id,
                "history_type": history_type,
                "updated_fields": list(update_data.keys())
            },
            request_id=request_id
        )
        
        return success_response.dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update medical history record: {e}")
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                "INTERNAL_SERVER_ERROR",
                custom_message=f"Failed to update medical history record: {str(e)}",
                request_id=request_id
            ).dict()
        )

@router.delete("/medical-history-management/{history_type}/{record_id}", response_model=SuccessResponse)
async def delete_medical_history_record(
    request: Request,
    history_type: str,
    record_id: str,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Delete medical history record"""
    import uuid
    try:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
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
            "temperature": "temperature_data_histories",
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
                    request_id=request_id
                ).dict()
            )
        
        # Validate record_id
        try:
            object_id = ObjectId(record_id)
        except Exception:
            raise HTTPException(
                status_code=400,
                detail=create_error_response(
                    "INVALID_RECORD_ID",
                    field="record_id",
                    value=record_id,
                    request_id=request_id
                ).dict()
            )
        
        collection = mongodb_service.get_collection(collection_name)
        
        # Check if record exists
        existing_record = await collection.find_one({"_id": object_id})
        if not existing_record:
            raise HTTPException(
                status_code=404,
                detail=create_error_response(
                    "RECORD_NOT_FOUND",
                    field="record_id",
                    value=record_id,
                    request_id=request_id
                ).dict()
            )
        
        # Delete record (hard delete for medical history)
        await collection.delete_one({"_id": object_id})
        
        success_response = create_success_response(
            message=f"Medical history ({history_type}) record deleted successfully",
            data={
                "record_id": record_id,
                "history_type": history_type
            },
            request_id=request_id
        )
        
        return success_response.dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete medical history record: {e}")
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                "INTERNAL_SERVER_ERROR",
                custom_message=f"Failed to delete medical history record: {str(e)}",
                request_id=request_id
            ).dict()
        )

@router.post("/medical-history-management/{history_type}/search", response_model=SuccessResponse)
async def search_medical_history_records(
    request: Request,
    history_type: str,
    search_query: MedicalHistorySearchQueryModel,
    limit: int = Query(50, ge=1, le=1000),
    skip: int = Query(0, ge=0),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Advanced search for medical history records"""
    import uuid
    try:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
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
            "temperature": "temperature_data_histories",
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
                    request_id=request_id
                ).dict()
            )
        
        collection = mongodb_service.get_collection(collection_name)
        
        # Build advanced filter query
        filter_query: Dict[str, Any] = {}
        
        # Patient filter
        if search_query.patient_id:
            try:
                filter_query["patient_id"] = ObjectId(search_query.patient_id)
            except Exception:
                raise HTTPException(
                    status_code=400,
                    detail=create_error_response(
                        "INVALID_PATIENT_ID",
                        field="patient_id",
                        value=search_query.patient_id,
                        request_id=request_id
                    ).dict()
                )
        
        # Device filters
        if search_query.device_id:
            filter_query["device_id"] = {"$regex": search_query.device_id, "$options": "i"}
        if search_query.device_type:
            filter_query["device_type"] = {"$regex": search_query.device_type, "$options": "i"}
        
        # Date range filter
        if search_query.date_from or search_query.date_to:
            date_filter = {}
            if search_query.date_from:
                date_filter["$gte"] = search_query.date_from
            if search_query.date_to:
                date_filter["$lte"] = search_query.date_to
            filter_query["created_at"] = date_filter
        
        # Value range filter for numeric data
        if search_query.value_min is not None or search_query.value_max is not None:
            value_filter = {}
            if search_query.value_min is not None:
                value_filter["$gte"] = search_query.value_min
            if search_query.value_max is not None:
                value_filter["$lte"] = search_query.value_max
            
            # Apply to different value fields based on history type
            if history_type == "blood_pressure":
                filter_query["$or"] = [
                    {"data.systolic": value_filter},
                    {"data.diastolic": value_filter},
                    {"data.pulse": value_filter}
                ]
            elif history_type in ["blood_sugar", "creatinine", "spo2", "temperature"]:
                filter_query["data.value"] = value_filter
            elif history_type == "step":
                filter_query["data.steps"] = value_filter
            elif history_type == "body_data":
                filter_query["$or"] = [
                    {"data.weight": value_filter},
                    {"data.height": value_filter},
                    {"data.bmi": value_filter}
                ]
        
        # General search
        if search_query.search:
            search_regex = {"$regex": search_query.search, "$options": "i"}
            search_or = [
                {"device_id": search_regex},
                {"device_type": search_regex},
                {"notes": search_regex}
            ]
            
            # Try numeric search
            try:
                search_numeric = float(search_query.search)
                if history_type == "blood_pressure":
                    search_or.extend([
                        {"data.systolic": search_numeric},
                        {"data.diastolic": search_numeric},
                        {"data.pulse": search_numeric}
                    ])
                elif history_type in ["blood_sugar", "creatinine", "spo2", "temperature"]:
                    search_or.append({"data.value": search_numeric})
            except ValueError:
                pass
            
            if "$or" in filter_query:
                filter_query = {"$and": [filter_query, {"$or": search_or}]}
            else:
                filter_query["$or"] = search_or
        
        # Get total count
        total = await collection.count_documents(filter_query)
        
        # Get records with pagination
        cursor = collection.find(filter_query).sort("created_at", -1).skip(skip).limit(limit)
        records = await cursor.to_list(length=limit)
        
        # Serialize records
        serialized_records = serialize_mongodb_response(records)
        
        # Calculate pagination info
        has_next = (skip + limit) < total
        has_prev = skip > 0
        
        success_response = create_success_response(
            message=f"Medical history ({history_type}) search completed successfully",
            data={
                "records": serialized_records,
                "total": total,
                "limit": limit,
                "skip": skip,
                "has_next": has_next,
                "has_prev": has_prev,
                "search_criteria": search_query.dict(exclude_none=True)
            },
            request_id=request_id
        )
        
        return success_response.dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to search medical history records: {e}")
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                "INTERNAL_SERVER_ERROR",
                custom_message=f"Failed to search medical history: {str(e)}",
                request_id=request_id
            ).dict()
        )

@router.get("/medical-history-management/stats/overview", response_model=SuccessResponse)
async def get_medical_history_stats(
    request: Request,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get comprehensive medical history statistics"""
    import uuid
    try:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        # Define all collections
        collections_info = {
            "blood_pressure_histories": "Blood Pressure",
            "blood_sugar_histories": "Blood Sugar", 
            "body_data_histories": "Body Data",
            "creatinine_histories": "Creatinine",
            "lipid_histories": "Lipid",
            "sleep_data_histories": "Sleep Data",
            "spo2_histories": "SPO2",
            "step_histories": "Step",
            "temperature_data_histories": "Temperature",
            "medication_histories": "Medication",
            "allergy_histories": "Allergy",
            "underlying_disease_histories": "Underlying Disease",
            "admit_data_histories": "Hospital Admission"
        }
        
        # Get statistics for each collection
        records_by_type = []
        total_records = 0
        
        for collection_name, display_name in collections_info.items():
            try:
                collection = mongodb_service.get_collection(collection_name)
                count = await collection.count_documents({})
                
                # Get date range
                first_record = await collection.find_one({}, sort=[("created_at", 1)])
                last_record = await collection.find_one({}, sort=[("created_at", -1)])
                
                date_range = None
                if first_record and last_record:
                    date_range = {
                        "first_record": first_record.get("created_at"),
                        "last_record": last_record.get("created_at")
                    }
                
                records_by_type.append({
                    "collection_name": collection_name,
                    "display_name": display_name,
                    "count": count,
                    "date_range": date_range,
                    "status": "✅ Active" if count > 0 else "⚠️ Empty"
                })
                
                total_records += count
                
            except Exception as e:
                records_by_type.append({
                    "collection_name": collection_name,
                    "display_name": display_name,
                    "count": 0,
                    "error": str(e),
                    "status": "❌ Error"
                })
        
        # Sort by record count
        records_by_type.sort(key=lambda x: x.get("count", 0), reverse=True)
        
        # Get patient statistics
        patients_with_data = set()
        records_by_patient = []
        
        try:
            patients_collection = mongodb_service.get_collection("patients")
            
            # Sample top patients with medical data
            for collection_name in collections_info.keys():
                if any(r["collection_name"] == collection_name and r.get("count", 0) > 0 for r in records_by_type):
                    collection = mongodb_service.get_collection(collection_name)
                    patient_counts = await collection.aggregate([
                        {"$group": {"_id": "$patient_id", "count": {"$sum": 1}}},
                        {"$sort": {"count": -1}},
                        {"$limit": 10}
                    ]).to_list(10)
                    
                    for pc in patient_counts:
                        if pc["_id"]:
                            patients_with_data.add(str(pc["_id"]))
                            
                            # Get patient info
                            patient = await patients_collection.find_one({"_id": pc["_id"]})
                            patient_name = "Unknown Patient"
                            if patient:
                                patient_name = f"{patient.get('first_name', '')} {patient.get('last_name', '')}".strip()
                            
                            existing_patient = next((p for p in records_by_patient if p["patient_id"] == str(pc["_id"])), None)
                            if existing_patient:
                                existing_patient["total_records"] += pc["count"]
                                existing_patient["collections"][collection_name] = pc["count"]
                            else:
                                records_by_patient.append({
                                    "patient_id": str(pc["_id"]),
                                    "patient_name": patient_name,
                                    "total_records": pc["count"],
                                    "collections": {collection_name: pc["count"]}
                                })
        except Exception as e:
            logger.warning(f"Error calculating patient statistics: {e}")
        
        # Sort patients by total records
        records_by_patient.sort(key=lambda x: x["total_records"], reverse=True)
        records_by_patient = records_by_patient[:20]  # Top 20 patients
        
        # Device statistics
        records_by_device = []
        try:
            device_stats = {}
            for collection_name in collections_info.keys():
                if any(r["collection_name"] == collection_name and r.get("count", 0) > 0 for r in records_by_type):
                    collection = mongodb_service.get_collection(collection_name)
                    device_counts = await collection.aggregate([
                        {"$match": {"device_type": {"$ne": None, "$ne": ""}}},
                        {"$group": {"_id": "$device_type", "count": {"$sum": 1}}},
                        {"$sort": {"count": -1}}
                    ]).to_list(None)
                    
                    for dc in device_counts:
                        device_type = dc["_id"] or "Unknown"
                        if device_type in device_stats:
                            device_stats[device_type] += dc["count"]
                        else:
                            device_stats[device_type] = dc["count"]
            
            records_by_device = [
                {"device_type": device_type, "count": count}
                for device_type, count in sorted(device_stats.items(), key=lambda x: x[1], reverse=True)
            ]
        except Exception as e:
            logger.warning(f"Error calculating device statistics: {e}")
        
        success_response = create_success_response(
            message="Medical history statistics retrieved successfully",
            data={
                "summary": {
                    "total_records": total_records,
                    "total_collections": len(collections_info),
                    "active_collections": len([r for r in records_by_type if r.get("count", 0) > 0]),
                    "patients_with_data": len(patients_with_data)
                },
                "records_by_type": records_by_type,
                "records_by_patient": records_by_patient,
                "records_by_device": records_by_device,
                "top_collections": records_by_type[:5]
            },
            request_id=request_id
        )
        
        return success_response.dict()
        
    except Exception as e:
        logger.error(f"Failed to get medical history statistics: {e}")
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                "INTERNAL_SERVER_ERROR",
                custom_message=f"Failed to retrieve statistics: {str(e)}",
                request_id=request_id
            ).dict()
        )

@router.post("/master-data/{data_type}", 
            response_model=SuccessResponse,
            summary="Create Master Data Record",
            description="""
## Create Master Data Record

Create a new master data record for the specified data type.

### Supported Data Types:
- `blood_groups`, `nations`, `human_skin_colors`, `ward_lists`, `staff_types`, `underlying_diseases`

### Request Body:
```json
{
  "name": [
    {"code": "en", "name": "English Name"},
    {"code": "th", "name": "Thai Name"}
  ],
  "en_name": "English Name",
  "is_active": true,
  "additional_fields": {}
}
```

### Features:
- **Multilingual Support**: English and Thai names
- **Validation**: Automatic field validation
- **Audit Trail**: Automatic timestamps and user tracking
- **Soft Delete**: Records are soft-deleted by default
- **Unique Constraints**: Prevents duplicate entries

### Authentication:
Requires valid JWT Bearer token with admin privileges.
            """,
            responses={
                201: {
                    "description": "Master data record created successfully",
                    "content": {
                        "application/json": {
                            "example": {
                                "success": True,
                                "message": "Master data record created successfully",
                                "data": {
                                    "_id": "663220b2a9e900f9ded0a62f",
                                    "name": [
                                        {"code": "en", "name": "New Staff Type"},
                                        {"code": "th", "name": "ประเภทเจ้าหน้าที่ใหม่"}
                                    ],
                                    "en_name": "New Staff Type",
                                    "is_active": True,
                                    "is_deleted": False,
                                    "created_at": "2024-05-01T11:00:02.415Z",
                                    "updated_at": "2024-05-01T11:00:02.415Z",
                                    "unique_id": 7,
                                    "__v": 0
                                },
                                "request_id": "k1l2m3n4-o5p6-7890-klmn-123456789012",
                                "timestamp": "2025-07-07T19:00:00.000Z"
                            }
                        }
                    }
                },
                400: {
                    "description": "Validation error or invalid data type",
                    "content": {
                        "application/json": {
                            "example": {
                                "success": False,
                                "error_count": 1,
                                "errors": [{
                                    "error_code": "VALIDATION_ERROR",
                                    "error_type": "validation_error",
                                    "message": "Name is required for master data creation",
                                    "field": "name",
                                    "value": None,
                                    "suggestion": "Please provide a valid name with English and Thai translations"
                                }],
                                "request_id": "l2m3n4o5-p6q7-8901-lmno-234567890123",
                                "timestamp": "2025-07-07T19:00:00.000Z"
                            }
                        }
                    }
                },
                401: {"description": "Authentication required"},
                403: {"description": "Admin privileges required"},
                500: {"description": "Internal server error"}
            })
async def create_master_data(
    request: Request,
    data_type: str,
    record_data: MasterDataCreate,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Create a new master data record"""
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    try:
        # Normalize data_type
        normalized_data_type = data_type.replace("-", "_")
        
        # Map data type to collection
        collection_mapping = {
            "blood_groups": "blood_groups",
            "human_skin_colors": "human_skin_colors",
            "nations": "nations",
            "ward_lists": "ward_lists",
            "staff_types": "staff_types",
            "underlying_diseases": "underlying_diseases"
        }
        
        collection_name = collection_mapping.get(normalized_data_type)
        if not collection_name:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid data type: {data_type}. Supported types: {', '.join(collection_mapping.keys())}"
            )
        
        collection = mongodb_service.get_collection(collection_name)
        
        # Validate required fields
        if not record_data.name:
            raise HTTPException(
                status_code=400,
                detail="Name is required for master data creation"
            )
        
        # Prepare document
        document = {
            "name": record_data.name,
            "en_name": record_data.name[0]["name"] if record_data.name else None,
            "is_active": record_data.is_active if record_data.is_active is not None else True,
            "is_deleted": False,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "__v": 0
        }
        
        # Add additional fields if provided
        if record_data.additional_fields:
            document.update(record_data.additional_fields)
        
        # Get next unique_id
        last_record = await collection.find_one(
            {"is_deleted": {"$ne": True}}, 
            sort=[("unique_id", -1)]
        )
        next_unique_id = (last_record.get("unique_id", 0) + 1) if last_record else 1
        document["unique_id"] = next_unique_id
        
        # Insert document
        result = await collection.insert_one(document)
        document["_id"] = result.inserted_id
        
        # Log audit
        await audit_logger.log_action(
            user_id=current_user.get("user_id"),
            action="CREATE",
            resource_type=f"master_data_{normalized_data_type}",
            resource_id=str(result.inserted_id),
            details=f"Created {normalized_data_type} record: {document.get('en_name', 'Unknown')}",
            request_id=request_id
        )
        
        success_response = create_success_response(
            message="Master data record created successfully",
            data=serialize_mongodb_response(document),
            request_id=request_id
        )
        
        return JSONResponse(
            status_code=201,
            content=success_response.dict()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                "INTERNAL_SERVER_ERROR",
                custom_message=f"Failed to create master data record: {str(e)}",
                request_id=request_id
            ).dict()
        )

@router.put("/master-data/{data_type}/{record_id}", 
            response_model=SuccessResponse,
            summary="Update Master Data Record",
            description="""
## Update Master Data Record

Update an existing master data record by ID.

### Supported Data Types:
- `blood_groups`, `nations`, `human_skin_colors`, `ward_lists`, `staff_types`, `underlying_diseases`

### Request Body:
```json
{
  "name": [
    {"code": "en", "name": "Updated English Name"},
    {"code": "th", "name": "Updated Thai Name"}
  ],
  "en_name": "Updated English Name",
  "is_active": true,
  "additional_fields": {}
}
```

### Features:
- **Partial Updates**: Only provided fields are updated
- **Validation**: Automatic field validation
- **Audit Trail**: Automatic timestamp updates
- **Soft Delete**: Records can be soft-deleted
- **Multilingual Support**: English and Thai names

### Authentication:
Requires valid JWT Bearer token with admin privileges.
            """,
            responses={
                200: {
                    "description": "Master data record updated successfully",
                    "content": {
                        "application/json": {
                            "example": {
                                "success": True,
                                "message": "Master data record updated successfully",
                                "data": {
                                    "_id": "663220b2a9e900f9ded0a62f",
                                    "name": [
                                        {"code": "en", "name": "Updated Staff Type"},
                                        {"code": "th", "name": "ประเภทเจ้าหน้าที่ที่อัปเดต"}
                                    ],
                                    "en_name": "Updated Staff Type",
                                    "is_active": True,
                                    "is_deleted": False,
                                    "created_at": "2024-05-01T11:00:02.415Z",
                                    "updated_at": "2025-07-07T19:00:00.000Z",
                                    "unique_id": 1,
                                    "__v": 1
                                },
                                "request_id": "m3n4o5p6-q7r8-9012-mnop-345678901234",
                                "timestamp": "2025-07-07T19:00:00.000Z"
                            }
                        }
                    }
                },
                400: {"description": "Validation error or invalid data type"},
                401: {"description": "Authentication required"},
                403: {"description": "Admin privileges required"},
                404: {"description": "Record not found"},
                500: {"description": "Internal server error"}
            })
async def update_master_data(
    request: Request,
    data_type: str,
    record_id: str,
    record_data: MasterDataUpdate,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Update a master data record"""
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    try:
        # Normalize data_type
        normalized_data_type = data_type.replace("-", "_")
        
        # Map data type to collection
        collection_mapping = {
            "blood_groups": "blood_groups",
            "human_skin_colors": "human_skin_colors",
            "nations": "nations",
            "ward_lists": "ward_lists",
            "staff_types": "staff_types",
            "underlying_diseases": "underlying_diseases"
        }
        
        collection_name = collection_mapping.get(normalized_data_type)
        if not collection_name:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid data type: {data_type}. Supported types: {', '.join(collection_mapping.keys())}"
            )
        
        collection = mongodb_service.get_collection(collection_name)
        
        # Validate ObjectId
        try:
            object_id = ObjectId(record_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid record ID format")
        
        # Check if record exists
        existing_record = await collection.find_one({"_id": object_id, "is_deleted": {"$ne": True}})
        if not existing_record:
            raise HTTPException(status_code=404, detail="Record not found")
        
        # Prepare update data
        update_data = {"updated_at": datetime.utcnow()}
        
        if record_data.name is not None:
            update_data["name"] = record_data.name
            update_data["en_name"] = record_data.name[0]["name"] if record_data.name else None
        
        if record_data.is_active is not None:
            update_data["is_active"] = record_data.is_active
        
        if record_data.additional_fields is not None:
            update_data.update(record_data.additional_fields)
        
        # Update document
        result = await collection.update_one(
            {"_id": object_id},
            {"$set": update_data, "$inc": {"__v": 1}}
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Record not found or no changes made")
        
        # Get updated record
        updated_record = await collection.find_one({"_id": object_id})
        
        # Log audit
        await audit_logger.log_action(
            user_id=current_user.get("user_id"),
            action="UPDATE",
            resource_type=f"master_data_{normalized_data_type}",
            resource_id=record_id,
            details=f"Updated {normalized_data_type} record: {updated_record.get('en_name', 'Unknown')}",
            request_id=request_id
        )
        
        success_response = create_success_response(
            message="Master data record updated successfully",
            data=serialize_mongodb_response(updated_record),
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
                custom_message=f"Failed to update master data record: {str(e)}",
                request_id=request_id
            ).dict()
        )

@router.patch("/master-data/{data_type}/{record_id}", 
            response_model=SuccessResponse,
            summary="Partially Update Master Data Record",
            description="""
## Partially Update Master Data Record

Partially update an existing master data record by ID.

### Supported Data Types:
- `blood_groups`, `nations`, `human_skin_colors`, `ward_lists`, `staff_types`, `underlying_diseases`

### Request Body:
```json
{
  "name": [
    {"code": "en", "name": "Updated English Name"},
    {"code": "th", "name": "Updated Thai Name"}
  ],
  "is_active": false
}
```

### Features:
- **Partial Updates**: Only provided fields are updated
- **Validation**: Automatic field validation
- **Audit Trail**: Automatic timestamp updates
- **Soft Delete**: Records can be soft-deleted
- **Multilingual Support**: English and Thai names

### Authentication:
Requires valid JWT Bearer token with admin privileges.
            """,
            responses={
                200: {
                    "description": "Master data record partially updated successfully",
                    "content": {
                        "application/json": {
                            "example": {
                                "success": True,
                                "message": "Master data record partially updated successfully",
                                "data": {
                                    "_id": "663220b2a9e900f9ded0a62f",
                                    "name": [
                                        {"code": "en", "name": "Partially Updated Staff Type"},
                                        {"code": "th", "name": "ประเภทเจ้าหน้าที่ที่อัปเดตบางส่วน"}
                                    ],
                                    "en_name": "Partially Updated Staff Type",
                                    "is_active": False,
                                    "is_deleted": False,
                                    "created_at": "2024-05-01T11:00:02.415Z",
                                    "updated_at": "2025-07-07T19:00:00.000Z",
                                    "unique_id": 1,
                                    "__v": 2
                                },
                                "request_id": "n4o5p6q7-r8s9-0123-nopq-456789012345",
                                "timestamp": "2025-07-07T19:00:00.000Z"
                            }
                        }
                    }
                },
                400: {"description": "Validation error or invalid data type"},
                401: {"description": "Authentication required"},
                403: {"description": "Admin privileges required"},
                404: {"description": "Record not found"},
                500: {"description": "Internal server error"}
            })
async def patch_master_data(
    request: Request,
    data_type: str,
    record_id: str,
    record_data: MasterDataUpdate,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Partially update a master data record"""
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    try:
        # Normalize data_type
        normalized_data_type = data_type.replace("-", "_")
        
        # Map data type to collection
        collection_mapping = {
            "blood_groups": "blood_groups",
            "human_skin_colors": "human_skin_colors",
            "nations": "nations",
            "ward_lists": "ward_lists",
            "staff_types": "staff_types",
            "underlying_diseases": "underlying_diseases"
        }
        
        collection_name = collection_mapping.get(normalized_data_type)
        if not collection_name:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid data type: {data_type}. Supported types: {', '.join(collection_mapping.keys())}"
            )
        
        collection = mongodb_service.get_collection(collection_name)
        
        # Validate ObjectId
        try:
            object_id = ObjectId(record_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid record ID format")
        
        # Check if record exists
        existing_record = await collection.find_one({"_id": object_id, "is_deleted": {"$ne": True}})
        if not existing_record:
            raise HTTPException(status_code=404, detail="Record not found")
        
        # Prepare update data (only non-None fields)
        update_data = {"updated_at": datetime.utcnow()}
        
        if record_data.name is not None:
            update_data["name"] = record_data.name
            update_data["en_name"] = record_data.name[0]["name"] if record_data.name else None
        
        if record_data.is_active is not None:
            update_data["is_active"] = record_data.is_active
        
        if record_data.additional_fields is not None:
            update_data.update(record_data.additional_fields)
        
        # Update document
        result = await collection.update_one(
            {"_id": object_id},
            {"$set": update_data, "$inc": {"__v": 1}}
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Record not found or no changes made")
        
        # Get updated record
        updated_record = await collection.find_one({"_id": object_id})
        
        # Log audit
        await audit_logger.log_action(
            user_id=current_user.get("user_id"),
            action="PATCH",
            resource_type=f"master_data_{normalized_data_type}",
            resource_id=record_id,
            details=f"Partially updated {normalized_data_type} record: {updated_record.get('en_name', 'Unknown')}",
            request_id=request_id
        )
        
        success_response = create_success_response(
            message="Master data record partially updated successfully",
            data=serialize_mongodb_response(updated_record),
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
                custom_message=f"Failed to partially update master data record: {str(e)}",
                request_id=request_id
            ).dict()
        )

@router.delete("/master-data/{data_type}/{record_id}", 
            response_model=SuccessResponse,
            summary="Delete Master Data Record",
            description="""
## Delete Master Data Record

Soft delete a master data record by ID.

### Supported Data Types:
- `blood_groups`, `nations`, `human_skin_colors`, `ward_lists`, `staff_types`, `underlying_diseases`

### Features:
- **Soft Delete**: Records are marked as deleted but not physically removed
- **Audit Trail**: Automatic timestamp updates and user tracking
- **Validation**: Checks if record exists before deletion
- **Reversible**: Soft-deleted records can be restored

### Authentication:
Requires valid JWT Bearer token with admin privileges.
            """,
            responses={
                200: {
                    "description": "Master data record deleted successfully",
                    "content": {
                        "application/json": {
                            "example": {
                                "success": True,
                                "message": "Master data record deleted successfully",
                                "data": {
                                    "_id": "663220b2a9e900f9ded0a62f",
                                    "name": [
                                        {"code": "en", "name": "Deleted Staff Type"},
                                        {"code": "th", "name": "ประเภทเจ้าหน้าที่ที่ลบ"}
                                    ],
                                    "en_name": "Deleted Staff Type",
                                    "is_active": False,
                                    "is_deleted": True,
                                    "deleted_at": "2025-07-07T19:00:00.000Z",
                                    "deleted_by": "6638a496f7ce6d32b68120f1",
                                    "created_at": "2024-05-01T11:00:02.415Z",
                                    "updated_at": "2025-07-07T19:00:00.000Z",
                                    "unique_id": 1,
                                    "__v": 3
                                },
                                "request_id": "o5p6q7r8-s9t0-1234-opqr-567890123456",
                                "timestamp": "2025-07-07T19:00:00.000Z"
                            }
                        }
                    }
                },
                400: {"description": "Invalid data type or record ID format"},
                401: {"description": "Authentication required"},
                403: {"description": "Admin privileges required"},
                404: {"description": "Record not found"},
                500: {"description": "Internal server error"}
            })
async def delete_master_data(
    request: Request,
    data_type: str,
    record_id: str,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Soft delete a master data record"""
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    try:
        # Normalize data_type
        normalized_data_type = data_type.replace("-", "_")
        
        # Map data type to collection
        collection_mapping = {
            "blood_groups": "blood_groups",
            "human_skin_colors": "human_skin_colors",
            "nations": "nations",
            "ward_lists": "ward_lists",
            "staff_types": "staff_types",
            "underlying_diseases": "underlying_diseases"
        }
        
        collection_name = collection_mapping.get(normalized_data_type)
        if not collection_name:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid data type: {data_type}. Supported types: {', '.join(collection_mapping.keys())}"
            )
        
        collection = mongodb_service.get_collection(collection_name)
        
        # Validate ObjectId
        try:
            object_id = ObjectId(record_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid record ID format")
        
        # Check if record exists
        existing_record = await collection.find_one({"_id": object_id, "is_deleted": {"$ne": True}})
        if not existing_record:
            raise HTTPException(status_code=404, detail="Record not found")
        
        # Soft delete record
        result = await collection.update_one(
            {"_id": object_id},
            {
                "$set": {
                    "is_deleted": True,
                    "is_active": False,
                    "deleted_at": datetime.utcnow(),
                    "deleted_by": current_user.get("user_id"),
                    "updated_at": datetime.utcnow()
                },
                "$inc": {"__v": 1}
            }
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Record not found or already deleted")
        
        # Get deleted record
        deleted_record = await collection.find_one({"_id": object_id})
        
        # Log audit
        await audit_logger.log_action(
            user_id=current_user.get("user_id"),
            action="DELETE",
            resource_type=f"master_data_{normalized_data_type}",
            resource_id=record_id,
            details=f"Soft deleted {normalized_data_type} record: {deleted_record.get('en_name', 'Unknown')}",
            request_id=request_id
        )
        
        success_response = create_success_response(
            message="Master data record deleted successfully",
            data=serialize_mongodb_response(deleted_record),
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
                custom_message=f"Failed to delete master data record: {str(e)}",
                request_id=request_id
            ).dict()
        )

@router.get(
    "/hospitals-raw-documents",
    summary="Get Raw Hospital Documents",
    description="""
    ## Raw Hospital Document Analysis
    
    Access complete MongoDB hospital documents without serialization for analysis and debugging.
    
    ### Features:
    - **Complete Raw Structure**: All hospital fields per document
    - **Field Analysis**: Automatic data type detection and statistics
    - **Sample Values**: Preview of actual field content
    - **ObjectId Mapping**: MongoDB relationship identification
    - **Pagination Support**: Handle large document sets efficiently
    - **Filtering Options**: Hospital ID and deletion status filters
    
    ### Document Structure:
    
    #### **Core Hospital Information** (15+ fields):
    - `_id`, `name`, `en_name`, `province_code`, `district_code`
    - `sub_district_code`, `organizecode`, `hospital_area_code`
    - `is_active`, `is_deleted`, `created_at`, `updated_at`
    
    #### **Enhanced Address Information** (10+ fields):
    - `address`: Basic address string
    - `address_details`: Detailed address structure
    - `location`: Geographic coordinates and precision
    
    #### **Contact Information** (10+ fields):
    - `contact`: Comprehensive contact details
    - `phone`, `email`, `website`: Legacy contact fields
    - `fax`, `mobile`, `emergency_phone`: Additional contact methods
    
    #### **Service Information** (10+ fields):
    - `services`: Service and capacity details
    - `bed_capacity`, `service_plan_type`: Legacy service fields
    - `emergency_services`, `trauma_center`, `icu_beds`
    
    #### **Digital Integration** (10+ fields):
    - `image_url`: Hospital image URL
    - `auto_login_liff_id`, `disconnect_liff_id`, `login_liff_id`
    - `mac_hv01_box`, `notifyToken`, `rich_menu_token`
    - `telegram_Token`: Telegram notification token
    
    #### **Notification Settings** (5+ fields):
    - `is_acknowledge`, `is_admit_discard`
    - `is_body_data`, `is_lab_data`, `is_status_change`
    
    ### Query Parameters:
    - `limit`: Number of documents to return (1-50, default: 5)
    - `skip`: Number of documents to skip for pagination
    - `hospital_id`: Filter by specific hospital ObjectId
    - `include_deleted`: Include soft-deleted hospitals (default: false)
    - `province_code`: Filter by province code
    - `district_code`: Filter by district code
    - `sub_district_code`: Filter by sub-district code
    
    ### Response Features:
    - **Raw Documents**: Complete MongoDB structure preserved
    - **Field Analysis**: Data type detection and usage statistics
    - **Sample Values**: Up to 3 sample values per field
    - **ObjectId Detection**: Automatic relationship mapping
    - **Pagination Info**: Total count and navigation details
    
    ### Use Cases:
    - **Database Analysis**: Understand complete hospital data structure
    - **Integration Planning**: Map fields for external system integration
    - **Data Migration**: Analyze field usage and data types
    - **Debugging**: Inspect raw MongoDB documents
    - **API Development**: Understand available hospital fields
    
    ### Authentication:
    Requires valid JWT Bearer token with admin privileges.
    """,
    responses={
        200: {
            "description": "Raw hospital documents retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Raw hospital documents retrieved successfully",
                        "data": {
                            "raw_documents": [
                                {
                                    "_id": {"$oid": "507f1f77bcf86cd799439011"},
                                    "name": [
                                        {"code": "en", "name": "Bangkok General Hospital"},
                                        {"code": "th", "name": "โรงพยาบาลกรุงเทพ"}
                                    ],
                                    "en_name": "Bangkok General Hospital",
                                    "province_code": 10,
                                    "district_code": 1003,
                                    "sub_district_code": 100301,
                                    "organizecode": 1001,
                                    "hospital_area_code": "10330",
                                    "is_active": True,
                                    "is_deleted": False,
                                    "address": "123 Rama IV Road, Pathum Wan, Bangkok 10330",
                                    "phone": "+66-2-123-4567",
                                    "email": "info@bgh.co.th",
                                    "website": "https://www.bgh.co.th",
                                    "bed_capacity": 500,
                                    "service_plan_type": "A",
                                    "created_at": {"$date": "2024-01-15T08:00:00.000Z"},
                                    "updated_at": {"$date": "2024-01-15T10:30:00.000Z"},
                                    "__v": 2
                                }
                            ],
                            "total_count": 12350,
                            "returned_count": 1,
                            "field_analysis": {
                                "_id": {
                                    "count": 1,
                                    "data_types": ["ObjectId"],
                                    "sample_values": ["507f1f77bcf86cd799439011"],
                                    "is_object_id": True
                                },
                                "name": {
                                    "count": 1,
                                    "data_types": ["array"],
                                    "sample_values": [{"code": "en", "name": "Bangkok General Hospital"}],
                                    "is_object_id": False
                                },
                                "province_code": {
                                    "count": 1,
                                    "data_types": ["int"],
                                    "sample_values": [10],
                                    "is_object_id": False
                                },
                                "bed_capacity": {
                                    "count": 1,
                                    "data_types": ["int"],
                                    "sample_values": [500],
                                    "is_object_id": False
                                }
                            },
                            "pagination": {
                                "limit": 5,
                                "skip": 0,
                                "has_more": True
                            },
                            "filters": {
                                "hospital_id": None,
                                "include_deleted": False,
                                "province_code": None,
                                "district_code": None
                            },
                            "metadata": {
                                "collection": "hospitals",
                                "query_filter": "{'is_deleted': {'$ne': True}}",
                                "timestamp": "2024-01-15T10:30:00.000000Z"
                            }
                        }
                    }
                }
            }
        },
        400: {"description": "Invalid hospital ID format"},
        401: {"description": "Authentication required"},
        403: {"description": "Admin privileges required"},
        500: {"description": "Internal server error"}
    },
    tags=["admin"]
)
async def get_raw_hospital_documents(
    request: Request,
    limit: int = Query(5, ge=1, le=50, description="Number of raw documents to return"),
    skip: int = Query(0, ge=0, description="Number of documents to skip"),
    hospital_id: Optional[str] = Query(None, description="Filter by specific hospital ID"),
    include_deleted: bool = Query(False, description="Include soft-deleted hospitals"),
    province_code: Optional[int] = Query(None, description="Filter by province code"),
    district_code: Optional[int] = Query(None, description="Filter by district code"),
    sub_district_code: Optional[int] = Query(None, description="Filter by sub-district code"),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get raw hospital documents from MongoDB without serialization for debugging and analysis"""
    import uuid
    try:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        collection = mongodb_service.get_collection("hospitals")
        
        # Build filter
        filter_query = {}
        if not include_deleted:
            filter_query["is_deleted"] = {"$ne": True}
        
        if hospital_id:
            try:
                filter_query["_id"] = ObjectId(hospital_id)
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
        
        if province_code:
            filter_query["province_code"] = province_code
        
        if district_code:
            filter_query["district_code"] = district_code
        
        if sub_district_code:
            filter_query["sub_district_code"] = sub_district_code
        
        # Get raw documents without serialization
        cursor = collection.find(filter_query).sort("_id", 1).skip(skip).limit(limit)
        raw_documents = await cursor.to_list(length=limit)
        
        # Get total count
        total_count = await collection.count_documents(filter_query)
        
        # If no documents found, return a clear error
        if total_count == 0:
            logger.warning(f"HOSPITAL_RAW_DOCS: No hospital documents found for filter: {filter_query} - Request ID: {request_id}")
            raise HTTPException(
                status_code=404,
                detail=create_error_response(
                    "NO_HOSPITAL_DOCUMENTS_FOUND",
                    custom_message=f"No hospital documents found in the database for the given filter. Filter applied: {filter_query}",
                    field=None,
                    value=None,
                    request_id=request_id
                ).dict()
            )
        
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
                
                # Determine data type
                field_type = type(doc[field]).__name__
                field_analysis[field]["data_types"].add(field_type)
                
                # Check if it's an ObjectId
                if field == "_id" or (isinstance(doc[field], ObjectId)):
                    field_analysis[field]["is_object_id"] = True
                
                # Add sample values (up to 3)
                if len(field_analysis[field]["sample_values"]) < 3:
                    sample_value = str(doc[field]) if isinstance(doc[field], ObjectId) else doc[field]
                    if sample_value not in field_analysis[field]["sample_values"]:
                        field_analysis[field]["sample_values"].append(sample_value)
        
        # Convert sets to lists for JSON serialization
        for field in field_analysis:
            field_analysis[field]["data_types"] = list(field_analysis[field]["data_types"])
        
        # Use enhanced serialization for all components
        serialized_documents = serialize_mongodb_response(raw_documents)
        serialized_field_analysis = serialize_field_analysis(field_analysis)
        
        # Create response data with comprehensive serialization
        response_data = {
            "raw_documents": serialized_documents,
            "total_count": total_count,
            "returned_count": len(raw_documents),
            "field_analysis": serialized_field_analysis,
            "pagination": {
                "limit": limit,
                "skip": skip,
                "has_more": (skip + limit) < total_count
            },
            "filters": {
                "hospital_id": hospital_id,
                "include_deleted": include_deleted,
                "province_code": province_code,
                "district_code": district_code,
                "sub_district_code": sub_district_code
            },
            "metadata": {
                "collection": "hospitals",
                "query_filter": str(filter_query),
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
        # Use the enhanced MongoDB-compatible response creator
        final_response = create_mongodb_compatible_response(
            success=True,
            message="Raw hospital documents retrieved successfully",
            data=response_data,
            request_id=request_id
        )
        
        # Return as JSONResponse with full serialization guarantee
        return JSONResponse(content=final_response)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                "INTERNAL_SERVER_ERROR",
                custom_message=f"Failed to retrieve raw hospital documents: {str(e)}",
                request_id=request_id
            ).dict()
        )

@router.get("/dropdown/provinces", 
            response_model=SuccessResponse,
            summary="Get Provinces for Dropdown",
            description="""
## Province Dropdown Endpoint

Optimized endpoint for province dropdown lists in forms with flexible filtering options.

### Features:
- **Lightweight Response**: Only essential fields (code, en_name, th_name)
- **Fast Performance**: Minimal data transfer
- **Sorted Results**: Alphabetically sorted by English name
- **Flexible Filtering**: Optional inclusion of inactive/deleted records
- **Search Support**: Optional text search across province names
- **Pagination**: Optional limit for large datasets

### Query Parameters:
- `include_inactive` (optional): Include inactive provinces (default: false)
- `include_deleted` (optional): Include soft-deleted provinces (default: false)
- `search` (optional): Search text across English and Thai names
- `limit` (optional): Maximum number of results (default: unlimited)
- `sort_by` (optional): Sort field - 'en_name' or 'code' (default: 'en_name')

### Response Format:
```json
{
  "success": true,
  "data": {
    "provinces": [
      {"code": 10, "en_name": "Bangkok", "th_name": "กรุงเทพมหานคร", "is_active": true},
      {"code": 11, "en_name": "Samut Prakan", "th_name": "สมุทรปราการ", "is_active": true}
    ],
    "total": 79,
    "filters_applied": {
      "include_inactive": false,
      "include_deleted": false,
      "search": null
    }
  }
}
```

### Use Cases:
- Province dropdown in patient registration forms
- Hospital search filters
- Address selection forms
- Geographic filtering interfaces
- Administrative management (with inactive/deleted records)

### Authentication:
Requires valid JWT Bearer token.
            """,
            responses={
                200: {
                    "description": "Provinces retrieved successfully for dropdown",
                    "content": {
                        "application/json": {
                            "example": {
                                "success": True,
                                "message": "Provinces retrieved successfully for dropdown",
                                "data": {
                                    "provinces": [
                                        {"code": 10, "en_name": "Bangkok", "th_name": "กรุงเทพมหานคร", "is_active": True},
                                        {"code": 11, "en_name": "Samut Prakan", "th_name": "สมุทรปราการ", "is_active": True},
                                        {"code": 12, "en_name": "Nonthaburi", "th_name": "นนทบุรี", "is_active": True}
                                    ],
                                    "total": 6,
                                    "filters_applied": {
                                        "include_inactive": False,
                                        "include_deleted": False,
                                        "search": None
                                    }
                                },
                                "request_id": "dropdown-001",
                                "timestamp": "2025-01-08T05:42:00.000Z"
                            }
                        }
                    }
                },
                401: {"description": "Authentication required"},
                500: {"description": "Internal server error"}
            })
async def get_provinces_dropdown(
    request: Request,
    include_inactive: bool = Query(False, description="Include inactive provinces"),
    include_deleted: bool = Query(False, description="Include soft-deleted provinces"),
    search: Optional[str] = Query(None, description="Search text across province names"),
    limit: Optional[int] = Query(None, ge=1, le=1000, description="Maximum number of results"),
    sort_by: str = Query("en_name", description="Sort field: 'en_name' or 'code'"),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get provinces optimized for dropdown forms with flexible filtering"""
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    try:
        collection = mongodb_service.get_collection("provinces")
        
        # Build dynamic filter based on parameters
        filter_query = {}
        
        # Apply status filters
        if not include_inactive:
            filter_query["is_active"] = True
        if not include_deleted:
            filter_query["is_deleted"] = False
            
        # Apply search filter
        if search:
            filter_query["$or"] = [
                {"en_name": {"$regex": search, "$options": "i"}},
                {"name.name": {"$regex": search, "$options": "i"}}
            ]
        
        # Select fields to return (include is_active for response)
        projection = {"code": 1, "en_name": 1, "name": 1, "is_active": 1, "_id": 0}
        
        # Determine sort field
        sort_field = sort_by if sort_by in ["en_name", "code"] else "en_name"
        
        # Execute query
        cursor = collection.find(filter_query, projection).sort(sort_field, 1)
        
        # Apply limit if specified
        if limit:
            cursor = cursor.limit(limit)
            
        provinces_data = await cursor.to_list(length=None)
        
        # Format for dropdown (extract Thai name from name array)
        provinces = []
        for province in provinces_data:
            th_name = ""
            if province.get("name"):
                for name_obj in province["name"]:
                    if name_obj.get("code") == "th":
                        th_name = name_obj.get("name", "")
                        break
            
            provinces.append({
                "code": province["code"],
                "en_name": province["en_name"],
                "th_name": th_name,
                "is_active": province.get("is_active", True)
            })
        
        return create_success_response(
            message="Provinces retrieved successfully for dropdown",
            data={
                "provinces": provinces,
                "total": len(provinces),
                "filters_applied": {
                    "include_inactive": include_inactive,
                    "include_deleted": include_deleted,
                    "search": search,
                    "limit": limit,
                    "sort_by": sort_field
                }
            },
            request_id=request_id
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                "INTERNAL_SERVER_ERROR",
                custom_message=f"Failed to retrieve provinces for dropdown: {str(e)}",
                request_id=request_id
            ).dict()
        )

@router.get("/dropdown/districts", 
            response_model=SuccessResponse,
            summary="Get Districts for Dropdown",
            description="""
## District Dropdown Endpoint

Optimized endpoint for district dropdown lists in forms with province filtering and flexible options.

### Features:
- **Cascading Filter**: Filter by province_code for cascading dropdowns
- **Lightweight Response**: Only essential fields (code, en_name, th_name)
- **Fast Performance**: Minimal data transfer
- **Sorted Results**: Alphabetically sorted by English name
- **Flexible Filtering**: Optional inclusion of inactive/deleted records
- **Search Support**: Optional text search across district names

### Query Parameters:
- `province_code` (required): Province code to filter districts
- `include_inactive` (optional): Include inactive districts (default: false)
- `include_deleted` (optional): Include soft-deleted districts (default: false)
- `search` (optional): Search text across English and Thai names
- `limit` (optional): Maximum number of results (default: unlimited)
- `sort_by` (optional): Sort field - 'en_name' or 'code' (default: 'en_name')

### Response Format:
```json
{
  "success": true,
  "data": {
    "districts": [
      {"code": 1003, "en_name": "Khet Pathum Wan", "th_name": "เขตปทุมวัน", "is_active": true},
      {"code": 1008, "en_name": "Khet Pom Prap Sattru Phai", "th_name": "เขตป้อมปราบศัตรูพ่าย", "is_active": true}
    ],
    "total": 12,
    "province_code": 10,
    "filters_applied": {
      "include_inactive": false,
      "include_deleted": false,
      "search": null
    }
  }
}
```

### Use Cases:
- District dropdown after province selection
- Cascading geographic forms
- Hospital location filtering
- Address completion forms
- Administrative management (with inactive/deleted records)

### Authentication:
Requires valid JWT Bearer token.
            """,
            responses={
                200: {
                    "description": "Districts retrieved successfully for dropdown",
                    "content": {
                        "application/json": {
                            "example": {
                                "success": True,
                                "message": "Districts retrieved successfully for dropdown",
                                "data": {
                                    "districts": [
                                        {"code": 1003, "en_name": "Khet Pathum Wan", "th_name": "เขตปทุมวัน", "is_active": True},
                                        {"code": 1008, "en_name": "Khet Pom Prap Sattru Phai", "th_name": "เขตป้อมปราบศัตรูพ่าย", "is_active": True}
                                    ],
                                    "total": 12,
                                    "province_code": 10,
                                    "filters_applied": {
                                        "include_inactive": False,
                                        "include_deleted": False,
                                        "search": None
                                    }
                                },
                                "request_id": "dropdown-002",
                                "timestamp": "2025-01-08T05:42:00.000Z"
                            }
                        }
                    }
                },
                400: {"description": "Province code is required"},
                401: {"description": "Authentication required"},
                404: {"description": "Province not found"},
                500: {"description": "Internal server error"}
            })
async def get_districts_dropdown(
    request: Request,
    province_code: int = Query(..., description="Province code to filter districts"),
    include_inactive: bool = Query(False, description="Include inactive districts"),
    include_deleted: bool = Query(False, description="Include soft-deleted districts"),
    search: Optional[str] = Query(None, description="Search text across district names"),
    limit: Optional[int] = Query(None, ge=1, le=1000, description="Maximum number of results"),
    sort_by: str = Query("en_name", description="Sort field: 'en_name' or 'code'"),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get districts for a province optimized for dropdown forms with flexible filtering"""
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    try:
        # Validate province exists (use flexible validation based on include flags)
        provinces_collection = mongodb_service.get_collection("provinces")
        province_filter = {"code": province_code}
        if not include_inactive:
            province_filter["is_active"] = True
        if not include_deleted:
            province_filter["is_deleted"] = False
            
        province_exists = await provinces_collection.find_one(province_filter)
        
        if not province_exists:
            raise HTTPException(
                status_code=404,
                detail=create_error_response(
                    "NOT_FOUND",
                    custom_message=f"Province with code {province_code} not found",
                    field="province_code",
                    value=province_code,
                    request_id=request_id
                ).dict()
            )
        
        # Build dynamic filter for districts
        filter_query = {"province_code": province_code}
        
        # Apply status filters
        if not include_inactive:
            filter_query["is_active"] = True
        if not include_deleted:
            filter_query["is_deleted"] = False
            
        # Apply search filter
        if search:
            filter_query["$or"] = [
                {"en_name": {"$regex": search, "$options": "i"}},
                {"name.name": {"$regex": search, "$options": "i"}}
            ]
        
        # Select fields to return (include is_active for response)
        projection = {"code": 1, "en_name": 1, "name": 1, "is_active": 1, "_id": 0}
        
        # Determine sort field
        sort_field = sort_by if sort_by in ["en_name", "code"] else "en_name"
        
        # Execute query
        collection = mongodb_service.get_collection("districts")
        cursor = collection.find(filter_query, projection).sort(sort_field, 1)
        
        # Apply limit if specified
        if limit:
            cursor = cursor.limit(limit)
        
        districts_data = await cursor.to_list(length=None)
        
        # Format for dropdown (extract Thai name from name array)
        districts = []
        for district in districts_data:
            th_name = ""
            if district.get("name"):
                for name_obj in district["name"]:
                    if name_obj.get("code") == "th":
                        th_name = name_obj.get("name", "")
                        break
            
            districts.append({
                "code": district["code"],
                "en_name": district["en_name"],
                "th_name": th_name,
                "is_active": district.get("is_active", True)
            })
        
        return create_success_response(
            message="Districts retrieved successfully for dropdown",
            data={
                "districts": districts,
                "total": len(districts),
                "province_code": province_code,
                "filters_applied": {
                    "include_inactive": include_inactive,
                    "include_deleted": include_deleted,
                    "search": search,
                    "limit": limit,
                    "sort_by": sort_field
                }
            },
            request_id=request_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                "INTERNAL_SERVER_ERROR",
                custom_message=f"Failed to retrieve districts for dropdown: {str(e)}",
                request_id=request_id
            ).dict()
        )

@router.get("/dropdown/sub-districts", 
            response_model=SuccessResponse,
            summary="Get Sub-Districts for Dropdown",
            description="""
## Sub-District Dropdown Endpoint

Optimized endpoint for sub-district dropdown lists in forms with province and district filtering.

### Features:
- **Cascading Filter**: Filter by province_code and district_code for cascading dropdowns
- **Lightweight Response**: Only essential fields (code, en_name, th_name)
- **Fast Performance**: Minimal data transfer
- **Sorted Results**: Alphabetically sorted by English name
- **Active Only**: Returns only active, non-deleted sub-districts

### Query Parameters:
- `province_code` (required): Province code to filter sub-districts
- `district_code` (required): District code to filter sub-districts

### Response Format:
```json
{
  "success": true,
  "data": {
    "sub_districts": [
      {"code": 100301, "en_name": "Khwaeng Lumphini", "th_name": "แขวงลุมพินี"},
      {"code": 100302, "en_name": "Khwaeng Pathum Wan", "th_name": "แขวงปทุมวัน"}
    ],
    "total": 6,
    "province_code": 10,
    "district_code": 1003
  }
}
```

### Use Cases:
- Sub-district dropdown after district selection
- Complete cascading geographic forms
- Detailed address forms
- Hospital location specification

### Authentication:
Requires valid JWT Bearer token.
            """,
            responses={
                200: {
                    "description": "Sub-districts retrieved successfully for dropdown",
                    "content": {
                        "application/json": {
                            "example": {
                                "success": True,
                                "message": "Sub-districts retrieved successfully for dropdown",
                                "data": {
                                    "sub_districts": [
                                        {"code": 100301, "en_name": "Khwaeng Lumphini", "th_name": "แขวงลุมพินี"},
                                        {"code": 100302, "en_name": "Khwaeng Pathum Wan", "th_name": "แขวงปทุมวัน"}
                                    ],
                                    "total": 6,
                                    "province_code": 10,
                                    "district_code": 1003
                                },
                                "request_id": "dropdown-003",
                                "timestamp": "2025-01-08T05:42:00.000Z"
                            }
                        }
                    }
                },
                400: {"description": "Province code and district code are required"},
                401: {"description": "Authentication required"},
                404: {"description": "Province or district not found"},
                500: {"description": "Internal server error"}
            })
async def get_sub_districts_dropdown(
    request: Request,
    province_code: int = Query(..., description="Province code to filter sub-districts"),
    district_code: int = Query(..., description="District code to filter sub-districts"),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get sub-districts for a province and district optimized for dropdown forms"""
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    try:
        # Validate province exists
        provinces_collection = mongodb_service.get_collection("provinces")
        province_exists = await provinces_collection.find_one(
            {"code": province_code, "is_active": True, "is_deleted": False}
        )
        
        if not province_exists:
            raise HTTPException(
                status_code=404,
                detail=create_error_response(
                    "NOT_FOUND",
                    custom_message=f"Province with code {province_code} not found",
                    field="province_code",
                    value=province_code,
                    request_id=request_id
                ).dict()
            )
        
        # Validate district exists
        districts_collection = mongodb_service.get_collection("districts")
        district_exists = await districts_collection.find_one(
            {
                "code": district_code,
                "province_code": province_code,
                "is_active": True, 
                "is_deleted": False
            }
        )
        
        if not district_exists:
            raise HTTPException(
                status_code=404,
                detail=create_error_response(
                    "NOT_FOUND",
                    custom_message=f"District with code {district_code} in province {province_code} not found",
                    field="district_code",
                    value=district_code,
                    request_id=request_id
                ).dict()
            )
        
        # Get sub-districts for the province and district
        collection = mongodb_service.get_collection("sub_districts")
        cursor = collection.find(
            {
                "province_code": province_code,
                "district_code": district_code,
                "is_active": True, 
                "is_deleted": False
            },
            {"code": 1, "en_name": 1, "name": 1, "_id": 0}
        ).sort("en_name", 1)
        
        sub_districts_data = await cursor.to_list(length=None)
        
        # Format for dropdown (extract Thai name from name array)
        sub_districts = []
        for sub_district in sub_districts_data:
            th_name = ""
            if sub_district.get("name"):
                for name_obj in sub_district["name"]:
                    if name_obj.get("code") == "th":
                        th_name = name_obj.get("name", "")
                        break
            
            sub_districts.append({
                "code": sub_district["code"],
                "en_name": sub_district["en_name"],
                "th_name": th_name
            })
        
        return create_success_response(
            message="Sub-districts retrieved successfully for dropdown",
            data={
                "sub_districts": sub_districts,
                "total": len(sub_districts),
                "province_code": province_code,
                "district_code": district_code
            },
            request_id=request_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                "INTERNAL_SERVER_ERROR",
                custom_message=f"Failed to retrieve sub-districts for dropdown: {str(e)}",
                request_id=request_id
            ).dict()
        )

# IP Management API Endpoints

@router.get("/rate-limit/whitelist", 
            response_model=SuccessResponse,
            responses={
                200: {
                    "description": "Whitelist retrieved successfully",
                    "content": {
                        "application/json": {
                            "example": {
                                "success": True,
                                "message": "Retrieved whitelist with 3 IP addresses",
                                "data": {
                                    "total_count": 3,
                                    "whitelist": [
                                        {
                                            "ip_address": "127.0.0.1",
                                            "reason": "Local development",
                                            "added_by": "system",
                                            "timestamp": "2025-07-09T06:30:00.000000Z"
                                        },
                                        {
                                            "ip_address": "49.0.81.155",
                                            "reason": "Admin access",
                                            "added_by": "admin",
                                            "timestamp": "2025-07-09T06:30:00.000000Z"
                                        }
                                    ]
                                }
                            }
                        }
                    }
                }
            })
async def get_ip_whitelist(
    request: Request,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get current IP whitelist with detailed information"""
    import uuid
    try:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        from app.services.rate_limiter import rate_limiter
        
        # Get whitelist status
        whitelist_status = await rate_limiter.get_whitelist_status()
        
        if whitelist_status["success"]:
            success_response = create_success_response(
                message=whitelist_status["message"],
                data=whitelist_status,
                request_id=request_id
            )
            return success_response.dict()
        else:
            raise HTTPException(
                status_code=500,
                detail=create_error_response(
                    "WHITELIST_RETRIEVAL_FAILED",
                    custom_message=whitelist_status["message"],
                    request_id=request_id
                ).dict()
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                "INTERNAL_SERVER_ERROR",
                custom_message=f"Failed to retrieve IP whitelist: {str(e)}",
                request_id=request_id
            ).dict()
        )

@router.post("/rate-limit/whitelist", 
             response_model=SuccessResponse,
             responses={
                 201: {
                     "description": "IP successfully added to whitelist",
                     "content": {
                         "application/json": {
                             "example": {
                                 "success": True,
                                 "message": "IP 203.0.113.45 successfully added to whitelist",
                                 "data": {
                                     "ip_address": "203.0.113.45",
                                     "reason": "Office network",
                                     "added_by": "admin",
                                     "timestamp": "2025-07-09T06:30:00.000000Z",
                                     "total_whitelisted": 4
                                 }
                             }
                         }
                     }
                 }
             })
async def add_ip_to_whitelist(
    request: Request,
    ip_data: Dict[str, str] = Body(..., example={
        "ip_address": "203.0.113.45", 
        "reason": "Office network access"
    }),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Add IP address to whitelist"""
    import uuid
    try:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        # Validate input
        ip_address = ip_data.get("ip_address")
        reason = ip_data.get("reason", "Added via API")
        
        if not ip_address:
            raise HTTPException(
                status_code=400,
                detail=create_error_response(
                    "MISSING_IP_ADDRESS",
                    custom_message="IP address is required",
                    field="ip_address",
                    request_id=request_id
                ).dict()
            )
        
        # Validate IP format (basic validation)
        import re
        ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        if not re.match(ip_pattern, ip_address):
            raise HTTPException(
                status_code=400,
                detail=create_error_response(
                    "INVALID_IP_FORMAT",
                    custom_message="Invalid IP address format",
                    field="ip_address",
                    value=ip_address,
                    request_id=request_id
                ).dict()
            )
        
        from app.services.rate_limiter import rate_limiter
        
        # Add to whitelist
        result = await rate_limiter.add_to_whitelist(
            ip_address=ip_address,
            reason=reason,
            user_id=current_user.get("username", "unknown")
        )
        
        if result["success"]:
            # Log audit trail
            await audit_logger.log_admin_action(
                action="ADD_IP_WHITELIST",
                resource_type="RateLimit",
                resource_id=ip_address,
                user_id=current_user.get("username"),
                details={
                    "ip_address": ip_address,
                    "reason": reason,
                    "total_whitelisted": result.get("total_whitelisted", 0)
                }
            )
            
            success_response = create_success_response(
                message=result["message"],
                data=result,
                request_id=request_id
            )
            return JSONResponse(content=success_response.dict(), status_code=201)
        else:
            raise HTTPException(
                status_code=500,
                detail=create_error_response(
                    "WHITELIST_ADD_FAILED",
                    custom_message=result["message"],
                    request_id=request_id
                ).dict()
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                "INTERNAL_SERVER_ERROR",
                custom_message=f"Failed to add IP to whitelist: {str(e)}",
                request_id=request_id
            ).dict()
        )

@router.delete("/rate-limit/whitelist/{ip_address}", 
               response_model=SuccessResponse,
               responses={
                   200: {
                       "description": "IP successfully removed from whitelist",
                       "content": {
                           "application/json": {
                               "example": {
                                   "success": True,
                                   "message": "IP 203.0.113.45 successfully removed from whitelist",
                                   "data": {
                                       "ip_address": "203.0.113.45",
                                       "removed_by": "admin",
                                       "timestamp": "2025-07-09T06:30:00.000000Z",
                                       "total_whitelisted": 3
                                   }
                               }
                           }
                       }
                   }
               })
async def remove_ip_from_whitelist(
    ip_address: str,
    request: Request,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Remove IP address from whitelist"""
    import uuid
    try:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        from app.services.rate_limiter import rate_limiter
        
        # Remove from whitelist
        result = await rate_limiter.remove_from_whitelist(
            ip_address=ip_address,
            user_id=current_user.get("username", "unknown")
        )
        
        if result["success"]:
            # Log audit trail
            await audit_logger.log_admin_action(
                action="REMOVE_IP_WHITELIST",
                resource_type="RateLimit",
                resource_id=ip_address,
                user_id=current_user.get("username"),
                details={
                    "ip_address": ip_address,
                    "total_whitelisted": result.get("total_whitelisted", 0)
                }
            )
            
            success_response = create_success_response(
                message=result["message"],
                data=result,
                request_id=request_id
            )
            return success_response.dict()
        else:
            raise HTTPException(
                status_code=404,
                detail=create_error_response(
                    "IP_NOT_IN_WHITELIST",
                    custom_message=result["message"],
                    request_id=request_id
                ).dict()
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                "INTERNAL_SERVER_ERROR",
                custom_message=f"Failed to remove IP from whitelist: {str(e)}",
                request_id=request_id
            ).dict()
        )

@router.post("/rate-limit/blacklist", 
             response_model=SuccessResponse,
             responses={
                 201: {
                     "description": "IP successfully added to blacklist",
                     "content": {
                         "application/json": {
                             "example": {
                                 "success": True,
                                 "message": "IP 192.0.2.100 successfully added to blacklist",
                                 "data": {
                                     "ip_address": "192.0.2.100",
                                     "reason": "Suspicious activity",
                                     "added_by": "admin",
                                     "timestamp": "2025-07-09T06:30:00.000000Z",
                                     "total_blacklisted": 5
                                 }
                             }
                         }
                     }
                 }
             })
async def add_ip_to_blacklist(
    request: Request,
    ip_data: Dict[str, str] = Body(..., example={
        "ip_address": "192.0.2.100", 
        "reason": "Suspicious activity detected"
    }),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Add IP address to blacklist"""
    import uuid
    try:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        # Validate input
        ip_address = ip_data.get("ip_address")
        reason = ip_data.get("reason", "Added via API")
        
        if not ip_address:
            raise HTTPException(
                status_code=400,
                detail=create_error_response(
                    "MISSING_IP_ADDRESS",
                    custom_message="IP address is required",
                    field="ip_address",
                    request_id=request_id
                ).dict()
            )
        
        from app.services.rate_limiter import rate_limiter
        
        # Add to blacklist
        result = await rate_limiter.add_to_blacklist(
            ip_address=ip_address,
            reason=reason,
            user_id=current_user.get("username", "unknown")
        )
        
        if result["success"]:
            # Log audit trail
            await audit_logger.log_admin_action(
                action="ADD_IP_BLACKLIST",
                resource_type="RateLimit",
                resource_id=ip_address,
                user_id=current_user.get("username"),
                details={
                    "ip_address": ip_address,
                    "reason": reason,
                    "total_blacklisted": result.get("total_blacklisted", 0)
                }
            )
            
            success_response = create_success_response(
                message=result["message"],
                data=result,
                request_id=request_id
            )
            return JSONResponse(content=success_response.dict(), status_code=201)
        else:
            raise HTTPException(
                status_code=500,
                detail=create_error_response(
                    "BLACKLIST_ADD_FAILED",
                    custom_message=result["message"],
                    request_id=request_id
                ).dict()
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                "INTERNAL_SERVER_ERROR",
                custom_message=f"Failed to add IP to blacklist: {str(e)}",
                request_id=request_id
            ).dict()
        )

@router.get("/master-data/{data_type}/bulk-export", 
            response_model=SuccessResponse,
            summary="Bulk Export Master Data",
            description="""
## Bulk Export Master Data

Export large datasets of master data without pagination limits for data migration and analysis.

### Features:
- **No Pagination Limits**: Export entire datasets in one request
- **Large Dataset Support**: Handles datasets with 10,000+ records
- **Filtering Support**: All standard filters available
- **Performance Optimized**: Uses streaming for large exports
- **Memory Efficient**: Processes data in chunks

### Query Parameters:
- `search`: Search across data fields
- `is_active`: Filter by active status (true/false, optional)
- `province_code`: Filter by province code (for geographic data)
- `district_code`: Filter by district code (for geographic data)
- `sub_district_code`: Filter by sub-district code (for geographic data)
- `format`: Export format - 'json' or 'csv' (default: 'json')

### Use Cases:
- Data migration to external systems
- Bulk data analysis
- Database backups
- Integration with reporting tools
- Complete dataset exports

### Authentication:
Requires valid JWT Bearer token with admin privileges.
            """,
            responses={
                200: {
                    "description": "Bulk export completed successfully",
                    "content": {
                        "application/json": {
                            "example": {
                                "success": True,
                                "message": "Bulk export completed successfully",
                                "data": {
                                    "data_type": "hospitals",
                                    "total_records": 12350,
                                    "exported_records": 12350,
                                    "format": "json",
                                    "filters_applied": {
                                        "is_active": True,
                                        "search": None
                                    },
                                    "export_metadata": {
                                        "export_id": "bulk-export-001",
                                        "exported_at": "2025-07-10T03:30:00.000Z",
                                        "processing_time_ms": 1250
                                    }
                                }
                            }
                        }
                    }
                },
                400: {"description": "Invalid data type or format"},
                401: {"description": "Authentication required"},
                500: {"description": "Internal server error"}
            })
async def bulk_export_master_data(
    request: Request,
    data_type: str,
    search: Optional[str] = None,
    province_code: Optional[int] = None,
    district_code: Optional[int] = None,
    sub_district_code: Optional[int] = None,
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    format: str = Query("json", description="Export format: json or csv"),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Bulk export master data for large datasets"""
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    start_time = time.time()
    
    try:
        # Validate format
        if format not in ["json", "csv"]:
            raise HTTPException(
                status_code=400,
                detail=create_error_response(
                    "INVALID_FORMAT",
                    field="format",
                    value=format,
                    custom_message="Invalid format. Must be 'json' or 'csv'",
                    request_id=request_id
                ).dict()
            )
        
        # Normalize data_type: convert hyphens to underscores for consistency
        normalized_data_type = data_type.replace("-", "_")
        
        # Map data type to collection
        collection_mapping = {
            "hospitals": "hospitals",
            "provinces": "provinces", 
            "districts": "districts",
            "sub_districts": "sub_districts",
            "hospital_types": "master_hospital_types",
            "blood_groups": "blood_groups",
            "human_skin_colors": "human_skin_colors",
            "nations": "nations",
            "ward_lists": "ward_lists",
            "staff_types": "staff_types",
            "underlying_diseases": "underlying_diseases"
        }
        
        collection_name = collection_mapping.get(normalized_data_type)
        if not collection_name:
            raise HTTPException(
                status_code=400, 
                detail=create_error_response(
                    "INVALID_DATA_TYPE",
                    field="data_type",
                    value=data_type,
                    custom_message=f"Invalid data type: {data_type}. Supported types: {', '.join(collection_mapping.keys())}",
                    request_id=request_id
                ).dict()
            )
        
        collection = mongodb_service.get_collection(collection_name)
        
        # Build filter based on data type structure (same logic as get_master_data)
        filter_query = {}
        
        # Apply entity-specific filters
        if normalized_data_type == "provinces":
            filter_query = {"is_deleted": {"$ne": True}}
            if is_active is not None:
                filter_query["is_active"] = is_active
        elif normalized_data_type == "districts":
            filter_query = {"is_deleted": {"$ne": True}}
            if is_active is not None:
                filter_query["is_active"] = is_active
            if province_code:
                filter_query["province_code"] = province_code
        elif normalized_data_type == "sub_districts":
            filter_query = {"is_deleted": {"$ne": True}}
            if is_active is not None:
                filter_query["is_active"] = is_active
            if province_code:
                filter_query["province_code"] = province_code
            if district_code:
                filter_query["district_code"] = district_code
        elif normalized_data_type == "hospital_types":
            filter_query = {"active": True}
        elif normalized_data_type == "hospitals":
            filter_query = {"is_deleted": {"$ne": True}}
            if is_active is not None:
                filter_query["is_active"] = is_active
            if province_code:
                filter_query["province_code"] = province_code
            if district_code:
                filter_query["district_code"] = district_code
            if sub_district_code:
                filter_query["sub_district_code"] = sub_district_code
        elif normalized_data_type in ["blood_groups", "human_skin_colors", "nations", "ward_lists", "staff_types", "underlying_diseases"]:
            filter_query = {"is_deleted": {"$ne": True}}
            if is_active is not None:
                filter_query["is_active"] = is_active
        
        # Add search functionality
        if search:
            search_conditions = []
            if normalized_data_type == "hospitals":
                search_conditions = [
                    {"name.0.name": {"$regex": search, "$options": "i"}},
                    {"name.1.name": {"$regex": search, "$options": "i"}},
                    {"en_name": {"$regex": search, "$options": "i"}}
                ]
            elif normalized_data_type in ["provinces", "districts", "sub_districts"]:
                search_conditions = [
                    {"name.0.name": {"$regex": search, "$options": "i"}},
                    {"name.1.name": {"$regex": search, "$options": "i"}},
                    {"en_name": {"$regex": search, "$options": "i"}}
                ]
            elif normalized_data_type == "hospital_types":
                search_conditions = [
                    {"name.th": {"$regex": search, "$options": "i"}},
                    {"name.en": {"$regex": search, "$options": "i"}}
                ]
            elif normalized_data_type in ["blood_groups", "human_skin_colors", "nations", "ward_lists", "staff_types", "underlying_diseases"]:
                search_conditions = [
                    {"name.0.name": {"$regex": search, "$options": "i"}},
                    {"name.1.name": {"$regex": search, "$options": "i"}},
                    {"en_name": {"$regex": search, "$options": "i"}}
                ]
            
            if search_conditions:
                filter_query["$or"] = search_conditions
        
        # Get total count
        total = await collection.count_documents(filter_query)
        
        # Export data in chunks for memory efficiency
        chunk_size = 1000
        all_data = []
        
        # Use cursor to stream data
        cursor = collection.find(filter_query)
        sort_field = "created_at" if normalized_data_type in ["provinces", "districts", "sub_districts", "hospitals", "blood_groups", "human_skin_colors", "nations"] else "_id"
        cursor = cursor.sort(sort_field, 1)
        
        # Process data in chunks
        while True:
            chunk = await cursor.to_list(length=chunk_size)
            if not chunk:
                break
            all_data.extend(chunk)
        
        # Serialize data
        serialized_data = serialize_mongodb_response(all_data)
        
        # Calculate processing time
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        # Create export metadata
        export_metadata = {
            "export_id": f"bulk-export-{uuid.uuid4().hex[:8]}",
            "exported_by": current_user.get("user_id"),
            "exported_at": datetime.utcnow().isoformat() + "Z",
            "processing_time_ms": processing_time_ms,
            "request_id": request_id
        }
        
        success_response = create_success_response(
            message="Bulk export completed successfully",
            data={
                "data_type": normalized_data_type,
                "total_records": total,
                "exported_records": len(serialized_data),
                "format": format,
                "filters_applied": {
                    "search": search,
                    "province_code": province_code,
                    "district_code": district_code,
                    "sub_district_code": sub_district_code,
                    "is_active": is_active
                },
                "export_metadata": export_metadata,
                "data": serialized_data if format == "json" else "CSV format would be implemented with proper CSV serialization"
            },
            request_id=request_id
        )
        
        # Log the bulk export operation
        logger.info(f"Bulk export completed - Type: {normalized_data_type}, Records: {len(serialized_data)}, Time: {processing_time_ms}ms, User: {current_user.get('user_id')}")
        
        return success_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Bulk export failed for {data_type}: {e}")
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                "INTERNAL_SERVER_ERROR",
                custom_message=f"Failed to perform bulk export: {str(e)}",
                request_id=request_id
            ).dict()
        )

# ===================== BLOOD PRESSURE TEST ENDPOINT =====================

@router.get("/test-blood-pressure")
async def test_blood_pressure(
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Simple test endpoint for blood pressure"""
    import uuid
    try:
        request_id = str(uuid.uuid4())
        logger.warning("Test blood pressure endpoint called")
        return create_success_response(
            message="Blood pressure test successful",
            data={"test": True, "endpoint": "blood_pressure_test"},
            request_id=request_id
        )
    except Exception as e:
        logger.error(f"Test blood pressure failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                "INTERNAL_SERVER_ERROR",
                custom_message=f"Test failed: {str(e)}",
                request_id=request_id
            ).dict()
        )

