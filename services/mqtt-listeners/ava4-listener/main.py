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
import requests

# Add shared utilities to path
sys.path.append('/app/shared')

from paho.mqtt import client as mqtt_client
from device_mapper import DeviceMapper
from data_processor import DataProcessor
from data_flow_emitter import data_flow_emitter
from fhir_validator import fhir_validator
from event_logger import EventLogger

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Debug logging for imports
logger.info(f"🔍 DEBUG: data_flow_emitter imported: {data_flow_emitter}")
logger.info(f"🔍 DEBUG: fhir_validator imported: {fhir_validator}")

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
        
        # Web Panel Configuration
        self.web_panel_url = os.getenv('WEB_PANEL_URL', 'http://web-panel:554')
        self.web_panel_timeout = int(os.getenv('WEB_PANEL_TIMEOUT', 5))
        
        # Initialize services
        self.device_mapper = DeviceMapper(self.mongodb_uri, self.mongodb_database)
        self.data_processor = DataProcessor(self.mongodb_uri, self.mongodb_database)
        
        # Initialize event logger
        self.event_logger = EventLogger(source_name='ava4-listener')
        
        # MQTT client
        self.client = None
        self.connected = False
        
    def post_event_to_web_panel(self, event_data: Dict[str, Any]) -> bool:
        """Post event to web panel's data flow emit endpoint"""
        try:
            url = f"{self.web_panel_url}/api/data-flow/emit"
            payload = {"event": event_data}
            
            response = requests.post(
                url,
                json=payload,
                timeout=self.web_panel_timeout,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                logger.info(f"✅ Event posted to web panel successfully: {event_data.get('step')} - {event_data.get('status')}")
                return True
            else:
                logger.warning(f"⚠️ Failed to post event to web panel: {response.status_code} - {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error posting event to web panel: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error posting event to web panel: {e}")
            return False
    
    def broadcast_medical_data_to_web_panel(self, medical_data: Dict[str, Any]) -> bool:
        """Broadcast medical data to web panel's Socket.IO system for real-time updates"""
        try:
            # Convert medical data to JSON serializable format
            def convert_for_json(obj):
                if isinstance(obj, dict):
                    return {k: convert_for_json(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [convert_for_json(item) for item in obj]
                elif hasattr(obj, 'isoformat'):
                    return obj.isoformat()
                elif hasattr(obj, '__str__'):
                    return str(obj)
                else:
                    return obj
            
            # Convert the medical data to ensure it's JSON serializable
            serializable_medical_data = convert_for_json(medical_data)
            
            url = f"{self.web_panel_url}/api/medical-data/broadcast"
            payload = {"medical_data": serializable_medical_data}
            
            response = requests.post(
                url,
                json=payload,
                timeout=self.web_panel_timeout,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                logger.info(f"✅ Medical data broadcasted to web panel successfully")
                return True
            else:
                logger.warning(f"⚠️ Failed to broadcast medical data to web panel: {response.status_code} - {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error broadcasting medical data to web panel: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error broadcasting medical data to web panel: {e}")
            return False
    
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
                # Try to decode as UTF-8, fallback to binary if it fails
                try:
                    payload = msg.payload.decode('utf-8')
                except UnicodeDecodeError:
                    # If UTF-8 fails, try to decode as binary and convert to hex
                    payload = msg.payload.hex()
                    logger.warning(f"⚠️ Non-UTF-8 message received on topic {msg.topic}, converted to hex")
                self.process_message(msg.topic, payload)
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
            # Post to web panel
            event_data_1 = {
                "step": "1_mqtt_received",
                "status": "success",
                "device_type": "AVA4",
                "topic": topic,
                "payload": {"raw_payload": payload},
                "timestamp": datetime.utcnow().isoformat()
            }
            self.post_event_to_web_panel(event_data_1)
            
            # Log data received event
            self.event_logger.log_data_received(
                device_id="AVA4",
                topic=topic,
                payload_size=len(payload),
                medical_data="AVA4 Medical Data"
            )
            
            # Parse JSON payload
            data = json.loads(payload)
            logger.info(f"Processing {topic} message: {data.get('type', 'unknown')}")
            
            # Step 2: Payload Parsed
            data_flow_emitter.emit_payload_parsed("AVA4", topic, data, {"parsed": True})
            # Post to web panel
            event_data_2 = {
                "step": "2_payload_parsed",
                "status": "success",
                "device_type": "AVA4",
                "topic": topic,
                "payload": data,
                "timestamp": datetime.utcnow().isoformat()
            }
            self.post_event_to_web_panel(event_data_2)
            
            # Log data processed event
            self.event_logger.log_data_processed(
                device_id="AVA4",
                topic=topic,
                processing_time=0.1,  # Approximate processing time
                medical_data="AVA4 Medical Data"
            )
            
            if topic == "ESP32_BLE_GW_TX":
                self.process_ava4_status(data)
            elif topic == "dusun_pub":
                self.process_ava4_medical_data(data)
            else:
                logger.warning(f"Unknown topic: {topic}")
                data_flow_emitter.emit_error("2_payload_parsed", "AVA4", topic, data, f"Unknown topic: {topic}")
                self.event_logger.log_error(
                    device_id="AVA4",
                    error_type="UNKNOWN_TOPIC",
                    error_message=f"Unknown topic: {topic}",
                    topic=topic
                )
                
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON payload: {e}")
            data_flow_emitter.emit_error("2_payload_parsed", "AVA4", topic, {"raw_payload": payload}, f"Invalid JSON: {e}")
            self.event_logger.log_error(
                device_id="AVA4",
                error_type="JSON_PARSE_ERROR",
                error_message=f"Invalid JSON: {e}",
                topic=topic
            )
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            data_flow_emitter.emit_error("1_mqtt_received", "AVA4", topic, {"raw_payload": payload}, str(e))
            self.event_logger.log_error(
                device_id="AVA4",
                error_type="PROCESSING_ERROR",
                error_message=str(e),
                topic=topic
            )
    
    def process_ava4_status(self, data: Dict[str, Any]):
        """Process AVA4 status messages (heartbeat, online trigger)"""
        try:
            msg_type = data.get('type')
            mac_address = data.get('mac')
            imei = data.get('IMEI')
            iccid = data.get('ICCID')
            timestamp = data.get('time')
            device_name = data.get('name')  # AVA4 device name from HB_Msg
            
            if not mac_address:
                logger.warning("No MAC address in AVA4 status message")
                return
            
            # Find patient by AVA4 MAC address
            patient = self.device_mapper.find_patient_by_ava4_mac(mac_address)
            patient_name = "Unknown"
            patient_id = None
            
            if patient:
                patient_name = f"{patient.get('first_name', '')} {patient.get('last_name', '')}".strip()
                patient_id = str(patient['_id'])
                logger.info(f"🏠 AVA4 GATEWAY STATUS - Gateway Owner: {patient['_id']} ({patient_name}) - Type: {msg_type}")
            else:
                logger.warning(f"No patient found for AVA4 MAC: {mac_address}")
            
            if msg_type == 'reportMsg':
                # First turn-on message (not for online status tracking)
                msg_data = data.get('data', {})
                status_msg = msg_data.get('msg', 'Unknown')
                if status_msg == 'Online':
                    logger.info(f"🔌 AVA4 FIRST TURN-ON - Device: {mac_address} ({patient_name}) - IMEI: {imei}")
                    status_doc = {
                        'ava4_mac': mac_address,
                        'ava4_name': device_name or f"AVA4-{mac_address[-6:]}",
                        'imei': imei,
                        'iccid': iccid,
                        'status': 'Unknown',  # Never set Online here
                        'first_turn_on': datetime.utcnow(),
                        'patient_id': patient_id,
                        'updated_at': datetime.utcnow()
                    }
                    try:
                        self.device_mapper.db.ava4_status.update_one(
                            {'ava4_mac': mac_address},
                            {'$set': status_doc},
                            upsert=True
                        )
                        logger.info(f"✅ AVA4 first turn-on recorded - Device: {mac_address}")
                    except Exception as e:
                        logger.error(f"❌ Failed to record AVA4 first turn-on: {e}")
                    data_flow_emitter.emit_device_status("AVA4", "ESP32_BLE_GW_TX", data, {
                        "device_id": mac_address,
                        "status": "First Turn-On",
                        "patient_name": patient_name,
                        "device_name": device_name
                    })
                else:
                    logger.info(f"📊 AVA4 Status Message - Device: {mac_address}, Message: {status_msg}")
            elif msg_type == 'HB_Msg':
                # Heartbeat message (every minute during operation)
                logger.info(f"💓 AVA4 HEARTBEAT - Device: {mac_address} ({patient_name}) - Name: {device_name} - IMEI: {imei}")
                try:
                    self.device_mapper.db.ava4_status.update_one(
                        {'ava4_mac': mac_address},
                        {
                            '$set': {
                                'ava4_name': device_name,  # Always update device name from heartbeat
                                'last_heartbeat': datetime.utcnow(),
                                'status': 'Online',
                                'updated_at': datetime.utcnow()
                            },
                            '$inc': {'heartbeat_count': 1}
                        },
                        upsert=True
                    )
                    logger.info(f"✅ AVA4 heartbeat updated - Device: {mac_address} ({device_name})")
                except Exception as e:
                    logger.error(f"❌ Failed to update AVA4 heartbeat: {e}")
                data_flow_emitter.emit_device_status("AVA4", "ESP32_BLE_GW_TX", data, {
                    "device_id": mac_address,
                    "status": "Online",
                    "patient_name": patient_name,
                    "device_name": device_name,
                    "type": "heartbeat"
                })
            else:
                logger.info(f"📊 AVA4 Status Message - Type: {msg_type}, Device: {mac_address}")
            status_data = {
                "device_id": mac_address,
                "type": msg_type,
                "mac": mac_address,
                "name": device_name,
                "imei": imei,
                "iccid": iccid,
                "timestamp": datetime.utcnow(),
                "data": data.get('data', {}),
                "patient_id": patient_id,
                "patient_name": patient_name
            }
            
            # Store in device_status collection for historical tracking
            try:
                # Use update_one with upsert=True to avoid duplicate key errors
                self.device_mapper.db.device_status.update_one(
                    {'device_id': mac_address},
                    {'$set': status_data},
                    upsert=True
                )
                logger.debug(f"📊 Device status stored for AVA4: {mac_address}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to store device status: {e}")
        except Exception as e:
            logger.error(f"Error processing AVA4 status: {e}")
            data_flow_emitter.emit_error("3_device_status", "AVA4", "ESP32_BLE_GW_TX", data, str(e))

    # Pass device_name to medical data processor for Recent Medical Data table
    def process_ava4_medical_data(self, data: Dict[str, Any]):
        """Process AVA4 medical data messages"""
        try:
            logger.info(f"🔍 DEBUG: Starting process_ava4_medical_data with data: {data}")
            logger.info(f"🔍 DEBUG: data_flow_emitter: {data_flow_emitter}")
            
            # Handle both old and new payload formats
            msg_type = data.get('type')
            logger.info(f"🔍 DEBUG: msg_type: {msg_type}")
            
            # Check if this is the new BLE format
            if data.get('from') == 'BLE' and data.get('to') == 'CLOUD':
                logger.info(f"🔍 Processing new BLE format AVA4 data")
                ava4_mac = data.get('mac')  # AVA4 device MAC
                device_code = data.get('deviceCode')
                device_type = data.get('device')  # Device description
                data_section = data.get('data', {})
                attribute = data_section.get('attribute')
                value = data_section.get('value', {})
                timestamp = data.get('time')
            else:
                # Handle old format
                logger.info(f"🔍 Processing legacy AVA4 format")
                ava4_mac = data.get('mac')  # AVA4 device MAC
                device_code = data.get('deviceCode')
                data_section = data.get('data', {})
                attribute = data_section.get('attribute')
                value = data_section.get('value', {})
                device_type = None
                timestamp = None
            
            logger.info(f"🔍 DEBUG: Extracted fields:")
            logger.info(f"🔍 DEBUG: msg_type: {msg_type}")
            logger.info(f"🔍 DEBUG: ava4_mac: {ava4_mac}")
            logger.info(f"🔍 DEBUG: device_code: {device_code}")
            logger.info(f"🔍 DEBUG: device_type: {device_type}")
            logger.info(f"🔍 DEBUG: data_section: {data_section}")
            logger.info(f"🔍 DEBUG: attribute: {attribute}")
            logger.info(f"🔍 DEBUG: value: {value}")
            logger.info(f"🔍 DEBUG: timestamp: {timestamp}")
            
            # Handle both reportAttribute and cmdResult message types
            if msg_type not in ["reportAttribute", "cmdResult"]:
                logger.info(f"Non-medical message type: {msg_type}")
                return
            
            if not ava4_mac:
                logger.warning(f"❌ Missing AVA4 MAC in medical data. Available keys: {list(data.keys())}")
                logger.warning(f"❌ Data structure: {data}")
                return
            
            # Check if this is a status message (only contains id and code)
            if data_section and len(data_section) == 2 and 'id' in data_section and 'code' in data_section:
                logger.info(f"📊 Status message received - ID: {data_section.get('id')}, Code: {data_section.get('code')}")
                # This is a status message, not medical data - skip processing
                return
                
            if not attribute:
                logger.warning(f"❌ Missing attribute in medical data. Data section: {data_section}")
                logger.warning(f"❌ Available keys in data section: {list(data_section.keys())}")
                return
            
            logger.info(f"💊 Processing AVA4 medical data - Type: {msg_type}, Attribute: {attribute}, Device: {device_type}")
            
            # Step 2.5: FHIR Data Format Validation (NEW)
            validated_data = None
            try:
                validation_result = fhir_validator.validate_ava4_data_format(data, "dusun_pub")
                
                if not validation_result["valid"]:
                    logger.warning(f"⚠️ AVA4 Data validation failed: {validation_result['errors']}")
                    if validation_result["warnings"]:
                        logger.warning(f"⚠️ AVA4 Data validation warnings: {validation_result['warnings']}")
                    data_flow_emitter.emit_error("2.5_fhir_validation", "AVA4", "dusun_pub", data, f"Validation failed: {validation_result['errors']}")
                    # Continue processing even if validation fails for debugging purposes
                    validated_data = None
                else:
                    if validation_result["warnings"]:
                        logger.warning(f"⚠️ AVA4 Data validation warnings: {validation_result['warnings']}")
                    
                    # Use validated and transformed data
                    validated_data = validation_result["transformed_data"]
                    logger.info(f"✅ AVA4 Data validation passed - Device: {attribute}")
                    data_flow_emitter.emit_fhir_validation("AVA4", "dusun_pub", data, {"validated": True, "device_type": "AVA4"})
                
            except Exception as e:
                logger.error(f"❌ Error in AVA4 FHIR validation: {e}")
                data_flow_emitter.emit_error("2.5_fhir_validation", "AVA4", "dusun_pub", data, f"Validation error: {str(e)}")
                # Continue processing even if validation fails for debugging purposes
                validated_data = None
            
            # Extract sub-device BLE MAC from device_list
            sub_device_mac = None
            medical_data = None
            logger.info(f"🔍 DEBUG: Processing medical data - attribute: {attribute}, value keys: {list(value.keys())}")
            if value and 'device_list' in value and len(value['device_list']) > 0:
                sub_device_mac = value['device_list'][0].get('ble_addr')
                medical_data = value['device_list'][0]  # Get the actual medical data
                logger.info(f"📱 Sub-device BLE MAC: {sub_device_mac}")
                logger.info(f"💊 Medical data: {medical_data}")
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
                # Map attribute to device type - Updated with all device types
                device_type_mapping = {
                    "BP_BIOLIGTH": "blood_pressure",
                    "WBP BIOLIGHT": "blood_pressure",  # Added this variant
                    "BLE_BPG": "blood_pressure",
                    "Contour_Elite": "blood_sugar",
                    "AccuChek_Instant": "blood_sugar",
                    "Oximeter JUMPER": "spo2",
                    "IR_TEMO_JUMPER": "body_temp",
                    "BodyScale_JUMPER": "weight",
                    "MGSS_REF_UA": "uric_acid",
                    "MGSS_REF_CHOL": "cholesterol"
                }
                
                mapped_device_type = device_type_mapping.get(attribute)
                if mapped_device_type:
                    logger.info(f"📱 Looking for device type: {mapped_device_type}")
                    patient = self.device_mapper.find_patient_by_device_mac(sub_device_mac, mapped_device_type)
                    if patient:
                        device_patient_name = f"{patient.get('first_name', '')} {patient.get('last_name', '')}".strip()
                        logger.info(f"📱 MEDICAL DEVICE OWNER (patient fields): {patient['_id']} ({device_patient_name}) - Device: {sub_device_mac} - Type: {mapped_device_type}")
                    else:
                        logger.warning(f"📱 No patient found for device {sub_device_mac} with type {mapped_device_type} in patient fields")
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
                
                # Create fallback patient info for medical data display
                patient_info = {
                    "patient_id": "unknown",
                    "patient_name": f"Unknown Patient ({sub_device_mac})",
                    "first_name": "Unknown",
                    "last_name": "Patient"
                }
                logger.info(f"📱 Using fallback patient info for medical data display")
            
            patient_name = patient_info["patient_name"]
            logger.info(f"💊 PROCESSING MEDICAL DATA - Device Owner: {patient_info['patient_id']} ({patient_name}) - Device: {attribute} - BLE: {sub_device_mac}")
            
            success = False
            
            # Get the latest AVA4 device name from status collection
            ava4_status = self.device_mapper.db.ava4_status.find_one({'ava4_mac': ava4_mac})
            latest_device_name = None
            if ava4_status:
                latest_device_name = ava4_status.get('ava4_name')
                logger.info(f"📱 Found AVA4 device name from status: {latest_device_name}")
            else:
                logger.warning(f"📱 No AVA4 status found for MAC: {ava4_mac}")
            
            # Use validated data if available, fallback to original value
            data_to_process = value
            if validated_data and isinstance(validated_data, dict):
                data_to_process = validated_data.get('data', {}).get('value', value)
            
            if patient:
                success = self.data_processor.process_ava4_data(
                    patient['_id'], 
                    ava4_mac,  # AVA4 gateway MAC
                    attribute, 
                    data_to_process,  # Use safely extracted data
                    sub_device_mac,
                    latest_device_name  # Pass the latest device name from status collection
                )
            else:
                logger.info(f"📱 Patient not found, but storing data in database for display purposes")
                # Store data in database even when patient mapping fails for display purposes
                success = self.data_processor.process_ava4_data(
                    "unknown",  # Use "unknown" as patient ID
                    ava4_mac,  # AVA4 gateway MAC
                    attribute, 
                    data_to_process,  # Use safely extracted data
                    sub_device_mac,
                    latest_device_name  # Pass the latest device name from status collection
                )
            
            # Create medical data event for data flow emitter
            medical_data_event = {
                "attribute": attribute,
                "device_type": device_type,
                "sub_device_mac": sub_device_mac,
                "medical_data": medical_data,
                "ava4_mac": ava4_mac,
                "device_code": device_code
            }
            
            logger.info(f"🔍 DEBUG: medical_data_event created: {medical_data_event}")
            
            # Step 4: Patient Updated
            logger.info(f"🔍 DEBUG: About to emit patient_updated with patient_info: {patient_info}, medical_data_event: {medical_data_event}")
            try:
                logger.info(f"🔍 DEBUG: Calling emit_patient_updated...")
                data_flow_emitter.emit_patient_updated("AVA4", "dusun_pub", data, patient_info, medical_data_event)
                logger.info(f"🔍 DEBUG: emit_patient_updated completed successfully")
            except Exception as e:
                logger.error(f"❌ Exception in emit_patient_updated: {e}")
                logger.error(f"❌ patient_info: {patient_info}")
                logger.error(f"❌ medical_data_event: {medical_data_event}")
                raise

            # Step 5: Medical Data Stored
            if success:
                logger.info(f"Successfully processed {attribute} data for patient {patient_info['patient_id']} ({patient_name})")
                logger.info(f"🔍 DEBUG: About to emit medical_stored")
                try:
                    logger.info(f"🔍 DEBUG: Calling emit_medical_stored...")
                    data_flow_emitter.emit_medical_stored("AVA4", "dusun_pub", data, patient_info, medical_data_event)
                    logger.info(f"🔍 DEBUG: emit_medical_stored completed successfully")
                except Exception as e:
                    logger.error(f"❌ Exception in emit_medical_stored: {e}")
                    logger.error(f"❌ patient_info: {patient_info}")
                    logger.error(f"❌ medical_data_event: {medical_data_event}")
                    raise
                
                # Step 6: Post medical data to web panel for medical monitor display
                if medical_data and isinstance(medical_data, dict):
                    try:
                        logger.info(f"🔍 DEBUG: About to create flattened payload")
                        # Create medical data event for web panel
                        # Flatten the medical data structure for better display
                        flattened_payload = {
                            "ble_addr": medical_data.get("ble_addr"),
                            "scan_time": medical_data.get("scan_time"),
                            "device_type": attribute,
                            "ava4_mac": ava4_mac,
                            "sub_device_mac": sub_device_mac,
                            # Blood pressure data
                            "bp_high": medical_data.get("bp_high"),
                            "bp_low": medical_data.get("bp_low"),
                            "PR": medical_data.get("PR"),  # Pulse Rate
                            # Blood glucose data
                            "blood_glucose": medical_data.get("blood_glucose"),
                            "marker": medical_data.get("marker"),
                            "scan_rssi": medical_data.get("scan_rssi"),
                            # SpO2 data
                            "spo2": medical_data.get("spo2"),
                            "pulse": medical_data.get("pulse"),
                            "pi": medical_data.get("pi"),
                            # Temperature data
                            "temp": medical_data.get("temp"),
                            "mode": medical_data.get("mode"),
                            # Weight data
                            "weight": medical_data.get("weight"),
                            "resistance": medical_data.get("resistance"),
                            # Uric acid data
                            "uric_acid": medical_data.get("uric_acid"),
                            # Cholesterol data
                            "cholesterol": medical_data.get("cholesterol"),
                            # Also include the original nested structure for compatibility
                            "data": {
                                "attribute": attribute,
                                "mac": ava4_mac,
                                "value": {
                                    "device_list": [medical_data]
                                }
                            }
                        }
                        
                        logger.info(f"🔍 DEBUG: About to create medical event")
                        medical_event = {
                            "step": "5_medical_stored",
                            "status": "success",
                            "device_type": "AVA4",
                            "source": "AVA4",
                            "topic": "dusun_pub",
                            "device_id": ava4_mac,
                            "patient_id": patient_info['patient_id'],
                            "patient_name": patient_name,
                            "details": {
                                "payload": flattened_payload,  # Use flattened medical data
                                "attribute": attribute,
                                "device_type": device_type,
                                "sub_device_mac": sub_device_mac,
                                "device_code": device_code
                            },
                            "timestamp": datetime.utcnow().isoformat()
                        }
                        
                        logger.info(f"🔍 DEBUG: About to post to web panel")
                        # Post to web panel
                        self.post_event_to_web_panel(medical_event)
                        logger.info(f"✅ Medical data posted to web panel for patient {patient_name}")
                        
                        # Broadcast medical data to Socket.IO clients for real-time updates
                        try:
                            # Create medical data for broadcast
                            broadcast_data = {
                                "device_id": ava4_mac,
                                "patient_id": patient_info['patient_id'],
                                "patient_name": patient_name,
                                "source": "AVA4",
                                "timestamp": datetime.utcnow().isoformat(),
                                "medical_values": {
                                    "device_type": attribute,
                                    "sub_device_mac": sub_device_mac,
                                    "ava4_device_name": latest_device_name,
                                    # Blood pressure
                                    "systolic": flattened_payload.get('bp_high'),
                                    "diastolic": flattened_payload.get('bp_low'),
                                    "pulse_rate": flattened_payload.get('PR'),
                                    # Blood glucose
                                    "blood_glucose": flattened_payload.get('blood_glucose'),
                                    "marker": flattened_payload.get('marker'),
                                    # SpO2
                                    "spO2": flattened_payload.get('spo2'),
                                    "pulse": flattened_payload.get('pulse'),
                                    "pi": flattened_payload.get('pi'),
                                    # Temperature
                                    "temperature": flattened_payload.get('temp'),
                                    "mode": flattened_payload.get('mode'),
                                    # Weight
                                    "weight": flattened_payload.get('weight'),
                                    "resistance": flattened_payload.get('resistance'),
                                    # Uric acid
                                    "uric_acid": flattened_payload.get('uric_acid'),
                                    # Cholesterol
                                    "cholesterol": flattened_payload.get('cholesterol')
                                },
                                "raw_data": flattened_payload
                            }
                            
                            self.broadcast_medical_data_to_web_panel(broadcast_data)
                            logger.info(f"📡 Medical data broadcasted to Socket.IO clients for patient {patient_name}")
                        except Exception as e:
                            logger.warning(f"⚠️ Failed to broadcast medical data to Socket.IO: {e}")
                        
                        # Log appropriate medical data based on device type
                        if attribute in ["BLE_BPG", "BP_BIOLIGTH", "WBP BIOLIGHT"]:
                            logger.info(f"💊 Blood Pressure: {flattened_payload.get('bp_high')}/{flattened_payload.get('bp_low')} mmHg, PR: {flattened_payload.get('PR')} bpm")
                        elif attribute in ["Contour_Elite", "AccuChek_Instant"]:
                            logger.info(f"🩸 Blood Glucose: {flattened_payload.get('blood_glucose')} mg/dL, Marker: {flattened_payload.get('marker')}")
                        elif attribute == "Oximeter JUMPER":
                            logger.info(f"🫁 SpO2: {flattened_payload.get('spo2')}%, Pulse: {flattened_payload.get('pulse')} bpm, PI: {flattened_payload.get('pi')}")
                        elif attribute == "IR_TEMO_JUMPER":
                            logger.info(f"🌡️ Temperature: {flattened_payload.get('temp')}°C, Mode: {flattened_payload.get('mode')}")
                        elif attribute == "BodyScale_JUMPER":
                            logger.info(f"⚖️ Weight: {flattened_payload.get('weight')} kg, Resistance: {flattened_payload.get('resistance')}")
                        elif attribute == "MGSS_REF_UA":
                            logger.info(f"🧪 Uric Acid: {flattened_payload.get('uric_acid')} μmol/L")
                        elif attribute == "MGSS_REF_CHOL":
                            logger.info(f"🩸 Cholesterol: {flattened_payload.get('cholesterol')} mmol/L")
                        else:
                            logger.info(f"📊 Medical Data: {medical_data}")
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to post medical data to web panel: {e}")
                        logger.info(f"📊 Medical data processed but web panel posting failed - Device: {attribute}, Patient: {patient_name}")
                else:
                    logger.warning(f"⚠️ No valid medical data to post to web panel - medical_data: {medical_data}")
                
                # Step 7: FHIR R5 Resource Data Store (disabled in MQTT listener)
                # Note: FHIR R5 processing is handled by the main API service
                # The MQTT listener focuses on real-time data processing and storage
                if patient:
                    logger.info(f"ℹ️ FHIR R5 processing skipped - handled by main API service for patient {patient['_id']} ({patient_name})")
                else:
                    logger.info(f"ℹ️ FHIR R5 processing skipped - patient not found for device {sub_device_mac}")
            else:
                logger.error(f"Failed to process {attribute} data for patient {patient_info['patient_id']} ({patient_name})")
                data_flow_emitter.emit_error("5_medical_stored", "AVA4", "dusun_pub", data, f"Failed to process {attribute} data")
                
        except Exception as e:
            logger.error(f"Error processing AVA4 medical data: {e}")
            data_flow_emitter.emit_error("3_patient_lookup", "AVA4", "dusun_pub", data, str(e))
    
    # FHIR R5 processing methods removed - handled by main API service
    
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