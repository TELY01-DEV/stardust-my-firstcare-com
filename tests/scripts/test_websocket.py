#!/usr/bin/env python3
import requests
import json
from datetime import datetime

def test_data_flow_event():
    """Test data flow event emission"""
    event = {
        "step": "1_mqtt_received",
        "status": "success",
        "device_type": "AVA4",
        "topic": "ESP32_BLE_GW_TX",
        "timestamp": datetime.utcnow().isoformat(),
        "payload": {"mac": "08:B6:1F:88:12:98", "type": "HB_Msg"},
        "patient_info": {"patient_id": "6679433c92df55f28174fdb2", "patient_name": "กิตติศักดิ์ แสงชื่นถนอม"}
    }
    
    try:
        response = requests.post(
            "http://localhost:8098/api/data-flow/emit",
            json={"event": event},
            timeout=5
        )
        print(f"✅ Test event sent: {response.status_code}")
        if response.status_code == 200:
            print("📡 Event should be broadcasted via WebSocket")
            print("🔍 Check your browser console for 'data_flow_update' events")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Testing Data Flow WebSocket Events...")
    test_data_flow_event() 