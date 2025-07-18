#!/usr/bin/env python3
"""
Test script to send medical device messages and check if they appear in the medical data table
"""

import requests
import json
import time
from datetime import datetime

def send_mqtt_message(topic, payload):
    """Send MQTT message via web panel API"""
    try:
        url = 'http://localhost:8098/api/data-flow/emit'
        event_data = {
            "step": "test_message",
            "status": "success",
            "device_type": "AVA4",
            "topic": topic,
            "payload": payload,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        response = requests.post(url, json={"event": event_data}, timeout=10)
        if response.status_code == 200:
            print(f"✅ Message sent to {topic}")
            return True
        else:
            print(f"❌ Failed to send message: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error sending message: {e}")
        return False

def check_medical_data():
    """Check recent medical data"""
    try:
        response = requests.get('http://localhost:8098/api/recent-medical-data', timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                medical_data = data.get('data', {}).get('recent_medical_data', [])
                print(f"📊 Found {len(medical_data)} medical data records")
                
                # Look for our test devices
                accucheck_found = False
                jumper_found = False
                
                for record in medical_data:
                    device_id = record.get('device_id', '')
                    patient_name = record.get('patient_name', '')
                    source = record.get('source', '')
                    
                    if '60e85b7aab77' in str(record) or 'AccuCheck' in str(record):
                        accucheck_found = True
                        print(f"🩸 Found AccuCheck record: {device_id} - {patient_name} - {source}")
                    
                    if 'A0779E1C14D8' in str(record) or 'JUMPER SCALE' in str(record):
                        jumper_found = True
                        print(f"⚖️ Found JUMPER SCALE record: {device_id} - {patient_name} - {source}")
                
                if not accucheck_found:
                    print("❌ AccuCheck data not found")
                if not jumper_found:
                    print("❌ JUMPER SCALE data not found")
                
                return accucheck_found, jumper_found
            else:
                print(f"❌ API call failed: {data.get('error')}")
                return False, False
        else:
            print(f"❌ HTTP error: {response.status_code}")
            return False, False
    except Exception as e:
        print(f"❌ Error checking medical data: {e}")
        return False, False

def main():
    print("🧪 Testing Medical Data Display for Unknown Patients")
    print("=" * 60)
    
    # Test messages
    accucheck_message = {
        "from": "BLE",
        "to": "CLOUD",
        "time": 1841875953,
        "deviceCode": "80:65:99:A1:DC:77",
        "mac": "80:65:99:A1:DC:77",
        "type": "reportAttribute",
        "device": "SUGA AccuCheck",
        "data": {
            "attribute": "AccuChek_Instant",
            "mac": "80:65:99:A1:DC:77",
            "value": {
                "device_list": [{
                    "scan_time": 1841875953,
                    "ble_addr": "60e85b7aab77",
                    "scan_rssi": -66,
                    "blood_glucose": "111",
                    "marker": "After Meal"
                }]
            }
        }
    }
    
    jumper_message = {
        "from": "BLE",
        "to": "CLOUD",
        "time": 1773337306,
        "deviceCode": "DC:DA:0C:5A:80:33",
        "mac": "DC:DA:0C:5A:80:33",
        "type": "reportAttribute",
        "device": "JUMPER SCALE",
        "data": {
            "attribute": "BodyScale_JUMPER",
            "mac": "DC:DA:0C:5A:80:33",
            "value": {
                "device_list": [{
                    "scan_time": 1773337306,
                    "ble_addr": "A0779E1C14D8",
                    "weight": 79.30000305,
                    "resistance": 605.9000244
                }]
            }
        }
    }
    
    # Send test messages
    print("📤 Sending test messages...")
    send_mqtt_message("dusun_pub", accucheck_message)
    time.sleep(2)
    send_mqtt_message("dusun_pub", jumper_message)
    
    # Wait for processing
    print("⏳ Waiting for processing...")
    time.sleep(5)
    
    # Check results
    print("🔍 Checking medical data...")
    accucheck_found, jumper_found = check_medical_data()
    
    # Summary
    print("\n📋 Test Results:")
    print(f"🩸 AccuCheck Data Displayed: {'✅ YES' if accucheck_found else '❌ NO'}")
    print(f"⚖️ JUMPER SCALE Data Displayed: {'✅ YES' if jumper_found else '❌ NO'}")
    
    if accucheck_found and jumper_found:
        print("\n🎉 SUCCESS: Both medical data types are now being displayed!")
    else:
        print("\n⚠️ Some data is still not being displayed. Check the logs for more details.")

if __name__ == "__main__":
    main() 