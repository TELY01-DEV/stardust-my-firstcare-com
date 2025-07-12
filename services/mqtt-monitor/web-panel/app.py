#!/usr/bin/env python3
"""
MQTT Monitor Web Panel
Real-time monitoring dashboard for MQTT messages and patient mapping
"""

import os
import json
import logging
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, jsonify, request, redirect, url_for, session
from flask_socketio import SocketIO, emit
import requests
import sys

# Add shared utilities to path
sys.path.append('/app/shared')

from mqtt_monitor import MQTTMonitor

# Configure logging
logging.basicConfig(level=logging.INFO)
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

def login_required(f):
    """Decorator to require JWT authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if user is logged in via session
        if 'jwt_token' not in session:
            return redirect(url_for('login'))
        
        # Verify JWT token with Stardust-V1
        try:
            response = requests.get(
                f"{JWT_AUTH_BASE_URL}{JWT_ME_ENDPOINT}",
                headers={"Authorization": f"Bearer {session['jwt_token']}"},
                timeout=10
            )
            
            if response.status_code != 200:
                # Token is invalid, clear session and redirect to login
                session.clear()
                return redirect(url_for('login'))
                
        except requests.RequestException as e:
            logger.error(f"JWT verification error: {e}")
            session.clear()
            return redirect(url_for('login'))
        
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
@login_required
def index():
    """Main dashboard page"""
    return render_template('index.html')

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

def broadcast_mqtt_message(message):
    """Broadcast MQTT message to all connected clients"""
    socketio.emit('mqtt_message', {
        "data": message,
        "timestamp": datetime.utcnow()
    })

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

if __name__ == '__main__':
    port = int(os.getenv('WEB_PORT', 8080))
    host = os.getenv('WEB_HOST', '0.0.0.0')
    
    logger.info(f"Starting MQTT Monitor Web Panel on {host}:{port}")
    socketio.run(app, host=host, port=port, debug=False, allow_unsafe_werkzeug=True) 