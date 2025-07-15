from flask import Flask, render_template, jsonify, request, session, redirect, url_for
from flask_socketio import SocketIO, emit
import pymongo
from datetime import datetime, timedelta
import json
import os
from bson import ObjectId
import logging
from notification_service import send_emergency_notification

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'emergency-dashboard-secret-key')
socketio = SocketIO(app, cors_allowed_origins="*")

# MongoDB connection
MONGO_URI = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/')
client = pymongo.MongoClient(MONGO_URI)
db = client['AMY']

# Emergency alert settings
EMERGENCY_COLORS = {
    'sos': '#ff0000',  # Red
    'fall_down': '#ff6600',  # Orange
    'low_battery': '#ffff00',  # Yellow
    'other': '#ff00ff'  # Magenta
}

EMERGENCY_PRIORITIES = {
    'CRITICAL': {'color': '#ff0000', 'icon': '🚨'},
    'HIGH': {'color': '#ff6600', 'icon': '⚠️'},
    'MEDIUM': {'color': '#ffff00', 'icon': '⚡'},
    'LOW': {'color': '#00ff00', 'icon': 'ℹ️'}
}

@app.route('/')
def index():
    """Main emergency dashboard page"""
    return render_template('emergency_dashboard.html')

@app.route('/api/emergency-alerts')
def get_emergency_alerts():
    """Get emergency alerts from database"""
    try:
        # Get alerts from last 24 hours
        yesterday = datetime.now() - timedelta(hours=24)
        
        alerts = list(db.emergency_alarm.find({
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
def get_emergency_stats():
    """Get emergency alert statistics"""
    try:
        # Last 24 hours
        yesterday = datetime.now() - timedelta(hours=24)
        
        # Total alerts in last 24 hours
        total_24h = db.emergency_alarm.count_documents({
            'timestamp': {'$gte': yesterday}
        })
        
        # Alerts by type
        sos_count = db.emergency_alarm.count_documents({
            'timestamp': {'$gte': yesterday},
            'alert_type': 'sos'
        })
        
        fall_count = db.emergency_alarm.count_documents({
            'timestamp': {'$gte': yesterday},
            'alert_type': 'fall_down'
        })
        
        # Active alerts (not processed)
        active_count = db.emergency_alarm.count_documents({
            'timestamp': {'$gte': yesterday},
            'processed': False
        })
        
        # Alerts by priority
        critical_count = db.emergency_alarm.count_documents({
            'timestamp': {'$gte': yesterday},
            'alert_data.priority': 'CRITICAL'
        })
        
        high_count = db.emergency_alarm.count_documents({
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
def mark_alert_processed(alert_id):
    """Mark an emergency alert as processed"""
    try:
        result = db.emergency_alarm.update_one(
            {'_id': ObjectId(alert_id)},
            {'$set': {'processed': True, 'processed_at': datetime.now()}}
        )
        
        if result.modified_count > 0:
            # Emit to all connected clients
            socketio.emit('alert_processed', {
                'alert_id': alert_id,
                'processed_at': datetime.now().isoformat()
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

@app.route('/api/patients')
def get_patients():
    """Get all patients for filtering"""
    try:
        patients = list(db.patients.find({}, {
            '_id': 1,
            'first_name': 1,
            'last_name': 1,
            'citizen_id': 1
        }).limit(100))
        
        # Convert ObjectIds to strings
        for patient in patients:
            patient['_id'] = str(patient['_id'])
        
        return jsonify({
            'success': True,
            'patients': patients
        })
    except Exception as e:
        logger.error(f"Error fetching patients: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    logger.info(f"Client connected: {request.sid}")
    emit('connected', {'message': 'Connected to Emergency Dashboard'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    logger.info(f"Client disconnected: {request.sid}")

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
        
        # Send external notifications for critical alerts
        if alert_data.get('alert_data', {}).get('priority') in ['CRITICAL', 'HIGH']:
            try:
                notification_results = send_emergency_notification(alert_data)
                logger.info(f"External notifications sent: {notification_results}")
            except Exception as e:
                logger.error(f"Error sending external notifications: {e}")
        
    except Exception as e:
        logger.error(f"Error broadcasting emergency alert: {e}")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5056))
    socketio.run(app, host='0.0.0.0', port=port, debug=True) 