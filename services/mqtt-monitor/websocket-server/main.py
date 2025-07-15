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
import aiohttp

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
        
        # Web Panel Configuration (for data flow events)
        self.web_panel_url = os.getenv('WEB_PANEL_URL', 'http://mqtt-panel:8098')
        
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
        
        # Data flow events history
        self.data_flow_history: list = []
        self.max_data_flow_history = 100
        
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
    
    async def handle_data_flow_event(self, flow_event: Dict[str, Any]):
        """Handle data flow event from web panel"""
        try:
            logger.info(f"Received data flow event: {flow_event.get('step')} - {flow_event.get('status')}")
            
            # Add to data flow history
            self.data_flow_history.append(flow_event)
            if len(self.data_flow_history) > self.max_data_flow_history:
                self.data_flow_history.pop(0)
            
            # Broadcast to WebSocket clients
            broadcast_message = {
                "type": "data_flow_update",
                "data": flow_event,
                "timestamp": datetime.utcnow()
            }
            await self.broadcast_message(broadcast_message)
            
        except Exception as e:
            logger.error(f"Error handling data flow event: {e}")
    
    async def handle_websocket(self, websocket, path):
        """Handle WebSocket connection"""
        logger.info(f"New WebSocket connection from {websocket.remote_address}")
        self.websocket_clients.add(websocket)
        
        try:
            # Send initial data
            initial_data = {
                "type": "initial_data",
                "message_history": self.message_history[-50:],  # Last 50 messages
                "data_flow_history": self.data_flow_history[-20:],  # Last 20 data flow events
                "statistics": self.mqtt_monitor.get_statistics(),
                "timestamp": datetime.utcnow()
            }
            await websocket.send(json.dumps(initial_data, default=str))
            
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
                    elif data.get('type') == 'data_flow_event':
                        # Handle data flow event from client
                        await self.handle_data_flow_event(data.get('data', {}))
                        
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON from WebSocket client: {message}")
                except Exception as e:
                    logger.error(f"Error handling WebSocket message: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"WebSocket connection closed: {websocket.remote_address}")
        except Exception as e:
            logger.error(f"Error in WebSocket connection: {e}")
        finally:
            self.websocket_clients.discard(websocket)
    
    async def run(self):
        """Run the WebSocket server"""
        logger.info(f"Starting MQTT WebSocket Server on {self.ws_host}:{self.ws_port}")
        
        # Connect to MQTT broker
        self.mqtt_client = self.connect_mqtt()
        if not self.mqtt_client:
            logger.error("Failed to connect to MQTT broker")
            return
        
        # Start WebSocket server
        start_server = websockets.serve(
            self.handle_websocket,
            self.ws_host,
            self.ws_port
        )
        
        logger.info(f"WebSocket server started on ws://{self.ws_host}:{self.ws_port}")
        
        try:
            await start_server
            
            # Start background task to process pending messages
            asyncio.create_task(self.process_pending_messages())
            
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