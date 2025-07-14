import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, Depends, Request, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from bson import ObjectId
from app.services.mongo import mongodb_service
from app.services.auth import require_auth
from app.services.audit_logger import audit_logger
from app.services.fhir_r5_service import fhir_service
from app.utils.json_encoder import serialize_mongodb_response
from app.utils.error_definitions import create_error_response, create_success_response
from config import settings, logger

router = APIRouter(prefix="/api/ava4", tags=["ava4"])

# Response Models for Swagger Documentation
class MedicalHistoryCollection(BaseModel):
    """Medical history collection information"""
    name: str = Field(..., description="Collection display name")
    description: str = Field(..., description="Collection description")
    record_count: int = Field(..., description="Number of records in collection")
    status: str = Field(..., description="Collection status (active/inactive)")
    last_updated: Optional[str] = Field(None, description="Last update timestamp")
    data_fields: List[str] = Field(..., description="Available data fields")

class MedicalHistoryCollectionsResponse(BaseModel):
    """Response model for medical history collections overview"""
    success: bool = Field(True, description="Request success status")
    message: str = Field(..., description="Response message")
    data: Dict[str, Any] = Field(..., description="Collections data")

class PatientMedicalHistoryResponse(BaseModel):
    """Response model for patient medical history"""
    success: bool = Field(True, description="Request success status")
    message: str = Field(..., description="Response message")
    data: Dict[str, Any] = Field(..., description="Patient medical history data")

class MedicalTrendsResponse(BaseModel):
    """Response model for medical trends analysis"""
    success: bool = Field(True, description="Request success status")
    message: str = Field(..., description="Response message")
    data: Dict[str, Any] = Field(..., description="Medical trends data with analytics")

class MedicalAnalyticsResponse(BaseModel):
    """Response model for medical analytics"""
    success: bool = Field(True, description="Request success status")
    message: str = Field(..., description="Response message")
    data: Dict[str, Any] = Field(..., description="Medical analytics data")

class Ava4DataRequest(BaseModel):
    timestamp: datetime
    device_id: str  # MAC address
    type: str  # "WEIGHT", "BLOOD_PRESSURE", "TEMPERATURE", etc.
    data: Dict[str, Any]

class Ava4DataResponse(BaseModel):
    success: bool
    message: str
    observation_id: Optional[str] = None

class Ava4DeviceCreate(BaseModel):
    """Model for creating a new AVA4 device"""
    mac_address: str = Field(..., description="MAC address of the AVA4 device", min_length=17, max_length=17)
    box_name: str = Field(..., description="Display name for the AVA4 box", min_length=1, max_length=100)
    model: str = Field(default="AVA4", description="Device model")
    imei: Optional[str] = Field(None, description="IMEI of the device", min_length=15, max_length=15)
    serial_number: Optional[str] = Field(None, description="Serial number of the device")
    firmware_version: Optional[str] = Field(None, description="Firmware version")
    location: Optional[str] = Field(None, description="Physical location of the device")
    status: str = Field(default="inactive", description="Device status")
    patient_id: Optional[str] = Field(None, description="Patient ID to assign the device to")
    is_active: bool = Field(default=True, description="Whether the device is active")

class Ava4DeviceUpdate(BaseModel):
    """Model for updating an AVA4 device"""
    box_name: Optional[str] = Field(None, description="Display name for the AVA4 box", min_length=1, max_length=100)
    model: Optional[str] = Field(None, description="Device model")
    imei: Optional[str] = Field(None, description="IMEI of the device", min_length=15, max_length=15)
    serial_number: Optional[str] = Field(None, description="Serial number of the device")
    firmware_version: Optional[str] = Field(None, description="Firmware version")
    location: Optional[str] = Field(None, description="Physical location of the device")
    status: Optional[str] = Field(None, description="Device status")
    patient_id: Optional[str] = Field(None, description="Patient ID to assign the device to")
    is_active: Optional[bool] = Field(None, description="Whether the device is active")

@router.post("/data", response_model=Ava4DataResponse)
async def receive_ava4_data(
    data: Ava4DataRequest,
    request: Request,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Receive data from AVA4 device"""
    try:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        # Validate device exists
        collection = mongodb_service.get_collection("amy_boxes")
        device = await collection.find_one({"mac_address": data.device_id})
        
        if not device:
            raise HTTPException(
                status_code=404,
                detail=create_error_response(
                    "DEVICE_NOT_FOUND",
                    field="device_id",
                    value=data.device_id,
                    custom_message=f"AVA4 device with MAC address '{data.device_id}' not found",
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
        
        # Route to appropriate medical history collection (legacy)
        await route_to_medical_history(data, device.get("patient_id"))
        
        # Create FHIR R5 Observations (new implementation)
        await create_fhir_observations_from_ava4(data, device.get("patient_id"), data.device_id)
        
        # Log audit trail
        await audit_logger.log_device_data_received(
            device_id=data.device_id,
            device_type="AVA4",
            data_type=data.type,
            observation_id=observation_id,
            user_id=current_user.get("username")
        )
        
        logger.info(f"AVA4 data received: {data.type} from {data.device_id}")
        
        # Create success response
        success_response = create_success_response(
            message="AVA4 data received successfully",
            data={
                "observation_id": observation_id,
                "device_id": data.device_id,
                "data_type": data.type,
                "timestamp": data.timestamp.isoformat()
            },
            request_id=request_id
        )
        return success_response.dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"AVA4 data processing error: {e}")
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                "INTERNAL_SERVER_ERROR",
                custom_message=f"Failed to process AVA4 data: {str(e)}",
                request_id=request.headers.get("X-Request-ID") or str(uuid.uuid4())
            ).dict()
        )

async def route_to_medical_history(data: Ava4DataRequest, patient_id: str):
    """Route data to appropriate medical history collection"""
    try:
        collection_name = None
        
        # Map data type to collection
        if data.type == "BLOOD_PRESSURE":
            collection_name = "blood_pressure_histories"
        elif data.type == "BLOOD_SUGAR":
            collection_name = "blood_sugar_histories"
        elif data.type == "TEMPERATURE":
            collection_name = "temprature_data_histories"
        elif data.type == "WEIGHT":
            collection_name = "body_data_histories"
        elif data.type == "CREATININE":
            collection_name = "creatinine_histories"
        elif data.type == "LIPID":
            collection_name = "lipid_histories"
        
        if collection_name:
            collection = mongodb_service.get_collection(collection_name)
            
            # Create history entry
            history_entry = {
                "patient_id": ObjectId(patient_id),
                "data": [{
                    **data.data,
                    "timestamp": data.timestamp,
                    "device_id": data.device_id,
                    "device_type": "AVA4"
                }],
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            await collection.insert_one(history_entry)
            logger.info(f"Data routed to {collection_name}")
            
    except Exception as e:
        logger.error(f"Failed to route to medical history: {e}")

async def create_fhir_observations_from_ava4(data: Ava4DataRequest, patient_id: str, device_id: str):
    """Create FHIR R5 Observations from AVA4 data"""
    try:
        # Create a simplified MQTT payload structure for the FHIR service
        mqtt_payload = {
            "time": int(data.timestamp.timestamp()),
            "mac": device_id,
            "data": {
                "attribute": data.type,
                "device": "AVA4 Device",
                "value": {
                    "device_list": [
                        {
                            "scan_time": int(data.timestamp.timestamp()),
                            "ble_addr": device_id,
                            **data.data  # Include all the data from AVA4
                        }
                    ]
                }
            }
        }
        
        # Transform to FHIR Observations
        observations = await fhir_service.transform_ava4_mqtt_to_fhir(
            mqtt_payload=mqtt_payload,
            patient_id=patient_id,
            device_id=device_id
        )
        
        # Create FHIR resources
        for obs_data in observations:
            await fhir_service.create_fhir_resource(
                resource_type="Observation",
                resource_data=obs_data,
                source_system="ava4_api",
                device_mac_address=device_id
            )
        
        logger.info(f"Created {len(observations)} FHIR Observations from AVA4 data")
        
    except Exception as e:
        logger.error(f"Failed to create FHIR observations from AVA4: {e}")

@router.get("/devices")
async def get_ava4_devices(
    request: Request,
    limit: int = 100,
    skip: int = 0,
    active_only: Optional[bool] = None,
    patient_id: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    include_patient_info: bool = False,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get AVA4 devices with advanced filtering and search"""
    try:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        device_collection = mongodb_service.get_collection("amy_boxes")
        
        # Build filter query
        filter_query = {}
        
        # Active/deleted filter - only apply if explicitly set
        if active_only is True:
            filter_query["is_active"] = True
            filter_query["is_deleted"] = {"$ne": True}
        elif active_only is False:
            # Show all devices including inactive and deleted
            pass
        else:
            # Default behavior when active_only is None - show only non-deleted
            filter_query["is_deleted"] = {"$ne": True}
        
        # Patient filter
        if patient_id:
            try:
                patient_obj_id = ObjectId(patient_id)
                filter_query["patient_id"] = patient_obj_id
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
        
        # Status filter
        if status:
            filter_query["status"] = status
        
        # Search functionality
        if search:
            search_regex = {"$regex": search, "$options": "i"}
            filter_query["$or"] = [
                {"box_name": search_regex},
                {"mac_address": search_regex},
                {"model": search_regex},
                {"location": search_regex},
                {"imei": search_regex},
                {"serial_number": search_regex}
            ]
        
        # Build sort
        sort_direction = 1 if sort_order.lower() == "asc" else -1
        valid_sort_fields = ["created_at", "updated_at", "box_name", "mac_address", "status", "model"]
        if sort_by not in valid_sort_fields:
            sort_by = "created_at"
        
        # Get total count
        total_count = await device_collection.count_documents(filter_query)
        
        # Get devices with pagination and sorting
        cursor = device_collection.find(filter_query).sort(sort_by, sort_direction).skip(skip).limit(limit)
        devices = await cursor.to_list(length=limit)
        
        # Serialize devices
        serialized_devices = serialize_mongodb_response(devices)
        
        # Add patient information if requested
        if include_patient_info and isinstance(serialized_devices, list):
            patient_collection = mongodb_service.get_collection("patients")
            for device in serialized_devices:
                if isinstance(device, dict) and device.get("patient_id"):
                    try:
                        patient_obj_id = ObjectId(device["patient_id"])
                        patient = await patient_collection.find_one({"_id": patient_obj_id})
                        if patient:
                            patient_info = serialize_mongodb_response(patient)
                            device["patient_info"] = {
                                "patient_name": f"{patient_info.get('first_name', '')} {patient_info.get('last_name', '')}".strip(),
                                "hn": patient_info.get("hn"),
                                "phone": patient_info.get("phone"),
                                "is_active": patient_info.get("is_active")
                            }
                    except Exception:
                        device["patient_info"] = None
        
        # Calculate pagination info
        total_pages = (total_count + limit - 1) // limit if limit > 0 else 1
        current_page = (skip // limit) + 1 if limit > 0 else 1
        has_next = (skip + len(serialized_devices)) < total_count
        has_prev = skip > 0
        
        success_response = create_success_response(
            message="AVA4 devices retrieved successfully",
            data={
                "devices": serialized_devices,
                "pagination": {
                    "total": total_count,
                    "limit": limit,
                    "skip": skip,
                    "current_page": current_page,
                    "total_pages": total_pages,
                    "has_next": has_next,
                    "has_prev": has_prev,
                    "returned_count": len(serialized_devices)
                },
                "filters": {
                    "active_only": active_only,
                    "patient_id": patient_id,
                    "status": status,
                    "search": search,
                    "sort_by": sort_by,
                    "sort_order": sort_order
                },
                "statistics": {
                    "total_devices": total_count,
                    "returned_devices": len(serialized_devices)
                }
            },
            request_id=request_id
        )
        
        return success_response.dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting AVA4 devices: {e}")
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                "INTERNAL_SERVER_ERROR",
                custom_message=f"Failed to retrieve devices: {str(e)}",
                request_id=request.headers.get("X-Request-ID") or str(uuid.uuid4())
            ).dict()
        )

