#!/usr/bin/env python3
"""
Comprehensive AVA4 Device Test Script
Tests all AVA4 medical device types with correct payload formats
"""

import paho.mqtt.publish as publish
import json
import time

def send_ava4_payload(topic, payload, device_name):
    """Send AVA4 payload and log result"""
    try:
        print(f"📊 Sending {device_name} data...")
        publish.single(
            topic=topic,
            payload=json.dumps(payload),
            hostname='adam.amy.care',
            port=1883,
            auth={'username': 'webapi', 'password': 'Sim!4433'}
        )
        print(f"✅ {device_name} data sent successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to send {device_name} data: {e}")
        return False

# 1. Blood Pressure - BP_BIOLIGTH
blood_pressure_payload = {
    "from": "BLE",
    "to": "CLOUD", 
    "time": 1836942771,
    "deviceCode": "08:F9:E0:D1:F7:B4",
    "mac": "08:F9:E0:D1:F7:B4",
    "type": "reportAttribute",
    "device": "WBP BIOLIGHT",
    "data": {
        "attribute": "BP_BIOLIGTH",
        "mac": "08:F9:E0:D1:F7:B4",
        "value": {
            "device_list": [
                {
                    "scan_time": 1836942771,
                    "ble_addr": "d616f9641622",
                    "bp_high": 137,
                    "bp_low": 95,
                    "PR": 74
                }
            ]
        }
    }
}

# 2. Oximeter - Oximeter JUMPER
oximeter_payload = {
    "from": "BLE",
    "to": "CLOUD",
    "time": 1836946958,
    "deviceCode": "DC:DA:0C:5A:80:44", 
    "mac": "DC:DA:0C:5A:80:44",
    "type": "reportAttribute",
    "device": "Oximeter Jumper",
    "data": {
        "attribute": "Oximeter JUMPER",
        "mac": "DC:DA:0C:5A:80:44",
        "value": {
            "device_list": [
                {
                    "scan_time": 1836946958,
                    "ble_addr": "ff23041920b4",
                    "pulse": 72,
                    "spo2": 96,
                    "pi": 43
                }
            ]
        }
    }
}

# 3. Glucometer - Contour Elite
glucometer_contour_payload = {
    "from": "BLE",
    "to": "CLOUD",
    "time": 1841875953,
    "deviceCode": "DC:DA:0C:5A:80:88",
    "mac": "DC:DA:0C:5A:80:88",
    "type": "reportAttribute",
    "device": "SUGA Contour",
    "data": {
        "attribute": "Contour_Elite",
        "mac": "DC:DA:0C:5A:80:88",
        "value": {
            "device_list": [{
                "scan_time": 1841875953,
                "ble_addr": "806fb0750c88",
                "scan_rssi": -66,
                "blood_glucose": "108",
                "marker": "After Meal"
            }]
        }
    }
}

# 4. Glucometer - AccuChek Instant
glucometer_accuchek_payload = {
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

# 5. Thermometer - IR_TEMO_JUMPER
thermometer_payload = {
    "from": "BLE",
    "to": "CLOUD",
    "time": 1841932446,
    "deviceCode": "DC:DA:0C:5A:80:64",
    "mac": "DC:DA:0C:5A:80:64",
    "type": "reportAttribute",
    "device": "TEMO Jumper",
    "data": {
        "attribute": "IR_TEMO_JUMPER",
        "mac": "DC:DA:0C:5A:80:64",
        "value": {
            "device_list": [{
                "scan_time": 1841932446,
                "ble_addr": "ff2301283119",
                "temp": 36.43000031,
                "mode": "Head"
            }]
        }
    }
}

# 6. Weight Scale - BodyScale_JUMPER
weight_scale_payload = {
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

# 7. Uric Acid - MGSS_REF_UA
uric_acid_payload = {
    "from": "BLE",
    "to": "CLOUD",
    "time": 1841875953,
    "deviceCode": "34:20:03:9a:13:22",
    "mac": "34:20:03:9a:13:22",
    "type": "reportAttribute",
    "device": "Uric REF_UA",
    "data": {
        "attribute": "MGSS_REF_UA",
        "mac": "34:20:03:9a:13:22",
        "value": {
            "device_list": [{
                "scan_time": 1841875953,
                "ble_addr": "60e85b7aab77",
                "scan_rssi": -66,
                "uric_acid": "517.5"
            }]
        }
    }
}

# 8. Cholesterol - MGSS_REF_CHOL
cholesterol_payload = {
    "from": "BLE",
    "to": "CLOUD",
    "time": 1841875953,
    "deviceCode": "34:20:03:9a:13:11",
    "mac": "34:20:03:9a:13:11",
    "type": "reportAttribute",
    "device": "Cholesterol REF_CHOL",
    "data": {
        "attribute": "MGSS_REF_CHOL",
        "mac": "34:20:03:9a:13:11",
        "value": {
            "device_list": [{
                "scan_time": 1841875953,
                "ble_addr": "0035FF226907",
                "scan_rssi": -66,
                "cholesterol": "4.3"
            }]
        }
    }
}

def main():
    """Run all AVA4 device tests"""
    print("🚀 Starting Comprehensive AVA4 Device Test")
    print("=" * 50)
    
    # Test all device types
    tests = [
        (blood_pressure_payload, "Blood Pressure (BP_BIOLIGTH)"),
        (oximeter_payload, "Oximeter (Oximeter JUMPER)"),
        (glucometer_contour_payload, "Glucometer (Contour Elite)"),
        (glucometer_accuchek_payload, "Glucometer (AccuChek Instant)"),
        (thermometer_payload, "Thermometer (IR_TEMO_JUMPER)"),
        (weight_scale_payload, "Weight Scale (BodyScale_JUMPER)"),
        (uric_acid_payload, "Uric Acid (MGSS_REF_UA)"),
        (cholesterol_payload, "Cholesterol (MGSS_REF_CHOL)")
    ]
    
    success_count = 0
    total_tests = len(tests)
    
    for payload, device_name in tests:
        if send_ava4_payload('dusun_pub', payload, device_name):
            success_count += 1
        time.sleep(1)  # Small delay between sends
    
    print("=" * 50)
    print(f"📊 Test Results: {success_count}/{total_tests} devices tested successfully")
    print("🎯 Check AVA4 listener logs for processing details")
    print("💡 Note: Patient mapping warnings are expected for test devices")

if __name__ == "__main__":
    main() 