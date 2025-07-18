#!/usr/bin/env python3
"""
Kati Watch MQTT Listener Service
Handles MQTT messages from Kati Watch devices
Updated to handle all Kati Watch payload formats:
- iMEDE_watch/onlineTrigger (online/offline status)
- iMEDE_watch/hb (heartbeat with step, battery, signal)
- iMEDE_watch/VitalSign (vital signs with new format)
- iMEDE_watch/AP55 (batch vital signs)
- iMEDE_watch/location (GPS, WiFi, LBS location)
- iMEDE_watch/sleepdata (sleep tracking data)
- iMEDE_watch/sos (SOS emergency)
- iMEDE_watch/fallDown (fall detection)
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
        
        self.web_panel_url = os.getenv('WEB_PANEL_URL', 'http://mqtt-panel:8098')
        self.web_panel_timeout = int(os.getenv('WEB_PANEL_TIMEOUT', 30))
        
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
            data_flow_emitter.emit_mqtt_received("Kati", topic, {"raw_payload": payload})
            event_data_1 = {
                "step": "1_mqtt_received",
                "status": "success",
                "device_type": "Kati",
                "topic": topic,
                "payload": {"raw_payload": payload},
                "timestamp": datetime.utcnow().isoformat()
            }
            self.post_event_to_web_panel(event_data_1)
            
            # Parse JSON payload
            data = json.loads(payload)
            logger.info(f"Processing {topic} message")
            
            # Step 2: Payload Parsed
            data_flow_emitter.emit_payload_parsed("Kati", topic, data, {"parsed": True})
            event_data_2 = {
                "step": "2_payload_parsed",
                "status": "success",
                "device_type": "Kati",
                "topic": topic,
                "payload": data,
                "timestamp": datetime.utcnow().isoformat()
            }
            self.post_event_to_web_panel(event_data_2)
            
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
            patient_name = "Unknown Device"
            patient_id = None
            
            if patient:
                patient_info = {
                    "patient_id": str(patient['_id']),
                    "patient_name": f"{patient.get('first_name', '')} {patient.get('last_name', '')}".strip(),
                    "first_name": patient.get('first_name', ''),
                    "last_name": patient.get('last_name', '')
                }
                patient_name = patient_info["patient_name"]
                patient_id = patient['_id']
                data_flow_emitter.emit_patient_lookup("Kati", topic, data, patient_info)
                logger.info(f"⌚ Processing {topic} data for patient {patient['_id']} ({patient_name})")
            else:
                error_msg = f"No patient found for Kati IMEI: {imei}"
                logger.warning(error_msg)
                data_flow_emitter.emit_patient_lookup("Kati", topic, data, None, error_msg)
                logger.info(f"⌚ Processing {topic} data for unmapped device IMEI: {imei}")
            
            logger.info(f"📱 Kati IMEI: {imei}")
            logger.info(f"📊 Raw payload keys: {list(data.keys())}")
            
            # Step 6: FHIR R5 Resource Data Store (only for mapped patients)
            if patient_info:  # Only store in FHIR if patient is mapped
                try:
                    # Check if this is patient-related data that should be stored in FHIR R5
                    if self._should_store_in_fhir(topic, data):  # Use original data, not validated_data
                        logger.info(f"💾 Storing {topic} data in FHIR R5 for patient {patient_info.get('patient_id')}")
                        
                        # Process FHIR R5 data
                        fhir_success = self._process_fhir_r5_data(topic, data, patient_info)
                        
                        if fhir_success:
                            data_flow_emitter.emit_fhir_storage("Kati", topic, data, patient_info)
                            event_data_6 = {
                                "step": "6_fhir_storage",
                                "status": "success",
                                "device_type": "Kati",
                                "topic": topic,
                                "payload": data,
                                "patient_info": patient_info,
                                "timestamp": datetime.utcnow().isoformat()
                            }
                            self.post_event_to_web_panel(event_data_6)
                        else:
                            data_flow_emitter.emit_error("6_fhir_storage", "Kati", topic, data, "FHIR storage failed")
                            event_data_6 = {
                                "step": "6_fhir_storage",
                                "status": "error",
                                "device_type": "Kati",
                                "topic": topic,
                                "payload": data,
                                "patient_info": patient_info,
                                "error": "FHIR storage failed",
                                "timestamp": datetime.utcnow().isoformat()
                            }
                            self.post_event_to_web_panel(event_data_6)
                    else:
                        logger.info(f"📝 {topic} data not stored in FHIR R5 (not patient-related)")
                        data_flow_emitter.emit_data_processed("Kati", topic, data, patient_info)
                        event_data_6 = {
                            "step": "6_data_processed",
                            "status": "success",
                            "device_type": "Kati",
                            "topic": topic,
                            "payload": data,
                            "patient_info": patient_info,
                            "timestamp": datetime.utcnow().isoformat()
                        }
                        self.post_event_to_web_panel(event_data_6)
                        
                except Exception as e:
                    logger.error(f"❌ Error in FHIR R5 processing: {e}")
                    data_flow_emitter.emit_error("6_fhir_storage", "Kati", topic, data, f"FHIR processing error: {str(e)}")
                    event_data_6 = {
                        "step": "6_fhir_storage",
                        "status": "error",
                        "device_type": "Kati",
                        "topic": topic,
                        "payload": data,
                        "patient_info": patient_info,
                        "error": f"FHIR processing error: {str(e)}",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    self.post_event_to_web_panel(event_data_6)
            else:
                logger.info(f"📝 Skipping FHIR storage for unmapped device IMEI: {imei}")
                data_flow_emitter.emit_data_processed("Kati", topic, data, None)
                event_data_6 = {
                    "step": "6_data_processed",
                    "status": "success",
                    "device_type": "Kati",
                    "topic": topic,
                    "payload": data,
                    "patient_info": None,
                    "timestamp": datetime.utcnow().isoformat()
                }
                self.post_event_to_web_panel(event_data_6)
            
            # Step 7: Store in medical collection (for monitoring) - ALL data types (mapped and unmapped)
            try:
                # Store ALL data types for monitoring display (including unmapped devices)
                logger.info(f"📝 Storing {topic} data for monitoring display")
                
                # Store processed data in medical collection for monitoring
                medical_data = {
                    "device_type": "Kati_Watch",
                    "device_id": imei,
                    "topic": topic,
                    "data": data,
                    "timestamp": datetime.utcnow(),
                    "processed_at": datetime.utcnow()
                }
                
                # Add patient info if available
                if patient_id:
                    medical_data["patient_id"] = patient_id
                    medical_data["patient_name"] = patient_name
                else:
                    medical_data["patient_name"] = f"Unmapped Device ({imei})"
                
                # Add topic-specific processing based on exact payload structures
                if topic == "iMEDE_watch/onlineTrigger":
                    # Online/Offline status
                    medical_data["status"] = data.get("status", "unknown")  # "online" or "offline"
                    medical_data["event_type"] = "device_status"
                    logger.info(f"[DEBUG] DEVICE STATUS: {medical_data['status']} for IMEI {data.get('IMEI')}")
                    
                elif topic == "iMEDE_watch/hb":
                    # Heartbeat with step, battery, signalGSM
                    medical_data["step_count"] = data.get("step", 0)
                    medical_data["battery"] = data.get("battery", 0)
                    medical_data["signal_gsm"] = data.get("signalGSM", 0)
                    medical_data["satellites"] = data.get("satellites", 0)
                    medical_data["working_mode"] = data.get("workingMode", 0)
                    medical_data["time_stamps"] = data.get("timeStamps", "")
                    medical_data["event_type"] = "heartbeat"
                    
                    # Working mode description
                    working_mode_desc = {
                        1: "Normal mode (15min position report with WiFi+LBS)",
                        2: "Power-saving mode (60min position report with WiFi+LBS)", 
                        3: "Emergency mode (1min position report with GPS+WiFi+LBS)",
                        8: "GPS mode (time interval setting by admin)"
                    }
                    working_mode_text = working_mode_desc.get(medical_data["working_mode"], "Unknown mode")
                    logger.info(f"[DEBUG] HEARTBEAT: Steps={medical_data['step_count']}, Battery={medical_data['battery']}%, Signal={medical_data['signal_gsm']}, Mode={working_mode_text}")
                    
                elif topic == "iMEDE_watch/VitalSign":
                    # Vital signs with location
                    medical_data["heart_rate"] = data.get("heartRate")
                    medical_data["blood_pressure"] = data.get("bloodPressure")
                    medical_data["body_temperature"] = data.get("bodyTemperature")
                    medical_data["spo2"] = data.get("spO2")
                    medical_data["signal_gsm"] = data.get("signalGSM")
                    medical_data["battery"] = data.get("battery")
                    medical_data["location"] = data.get("location")
                    medical_data["time_stamps"] = data.get("timeStamps", "")
                    medical_data["event_type"] = "vital_signs"
                    
                    # Debug log for extracted vital signs
                    bp_data = medical_data["blood_pressure"] or {}
                    logger.info(f"[DEBUG] VITAL SIGNS: HR={medical_data['heart_rate']}, BP={bp_data.get('bp_sys')}/{bp_data.get('bp_dia')}, BT={medical_data['body_temperature']}°C, SpO2={medical_data['spo2']}%")
                    
                elif topic == "iMEDE_watch/AP55":
                    # Batch vital signs (hourly upload)
                    medical_data["num_datas"] = data.get("num_datas", 0)
                    medical_data["vital_signs_data"] = data.get("data", [])
                    medical_data["location"] = data.get("location")
                    medical_data["time_stamps"] = data.get("timeStamps", "")
                    medical_data["event_type"] = "batch_vital_signs"
                    
                    # Debug log for AP55 batch vital signs
                    if isinstance(medical_data["vital_signs_data"], list):
                        logger.info(f"[DEBUG] AP55 BATCH: {len(medical_data['vital_signs_data'])} vital signs records")
                        for idx, item in enumerate(medical_data["vital_signs_data"]):
                            bp_data = item.get('bloodPressure', {})
                            logger.info(f"[DEBUG] AP55 VITAL SIGN #{idx+1}: HR={item.get('heartRate')}, BP={bp_data.get('bp_sys')}/{bp_data.get('bp_dia')}, BT={item.get('bodyTemperature')}°C, SpO2={item.get('spO2')}%")
                    
                elif topic == "iMEDE_watch/location":
                    # Location data (GPS, WiFi, LBS)
                    medical_data["location"] = data.get("location")
                    medical_data["time"] = data.get("time", "")
                    medical_data["event_type"] = "location"
                    
                    # Debug location data
                    location_data = medical_data["location"] or {}
                    gps_data = location_data.get("GPS", {})
                    wifi_data = location_data.get("WiFi", "")
                    lbs_data = location_data.get("LBS", {})
                    
                    if gps_data.get("latitude") and gps_data.get("longitude"):
                        logger.info(f"[DEBUG] LOCATION GPS: Lat={gps_data['latitude']}, Lon={gps_data['longitude']}, Speed={gps_data.get('speed')}, Header={gps_data.get('header')}")
                    if lbs_data:
                        logger.info(f"[DEBUG] LOCATION LBS: MCC={lbs_data.get('MCC')}, MNC={lbs_data.get('MNC')}, LAC={lbs_data.get('LAC')}, CID={lbs_data.get('CID')}")
                    
                elif topic == "iMEDE_watch/sleepdata":
                    # Sleep tracking data
                    medical_data["sleep_data"] = data.get("sleep", {})
                    medical_data["event_type"] = "sleep_data"
                    
                    # Debug sleep data
                    sleep_data = medical_data["sleep_data"] or {}
                    logger.info(f"[DEBUG] SLEEP DATA: Period={sleep_data.get('time')}, Slots={sleep_data.get('num')}, Data length={len(sleep_data.get('data', ''))}")
                    
                elif topic == "iMEDE_watch/sos" or topic == "iMEDE_watch/SOS":
                    # SOS emergency
                    medical_data["status"] = data.get("status", "SOS")
                    medical_data["location"] = data.get("location")
                    medical_data["event_type"] = "emergency_sos"
                    
                    # Debug SOS data
                    location_data = medical_data["location"] or {}
                    gps_data = location_data.get("GPS", {})
                    lbs_data = location_data.get("LBS", {})
                    logger.info(f"[DEBUG] SOS EMERGENCY: Status={medical_data['status']}, GPS={gps_data.get('latitude')}/{gps_data.get('longitude')}, LBS={lbs_data.get('MCC')}-{lbs_data.get('MNC')}")
                    
                elif topic == "iMEDE_watch/fallDown" or topic == "iMEDE_watch/FALLDOWN":
                    # Fall detection
                    medical_data["status"] = data.get("status", "FALL DOWN")
                    medical_data["location"] = data.get("location")
                    medical_data["event_type"] = "fall_detection"
                    
                    # Debug fall detection data
                    location_data = medical_data["location"] or {}
                    gps_data = location_data.get("GPS", {})
                    lbs_data = location_data.get("LBS", {})
                    logger.info(f"[DEBUG] FALL DETECTION: Status={medical_data['status']}, GPS={gps_data.get('latitude')}/{gps_data.get('longitude')}, LBS={lbs_data.get('MCC')}-{lbs_data.get('MNC')}")
                
                # Store in medical collection
                result = self.data_processor.store_medical_data(medical_data)
                if result:
                    logger.info(f"✅ Medical data stored for {topic}")
                    data_flow_emitter.emit_medical_stored("Kati", topic, data, patient_info, medical_data)
                else:
                    logger.warning(f"⚠️ Failed to store medical data for {topic}")
                    
            except Exception as e:
                logger.error(f"❌ Error storing medical data: {e}")
            
            logger.info(f"✅ Successfully processed {topic} message for patient {patient_name}")
                
        except json.JSONDecodeError as e:
            logger.error(f"❌ Invalid JSON in payload: {e}")
            data_flow_emitter.emit_error("2_payload_parsed", "Kati", topic, payload, f"Invalid JSON: {str(e)}")
        except Exception as e:
            logger.error(f"❌ Error processing message: {e}")
            data_flow_emitter.emit_error("message_processing", "Kati", topic, payload, f"Processing error: {str(e)}")
    
    def post_event_to_web_panel(self, event_data: Dict[str, Any]) -> bool:
        """Post event to web panel for real-time monitoring"""
        try:
            # Wrap event data in 'event' key as expected by web panel
            wrapped_data = {"event": event_data}
            
            response = requests.post(
                f"{self.web_panel_url}/api/data-flow/emit",
                json=wrapped_data,
                timeout=self.web_panel_timeout
            )
            if response.status_code == 200:
                logger.debug(f"✅ Event posted to web panel: {event_data.get('step', 'unknown')}")
                return True
            else:
                logger.warning(f"⚠️ Failed to post event to web panel: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ Error posting event to web panel: {e}")
            return False
    
    def _should_store_in_fhir(self, topic: str, data: Dict[str, Any]) -> bool:
        """Check if the data should be stored in FHIR R5 (only for Patient resource data)"""
        # Store all patient-related data in FHIR R5
        patient_related_topics = [
            "iMEDE_watch/VitalSign",    # Vital signs
            "iMEDE_watch/AP55",         # Batch vital signs (hourly upload)
            "iMEDE_watch/location",     # Location data (GPS, WiFi, LBS)
            "iMEDE_watch/sleepdata",    # Sleep tracking data
            "iMEDE_watch/hb",           # Heartbeat with step count, battery, signal
            "iMEDE_watch/onlineTrigger" # Device online/offline status
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
            # If AP55, observation_data is a list - use batch endpoint
            if isinstance(observation_data, list):
                # Use batch endpoint for multiple observations
                response = requests.post(f"{api_base_url}/fhir/R5/Observation/batch", 
                                       json=observation_data, headers=headers, timeout=30)
                if response.status_code in (200, 201):
                    result = response.json()
                    successful = result.get('successful', 0)
                    failed = result.get('failed', 0)
                    logger.info(f"✅ FHIR R5 Batch Observation (AP55) created for patient {patient_info.get('patient_id')} - {successful} successful, {failed} failed")
                    return failed == 0
                else:
                    logger.error(f"FHIR R5 Batch API error (AP55): {response.status_code} - {response.text}")
                    return False
            else:
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

    def _transform_kati_to_fhir_observation(self, topic: str, data: Dict[str, Any], patient_info: Dict[str, Any]) -> Any:
        """Transform Kati data to FHIR R5 Observation format. For AP55, return a list of observations."""
        try:
            # Base observation structure
            def base_observation():
                return {
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
            
            # AP55: Batch vital signs (hourly upload)
            if topic == "iMEDE_watch/AP55":
                obs_list = []
                
                # Check if data contains a 'data' array (new AP55 structure)
                if "data" in data and isinstance(data["data"], list):
                    # Process each vital sign in the data array
                    for data_item in data["data"]:
                        # Heart rate
                        if "heartRate" in data_item:
                            obs = base_observation()
                            obs.update({
                                "code": {
                                    "coding": [
                                        {"system": "http://loinc.org", "code": "8867-4", "display": "Heart rate"}
                                    ],
                                    "text": "Heart Rate"
                                },
                                "valueQuantity": {
                                    "value": float(data_item["heartRate"]),
                                    "unit": "beats/min",
                                    "system": "http://unitsofmeasure.org",
                                    "code": "/min"
                                }
                            })
                            obs_list.append(obs)
                        
                        # Blood pressure
                        if "bloodPressure" in data_item:
                            bp_data = data_item["bloodPressure"]
                            if "bp_sys" in bp_data and "bp_dia" in bp_data:
                                obs = base_observation()
                                obs.update({
                                    "code": {
                                        "coding": [
                                            {"system": "http://loinc.org", "code": "85354-9", "display": "Blood pressure panel"}
                                        ],
                                        "text": "Blood Pressure"
                                    },
                                    "component": [
                                        {
                                            "code": {"coding": [{"system": "http://loinc.org", "code": "8480-6", "display": "Systolic blood pressure"}]},
                                            "valueQuantity": {
                                                "value": float(bp_data["bp_sys"]),
                                                "unit": "mmHg",
                                                "system": "http://unitsofmeasure.org",
                                                "code": "mm[Hg]"
                                            }
                                        },
                                        {
                                            "code": {"coding": [{"system": "http://loinc.org", "code": "8462-4", "display": "Diastolic blood pressure"}]},
                                            "valueQuantity": {
                                                "value": float(bp_data["bp_dia"]),
                                                "unit": "mmHg",
                                                "system": "http://unitsofmeasure.org",
                                                "code": "mm[Hg]"
                                            }
                                        }
                                    ]
                                })
                                obs_list.append(obs)
                        
                        # SpO2
                        if "spO2" in data_item:
                            obs = base_observation()
                            obs.update({
                                "code": {
                                    "coding": [
                                        {"system": "http://loinc.org", "code": "2708-6", "display": "Oxygen saturation"}
                                    ],
                                    "text": "SpO2"
                                },
                                "valueQuantity": {
                                    "value": float(data_item["spO2"]),
                                    "unit": "%",
                                    "system": "http://unitsofmeasure.org",
                                    "code": "%"
                                }
                            })
                            obs_list.append(obs)
                        
                        # Temperature
                        if "bodyTemperature" in data_item:
                            obs = base_observation()
                            obs.update({
                                "code": {
                                    "coding": [
                                        {"system": "http://loinc.org", "code": "8310-5", "display": "Body temperature"}
                                    ],
                                    "text": "Body Temperature"
                                },
                                "valueQuantity": {
                                    "value": float(data_item["bodyTemperature"]),
                                    "unit": "°C",
                                    "system": "http://unitsofmeasure.org",
                                    "code": "Cel"
                                }
                            })
                            obs_list.append(obs)
                
                # Legacy support for old AP55 structure
                else:
                    # Heart rate
                    if "hr" in data:
                        obs = base_observation()
                        obs.update({
                            "code": {
                                "coding": [
                                    {"system": "http://loinc.org", "code": "8867-4", "display": "Heart rate"}
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
                        obs_list.append(obs)
                    
                    # Systolic/Diastolic
                    if "systolic" in data and "diastolic" in data:
                        obs = base_observation()
                        obs.update({
                            "code": {
                                "coding": [
                                    {"system": "http://loinc.org", "code": "85354-9", "display": "Blood pressure panel"}
                                ],
                                "text": "Blood Pressure"
                            },
                            "component": [
                                {
                                    "code": {"coding": [{"system": "http://loinc.org", "code": "8480-6", "display": "Systolic blood pressure"}]},
                                    "valueQuantity": {
                                        "value": float(data["systolic"]),
                                        "unit": "mmHg",
                                        "system": "http://unitsofmeasure.org",
                                        "code": "mm[Hg]"
                                    }
                                },
                                {
                                    "code": {"coding": [{"system": "http://loinc.org", "code": "8462-4", "display": "Diastolic blood pressure"}]},
                                    "valueQuantity": {
                                        "value": float(data["diastolic"]),
                                        "unit": "mmHg",
                                        "system": "http://unitsofmeasure.org",
                                        "code": "mm[Hg]"
                                    }
                                }
                            ]
                        })
                        obs_list.append(obs)
                    
                    # SpO2
                    if "spo2" in data:
                        obs = base_observation()
                        obs.update({
                            "code": {
                                "coding": [
                                    {"system": "http://loinc.org", "code": "2708-6", "display": "Oxygen saturation"}
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
                        obs_list.append(obs)
                    
                    # Temperature
                    if "temp" in data:
                        obs = base_observation()
                        obs.update({
                            "code": {
                                "coding": [
                                    {"system": "http://loinc.org", "code": "8310-5", "display": "Body temperature"}
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
                        obs_list.append(obs)
                
                return obs_list if obs_list else None
            
            # Vital signs observation (new format)
            elif topic == "iMEDE_watch/VitalSign":
                vital_signs = []
                
                # Heart rate
                if "heartRate" in data:
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
                            "value": float(data["heartRate"]),
                            "unit": "beats/min",
                            "system": "http://unitsofmeasure.org",
                            "code": "/min"
                        }
                    })
                
                # Blood pressure
                if "bloodPressure" in data:
                    bp_data = data["bloodPressure"]
                    if "bp_sys" in bp_data and "bp_dia" in bp_data:
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
                                        "value": float(bp_data["bp_sys"]),
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
                                        "value": float(bp_data["bp_dia"]),
                                        "unit": "mmHg",
                                        "system": "http://unitsofmeasure.org",
                                        "code": "mm[Hg]"
                                    }
                                }
                            ]
                        })
                
                # SpO2
                if "spO2" in data:
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
                            "value": float(data["spO2"]),
                            "unit": "%",
                            "system": "http://unitsofmeasure.org",
                            "code": "%"
                        }
                    })
                
                # Temperature
                if "bodyTemperature" in data:
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
                            "value": float(data["bodyTemperature"]),
                            "unit": "°C",
                            "system": "http://unitsofmeasure.org",
                            "code": "Cel"
                        }
                    })
                
                # Return multiple observations if multiple vital signs
                if len(vital_signs) == 1:
                    return vital_signs[0]
                elif len(vital_signs) > 1:
                    # For multiple vital signs, we'll create separate observations
                    # For now, return the first one
                    return vital_signs[0]
                else:
                    return None
                    
            elif topic == "iMEDE_watch/hb":
                # Heartbeat observation (step count)
                if "step" in data:
                    observation = base_observation()
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
                    return observation
                else:
                    return None
                    
            elif topic == "iMEDE_watch/location":
                # Location observation
                if "location" in data and "GPS" in data["location"]:
                    gps_data = data["location"]["GPS"]
                    if "latitude" in gps_data and "longitude" in gps_data:
                        observation = base_observation()
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
                            "valueString": f"{gps_data['latitude']},{gps_data['longitude']}"
                        })
                        return observation
                return None
                    
            elif topic == "iMEDE_watch/sleepdata":
                # Sleep data observation
                if "sleep" in data:
                    sleep_data = data["sleep"]
                    if "data" in sleep_data:
                        observation = base_observation()
                        observation.update({
                            "code": {
                                "coding": [
                                    {
                                        "system": "http://loinc.org",
                                        "code": "93832-4",
                                        "display": "Sleep study"
                                    }
                                ],
                                "text": "Sleep Data"
                            },
                            "valueString": f"Sleep period: {sleep_data.get('time', 'N/A')}, Slots: {sleep_data.get('num', 0)}"
                        })
                        return observation
                return None
                    
            elif topic == "iMEDE_watch/onlineTrigger":
                # Device status observation
                if "status" in data:
                    observation = base_observation()
                    observation.update({
                        "code": {
                            "coding": [
                                {
                                    "system": "http://loinc.org",
                                    "code": "75275-8",
                                    "display": "Device status"
                                }
                            ],
                            "text": "Device Status"
                        },
                        "valueString": data["status"]  # "online" or "offline"
                    })
                    return observation
                return None
                    
            else:
                # Unknown topic
                return None
            
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