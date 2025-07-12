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
        self.topics = os.getenv('MQTT_TOPICS', 'ESP32_BLE_GW_TX,dusun_sub').split(',')
        
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
            # Parse JSON payload
            data = json.loads(payload)
            logger.info(f"Processing {topic} message: {data.get('type', 'unknown')}")
            
            if topic == "ESP32_BLE_GW_TX":
                self.process_ava4_status(data)
            elif topic == "dusun_sub":
                self.process_ava4_medical_data(data)
            else:
                logger.warning(f"Unknown topic: {topic}")
                
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON payload: {e}")
        except Exception as e:
            logger.error(f"Error processing message: {e}")
    
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
            
            logger.info(f"AVA4 status for patient {patient['_id']}: {msg_type}")
            
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
            device_mac = data.get('mac')
            device_code = data.get('deviceCode')
            attribute = data.get('data', {}).get('attribute')
            value = data.get('data', {}).get('value', {})
            
            if msg_type != "reportAttribute":
                logger.info(f"Non-medical message type: {msg_type}")
                return
            
            if not device_mac or not attribute:
                logger.warning("Missing device MAC or attribute in medical data")
                return
            
            # Try to find patient by device MAC
            patient = None
            
            # First try to find by device MAC in amy_devices collection
            device_info = self.device_mapper.get_device_info(device_mac)
            if device_info and device_info.get('patient_id'):
                patient = self.device_mapper.db.patients.find_one({"_id": device_info['patient_id']})
            
            # If not found, try to find by device type mapping
            if not patient:
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
                    patient = self.device_mapper.find_patient_by_device_mac(device_mac, device_type)
            
            if not patient:
                logger.warning(f"No patient found for device MAC: {device_mac}, attribute: {attribute}")
                return
            
            logger.info(f"Processing {attribute} data for patient {patient['_id']}")
            
            # Process the medical data
            success = self.data_processor.process_ava4_data(
                patient['_id'], 
                device_mac, 
                attribute, 
                value
            )
            
            if success:
                logger.info(f"Successfully processed {attribute} data for patient {patient['_id']}")
            else:
                logger.error(f"Failed to process {attribute} data for patient {patient['_id']}")
                
        except Exception as e:
            logger.error(f"Error processing AVA4 medical data: {e}")
    
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