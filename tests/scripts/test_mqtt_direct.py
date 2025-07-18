#!/usr/bin/env python3
"""
Test script to send messages directly to MQTT broker for testing AVA4 listener
"""

import paho.mqtt.client as mqtt_client
import json
import time
from datetime import datetime

# MQTT Configuration
MQTT_BROKER = 'adam.amy.care'
MQTT_PORT = 1883
MQTT_USERNAME = 'webapi'
MQTT_PASSWORD = 'Sim!4433'
MQTT_TOPIC = 'dusun_pub'

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ Connected to MQTT broker")
    else:
        print(f"❌ Failed to connect to MQTT broker, return code: {rc}")

def on_publish(client, userdata, mid):
    print(f"✅ Message published with ID: {mid}")

def send_mqtt_message(client, topic, payload):
    """Send message to MQTT broker"""
    try:
        message = json.dumps(payload)
        result = client.publish(topic, message)
        if result.rc == mqtt_client.MQTT_ERR_SUCCESS:
            print(f"✅ Message sent to {topic}")
            return True
        else:
            print(f"❌ Failed to send message: {result.rc}")
            return False
    except Exception as e:
        print(f"❌ Error sending message: {e}")
        return False

def main():
    print("🧪 Testing AVA4 Listener with Direct MQTT Messages")
    print("=" * 60)
    
    # Create MQTT client
    client = mqtt_client.Client()
    client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    client.on_connect = on_connect
    client.on_publish = on_publish
    
    try:
        # Connect to MQTT broker
        print("🔌 Connecting to MQTT broker...")
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_start()
        
        # Wait for connection
        time.sleep(2)
        
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
        send_mqtt_message(client, MQTT_TOPIC, accucheck_message)
        time.sleep(2)
        send_mqtt_message(client, MQTT_TOPIC, jumper_message)
        
        # Wait for processing
        print("⏳ Waiting for processing...")
        time.sleep(10)
        
        print("✅ Test messages sent successfully!")
        print("📋 Check the AVA4 listener logs to see if the messages were processed")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        client.loop_stop()
        client.disconnect()

if __name__ == "__main__":
    main() 