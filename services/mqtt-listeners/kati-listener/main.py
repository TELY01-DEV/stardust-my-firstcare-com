#!/usr/bin/env python3
"""
Kati Watch MQTT Listener Service
Handles MQTT messages from Kati Watch devices
"""

import os
import json
import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional
import sys

# Add shared utilities to path
sys.path.append('/app/shared')

from paho.mqtt import client as mqtt_client
from device_mapper import DeviceMapper
from data_processor import DataProcessor
from data_flow_emitter import data_flow_emitter
from fhir_validator import fhir_validator
import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class KatiMQTTListener:
    """Kati Watch MQTT Listener Service"""
    
    def __init__(self):
        # MQTT Configuration
        self.mqtt_broker = os.getenv('MQTT_BROKER_HOST', 'adam.amy.care')
        self.mqtt_port = int(os.getenv('MQTT_BROKER_PORT', 1883))
        self.mqtt_username = os.getenv('MQTT_USERNAME', 'webapi')
        self.mqtt_password = os.getenv('MQTT_PASSWORD', 'Sim!4433')
        self.mqtt_qos = int(os.getenv('MQTT_QOS', 1))
        self.mqtt_keepalive = int(os.getenv('MQTT_KEEPALIVE', 60))
        self.mqtt_timeout = int(os.getenv('MQTT_CONNECTION_TIMEOUT', 10))
        
        # Topics to subscribe to (wildcard for all Kati topics)
        self.topics = os.getenv('MQTT_TOPICS', 'iMEDE_watch/#').split(',')
        
        # MongoDB Configuration
        self.mongodb_uri = os.getenv('MONGODB_URI')
        self.mongodb_database = os.getenv('MONGODB_DATABASE', 'AMY')
        
        # Initialize services
        self.device_mapper = DeviceMapper(self.mongodb_uri, self.mongodb_database)
        self.data_processor = DataProcessor(self.mongodb_uri, self.mongodb_database)
        
        # MQTT client
        self.client = None
        self.connected = False
        
    def connect_mqtt(self) -> mqtt_client.Client:
        """Connect to MQTT broker"""
        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                logger.info("Connected to MQTT broker successfully")
                self.connected = True
                # Subscribe to topics
                for topic in self.topics:
                    client.subscribe(topic, self.mqtt_qos)
                    logger.info(f"Subscribed to topic: {topic}")
            else:
                logger.error(f"Failed to connect to MQTT broker, return code: {rc}")
                self.connected = False
        
        def on_disconnect(client, userdata, rc):
            logger.warning(f"Disconnected from MQTT broker, return code: {rc}")
            self.connected = False
        
        def on_message(client, userdata, msg):
            try:
                logger.info(f"Received message on topic: {msg.topic}")
                self.process_message(msg.topic, msg.payload.decode())
            except Exception as e:
                logger.error(f"Error processing message: {e}")
        
        # Create client
        client = mqtt_client.Client()
        client.username_pw_set(self.mqtt_username, self.mqtt_password)
        client.on_connect = on_connect
        client.on_disconnect = on_disconnect
        client.on_message = on_message
        
        # Connect
        try:
            client.connect(self.mqtt_broker, self.mqtt_port, self.mqtt_keepalive)
            client.loop_start()
            return client
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")
            return None
    
    def process_message(self, topic: str, payload: str):
        """Process incoming MQTT message"""
        try:
            # Step 1: MQTT Message Received
            data_flow_emitter.emit_mqtt_received("Kati", topic, {"raw_payload": payload})
            
            # Parse JSON payload
            data = json.loads(payload)
            logger.info(f"Processing {topic} message")
            
            # Step 2: Payload Parsed
            data_flow_emitter.emit_payload_parsed("Kati", topic, data, {"parsed": True})
            
            # Step 2.5: FHIR Data Format Validation (NEW)
            try:
                validation_result = fhir_validator.validate_kati_data_format(data, topic)
                
                if not validation_result["valid"]:
                    logger.error(f"❌ Kati Data validation failed: {validation_result['errors']}")
                    if validation_result["warnings"]:
                        logger.warning(f"⚠️ Kati Data validation warnings: {validation_result['warnings']}")
                    data_flow_emitter.emit_error("2.5_fhir_validation", "Kati", topic, data, f"Validation failed: {validation_result['errors']}")
                    return
                
                if validation_result["warnings"]:
                    logger.warning(f"⚠️ Kati Data validation warnings: {validation_result['warnings']}")
                
                # Use validated and transformed data
                validated_data = validation_result["transformed_data"]
                logger.info(f"✅ Kati Data validation passed - Topic: {topic}")
                data_flow_emitter.emit_fhir_validation("Kati", topic, data, {"validated": True, "device_type": "Kati_Watch"})
                
            except Exception as e:
                logger.error(f"❌ Error in Kati FHIR validation: {e}")
                data_flow_emitter.emit_error("2.5_fhir_validation", "Kati", topic, data, f"Validation error: {str(e)}")
                return
            
            # Extract IMEI from payload
            imei = data.get('IMEI')
            if not imei:
                logger.warning("No IMEI found in Kati message")
                data_flow_emitter.emit_error("2_payload_parsed", "Kati", topic, data, "No IMEI found in payload")
                return
            
            # Find patient by Kati IMEI
            patient = self.device_mapper.find_patient_by_kati_imei(imei)
            
            # Step 3: Patient Lookup
            patient_info = None
            if patient:
                patient_info = {
                    "patient_id": str(patient['_id']),
                    "patient_name": f"{patient.get('first_name', '')} {patient.get('last_name', '')}".strip(),
                    "first_name": patient.get('first_name', ''),
                    "last_name": patient.get('last_name', '')
                }
                data_flow_emitter.emit_patient_lookup("Kati", topic, data, patient_info)
            else:
                error_msg = f"No patient found for Kati IMEI: {imei}"
                logger.warning(error_msg)
                data_flow_emitter.emit_patient_lookup("Kati", topic, data, None, error_msg)
                return
            
            patient_name = f"{patient.get('first_name', '')} {patient.get('last_name', '')}".strip()
            logger.info(f"⌚ Processing {topic} data for patient {patient['_id']} ({patient_name})")
            logger.info(f"📱 Kati IMEI: {imei}")
            logger.info(f"📊 Raw payload keys: {list(data.keys())}")
            
            # Process the data based on topic using validated data
            success = self.data_processor.process_kati_data(patient['_id'], topic, validated_data, patient_name)
            
            # Step 4: Patient Updated
            medical_data = {
                "topic": topic,
                "imei": imei,
                "processed": success,
                "validation_passed": True
            }
            data_flow_emitter.emit_patient_updated("Kati", topic, data, patient_info, medical_data)
            
            # Step 5: Medical Data Stored
            if success:
                logger.info(f"✅ Successfully processed {topic} data for patient {patient['_id']} ({patient_name})")
                data_flow_emitter.emit_medical_stored("Kati", topic, data, patient_info, medical_data)
                
                # Step 6: FHIR R5 Resource Data Store (only for Patient resource data)
                try:
                    # Check if this is patient-related data that should be stored in FHIR R5
                    if self._should_store_in_fhir(topic, validated_data):
                        fhir_success = self._process_fhir_r5_data(topic, validated_data, patient_info)
                        if fhir_success:
                            # Determine the correct FHIR resource type
                            fhir_resource_type = self._determine_fhir_resource_type(topic, validated_data)
                            fhir_data = {
                                "topic": topic,
                                "imei": imei,
                                "fhir_processed": True,
                                "resource_type": fhir_resource_type
                            }
                            data_flow_emitter.emit_fhir_r5_stored("Kati", topic, data, patient_info, fhir_data)
                            logger.info(f"✅ FHIR R5 data stored for patient {patient['_id']} ({patient_name}) - Resource: {fhir_resource_type}")
                        else:
                            logger.warning(f"⚠️ FHIR R5 processing failed for patient {patient['_id']} ({patient_name})")
                            data_flow_emitter.emit_error("6_fhir_r5_stored", "Kati", topic, data, "FHIR R5 processing failed")
                    else:
                        logger.info(f"ℹ️ Skipping FHIR R5 storage for non-patient data: {topic}")
                except Exception as e:
                    logger.error(f"❌ Error in FHIR R5 processing: {e}")
                    data_flow_emitter.emit_error("6_fhir_r5_stored", "Kati", topic, data, f"FHIR R5 error: {str(e)}")
            else:
                logger.error(f"❌ Failed to process {topic} data for patient {patient['_id']} ({patient_name})")
                data_flow_emitter.emit_error("5_medical_stored", "Kati", topic, data, f"Failed to process {topic} data")
                
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON payload: {e}")
            data_flow_emitter.emit_error("2_payload_parsed", "Kati", topic, {"raw_payload": payload}, f"Invalid JSON: {e}")
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            data_flow_emitter.emit_error("1_mqtt_received", "Kati", topic, {"raw_payload": payload}, str(e))
    
    def _should_store_in_fhir(self, topic: str, data: Dict[str, Any]) -> bool:
        """Check if the data should be stored in FHIR R5 (only for Patient resource data)"""
        # Only store patient-related data in FHIR R5
        patient_related_topics = [
            "iMEDE_watch/VitalSign",  # Vital signs
            "iMEDE_watch/AP55",       # Batch vital signs
            "iMEDE_watch/location",   # Location data
            "iMEDE_watch/sleepdata",  # Sleep data
            "iMEDE_watch/hb"          # Heartbeat with step count
        ]
        return topic in patient_related_topics
    
    def _process_fhir_r5_data(self, topic: str, data: dict, patient_info: dict) -> bool:
        """Process data for FHIR R5 storage using HTTP API calls"""
        try:
            api_base_url = os.getenv('STARDUST_API_URL', 'http://stardust-api:5054')
            api_token = os.getenv('STARDUST_API_TOKEN', 'test-token')
            # Transform Kati data to FHIR R5 Observation format
            observation_data = self._transform_kati_to_fhir_observation(topic, data, patient_info)
            if not observation_data:
                logger.warning(f"No FHIR Observation data generated for topic {topic}")
                return False
            headers = {
                'Authorization': f'Bearer {api_token}',
                'Content-Type': 'application/json'
            }
            response = requests.post(f"{api_base_url}/fhir/R5/Observation", json=observation_data, headers=headers, timeout=10)
            if response.status_code in (200, 201):
                logger.info(f"✅ FHIR R5 Observation created for patient {patient_info.get('patient_id')}")
                return True
            else:
                logger.error(f"FHIR R5 API error: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"Error processing FHIR R5 data: {e}")
            return False
    
    def _transform_kati_to_fhir_observation(self, topic: str, data: Dict[str, Any], patient_info: Dict[str, Any]) -> Dict[str, Any]:
        """Transform Kati data to FHIR R5 Observation format"""
        try:
            # Base observation structure
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
                "subject": {
                    "reference": f"Patient/{patient_info['patient_id']}"
                },
                "effectiveDateTime": datetime.now().isoformat(),
                "issued": datetime.now().isoformat(),
                "performer": [
                    {
                        "reference": f"Device/Kati_{data.get('IMEI', 'unknown')}"
                    }
                ]
            }
            
            # Transform based on topic
            if topic == "iMEDE_watch/hb" and "step" in data:
                # Step count observation
                observation.update({
                    "code": {
                        "coding": [
                            {
                                "system": "http://loinc.org",
                                "code": "55423-8",
                                "display": "Number of steps in 24 hour Measured"
                            }
                        ],
                        "text": "Step Count"
                    },
                    "valueQuantity": {
                        "value": float(data["step"]),
                        "unit": "steps",
                        "system": "http://unitsofmeasure.org",
                        "code": "steps"
                    }
                })
                
            elif topic == "iMEDE_watch/VitalSign":
                # Vital signs observation
                vital_signs = []
                
                # Heart rate
                if "hr" in data:
                    vital_signs.append({
                        "code": {
                            "coding": [
                                {
                                    "system": "http://loinc.org",
                                    "code": "8867-4",
                                    "display": "Heart rate"
                                }
                            ],
                            "text": "Heart Rate"
                        },
                        "valueQuantity": {
                            "value": float(data["hr"]),
                            "unit": "beats/min",
                            "system": "http://unitsofmeasure.org",
                            "code": "/min"
                        }
                    })
                
                # Blood pressure
                if "systolic" in data and "diastolic" in data:
                    vital_signs.append({
                        "code": {
                            "coding": [
                                {
                                    "system": "http://loinc.org",
                                    "code": "85354-9",
                                    "display": "Blood pressure panel"
                                }
                            ],
                            "text": "Blood Pressure"
                        },
                        "component": [
                            {
                                "code": {
                                    "coding": [
                                        {
                                            "system": "http://loinc.org",
                                            "code": "8480-6",
                                            "display": "Systolic blood pressure"
                                        }
                                    ]
                                },
                                "valueQuantity": {
                                    "value": float(data["systolic"]),
                                    "unit": "mmHg",
                                    "system": "http://unitsofmeasure.org",
                                    "code": "mm[Hg]"
                                }
                            },
                            {
                                "code": {
                                    "coding": [
                                        {
                                            "system": "http://loinc.org",
                                            "code": "8462-4",
                                            "display": "Diastolic blood pressure"
                                        }
                                    ]
                                },
                                "valueQuantity": {
                                    "value": float(data["diastolic"]),
                                    "unit": "mmHg",
                                    "system": "http://unitsofmeasure.org",
                                    "code": "mm[Hg]"
                                }
                            }
                        ]
                    })
                
                # SpO2
                if "spo2" in data:
                    vital_signs.append({
                        "code": {
                            "coding": [
                                {
                                    "system": "http://loinc.org",
                                    "code": "2708-6",
                                    "display": "Oxygen saturation"
                                }
                            ],
                            "text": "SpO2"
                        },
                        "valueQuantity": {
                            "value": float(data["spo2"]),
                            "unit": "%",
                            "system": "http://unitsofmeasure.org",
                            "code": "%"
                        }
                    })
                
                # Temperature
                if "temp" in data:
                    vital_signs.append({
                        "code": {
                            "coding": [
                                {
                                    "system": "http://loinc.org",
                                    "code": "8310-5",
                                    "display": "Body temperature"
                                }
                            ],
                            "text": "Body Temperature"
                        },
                        "valueQuantity": {
                            "value": float(data["temp"]),
                            "unit": "°C",
                            "system": "http://unitsofmeasure.org",
                            "code": "Cel"
                        }
                    })
                
                # Return multiple observations if multiple vital signs
                if len(vital_signs) == 1:
                    observation.update(vital_signs[0])
                elif len(vital_signs) > 1:
                    # For multiple vital signs, we'll create separate observations
                    # For now, return the first one
                    observation.update(vital_signs[0])
                else:
                    return None
                    
            elif topic == "iMEDE_watch/location":
                # Location observation
                if "latitude" in data and "longitude" in data:
                    observation.update({
                        "code": {
                            "coding": [
                                {
                                    "system": "http://loinc.org",
                                    "code": "86711-2",
                                    "display": "Location"
                                }
                            ],
                            "text": "Location"
                        },
                        "valueString": f"{data['latitude']},{data['longitude']}"
                    })
                else:
                    return None
                    
            else:
                # Unknown topic
                return None
            
            return observation
            
        except Exception as e:
            logger.error(f"Error transforming Kati data to FHIR: {e}")
            return None
    
    def _determine_fhir_resource_type(self, topic: str, data: Dict[str, Any]) -> str:
        """Determine the correct FHIR resource type for the data"""
        # All Kati Watch medical data is stored as Observation resources
        return "Observation"
    
    async def run(self):
        """Run the MQTT listener"""
        logger.info("Starting Kati Watch MQTT Listener Service")
        
        # Connect to MQTT broker
        self.client = self.connect_mqtt()
        if not self.client:
            logger.error("Failed to connect to MQTT broker")
            return
        
        try:
            # Keep the service running
            while True:
                if not self.connected:
                    logger.warning("MQTT connection lost, attempting to reconnect...")
                    self.client.reconnect()
                
                await asyncio.sleep(5)
                
        except KeyboardInterrupt:
            logger.info("Shutting down Kati Watch MQTT Listener Service")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
        finally:
            if self.client:
                self.client.loop_stop()
                self.client.disconnect()
            
            # Close database connections
            self.device_mapper.close()
            self.data_processor.close()

if __name__ == "__main__":
    listener = KatiMQTTListener()
    asyncio.run(listener.run()) 