@router.get("/devices/table")
async def get_ava4_devices_table(
    request: Request,
    page: int = 1,
    limit: int = 25,
    active_only: Optional[bool] = None,
    patient_id: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    columns: Optional[str] = None,
    export_format: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get AVA4 devices in table format with advanced features"""
    try:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        # Calculate skip from page
        skip = (page - 1) * limit if page > 0 else 0
        
        # Define available columns
        available_columns = [
            "box_name", "mac_address", "model", "status", "location", "imei",
            "serial_number", "firmware_version", "patient_info", "is_active", 
            "created_at", "updated_at"
        ]
        
        # Parse requested columns
        selected_columns = available_columns
        if columns:
            requested_cols = [col.strip() for col in columns.split(",")]
            selected_columns = [col for col in requested_cols if col in available_columns]
        
        device_collection = mongodb_service.get_collection("amy_boxes")
        
        # Build filter query
        filter_query = {}
        
        # Active/deleted filter - only apply if explicitly set
        if active_only is True:
            filter_query["is_active"] = True
            filter_query["is_deleted"] = {"$ne": True}
        elif active_only is False:
            # Show all devices including inactive and deleted
            pass
        else:
            # Default behavior when active_only is None - show only non-deleted
            filter_query["is_deleted"] = {"$ne": True}
        
        if patient_id:
            try:
                filter_query["patient_id"] = ObjectId(patient_id)
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
        
        if status:
            filter_query["status"] = status
        
        if search:
            search_regex = {"$regex": search, "$options": "i"}
            filter_query["$or"] = [
                {"box_name": search_regex},
                {"mac_address": search_regex},
                {"model": search_regex},
                {"location": search_regex},
                {"imei": search_regex},
                {"serial_number": search_regex}
            ]
        
        # Build sort
        sort_direction = 1 if sort_order.lower() == "asc" else -1
        valid_sort_fields = ["created_at", "updated_at", "box_name", "mac_address", "status", "model"]
        if sort_by not in valid_sort_fields:
            sort_by = "created_at"
        
        # Get total count
        total_count = await device_collection.count_documents(filter_query)
        
        # Get devices
        cursor = device_collection.find(filter_query).sort(sort_by, sort_direction).skip(skip).limit(limit)
        devices = await cursor.to_list(length=limit)
        
        # Serialize and add patient info
        serialized_devices = serialize_mongodb_response(devices)
        patient_collection = mongodb_service.get_collection("patients")
        
        # Prepare table data
        table_data = []
        if isinstance(serialized_devices, list):
            for device in serialized_devices:
                if isinstance(device, dict):
                    row = {}
                    
                    # Add selected columns
                    for col in selected_columns:
                        if col == "patient_info" and device.get("patient_id"):
                            try:
                                patient_obj_id = ObjectId(device["patient_id"])
                                patient = await patient_collection.find_one({"_id": patient_obj_id})
                                if patient:
                                    patient_info = serialize_mongodb_response(patient)
                                    row["patient_info"] = {
                                        "patient_name": f"{patient_info.get('first_name', '')} {patient_info.get('last_name', '')}".strip(),
                                        "hn": patient_info.get("hn"),
                                        "phone": patient_info.get("phone")
                                    }
                                else:
                                    row["patient_info"] = None
                            except Exception:
                                row["patient_info"] = None
                        else:
                            row[col] = device.get(col)
                    
                    table_data.append(row)
        
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
                "download_url": f"/api/ava4/devices/export?format={export_format}&filters={request.url.query}"
            }
        
        success_response = create_success_response(
            message="AVA4 devices table data retrieved successfully",
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
                    "patient_id": patient_id,
                    "status": status,
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
        logger.error(f"Error getting AVA4 devices table: {e}")
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                "INTERNAL_SERVER_ERROR",
                custom_message=f"Failed to retrieve devices table: {str(e)}",
                request_id=request.headers.get("X-Request-ID") or str(uuid.uuid4())
            ).dict()
        )

@router.get("/devices/{device_id}")
async def get_ava4_device(
    device_id: str,
    request: Request,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get specific AVA4 device"""
    try:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        collection = mongodb_service.get_collection("amy_boxes")
        device = await collection.find_one({"_id": ObjectId(device_id)})
        
        if not device:
            raise HTTPException(
                status_code=404,
                detail=create_error_response(
                    "DEVICE_NOT_FOUND",
                    field="device_id",
                    value=device_id,
                    custom_message=f"AVA4 device with ID '{device_id}' not found",
                    request_id=request_id
                ).dict()
            )
        
        # Serialize ObjectIds
        serialized_device = serialize_mongodb_response(device)
        
        success_response = create_success_response(
            message="AVA4 device retrieved successfully",
            data={"device": serialized_device},
            request_id=request_id
        )
        return success_response.dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting AVA4 device: {e}")
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                "INTERNAL_SERVER_ERROR",
                custom_message=f"Failed to retrieve AVA4 device: {str(e)}",
                request_id=request.headers.get("X-Request-ID") or str(uuid.uuid4())
            ).dict()
        )

@router.post("/devices")
async def create_ava4_device(
    device_data: Ava4DeviceCreate,
    request: Request,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Create a new AVA4 device"""
    try:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        # Check if MAC address already exists
        device_collection = mongodb_service.get_collection("amy_boxes")
        existing_device = await device_collection.find_one({"mac_address": device_data.mac_address})
        
        if existing_device:
            raise HTTPException(
                status_code=400,
                detail=create_error_response(
                    "DEVICE_ALREADY_EXISTS",
                    field="mac_address",
                    value=device_data.mac_address,
                    custom_message=f"AVA4 device with MAC address '{device_data.mac_address}' already exists",
                    request_id=request_id
                ).dict()
            )
        
        # Validate patient if provided
        patient_obj_id = None
        if device_data.patient_id:
            try:
                patient_obj_id = ObjectId(device_data.patient_id)
                patient_collection = mongodb_service.get_collection("patients")
                patient = await patient_collection.find_one({"_id": patient_obj_id})
                
                if not patient:
                    raise HTTPException(
                        status_code=404,
                        detail=create_error_response(
                            "PATIENT_NOT_FOUND",
                            field="patient_id",
                            value=device_data.patient_id,
                            custom_message=f"Patient with ID '{device_data.patient_id}' not found",
                            request_id=request_id
                        ).dict()
                    )
            except Exception as e:
                raise HTTPException(
                    status_code=400,
                    detail=create_error_response(
                        "INVALID_PATIENT_ID",
                        field="patient_id",
                        value=device_data.patient_id,
                        custom_message=f"Invalid patient ID format: {str(e)}",
                        request_id=request_id
                    ).dict()
                )
        
        # Create device document
        device_doc = {
            "mac_address": device_data.mac_address,
            "box_name": device_data.box_name,
            "model": device_data.model,
            "imei": device_data.imei,
            "serial_number": device_data.serial_number,
            "firmware_version": device_data.firmware_version,
            "location": device_data.location,
            "status": device_data.status,
            "is_active": device_data.is_active,
            "is_deleted": False,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "created_by": current_user.get("username")
        }
        
        # Add patient_id if provided
        if patient_obj_id:
            device_doc["patient_id"] = patient_obj_id
        
        # Insert device
        insert_result = await device_collection.insert_one(device_doc)
        device_id = str(insert_result.inserted_id)
        
        # Log audit trail
        await audit_logger.log_admin_action(
            action="CREATE",
            resource_type="AVA4Device",
            resource_id=device_id,
            user_id=current_user.get("username") or "unknown",
            details={
                "device_mac": device_data.mac_address,
                "box_name": device_data.box_name,
                "patient_id": device_data.patient_id,
                "model": device_data.model
            }
        )
        
        # Get created device with serialization
        created_device = await device_collection.find_one({"_id": insert_result.inserted_id})
        serialized_device = serialize_mongodb_response(created_device)
        
        success_response = create_success_response(
            message="AVA4 device created successfully",
            data={
                "device": serialized_device,
                "device_id": device_id
            },
            request_id=request_id
        )
        
        return success_response.dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating AVA4 device: {e}")
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                "INTERNAL_SERVER_ERROR",
                custom_message=f"Failed to create device: {str(e)}",
                request_id=request.headers.get("X-Request-ID") or str(uuid.uuid4())
            ).dict()
        )

@router.put("/devices/{device_id}")
async def update_ava4_device(
    device_id: str,
    device_data: Ava4DeviceUpdate,
    request: Request,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Update an AVA4 device"""
    try:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
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
        device_collection = mongodb_service.get_collection("amy_boxes")
        device = await device_collection.find_one({"_id": device_obj_id})
        
        if not device:
            raise HTTPException(
                status_code=404,
                detail=create_error_response(
                    "DEVICE_NOT_FOUND",
                    field="device_id",
                    value=device_id,
                    custom_message=f"AVA4 device with ID '{device_id}' not found",
                    request_id=request_id
                ).dict()
            )
        
        # Build update document
        update_fields = {"updated_at": datetime.utcnow(), "updated_by": current_user.get("username")}
        
        # Add fields that have values
        if device_data.box_name is not None:
            update_fields["box_name"] = device_data.box_name
        if device_data.model is not None:
            update_fields["model"] = device_data.model
        if device_data.imei is not None:
            update_fields["imei"] = device_data.imei
        if device_data.serial_number is not None:
            update_fields["serial_number"] = device_data.serial_number
        if device_data.firmware_version is not None:
            update_fields["firmware_version"] = device_data.firmware_version
        if device_data.location is not None:
            update_fields["location"] = device_data.location
        if device_data.status is not None:
            update_fields["status"] = device_data.status
        if device_data.is_active is not None:
            update_fields["is_active"] = device_data.is_active
        
        # Handle patient_id if provided
        if device_data.patient_id is not None:
            if device_data.patient_id == "":
                # Remove patient assignment
                update_fields["$unset"] = {"patient_id": ""}
            else:
                try:
                    patient_obj_id = ObjectId(device_data.patient_id)
                    patient_collection = mongodb_service.get_collection("patients")
                    patient = await patient_collection.find_one({"_id": patient_obj_id})
                    
                    if not patient:
                        raise HTTPException(
                            status_code=404,
                            detail=create_error_response(
                                "PATIENT_NOT_FOUND",
                                field="patient_id",
                                value=device_data.patient_id,
                                custom_message=f"Patient with ID '{device_data.patient_id}' not found",
                                request_id=request_id
                            ).dict()
                        )
                    
                    update_fields["patient_id"] = patient_obj_id
                except Exception as e:
                    raise HTTPException(
                        status_code=400,
                        detail=create_error_response(
                            "INVALID_PATIENT_ID",
                            field="patient_id",
                            value=device_data.patient_id,
                            custom_message=f"Invalid patient ID format: {str(e)}",
                            request_id=request_id
                        ).dict()
                    )
        
        # Update device
        update_result = await device_collection.update_one(
            {"_id": device_obj_id},
            {"$set": update_fields}
        )
        
        if update_result.modified_count == 0:
            raise HTTPException(
                status_code=500,
                detail=create_error_response(
                    "UPDATE_FAILED",
                    custom_message="Failed to update device",
                    request_id=request_id
                ).dict()
            )
        
        # Log audit trail
        await audit_logger.log_admin_action(
            action="UPDATE",
            resource_type="AVA4Device",
            resource_id=device_id,
            user_id=current_user.get("username") or "unknown",
            details={
                "device_mac": device.get("mac_address"),
                "updated_fields": list(update_fields.keys()),
                "patient_id": device_data.patient_id
            }
        )
        
        # Get updated device
        updated_device = await device_collection.find_one({"_id": device_obj_id})
        serialized_device = serialize_mongodb_response(updated_device)
        
        success_response = create_success_response(
            message="AVA4 device updated successfully",
            data={
                "device": serialized_device,
                "device_id": device_id
            },
            request_id=request_id
        )
        
        return success_response.dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating AVA4 device: {e}")
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                "INTERNAL_SERVER_ERROR",
                custom_message=f"Failed to update device: {str(e)}",
                request_id=request.headers.get("X-Request-ID") or str(uuid.uuid4())
            ).dict()
        )

