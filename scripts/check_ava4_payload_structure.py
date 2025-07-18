#!/usr/bin/env python3
"""
Check AVA4 Payload Structure Script

This script examines the actual AVA4 payload structure in event logs to understand
how sub-device data is stored.
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

def examine_ava4_events(client):
    """Examine AVA4 events to understand payload structure"""
    try:
        db = client[MONGODB_DATABASE]
        event_logs = db.event_logs
        
        # Get recent AVA4 events
        ava4_events = list(event_logs.find({
            'source': 'AVA4'
        }).sort('timestamp', -1).limit(10))
        
        print(f"📊 Found {len(ava4_events)} recent AVA4 events")
        
        for i, event in enumerate(ava4_events):
            print(f"\n📋 AVA4 Event {i+1}:")
            print(f"   Device ID: {event.get('device_id', 'N/A')}")
            print(f"   Event Type: {event.get('event_type', 'N/A')}")
            print(f"   Timestamp: {event.get('timestamp', 'N/A')}")
            
            # Check details structure
            details = event.get('details', {})
            print(f"   Details keys: {list(details.keys())}")
            
            # Check payload structure
            if 'payload' in details:
                payload = details['payload']
                print(f"   Payload keys: {list(payload.keys())}")
                
                # Pretty print the payload structure
                print(f"   Payload structure:")
                print(json.dumps(payload, indent=4, default=str)[:1000] + "..." if len(json.dumps(payload, default=str)) > 1000 else json.dumps(payload, indent=4, default=str))
            
            # Check message structure
            if 'message' in details:
                message = details['message']
                print(f"   Message: {message}")
        
        return ava4_events
        
    except Exception as e:
        print(f"❌ Error examining AVA4 events: {e}")
        return []

def check_ava4_device_list_structure(client):
    """Check for device_list structure in AVA4 events"""
    try:
        db = client[MONGODB_DATABASE]
        event_logs = db.event_logs
        
        # Search for events with device_list
        device_list_events = list(event_logs.find({
            'source': 'AVA4',
            '$or': [
                {'details.payload.data.value.device_list': {'$exists': True}},
                {'details.message': {'$regex': 'device_list'}},
                {'details.payload': {'$regex': 'device_list'}}
            ]
        }).limit(5))
        
        print(f"\n🔍 Found {len(device_list_events)} AVA4 events with device_list")
        
        for i, event in enumerate(device_list_events):
            print(f"\n📋 Device List Event {i+1}:")
            print(f"   Device ID: {event.get('device_id', 'N/A')}")
            print(f"   Event Type: {event.get('event_type', 'N/A')}")
            
            details = event.get('details', {})
            
            # Check different possible locations for device_list
            if 'payload' in details:
                payload = details['payload']
                if isinstance(payload, dict):
                    # Check nested structure
                    if 'data' in payload and 'value' in payload.get('data', {}):
                        value = payload['data']['value']
                        if 'device_list' in value:
                            device_list = value['device_list']
                            print(f"   ✅ Found device_list with {len(device_list)} devices")
                            for j, device in enumerate(device_list):
                                print(f"      Device {j+1}: {device}")
            
            # Check message field
            if 'message' in details:
                message = details['message']
                if 'device_list' in str(message):
                    print(f"   📝 Message contains device_list: {message}")
        
        return device_list_events
        
    except Exception as e:
        print(f"❌ Error checking device_list structure: {e}")
        return []

def check_ava4_ble_addresses(client):
    """Check for BLE addresses in AVA4 events"""
    try:
        db = client[MONGODB_DATABASE]
        event_logs = db.event_logs
        
        # Search for events with BLE addresses
        ble_events = list(event_logs.find({
            'source': 'AVA4',
            '$or': [
                {'details.payload': {'$regex': 'ble_addr'}},
                {'details.message': {'$regex': 'ble_addr'}},
                {'details.payload': {'$regex': 'd616f9641622'}}  # Example BLE address
            ]
        }).limit(5))
        
        print(f"\n🔍 Found {len(ble_events)} AVA4 events with BLE addresses")
        
        for i, event in enumerate(ble_events):
            print(f"\n📋 BLE Event {i+1}:")
            print(f"   Device ID: {event.get('device_id', 'N/A')}")
            
            details = event.get('details', {})
            
            # Search for BLE addresses in the entire event
            event_str = json.dumps(event, default=str)
            if 'ble_addr' in event_str:
                print(f"   ✅ Contains ble_addr field")
                
                # Extract BLE addresses
                import re
                ble_addresses = re.findall(r'"ble_addr":\s*"([^"]+)"', event_str)
                if ble_addresses:
                    print(f"   📱 BLE Addresses found: {ble_addresses}")
            
            # Check for the specific example BLE address
            if 'd616f9641622' in event_str:
                print(f"   🎯 Found example BLE address: d616f9641622")
        
        return ble_events
        
    except Exception as e:
        print(f"❌ Error checking BLE addresses: {e}")
        return []

def main():
    """Main function to examine AVA4 payload structure"""
    print("🔍 AVA4 Payload Structure Examination")
    print("=" * 50)
    
    # Step 1: Connect to MongoDB
    print("\n1. Connecting to MongoDB...")
    client = connect_to_mongodb()
    if not client:
        return
    
    # Step 2: Examine AVA4 events
    print("\n2. Examining AVA4 events...")
    ava4_events = examine_ava4_events(client)
    
    # Step 3: Check device_list structure
    print("\n3. Checking device_list structure...")
    device_list_events = check_ava4_device_list_structure(client)
    
    # Step 4: Check BLE addresses
    print("\n4. Checking BLE addresses...")
    ble_events = check_ava4_ble_addresses(client)
    
    # Step 5: Summary
    print("\n" + "=" * 50)
    print("🎯 AVA4 PAYLOAD STRUCTURE SUMMARY")
    print("=" * 50)
    
    if ava4_events:
        print("✅ AVA4 events found and examined")
        print("💡 Check the output above to understand the actual payload structure")
    else:
        print("❌ No AVA4 events found")
    
    # Close connection
    client.close()
    print("\n✅ Database connection closed")

if __name__ == "__main__":
    main() 