from typing import Dict, List, Set, Any, Optional
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime
import json
import asyncio
from uuid import uuid4
from config import logger
from app.services.cache_service import cache_service
from app.utils.json_encoder import MongoJSONEncoder

class ConnectionManager:
    """
    Manages WebSocket connections for real-time communication
    """
    
    def __init__(self):
        # Active connections: {connection_id: {"websocket": ws, "user_id": str, "subscriptions": set}}
        self.active_connections: Dict[str, Dict[str, Any]] = {}
        
        # User to connections mapping: {user_id: set(connection_ids)}
        self.user_connections: Dict[str, Set[str]] = {}
        
        # Room subscriptions: {room_name: set(connection_ids)}
        self.room_subscriptions: Dict[str, Set[str]] = {}
        
        # Connection metadata
        self.connection_metadata: Dict[str, Dict[str, Any]] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str, 
                     metadata: Optional[Dict[str, Any]] = None) -> str:
        """Accept a new WebSocket connection"""
        await websocket.accept()
        
        connection_id = str(uuid4())
        
        # Store connection
        self.active_connections[connection_id] = {
            "websocket": websocket,
            "user_id": user_id,
            "subscriptions": set(),
            "connected_at": datetime.utcnow()
        }
        
        # Map user to connection
        if user_id not in self.user_connections:
            self.user_connections[user_id] = set()
        self.user_connections[user_id].add(connection_id)
        
        # Store metadata
        if metadata:
            self.connection_metadata[connection_id] = metadata
        
        # Log connection
        logger.info(f"WebSocket connected: user={user_id}, connection={connection_id}")
        
        # Send connection confirmation
        await self.send_to_connection(connection_id, {
            "type": "connection",
            "status": "connected",
            "connection_id": connection_id,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        return connection_id
    
    async def disconnect(self, connection_id: str):
        """Remove a WebSocket connection"""
        if connection_id not in self.active_connections:
            return
        
        connection = self.active_connections[connection_id]
        user_id = connection["user_id"]
        
        # Remove from user connections
        if user_id in self.user_connections:
            self.user_connections[user_id].discard(connection_id)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]
        
        # Remove from all room subscriptions
        for room_name in list(connection["subscriptions"]):
            await self.leave_room(connection_id, room_name)
        
        # Remove connection
        del self.active_connections[connection_id]
        
        # Clean up metadata
        if connection_id in self.connection_metadata:
            del self.connection_metadata[connection_id]
        
        logger.info(f"WebSocket disconnected: user={user_id}, connection={connection_id}")
    
    async def subscribe_to_room(self, connection_id: str, room_name: str):
        """Subscribe a connection to a room"""
        if connection_id not in self.active_connections:
            return False
        
        # Add to room
        if room_name not in self.room_subscriptions:
            self.room_subscriptions[room_name] = set()
        self.room_subscriptions[room_name].add(connection_id)
        
        # Track subscription
        self.active_connections[connection_id]["subscriptions"].add(room_name)
        
        # Send confirmation
        await self.send_to_connection(connection_id, {
            "type": "subscription",
            "action": "joined",
            "room": room_name,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        logger.debug(f"Connection {connection_id} joined room {room_name}")
        return True
    
    async def leave_room(self, connection_id: str, room_name: str):
        """Remove a connection from a room"""
        if room_name in self.room_subscriptions:
            self.room_subscriptions[room_name].discard(connection_id)
            if not self.room_subscriptions[room_name]:
                del self.room_subscriptions[room_name]
        
        if connection_id in self.active_connections:
            self.active_connections[connection_id]["subscriptions"].discard(room_name)
        
        # Send confirmation
        await self.send_to_connection(connection_id, {
            "type": "subscription",
            "action": "left",
            "room": room_name,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        logger.debug(f"Connection {connection_id} left room {room_name}")
    
    async def send_to_connection(self, connection_id: str, data: Dict[str, Any]):
        """Send data to a specific connection"""
        if connection_id not in self.active_connections:
            return
        
        websocket = self.active_connections[connection_id]["websocket"]
        try:
            # Serialize with MongoDB encoder
            json_data = json.dumps(data, cls=MongoJSONEncoder)
            await websocket.send_text(json_data)
        except Exception as e:
            logger.error(f"Error sending to connection {connection_id}: {e}")
            await self.disconnect(connection_id)
    
    async def send_to_user(self, user_id: str, data: Dict[str, Any]):
        """Send data to all connections of a user"""
        if user_id not in self.user_connections:
            return
        
        # Send to all user connections
        tasks = []
        for connection_id in list(self.user_connections[user_id]):
            tasks.append(self.send_to_connection(connection_id, data))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def broadcast_to_room(self, room_name: str, data: Dict[str, Any], 
                               exclude_connection: Optional[str] = None):
        """Broadcast data to all connections in a room"""
        if room_name not in self.room_subscriptions:
            return
        
        # Send to all room connections
        tasks = []
        for connection_id in list(self.room_subscriptions[room_name]):
            if connection_id != exclude_connection:
                tasks.append(self.send_to_connection(connection_id, data))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def broadcast_to_all(self, data: Dict[str, Any]):
        """Broadcast data to all connected clients"""
        tasks = []
        for connection_id in list(self.active_connections.keys()):
            tasks.append(self.send_to_connection(connection_id, data))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    def get_connection_info(self, connection_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a connection"""
        if connection_id not in self.active_connections:
            return None
        
        conn = self.active_connections[connection_id]
        return {
            "connection_id": connection_id,
            "user_id": conn["user_id"],
            "subscriptions": list(conn["subscriptions"]),
            "connected_at": conn["connected_at"].isoformat(),
            "metadata": self.connection_metadata.get(connection_id, {})
        }
    
    def get_room_connections(self, room_name: str) -> List[str]:
        """Get all connections in a room"""
        return list(self.room_subscriptions.get(room_name, set()))
    
    def get_user_connections(self, user_id: str) -> List[str]:
        """Get all connections for a user"""
        return list(self.user_connections.get(user_id, set()))
    
    def get_stats(self) -> Dict[str, Any]:
        """Get connection statistics"""
        return {
            "total_connections": len(self.active_connections),
            "unique_users": len(self.user_connections),
            "active_rooms": len(self.room_subscriptions),
            "connections_by_room": {
                room: len(connections) 
                for room, connections in self.room_subscriptions.items()
            },
            "connections_by_user": {
                user: len(connections) 
                for user, connections in self.user_connections.items()
            }
        }


# Global connection manager instance
websocket_manager = ConnectionManager()


# Room name constants for different features
class Rooms:
    """WebSocket room names for different features"""
    
    # Patient-specific rooms
    PATIENT_UPDATES = "patient:{patient_id}"
    PATIENT_VITALS = "patient:{patient_id}:vitals"
    PATIENT_ALERTS = "patient:{patient_id}:alerts"
    
    # Hospital-specific rooms
    HOSPITAL_UPDATES = "hospital:{hospital_id}"
    HOSPITAL_ALERTS = "hospital:{hospital_id}:alerts"
    HOSPITAL_DEVICES = "hospital:{hospital_id}:devices"
    
    # Device-specific rooms
    DEVICE_DATA = "device:{device_type}:{device_id}"
    DEVICE_STATUS = "device:{device_type}:{device_id}:status"
    
    # Global rooms
    SYSTEM_ALERTS = "system:alerts"
    ADMIN_UPDATES = "admin:updates"
    
    @staticmethod
    def patient_updates(patient_id: str) -> str:
        return f"patient:{patient_id}"
    
    @staticmethod
    def patient_vitals(patient_id: str) -> str:
        return f"patient:{patient_id}:vitals"
    
    @staticmethod
    def patient_alerts(patient_id: str) -> str:
        return f"patient:{patient_id}:alerts"
    
    @staticmethod
    def hospital_updates(hospital_id: str) -> str:
        return f"hospital:{hospital_id}"
    
    @staticmethod
    def hospital_alerts(hospital_id: str) -> str:
        return f"hospital:{hospital_id}:alerts"
    
    @staticmethod
    def hospital_devices(hospital_id: str) -> str:
        return f"hospital:{hospital_id}:devices"
    
    @staticmethod
    def device_data(device_type: str, device_id: str) -> str:
        return f"device:{device_type}:{device_id}"
    
    @staticmethod
    def device_status(device_type: str, device_id: str) -> str:
        return f"device:{device_type}:{device_id}:status" 