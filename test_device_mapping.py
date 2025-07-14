#!/usr/bin/env python3
"""
Test script for device-patient mapping with real MQTT payloads
Tests AVA4, Kati Watch, and Qube-Vital device mapping according to actual requirements
"""

import requests
import json
import time
from datetime import datetime

# API Configuration
BASE_URL = "http://localhost:5054"
TRANSACTION_API = f"{BASE_URL}/api/transactions"

# Authentication
AUTH_TOKEN = None

def get_auth_token():
    """Get JWT authentication token"""
    global AUTH_TOKEN
    try:
        response = requests.post(f"{BASE_URL}/auth/login", json={
            "username": "operapanel",
            "password": "Sim!443355"
        })
        if response.status_code == 200:
            AUTH_TOKEN = response.json().get('access_token')
            return AUTH_TOKEN
        else:
            print(f"Failed to get auth token: {response.status_code}")
            return None
    except Exception as e:
        print(f"Error getting auth token: {e}")
        return None

def get_headers():
    """Get headers with authentication"""
    headers = {"Content-Type": "application/json"}
    if AUTH_TOKEN:
        headers["Authorization"] = f"Bearer {AUTH_TOKEN}"
    return headers

def test_ava4_device_mapping():
    """Test AVA4 device mapping with real payload structure"""
    print("\n=== Testing AVA4 Device Mapping ===")
    
    # Test 1: AVA4 Box Status Message
    ava4_status_payload = {
        "type": "status",
        "mac": "AA:BB:CC:DD:EE:FF",  # This should map to patients.ava_mac_address
        "IMEI": "123456789012345",
        "name": "AVA4_Box_001",
        "status": "online",
        "timestamp": datetime.utcnow().isoformat()
    }
    
    print(f"Testing AVA4 Status: {ava4_status_payload['mac']}")
    response = requests.post(TRANSACTION_API, json={
        "topic": "ESP32_BLE_GW_TX",
        "payload": ava4_status_payload,
        "device_type": "AVA4"
    }, headers=get_headers())
    print(f"Status Response: {response.status_code} - {response.json()}")
    
    # Test 2: AVA4 Blood Pressure Device
    ava4_bp_payload = {
        "type": "reportAttribute",
        "mac": "AA:BB:CC:DD:EE:FF",
        "deviceCode": "AVA4_BP_001",
        "device": "Blood Pressure Monitor",
        "data": {
            "attribute": "BP_BIOLIGTH",
            "value": {
                "device_list": [{
                    "ble_addr": "11:22:33:44:55:66",  # This should map to patients.blood_pressure_mac_address
                    "scan_time": "2024-01-15T10:30:00Z",
                    "scan_rssi": -45,
                    "bp_high": 120,
                    "bp_low": 80,
                    "PR": 72
                }]
            }
        }
    }
    
    print(f"Testing AVA4 Blood Pressure: {ava4_bp_payload['data']['value']['device_list'][0]['ble_addr']}")
    response = requests.post(TRANSACTION_API, json={
        "topic": "dusun_sub",
        "payload": ava4_bp_payload,
        "device_type": "AVA4"
    }, headers=get_headers())
    print(f"BP Response: {response.status_code} - {response.json()}")
    
    # Test 3: AVA4 SpO2 Device
    ava4_spo2_payload = {
        "type": "reportAttribute",
        "mac": "AA:BB:CC:DD:EE:FF",
        "deviceCode": "AVA4_SPO2_001",
        "device": "Pulse Oximeter",
        "data": {
            "attribute": "Oximeter JUMPER",
            "value": {
                "device_list": [{
                    "ble_addr": "AA:BB:CC:DD:EE:77",  # This should map to patients.fingertip_pulse_oximeter_mac_address
                    "scan_time": "2024-01-15T10:31:00Z",
                    "scan_rssi": -42,
                    "spo2": 98,
                    "pulse": 75,
                    "pi": 2.5
                }]
            }
        }
    }
    
    print(f"Testing AVA4 SpO2: {ava4_spo2_payload['data']['value']['device_list'][0]['ble_addr']}")
    response = requests.post(TRANSACTION_API, json={
        "topic": "dusun_sub",
        "payload": ava4_spo2_payload,
        "device_type": "AVA4"
    }, headers=get_headers())
    print(f"SpO2 Response: {response.status_code} - {response.json()}")

