#!/usr/bin/env python3
"""
Fix Sub-Device Mapping Script v2

This script fixes the device-patient mapping by using the ble_addr field from AVA4 payloads
to map sub-devices to patients in the amy_devices collection.
"""

import pymongo
from bson import ObjectId
import ssl
from datetime import datetime
import json

# MongoDB Configuration
MONGODB_URI = "mongodb://opera_admin:Sim!443355@coruscant.my-firstcare.com:27023/admin?ssl=true&authSource=admin&tlsAllowInvalidCertificates=true&tlsAllowInvalidHostnames=true"
MONGODB_DATABASE = "AMY"

def connect_to_mongodb():
    """Connect to MongoDB with SSL"""
    try:
        # Connect to MongoDB with proper SSL certificates
        client = pymongo.MongoClient(
            MONGODB_URI,
            tls=True,
            tlsCAFile='ssl/ca-latest.pem',
            tlsCertificateKeyFile='ssl/client-combined-latest.pem',
            tlsAllowInvalidCertificates=True,
            tlsAllowInvalidHostnames=True
        )
        
        # Test connection
        client.admin.command('ping')
        print("✅ Successfully connected to MongoDB")
        return client
    except Exception as e:
        print(f"❌ Failed to connect to MongoDB: {e}")
        return None

def get_amy_devices_with_mac_addresses(client):
    """Get amy_devices with MAC addresses for sub-device mapping"""
    try:
        db = client[MONGODB_DATABASE]
        devices_collection = db.amy_devices
        
        # Get devices with MAC addresses
        devices = list(devices_collection.find({}))
        print(f"📊 Found {len(devices)} devices in amy_devices collection")
        
        # Extract MAC addresses from various fields
        mac_mappings = {}
        for device in devices:
            patient_id = str(device.get('patient_id', ''))
            
            # Check various MAC address fields
            mac_fields = [
                'mac_dusun_bps',      # Blood pressure MAC
                'mac_gluc',           # Glucose MAC
                'mac_oxymeter',       # Oximeter MAC
                'mac_body_temp',      # Body temperature MAC
                'mac_weight',         # Weight scale MAC
                'mac_chol',           # Cholesterol MAC
                'mac_salt_meter',     # Salt meter MAC
                'mac_ua',             # Uric acid MAC
                'mac_mgss_oxymeter',  # MGSS oximeter MAC
                'mac_watch',          # Watch MAC
                'mac_bps',            # BPS MAC
                'mac_gw'              # Gateway MAC
            ]
            
            for field in mac_fields:
                mac = device.get(field, '').strip()
                if mac and mac != '':
                    # Normalize MAC address (remove colons, make uppercase)
                    normalized_mac = mac.replace(':', '').upper()
                    mac_mappings[normalized_mac] = {
                        'patient_id': patient_id,
                        'device_id': device.get('_id'),
                        'mac_field': field,
                        'original_mac': mac
                    }
        
        print(f"📱 Found {len(mac_mappings)} MAC address mappings")
        return mac_mappings
        
    except Exception as e:
        print(f"❌ Error getting amy_devices: {e}")
        return {}

def analyze_ava4_device_list_events(client):
    """Analyze AVA4 events with device_list to extract sub-device MAC addresses"""
    try:
        db = client[MONGODB_DATABASE]
        event_logs = db.event_logs
        
        # Get AVA4 events with device_list
        device_list_events = list(event_logs.find({
            'source': 'AVA4',
            'details.payload.data.value.device_list': {'$exists': True}
        }).sort('timestamp', -1).limit(100))
        
        print(f"📊 Found {len(device_list_events)} AVA4 events with device_list")
        
        sub_device_mappings = {}
        
        for event in device_list_events:
            try:
                payload = event.get('details', {}).get('payload', {})
                data = payload.get('data', {})
                value = data.get('value', {})
                device_list = value.get('device_list', [])
                
                ava4_mac = payload.get('mac', 'unknown')
                device_type = data.get('device', 'unknown')
                
                for sub_device in device_list:
                    ble_addr = sub_device.get('ble_addr', '').upper()
                    if ble_addr:
                        sub_device_mappings[ble_addr] = {
                            'ava4_mac': ava4_mac,
                            'device_type': device_type,
                            'sub_device_mac': ble_addr,
                            'event_timestamp': event.get('timestamp'),
                            'event_id': str(event.get('_id')),
                            'sub_device_data': sub_device
                        }
                        
            except Exception as e:
                print(f"⚠️ Error parsing event {event.get('_id')}: {e}")
                continue
        
        print(f"🔍 Found {len(sub_device_mappings)} unique sub-device MAC addresses")
        return sub_device_mappings
        
    except Exception as e:
        print(f"❌ Error analyzing AVA4 device_list events: {e}")
        return {}

