#!/usr/bin/env python3
"""
Check AMY Devices Collection Script

This script checks the amy_devices collection to understand how devices are stored
and how to fix the device-patient mapping.
"""

import pymongo
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

def check_amy_devices(client):
    """Check the amy_devices collection"""
    try:
        db = client[MONGODB_DATABASE]
        
        # Get all devices from amy_devices collection
        devices = list(db.amy_devices.find({}))
        print(f"\n📱 AMY Devices Collection:")
        print(f"   Total devices: {len(devices)}")
        
        if devices:
            print(f"\n📋 Sample device structure:")
            sample_device = devices[0]
            for key, value in sample_device.items():
                if key != '_id':
                    print(f"     {key}: {value}")
            
            print(f"\n🔍 Device types found:")
            device_types = {}
            for device in devices:
                device_type = device.get('device_type', 'unknown')
                device_types[device_type] = device_types.get(device_type, 0) + 1
            
            for device_type, count in device_types.items():
                print(f"   - {device_type}: {count} devices")
            
            # Check for devices with patient_id
            devices_with_patient = [d for d in devices if d.get('patient_id')]
            print(f"\n👥 Devices with patient_id: {len(devices_with_patient)}")
            
            # Check for devices with device_id
            devices_with_device_id = [d for d in devices if d.get('device_id')]
            print(f"📱 Devices with device_id: {len(devices_with_device_id)}")
            
            # Show sample devices with patient mapping
            if devices_with_patient:
                print(f"\n✅ Sample devices with patient mapping:")
                for device in devices_with_patient[:3]:
                    print(f"   - Device: {device.get('device_id', 'N/A')} -> Patient: {device.get('patient_id', 'N/A')} ({device.get('device_type', 'N/A')})")
            
            return devices
            
        else:
            print("   No devices found in collection")
            return []
            
    except Exception as e:
        print(f"❌ Error checking amy_devices collection: {e}")
        return []

def check_event_logs_for_devices(client):
    """Check event_logs for device information"""
    try:
        db = client[MONGODB_DATABASE]
        
        print(f"\n📊 Event Logs Analysis:")
        
        # Get recent events with device information
        recent_events = list(db.event_logs.find(
            {'device_id': {'$ne': 'unknown'}},
            {'device_id': 1, 'source': 1, 'patient_id': 1, 'timestamp': 1}
        ).sort('timestamp', -1).limit(10))
        
        print(f"   Recent events with device IDs: {len(recent_events)}")
        
        if recent_events:
            print(f"   Sample recent devices:")
            for event in recent_events:
                print(f"     - {event.get('device_id')} ({event.get('source')}) - Patient: {event.get('patient_id', 'N/A')}")
        
        # Count devices by source
        pipeline = [
            {'$match': {'device_id': {'$ne': 'unknown'}}},
            {'$group': {'_id': '$source', 'count': {'$sum': 1}, 'devices': {'$addToSet': '$device_id'}}}
        ]
        
        device_counts = list(db.event_logs.aggregate(pipeline))
        print(f"\n📈 Device counts by source:")
        for result in device_counts:
            source = result['_id']
            count = result['count']
            devices = result['devices']
            print(f"   - {source}: {count} events from {len(devices)} unique devices")
            print(f"     Devices: {', '.join(devices[:5])}{'...' if len(devices) > 5 else ''}")
            
    except Exception as e:
        print(f"❌ Error checking event_logs: {e}")

def main():
    """Main function to check amy_devices collection"""
    print("🔍 AMY Devices Collection Check")
    print("=" * 50)
    
    # Step 1: Connect to MongoDB
    print("\n1. Connecting to MongoDB...")
    client = connect_to_mongodb()
    if not client:
        return
    
    # Step 2: Check amy_devices collection
    print("\n2. Checking amy_devices collection...")
    devices = check_amy_devices(client)
    
    # Step 3: Check event_logs for device information
    print("\n3. Checking event_logs for device information...")
    check_event_logs_for_devices(client)
    
    # Step 4: Summary
    print("\n" + "=" * 50)
    print("🎯 AMY DEVICES ANALYSIS SUMMARY")
    print("=" * 50)
    
    if devices:
        print("✅ AMY devices collection exists and has data")
        print("💡 We can update the device-patient mapping in this collection")
    else:
        print("❌ No devices found in amy_devices collection")
    
    # Close connection
    client.close()
    print("\n✅ Database connection closed")

if __name__ == "__main__":
    main() 