def test_kati_watch_mapping():
    """Test Kati Watch device mapping with real payload structure"""
    print("\n=== Testing Kati Watch Device Mapping ===")
    
    # Test 1: Kati Watch Vital Signs
    kati_vital_payload = {
        "IMEI": "987654321098765",  # This should map to patients.watch_mac_address
        "heartRate": 78,
        "bloodPressure": {
            "bp_sys": 125,
            "bp_dia": 82
        },
        "spO2": 97,
        "bodyTemperature": 36.8,
        "signalGSM": 4,
        "battery": 85,
        "location": {
            "lat": 13.7563,
            "lng": 100.5018
        },
        "timeStamps": datetime.utcnow().isoformat()
    }
    
    print(f"Testing Kati Vital Signs: {kati_vital_payload['IMEI']}")
    response = requests.post(TRANSACTION_API, json={
        "topic": "iMEDE_watch/VitalSign",
        "payload": kati_vital_payload,
        "device_type": "Kati Watch"
    }, headers=get_headers())
    print(f"Vital Signs Response: {response.status_code} - {response.json()}")
    
    # Test 2: Kati Watch Heartbeat with Steps
    kati_hb_payload = {
        "IMEI": "987654321098765",
        "signalGSM": 4,
        "battery": 85,
        "satellites": 8,
        "workingMode": "normal",
        "step": 5432,
        "timeStamps": datetime.utcnow().isoformat()
    }
    
    print(f"Testing Kati Heartbeat: {kati_hb_payload['IMEI']}")
    response = requests.post(TRANSACTION_API, json={
        "topic": "iMEDE_watch/hb",
        "payload": kati_hb_payload,
        "device_type": "Kati Watch"
    }, headers=get_headers())
    print(f"Heartbeat Response: {response.status_code} - {response.json()}")
    
    # Test 3: Kati Watch Sleep Data
    kati_sleep_payload = {
        "IMEI": "987654321098765",
        "sleep": {
            "time": 7.5,
            "data": "good",
            "num": 1,
            "timeStamps": datetime.utcnow().isoformat()
        }
    }
    
    print(f"Testing Kati Sleep Data: {kati_sleep_payload['IMEI']}")
    response = requests.post(TRANSACTION_API, json={
        "topic": "iMEDE_watch/sleepdata",
        "payload": kati_sleep_payload,
        "device_type": "Kati Watch"
    }, headers=get_headers())
    print(f"Sleep Data Response: {response.status_code} - {response.json()}")

def test_qube_vital_mapping():
    """Test Qube-Vital device mapping with real payload structure"""
    print("\n=== Testing Qube-Vital Device Mapping ===")
    
    # Test 1: Qube-Vital Blood Pressure (WBP_JUMPER)
    qube_bp_payload = {
        "device_id": "QUBE_VITAL_001",  # This should map to hospitals.mac_hv01_box
        "citiz": "1234567890123",  # This should map to patients.national_id
        "attribute": "WBP_JUMPER",
        "data": {
            "value": {
                "bp_high": 120,
                "bp_low": 80,
                "map": 93,
                "pr": 72
            }
        },
        "timestamp": datetime.utcnow().isoformat()
    }
    
    print(f"Testing Qube-Vital Blood Pressure (WBP_JUMPER): Device={qube_bp_payload['device_id']}, Citizen={qube_bp_payload['citiz']}")
    response = requests.post(TRANSACTION_API, json={
        "topic": "qube/blood_pressure",
        "payload": qube_bp_payload,
        "device_type": "Qube-Vital"
    }, headers=get_headers())
    print(f"Blood Pressure Response: {response.status_code} - {response.json()}")
    
    # Test 2: Qube-Vital Blood Glucose (CONTOUR)
    qube_glucose_payload = {
        "device_id": "QUBE_VITAL_001",
        "citiz": "9876543210987",  # Different citizen ID
        "attribute": "CONTOUR",
        "data": {
            "value": {
                "blood_glucose": 95,
                "marker": "fasting"
            }
        },
        "timestamp": datetime.utcnow().isoformat()
    }
    
    print(f"Testing Qube-Vital Blood Glucose (CONTOUR): Device={qube_glucose_payload['device_id']}, Citizen={qube_glucose_payload['citiz']}")
    response = requests.post(TRANSACTION_API, json={
        "topic": "qube/blood_glucose",
        "payload": qube_glucose_payload,
        "device_type": "Qube-Vital"
    }, headers=get_headers())
    print(f"Blood Glucose Response: {response.status_code} - {response.json()}")
    
    # Test 3: Qube-Vital Weight (BodyScale_JUMPER)
    qube_weight_payload = {
        "device_id": "QUBE_VITAL_001",
        "citiz": "1112223334445",  # Different citizen ID
        "attribute": "BodyScale_JUMPER",
        "data": {
            "value": {
                "weight": 68.5,
                "bmi": 22.1,
                "body_fat": 18.5
            }
        },
        "timestamp": datetime.utcnow().isoformat()
    }
    
    print(f"Testing Qube-Vital Weight (BodyScale_JUMPER): Device={qube_weight_payload['device_id']}, Citizen={qube_weight_payload['citiz']}")
    response = requests.post(TRANSACTION_API, json={
        "topic": "qube/weight",
        "payload": qube_weight_payload,
        "device_type": "Qube-Vital"
    }, headers=get_headers())
    print(f"Weight Response: {response.status_code} - {response.json()}")
    
    # Test 4: Qube-Vital Body Temperature (TEMO_Jumper)
    qube_temp_payload = {
        "device_id": "QUBE_VITAL_001",
        "citiz": "1234567890123",
        "attribute": "TEMO_Jumper",
        "data": {
            "value": {
                "temp": 36.8,
                "mode": "ear"
            }
        },
        "timestamp": datetime.utcnow().isoformat()
    }
    
    print(f"Testing Qube-Vital Body Temperature (TEMO_Jumper): Device={qube_temp_payload['device_id']}, Citizen={qube_temp_payload['citiz']}")
    response = requests.post(TRANSACTION_API, json={
        "topic": "qube/temperature",
        "payload": qube_temp_payload,
        "device_type": "Qube-Vital"
    }, headers=get_headers())
    print(f"Temperature Response: {response.status_code} - {response.json()}")
    
    # Test 5: Qube-Vital SpO2 (Oximeter_JUMPER)
    qube_spo2_payload = {
        "device_id": "QUBE_VITAL_001",
        "citiz": "9876543210987",
        "attribute": "Oximeter_JUMPER",
        "data": {
            "value": {
                "spo2": 98,
                "pulse": 75,
                "pi": 2.5
            }
        },
        "timestamp": datetime.utcnow().isoformat()
    }
    
    print(f"Testing Qube-Vital SpO2 (Oximeter_JUMPER): Device={qube_spo2_payload['device_id']}, Citizen={qube_spo2_payload['citiz']}")
    response = requests.post(TRANSACTION_API, json={
        "topic": "qube/spo2",
        "payload": qube_spo2_payload,
        "device_type": "Qube-Vital"
    }, headers=get_headers())
    print(f"SpO2 Response: {response.status_code} - {response.json()}")

