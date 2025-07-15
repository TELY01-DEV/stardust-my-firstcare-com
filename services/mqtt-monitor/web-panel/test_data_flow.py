#!/usr/bin/env python3
"""
Test Data Flow Events
Simulates data flow events for testing the frontend
"""

import time
import json
import requests
from datetime import datetime

def send_data_flow_event(step, status, device_type, topic, payload, patient_info=None, processed_data=None, error=None):
    """Send a data flow event to the web panel"""
    event_data = {
        "step": step,
        "status": status,
        "device_type": device_type,
        "topic": topic,
        "timestamp": datetime.utcnow().isoformat(),
        "payload": payload,
        "patient_info": patient_info,
        "processed_data": processed_data,
        "error": error
    }
    
    try:
        response = requests.post(
            "http://localhost:8098/api/data-flow/emit",
            json={"event": event_data},
            timeout=5
        )
        
        if response.status_code == 200:
            print(f"✅ Event sent: {step} - {status}")
        else:
            print(f"❌ Failed to send event: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error sending event: {e}")

def simulate_ava4_data_flow():
    """Simulate complete AVA4 data flow"""
    print("🔄 Simulating AVA4 data flow...")
    
    # Step 1: MQTT Received
    send_data_flow_event(
        step="1_mqtt_received",
        status="success",
        device_type="AVA4",
        topic="dusun_sub",
        payload={
            "mac": "AA:BB:CC:DD:EE:FF",
            "data": {
                "attribute": "BP_BIOLIGTH",
                "value": {
                    "device_list": [
                        {
                            "systolic": 120,
                            "diastolic": 80,
                            "pulse": 72
                        }
                    ]
                }
            }
        }
    )
    time.sleep(1)
    
    # Step 2: Payload Parsed
    send_data_flow_event(
        step="2_payload_parsed",
        status="success",
        device_type="AVA4",
        topic="dusun_sub",
        payload={
            "mac": "AA:BB:CC:DD:EE:FF",
            "data": {
                "attribute": "BP_BIOLIGTH",
                "value": {
                    "device_list": [
                        {
                            "systolic": 120,
                            "diastolic": 80,
                            "pulse": 72
                        }
                    ]
                }
            }
        },
        processed_data={
            "blood_pressure": {
                "systolic": 120,
                "diastolic": 80,
                "pulse": 72,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
    )
    time.sleep(1)
    
    # Step 3: Patient Lookup
    send_data_flow_event(
        step="3_patient_lookup",
        status="success",
        device_type="AVA4",
        topic="dusun_sub",
        payload={
            "mac": "AA:BB:CC:DD:EE:FF",
            "data": {
                "attribute": "BP_BIOLIGTH",
                "value": {
                    "device_list": [
                        {
                            "systolic": 120,
                            "diastolic": 80,
                            "pulse": 72
                        }
                    ]
                }
            }
        },
        patient_info={
            "patient_id": "507f1f77bcf86cd799439011",
            "patient_name": "John Doe",
            "mapping_type": "ava_mac_address",
            "mapping_value": "AA:BB:CC:DD:EE:FF"
        }
    )
    time.sleep(1)
    
    # Step 4: Patient Updated
    send_data_flow_event(
        step="4_patient_updated",
        status="success",
        device_type="AVA4",
        topic="dusun_sub",
        payload={
            "mac": "AA:BB:CC:DD:EE:FF",
            "data": {
                "attribute": "BP_BIOLIGTH",
                "value": {
                    "device_list": [
                        {
                            "systolic": 120,
                            "diastolic": 80,
                            "pulse": 72
                        }
                    ]
                }
            }
        },
        patient_info={
            "patient_id": "507f1f77bcf86cd799439011",
            "patient_name": "John Doe",
            "mapping_type": "ava_mac_address",
            "mapping_value": "AA:BB:CC:DD:EE:FF"
        },
        processed_data={
            "blood_pressure": {
                "systolic": 120,
                "diastolic": 80,
                "pulse": 72,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
    )
    time.sleep(1)
    
    # Step 5: Medical Stored
    send_data_flow_event(
        step="5_medical_stored",
        status="success",
        device_type="AVA4",
        topic="dusun_sub",
        payload={
            "mac": "AA:BB:CC:DD:EE:FF",
            "data": {
                "attribute": "BP_BIOLIGTH",
                "value": {
                    "device_list": [
                        {
                            "systolic": 120,
                            "diastolic": 80,
                            "pulse": 72
                        }
                    ]
                }
            }
        },
        patient_info={
            "patient_id": "507f1f77bcf86cd799439011",
            "patient_name": "John Doe",
            "mapping_type": "ava_mac_address",
            "mapping_value": "AA:BB:CC:DD:EE:FF"
        },
        processed_data={
            "blood_pressure": {
                "systolic": 120,
                "diastolic": 80,
                "pulse": 72,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
    )

def simulate_kati_data_flow():
    """Simulate complete Kati Watch data flow"""
    print("🔄 Simulating Kati Watch data flow...")
    
    # Step 1: MQTT Received
    send_data_flow_event(
        step="1_mqtt_received",
        status="success",
        device_type="Kati",
        topic="iMEDE_watch/VitalSign",
        payload={
            "IMEI": "123456789012345",
            "vital_signs": {
                "heart_rate": 75,
                "spo2": 98,
                "temperature": 36.5
            }
        }
    )
    time.sleep(1)
    
    # Step 2: Payload Parsed
    send_data_flow_event(
        step="2_payload_parsed",
        status="success",
        device_type="Kati",
        topic="iMEDE_watch/VitalSign",
        payload={
            "IMEI": "123456789012345",
            "vital_signs": {
                "heart_rate": 75,
                "spo2": 98,
                "temperature": 36.5
            }
        },
        processed_data={
            "heart_rate": 75,
            "spo2": 98,
            "temperature": 36.5,
            "timestamp": datetime.utcnow().isoformat()
        }
    )
    time.sleep(1)
    
    # Step 3: Patient Lookup
    send_data_flow_event(
        step="3_patient_lookup",
        status="success",
        device_type="Kati",
        topic="iMEDE_watch/VitalSign",
        payload={
            "IMEI": "123456789012345",
            "vital_signs": {
                "heart_rate": 75,
                "spo2": 98,
                "temperature": 36.5
            }
        },
        patient_info={
            "patient_id": "507f1f77bcf86cd799439012",
            "patient_name": "Jane Smith",
            "mapping_type": "watch_imei",
            "mapping_value": "123456789012345"
        }
    )
    time.sleep(1)
    
    # Step 4: Patient Updated
    send_data_flow_event(
        step="4_patient_updated",
        status="success",
        device_type="Kati",
        topic="iMEDE_watch/VitalSign",
        payload={
            "IMEI": "123456789012345",
            "vital_signs": {
                "heart_rate": 75,
                "spo2": 98,
                "temperature": 36.5
            }
        },
        patient_info={
            "patient_id": "507f1f77bcf86cd799439012",
            "patient_name": "Jane Smith",
            "mapping_type": "watch_imei",
            "mapping_value": "123456789012345"
        },
        processed_data={
            "heart_rate": 75,
            "spo2": 98,
            "temperature": 36.5,
            "timestamp": datetime.utcnow().isoformat()
        }
    )
    time.sleep(1)
    
    # Step 5: Medical Stored
    send_data_flow_event(
        step="5_medical_stored",
        status="success",
        device_type="Kati",
        topic="iMEDE_watch/VitalSign",
        payload={
            "IMEI": "123456789012345",
            "vital_signs": {
                "heart_rate": 75,
                "spo2": 98,
                "temperature": 36.5
            }
        },
        patient_info={
            "patient_id": "507f1f77bcf86cd799439012",
            "patient_name": "Jane Smith",
            "mapping_type": "watch_imei",
            "mapping_value": "123456789012345"
        },
        processed_data={
            "heart_rate": 75,
            "spo2": 98,
            "temperature": 36.5,
            "timestamp": datetime.utcnow().isoformat()
        }
    )

if __name__ == "__main__":
    print("🚀 Starting data flow simulation...")
    
    while True:
        try:
            simulate_ava4_data_flow()
            time.sleep(5)
            simulate_kati_data_flow()
            time.sleep(5)
        except KeyboardInterrupt:
            print("\n⏹️ Simulation stopped")
            break
        except Exception as e:
            print(f"❌ Error in simulation: {e}")
            time.sleep(5) 