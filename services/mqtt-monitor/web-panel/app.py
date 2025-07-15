#!/usr/bin/env python3
"""
MQTT Monitor Web Panel
Real-time monitoring dashboard for MQTT messages and patient mapping
Enhanced with Emergency Alert Monitoring
"""

import os
import json
import logging
from datetime import datetime, timedelta
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

# JWT Authentication Configuration
JWT_AUTH_BASE_URL = os.environ.get('JWT_AUTH_BASE_URL', 'https://stardust-v1.my-firstcare.com')
JWT_LOGIN_ENDPOINT = os.environ.get('JWT_LOGIN_ENDPOINT', '/auth/login')
JWT_ME_ENDPOINT = os.environ.get('JWT_ME_ENDPOINT', '/auth/me')

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
    return render_template('index.html')

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
            "timestamp": datetime.utcnow()
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
            elif isinstance(obj, list):
                for item in obj:
                    convert_objectids(item)
            return obj
        
        patients = convert_objectids(patients)
        
        return jsonify({
            "success": True,
            "data": patients,
            "timestamp": datetime.utcnow()
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
            "timestamp": datetime.utcnow()
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
            "timestamp": datetime.utcnow()
        })
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        emit('error', {'error': str(e)})

@socketio.on('get_data_flow_events')
def handle_get_data_flow_events():
    """Handle data flow events request"""
    try:
        # For now, return empty list - events are sent via broadcast
        emit('data_flow_events', {
            "data": [],
            "timestamp": datetime.utcnow()
        })
    except Exception as e:
        logger.error(f"Error getting data flow events: {e}")
        emit('error', {'error': str(e)})

