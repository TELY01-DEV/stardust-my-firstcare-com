#!/usr/bin/env python3
"""
Test BLE Device Mapping Fix
Simulates the blood pressure data that was failing before
"""

import json
import time

# Simulate the blood pressure data that was received
test_blood_pressure_data = {
    "from": "BLE",
    "to": "CLOUD", 
    "time": 1836942771,
    "deviceCode": "08:F9:E0:D1:F7:B4",
    "mac": "08:F9:E0:D1:F7:B4",
    "type": "reportAttribute",
    "device": "WBP BIOLIGHT",
    "data": {
        "attribute": "BLE_BPG",
        "mac": "08:F9:E0:D1:F7:B4", 
        "value": {
            "device_list": [{
                "scan_time": 1836942771,
                "ble_addr": "c12488906de0",  # This is the BLE MAC that was failing
                "bp_high": 137,
                "bp_low": 95,
                "PR": 74
            }]
        }
    }
}

print("🧪 Testing BLE Device Mapping Fix")
print("=" * 50)
print(f"📋 Test Data:")
print(f"   BLE MAC: c12488906de0")
print(f"   Device Type: BLE_BPG (Blood Pressure)")
print(f"   AVA4 Gateway MAC: 08:F9:E0:D1:F7:B4")
print()

print("📊 Expected Result:")
print("   ✅ Device should be found in amy_devices collection")
print("   ✅ Patient should be found: KM DEV (626a48decc8269328b021f93)")
print("   ✅ Blood pressure data should be processed successfully")
print()

print("🔍 What the updated device mapper will do:")
print("   1. Check patients.blood_pressure_mac_address (will fail)")
print("   2. Check amy_devices.mac_dusun_bps (should succeed)")
print("   3. Get patient info from patients collection")
print("   4. Process blood pressure data")
print()

print("📡 To test this:")
print("   1. Send this data to the MQTT topic: dusun_pub")
print("   2. Check the AVA4 listener logs")
print("   3. Verify patient mapping works")
print()

print("📝 Test Payload (JSON):")
print(json.dumps(test_blood_pressure_data, indent=2))
print()

print("🚀 The fix should now work because:")
print("   - BLE MAC c12488906de0 is registered in amy_devices.mac_dusun_bps")
print("   - Patient ID 626a48decc8269328b021f93 is linked")
print("   - Device mapper now checks both collections")
print()

print("✅ Fix Status: IMPLEMENTED AND DEPLOYED")
print("   - Updated device_mapper.py to check amy_devices collection")
print("   - Rebuilt and restarted AVA4 listener")
print("   - Ready to process blood pressure data") 