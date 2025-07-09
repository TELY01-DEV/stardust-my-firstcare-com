"""
Kati Watch FHIR Integration API Routes
=====================================
API endpoints for processing Kati Watch MQTT data and converting to FHIR R5 resources.

These routes serve as the bridge between the MQTT parser and the FHIR R5 system,
enabling real-time patient data ingestion from IoT devices.
"""

from fastapi import APIRouter, Depends, Body, Request, HTTPException
from typing import Dict, Any, List, Optional
import uuid
from datetime import datetime

from app.services.kati_watch_fhir_service import KatiWatchFHIRService
from app.services.auth import require_auth
from app.utils.structured_logging import get_logger
from app.utils.performance_decorators import api_endpoint_timing
from app.utils.error_definitions import create_success_response, create_error_response

logger = get_logger(__name__)
router = APIRouter(prefix="/kati-watch", tags=["Kati Watch FHIR Integration"])

# Initialize the Kati Watch FHIR service
kati_fhir_service = KatiWatchFHIRService()

@router.post("/mqtt/process", summary="Process MQTT Message to FHIR")
@api_endpoint_timing("kati_watch_mqtt_process")
async def process_mqtt_message(
    request: Request,
    mqtt_data: Dict[str, Any] = Body(..., description="MQTT message data with topic and payload"),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """
    Process MQTT message from Kati Watch and create FHIR R5 resources
    
    Expected payload format:
    {
        "topic": "iMEDE_watch/VitalSign",
        "payload": {
            "IMEI": "865067123456789",
            "heartRate": 72,
            "bloodPressure": {"bp_sys": 122, "bp_dia": 74},
            "spO2": 97,
            "bodyTemperature": 36.6,
            "timeStamps": "16/06/2025 12:30:45"
        }
    }
    """
    try:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        # Validate required fields
        if 'topic' not in mqtt_data or 'payload' not in mqtt_data:
                         return create_error_response(
                 error_code="INVALID_REQUEST",
                 custom_message="Missing required fields: topic and payload",
                 request_id=request_id
             )
        
        topic = mqtt_data['topic']
        payload = mqtt_data['payload']
        
        logger.info(f"Processing Kati Watch MQTT message: topic={topic}, IMEI={payload.get('IMEI')}")
        
        # Process the MQTT message and create FHIR resources
        result = await kati_fhir_service.process_mqtt_message(topic, payload)
        
                 if result['status'] == 'error':
             return create_error_response(
                 error_code="PROCESSING_ERROR",
                 custom_message=result.get('error', 'Unknown processing error'),
                 request_id=request_id
             )
        elif result['status'] == 'skipped':
            return create_success_response(
                message=f"Message skipped: {result.get('reason')}",
                data=result,
                request_id=request_id
            )
        else:
            return create_success_response(
                message=f"Successfully processed {topic} message",
                data=result,
                request_id=request_id
            )
            
    except Exception as e:
        logger.error(f"Failed to process Kati Watch MQTT message: {e}")
        return create_error_response(
            error_code="PROCESSING_ERROR",
            message=f"Failed to process MQTT message: {str(e)}",
            request_id=request_id
        )

@router.post("/mqtt/batch", summary="Process Multiple MQTT Messages")
@api_endpoint_timing("kati_watch_mqtt_batch")
async def process_mqtt_batch(
    request: Request,
    mqtt_batch: Dict[str, Any] = Body(..., description="Batch of MQTT messages"),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """
    Process multiple MQTT messages in a single request
    
    Expected payload format:
    {
        "messages": [
            {"topic": "iMEDE_watch/VitalSign", "payload": {...}},
            {"topic": "iMEDE_watch/location", "payload": {...}},
            {"topic": "iMEDE_watch/sleepdata", "payload": {...}}
        ]
    }
    """
    try:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        messages = mqtt_batch.get('messages', [])
        if not messages:
            return create_error_response(
                error_code="INVALID_REQUEST",
                message="No messages provided in batch",
                request_id=request_id
            )
        
        results = {
            "processed": 0,
            "skipped": 0,
            "errors": 0,
            "details": []
        }
        
        for i, message in enumerate(messages):
            try:
                if 'topic' not in message or 'payload' not in message:
                    results["errors"] += 1
                    results["details"].append({
                        "index": i,
                        "status": "error",
                        "error": "Missing topic or payload"
                    })
                    continue
                
                result = await kati_fhir_service.process_mqtt_message(
                    message['topic'], 
                    message['payload']
                )
                
                if result['status'] == 'success':
                    results["processed"] += 1
                elif result['status'] == 'skipped':
                    results["skipped"] += 1
                else:
                    results["errors"] += 1
                
                results["details"].append({
                    "index": i,
                    "topic": message['topic'],
                    "imei": message['payload'].get('IMEI'),
                    "status": result['status'],
                    "observations": result.get('observations', [])
                })
                
            except Exception as e:
                results["errors"] += 1
                results["details"].append({
                    "index": i,
                    "status": "error",
                    "error": str(e)
                })
        
        return create_success_response(
            message=f"Batch processed: {results['processed']} success, {results['skipped']} skipped, {results['errors']} errors",
            data=results,
            request_id=request_id
        )
        
    except Exception as e:
        logger.error(f"Failed to process MQTT batch: {e}")
        return create_error_response(
            error_code="BATCH_PROCESSING_ERROR",
            message=f"Failed to process MQTT batch: {str(e)}",
            request_id=request_id
        )

@router.post("/device/register", summary="Register Kati Watch Device")
@api_endpoint_timing("kati_watch_device_register")
async def register_device(
    request: Request,
    device_data: Dict[str, Any] = Body(..., description="Device registration data"),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """
    Register a Kati Watch device with a patient
    
    Expected payload format:
    {
        "imei": "865067123456789",
        "patient_id": "60f7b3b3b3b3b3b3b3b3b3b3",
        "device_model": "Kati Watch Pro",
        "serial_number": "KW123456",
        "registration_date": "2024-01-01"
    }
    """
    try:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        # Validate required fields
        required_fields = ['imei', 'patient_id']
        for field in required_fields:
            if field not in device_data:
                return create_error_response(
                    error_code="INVALID_REQUEST",
                    message=f"Missing required field: {field}",
                    request_id=request_id
                )
        
        from app.services.mongo import mongodb_service
        device_collection = mongodb_service.get_collection("device_registrations")
        
        # Check if device is already registered
        existing_device = await device_collection.find_one({"imei": device_data['imei']})
        if existing_device:
            return create_error_response(
                error_code="DEVICE_ALREADY_REGISTERED",
                message=f"Device with IMEI {device_data['imei']} is already registered",
                request_id=request_id
            )
        
        # Create device registration record
        registration_doc = {
            "imei": device_data['imei'],
            "patient_id": device_data['patient_id'],
            "device_model": device_data.get('device_model', 'Kati Watch'),
            "serial_number": device_data.get('serial_number'),
            "registration_date": device_data.get('registration_date'),
            "status": "active",
            "created_at": datetime.utcnow(),
            "created_by": current_user.get('user_id')
        }
        
        result = await device_collection.insert_one(registration_doc)
        
        return create_success_response(
            message="Device registered successfully",
            data={
                "registration_id": str(result.inserted_id),
                "imei": device_data['imei'],
                "patient_id": device_data['patient_id']
            },
            request_id=request_id
        )
        
    except Exception as e:
        logger.error(f"Failed to register device: {e}")
        return create_error_response(
            error_code="REGISTRATION_ERROR",
            message=f"Failed to register device: {str(e)}",
            request_id=request_id
        )

@router.get("/device/{imei}", summary="Get Device Registration")
@api_endpoint_timing("kati_watch_device_get")
async def get_device_registration(
    imei: str,
    request: Request,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get device registration information by IMEI"""
    try:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        from app.services.mongo import mongodb_service
        device_collection = mongodb_service.get_collection("device_registrations")
        
        device_doc = await device_collection.find_one({"imei": imei})
        
        if not device_doc:
            return create_error_response(
                error_code="DEVICE_NOT_FOUND",
                message=f"Device with IMEI {imei} not found",
                request_id=request_id
            )
        
        # Convert ObjectId to string for JSON serialization
        device_doc['_id'] = str(device_doc['_id'])
        
        return create_success_response(
            message="Device registration found",
            data=device_doc,
            request_id=request_id
        )
        
    except Exception as e:
        logger.error(f"Failed to get device registration: {e}")
        return create_error_response(
            error_code="RETRIEVAL_ERROR",
            message=f"Failed to get device registration: {str(e)}",
            request_id=request_id
        )

@router.get("/patient/{patient_id}/observations", summary="Get Patient's Device Observations")
@api_endpoint_timing("kati_watch_patient_observations")
async def get_patient_observations(
    patient_id: str,
    request: Request,
    observation_type: Optional[str] = None,
    limit: int = 50,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get FHIR observations for a patient from Kati Watch devices"""
    try:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        # Build search parameters
        search_params = {
            "subject": f"Patient/{patient_id}",
            "_count": limit
        }
        
        # Add observation type filter if specified
        if observation_type:
            if observation_type == "vital-signs":
                search_params["category"] = "vital-signs"
            elif observation_type == "device-status":
                search_params["code"] = "67504-6"  # Device status LOINC code
            elif observation_type == "emergency":
                search_params["category"] = "safety"
        
        # Search FHIR observations
        from app.services.fhir_r5_service import FHIRR5Service
        fhir_service = FHIRR5Service()
        
        observations = await fhir_service.search_fhir_resources(
            "Observation", 
            **search_params
        )
        
        # Filter for Kati Watch device observations
        kati_observations = []
        for obs in observations.get('resources', []):
            device_info = obs.get('device', {})
            if 'Kati Watch' in device_info.get('display', ''):
                kati_observations.append(obs)
        
        return create_success_response(
            message=f"Found {len(kati_observations)} Kati Watch observations",
            data={
                "patient_id": patient_id,
                "observation_type": observation_type,
                "total": len(kati_observations),
                "observations": kati_observations
            },
            request_id=request_id
        )
        
    except Exception as e:
        logger.error(f"Failed to get patient observations: {e}")
        return create_error_response(
            error_code="RETRIEVAL_ERROR",
            message=f"Failed to get patient observations: {str(e)}",
            request_id=request_id
        ) 