#!/usr/bin/env python3
import requests
import json

# Get recent medical data
response = requests.get('http://localhost:8098/api/recent-medical-data')
data = response.json()

# Find AVA4 records
ava4_records = [r for r in data['data']['recent_medical_data'] if r['source'] == 'AVA4']

if ava4_records:
    print("📋 AVA4 Raw Data Structure:")
    print("=" * 50)
    
    for i, record in enumerate(ava4_records[:2]):
        print(f"\n📋 Record {i+1}:")
        print(f"Device ID: {record.get('device_id')}")
        print(f"Patient: {record.get('patient_name')}")
        
        raw_data = record.get('raw_data', {})
        print(f"Raw Data Keys: {list(raw_data.keys())}")
        
        # Check for MAC address in various locations
        mac_locations = [
            'mac', 'ava4_mac', 'device_mac', 'ble_mac', 'ble_addr',
            'device_id', 'sub_device_mac'
        ]
        
        print("🔍 Looking for MAC address:")
        for key in mac_locations:
            if key in raw_data:
                print(f"   ✅ {key}: {raw_data[key]}")
            else:
                print(f"   ❌ {key}: Not found")
        
        # Show full raw_data for first record
        if i == 0:
            print(f"\n📄 Full Raw Data:")
            print(json.dumps(raw_data, indent=2))
else:
    print("❌ No AVA4 records found") 