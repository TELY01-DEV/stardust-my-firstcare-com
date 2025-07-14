#!/usr/bin/env python3
"""
Test MQTT Data Processing
=========================
Script to test the MQTT listeners and data processing functionality
by sending sample MQTT messages to the brokers.
"""

import asyncio
import json
import time
from datetime import datetime
import paho.mqtt.client as mqtt
import random

# MQTT Broker Configuration
MQTT_BROKER = "adam.amy.care"
MQTT_PORT = 1883
MQTT_USERNAME = "webapi"
MQTT_PASSWORD = "Sim!4433"

# Test data for different device types
KATI_TEST_DATA = {
    "location": {
        "topic": "iMEDE_watch/location",
        "payload": {
            "IMEI": "861265061478050",
            "timestamp": datetime.utcnow().isoformat(),
            "latitude": 13.7563,
            "longitude": 100.5018,
            "altitude": 15.5,
            "accuracy": 5.0,
            "speed": 0.0,
            "heading": 180.0,
            "satellites": 8,
            "battery": 85
        }
    },
    "heartbeat": {
        "topic": "iMEDE_watch/hb",
        "payload": {
            "IMEI": "861265061478050",
            "timestamp": datetime.utcnow().isoformat(),
            "heart_rate": random.randint(60, 100),
            "blood_pressure_systolic": random.randint(110, 140),
            "blood_pressure_diastolic": random.randint(70, 90),
            "temperature": round(random.uniform(36.5, 37.5), 1),
            "spo2": random.randint(95, 100),
            "battery": 85,
            "signal_strength": random.randint(1, 5)
        }
    },
    "vitals": {
        "topic": "iMEDE_watch/vitals",
        "payload": {
            "IMEI": "861265061478050",
            "timestamp": datetime.utcnow().isoformat(),
            "heart_rate": random.randint(60, 100),
            "blood_pressure_systolic": random.randint(110, 140),
            "blood_pressure_diastolic": random.randint(70, 90),
            "temperature": round(random.uniform(36.5, 37.5), 1),
            "spo2": random.randint(95, 100),
            "respiratory_rate": random.randint(12, 20),
            "battery": 85
        }
    }
}

AVA4_TEST_DATA = {
    "heartbeat": {
        "topic": "ESP32_BLE_GW_TX",
        "payload": {
            "device_type": "AVA4",
            "mac_address": "08:B6:1F:88:12:98",
            "timestamp": datetime.utcnow().isoformat(),
            "message_type": "HB_Msg",
            "heart_rate": random.randint(60, 100),
            "blood_pressure_systolic": random.randint(110, 140),
            "blood_pressure_diastolic": random.randint(70, 90),
            "temperature": round(random.uniform(36.5, 37.5), 1),
            "spo2": random.randint(95, 100),
            "battery": random.randint(80, 100),
            "signal_strength": random.randint(1, 5)
        }
    },
    "vitals": {
        "topic": "ESP32_BLE_GW_TX",
        "payload": {
            "device_type": "AVA4",
            "mac_address": "08:B6:1F:88:12:98",
            "timestamp": datetime.utcnow().isoformat(),
            "message_type": "Vitals_Msg",
            "heart_rate": random.randint(60, 100),
            "blood_pressure_systolic": random.randint(110, 140),
            "blood_pressure_diastolic": random.randint(70, 90),
            "temperature": round(random.uniform(36.5, 37.5), 1),
            "spo2": random.randint(95, 100),
            "respiratory_rate": random.randint(12, 20),
            "battery": random.randint(80, 100)
        }
    }
}

QUBE_TEST_DATA = {
    "vitals": {
        "topic": "qube/vitals",
        "payload": {
            "device_id": "QUBE_001",
            "timestamp": datetime.utcnow().isoformat(),
            "heart_rate": random.randint(60, 100),
            "blood_pressure_systolic": random.randint(110, 140),
            "blood_pressure_diastolic": random.randint(70, 90),
            "temperature": round(random.uniform(36.5, 37.5), 1),
            "spo2": random.randint(95, 100),
            "respiratory_rate": random.randint(12, 20),
            "battery": random.randint(80, 100),
            "device_status": "active"
        }
    }
}

def on_connect(client, userdata, flags, rc):
    """Callback when connected to MQTT broker"""
    if rc == 0:
        print(f"✅ Connected to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}")
    else:
        print(f"❌ Failed to connect to MQTT broker, return code: {rc}")

def on_publish(client, userdata, mid):
    """Callback when message is published"""
    print(f"📤 Message published with ID: {mid}")

def send_mqtt_message(client, topic, payload):
    """Send a single MQTT message"""
    try:
        message = json.dumps(payload, indent=2)
        result = client.publish(topic, message, qos=1)
        print(f"📡 Sending to topic '{topic}':")
        print(f"   Payload: {message[:200]}...")
        return result
    except Exception as e:
        print(f"❌ Error sending message: {e}")
        return None

def test_kati_messages(client):
    """Test Kati Watch MQTT messages"""
    print("\n🔴 Testing Kati Watch Messages:")
    print("=" * 50)
    
    for msg_type, data in KATI_TEST_DATA.items():
        print(f"\n📱 Sending Kati {msg_type} message...")
        send_mqtt_message(client, data["topic"], data["payload"])
        time.sleep(1)

def test_ava4_messages(client):
    """Test AVA4 MQTT messages"""
    print("\n🔵 Testing AVA4 Messages:")
    print("=" * 50)
    
    for msg_type, data in AVA4_TEST_DATA.items():
        print(f"\n📱 Sending AVA4 {msg_type} message...")
        send_mqtt_message(client, data["topic"], data["payload"])
        time.sleep(1)

def test_qube_messages(client):
    """Test Qube-Vital MQTT messages"""
    print("\n🟢 Testing Qube-Vital Messages:")
    print("=" * 50)
    
    for msg_type, data in QUBE_TEST_DATA.items():
        print(f"\n📱 Sending Qube {msg_type} message...")
        send_mqtt_message(client, data["topic"], data["payload"])
        time.sleep(1)

def main():
    """Main test function"""
    print("🚀 Starting MQTT Data Processing Test")
    print("=" * 60)
    
    # Create MQTT client
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_publish = on_publish
    
    try:
        # Connect to MQTT broker
        print(f"🔌 Connecting to MQTT broker: {MQTT_BROKER}:{MQTT_PORT}")
        client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_start()
        
        # Wait for connection
        time.sleep(2)
        
        # Test different device types
        test_kati_messages(client)
        time.sleep(2)
        
        test_ava4_messages(client)
        time.sleep(2)
        
        test_qube_messages(client)
        time.sleep(2)
        
        print("\n✅ MQTT Data Processing Test Completed!")
        print("📊 Check the transaction logs to see if data was processed:")
        print("   curl -H 'Authorization: Bearer <token>' http://localhost:5054/api/transactions/logs")
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
    finally:
        # Cleanup
        client.loop_stop()
        client.disconnect()
        print("\n🔌 Disconnected from MQTT broker")

if __name__ == "__main__":
    main() 