def broadcast_mqtt_message(message):
    """Broadcast MQTT message to all connected clients"""
    socketio.emit('mqtt_message', {
        "data": message,
        "timestamp": datetime.utcnow()
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
            "timestamp": datetime.utcnow().isoformat()
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
                        logger.error(f"Error processing forwarded message: {e}")
                        # Don't let individual message errors stop the forwarding
                        continue
                        
        except Exception as e:
            logger.error(f"Error in MQTT message forwarding: {e}")
            await asyncio.sleep(5)  # Wait before reconnecting

def start_mqtt_forwarding():
    """Start MQTT message forwarding in a separate thread"""
    def run_forwarding():
        try:
            # Create a new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(forward_mqtt_messages())
        except Exception as e:
            logger.error(f"Error in MQTT forwarding thread: {e}")
    
    thread = threading.Thread(target=run_forwarding, daemon=True)
    thread.start()
    logger.info("Started MQTT message forwarding thread")

def create_data_flow_event(step: str, status: str, device_type: str, topic: str, 
                          payload: dict, patient_info: Optional[dict] = None, 
                          processed_data: Optional[dict] = None, error: Optional[str] = None) -> dict:
    """Create a standardized data flow event"""
    return {
        "step": step,
        "status": status,  # "processing", "success", "error"
        "device_type": device_type,
        "topic": topic,
        "timestamp": datetime.utcnow(),
        "payload": payload,
        "patient_info": patient_info,
        "processed_data": processed_data,
        "error": error
    }

@app.route('/api/data-flow/events')
def get_data_flow_events():
    """Get recent data flow events"""
    try:
        # This would typically come from a database or cache
        # For now, return empty list - events are sent via WebSocket
        return jsonify({
            "success": True,
            "data": [],
            "timestamp": datetime.utcnow()
        })
    except Exception as e:
        logger.error(f"Error getting data flow events: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/data-flow/emit', methods=['POST'])
def emit_data_flow_event():
    """Receive data flow events from MQTT listeners and broadcast to clients"""
    try:
        data = request.get_json()
        logger.info(f"📊 Received data flow event request: {data}")
        
        if not data:
            logger.error("No data received in data flow event")
            return jsonify({"success": False, "error": "No data received"}), 400
        
        # Handle both direct event and nested event format
        event = data.get('event', data)
        logger.info(f"📊 Processing data flow event: {event.get('step')} - {event.get('status')}")
        
        # Convert non-serializable objects to JSON-serializable format
        def convert_for_json(obj):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if isinstance(value, datetime):
                        obj[key] = value.isoformat()
                    elif hasattr(value, '__class__') and value.__class__.__name__ == 'ObjectId':
                        obj[key] = str(value)
                    elif isinstance(value, dict):
                        convert_for_json(value)
                    elif isinstance(value, list):
                        for item in value:
                            if isinstance(item, dict):
                                convert_for_json(item)
            return obj
        
        # Convert non-serializable objects in the event
        event = convert_for_json(event)
        logger.info(f"📊 Converted event: {event}")
        
        # Broadcast to all connected clients as data_flow_update
        logger.info("📊 Broadcasting data flow event to all clients")
        socketio.emit('data_flow_update', {
            'type': 'data_flow_update',
            'event': event,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        logger.info("📊 Data flow event broadcasted successfully")
        return jsonify({"success": True, "message": "Event broadcasted"})
    except Exception as e:
        logger.error(f"Error emitting data flow event: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/data-flow-event', methods=['POST'])
def receive_data_flow_event():
    """Simple endpoint to receive data flow events (no auth required for testing)"""
    try:
        data = request.get_json()
        logger.info(f"🔍 Simple data flow event received: {data}")
        
        if not data:
            logger.error("No data received in simple data flow event")
            return jsonify({'error': 'No data received'}), 400
        
        # Convert to JSON serializable format
        def convert_to_json_serializable(obj):
            if isinstance(obj, dict):
                return {k: convert_to_json_serializable(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_to_json_serializable(item) for item in obj]
            elif hasattr(obj, 'isoformat'):  # datetime objects
                return obj.isoformat()
            elif hasattr(obj, '__str__'):  # ObjectId and other objects
                return str(obj)
            else:
                return obj
        
        serializable_data = convert_to_json_serializable(data)
        logger.info(f"🔍 Serialized data: {serializable_data}")
        
        # Add timestamp if not present (ensure it's a dict)
        if isinstance(serializable_data, dict) and 'timestamp' not in serializable_data:
            serializable_data['timestamp'] = datetime.now().isoformat()
        elif not isinstance(serializable_data, dict):
            # If it's not a dict, create a new dict with the data
            serializable_data = {
                'data': serializable_data,
                'timestamp': datetime.now().isoformat()
            }
        
        # Broadcast to all connected clients
        logger.info("🔍 Broadcasting simple data flow event to all clients")
        socketio.emit('data_flow_update', {
            'type': 'data_flow_update',
            'event': serializable_data,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        logger.info("🔍 Simple data flow event processed and broadcasted successfully")
        return jsonify({'status': 'success'})
        
    except Exception as e:
        logger.error(f"Error processing simple data flow event: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/user/profile')
@login_required
def get_user_profile():
    """Get current user profile"""
    try:
        response = requests.get(
            f"{JWT_AUTH_BASE_URL}{JWT_ME_ENDPOINT}",
            headers={"Authorization": f"Bearer {session['jwt_token']}"},
            timeout=10
        )
        
        if response.status_code == 200:
            user_info = response.json()
            return jsonify({
                "success": True,
                "data": user_info,
                "timestamp": datetime.utcnow()
            })
        else:
            return jsonify({
                "success": False,
                "error": "Failed to get user profile"
            }), 401
            
    except requests.RequestException as e:
        logger.error(f"Error getting user profile: {e}")
        return jsonify({
            "success": False,
            "error": "Authentication service unavailable"
        }), 503

# ========================================
# DEVICE AND PATIENT MANAGEMENT PAGES
# ========================================

@app.route('/devices')
@login_required
def devices_page():
    """Devices management page"""
    return render_template('devices.html')

@app.route('/patients')
@login_required
def patients_page():
    """Patients management page"""
    return render_template('patients.html')

@app.route('/messages')
@login_required
def messages_page():
    """MQTT Messages table page"""
    return render_template('messages.html')

# ========================================
# EMERGENCY ALERT MONITORING ENDPOINTS
# ========================================

@app.route('/emergency')
@login_required
def emergency_dashboard():
    """Emergency alert monitoring dashboard"""
    return render_template('emergency_dashboard.html')

@app.route('/api/emergency-alerts')
@login_required
def get_emergency_alerts():
    """Get emergency alerts from database"""
    try:
        # Get time range from query parameter (default 24 hours)
        hours = request.args.get('hours', 24, type=int)
        yesterday = datetime.utcnow() - timedelta(hours=hours)
        
        alerts = list(mqtt_monitor.db.emergency_alarm.find({
            'timestamp': {'$gte': yesterday}
        }).sort('timestamp', -1).limit(100))
        
        # Convert ObjectIds to strings
        for alert in alerts:
            alert['_id'] = str(alert['_id'])
            alert['patient_id'] = str(alert['patient_id'])
            if 'timestamp' in alert:
                alert['timestamp'] = alert['timestamp'].isoformat()
            if 'created_at' in alert:
                alert['created_at'] = alert['created_at'].isoformat()
        
        return jsonify({
            'success': True,
            'alerts': alerts,
            'total': len(alerts)
        })
    except Exception as e:
        logger.error(f"Error fetching emergency alerts: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/emergency-stats')
@login_required
def get_emergency_stats():
    """Get emergency alert statistics"""
    try:
        # Last 24 hours
        yesterday = datetime.utcnow() - timedelta(hours=24)
        
        # Total alerts in last 24 hours
        total_24h = mqtt_monitor.db.emergency_alarm.count_documents({
            'timestamp': {'$gte': yesterday}
        })
        
        # Alerts by type
        sos_count = mqtt_monitor.db.emergency_alarm.count_documents({
            'timestamp': {'$gte': yesterday},
            'alert_type': 'sos'
        })
        
        fall_count = mqtt_monitor.db.emergency_alarm.count_documents({
            'timestamp': {'$gte': yesterday},
            'alert_type': 'fall_down'
        })
        
        # Active alerts (not processed)
        active_count = mqtt_monitor.db.emergency_alarm.count_documents({
            'timestamp': {'$gte': yesterday},
            'processed': False
        })
        
        # Alerts by priority
        critical_count = mqtt_monitor.db.emergency_alarm.count_documents({
            'timestamp': {'$gte': yesterday},
            'alert_data.priority': 'CRITICAL'
        })
        
        high_count = mqtt_monitor.db.emergency_alarm.count_documents({
            'timestamp': {'$gte': yesterday},
            'alert_data.priority': 'HIGH'
        })
        
        return jsonify({
            'success': True,
            'stats': {
                'total_24h': total_24h,
                'sos_count': sos_count,
                'fall_count': fall_count,
                'active_count': active_count,
                'critical_count': critical_count,
                'high_count': high_count
            }
        })
    except Exception as e:
        logger.error(f"Error fetching emergency stats: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/mark-processed/<alert_id>', methods=['POST'])
@login_required
def mark_alert_processed(alert_id):
    """Mark an emergency alert as processed"""
    try:
        result = mqtt_monitor.db.emergency_alarm.update_one(
            {'_id': ObjectId(alert_id)},
            {'$set': {'processed': True, 'processed_at': datetime.utcnow()}}
        )
        
        if result.modified_count > 0:
            # Emit to all connected clients
            socketio.emit('alert_processed', {
                'alert_id': alert_id,
                'processed_at': datetime.utcnow().isoformat()
            })
            
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Alert not found'}), 404
            
    except Exception as e:
        logger.error(f"Error marking alert as processed: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def broadcast_emergency_alert(alert_data):
    """Broadcast emergency alert to all connected clients"""
    try:
        # Convert ObjectIds to strings
        if '_id' in alert_data:
            alert_data['_id'] = str(alert_data['_id'])
        if 'patient_id' in alert_data:
            alert_data['patient_id'] = str(alert_data['patient_id'])
        
        # Convert timestamps
        if 'timestamp' in alert_data:
            alert_data['timestamp'] = alert_data['timestamp'].isoformat()
        if 'created_at' in alert_data:
            alert_data['created_at'] = alert_data['created_at'].isoformat()
        
        # Add visual styling
        alert_data['priority_info'] = EMERGENCY_PRIORITIES.get(
            alert_data.get('alert_data', {}).get('priority', 'MEDIUM'), 
            EMERGENCY_PRIORITIES['MEDIUM']
        )
        
        socketio.emit('new_emergency_alert', alert_data)
        logger.info(f"Broadcasted emergency alert: {alert_data.get('alert_type')} for {alert_data.get('patient_name')}")
        
    except Exception as e:
        logger.error(f"Error broadcasting emergency alert: {e}")

if __name__ == '__main__':
    # Start MQTT message forwarding
    start_mqtt_forwarding()
    
    # Start the Flask app with SocketIO on port 8098
    port = int(os.getenv('WEB_PORT', 8098))
    host = os.getenv('WEB_HOST', '0.0.0.0')
    
    logger.info(f"Starting MQTT Monitor Web Panel on {host}:{port}")
    socketio.run(app, host=host, port=port, debug=False, allow_unsafe_werkzeug=True) 