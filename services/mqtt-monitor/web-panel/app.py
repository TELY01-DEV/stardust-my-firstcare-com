#!/usr/bin/env python3
"""
MQTT Monitor Web Panel
Real-time monitoring dashboard for MQTT messages and patient mapping
"""

import os
import json
import logging
from datetime import datetime, timedelta
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

# Configure SocketIO for production
is_production = os.getenv('FLASK_ENV') == 'production' or os.getenv('ENVIRONMENT') == 'production'
if is_production:
    # Production configuration
    socketio = SocketIO(
        app, 
        cors_allowed_origins="*",
        logger=True,
        engineio_logger=True
    )
else:
    # Development configuration
    socketio = SocketIO(app, cors_allowed_origins="*")

# JWT Authentication Configuration
JWT_AUTH_BASE_URL = os.environ.get('JWT_AUTH_BASE_URL', 'https://stardust-v1.my-firstcare.com')
JWT_LOGIN_ENDPOINT = os.environ.get('JWT_LOGIN_ENDPOINT', '/auth/login')
JWT_ME_ENDPOINT = os.environ.get('JWT_ME_ENDPOINT', '/auth/me')
JWT_REFRESH_ENDPOINT = os.environ.get('JWT_REFRESH_ENDPOINT', '/auth/refresh')

# Initialize MQTT monitor
mongodb_uri = os.getenv('MONGODB_URI')
mongodb_database = os.getenv('MONGODB_DATABASE', 'AMY')
mqtt_monitor = MQTTMonitor(mongodb_uri, mongodb_database)

# Transaction logging system
class TransactionLogger:
    def __init__(self, db):
        self.db = db
        self.transactions_collection = db.transaction_logs
    
    async def log_transaction(self, operation: str, data_type: str, collection: str, 
                            patient_id: str = None, status: str = "success", 
                            details: str = None, device_id: str = None):
        """Log a data processing transaction"""
        try:
            transaction = {
                "operation": operation,
                "data_type": data_type,
                "collection": collection,
                "patient_id": patient_id,
                "status": status,
                "details": details,
                "device_id": device_id,
                "timestamp": datetime.utcnow(),
                "created_at": datetime.utcnow()
            }
            
            await self.transactions_collection.insert_one(transaction)
            logger.info(f"📝 Transaction logged: {operation} - {data_type} - {collection}")
            
        except Exception as e:
            logger.error(f"Error logging transaction: {e}")
    
    async def get_recent_transactions(self, limit: int = 50):
        """Get recent transactions"""
        try:
            transactions = await self.transactions_collection.find().sort("timestamp", -1).limit(limit).to_list(length=limit)
            
            # Convert ObjectIds to strings
            for transaction in transactions:
                transaction["_id"] = str(transaction["_id"])
                transaction["timestamp"] = transaction["timestamp"].isoformat()
                transaction["created_at"] = transaction["created_at"].isoformat()
            
            return transactions
        except Exception as e:
            logger.error(f"Error getting transactions: {e}")
            return []

# Initialize transaction logger with error handling
try:
    transaction_logger = TransactionLogger(mqtt_monitor.db) if mqtt_monitor.db is not None else None
    if transaction_logger is not None:
        logger.info("✅ Transaction logger initialized successfully")
    else:
        logger.warning("⚠️ Transaction logger not initialized - no database connection")
except Exception as e:
    logger.error(f"❌ Failed to initialize transaction logger: {e}")
    transaction_logger = None

def refresh_jwt_token():
    """Refresh JWT token using refresh token"""
    try:
        if 'refresh_token' not in session:
            return False
        
        response = requests.post(
            f"{JWT_AUTH_BASE_URL}{JWT_REFRESH_ENDPOINT}",
            json={"refresh_token": session['refresh_token']},
            timeout=10
        )
        
        if response.status_code == 200:
            tokens = response.json()
            session['jwt_token'] = tokens.get('access_token')
            session['refresh_token'] = tokens.get('refresh_token', session['refresh_token'])
            logger.info("✅ JWT token refreshed successfully")
            return True
        else:
            logger.warning(f"Token refresh failed: {response.status_code}")
            return False
            
    except requests.RequestException as e:
        logger.error(f"Token refresh error: {e}")
        return False

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
            
            if response.status_code == 200:
                # Token is valid
                return f(*args, **kwargs)
            elif response.status_code == 401:
                # Token expired, try to refresh
                if refresh_jwt_token():
                    # Retry with new token
                    response = requests.get(
                        f"{JWT_AUTH_BASE_URL}{JWT_ME_ENDPOINT}",
                        headers={"Authorization": f"Bearer {session['jwt_token']}"},
                        timeout=10
                    )
                    if response.status_code == 200:
                        return f(*args, **kwargs)
                
                # Refresh failed, clear session and redirect to login
                session.clear()
                return redirect(url_for('login'))
            else:
                # Other error, clear session and redirect to login
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

