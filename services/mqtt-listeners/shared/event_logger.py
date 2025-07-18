#!/usr/bin/env python3
"""
Event Logger Utility
Shared module for sending events to the unified event log API
"""

import os
import json
import logging
import requests
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from urllib.parse import urljoin

logger = logging.getLogger(__name__)

class EventLogger:
    """Utility class for logging events to the unified event log API"""
    
    def __init__(self, api_base_url: str = None, source_name: str = "unknown"):
        """
        Initialize the event logger
        
        Args:
            api_base_url: Base URL for the event log API (defaults to environment variable)
            source_name: Name of the source (e.g., 'ava4-listener', 'kati-listener')
        """
        self.api_base_url = api_base_url or os.getenv('EVENT_LOG_API_URL', 'http://mqtt-panel:8098')
        self.source_name = source_name
        self.event_log_url = urljoin(self.api_base_url, '/api/event-log')
        
        logger.info(f"EventLogger initialized for {source_name} -> {self.event_log_url}")
    
    def log_event(self, 
                  event_type: str, 
                  status: str, 
                  device_id: Optional[str] = None, 
                  patient: Optional[str] = None, 
                  topic: Optional[str] = None, 
                  medical_data: Optional[str] = None, 
                  details: Optional[Dict[str, Any]] = None, 
                  error: Optional[str] = None) -> bool:
        """
        Log an event to the unified event log
        
        Args:
            event_type: Type of event (e.g., 'DATA_RECEIVED', 'DATA_PROCESSED', 'ERROR_OCCURRED')
            status: Event status ('success', 'error', 'warning', 'info', 'processing')
            device_id: Device identifier
            patient: Patient name or identifier
            topic: MQTT topic
            medical_data: Type of medical data
            details: Additional event details
            error: Error message if applicable
            
        Returns:
            bool: True if event was logged successfully, False otherwise
        """
        try:
            event_data = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'source': self.source_name,
                'event_type': event_type,
                'status': status
            }
            
            # Add optional fields
            if device_id:
                event_data['device_id'] = device_id
            if patient:
                event_data['patient'] = patient
            if topic:
                event_data['topic'] = topic
            if medical_data:
                event_data['medical_data'] = medical_data
            if error:
                event_data['error'] = error
            
            # Add details
            if details:
                event_data['details'] = details
            else:
                event_data['details'] = {}
            
            # Send to API
            response = requests.post(
                self.event_log_url,
                json=event_data,
                headers={'Content-Type': 'application/json'},
                timeout=5
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    logger.debug(f"Event logged successfully: {event_type} - {status}")
                    return True
                else:
                    logger.warning(f"Event log API returned error: {result.get('error')}")
                    return False
            else:
                logger.warning(f"Event log API returned status {response.status_code}: {response.text}")
                return False
                
        except requests.RequestException as e:
            logger.warning(f"Failed to send event to log API: {e}")
            return False
        except Exception as e:
            logger.error(f"Error logging event: {e}")
            return False
    
    def log_data_received(self, device_id: str, topic: str, payload_size: int, 
                         patient: Optional[str] = None, medical_data: Optional[str] = None) -> bool:
        """Log when data is received from a device"""
        details = {
            'payload_size': payload_size,
            'message': f'Data received from {device_id} on topic {topic}'
        }
        return self.log_event(
            event_type='DATA_RECEIVED',
            status='success',
            device_id=device_id,
            patient=patient,
            topic=topic,
            medical_data=medical_data,
            details=details
        )
    
    def log_data_processed(self, device_id: str, topic: str, processing_time: float,
                          patient: Optional[str] = None, medical_data: Optional[str] = None) -> bool:
        """Log when data is successfully processed"""
        details = {
            'processing_time_ms': round(processing_time * 1000, 2),
            'message': f'Data processed successfully for {device_id}'
        }
        return self.log_event(
            event_type='DATA_PROCESSED',
            status='success',
            device_id=device_id,
            patient=patient,
            topic=topic,
            medical_data=medical_data,
            details=details
        )
    
    def log_data_stored(self, device_id: str, collection: str, record_id: str,
                       patient: Optional[str] = None, medical_data: Optional[str] = None) -> bool:
        """Log when data is stored in database"""
        details = {
            'collection': collection,
            'record_id': record_id,
            'message': f'Data stored in {collection} collection'
        }
        return self.log_event(
            event_type='DATA_STORED',
            status='success',
            device_id=device_id,
            patient=patient,
            medical_data=medical_data,
            details=details
        )
    
    def log_fhir_converted(self, device_id: str, fhir_resource_type: str, fhir_id: str,
                          patient: Optional[str] = None, medical_data: Optional[str] = None) -> bool:
        """Log when data is converted to FHIR format"""
        details = {
            'fhir_resource_type': fhir_resource_type,
            'fhir_id': fhir_id,
            'message': f'Data converted to FHIR {fhir_resource_type}'
        }
        return self.log_event(
            event_type='FHIR_CONVERTED',
            status='success',
            device_id=device_id,
            patient=patient,
            medical_data=medical_data,
            details=details
        )
    
    def log_error(self, device_id: str, error_type: str, error_message: str,
                 topic: Optional[str] = None, patient: Optional[str] = None) -> bool:
        """Log when an error occurs"""
        details = {
            'error_type': error_type,
            'error_message': error_message,
            'message': f'Error occurred: {error_type}'
        }
        return self.log_event(
            event_type='ERROR_OCCURRED',
            status='error',
            device_id=device_id,
            patient=patient,
            topic=topic,
            details=details,
            error=error_message
        )
    
    def log_warning(self, device_id: str, warning_type: str, warning_message: str,
                   topic: Optional[str] = None, patient: Optional[str] = None) -> bool:
        """Log when a warning occurs"""
        details = {
            'warning_type': warning_type,
            'warning_message': warning_message,
            'message': f'Warning: {warning_type}'
        }
        return self.log_event(
            event_type='WARNING_OCCURRED',
            status='warning',
            device_id=device_id,
            patient=patient,
            topic=topic,
            details=details
        )
    
    def log_alert_sent(self, alert_type: str, alert_message: str, 
                      device_id: Optional[str] = None, patient: Optional[str] = None) -> bool:
        """Log when an alert is sent"""
        details = {
            'alert_type': alert_type,
            'alert_message': alert_message,
            'message': f'Alert sent: {alert_type}'
        }
        return self.log_event(
            event_type='ALERT_SENT',
            status='info',
            device_id=device_id,
            patient=patient,
            details=details
        )

# Convenience functions for quick logging
def log_data_received(source_name: str, device_id: str, topic: str, payload_size: int, 
                     patient: Optional[str] = None, medical_data: Optional[str] = None) -> bool:
    """Quick function to log data received event"""
    logger_instance = EventLogger(source_name=source_name)
    return logger_instance.log_data_received(device_id, topic, payload_size, patient, medical_data)

def log_data_processed(source_name: str, device_id: str, topic: str, processing_time: float,
                      patient: Optional[str] = None, medical_data: Optional[str] = None) -> bool:
    """Quick function to log data processed event"""
    logger_instance = EventLogger(source_name=source_name)
    return logger_instance.log_data_processed(device_id, topic, processing_time, patient, medical_data)

def log_error(source_name: str, device_id: str, error_type: str, error_message: str,
             topic: Optional[str] = None, patient: Optional[str] = None) -> bool:
    """Quick function to log error event"""
    logger_instance = EventLogger(source_name=source_name)
    return logger_instance.log_error(device_id, error_type, error_message, topic, patient) 