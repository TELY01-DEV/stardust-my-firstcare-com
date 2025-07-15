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

logger = logging.getLogger(__name__)

class DataFlowEmitter:
    """Emits data flow events to the web panel"""
    
    def __init__(self, web_panel_url: str = "http://localhost:8098"):
        self.web_panel_url = web_panel_url
        self.enabled = os.getenv('DATA_FLOW_EMISSION_ENABLED', 'true').lower() == 'true'
        
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
                "payload": payload,
                "patient_info": patient_info,
                "processed_data": processed_data,
                "error": error
            }
            
            # Send to web panel via HTTP endpoint (for now)
            # In production, this would use WebSocket or message queue
            response = requests.post(
                f"{self.web_panel_url}/api/data-flow/emit",
                json={"event": event_data},
                timeout=5
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

# Global instance
data_flow_emitter = DataFlowEmitter() 