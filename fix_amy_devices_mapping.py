#!/usr/bin/env python3
"""
Fix AMY Devices Mapping Script

This script fixes the device-patient mapping by updating the amy_devices collection
with proper device IDs extracted from event logs.
"""

import pymongo
from bson import ObjectId
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

def get_amy_devices(client):
    """Get current amy_devices from database"""
    try:
        db = client[MONGODB_DATABASE]
        devices_collection = db.amy_devices
        
        # Get all devices
        devices = list(devices_collection.find({}))
        print(f"📊 Found {len(devices)} devices in amy_devices collection")
        
        return devices
    except Exception as e:
        print(f"❌ Error getting amy_devices: {e}")
        return []

def update_amy_device_mapping(client, device_id, patient_id, device_type):
    """Update a single amy_device mapping"""
    try:
        db = client[MONGODB_DATABASE]
        devices_collection = db.amy_devices
        
        # Find device by patient_id (convert string to ObjectId)
        device = devices_collection.find_one({'patient_id': ObjectId(patient_id)})
        
        if device:
            # Update the device
            result = devices_collection.update_one(
                {'_id': device['_id']},
                {
                    '$set': {
                        'device_id': device_id,
                        'device_type': device_type.capitalize(),
                        'updated_at': datetime.utcnow(),
                        'mapping_status': 'updated'
                    }
                }
            )
            
            if result.modified_count > 0:
                print(f"✅ Updated device {device_id} -> Patient {patient_id} ({device_type})")
                return True
            else:
                print(f"⚠️ No changes made to device {device_id}")
                return False
        else:
            print(f"❌ Device with patient_id {patient_id} not found")
            return False
            
    except Exception as e:
        print(f"❌ Error updating device {device_id}: {e}")
        return False

def verify_amy_devices_mapping(client):
    """Verify that amy_devices mappings are working"""
    try:
        db = client[MONGODB_DATABASE]
        devices_collection = db.amy_devices
        
        # Check devices with proper device_id
        proper_devices = list(devices_collection.find({'device_id': {'$exists': True, '$ne': None}}))
        null_devices = list(devices_collection.find({'device_id': {'$exists': False}}))
        
        print(f"\n📊 AMY Devices Mapping Verification:")
        print(f"   Devices with proper device_id: {len(proper_devices)}")
        print(f"   Devices without device_id: {len(null_devices)}")
        
        if len(proper_devices) > 0:
            print(f"\n✅ Sample mapped devices:")
            for device in proper_devices[:3]:
                print(f"   - {device.get('device_id')} -> Patient {device.get('patient_id')} ({device.get('device_type')})")
        
        return len(null_devices) == 0
        
    except Exception as e:
        print(f"❌ Error verifying amy_devices mapping: {e}")
        return False

def test_patient_lookup_from_amy_devices(client):
    """Test patient lookup functionality using amy_devices"""
    try:
        db = client[MONGODB_DATABASE]
        devices_collection = db.amy_devices
        
        # Test with a known device
        test_device = devices_collection.find_one({'device_id': '861265061482599'})
        
        if test_device:
            print(f"\n🧪 AMY Devices Patient Lookup Test:")
            print(f"   Device ID: {test_device.get('device_id')}")
            print(f"   Patient ID: {test_device.get('patient_id')}")
            print(f"   Device Type: {test_device.get('device_type')}")
            print(f"   ✅ Patient lookup working correctly!")
            return True
        else:
            print(f"\n❌ AMY devices patient lookup test failed - device not found")
            return False
            
    except Exception as e:
        print(f"❌ Error testing amy_devices patient lookup: {e}")
        return False

def main():
    """Main function to fix amy_devices mappings"""
    print("🔧 AMY Devices Mapping Database Fix")
    print("=" * 50)
    
    # Step 1: Connect to MongoDB
    print("\n1. Connecting to MongoDB...")
    client = connect_to_mongodb()
    if not client:
        return
    
    # Step 2: Get current amy_devices
    print("\n2. Getting current amy_devices data...")
    current_devices = get_amy_devices(client)
    
    if not current_devices:
        print("❌ No amy_devices found. Cannot proceed.")
        return
    
    # Step 3: Apply device mappings
    print("\n3. Applying amy_devices mappings...")
    
    total_updates = 0
    successful_updates = 0
    
    for device_type, mappings in DEVICE_MAPPINGS.items():
        print(f"\n📱 Processing {device_type.upper()} devices...")
        
        for mapping in mappings:
            if update_amy_device_mapping(client, mapping['device_id'], mapping['patient_id'], device_type):
                successful_updates += 1
            total_updates += 1
    
    print(f"\n📊 Update Summary:")
    print(f"   Total mappings to apply: {total_updates}")
    print(f"   Successful updates: {successful_updates}")
    
    # Step 4: Verify mappings
    print("\n4. Verifying amy_devices mappings...")
    mapping_success = verify_amy_devices_mapping(client)
    
    # Step 5: Test patient lookup
    print("\n5. Testing amy_devices patient lookup functionality...")
    lookup_success = test_patient_lookup_from_amy_devices(client)
    
    # Step 6: Summary
    print("\n" + "=" * 50)
    print("🎯 AMY DEVICES MAPPING FIX SUMMARY")
    print("=" * 50)
    
    if mapping_success and lookup_success:
        print("✅ SUCCESS: AMY devices mapping has been fixed!")
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
        print("1. Check if all patient_ids in mappings exist in amy_devices")
        print("2. Verify device collection structure")
        print("3. Manually verify device mappings in database")
    
    # Close connection
    client.close()
    print("\n✅ Database connection closed")

if __name__ == "__main__":
    main() 