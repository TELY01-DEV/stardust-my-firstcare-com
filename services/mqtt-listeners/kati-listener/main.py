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
from transaction_logger import TransactionLogger

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
            logger.info(f"Processing {topic} message")
            
            # Extract IMEI from payload
            imei = data.get('IMEI')
            if not imei:
                logger.warning("No IMEI found in Kati message")
                # Log failed transaction
                self.transaction_logger.log_transaction(
                    operation="kati_message_processing",
                    data_type="vital_signs",
                    collection="patients",
                    status="failed",
                    details="No IMEI found in Kati message",
                    device_id=imei
                )
                return
            
            # Handle online/offline trigger messages
            if topic == 'iMEDE_watch/onlineTrigger':
                self.process_kati_online_status(data)
                return
            
            # Find patient by Kati IMEI
            patient = self.device_mapper.find_patient_by_kati_imei(imei)
            if not patient:
                logger.warning(f"No patient found for Kati IMEI: {imei}")
                # Log failed transaction
                self.transaction_logger.log_transaction(
                    operation="kati_message_processing",
                    data_type="vital_signs",
                    collection="patients",
                    status="failed",
                    details=f"No patient found for Kati IMEI: {imei}",
                    device_id=imei
                )
                return
            
            logger.info(f"Processing {topic} data for patient {patient['_id']}")
            
            # Store device status for heartbeat messages
            if topic == 'iMEDE_watch/hb':
                try:
                    logger.info(f"Attempting to store device status for Kati {imei} in latest_devices_status collection")
                    
                    status_data = {
                        "device_id": imei,  # Use IMEI as device_id for Kati Watch
                        "device_type": "kati",
                        "imei": imei,
                        "mac_address": None,  # Kati Watch doesn't have MAC address
                        "online_status": "online",
                        "last_updated": datetime.utcnow(),
                        "patient_id": patient['_id'],
                        "message_type": "heartbeat",
                        "battery_level": data.get('battery'),
                        "signal_strength": data.get('signalGSM'),
                        "alerts": []
                    }
                    
                    # Store this in latest_devices_status collection
                    result = self.device_mapper.db.latest_devices_status.update_one(
                        {"device_id": imei},
                        {"$set": status_data},
                        upsert=True
                    )
                    
                    if result.upserted_id:
                        logger.info(f"✅ Created new device status record for Kati {imei} in latest_devices_status collection")
                    elif result.modified_count > 0:
                        logger.info(f"✅ Updated existing device status record for Kati {imei} in latest_devices_status collection")
                    else:
                        logger.info(f"✅ Device status record for Kati {imei} already up-to-date in latest_devices_status collection")
                        
                except Exception as e:
                    logger.error(f"❌ Failed to store device status for Kati {imei} in latest_devices_status collection: {e}")
                    # Log failed transaction for device status storage
                    self.transaction_logger.log_transaction(
                        operation="kati_device_status_storage",
                        data_type="device_status",
                        collection="latest_devices_status",
                        status="failed",
                        details=f"Failed to store device status: {e}",
                        device_id=imei
                    )
            
            # Process the data based on topic
            success = self.data_processor.process_kati_data(patient['_id'], topic, data)
            
            if success:
                logger.info(f"Successfully processed {topic} data for patient {patient['_id']}")
                # Log successful transaction
                self.transaction_logger.log_transaction(
                    operation="kati_message_processing",
                    data_type="vital_signs",
                    collection="patients",
                    patient_id=str(patient['_id']),
                    status="success",
                    details=f"Successfully processed {topic} data",
                    device_id=imei
                )
            else:
                logger.error(f"Failed to process {topic} data for patient {patient['_id']}")
                # Log failed transaction
                self.transaction_logger.log_transaction(
                    operation="kati_message_processing",
                    data_type="vital_signs",
                    collection="patients",
                    patient_id=str(patient['_id']),
                    status="failed",
                    details=f"Failed to process {topic} data",
                    device_id=imei
                )
                
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON payload: {e}")
            # Log failed transaction
            self.transaction_logger.log_transaction(
                operation="kati_message_processing",
                data_type="vital_signs",
                collection="patients",
                status="failed",
                details=f"Invalid JSON payload: {e}",
                device_id="unknown"
            )
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            # Log failed transaction
            self.transaction_logger.log_transaction(
                operation="kati_message_processing",
                data_type="vital_signs",
                collection="patients",
                status="failed",
                details=f"Error processing message: {e}",
                device_id="unknown"
            )
    
    def process_kati_online_status(self, data: Dict[str, Any]):
        """Process Kati Watch online/offline status messages"""
        try:
            imei = data.get('IMEI')
            status = data.get('status', 'unknown')  # 'online' or 'offline'
            
            if not imei:
                logger.warning("No IMEI found in Kati online status message")
                return
            
            logger.info(f"Kati online status: IMEI={imei}, Status={status}")
            
            # Find patient by Kati IMEI
            patient = self.device_mapper.find_patient_by_kati_imei(imei)
            patient_id = patient['_id'] if patient else None
            
            # Store device status in latest_devices_status collection
            try:
                logger.info(f"Attempting to store online status for Kati {imei} in latest_devices_status collection")
                
                status_data = {
                    "device_id": imei,  # Use IMEI as device_id for Kati Watch
                    "device_type": "kati",
                    "imei": imei,
                    "mac_address": None,  # Kati Watch doesn't have MAC address
                    "online_status": status,
                    "last_updated": datetime.utcnow(),
                    "patient_id": patient_id,
                    "message_type": "online_trigger",
                    "battery_level": None,  # Not provided in online trigger
                    "signal_strength": None,  # Not provided in online trigger
                    "alerts": []
                }
                
                # Use upsert to update existing record or create new one
                result = self.device_mapper.db.latest_devices_status.update_one(
                    {"device_id": imei},
                    {"$set": status_data},
                    upsert=True
                )
                
                if result.upserted_id:
                    logger.info(f"✅ Created new online status record for Kati {imei} in latest_devices_status collection")
                elif result.modified_count > 0:
                    logger.info(f"✅ Updated existing online status record for Kati {imei} in latest_devices_status collection")
                else:
                    logger.info(f"✅ Online status record for Kati {imei} already up-to-date in latest_devices_status collection")
                    
            except Exception as e:
                logger.error(f"❌ Failed to store online status for Kati {imei} in latest_devices_status collection: {e}")
                # Log failed transaction for device status storage
                self.transaction_logger.log_transaction(
                    operation="kati_online_status_storage",
                    data_type="device_status",
                    collection="latest_devices_status",
                    status="failed",
                    details=f"Failed to store online status: {e}",
                    device_id=imei
                )
            
            # Log transaction
            self.transaction_logger.log_transaction(
                operation="kati_online_status_processing",
                data_type="device_status",
                collection="patients",
                patient_id=str(patient_id) if patient_id else None,
                status="success",
                details=f"Kati online status: {status}",
                device_id=imei
            )
            
        except Exception as e:
            logger.error(f"Error processing Kati online status: {e}")
    
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
            self.transaction_logger.close()

if __name__ == "__main__":
    listener = KatiMQTTListener()
    asyncio.run(listener.run()) 