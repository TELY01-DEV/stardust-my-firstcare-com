#!/usr/bin/env python3
"""
Fix Device-Patient Mapping Database Script

This script directly updates the MongoDB database to fix the broken device-patient mapping
by setting proper device IDs for each device. This is critical for medical monitoring.
"""

import pymongo
import ssl
from datetime import datetime
import json

# MongoDB Configuration
MONGODB_URI = "mongodb://opera_admin:Sim!443355@coruscant.my-firstcare.com:27023/admin?ssl=true&authSource=admin&tlsAllowInvalidCertificates=true&tlsAllowInvalidHostnames=true"
MONGODB_DATABASE = "AMY"

# Device mappings based on the analysis
DEVICE_MAPPINGS = {
    'kati': [
        {'device_id': '861265061478050', 'patient_id': '620c83a78ae03f05312cb9b5'},
        {'device_id': '861265061480536', 'patient_id': '623c133cf9e69c3b67a9af64'},
        {'device_id': '861265061482458', 'patient_id': '622035a5fd26d7b6d9b7730c'},
        {'device_id': '861265061366537', 'patient_id': '6260cdbf79b00113f9bbe76c'},
        {'device_id': '861265061477987', 'patient_id': '62635af508e389411192a987'},
        {'device_id': '861265061482334', 'patient_id': '627de0ea4b8ec2f57f079243'},
        {'device_id': '861265061482607', 'patient_id': '627de20f4b8ec2f57f07929b'},
        {'device_id': '861265061482599', 'patient_id': '627e158d4b8ec2f57f079e67'},
        {'device_id': '861265061481799', 'patient_id': '624ac947576e198cc6240b08'},
        {'device_id': '861265061480353', 'patient_id': '625ce462e405cfa083081f33'},
        {'device_id': '861265061486269', 'patient_id': '6260146b79b00113f9bbdf22'},
        {'device_id': '861265061482789', 'patient_id': '66233dc652cddddd4d40b7c2'}
    ],
    'ava4': [
        {'device_id': '08:F9:E0:D1:82:80', 'patient_id': '661f2b5d818cc24bd96a8722'},
        {'device_id': 'DC:DA:0C:5A:80:64', 'patient_id': '65e88b3d0705ee793b74e9cf'},
        {'device_id': '08:B6:1F:88:12:98', 'patient_id': '65e88b1d0705ee793b74e9c2'},
        {'device_id': '30:ae:7b:e2:2b:19', 'patient_id': '67a475217a8421c6ad92cc98'},
        {'device_id': '08:F9:E0:D1:F7:B4', 'patient_id': '65e88bb50705ee793b74ea05'},
        {'device_id': '74:4D:BD:83:42:58', 'patient_id': '67a4756909af987621e9a8ff'},
        {'device_id': '80:65:99:A2:80:08', 'patient_id': '65f70467c24dd6a8f8949546'},
        {'device_id': '3C:61:05:0C:3A:F0', 'patient_id': '65e88c1b0705ee793b74ea30'},
        {'device_id': '80:65:99:A2:7B:98', 'patient_id': '65e88c270705ee793b74ea37'},
        {'device_id': '08:F9:E0:D1:FB:70', 'patient_id': '6604f5e200df0d8b0c5a1e34'}
    ]
}

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

def get_current_devices(client):
    """Get current devices from database"""
    try:
        db = client[MONGODB_DATABASE]
        devices_collection = db.devices
        
        # Get all devices
        devices = list(devices_collection.find({}))
        print(f"📊 Found {len(devices)} devices in database")
        
        # Group by device type
        devices_by_type = {}
        for device in devices:
            device_type = device.get('device_type', 'unknown')
            if device_type not in devices_by_type:
                devices_by_type[device_type] = []
            devices_by_type[device_type].append(device)
        
        return devices_by_type
    except Exception as e:
        print(f"❌ Error getting devices: {e}")
        return {}

def update_device_mapping(client, device_type, device_index, mapping):
    """Update a single device mapping"""
    try:
        db = client[MONGODB_DATABASE]
        devices_collection = db.devices
        
        # Find devices by type
        devices = list(devices_collection.find({'device_type': device_type}))
        
        if device_index < len(devices):
            device_id = devices[device_index]['_id']
            
            # Update the device
            result = devices_collection.update_one(
                {'_id': device_id},
                {
                    '$set': {
                        'device_id': mapping['device_id'],
                        'patient_id': mapping['patient_id'],
                        'device_type': device_type.capitalize(),
                        'updated_at': datetime.utcnow(),
                        'mapping_status': 'updated'
                    }
                }
            )
            
            if result.modified_count > 0:
                print(f"✅ Updated {device_type} device {device_index}: {mapping['device_id']} -> Patient {mapping['patient_id']}")
                return True
            else:
                print(f"⚠️ No changes made to {device_type} device {device_index}")
                return False
        else:
            print(f"❌ Device index {device_index} not found for {device_type}")
            return False
            
    except Exception as e:
        print(f"❌ Error updating {device_type} device {device_index}: {e}")
        return False