@router.delete("/devices/{device_id}")
async def delete_ava4_device(
    device_id: str,
    request: Request,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Delete (soft delete) an AVA4 device"""
    try:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
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
        device_collection = mongodb_service.get_collection("amy_boxes")
        device = await device_collection.find_one({"_id": device_obj_id})
        
        if not device:
            raise HTTPException(
                status_code=404,
                detail=create_error_response(
                    "DEVICE_NOT_FOUND",
                    field="device_id",
                    value=device_id,
                    custom_message=f"AVA4 device with ID '{device_id}' not found",
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
            resource_type="AVA4Device",
            resource_id=device_id,
            user_id=current_user.get("username") or "unknown",
            details={
                "device_mac": device.get("mac_address"),
                "box_name": device.get("box_name"),
                "patient_id": str(device.get("patient_id")) if device.get("patient_id") else None
            }
        )
        
        success_response = create_success_response(
            message="AVA4 device deleted successfully",
            data={"device_id": device_id},
            request_id=request_id
        )
        
        return success_response.dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting AVA4 device: {e}")
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                "INTERNAL_SERVER_ERROR",
                custom_message=f"Failed to delete device: {str(e)}",
                request_id=request.headers.get("X-Request-ID") or str(uuid.uuid4())
            ).dict()
        )



@router.get("/patient-info")
async def get_patient_info_by_mac(
    mac_address: str,
    request: Request,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get patient basic information by AVA4 device MAC address for device mapping"""
    try:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        # Find device by MAC address
        device_collection = mongodb_service.get_collection("amy_boxes")
        device = await device_collection.find_one({"mac_address": mac_address})
        
        if not device:
            raise HTTPException(
                status_code=404,
                detail=create_error_response(
                    "DEVICE_NOT_FOUND",
                    field="mac_address",
                    value=mac_address,
                    custom_message=f"AVA4 device with MAC address '{mac_address}' not found",
                    request_id=request_id
                ).dict()
            )
        
        # Check if device has patient assignment
        patient_id = device.get("patient_id")
        if not patient_id:
            raise HTTPException(
                status_code=404,
                detail=create_error_response(
                    "PATIENT_NOT_ASSIGNED",
                    field="patient_id",
                    value=None,
                    custom_message=f"No patient assigned to AVA4 device '{mac_address}'",
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
            # Device has patient_id but patient doesn't exist - data integrity issue
            logger.warning(f"Data integrity issue: AVA4 device {mac_address} references non-existent patient {patient_obj_id}")
            
            # Return device info with warning
            device_info = serialize_mongodb_response(device)
            success_response = create_success_response(
                message="AVA4 device found but patient data unavailable",
                data={
                    "device": device_info,
                    "patient": None,
                    "warning": "Patient data not found - possible data integrity issue"
                },
                request_id=request_id
            )
            return success_response.dict()
        
        # Check if patient is active
        if not patient.get("is_active", True):
            raise HTTPException(
                status_code=404,
                detail=create_error_response(
                    "PATIENT_INACTIVE",
                    field="patient_id",
                    value=str(patient_obj_id),
                    custom_message=f"Patient assigned to AVA4 device '{mac_address}' is inactive",
                    request_id=request_id
                ).dict()
            )
        
        # Prepare response data
        device_info = serialize_mongodb_response(device)
        patient_info = serialize_mongodb_response(patient)
        
        # Create patient basic info (excluding sensitive data)
        patient_basic = {
            "patient_id": patient_info.get("_id"),
            "hn": patient_info.get("hn"),
            "first_name": patient_info.get("first_name"),
            "last_name": patient_info.get("last_name"),
            "gender": patient_info.get("gender"),
            "birth_date": patient_info.get("birth_date"),
            "age": patient_info.get("age"),
            "phone": patient_info.get("phone"),
            "is_active": patient_info.get("is_active", True),
            "created_at": patient_info.get("created_at"),
            "updated_at": patient_info.get("updated_at")
        }
        
        # Log audit trail
        await audit_logger.log_admin_action(
            action="READ",
            resource_type="Patient",
            resource_id=str(patient_obj_id),
            user_id=current_user.get("username"),
            details={
                "access_method": "ava4_device_mapping",
                "device_mac": mac_address,
                "device_type": "AVA4"
            }
        )
        
        success_response = create_success_response(
            message="Patient information retrieved successfully",
            data={
                "device": {
                    "device_id": device_info.get("_id"),
                    "mac_address": device_info.get("mac_address"),
                    "box_name": device_info.get("box_name"),
                    "model": device_info.get("model"),
                    "status": device_info.get("status"),
                    "is_active": device_info.get("is_active"),
                    "patient_id": device_info.get("patient_id")
                },
                "patient": patient_basic,
                "mapping_info": {
                    "mapped_at": device_info.get("updated_at"),
                    "device_type": "AVA4",
                    "mapping_status": "active"
                }
            },
            request_id=request_id
        )
        
        return success_response.dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting AVA4 patient info: {e}")
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                "INTERNAL_SERVER_ERROR",
                custom_message=f"Failed to retrieve patient information: {str(e)}",
                request_id=request.headers.get("X-Request-ID") or str(uuid.uuid4())
            ).dict()
        )

@router.get("/sub-devices")
async def get_ava4_sub_devices(
    mac_address: str,
    request: Request,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get AVA4 sub-devices (medical devices) connected to a specific AVA4 box"""
    try:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        # Find the main AVA4 device
        device_collection = mongodb_service.get_collection("amy_boxes")
        main_device = await device_collection.find_one({"mac_address": mac_address})
        
        if not main_device:
            raise HTTPException(
                status_code=404,
                detail=create_error_response(
                    "DEVICE_NOT_FOUND",
                    field="mac_address",
                    value=mac_address,
                    custom_message=f"AVA4 device with MAC address '{mac_address}' not found",
                    request_id=request_id
                ).dict()
            )
        
        # Get the patient_id from the main device
        patient_id = main_device.get("patient_id")
        if not patient_id:
            # Return empty result if no patient assigned
            success_response = create_success_response(
                message="AVA4 device found but no patient assigned - no sub-devices available",
                data={
                    "main_device": {
                        "device_id": str(main_device.get("_id")),
                        "mac_address": main_device.get("mac_address"),
                        "box_name": main_device.get("box_name"),
                        "model": main_device.get("model"),
                        "status": main_device.get("status"),
                        "patient_id": None
                    },
                    "sub_devices": {
                        "total_count": 0,
                        "categories": {
                            "blood_pressure": [],
                            "blood_glucose": [],
                            "weight_scale": [],
                            "thermometer": [],
                            "pulse_oximeter": [],
                            "other": []
                        },
                        "all_devices": []
                    }
                },
                request_id=request_id
            )
            return success_response.dict()
        
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
        
        # Get connected medical devices by patient_id
        amy_devices_collection = mongodb_service.get_collection("amy_devices")
        patient_devices = await amy_devices_collection.find_one({"patient_id.$oid": patient_id})
        
        # Parse medical devices from the patient's device record
        sub_devices = []
        if patient_devices:
            device_types = {
                "mac_dusun_bps": {"type": "blood_pressure", "name": "Blood Pressure Monitor (Dusun)"},
                "mac_bps": {"type": "blood_pressure", "name": "Blood Pressure Monitor"},
                "mac_gluc": {"type": "blood_glucose", "name": "Blood Glucose Meter"},
                "mac_weight": {"type": "weight_scale", "name": "Weight Scale"},
                "mac_body_temp": {"type": "thermometer", "name": "Body Temperature Sensor"},
                "mac_oxymeter": {"type": "pulse_oximeter", "name": "Pulse Oximeter"},
                "mac_mgss_oxymeter": {"type": "pulse_oximeter", "name": "MGSS Pulse Oximeter"},
                "mac_chol": {"type": "other", "name": "Cholesterol Meter"},
                "mac_ua": {"type": "other", "name": "Uric Acid Meter"},
                "mac_salt_meter": {"type": "other", "name": "Salt Meter"}
            }
            
            for mac_field, device_info in device_types.items():
                mac_value = patient_devices.get(mac_field)
                if mac_value and mac_value.strip():  # Check if MAC address exists and is not empty
                    sub_devices.append({
                        "device_id": f"{mac_field}_{patient_devices.get('_id')}",
                        "mac_address": mac_value,
                        "device_type": device_info["type"],
                        "device_name": device_info["name"],
                        "is_active": True,
                        "patient_id": str(patient_obj_id),
                        "created_at": patient_devices.get("created_at"),
                        "updated_at": patient_devices.get("updated_at")
                    })
        
        # Serialize the results
        main_device_info = serialize_mongodb_response(main_device)
        
        # Categorize sub-devices by type
        device_categories = {
            "blood_pressure": [],
            "blood_glucose": [],
            "weight_scale": [],
            "thermometer": [],
            "pulse_oximeter": [],
            "other": []
        }
        
        for device in sub_devices:
            device_type = device.get("device_type", "other")
            if device_type in device_categories:
                device_categories[device_type].append(device)
            else:
                device_categories["other"].append(device)
        
        success_response = create_success_response(
            message="AVA4 sub-devices retrieved successfully",
            data={
                "main_device": {
                    "device_id": main_device_info.get("_id"),
                    "mac_address": main_device_info.get("mac_address"),
                    "box_name": main_device_info.get("box_name"),
                    "model": main_device_info.get("model"),
                    "status": main_device_info.get("status"),
                    "patient_id": main_device_info.get("patient_id")
                },
                "sub_devices": {
                    "total_count": len(sub_devices),
                    "categories": device_categories,
                    "all_devices": sub_devices
                }
            },
            request_id=request_id
        )
        
        return success_response.dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting AVA4 sub-devices: {e}")
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                "INTERNAL_SERVER_ERROR",
                custom_message=f"Failed to retrieve sub-devices: {str(e)}",
                request_id=request.headers.get("X-Request-ID")
            ).dict()
        )

@router.get("/sub-devices/table")
async def get_ava4_sub_devices_table(
    request: Request,
    page: int = 1,
    limit: int = 25,
    patient_id: Optional[str] = None,
    device_type: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: str = "device_name",
    sort_order: str = "asc",
    columns: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get AVA4 sub-devices in table format with advanced filtering"""
    try:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        # Calculate skip from page
        skip = (page - 1) * limit if page > 0 else 0
        
        # Define available columns
        available_columns = [
            "device_name", "mac_address", "device_type", "patient_info", "is_active",
            "ava4_device_info", "created_at", "updated_at"
        ]
        
        # Parse requested columns
        selected_columns = available_columns
        if columns:
            requested_cols = [col.strip() for col in columns.split(",")]
            selected_columns = [col for col in requested_cols if col in available_columns]
        
        # Get all sub-devices from amy_devices collection
        amy_devices_collection = mongodb_service.get_collection("amy_devices")
        patient_collection = mongodb_service.get_collection("patients")
        device_collection = mongodb_service.get_collection("amy_boxes")
        
        # Build filter query
        filter_query = {}
        
        # Patient filter
        if patient_id:
            try:
                patient_obj_id = ObjectId(patient_id)
                # Query using both possible formats
                filter_query = {
                    "$or": [
                        {"patient_id": patient_obj_id},
                        {"patient_id.$oid": patient_id}
                    ]
                }
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
        
        # Get all device records
        amy_device_records = await amy_devices_collection.find(filter_query).to_list(length=None)
        
        # Process all sub-devices
        all_sub_devices = []
        device_types = {
            "mac_dusun_bps": {"type": "blood_pressure", "name": "Blood Pressure Monitor (Dusun)"},
            "mac_bps": {"type": "blood_pressure", "name": "Blood Pressure Monitor"},
            "mac_gluc": {"type": "blood_glucose", "name": "Blood Glucose Meter"},
            "mac_weight": {"type": "weight_scale", "name": "Weight Scale"},
            "mac_body_temp": {"type": "thermometer", "name": "Body Temperature Sensor"},
            "mac_oxymeter": {"type": "pulse_oximeter", "name": "Pulse Oximeter"},
            "mac_mgss_oxymeter": {"type": "pulse_oximeter", "name": "MGSS Pulse Oximeter"},
            "mac_chol": {"type": "other", "name": "Cholesterol Meter"},
            "mac_ua": {"type": "other", "name": "Uric Acid Meter"},
            "mac_salt_meter": {"type": "other", "name": "Salt Meter"}
        }
        
        for record in amy_device_records:
            for mac_field, device_info in device_types.items():
                mac_value = record.get(mac_field)
                if mac_value and mac_value.strip():
                    # Filter by device type if specified
                    if device_type and device_info["type"] != device_type:
                        continue
                    
                    # Search functionality
                    if search:
                        search_lower = search.lower()
                        if not any([
                            search_lower in device_info["name"].lower(),
                            search_lower in mac_value.lower(),
                            search_lower in device_info["type"].lower()
                        ]):
                            continue
                    
                    sub_device = {
                        "device_id": f"{mac_field}_{record.get('_id')}",
                        "mac_address": mac_value,
                        "device_type": device_info["type"],
                        "device_name": device_info["name"],
                        "is_active": record.get(f"{mac_field}_active", True),
                        "patient_id": str(record.get("patient_id", "")),
                        "created_at": record.get("created_at"),
                        "updated_at": record.get("updated_at"),
                        "registered_at": record.get(f"{mac_field}_registered_at"),
                        "model": record.get(f"{mac_field}_model", ""),
                        "custom_name": record.get(f"{mac_field}_name", "")
                    }
                    
                    all_sub_devices.append(sub_device)
        
        # Apply sorting
        reverse_sort = sort_order.lower() == "desc"
        valid_sort_fields = ["device_name", "mac_address", "device_type", "created_at", "updated_at"]
        if sort_by in valid_sort_fields:
            all_sub_devices.sort(key=lambda x: x.get(sort_by, ""), reverse=reverse_sort)
        
        # Apply pagination
        total_count = len(all_sub_devices)
        start_index = skip
        end_index = skip + limit
        paginated_devices = all_sub_devices[start_index:end_index]
        
        # Prepare table data with selected columns
        table_data = []
        for device in paginated_devices:
            row = {}
            
            for col in selected_columns:
                if col == "patient_info" and device.get("patient_id"):
                    try:
                        patient_obj_id = ObjectId(device["patient_id"])
                        patient = await patient_collection.find_one({"_id": patient_obj_id})
                        if patient:
                            patient_info = serialize_mongodb_response(patient)
                            row["patient_info"] = {
                                "patient_name": f"{patient_info.get('first_name', '')} {patient_info.get('last_name', '')}".strip(),
                                "hn": patient_info.get("hn"),
                                "phone": patient_info.get("phone")
                            }
                        else:
                            row["patient_info"] = None
                    except Exception:
                        row["patient_info"] = None
                elif col == "ava4_device_info" and device.get("patient_id"):
                    # Find AVA4 device for this patient
                    try:
                        patient_obj_id = ObjectId(device["patient_id"])
                        ava4_device = await device_collection.find_one({"patient_id": patient_obj_id})
                        if ava4_device:
                            ava4_info = serialize_mongodb_response(ava4_device)
                            row["ava4_device_info"] = {
                                "box_name": ava4_info.get("box_name"),
                                "mac_address": ava4_info.get("mac_address"),
                                "status": ava4_info.get("status")
                            }
                        else:
                            row["ava4_device_info"] = None
                    except Exception:
                        row["ava4_device_info"] = None
                else:
                    row[col] = device.get(col)
            
            table_data.append(row)
        
        # Calculate pagination
        total_pages = (total_count + limit - 1) // limit if limit > 0 else 1
        has_next = page < total_pages
        has_prev = page > 1
        
        success_response = create_success_response(
            message="AVA4 sub-devices table data retrieved successfully",
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
                    "patient_id": patient_id,
                    "device_type": device_type,
                    "search": search,
                    "sort_by": sort_by,
                    "sort_order": sort_order
                },
                "statistics": {
                    "total_sub_devices": total_count,
                    "device_type_counts": {
                        "blood_pressure": len([d for d in all_sub_devices if d["device_type"] == "blood_pressure"]),
                        "blood_glucose": len([d for d in all_sub_devices if d["device_type"] == "blood_glucose"]),
                        "weight_scale": len([d for d in all_sub_devices if d["device_type"] == "weight_scale"]),
                        "thermometer": len([d for d in all_sub_devices if d["device_type"] == "thermometer"]),
                        "pulse_oximeter": len([d for d in all_sub_devices if d["device_type"] == "pulse_oximeter"]),
                        "other": len([d for d in all_sub_devices if d["device_type"] == "other"])
                    }
                }
            },
            request_id=request_id
        )
        
        return success_response.dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting AVA4 sub-devices table: {e}")
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                "INTERNAL_SERVER_ERROR",
                custom_message=f"Failed to retrieve sub-devices table: {str(e)}",
                request_id=request.headers.get("X-Request-ID") or str(uuid.uuid4())
            ).dict()
        )

