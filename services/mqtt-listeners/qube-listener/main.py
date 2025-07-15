#!/usr/bin/env python3
"""
Qube-Vital MQTT Listener Service
Handles MQTT messages from Qube-Vital devices
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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class QubeMQTTListener:
    """Qube-Vital MQTT Listener Service"""
    
    def __init__(self):
        # MQTT Configuration
        self.mqtt_broker = os.getenv('MQTT_BROKER_HOST', 'adam.amy.care')
        self.mqtt_port = int(os.getenv('MQTT_BROKER_PORT', 1883))
        self.mqtt_username = os.getenv('MQTT_USERNAME', 'webapi')
        self.mqtt_password = os.getenv('MQTT_PASSWORD', 'Sim!4433')
        self.mqtt_qos = int(os.getenv('MQTT_QOS', 1))
        self.mqtt_keepalive = int(os.getenv('MQTT_KEEPALIVE', 60))
        self.mqtt_timeout = int(os.getenv('MQTT_CONNECTION_TIMEOUT', 10))
        
        # Topics to subscribe to
        self.topics = os.getenv('MQTT_TOPICS', 'CM4_BLE_GW_TX').split(',')
        
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
            data_flow_emitter.emit_mqtt_received("Qube", topic, {"raw_payload": payload})
            
            # Parse JSON payload
            data = json.loads(payload)
            logger.info(f"Processing {topic} message: {data.get('type', 'unknown')}")
            
            # Step 2: Payload Parsed
            data_flow_emitter.emit_payload_parsed("Qube", topic, data, {"parsed": True})
            
            msg_type = data.get('type')
            
            if msg_type == "HB_Msg":
                self.process_qube_status(data)
            elif msg_type == "reportAttribute":
                self.process_qube_medical_data(data)
            else:
                logger.info(f"Unhandled message type: {msg_type}")
                data_flow_emitter.emit_error("2_payload_parsed", "Qube", topic, data, f"Unhandled message type: {msg_type}")
                
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON payload: {e}")
            data_flow_emitter.emit_error("2_payload_parsed", "Qube", topic, {"raw_payload": payload}, f"Invalid JSON: {e}")
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            data_flow_emitter.emit_error("1_mqtt_received", "Qube", topic, {"raw_payload": payload}, str(e))
    
    def process_qube_status(self, data: Dict[str, Any]):
        """Process Qube-Vital status messages (heartbeat)"""
        try:
            mac_address = data.get('mac')
            imei = data.get('IMEI')
            
            if not mac_address:
                logger.warning("No MAC address in Qube-Vital status message")
                return
            
            logger.info(f"Qube-Vital status: MAC={mac_address}, IMEI={imei}")
            
            # Store device status (optional - for monitoring)
            status_data = {
                "type": "heartbeat",
                "mac": mac_address,
                "imei": imei,
                "timestamp": datetime.utcnow(),
                "data": data.get('data', {})
            }
            
            # You could store this in a device_status collection if needed
            # self.db.device_status.insert_one(status_data)
            
        except Exception as e:
            logger.error(f"Error processing Qube-Vital status: {e}")
    
    def process_qube_medical_data(self, data: Dict[str, Any]):
        """Process Qube-Vital medical device data"""
        try:
            citiz = data.get('citiz')
            attribute = data.get('data', {}).get('attribute')
            value = data.get('data', {}).get('value', {})
            
            if not citiz:
                logger.warning("No citizen ID in Qube-Vital medical data")
                return
            
            if not attribute:
                logger.warning("No attribute in Qube-Vital medical data")
                return
            
            # Step 2.5: FHIR Data Format Validation (NEW)
            try:
                validation_result = fhir_validator.validate_qube_data_format(data)
                
                if not validation_result["valid"]:
                    logger.error(f"❌ Qube-Vital Data validation failed: {validation_result['errors']}")
                    if validation_result["warnings"]:
                        logger.warning(f"⚠️ Qube-Vital Data validation warnings: {validation_result['warnings']}")
                    data_flow_emitter.emit_error("2.5_fhir_validation", "Qube", "CM4_BLE_GW_TX", data, f"Validation failed: {validation_result['errors']}")
                    return
                
                if validation_result["warnings"]:
                    logger.warning(f"⚠️ Qube-Vital Data validation warnings: {validation_result['warnings']}")
                
                # Use validated and transformed data
                validated_data = validation_result["transformed_data"]
                logger.info(f"✅ Qube-Vital Data validation passed - Device: {attribute}")
                data_flow_emitter.emit_fhir_validation("Qube", "CM4_BLE_GW_TX", data, {"validated": True, "device_type": "Qube_Vital"})
                
            except Exception as e:
                logger.error(f"❌ Error in Qube-Vital FHIR validation: {e}")
                data_flow_emitter.emit_error("2.5_fhir_validation", "Qube", "CM4_BLE_GW_TX", data, f"Validation error: {str(e)}")
                return
            
            # Find patient by citizen ID
            patient = self.device_mapper.find_patient_by_citiz(citiz)
            
            # If patient not found, create unregistered patient
            if not patient:
                logger.info(f"Creating unregistered patient for citizen ID: {citiz}")
                patient = self.device_mapper.create_unregistered_patient(
                    citiz=citiz,
                    name_th=data.get('nameTH', ''),
                    name_en=data.get('nameEN', ''),
                    birth_date=data.get('brith', ''),
                    gender=data.get('gender', '')
                )
                
                if not patient:
                    logger.error(f"Failed to create unregistered patient for citizen ID: {citiz}")
                    return
            
            # Step 3: Patient Lookup
            patient_info = {
                "patient_id": str(patient['_id']),
                "patient_name": f"{patient.get('first_name', '')} {patient.get('last_name', '')}".strip(),
                "first_name": patient.get('first_name', ''),
                "last_name": patient.get('last_name', ''),
                "citiz": citiz
            }
            data_flow_emitter.emit_patient_lookup("Qube", "CM4_BLE_GW_TX", data, patient_info)
            
            logger.info(f"Processing {attribute} data for patient {patient['_id']}")
            
            # Process the medical data using validated data
            success = self.data_processor.process_qube_data(
                patient['_id'], 
                attribute, 
                validated_data.get('data', {}).get('value', value)
            )
            
            # Step 4: Patient Updated
            medical_data = {
                "attribute": attribute,
                "citiz": citiz,
                "processed": success,
                "validation_passed": True
            }
            data_flow_emitter.emit_patient_updated("Qube", "CM4_BLE_GW_TX", data, patient_info, medical_data)
            
            # Step 5: Medical Data Stored
            if success:
                logger.info(f"Successfully processed {attribute} data for patient {patient['_id']}")
                data_flow_emitter.emit_medical_stored("Qube", "CM4_BLE_GW_TX", data, patient_info, medical_data)
                
                # Step 6: FHIR R5 Resource Data Store (only for Patient resource data)
                try:
                    # Check if this is patient-related data that should be stored in FHIR R5
                    if self._should_store_in_fhir(attribute, validated_data):
                        fhir_success = self._process_fhir_r5_data(attribute, validated_data, patient_info)
                        if fhir_success:
                            # Determine the correct FHIR resource type
                            fhir_resource_type = self._determine_fhir_resource_type(attribute, validated_data)
                            fhir_data = {
                                "attribute": attribute,
                                "citiz": citiz,
                                "fhir_processed": True,
                                "resource_type": fhir_resource_type
                            }
                            data_flow_emitter.emit_fhir_r5_stored("Qube", "CM4_BLE_GW_TX", data, patient_info, fhir_data)
                            logger.info(f"✅ FHIR R5 data stored for patient {patient['_id']} - Resource: {fhir_resource_type}")
                        else:
                            logger.warning(f"⚠️ FHIR R5 processing failed for patient {patient['_id']}")
                            data_flow_emitter.emit_error("6_fhir_r5_stored", "Qube", "CM4_BLE_GW_TX", data, "FHIR R5 processing failed")
                    else:
                        logger.info(f"ℹ️ Skipping FHIR R5 storage for non-patient data: {attribute}")
                except Exception as e:
                    logger.error(f"❌ Error in FHIR R5 processing: {e}")
                    data_flow_emitter.emit_error("6_fhir_r5_stored", "Qube", "CM4_BLE_GW_TX", data, f"FHIR R5 error: {str(e)}")
            else:
                logger.error(f"Failed to process {attribute} data for patient {patient['_id']}")
                data_flow_emitter.emit_error("5_medical_stored", "Qube", "CM4_BLE_GW_TX", data, f"Failed to process {attribute} data")
                
        except Exception as e:
            logger.error(f"Error processing Qube-Vital medical data: {e}")
            data_flow_emitter.emit_error("3_patient_lookup", "Qube", "CM4_BLE_GW_TX", data, str(e))
    
    def _should_store_in_fhir(self, attribute: str, data: Dict[str, Any]) -> bool:
        """Check if the data should be stored in FHIR R5 (only for Patient resource data)"""
        # Only store patient-related data in FHIR R5
        patient_related_attributes = [
            "BP_BIOLIGTH",      # Blood pressure
            "Contour_Elite",    # Blood glucose
            "AccuChek_Instant", # Blood glucose
            "Oximeter JUMPER",  # SpO2
            "IR_TEMO_JUMPER",   # Temperature
            "BodyScale_JUMPER"  # Weight
        ]
        return attribute in patient_related_attributes
    
    def _process_fhir_r5_data(self, attribute: str, data: Dict[str, Any], patient_info: Dict[str, Any]) -> bool:
        """Process data for FHIR R5 storage"""
        try:
            # Import FHIR service
            from app.services.fhir_r5_service import fhir_service
            
            # Transform Qube-Vital data to FHIR R5
            observations = asyncio.run(fhir_service.transform_qube_mqtt_to_fhir(
                data, 
                patient_info["patient_id"], 
                f"Qube_{patient_info.get('citiz', 'unknown')}"
            ))
            
            # Store observations
            for observation in observations:
                asyncio.run(fhir_service.create_fhir_resource(
                    "Observation",
                    observation,
                    source_system="Qube_Vital_MQTT"
                ))
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing FHIR R5 data: {e}")
            return False
    
    def _determine_fhir_resource_type(self, attribute: str, data: Dict[str, Any]) -> str:
        """Determine the correct FHIR resource type for the data"""
        # All Qube-Vital medical data is stored as Observation resources
        return "Observation"
    
    async def run(self):
        """Run the MQTT listener"""
        logger.info("Starting Qube-Vital MQTT Listener Service")
        
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
            logger.info("Shutting down Qube-Vital MQTT Listener Service")
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
    listener = QubeMQTTListener()
    asyncio.run(listener.run()) 