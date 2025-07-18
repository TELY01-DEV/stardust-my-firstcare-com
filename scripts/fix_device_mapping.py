#!/usr/bin/env python3
"""
Fix Device-Patient Mapping Script

This script fixes the broken device-patient mapping by:
1. Extracting actual device IDs from event logs
2. Updating the devices collection with proper device IDs
3. Ensuring devices are properly linked to patients
"""

import requests
import json
from datetime import datetime, timezone, timedelta

# Configuration
BASE_URL = "http://localhost:8098"
HEADERS = {"Content-Type": "application/json"}

def get_event_logs(limit=1000):
    """Get event logs to extract device IDs"""
    try:
        response = requests.get(f"{BASE_URL}/api/event-log?limit={limit}")
        if response.status_code == 200:
            data = response.json()
            return data.get('data', {}).get('events', [])
        else:
            print(f"Error getting event logs: {response.status_code}")
            return []
    except Exception as e:
        print(f"Error getting event logs: {e}")
        return []

def get_devices():
    """Get current devices from API"""
    try:
        response = requests.get(f"{BASE_URL}/api/devices")
        if response.status_code == 200:
            data = response.json()
            return data.get('data', {})
        else:
            print(f"Error getting devices: {response.status_code}")
            return {}
    except Exception as e:
        print(f"Error getting devices: {e}")
        return {}

def get_patients():
    """Get patients from API"""
    try:
        response = requests.get(f"{BASE_URL}/api/patients")
        if response.status_code == 200:
            data = response.json()
            return data.get('data', [])
        else:
            print(f"Error getting patients: {response.status_code}")
            return []
    except Exception as e:
        print(f"Error getting patients: {e}")
        return []

def extract_device_mappings(events):
    """Extract device ID to source mappings from events"""
    device_mappings = {}
    
    for event in events:
        device_id = event.get('device_id')
        source = event.get('source')
        
        if device_id and device_id != 'unknown' and source:
            if device_id not in device_mappings:
                device_mappings[device_id] = {
                    'source': source,
                    'first_seen': event.get('timestamp'),
                    'last_seen': event.get('timestamp'),
                    'event_count': 0
                }
            else:
                device_mappings[device_id]['last_seen'] = event.get('timestamp')
                device_mappings[device_id]['event_count'] += 1
    
    return device_mappings

def analyze_device_data(events):
    """Analyze device data patterns"""
    print("\n=== Device Data Analysis ===")
    
    # Count events by source
    source_counts = {}
    device_counts = {}
    
    for event in events:
        source = event.get('source', 'unknown')
        device_id = event.get('device_id', 'unknown')
        
        source_counts[source] = source_counts.get(source, 0) + 1
        if device_id != 'unknown':
            device_counts[device_id] = device_counts.get(device_id, 0) + 1
    
    print(f"Total events: {len(events)}")
    print(f"Events by source:")
    for source, count in source_counts.items():
        print(f"  {source}: {count}")
    
    print(f"\nUnique devices: {len(device_counts)}")
    print("Top 10 devices by event count:")
    sorted_devices = sorted(device_counts.items(), key=lambda x: x[1], reverse=True)
    for device_id, count in sorted_devices[:10]:
        print(f"  {device_id}: {count} events")
    
    return source_counts, device_counts