def test_unknown_device():
    """Test unknown device type handling"""
    print("\n=== Testing Unknown Device Type ===")
    
    unknown_payload = {
        "device_id": "UNKNOWN_DEVICE",
        "data": "test_data",
        "timestamp": datetime.utcnow().isoformat()
    }
    
    print(f"Testing Unknown Device: {unknown_payload['device_id']}")
    response = requests.post(TRANSACTION_API, json={
        "topic": "unknown/topic",
        "payload": unknown_payload,
        "device_type": "Unknown"
    }, headers=get_headers())
    print(f"Unknown Device Response: {response.status_code} - {response.json()}")

def check_transactions():
    """Check all transactions in the database"""
    print("\n=== Checking All Transactions ===")
    
    try:
        response = requests.get(f"{BASE_URL}/api/transactions", headers=get_headers())
        if response.status_code == 200:
            transactions = response.json()
            print(f"Total transactions: {len(transactions)}")
            
            # Group by device type
            device_counts = {}
            for tx in transactions:
                device_type = tx.get('device_type', 'Unknown')
                device_counts[device_type] = device_counts.get(device_type, 0) + 1
            
            print("Transactions by device type:")
            for device_type, count in device_counts.items():
                print(f"  {device_type}: {count}")
            
            # Show recent transactions
            print("\nRecent transactions:")
            for tx in transactions[-5:]:  # Last 5 transactions
                print(f"  {tx.get('timestamp')} - {tx.get('device_type')} - {tx.get('status')}")
                if tx.get('patient_mapping'):
                    print(f"    Patient: {tx.get('patient_mapping', {}).get('patient_name', 'Unknown')}")
                if tx.get('error'):
                    print(f"    Error: {tx.get('error')}")
        else:
            print(f"Failed to get transactions: {response.status_code}")
    except Exception as e:
        print(f"Error checking transactions: {e}")

def main():
    """Run all device mapping tests"""
    print("Starting Device Mapping Tests...")
    print(f"API Base URL: {BASE_URL}")
    
    # Get authentication token
    if not get_auth_token():
        print("Failed to get authentication token. Tests may fail.")
    else:
        print("Authentication successful!")
    
    # Test each device type
    test_ava4_device_mapping()
    time.sleep(1)
    
    test_kati_watch_mapping()
    time.sleep(1)
    
    test_qube_vital_mapping()
    time.sleep(1)
    
    test_unknown_device()
    time.sleep(1)
    
    # Check results
    check_transactions()
    
    print("\n=== Device Mapping Tests Complete ===")
    print("Check the web panel at http://localhost:8098 to see the transactions in real-time!")
    print("Check medical history at http://localhost:5054/admin/medical-history-management/")

if __name__ == "__main__":
    main() 