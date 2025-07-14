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
from transaction_logger import TransactionLogger

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
        self.transaction_logger = TransactionLogger()
        
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
            
            msg_type = data.get('type')
            
            if msg_type == "HB_Msg":
                self.process_qube_status(data)
            elif msg_type == "reportAttribute":
                self.process_qube_medical_data(data)
            else:
                logger.info(f"Unhandled message type: {msg_type}")
                
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON payload: {e}")
        except Exception as e:
            logger.error(f"Error processing message: {e}")
    
    def process_qube_status(self, data: Dict[str, Any]):
        """Process Qube-Vital status messages (heartbeat)"""
        try:
            mac_address = data.get('mac')
            imei = data.get('IMEI')
            
            if not mac_address:
                logger.warning("No MAC address in Qube-Vital status message")
                return
            
            logger.info(f"Qube-Vital status: MAC={mac_address}, IMEI={imei}")
            
            # Store device status in latest_devices_status collection
            try:
                logger.info(f"Attempting to store device status for Qube-Vital {mac_address} in latest_devices_status collection")
                
                status_data = {
                    "device_id": mac_address,  # Use MAC address as device_id for Qube-Vital
                    "device_type": "qube-vital",
                    "imei": imei,
                    "mac_address": mac_address,  # Include MAC address field
                    "online_status": "online",
                    "last_updated": datetime.utcnow(),
                    "patient_id": None,  # Qube-Vital gateways don't have direct patient assignment
                    "message_type": "HB_Msg",
                    "data": data.get('data', {}),
                    "battery_level": None,  # Qube-Vital doesn't provide battery level
                    "signal_strength": None,  # Qube-Vital doesn't provide signal strength
                    "alerts": []
                }
                
                # Use upsert to update existing record or create new one
                result = self.device_mapper.db.latest_devices_status.update_one(
                    {"device_id": mac_address},
                    {"$set": status_data},
                    upsert=True
                )
                
                if result.upserted_id:
                    logger.info(f"✅ Created new device status record for Qube-Vital {mac_address} in latest_devices_status collection")
                elif result.modified_count > 0:
                    logger.info(f"✅ Updated existing device status record for Qube-Vital {mac_address} in latest_devices_status collection")
                else:
                    logger.info(f"✅ Device status record for Qube-Vital {mac_address} already up-to-date in latest_devices_status collection")
                    
            except Exception as e:
                logger.error(f"❌ Failed to store device status for Qube-Vital {mac_address} in latest_devices_status collection: {e}")
                # Log failed transaction for device status storage
                self.transaction_logger.log_transaction(
                    operation="qube_device_status_storage",
                    data_type="device_status",
                    collection="latest_devices_status",
                    status="failed",
                    details=f"Failed to store device status: {e}",
                    device_id=mac_address
                )
            
            # Update device status for Qube-Vital gateway
            self.data_processor.device_status_service.update_device_status(
                device_id=mac_address,
                device_type="Qube-Vital",
                status_data={
                    "type": "HB_Msg",
                    "mac": mac_address,
                    "imei": imei,
                    "name": data.get('name', ''),
                    "data": data.get('data', {}),
                    "online_status": "online"
                }
            )
            
            # Log transaction
            self.transaction_logger.log_data_update(
                "system", "online_status", "device_status", 
                mac_address, f"Qube-Vital gateway online: {data.get('name', '')}"
            )
            
        except Exception as e:
            logger.error(f"Error processing Qube-Vital status: {e}")

    def process_qube_medical_data(self, data: Dict[str, Any]):
        """Process Qube-Vital medical device data"""
        try:
            citiz = data.get('citiz')
            attribute = data.get('data', {}).get('attribute')
            value = data.get('data', {}).get('value', {})
            device_mac = data.get('mac')
            
            if not citiz:
                logger.warning("No citizen ID in Qube-Vital medical data")
                return
            
            if not attribute:
                logger.warning("No attribute in Qube-Vital medical data")
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
            
            logger.info(f"Processing {attribute} data for patient {patient['_id']}")
            
            # Process the medical data with device MAC
            success = self.data_processor.process_qube_data(
                patient['_id'], 
                attribute, 
                value,
                device_mac
            )
            
            if success:
                logger.info(f"Successfully processed {attribute} data for patient {patient['_id']}")
            else:
                logger.error(f"Failed to process {attribute} data for patient {patient['_id']}")
                
        except Exception as e:
            logger.error(f"Error processing Qube-Vital medical data: {e}")
    
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