#!/usr/bin/env python3
"""
WSGI entry point for MQTT Monitor Web Panel
Production deployment with Gunicorn
"""

import os
import sys
from app import app, socketio

# Configure for production
os.environ['FLASK_ENV'] = 'production'

# Create WSGI application
application = app

if __name__ == '__main__':
    port = int(os.getenv('WEB_PORT', 8080))
    host = os.getenv('WEB_HOST', '0.0.0.0')
    
    print(f"Starting MQTT Monitor Web Panel on {host}:{port}")
    socketio.run(app, host=host, port=port, debug=False, allow_unsafe_werkzeug=True) 