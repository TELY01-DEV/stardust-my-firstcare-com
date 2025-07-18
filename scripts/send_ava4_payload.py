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
TOPIC = "dusun_pub"

# SUGA AccuCheck blood glucose payload
payload = {
    "from": "BLE",
    "to": "CLOUD", 
    "time": 1770852839,
    "deviceCode": "80:65:99:A1:DC:77",
    "mac": "80:65:99:A1:DC:77",
    "type": "reportAttribute",
    "device": "SUGA AccuCheck",
    "data": {
        "attribute": "AccuChek_Instant",
        "mac": "80:65:99:A1:DC:77",
        "value": {
            "device_list": [
                {
                    "scan_time": 1770852839,
                    "ble_addr": "60e85b7aab77",
                    "scan_rssi": -66,
                    "blood_glucose": "111",
                    "marker": "After Meal"
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