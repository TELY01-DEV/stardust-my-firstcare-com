"""
Data Flow Event Emitter
Handles emission of step-by-step data flow events for real-time monitoring
"""

import os
import json
import logging
import requests
from datetime import datetime
from typing import Optional, Dict, Any
from bson import ObjectId

logger = logging.getLogger(__name__)

class DataFlowEmitter:
    """Emits data flow events to the web panel"""
    
    def __init__(self, web_panel_url: str = "http://mqtt-panel:8098"):
        self.web_panel_url = web_panel_url
        self.enabled = os.getenv('DATA_FLOW_EMISSION_ENABLED', 'true').lower() == 'true'
    
    def _serialize_for_json(self, obj):
        """Convert objects to JSON-serializable format"""
        if isinstance(obj, dict):
            return {k: self._serialize_for_json(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._serialize_for_json(item) for item in obj]
        elif isinstance(obj, ObjectId):
            return str(obj)
        elif hasattr(obj, 'isoformat'):  # datetime objects
            return obj.isoformat()
        elif hasattr(obj, '__str__'):
            return str(obj)
        else:
            return obj
        
    def emit_data_flow_event(self, step: str, status: str, device_type: str, topic: str,
                           payload: Dict[str, Any], patient_info: Optional[Dict[str, Any]] = None,
                           processed_data: Optional[Dict[str, Any]] = None, error: Optional[str] = None):
        """Emit a data flow event to the web panel"""
        if not self.enabled:
            return
            
        try:
            event_data = {
                "step": step,
                "status": status,
                "device_type": device_type,
                "topic": topic,
                "timestamp": datetime.utcnow().isoformat(),
                "payload": self._serialize_for_json(payload),
                "patient_info": self._serialize_for_json(patient_info) if patient_info else None,
                "processed_data": self._serialize_for_json(processed_data) if processed_data else None,
                "error": error
            }
            
            # Send to web panel via HTTP endpoint
            response = requests.post(
                f"{self.web_panel_url}/api/data-flow/emit",
                json={"event": event_data},
                timeout=30
            )
            
            if response.status_code == 200:
                logger.debug(f"✅ Data flow event emitted: {step} - {status}")
            else:
                logger.warning(f"⚠️ Failed to emit data flow event: {response.status_code}")
                
        except Exception as e:
            logger.error(f"❌ Error emitting data flow event: {e}")
    
    def emit_mqtt_received(self, device_type: str, topic: str, payload: Dict[str, Any]):
        """Emit MQTT message received event"""
        self.emit_data_flow_event(
            step="1_mqtt_received",
            status="success",
            device_type=device_type,
            topic=topic,
            payload=payload
        )
    
    def emit_payload_parsed(self, device_type: str, topic: str, payload: Dict[str, Any], parsed_data: Dict[str, Any]):
        """Emit payload parsed event"""
        self.emit_data_flow_event(
            step="2_payload_parsed",
            status="success",
            device_type=device_type,
            topic=topic,
            payload=payload,
            processed_data=parsed_data
        )
    
    def emit_patient_lookup(self, device_type: str, topic: str, payload: Dict[str, Any], 
                          patient_info: Optional[Dict[str, Any]], error: Optional[str] = None):
        """Emit patient lookup event"""
        status = "success" if patient_info else "error"
        self.emit_data_flow_event(
            step="3_patient_lookup",
            status=status,
            device_type=device_type,
            topic=topic,
            payload=payload,
            patient_info=patient_info,
            error=error
        )
    
    def emit_patient_updated(self, device_type: str, topic: str, payload: Dict[str, Any],
                           patient_info: Dict[str, Any], medical_data: Dict[str, Any]):
        """Emit patient collection updated event"""
        logger.debug(f"🔍 DEBUG: emit_patient_updated called with device_type: {device_type}, topic: {topic}")
        logger.debug(f"🔍 DEBUG: patient_info: {patient_info}")
        logger.debug(f"🔍 DEBUG: medical_data: {medical_data}")
        self.emit_data_flow_event(
            step="4_patient_updated",
            status="success",
            device_type=device_type,
            topic=topic,
            payload=payload,
            patient_info=patient_info,
            processed_data=medical_data
        )
    
    def emit_medical_stored(self, device_type: str, topic: str, payload: Dict[str, Any],
                          patient_info: Dict[str, Any], medical_data: Dict[str, Any]):
        """Emit medical collection stored event"""
        self.emit_data_flow_event(
            step="5_medical_stored",
            status="success",
            device_type=device_type,
            topic=topic,
            payload=payload,
            patient_info=patient_info,
            processed_data=medical_data
        )
    
    def emit_fhir_r5_stored(self, device_type: str, topic: str, payload: Dict[str, Any],
                           patient_info: Dict[str, Any], fhir_data: Dict[str, Any]):
        """Emit FHIR R5 resource data stored event (only for Patient resource data)"""
        self.emit_data_flow_event(
            step="6_fhir_r5_stored",
            status="success",
            device_type=device_type,
            topic=topic,
            payload=payload,
            patient_info=patient_info,
            processed_data=fhir_data
        )
    
    def emit_fhir_storage(self, device_type: str, topic: str, payload: Dict[str, Any],
                         patient_info: Dict[str, Any]):
        """Emit FHIR storage event (alias for emit_fhir_r5_stored for backward compatibility)"""
        self.emit_data_flow_event(
            step="6_fhir_storage",
            status="success",
            device_type=device_type,
            topic=topic,
            payload=payload,
            patient_info=patient_info,
            processed_data={"fhir_stored": True, "topic": topic}
        )
    
    def emit_data_processed(self, device_type: str, topic: str, payload: Dict[str, Any],
                           patient_info: Dict[str, Any]):
        """Emit data processed event (for non-FHIR data)"""
        self.emit_data_flow_event(
            step="6_data_processed",
            status="success",
            device_type=device_type,
            topic=topic,
            payload=payload,
            patient_info=patient_info,
            processed_data={"data_processed": True, "topic": topic}
        )
    
    def emit_fhir_validation(self, device_type: str, topic: str, payload: Dict[str, Any], validation_data: Dict[str, Any]):
        """Emit FHIR data format validation event"""
        self.emit_data_flow_event(
            step="2.5_fhir_validation",
            status="success",
            device_type=device_type,
            topic=topic,
            payload=payload,
            processed_data=validation_data
        )
    
    def emit_error(self, step: str, device_type: str, topic: str, payload: Dict[str, Any], error: str):
        """Emit error event"""
        self.emit_data_flow_event(
            step=step,
            status="error",
            device_type=device_type,
            topic=topic,
            payload=payload,
            error=error
        )
    
    def emit_device_status(self, device_type: str, topic: str, payload: Dict[str, Any], status_data: Dict[str, Any]):
        """Emit device status event (for AVA4 online/offline status)"""
        self.emit_data_flow_event(
            step="3_device_status",
            status="success",
            device_type=device_type,
            topic=topic,
            payload=payload,
            processed_data=status_data
        )

# Global instance
data_flow_emitter = DataFlowEmitter() 