@router.get("/test-medical-devices/{patient_id}")
async def test_medical_devices(
    patient_id: str,
    request: Request,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Test endpoint to check medical devices for a specific patient"""
    try:
        # Convert patient_id to ObjectId
        try:
            patient_obj_id = ObjectId(patient_id)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid patient_id format: {e}")
        
        # Get patient's medical devices
        amy_devices_collection = mongodb_service.get_collection("amy_devices")
        patient_devices = await amy_devices_collection.find_one({"patient_id.$oid": patient_id})
        
        if not patient_devices:
            return {"message": "No medical devices found for this patient", "patient_id": patient_id}
        
        # Parse all MAC addresses
        device_macs = {}
        mac_fields = [
            "mac_gw", "mac_bps", "mac_watch", "mac_body_temp", "mac_oxymeter", 
            "mac_weight", "mac_gluc", "mac_chol", "mac_ua", "mac_dusun_bps", 
            "mac_mgss_oxymeter", "mac_salt_meter"
        ]
        
        for field in mac_fields:
            mac_value = patient_devices.get(field)
            if mac_value and mac_value.strip():
                device_macs[field] = mac_value
        
        return {
            "patient_id": patient_id,
            "total_devices": len(device_macs),
            "devices": device_macs,
            "created_at": patient_devices.get("created_at"),
            "updated_at": patient_devices.get("updated_at")
        }
        
    except Exception as e:
        logger.error(f"Error testing medical devices: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sub-devices")
async def register_ava4_sub_device(
    request: Request,
    mac_address: str,
    patient_id: str,
    device_type: str,
    device_name: str,
    model: str = None,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Register a new AVA4 sub-device (medical device) for a patient"""
    try:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        # Validate patient exists
        patient_collection = mongodb_service.get_collection("patients")
        try:
            patient_obj_id = ObjectId(patient_id)
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
        
        patient = await patient_collection.find_one({"_id": patient_obj_id})
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
        
        # Validate device type
        valid_device_types = {
            "blood_pressure": "mac_bps",
            "blood_pressure_dusun": "mac_dusun_bps",
            "blood_glucose": "mac_gluc",
            "weight_scale": "mac_weight",
            "thermometer": "mac_body_temp",
            "pulse_oximeter": "mac_oxymeter",
            "pulse_oximeter_mgss": "mac_mgss_oxymeter",
            "cholesterol": "mac_chol",
            "uric_acid": "mac_ua",
            "salt_meter": "mac_salt_meter"
        }
        
        if device_type not in valid_device_types:
            raise HTTPException(
                status_code=400,
                detail=create_error_response(
                    "INVALID_DEVICE_TYPE",
                    field="device_type",
                    value=device_type,
                    custom_message=f"Invalid device type. Valid types: {list(valid_device_types.keys())}",
                    request_id=request_id
                ).dict()
            )
        
        # Check if patient already has a device record
        amy_devices_collection = mongodb_service.get_collection("amy_devices")
        existing_device_record = await amy_devices_collection.find_one({"patient_id.$oid": patient_id})
        
        mac_field = valid_device_types[device_type]
        
        if existing_device_record:
            # Check if this device type is already registered
            if existing_device_record.get(mac_field):
                raise HTTPException(
                    status_code=400,
                    detail=create_error_response(
                        "DEVICE_ALREADY_REGISTERED",
                        field="device_type",
                        value=device_type,
                        custom_message=f"Patient already has a {device_type} device registered",
                        request_id=request_id
                    ).dict()
                )
            
            # Update existing record with new device
            update_result = await amy_devices_collection.update_one(
                {"_id": existing_device_record["_id"]},
                {
                    "$set": {
                        mac_field: mac_address,
                        f"{mac_field}_name": device_name,
                        f"{mac_field}_model": model,
                        f"{mac_field}_registered_at": datetime.utcnow(),
                        f"{mac_field}_registered_by": current_user.get("username"),
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            if update_result.modified_count == 0:
                raise HTTPException(
                    status_code=500,
                    detail=create_error_response(
                        "REGISTRATION_FAILED",
                        custom_message="Failed to register sub-device",
                        request_id=request_id
                    ).dict()
                )
            
            device_record_id = str(existing_device_record["_id"])
        else:
            # Create new device record
            device_record = {
                "patient_id": patient_obj_id,
                mac_field: mac_address,
                f"{mac_field}_name": device_name,
                f"{mac_field}_model": model,
                f"{mac_field}_registered_at": datetime.utcnow(),
                f"{mac_field}_registered_by": current_user.get("username"),
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            insert_result = await amy_devices_collection.insert_one(device_record)
            device_record_id = str(insert_result.inserted_id)
        
        # Log audit trail
        await audit_logger.log_admin_action(
            action="CREATE",
            resource_type="AVA4SubDevice",
            resource_id=device_record_id,
            user_id=current_user.get("username") or "unknown",
            details={
                "patient_id": patient_id,
                "device_type": device_type,
                "mac_address": mac_address,
                "device_name": device_name,
                "model": model
            }
        )
        
        success_response = create_success_response(
            message="AVA4 sub-device registered successfully",
            data={
                "device_record_id": device_record_id,
                "patient_id": patient_id,
                "device_type": device_type,
                "mac_address": mac_address,
                "device_name": device_name,
                "model": model
            },
            request_id=request_id
        )
        
        return success_response.dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error registering AVA4 sub-device: {e}")
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                "INTERNAL_SERVER_ERROR",
                custom_message=f"Failed to register sub-device: {str(e)}",
                request_id=request.headers.get("X-Request-ID") or str(uuid.uuid4())
            ).dict()
        )

@router.put("/sub-devices/{patient_id}/{device_type}")
async def update_ava4_sub_device(
    patient_id: str,
    device_type: str,
    request: Request,
    mac_address: str = None,
    device_name: str = None,
    model: str = None,
    is_active: bool = None,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Update an AVA4 sub-device for a patient"""
    try:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        # Validate patient and device type
        try:
            patient_obj_id = ObjectId(patient_id)
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
        
        valid_device_types = {
            "blood_pressure": "mac_bps",
            "blood_pressure_dusun": "mac_dusun_bps",
            "blood_glucose": "mac_gluc",
            "weight_scale": "mac_weight",
            "thermometer": "mac_body_temp",
            "pulse_oximeter": "mac_oxymeter",
            "pulse_oximeter_mgss": "mac_mgss_oxymeter",
            "cholesterol": "mac_chol",
            "uric_acid": "mac_ua",
            "salt_meter": "mac_salt_meter"
        }
        
        if device_type not in valid_device_types:
            raise HTTPException(
                status_code=400,
                detail=create_error_response(
                    "INVALID_DEVICE_TYPE",
                    field="device_type",
                    value=device_type,
                    custom_message=f"Invalid device type. Valid types: {list(valid_device_types.keys())}",
                    request_id=request_id
                ).dict()
            )
        
        # Find existing device record
        amy_devices_collection = mongodb_service.get_collection("amy_devices")
        device_record = await amy_devices_collection.find_one({"patient_id.$oid": patient_obj_id})
        
        if not device_record:
            raise HTTPException(
                status_code=404,
                detail=create_error_response(
                    "DEVICE_RECORD_NOT_FOUND",
                    field="patient_id",
                    value=patient_id,
                    custom_message=f"No device record found for patient '{patient_id}'",
                    request_id=request_id
                ).dict()
            )
        
        mac_field = valid_device_types[device_type]
        
        # Check if device exists
        if not device_record.get(mac_field):
            raise HTTPException(
                status_code=404,
                detail=create_error_response(
                    "SUB_DEVICE_NOT_FOUND",
                    field="device_type",
                    value=device_type,
                    custom_message=f"No {device_type} device found for this patient",
                    request_id=request_id
                ).dict()
            )
        
        # Build update fields
        update_fields = {"updated_at": datetime.utcnow()}
        
        if mac_address is not None:
            update_fields[mac_field] = mac_address
        if device_name is not None:
            update_fields[f"{mac_field}_name"] = device_name
        if model is not None:
            update_fields[f"{mac_field}_model"] = model
        if is_active is not None:
            update_fields[f"{mac_field}_active"] = is_active
        
        # Update device record
        update_result = await amy_devices_collection.update_one(
            {"_id": device_record["_id"]},
            {"$set": update_fields}
        )
        
        if update_result.modified_count == 0:
            raise HTTPException(
                status_code=500,
                detail=create_error_response(
                    "UPDATE_FAILED",
                    custom_message="Failed to update sub-device",
                    request_id=request_id
                ).dict()
            )
        
        # Log audit trail
        await audit_logger.log_admin_action(
            action="UPDATE",
            resource_type="AVA4SubDevice",
            resource_id=str(device_record["_id"]),
            user_id=current_user.get("username") or "unknown",
            details={
                "patient_id": patient_id,
                "device_type": device_type,
                "updated_fields": update_fields
            }
        )
        
        success_response = create_success_response(
            message="AVA4 sub-device updated successfully",
            data={
                "device_record_id": str(device_record["_id"]),
                "patient_id": patient_id,
                "device_type": device_type,
                "updated_fields": update_fields
            },
            request_id=request_id
        )
        
        return success_response.dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating AVA4 sub-device: {e}")
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                "INTERNAL_SERVER_ERROR",
                custom_message=f"Failed to update sub-device: {str(e)}",
                request_id=request.headers.get("X-Request-ID") or str(uuid.uuid4())
            ).dict()
        )

@router.delete("/sub-devices/{patient_id}/{device_type}")
async def unregister_ava4_sub_device(
    patient_id: str,
    device_type: str,
    request: Request,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Unregister an AVA4 sub-device from a patient"""
    try:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        # Validate patient and device type
        try:
            patient_obj_id = ObjectId(patient_id)
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
        
        valid_device_types = {
            "blood_pressure": "mac_bps",
            "blood_pressure_dusun": "mac_dusun_bps",
            "blood_glucose": "mac_gluc",
            "weight_scale": "mac_weight",
            "thermometer": "mac_body_temp",
            "pulse_oximeter": "mac_oxymeter",
            "pulse_oximeter_mgss": "mac_mgss_oxymeter",
            "cholesterol": "mac_chol",
            "uric_acid": "mac_ua",
            "salt_meter": "mac_salt_meter"
        }
        
        if device_type not in valid_device_types:
            raise HTTPException(
                status_code=400,
                detail=create_error_response(
                    "INVALID_DEVICE_TYPE",
                    field="device_type",
                    value=device_type,
                    custom_message=f"Invalid device type. Valid types: {list(valid_device_types.keys())}",
                    request_id=request_id
                ).dict()
            )
        
        # Find existing device record
        amy_devices_collection = mongodb_service.get_collection("amy_devices")
        device_record = await amy_devices_collection.find_one({"patient_id.$oid": patient_obj_id})
        
        if not device_record:
            raise HTTPException(
                status_code=404,
                detail=create_error_response(
                    "DEVICE_RECORD_NOT_FOUND",
                    field="patient_id",
                    value=patient_id,
                    custom_message=f"No device record found for patient '{patient_id}'",
                    request_id=request_id
                ).dict()
            )
        
        mac_field = valid_device_types[device_type]
        
        # Check if device exists
        if not device_record.get(mac_field):
            raise HTTPException(
                status_code=404,
                detail=create_error_response(
                    "SUB_DEVICE_NOT_FOUND",
                    field="device_type",
                    value=device_type,
                    custom_message=f"No {device_type} device found for this patient",
                    request_id=request_id
                ).dict()
            )
        
        # Store device info for audit
        device_mac = device_record.get(mac_field)
        device_name = device_record.get(f"{mac_field}_name")
        
        # Remove device fields
        unset_fields = {
            mac_field: "",
            f"{mac_field}_name": "",
            f"{mac_field}_model": "",
            f"{mac_field}_registered_at": "",
            f"{mac_field}_registered_by": "",
            f"{mac_field}_active": ""
        }
        
        update_result = await amy_devices_collection.update_one(
            {"_id": device_record["_id"]},
            {
                "$unset": unset_fields,
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        
        if update_result.modified_count == 0:
            raise HTTPException(
                status_code=500,
                detail=create_error_response(
                    "UNREGISTER_FAILED",
                    custom_message="Failed to unregister sub-device",
                    request_id=request_id
                ).dict()
            )
        
        # Log audit trail
        await audit_logger.log_admin_action(
            action="DELETE",
            resource_type="AVA4SubDevice",
            resource_id=str(device_record["_id"]),
            user_id=current_user.get("username") or "unknown",
            details={
                "patient_id": patient_id,
                "device_type": device_type,
                "mac_address": device_mac,
                "device_name": device_name
            }
        )
        
        success_response = create_success_response(
            message="AVA4 sub-device unregistered successfully",
            data={
                "device_record_id": str(device_record["_id"]),
                "patient_id": patient_id,
                "device_type": device_type,
                "mac_address": device_mac
            },
            request_id=request_id
        )
        
        return success_response.dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error unregistering AVA4 sub-device: {e}")
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                "INTERNAL_SERVER_ERROR",
                custom_message=f"Failed to unregister sub-device: {str(e)}",
                request_id=request.headers.get("X-Request-ID")
            ).dict()
        )

@router.get("/sub-devices/analytics")
async def get_ava4_sub_device_analytics(
    request: Request,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get analytics for AVA4 sub-devices"""
    try:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        # Get device analytics
        amy_devices_collection = mongodb_service.get_collection("amy_devices")
        
        # Get all device records
        all_device_records = await amy_devices_collection.find({}).to_list(length=None)
        
        # Initialize analytics
        device_type_counts = {
            "blood_pressure": 0,
            "blood_pressure_dusun": 0,
            "blood_glucose": 0,
            "weight_scale": 0,
            "thermometer": 0,
            "pulse_oximeter": 0,
            "pulse_oximeter_mgss": 0,
            "cholesterol": 0,
            "uric_acid": 0,
            "salt_meter": 0
        }
        
        device_type_mapping = {
            "mac_bps": "blood_pressure",
            "mac_dusun_bps": "blood_pressure_dusun",
            "mac_gluc": "blood_glucose",
            "mac_weight": "weight_scale",
            "mac_body_temp": "thermometer",
            "mac_oxymeter": "pulse_oximeter",
            "mac_mgss_oxymeter": "pulse_oximeter_mgss",
            "mac_chol": "cholesterol",
            "mac_ua": "uric_acid",
            "mac_salt_meter": "salt_meter"
        }
        
        total_patients_with_devices = 0
        total_devices_registered = 0
        
        # Analyze each device record
        for record in all_device_records:
            has_devices = False
            
            for mac_field, device_type in device_type_mapping.items():
                if record.get(mac_field):
                    device_type_counts[device_type] += 1
                    total_devices_registered += 1
                    has_devices = True
            
            if has_devices:
                total_patients_with_devices += 1
        
        # Get total patients
        patient_collection = mongodb_service.get_collection("patients")
        total_patients = await patient_collection.count_documents({})
        
        # Calculate percentages
        patient_coverage_percentage = (total_patients_with_devices / total_patients * 100) if total_patients > 0 else 0
        
        # Get most popular device types
        popular_devices = sorted(device_type_counts.items(), key=lambda x: x[1], reverse=True)
        
        success_response = create_success_response(
            message="AVA4 sub-device analytics retrieved successfully",
            data={
                "summary": {
                    "total_patients": total_patients,
                    "patients_with_devices": total_patients_with_devices,
                    "total_devices_registered": total_devices_registered,
                    "patient_coverage_percentage": round(patient_coverage_percentage, 2)
                },
                "device_type_counts": device_type_counts,
                "popular_devices": popular_devices[:5],
                "device_categories": {
                    "vital_signs": device_type_counts["blood_pressure"] + device_type_counts["blood_pressure_dusun"] + device_type_counts["pulse_oximeter"] + device_type_counts["pulse_oximeter_mgss"] + device_type_counts["thermometer"],
                    "metabolic": device_type_counts["blood_glucose"] + device_type_counts["cholesterol"] + device_type_counts["uric_acid"],
                    "physical": device_type_counts["weight_scale"],
                    "other": device_type_counts["salt_meter"]
                }
            },
            request_id=request_id
        )
        
        return success_response.dict()
        
    except Exception as e:
        logger.error(f"Error getting AVA4 sub-device analytics: {e}")
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                "INTERNAL_SERVER_ERROR",
                custom_message=f"Failed to retrieve analytics: {str(e)}",
                request_id=request.headers.get("X-Request-ID")
            ).dict()
        )

@router.get("/sub-devices/discovery")
async def discover_ava4_sub_devices(
    request: Request,
    box_mac_address: str = None,
    scan_duration: int = 30,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Discover available AVA4 sub-devices for registration"""
    try:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        # This is a mock implementation - in a real system, this would scan for nearby devices
        # For now, we'll return a simulated discovery result
        
        discovered_devices = [
            {
                "mac_address": "AA:BB:CC:DD:EE:01",
                "device_type": "blood_pressure",
                "device_name": "Omron Blood Pressure Monitor",
                "model": "HEM-7120",
                "signal_strength": -45,
                "last_seen": datetime.utcnow().isoformat(),
                "is_paired": False
            },
            {
                "mac_address": "AA:BB:CC:DD:EE:02",
                "device_type": "blood_glucose",
                "device_name": "Accu-Chek Glucose Meter",
                "model": "AC-7500",
                "signal_strength": -52,
                "last_seen": datetime.utcnow().isoformat(),
                "is_paired": False
            },
            {
                "mac_address": "AA:BB:CC:DD:EE:03",
                "device_type": "weight_scale",
                "device_name": "Digital Weight Scale",
                "model": "WS-2000",
                "signal_strength": -38,
                "last_seen": datetime.utcnow().isoformat(),
                "is_paired": False
            }
        ]
        
        success_response = create_success_response(
            message="AVA4 sub-device discovery completed",
            data={
                "scan_info": {
                    "box_mac_address": box_mac_address,
                    "scan_duration": scan_duration,
                    "scan_completed_at": datetime.utcnow().isoformat()
                },
                "discovered_devices": discovered_devices,
                "total_discovered": len(discovered_devices)
            },
            request_id=request_id
        )
        
        return success_response.dict()
        
    except Exception as e:
        logger.error(f"Error discovering AVA4 sub-devices: {e}")
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                "INTERNAL_SERVER_ERROR",
                custom_message=f"Failed to discover sub-devices: {str(e)}",
                request_id=request.headers.get("X-Request-ID")
            ).dict()
        )

@router.get("/sub-devices/raw-documents")
async def get_raw_amy_devices_documents(
    request: Request,
    limit: int = 5,
    skip: int = 0,
    patient_id: str = None,
    data_type: str = Query("devices", description="Type of data: 'devices' or 'patients'"),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get raw documents to examine structure and relationships - supports both devices and patients"""
    try:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        if data_type == "patients":
            # Handle patient data
            patients_collection = mongodb_service.get_collection("patients")
            
            # Build filter for patients
            filter_query = {"is_deleted": {"$ne": True}}
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
            
            # Get raw patient documents
            cursor = patients_collection.find(filter_query).sort("_id", 1).skip(skip).limit(limit)
            raw_documents = await cursor.to_list(length=limit)
            
            # Get total count
            total_count = await patients_collection.count_documents(filter_query)
            
            # Analyze patient document structure
            field_analysis = {}
            patient_fields = [
                "_id", "first_name", "last_name", "nickname", "gender", "birth_date",
                "id_card", "phone", "email", "address", "province_code", "district_code",
                "sub_district_code", "postal_code", "emergency_contact_name", 
                "emergency_contact_phone", "emergency_contact_relationship", "blood_type",
                "height", "weight", "bmi", "watch_mac_address", "ava_mac_address",
                "new_hospital_ids", "created_at", "updated_at", "is_active", "is_deleted"
            ]
            
            for doc in raw_documents:
                for field in doc.keys():
                    if field not in field_analysis:
                        field_analysis[field] = {
                            "count": 0,
                            "sample_values": [],
                            "is_standard_field": field in patient_fields,
                            "data_type": type(doc[field]).__name__
                        }
                    
                    field_analysis[field]["count"] += 1
                    
                    # Store sample values (limit to 3)
                    if len(field_analysis[field]["sample_values"]) < 3:
                        value = doc[field]
                        if isinstance(value, ObjectId):
                            field_analysis[field]["sample_values"].append(str(value))
                        elif isinstance(value, datetime):
                            field_analysis[field]["sample_values"].append(value.isoformat())
                        elif isinstance(value, (dict, list)):
                            field_analysis[field]["sample_values"].append(str(value)[:100] + "..." if len(str(value)) > 100 else str(value))
                        else:
                            field_analysis[field]["sample_values"].append(value)
            
            # Serialize documents for response
            serialized_documents = serialize_mongodb_response(raw_documents)
            
            success_response = create_success_response(
                message="Raw patient documents retrieved successfully",
                data={
                    "documents": serialized_documents,
                    "total_count": total_count,
                    "returned_count": len(serialized_documents),
                    "field_analysis": field_analysis,
                    "standard_patient_fields": patient_fields,
                    "data_type": "patients",
                    "pagination": {
                        "limit": limit,
                        "skip": skip,
                        "has_more": total_count > (skip + len(serialized_documents))
                    }
                },
                request_id=request_id
            )
            
            return success_response.dict()
            
        else:
            # Handle device data (existing functionality)
            amy_devices_collection = mongodb_service.get_collection("amy_devices")
            
            # Build filter
            filter_query = {}
            if patient_id:
                try:
                    filter_query["patient_id.$oid"] = patient_id
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
            
            # Get raw documents
            cursor = amy_devices_collection.find(filter_query).sort("_id", 1).skip(skip).limit(limit)
            raw_documents = await cursor.to_list(length=limit)
            
            # Get total count
            total_count = await amy_devices_collection.count_documents(filter_query)
            
            # Analyze document structure
            field_analysis = {}
            device_type_fields = [
                "mac_gw", "mac_bps", "mac_watch", "mac_body_temp", "mac_oxymeter", 
                "mac_weight", "mac_gluc", "mac_chol", "mac_ua", "mac_dusun_bps", 
                "mac_mgss_oxymeter", "mac_salt_meter"
            ]
            
            for doc in raw_documents:
                for field in doc.keys():
                    if field not in field_analysis:
                        field_analysis[field] = {
                            "count": 0,
                            "sample_values": [],
                            "is_device_field": field in device_type_fields
                        }
                    
                    field_analysis[field]["count"] += 1
                    
                    # Store sample values (limit to 3)
                    if len(field_analysis[field]["sample_values"]) < 3:
                        value = doc[field]
                        if isinstance(value, ObjectId):
                            value = str(value)
                        field_analysis[field]["sample_values"].append(value)
            
            # Serialize documents for response
            serialized_documents = serialize_mongodb_response(raw_documents)
            
            success_response = create_success_response(
                message="Raw amy_devices documents retrieved successfully",
                data={
                    "documents": serialized_documents,
                    "total_count": total_count,
                    "returned_count": len(serialized_documents),
                    "field_analysis": field_analysis,
                    "device_type_fields": device_type_fields,
                    "data_type": "devices",
                    "pagination": {
                        "limit": limit,
                        "skip": skip,
                        "has_more": total_count > (skip + len(serialized_documents))
                    }
                },
                request_id=request_id
            )
            
            return success_response.dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting raw documents: {e}")
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                "INTERNAL_SERVER_ERROR",
                custom_message=f"Failed to retrieve raw documents: {str(e)}",
                request_id=request.headers.get("X-Request-ID")
            ).dict()
        )

@router.get("/sub-devices/patient-relationship/{patient_id}")
async def analyze_patient_device_relationship(
    patient_id: str,
    request: Request,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Analyze the complete relationship between a patient and their devices"""
    try:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        # Convert patient_id to ObjectId
        try:
            patient_obj_id = ObjectId(patient_id)
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
        
        # Get patient information
        patient_collection = mongodb_service.get_collection("patients")
        patient = await patient_collection.find_one({"_id": patient_obj_id})
        
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
        
        # Get AVA4 main device (amy_boxes)
        ava4_collection = mongodb_service.get_collection("amy_boxes")
        ava4_devices = await ava4_collection.find({"patient_id": patient_obj_id}).to_list(length=None)
        
        # Get Kati watches
        kati_collection = mongodb_service.get_collection("watches")
        kati_devices = await kati_collection.find({"patient_id": patient_obj_id}).to_list(length=None)
        
        # Get medical devices (amy_devices)
        amy_devices_collection = mongodb_service.get_collection("amy_devices")
        
        # The patient_id is stored as {"$oid": "string"} format, so we need to query accordingly
        medical_device_record = await amy_devices_collection.find_one({"patient_id.$oid": patient_id})
        
        # Analyze medical device fields
        medical_devices_analysis = {}
        if medical_device_record:
            device_fields = {
                "mac_gw": "Gateway Device",
                "mac_bps": "Blood Pressure Monitor",
                "mac_watch": "Watch Device",
                "mac_body_temp": "Body Temperature Sensor",
                "mac_oxymeter": "Pulse Oximeter",
                "mac_weight": "Weight Scale",
                "mac_gluc": "Blood Glucose Meter",
                "mac_chol": "Cholesterol Meter",
                "mac_ua": "Uric Acid Meter",
                "mac_dusun_bps": "Dusun Blood Pressure Monitor",
                "mac_mgss_oxymeter": "MGSS Pulse Oximeter",
                "mac_salt_meter": "Salt Meter"
            }
            
            for field, description in device_fields.items():
                mac_value = medical_device_record.get(field)
                if mac_value and str(mac_value).strip():
                    medical_devices_analysis[field] = {
                        "description": description,
                        "mac_address": mac_value,
                        "has_name": bool(medical_device_record.get(f"{field}_name")),
                        "has_model": bool(medical_device_record.get(f"{field}_model")),
                        "has_registration_info": bool(medical_device_record.get(f"{field}_registered_at"))
                    }
        
        # Serialize all data
        patient_info = serialize_mongodb_response(patient)
        ava4_info = serialize_mongodb_response(ava4_devices)
        kati_info = serialize_mongodb_response(kati_devices)
        medical_device_info = serialize_mongodb_response(medical_device_record) if medical_device_record else None
        
        success_response = create_success_response(
            message="Patient device relationship analysis completed",
            data={
                "patient": {
                    "patient_id": patient_info.get("_id") if isinstance(patient_info, dict) else None,
                    "name": f"{patient_info.get('first_name', '') if isinstance(patient_info, dict) else ''} {patient_info.get('last_name', '') if isinstance(patient_info, dict) else ''}".strip(),
                    "created_at": patient_info.get("created_at") if isinstance(patient_info, dict) else None,
                    "updated_at": patient_info.get("updated_at") if isinstance(patient_info, dict) else None,
                    "ava_mac_address": patient_info.get("ava_mac_address") if isinstance(patient_info, dict) else None,
                    "watch_mac_address": patient_info.get("watch_mac_address") if isinstance(patient_info, dict) else None
                },
                "ava4_main_devices": {
                    "count": len(ava4_info) if isinstance(ava4_info, list) else 0,
                    "devices": ava4_info if isinstance(ava4_info, list) else []
                },
                "kati_watches": {
                    "count": len(kati_info) if isinstance(kati_info, list) else 0,
                    "devices": kati_info if isinstance(kati_info, list) else []
                },
                "medical_devices": {
                    "has_record": medical_device_info is not None,
                    "record_id": medical_device_info.get("_id") if isinstance(medical_device_info, dict) else None,
                    "total_devices": len(medical_devices_analysis),
                    "devices": medical_devices_analysis,
                    "raw_record": medical_device_info,
                    "created_at": medical_device_info.get("created_at") if isinstance(medical_device_info, dict) else None,
                    "updated_at": medical_device_info.get("updated_at") if isinstance(medical_device_info, dict) else None
                },
                "relationship_summary": {
                    "total_ava4_devices": len(ava4_info) if isinstance(ava4_info, list) else 0,
                    "total_kati_devices": len(kati_info) if isinstance(kati_info, list) else 0,
                    "total_medical_devices": len(medical_devices_analysis),
                    "has_complete_setup": (len(ava4_info) if isinstance(ava4_info, list) else 0) > 0 and len(medical_devices_analysis) > 0,
                    "patient_has_ava_mac": bool(patient_info.get("ava_mac_address") if isinstance(patient_info, dict) else False),
                    "patient_has_watch_mac": bool(patient_info.get("watch_mac_address") if isinstance(patient_info, dict) else False)
                }
            },
            request_id=request_id
        )
        
        return success_response.dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing patient device relationship: {e}")
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                "INTERNAL_SERVER_ERROR",
                custom_message=f"Failed to analyze patient relationship: {str(e)}",
                request_id=request.headers.get("X-Request-ID")
            ).dict()
        )

@router.get("/debug-patient-query/{patient_id}")
async def debug_patient_query(
    patient_id: str,
    request: Request,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Debug endpoint to test patient_id queries"""
    try:
        # Convert patient_id to ObjectId
        patient_obj_id = ObjectId(patient_id)
        
        # Get medical devices collection
        amy_devices_collection = mongodb_service.get_collection("amy_devices")
        
        # Get a few raw documents to see the actual ObjectId structure
        raw_docs = await amy_devices_collection.find({}).limit(3).to_list(length=3)
        
        raw_patient_ids = []
        for doc in raw_docs:
            raw_patient_ids.append({
                "raw_patient_id": doc.get("patient_id"),
                "raw_patient_id_type": type(doc.get("patient_id")).__name__,
                "raw_patient_id_str": str(doc.get("patient_id")),
                "equals_input": doc.get("patient_id") == patient_obj_id,
                "equals_input_str": str(doc.get("patient_id")) == patient_id
            })
        
        # Try to find the specific document
        found_doc = None
        for doc in raw_docs:
            if str(doc.get("patient_id")) == patient_id:
                found_doc = doc
                break
        
        # Get all documents and check manually
        all_docs = await amy_devices_collection.find({}).to_list(length=None)
        matching_docs = []
        for doc in all_docs:
            if str(doc.get("patient_id")) == patient_id:
                matching_docs.append({
                    "doc_id": str(doc.get("_id")),
                    "patient_id": str(doc.get("patient_id")),
                    "has_devices": any([
                        doc.get("mac_body_temp"),
                        doc.get("mac_dusun_bps"),
                        doc.get("mac_gluc"),
                        doc.get("mac_oxymeter"),
                        doc.get("mac_weight")
                    ])
                })
        
        return {
            "patient_id": patient_id,
            "patient_obj_id": str(patient_obj_id),
            "raw_patient_ids_sample": raw_patient_ids,
            "matching_docs_count": len(matching_docs),
            "matching_docs": matching_docs,
            "total_docs_in_collection": len(all_docs)
        }
        
    except Exception as e:
        return {"error": str(e)}

@router.get(
    "/medical-history/collections",
    response_model=MedicalHistoryCollectionsResponse,
    summary="Get Medical History Collections Overview",
    description="""
    ## Medical History Collections Overview
    
    Get comprehensive information about all medical history collections in the system.
    
    ### Features:
    - **Collection Statistics**: Record counts, status, and metadata
    - **Data Fields**: Available fields for each collection type
    - **System Overview**: Total records and active collections
    - **Real-time Data**: Live collection statistics
    
    ### Collections Included:
    - Blood Pressure Histories
    - Blood Sugar Histories  
    - Body Data Histories
    - Temperature Data Histories
    - SPO2 Histories
    - Sleep Data Histories
    - Step Histories
    - Medication Histories
    - Allergy Histories
    - And more...
    
    ### Response Data:
    - `summary`: Overall system statistics
    - `collections`: Detailed collection information
    - `top_collections`: Most active collections by record count
    
    ### Authentication:
    Requires valid JWT Bearer token.
    """,
    responses={
        200: {
            "description": "Medical history collections retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Medical history collections retrieved successfully",
                        "data": {
                            "summary": {
                                "total_collections": 13,
                                "total_records": 56219,
                                "active_collections": 13,
                                "empty_collections": 0
                            },
                            "collections": {
                                "blood_pressure_histories": {
                                    "name": "Blood Pressure History",
                                    "record_count": 21542,
                                    "status": "active",
                                    "data_fields": ["systolic", "diastolic", "pulse"]
                                }
                            }
                        }
                    }
                }
            }
        },
        401: {"description": "Authentication required"},
        500: {"description": "Internal server error"}
    },
    tags=["ava4"]
)
async def get_medical_history_collections(
    request: Request,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get overview of all medical history collections"""
    try:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        # Define all medical history collections
        collections_info = {
            "blood_pressure_histories": {
                "name": "Blood Pressure History",
                "description": "Systolic, diastolic blood pressure and pulse readings",
                "data_fields": ["systolic", "diastolic", "pulse", "timestamp", "device_id"]
            },
            "blood_sugar_histories": {
                "name": "Blood Sugar History", 
                "description": "Blood glucose level measurements",
                "data_fields": ["value", "unit", "timestamp", "device_id"]
            },
            "body_data_histories": {
                "name": "Body Data History",
                "description": "Weight, height, BMI, body fat measurements",
                "data_fields": ["weight", "height", "bmi", "body_fat", "muscle_mass", "timestamp"]
            },
            "creatinine_histories": {
                "name": "Creatinine History",
                "description": "Kidney function test results",
                "data_fields": ["value", "unit", "timestamp", "device_id"]
            },
            "lipid_histories": {
                "name": "Lipid History",
                "description": "Cholesterol and lipid panel results",
                "data_fields": ["total_cholesterol", "hdl", "ldl", "triglycerides", "timestamp"]
            },
            "sleep_data_histories": {
                "name": "Sleep Data History",
                "description": "Sleep patterns and quality metrics",
                "data_fields": ["start_time", "end_time", "duration_minutes", "sleep_score", "deep_sleep_minutes"]
            },
            "spo2_histories": {
                "name": "SPO2 History",
                "description": "Blood oxygen saturation levels",
                "data_fields": ["value", "timestamp", "device_id"]
            },
            "step_histories": {
                "name": "Step History",
                "description": "Daily step count and activity data",
                "data_fields": ["steps", "distance", "calories", "timestamp"]
            },
            "temprature_data_histories": {
                "name": "Temperature Data History",
                "description": "Body temperature measurements",
                "data_fields": ["value", "unit", "timestamp", "device_id"]
            },
            "admit_data_histories": {
                "name": "Hospital Admission History",
                "description": "Hospital admission and discharge records",
                "data_fields": ["hospital_name", "admit_date", "discharge_date", "diagnosis"]
            },
            "allergy_histories": {
                "name": "Allergy History",
                "description": "Patient allergy information",
                "data_fields": ["allergen", "severity", "symptoms", "timestamp"]
            },
            "medication_histories": {
                "name": "Medication History",
                "description": "Prescribed medication records",
                "data_fields": ["medication_detail", "medication_import_date", "medication_source"]
            },
            "underlying_disease_histories": {
                "name": "Underlying Disease History",
                "description": "Chronic conditions and diseases",
                "data_fields": ["disease_name", "diagnosis_date", "severity", "notes"]
            }
        }
        
        # Get actual counts from database
        collection_stats = {}
        total_records = 0
        
        for collection_name, info in collections_info.items():
            try:
                collection = mongodb_service.get_collection(collection_name)
                count = await collection.count_documents({})
                collection_stats[collection_name] = {
                    **info,
                    "record_count": count,
                    "status": "✅ Active" if count > 0 else "⚠️ Empty"
                }
                total_records += count
            except Exception as e:
                collection_stats[collection_name] = {
                    **info,
                    "record_count": 0,
                    "status": f"❌ Error: {str(e)}"
                }
        
        success_response = create_success_response(
            message="Medical history collections overview retrieved successfully",
            data={
                "collections": collection_stats,
                "summary": {
                    "total_collections": len(collections_info),
                    "total_records": total_records,
                    "active_collections": len([c for c in collection_stats.values() if c["record_count"] > 0]),
                    "empty_collections": len([c for c in collection_stats.values() if c["record_count"] == 0])
                }
            },
            request_id=request_id
        )
        
        return success_response.dict()
        
    except Exception as e:
        logger.error(f"Error getting medical history collections: {e}")
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                "INTERNAL_SERVER_ERROR",
                custom_message=f"Failed to retrieve collections overview: {str(e)}",
                request_id=request.headers.get("X-Request-ID")
            ).dict()
        )

@router.get(
    "/medical-history/patient/{patient_id}",
    response_model=PatientMedicalHistoryResponse,
    summary="Get Patient Medical History",
    description="""
    ## Patient Medical History Retrieval
    
    Get comprehensive medical history for a specific patient across all data types.
    
    ### Features:
    - **Complete Medical Records**: All medical data types for the patient
    - **Flexible Filtering**: Filter by collection type, date range
    - **Pagination Support**: Efficient handling of large datasets
    - **Multi-Collection Data**: Blood pressure, temperature, SPO2, etc.
    - **Structured Response**: Organized by medical data type
    
    ### Query Parameters:
    - `collection_type`: Filter by specific medical data type (optional)
    - `limit`: Number of records per collection (default: 100)
    - `skip`: Number of records to skip (default: 0)
    - `date_from`: Start date filter (ISO format, optional)
    - `date_to`: End date filter (ISO format, optional)
    
    ### Medical Data Types:
    - `blood_pressure_histories`: Blood pressure readings
    - `temprature_data_histories`: Temperature measurements
    - `spo2_histories`: Oxygen saturation levels
    - `blood_sugar_histories`: Blood glucose readings
    - `sleep_data_histories`: Sleep tracking data
    - `step_histories`: Physical activity data
    - And more...
    
    ### Response Structure:
    - `summary`: Patient overview and record counts
    - `medical_history`: Organized data by collection type
    - `pagination`: Current pagination status
    
    ### Authentication:
    Requires valid JWT Bearer token.
    """,
    responses={
        200: {
            "description": "Patient medical history retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Patient medical history retrieved successfully",
                        "data": {
                            "summary": {
                                "patient_id": "622035a5fd26d7b6d9b7730c",
                                "total_records": 2853,
                                "collections_with_data": 4,
                                "date_range": {
                                    "from": "2022-01-01T00:00:00Z",
                                    "to": "2024-12-31T23:59:59Z"
                                }
                            },
                            "medical_history": {
                                "temprature_data_histories": {
                                    "count": 2574,
                                    "records": [
                                        {
                                            "temprature_data": 36.5,
                                            "temprature_import_date": "2024-01-15T10:30:00Z"
                                        }
                                    ]
                                }
                            }
                        }
                    }
                }
            }
        },
        404: {"description": "Patient not found"},
        401: {"description": "Authentication required"},
        500: {"description": "Internal server error"}
    },
    tags=["ava4"]
)
async def get_patient_medical_history(
    patient_id: str,
    request: Request,
    collection_type: Optional[str] = Query(None, description="Filter by specific medical data type"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records per collection"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    date_from: Optional[str] = Query(None, description="Start date filter (ISO format)"),
    date_to: Optional[str] = Query(None, description="End date filter (ISO format)"),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get comprehensive medical history for a specific patient"""
    try:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        # Validate patient exists
        patient_collection = mongodb_service.get_collection("patients")
        try:
            patient_obj_id = ObjectId(patient_id)
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
        
        patient = await patient_collection.find_one({"_id": patient_obj_id})
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
        
        # Define collections to query
        collections_to_query = [
            "blood_pressure_histories",
            "blood_sugar_histories", 
            "body_data_histories",
            "creatinine_histories",
            "lipid_histories",
            "sleep_data_histories",
            "spo2_histories",
            "step_histories",
            "temprature_data_histories",
            "admit_data_histories",
            "allergy_histories",
            "medication_histories",
            "underlying_disease_histories"
        ]
        
        # Filter by collection type if specified
        if collection_type:
            if collection_type not in collections_to_query:
                raise HTTPException(
                    status_code=400,
                    detail=create_error_response(
                        "INVALID_COLLECTION_TYPE",
                        field="collection_type",
                        value=collection_type,
                        custom_message=f"Invalid collection type. Valid types: {collections_to_query}",
                        request_id=request_id
                    ).dict()
                )
            collections_to_query = [collection_type]
        
        # Build date filter
        date_filter = {}
        if date_from or date_to:
            date_filter = {}
            if date_from:
                try:
                    date_filter["$gte"] = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
                except:
                    raise HTTPException(status_code=400, detail="Invalid date_from format. Use ISO format.")
            if date_to:
                try:
                    date_filter["$lte"] = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
                except:
                    raise HTTPException(status_code=400, detail="Invalid date_to format. Use ISO format.")
        
        # Query each collection
        medical_history = {}
        total_records = 0
        
        for collection_name in collections_to_query:
            try:
                collection = mongodb_service.get_collection(collection_name)
                
                # Build query - patient_id might be stored as $oid format
                query = {"patient_id.$oid": patient_id}
                
                # Try alternative query format if first doesn't work
                records = await collection.find(query).limit(limit).skip(skip).to_list(length=limit)
                if not records:
                    query = {"patient_id": patient_obj_id}
                    records = await collection.find(query).limit(limit).skip(skip).to_list(length=limit)
                
                # Apply date filtering to data array if specified
                filtered_records = []
                for record in records:
                    if date_filter and "data" in record:
                        # Filter data array by timestamp
                        filtered_data = []
                        for data_item in record.get("data", []):
                            item_timestamp = None
                            # Try different timestamp field names
                            for ts_field in ["timestamp", "admit_date", "medication_import_date", "diagnosis_date"]:
                                if ts_field in data_item:
                                    item_timestamp = data_item[ts_field]
                                    break
                            
                            if item_timestamp:
                                if isinstance(item_timestamp, str):
                                    try:
                                        item_timestamp = datetime.fromisoformat(item_timestamp.replace('Z', '+00:00'))
                                    except:
                                        continue
                                
                                # Check if timestamp is within range
                                if date_filter.get("$gte") and item_timestamp < date_filter["$gte"]:
                                    continue
                                if date_filter.get("$lte") and item_timestamp > date_filter["$lte"]:
                                    continue
                            
                            filtered_data.append(data_item)
                        
                        if filtered_data:
                            record["data"] = filtered_data
                            filtered_records.append(record)
                    else:
                        filtered_records.append(record)
                
                # Serialize and count
                serialized_records = serialize_mongodb_response(filtered_records)
                record_count = sum(len(record.get("data", [])) for record in serialized_records)
                
                medical_history[collection_name] = {
                    "collection_name": collection_name,
                    "records": serialized_records,
                    "record_count": record_count,
                    "document_count": len(serialized_records)
                }
                total_records += record_count
                
            except Exception as e:
                logger.warning(f"Error querying {collection_name}: {e}")
                medical_history[collection_name] = {
                    "collection_name": collection_name,
                    "records": [],
                    "record_count": 0,
                    "document_count": 0,
                    "error": str(e)
                }
        
        # Get patient basic info
        patient_info = serialize_mongodb_response(patient)
        patient_basic = {
            "patient_id": patient_info.get("_id"),
            "name": f"{patient_info.get('first_name', '')} {patient_info.get('last_name', '')}".strip(),
            "gender": patient_info.get("gender"),
            "birth_date": patient_info.get("birth_date"),
            "phone": patient_info.get("phone")
        }
        
        success_response = create_success_response(
            message="Patient medical history retrieved successfully",
            data={
                "patient": patient_basic,
                "medical_history": medical_history,
                "summary": {
                    "total_records": total_records,
                    "collections_with_data": len([c for c in medical_history.values() if c["record_count"] > 0]),
                    "date_range": {
                        "from": date_from,
                        "to": date_to
                    },
                    "pagination": {
                        "limit": limit,
                        "skip": skip
                    }
                }
            },
            request_id=request_id
        )
        
        return success_response.dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting patient medical history: {e}")
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                "INTERNAL_SERVER_ERROR",
                custom_message=f"Failed to retrieve medical history: {str(e)}",
                request_id=request.headers.get("X-Request-ID")
            ).dict()
        )

@router.get(
    "/medical-history/trends/{patient_id}",
    response_model=MedicalTrendsResponse,
    summary="Get Patient Medical Trends Analysis",
    description="""
    ## Medical Trends Analysis
    
    Analyze medical trends and patterns for a specific patient over time.
    
    ### Features:
    - **Statistical Analysis**: Min, max, average, latest values
    - **Time-based Trends**: Configurable time periods
    - **Multiple Metrics**: Support for various medical data types
    - **Trend Visualization**: Data ready for charts and graphs
    - **Historical Analysis**: Long-term health monitoring
    
    ### Supported Metric Types:
    - `blood_pressure`: Systolic, diastolic, pulse readings
    - `blood_sugar`: Fasting, post-meal glucose levels
    - `temperature`: Body temperature measurements
    - `spo2`: Oxygen saturation and pulse rate
    - `body_data`: Weight, BMI, body composition
    - `sleep`: Sleep duration and quality metrics
    - `steps`: Physical activity tracking
    - `creatinine`: Kidney function markers
    - `lipid`: Cholesterol and lipid profiles
    
    ### Query Parameters:
    - `metric_type`: Type of medical data to analyze (required)
    - `days`: Number of days to analyze (default: 30, max: 3650)
    
    ### Response Analytics:
    - `total_readings`: Number of data points analyzed
    - `date_range`: Time period covered
    - `statistics`: Statistical analysis per metric
    - `trends`: Time-series data for visualization
    
    ### Authentication:
    Requires valid JWT Bearer token.
    """,
    responses={
        200: {
            "description": "Medical trends analysis completed successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Medical trends analysis completed successfully",
                        "data": {
                            "analytics": {
                                "total_readings": 34115,
                                "date_range": {
                                    "start": "2022-10-10T11:51:45.234672",
                                    "end": "2025-07-06T11:51:45.234672",
                                    "days": 1000
                                },
                                "statistics": {
                                    "temprature_data": {
                                        "count": 34115,
                                        "min": 21.6,
                                        "max": 44.2,
                                        "avg": 36.34,
                                        "latest": 36.6,
                                        "unit": "°C"
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },
        400: {"description": "Invalid metric type or parameters"},
        404: {"description": "Patient not found"},
        401: {"description": "Authentication required"},
        500: {"description": "Internal server error"}
    },
    tags=["ava4"]
)
async def get_patient_medical_trends(
    patient_id: str,
    metric_type: str,
    request: Request,
    days: int = Query(30, ge=1, le=3650, description="Number of days to analyze"),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get medical trends and analytics for a specific patient and metric"""
    try:
        request_id = request.headers.get("X-Request-ID")
        
        # Validate metric type
        valid_metrics = {
            "blood_pressure": {
                "collection": "blood_pressure_histories",
                "fields": ["systolic", "diastolic", "pulse"],
                "units": ["mmHg", "mmHg", "bpm"],
                "timestamp_field": "blood_pressure_import_date"
            },
            "blood_sugar": {
                "collection": "blood_sugar_histories", 
                "fields": ["fasting_dtx", "post_meal_dtx", "no_marker_dtx"],
                "units": ["mg/dL", "mg/dL", "mg/dL"],
                "timestamp_field": "blood_sugar_import_date"
            },
            "spo2": {
                "collection": "spo2_histories",
                "fields": ["spo2_data", "spo2_pr_data", "spo2_resp_data"],
                "units": ["%", "bpm", "rpm"],
                "timestamp_field": "spo2_import_date"
            },
            "temperature": {
                "collection": "temprature_data_histories",
                "fields": ["temprature_data"],
                "units": ["°C"],
                "timestamp_field": "temprature_import_date"
            },
            "weight": {
                "collection": "body_data_histories",
                "fields": ["weight", "bmi"],
                "units": ["kg", "kg/m²"],
                "timestamp_field": "body_data_import_date"
            },
            "sleep": {
                "collection": "sleep_data_histories",
                "fields": ["sleep_num", "sleep_time"],
                "units": ["score", "time"],
                "timestamp_field": "sleep_data_import_date"
            },
            "steps": {
                "collection": "step_histories",
                "fields": ["step"],
                "units": ["steps"],
                "timestamp_field": "step_import_date"
            }
        }
        
        if metric_type not in valid_metrics:
            raise HTTPException(
                status_code=400,
                detail=create_error_response(
                    "INVALID_METRIC_TYPE",
                    field="metric_type",
                    value=metric_type,
                    custom_message=f"Invalid metric type. Valid types: {list(valid_metrics.keys())}",
                    request_id=request_id
                ).dict()
            )
        
        # Get metric configuration
        metric_config = valid_metrics[metric_type]
        collection_name = metric_config["collection"]
        
        # Calculate date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Query the specific collection
        collection = mongodb_service.get_collection(collection_name)
        
        # Try both query formats for patient_id
        query = {"patient_id.$oid": patient_id}
        records = await collection.find(query).to_list(length=None)
        if not records:
            try:
                patient_obj_id = ObjectId(patient_id)
                query = {"patient_id": patient_obj_id}
                records = await collection.find(query).to_list(length=None)
            except:
                pass
        
        if not records:
            # Return empty trend data
            success_response = create_success_response(
                message=f"No {metric_type} data found for patient",
                data={
                    "patient_id": patient_id,
                    "metric_type": metric_type,
                    "trend_data": [],
                    "analytics": {
                        "total_readings": 0,
                        "date_range": {
                            "start": start_date.isoformat(),
                            "end": end_date.isoformat(),
                            "days": days
                        }
                    }
                },
                request_id=request_id
            )
            return success_response.dict()
        
        # Extract and filter data points
        trend_data = []
        for record in records:
            data_points = record.get("data", [])
            for point in data_points:
                # Get timestamp using the correct field name for this metric type
                timestamp_field = metric_config["timestamp_field"]
                timestamp = point.get(timestamp_field)
                if not timestamp:
                    continue
                
                # Handle different timestamp formats
                if isinstance(timestamp, dict) and "$date" in timestamp:
                    timestamp = timestamp["$date"]
                
                if isinstance(timestamp, str):
                    try:
                        timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    except:
                        continue
                elif hasattr(timestamp, 'timestamp'):
                    # Handle datetime objects
                    timestamp = timestamp
                else:
                    continue
                
                # Filter by date range
                if timestamp < start_date or timestamp > end_date:
                    continue
                
                # Extract metric values
                data_point = {
                    "timestamp": timestamp.isoformat(),
                    "device_id": point.get("device_id"),
                    "values": {}
                }
                
                for i, field in enumerate(metric_config["fields"]):
                    value = point.get(field)
                    if value is not None:
                        data_point["values"][field] = {
                            "value": value,
                            "unit": metric_config["units"][i] if i < len(metric_config["units"]) else ""
                        }
                
                if data_point["values"]:
                    trend_data.append(data_point)
        
        # Sort by timestamp
        trend_data.sort(key=lambda x: x["timestamp"])
        
        # Calculate analytics
        analytics = {
            "total_readings": len(trend_data),
            "date_range": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "days": days
            },
            "statistics": {}
        }
        
        # Calculate statistics for each field
        for field in metric_config["fields"]:
            values = [point["values"][field]["value"] for point in trend_data if field in point["values"]]
            if values:
                analytics["statistics"][field] = {
                    "count": len(values),
                    "min": min(values),
                    "max": max(values),
                    "avg": sum(values) / len(values),
                    "latest": values[-1] if values else None,
                    "unit": metric_config["units"][metric_config["fields"].index(field)]
                }
        
        success_response = create_success_response(
            message=f"Medical trends for {metric_type} retrieved successfully",
            data={
                "patient_id": patient_id,
                "metric_type": metric_type,
                "trend_data": trend_data,
                "analytics": analytics
            },
            request_id=request_id
        )
        
        return success_response.dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting medical trends: {e}")
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                "INTERNAL_SERVER_ERROR",
                custom_message=f"Failed to retrieve medical trends: {str(e)}",
                request_id=request.headers.get("X-Request-ID")
            ).dict()
        ) 

