#!/usr/bin/env python3
"""
Test script to simulate AP55 batch vital signs data
"""

import json
import time
from datetime import datetime
import paho.mqtt.client as mqtt_client
import os

# MQTT Configuration
MQTT_BROKER = os.getenv('MQTT_BROKER_HOST', 'adam.amy.care')
MQTT_PORT = int(os.getenv('MQTT_BROKER_PORT', 1883))
MQTT_USERNAME = os.getenv('MQTT_USERNAME', 'webapi')
MQTT_PASSWORD = os.getenv('MQTT_PASSWORD', 'Sim!4433')

def create_ap55_batch_payload():
    """Create a sample AP55 batch vital signs payload"""
    current_time = int(time.time())
    
    # Create sample batch data with multiple readings
    batch_data = [
        {
            "timestamp": current_time - 3600,  # 1 hour ago
            "heartRate": 72,
            "bloodPressure": {"bp_sys": 120, "bp_dia": 80},
            "spO2": 98,
            "bodyTemperature": 36.6
        },
        {
            "timestamp": current_time - 1800,  # 30 minutes ago
            "heartRate": 75,
            "bloodPressure": {"bp_sys": 118, "bp_dia": 78},
            "spO2": 97,
            "bodyTemperature": 36.7
        },
        {
            "timestamp": current_time - 900,   # 15 minutes ago
            "heartRate": 78,
            "bloodPressure": {"bp_sys": 125, "bp_dia": 82},
            "spO2": 96,
            "bodyTemperature": 36.8
        },
        {
            "timestamp": current_time,         # Current time
            "heartRate": 80,
            "bloodPressure": {"bp_sys": 122, "bp_dia": 79},
            "spO2": 95,
            "bodyTemperature": 36.9
        }
    ]
    
    payload = {
        "IMEI": "861265061481799",  # Use existing IMEI
        "location": {
            "GPS": {"latitude": 13.7563, "longitude": 100.5018},
            "WiFi": [],
            "LBS": {"MCC": "520", "MNC": "3", "LAC": "1815", "CID": "79474300"}
        },
        "timeStamps": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "num_datas": len(batch_data),
        "data": batch_data
    }
    
    return payload

def on_connect(client, userdata, flags, rc):
    """Callback when connected to MQTT broker"""
    if rc == 0:
        print("✅ Connected to MQTT broker successfully")
    else:
        print(f"❌ Failed to connect to MQTT broker, return code: {rc}")

def on_publish(client, userdata, mid):
    """Callback when message is published"""
    print(f"✅ Message published successfully (Message ID: {mid})")

def main():
    """Main function to send AP55 batch data"""
    print("🚀 Starting AP55 batch data test...")
    
    # Create MQTT client
    client = mqtt_client.Client()
    client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    client.on_connect = on_connect
    client.on_publish = on_publish
    
    try:
        # Connect to MQTT broker
        print(f"🔌 Connecting to MQTT broker: {MQTT_BROKER}:{MQTT_PORT}")
        client.connect(MQTT_BROKER, MQTT_PORT)
        client.loop_start()
        
        # Wait for connection
        time.sleep(2)
        
        # Create AP55 payload
        payload = create_ap55_batch_payload()
        
        print("📦 AP55 Batch Data Payload:")
        print(json.dumps(payload, indent=2))
        
        # Publish to AP55 topic
        topic = "iMEDE_watch/AP55"
        message = json.dumps(payload)
        
        print(f"📤 Publishing to topic: {topic}")
        result = client.publish(topic, message, qos=1)
        
        # Wait for publish callback
        time.sleep(2)
        
        print("✅ AP55 batch data sent successfully!")
        print("📊 Check the web panel and logs to verify processing")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    
    finally:
        # Cleanup
        client.loop_stop()
        client.disconnect()
        print("🔌 Disconnected from MQTT broker")

if __name__ == "__main__":
    main() 