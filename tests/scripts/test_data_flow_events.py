#!/usr/bin/env python3
"""
Test Data Flow Events
Generate sample data flow events to test the data flow monitoring page
"""

import requests
import json
import time
from datetime import datetime

def send_data_flow_event(step, status, device_type, topic, payload, patient_info=None, error=None):
    """Send a data flow event to the web panel"""
    event_data = {
        "step": step,
        "status": status,
        "device_type": device_type,
        "topic": topic,
        "timestamp": datetime.utcnow().isoformat(),
        "payload": payload,
        "patient_info": patient_info,
        "error": error
    }
    
    try:
        response = requests.post(
            "http://localhost:8098/api/data-flow/emit",
            json={"event": event_data},
            timeout=5
        )
        
        if response.status_code == 200:
            print(f"✅ Event sent: {step} - {status} - {device_type}")
        else:
            print(f"❌ Failed to send event: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error sending event: {e}")

def test_ava4_flow():
    """Test AVA4 device data flow"""
    print("\n🔄 Testing AVA4 Data Flow...")
    
    # Sample AVA4 payload
    payload = {
        "type": "reportAttribute",
        "mac": "AA:BB:CC:DD:EE:FF",
        "deviceCode": "BP001",
        "data": {
            "attribute": "blood_pressure",
            "value": {
                "systolic": 120,
                "diastolic": 80,
                "pulse": 72
            }
        }
    }
    
    patient_info = {
        "patient_id": "12345",
        "patient_name": "John Doe",
        "first_name": "John",
        "last_name": "Doe"
    }
    
    # Step 1: MQTT Message Received
    send_data_flow_event(
        step="1_mqtt_received",
        status="success",
        device_type="AVA4",
        topic="dusun_pub",
        payload=payload
    )
    time.sleep(1)
    
    # Step 2: Payload Parsed
    send_data_flow_event(
        step="2_payload_parsed",
        status="success",
        device_type="AVA4",
        topic="dusun_pub",
        payload=payload,
        patient_info=patient_info
    )
    time.sleep(1)
    
    # Step 3: Patient Lookup
    send_data_flow_event(
        step="3_patient_lookup",
        status="success",
        device_type="AVA4",
        topic="dusun_pub",
        payload=payload,
        patient_info=patient_info
    )
    time.sleep(1)
    
    # Step 4: Patient Updated
    send_data_flow_event(
        step="4_patient_updated",
        status="success",
        device_type="AVA4",
        topic="dusun_pub",
        payload=payload,
        patient_info=patient_info
    )
    time.sleep(1)
    
    # Step 5: Medical Data Stored
    send_data_flow_event(
        step="5_medical_stored",
        status="success",
        device_type="AVA4",
        topic="dusun_pub",
        payload=payload,
        patient_info=patient_info
    )

def test_kati_flow():
    """Test Kati Watch data flow"""
    print("\n⌚ Testing Kati Watch Data Flow...")
    
    # Sample Kati payload
    payload = {
        "type": "health_data",
        "imei": "123456789012345",
        "data": {
            "heart_rate": 75,
            "steps": 8500,
            "sleep_hours": 7.5
        }
    }
    
    patient_info = {
        "patient_id": "67890",
        "patient_name": "Jane Smith",
        "first_name": "Jane",
        "last_name": "Smith"
    }
    
    # Step 1: MQTT Message Received
    send_data_flow_event(
        step="1_mqtt_received",
        status="success",
        device_type="Kati",
        topic="kati/health",
        payload=payload
    )
    time.sleep(1)
    
    # Step 2: Payload Parsed
    send_data_flow_event(
        step="2_payload_parsed",
        status="success",
        device_type="Kati",
        topic="kati/health",
        payload=payload,
        patient_info=patient_info
    )
    time.sleep(1)
    
    # Step 3: Patient Lookup
    send_data_flow_event(
        step="3_patient_lookup",
        status="success",
        device_type="Kati",
        topic="kati/health",
        payload=payload,
        patient_info=patient_info
    )
    time.sleep(1)
    
    # Step 4: Patient Updated
    send_data_flow_event(
        step="4_patient_updated",
        status="success",
        device_type="Kati",
        topic="kati/health",
        payload=payload,
        patient_info=patient_info
    )
    time.sleep(1)
    
    # Step 5: Medical Data Stored
    send_data_flow_event(
        step="5_medical_stored",
        status="success",
        device_type="Kati",
        topic="kati/health",
        payload=payload,
        patient_info=patient_info
    )

def test_error_flow():
    """Test error handling in data flow"""
    print("\n❌ Testing Error Flow...")
    
    payload = {
        "type": "invalid_data",
        "mac": "FF:EE:DD:CC:BB:AA",
        "data": "invalid_format"
    }
    
    # Error in payload parsing
    send_data_flow_event(
        step="2_payload_parsed",
        status="error",
        device_type="AVA4",
        topic="dusun_pub",
        payload=payload,
        error="Invalid JSON format in payload"
    )
    time.sleep(1)
    
    # Error in patient lookup
    send_data_flow_event(
        step="3_patient_lookup",
        status="error",
        device_type="AVA4",
        topic="dusun_pub",
        payload=payload,
        error="Patient not found for device FF:EE:DD:CC:BB:AA"
    )

if __name__ == "__main__":
    print("🚀 Starting Data Flow Event Tests...")
    print("Make sure the web panel is running on http://localhost:8098")
    
    # Test multiple flows
    test_ava4_flow()
    time.sleep(2)
    
    test_kati_flow()
    time.sleep(2)
    
    test_error_flow()
    
    print("\n✅ All test events sent!")
    print("Check the Data Flow page at http://localhost:8098/data-flow") 