@router.get(
    "/medical-history/analytics",
    response_model=MedicalAnalyticsResponse,
    summary="Get System-Wide Medical Analytics",
    description="""
    ## System-Wide Medical Analytics
    
    Get comprehensive analytics and insights across all medical history collections.
    
    ### Features:
    - **System Overview**: Total records, collections, and patients
    - **Collection Statistics**: Record counts and status per collection
    - **Data Quality Metrics**: Active vs inactive collections
    - **Performance Insights**: Top collections by activity
    - **Real-time Data**: Live system statistics
    
    ### Analytics Included:
    - Total medical records across all collections
    - Number of patients with medical data
    - Collection-wise record distribution
    - Data quality and completeness metrics
    - Top performing collections
    
    ### Response Structure:
    - `summary`: High-level system statistics
    - `collections`: Detailed collection analytics
    - `top_collections`: Most active collections ranked
    
    ### Use Cases:
    - System monitoring and health checks
    - Data quality assessment
    - Performance optimization
    - Resource planning
    - Compliance reporting
    
    ### Authentication:
    Requires valid JWT Bearer token.
    """,
    responses={
        200: {
            "description": "System-wide medical analytics retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Medical history analytics retrieved successfully",
                        "data": {
                            "summary": {
                                "total_collections": 13,
                                "active_collections": 13,
                                "total_medical_records": 56219,
                                "patients_with_medical_data": 246
                            },
                            "collections": {
                                "blood_pressure_histories": {
                                    "record_count": 21542,
                                    "status": "active",
                                    "last_updated": "2024-01-15T10:30:00Z"
                                }
                            },
                            "top_collections": [
                                ["temprature_data_histories", 34115],
                                ["blood_pressure_histories", 21542]
                            ]
                        }
                    }
                }
            }
        },
        401: {"description": "Authentication required"},
        500: {"description": "Internal server error"}
    },
    tags=["ava4"]
)
async def get_medical_history_analytics(
    request: Request,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get system-wide medical history analytics"""
    try:
        request_id = request.headers.get("X-Request-ID")
        
        # Define all medical history collections
        collections = [
            "blood_pressure_histories", "blood_sugar_histories", "body_data_histories",
            "creatinine_histories", "lipid_histories", "sleep_data_histories",
            "spo2_histories", "step_histories", "temprature_data_histories",
            "admit_data_histories", "allergy_histories", "medication_histories",
            "underlying_disease_histories"
        ]
        
        analytics = {}
        total_records = 0
        
        for collection_name in collections:
            try:
                collection = mongodb_service.get_collection(collection_name)
                count = await collection.count_documents({})
                analytics[collection_name] = {
                    "record_count": count,
                    "status": "active" if count > 0 else "empty"
                }
                total_records += count
            except Exception as e:
                analytics[collection_name] = {
                    "record_count": 0,
                    "status": "error",
                    "error": str(e)
                }
        
        # Get unique patients with medical data
        patients_with_data = set()
        for collection_name in collections:
            if analytics[collection_name]["record_count"] > 0:
                try:
                    collection = mongodb_service.get_collection(collection_name)
                    # Get distinct patient IDs
                    patient_ids = await collection.distinct("patient_id")
                    for pid in patient_ids:
                        if isinstance(pid, dict) and "$oid" in pid:
                            patients_with_data.add(pid["$oid"])
                        elif isinstance(pid, str):
                            patients_with_data.add(pid)
                except Exception:
                    continue
        
        success_response = create_success_response(
            message="Medical history analytics retrieved successfully",
            data={
                "summary": {
                    "total_collections": len(collections),
                    "active_collections": len([c for c in analytics.values() if c["status"] == "active"]),
                    "total_medical_records": total_records,
                    "patients_with_medical_data": len(patients_with_data)
                },
                "collections": analytics,
                "top_collections": sorted(
                    [(k, v["record_count"]) for k, v in analytics.items()],
                    key=lambda x: x[1],
                    reverse=True
                )[:5]
            }
        )
        
        return success_response
        
    except Exception as e:
        logger.error(f"Error in medical history analytics: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                error_code="ANALYTICS_ERROR",
                custom_message="Failed to retrieve medical history analytics"
            ).dict()
        )

@router.get("/medical-history/analytics/{patient_id}")
async def get_patient_medical_analytics(
    patient_id: str,
    request: Request,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get comprehensive medical analytics for a specific patient"""
    try:
        request_id = request.headers.get("X-Request-ID")
        
        # Validate patient exists
        patients_collection = mongodb_service.get_collection("patients")
        patient = await patients_collection.find_one({"_id": ObjectId(patient_id)})
        if not patient:
            raise HTTPException(
                status_code=404,
                detail=create_error_response(
                    error_code="PATIENT_NOT_FOUND",
                    custom_message="Patient not found"
                ).dict()
            )
        
        # Define collections with their key fields
        collections_config = {
            "blood_pressure_histories": {
                "name": "Blood Pressure",
                "key_fields": ["systolic", "diastolic", "pulse"],
                "timestamp_field": "blood_pressure_import_date"
            },
            "blood_sugar_histories": {
                "name": "Blood Sugar",
                "key_fields": ["fasting_dtx", "post_meal_dtx", "no_marker_dtx"],
                "timestamp_field": "blood_sugar_import_date"
            },
            "spo2_histories": {
                "name": "SPO2/Oxygen Saturation",
                "key_fields": ["spo2_data", "spo2_pr_data"],
                "timestamp_field": "spo2_import_date"
            },
            "temprature_data_histories": {
                "name": "Temperature",
                "key_fields": ["temprature_data"],
                "timestamp_field": "temprature_import_date"
            },
            "body_data_histories": {
                "name": "Body Data",
                "key_fields": ["weight", "bmi", "height"],
                "timestamp_field": "body_data_import_date"
            },
            "step_histories": {
                "name": "Step Count",
                "key_fields": ["step"],
                "timestamp_field": "step_import_date"
            },
            "sleep_data_histories": {
                "name": "Sleep Data",
                "key_fields": ["sleep_num", "sleep_time"],
                "timestamp_field": "sleep_data_import_date"
            }
        }
        
        patient_analytics = {}
        total_records = 0
        date_range = {"earliest": None, "latest": None}
        
        for collection_name, config in collections_config.items():
            try:
                collection = mongodb_service.get_collection(collection_name)
                
                # Query with patient_id.$oid format
                records = await collection.find({"patient_id.$oid": patient_id}).to_list(length=None)
                
                if records:
                    record_count = len(records)
                    total_records += record_count
                    
                    # Extract timestamps
                    timestamps = []
                    for record in records:
                        timestamp = record.get(config["timestamp_field"])
                        if timestamp:
                            if isinstance(timestamp, str):
                                try:
                                    timestamps.append(datetime.fromisoformat(timestamp.replace('Z', '+00:00')))
                                except:
                                    pass
                    
                    # Calculate date range
                    if timestamps:
                        earliest = min(timestamps)
                        latest = max(timestamps)
                        
                        if date_range["earliest"] is None or earliest < date_range["earliest"]:
                            date_range["earliest"] = earliest
                        if date_range["latest"] is None or latest > date_range["latest"]:
                            date_range["latest"] = latest
                    
                    patient_analytics[collection_name] = {
                        "collection_name": config["name"],
                        "record_count": record_count,
                        "date_range": {
                            "earliest": timestamps[0].isoformat() if timestamps else None,
                            "latest": timestamps[-1].isoformat() if timestamps else None
                        },
                        "status": "active"
                    }
                else:
                    patient_analytics[collection_name] = {
                        "collection_name": config["name"],
                        "record_count": 0,
                        "status": "no_data"
                    }
                    
            except Exception as e:
                patient_analytics[collection_name] = {
                    "collection_name": config["name"],
                    "record_count": 0,
                    "status": "error",
                    "error": str(e)
                }
        
        # Calculate monitoring period
        monitoring_days = 0
        if date_range["earliest"] and date_range["latest"]:
            monitoring_days = (date_range["latest"] - date_range["earliest"]).days
        
        success_response = create_success_response(
            message="Patient medical analytics retrieved successfully",
            data={
                "patient_info": {
                    "patient_id": patient_id,
                    "name": f"{patient.get('first_name', '')} {patient.get('last_name', '')}".strip()
                },
                "summary": {
                    "total_medical_records": total_records,
                    "active_data_types": len([c for c in patient_analytics.values() if c["status"] == "active"]),
                    "monitoring_period_days": monitoring_days,
                    "data_date_range": {
                        "earliest": date_range["earliest"].isoformat() if date_range["earliest"] else None,
                        "latest": date_range["latest"].isoformat() if date_range["latest"] else None
                    }
                },
                "data_types": patient_analytics,
                "most_recorded_types": sorted(
                    [(k, v["record_count"]) for k, v in patient_analytics.items() if v["status"] == "active"],
                    key=lambda x: x[1],
                    reverse=True
                )[:3]
            }
        )
        
        return success_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in patient medical analytics: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                error_code="PATIENT_ANALYTICS_ERROR",
                custom_message="Failed to retrieve patient medical analytics"
            ).dict()
        )

