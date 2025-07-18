#!/usr/bin/env python3
"""
MQTT Monitor Web Panel
Real-time monitoring dashboard for MQTT messages and patient mapping
Enhanced with Emergency Alert Monitoring and Redis-based real-time data fetching
"""

import os
import json
import logging
from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import Optional
from flask import Flask, render_template, jsonify, request, redirect, url_for, session
from flask_socketio import SocketIO, emit
import requests
import sys
import pymongo
from bson import ObjectId
import asyncio
import websockets
import threading
import time
import redis

# Add shared utilities to path
sys.path.append('/app/shared')

from mqtt_monitor import MQTTMonitor

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'mqtt-monitor-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*")

# Redis Configuration
REDIS_URL = os.getenv('REDIS_URL', 'redis://redis:6374/1')
redis_client = redis.from_url(REDIS_URL, decode_responses=True)

# Redis keys for real-time data
REDIS_KEYS = {
    'recent_events': 'mqtt_monitor:recent_events',
    'event_stats': 'mqtt_monitor:event_stats',
    'live_events': 'mqtt_monitor:live_events',
    'device_status': 'mqtt_monitor:device_status',
    'patient_updates': 'mqtt_monitor:patient_updates',
    'emergency_alerts': 'mqtt_monitor:emergency_alerts'
}

# JWT Authentication Configuration
JWT_AUTH_BASE_URL = os.environ.get('JWT_AUTH_BASE_URL', 'https://stardust-v1.my-firstcare.com')
JWT_LOGIN_ENDPOINT = os.environ.get('JWT_LOGIN_ENDPOINT', '/auth/login')
JWT_ME_ENDPOINT = os.environ.get('JWT_ME_ENDPOINT', '/auth/me')

# Google Maps API Configuration
GOOGLE_MAPS_API_KEY = os.environ.get('GOOGLE_MAPS_API_KEY', 'AIzaSyB41DRUbKWJHPxaFjMAwdrzWzbVKartNGg')

# Initialize MQTT monitor
mongodb_uri = os.getenv('MONGODB_URI')
mongodb_database = os.getenv('MONGODB_DATABASE', 'AMY')
mqtt_monitor = MQTTMonitor(mongodb_uri, mongodb_database)

# Emergency alert settings
EMERGENCY_PRIORITIES = {
    'CRITICAL': {'color': '#ff0000', 'icon': '🚨'},
    'HIGH': {'color': '#ff6600', 'icon': '⚠️'},
    'MEDIUM': {'color': '#ffff00', 'icon': '⚡'},
    'LOW': {'color': '#00ff00', 'icon': 'ℹ️'}
}

# Event log settings
EVENT_LOG_COLLECTION = 'event_logs'
EVENT_LOG_TTL_DAYS = 30  # Keep events for 30 days

