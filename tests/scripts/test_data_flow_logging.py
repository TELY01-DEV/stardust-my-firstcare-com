#!/usr/bin/env python3
"""
Test script to send data flow events and check logging
"""

import requests
import json
import time
from datetime import datetime

# Configuration
WEB_PANEL_URL = "http://localhost:8098"
BACKEND_URL = "http://localhost:5054"

def test_data_flow_event():
    """Test sending a data flow event to the web panel"""
    
    # Test event data
    test_event = {
        "step": "mqtt_message_received",
        "status": "processing",
        "device_type": "AVA4",
        "topic": "ava4/+/data",
        "timestamp": datetime.now().isoformat(),
        "payload": {
            "mac_address": "AA:BB:CC:DD:EE:FF",
            "heart_rate": 75,
            "temperature": 36.5,
            "blood_pressure": {"systolic": 120, "diastolic": 80}
        },
        "patient_info": {
            "patient_id": "507f1f77bcf86cd799439011",
            "name": "John Doe",
            "id_card": "1234567890123"
        },
        "processed_data": {
            "vital_signs": {
                "heart_rate": 75,
                "temperature": 36.5,
                "blood_pressure": {"systolic": 120, "diastolic": 80}
            }
        }
    }
    
    print("🔍 Testing data flow event...")
    print(f"📊 Event data: {json.dumps(test_event, indent=2)}")
    
    try:
        # Send to simple endpoint (no auth required)
        response = requests.post(
            f"{WEB_PANEL_URL}/api/data-flow-event",
            json=test_event,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        print(f"📊 Response status: {response.status_code}")
        print(f"📊 Response body: {response.text}")
        
        if response.status_code == 200:
            print("✅ Data flow event sent successfully!")
        else:
            print(f"❌ Failed to send data flow event: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error sending data flow event: {e}")

def test_backend_data_flow():
    """Test sending data flow event to backend"""
    
    test_event = {
        "step": "patient_update",
        "status": "success",
        "device_type": "Kati",
        "topic": "kati/+/alert",
        "timestamp": datetime.now().isoformat(),
        "payload": {
            "imei": "123456789012345",
            "alert_type": "sos",
            "location": {"lat": 13.7563, "lng": 100.5018}
        },
        "patient_info": {
            "patient_id": "507f1f77bcf86cd799439012",
            "name": "Jane Smith",
            "id_card": "9876543210987"
        }
    }
    
    print("\n🔍 Testing backend data flow event...")
    print(f"📊 Event data: {json.dumps(test_event, indent=2)}")
    
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/data-flow-event",
            json=test_event,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        print(f"📊 Response status: {response.status_code}")
        print(f"📊 Response body: {response.text}")
        
        if response.status_code == 200:
            print("✅ Backend data flow event sent successfully!")
        else:
            print(f"❌ Failed to send backend data flow event: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error sending backend data flow event: {e}")

def check_web_panel_logs():
    """Check web panel logs"""
    print("\n📋 Checking web panel logs...")
    
    try:
        import subprocess
        result = subprocess.run(
            ["docker", "logs", "stardust-mqtt-panel", "--tail", "20"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            print("📋 Recent web panel logs:")
            print(result.stdout)
        else:
            print(f"❌ Error getting logs: {result.stderr}")
            
    except Exception as e:
        print(f"❌ Error checking logs: {e}")

if __name__ == "__main__":
    print("🚀 Starting data flow event testing...")
    
    # Test web panel endpoint
    test_data_flow_event()
    
    # Wait a moment
    time.sleep(2)
    
    # Test backend endpoint
    test_backend_data_flow()
    
    # Wait a moment
    time.sleep(2)
    
    # Check logs
    check_web_panel_logs()
    
    print("\n✅ Testing completed!") 