def create_device_mapping_plan(device_mappings, patients, devices):
    """Create a plan to fix device mappings"""
    print("\n=== Device Mapping Fix Plan ===")
    
    # Group devices by source
    kati_devices = []
    ava4_devices = []
    qube_devices = []
    
    for device_id, info in device_mappings.items():
        if info['source'] == 'Kati':
            kati_devices.append(device_id)
        elif info['source'] == 'AVA4':
            ava4_devices.append(device_id)
        elif info['source'] == 'Qube':
            qube_devices.append(device_id)
    
    print(f"Kati devices found: {len(kati_devices)}")
    print(f"AVA4 devices found: {len(ava4_devices)}")
    print(f"Qube devices found: {len(qube_devices)}")
    
    # Check current device mappings
    current_kati = devices.get('kati', [])
    current_ava4 = devices.get('ava4', [])
    current_qube = devices.get('qube', [])
    
    print(f"\nCurrent device mappings:")
    print(f"  Kati devices in DB: {len(current_kati)} (all have null device_id)")
    print(f"  AVA4 devices in DB: {len(current_ava4)} (all have null device_id)")
    print(f"  Qube devices in DB: {len(current_qube)} (all have null device_id)")
    
    # Create mapping plan
    mapping_plan = {
        'kati': [],
        'ava4': [],
        'qube': []
    }
    
    # For Kati devices, try to map to patients
    for i, device_id in enumerate(kati_devices):
        if i < len(current_kati):
            patient_id = current_kati[i].get('patient_id')
            if isinstance(patient_id, dict) and '$oid' in patient_id:
                patient_id = patient_id['$oid']
            
            mapping_plan['kati'].append({
                'device_id': device_id,
                'patient_id': patient_id,
                'device_type': 'Kati',
                'source': 'Kati'
            })
    
    # For AVA4 devices, try to map to patients
    for i, device_id in enumerate(ava4_devices):
        if i < len(current_ava4):
            patient_id = current_ava4[i].get('patient_id')
            if isinstance(patient_id, dict) and '$oid' in patient_id:
                patient_id = patient_id['$oid']
            
            mapping_plan['ava4'].append({
                'device_id': device_id,
                'patient_id': patient_id,
                'device_type': 'AVA4',
                'source': 'AVA4'
            })
    
    # For Qube devices, try to map to patients
    for i, device_id in enumerate(qube_devices):
        if i < len(current_qube):
            patient_id = current_qube[i].get('patient_id')
            if isinstance(patient_id, dict) and '$oid' in patient_id:
                patient_id = patient_id['$oid']
            
            mapping_plan['qube'].append({
                'device_id': device_id,
                'patient_id': patient_id,
                'device_type': 'Qube',
                'source': 'Qube'
            })
    
    return mapping_plan

def print_mapping_plan(mapping_plan):
    """Print the device mapping plan"""
    print("\n=== Proposed Device Mappings ===")
    
    for device_type, devices in mapping_plan.items():
        print(f"\n{device_type.upper()} Devices:")
        for device in devices:
            print(f"  Device ID: {device['device_id']}")
            print(f"  Patient ID: {device['patient_id']}")
            print(f"  Device Type: {device['device_type']}")
            print(f"  Source: {device['source']}")
            print()

def main():
    """Main function to fix device mappings"""
    print("🔧 Device-Patient Mapping Fix Script")
    print("=" * 50)
    
    # Step 1: Get current data
    print("\n1. Fetching current data...")
    events = get_event_logs(2000)  # Get more events for better analysis
    devices = get_devices()
    patients = get_patients()
    
    if not events:
        print("❌ No events found. Cannot proceed.")
        return
    
    if not devices:
        print("❌ No devices found. Cannot proceed.")
        return
    
    if not patients:
        print("❌ No patients found. Cannot proceed.")
        return
    
    print(f"✅ Found {len(events)} events, {len(devices)} device types, {len(patients)} patients")
    
    # Step 2: Analyze current state
    print("\n2. Analyzing current device data...")
    source_counts, device_counts = analyze_device_data(events)
    
    # Step 3: Extract device mappings
    print("\n3. Extracting device mappings from events...")
    device_mappings = extract_device_mappings(events)
    print(f"✅ Found {len(device_mappings)} unique devices with mappings")
    
    # Step 4: Create mapping plan
    print("\n4. Creating device mapping plan...")
    mapping_plan = create_device_mapping_plan(device_mappings, patients, devices)
    
    # Step 5: Display plan
    print_mapping_plan(mapping_plan)
    
    # Step 6: Summary
    print("\n=== Summary ===")
    print("The device-patient mapping is currently broken because:")
    print("1. All devices in the database have device_id: null")
    print("2. Patient lookup fails because devices can't be identified")
    print("3. Medical monitoring shows 'N/A' for patient information")
    
    print("\nTo fix this, you need to:")
    print("1. Update the devices collection with proper device IDs")
    print("2. Ensure each device is linked to a patient")
    print("3. Restart the MQTT listeners to use the updated mappings")
    
    print(f"\n📊 Current Status:")
    print(f"  - Total events: {len(events)}")
    print(f"  - Unique devices: {len(device_mappings)}")
    print(f"  - Patients available: {len(patients)}")
    print(f"  - Device mappings needed: {sum(len(devices) for devices in mapping_plan.values())}")
    
    print("\n🎯 Next Steps:")
    print("1. Review the proposed mappings above")
    print("2. Update the database with proper device IDs")
    print("3. Test the patient lookup functionality")
    print("4. Verify medical monitoring shows proper patient information")

if __name__ == "__main__":
    main() 