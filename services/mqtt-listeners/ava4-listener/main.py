#!/usr/bin/env python3
"""
AVA4 MQTT Listener Service
Handles MQTT messages from AVA4 devices and sub-devices
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

class AVA4MQTTListener:
    """AVA4 MQTT Listener Service"""
    
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
        self.topics = os.getenv('MQTT_TOPICS', 'ESP32_BLE_GW_TX,dusun_pub').split(',')
        
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
            data_flow_emitter.emit_mqtt_received("AVA4", topic, {"raw_payload": payload})
            
            # Parse JSON payload
            data = json.loads(payload)
            logger.info(f"Processing {topic} message: {data.get('type', 'unknown')}")
            
            # Step 2: Payload Parsed
            data_flow_emitter.emit_payload_parsed("AVA4", topic, data, {"parsed": True})
            
            if topic == "ESP32_BLE_GW_TX":
                self.process_ava4_status(data)
            elif topic == "dusun_pub":
                self.process_ava4_medical_data(data)
            else:
                logger.warning(f"Unknown topic: {topic}")
                data_flow_emitter.emit_error("2_payload_parsed", "AVA4", topic, data, f"Unknown topic: {topic}")
                
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON payload: {e}")
            data_flow_emitter.emit_error("2_payload_parsed", "AVA4", topic, {"raw_payload": payload}, f"Invalid JSON: {e}")
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            data_flow_emitter.emit_error("1_mqtt_received", "AVA4", topic, {"raw_payload": payload}, str(e))
    
    def process_ava4_status(self, data: Dict[str, Any]):
        """Process AVA4 status messages (heartbeat, online trigger)"""
        try:
            msg_type = data.get('type')
            mac_address = data.get('mac')
            imei = data.get('IMEI')
            
            if not mac_address:
                logger.warning("No MAC address in AVA4 status message")
                return
            
            # Find patient by AVA4 MAC address
            patient = self.device_mapper.find_patient_by_ava4_mac(mac_address)
            if not patient:
                logger.warning(f"No patient found for AVA4 MAC: {mac_address}")
                return
            
            patient_name = f"{patient.get('first_name', '')} {patient.get('last_name', '')}".strip()
            logger.info(f"🏠 AVA4 GATEWAY STATUS - Gateway Owner: {patient['_id']} ({patient_name}) - Type: {msg_type}")
            
            # Store device status (optional - for monitoring)
            status_data = {
                "type": msg_type,
                "mac": mac_address,
                "imei": imei,
                "timestamp": datetime.utcnow(),
                "data": data.get('data', {})
            }
            
            # You could store this in a device_status collection if needed
            # self.db.device_status.insert_one(status_data)
            
        except Exception as e:
            logger.error(f"Error processing AVA4 status: {e}")
    
    def process_ava4_medical_data(self, data: Dict[str, Any]):
        """Process AVA4 medical device data"""
        try:
            msg_type = data.get('type')
            ava4_mac = data.get('mac')  # AVA4 device MAC
            device_code = data.get('deviceCode')
            attribute = data.get('data', {}).get('attribute')
            value = data.get('data', {}).get('value', {})
            
            if msg_type != "reportAttribute":
                logger.info(f"Non-medical message type: {msg_type}")
                return
            
            if not ava4_mac or not attribute:
                logger.warning("Missing AVA4 MAC or attribute in medical data")
                return
            
            # Step 2.5: FHIR Data Format Validation (NEW)
            try:
                validation_result = fhir_validator.validate_ava4_data_format(data, "dusun_pub")
                
                if not validation_result["valid"]:
                    logger.error(f"❌ AVA4 Data validation failed: {validation_result['errors']}")
                    if validation_result["warnings"]:
                        logger.warning(f"⚠️ AVA4 Data validation warnings: {validation_result['warnings']}")
                    data_flow_emitter.emit_error("2.5_fhir_validation", "AVA4", "dusun_pub", data, f"Validation failed: {validation_result['errors']}")
                    return
                
                if validation_result["warnings"]:
                    logger.warning(f"⚠️ AVA4 Data validation warnings: {validation_result['warnings']}")
                
                # Use validated and transformed data
                validated_data = validation_result["transformed_data"]
                logger.info(f"✅ AVA4 Data validation passed - Device: {attribute}")
                data_flow_emitter.emit_fhir_validation("AVA4", "dusun_pub", data, {"validated": True, "device_type": "AVA4"})
                
            except Exception as e:
                logger.error(f"❌ Error in AVA4 FHIR validation: {e}")
                data_flow_emitter.emit_error("2.5_fhir_validation", "AVA4", "dusun_pub", data, f"Validation error: {str(e)}")
                return
            
            # Extract sub-device BLE MAC from device_list
            sub_device_mac = None
            logger.info(f"🔍 DEBUG: Processing medical data - attribute: {attribute}, value keys: {list(value.keys()) if value else 'None'}")
            if value and 'device_list' in value and len(value['device_list']) > 0:
                sub_device_mac = value['device_list'][0].get('ble_addr')
                logger.info(f"📱 Sub-device BLE MAC: {sub_device_mac}")
            else:
                logger.warning(f"📱 No device_list found in value: {value}")
            
            # Try to find patient by multiple methods
            patient = None
            logger.info(f"🔍 DEBUG: Starting patient mapping for BLE: {sub_device_mac}")
            
            # Method 1: Try to find by AVA4 MAC (main device) - for logging only
            logger.debug(f"🔍 Method 1: Looking for patient by AVA4 MAC: {ava4_mac}")
            ava4_gateway_patient = self.device_mapper.find_patient_by_ava4_mac(ava4_mac)
            if ava4_gateway_patient:
                ava4_gateway_name = f"{ava4_gateway_patient.get('first_name', '')} {ava4_gateway_patient.get('last_name', '')}".strip()
                logger.info(f"🏠 AVA4 GATEWAY OWNER: {ava4_gateway_patient['_id']} ({ava4_gateway_name})")
            
            # Method 2: Try by sub-device BLE MAC in amy_devices (PRIORITY)
            if sub_device_mac:
                logger.info(f"🔍 Method 2: Looking for patient by sub-device BLE MAC: {sub_device_mac}")
                device_info = self.device_mapper.get_device_info(sub_device_mac)
                if device_info:
                    logger.info(f"📱 Found device in amy_devices: {device_info}")
                    if device_info.get('patient_id'):
                        patient = self.device_mapper.db.patients.find_one({"_id": device_info['patient_id']})
                        if patient:
                            device_patient_name = f"{patient.get('first_name', '')} {patient.get('last_name', '')}".strip()
                            logger.info(f"📱 MEDICAL DEVICE OWNER (amy_devices): {patient['_id']} ({device_patient_name}) - Device: {sub_device_mac}")
                        else:
                            logger.warning(f"📱 Patient not found for device {sub_device_mac} with patient_id: {device_info['patient_id']}")
                    else:
                        logger.warning(f"📱 Device {sub_device_mac} found in amy_devices but no patient_id")
                else:
                    logger.warning(f"📱 Device {sub_device_mac} not found in amy_devices collection")
            
            # Method 3: If not found, try by sub-device BLE MAC in patient device fields
            if not patient and sub_device_mac:
                logger.info(f"🔍 Method 3: Looking for patient by sub-device BLE MAC in patient fields: {sub_device_mac}")
                # Map attribute to device type
                device_type_mapping = {
                    "BP_BIOLIGTH": "blood_pressure",
                    "Contour_Elite": "blood_sugar",
                    "AccuChek_Instant": "blood_sugar",
                    "Oximeter JUMPER": "spo2",
                    "IR_TEMO_JUMPER": "body_temp",
                    "BodyScale_JUMPER": "weight",
                    "MGSS_REF_UA": "uric",
                    "MGSS_REF_CHOL": "cholesterol"
                }
                
                device_type = device_type_mapping.get(attribute)
                if device_type:
                    logger.info(f"📱 Looking for device type: {device_type}")
                    patient = self.device_mapper.find_patient_by_device_mac(sub_device_mac, device_type)
                    if patient:
                        device_patient_name = f"{patient.get('first_name', '')} {patient.get('last_name', '')}".strip()
                        logger.info(f"📱 MEDICAL DEVICE OWNER (patient fields): {patient['_id']} ({device_patient_name}) - Device: {sub_device_mac} - Type: {device_type}")
                    else:
                        logger.warning(f"📱 No patient found for device {sub_device_mac} with type {device_type} in patient fields")
                else:
                    logger.warning(f"📱 Unknown device type for attribute: {attribute}")
            
            # Method 4: Fallback to AVA4 gateway owner if no medical device owner found
            if not patient and ava4_gateway_patient:
                logger.info(f"📱 FALLBACK: Using AVA4 gateway owner as medical device owner")
                patient = ava4_gateway_patient
            
            # Step 3: Patient Lookup
            patient_info = None
            if patient:
                patient_info = {
                    "patient_id": str(patient['_id']),
                    "patient_name": f"{patient.get('first_name', '')} {patient.get('last_name', '')}".strip(),
                    "first_name": patient.get('first_name', ''),
                    "last_name": patient.get('last_name', '')
                }
                data_flow_emitter.emit_patient_lookup("AVA4", "dusun_pub", data, patient_info)
            else:
                error_msg = f"No patient found for AVA4 MAC: {ava4_mac}, sub-device MAC: {sub_device_mac}, attribute: {attribute}"
                logger.warning(error_msg)
                data_flow_emitter.emit_patient_lookup("AVA4", "dusun_pub", data, None, error_msg)
                return
            
            patient_name = f"{patient.get('first_name', '')} {patient.get('last_name', '')}".strip()
            logger.info(f"💊 PROCESSING MEDICAL DATA - Device Owner: {patient['_id']} ({patient_name}) - Device: {attribute} - BLE: {sub_device_mac}")
            
            # Process the medical data using validated data
            success = self.data_processor.process_ava4_data(
                patient['_id'], 
                ava4_mac,  # AVA4 gateway MAC
                attribute, 
                validated_data.get('data', {}).get('value', value),  # Use validated data
                sub_device_mac  # Sub-device BLE address
            )
            
            # Step 4: Patient Updated
            medical_data = {
                "attribute": attribute,
                "device_code": device_code,
                "sub_device_mac": sub_device_mac,
                "processed": success,
                "validation_passed": True
            }
            data_flow_emitter.emit_patient_updated("AVA4", "dusun_pub", data, patient_info, medical_data)
            
            # Step 5: Medical Data Stored
            if success:
                logger.info(f"Successfully processed {attribute} data for patient {patient['_id']} ({patient_name})")
                data_flow_emitter.emit_medical_stored("AVA4", "dusun_pub", data, patient_info, medical_data)
                
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
                                "device_code": device_code,
                                "fhir_processed": True,
                                "resource_type": fhir_resource_type
                            }
                            data_flow_emitter.emit_fhir_r5_stored("AVA4", "dusun_pub", data, patient_info, fhir_data)
                            logger.info(f"✅ FHIR R5 data stored for patient {patient['_id']} ({patient_name}) - Resource: {fhir_resource_type}")
                        else:
                            logger.warning(f"⚠️ FHIR R5 processing failed for patient {patient['_id']} ({patient_name})")
                            data_flow_emitter.emit_error("6_fhir_r5_stored", "AVA4", "dusun_pub", data, "FHIR R5 processing failed")
                    else:
                        logger.info(f"ℹ️ Skipping FHIR R5 storage for non-patient data: {attribute}")
                except Exception as e:
                    logger.error(f"❌ Error in FHIR R5 processing: {e}")
                    data_flow_emitter.emit_error("6_fhir_r5_stored", "AVA4", "dusun_pub", data, f"FHIR R5 error: {str(e)}")
            else:
                logger.error(f"Failed to process {attribute} data for patient {patient['_id']} ({patient_name})")
                data_flow_emitter.emit_error("5_medical_stored", "AVA4", "dusun_pub", data, f"Failed to process {attribute} data")
                
        except Exception as e:
            logger.error(f"Error processing AVA4 medical data: {e}")
            data_flow_emitter.emit_error("3_patient_lookup", "AVA4", "dusun_pub", data, str(e))
    
    def _should_store_in_fhir(self, attribute: str, data: Dict[str, Any]) -> bool:
        """Check if the data should be stored in FHIR R5 (only for Patient resource data)"""
        # Only store patient-related data in FHIR R5
        patient_related_attributes = [
            "BP_BIOLIGTH",      # Blood pressure
            "Contour_Elite",    # Blood glucose
            "AccuChek_Instant", # Blood glucose
            "Oximeter JUMPER",  # SpO2
            "IR_TEMO_JUMPER",   # Temperature
            "BodyScale_JUMPER", # Weight
            "MGSS_REF_UA",      # Uric acid
            "MGSS_REF_CHOL"     # Cholesterol
        ]
        return attribute in patient_related_attributes
    
    def _process_fhir_r5_data(self, attribute: str, data: Dict[str, Any], patient_info: Dict[str, Any]) -> bool:
        """Process data for FHIR R5 storage"""
        try:
            # Import FHIR service
            from app.services.fhir_r5_service import fhir_service
            
            # Transform AVA4 data to FHIR R5
            observations = asyncio.run(fhir_service.transform_ava4_mqtt_to_fhir(
                data, 
                patient_info["patient_id"], 
                f"AVA4_{data.get('mac', 'unknown')}"
            ))
            
            # Store observations
            for observation in observations:
                asyncio.run(fhir_service.create_fhir_resource(
                    "Observation",
                    observation,
                    source_system="AVA4_MQTT"
                ))
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing FHIR R5 data: {e}")
            return False
    
    def _determine_fhir_resource_type(self, attribute: str, data: Dict[str, Any]) -> str:
        """Determine the correct FHIR resource type for the data"""
        # All AVA4 medical data is stored as Observation resources
        return "Observation"
    
    async def run(self):
        """Run the MQTT listener"""
        logger.info("Starting AVA4 MQTT Listener Service")
        
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
            logger.info("Shutting down AVA4 MQTT Listener Service")
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
    listener = AVA4MQTTListener()
    asyncio.run(listener.run()) 