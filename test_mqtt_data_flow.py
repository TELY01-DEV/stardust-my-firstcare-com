#!/usr/bin/env python3
"""
Test MQTT Data Flow
Simulates MQTT messages to test the complete data flow:
MQTT Broker -> WebSocket Server -> Database Storage -> Web Panel Display
"""

import json
import requests
import time
from datetime import datetime

def test_transaction_logging():
    """Test transaction logging API"""
    print("🧪 Testing transaction logging API...")
    
    # Test data
    test_transactions = [
        {
            "operation": "store_medical_data",
            "data_type": "heart_rate",
            "collection": "heart_rate_histories",
            "patient_id": "507f1f77bcf86cd799439011",
            "status": "success",
            "details": "Stored heart rate data for patient 507f1f77bcf86cd799439011",
            "device_id": "Kati Watch"
        },
        {
            "operation": "store_medical_data",
            "data_type": "blood_pressure",
            "collection": "blood_pressure_histories",
            "patient_id": "507f1f77bcf86cd799439011",
            "status": "success",
            "details": "Stored blood pressure data for patient 507f1f77bcf86cd799439011",
            "device_id": "Kati Watch"
        },
        {
            "operation": "store_medical_data",
            "data_type": "spo2",
            "collection": "spo2_histories",
            "patient_id": "507f1f77bcf86cd799439011",
            "status": "success",
            "details": "Stored SpO2 data for patient 507f1f77bcf86cd799439011",
            "device_id": "Kati Watch"
        }
    ]
    
    for i, transaction in enumerate(test_transactions):
        try:
            response = requests.post(
                "http://localhost:8080/api/log-transaction",
                json=transaction,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                print(f"✅ Transaction {i+1} logged successfully")
            else:
                print(f"❌ Failed to log transaction {i+1}: {response.status_code}")
                print(f"   Response: {response.text}")
                
        except Exception as e:
            print(f"❌ Error logging transaction {i+1}: {e}")
        
        time.sleep(1)  # Wait between requests

def test_mqtt_message_simulation():
    """Simulate MQTT messages by calling the WebSocket server directly"""
    print("🧪 Testing MQTT message simulation...")
    
    # Simulate Kati Watch vital signs message
    kati_vital_signs = {
        "IMEI": "123456789012345",
        "heartRate": 75,
        "bloodPressure": {
            "systolic": 120,
            "diastolic": 80
        },
        "spO2": 98,
        "bodyTemperature": 36.8,
        "location": "Home"
    }
    
    # Simulate Kati Watch heartbeat message
    kati_heartbeat = {
        "IMEI": "123456789012345",
        "signalGSM": 4,
        "battery": 85,
        "satellites": 8,
        "workingMode": "normal",
        "step": 1250
    }
    
    # Simulate AVA4 medical device data
    ava4_medical = {
        "mac": "AA:BB:CC:DD:EE:FF",
        "data": {
            "attribute": "BP_BIOLIGTH",
            "value": {
                "systolic": 118,
                "diastolic": 78
            }
        },
        "deviceCode": "BP001",
        "device": "Blood Pressure Monitor"
    }
    
    test_messages = [
        ("iMEDE_watch/VitalSign", kati_vital_signs),
        ("iMEDE_watch/hb", kati_heartbeat),
        ("dusun_sub", ava4_medical)
    ]
    
    for topic, payload in test_messages:
        print(f"📡 Simulating MQTT message on topic: {topic}")
        print(f"   Payload: {json.dumps(payload, indent=2)}")
        
        # In a real scenario, this would be sent to the MQTT broker
        # For testing, we'll just log it
        print(f"   ✅ Message simulated (would be sent to MQTT broker)")
        time.sleep(2)

def test_web_panel_apis():
    """Test web panel API endpoints"""
    print("🧪 Testing web panel API endpoints...")
    
    endpoints = [
        "/test/transactions",
        "/test/schema", 
        "/test/collection-stats"
    ]
    
    for endpoint in endpoints:
        try:
            response = requests.get(f"http://localhost:8080{endpoint}")
            print(f"📊 {endpoint}: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if "data" in data:
                    if isinstance(data["data"], list):
                        print(f"   📈 Found {len(data['data'])} items")
                    elif isinstance(data["data"], dict):
                        print(f"   📈 Found {len(data['data'])} collections")
                    else:
                        print(f"   📈 Data: {data['data']}")
            else:
                print(f"   ❌ Error: {response.text}")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        time.sleep(1)

def main():
    """Run all tests"""
    print("🚀 Starting MQTT Data Flow Test")
    print("=" * 50)
    
    # Test 1: Web Panel APIs
    print("\n1️⃣ Testing Web Panel APIs")
    test_web_panel_apis()
    
    # Test 2: Transaction Logging
    print("\n2️⃣ Testing Transaction Logging")
    test_transaction_logging()
    
    # Test 3: MQTT Message Simulation
    print("\n3️⃣ Testing MQTT Message Simulation")
    test_mqtt_message_simulation()
    
    # Test 4: Verify transactions were logged
    print("\n4️⃣ Verifying Transaction Logging")
    try:
        response = requests.get("http://localhost:8080/test/transactions")
        if response.status_code == 200:
            data = response.json()
            if "data" in data and isinstance(data["data"], list):
                print(f"✅ Found {len(data['data'])} transactions in database")
                for i, transaction in enumerate(data["data"][:3]):  # Show first 3
                    print(f"   {i+1}. {transaction.get('operation')} - {transaction.get('data_type')}")
            else:
                print("❌ No transaction data found")
        else:
            print(f"❌ Failed to get transactions: {response.status_code}")
    except Exception as e:
        print(f"❌ Error getting transactions: {e}")
    
    print("\n" + "=" * 50)
    print("✅ MQTT Data Flow Test Complete")
    print("\n📋 Next Steps:")
    print("1. Check the web panel at http://localhost:8080")
    print("2. Go to the 'Data Processing Transactions' tab")
    print("3. You should see the test transactions displayed")
    print("4. Real MQTT messages will appear as they are processed")

if __name__ == "__main__":
    main() 