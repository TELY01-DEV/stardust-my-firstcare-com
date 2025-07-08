import json
import asyncio
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime
import redis.asyncio as redis
from app.services.websocket_manager import websocket_manager, Rooms
from app.utils.json_encoder import MongoJSONEncoder
from config import settings, logger

class RealtimeEventHandler:
    """
    Handles real-time event broadcasting using Redis Pub/Sub
    """
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.pubsub: Optional[redis.client.PubSub] = None
        self.listeners: Dict[str, List[Callable]] = {}
        self.is_listening = False
        self._listen_task: Optional[asyncio.Task] = None
    
    async def connect(self):
        """Connect to Redis for Pub/Sub"""
        try:
            self.redis_client = await redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            
            self.pubsub = self.redis_client.pubsub()
            logger.info("✅ Connected to Redis Pub/Sub for real-time events")
            
            # Start listening for events
            await self.start_listening()
            
        except Exception as e:
            logger.error(f"❌ Redis Pub/Sub connection failed: {e}")
            self.redis_client = None
    
    async def disconnect(self):
        """Disconnect from Redis Pub/Sub"""
        self.is_listening = False
        
        if self._listen_task:
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass
        
        if self.pubsub:
            await self.pubsub.close()
        
        if self.redis_client:
            await self.redis_client.close()
        
        logger.info("Disconnected from Redis Pub/Sub")
    
    async def start_listening(self):
        """Start listening for Redis Pub/Sub events"""
        if not self.pubsub:
            return
        
        self.is_listening = True
        self._listen_task = asyncio.create_task(self._listen_loop())
    
    async def _listen_loop(self):
        """Main loop for listening to Redis Pub/Sub messages"""
        try:
            # Subscribe to all channels
            await self.pubsub.psubscribe("realtime:*")
            
            while self.is_listening:
                try:
                    message = await self.pubsub.get_message(
                        ignore_subscribe_messages=True,
                        timeout=1.0
                    )
                    
                    if message and message["type"] == "pmessage":
                        channel = message["channel"]
                        data = json.loads(message["data"])
                        
                        # Process the message
                        await self._process_message(channel, data)
                        
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    logger.error(f"Error processing Pub/Sub message: {e}")
                    
        except asyncio.CancelledError:
            logger.info("Redis Pub/Sub listener cancelled")
        except Exception as e:
            logger.error(f"Redis Pub/Sub listener error: {e}")
    
    async def _process_message(self, channel: str, data: Dict[str, Any]):
        """Process a message from Redis Pub/Sub"""
        # Extract event type from channel (realtime:event_type)
        event_type = channel.split(":", 1)[1] if ":" in channel else channel
        
        # Call registered listeners
        if event_type in self.listeners:
            for listener in self.listeners[event_type]:
                try:
                    await listener(data)
                except Exception as e:
                    logger.error(f"Error in event listener for {event_type}: {e}")
        
        # Route to appropriate WebSocket rooms based on event type
        await self._route_to_websocket(event_type, data)
    
    async def _route_to_websocket(self, event_type: str, data: Dict[str, Any]):
        """Route events to appropriate WebSocket rooms"""
        
        # Patient vital signs update
        if event_type == "patient.vitals.update":
            patient_id = data.get("patient_id")
            if patient_id:
                await websocket_manager.broadcast_to_room(
                    Rooms.patient_vitals(patient_id),
                    {
                        "type": "vitals_update",
                        "data": data,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )
        
        # Patient alert
        elif event_type == "patient.alert":
            patient_id = data.get("patient_id")
            if patient_id:
                await websocket_manager.broadcast_to_room(
                    Rooms.patient_alerts(patient_id),
                    {
                        "type": "patient_alert",
                        "data": data,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )
        
        # Device data update
        elif event_type == "device.data.update":
            device_type = data.get("device_type")
            device_id = data.get("device_id")
            if device_type and device_id:
                await websocket_manager.broadcast_to_room(
                    Rooms.device_data(device_type, device_id),
                    {
                        "type": "device_data",
                        "data": data,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )
        
        # Device status change
        elif event_type == "device.status.change":
            device_type = data.get("device_type")
            device_id = data.get("device_id")
            if device_type and device_id:
                await websocket_manager.broadcast_to_room(
                    Rooms.device_status(device_type, device_id),
                    {
                        "type": "device_status",
                        "data": data,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )
        
        # Hospital alert
        elif event_type == "hospital.alert":
            hospital_id = data.get("hospital_id")
            if hospital_id:
                await websocket_manager.broadcast_to_room(
                    Rooms.hospital_alerts(hospital_id),
                    {
                        "type": "hospital_alert",
                        "data": data,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )
        
        # System-wide alert
        elif event_type == "system.alert":
            await websocket_manager.broadcast_to_room(
                Rooms.SYSTEM_ALERTS,
                {
                    "type": "system_alert",
                    "data": data,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
    
    async def publish_event(self, event_type: str, data: Dict[str, Any]):
        """Publish an event to Redis Pub/Sub"""
        if not self.redis_client:
            logger.warning(f"Cannot publish event {event_type}: Redis not connected")
            return
        
        try:
            channel = f"realtime:{event_type}"
            message = json.dumps(data, cls=MongoJSONEncoder)
            
            await self.redis_client.publish(channel, message)
            logger.debug(f"Published event to {channel}")
            
        except Exception as e:
            logger.error(f"Error publishing event {event_type}: {e}")
    
    def register_listener(self, event_type: str, callback: Callable):
        """Register a callback for a specific event type"""
        if event_type not in self.listeners:
            self.listeners[event_type] = []
        self.listeners[event_type].append(callback)
    
    def unregister_listener(self, event_type: str, callback: Callable):
        """Unregister a callback for a specific event type"""
        if event_type in self.listeners:
            self.listeners[event_type].remove(callback)
            if not self.listeners[event_type]:
                del self.listeners[event_type]
    
    # Convenience methods for common events
    
    async def publish_patient_vitals(self, patient_id: str, vitals_data: Dict[str, Any]):
        """Publish patient vitals update"""
        await self.publish_event("patient.vitals.update", {
            "patient_id": patient_id,
            "vitals": vitals_data,
            "recorded_at": datetime.utcnow().isoformat()
        })
    
    async def publish_patient_alert(self, patient_id: str, alert_type: str, 
                                   severity: str, message: str, data: Optional[Dict] = None):
        """Publish patient alert"""
        await self.publish_event("patient.alert", {
            "patient_id": patient_id,
            "alert_type": alert_type,
            "severity": severity,
            "message": message,
            "data": data or {},
            "created_at": datetime.utcnow().isoformat()
        })
    
    async def publish_device_data(self, device_type: str, device_id: str, 
                                 data_type: str, values: Dict[str, Any]):
        """Publish device data update"""
        await self.publish_event("device.data.update", {
            "device_type": device_type,
            "device_id": device_id,
            "data_type": data_type,
            "values": values,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    async def publish_device_status(self, device_type: str, device_id: str, 
                                   status: str, details: Optional[Dict] = None):
        """Publish device status change"""
        await self.publish_event("device.status.change", {
            "device_type": device_type,
            "device_id": device_id,
            "status": status,
            "details": details or {},
            "changed_at": datetime.utcnow().isoformat()
        })
    
    async def publish_hospital_alert(self, hospital_id: str, alert_type: str, 
                                    message: str, data: Optional[Dict] = None):
        """Publish hospital alert"""
        await self.publish_event("hospital.alert", {
            "hospital_id": hospital_id,
            "alert_type": alert_type,
            "message": message,
            "data": data or {},
            "created_at": datetime.utcnow().isoformat()
        })
    
    async def publish_system_alert(self, alert_type: str, severity: str, 
                                  message: str, data: Optional[Dict] = None):
        """Publish system-wide alert"""
        await self.publish_event("system.alert", {
            "alert_type": alert_type,
            "severity": severity,
            "message": message,
            "data": data or {},
            "created_at": datetime.utcnow().isoformat()
        })


# Global event handler instance
realtime_events = RealtimeEventHandler()


# Event types for reference
class EventTypes:
    """Real-time event type constants"""
    
    # Patient events
    PATIENT_VITALS_UPDATE = "patient.vitals.update"
    PATIENT_ALERT = "patient.alert"
    PATIENT_STATUS_CHANGE = "patient.status.change"
    PATIENT_ADMISSION = "patient.admission"
    PATIENT_DISCHARGE = "patient.discharge"
    
    # Device events
    DEVICE_DATA_UPDATE = "device.data.update"
    DEVICE_STATUS_CHANGE = "device.status.change"
    DEVICE_CONNECTED = "device.connected"
    DEVICE_DISCONNECTED = "device.disconnected"
    DEVICE_ALERT = "device.alert"
    
    # Hospital events
    HOSPITAL_ALERT = "hospital.alert"
    HOSPITAL_CAPACITY_UPDATE = "hospital.capacity.update"
    HOSPITAL_EMERGENCY = "hospital.emergency"
    
    # System events
    SYSTEM_ALERT = "system.alert"
    SYSTEM_MAINTENANCE = "system.maintenance"
    SYSTEM_UPDATE = "system.update" 