@app.route('/test')
def test():
    """JavaScript test page (no authentication required)"""
    return render_template('test.html')

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
    """Get patients in frontend-expected structure"""
    try:
        # Get all patients
        patients = list(mqtt_monitor.db.patients.find({}, {
            "_id": 1,
            "first_name": 1,
            "last_name": 1,
            "ava_mac_address": 1,
            "watch_mac_address": 1,
            "registration_status": 1
        }))
        # Map to expected fields
        patient_list = []
        for p in patients:
            # Add AVA4 device
            patient_list.append({
                "patient_id": str(p.get('_id', '')),
                "name": f"{p.get('first_name', '')} {p.get('last_name', '')}",
                "device_type": "AVA4",
                "device_id": p.get('ava_mac_address', ''),
                "status": p.get('registration_status', 'Active').capitalize()
            })
            # Add Kati device
            patient_list.append({
                "patient_id": str(p.get('_id', '')),
                "name": f"{p.get('first_name', '')} {p.get('last_name', '')}",
                "device_type": "Kati",
                "device_id": p.get('watch_mac_address', ''),
                "status": p.get('registration_status', 'Active').capitalize()
            })
        return jsonify({
            "success": True,
            "data": patient_list,
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
    """Get device mappings in frontend-expected structure"""
    try:
        # Get AVA4 devices
        ava4_devices = list(mqtt_monitor.db.amy_boxes.find({}, {
            "_id": 1,
            "mac_address": 1,
            "name": 1,
            "patient_id": 1
        }))
        # Map to expected fields
        ava4 = [
            {
                "device_id": str(dev.get('_id', '')),
                "mac_address": dev.get('mac_address', ''),
                "name": dev.get('name', ''),
                "patient_id": str(dev.get('patient_id', ''))
            } for dev in ava4_devices
        ]
        # Get Kati devices
        kati_devices = list(mqtt_monitor.db.watches.find({}, {
            "_id": 1,
            "imei": 1,
            "patient_id": 1
        }))
        kati = [
            {
                "device_id": str(dev.get('_id', '')),
                "imei": dev.get('imei', ''),
                "patient_id": str(dev.get('patient_id', ''))
            } for dev in kati_devices
        ]
        # Get Qube devices
        qube_devices = list(mqtt_monitor.db.hospitals.find({"mac_hv01_box": {"$exists": True}}, {
            "_id": 1,
            "name": 1,
            "mac_hv01_box": 1
        }))
        qube = [
            {
                "device_id": str(dev.get('_id', '')),
                "name": dev.get('name', ''),
                "mac_hv01_box": dev.get('mac_hv01_box', '')
            } for dev in qube_devices
        ]
        return jsonify({
            "success": True,
            "data": {
                "ava4": ava4,
                "kati": kati,
                "qube": qube
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

@app.route('/api/collection-stats')
@login_required
def get_collection_stats():
    """Get collection statistics"""
    try:
        stats = {}
        
        # Get stats for main collections
        collections = ['patients', 'heart_rate_histories', 'blood_pressure_histories', 
                      'spo2_histories', 'body_temp_histories', 'step_histories', 
                      'sleep_data_histories', 'blood_sugar_histories', 'creatinine_histories',
                      'lipid_histories', 'medication_histories', 'allergy_histories']
        
        for collection_name in collections:
            try:
                collection = mqtt_monitor.db[collection_name]
                count = collection.count_documents({})
                
                # Get collection stats
                stats_command = {"collStats": collection_name}
                coll_stats = mqtt_monitor.db.command(stats_command)
                
                stats[collection_name] = {
                    "total_documents": count,
                    "size": coll_stats.get("size", 0),
                    "storage_size": coll_stats.get("storageSize", 0),
                    "last_updated": datetime.utcnow().isoformat() if count > 0 else None
                }
            except Exception as e:
                logger.error(f"Error getting stats for {collection_name}: {e}")
                stats[collection_name] = {
                    "total_documents": 0,
                    "size": 0,
                    "storage_size": 0,
                    "last_updated": None
                }
        
        return jsonify({
            "success": True,
            "data": stats,
            "timestamp": datetime.utcnow()
        })
    except Exception as e:
        logger.error(f"Error getting collection stats: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/schema')
@login_required
def get_schema():
    """Get database schema information"""
    try:
        schema = {
            "patients": [
                {"name": "_id", "type": "ObjectId", "description": "Unique patient identifier"},
                {"name": "first_name", "type": "String", "description": "Patient's first name"},
                {"name": "last_name", "type": "String", "description": "Patient's last name"},
                {"name": "id_card", "type": "String", "description": "Patient's ID card number"},
                {"name": "ava_mac_address", "type": "String", "description": "AVA4 device MAC address"},
                {"name": "watch_mac_address", "type": "String", "description": "Kati watch MAC address"},
                {"name": "registration_status", "type": "String", "description": "Patient registration status"}
            ],
            "heart_rate_histories": [
                {"name": "_id", "type": "ObjectId", "description": "Unique record identifier"},
                {"name": "patient_id", "type": "ObjectId", "description": "Reference to patient"},
                {"name": "heart_rate", "type": "Number", "description": "Heart rate value (BPM)"},
                {"name": "timestamp", "type": "Date", "description": "Measurement timestamp"},
                {"name": "device_type", "type": "String", "description": "Source device type"}
            ],
            "blood_pressure_histories": [
                {"name": "_id", "type": "ObjectId", "description": "Unique record identifier"},
                {"name": "patient_id", "type": "ObjectId", "description": "Reference to patient"},
                {"name": "systolic", "type": "Number", "description": "Systolic blood pressure"},
                {"name": "diastolic", "type": "Number", "description": "Diastolic blood pressure"},
                {"name": "timestamp", "type": "Date", "description": "Measurement timestamp"},
                {"name": "device_type", "type": "String", "description": "Source device type"}
            ],
            "spo2_histories": [
                {"name": "_id", "type": "ObjectId", "description": "Unique record identifier"},
                {"name": "patient_id", "type": "ObjectId", "description": "Reference to patient"},
                {"name": "spo2", "type": "Number", "description": "SpO2 percentage"},
                {"name": "timestamp", "type": "Date", "description": "Measurement timestamp"},
                {"name": "device_type", "type": "String", "description": "Source device type"}
            ],
            "body_temp_histories": [
                {"name": "_id", "type": "ObjectId", "description": "Unique record identifier"},
                {"name": "patient_id", "type": "ObjectId", "description": "Reference to patient"},
                {"name": "body_temp", "type": "Number", "description": "Body temperature value"},
                {"name": "timestamp", "type": "Date", "description": "Measurement timestamp"},
                {"name": "device_type", "type": "String", "description": "Source device type"}
            ],
            "step_histories": [
                {"name": "_id", "type": "ObjectId", "description": "Unique record identifier"},
                {"name": "patient_id", "type": "ObjectId", "description": "Reference to patient"},
                {"name": "steps", "type": "Number", "description": "Step count"},
                {"name": "timestamp", "type": "Date", "description": "Measurement timestamp"},
                {"name": "device_type", "type": "String", "description": "Source device type"}
            ],
            "sleep_data_histories": [
                {"name": "_id", "type": "ObjectId", "description": "Unique record identifier"},
                {"name": "patient_id", "type": "ObjectId", "description": "Reference to patient"},
                {"name": "sleep_duration", "type": "Number", "description": "Sleep duration in minutes"},
                {"name": "sleep_quality", "type": "String", "description": "Sleep quality rating"},
                {"name": "timestamp", "type": "Date", "description": "Measurement timestamp"},
                {"name": "device_type", "type": "String", "description": "Source device type"}
            ]
        }
        
        return jsonify({
            "success": True,
            "data": schema,
            "timestamp": datetime.utcnow()
        })
    except Exception as e:
        logger.error(f"Error getting schema: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/transactions')
@login_required
def get_transactions():
    """Get transaction logs from Stardust API"""
    try:
        # Get query parameters
        limit = request.args.get('limit', 100, type=int)
        offset = request.args.get('offset', 0, type=int)
        operation = request.args.get('operation')
        data_type = request.args.get('data_type')
        patient_id = request.args.get('patient_id')
        device_id = request.args.get('device_id')
        
        # Build query parameters for Stardust API
        params = {
            'limit': limit,
            'offset': offset
        }
        if operation:
            params['operation'] = operation
        if data_type:
            params['data_type'] = data_type
        if patient_id:
            params['patient_id'] = patient_id
        if device_id:
            params['device_id'] = device_id
        
        # Call Stardust API
        stardust_url = os.getenv('STARDUST_API_URL', 'http://localhost:8000')
        response = requests.get(
            f"{stardust_url}/api/transactions/logs",
            params=params,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                return jsonify({
                    "success": True,
                    "data": result.get("data", {}).get("transactions", []),
                    "total_count": result.get("data", {}).get("total_count", 0),
                    "timestamp": datetime.utcnow().isoformat()
                })
            else:
                return jsonify({
                    "success": False,
                    "error": result.get("message", "Failed to fetch transactions"),
                    "timestamp": datetime.utcnow().isoformat()
                }), 500
        else:
            return jsonify({
                "success": False,
                "error": f"Stardust API error: {response.status_code}",
                "timestamp": datetime.utcnow().isoformat()
            }), 500
            
    except Exception as e:
        logger.error(f"Failed to get transactions: {e}")
        return jsonify({
            "success": False,
            "error": f"Failed to get transactions: {str(e)}",
            "timestamp": datetime.utcnow().isoformat()
        }), 500

# WebSocket event for real-time transaction updates
@socketio.on('subscribe_transactions')
def handle_subscribe_transactions():
    """Subscribe to real-time transaction updates"""
    logger.info("Client subscribed to transaction updates")
    emit('transaction_subscribed', {'status': 'subscribed'})

def broadcast_transaction(transaction_data):
    """Broadcast a new transaction to all connected clients"""
    try:
        socketio.emit('new_transaction', {
            'type': 'transaction',
            'data': transaction_data,
            'timestamp': datetime.utcnow().isoformat()
        })
        logger.info(f"📡 Broadcasted transaction: {transaction_data.get('operation')}")
    except Exception as e:
        logger.error(f"Error broadcasting transaction: {e}")

@app.route('/api/log-transaction', methods=['POST'])
@login_required
def log_transaction():
    """Log a transaction to Stardust API"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['operation', 'data_type', 'collection']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    "success": False,
                    "error": f"Missing required field: {field}"
                }), 400
        
        # Call Stardust API
        stardust_url = os.getenv('STARDUST_API_URL', 'https://stardust.my-firstcare.com')
        response = requests.post(
            f"{stardust_url}/api/transactions/log",
            json=data,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                return jsonify({
                    "success": True,
                    "message": "Transaction logged successfully",
                    "data": result.get("data", {}),
                    "timestamp": datetime.utcnow().isoformat()
                })
            else:
                return jsonify({
                    "success": False,
                    "error": result.get("message", "Failed to log transaction")
                }), 500
        else:
            return jsonify({
                "success": False,
                "error": f"Stardust API error: {response.status_code}"
            }), 500
            
    except Exception as e:
        logger.error(f"Failed to log transaction: {e}")
        return jsonify({
            "success": False,
            "error": f"Failed to log transaction: {str(e)}"
        }), 500

# Device Status API Endpoints
@app.route('/api/device-status/summary')
@login_required
def get_device_status_summary():
    """Get device status summary"""
    try:
        # Call Stardust API
        stardust_url = os.getenv('STARDUST_API_URL', 'http://stardust-api:5054')
        response = requests.get(
            f"{stardust_url}/api/devices/status/summary",
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            return jsonify(result)
        else:
            return jsonify({
                "success": False,
                "error": f"Stardust API error: {response.status_code}"
            }), 500
            
    except Exception as e:
        logger.error(f"Failed to get device status summary: {e}")
        return jsonify({
            "success": False,
            "error": f"Failed to get device status summary: {str(e)}"
        }), 500

@app.route('/api/device-status/health/overview')
@login_required
def get_device_health_overview():
    """Get device health overview"""
    try:
        # Call Stardust API
        stardust_url = os.getenv('STARDUST_API_URL', 'http://stardust-api:5054')
        response = requests.get(
            f"{stardust_url}/api/devices/status/health/overview",
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            return jsonify(result)
        else:
            return jsonify({
                "success": False,
                "error": f"Stardust API error: {response.status_code}"
            }), 500
            
    except Exception as e:
        logger.error(f"Failed to get device health overview: {e}")
        return jsonify({
            "success": False,
            "error": f"Failed to get device health overview: {str(e)}"
        }), 500

@app.route('/api/device-status/recent')
@login_required
def get_device_status_recent():
    """Get recent device status"""
    try:
        # Call Stardust API
        stardust_url = os.getenv('STARDUST_API_URL', 'http://stardust-api:5054')
        response = requests.get(
            f"{stardust_url}/api/devices/status/recent",
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            return jsonify(result)
        else:
            return jsonify({
                "success": False,
                "error": f"Stardust API error: {response.status_code}"
            }), 500
            
    except Exception as e:
        logger.error(f"Failed to get recent device status: {e}")
        return jsonify({
            "success": False,
            "error": f"Failed to get recent device status: {str(e)}"
        }), 500

@app.route('/api/device-status/alerts')
@login_required
def get_device_status_alerts():
    """Get device status alerts"""
    try:
        # Call Stardust API
        stardust_url = os.getenv('STARDUST_API_URL', 'http://stardust-api:5054')
        response = requests.get(
            f"{stardust_url}/api/devices/status/alerts",
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            return jsonify(result)
        else:
            return jsonify({
                "success": False,
                "error": f"Stardust API error: {response.status_code}"
            }), 500
            
    except Exception as e:
        logger.error(f"Failed to get device status alerts: {e}")
        return jsonify({
            "success": False,
            "error": f"Failed to get device status alerts: {str(e)}"
        }), 500

@app.route('/api/device-status/<device_id>')
@login_required
def get_device_status_detail(device_id):
    """Get detailed status for a specific device"""
    try:
        # Call Stardust API
        stardust_url = os.getenv('STARDUST_API_URL', 'http://stardust-api:5054')
        response = requests.get(
            f"{stardust_url}/api/devices/status/{device_id}",
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            return jsonify(result)
        else:
            return jsonify({
                "success": False,
                "error": f"Stardust API error: {response.status_code}"
            }), 500
            
    except Exception as e:
        logger.error(f"Failed to get device status detail: {e}")
        return jsonify({
            "success": False,
            "error": f"Failed to get device status detail: {str(e)}"
        }), 500

# Test endpoints for device status (no authentication required)
@app.route('/test/device-status/summary')
def test_device_status_summary():
    """Test endpoint to get device status summary without authentication"""
    try:
        # Call Stardust API
        stardust_url = os.getenv('STARDUST_API_URL', 'http://localhost:8000')
        response = requests.get(
            f"{stardust_url}/api/devices/status/summary",
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            return jsonify(result)
        else:
            return jsonify({
                "success": True,
                "data": {
                    "total_devices": 0,
                    "online_devices": 0,
                    "offline_devices": 0,
                    "low_battery_devices": 0,
                    "active_alerts": 0,
                    "device_breakdown": {}
                },
                "message": f"Stardust API error: {response.status_code}",
                "timestamp": datetime.utcnow().isoformat()
            })
            
    except Exception as e:
        logger.error(f"Failed to get test device status summary: {e}")
        return jsonify({
            "success": True,
            "data": {
                "total_devices": 0,
                "online_devices": 0,
                "offline_devices": 0,
                "low_battery_devices": 0,
                "active_alerts": 0,
                "device_breakdown": {}
            },
            "message": f"Failed to get device status summary: {str(e)}",
            "timestamp": datetime.utcnow().isoformat()
        })

@app.route('/test/device-status/recent')
def test_device_status_recent():
    """Test endpoint to get recent device status without authentication"""
    try:
        # Call Stardust API
        stardust_url = os.getenv('STARDUST_API_URL', 'http://localhost:8000')
        response = requests.get(
            f"{stardust_url}/api/devices/status/recent",
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            return jsonify(result)
        else:
            return jsonify({
                "success": True,
                "data": [],
                "message": f"Stardust API error: {response.status_code}",
                "timestamp": datetime.utcnow().isoformat()
            })
            
    except Exception as e:
        logger.error(f"Failed to get test recent device status: {e}")
        return jsonify({
            "success": True,
            "data": [],
            "message": f"Failed to get recent device status: {str(e)}",
            "timestamp": datetime.utcnow().isoformat()
        })

@app.route('/test/device-status/alerts')
def test_device_status_alerts():
    """Test endpoint to get device status alerts without authentication"""
    try:
        # Call Stardust API
        stardust_url = os.getenv('STARDUST_API_URL', 'http://localhost:8000')
        response = requests.get(
            f"{stardust_url}/api/devices/status/alerts",
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            return jsonify(result)
        else:
            return jsonify({
                "success": True,
                "data": [],
                "message": f"Stardust API error: {response.status_code}",
                "timestamp": datetime.utcnow().isoformat()
            })
            
    except Exception as e:
        logger.error(f"Failed to get test device status alerts: {e}")
        return jsonify({
            "success": True,
            "data": [],
            "message": f"Failed to get device status alerts: {str(e)}",
            "timestamp": datetime.utcnow().isoformat()
        })

@app.route('/test/device-status/health/overview')
def test_device_health_overview():
    """Test endpoint to get device health overview without authentication"""
    try:
        # Call Stardust API
        stardust_url = os.getenv('STARDUST_API_URL', 'http://stardust-my-firstcare-com:5054')
        response = requests.get(
            f"{stardust_url}/api/devices/status/health/overview",
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            return jsonify(result)
        else:
            return jsonify({
                "success": True,
                "data": {
                    "system_health_score": 85,
                    "avg_response_time": 150,
                    "data_integrity": 98,
                    "uptime_percentage": 99.5,
                    "recent_activity": {
                        "messages_last_hour": 0,
                        "devices_active": 0,
                        "alerts_generated": 0
                    },
                    "alerts_summary": {
                        "critical": 0,
                        "warning": 0,
                        "info": 0
                    }
                },
                "message": f"Stardust API error: {response.status_code}",
                "timestamp": datetime.utcnow().isoformat()
            })
            
    except Exception as e:
        logger.error(f"Failed to get test device health overview: {e}")
        return jsonify({
            "success": True,
            "data": {
                "system_health_score": 85,
                "avg_response_time": 150,
                "data_integrity": 98,
                "uptime_percentage": 99.5,
                "recent_activity": {
                    "messages_last_hour": 0,
                    "devices_active": 0,
                    "alerts_generated": 0
                },
                "alerts_summary": {
                    "critical": 0,
                    "warning": 0,
                    "info": 0
                }
            },
            "message": f"Failed to get device health overview: {str(e)}",
            "timestamp": datetime.utcnow().isoformat()
        })

@app.route('/test/transactions')
def test_transactions():
    """Test endpoint to check transaction data without authentication"""
    try:
        # Call Stardust API
        stardust_url = os.getenv('STARDUST_API_URL', 'http://localhost:8000')
        response = requests.get(
            f"{stardust_url}/api/transactions/logs",
            params={'limit': 100},
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                return jsonify({
                    "success": True,
                    "data": result.get("data", {}).get("transactions", []),
                    "total_count": result.get("data", {}).get("total_count", 0),
                    "timestamp": datetime.utcnow().isoformat()
                })
            else:
                return jsonify({
                    "success": True,
                    "data": [],
                    "message": result.get("message", "No transactions available"),
                    "timestamp": datetime.utcnow().isoformat()
                })
        else:
            return jsonify({
                "success": True,
                "data": [],
                "message": f"Stardust API error: {response.status_code}",
                "timestamp": datetime.utcnow().isoformat()
            })
            
    except Exception as e:
        logger.error(f"Failed to get test transactions: {e}")
        return jsonify({
            "success": True,
            "data": [],
            "message": f"Failed to get transactions: {str(e)}",
            "timestamp": datetime.utcnow().isoformat()
        })

@app.route('/test/schema')
def test_schema():
    """Test endpoint to get schema without authentication"""
    try:
        schema = {
            "patients": [
                {"name": "_id", "type": "ObjectId", "description": "Unique patient identifier"},
                {"name": "first_name", "type": "String", "description": "Patient's first name"},
                {"name": "last_name", "type": "String", "description": "Patient's last name"},
                {"name": "id_card", "type": "String", "description": "Patient's ID card number"},
                {"name": "ava_mac_address", "type": "String", "description": "AVA4 device MAC address"},
                {"name": "watch_mac_address", "type": "String", "description": "Kati watch MAC address"},
                {"name": "registration_status", "type": "String", "description": "Patient registration status"}
            ],
            "heart_rate_histories": [
                {"name": "_id", "type": "ObjectId", "description": "Unique record identifier"},
                {"name": "patient_id", "type": "ObjectId", "description": "Reference to patient"},
                {"name": "heart_rate", "type": "Number", "description": "Heart rate value (BPM)"},
                {"name": "timestamp", "type": "Date", "description": "Measurement timestamp"},
                {"name": "device_type", "type": "String", "description": "Source device type"}
            ],
            "blood_pressure_histories": [
                {"name": "_id", "type": "ObjectId", "description": "Unique record identifier"},
                {"name": "patient_id", "type": "ObjectId", "description": "Reference to patient"},
                {"name": "systolic", "type": "Number", "description": "Systolic blood pressure"},
                {"name": "diastolic", "type": "Number", "description": "Diastolic blood pressure"},
                {"name": "timestamp", "type": "Date", "description": "Measurement timestamp"},
                {"name": "device_type", "type": "String", "description": "Source device type"}
            ],
            "spo2_histories": [
                {"name": "_id", "type": "ObjectId", "description": "Unique record identifier"},
                {"name": "patient_id", "type": "ObjectId", "description": "Reference to patient"},
                {"name": "spo2", "type": "Number", "description": "SpO2 percentage"},
                {"name": "timestamp", "type": "Date", "description": "Measurement timestamp"},
                {"name": "device_type", "type": "String", "description": "Source device type"}
            ],
            "body_temp_histories": [
                {"name": "_id", "type": "ObjectId", "description": "Unique record identifier"},
                {"name": "patient_id", "type": "ObjectId", "description": "Reference to patient"},
                {"name": "body_temp", "type": "Number", "description": "Body temperature value"},
                {"name": "timestamp", "type": "Date", "description": "Measurement timestamp"},
                {"name": "device_type", "type": "String", "description": "Source device type"}
            ],
            "step_histories": [
                {"name": "_id", "type": "ObjectId", "description": "Unique record identifier"},
                {"name": "patient_id", "type": "ObjectId", "description": "Reference to patient"},
                {"name": "steps", "type": "Number", "description": "Step count"},
                {"name": "timestamp", "type": "Date", "description": "Measurement timestamp"},
                {"name": "device_type", "type": "String", "description": "Source device type"}
            ],
            "sleep_data_histories": [
                {"name": "_id", "type": "ObjectId", "description": "Unique record identifier"},
                {"name": "patient_id", "type": "ObjectId", "description": "Reference to patient"},
                {"name": "sleep_duration", "type": "Number", "description": "Sleep duration in minutes"},
                {"name": "sleep_quality", "type": "String", "description": "Sleep quality rating"},
                {"name": "timestamp", "type": "Date", "description": "Measurement timestamp"},
                {"name": "device_type", "type": "String", "description": "Source device type"}
            ],
            "transaction_logs": [
                {"name": "_id", "type": "ObjectId", "description": "Unique transaction identifier"},
                {"name": "operation", "type": "String", "description": "Transaction operation type"},
                {"name": "data_type", "type": "String", "description": "Type of data processed"},
                {"name": "collection", "type": "String", "description": "Target database collection"},
                {"name": "patient_id", "type": "String", "description": "Patient identifier"},
                {"name": "status", "type": "String", "description": "Transaction status"},
                {"name": "details", "type": "String", "description": "Transaction details"},
                {"name": "device_id", "type": "String", "description": "Device identifier"},
                {"name": "timestamp", "type": "Date", "description": "Transaction timestamp"},
                {"name": "created_at", "type": "Date", "description": "Record creation timestamp"}
            ]
        }
        
        return jsonify({
            "success": True,
            "data": schema,
            "timestamp": datetime.utcnow()
        })
    except Exception as e:
        logger.error(f"Error getting schema: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/test/collection-stats')
def test_collection_stats():
    """Test endpoint to get collection stats without authentication"""
    try:
        if mqtt_monitor.db is None:
            return jsonify({
                "success": True,
                "data": {},
                "message": "Database not available",
                "timestamp": datetime.utcnow()
            })
        
        stats = {}
        collections = ['patients', 'heart_rate_histories', 'blood_pressure_histories', 
                      'spo2_histories', 'body_temp_histories', 'step_histories', 
                      'sleep_data_histories', 'transaction_logs']
        
        for collection_name in collections:
            try:
                collection = mqtt_monitor.db[collection_name]
                count = collection.count_documents({})
                
                # Get collection stats
                coll_stats = mqtt_monitor.db.command("collstats", collection_name)
                
                stats[collection_name] = {
                    "total_documents": count,
                    "size": coll_stats.get("size", 0),
                    "storage_size": coll_stats.get("storageSize", 0),
                    "last_updated": datetime.utcnow().isoformat() if count > 0 else None
                }
            except Exception as e:
                logger.error(f"Error getting stats for {collection_name}: {e}")
                stats[collection_name] = {
                    "total_documents": 0,
                    "size": 0,
                    "storage_size": 0,
                    "last_updated": None
                }
        
        return jsonify({
            "success": True,
            "data": stats,
            "timestamp": datetime.utcnow()
        })
    except Exception as e:
        logger.error(f"Error getting collection stats: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/device-mappings')
@login_required
def get_device_mappings():
    """Get comprehensive device mapping data"""
    try:
        # Get AVA4 device mappings
        ava4_mappings = list(mqtt_monitor.db.amy_boxes.find({}, {
            "_id": 1,
            "mac_address": 1,
            "name": 1,
            "patient_id": 1,
            "created_at": 1,
            "updated_at": 1
        }))
        
        # Get Kati device mappings
        kati_mappings = list(mqtt_monitor.db.watches.find({}, {
            "_id": 1,
            "imei": 1,
            "patient_id": 1,
            "created_at": 1,
            "updated_at": 1
        }))
        
        # Get Qube device mappings
        qube_mappings = list(mqtt_monitor.db.hospitals.find({"mac_hv01_box": {"$exists": True}}, {
            "_id": 1,
            "name": 1,
            "mac_hv01_box": 1,
            "created_at": 1,
            "updated_at": 1
        }))
        
        # Process AVA4 mappings
        ava4_data = []
        for dev in ava4_mappings:
            # Get patient info
            patient_info = None
            if dev.get('patient_id'):
                patient = mqtt_monitor.db.patients.find_one({"_id": dev['patient_id']})
                if patient:
                    patient_info = {
                        "patient_id": str(patient.get('_id', '')),
                        "patient_name": f"{patient.get('first_name', '')} {patient.get('last_name', '')}".strip(),
                        "registration_status": patient.get('registration_status', 'Unknown')
                    }
            
            ava4_data.append({
                "device_id": str(dev.get('_id', '')),
                "device_type": "AVA4",
                "mac_address": dev.get('mac_address', ''),
                "name": dev.get('name', ''),
                "patient_info": patient_info,
                "mapping_status": "Mapped" if patient_info else "Unmapped",
                "created_at": dev.get('created_at', dev.get('_id').generation_time).isoformat() if dev.get('created_at') or dev.get('_id') else None,
                "updated_at": dev.get('updated_at', dev.get('_id').generation_time).isoformat() if dev.get('updated_at') or dev.get('_id') else None
            })
        
        # Process Kati mappings
        kati_data = []
        for dev in kati_mappings:
            # Get patient info
            patient_info = None
            if dev.get('patient_id'):
                patient = mqtt_monitor.db.patients.find_one({"_id": dev['patient_id']})
                if patient:
                    patient_info = {
                        "patient_id": str(patient.get('_id', '')),
                        "patient_name": f"{patient.get('first_name', '')} {patient.get('last_name', '')}".strip(),
                        "registration_status": patient.get('registration_status', 'Unknown')
                    }
            
            kati_data.append({
                "device_id": str(dev.get('_id', '')),
                "device_type": "Kati Watch",
                "imei": dev.get('imei', ''),
                "patient_info": patient_info,
                "mapping_status": "Mapped" if patient_info else "Unmapped",
                "created_at": dev.get('created_at', dev.get('_id').generation_time).isoformat() if dev.get('created_at') or dev.get('_id') else None,
                "updated_at": dev.get('updated_at', dev.get('_id').generation_time).isoformat() if dev.get('updated_at') or dev.get('_id') else None
            })
        
        # Process Qube mappings
        qube_data = []
        for dev in qube_mappings:
            qube_data.append({
                "device_id": str(dev.get('_id', '')),
                "device_type": "Qube-Vital",
                "mac_address": dev.get('mac_hv01_box', ''),
                "name": dev.get('name', ''),
                "patient_info": None,  # Qube devices are typically hospital-level
                "mapping_status": "Hospital Device",
                "created_at": dev.get('created_at', dev.get('_id').generation_time).isoformat() if dev.get('created_at') or dev.get('_id') else None,
                "updated_at": dev.get('updated_at', dev.get('_id').generation_time).isoformat() if dev.get('updated_at') or dev.get('_id') else None
            })
        
        return jsonify({
            "success": True,
            "data": {
                "ava4": ava4_data,
                "kati": kati_data,
                "qube": qube_data,
                "summary": {
                    "total_devices": len(ava4_data) + len(kati_data) + len(qube_data),
                    "mapped_devices": len([d for d in ava4_data + kati_data if d['mapping_status'] == 'Mapped']),
                    "unmapped_devices": len([d for d in ava4_data + kati_data if d['mapping_status'] == 'Unmapped']),
                    "ava4_count": len(ava4_data),
                    "kati_count": len(kati_data),
                    "qube_count": len(qube_data)
                }
            },
            "timestamp": datetime.utcnow()
        })
    except Exception as e:
        logger.error(f"Error getting device mappings: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/patient-mappings')
@login_required
def get_patient_mappings():
    """Get comprehensive patient mapping data"""
    try:
        # Get all patients with their device mappings
        patients = list(mqtt_monitor.db.patients.find({}, {
            "_id": 1,
            "first_name": 1,
            "last_name": 1,
            "ava_mac_address": 1,
            "watch_mac_address": 1,
            "registration_status": 1,
            "created_at": 1,
            "updated_at": 1
        }))
        
        patient_mappings = []
        for patient in patients:
            patient_id = str(patient.get('_id', ''))
            patient_name = f"{patient.get('first_name', '')} {patient.get('last_name', '')}".strip()
            
            # Get AVA4 device info
            ava4_device = None
            if patient.get('ava_mac_address'):
                ava4 = mqtt_monitor.db.amy_boxes.find_one({"mac_address": patient['ava_mac_address']})
                if ava4:
                    ava4_device = {
                        "device_id": str(ava4.get('_id', '')),
                        "device_type": "AVA4",
                        "mac_address": ava4.get('mac_address', ''),
                        "name": ava4.get('name', ''),
                        "mapping_status": "Mapped"
                    }
            
            # Get Kati device info
            kati_device = None
            if patient.get('watch_mac_address'):
                kati = mqtt_monitor.db.watches.find_one({"imei": patient['watch_mac_address']})
                if kati:
                    kati_device = {
                        "device_id": str(kati.get('_id', '')),
                        "device_type": "Kati Watch",
                        "imei": kati.get('imei', ''),
                        "mapping_status": "Mapped"
                    }
            
            # Count mapped devices
            mapped_devices = sum([1 for device in [ava4_device, kati_device] if device])
            
            patient_mappings.append({
                "patient_id": patient_id,
                "patient_name": patient_name,
                "registration_status": patient.get('registration_status', 'Unknown'),
                "devices": {
                    "ava4": ava4_device,
                    "kati": kati_device
                },
                "mapping_summary": {
                    "total_devices": 2,  # AVA4 + Kati
                    "mapped_devices": mapped_devices,
                    "unmapped_devices": 2 - mapped_devices
                },
                "created_at": patient.get('created_at', patient.get('_id').generation_time).isoformat() if patient.get('created_at') or patient.get('_id') else None,
                "updated_at": patient.get('updated_at', patient.get('_id').generation_time).isoformat() if patient.get('updated_at') or patient.get('_id') else None
            })
        
        return jsonify({
            "success": True,
            "data": {
                "patients": patient_mappings,
                "summary": {
                    "total_patients": len(patient_mappings),
                    "patients_with_devices": len([p for p in patient_mappings if p['mapping_summary']['mapped_devices'] > 0]),
                    "patients_without_devices": len([p for p in patient_mappings if p['mapping_summary']['mapped_devices'] == 0]),
                    "total_device_mappings": sum([p['mapping_summary']['mapped_devices'] for p in patient_mappings])
                }
            },
            "timestamp": datetime.utcnow()
        })
    except Exception as e:
        logger.error(f"Error getting patient mappings: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/recent-mappings')
@login_required
def get_recent_mappings():
    """Get recent device and patient mapping updates for dashboard"""
    try:
        recent_mappings = []
        
        # Get recent AVA4 mappings (last 10)
        ava4_recent = list(mqtt_monitor.db.amy_boxes.find().sort("_id", -1).limit(10))
        for dev in ava4_recent:
            # Get patient info
            patient_info = None
            if dev.get('patient_id'):
                try:
                    # Convert string patient_id to ObjectId if needed
                    from bson import ObjectId
                    if isinstance(dev['patient_id'], str):
                        patient_id_obj = ObjectId(dev['patient_id'])
                    else:
                        patient_id_obj = dev['patient_id']
                    
                    patient = mqtt_monitor.db.patients.find_one({"_id": patient_id_obj})
                    if patient:
                        patient_info = f"{patient.get('first_name', '')} {patient.get('last_name', '')}".strip()
                except Exception as e:
                    logger.warning(f"Error getting patient info for AVA4 device {dev.get('_id')}: {e}")
                    patient_info = None
            
            # Get timestamp safely - handle both ObjectId and string cases
            try:
                if isinstance(dev.get('_id'), ObjectId):
                    timestamp = dev.get('_id').generation_time.isoformat()
                else:
                    # If _id is already a string, use created_at or current time
                    timestamp = dev.get('created_at', datetime.utcnow()).isoformat()
            except Exception as e:
                logger.warning(f"Error getting timestamp for AVA4 device {dev.get('_id')}: {e}")
                timestamp = datetime.utcnow().isoformat()
            
            recent_mappings.append({
                "type": "device_mapping",
                "device_type": "AVA4",
                "device_id": str(dev.get('_id', '')),
                "device_identifier": dev.get('mac_address', ''),
                "patient_name": patient_info,
                "mapping_status": "Mapped" if patient_info else "Unmapped",
                "timestamp": timestamp
            })
        
        # Get recent Kati mappings (last 10)
        kati_recent = list(mqtt_monitor.db.watches.find().sort("_id", -1).limit(10))
        for dev in kati_recent:
            # Get patient info
            patient_info = None
            if dev.get('patient_id'):
                try:
                    # Convert string patient_id to ObjectId if needed
                    from bson import ObjectId
                    if isinstance(dev['patient_id'], str):
                        patient_id_obj = ObjectId(dev['patient_id'])
                    else:
                        patient_id_obj = dev['patient_id']
                    
                    patient = mqtt_monitor.db.patients.find_one({"_id": patient_id_obj})
                    if patient:
                        patient_info = f"{patient.get('first_name', '')} {patient.get('last_name', '')}".strip()
                except Exception as e:
                    logger.warning(f"Error getting patient info for Kati device {dev.get('_id')}: {e}")
                    patient_info = None
            
            # Get timestamp safely - handle both ObjectId and string cases
            try:
                if isinstance(dev.get('_id'), ObjectId):
                    timestamp = dev.get('_id').generation_time.isoformat()
                else:
                    # If _id is already a string, use created_at or current time
                    timestamp = dev.get('created_at', datetime.utcnow()).isoformat()
            except Exception as e:
                logger.warning(f"Error getting timestamp for Kati device {dev.get('_id')}: {e}")
                timestamp = datetime.utcnow().isoformat()
            
            recent_mappings.append({
                "type": "device_mapping",
                "device_type": "Kati Watch",
                "device_id": str(dev.get('_id', '')),
                "device_identifier": dev.get('imei', ''),
                "patient_name": patient_info,
                "mapping_status": "Mapped" if patient_info else "Unmapped",
                "timestamp": timestamp
            })
        
        # Get recent patient registrations (last 10)
        patients_recent = list(mqtt_monitor.db.patients.find().sort("_id", -1).limit(10))
        for patient in patients_recent:
            # Get timestamp safely - handle both ObjectId and string cases
            try:
                if isinstance(patient.get('_id'), ObjectId):
                    timestamp = patient.get('_id').generation_time.isoformat()
                else:
                    # If _id is already a string, use created_at or current time
                    timestamp = patient.get('created_at', datetime.utcnow()).isoformat()
            except Exception as e:
                logger.warning(f"Error getting timestamp for patient {patient.get('_id')}: {e}")
                timestamp = datetime.utcnow().isoformat()
            
            recent_mappings.append({
                "type": "patient_registration",
                "patient_id": str(patient.get('_id', '')),
                "patient_name": f"{patient.get('first_name', '')} {patient.get('last_name', '')}".strip(),
                "registration_status": patient.get('registration_status', 'Unknown'),
                "device_count": sum([1 for device in [patient.get('ava_mac_address'), patient.get('watch_mac_address')] if device]),
                "timestamp": timestamp
            })
        
        # Sort by timestamp (most recent first) and take top 10
        recent_mappings.sort(key=lambda x: x['timestamp'], reverse=True)
        recent_mappings = recent_mappings[:10]
        
        return jsonify({
            "success": True,
            "data": recent_mappings,
            "timestamp": datetime.utcnow()
        })
    except Exception as e:
        logger.error(f"Error getting recent mappings: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

if __name__ == '__main__':
    port = int(os.getenv('WEB_PORT', 8098))
    host = os.getenv('WEB_HOST', '0.0.0.0')
    
    logger.info(f"Starting MQTT Monitor Web Panel on {host}:{port}")
    socketio.run(app, host=host, port=port, debug=False, allow_unsafe_werkzeug=True) 