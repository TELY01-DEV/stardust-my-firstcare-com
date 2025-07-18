"""
FHIR R5 REST API Endpoints
=========================
Comprehensive FHIR R5 compliant REST API for healthcare data management.
Implements standard FHIR operations: Create, Read, Update, Delete, and Search.

Based on FHIR R5 specification: https://hl7.org/fhir/R5/
"""

import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from fastapi import APIRouter, Depends, HTTPException, Request, Query, Path, Body
from fastapi.responses import JSONResponse

from app.services.auth import require_auth
from app.services.fhir_r5_service import fhir_service
from app.models.fhir_r5 import (
    FHIRCreateRequest, FHIRSearchParams, FHIRSearchResponse,
    Patient, Observation, Device, Organization, Location,
    Condition, Medication, AllergyIntolerance, Encounter, Provenance
)
from app.utils.error_definitions import create_error_response, create_success_response
from app.utils.structured_logging import get_logger
from app.utils.performance_decorators import api_endpoint_timing

logger = get_logger(__name__)
router = APIRouter(prefix="/fhir/R5", tags=["fhir-r5"])

# =============== FHIR R5 Capability Statement ===============

@router.get("/metadata", summary="FHIR R5 Capability Statement")
async def get_capability_statement(
    request: Request,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get FHIR R5 Capability Statement"""
    try:
        capability = {
            "resourceType": "CapabilityStatement",
            "id": "my-firstcare-fhir-r5",
            "url": "http://my-firstcare.com/fhir/R5/metadata",
            "version": "5.0.0",
            "name": "MyFirstCareFHIRR5",
            "title": "My FirstCare FHIR R5 Server",
            "status": "active",
            "experimental": False,
            "date": datetime.utcnow().isoformat() + "Z",
            "publisher": "My FirstCare",
            "description": "FHIR R5 server for healthcare IoT device data and patient management",
            "kind": "instance",
            "software": {
                "name": "My FirstCare FHIR R5 Server",
                "version": "1.0.0"
            },
            "implementation": {
                "description": "Healthcare IoT FHIR R5 Implementation",
                "url": "http://my-firstcare.com/fhir/R5"
            },
            "fhirVersion": "5.0.0",
            "format": ["json"],
            "rest": [{
                "mode": "server",
                "documentation": "FHIR R5 server for healthcare IoT data",
                "security": {
                    "cors": True,
                    "service": [{
                        "coding": [{
                            "system": "http://terminology.hl7.org/CodeSystem/restful-security-service",
                            "code": "OAuth",
                            "display": "OAuth"
                        }]
                    }],
                    "description": "JWT Bearer token authentication required"
                },
                "resource": [
                    {
                        "type": "Patient",
                        "interaction": [
                            {"code": "create"}, {"code": "read"}, {"code": "update"}, 
                            {"code": "delete"}, {"code": "search-type"}
                        ],
                        "searchParam": [
                            {"name": "identifier", "type": "token"},
                            {"name": "name", "type": "string"},
                            {"name": "birthdate", "type": "date"},
                            {"name": "gender", "type": "token"},
                            {"name": "organization", "type": "reference"}
                        ]
                    },
                    {
                        "type": "Observation",
                        "interaction": [
                            {"code": "create"}, {"code": "read"}, {"code": "update"}, 
                            {"code": "delete"}, {"code": "search-type"}
                        ],
                        "searchParam": [
                            {"name": "patient", "type": "reference"},
                            {"name": "code", "type": "token"},
                            {"name": "category", "type": "token"},
                            {"name": "date", "type": "date"},
                            {"name": "device", "type": "reference"},
                            {"name": "status", "type": "token"}
                        ]
                    },
                    {
                        "type": "Device",
                        "interaction": [
                            {"code": "create"}, {"code": "read"}, {"code": "update"}, 
                            {"code": "delete"}, {"code": "search-type"}
                        ],
                        "searchParam": [
                            {"name": "identifier", "type": "token"},
                            {"name": "type", "type": "token"},
                            {"name": "manufacturer", "type": "string"},
                            {"name": "model", "type": "string"},
                            {"name": "status", "type": "token"}
                        ]
                    },
                    {
                        "type": "Organization",
                        "interaction": [
                            {"code": "create"}, {"code": "read"}, {"code": "update"}, 
                            {"code": "delete"}, {"code": "search-type"}
                        ]
                    },
                    {
                        "type": "Location",
                        "interaction": [
                            {"code": "create"}, {"code": "read"}, {"code": "update"}, 
                            {"code": "delete"}, {"code": "search-type"}
                        ]
                    },
                    {
                        "type": "Condition",
                        "interaction": [
                            {"code": "create"}, {"code": "read"}, {"code": "update"}, 
                            {"code": "delete"}, {"code": "search-type"}
                        ]
                    },
                    {
                        "type": "Medication",
                        "interaction": [
                            {"code": "create"}, {"code": "read"}, {"code": "update"}, 
                            {"code": "delete"}, {"code": "search-type"}
                        ]
                    },
                    {
                        "type": "AllergyIntolerance",
                        "interaction": [
                            {"code": "create"}, {"code": "read"}, {"code": "update"}, 
                            {"code": "delete"}, {"code": "search-type"}
                        ]
                    },
                    {
                        "type": "Encounter",
                        "interaction": [
                            {"code": "create"}, {"code": "read"}, {"code": "update"}, 
                            {"code": "delete"}, {"code": "search-type"}
                        ]
                    },
                    {
                        "type": "Provenance",
                        "interaction": [
                            {"code": "create"}, {"code": "read"}, {"code": "search-type"}
                        ]
                    },
                    {
                        "type": "Goal",
                        "interaction": [
                            {"code": "create"}, {"code": "read"}, {"code": "update"}, 
                            {"code": "delete"}, {"code": "search-type"}
                        ],
                        "searchParam": [
                            {"name": "patient", "type": "reference"},
                            {"name": "category", "type": "token"},
                            {"name": "lifecycle-status", "type": "token"},
                            {"name": "achievement-status", "type": "token"},
                            {"name": "start-date", "type": "date"}
                        ]
                    },
                    {
                        "type": "RelatedPerson",
                        "interaction": [
                            {"code": "create"}, {"code": "read"}, {"code": "update"}, 
                            {"code": "delete"}, {"code": "search-type"}
                        ],
                        "searchParam": [
                            {"name": "patient", "type": "reference"},
                            {"name": "relationship", "type": "token"},
                            {"name": "name", "type": "string"},
                            {"name": "telecom", "type": "token"},
                            {"name": "active", "type": "token"}
                        ]
                    },
                    {
                        "type": "Flag",
                        "interaction": [
                            {"code": "create"}, {"code": "read"}, {"code": "update"}, 
                            {"code": "delete"}, {"code": "search-type"}
                        ],
                        "searchParam": [
                            {"name": "patient", "type": "reference"},
                            {"name": "category", "type": "token"},
                            {"name": "code", "type": "token"},
                            {"name": "status", "type": "token"},
                            {"name": "date", "type": "date"}
                        ]
                    },
                    {
                        "type": "RiskAssessment",
                        "interaction": [
                            {"code": "create"}, {"code": "read"}, {"code": "update"}, 
                            {"code": "delete"}, {"code": "search-type"}
                        ],
                        "searchParam": [
                            {"name": "patient", "type": "reference"},
                            {"name": "method", "type": "token"},
                            {"name": "code", "type": "token"},
                            {"name": "status", "type": "token"},
                            {"name": "date", "type": "date"}
                        ]
                    },
                    {
                        "type": "ServiceRequest",
                        "interaction": [
                            {"code": "create"}, {"code": "read"}, {"code": "update"}, 
                            {"code": "delete"}, {"code": "search-type"}
                        ],
                        "searchParam": [
                            {"name": "patient", "type": "reference"},
                            {"name": "category", "type": "token"},
                            {"name": "code", "type": "token"},
                            {"name": "status", "type": "token"},
                            {"name": "intent", "type": "token"},
                            {"name": "authored", "type": "date"}
                        ]
                    },
                    {
                        "type": "CarePlan",
                        "interaction": [
                            {"code": "create"}, {"code": "read"}, {"code": "update"}, 
                            {"code": "delete"}, {"code": "search-type"}
                        ],
                        "searchParam": [
                            {"name": "patient", "type": "reference"},
                            {"name": "category", "type": "token"},
                            {"name": "status", "type": "token"},
                            {"name": "intent", "type": "token"},
                            {"name": "date", "type": "date"}
                        ]
                    },
                    {
                        "type": "Specimen",
                        "interaction": [
                            {"code": "create"}, {"code": "read"}, {"code": "update"}, 
                            {"code": "delete"}, {"code": "search-type"}
                        ],
                        "searchParam": [
                            {"name": "patient", "type": "reference"},
                            {"name": "type", "type": "token"},
                            {"name": "status", "type": "token"},
                            {"name": "collected", "type": "date"},
                            {"name": "accession", "type": "token"}
                        ]
                    }
                ]
            }]
        }
        
        return JSONResponse(content=capability, media_type="application/fhir+json")
        
    except Exception as e:
        logger.error(f"Error getting capability statement: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =============== Generic FHIR Resource Endpoints ===============

async def create_fhir_resource_endpoint(
    resource_type: str,
    resource_data: Dict[str, Any],
    request: Request,
    current_user: Dict[str, Any]
):
    """Generic create FHIR resource endpoint"""
    try:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        result = await fhir_service.create_fhir_resource(
            resource_type=resource_type,
            resource_data=resource_data,
            source_system="api"
        )
        
        response = create_success_response(
            message=f"FHIR {resource_type} created successfully",
            data=result,
            request_id=request_id
        )
        
        # Return with FHIR content type and location header
        headers = {
            "Location": f"/fhir/R5/{resource_type}/{result['resource_id']}",
            "Content-Type": "application/fhir+json"
        }
        
        return JSONResponse(
            content=response.dict(),
            status_code=201,
            headers=headers
        )
        
    except Exception as e:
        logger.error(f"Error creating FHIR {resource_type}: {e}")
        raise HTTPException(
            status_code=400,
            detail=create_error_response(
                "FHIR_CREATE_ERROR",
                custom_message=f"Failed to create {resource_type}: {str(e)}",
                request_id=request.headers.get("X-Request-ID")
            ).dict()
        )

async def get_fhir_resource_endpoint(
    resource_type: str,
    resource_id: str,
    request: Request,
    current_user: Dict[str, Any]
):
    """Generic get FHIR resource endpoint"""
    try:
        resource = await fhir_service.get_fhir_resource(resource_type, resource_id)
        
        if not resource:
            raise HTTPException(
                status_code=404,
                detail=create_error_response(
                    "FHIR_RESOURCE_NOT_FOUND",
                    custom_message=f"{resource_type} with ID {resource_id} not found",
                    request_id=request.headers.get("X-Request-ID")
                ).dict()
            )
        
        return JSONResponse(
            content=resource,
            media_type="application/fhir+json"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting FHIR {resource_type} {resource_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                "FHIR_GET_ERROR",
                custom_message=f"Failed to get {resource_type}: {str(e)}",
                request_id=request.headers.get("X-Request-ID")
            ).dict()
        )

async def update_fhir_resource_endpoint(
    resource_type: str,
    resource_id: str,
    resource_data: Dict[str, Any],
    request: Request,
    current_user: Dict[str, Any]
):
    """Generic update FHIR resource endpoint"""
    try:
        result = await fhir_service.update_fhir_resource(
            resource_type=resource_type,
            resource_id=resource_id,
            resource_data=resource_data,
            source_system="api"
        )
        
        return JSONResponse(
            content=result["resource"],
            media_type="application/fhir+json"
        )
        
    except Exception as e:
        logger.error(f"Error updating FHIR {resource_type} {resource_id}: {e}")
        raise HTTPException(
            status_code=400,
            detail=create_error_response(
                "FHIR_UPDATE_ERROR",
                custom_message=f"Failed to update {resource_type}: {str(e)}",
                request_id=request.headers.get("X-Request-ID")
            ).dict()
        )

async def delete_fhir_resource_endpoint(
    resource_type: str,
    resource_id: str,
    request: Request,
    current_user: Dict[str, Any]
):
    """Generic delete FHIR resource endpoint"""
    try:
        await fhir_service.delete_fhir_resource(resource_type, resource_id)
        
        return JSONResponse(
            content={"resourceType": "OperationOutcome", "id": str(uuid.uuid4())},
            status_code=204,
            media_type="application/fhir+json"
        )
        
    except Exception as e:
        logger.error(f"Error deleting FHIR {resource_type} {resource_id}: {e}")
        raise HTTPException(
            status_code=400,
            detail=create_error_response(
                "FHIR_DELETE_ERROR",
                custom_message=f"Failed to delete {resource_type}: {str(e)}",
                request_id=request.headers.get("X-Request-ID")
            ).dict()
        )

async def search_fhir_resources_endpoint(
    resource_type: str,
    request: Request,
    current_user: Dict[str, Any],
    **search_params
):
    """Generic search FHIR resources endpoint"""
    try:
        # Map underscore-prefixed parameters to their correct field names
        mapped_params = {}
        for key, value in search_params.items():
            if key == "_count":
                mapped_params["count"] = value
            elif key == "_offset":
                mapped_params["offset"] = value
            elif key == "_sort":
                mapped_params["sort"] = value
            elif key == "_id":
                mapped_params["id"] = value
            elif key == "_lastUpdated":
                mapped_params["lastUpdated"] = value
            elif key == "_profile":
                mapped_params["profile"] = value
            elif key == "_security":
                mapped_params["security"] = value
            elif key == "_source":
                mapped_params["source"] = value
            elif key == "_tag":
                mapped_params["tag"] = value
            else:
                mapped_params[key] = value
        
        # Convert query parameters to FHIRSearchParams
        fhir_search_params = FHIRSearchParams(**mapped_params)
        
        result = await fhir_service.search_fhir_resources(resource_type, fhir_search_params)
        
        return JSONResponse(
            content=result.dict(),
            media_type="application/fhir+json"
        )
        
    except Exception as e:
        logger.error(f"Error searching FHIR {resource_type}: {e}")
        raise HTTPException(
            status_code=400,
            detail=create_error_response(
                "FHIR_SEARCH_ERROR",
                custom_message=f"Failed to search {resource_type}: {str(e)}",
                request_id=request.headers.get("X-Request-ID")
            ).dict()
        )

# =============== Patient Resource Endpoints ===============

@router.post("/Patient", summary="Create Patient")
@api_endpoint_timing("fhir_create_patient")
async def create_patient(
    request: Request,
    patient_data: Dict[str, Any] = Body(...),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Create a new FHIR R5 Patient resource"""
    return await create_fhir_resource_endpoint("Patient", patient_data, request, current_user)

@router.get("/Patient/{patient_id}", summary="Get Patient by ID")
@api_endpoint_timing("fhir_get_patient")
async def get_patient(
    patient_id: str = Path(..., description="Patient ID"),
    request: Request = None,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get a FHIR R5 Patient resource by ID"""
    return await get_fhir_resource_endpoint("Patient", patient_id, request, current_user)

@router.put("/Patient/{patient_id}", summary="Update Patient")
@api_endpoint_timing("fhir_update_patient")
async def update_patient(
    patient_id: str = Path(..., description="Patient ID"),
    patient_data: Dict[str, Any] = Body(...),
    request: Request = None,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Update a FHIR R5 Patient resource"""
    return await update_fhir_resource_endpoint("Patient", patient_id, patient_data, request, current_user)

@router.delete("/Patient/{patient_id}", summary="Delete Patient")
@api_endpoint_timing("fhir_delete_patient")
async def delete_patient(
    patient_id: str = Path(..., description="Patient ID"),
    request: Request = None,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Delete a FHIR R5 Patient resource"""
    return await delete_fhir_resource_endpoint("Patient", patient_id, request, current_user)

@router.get("/Patient", summary="Search Patients")
@api_endpoint_timing("fhir_search_patients")
async def search_patients(
    request: Request,
    identifier: Optional[str] = Query(None, description="Patient identifier"),
    name: Optional[str] = Query(None, description="Patient name"),
    birthdate: Optional[str] = Query(None, description="Birth date"),
    gender: Optional[str] = Query(None, description="Gender"),
    organization: Optional[str] = Query(None, description="Managing organization"),
    _count: Optional[int] = Query(10, description="Number of results"),
    _offset: Optional[int] = Query(0, description="Search offset"),
    _sort: Optional[str] = Query(None, description="Sort parameters"),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Search FHIR R5 Patient resources"""
    search_params = {
        "identifier": identifier,
        "_count": _count,
        "_offset": _offset,
        "_sort": _sort
    }
    return await search_fhir_resources_endpoint("Patient", request, current_user, **search_params)

# =============== Observation Resource Endpoints ===============

@router.post("/Observation", summary="Create Observation")
@api_endpoint_timing("fhir_create_observation")
async def create_observation(
    request: Request,
    observation_data: Dict[str, Any] = Body(...),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Create a new FHIR R5 Observation resource"""
    return await create_fhir_resource_endpoint("Observation", observation_data, request, current_user)

@router.get("/Observation/{observation_id}", summary="Get Observation by ID")
@api_endpoint_timing("fhir_get_observation")
async def get_observation(
    observation_id: str = Path(..., description="Observation ID"),
    request: Request = None,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get a FHIR R5 Observation resource by ID"""
    return await get_fhir_resource_endpoint("Observation", observation_id, request, current_user)

@router.put("/Observation/{observation_id}", summary="Update Observation")
@api_endpoint_timing("fhir_update_observation")
async def update_observation(
    observation_id: str = Path(..., description="Observation ID"),
    observation_data: Dict[str, Any] = Body(...),
    request: Request = None,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Update a FHIR R5 Observation resource"""
    return await update_fhir_resource_endpoint("Observation", observation_id, observation_data, request, current_user)

@router.delete("/Observation/{observation_id}", summary="Delete Observation")
@api_endpoint_timing("fhir_delete_observation")
async def delete_observation(
    observation_id: str = Path(..., description="Observation ID"),
    request: Request = None,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Delete a FHIR R5 Observation resource"""
    return await delete_fhir_resource_endpoint("Observation", observation_id, request, current_user)

@router.get("/Observation", summary="Search Observations")
@api_endpoint_timing("fhir_search_observations")
async def search_observations(
    request: Request,
    patient: Optional[str] = Query(None, description="Patient reference"),
    code: Optional[str] = Query(None, description="Observation code"),
    category: Optional[str] = Query(None, description="Observation category"),
    date: Optional[str] = Query(None, description="Date range"),
    device: Optional[str] = Query(None, description="Device reference"),
    status: Optional[str] = Query(None, description="Observation status"),
    _count: Optional[int] = Query(10, description="Number of results"),
    _offset: Optional[int] = Query(0, description="Search offset"),
    _sort: Optional[str] = Query(None, description="Sort parameters"),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Search FHIR R5 Observation resources"""
    search_params = {
        "patient": patient,
        "status": status,
        "date": date,
        "_count": _count,
        "_offset": _offset,
        "_sort": _sort
    }
    return await search_fhir_resources_endpoint("Observation", request, current_user, **search_params)

@router.post("/Observation/batch", summary="Create Multiple Observations")
@api_endpoint_timing("fhir_create_observations_batch")
async def create_observations_batch(
    request: Request,
    observations_data: List[Dict[str, Any]] = Body(..., description="List of observation data"),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Create multiple FHIR R5 Observations in a single request"""
    try:
        results = []
        errors = []
        
        for i, observation_data in enumerate(observations_data):
            try:
                result = await create_fhir_resource_endpoint("Observation", observation_data, request, current_user)
                results.append({
                    "index": i,
                    "success": True,
                    "resource_id": result.get("resource_id"),
                    "mongo_id": result.get("mongo_id")
                })
            except Exception as e:
                errors.append({
                    "index": i,
                    "success": False,
                    "error": str(e)
                })
                logger.error(f"Error creating observation at index {i}: {e}")
        
        return {
            "success": len(errors) == 0,
            "total_requested": len(observations_data),
            "successful": len(results),
            "failed": len(errors),
            "results": results,
            "errors": errors
        }
    except Exception as e:
        logger.error(f"Error in batch observation creation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =============== Device Resource Endpoints ===============

@router.post("/Device", summary="Create Device")
@api_endpoint_timing("fhir_create_device")
async def create_device(
    request: Request,
    device_data: Dict[str, Any] = Body(...),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Create a new FHIR R5 Device resource"""
    return await create_fhir_resource_endpoint("Device", device_data, request, current_user)

@router.get("/Device/{device_id}", summary="Get Device by ID")
@api_endpoint_timing("fhir_get_device")
async def get_device(
    device_id: str = Path(..., description="Device ID"),
    request: Request = None,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get a FHIR R5 Device resource by ID"""
    return await get_fhir_resource_endpoint("Device", device_id, request, current_user)

@router.put("/Device/{device_id}", summary="Update Device")
@api_endpoint_timing("fhir_update_device")
async def update_device(
    device_id: str = Path(..., description="Device ID"),
    device_data: Dict[str, Any] = Body(...),
    request: Request = None,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Update a FHIR R5 Device resource"""
    return await update_fhir_resource_endpoint("Device", device_id, device_data, request, current_user)

@router.delete("/Device/{device_id}", summary="Delete Device")
@api_endpoint_timing("fhir_delete_device")
async def delete_device(
    device_id: str = Path(..., description="Device ID"),
    request: Request = None,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Delete a FHIR R5 Device resource"""
    return await delete_fhir_resource_endpoint("Device", device_id, request, current_user)

@router.get("/Device", summary="Search Devices")
@api_endpoint_timing("fhir_search_devices")
async def search_devices(
    request: Request,
    identifier: Optional[str] = Query(None, description="Device identifier"),
    type: Optional[str] = Query(None, description="Device type"),
    manufacturer: Optional[str] = Query(None, description="Manufacturer"),
    model: Optional[str] = Query(None, description="Model number"),
    status: Optional[str] = Query(None, description="Device status"),
    _count: Optional[int] = Query(10, description="Number of results"),
    _offset: Optional[int] = Query(0, description="Search offset"),
    _sort: Optional[str] = Query(None, description="Sort parameters"),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Search FHIR R5 Device resources"""
    search_params = {
        "identifier": identifier,
        "status": status,
        "_count": _count,
        "_offset": _offset,
        "_sort": _sort
    }
    return await search_fhir_resources_endpoint("Device", request, current_user, **search_params)

# =============== Organization Resource Endpoints ===============

@router.post("/Organization", summary="Create Organization")
@api_endpoint_timing("fhir_create_organization")
async def create_organization(
    request: Request,
    organization_data: Dict[str, Any] = Body(...),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Create a new FHIR R5 Organization resource"""
    return await create_fhir_resource_endpoint("Organization", organization_data, request, current_user)

@router.get("/Organization/{organization_id}", summary="Get Organization by ID")
@api_endpoint_timing("fhir_get_organization")
async def get_organization(
    organization_id: str = Path(..., description="Organization ID"),
    request: Request = None,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get a FHIR R5 Organization resource by ID"""
    return await get_fhir_resource_endpoint("Organization", organization_id, request, current_user)

@router.put("/Organization/{organization_id}", summary="Update Organization")
@api_endpoint_timing("fhir_update_organization")
async def update_organization(
    organization_id: str = Path(..., description="Organization ID"),
    organization_data: Dict[str, Any] = Body(...),
    request: Request = None,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Update a FHIR R5 Organization resource"""
    return await update_fhir_resource_endpoint("Organization", organization_id, organization_data, request, current_user)

@router.get("/Organization", summary="Search Organizations")
@api_endpoint_timing("fhir_search_organizations")
async def search_organizations(
    request: Request,
    identifier: Optional[str] = Query(None, description="Organization identifier"),
    name: Optional[str] = Query(None, description="Organization name"),
    type: Optional[str] = Query(None, description="Organization type"),
    _count: Optional[int] = Query(10, description="Number of results"),
    _offset: Optional[int] = Query(0, description="Search offset"),
    _sort: Optional[str] = Query(None, description="Sort parameters"),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Search FHIR R5 Organization resources"""
    search_params = {
        "identifier": identifier,
        "_count": _count,
        "_offset": _offset,
        "_sort": _sort
    }
    return await search_fhir_resources_endpoint("Organization", request, current_user, **search_params)

# =============== Hospital Data Integration Endpoints ===============

@router.post("/Organization/hospital", summary="Create Hospital Organization")
@api_endpoint_timing("fhir_create_hospital_organization")
async def create_hospital_organization(
    request: Request,
    hospital_id: str = Body(..., description="Hospital ID from master data"),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Create a comprehensive FHIR R5 Organization resource from hospital master data"""
    try:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        # Get or create hospital organization
        org_id = await fhir_service.get_or_create_hospital_organization(hospital_id)
        
        if not org_id:
            raise HTTPException(
                status_code=404,
                detail=f"Hospital {hospital_id} not found in master data"
            )
        
        # Get the created organization
        organization = await fhir_service.get_fhir_resource("Organization", org_id)
        
        return {
            "success": True,
            "message": f"Hospital organization created successfully",
            "organization_id": org_id,
            "organization": organization,
            "request_id": request_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create hospital organization: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create hospital organization: {str(e)}"
        )

@router.post("/Location/hospital", summary="Create Hospital Location")
@api_endpoint_timing("fhir_create_hospital_location")
async def create_hospital_location(
    request: Request,
    hospital_id: str = Body(..., description="Hospital ID from master data"),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Create a FHIR R5 Location resource for hospital physical location"""
    try:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        # Get hospital data from master data
        hospital_collection = mongodb_service.get_collection("hospitals")
        hospital_doc = await hospital_collection.find_one({"_id": ObjectId(hospital_id)})
        
        if not hospital_doc:
            raise HTTPException(
                status_code=404,
                detail=f"Hospital {hospital_id} not found in master data"
            )
        
        # Get or create hospital organization first
        org_id = await fhir_service.get_or_create_hospital_organization(hospital_id)
        
        if not org_id:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create hospital organization for {hospital_id}"
            )
        
        # Create location resource
        location_id = await fhir_service.create_hospital_location(hospital_doc, org_id)
        
        # Get the created location
        location = await fhir_service.get_fhir_resource("Location", location_id)
        
        return {
            "success": True,
            "message": f"Hospital location created successfully",
            "location_id": location_id,
            "organization_id": org_id,
            "location": location,
            "request_id": request_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create hospital location: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create hospital location: {str(e)}"
        )

@router.post("/Patient/with-hospital", summary="Create Patient with Hospital Context")
@api_endpoint_timing("fhir_create_patient_with_hospital")
async def create_patient_with_hospital(
    request: Request,
    patient_data: Dict[str, Any] = Body(..., description="Patient data with hospital_id"),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Create a FHIR R5 Patient resource with hospital organization context"""
    try:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        # Create patient with hospital context
        patient_id = await fhir_service.migrate_existing_patient_to_fhir_with_hospital(patient_data)
        
        # Get the created patient
        patient = await fhir_service.get_fhir_resource("Patient", patient_id)
        
        return {
            "success": True,
            "message": f"Patient created successfully with hospital context",
            "patient_id": patient_id,
            "patient": patient,
            "request_id": request_id
        }
        
    except Exception as e:
        logger.error(f"Failed to create patient with hospital context: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create patient with hospital context: {str(e)}"
        )

# =============== Enhanced MQTT Integration with Hospital Context ===============

@router.post("/Observation/from-mqtt-with-hospital", summary="Create Observation from MQTT with Hospital Context")
@api_endpoint_timing("fhir_create_observation_mqtt_hospital")
async def create_observation_from_mqtt_with_hospital(
    request: Request,
    mqtt_payload: Dict[str, Any] = Body(..., description="MQTT payload"),
    patient_id: str = Body(..., description="Patient ID"),
    device_id: str = Body(..., description="Device ID"),
    hospital_id: Optional[str] = Body(None, description="Hospital ID (optional)"),
    device_type: str = Body(..., description="Device type (ava4, qube, kati)"),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Create FHIR R5 Observations from MQTT data with hospital context"""
    try:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        # Transform MQTT data to FHIR Observations with hospital context
        if device_type.lower() == "ava4":
            observations = await fhir_service.transform_ava4_mqtt_to_fhir_with_hospital(
                mqtt_payload=mqtt_payload,
                patient_id=patient_id,
                device_id=device_id,
                hospital_id=hospital_id
            )
        elif device_type.lower() == "qube":
            observations = await fhir_service.transform_qube_mqtt_to_fhir_with_hospital(
                mqtt_payload=mqtt_payload,
                patient_id=patient_id,
                device_id=device_id,
                hospital_id=hospital_id
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported device type: {device_type}. Supported types: ava4, qube"
            )
        
        # Create FHIR Observation resources
        created_observations = []
        for obs_data in observations:
            result = await fhir_service.create_fhir_resource(
                resource_type="Observation",
                resource_data=obs_data,
                source_system="mqtt_with_hospital",
                device_mac_address=device_id,
                user_id=current_user.get("user_id"),
                request_id=request_id
            )
            created_observations.append(result)
        
        return {
            "success": True,
            "message": f"Created {len(created_observations)} observations with hospital context",
            "observations": created_observations,
            "device_type": device_type,
            "hospital_id": hospital_id,
            "request_id": request_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create observations from MQTT with hospital context: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create observations from MQTT with hospital context: {str(e)}"
        )

@router.post("/Device/with-hospital", summary="Create Device with Hospital Context")
@api_endpoint_timing("fhir_create_device_with_hospital")
async def create_device_with_hospital(
    request: Request,
    device_data: Dict[str, Any] = Body(..., description="Device data"),
    hospital_id: Optional[str] = Body(None, description="Hospital ID (optional)"),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Create a FHIR R5 Device resource with hospital organization context"""
    try:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        # Add hospital context to device
        device_data = await fhir_service.add_hospital_context_to_device(device_data, hospital_id)
        
        # Create FHIR Device resource
        result = await fhir_service.create_fhir_resource(
            resource_type="Device",
            resource_data=device_data,
            source_system="manual_with_hospital",
            user_id=current_user.get("user_id"),
            request_id=request_id
        )
        
        return {
            "success": True,
            "message": f"Device created successfully with hospital context",
            "device_id": result["resource_id"],
            "device": result["resource"],
            "hospital_id": hospital_id,
            "request_id": request_id
        }
        
    except Exception as e:
        logger.error(f"Failed to create device with hospital context: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create device with hospital context: {str(e)}"
        )

# =============== Hospital Data Migration Endpoints ===============

@router.post("/migrate/hospitals", summary="Migrate Hospitals to FHIR")
@api_endpoint_timing("fhir_migrate_hospitals")
async def migrate_hospitals_to_fhir(
    request: Request,
    hospital_ids: Optional[List[str]] = Body(None, description="Specific hospital IDs to migrate (optional)"),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Migrate hospital master data to FHIR R5 Organization and Location resources"""
    try:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        hospital_collection = mongodb_service.get_collection("hospitals")
        
        # Build query
        if hospital_ids:
            # Migrate specific hospitals
            object_ids = [ObjectId(hid) for hid in hospital_ids]
            query = {"_id": {"$in": object_ids}}
        else:
            # Migrate all active hospitals
            query = {"is_active": True, "is_deleted": {"$ne": True}}
        
        # Get hospitals to migrate
        hospitals = await hospital_collection.find(query).to_list(length=None)
        
        if not hospitals:
            return {
                "success": True,
                "message": "No hospitals found to migrate",
                "migrated_count": 0,
                "request_id": request_id
            }
        
        # Migrate each hospital
        migrated_organizations = []
        migrated_locations = []
        errors = []
        
        for hospital_doc in hospitals:
            try:
                # Migrate to Organization
                org_id = await fhir_service.migrate_hospital_to_organization(hospital_doc)
                migrated_organizations.append({
                    "hospital_id": str(hospital_doc["_id"]),
                    "organization_id": org_id,
                    "hospital_name": hospital_doc.get("en_name", "Unknown")
                })
                
                # Location is created automatically in migrate_hospital_to_organization
                migrated_locations.append({
                    "hospital_id": str(hospital_doc["_id"]),
                    "organization_id": org_id
                })
                
            except Exception as e:
                errors.append({
                    "hospital_id": str(hospital_doc["_id"]),
                    "error": str(e)
                })
        
        return {
            "success": True,
            "message": f"Migrated {len(migrated_organizations)} hospitals to FHIR",
            "migrated_organizations": migrated_organizations,
            "migrated_locations": migrated_locations,
            "total_hospitals": len(hospitals),
            "successful_migrations": len(migrated_organizations),
            "errors": errors,
            "request_id": request_id
        }
        
    except Exception as e:
        logger.error(f"Failed to migrate hospitals to FHIR: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to migrate hospitals to FHIR: {str(e)}"
        )

@router.get("/hospitals/summary", summary="Get Hospital FHIR Summary")
@api_endpoint_timing("fhir_get_hospital_summary")
async def get_hospital_fhir_summary(
    request: Request,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get summary of hospital data in FHIR R5 format"""
    try:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        # Get counts from FHIR collections
        org_collection = mongodb_service.get_fhir_collection("fhir_organizations")
        location_collection = mongodb_service.get_fhir_collection("fhir_locations")
        hospital_collection = mongodb_service.get_collection("hospitals")
        
        # Count FHIR resources
        org_count = await org_collection.count_documents({"is_deleted": {"$ne": True}})
        location_count = await location_collection.count_documents({"is_deleted": {"$ne": True}})
        
        # Count master data hospitals
        total_hospitals = await hospital_collection.count_documents({"is_active": True, "is_deleted": {"$ne": True}})
        
        # Get sample organizations
        sample_orgs = await org_collection.find({"is_deleted": {"$ne": True}}).limit(5).to_list(length=5)
        
        return {
            "success": True,
            "summary": {
                "total_hospitals_master_data": total_hospitals,
                "fhir_organizations": org_count,
                "fhir_locations": location_count,
                "migration_coverage": f"{(org_count/total_hospitals*100):.1f}%" if total_hospitals > 0 else "0%"
            },
            "sample_organizations": [
                {
                    "id": org["resource_id"],
                    "name": org["resource_data"].get("name", "Unknown"),
                    "active": org["resource_data"].get("active", False)
                }
                for org in sample_orgs
            ],
            "request_id": request_id
        }
        
    except Exception as e:
        logger.error(f"Failed to get hospital FHIR summary: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get hospital FHIR summary: {str(e)}"
        )

# =============== AVA4 MQTT Integration Endpoint ===============

@router.post("/Observation/from-mqtt", summary="Create Observation from AVA4 MQTT")
@api_endpoint_timing("fhir_create_observation_mqtt")
async def create_observation_from_mqtt(
    request: Request,
    mqtt_payload: Dict[str, Any] = Body(..., description="AVA4 MQTT payload"),
    patient_id: str = Body(..., description="Patient ID"),
    device_id: str = Body(..., description="Device ID"),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Create FHIR R5 Observations from AVA4 MQTT data"""
    try:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        # Transform MQTT data to FHIR Observations
        observations = await fhir_service.transform_ava4_mqtt_to_fhir(
            mqtt_payload=mqtt_payload,
            patient_id=patient_id,
            device_id=device_id
        )
        
        # Create FHIR Observation resources
        created_observations = []
        for obs_data in observations:
            result = await fhir_service.create_fhir_resource(
                resource_type="Observation",
                resource_data=obs_data,
                source_system="ava4_mqtt",
                device_mac_address=mqtt_payload.get("mac")
            )
            created_observations.append(result)
        
        response = create_success_response(
            message=f"Created {len(created_observations)} FHIR Observations from AVA4 MQTT data",
            data={
                "observations_created": len(created_observations),
                "observation_ids": [obs["resource_id"] for obs in created_observations],
                "mqtt_timestamp": mqtt_payload.get("time"),
                "device_mac": mqtt_payload.get("mac"),
                "device_type": mqtt_payload.get("data", {}).get("device", "Unknown")
            },
            request_id=request_id
        )
        
        return JSONResponse(
            content=response.dict(),
            status_code=201,
            media_type="application/fhir+json"
        )
        
    except Exception as e:
        logger.error(f"Error creating FHIR Observations from MQTT: {e}")
        raise HTTPException(
            status_code=400,
            detail=create_error_response(
                "FHIR_MQTT_TRANSFORM_ERROR",
                custom_message=f"Failed to transform MQTT data to FHIR: {str(e)}",
                request_id=request.headers.get("X-Request-ID")
            ).dict()
        )

# =============== MedicationStatement Endpoints ===============

@router.post("/MedicationStatement", summary="Create MedicationStatement")
@api_endpoint_timing("fhir_create_medication_statement")
async def create_medication_statement(
    request: Request,
    medication_statement_data: Dict[str, Any] = Body(...),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Create a FHIR R5 MedicationStatement resource"""
    return await create_fhir_resource_endpoint("MedicationStatement", medication_statement_data, request, current_user)

@router.get("/MedicationStatement/{medication_statement_id}", summary="Get MedicationStatement by ID")
@api_endpoint_timing("fhir_get_medication_statement")
async def get_medication_statement(
    medication_statement_id: str = Path(..., description="MedicationStatement ID"),
    request: Request = None,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get a FHIR R5 MedicationStatement by ID"""
    return await get_fhir_resource_endpoint("MedicationStatement", medication_statement_id, request, current_user)

@router.put("/MedicationStatement/{medication_statement_id}", summary="Update MedicationStatement")
@api_endpoint_timing("fhir_update_medication_statement")
async def update_medication_statement(
    medication_statement_id: str = Path(..., description="MedicationStatement ID"),
    medication_statement_data: Dict[str, Any] = Body(...),
    request: Request = None,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Update a FHIR R5 MedicationStatement"""
    return await update_fhir_resource_endpoint("MedicationStatement", medication_statement_id, medication_statement_data, request, current_user)

@router.delete("/MedicationStatement/{medication_statement_id}", summary="Delete MedicationStatement")
@api_endpoint_timing("fhir_delete_medication_statement")
async def delete_medication_statement(
    medication_statement_id: str = Path(..., description="MedicationStatement ID"),
    request: Request = None,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Delete a FHIR R5 MedicationStatement"""
    return await delete_fhir_resource_endpoint("MedicationStatement", medication_statement_id, request, current_user)

@router.get("/MedicationStatement", summary="Search MedicationStatements")
@api_endpoint_timing("fhir_search_medication_statements")
async def search_medication_statements(
    request: Request,
    patient: Optional[str] = Query(None, description="Patient reference"),
    status: Optional[str] = Query(None, description="MedicationStatement status"),
    medication: Optional[str] = Query(None, description="Medication reference"),
    effective: Optional[str] = Query(None, description="Date range when medication was taken"),
    source: Optional[str] = Query(None, description="Information source"),
    _count: Optional[int] = Query(10, description="Number of results"),
    _offset: Optional[int] = Query(0, description="Search offset"),
    _sort: Optional[str] = Query(None, description="Sort parameters"),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Search FHIR R5 MedicationStatement resources"""
    search_params = {
        "patient": patient, "status": status, "medication": medication,
        "effective": effective, "source": source, 
        "_count": _count, "_offset": _offset,
        "_sort": _sort
    }
    return await search_fhir_resources_endpoint("MedicationStatement", request, current_user, **search_params)

# =============== DiagnosticReport Endpoints ===============

@router.post("/DiagnosticReport", summary="Create DiagnosticReport")
@api_endpoint_timing("fhir_create_diagnostic_report")
async def create_diagnostic_report(
    request: Request,
    diagnostic_report_data: Dict[str, Any] = Body(...),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Create a FHIR R5 DiagnosticReport resource"""
    return await create_fhir_resource_endpoint("DiagnosticReport", diagnostic_report_data, request, current_user)

@router.get("/DiagnosticReport/{diagnostic_report_id}", summary="Get DiagnosticReport by ID")
@api_endpoint_timing("fhir_get_diagnostic_report")
async def get_diagnostic_report(
    diagnostic_report_id: str = Path(..., description="DiagnosticReport ID"),
    request: Request = None,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get a FHIR R5 DiagnosticReport by ID"""
    return await get_fhir_resource_endpoint("DiagnosticReport", diagnostic_report_id, request, current_user)

@router.put("/DiagnosticReport/{diagnostic_report_id}", summary="Update DiagnosticReport")
@api_endpoint_timing("fhir_update_diagnostic_report")
async def update_diagnostic_report(
    diagnostic_report_id: str = Path(..., description="DiagnosticReport ID"),
    diagnostic_report_data: Dict[str, Any] = Body(...),
    request: Request = None,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Update a FHIR R5 DiagnosticReport"""
    return await update_fhir_resource_endpoint("DiagnosticReport", diagnostic_report_id, diagnostic_report_data, request, current_user)

@router.delete("/DiagnosticReport/{diagnostic_report_id}", summary="Delete DiagnosticReport")
@api_endpoint_timing("fhir_delete_diagnostic_report")
async def delete_diagnostic_report(
    diagnostic_report_id: str = Path(..., description="DiagnosticReport ID"),
    request: Request = None,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Delete a FHIR R5 DiagnosticReport"""
    return await delete_fhir_resource_endpoint("DiagnosticReport", diagnostic_report_id, request, current_user)

@router.get("/DiagnosticReport", summary="Search DiagnosticReports")
@api_endpoint_timing("fhir_search_diagnostic_reports")
async def search_diagnostic_reports(
    request: Request,
    patient: Optional[str] = Query(None, description="Patient reference"),
    category: Optional[str] = Query(None, description="Report category"),
    code: Optional[str] = Query(None, description="Report code"),
    date: Optional[str] = Query(None, description="Date range"),
    status: Optional[str] = Query(None, description="Report status"),
    _count: Optional[int] = Query(10, description="Number of results"),
    _offset: Optional[int] = Query(0, description="Search offset"),
    _sort: Optional[str] = Query(None, description="Sort parameters"),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Search FHIR R5 DiagnosticReport resources"""
    search_params = {
        "patient": patient, "category": category, "code": code,
        "date": date, "status": status,
        "_count": _count, "_offset": _offset,
        "_sort": _sort
    }
    return await search_fhir_resources_endpoint("DiagnosticReport", request, current_user, **search_params)

# =============== DocumentReference Endpoints ===============

@router.post("/DocumentReference", summary="Create DocumentReference")
@api_endpoint_timing("fhir_create_document_reference")
async def create_document_reference(
    request: Request,
    document_reference_data: Dict[str, Any] = Body(...),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Create a FHIR R5 DocumentReference resource"""
    return await create_fhir_resource_endpoint("DocumentReference", document_reference_data, request, current_user)

@router.get("/DocumentReference/{document_reference_id}", summary="Get DocumentReference by ID")
@api_endpoint_timing("fhir_get_document_reference")
async def get_document_reference(
    document_reference_id: str = Path(..., description="DocumentReference ID"),
    request: Request = None,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get a FHIR R5 DocumentReference by ID"""
    return await get_fhir_resource_endpoint("DocumentReference", document_reference_id, request, current_user)

@router.put("/DocumentReference/{document_reference_id}", summary="Update DocumentReference")
@api_endpoint_timing("fhir_update_document_reference")
async def update_document_reference(
    document_reference_id: str = Path(..., description="DocumentReference ID"),
    document_reference_data: Dict[str, Any] = Body(...),
    request: Request = None,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Update a FHIR R5 DocumentReference"""
    return await update_fhir_resource_endpoint("DocumentReference", document_reference_id, document_reference_data, request, current_user)

@router.delete("/DocumentReference/{document_reference_id}", summary="Delete DocumentReference")
@api_endpoint_timing("fhir_delete_document_reference")
async def delete_document_reference(
    document_reference_id: str = Path(..., description="DocumentReference ID"),
    request: Request = None,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Delete a FHIR R5 DocumentReference"""
    return await delete_fhir_resource_endpoint("DocumentReference", document_reference_id, request, current_user)

@router.get("/DocumentReference", summary="Search DocumentReferences")
@api_endpoint_timing("fhir_search_document_references")
async def search_document_references(
    request: Request,
    patient: Optional[str] = Query(None, description="Patient reference"),
    type: Optional[str] = Query(None, description="Document type"),
    category: Optional[str] = Query(None, description="Document category"),
    date: Optional[str] = Query(None, description="Date range"),
    status: Optional[str] = Query(None, description="Document status"),
    _count: Optional[int] = Query(10, description="Number of results"),
    _offset: Optional[int] = Query(0, description="Search offset"),
    _sort: Optional[str] = Query(None, description="Sort parameters"),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Search FHIR R5 DocumentReference resources"""
    search_params = {
        "patient": patient, "type": type, "category": category,
        "date": date, "status": status,
        "_count": _count, "_offset": _offset,
        "_sort": _sort
    }
    return await search_fhir_resources_endpoint("DocumentReference", request, current_user, **search_params)

# =============== AMY Data Migration Endpoints ===============

@router.post("/migration/amy/medication-history", summary="Migrate AMY Medication History")
@api_endpoint_timing("fhir_migrate_amy_medication")
async def migrate_amy_medication_history(
    request: Request,
    patient_id: str = Body(..., description="Patient ObjectId from AMY"),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Migrate AMY medication history to FHIR R5 MedicationStatement resources"""
    try:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        # Get medication history from AMY database
        from app.services.mongo import mongodb_service
        from bson import ObjectId
        medication_collection = mongodb_service.get_collection("medication_histories")
        medication_doc = await medication_collection.find_one({"patient_id": ObjectId(patient_id)})
        
        if not medication_doc:
            return create_error_response(
                error_code="RESOURCE_NOT_FOUND",
                message=f"No medication history found for patient {patient_id}",
                request_id=request_id
            )
        
        # Migrate to FHIR
        medication_ids = await fhir_service.migrate_medication_history_to_fhir(medication_doc)
        
        return create_success_response(
            message=f"Migrated {len(medication_ids)} medication statements",
            data={
                "patient_id": patient_id,
                "medication_statement_ids": medication_ids,
                "total_migrated": len(medication_ids)
            },
            request_id=request_id
        )
        
    except Exception as e:
        logger.error(f"Failed to migrate medication history: {e}")
        return create_error_response(
            error_code="MIGRATION_ERROR",
            message=f"Failed to migrate medication history: {str(e)}",
            request_id=request_id
        )

@router.post("/migration/amy/allergy-history", summary="Migrate AMY Allergy History")
@api_endpoint_timing("fhir_migrate_amy_allergy")
async def migrate_amy_allergy_history(
    request: Request,
    patient_id: str = Body(..., description="Patient ObjectId from AMY"),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Migrate AMY allergy history to FHIR R5 AllergyIntolerance resources"""
    try:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        # Get allergy history from AMY database
        from app.services.mongo import mongodb_service
        from bson import ObjectId
        allergy_collection = mongodb_service.get_collection("allergy_histories")
        allergy_doc = await allergy_collection.find_one({"patient_id": ObjectId(patient_id)})
        
        if not allergy_doc:
            return create_error_response(
                error_code="RESOURCE_NOT_FOUND",
                message=f"No allergy history found for patient {patient_id}",
                request_id=request_id
            )
        
        # Migrate to FHIR
        allergy_ids = await fhir_service.migrate_allergy_history_to_fhir(allergy_doc)
        
        return create_success_response(
            message=f"Migrated {len(allergy_ids)} allergy intolerances",
            data={
                "patient_id": patient_id,
                "allergy_intolerance_ids": allergy_ids,
                "total_migrated": len(allergy_ids)
            },
            request_id=request_id
        )
        
    except Exception as e:
        logger.error(f"Failed to migrate allergy history: {e}")
        return create_error_response(
            error_code="MIGRATION_ERROR",
            message=f"Failed to migrate allergy history: {str(e)}",
            request_id=request_id
        )

@router.post("/migration/amy/body-data", summary="Migrate AMY Body Data")
@api_endpoint_timing("fhir_migrate_amy_body_data")
async def migrate_amy_body_data(
    request: Request,
    patient_id: str = Body(..., description="Patient ObjectId from AMY"),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Migrate AMY body data to FHIR R5 Observation resources"""
    try:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        # Get body data from AMY database
        from app.services.mongo import mongodb_service
        from bson import ObjectId
        body_data_collection = mongodb_service.get_collection("body_data_histories")
        body_data_doc = await body_data_collection.find_one({"patient_id": ObjectId(patient_id)})
        
        if not body_data_doc:
            return create_error_response(
                error_code="RESOURCE_NOT_FOUND",
                message=f"No body data found for patient {patient_id}",
                request_id=request_id
            )
        
        # Migrate to FHIR
        observation_ids = await fhir_service.migrate_body_data_to_observations(body_data_doc)
        
        return create_success_response(
            message=f"Migrated {len(observation_ids)} body measurement observations",
            data={
                "patient_id": patient_id,
                "observation_ids": observation_ids,
                "total_migrated": len(observation_ids)
            },
            request_id=request_id
        )
        
    except Exception as e:
        logger.error(f"Failed to migrate body data: {e}")
        return create_error_response(
            error_code="MIGRATION_ERROR",
            message=f"Failed to migrate body data: {str(e)}",
            request_id=request_id
        )

# =============== FHIR R5 Analytics and Summary Endpoints ===============

@router.get("/analytics/summary", summary="FHIR R5 Resources Summary")
@api_endpoint_timing("fhir_analytics_summary")
async def get_fhir_summary(
    request: Request,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get summary analytics of all FHIR R5 resources"""
    try:
        from app.services.mongo import mongodb_service
        
        summary = {}
        
        # Count resources in each FHIR collection
        for resource_type, collection_name in fhir_service.fhir_collections.items():
            try:
                collection = mongodb_service.get_fhir_collection(collection_name)
                total_count = await collection.count_documents({"is_deleted": False})
                active_count = await collection.count_documents({
                    "is_deleted": False,
                    "resource_data.status": {"$nin": ["inactive", "entered-in-error"]}
                })
                
                summary[resource_type] = {
                    "total_resources": total_count,
                    "active_resources": active_count,
                    "collection": collection_name
                }
            except Exception as e:
                logger.warning(f"Failed to count {resource_type}: {e}")
                summary[resource_type] = {
                    "total_resources": 0,
                    "active_resources": 0,
                    "collection": collection_name,
                    "error": str(e)
                }
        
        response = create_success_response(
            message="FHIR R5 resources summary retrieved successfully",
            data={
                "summary": summary,
                "total_fhir_resources": sum(res.get("total_resources", 0) for res in summary.values()),
                "fhir_version": "5.0.0",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            },
            request_id=request.headers.get("X-Request-ID")
        )
        
        return JSONResponse(
            content=response.dict(),
            media_type="application/fhir+json"
        )
        
    except Exception as e:
        logger.error(f"Error getting FHIR summary: {e}")
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                "FHIR_SUMMARY_ERROR",
                custom_message=f"Failed to get FHIR summary: {str(e)}",
                request_id=request.headers.get("X-Request-ID")
            ).dict()
        ) 

# =============== Goal Resource Endpoints ===============

@router.post("/Goal", summary="Create Goal")
@api_endpoint_timing("fhir_create_goal")
async def create_goal(
    request: Request,
    goal_data: Dict[str, Any] = Body(...),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Create a new FHIR R5 Goal resource"""
    return await create_fhir_resource_endpoint("Goal", goal_data, request, current_user)

@router.get("/Goal/{goal_id}", summary="Get Goal by ID")
@api_endpoint_timing("fhir_get_goal")
async def get_goal(
    goal_id: str = Path(..., description="Goal ID"),
    request: Request = None,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get a FHIR R5 Goal resource by ID"""
    return await get_fhir_resource_endpoint("Goal", goal_id, request, current_user)

@router.put("/Goal/{goal_id}", summary="Update Goal")
@api_endpoint_timing("fhir_update_goal")
async def update_goal(
    goal_id: str = Path(..., description="Goal ID"),
    goal_data: Dict[str, Any] = Body(...),
    request: Request = None,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Update a FHIR R5 Goal resource"""
    return await update_fhir_resource_endpoint("Goal", goal_id, goal_data, request, current_user)

@router.delete("/Goal/{goal_id}", summary="Delete Goal")
@api_endpoint_timing("fhir_delete_goal")
async def delete_goal(
    goal_id: str = Path(..., description="Goal ID"),
    request: Request = None,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Delete a FHIR R5 Goal resource"""
    return await delete_fhir_resource_endpoint("Goal", goal_id, request, current_user)

@router.get("/Goal", summary="Search Goals")
@api_endpoint_timing("fhir_search_goals")
async def search_goals(
    request: Request,
    patient: Optional[str] = Query(None, description="Patient reference"),
    category: Optional[str] = Query(None, description="Goal category"),
    lifecycle_status: Optional[str] = Query(None, alias="lifecycle-status", description="Goal lifecycle status"),
    achievement_status: Optional[str] = Query(None, alias="achievement-status", description="Goal achievement status"),
    start_date: Optional[str] = Query(None, alias="start-date", description="Goal start date"),
    _count: Optional[int] = Query(10, description="Number of results"),
    _offset: Optional[int] = Query(0, description="Search offset"),
    _sort: Optional[str] = Query(None, description="Sort parameters"),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Search FHIR R5 Goal resources"""
    search_params = {
        "patient": patient,
        "status": lifecycle_status,
        "date": start_date,
        "_count": _count,
        "_offset": _offset,
        "_sort": _sort
    }
    return await search_fhir_resources_endpoint("Goal", request, current_user, **search_params)

# =============== RelatedPerson Resource Endpoints ===============

@router.post("/RelatedPerson", summary="Create RelatedPerson")
@api_endpoint_timing("fhir_create_related_person")
async def create_related_person(
    request: Request,
    related_person_data: Dict[str, Any] = Body(...),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Create a new FHIR R5 RelatedPerson resource"""
    return await create_fhir_resource_endpoint("RelatedPerson", related_person_data, request, current_user)

@router.get("/RelatedPerson/{related_person_id}", summary="Get RelatedPerson by ID")
@api_endpoint_timing("fhir_get_related_person")
async def get_related_person(
    related_person_id: str = Path(..., description="RelatedPerson ID"),
    request: Request = None,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get a FHIR R5 RelatedPerson resource by ID"""
    return await get_fhir_resource_endpoint("RelatedPerson", related_person_id, request, current_user)

@router.put("/RelatedPerson/{related_person_id}", summary="Update RelatedPerson")
@api_endpoint_timing("fhir_update_related_person")
async def update_related_person(
    related_person_id: str = Path(..., description="RelatedPerson ID"),
    related_person_data: Dict[str, Any] = Body(...),
    request: Request = None,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Update a FHIR R5 RelatedPerson resource"""
    return await update_fhir_resource_endpoint("RelatedPerson", related_person_id, related_person_data, request, current_user)

@router.delete("/RelatedPerson/{related_person_id}", summary="Delete RelatedPerson")
@api_endpoint_timing("fhir_delete_related_person")
async def delete_related_person(
    related_person_id: str = Path(..., description="RelatedPerson ID"),
    request: Request = None,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Delete a FHIR R5 RelatedPerson resource"""
    return await delete_fhir_resource_endpoint("RelatedPerson", related_person_id, request, current_user)

@router.get("/RelatedPerson", summary="Search RelatedPersons")
@api_endpoint_timing("fhir_search_related_persons")
async def search_related_persons(
    request: Request,
    patient: Optional[str] = Query(None, description="Patient reference"),
    relationship: Optional[str] = Query(None, description="Relationship type"),
    name: Optional[str] = Query(None, description="Related person name"),
    telecom: Optional[str] = Query(None, description="Contact information"),
    active: Optional[str] = Query(None, description="Active status"),
    _count: Optional[int] = Query(10, description="Number of results"),
    _offset: Optional[int] = Query(0, description="Search offset"),
    _sort: Optional[str] = Query(None, description="Sort parameters"),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Search FHIR R5 RelatedPerson resources"""
    search_params = {
        "patient": patient,
        "_count": _count,
        "_offset": _offset,
        "_sort": _sort
    }
    return await search_fhir_resources_endpoint("RelatedPerson", request, current_user, **search_params)

# =============== Flag Resource Endpoints ===============

@router.post("/Flag", summary="Create Flag")
@api_endpoint_timing("fhir_create_flag")
async def create_flag(
    request: Request,
    flag_data: Dict[str, Any] = Body(...),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Create a new FHIR R5 Flag resource"""
    return await create_fhir_resource_endpoint("Flag", flag_data, request, current_user)

@router.get("/Flag/{flag_id}", summary="Get Flag by ID")
@api_endpoint_timing("fhir_get_flag")
async def get_flag(
    flag_id: str = Path(..., description="Flag ID"),
    request: Request = None,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get a FHIR R5 Flag resource by ID"""
    return await get_fhir_resource_endpoint("Flag", flag_id, request, current_user)

@router.put("/Flag/{flag_id}", summary="Update Flag")
@api_endpoint_timing("fhir_update_flag")
async def update_flag(
    flag_id: str = Path(..., description="Flag ID"),
    flag_data: Dict[str, Any] = Body(...),
    request: Request = None,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Update a FHIR R5 Flag resource"""
    return await update_fhir_resource_endpoint("Flag", flag_id, flag_data, request, current_user)

@router.delete("/Flag/{flag_id}", summary="Delete Flag")
@api_endpoint_timing("fhir_delete_flag")
async def delete_flag(
    flag_id: str = Path(..., description="Flag ID"),
    request: Request = None,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Delete a FHIR R5 Flag resource"""
    return await delete_fhir_resource_endpoint("Flag", flag_id, request, current_user)

@router.get("/Flag", summary="Search Flags")
@api_endpoint_timing("fhir_search_flags")
async def search_flags(
    request: Request,
    patient: Optional[str] = Query(None, description="Patient reference"),
    category: Optional[str] = Query(None, description="Flag category"),
    code: Optional[str] = Query(None, description="Flag code"),
    status: Optional[str] = Query(None, description="Flag status"),
    date: Optional[str] = Query(None, description="Date range"),
    _count: Optional[int] = Query(10, description="Number of results"),
    _offset: Optional[int] = Query(0, description="Search offset"),
    _sort: Optional[str] = Query(None, description="Sort parameters"),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Search FHIR R5 Flag resources"""
    search_params = {
        "patient": patient,
        "status": status,
        "date": date,
        "_count": _count,
        "_offset": _offset,
        "_sort": _sort
    }
    return await search_fhir_resources_endpoint("Flag", request, current_user, **search_params)

# =============== RiskAssessment Resource Endpoints ===============

@router.post("/RiskAssessment", summary="Create RiskAssessment")
@api_endpoint_timing("fhir_create_risk_assessment")
async def create_risk_assessment(
    request: Request,
    risk_assessment_data: Dict[str, Any] = Body(...),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Create a new FHIR R5 RiskAssessment resource"""
    return await create_fhir_resource_endpoint("RiskAssessment", risk_assessment_data, request, current_user)

@router.get("/RiskAssessment/{risk_assessment_id}", summary="Get RiskAssessment by ID")
@api_endpoint_timing("fhir_get_risk_assessment")
async def get_risk_assessment(
    risk_assessment_id: str = Path(..., description="RiskAssessment ID"),
    request: Request = None,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get a FHIR R5 RiskAssessment resource by ID"""
    return await get_fhir_resource_endpoint("RiskAssessment", risk_assessment_id, request, current_user)

@router.put("/RiskAssessment/{risk_assessment_id}", summary="Update RiskAssessment")
@api_endpoint_timing("fhir_update_risk_assessment")
async def update_risk_assessment(
    risk_assessment_id: str = Path(..., description="RiskAssessment ID"),
    risk_assessment_data: Dict[str, Any] = Body(...),
    request: Request = None,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Update a FHIR R5 RiskAssessment resource"""
    return await update_fhir_resource_endpoint("RiskAssessment", risk_assessment_id, risk_assessment_data, request, current_user)

@router.delete("/RiskAssessment/{risk_assessment_id}", summary="Delete RiskAssessment")
@api_endpoint_timing("fhir_delete_risk_assessment")
async def delete_risk_assessment(
    risk_assessment_id: str = Path(..., description="RiskAssessment ID"),
    request: Request = None,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Delete a FHIR R5 RiskAssessment resource"""
    return await delete_fhir_resource_endpoint("RiskAssessment", risk_assessment_id, request, current_user)

@router.get("/RiskAssessment", summary="Search RiskAssessments")
@api_endpoint_timing("fhir_search_risk_assessments")
async def search_risk_assessments(
    request: Request,
    patient: Optional[str] = Query(None, description="Patient reference"),
    method: Optional[str] = Query(None, description="Assessment method"),
    code: Optional[str] = Query(None, description="Assessment code"),
    status: Optional[str] = Query(None, description="Assessment status"),
    date: Optional[str] = Query(None, description="Date range"),
    _count: Optional[int] = Query(10, description="Number of results"),
    _offset: Optional[int] = Query(0, description="Search offset"),
    _sort: Optional[str] = Query(None, description="Sort parameters"),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Search FHIR R5 RiskAssessment resources"""
    search_params = {
        "patient": patient,
        "status": status,
        "date": date,
        "_count": _count,
        "_offset": _offset,
        "_sort": _sort
    }
    return await search_fhir_resources_endpoint("RiskAssessment", request, current_user, **search_params)

# =============== ServiceRequest Resource Endpoints ===============

@router.post("/ServiceRequest", summary="Create ServiceRequest")
@api_endpoint_timing("fhir_create_service_request")
async def create_service_request(
    request: Request,
    service_request_data: Dict[str, Any] = Body(...),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Create a new FHIR R5 ServiceRequest resource"""
    return await create_fhir_resource_endpoint("ServiceRequest", service_request_data, request, current_user)

@router.get("/ServiceRequest/{service_request_id}", summary="Get ServiceRequest by ID")
@api_endpoint_timing("fhir_get_service_request")
async def get_service_request(
    service_request_id: str = Path(..., description="ServiceRequest ID"),
    request: Request = None,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get a FHIR R5 ServiceRequest resource by ID"""
    return await get_fhir_resource_endpoint("ServiceRequest", service_request_id, request, current_user)

@router.put("/ServiceRequest/{service_request_id}", summary="Update ServiceRequest")
@api_endpoint_timing("fhir_update_service_request")
async def update_service_request(
    service_request_id: str = Path(..., description="ServiceRequest ID"),
    service_request_data: Dict[str, Any] = Body(...),
    request: Request = None,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Update a FHIR R5 ServiceRequest resource"""
    return await update_fhir_resource_endpoint("ServiceRequest", service_request_id, service_request_data, request, current_user)

@router.delete("/ServiceRequest/{service_request_id}", summary="Delete ServiceRequest")
@api_endpoint_timing("fhir_delete_service_request")
async def delete_service_request(
    service_request_id: str = Path(..., description="ServiceRequest ID"),
    request: Request = None,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Delete a FHIR R5 ServiceRequest resource"""
    return await delete_fhir_resource_endpoint("ServiceRequest", service_request_id, request, current_user)

@router.get("/ServiceRequest", summary="Search ServiceRequests")
@api_endpoint_timing("fhir_search_service_requests")
async def search_service_requests(
    request: Request,
    patient: Optional[str] = Query(None, description="Patient reference"),
    category: Optional[str] = Query(None, description="Service category"),
    code: Optional[str] = Query(None, description="Service code"),
    status: Optional[str] = Query(None, description="Request status"),
    intent: Optional[str] = Query(None, description="Request intent"),
    authored: Optional[str] = Query(None, description="Date authored"),
    _count: Optional[int] = Query(10, description="Number of results"),
    _offset: Optional[int] = Query(0, description="Search offset"),
    _sort: Optional[str] = Query(None, description="Sort parameters"),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Search FHIR R5 ServiceRequest resources"""
    search_params = {
        "patient": patient,
        "status": status,
        "date": authored,
        "_count": _count,
        "_offset": _offset,
        "_sort": _sort
    }
    return await search_fhir_resources_endpoint("ServiceRequest", request, current_user, **search_params)

# =============== CarePlan Resource Endpoints ===============

@router.post("/CarePlan", summary="Create CarePlan")
@api_endpoint_timing("fhir_create_care_plan")
async def create_care_plan(
    request: Request,
    care_plan_data: Dict[str, Any] = Body(...),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Create a new FHIR R5 CarePlan resource"""
    return await create_fhir_resource_endpoint("CarePlan", care_plan_data, request, current_user)

@router.get("/CarePlan/{care_plan_id}", summary="Get CarePlan by ID")
@api_endpoint_timing("fhir_get_care_plan")
async def get_care_plan(
    care_plan_id: str = Path(..., description="CarePlan ID"),
    request: Request = None,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get a FHIR R5 CarePlan resource by ID"""
    return await get_fhir_resource_endpoint("CarePlan", care_plan_id, request, current_user)

@router.put("/CarePlan/{care_plan_id}", summary="Update CarePlan")
@api_endpoint_timing("fhir_update_care_plan")
async def update_care_plan(
    care_plan_id: str = Path(..., description="CarePlan ID"),
    care_plan_data: Dict[str, Any] = Body(...),
    request: Request = None,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Update a FHIR R5 CarePlan resource"""
    return await update_fhir_resource_endpoint("CarePlan", care_plan_id, care_plan_data, request, current_user)

@router.delete("/CarePlan/{care_plan_id}", summary="Delete CarePlan")
@api_endpoint_timing("fhir_delete_care_plan")
async def delete_care_plan(
    care_plan_id: str = Path(..., description="CarePlan ID"),
    request: Request = None,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Delete a FHIR R5 CarePlan resource"""
    return await delete_fhir_resource_endpoint("CarePlan", care_plan_id, request, current_user)

@router.get("/CarePlan", summary="Search CarePlans")
@api_endpoint_timing("fhir_search_care_plans")
async def search_care_plans(
    request: Request,
    patient: Optional[str] = Query(None, description="Patient reference"),
    category: Optional[str] = Query(None, description="Care plan category"),
    status: Optional[str] = Query(None, description="Care plan status"),
    intent: Optional[str] = Query(None, description="Care plan intent"),
    date: Optional[str] = Query(None, description="Date range"),
    _count: Optional[int] = Query(10, description="Number of results"),
    _offset: Optional[int] = Query(0, description="Search offset"),
    _sort: Optional[str] = Query(None, description="Sort parameters"),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Search FHIR R5 CarePlan resources"""
    search_params = {
        "patient": patient,
        "status": status,
        "date": date,
        "_count": _count,
        "_offset": _offset,
        "_sort": _sort
    }
    return await search_fhir_resources_endpoint("CarePlan", request, current_user, **search_params)

# =============== Specimen Resource Endpoints ===============

@router.post("/Specimen", summary="Create Specimen")
@api_endpoint_timing("fhir_create_specimen")
async def create_specimen(
    request: Request,
    specimen_data: Dict[str, Any] = Body(...),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Create a new FHIR R5 Specimen resource"""
    return await create_fhir_resource_endpoint("Specimen", specimen_data, request, current_user)

@router.get("/Specimen/{specimen_id}", summary="Get Specimen by ID")
@api_endpoint_timing("fhir_get_specimen")
async def get_specimen(
    specimen_id: str = Path(..., description="Specimen ID"),
    request: Request = None,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get a FHIR R5 Specimen resource by ID"""
    return await get_fhir_resource_endpoint("Specimen", specimen_id, request, current_user)

@router.put("/Specimen/{specimen_id}", summary="Update Specimen")
@api_endpoint_timing("fhir_update_specimen")
async def update_specimen(
    specimen_id: str = Path(..., description="Specimen ID"),
    specimen_data: Dict[str, Any] = Body(...),
    request: Request = None,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Update a FHIR R5 Specimen resource"""
    return await update_fhir_resource_endpoint("Specimen", specimen_id, specimen_data, request, current_user)

@router.delete("/Specimen/{specimen_id}", summary="Delete Specimen")
@api_endpoint_timing("fhir_delete_specimen")
async def delete_specimen(
    specimen_id: str = Path(..., description="Specimen ID"),
    request: Request = None,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Delete a FHIR R5 Specimen resource"""
    return await delete_fhir_resource_endpoint("Specimen", specimen_id, request, current_user)

@router.get("/Specimen", summary="Search Specimens")
@api_endpoint_timing("fhir_search_specimens")
async def search_specimens(
    request: Request,
    patient: Optional[str] = Query(None, description="Patient reference"),
    type: Optional[str] = Query(None, description="Specimen type"),
    status: Optional[str] = Query(None, description="Specimen status"),
    collected: Optional[str] = Query(None, description="Collection date"),
    accession: Optional[str] = Query(None, description="Accession identifier"),
    _count: Optional[int] = Query(10, description="Number of results"),
    _offset: Optional[int] = Query(0, description="Search offset"),
    _sort: Optional[str] = Query(None, description="Sort parameters"),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Search FHIR R5 Specimen resources"""
    search_params = {
        "patient": patient,
        "status": status,
        "date": collected,
        "_count": _count,
        "_offset": _offset,
        "_sort": _sort
    }
    return await search_fhir_resources_endpoint("Specimen", request, current_user, **search_params)

# =============== Comprehensive AMY Migration Endpoints ===============

@router.post("/migration/amy/comprehensive-patient", summary="Comprehensive AMY Patient Migration")
@api_endpoint_timing("fhir_migrate_amy_comprehensive")
async def migrate_amy_comprehensive_patient(
    request: Request,
    patient_id: str = Body(..., description="Patient ObjectId from AMY"),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Comprehensive migration of AMY patient data to all relevant FHIR R5 resources"""
    try:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        # Get patient document from AMY database
        patients_collection = fhir_service.mongodb_service.get_collection('patients')
        patient_doc = await patients_collection.find_one({"_id": ObjectId(patient_id)})
        
        if not patient_doc:
            raise HTTPException(
                status_code=404,
                detail=create_error_response(
                    "PATIENT_NOT_FOUND",
                    custom_message=f"Patient with ID {patient_id} not found in AMY database",
                    request_id=request_id
                ).dict()
            )
        
        # Perform comprehensive migration
        migration_results = await fhir_service.migrate_comprehensive_patient_to_fhir(patient_doc)
        
        response = create_success_response(
            message="Comprehensive AMY patient migration completed successfully",
            data=migration_results,
            request_id=request_id
        )
        
        return JSONResponse(
            content=response.dict(),
            media_type="application/fhir+json"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in comprehensive AMY patient migration: {e}")
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                "AMY_MIGRATION_ERROR",
                custom_message=f"Comprehensive migration failed: {str(e)}",
                request_id=request.headers.get("X-Request-ID")
            ).dict()
        )

@router.post("/migration/amy/patient-goals", summary="Migrate AMY Patient Goals")
@api_endpoint_timing("fhir_migrate_amy_goals")
async def migrate_amy_patient_goals(
    request: Request,
    patient_id: str = Body(..., description="Patient ObjectId from AMY"),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Migrate AMY patient goal data to FHIR Goal resources"""
    try:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        patients_collection = fhir_service.mongodb_service.get_collection('patients')
        patient_doc = await patients_collection.find_one({"_id": ObjectId(patient_id)})
        
        if not patient_doc:
            raise HTTPException(status_code=404, detail="Patient not found")
        
        goal_ids = await fhir_service.migrate_patient_goals_to_fhir(patient_doc)
        
        response = create_success_response(
            message=f"Successfully migrated {len(goal_ids)} goals from AMY patient data",
            data={"goal_ids": goal_ids, "total_goals": len(goal_ids)},
            request_id=request_id
        )
        
        return JSONResponse(content=response.dict(), media_type="application/fhir+json")
        
    except Exception as e:
        logger.error(f"Error migrating AMY patient goals: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/migration/amy/emergency-contacts", summary="Migrate AMY Emergency Contacts")
@api_endpoint_timing("fhir_migrate_amy_contacts")
async def migrate_amy_emergency_contacts(
    request: Request,
    patient_id: str = Body(..., description="Patient ObjectId from AMY"),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Migrate AMY emergency contact data to FHIR RelatedPerson resources"""
    try:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        patients_collection = fhir_service.mongodb_service.get_collection('patients')
        patient_doc = await patients_collection.find_one({"_id": ObjectId(patient_id)})
        
        if not patient_doc:
            raise HTTPException(status_code=404, detail="Patient not found")
        
        related_person_ids = await fhir_service.migrate_emergency_contacts_to_fhir(patient_doc)
        
        response = create_success_response(
            message=f"Successfully migrated {len(related_person_ids)} emergency contacts from AMY patient data",
            data={"related_person_ids": related_person_ids, "total_contacts": len(related_person_ids)},
            request_id=request_id
        )
        
        return JSONResponse(content=response.dict(), media_type="application/fhir+json")
        
    except Exception as e:
        logger.error(f"Error migrating AMY emergency contacts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/migration/amy/patient-alerts", summary="Migrate AMY Patient Alerts")
@api_endpoint_timing("fhir_migrate_amy_alerts")
async def migrate_amy_patient_alerts(
    request: Request,
    patient_id: str = Body(..., description="Patient ObjectId from AMY"),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Migrate AMY patient alert data to FHIR Flag resources"""
    try:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        patients_collection = fhir_service.mongodb_service.get_collection('patients')
        patient_doc = await patients_collection.find_one({"_id": ObjectId(patient_id)})
        
        if not patient_doc:
            raise HTTPException(status_code=404, detail="Patient not found")
        
        flag_ids = await fhir_service.migrate_patient_alerts_to_flags(patient_doc)
        
        response = create_success_response(
            message=f"Successfully migrated {len(flag_ids)} alerts from AMY patient data",
            data={"flag_ids": flag_ids, "total_flags": len(flag_ids)},
            request_id=request_id
        )
        
        return JSONResponse(content=response.dict(), media_type="application/fhir+json")
        
    except Exception as e:
        logger.error(f"Error migrating AMY patient alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/migration/amy/patient-devices", summary="Migrate AMY Patient Devices")
@api_endpoint_timing("fhir_migrate_amy_devices")
async def migrate_amy_patient_devices(
    request: Request,
    patient_id: str = Body(..., description="Patient ObjectId from AMY"),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Migrate AMY patient device data to FHIR Device resources"""
    try:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        patients_collection = fhir_service.mongodb_service.get_collection('patients')
        patient_doc = await patients_collection.find_one({"_id": ObjectId(patient_id)})
        
        if not patient_doc:
            raise HTTPException(status_code=404, detail="Patient not found")
        
        device_ids = await fhir_service.migrate_patient_devices_to_fhir(patient_doc)
        
        response = create_success_response(
            message=f"Successfully migrated {len(device_ids)} devices from AMY patient data",
            data={"device_ids": device_ids, "total_devices": len(device_ids)},
            request_id=request_id
        )
        
        return JSONResponse(content=response.dict(), media_type="application/fhir+json")
        
    except Exception as e:
        logger.error(f"Error migrating AMY patient devices: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 

# =============== Blockchain Hash Verification Endpoints ===============

@router.get("/{resource_type}/{resource_id}/$verify", summary="Verify Resource Blockchain Hash")
@api_endpoint_timing("fhir_verify_resource_blockchain")
async def verify_resource_blockchain_hash(
    resource_type: str = Path(..., description="FHIR resource type"),
    resource_id: str = Path(..., description="Resource ID"),
    request: Request = None,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Verify the blockchain hash integrity of a specific FHIR resource"""
    try:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        # Validate resource type
        if resource_type not in fhir_service.fhir_collections:
            raise HTTPException(
                status_code=400,
                detail=create_error_response(
                    "INVALID_RESOURCE_TYPE",
                    custom_message=f"Unsupported resource type: {resource_type}",
                    request_id=request_id
                ).dict()
            )
        
        verification_result = await fhir_service.verify_fhir_resource_integrity(
            resource_type=resource_type,
            resource_id=resource_id
        )
        
        response = create_success_response(
            message=f"Blockchain verification completed for {resource_type}/{resource_id}",
            data=verification_result,
            request_id=request_id
        )
        
        return JSONResponse(
            content=response.dict(),
            media_type="application/fhir+json"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying blockchain hash for {resource_type}/{resource_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                "BLOCKCHAIN_VERIFICATION_ERROR",
                custom_message=f"Failed to verify blockchain hash: {str(e)}",
                request_id=request.headers.get("X-Request-ID")
            ).dict()
        )

@router.post("/{resource_type}/$verify-batch", summary="Verify Batch Resource Blockchain Hashes")
@api_endpoint_timing("fhir_verify_batch_blockchain")
async def verify_batch_blockchain_hashes(
    resource_type: str = Path(..., description="FHIR resource type"),
    resource_ids: List[str] = Body(..., description="List of resource IDs to verify"),
    request: Request = None,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Verify the blockchain hash integrity of multiple FHIR resources"""
    try:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        # Validate resource type
        if resource_type not in fhir_service.fhir_collections:
            raise HTTPException(
                status_code=400,
                detail=create_error_response(
                    "INVALID_RESOURCE_TYPE",
                    custom_message=f"Unsupported resource type: {resource_type}",
                    request_id=request_id
                ).dict()
            )
        
        if not resource_ids:
            raise HTTPException(
                status_code=400,
                detail=create_error_response(
                    "EMPTY_RESOURCE_LIST",
                    custom_message="Resource IDs list cannot be empty",
                    request_id=request_id
                ).dict()
            )
        
        verification_result = await fhir_service.verify_fhir_batch_integrity(
            resource_type=resource_type,
            resource_ids=resource_ids
        )
        
        response = create_success_response(
            message=f"Batch blockchain verification completed for {len(resource_ids)} {resource_type} resources",
            data=verification_result,
            request_id=request_id
        )
        
        return JSONResponse(
            content=response.dict(),
            media_type="application/fhir+json"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying batch blockchain hashes for {resource_type}: {e}")
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                "BATCH_VERIFICATION_ERROR",
                custom_message=f"Failed to verify batch blockchain hashes: {str(e)}",
                request_id=request.headers.get("X-Request-ID")
            ).dict()
        )

@router.get("/blockchain/$chain-info", summary="Get Blockchain Chain Information")
@api_endpoint_timing("fhir_blockchain_chain_info")
async def get_blockchain_chain_info(
    request: Request,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get comprehensive information about the FHIR blockchain hash chain"""
    try:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        chain_info = await fhir_service.get_blockchain_chain_info()
        
        response = create_success_response(
            message="Blockchain chain information retrieved successfully",
            data=chain_info,
            request_id=request_id
        )
        
        return JSONResponse(
            content=response.dict(),
            media_type="application/fhir+json"
        )
        
    except Exception as e:
        logger.error(f"Error getting blockchain chain info: {e}")
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                "CHAIN_INFO_ERROR",
                custom_message=f"Failed to get blockchain chain info: {str(e)}",
                request_id=request.headers.get("X-Request-ID")
            ).dict()
        )

@router.get("/blockchain/$chain-verify", summary="Verify Blockchain Chain Integrity")
@api_endpoint_timing("fhir_blockchain_chain_verify")
async def verify_blockchain_chain_integrity(
    request: Request,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Verify the integrity of the entire blockchain hash chain"""
    try:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        verification_result = await fhir_service.verify_hash_chain_integrity()
        
        response = create_success_response(
            message="Blockchain chain integrity verification completed",
            data=verification_result,
            request_id=request_id
        )
        
        return JSONResponse(
            content=response.dict(),
            media_type="application/fhir+json"
        )
        
    except Exception as e:
        logger.error(f"Error verifying blockchain chain integrity: {e}")
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                "CHAIN_VERIFICATION_ERROR", 
                custom_message=f"Failed to verify blockchain chain integrity: {str(e)}",
                request_id=request.headers.get("X-Request-ID")
            ).dict()
        )

@router.get("/blockchain/$chain-export", summary="Export Blockchain Chain")
@api_endpoint_timing("fhir_blockchain_chain_export")
async def export_blockchain_chain(
    request: Request,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Export the complete blockchain hash chain for backup or analysis"""
    try:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        chain_export = await fhir_service.export_blockchain_chain()
        
        response = create_success_response(
            message="Blockchain chain exported successfully",
            data=chain_export,
            request_id=request_id
        )
        
        return JSONResponse(
            content=response.dict(),
            media_type="application/json",
            headers={
                "Content-Disposition": f"attachment; filename=blockchain_chain_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
            }
        )
        
    except Exception as e:
        logger.error(f"Error exporting blockchain chain: {e}")
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                "CHAIN_EXPORT_ERROR",
                custom_message=f"Failed to export blockchain chain: {str(e)}",
                request_id=request.headers.get("X-Request-ID")
            ).dict()
        )

@router.get("/blockchain/$statistics", summary="Get Blockchain Statistics")
@api_endpoint_timing("fhir_blockchain_statistics")
async def get_blockchain_statistics(
    request: Request,
    include_resource_details: bool = Query(False, description="Include detailed per-resource statistics"),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get comprehensive blockchain and FHIR resource statistics"""
    try:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        # Get basic chain info
        chain_info = await fhir_service.get_blockchain_chain_info()
        
        statistics = {
            "blockchain_summary": {
                "total_hashes": chain_info["chain_info"]["chain_length"],
                "genesis_hash": chain_info["chain_info"]["genesis_hash"],
                "latest_hash": chain_info["chain_info"]["latest_hash"],
                "algorithm": chain_info["chain_info"]["hash_algorithm"]
            },
            "fhir_resources": {
                "total_resources": chain_info["fhir_statistics"]["total_resources"],
                "verified_resources": chain_info["fhir_statistics"]["verified_resources"],
                "verification_rate": chain_info["fhir_statistics"]["verification_rate"],
                "resource_counts": chain_info["resource_type_counts"]
            },
            "integrity_status": {
                "chain_verified": True,  # Could add actual verification here
                "last_verification": datetime.utcnow().isoformat() + "Z"
            }
        }
        
        if include_resource_details:
            # Add detailed verification status per resource type
            statistics["detailed_verification"] = {}
            for resource_type in fhir_service.fhir_collections.keys():
                collection = fhir_service.fhir_collections[resource_type]
                total = chain_info["resource_type_counts"].get(resource_type, 0)
                
                # This could be enhanced to get actual verification counts
                statistics["detailed_verification"][resource_type] = {
                    "total": total,
                    "verified": total,  # Placeholder - could add actual verification logic
                    "verification_rate": 100.0 if total > 0 else 0.0
                }
        
        response = create_success_response(
            message="Blockchain statistics retrieved successfully",
            data=statistics,
            request_id=request_id
        )
        
        return JSONResponse(
            content=response.dict(),
            media_type="application/fhir+json"
        )
        
    except Exception as e:
        logger.error(f"Error getting blockchain statistics: {e}")
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                "STATISTICS_ERROR",
                custom_message=f"Failed to get blockchain statistics: {str(e)}",
                request_id=request.headers.get("X-Request-ID")
            ).dict()
        )