def create_sub_device_mapping(client, mac_mappings, sub_device_mappings):
    """Create mapping between sub-devices and patients"""
    try:
        db = client[MONGODB_DATABASE]
        
        print(f"\n🔗 Creating sub-device to patient mappings...")
        
        successful_mappings = 0
        unmapped_devices = []
        
        for ble_addr, sub_device_info in sub_device_mappings.items():
            if ble_addr in mac_mappings:
                # Found a match!
                patient_info = mac_mappings[ble_addr]
                ava4_mac = sub_device_info['ava4_mac']
                device_type = sub_device_info['device_type']
                sub_device_data = sub_device_info['sub_device_data']
                
                print(f"✅ Mapped: {ble_addr} ({device_type}) -> Patient {patient_info['patient_id']} via AVA4 {ava4_mac}")
                print(f"   Data: {sub_device_data}")
                successful_mappings += 1
                
                # Store this mapping for later use
                sub_device_info['patient_id'] = patient_info['patient_id']
                sub_device_info['mapped'] = True
                
            else:
                # No patient mapping found
                unmapped_devices.append({
                    'ble_addr': ble_addr,
                    'ava4_mac': sub_device_info['ava4_mac'],
                    'device_type': sub_device_info['device_type'],
                    'sub_device_data': sub_device_info['sub_device_data']
                })
                print(f"❌ No mapping: {ble_addr} ({sub_device_info['device_type']}) via AVA4 {sub_device_info['ava4_mac']}")
        
        print(f"\n📊 Mapping Summary:")
        print(f"   Successfully mapped: {successful_mappings}")
        print(f"   Unmapped devices: {len(unmapped_devices)}")
        
        if unmapped_devices:
            print(f"\n📋 Unmapped sub-devices:")
            for device in unmapped_devices[:10]:  # Show first 10
                print(f"   - {device['ble_addr']} ({device['device_type']}) via AVA4 {device['ava4_mac']}")
                print(f"     Data: {device['sub_device_data']}")
            if len(unmapped_devices) > 10:
                print(f"   ... and {len(unmapped_devices) - 10} more")
        
        return successful_mappings, unmapped_devices
        
    except Exception as e:
        print(f"❌ Error creating sub-device mapping: {e}")
        return 0, []

def update_event_logs_with_patient_info(client, mac_mappings, sub_device_mappings):
    """Update event logs with patient information based on sub-device mapping"""
    try:
        db = client[MONGODB_DATABASE]
        event_logs = db.event_logs
        
        print(f"\n🔄 Updating event logs with patient information...")
        
        updated_count = 0
        
        for ble_addr, sub_device_info in sub_device_mappings.items():
            if ble_addr in mac_mappings:
                patient_info = mac_mappings[ble_addr]
                patient_id = patient_info['patient_id']
                
                # Update events for this sub-device
                result = event_logs.update_many(
                    {
                        'source': 'AVA4',
                        'details.payload.data.value.device_list.ble_addr': ble_addr
                    },
                    {
                        '$set': {
                            'patient_id': patient_id,
                            'sub_device_mac': ble_addr,
                            'mapped_status': 'mapped'
                        }
                    }
                )
                
                if result.modified_count > 0:
                    print(f"✅ Updated {result.modified_count} events for {ble_addr} -> Patient {patient_id}")
                    updated_count += result.modified_count
        
        print(f"\n📊 Event Log Update Summary:")
        print(f"   Total events updated: {updated_count}")
        
        return updated_count
        
    except Exception as e:
        print(f"❌ Error updating event logs: {e}")
        return 0