@router.get(
    "/patients/raw-documents",
    summary="Get Raw Patient Documents (AVA4)",
    description="""
    ## AVA4 Raw Patient Document Analysis
    
    Access complete MongoDB patient documents for AVA4 device integration analysis.
    
    ### Features:
    - **Complete Patient Structure**: All 269 fields per patient document
    - **AVA4 Device Integration**: Focus on AVA4-related patient fields
    - **Field Analysis**: Automatic data type detection and statistics
    - **Sample Values**: Preview of actual field content
    - **Standard Field Detection**: Identification of core patient fields vs extended data
    - **Pagination Support**: Handle large document sets efficiently
    
    ### Key AVA4 Integration Fields:
    
    #### **AVA4 Device Identifiers**:
    - `ava_mac_address`: Primary AVA4 device MAC address
    - `ava_box_id`: AVA4 box/gateway identifier
    - `ava_sim_card`: SIM card information for connectivity
    - `ava_box_version`: Device firmware/software version
    
    #### **Medical Device MAC Addresses**:
    - `blood_pressure_mac_address`: BP monitor MAC address
    - `blood_glucose_mac_address`: Glucose meter MAC address
    - `body_temperature_mac_address`: Temperature sensor MAC address
    - `fingertip_pulse_oximeter_mac_address`: SPO2 sensor MAC address
    - `cholesterol_mac_address`: Cholesterol meter MAC address
    
    #### **Medical Alert Thresholds for AVA4**:
    - **Blood Pressure**: `bp_sbp_above`, `bp_sbp_below`, `bp_dbp_above`, `bp_dbp_below`
    - **Blood Sugar**: `glucose_normal_before`, `glucose_normal_after`
    - **Temperature**: `temperature_normal_above`, `temperature_normal_below`
    - **SPO2**: `spo2_normal_above`, `spo2_normal_below`
    
    ### Query Parameters:
    - `limit`: Number of documents to return (1-50, default: 5)
    - `skip`: Number of documents to skip for pagination
    - `patient_id`: Filter by specific patient ObjectId
    - `include_deleted`: Include soft-deleted patients (default: false)
    
    ### Response Features:
    - **Raw Documents**: Complete MongoDB structure preserved
    - **Field Analysis**: Data type detection and usage statistics per field
    - **Standard Field Detection**: Identifies core vs extended patient fields
    - **Sample Values**: Up to 3 sample values per field for preview
    - **Pagination Info**: Total count and navigation details
    
    ### AVA4 Use Cases:
    - **Device Configuration**: Map patient thresholds to AVA4 alerts
    - **Patient Device Linking**: Associate patients with AVA4 devices
    - **Medical Integration**: Understand patient medical data structure
    - **Alert Setup**: Configure AVA4 medical alerts based on patient data
    - **Data Migration**: Map existing patient data to AVA4 format
    
    ### Standard Patient Fields (29 core fields):
    `_id`, `first_name`, `last_name`, `nickname`, `gender`, `birth_date`, `id_card`, 
    `phone`, `email`, `address`, `province_code`, `district_code`, `sub_district_code`, 
    `postal_code`, `emergency_contact_name`, `emergency_contact_phone`, 
    `emergency_contact_relationship`, `blood_type`, `height`, `weight`, `bmi`, 
    `watch_mac_address`, `ava_mac_address`, `new_hospital_ids`, `created_at`, 
    `updated_at`, `is_active`, `is_deleted`
    
    ### Authentication:
    Requires valid JWT Bearer token.
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
                                    "_id": "620c83a78ae03f05312cb9b5",
                                    "first_name": "TEST 001",
                                    "last_name": "Patient 1",
                                    "phone": "789456789",
                                    "ava_mac_address": "AA:BB:CC:DD:EE:FF",
                                    "ava_box_id": "AVA4-001",
                                    "blood_pressure_mac_address": "11:22:33:44:55:66",
                                    "blood_glucose_mac_address": "",
                                    "bp_sbp_above": 140,
                                    "bp_sbp_below": 90,
                                    "bp_dbp_above": 90,
                                    "bp_dbp_below": 60,
                                    "glucose_normal_before": 100,
                                    "glucose_normal_after": 140,
                                    "created_at": "2022-02-16T04:55:03.469000",
                                    "hospital_data": [],
                                    "amy_id": "AMY001"
                                }
                            ],
                            "total_count": 431,
                            "returned_count": 1,
                            "field_analysis": {
                                "_id": {
                                    "count": 1,
                                    "sample_values": ["620c83a78ae03f05312cb9b5"],
                                    "is_standard_field": True,
                                    "data_type": "str"
                                },
                                "ava_mac_address": {
                                    "count": 1,
                                    "sample_values": ["AA:BB:CC:DD:EE:FF"],
                                    "is_standard_field": True,
                                    "data_type": "str"
                                },
                                "bp_sbp_above": {
                                    "count": 1,
                                    "sample_values": [140],
                                    "is_standard_field": False,
                                    "data_type": "int"
                                }
                            },
                            "standard_patient_fields": [
                                "_id", "first_name", "last_name", "ava_mac_address"
                            ],
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
        500: {"description": "Internal server error"}
    },
    tags=["ava4"]
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
        
        patients_collection = mongodb_service.get_collection("patients")
        
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
        cursor = patients_collection.find(filter_query).skip(skip).limit(limit)
        raw_documents = await cursor.to_list(length=limit)
        
        # Get total count
        total_count = await patients_collection.count_documents(filter_query)
        
        # Analyze document structure
        field_analysis = {}
        patient_fields = [
            "_id", "first_name", "last_name", "nickname", "gender", "birth_date",
            "id_card", "phone", "email", "address", "province_code", "district_code",
            "sub_district_code", "postal_code", "emergency_contact_name", 
            "emergency_contact_phone", "emergency_contact_relationship", "blood_type",
            "height", "weight", "bmi", "watch_mac_address", "ava_mac_address",
            "new_hospital_ids", "created_at", "updated_at", "is_active", "is_deleted"
        ]
        
        for doc in raw_documents:
            for field in doc.keys():
                if field not in field_analysis:
                    field_analysis[field] = {
                        "count": 0,
                        "sample_values": [],
                        "is_standard_field": field in patient_fields,
                        "data_type": None
                    }
                
                field_analysis[field]["count"] += 1
                field_analysis[field]["data_type"] = type(doc[field]).__name__
                
                # Store sample values (limit to 3)
                if len(field_analysis[field]["sample_values"]) < 3:
                    value = doc[field]
                    if isinstance(value, ObjectId):
                        field_analysis[field]["sample_values"].append(str(value))
                    elif isinstance(value, datetime):
                        field_analysis[field]["sample_values"].append(value.isoformat())
                    elif isinstance(value, (dict, list)):
                        field_analysis[field]["sample_values"].append(str(value)[:100] + "..." if len(str(value)) > 100 else str(value))
                    else:
                        field_analysis[field]["sample_values"].append(value)
        
        # Serialize documents for response while preserving raw structure
        serialized_documents = serialize_mongodb_response(raw_documents)
        
        success_response = create_success_response(
            message="Raw patient documents retrieved successfully",
            data={
                "raw_documents": serialized_documents,
                "total_count": total_count,
                "returned_count": len(serialized_documents),
                "field_analysis": field_analysis,
                "standard_patient_fields": patient_fields,
                "pagination": {
                    "limit": limit,
                    "skip": skip,
                    "has_more": total_count > (skip + len(serialized_documents))
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

@router.get("/test-patient-raw")
async def test_patient_raw_endpoint(current_user: Dict[str, Any] = Depends(require_auth())):
    """Simple test endpoint for patient raw data"""
    return {
        "message": "Patient raw endpoint test successful", 
        "timestamp": datetime.utcnow().isoformat(),
        "endpoint": "/api/ava4/test-patient-raw"
    }

@router.get("/patients-raw")
async def get_raw_patients_simple(
    limit: int = Query(5, ge=1, le=50),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get raw patient documents - simplified version"""
    try:
        patients_collection = mongodb_service.get_collection("patients")
        
        # Simple query
        cursor = patients_collection.find({"is_deleted": {"$ne": True}}).limit(limit)
        raw_documents = await cursor.to_list(length=limit)
        
        # Basic serialization
        serialized_docs = serialize_mongodb_response(raw_documents)
        
        return {
            "success": True,
            "message": "Raw patient documents retrieved",
            "data": {
                "raw_documents": serialized_docs,
                "count": len(serialized_docs)
            }
        }
        
    except Exception as e:
        logger.error(f"Error in raw patients endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))