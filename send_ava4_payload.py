#!/usr/bin/env python3
"""
Send AVA4 Blood Pressure Payload to MQTT
"""

import paho.mqtt.publish as publish
import json
import time

# MQTT Configuration
MQTT_BROKER = "adam.amy.care"
MQTT_PORT = 1883
MQTT_USERNAME = "webapi"
MQTT_PASSWORD = "Sim!4433"
TOPIC = "dusun_sub"

# Payload from patient
payload = {
    "from": "BLE",
    "to": "CLOUD", 
    "time": 1770852839,
    "deviceCode": "08:B6:1F:88:12:98",
    "mac": "08:B6:1F:88:12:98",
    "type": "reportAttribute",
    "data": {
        "attribute": "BLE_BPG",
        "mac": "08:B6:1F:88:12:98",
        "value": {
            "device_list": [
                {
                    "scan_time": 1770852839,
                    "ble_addr": "c12488906de0",
                    "bp_high": 128,
                    "bp_low": 91,
                    "PR": 66
                }
            ]
        }
    }
}

def send_payload():
    """Send the AVA4 blood pressure payload to MQTT"""
    try:
        print(f"📤 Sending AVA4 blood pressure payload to topic: {TOPIC}")
        print(f"📊 Payload: {json.dumps(payload, indent=2)}")
        
        # Send the message
        publish.single(
            topic=TOPIC,
            payload=json.dumps(payload),
            hostname=MQTT_BROKER,
            port=MQTT_PORT,
            auth={'username': MQTT_USERNAME, 'password': MQTT_PASSWORD}
        )
        
        print("✅ Payload sent successfully!")
        print(f"⏰ Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}")
        
    except Exception as e:
        print(f"❌ Error sending payload: {e}")

if __name__ == "__main__":
    send_payload() 