def update_ava4_gateway_events(client):
    """Update AVA4 gateway events to show 'Not mapped to patient'"""
    try:
        db = client[MONGODB_DATABASE]
        event_logs = db.event_logs
        
        print(f"\n🔄 Updating AVA4 gateway events...")
        
        # Update AVA4 events that don't have device_list (gateway events)
        result = event_logs.update_many(
            {
                'source': 'AVA4',
                'details.payload.data.value.device_list': {'$exists': False},
                'patient_id': {'$exists': False}
            },
            {
                '$set': {
                    'patient_id': 'Not mapped to patient',
                    'mapped_status': 'gateway_device'
                }
            }
        )
        
        print(f"✅ Updated {result.modified_count} AVA4 gateway events")
        return result.modified_count
        
    except Exception as e:
        print(f"❌ Error updating AVA4 gateway events: {e}")
        return 0

def main():
    """Main function to fix sub-device mapping"""
    print("🔧 Sub-Device Mapping Database Fix v2")
    print("=" * 50)
    
    # Step 1: Connect to MongoDB
    print("\n1. Connecting to MongoDB...")
    client = connect_to_mongodb()
    if not client:
        return
    
    # Step 2: Get amy_devices with MAC addresses
    print("\n2. Getting amy_devices with MAC addresses...")
    mac_mappings = get_amy_devices_with_mac_addresses(client)
    
    if not mac_mappings:
        print("❌ No MAC address mappings found in amy_devices")
        return
    
    # Step 3: Analyze AVA4 device_list events
    print("\n3. Analyzing AVA4 device_list events...")
    sub_device_mappings = analyze_ava4_device_list_events(client)
    
    if not sub_device_mappings:
        print("❌ No sub-device mappings found in AVA4 events")
        return
    
    # Step 4: Create sub-device mapping
    print("\n4. Creating sub-device to patient mappings...")
    successful_mappings, unmapped_devices = create_sub_device_mapping(client, mac_mappings, sub_device_mappings)
    
    # Step 5: Update event logs
    print("\n5. Updating event logs with patient information...")
    updated_events = update_event_logs_with_patient_info(client, mac_mappings, sub_device_mappings)
    
    # Step 6: Update AVA4 gateway events
    print("\n6. Updating AVA4 gateway events...")
    updated_gateway_events = update_ava4_gateway_events(client)
    
    # Step 7: Summary
    print("\n" + "=" * 50)
    print("🎯 SUB-DEVICE MAPPING FIX SUMMARY")
    print("=" * 50)
    
    if successful_mappings > 0:
        print("✅ SUCCESS: Sub-device mapping has been implemented!")
        print(f"\n📊 Results:")
        print(f"   - Successfully mapped sub-devices: {successful_mappings}")
        print(f"   - Unmapped sub-devices: {len(unmapped_devices)}")
        print(f"   - Event logs updated: {updated_events}")
        print(f"   - Gateway events updated: {updated_gateway_events}")
        
        print("\n🚀 Next Steps:")
        print("1. Restart MQTT listeners: docker-compose restart ava4-listener kati-listener qube-listener")
        print("2. Check Event Log: http://localhost:8098/event-log")
        print("3. Verify AVA4 sub-devices now show patient names instead of N/A")
        print("4. Verify AVA4 gateway devices show 'Not mapped to patient'")
        print("5. Test Medical Monitor: http://localhost:8098/medical-monitor")
        
        print("\n💡 Expected Results:")
        print("- AVA4 sub-devices (blood pressure, weight, etc.) will show patient names")
        print("- AVA4 gateway devices will show 'Not mapped to patient'")
        print("- Medical alerts will be associated with specific patients")
        print("- Patient lookup events will show 'success' with patient IDs")
    else:
        print("⚠️ NO MAPPINGS FOUND")
        print("\n🔧 Troubleshooting:")
        print("1. Check if MAC addresses in amy_devices match ble_addr in AVA4 payloads")
        print("2. Verify AVA4 event logs contain proper device_list structure")
        print("3. Check MAC address format (with/without colons)")
    
    # Close connection
    client.close()
    print("\n✅ Database connection closed")

if __name__ == "__main__":
    main() 