#!/usr/bin/env python3
"""
Test script to send data flow events to verify the main Data Flow page is working
"""

import requests
import json
import time
from datetime import datetime

def send_data_flow_event():
    """Send a test data flow event to the backend"""
    
    # Test data flow event
    test_event = {
        "step": "1_mqtt_received",
        "status": "success",
        "device_type": "AVA4",
        "topic": "ESP32_BLE_GW_TX",
        "timestamp": datetime.now().isoformat(),
        "payload": {
            "from": "ESP32_GW",
            "to": "CLOUD",
            "name": "Test AVA4 Device",
            "time": int(time.time()),
            "mac": "AA:BB:CC:DD:EE:FF",
            "IMEI": "123456789012345",
            "ICCID": "1234567890123456789",
            "type": "HB_Msg",
            "data": {"msg": "Online"}
        },
        "patient_info": {
            "patient_id": "test_patient_123",
            "patient_name": "Test Patient",
            "first_name": "Test",
            "last_name": "Patient"
        },
        "processed_data": {"parsed": True},
        "error": None
    }
    
    try:
        # Send to the data flow endpoint
        response = requests.post(
            "http://localhost:8098/api/data-flow/emit",
            json={"event": test_event},
            headers={"Content-Type": "application/json"},
            timeout=5
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Test event sent successfully: {result}")
            return True
        else:
            print(f"❌ Failed to send test event: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error sending test event: {e}")
        return False

def main():
    print("🧪 Testing Data Flow Main Page...")
    print("=" * 50)
    
    # Send multiple test events
    for i in range(3):
        print(f"\n📡 Sending test event {i+1}/3...")
        success = send_data_flow_event()
        
        if success:
            print(f"✅ Event {i+1} sent successfully")
        else:
            print(f"❌ Event {i+1} failed")
        
        time.sleep(2)  # Wait between events
    
    print("\n" + "=" * 50)
    print("🎯 Test completed!")
    print("📝 Please check the main Data Flow page at: http://localhost:8098/data-flow")
    print("🔍 Look for the test events in the Real-time Data Flow section")

if __name__ == "__main__":
    main() 