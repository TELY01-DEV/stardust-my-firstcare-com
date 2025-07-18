#!/usr/bin/env python3
"""
Qube-Vital MQTT Listener Service
Handles MQTT messages from Qube-Vital devices with robust connection handling
"""

import os
import json
import logging
import asyncio
import time
import random
from datetime import datetime, timedelta
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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RobustQubeMQTTListener:
    """Qube-Vital MQTT Listener Service with robust connection handling"""
    
    def __init__(self):
        # MQTT Configuration
        self.mqtt_broker = os.getenv('MQTT_BROKER_HOST', 'adam.amy.care')
        self.mqtt_port = int(os.getenv('MQTT_BROKER_PORT', 1883))
        self.mqtt_username = os.getenv('MQTT_USERNAME', 'webapi')
        self.mqtt_password = os.getenv('MQTT_PASSWORD', 'Sim!4433')
        self.mqtt_qos = int(os.getenv('MQTT_QOS', 1))
        self.mqtt_keepalive = int(os.getenv('MQTT_KEEPALIVE', 60))
        self.mqtt_timeout = int(os.getenv('MQTT_CONNECTION_TIMEOUT', 10))
        
        # Connection stability settings
        self.max_reconnect_attempts = int(os.getenv('MQTT_MAX_RECONNECT_ATTEMPTS', 10))
        self.initial_reconnect_delay = float(os.getenv('MQTT_INITIAL_RECONNECT_DELAY', 1.0))
        self.max_reconnect_delay = float(os.getenv('MQTT_MAX_RECONNECT_DELAY', 300.0))
        self.reconnect_backoff_multiplier = float(os.getenv('MQTT_RECONNECT_BACKOFF_MULTIPLIER', 2.0))
        self.connection_check_interval = int(os.getenv('MQTT_CONNECTION_CHECK_INTERVAL', 30))
        
        # Topics to subscribe to
        self.topics = os.getenv('MQTT_TOPICS', 'CM4_BLE_GW_TX').split(',')
        
        # MongoDB Configuration
        self.mongodb_uri = os.getenv('MONGODB_URI')
        self.mongodb_database = os.getenv('MONGODB_DATABASE', 'AMY')
        
        # Initialize services
        self.device_mapper = DeviceMapper(self.mongodb_uri, self.mongodb_database)
        self.data_processor = DataProcessor(self.mongodb_uri, self.mongodb_database)
        
        # Connection state
        self.client = None
        self.connected = False
        self.connection_start_time = None
        self.last_message_time = None
        self.reconnect_attempts = 0
        self.reconnect_delay = self.initial_reconnect_delay
        self.should_reconnect = True
        self.connection_lock = asyncio.Lock()
        
        # Statistics
        self.messages_received = 0
        self.messages_processed = 0
        self.errors_count = 0
        self.last_stats_time = time.time()
        
        self.web_panel_url = os.getenv('WEB_PANEL_URL', 'http://mqtt-panel:8098')
        self.web_panel_timeout = int(os.getenv('WEB_PANEL_TIMEOUT', 30))
        
    def _get_client_id(self) -> str:
        """Generate unique client ID"""
        return f"qube_listener_{int(time.time())}_{random.randint(1000, 9999)}"
    
    def _exponential_backoff(self) -> float:
        """Calculate exponential backoff delay with jitter"""
        delay = min(self.reconnect_delay * (self.reconnect_backoff_multiplier ** self.reconnect_attempts), 
                   self.max_reconnect_delay)
        # Add jitter to prevent thundering herd
        jitter = random.uniform(0.8, 1.2)
        return delay * jitter
    
    def _reset_reconnect_delay(self):
        """Reset reconnect delay after successful connection"""
        self.reconnect_delay = self.initial_reconnect_delay
        self.reconnect_attempts = 0
    
    def _on_connect(self, client, userdata, flags, rc):
        """Handle MQTT connection events"""
        if rc == 0:
            logger.info("✅ Connected to MQTT broker successfully")
            self.connected = True
            self.connection_start_time = time.time()
            self._reset_reconnect_delay()
            
            # Subscribe to topics
            for topic in self.topics:
                result = client.subscribe(topic, self.mqtt_qos)
                if result[0] == 0:
                    logger.info(f"📡 Subscribed to topic: {topic}")
                else:
                    logger.error(f"❌ Failed to subscribe to topic: {topic}, error code: {result[0]}")
        else:
            error_messages = {
                1: "Incorrect protocol version",
                2: "Invalid client identifier",
                3: "Server unavailable",
                4: "Bad username or password",
                5: "Not authorized"
            }
            error_msg = error_messages.get(rc, f"Unknown error code: {rc}")
            logger.error(f"❌ Failed to connect to MQTT broker: {error_msg} (code: {rc})")
            self.connected = False
    
    def _on_disconnect(self, client, userdata, rc):
        """Handle MQTT disconnection events"""
        self.connected = False
        self.connection_start_time = None
        
        if rc == 0:
            logger.info("ℹ️ Disconnected from MQTT broker (clean disconnect)")
        else:
            logger.warning(f"⚠️ Disconnected from MQTT broker, return code: {rc}")
            
        # Log connection statistics
        if self.connection_start_time:
            duration = time.time() - self.connection_start_time
            logger.info(f"📊 Connection duration: {duration:.1f} seconds, Messages: {self.messages_received}")
    
    def _on_message(self, client, userdata, msg):
        """Handle incoming MQTT messages"""
        try:
            self.last_message_time = time.time()
            self.messages_received += 1
            
            logger.info(f"📨 Received message on topic: {msg.topic}")
            self.process_message(msg.topic, msg.payload.decode())
            self.messages_processed += 1
            
        except Exception as e:
            self.errors_count += 1
            logger.error(f"❌ Error processing message: {e}")
    
    def _on_log(self, client, userdata, level, buf):
        """Handle MQTT client logs"""
        if level >= mqtt_client.MQTT_LOG_WARNING:
            logger.warning(f"MQTT Client: {buf}")
    
    def _create_mqtt_client(self) -> mqtt_client.Client:
        """Create and configure MQTT client"""
        client_id = self._get_client_id()
        client = mqtt_client.Client(client_id=client_id, clean_session=True)
        
        # Set callbacks
        client.on_connect = self._on_connect
        client.on_disconnect = self._on_disconnect
        client.on_message = self._on_message
        client.on_log = self._on_log
        
        # Set credentials
        client.username_pw_set(self.mqtt_username, self.mqtt_password)
        
        # Set connection options
        client.connect_timeout = self.mqtt_timeout
        client.keepalive = self.mqtt_keepalive
        
        return client
    
    async def _connect_with_retry(self) -> bool:
        """Connect to MQTT broker with retry logic"""
        async with self.connection_lock:
            if self.client and self.connected:
                return True
            
            # Clean up existing client
            if self.client:
                try:
                    self.client.loop_stop()
                    self.client.disconnect()
                except:
                    pass
                self.client = None
            
            # Create new client
            self.client = self._create_mqtt_client()
            
            try:
                logger.info(f"🔌 Attempting to connect to MQTT broker: {self.mqtt_broker}:{self.mqtt_port}")
                self.client.connect(self.mqtt_broker, self.mqtt_port, self.mqtt_keepalive)
                self.client.loop_start()
                
                # Wait for connection to establish
                wait_time = 0
                while not self.connected and wait_time < self.mqtt_timeout:
                    await asyncio.sleep(0.1)
                    wait_time += 0.1
                
                if self.connected:
                    logger.info("✅ MQTT connection established successfully")
                    return True
                else:
                    logger.error("❌ MQTT connection timeout")
                    return False
                    
            except Exception as e:
                logger.error(f"❌ Failed to connect to MQTT broker: {e}")
                return False
    
    async def _reconnect(self) -> bool:
        """Reconnect to MQTT broker with exponential backoff"""
        if not self.should_reconnect:
            return False
        
        self.reconnect_attempts += 1
        
        if self.reconnect_attempts > self.max_reconnect_attempts:
            logger.error(f"❌ Max reconnection attempts ({self.max_reconnect_attempts}) reached. Stopping reconnection.")
            self.should_reconnect = False
            return False
        
        delay = self._exponential_backoff()
        logger.warning(f"🔄 Attempting reconnection {self.reconnect_attempts}/{self.max_reconnect_attempts} in {delay:.1f} seconds...")
        
        await asyncio.sleep(delay)
        
        return await self._connect_with_retry()
    
    async def _monitor_connection(self):
        """Monitor connection health and trigger reconnection if needed"""
        while self.should_reconnect:
            try:
                await asyncio.sleep(self.connection_check_interval)
                
                if not self.connected:
                    logger.warning("🔍 Connection lost, initiating reconnection...")
                    await self._reconnect()
                elif self.last_message_time:
                    # Check if we haven't received messages for too long
                    time_since_last_message = time.time() - self.last_message_time
                    if time_since_last_message > self.connection_check_interval * 2:
                        logger.warning(f"⚠️ No messages received for {time_since_last_message:.1f} seconds, checking connection...")
                        # Force a ping to check connection
                        if self.client:
                            try:
                                self.client.publish("$SYS/broker/uptime", "", qos=0)
                            except:
                                logger.warning("🔍 Connection check failed, initiating reconnection...")
                                await self._reconnect()
                
                # Log statistics periodically
                await self._log_statistics()
                
            except Exception as e:
                logger.error(f"❌ Error in connection monitor: {e}")
    
    async def _log_statistics(self):
        """Log connection and processing statistics"""
        current_time = time.time()
        if current_time - self.last_stats_time > 300:  # Every 5 minutes
            uptime = current_time - self.last_stats_time
            logger.info(f"📊 Statistics - Uptime: {uptime:.0f}s, Messages: {self.messages_received}, "
                       f"Processed: {self.messages_processed}, Errors: {self.errors_count}, "
                       f"Connected: {self.connected}")
            self.last_stats_time = current_time
    
    def post_event_to_web_panel(self, event_data: Dict[str, Any]) -> bool:
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
    
    def process_message(self, topic: str, payload: str):
        """Process incoming MQTT message"""
        try:
            # Step 1: MQTT Message Received
            data_flow_emitter.emit_mqtt_received("Qube", topic, {"raw_payload": payload})
            event_data_1 = {
                "step": "1_mqtt_received",
                "status": "success",
                "device_type": "Qube",
                "topic": topic,
                "payload": {"raw_payload": payload},
                "timestamp": datetime.utcnow().isoformat()
            }
            self.post_event_to_web_panel(event_data_1)
            
            # Parse JSON payload
            data = json.loads(payload)
            logger.info(f"Processing {topic} message: {data.get('type', 'unknown')}")
            
            # Step 2: Payload Parsed
            data_flow_emitter.emit_payload_parsed("Qube", topic, data, {"parsed": True})
            event_data_2 = {
                "step": "2_payload_parsed",
                "status": "success",
                "device_type": "Qube",
                "topic": topic,
                "payload": data,
                "timestamp": datetime.utcnow().isoformat()
            }
            self.post_event_to_web_panel(event_data_2)
            
            msg_type = data.get('type')
            
            if msg_type == "HB_Msg":
                self.process_qube_status(data)
            elif msg_type == "reportAttribute":
                self.process_qube_medical_data(data)
            else:
                logger.info(f"Unhandled message type: {msg_type}")
                data_flow_emitter.emit_error("2_payload_parsed", "Qube", topic, data, f"Unhandled message type: {msg_type}")
                
        except json.JSONDecodeError as e:
            self.errors_count += 1
            logger.error(f"❌ Invalid JSON payload: {e}")
            data_flow_emitter.emit_error("2_payload_parsed", "Qube", topic, {"raw_payload": payload}, f"Invalid JSON: {e}")
        except Exception as e:
            self.errors_count += 1
            logger.error(f"❌ Error processing message: {e}")
            data_flow_emitter.emit_error("1_mqtt_received", "Qube", topic, {"raw_payload": payload}, str(e))
    
    def process_qube_status(self, data: Dict[str, Any]):
        """Process Qube-Vital status messages (heartbeat)"""
        try:
            mac_address = data.get('mac')
            imei = data.get('IMEI')
            
            if not mac_address:
                logger.warning("⚠️ No MAC address in Qube-Vital status message")
                return
            
            logger.info(f"💓 Qube-Vital status: MAC={mac_address}, IMEI={imei}")
            
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
            self.errors_count += 1
            logger.error(f"❌ Error processing Qube-Vital status: {e}")
    
    def process_qube_medical_data(self, data: Dict[str, Any]):
        """Process Qube-Vital medical device data"""
        try:
            citiz = data.get('citiz')
            attribute = data.get('data', {}).get('attribute')
            value = data.get('data', {}).get('value', {})
            
            if not citiz:
                logger.warning("⚠️ No citizen ID in Qube-Vital medical data")
                return
            
            if not attribute:
                logger.warning("⚠️ No attribute in Qube-Vital medical data")
                return
            
            # Step 2.5: FHIR Data Format Validation (NEW)
            try:
                validation_result = fhir_validator.validate_qube_data_format(data, "CM4_BLE_GW_TX")
                
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
                logger.info(f"👤 Creating unregistered patient for citizen ID: {citiz}")
                patient = self.device_mapper.create_unregistered_patient(
                    citiz=citiz,
                    name_th=data.get('nameTH', ''),
                    name_en=data.get('nameEN', ''),
                    birth_date=data.get('brith', ''),
                    gender=data.get('gender', '')
                )
                
                if not patient:
                    logger.error(f"❌ Failed to create unregistered patient for citizen ID: {citiz}")
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
            
            logger.info(f"💊 Processing {attribute} data for patient {patient['_id']}")
            
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
                logger.info(f"✅ Successfully processed {attribute} data for patient {patient['_id']}")
                data_flow_emitter.emit_medical_stored("Qube", "CM4_BLE_GW_TX", data, patient_info, medical_data)
                
                # Step 6: FHIR R5 Resource Data Store (DISABLED - handled by main API service)
                logger.info(f"ℹ️ FHIR R5 processing disabled in Qube-Vital listener - handled by main API service")
            else:
                logger.error(f"❌ Failed to process {attribute} data for patient {patient['_id']}")
                data_flow_emitter.emit_error("5_medical_stored", "Qube", "CM4_BLE_GW_TX", data, f"Failed to process {attribute} data")
                
        except Exception as e:
            self.errors_count += 1
            logger.error(f"❌ Error processing Qube-Vital medical data: {e}")
            data_flow_emitter.emit_error("3_patient_lookup", "Qube", "CM4_BLE_GW_TX", data, str(e))
    
    async def run(self):
        """Run the MQTT listener with robust connection handling"""
        logger.info("🚀 Starting Robust Qube-Vital MQTT Listener Service")
        logger.info(f"📡 Broker: {self.mqtt_broker}:{self.mqtt_port}")
        logger.info(f"👤 Username: {self.mqtt_username}")
        logger.info(f"📋 Topics: {', '.join(self.topics)}")
        logger.info(f"🔄 Max reconnect attempts: {self.max_reconnect_attempts}")
        logger.info(f"⏱️ Connection check interval: {self.connection_check_interval}s")
        
        # Initial connection
        if not await self._connect_with_retry():
            logger.error("❌ Failed to establish initial MQTT connection")
            return
        
        # Start connection monitor
        monitor_task = asyncio.create_task(self._monitor_connection())
        
        try:
            # Keep the service running
            while self.should_reconnect:
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("🛑 Shutting down Qube-Vital MQTT Listener Service")
        except Exception as e:
            logger.error(f"❌ Unexpected error: {e}")
        finally:
            # Cleanup
            self.should_reconnect = False
            monitor_task.cancel()
            
            if self.client:
                try:
                    self.client.loop_stop()
                    self.client.disconnect()
                except:
                    pass
            
            # Close database connections
            self.device_mapper.close()
            self.data_processor.close()
            
            logger.info("✅ Qube-Vital MQTT Listener Service stopped")

if __name__ == "__main__":
    listener = RobustQubeMQTTListener()
    asyncio.run(listener.run()) 