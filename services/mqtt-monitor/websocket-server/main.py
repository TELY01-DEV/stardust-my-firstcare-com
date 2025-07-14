#!/usr/bin/env python3
"""
MQTT Monitor WebSocket Server
Provides real-time MQTT message updates to web clients
"""

import os
import json
import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, Set
import sys

# Add shared utilities to path
sys.path.append('/app/shared')

from paho.mqtt import client as mqtt_client
import websockets
from mqtt_monitor import MQTTMonitor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MQTTWebSocketServer:
    """WebSocket server for real-time MQTT monitoring"""
    
    def __init__(self):
        # MQTT Configuration
        self.mqtt_broker = os.getenv('MQTT_BROKER_HOST', 'adam.amy.care')
        self.mqtt_port = int(os.getenv('MQTT_BROKER_PORT', 1883))
        self.mqtt_username = os.getenv('MQTT_USERNAME', 'webapi')
        self.mqtt_password = os.getenv('MQTT_PASSWORD', 'Sim!4433')
        self.mqtt_qos = int(os.getenv('MQTT_QOS', 1))
        self.mqtt_keepalive = int(os.getenv('MQTT_KEEPALIVE', 60))
        
        # Topics to subscribe to
        self.topics = os.getenv('MQTT_TOPICS', 'ESP32_BLE_GW_TX,dusun_sub,iMEDE_watch/#,CM4_BLE_GW_TX').split(',')
        
        # MongoDB Configuration
        self.mongodb_uri = os.getenv('MONGODB_URI')
        self.mongodb_database = os.getenv('MONGODB_DATABASE', 'AMY')
        
        # WebSocket Configuration
        self.ws_port = int(os.getenv('WS_PORT', 8081))
        self.ws_host = os.getenv('WS_HOST', '0.0.0.0')
        
        # Initialize services
        self.mqtt_monitor = MQTTMonitor(self.mongodb_uri, self.mongodb_database)
        
        # MQTT client
        self.mqtt_client = None
        self.mqtt_connected = False
        
        # WebSocket clients
        self.websocket_clients: Set[websockets.WebSocketServerProtocol] = set()
        
        # Message history (last 1000 messages)
        self.message_history: list = []
        self.max_history = 1000
        
        # Pending messages for async broadcast
        self.pending_messages: list = []
        
    def connect_mqtt(self) -> mqtt_client.Client:
        """Connect to MQTT broker"""
        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                logger.info("Connected to MQTT broker successfully")
                self.mqtt_connected = True
                # Subscribe to topics
                for topic in self.topics:
                    client.subscribe(topic, self.mqtt_qos)
                    logger.info(f"Subscribed to topic: {topic}")
            else:
                logger.error(f"Failed to connect to MQTT broker, return code: {rc}")
                self.mqtt_connected = False
        
        def on_disconnect(client, userdata, rc):
            logger.warning(f"Disconnected from MQTT broker, return code: {rc}")
            self.mqtt_connected = False
        
        def on_message(client, userdata, msg):
            try:
                logger.info(f"Received MQTT message on topic: {msg.topic}")
                payload = json.loads(msg.payload.decode())
                
                # Process message based on topic
                if msg.topic in ["ESP32_BLE_GW_TX", "dusun_sub"]:
                    processed_message = self.mqtt_monitor.process_ava4_message(msg.topic, payload)
                elif msg.topic.startswith("iMEDE_watch/"):
                    processed_message = self.mqtt_monitor.process_kati_message(msg.topic, payload)
                elif msg.topic == "CM4_BLE_GW_TX":
                    processed_message = self.mqtt_monitor.process_qube_message(msg.topic, payload)
                else:
                    processed_message = {
                        "timestamp": datetime.utcnow(),
                        "topic": msg.topic,
                        "device_type": "Unknown",
                        "raw_payload": payload,
                        "status": "unknown_topic"
                    }
                
                # Store medical data if patient mapping is successful
                if (processed_message.get("status") == "processed" and 
                    processed_message.get("patient_mapping") and 
                    processed_message.get("medical_data")):
                    
                    patient_id = processed_message["patient_mapping"]["patient_id"]
                    medical_data = processed_message["medical_data"]
                    device_type = processed_message["device_type"]
                    
                    # Store different types of medical data based on device type and topic
                    if msg.topic == "iMEDE_watch/VitalSign":
                        # Kati Watch vital signs
                        if medical_data.get("heart_rate"):
                            asyncio.create_task(
                                self.mqtt_monitor.store_medical_data(
                                    patient_id, "heart_rate", 
                                    {"heart_rate": medical_data["heart_rate"]}, 
                                    device_type
                                )
                            )
                        
                        # Store blood pressure
                        if medical_data.get("blood_pressure"):
                            bp_data = medical_data["blood_pressure"]
                            if isinstance(bp_data, dict) and bp_data.get("systolic") and bp_data.get("diastolic"):
                                asyncio.create_task(
                                    self.mqtt_monitor.store_medical_data(
                                        patient_id, "blood_pressure",
                                        {"systolic": bp_data["systolic"], "diastolic": bp_data["diastolic"]},
                                        device_type
                                    )
                                )
                        
                        # Store SpO2
                        if medical_data.get("spO2"):
                            asyncio.create_task(
                                self.mqtt_monitor.store_medical_data(
                                    patient_id, "spo2",
                                    {"spo2": medical_data["spO2"]},
                                    device_type
                                )
                            )
                        
                        # Store body temperature
                        if medical_data.get("body_temperature"):
                            asyncio.create_task(
                                self.mqtt_monitor.store_medical_data(
                                    patient_id, "body_temperature",
                                    {"body_temp": medical_data["body_temperature"]},
                                    device_type
                                )
                            )
                    
                    elif msg.topic == "iMEDE_watch/hb":
                        # Kati Watch step count
                        if medical_data.get("step"):
                            asyncio.create_task(
                                self.mqtt_monitor.store_medical_data(
                                    patient_id, "steps",
                                    {"steps": medical_data["step"]},
                                    device_type
                                )
                            )
                    
                    elif msg.topic == "dusun_sub":
                        # AVA4 medical device data
                        data_type = medical_data.get("data_type")
                        if data_type == "blood_pressure":
                            if medical_data.get("systolic") and medical_data.get("diastolic"):
                                asyncio.create_task(
                                    self.mqtt_monitor.store_medical_data(
                                        patient_id, "blood_pressure",
                                        {"systolic": medical_data["systolic"], "diastolic": medical_data["diastolic"]},
                                        device_type
                                    )
                                )
                        elif data_type == "spo2":
                            if medical_data.get("spo2"):
                                asyncio.create_task(
                                    self.mqtt_monitor.store_medical_data(
                                        patient_id, "spo2",
                                        {"spo2": medical_data["spo2"]},
                                        device_type
                                    )
                                )
                        elif data_type == "blood_sugar":
                            if medical_data.get("blood_glucose"):
                                asyncio.create_task(
                                    self.mqtt_monitor.store_medical_data(
                                        patient_id, "blood_sugar",
                                        {"blood_sugar": medical_data["blood_glucose"]},
                                        device_type
                                    )
                                )
                        elif data_type == "body_temperature":
                            if medical_data.get("body_temp"):
                                asyncio.create_task(
                                    self.mqtt_monitor.store_medical_data(
                                        patient_id, "body_temperature",
                                        {"body_temp": medical_data["body_temp"]},
                                        device_type
                                    )
                                )
                        elif data_type == "weight":
                            if medical_data.get("weight"):
                                asyncio.create_task(
                                    self.mqtt_monitor.store_medical_data(
                                        patient_id, "weight",
                                        {"weight": medical_data["weight"]},
                                        device_type
                                    )
                                )
                    
                    elif msg.topic == "CM4_BLE_GW_TX" and payload.get('type') == "reportAttribute":
                        # Qube-Vital medical device data
                        data_type = medical_data.get("data_type")
                        if data_type == "blood_pressure":
                            if medical_data.get("systolic") and medical_data.get("diastolic"):
                                asyncio.create_task(
                                    self.mqtt_monitor.store_medical_data(
                                        patient_id, "blood_pressure",
                                        {"systolic": medical_data["systolic"], "diastolic": medical_data["diastolic"]},
                                        device_type
                                    )
                                )
                        elif data_type == "spo2":
                            if medical_data.get("spo2"):
                                asyncio.create_task(
                                    self.mqtt_monitor.store_medical_data(
                                        patient_id, "spo2",
                                        {"spo2": medical_data["spo2"]},
                                        device_type
                                    )
                                )
                        elif data_type == "blood_sugar":
                            if medical_data.get("blood_glucose"):
                                asyncio.create_task(
                                    self.mqtt_monitor.store_medical_data(
                                        patient_id, "blood_sugar",
                                        {"blood_sugar": medical_data["blood_glucose"]},
                                        device_type
                                    )
                                )
                        elif data_type == "body_temperature":
                            if medical_data.get("body_temp"):
                                asyncio.create_task(
                                    self.mqtt_monitor.store_medical_data(
                                        patient_id, "body_temperature",
                                        {"body_temp": medical_data["body_temp"]},
                                        device_type
                                    )
                                )
                        elif data_type == "weight":
                            if medical_data.get("weight"):
                                asyncio.create_task(
                                    self.mqtt_monitor.store_medical_data(
                                        patient_id, "weight",
                                        {"weight": medical_data["weight"]},
                                        device_type
                                    )
                                )
                    
                    # Log transaction for data processing
                    if self.mqtt_monitor.transaction_logger:
                        asyncio.create_task(
                            self.mqtt_monitor.transaction_logger.log_transaction(
                                operation="process_mqtt_message",
                                data_type=medical_data.get("data_type", "unknown"),
                                collection="mqtt_messages",
                                patient_id=patient_id,
                                status="success",
                                details=f"Processed {msg.topic} message for patient {patient_id}",
                                device_id=device_type
                            )
                        )
                
                # Add to history
                self.message_history.append(processed_message)
                if len(self.message_history) > self.max_history:
                    self.message_history.pop(0)
                
                # Broadcast to WebSocket clients (will be handled in async context)
                # Store message for async broadcast with proper type
                broadcast_message = {
                    "type": "mqtt_message",
                    "data": processed_message,
                    "timestamp": datetime.utcnow()
                }
                self.pending_messages.append(broadcast_message)
                
            except Exception as e:
                logger.error(f"Error processing MQTT message: {e}")
        
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
    
    async def broadcast_message(self, message: Dict[str, Any]):
        """Broadcast message to all connected WebSocket clients"""
        if not self.websocket_clients:
            return
        
        message_json = json.dumps(message, default=str)
        disconnected_clients = set()
        
        for client in self.websocket_clients:
            try:
                await client.send(message_json)
            except websockets.exceptions.ConnectionClosed:
                disconnected_clients.add(client)
            except Exception as e:
                logger.error(f"Error sending message to WebSocket client: {e}")
                disconnected_clients.add(client)
        
        # Remove disconnected clients
        self.websocket_clients -= disconnected_clients
        if disconnected_clients:
            logger.info(f"Removed {len(disconnected_clients)} disconnected WebSocket clients")
    
    async def handle_websocket(self, websocket, path):
        """Handle WebSocket connection"""
        logger.info(f"🔗 New WebSocket connection from {websocket.remote_address} on path: {path}")
        self.websocket_clients.add(websocket)
        
        try:
            # Send initial data
            initial_data = {
                "type": "initial_data",
                "message_history": self.message_history[-50:],  # Last 50 messages
                "statistics": self.mqtt_monitor.get_statistics(),
                "timestamp": datetime.utcnow()
            }
            await websocket.send(json.dumps(initial_data, default=str))
            logger.info(f"✅ Sent initial data to {websocket.remote_address}")
            
            # Keep connection alive and handle client messages
            async for message in websocket:
                try:
                    data = json.loads(message)
                    if data.get('type') == 'ping':
                        await websocket.send(json.dumps({"type": "pong"}))
                    elif data.get('type') == 'get_statistics':
                        stats = self.mqtt_monitor.get_statistics()
                        await websocket.send(json.dumps({
                            "type": "statistics",
                            "data": stats,
                            "timestamp": datetime.utcnow()
                        }, default=str))
                    elif data.get('type') == 'get_history':
                        limit = data.get('limit', 50)
                        history = self.message_history[-limit:]
                        await websocket.send(json.dumps({
                            "type": "history",
                            "data": history,
                            "timestamp": datetime.utcnow()
                        }, default=str))
                        
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON from WebSocket client: {message}")
                except Exception as e:
                    logger.error(f"Error handling WebSocket message: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"🔌 WebSocket connection closed: {websocket.remote_address}")
        except Exception as e:
            logger.error(f"❌ Error in WebSocket connection: {e}")
        finally:
            self.websocket_clients.discard(websocket)
            logger.info(f"🧹 Removed WebSocket client: {websocket.remote_address}")
    
    async def run(self):
        """Run the WebSocket server"""
        logger.info(f"🚀 Starting MQTT WebSocket Server on {self.ws_host}:{self.ws_port}")
        
        # Connect to MQTT broker
        self.mqtt_client = self.connect_mqtt()
        if not self.mqtt_client:
            logger.error("Failed to connect to MQTT broker")
            return
        
        # Start WebSocket server
        logger.info(f"🔧 Setting up WebSocket server on {self.ws_host}:{self.ws_port}")
        start_server = websockets.serve(
            self.handle_websocket,
            self.ws_host,
            self.ws_port
        )
        
        logger.info(f"✅ WebSocket server started on ws://{self.ws_host}:{self.ws_port}")
        logger.info(f"📡 Ready to accept WebSocket connections from any path")
        
        try:
            await start_server
            logger.info(f"🎯 WebSocket server is now listening for connections")
            
            # Start background task to process pending messages
            asyncio.create_task(self.process_pending_messages())
            logger.info(f"🔄 Background message processing task started")
            
            await asyncio.Future()  # Run forever
        except KeyboardInterrupt:
            logger.info("Shutting down MQTT WebSocket Server")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
        finally:
            if self.mqtt_client:
                self.mqtt_client.loop_stop()
                self.mqtt_client.disconnect()
            
            # Close database connections
            self.mqtt_monitor.close()
    
    async def process_pending_messages(self):
        """Background task to process pending messages"""
        while True:
            try:
                if self.pending_messages:
                    # Get all pending messages
                    messages = self.pending_messages.copy()
                    self.pending_messages.clear()
                    
                    # Broadcast each message
                    for message in messages:
                        await self.broadcast_message(message)
                
                await asyncio.sleep(0.1)  # Check every 100ms
            except Exception as e:
                logger.error(f"Error processing pending messages: {e}")
                await asyncio.sleep(1)  # Wait longer on error

if __name__ == "__main__":
    server = MQTTWebSocketServer()
    asyncio.run(server.run()) 