def redis_cache_event(event_data: dict, max_events: int = 1000):
    """Cache event in Redis for real-time access"""
    try:
        # Convert event data to JSON serializable format
        def convert_for_redis(obj):
            if isinstance(obj, dict):
                return {k: convert_for_redis(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_for_redis(item) for item in obj]
            elif hasattr(obj, 'isoformat'):
                return obj.isoformat()
            elif hasattr(obj, '__str__'):
                return str(obj)
            else:
                return obj
        
        # Convert the event data
        serializable_event = convert_for_redis(event_data)
        
        # Add timestamp if not present
        if 'timestamp' not in serializable_event:
            serializable_event['timestamp'] = datetime.now(timezone.utc).isoformat()
        
        # Store in recent events list (FIFO)
        redis_client.lpush(REDIS_KEYS['recent_events'], json.dumps(serializable_event))
        redis_client.ltrim(REDIS_KEYS['recent_events'], 0, max_events - 1)
        
        # Store in live events for real-time streaming
        event_id = f"{serializable_event.get('source', 'unknown')}_{serializable_event.get('timestamp', '')}"
        redis_client.hset(REDIS_KEYS['live_events'], event_id, json.dumps(serializable_event))
        
        # Set TTL for live events (1 hour)
        redis_client.expire(REDIS_KEYS['live_events'], 3600)
        
        # Update event statistics
        update_redis_event_stats(serializable_event)
        
        logger.debug(f"✅ Event cached in Redis: {event_id}")
        return True
    except Exception as e:
        logger.error(f"❌ Error caching event in Redis: {e}")
        return False

def update_redis_event_stats(event_data: dict):
    """Update event statistics in Redis"""
    try:
        source = event_data.get('source', 'unknown')
        event_type = event_data.get('event_type', 'unknown')
        status = event_data.get('status', 'info')
        
        # Increment counters
        redis_client.hincrby(f"{REDIS_KEYS['event_stats']}:source", source, 1)
        redis_client.hincrby(f"{REDIS_KEYS['event_stats']}:type", event_type, 1)
        redis_client.hincrby(f"{REDIS_KEYS['event_stats']}:status", status, 1)
        
        # Update total count
        redis_client.incr(f"{REDIS_KEYS['event_stats']}:total")
        
        # Set TTL for stats (24 hours)
        redis_client.expire(f"{REDIS_KEYS['event_stats']}:source", 86400)
        redis_client.expire(f"{REDIS_KEYS['event_stats']}:type", 86400)
        redis_client.expire(f"{REDIS_KEYS['event_stats']}:status", 86400)
        redis_client.expire(f"{REDIS_KEYS['event_stats']}:total", 86400)
        
    except Exception as e:
        logger.error(f"❌ Error updating Redis event stats: {e}")

def get_redis_recent_events(limit: int = 100) -> list:
    """Get recent events from Redis cache"""
    try:
        events = redis_client.lrange(REDIS_KEYS['recent_events'], 0, limit - 1)
        return [json.loads(event) for event in events]
    except Exception as e:
        logger.error(f"❌ Error getting recent events from Redis: {e}")
        return []

def get_redis_event_stats() -> dict:
    """Get event statistics from Redis"""
    try:
        stats = {
            'total': int(redis_client.get(f"{REDIS_KEYS['event_stats']}:total") or 0),
            'by_source': redis_client.hgetall(f"{REDIS_KEYS['event_stats']}:source"),
            'by_type': redis_client.hgetall(f"{REDIS_KEYS['event_stats']}:type"),
            'by_status': redis_client.hgetall(f"{REDIS_KEYS['event_stats']}:status")
        }
        
        # Convert string values to integers
        for key in ['by_source', 'by_type', 'by_status']:
            stats[key] = {k: int(v) for k, v in stats[key].items()}
        
        return stats
    except Exception as e:
        logger.error(f"❌ Error getting event stats from Redis: {e}")
        return {'total': 0, 'by_source': {}, 'by_type': {}, 'by_status': {}}

def broadcast_redis_event(event_data: dict):
    """Broadcast event to all connected Socket.IO clients"""
    try:
        # Convert event data to JSON serializable format
        def convert_for_broadcast(obj):
            if isinstance(obj, dict):
                return {k: convert_for_broadcast(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_for_broadcast(item) for item in obj]
            elif hasattr(obj, 'isoformat'):
                return obj.isoformat()
            elif hasattr(obj, '__str__'):
                return str(obj)
            else:
                return obj
        
        serializable_event = convert_for_broadcast(event_data)
        
        socketio.emit('real_time_event', {
            'type': 'new_event',
            'data': serializable_event,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        logger.debug(f"📡 Event broadcasted via Socket.IO: {serializable_event.get('event_type', 'unknown')}")
    except Exception as e:
        logger.error(f"❌ Error broadcasting Redis event: {e}")

def create_event_log_indexes():
    """Create indexes for event log collection"""
    try:
        collection = mqtt_monitor.db[EVENT_LOG_COLLECTION]
        # Create TTL index to automatically delete old events
        collection.create_index("timestamp", expireAfterSeconds=EVENT_LOG_TTL_DAYS * 24 * 60 * 60)
        # Create indexes for common queries
        collection.create_index("source")
        collection.create_index("device_id")
        collection.create_index("event_type")
        collection.create_index("status")
        collection.create_index([("timestamp", -1)])  # For sorting by newest first
        logger.info("✅ Event log indexes created successfully")
    except Exception as e:
        logger.error(f"❌ Error creating event log indexes: {e}")

# Initialize event log indexes
create_event_log_indexes()

def login_required(f):
    """Decorator to require JWT authentication - TEMPORARILY DISABLED"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # TEMPORARILY DISABLED FOR TESTING
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
@login_required
def index():
    """Main dashboard page"""
    logger.info("Dashboard page accessed")
    return render_template('index.html', timestamp=int(time.time()))

@app.route('/data-flow')
def data_flow_dashboard():
    """Complete data flow monitoring dashboard"""
    logger.info("Data Flow page accessed")
    return render_template('data-flow-dashboard.html')

@app.route('/data-flow-test')
def data_flow_test():
    """Simple data flow test page (no auth required)"""
    logger.info("Data Flow Test page accessed")
    return render_template('data-flow-test.html')

@app.route('/data-flow-main')
def data_flow_main():
    """Main data flow page without authentication (for testing)"""
    logger.info("Data Flow Main page accessed")
    return render_template('data-flow-dashboard.html')

@app.route('/data-flow-noauth')
def data_flow_noauth():
    """Data flow page without any authentication (for testing)"""
    logger.info("Data Flow NoAuth page accessed")
    return render_template('data-flow-dashboard.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page and authentication"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            return render_template('login.html', error='Username and password are required')
        
        try:
            # Authenticate with Stardust-V1
            response = requests.post(
                f"{JWT_AUTH_BASE_URL}{JWT_LOGIN_ENDPOINT}",
                json={"username": username, "password": password},
                timeout=10
            )
            
            if response.status_code == 200:
                tokens = response.json()
                # Store JWT token in session
                session['jwt_token'] = tokens.get('access_token')
                session['refresh_token'] = tokens.get('refresh_token')
                session['user_info'] = tokens.get('user', {})
                logger.info(f"Login successful for user: {username}")
                return redirect(url_for('index'))
            else:
                logger.warning(f"Login failed for user {username}: {response.status_code}")
                return render_template('login.html', error='Invalid credentials')
                
        except requests.RequestException as e:
            logger.error(f"Login error: {e}")
            return render_template('login.html', error='Authentication service unavailable')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Logout and clear session"""
    session.clear()
    return redirect(url_for('login'))

@app.route('/api/statistics')
@login_required
def get_statistics():
    """Get MQTT statistics"""
    try:
        stats = mqtt_monitor.get_statistics()
        return jsonify({
            "success": True,
            "data": stats,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/patients')
@login_required
def get_patients():
    """Get patient list"""
    try:
        patients = list(mqtt_monitor.db.patients.find({}, {
            "_id": 1,
            "first_name": 1,
            "last_name": 1,
            "id_card": 1,
            "ava_mac_address": 1,
            "watch_mac_address": 1,
            "registration_status": 1
        }).limit(100))
        
        # Convert ObjectIds to strings recursively
        def convert_objectids(obj):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if isinstance(value, dict):
                        convert_objectids(value)
                    elif isinstance(value, list):
                        for item in value:
                            convert_objectids(item)
                    elif hasattr(value, '__class__') and value.__class__.__name__ == 'ObjectId':
                        obj[key] = str(value)
                    elif hasattr(value, 'isoformat'):  # Handle datetime objects
                        obj[key] = value.isoformat()
            elif isinstance(obj, list):
                for item in obj:
                    convert_objectids(item)
            return obj
        
        patients = convert_objectids(patients)
        
        return jsonify({
            "success": True,
            "data": patients,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    except Exception as e:
        logger.error(f"Error getting patients: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/devices')
@login_required
def get_devices():
    """Get device mappings"""
    try:
        # Get AVA4 devices
        ava4_devices = list(mqtt_monitor.db.amy_boxes.find({}, {
            "_id": 1,
            "mac_address": 1,
            "name": 1,
            "patient_id": 1
        }))
        
        # Get Kati devices
        kati_devices = list(mqtt_monitor.db.watches.find({}, {
            "_id": 1,
            "imei": 1,
            "patient_id": 1
        }))
        
        # Get Qube devices
        qube_devices = list(mqtt_monitor.db.hospitals.find({"mac_hv01_box": {"$exists": True}}, {
            "_id": 1,
            "name": 1,
            "mac_hv01_box": 1
        }))
        
        # Convert ObjectIds to strings recursively
        def convert_objectids(obj):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if isinstance(value, dict):
                        convert_objectids(value)
                    elif isinstance(value, list):
                        for item in value:
                            convert_objectids(item)
                    elif hasattr(value, '__class__') and value.__class__.__name__ == 'ObjectId':
                        obj[key] = str(value)
                    elif hasattr(value, 'isoformat'):  # Handle datetime objects
                        obj[key] = value.isoformat()
            elif isinstance(obj, list):
                for item in obj:
                    convert_objectids(item)
            return obj
        
        # Apply conversion to all devices
        ava4_devices = convert_objectids(ava4_devices)
        kati_devices = convert_objectids(kati_devices)
        qube_devices = convert_objectids(qube_devices)
        
        return jsonify({
            "success": True,
            "data": {
                "ava4": ava4_devices,
                "kati": kati_devices,
                "qube": qube_devices
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    except Exception as e:
        logger.error(f"Error getting devices: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@socketio.on('connect')
def handle_connect():
    """Handle WebSocket connection"""
    logger.info(f"Client connected: {request.sid}")
    emit('connected', {'data': 'Connected to MQTT Monitor'})
    
    # Send initial data to the client
    try:
        # Get initial statistics
        stats = mqtt_monitor.get_statistics()
        
        # Get recent MQTT messages from Redis events (for dashboard)
        recent_mqtt_messages = get_redis_recent_events(limit=20)
        
        # Get recent data flow events from database (for data flow pages)
        collection = mqtt_monitor.db['data_flow_events']
        recent_flow_events = list(collection.find().sort('timestamp', -1).limit(20))
        
        # Convert ObjectIds to strings
        def convert_objectids(obj):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if isinstance(value, dict):
                        convert_objectids(value)
                    elif isinstance(value, list):
                        for item in value:
                            convert_objectids(item)
                    elif hasattr(value, '__class__') and value.__class__.__name__ == 'ObjectId':
                        obj[key] = str(value)
                    elif hasattr(value, 'isoformat'):  # Handle datetime objects
                        obj[key] = value.isoformat()
            elif isinstance(obj, list):
                for item in obj:
                    convert_objectids(item)
            return obj
        
        recent_flow_events = convert_objectids(recent_flow_events)
        
        # Get initial data
        initial_data = {
            "type": "initial_data",
            "statistics": stats,
            "message_history": recent_mqtt_messages,  # Use MQTT messages for dashboard
            "flow_events": recent_flow_events,  # Use flow events for data flow pages
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        emit('initial_data', initial_data)
        logger.info(f"📊 Initial data sent to client: {request.sid} with {len(recent_mqtt_messages)} MQTT messages and {len(recent_flow_events)} flow events")
        
    except Exception as e:
        logger.error(f"Error sending initial data: {e}")
        emit('error', {'error': str(e)})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle WebSocket disconnection"""
    logger.info(f"Client disconnected: {request.sid}")

@socketio.on('get_statistics')
def handle_get_statistics():
    """Handle statistics request"""
    try:
        stats = mqtt_monitor.get_statistics()
        emit('statistics', {
            "data": stats,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        emit('error', {'error': str(e)})

@socketio.on('get_data_flow_events')
def handle_get_data_flow_events():
    """Handle data flow events request"""
    try:
        # Get recent data flow events from database
        collection = mqtt_monitor.db['data_flow_events']
        events = list(collection.find().sort('timestamp', -1).limit(50))
        
        # Convert ObjectIds to strings
        def convert_objectids(obj):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if isinstance(value, dict):
                        convert_objectids(value)
                    elif isinstance(value, list):
                        for item in value:
                            convert_objectids(item)
                    elif hasattr(value, '__class__') and value.__class__.__name__ == 'ObjectId':
                        obj[key] = str(value)
                    elif hasattr(value, 'isoformat'):  # Handle datetime objects
                        obj[key] = value.isoformat()
            elif isinstance(obj, list):
                for item in obj:
                    convert_objectids(item)
            return obj
        
        events = convert_objectids(events)
        
        emit('data_flow_events_response', {
            "success": True,
            "events": events
        })
        
    except Exception as e:
        logger.error(f"Error getting data flow events: {e}")
        emit('data_flow_events_response', {
            "success": False,
            "error": str(e)
        })

@socketio.on('get_streaming_events')
def handle_get_streaming_events():
    """Handle streaming events request"""
    try:
        # Get recent events for streaming dashboard
        collection = mqtt_monitor.db[EVENT_LOG_COLLECTION]
        events = list(collection.find().sort('timestamp', -1).limit(100))
        
        # Convert ObjectIds to strings
        def convert_objectids(obj):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if isinstance(value, dict):
                        convert_objectids(value)
                    elif isinstance(value, list):
                        for item in value:
                            convert_objectids(item)
                    elif hasattr(value, '__class__') and value.__class__.__name__ == 'ObjectId':
                        obj[key] = str(value)
                    elif hasattr(value, 'isoformat'):  # Handle datetime objects
                        obj[key] = value.isoformat()
            elif isinstance(obj, list):
                for item in obj:
                    convert_objectids(item)
            return obj
        
        events = convert_objectids(events)
        
        emit('streaming_events_response', {
            "success": True,
            "events": events
        })
        
    except Exception as e:
        logger.error(f"Error getting streaming events: {e}")
        emit('streaming_events_response', {
            "success": False,
            "error": str(e)
        })

@socketio.on('get_streaming_stats')
def handle_get_streaming_stats():
    """Handle streaming statistics request"""
    try:
        collection = mqtt_monitor.db[EVENT_LOG_COLLECTION]
        
        # Get stats for last hour
        one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
        
        # Total events in last hour
        total_1h = collection.count_documents({'timestamp': {'$gte': one_hour_ago}})
        
        # Events per minute (last 10 minutes)
        ten_minutes_ago = datetime.now(timezone.utc) - timedelta(minutes=10)
        events_10min = collection.count_documents({'timestamp': {'$gte': ten_minutes_ago}})
        events_per_minute = events_10min / 10
        
        # Error rate
        total_errors = collection.count_documents({
            'timestamp': {'$gte': one_hour_ago},
            'status': 'error'
        })
        error_rate = (total_errors / total_1h * 100) if total_1h > 0 else 0
        
        # Active devices (unique device IDs in last hour)
        active_devices = len(collection.distinct('device_id', {'timestamp': {'$gte': one_hour_ago}}))
        
        # Events by source
        sources = list(collection.aggregate([
            {'$match': {'timestamp': {'$gte': one_hour_ago}}},
            {'$group': {'_id': '$source', 'count': {'$sum': 1}}},
            {'$sort': {'count': -1}}
        ]))
        
        # Convert to dict for easier access
        source_dict = {s['_id']: s['count'] for s in sources}
        
        emit('streaming_stats_response', {
            "success": True,
            "stats": {
                "total_events": total_1h,
                "events_per_minute": round(events_per_minute, 1),
                "error_rate": round(error_rate, 1),
                "active_devices": active_devices,
                "sources": source_dict
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting streaming stats: {e}")
        emit('streaming_stats_response', {
            "success": False,
            "error": str(e)
        })

def broadcast_mqtt_message(message):
    """Broadcast MQTT message to all connected clients"""
    socketio.emit('mqtt_message', {
        "data": message,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })

# WebSocket clients for direct WebSocket connections
websocket_clients = set()
mqtt_message_history = []
max_mqtt_history = 100

def broadcast_data_flow_update(flow_data):
    """Broadcast data flow update to all connected clients"""
    logger.info(f"🔍 Broadcasting data flow update: {flow_data.get('step')} - {flow_data.get('status')}")
    try:
        socketio.emit('data_flow_update', {
            "type": "data_flow_update",
            "data": flow_data,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        logger.info("✅ Data flow update broadcasted successfully")
    except Exception as e:
        logger.error(f"❌ Error broadcasting data flow update: {e}")

async def broadcast_to_websocket_clients(message):
    """Broadcast message to all direct WebSocket clients"""
    try:
        # Access the global variable - ensure it exists
        global websocket_clients
        if not hasattr(broadcast_to_websocket_clients, '_websocket_clients'):
            broadcast_to_websocket_clients._websocket_clients = set()
        
        current_clients = websocket_clients if websocket_clients else broadcast_to_websocket_clients._websocket_clients
        if not current_clients:
            return
        
        message_json = json.dumps(message, default=str)
        disconnected_clients = set()
        
        for client in current_clients:
            try:
                await client.send(message_json)
            except Exception as e:
                logger.error(f"Error sending message to WebSocket client: {e}")
                disconnected_clients.add(client)
        
        # Remove disconnected clients
        current_clients -= disconnected_clients
        if disconnected_clients:
            logger.info(f"Removed {len(disconnected_clients)} disconnected WebSocket clients")
    except Exception as e:
        logger.error(f"Error in broadcast_to_websocket_clients: {e}")

async def forward_mqtt_messages():
    """Forward MQTT messages from WebSocket server to web panel clients"""
    while True:
        try:
            # Connect to WebSocket server
            uri = "ws://mqtt-websocket:8097"
            async with websockets.connect(uri) as websocket:
                logger.info("Connected to MQTT WebSocket server for message forwarding")
                
                async for message in websocket:
                    try:
                        data = json.loads(message)
                        if data.get('type') == 'mqtt_message':
                            # Add to history
                            mqtt_message_history.append(data['data'])
                            if len(mqtt_message_history) > max_mqtt_history:
                                mqtt_message_history.pop(0)
                            
                            # Broadcast to web panel clients
                            await broadcast_to_websocket_clients(data)
                    except json.JSONDecodeError:
                        logger.warning(f"Invalid JSON from WebSocket server: {message}")
                    except Exception as e:
                        logger.error(f"Error processing WebSocket message: {e}")
        except Exception as e:
            logger.error(f"WebSocket connection error: {e}")
            await asyncio.sleep(5)  # Wait before reconnecting

def start_mqtt_forwarding():
    """Start MQTT message forwarding in background thread"""
    def run_forwarding():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(forward_mqtt_messages())
    
    thread = threading.Thread(target=run_forwarding, daemon=True)
    thread.start()
    logger.info("MQTT message forwarding started")

# Start MQTT forwarding
start_mqtt_forwarding()

def create_data_flow_event(step: str, status: str, device_type: str, topic: str, 
                          payload: dict, patient_info: Optional[dict] = None, 
                          processed_data: Optional[dict] = None, error: Optional[str] = None) -> dict:
    """Create a standardized data flow event"""
    return {
        'step': step,
        'status': status,
        'device_type': device_type,
        'topic': topic,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'payload': payload,
        'patient_info': patient_info,
        'processed_data': processed_data,
        'error': error
    }

@app.route('/api/data-flow/events')
def get_data_flow_events():
    """Get recent data flow events"""
    try:
        # For now, return empty list - events are sent via broadcast
        return jsonify({
            "success": True,
            "data": [],
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    except Exception as e:
        logger.error(f"Error getting data flow events: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/data-flow/emit', methods=['POST'])
def emit_data_flow_event():
    """Emit a data flow event and store in event log with Redis caching"""
    try:
        data = request.get_json()
        if not data or 'event' not in data:
            return jsonify({"success": False, "error": "No event data provided"}), 400
        
        event = data['event']
        logger.info(f"📊 Received data flow event request: {data}")
        
        # Convert event to JSON serializable format
        def convert_for_json(obj):
            if isinstance(obj, dict):
                return {k: convert_for_json(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_for_json(item) for item in obj]
            elif hasattr(obj, 'isoformat'):
                return obj.isoformat()
            else:
                return obj
        
        converted_event = convert_for_json(event)
        logger.info(f"📊 Processing data flow event: {event.get('step')} - {event.get('status')}")
        logger.info(f"📊 Converted event: {converted_event}")
        
        # Store event in event_logs collection
        try:
            event_log_entry = {
                "timestamp": datetime.now(timezone.utc),
                "source": event.get('device_type', 'unknown'),
                "event_type": event.get('step', 'data_flow'),
                "status": event.get('status', 'info'),
                "device_id": (event.get('payload', {}) or {}).get('mac') or (event.get('payload', {}) or {}).get('IMEI') or 'unknown',
                "message": f"Data flow: {event.get('step')} - {event.get('status')} for {event.get('device_type', 'unknown')}",
                "details": {
                    "topic": event.get('topic'),
                    "payload": event.get('payload'),
                    "patient_info": event.get('patient_info'),
                    "processed_data": event.get('processed_data'),
                    "error": event.get('error')
                },
                "server_timestamp": datetime.now(timezone.utc).isoformat()
            }
            collection = mqtt_monitor.db[EVENT_LOG_COLLECTION]
            result = collection.insert_one(event_log_entry)
            logger.info(f"✅ Event stored in event_logs: {event.get('step')} - {event.get('status')} (ID: {result.inserted_id})")
            
            # Create a Redis-serializable version of the event
            redis_event = event_log_entry.copy()
            redis_event['timestamp'] = redis_event['timestamp'].isoformat()
            
            # Cache event in Redis for real-time access
            redis_cache_event(redis_event)
            
            # Broadcast to all connected clients via Redis
            broadcast_redis_event(redis_event)
            
        except Exception as db_error:
            logger.error(f"❌ Failed to store event in event_logs: {db_error}")
            # Continue with broadcasting even if storage fails
        
        # Broadcast to all connected clients (legacy)
        broadcast_data_flow_update(converted_event)
        logger.info("📊 Broadcasting data flow event to all clients")
        socketio.emit('data_flow_update', {
            "type": "data_flow_update",
            "data": converted_event,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        logger.info("📊 Data flow event broadcasted successfully")
        
        return jsonify({"success": True, "message": "Event broadcasted and stored successfully"})
        
    except Exception as e:
        logger.error(f"Error emitting data flow event: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/data-flow-event', methods=['POST'])
def receive_data_flow_event():
    """Receive data flow events from external sources"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No data provided"}), 400
        
        # Convert to JSON serializable format
        def convert_to_json_serializable(obj):
            if isinstance(obj, dict):
                return {k: convert_to_json_serializable(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_to_json_serializable(item) for item in obj]
            elif hasattr(obj, 'isoformat'):
                return obj.isoformat()
            else:
                return obj
        
        converted_data = convert_to_json_serializable(data)
        
        # Broadcast to all connected clients
        socketio.emit('data_flow_update', {
            "type": "data_flow_update",
            "data": converted_data,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        return jsonify({"success": True, "message": "Event received and broadcasted"})
        
    except Exception as e:
        logger.error(f"Error receiving data flow event: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/user/profile')
@login_required
def get_user_profile():
    """Get current user profile"""
    try:
        # Get user info from session
        user_info = session.get('user_info', {})
        
        if not user_info:
            return jsonify({
                "success": False,
                "error": "User not authenticated"
            }), 401
        
        return jsonify({
            "success": True,
            "data": {
                "username": user_info.get('username', 'Unknown'),
                "email": user_info.get('email', ''),
                "role": user_info.get('role', 'user'),
                "permissions": user_info.get('permissions', [])
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting user profile: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/devices')
@login_required
def devices_page():
    """Devices management page"""
    return render_template('devices.html')

@app.route('/patients')
@login_required
def patients_page():
    """Patients management page"""
    return render_template('patients.html', timestamp=int(time.time()))

@app.route('/messages')
@login_required
def messages_page():
    """Messages page"""
    return render_template('messages.html')

@app.route('/emergency')
@login_required
def emergency_dashboard():
    """Emergency alerts dashboard"""
    return render_template('emergency_dashboard.html', google_maps_api_key=GOOGLE_MAPS_API_KEY)

@app.route('/api/emergency-alerts')
@login_required
def get_emergency_alerts():
    """Get emergency alerts"""
    try:
        # Get query parameters
        hours = int(request.args.get('hours', 24))
        priority = request.args.get('priority')
        processed = request.args.get('processed')
        
        # Build query
        query = {}
        
        # Time filter
        yesterday = datetime.now(timezone.utc) - timedelta(hours=hours)
        query['timestamp'] = {'$gte': yesterday}
        
        # Priority filter
        if priority:
            query['priority'] = priority
        
        # Processed filter
        if processed is not None:
            query['processed'] = processed.lower() == 'true'
        
        # Get alerts from database
        collection = mqtt_monitor.db['emergency_alarm']
        alerts = list(collection.find(query).sort('timestamp', -1).limit(100))
        
        # Convert ObjectIds to strings
        def convert_objectids(obj):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if isinstance(value, dict):
                        convert_objectids(value)
                    elif isinstance(value, list):
                        for item in value:
                            convert_objectids(item)
                    elif hasattr(value, '__class__') and value.__class__.__name__ == 'ObjectId':
                        obj[key] = str(value)
                    elif hasattr(value, 'isoformat'):  # Handle datetime objects
                        obj[key] = value.isoformat()
            elif isinstance(obj, list):
                for item in obj:
                    convert_objectids(item)
            return obj
        
        alerts = convert_objectids(alerts)
        
        return jsonify({
            "success": True,
            "alerts": alerts,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting emergency alerts: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/emergency-stats')
@login_required
def get_emergency_stats():
    """Get emergency alert statistics"""
    try:
        collection = mqtt_monitor.db['emergency_alarm']
        
        # Get stats for last 24 hours
        yesterday = datetime.now(timezone.utc) - timedelta(hours=24)
        
        # Total alerts in last 24 hours
        total_24h = collection.count_documents({'timestamp': {'$gte': yesterday}})
        
        # Alerts by priority
        priorities = list(collection.aggregate([
            {'$match': {'timestamp': {'$gte': yesterday}}},
            {'$group': {'_id': '$priority', 'count': {'$sum': 1}}},
            {'$sort': {'count': -1}}
        ]))
        
        # Alerts by device type
        device_types = list(collection.aggregate([
            {'$match': {'timestamp': {'$gte': yesterday}}},
            {'$group': {'_id': '$device_type', 'count': {'$sum': 1}}},
            {'$sort': {'count': -1}}
        ]))
        
        # Processed vs unprocessed
        processed_stats = list(collection.aggregate([
            {'$match': {'timestamp': {'$gte': yesterday}}},
            {'$group': {'_id': '$processed', 'count': {'$sum': 1}}},
            {'$sort': {'count': -1}}
        ]))
        
        return jsonify({
            "success": True,
            "stats": {
                "total_24h": total_24h,
                "priorities": priorities,
                "device_types": device_types,
                "processed_stats": processed_stats
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting emergency stats: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/mark-processed/<alert_id>', methods=['POST'])
@login_required
def mark_alert_processed(alert_id):
    """Mark an emergency alert as processed"""
    try:
        collection = mqtt_monitor.db['emergency_alarm']
        
        # Update the alert
        result = collection.update_one(
            {'_id': ObjectId(alert_id)},
            {'$set': {'processed': True, 'processed_at': datetime.now(timezone.utc)}}
        )
        
        if result.modified_count > 0:
            # Broadcast update to connected clients
            socketio.emit('emergency_alert_processed', {
                'alert_id': alert_id,
                'processed_at': datetime.now(timezone.utc).isoformat()
            })
            
            return jsonify({
                "success": True,
                "message": "Alert marked as processed"
            })
        else:
            return jsonify({
                "success": False,
                "error": "Alert not found"
            }), 404
            
    except Exception as e:
        logger.error(f"Error marking alert as processed: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

def broadcast_emergency_alert(alert_data):
    """Broadcast emergency alert to all connected clients"""
    socketio.emit('emergency_alert', {
        "type": "emergency_alert",
        "data": alert_data,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })

@app.route('/event-log')
@login_required
def event_log_page():
    """Event log page"""
    logger.info("Event Log page accessed")
    return render_template('event-log.html')

@app.route('/event-streaming')
@login_required
def event_streaming_dashboard():
    """Real-time event streaming dashboard"""
    logger.info("Event Streaming Dashboard page accessed")
    return render_template('event-streaming-dashboard.html')

@app.route('/api/event-log', methods=['POST'])
def receive_event():
    """Receive events from listeners and monitors"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No data provided"}), 400
        
        # Validate required fields
        required_fields = ['timestamp', 'source', 'event_type', 'status']
        for field in required_fields:
            if field not in data:
                return jsonify({"success": False, "error": f"Missing required field: {field}"}), 400
        
        # Add server timestamp if not provided
        if 'server_timestamp' not in data:
            data['server_timestamp'] = datetime.now(timezone.utc).isoformat()
        
        # Store event in database
        collection = mqtt_monitor.db[EVENT_LOG_COLLECTION]
        result = collection.insert_one(data)
        
        # Convert ObjectId to string for broadcasting
        broadcast_data = data.copy()
        broadcast_data['_id'] = str(result.inserted_id)
        
        # Broadcast to connected clients
        socketio.emit('new_event_log', broadcast_data)
        
        logger.info(f"Event logged: {data['source']} - {data['event_type']} - {data['status']}")
        
        return jsonify({
            "success": True,
            "event_id": str(result.inserted_id),
            "message": "Event logged successfully"
        })
        
    except Exception as e:
        logger.error(f"Error receiving event: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/event-log', methods=['GET'])
@login_required
def get_events():
    """Get events with filtering and pagination"""
    try:
        # Get query parameters
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 50))
        source = request.args.get('source')
        device_id = request.args.get('device_id')
        event_type = request.args.get('event_type')
        status = request.args.get('status')
        start_time = request.args.get('start_time')
        end_time = request.args.get('end_time')
        search = request.args.get('search')
        
        # Build query filter
        query = {}
        
        if source:
            query['source'] = source
        if device_id:
            query['device_id'] = device_id
        if event_type:
            query['event_type'] = event_type
        if status:
            query['status'] = status
        if start_time or end_time:
            time_filter = {}
            if start_time:
                time_filter['$gte'] = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            if end_time:
                time_filter['$lte'] = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            query['timestamp'] = time_filter
        if search:
            query['$or'] = [
                {'device_id': {'$regex': search, '$options': 'i'}},
                {'patient': {'$regex': search, '$options': 'i'}},
                {'event_type': {'$regex': search, '$options': 'i'}},
                {'details.message': {'$regex': search, '$options': 'i'}}
            ]
        
        # Get total count
        collection = mqtt_monitor.db[EVENT_LOG_COLLECTION]
        total_count = collection.count_documents(query)
        
        # Get paginated results
        skip = (page - 1) * limit
        events = list(collection.find(query).sort('timestamp', -1).skip(skip).limit(limit))
        
        # Convert ObjectIds to strings
        def convert_objectids(obj):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if isinstance(value, dict):
                        convert_objectids(value)
                    elif isinstance(value, list):
                        for item in value:
                            convert_objectids(item)
                    elif hasattr(value, '__class__') and value.__class__.__name__ == 'ObjectId':
                        obj[key] = str(value)
                    elif hasattr(value, 'isoformat'):  # Handle datetime objects
                        obj[key] = value.isoformat()
            elif isinstance(obj, list):
                for item in obj:
                    convert_objectids(item)
            return obj
        
        events = convert_objectids(events)
        
        return jsonify({
            "success": True,
            "data": {
                "events": events,
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total": total_count,
                    "pages": (total_count + limit - 1) // limit
                }
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting events: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/event-log/stats')
@login_required
def get_event_stats():
    """Get event statistics"""
    try:
        collection = mqtt_monitor.db[EVENT_LOG_COLLECTION]
        
        # Get stats for last 24 hours
        yesterday = datetime.now(timezone.utc) - timedelta(days=1)
        
        # Total events in last 24 hours
        total_24h = collection.count_documents({'timestamp': {'$gte': yesterday}})
        
        # Events by source
        sources = list(collection.aggregate([
            {'$match': {'timestamp': {'$gte': yesterday}}},
            {'$group': {'_id': '$source', 'count': {'$sum': 1}}},
            {'$sort': {'count': -1}}
        ]))
        
        # Events by status
        statuses = list(collection.aggregate([
            {'$match': {'timestamp': {'$gte': yesterday}}},
            {'$group': {'_id': '$status', 'count': {'$sum': 1}}},
            {'$sort': {'count': -1}}
        ]))
        
        # Events by event type
        event_types = list(collection.aggregate([
            {'$match': {'timestamp': {'$gte': yesterday}}},
            {'$group': {'_id': '$event_type', 'count': {'$sum': 1}}},
            {'$sort': {'count': -1}}
        ]))
        
        return jsonify({
            "success": True,
            "data": {
                "total_24h": total_24h,
                "sources": sources,
                "statuses": statuses,
                "event_types": event_types
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting event stats: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/event-log/export')
@login_required
def export_events():
    """Export events as CSV"""
    try:
        # Get query parameters (same as get_events)
        source = request.args.get('source')
        device_id = request.args.get('device_id')
        event_type = request.args.get('event_type')
        status = request.args.get('status')
        start_time = request.args.get('start_time')
        end_time = request.args.get('end_time')
        
        # Build query filter
        query = {}
        
        if source:
            query['source'] = source
        if device_id:
            query['device_id'] = device_id
        if event_type:
            query['event_type'] = event_type
        if status:
            query['status'] = status
        if start_time or end_time:
            time_filter = {}
            if start_time:
                time_filter['$gte'] = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            if end_time:
                time_filter['$lte'] = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            query['timestamp'] = time_filter
        
        # Get events (limit to 1000 for export)
        collection = mqtt_monitor.db[EVENT_LOG_COLLECTION]
        events = list(collection.find(query).sort('timestamp', -1).limit(1000))
        
        # Convert to CSV format
        import csv
        from io import StringIO
        
        output = StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            'Timestamp', 'Source', 'Event Type', 'Status', 'Device ID', 
            'Patient', 'Topic', 'Medical Data', 'Error', 'Details'
        ])
        
        # Write data
        for event in events:
            writer.writerow([
                event.get('timestamp', ''),
                event.get('source', ''),
                event.get('event_type', ''),
                event.get('status', ''),
                event.get('device_id', ''),
                event.get('patient', ''),
                event.get('topic', ''),
                event.get('medical_data', ''),
                event.get('error', ''),
                json.dumps(event.get('details', {}))
            ])
        
        output.seek(0)
        
        from flask import Response
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': 'attachment; filename=event_log.csv'}
        )
        
    except Exception as e:
        logger.error(f"Error exporting events: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/streaming/events')
@login_required
def get_streaming_events():
    """Get events for streaming dashboard with real-time updates"""
    try:
        # Get query parameters
        limit = int(request.args.get('limit', 100))
        source = request.args.get('source')
        event_type = request.args.get('event_type')
        status = request.args.get('status')
        time_range = request.args.get('time_range', '1440')  # Default to 24 hours instead of 60 minutes
        
        # Build query filter
        query = {}
        
        if source:
            query['source'] = source
        if event_type:
            query['event_type'] = event_type
        if status:
            query['status'] = status
        
        # Time range filter - use more flexible approach
        if time_range != 'all':
            try:
                minutes_ago = datetime.now(timezone.utc) - timedelta(minutes=int(time_range))
                # Use string comparison for timestamps since they might be stored as strings
                query['timestamp'] = {'$gte': minutes_ago.isoformat()}
            except ValueError:
                # If time_range is invalid, don't apply time filter
                pass
        
        # Get events
        collection = mqtt_monitor.db[EVENT_LOG_COLLECTION]
        events = list(collection.find(query).sort('timestamp', -1).limit(limit))
        
        # Convert ObjectIds to strings
        def convert_objectids(obj):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if isinstance(value, dict):
                        convert_objectids(value)
                    elif isinstance(value, list):
                        for item in value:
                            convert_objectids(item)
                    elif hasattr(value, '__class__') and value.__class__.__name__ == 'ObjectId':
                        obj[key] = str(value)
                    elif hasattr(value, 'isoformat'):  # Handle datetime objects
                        obj[key] = value.isoformat()
            elif isinstance(obj, list):
                for item in obj:
                    convert_objectids(item)
            return obj
        
        events = convert_objectids(events)
        
        return jsonify({
            "success": True,
            "data": {
                "events": events,
                "total": len(events),
                "limit": limit
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting streaming events: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/streaming/stats')
@login_required
def get_streaming_stats():
    """Get real-time statistics for streaming dashboard"""
    try:
        collection = mqtt_monitor.db[EVENT_LOG_COLLECTION]
        
        # Get stats for different time periods
        now = datetime.now(timezone.utc)
        one_hour_ago = now - timedelta(hours=1)
        ten_minutes_ago = now - timedelta(minutes=10)
        one_minute_ago = now - timedelta(minutes=1)
        
        # Convert to string format for comparison (since some timestamps might be strings)
        one_hour_ago_str = one_hour_ago.isoformat()
        ten_minutes_ago_str = ten_minutes_ago.isoformat()
        one_minute_ago_str = one_minute_ago.isoformat()
        
        # Get all events and filter by timestamp in Python (more reliable)
        all_events = list(collection.find())
        
        # Helper function to parse timestamp
        def parse_timestamp(ts):
            if isinstance(ts, str):
                try:
                    # Try to parse ISO format
                    if 'T' in ts and '+' in ts:
                        return datetime.fromisoformat(ts.replace('Z', '+00:00'))
                    elif 'T' in ts:
                        return datetime.fromisoformat(ts + '+00:00')
                    else:
                        # For non-ISO format, assume UTC
                        dt = datetime.strptime(ts, '%Y-%m-%d %H:%M:%S')
                        return dt.replace(tzinfo=timezone.utc)
                except:
                    return None
            elif isinstance(ts, datetime):
                # Ensure timezone-aware
                if ts.tzinfo is None:
                    return ts.replace(tzinfo=timezone.utc)
                return ts
            return None
        
        # Filter events by time periods
        events_1h = []
        events_10min = []
        events_1min = []
        
        for event in all_events:
            ts = parse_timestamp(event.get('timestamp'))
            if ts:
                # Ensure both timestamps are timezone-aware for comparison
                try:
                    if ts.tzinfo is None:
                        ts = ts.replace(tzinfo=timezone.utc)
                    
                    if ts >= one_hour_ago:
                        events_1h.append(event)
                    if ts >= ten_minutes_ago:
                        events_10min.append(event)
                    if ts >= one_minute_ago:
                        events_1min.append(event)
                except Exception as e:
                    logger.warning(f"Error comparing timestamps: {e}, skipping event")
                    continue
        
        # Calculate statistics
        total_1h = len(events_1h)
        total_10min = len(events_10min)
        total_1min = len(events_1min)
        
        # Events per minute (based on last 10 minutes)
        events_per_minute = total_10min / 10 if total_10min > 0 else 0
        
        # Error rate
        errors_1h = len([e for e in events_1h if e.get('status') == 'error'])
        error_rate = (errors_1h / total_1h * 100) if total_1h > 0 else 0
        
        # Active devices
        active_devices = len(set(e.get('device_id') for e in events_1h if e.get('device_id')))
        
        # Events by source
        source_counts = {}
        for event in events_1h:
            source = event.get('source')
            if source:
                source_counts[source] = source_counts.get(source, 0) + 1
        
        sources = [{'source': source, 'count': count} for source, count in source_counts.items()]
        sources.sort(key=lambda x: x['count'], reverse=True)
        
        # Events by type
        type_counts = {}
        for event in events_1h:
            event_type = event.get('event_type')
            if event_type:
                type_counts[event_type] = type_counts.get(event_type, 0) + 1
        
        event_types = [{'type': event_type, 'count': count} for event_type, count in type_counts.items()]
        event_types.sort(key=lambda x: x['count'], reverse=True)
        
        # Recent timeline data (last 50 events for timeline visualization)
        timeline_events = list(collection.find().sort('timestamp', -1).limit(50))
        
        # Convert ObjectIds to strings recursively
        def convert_objectids(obj):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if isinstance(value, dict):
                        convert_objectids(value)
                    elif isinstance(value, list):
                        for item in value:
                            convert_objectids(item)
                    elif hasattr(value, '__class__') and value.__class__.__name__ == 'ObjectId':
                        obj[key] = str(value)
                    elif hasattr(value, 'isoformat'):  # Handle datetime objects
                        obj[key] = value.isoformat()
            elif isinstance(obj, list):
                for item in obj:
                    convert_objectids(item)
            return obj
        
        # Convert ObjectIds in timeline events
        timeline_events = convert_objectids(timeline_events)
        
        return jsonify({
            "success": True,
            "data": {
                "total_events": total_1h,
                "events_per_minute": round(events_per_minute, 1),
                "events_last_minute": total_1min,
                "error_rate": round(error_rate, 1),
                "active_devices": active_devices,
                "sources": sources,
                "event_types": event_types,
                "timeline_events": timeline_events
            },
            "timestamp": now
        })
        
    except Exception as e:
        logger.error(f"Error getting streaming stats: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/streaming/correlation')
@login_required
def get_event_correlation():
    """Get event correlation data for visualization"""
    try:
        collection = mqtt_monitor.db[EVENT_LOG_COLLECTION]
        
        # Get events from last hour for correlation analysis
        one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
        
        # Get events with device and patient information
        events = list(collection.find({
            'timestamp': {'$gte': one_hour_ago}
        }).sort('timestamp', -1).limit(1000))
        
        # Analyze correlations
        correlations = {
            'device_patient_pairs': {},
            'event_sequences': {},
            'error_patterns': {},
            'source_patterns': {}
        }
        
        # Device-patient correlation
        for event in events:
            device_id = event.get('device_id')
            patient_id = event.get('patient_id')
            if device_id and patient_id:
                key = f"{device_id}_{patient_id}"
                if key not in correlations['device_patient_pairs']:
                    correlations['device_patient_pairs'][key] = {
                        'device_id': device_id,
                        'patient_id': patient_id,
                        'event_count': 0,
                        'last_event': None
                    }
                correlations['device_patient_pairs'][key]['event_count'] += 1
                correlations['device_patient_pairs'][key]['last_event'] = event.get('timestamp')
        
        # Event sequences (events happening within 5 minutes of each other)
        for i, event in enumerate(events):
            event_time = event.get('timestamp')
            if event_time:
                sequence_key = f"{event.get('source')}_{event.get('event_type')}"
                if sequence_key not in correlations['event_sequences']:
                    correlations['event_sequences'][sequence_key] = []
                
                # Find related events within 5 minutes
                related_events = []
                for other_event in events[i+1:]:
                    other_time = other_event.get('timestamp')
                    if other_time and (event_time - other_time).total_seconds() < 300:
                        related_events.append({
                            'event_type': other_event.get('event_type'),
                            'time_diff': (event_time - other_time).total_seconds()
                        })
                
                if related_events:
                    correlations['event_sequences'][sequence_key].extend(related_events)
        
        # Error patterns
        error_events = [e for e in events if e.get('status') == 'error']
        for error in error_events:
            source = error.get('source')
            event_type = error.get('event_type')
            key = f"{source}_{event_type}"
            
            if key not in correlations['error_patterns']:
                correlations['error_patterns'][key] = {
                    'count': 0,
                    'last_occurrence': None,
                    'common_causes': []
                }
            
            correlations['error_patterns'][key]['count'] += 1
            correlations['error_patterns'][key]['last_occurrence'] = error.get('timestamp')
        
        return jsonify({
            "success": True,
            "data": correlations,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting event correlation: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/redis/events')
@login_required
def get_redis_events():
    """Get recent events from Redis cache"""
    try:
        limit = int(request.args.get('limit', 100))
        source = request.args.get('source')
        event_type = request.args.get('event_type')
        
        events = get_redis_recent_events(limit)
        
        # Apply filters if provided
        if source:
            events = [e for e in events if e.get('source') == source]
        if event_type:
            events = [e for e in events if e.get('event_type') == event_type]
        
        return jsonify({
            "success": True,
            "data": events,
            "count": len(events),
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    except Exception as e:
        logger.error(f"Error getting Redis events: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/redis/stats')
@login_required
def get_redis_stats():
    """Get event statistics from Redis cache"""
    try:
        stats = get_redis_event_stats()
        
        return jsonify({
            "success": True,
            "data": stats,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    except Exception as e:
        logger.error(f"Error getting Redis stats: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/redis/live-stream')
@login_required
def get_redis_live_stream():
    """Get live events from Redis for real-time streaming"""
    try:
        # Get all live events from Redis
        live_events = redis_client.hgetall(REDIS_KEYS['live_events'])
        events = [json.loads(event) for event in live_events.values()]
        
        # Sort by timestamp (newest first)
        events.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        return jsonify({
            "success": True,
            "data": events,
            "count": len(events),
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    except Exception as e:
        logger.error(f"Error getting Redis live stream: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/redis/clear-cache', methods=['POST'])
@login_required
def clear_redis_cache():
    """Clear Redis cache (admin function)"""
    try:
        # Clear all Redis keys
        for key in REDIS_KEYS.values():
            redis_client.delete(key)
        
        logger.info("✅ Redis cache cleared successfully")
        return jsonify({
            "success": True,
            "message": "Redis cache cleared successfully"
        })
    except Exception as e:
        logger.error(f"Error clearing Redis cache: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/medical-monitor')
@login_required
def medical_monitor_page():
    """Medical data monitoring dashboard"""
    return render_template('medical-data-monitor.html')

@app.route('/api/medical-data')
@login_required
def get_medical_data():
    """Get medical data with enhanced analysis"""
    try:
        collection = mqtt_monitor.db[EVENT_LOG_COLLECTION]
        
        # Get medical events from last 24 hours
        one_day_ago = datetime.now(timezone.utc) - timedelta(days=1)
        
        # Get medical events (stored medical data and FHIR data)
        medical_events = list(collection.find({
            'timestamp': {'$gte': one_day_ago},
            'event_type': {'$in': ['5_medical_stored', '6_fhir_r5_stored']}
        }).sort('timestamp', -1).limit(1000))
        
        # Convert ObjectIds to strings
        def convert_objectids(obj):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if isinstance(value, dict):
                        convert_objectids(value)
                    elif isinstance(value, list):
                        for item in value:
                            convert_objectids(item)
                    elif hasattr(value, '__class__') and value.__class__.__name__ == 'ObjectId':
                        obj[key] = str(value)
                    elif hasattr(value, 'isoformat'):  # Handle datetime objects
                        obj[key] = value.isoformat()
            elif isinstance(obj, list):
                for item in obj:
                    convert_objectids(item)
            return obj
        
        medical_events = convert_objectids(medical_events)
        
        # Analyze medical data
        analysis = {
            'total_medical_events': len(medical_events),
            'devices': {},
            'patients': {},
            'alerts': [],
            'vital_trends': {}
        }
        
        # Process each medical event
        for event in medical_events:
            device_id = event.get('device_id', 'unknown')
            patient_id = event.get('patient_id', 'unknown')
            source = event.get('source', 'unknown')
            payload = event.get('details', {}).get('payload', {})
            
            # Track devices
            if device_id not in analysis['devices']:
                analysis['devices'][device_id] = {
                    'source': source,
                    'last_seen': event.get('timestamp'),
                    'data_count': 0,
                    'battery_level': None,
                    'signal_strength': None
                }
            analysis['devices'][device_id]['data_count'] += 1
            analysis['devices'][device_id]['last_seen'] = event.get('timestamp')
            
            # Track patients
            if patient_id not in analysis['patients']:
                analysis['patients'][patient_id] = {
                    'device_count': 0,
                    'last_activity': event.get('timestamp'),
                    'data_count': 0
                }
            analysis['patients'][patient_id]['data_count'] += 1
            analysis['patients'][patient_id]['last_activity'] = event.get('timestamp')
            
            # Check for medical alerts
            if source == 'Kati':
                battery = payload.get('battery')
                signal = payload.get('signalGSM')
                
                if battery is not None:
                    # Convert battery to integer for comparison
                    try:
                        battery_int = int(battery)
                        analysis['devices'][device_id]['battery_level'] = battery_int
                        if battery_int < 20:
                            analysis['alerts'].append({
                                'type': 'critical',
                                'device_id': device_id,
                                'message': f'Low battery: {battery_int}%',
                                'timestamp': event.get('timestamp')
                            })
                        elif battery_int < 40:
                            analysis['alerts'].append({
                                'type': 'warning',
                                'device_id': device_id,
                                'message': f'Battery warning: {battery_int}%',
                                'timestamp': event.get('timestamp')
                            })
                    except (ValueError, TypeError):
                        # If battery can't be converted to int, just store as is
                        analysis['devices'][device_id]['battery_level'] = battery
                
                if signal is not None:
                    # Convert signal to integer for comparison
                    try:
                        signal_int = int(signal)
                        analysis['devices'][device_id]['signal_strength'] = signal_int
                        if signal_int < 30:
                            analysis['alerts'].append({
                                'type': 'warning',
                                'device_id': device_id,
                                'message': f'Poor signal: {signal_int}%',
                                'timestamp': event.get('timestamp')
                            })
                    except (ValueError, TypeError):
                        # If signal can't be converted to int, just store as is
                        analysis['devices'][device_id]['signal_strength'] = signal
            
            # Track vital trends
            if source == 'Kati' and 'step' in payload:
                step_count = payload['step']
                if 'step_trends' not in analysis['vital_trends']:
                    analysis['vital_trends']['step_trends'] = []
                analysis['vital_trends']['step_trends'].append({
                    'device_id': device_id,
                    'steps': step_count,
                    'timestamp': event.get('timestamp')
                })
        
        return jsonify({
            "success": True,
            "data": {
                "events": medical_events,
                "analysis": analysis
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting medical data: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/recent-medical-data')
@login_required
def get_recent_medical_data():
    """Get recent medical data from the medical_data collection"""
    print("🔍 ENTERING get_recent_medical_data function")
    print("🔍 DEBUG: Function called successfully")
    try:
        # Check if MongoDB connection is available
        if mqtt_monitor.db is None:
            print("❌ MongoDB connection not available")
            return jsonify({
                "success": False,
                "error": "Database connection not available",
                "data": {
                    "recent_medical_data": [],
                    "total_count": 0,
                    "last_updated": datetime.now(timezone.utc).isoformat()
                }
        }), 503

        # Get medical data from the last 7 days for AVA4 devices, 24 hours for others
        one_day_ago = datetime.now(timezone.utc) - timedelta(days=1)
        seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
        
        # Also create timezone-naive versions for comparison with stored timestamps
        one_day_ago_naive = datetime.now() - timedelta(days=1)
        seven_days_ago_naive = datetime.now() - timedelta(days=7)
        
        # Query the medical_data collection directly
        medical_data_collection = mqtt_monitor.db['medical_data']
        
        # Get recent medical data, sorted by timestamp (newest first)
        # Temporarily remove timestamp filter to include all AVA4 data
        logger.info(f"🔍 DEBUG: Starting medical data query")
        
        # Debug: Check total counts
        total_ava4 = medical_data_collection.count_documents({'device_type': 'AVA4'})
        total_kati = medical_data_collection.count_documents({'device_type': {'$ne': 'AVA4'}})
        logger.info(f"🔍 DEBUG: Total AVA4 records: {total_ava4}")
        logger.info(f"🔍 DEBUG: Total Kati records: {total_kati}")
        
        # Get recent medical data from both AVA4 and Kati_Watch devices
        # Get the 50 most recent AVA4 records
        ava4_data = list(medical_data_collection.find({'device_type': 'AVA4'}).sort('timestamp', -1).limit(50))
        print(f"🔍 DEBUG: AVA4 query returned {len(ava4_data)} records")
        
        # Get the 50 most recent Kati_Watch records
        kati_data = list(medical_data_collection.find({'device_type': 'Kati_Watch'}).sort('timestamp', -1).limit(50))
        print(f"🔍 DEBUG: Kati query returned {len(kati_data)} records")
        
        # Combine the data
        recent_medical_data = ava4_data + kati_data
        print(f"🔍 DEBUG: Combined data has {len(recent_medical_data)} records")
        
        # Get emergency alarms (SOS, Fall Detection) from emergency_alarm collection
        emergency_alarm_collection = mqtt_monitor.db['emergency_alarm']
        emergency_alarms = list(emergency_alarm_collection.find({}).sort('timestamp', -1).limit(20))
        print(f"🔍 DEBUG: Emergency alarms query returned {len(emergency_alarms)} records")
        
        # Convert emergency alarms to medical data format for display
        for alarm in emergency_alarms:
            print(f"🔍 DEBUG: Processing emergency alarm: {alarm.get('alert_type')} for patient {alarm.get('patient_name')}")
            alarm['source'] = 'Emergency'  # Mark as emergency data
            alarm['collection_type'] = 'emergency_alarm'
            alarm['device_type'] = alarm.get('source', 'Kati')  # Use source as device_type
            recent_medical_data.append(alarm)
        
        # Sort by timestamp (newest first)
        recent_medical_data.sort(key=lambda x: x.get('timestamp', datetime.min), reverse=True)
        
        logger.info(f"🔍 DEBUG: Query returned {len(recent_medical_data)} records")
        sources = {}
        for record in recent_medical_data:
            source = record.get('device_type', 'Unknown')
            sources[source] = sources.get(source, 0) + 1
        logger.info(f"🔍 DEBUG: Sources in result: {sources}")
        
        # Convert ObjectIds to strings
        def convert_objectids(obj):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if isinstance(value, dict):
                        convert_objectids(value)
                    elif isinstance(value, list):
                        for item in value:
                            convert_objectids(item)
                    elif hasattr(value, '__class__') and value.__class__.__name__ == 'ObjectId':
                        obj[key] = str(value)
                    elif hasattr(value, 'isoformat'):  # Handle datetime objects
                        obj[key] = value.isoformat()
            elif isinstance(obj, list):
                for item in obj:
                    convert_objectids(item)
            return obj
        
        recent_medical_data = convert_objectids(recent_medical_data)
        
        # Process and format the medical data for display
        formatted_data = []
        for record in recent_medical_data:
            # Extract relevant information
            device_id = record.get('device_id', record.get('mac', 'Unknown'))
            patient_name = record.get('patient_name', 'Unknown')
            patient_id = record.get('patient_id', 'Unknown')
            timestamp = record.get('timestamp', record.get('created_at', datetime.now(timezone.utc)))
            
            # Use device_type as source, fallback to source field
            source = record.get('device_type', record.get('source', 'Unknown'))
            
            # Fix source determination based on IMEI patterns and data structure
            if device_id and isinstance(device_id, str):
                # Kati Watch IMEI pattern: 861265061xxxxxx
                if device_id.startswith('861265061'):
                    source = 'Kati'
                # AVA4 device MAC pattern: xx:xx:xx:xx:xx:xx
                elif ':' in device_id and len(device_id.split(':')) == 6:
                    source = 'AVA4'
            
            # Also check raw_data structure to determine source
            if 'raw_data' in record and isinstance(record['raw_data'], dict):
                raw_data = record['raw_data']
                # Check for Kati-specific fields
                if any(key in raw_data for key in ['IMEI', 'signalGSM', 'battery', 'workingMode', 'timeStamps']):
                    if source == 'Unknown':
                        source = 'Kati'
                # Check for AVA4-specific fields  
                elif any(key in raw_data for key in ['attribute', 'device_list', 'ava_mac_address']):
                    if source == 'Unknown':
                        source = 'AVA4'
            
            # Format timestamp
            if isinstance(timestamp, str):
                try:
                    timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                except:
                    timestamp = datetime.now(timezone.utc)
            
            # Extract medical values based on device type
            medical_values = {}
            
            # ALWAYS extract battery, signal, and step data from raw_data (if present)
            # This should work for all record types, including batch data records
            if 'raw_data' in record and isinstance(record['raw_data'], dict):
                raw_data = record['raw_data']
                if 'battery' in raw_data:
                    medical_values['battery'] = raw_data['battery']
                    print(f"✅ Extracted battery from raw_data: {raw_data['battery']}")
                if 'signal_gsm' in raw_data:
                    medical_values['signal_gsm'] = raw_data['signal_gsm']
                    print(f"✅ Extracted signal from raw_data: {raw_data['signal_gsm']}")
                if 'step_count' in raw_data:
                    medical_values['steps'] = raw_data['step_count']
                    print(f"✅ Extracted steps from raw_data: {raw_data['step_count']}")
            
            # Also check for battery/signal in nested data structure (fallback)
            if 'raw_data' in record and isinstance(record['raw_data'], dict):
                raw_data = record['raw_data']
                if 'data' in raw_data and isinstance(raw_data['data'], dict):
                    data = raw_data['data']
                    # Extract battery from nested data if not already extracted
                    if 'battery' in data and 'battery' not in medical_values:
                        medical_values['battery'] = data['battery']
                        print(f"✅ Extracted battery from nested data: {data['battery']}")
                    # Extract signal from nested data if not already extracted
                    if 'signalGSM' in data and 'signal_gsm' not in medical_values:
                        medical_values['signal_gsm'] = data['signalGSM']
                        print(f"✅ Extracted signal from nested data: {data['signalGSM']}")
                    # Extract step from nested data if not already extracted
                    if 'step' in data and 'steps' not in medical_values:
                        medical_values['steps'] = data['step']
                        print(f"✅ Extracted steps from nested data: {data['step']}")
            
            # FINAL: Always extract battery, signal, and step from top level (overwrite if present)
            if 'battery' in record:
                medical_values['battery'] = record['battery']
                print(f"✅ [FINAL] Extracted battery from top level: {record['battery']}")
            if 'signal_gsm' in record:
                medical_values['signal_gsm'] = record['signal_gsm']
                print(f"✅ [FINAL] Extracted signal from top level: {record['signal_gsm']}")
            if 'step_count' in record:
                medical_values['steps'] = record['step_count']
                print(f"✅ [FINAL] Extracted steps from top level: {record['step_count']}")
            
            # Handle emergency alarms (SOS, Fall Detection)
            if record.get('collection_type') == 'emergency_alarm':
                alert_type = record.get('alert_type', 'Unknown')
                if alert_type == 'sos':
                    medical_values['data_type'] = 'SOS Emergency'
                    medical_values['emergency_status'] = 'CRITICAL'
                    if 'alert_data' in record and isinstance(record['alert_data'], dict):
                        alert_data = record['alert_data']
                        if 'status' in alert_data:
                            medical_values['sos_status'] = alert_data['status']
                        if 'location' in alert_data:
                            medical_values['emergency_location'] = 'Available'
                        if 'imei' in alert_data:
                            medical_values['device_id'] = alert_data['imei']
                        if 'priority' in alert_data:
                            medical_values['priority'] = alert_data['priority']
                elif alert_type == 'fall_down':
                    medical_values['data_type'] = 'Fall Detection'
                    medical_values['emergency_status'] = 'HIGH'
                    if 'alert_data' in record and isinstance(record['alert_data'], dict):
                        alert_data = record['alert_data']
                        if 'status' in alert_data:
                            medical_values['fall_status'] = alert_data['status']
                        if 'location' in alert_data:
                            medical_values['fall_location'] = 'Available'
                        if 'imei' in alert_data:
                            medical_values['device_id'] = alert_data['imei']
                        if 'priority' in alert_data:
                            medical_values['priority'] = alert_data['priority']
            
            if source == 'AVA4' or source == 'AVA4_Gateway':
                print(f"🔍 ENTERING AVA4 PROCESSING - Device: {device_id}, Source: {source}")
                
                # Check if we have processed_data from the new storage format
                processed_data = None
                if 'processed_data' in record and record['processed_data']:
                    processed_data = record['processed_data']
                    print(f"✅ Found processed_data at top level for AVA4: {processed_data}")
                elif 'raw_data' in record and record['raw_data'] and 'processed_data' in record['raw_data']:
                    processed_data = record['raw_data']['processed_data']
                    print(f"✅ Found processed_data in raw_data for AVA4: {processed_data}")
                
                if processed_data:
                    # Extract medical values from processed_data
                    if 'systolic' in processed_data:
                        medical_values['systolic'] = processed_data['systolic']
                    if 'diastolic' in processed_data:
                        medical_values['diastolic'] = processed_data['diastolic']
                    if 'pulse' in processed_data:
                        medical_values['pulse_rate'] = processed_data['pulse']
                    if 'value' in processed_data:
                        # This could be blood glucose, SpO2, temperature, etc.
                        # Check both record attribute and raw_data attribute
                        attribute = record.get('attribute') or record.get('raw_data', {}).get('attribute')
                        if attribute in ['Contour_Elite', 'AccuChek_Instant']:
                            medical_values['blood_glucose'] = processed_data['value']
                        elif attribute == 'Oximeter JUMPER':
                            medical_values['spO2'] = processed_data['value']
                        elif attribute == 'IR_TEMO_JUMPER':
                            medical_values['temperature'] = processed_data['value']
                        elif attribute == 'BodyScale_JUMPER':
                            medical_values['weight'] = processed_data['value']
                        elif attribute == 'MGSS_REF_UA':
                            medical_values['uric_acid'] = processed_data['value']
                        elif attribute == 'MGSS_REF_CHOL':
                            medical_values['cholesterol'] = processed_data['value']
                        else:
                            medical_values['value'] = processed_data['value']
                    
                    # Extract additional fields
                    if 'marker' in processed_data:
                        medical_values['marker'] = processed_data['marker']
                    if 'pi' in processed_data:
                        medical_values['pi'] = processed_data['pi']
                    if 'scan_time' in processed_data:
                        medical_values['scan_time'] = processed_data['scan_time']
                    if 'mode' in processed_data:
                        medical_values['mode'] = processed_data['mode']
                    if 'pulse' in processed_data:
                        medical_values['pulse_rate'] = processed_data['pulse']
                    
                    print(f"🔧 DEBUG: processed_data keys: {list(processed_data.keys())}")
                    print(f"🔧 DEBUG: checking for resistance field...")
                    if 'resistance' in processed_data:
                        medical_values['resistance'] = processed_data['resistance']
                        print(f"🔧 DEBUG: ✅ Extracted resistance: {processed_data['resistance']}")
                    else:
                        print(f"🔧 DEBUG: ❌ No resistance field found")
                    
                    print(f"✅ Extracted AVA4 medical values: {medical_values}")
                
                # Fallback to old format for backward compatibility
                else:
                    print(f"🔍 Using legacy AVA4 format")
                    attribute = record.get('attribute', '')
                    value = record.get('value', {})
                    
                    # Helper function to only add valid values (not None, empty string, or 'N/A')
                    def add_if_valid(values_dict, key, value):
                        if value is not None and value != '' and value != 'N/A' and value != 'null':
                            values_dict[key] = value
                    
                    if attribute == 'Contour_Elite' and 'device_list' in value:
                        device_data = value['device_list'][0] if value['device_list'] else {}
                        add_if_valid(medical_values, 'blood_glucose', device_data.get('blood_glucose'))
                        add_if_valid(medical_values, 'marker', device_data.get('marker'))
                    elif attribute == 'BP_BIOLIGTH' and 'device_list' in value:
                        device_data = value['device_list'][0] if value['device_list'] else {}
                        add_if_valid(medical_values, 'systolic', device_data.get('bp_high'))
                        add_if_valid(medical_values, 'diastolic', device_data.get('bp_low'))
                        add_if_valid(medical_values, 'pulse_rate', device_data.get('PR'))
                    elif attribute == 'WBP BIOLIGHT' and 'device_list' in value:
                        device_data = value['device_list'][0] if value['device_list'] else {}
                        add_if_valid(medical_values, 'systolic', device_data.get('bp_high'))
                        add_if_valid(medical_values, 'diastolic', device_data.get('bp_low'))
                        add_if_valid(medical_values, 'pulse_rate', device_data.get('PR'))
                    elif attribute == 'Oximeter JUMPER' and 'device_list' in value:
                        device_data = value['device_list'][0] if value['device_list'] else {}
                        add_if_valid(medical_values, 'spO2', device_data.get('spo2'))
                        add_if_valid(medical_values, 'pulse', device_data.get('pulse'))
                        add_if_valid(medical_values, 'pi', device_data.get('pi'))
                    elif attribute == 'IR_TEMO_JUMPER' and 'device_list' in value:
                        device_data = value['device_list'][0] if value['device_list'] else {}
                        add_if_valid(medical_values, 'temperature', device_data.get('temp'))
                        add_if_valid(medical_values, 'mode', device_data.get('mode'))
                    elif attribute == 'BodyScale_JUMPER' and 'device_list' in value:
                        device_data = value['device_list'][0] if value['device_list'] else {}
                        add_if_valid(medical_values, 'weight', device_data.get('weight'))
                        add_if_valid(medical_values, 'resistance', device_data.get('resistance'))
                    elif attribute == 'MGSS_REF_UA' and 'device_list' in value:
                        device_data = value['device_list'][0] if value['device_list'] else {}
                        add_if_valid(medical_values, 'uric_acid', device_data.get('uric_acid'))
                    elif attribute == 'MGSS_REF_CHOL' and 'device_list' in value:
                        device_data = value['device_list'][0] if value['device_list'] else {}
                        add_if_valid(medical_values, 'cholesterol', device_data.get('cholesterol'))
                    elif attribute == 'AccuChek_Instant' and 'device_list' in value:
                        device_data = value['device_list'][0] if value['device_list'] else {}
                        add_if_valid(medical_values, 'blood_glucose', device_data.get('blood_glucose'))
                        add_if_valid(medical_values, 'marker', device_data.get('marker'))
            elif source == 'Kati' or source == 'Kati_Watch':
                print(f"🔍 ENTERING KATI PROCESSING - Device: {device_id}, Source: {source}")
                
                # Get the topic and event type to determine data type
                topic = record.get('topic', '')
                event_type = record.get('event_type', '')
                
                print(f"📊 Kati Topic: {topic}, Event Type: {event_type}")
                
                # Extract data based on topic/event type
                if topic == 'iMEDE_watch/hb' or event_type == 'heartbeat':
                    # Heartbeat data - extract battery, signal, steps
                    if 'raw_data' in record and isinstance(record['raw_data'], dict):
                        raw_data = record['raw_data']
                        if 'battery' in raw_data:
                            medical_values['battery'] = raw_data['battery']
                        if 'signal_gsm' in raw_data:
                            medical_values['signal_gsm'] = raw_data['signal_gsm']
                        if 'step_count' in raw_data:
                            medical_values['steps'] = raw_data['step_count']
                    # Also check nested data structure
                    if 'raw_data' in record and isinstance(record['raw_data'], dict):
                        raw_data = record['raw_data']
                        if 'data' in raw_data and isinstance(raw_data['data'], dict):
                            data = raw_data['data']
                            if 'battery' in data and 'battery' not in medical_values:
                                medical_values['battery'] = data['battery']
                            if 'signalGSM' in data and 'signal_gsm' not in medical_values:
                                medical_values['signal_gsm'] = data['signalGSM']
                            if 'step' in data and 'steps' not in medical_values:
                                medical_values['steps'] = data['step']
                    medical_values['data_type'] = 'Heartbeat'
                    
                elif topic == 'iMEDE_watch/VitalSign' or event_type == 'vital_signs':
                    # Vital signs data
                    if 'raw_data' in record and isinstance(record['raw_data'], dict):
                        raw_data = record['raw_data']
                        if 'heart_rate' in raw_data:
                            medical_values['heart_rate'] = raw_data['heart_rate']
                        if 'blood_pressure' in raw_data:
                            medical_values['blood_pressure'] = raw_data['blood_pressure']
                        if 'body_temperature' in raw_data:
                            medical_values['temperature'] = raw_data['body_temperature']
                        if 'spo2' in raw_data:
                            medical_values['spO2'] = raw_data['spo2']
                        if 'battery' in raw_data:
                            medical_values['battery'] = raw_data['battery']
                        if 'signal_gsm' in raw_data:
                            medical_values['signal_gsm'] = raw_data['signal_gsm']
                    medical_values['data_type'] = 'Vital Signs'
                    
                elif topic == 'iMEDE_watch/AP55' or event_type == 'batch_vital_signs':
                    # Batch vital signs data
                    vital_signs = record.get('vital_signs_data', [])
                    if vital_signs and len(vital_signs) > 0:
                        medical_values['vital_signs_count'] = len(vital_signs)
                        medical_values['data_type'] = f'Batch Vital Signs ({len(vital_signs)} readings)'
                    else:
                        medical_values['data_type'] = 'Batch Vital Signs'
                        
                elif topic == 'iMEDE_watch/location' or event_type == 'location':
                    # Location data
                    if 'raw_data' in record and isinstance(record['raw_data'], dict):
                        raw_data = record['raw_data']
                        if 'location' in raw_data:
                            location = raw_data['location']
                            if 'GPS' in location:
                                gps = location['GPS']
                                if gps.get('latitude') and gps.get('longitude'):
                                    medical_values['gps_coords'] = f"{gps['latitude']}, {gps['longitude']}"
                                else:
                                    medical_values['gps_status'] = 'No GPS signal'
                            if 'LBS' in location:
                                lbs = location['LBS']
                                medical_values['cell_tower'] = f"{lbs.get('MCC', '')}-{lbs.get('MNC', '')}-{lbs.get('LAC', '')}-{lbs.get('CID', '')}"
                    medical_values['data_type'] = 'Location'
                    
                elif topic == 'iMEDE_watch/sos' or event_type == 'emergency_sos':
                    # SOS emergency data
                    if 'raw_data' in record and isinstance(record['raw_data'], dict):
                        raw_data = record['raw_data']
                        if 'status' in raw_data:
                            medical_values['sos_status'] = raw_data['status']
                        if 'location' in raw_data:
                            medical_values['emergency_location'] = 'Available'
                    medical_values['data_type'] = 'SOS Emergency'
                    
                elif topic == 'iMEDE_watch/fallDown' or event_type == 'fall_detection':
                    # Fall detection data
                    if 'raw_data' in record and isinstance(record['raw_data'], dict):
                        raw_data = record['raw_data']
                        if 'status' in raw_data:
                            medical_values['fall_status'] = raw_data['status']
                        if 'location' in raw_data:
                            medical_values['fall_location'] = 'Available'
                    medical_values['data_type'] = 'Fall Detection'
                    
                elif topic == 'iMEDE_watch/sleepdata' or event_type == 'sleep_data':
                    # Sleep data
                    if 'raw_data' in record and isinstance(record['raw_data'], dict):
                        raw_data = record['raw_data']
                        if 'sleep_data' in raw_data:
                            medical_values['sleep_data'] = 'Available'
                    medical_values['data_type'] = 'Sleep Data'
                    
                elif topic == 'iMEDE_watch/onlineTrigger' or event_type == 'device_status':
                    # Device status data
                    if 'raw_data' in record and isinstance(record['raw_data'], dict):
                        raw_data = record['raw_data']
                        if 'status' in raw_data:
                            medical_values['device_status'] = raw_data['status']
                    medical_values['data_type'] = 'Device Status'
                    
                else:
                    # Generic data extraction for unknown topics
                    if 'raw_data' in record and isinstance(record['raw_data'], dict):
                        raw_data = record['raw_data']
                        # Extract common fields
                        for key in ['battery', 'signal_gsm', 'step_count', 'heart_rate', 'temperature', 'spO2']:
                            if key in raw_data:
                                medical_values[key] = raw_data[key]
                    medical_values['data_type'] = f'Unknown Topic: {topic}'
                
                print(f"✅ Extracted Kati values: {medical_values}")
            
            # Include ALL records with appropriate values for each data type
            formatted_data.append({
                'id': str(record.get('_id', '')),
                'device_id': device_id,
                'patient_name': patient_name,
                'patient_id': patient_id,
                'source': source,
                'timestamp': timestamp.isoformat() if hasattr(timestamp, 'isoformat') else str(timestamp),
                'medical_values': medical_values,
                'raw_data': record
            })
        
        return jsonify({
            "success": True,
            "data": {
                "recent_medical_data": formatted_data,
                "total_count": len(formatted_data),
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting recent medical data: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

# AVA4 Status Monitoring API Endpoints
@app.route('/ava4-status')
@login_required
def ava4_status_page():
    """AVA4 device status monitoring dashboard"""
    return render_template('ava4-status.html')

@app.route('/api/ava4-status')
@login_required
def get_ava4_status():
    """Get AVA4 device status"""
    try:
        # Connect to MongoDB with SSL
        client = pymongo.MongoClient(
            mongodb_uri,
            tls=True,
            tlsCAFile='/app/ssl/ca-latest.pem',
            tlsCertificateKeyFile='/app/ssl/client-combined-latest.pem',
            tlsAllowInvalidCertificates=True,
            tlsAllowInvalidHostnames=True
        )
        
        db = client[mongodb_database]
        ava4_status_collection = db.ava4_status
        
        # Get all AVA4 status
        ava4_devices = list(ava4_status_collection.find({}, {'_id': 0}))
        
        # Calculate offline devices
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=2)
        online_count = 0
        offline_count = 0
        
        for device in ava4_devices:
            last_heartbeat = device.get('last_heartbeat')
            if isinstance(last_heartbeat, str):
                try:
                    last_heartbeat = datetime.fromisoformat(last_heartbeat.replace('Z', '+00:00'))
                except:
                    last_heartbeat = datetime.now(timezone.utc)
            elif last_heartbeat and not last_heartbeat.tzinfo:
                # Make timezone-naive datetime timezone-aware
                last_heartbeat = last_heartbeat.replace(tzinfo=timezone.utc)
            
            if last_heartbeat and last_heartbeat >= cutoff_time:
                device['status'] = 'Online'
                online_count += 1
            else:
                device['status'] = 'Offline'
                offline_count += 1
        
        client.close()
        
        return jsonify({
            'success': True,
            'data': {
                'devices': ava4_devices,
                'summary': {
                    'total': len(ava4_devices),
                    'online': online_count,
                    'offline': offline_count
                }
            },
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting AVA4 status: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }), 500

@app.route('/api/ava4-status/<ava4_mac>')
@login_required
def get_ava4_device_status(ava4_mac):
    """Get specific AVA4 device status"""
    try:
        # Connect to MongoDB with SSL
        client = pymongo.MongoClient(
            mongodb_uri,
            tls=True,
            tlsCAFile='/app/ssl/ca-latest.pem',
            tlsCertificateKeyFile='/app/ssl/client-combined-latest.pem',
            tlsAllowInvalidCertificates=True,
            tlsAllowInvalidHostnames=True
        )
        
        db = client[mongodb_database]
        ava4_status_collection = db.ava4_status
        
        # Get specific device
        device = ava4_status_collection.find_one({'ava4_mac': ava4_mac}, {'_id': 0})
        
        if not device:
            client.close()
            return jsonify({
                'success': False,
                'error': 'Device not found',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }), 404
        
        # Check if device is online
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=2)
        last_heartbeat = device.get('last_heartbeat')
        
        if isinstance(last_heartbeat, str):
            try:
                last_heartbeat = datetime.fromisoformat(last_heartbeat.replace('Z', '+00:00'))
            except:
                last_heartbeat = datetime.now(timezone.utc)
        elif last_heartbeat and not last_heartbeat.tzinfo:
            # Make timezone-naive datetime timezone-aware
            last_heartbeat = last_heartbeat.replace(tzinfo=timezone.utc)
        
        if last_heartbeat and last_heartbeat >= cutoff_time:
            device['status'] = 'Online'
        else:
            device['status'] = 'Offline'
        
        client.close()
        
        return jsonify({
            'success': True,
            'data': device,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting AVA4 device status: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }), 500

@socketio.on('get_medical_data')
def handle_get_medical_data():
    """Handle Socket.IO request for medical data"""
    try:
        # Get recent medical data from Redis first, then fallback to MongoDB
        redis_medical_data = get_redis_recent_events(100)
        
        # Filter for medical data events
        medical_events = [event for event in redis_medical_data if event.get('event_type') == 'medical_stored']
        
        if medical_events:
            emit('medical_data_update', {
                'type': 'medical_data',
                'data': medical_events,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
        else:
            # Fallback to MongoDB if no Redis data
            try:
                # Check if MQTT monitor and database are properly initialized
                if mqtt_monitor is not None and hasattr(mqtt_monitor, 'db') and mqtt_monitor.db is not None:
                    one_day_ago = datetime.now(timezone.utc) - timedelta(days=1)
                    medical_data_collection = mqtt_monitor.db['medical_data']
                    
                    recent_medical_data = list(medical_data_collection.find({
                        '$or': [
                            {'timestamp': {'$gte': one_day_ago}},
                            {'timestamp': {'$gte': one_day_ago.isoformat()}}
                        ]
                    }).sort('timestamp', -1).limit(50))
                    
                    # Convert ObjectIds and datetime objects to strings
                    def convert_objectids(obj):
                        if isinstance(obj, dict):
                            for key, value in obj.items():
                                if isinstance(value, dict):
                                    convert_objectids(value)
                                elif isinstance(value, list):
                                    for item in value:
                                        convert_objectids(item)
                                elif hasattr(value, '__class__') and value.__class__.__name__ == 'ObjectId':
                                    obj[key] = str(value)
                                elif hasattr(value, 'isoformat'):  # Handle datetime objects
                                    obj[key] = value.isoformat()
                        elif isinstance(obj, list):
                            for item in obj:
                                convert_objectids(item)
                        return obj
                    
                    recent_medical_data = convert_objectids(recent_medical_data)
                    
                    emit('medical_data_update', {
                        'type': 'medical_data',
                        'data': recent_medical_data,
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    })
                    
                    logger.debug(f"📡 Medical data sent via Socket.IO from MongoDB: {len(recent_medical_data)} records")
                else:
                    logger.warning("⚠️ MQTT monitor database not available, sending empty data")
                    emit('medical_data_update', {
                        'type': 'medical_data',
                        'data': [],
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    })
                    
            except Exception as db_error:
                logger.error(f"❌ Database error in Socket.IO medical data handler: {db_error}")
                emit('medical_data_error', {
                    'type': 'error',
                    'message': f"Database error: {str(db_error)}",
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })
        
        logger.debug(f"📡 Medical data sent via Socket.IO: {len(medical_events) if medical_events else 0} records from Redis")
        
    except Exception as e:
        logger.error(f"❌ Error handling medical data Socket.IO request: {e}")
        emit('medical_data_error', {
            'type': 'error',
            'message': str(e),
            'timestamp': datetime.now(timezone.utc).isoformat()
        })

def broadcast_medical_data_update(medical_data: dict):
    """Broadcast medical data update to all connected Socket.IO clients"""
    try:
        # Convert medical data to JSON serializable format
        def convert_for_broadcast(obj):
            if isinstance(obj, dict):
                return {k: convert_for_broadcast(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_for_broadcast(item) for item in obj]
            elif hasattr(obj, 'isoformat'):
                return obj.isoformat()
            elif hasattr(obj, '__str__'):
                return str(obj)
            else:
                return obj
        
        # Convert the medical data to ensure it's JSON serializable
        serializable_medical_data = convert_for_broadcast(medical_data)
        
        # Cache the medical data in Redis
        redis_cache_event({
            'event_type': 'medical_stored',
            'data': serializable_medical_data,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        
        # Broadcast to all connected clients
        socketio.emit('medical_data_update', {
            'type': 'new_medical_data',
            'data': serializable_medical_data,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        
        logger.debug(f"📡 Medical data broadcasted via Socket.IO: {serializable_medical_data.get('device_id', 'unknown')}")
        
    except Exception as e:
        logger.error(f"❌ Error broadcasting medical data: {e}")

@app.route('/api/medical-data/broadcast', methods=['POST'])
def broadcast_medical_data():
    """Receive medical data broadcasts and forward to Socket.IO clients"""
    try:
        data = request.get_json()
        if not data or 'medical_data' not in data:
            return jsonify({'success': False, 'error': 'Missing medical_data in request'}), 400
        
        medical_data = data['medical_data']
        
        # Broadcast to all connected Socket.IO clients
        broadcast_medical_data_update(medical_data)
        
        logger.info(f"📡 Medical data broadcasted via Socket.IO: {medical_data.get('device_id', 'unknown')}")
        
        return jsonify({'success': True, 'message': 'Medical data broadcasted successfully'})
        
    except Exception as e:
        logger.error(f"❌ Error broadcasting medical data: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================================
# KATI TRANSACTION ENDPOINTS
# ============================================================================

@app.route('/kati-transaction')
@login_required
def kati_transaction_page():
    """Kati Watch transaction monitoring dashboard"""
    return render_template('kati-transaction.html', google_maps_api_key=GOOGLE_MAPS_API_KEY)

@app.route('/api/kati-transactions')
@login_required
def get_kati_transactions():
    """Get Kati Watch transaction data with enhanced analysis"""
    try:
        # Check if MongoDB connection is available
        if mqtt_monitor.db is None:
            return jsonify({
                "success": False,
                "error": "Database connection not available",
                "data": {
                    "transactions": [],
                    "statistics": {},
                    "last_updated": datetime.now(timezone.utc).isoformat()
                }
            }), 503

        # Get filter parameter from request
        data_filter = request.args.get('filter', 'patient_only')  # 'patient_only' or 'all_devices'
        
        # Get pagination parameters
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 50))
        skip = (page - 1) * per_page
        
        # Get Kati Watch data from the last 24 hours
        one_day_ago = datetime.now(timezone.utc) - timedelta(days=1)
        
        # Query the medical_data collection for Kati Watch data
        medical_data_collection = mqtt_monitor.db['medical_data']
        
        # Build query based on filter
        if data_filter == 'patient_only':
            # Only show data that has patient_id (mapped devices)
            kati_transactions = list(medical_data_collection.find({
                'device_type': 'Kati_Watch',
                'timestamp': {'$gte': one_day_ago},
                'patient_id': {'$exists': True, '$ne': None}
            }).sort('timestamp', -1).skip(skip).limit(per_page))
        else:
            # Show all Kati Watch data (including unmapped devices)
            kati_transactions = list(medical_data_collection.find({
                'device_type': 'Kati_Watch',
                'timestamp': {'$gte': one_day_ago}
            }).sort('timestamp', -1).skip(skip).limit(per_page))
        
        # Also get emergency alarms for Kati devices
        emergency_collection = mqtt_monitor.db['emergency_alarm']
        emergency_alarms = list(emergency_collection.find({
            'timestamp': {'$gte': one_day_ago},
            'device_type': 'Kati_Watch'
        }).sort('timestamp', -1).limit(100))
        
        # Convert emergency alarms to transaction format
        for alarm in emergency_alarms:
            alarm['_id'] = str(alarm['_id'])
            alarm['topic'] = alarm.get('topic', 'iMEDE_watch/SOS')
            alarm['event_type'] = 'emergency_sos' if 'SOS' in alarm.get('topic', '') else 'fall_detection'
            alarm['status'] = 'success'
            alarm['device_type'] = 'Kati_Watch'
        
        # Combine and sort all transactions
        all_transactions = kati_transactions + emergency_alarms
        all_transactions.sort(key=lambda x: x.get('timestamp', datetime.min), reverse=True)
        
        # Enhance transactions with patient information
        enhanced_transactions = []
        for transaction in all_transactions:
            enhanced_transaction = transaction.copy()
            
            # Add hospital and ward information if patient_id exists
            if transaction.get('patient_id'):
                try:
                    # Get patient information from patients collection
                    patient = mqtt_monitor.db.patients.find_one({'_id': transaction['patient_id']})
                    if patient:
                        enhanced_transaction['patient_info'] = {
                            'first_name': patient.get('first_name', ''),
                            'last_name': patient.get('last_name', ''),
                            'profile_image': patient.get('profile_image', ''),
                            'hospital_info': {}
                        }
                        
                        # Get hospital and ward information
                        hospital_ward_data = patient.get('hospital_ward_data', {})
                        if hospital_ward_data:
                            # Handle different data structures
                            if isinstance(hospital_ward_data, dict):
                                hospital_id = hospital_ward_data.get('hospitalId')
                                if hospital_id:
                                    # Get hospital information from AMY.hospitals collection
                                    hospital = mqtt_monitor.db.hospitals.find_one({'_id': ObjectId(hospital_id)})
                                    if hospital:
                                        # Extract Thai hospital name from multi-language object
                                        hospital_name_obj = hospital.get('name', {})
                                        if isinstance(hospital_name_obj, list):
                                            # Find Thai name in the list
                                            thai_name = next((item.get('name', 'Unknown Hospital') for item in hospital_name_obj if item.get('code') == 'th'), 'Unknown Hospital')
                                            enhanced_transaction['patient_info']['hospital_info']['hospital_name'] = thai_name
                                        else:
                                            enhanced_transaction['patient_info']['hospital_info']['hospital_name'] = hospital.get('name', 'Unknown Hospital')
                                        enhanced_transaction['patient_info']['hospital_info']['hospital_id'] = str(hospital_id)
                                        
                                        # Get ward information from AMY.ward_lists collection
                                        ward_list = hospital_ward_data.get('wardList', [])
                                        if ward_list:
                                            # Find the ward for this hospital
                                            for ward in ward_list:
                                                if ward.get('hospital_id') == hospital_id:
                                                    ward_id = ward.get('ward_id')
                                                    if ward_id:
                                                        # Lookup ward name from AMY.ward_lists collection
                                                        ward_info = mqtt_monitor.db.ward_lists.find_one({'_id': ObjectId(ward_id)})
                                                        if ward_info:
                                                            # Extract Thai ward name from multi-language object
                                                            ward_name_obj = ward_info.get('name', {})
                                                            if isinstance(ward_name_obj, list):
                                                                # Find Thai name in the list
                                                                thai_name = next((item.get('name', 'Unknown Ward') for item in ward_name_obj if item.get('code') == 'th'), 'Unknown Ward')
                                                                enhanced_transaction['patient_info']['hospital_info']['ward_name'] = thai_name
                                                            else:
                                                                enhanced_transaction['patient_info']['hospital_info']['ward_name'] = ward_info.get('name', 'Unknown Ward')
                                                            enhanced_transaction['patient_info']['hospital_info']['ward_id'] = str(ward_id)
                                                        else:
                                                            enhanced_transaction['patient_info']['hospital_info']['ward_name'] = 'Unknown Ward'
                                                            enhanced_transaction['patient_info']['hospital_info']['ward_id'] = str(ward_id)
                                                    break
                            elif isinstance(hospital_ward_data, list) and len(hospital_ward_data) > 0:
                                # Handle case where hospital_ward_data is a list
                                first_hospital = hospital_ward_data[0]
                                if isinstance(first_hospital, dict):
                                    hospital_id = first_hospital.get('hospitalId')
                                    if hospital_id:
                                        # Get hospital information from AMY.hospitals collection
                                        hospital = mqtt_monitor.db.hospitals.find_one({'_id': ObjectId(hospital_id)})
                                        if hospital:
                                            # Extract Thai hospital name from multi-language object
                                            hospital_name_obj = hospital.get('name', {})
                                            if isinstance(hospital_name_obj, list):
                                                # Find Thai name in the list
                                                thai_name = next((item.get('name', 'Unknown Hospital') for item in hospital_name_obj if item.get('code') == 'th'), 'Unknown Hospital')
                                                enhanced_transaction['patient_info']['hospital_info']['hospital_name'] = thai_name
                                            else:
                                                enhanced_transaction['patient_info']['hospital_info']['hospital_name'] = hospital.get('name', 'Unknown Hospital')
                                            enhanced_transaction['patient_info']['hospital_info']['hospital_id'] = str(hospital_id)
                                            
                                            # Get ward information from AMY.ward_lists collection
                                            ward_list = first_hospital.get('wardList', [])
                                            if ward_list:
                                                # Find the ward for this hospital
                                                for ward in ward_list:
                                                    if ward.get('hospital_id') == hospital_id:
                                                        ward_id = ward.get('ward_id')
                                                        if ward_id:
                                                            # Lookup ward name from AMY.ward_lists collection
                                                            ward_info = mqtt_monitor.db.ward_lists.find_one({'_id': ObjectId(ward_id)})
                                                            if ward_info:
                                                                # Extract Thai ward name from multi-language object
                                                                ward_name_obj = ward_info.get('name', {})
                                                                if isinstance(ward_name_obj, list):
                                                                    # Find Thai name in the list
                                                                    thai_name = next((item.get('name', 'Unknown Ward') for item in ward_name_obj if item.get('code') == 'th'), 'Unknown Ward')
                                                                    enhanced_transaction['patient_info']['hospital_info']['ward_name'] = thai_name
                                                                else:
                                                                    enhanced_transaction['patient_info']['hospital_info']['ward_name'] = ward_info.get('name', 'Unknown Ward')
                                                                enhanced_transaction['patient_info']['hospital_info']['ward_id'] = str(ward_id)
                                                            else:
                                                                enhanced_transaction['patient_info']['hospital_info']['ward_name'] = 'Unknown Ward'
                                                                enhanced_transaction['patient_info']['hospital_info']['ward_id'] = str(ward_id)
                                                        break
                except Exception as e:
                    logger.warning(f"Error enhancing patient info for transaction {transaction.get('_id')}: {e}")
            
            enhanced_transactions.append(enhanced_transaction)
        
        # Convert ObjectIds to strings
        def convert_objectids(obj):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if isinstance(value, dict):
                        convert_objectids(value)
                    elif isinstance(value, list):
                        for item in value:
                            convert_objectids(item)
                    elif hasattr(value, '__class__') and value.__class__.__name__ == 'ObjectId':
                        obj[key] = str(value)
                    elif hasattr(value, 'isoformat'):  # Handle datetime objects
                        obj[key] = value.isoformat()
            elif isinstance(obj, list):
                for item in obj:
                    convert_objectids(item)
            return obj
        
        enhanced_transactions = convert_objectids(enhanced_transactions)
        
        # Get total count for pagination
        if data_filter == 'patient_only':
            total_count = medical_data_collection.count_documents({
                'device_type': 'Kati_Watch',
                'timestamp': {'$gte': one_day_ago},
                'patient_id': {'$exists': True, '$ne': None}
            })
        else:
            total_count = medical_data_collection.count_documents({
                'device_type': 'Kati_Watch',
                'timestamp': {'$gte': one_day_ago}
            })
        
        # Calculate statistics
        mapped_count = len([t for t in enhanced_transactions if t.get('patient_id')])
        unmapped_count = len([t for t in enhanced_transactions if not t.get('patient_id')])
        
        statistics = {
            'total_transactions': total_count,  # Use the actual total count from database
            'mapped_devices': mapped_count,
            'unmapped_devices': unmapped_count,
            'active_devices': len(set(t.get('device_id') for t in enhanced_transactions if t.get('device_id'))),
            'success_rate': 100,  # All stored transactions are successful
            'topic_distribution': {},
            'emergency_count': len(emergency_alarms),
            'filter_applied': data_filter,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total_count': total_count,
                'total_pages': (total_count + per_page - 1) // per_page
            },
            'last_updated': datetime.now(timezone.utc).isoformat()
        }
        
        # Calculate topic distribution
        for transaction in enhanced_transactions:
            topic = transaction.get('topic', 'unknown')
            statistics['topic_distribution'][topic] = statistics['topic_distribution'].get(topic, 0) + 1
        
        return jsonify({
            "success": True,
            "data": {
                "transactions": enhanced_transactions,
                "statistics": statistics
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting Kati transactions: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/kati-transactions/all-devices')
@login_required
def get_all_kati_devices():
    """Get all Kati Watch data including unmapped devices"""
    try:
        # Check if MongoDB connection is available
        if mqtt_monitor.db is None:
            return jsonify({
                "success": False,
                "error": "Database connection not available",
                "data": {
                    "transactions": [],
                    "statistics": {},
                    "last_updated": datetime.now(timezone.utc).isoformat()
                }
            }), 503

        # Get Kati Watch data from the last 24 hours (all devices)
        one_day_ago = datetime.now(timezone.utc) - timedelta(days=1)
        
        # Query the medical_data collection for ALL Kati Watch data
        medical_data_collection = mqtt_monitor.db['medical_data']
        
        # Get all Kati Watch transactions (including unmapped)
        kati_transactions = list(medical_data_collection.find({
            'device_type': 'Kati_Watch',
            'timestamp': {'$gte': one_day_ago}
        }).sort('timestamp', -1).limit(1000))  # Increased limit for all devices
        
        # Also get emergency alarms for Kati devices
        emergency_collection = mqtt_monitor.db['emergency_alarm']
        emergency_alarms = list(emergency_collection.find({
            'timestamp': {'$gte': one_day_ago},
            'device_type': 'Kati_Watch'
        }).sort('timestamp', -1).limit(200))
        
        # Convert emergency alarms to transaction format
        for alarm in emergency_alarms:
            alarm['_id'] = str(alarm['_id'])
            alarm['topic'] = alarm.get('topic', 'iMEDE_watch/SOS')
            alarm['event_type'] = 'emergency_sos' if 'SOS' in alarm.get('topic', '') else 'fall_detection'
            alarm['status'] = 'success'
            alarm['device_type'] = 'Kati_Watch'
        
        # Combine and sort all transactions
        all_transactions = kati_transactions + emergency_alarms
        all_transactions.sort(key=lambda x: x.get('timestamp', datetime.min), reverse=True)
        
        # Convert ObjectIds to strings
        def convert_objectids(obj):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if isinstance(value, dict):
                        convert_objectids(value)
                    elif isinstance(value, list):
                        for item in value:
                            convert_objectids(item)
                    elif hasattr(value, '__class__') and value.__class__.__name__ == 'ObjectId':
                        obj[key] = str(value)
                    elif hasattr(value, 'isoformat'):  # Handle datetime objects
                        obj[key] = value.isoformat()
            elif isinstance(obj, list):
                for item in obj:
                    convert_objectids(item)
            return obj
        
        all_transactions = convert_objectids(all_transactions)
        
        # Calculate statistics
        mapped_count = len([t for t in all_transactions if t.get('patient_id')])
        unmapped_count = len([t for t in all_transactions if not t.get('patient_id')])
        unique_devices = set(t.get('device_id') for t in all_transactions if t.get('device_id'))
        mapped_devices = set(t.get('device_id') for t in all_transactions if t.get('device_id') and t.get('patient_id'))
        unmapped_devices = unique_devices - mapped_devices
        
        statistics = {
            'total_transactions': len(all_transactions),
            'mapped_transactions': mapped_count,
            'unmapped_transactions': unmapped_count,
            'total_devices': len(unique_devices),
            'mapped_devices': len(mapped_devices),
            'unmapped_devices': len(unmapped_devices),
            'success_rate': 100,  # All stored transactions are successful
            'topic_distribution': {},
            'emergency_count': len(emergency_alarms),
            'filter_applied': 'all_devices',
            'last_updated': datetime.now(timezone.utc).isoformat()
        }
        
        # Calculate topic distribution
        for transaction in all_transactions:
            topic = transaction.get('topic', 'unknown')
            statistics['topic_distribution'][topic] = statistics['topic_distribution'].get(topic, 0) + 1
        
        return jsonify({
            "success": True,
            "data": {
                "transactions": all_transactions,
                "statistics": statistics
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting all Kati devices: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/kati-transactions/stats')
@login_required
def get_kati_transaction_stats():
    """Get Kati Watch transaction statistics"""
    try:
        # Check if MongoDB connection is available
        if mqtt_monitor.db is None:
            return jsonify({
                "success": False,
                "error": "Database connection not available"
            }), 503

        # Get statistics for different time periods
        now = datetime.now(timezone.utc)
        one_hour_ago = now - timedelta(hours=1)
        one_day_ago = now - timedelta(days=1)
        one_week_ago = now - timedelta(days=7)
        
        medical_data_collection = mqtt_monitor.db['medical_data']
        emergency_collection = mqtt_monitor.db['emergency_alarm']
        
        # Get transaction counts for different periods
        stats = {
            'last_hour': {
                'transactions': medical_data_collection.count_documents({
                    'device_type': 'Kati_Watch',
                    'timestamp': {'$gte': one_hour_ago}
                }),
                'emergencies': emergency_collection.count_documents({
                    'device_type': 'Kati_Watch',
                    'timestamp': {'$gte': one_hour_ago}
                })
            },
            'last_24_hours': {
                'transactions': medical_data_collection.count_documents({
                    'device_type': 'Kati_Watch',
                    'timestamp': {'$gte': one_day_ago}
                }),
                'emergencies': emergency_collection.count_documents({
                    'device_type': 'Kati_Watch',
                    'timestamp': {'$gte': one_day_ago}
                })
            },
            'last_week': {
                'transactions': medical_data_collection.count_documents({
                    'device_type': 'Kati_Watch',
                    'timestamp': {'$gte': one_week_ago}
                }),
                'emergencies': emergency_collection.count_documents({
                    'device_type': 'Kati_Watch',
                    'timestamp': {'$gte': one_week_ago}
                })
            }
        }
        
        # Get active devices
        active_devices = medical_data_collection.distinct('device_id', {
            'device_type': 'Kati_Watch',
            'timestamp': {'$gte': one_day_ago}
        })
        
        stats['active_devices'] = len(active_devices)
        stats['last_updated'] = now.isoformat()
        
        return jsonify({
            "success": True,
            "data": stats
        })
        
    except Exception as e:
        logger.error(f"Error getting Kati transaction stats: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@socketio.on('get_kati_transactions')
def handle_get_kati_transactions():
    """Handle Socket.IO request for Kati transaction data"""
    try:
        # Get recent Kati transactions
        if mqtt_monitor.db is not None:
            one_day_ago = datetime.now(timezone.utc) - timedelta(days=1)
            medical_data_collection = mqtt_monitor.db['medical_data']
            
            recent_transactions = list(medical_data_collection.find({
                'device_type': 'Kati_Watch',
                'timestamp': {'$gte': one_day_ago}
            }).sort('timestamp', -1).limit(50))
            
            # Convert ObjectIds to strings
            def convert_objectids(obj):
                if isinstance(obj, dict):
                    for key, value in obj.items():
                        if isinstance(value, dict):
                            convert_objectids(value)
                        elif isinstance(value, list):
                            for item in value:
                                convert_objectids(item)
                        elif hasattr(value, '__class__') and value.__class__.__name__ == 'ObjectId':
                            obj[key] = str(value)
                        elif hasattr(value, 'isoformat'):
                            obj[key] = value.isoformat()
                elif isinstance(obj, list):
                    for item in obj:
                        convert_objectids(item)
                return obj
            
            recent_transactions = convert_objectids(recent_transactions)
            
            emit('kati_transaction_update', {
                'type': 'kati_transactions',
                'data': recent_transactions,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            
            logger.debug(f"📡 Kati transactions sent via Socket.IO: {len(recent_transactions)} records")
        else:
            emit('kati_transaction_error', {
                'type': 'error',
                'message': 'Database connection not available',
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            
    except Exception as e:
        logger.error(f"❌ Error handling Kati transaction Socket.IO request: {e}")
        emit('kati_transaction_error', {
            'type': 'error',
            'message': str(e),
            'timestamp': datetime.now(timezone.utc).isoformat()
        })

def broadcast_kati_transaction_update(transaction_data: dict):
    """Broadcast Kati transaction update to all connected Socket.IO clients"""
    try:
        # Convert transaction data to JSON serializable format
        def convert_for_broadcast(obj):
            if isinstance(obj, dict):
                return {k: convert_for_broadcast(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_for_broadcast(item) for item in obj]
            elif hasattr(obj, 'isoformat'):
                return obj.isoformat()
            elif hasattr(obj, '__str__'):
                return str(obj)
            else:
                return obj
        
        # Convert the transaction data to ensure it's JSON serializable
        serializable_transaction = convert_for_broadcast(transaction_data)
        
        # Broadcast to all connected clients
        socketio.emit('kati_transaction_update', {
            'type': 'new_kati_transaction',
            'data': serializable_transaction,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        
        logger.debug(f"📡 Kati transaction broadcasted via Socket.IO: {serializable_transaction.get('device_id', 'unknown')}")
        
    except Exception as e:
        logger.error(f"❌ Error broadcasting Kati transaction: {e}")

# Add route to serve patient profile images
@app.route('/patient_profile_images/<path:filename>')
def serve_patient_image(filename):
    """Serve patient profile images from static directory"""
    try:
        return app.send_static_file(f'patient_profile_images/{filename}')
    except Exception as e:
        logger.warning(f"Patient image not found: {filename}")
        # Return a default avatar or 404
        return app.send_static_file('user_profiles/default-avatar.png')

@app.route('/api/kati-transactions/<transaction_id>/location-details')
@login_required
def get_location_details(transaction_id):
    """Get detailed location data with hospital lookup and enhanced patient info for a specific transaction"""
    try:
        # Check if MongoDB connection is available
        if mqtt_monitor.db is None:
            return jsonify({
                "success": False,
                "error": "Database connection not available"
            }), 503

        # Get the transaction
        medical_data_collection = mqtt_monitor.db['medical_data']
        transaction = medical_data_collection.find_one({'_id': ObjectId(transaction_id)})
        
        if not transaction:
            return jsonify({
                "success": False,
                "error": "Transaction not found"
            }), 404
        
        # Check if this is a location or emergency transaction
        topic = transaction.get('topic', '')
        if topic not in ['iMEDE_watch/location', 'iMEDE_watch/sos', 'iMEDE_watch/fallDown']:
            return jsonify({
                "success": False,
                "error": "Transaction is not a location or emergency record"
            }), 400
        
        # Extract location data
        location_data = transaction.get('data', {}).get('location', {})
        
        if not location_data:
            return jsonify({
                "success": False,
                "error": "No location data found in transaction"
            }), 404
        
        # Extract coordinates from GPS, LBS, or WiFi
        coordinates = None
        location_source = None
        
        # Try GPS first (most accurate)
        if location_data.get('GPS') and isinstance(location_data['GPS'], dict) and location_data['GPS'].get('latitude') and location_data['GPS'].get('longitude'):
            coordinates = {
                'lat': float(location_data['GPS']['latitude']),
                'lng': float(location_data['GPS']['longitude'])
            }
            location_source = 'GPS'
        # Try LBS (cell tower) if GPS not available
        elif location_data.get('LBS') and isinstance(location_data['LBS'], dict) and location_data['LBS'].get('latitude') and location_data['LBS'].get('longitude'):
            coordinates = {
                'lat': float(location_data['LBS']['latitude']),
                'lng': float(location_data['LBS']['longitude'])
            }
            location_source = 'LBS'
        # Try WiFi geolocation if available
        elif location_data.get('WiFi') and isinstance(location_data['WiFi'], dict) and location_data['WiFi'].get('latitude') and location_data['WiFi'].get('longitude'):
            coordinates = {
                'lat': float(location_data['WiFi']['latitude']),
                'lng': float(location_data['WiFi']['longitude'])
            }
            location_source = 'WiFi'
        
        # Enhanced patient information
        enhanced_patient_info = None
        if transaction.get('patient_id'):
            try:
                patients_collection = mqtt_monitor.db['patients']
                patient = patients_collection.find_one({'_id': ObjectId(transaction['patient_id'])})
                
                if patient:
                    # Extract hospital and ward data with proper type checking
                    hospital_ward_data = patient.get('hospital_ward_data', {})
                    
                    # Handle different data types for hospital_ward_data
                    if isinstance(hospital_ward_data, list) and len(hospital_ward_data) > 0:
                        hospital_ward_data = hospital_ward_data[0]  # Take first entry
                    elif not isinstance(hospital_ward_data, dict):
                        hospital_ward_data = {}  # Reset to empty dict if not a dict
                    
                    enhanced_patient_info = {
                        'patient_id': str(patient['_id']),
                        'first_name': patient.get('first_name', ''),
                        'last_name': patient.get('last_name', ''),
                        'profile_image': patient.get('profile_image', ''),
                        'mobile_phone': patient.get('mobile_phone', ''),
                        'emergency_contact': patient.get('emergency_contact', ''),
                        'underlying_conditions': patient.get('underlying_conditions', []),
                        'allergies': patient.get('allergies', []),
                        'hospital_name': hospital_ward_data.get('hospital_name', '') if isinstance(hospital_ward_data, dict) else '',
                        'ward_name': hospital_ward_data.get('ward_name', '') if isinstance(hospital_ward_data, dict) else '',
                        'room_number': hospital_ward_data.get('room_number', '') if isinstance(hospital_ward_data, dict) else '',
                        'admission_date': hospital_ward_data.get('admission_date', '') if isinstance(hospital_ward_data, dict) else '',
                        'discharge_date': hospital_ward_data.get('discharge_date', '') if isinstance(hospital_ward_data, dict) else ''
                    }
            except Exception as e:
                logger.warning(f"Error getting enhanced patient info: {e}")
        
        # Find nearest hospital if coordinates are available
        hospital = None
        if coordinates:
            try:
                # Get all hospitals with location data
                hospitals_collection = mqtt_monitor.db['hospitals']
                hospitals = list(hospitals_collection.find({
                    'location': {'$exists': True},
                    'location.latitude': {'$exists': True},
                    'location.longitude': {'$exists': True}
                }))
                
                if hospitals:
                    # Calculate distances and find nearest hospital
                    nearest_hospital = None
                    min_distance = float('inf')
                    
                    for hosp in hospitals:
                        hosp_location = hosp.get('location', {})
                        if hosp_location.get('latitude') and hosp_location.get('longitude'):
                            # Calculate distance using Haversine formula
                            distance = calculate_distance(
                                coordinates['lat'], coordinates['lng'],
                                float(hosp_location['latitude']), float(hosp_location['longitude'])
                            )
                            
                            if distance < min_distance:
                                min_distance = distance
                                nearest_hospital = hosp
                    
                    if nearest_hospital:
                        hospital = {
                            'name': nearest_hospital.get('name', 'Unknown Hospital'),
                            'address': nearest_hospital.get('address', 'Address not available'),
                            'phone': nearest_hospital.get('phone', 'Phone not available'),
                            'lat': float(nearest_hospital['location']['latitude']),
                            'lng': float(nearest_hospital['location']['longitude']),
                            'distance': round(min_distance, 2)
                        }
            except Exception as e:
                logger.warning(f"Error finding nearest hospital: {e}")
        
        # Convert ObjectIds to strings
        def convert_objectids(obj):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if isinstance(value, dict):
                        convert_objectids(value)
                    elif isinstance(value, list):
                        for item in value:
                            convert_objectids(item)
                    elif hasattr(value, '__class__') and value.__class__.__name__ == 'ObjectId':
                        obj[key] = str(value)
                    elif hasattr(value, 'isoformat'):  # Handle datetime objects
                        obj[key] = value.isoformat()
            elif isinstance(obj, list):
                for item in obj:
                    convert_objectids(item)
            return obj
        
        # Convert the response data
        response_data = {
            'transaction_id': str(transaction['_id']),
            'topic': topic,
            'timestamp': transaction.get('timestamp'),
            'device_id': transaction.get('device_id'),
            'location': convert_objectids(location_data),
            'coordinates': coordinates,
            'location_source': location_source,
            'hospital': hospital,
            'enhanced_patient_info': enhanced_patient_info
        }
        
        return jsonify({
            "success": True,
            "data": response_data
        })
        
    except Exception as e:
        logger.error(f"Error getting location details: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two points using Haversine formula"""
    from math import radians, cos, sin, asin, sqrt
    
    # Convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    
    # Radius of earth in kilometers
    r = 6371
    
    return c * r

@app.route('/api/kati-transactions/<transaction_id>/batch-details')
@login_required
def get_batch_vital_signs_details(transaction_id):
    """Get detailed batch vital signs data for a specific transaction"""
    try:
        # Check if MongoDB connection is available
        if mqtt_monitor.db is None:
            return jsonify({
                "success": False,
                "error": "Database connection not available"
            }), 503

        # Get the transaction
        medical_data_collection = mqtt_monitor.db['medical_data']
        transaction = medical_data_collection.find_one({'_id': ObjectId(transaction_id)})
        
        if not transaction:
            return jsonify({
                "success": False,
                "error": "Transaction not found"
            }), 404
        
        # Check if this is a batch vital signs transaction
        if transaction.get('event_type') != 'batch_vital_signs':
            return jsonify({
                "success": False,
                "error": "Transaction is not a batch vital signs record"
            }), 400
        
        # Extract batch data
        batch_data = transaction.get('data', {})
        # Check for vital_signs array first, then fall back to data array
        vital_signs_list = batch_data.get('vital_signs', batch_data.get('data', []))
        
        if not vital_signs_list:
            return jsonify({
                "success": False,
                "error": "No vital signs data found in batch"
            }), 404
        
        # Calculate averages
        heart_rates = []
        blood_pressures_sys = []
        blood_pressures_dia = []
        body_temperatures = []
        spo2_values = []
        
        for vital_sign in vital_signs_list:
            if vital_sign.get('heartRate'):
                heart_rates.append(float(vital_sign['heartRate']))
            if vital_sign.get('bloodPressure'):
                bp = vital_sign['bloodPressure']
                if bp.get('bp_sys'):
                    blood_pressures_sys.append(float(bp['bp_sys']))
                if bp.get('bp_dia'):
                    blood_pressures_dia.append(float(bp['bp_dia']))
            if vital_sign.get('bodyTemperature'):
                body_temperatures.append(float(vital_sign['bodyTemperature']))
            if vital_sign.get('spO2'):
                spo2_values.append(float(vital_sign['spO2']))
        
        # Calculate averages
        averages = {
            'heartRate': round(sum(heart_rates) / len(heart_rates), 1) if heart_rates else None,
            'bloodPressure': {
                'systolic': round(sum(blood_pressures_sys) / len(blood_pressures_sys), 1) if blood_pressures_sys else None,
                'diastolic': round(sum(blood_pressures_dia) / len(blood_pressures_dia), 1) if blood_pressures_dia else None
            },
            'bodyTemperature': round(sum(body_temperatures) / len(body_temperatures), 1) if body_temperatures else None,
            'spO2': round(sum(spo2_values) / len(spo2_values), 1) if spo2_values else None
        }
        
        # Get enhanced patient info if available
        patient_info = None
        enhanced_patient_info = None
        if transaction.get('patient_id'):
            try:
                patient = mqtt_monitor.db.patients.find_one({'_id': transaction['patient_id']})
                if patient:
                    # Basic patient info
                    patient_info = {
                        'first_name': patient.get('first_name', ''),
                        'last_name': patient.get('last_name', ''),
                        'profile_image': patient.get('profile_image', '')
                    }
                    
                    # Enhanced patient info (same as location details)
                    enhanced_patient_info = {
                        'first_name': patient.get('first_name', ''),
                        'last_name': patient.get('last_name', ''),
                        'profile_image': patient.get('profile_image', ''),
                        'date_of_birth': patient.get('date_of_birth'),
                        'gender': patient.get('gender'),
                        'mobile_phone': patient.get('mobile_phone'),
                        'emergency_contact': patient.get('emergency_contact'),
                        'underlying_conditions': patient.get('underlying_conditions', []),
                        'allergies': patient.get('allergies', [])
                    }
                    
                    # Add hospital and ward information if available
                    if patient.get('hospital_ward_data'):
                        hospital_ward_data = patient['hospital_ward_data']
                        if isinstance(hospital_ward_data, list) and len(hospital_ward_data) > 0:
                            # If it's a list, take the first entry
                            hospital_info = hospital_ward_data[0]
                            enhanced_patient_info['hospital_name'] = hospital_info.get('hospital_name', '')
                            enhanced_patient_info['ward_name'] = hospital_info.get('ward_name', '')
                        elif isinstance(hospital_ward_data, dict):
                            # If it's a dict, use it directly
                            enhanced_patient_info['hospital_name'] = hospital_ward_data.get('hospital_name', '')
                            enhanced_patient_info['ward_name'] = hospital_ward_data.get('ward_name', '')
                    
            except Exception as e:
                logger.warning(f"Error getting patient info: {e}")
        
        # Convert ObjectIds to strings
        def convert_objectids(obj):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if isinstance(value, dict):
                        convert_objectids(value)
                    elif isinstance(value, list):
                        for item in value:
                            convert_objectids(item)
                    elif hasattr(value, '__class__') and value.__class__.__name__ == 'ObjectId':
                        obj[key] = str(value)
                    elif hasattr(value, 'isoformat'):  # Handle datetime objects
                        obj[key] = value.isoformat()
            elif isinstance(obj, list):
                for item in obj:
                    convert_objectids(item)
            return obj
        
        # Convert the response data
        response_data = {
            'transaction_id': str(transaction['_id']),
            'timestamp': transaction.get('timestamp'),
            'device_id': transaction.get('device_id'),
            'patient_info': patient_info,
            'enhanced_patient_info': enhanced_patient_info,
            'batch_size': len(vital_signs_list),
            'averages': averages,
            'vital_signs': convert_objectids(vital_signs_list)
        }
        
        return jsonify({
            "success": True,
            "data": response_data
        })
        
    except Exception as e:
        logger.error(f"Error getting batch vital signs details: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=8098, debug=True, allow_unsafe_werkzeug=True) 