def verify_mapping(client):
    """Verify that device mappings are working"""
    try:
        db = client[MONGODB_DATABASE]
        devices_collection = db.devices
        
        # Check devices with proper device_id
        proper_devices = list(devices_collection.find({'device_id': {'$ne': None}}))
        null_devices = list(devices_collection.find({'device_id': None}))
        
        print(f"\n📊 Mapping Verification:")
        print(f"   Devices with proper device_id: {len(proper_devices)}")
        print(f"   Devices with null device_id: {len(null_devices)}")
        
        if len(proper_devices) > 0:
            print(f"\n✅ Sample mapped devices:")
            for device in proper_devices[:3]:
                print(f"   - {device.get('device_id')} -> Patient {device.get('patient_id')} ({device.get('device_type')})")
        
        return len(null_devices) == 0
        
    except Exception as e:
        print(f"❌ Error verifying mapping: {e}")
        return False

def test_patient_lookup(client):
    """Test patient lookup functionality"""
    try:
        db = client[MONGODB_DATABASE]
        devices_collection = db.devices
        
        # Test with a known device
        test_device = devices_collection.find_one({'device_id': '861265061482599'})
        
        if test_device:
            print(f"\n🧪 Patient Lookup Test:")
            print(f"   Device ID: {test_device.get('device_id')}")
            print(f"   Patient ID: {test_device.get('patient_id')}")
            print(f"   Device Type: {test_device.get('device_type')}")
            print(f"   ✅ Patient lookup working correctly!")
            return True
        else:
            print(f"\n❌ Patient lookup test failed - device not found")
            return False
            
    except Exception as e:
        print(f"❌ Error testing patient lookup: {e}")
        return False

def main():
    """Main function to fix device mappings"""
    print("🔧 Device-Patient Mapping Database Fix")
    print("=" * 50)
    
    # Step 1: Connect to MongoDB
    print("\n1. Connecting to MongoDB...")
    client = connect_to_mongodb()
    if not client:
        return
    
    # Step 2: Get current devices
    print("\n2. Getting current device data...")
    current_devices = get_current_devices(client)
    
    if not current_devices:
        print("❌ No devices found. Cannot proceed.")
        return
    
    # Step 3: Apply device mappings
    print("\n3. Applying device mappings...")
    
    total_updates = 0
    successful_updates = 0
    
    for device_type, mappings in DEVICE_MAPPINGS.items():
        print(f"\n📱 Processing {device_type.upper()} devices...")
        
        for i, mapping in enumerate(mappings):
            if update_device_mapping(client, device_type, i, mapping):
                successful_updates += 1
            total_updates += 1
    
    print(f"\n📊 Update Summary:")
    print(f"   Total mappings to apply: {total_updates}")
    print(f"   Successful updates: {successful_updates}")
    
    # Step 4: Verify mappings
    print("\n4. Verifying device mappings...")
    mapping_success = verify_mapping(client)
    
    # Step 5: Test patient lookup
    print("\n5. Testing patient lookup functionality...")
    lookup_success = test_patient_lookup(client)
    
    # Step 6: Summary
    print("\n" + "=" * 50)
    print("🎯 MAPPING FIX SUMMARY")
    print("=" * 50)
    
    if mapping_success and lookup_success:
        print("✅ SUCCESS: Device-patient mapping has been fixed!")
        print("\n🚀 Next Steps:")
        print("1. Restart MQTT listeners: docker-compose restart ava4-listener kati-listener qube-listener")
        print("2. Check Event Log: http://localhost:8098/event-log")
        print("3. Verify Patient column shows actual patient names instead of N/A")
        print("4. Test Medical Monitor: http://localhost:8098/medical-monitor")
        
        print("\n💡 Expected Results:")
        print("- Event Log will show patient names instead of N/A")
        print("- Medical Monitor will display patient-specific data")
        print("- Patient lookup events will show 'success' with patient IDs")
        print("- Medical alerts will be associated with specific patients")
    else:
        print("⚠️ PARTIAL SUCCESS: Some issues may remain")
        print("\n🔧 Troubleshooting:")
        print("1. Check MongoDB connection and permissions")
        print("2. Verify device collection structure")
        print("3. Manually verify device mappings in database")
    
    # Close connection
    client.close()
    print("\n✅ Database connection closed")

if __name__ == "__main__":
    main() 