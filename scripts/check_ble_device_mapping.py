#!/usr/bin/env python3
"""
Check BLE Device Mapping Script
Investigates the mapping of BLE device c12488906de0
"""

import os
import sys
import json
from datetime import datetime
from pymongo import MongoClient
from bson import ObjectId

def connect_mongodb():
    """Connect to MongoDB with SSL"""
    try:
        # MongoDB Configuration with SSL
        mongodb_uri = "mongodb://opera_admin:Sim!443355@coruscant.my-firstcare.com:27023/admin?ssl=true&authSource=admin&tlsAllowInvalidCertificates=true&tlsAllowInvalidHostnames=true"
        
        client = MongoClient(mongodb_uri)
        db = client['AMY']
        print("✅ Connected to MongoDB successfully")
        return client, db
    except Exception as e:
        print(f"❌ Failed to connect to MongoDB: {e}")
        return None, None

def check_ble_device_mapping(ble_mac: str):
    """Check BLE device mapping in various collections"""
    client, db = connect_mongodb()
    if client is None or db is None:
        return
    
    try:
        print(f"\n🔍 Investigating BLE device: {ble_mac}")
        print("=" * 60)
        
        # 1. Check amy_devices collection
        print("\n1️⃣ Checking amy_devices collection...")
        amy_device = db.amy_devices.find_one({'mac_address': ble_mac})
        if amy_device:
            print(f"✅ Found in amy_devices:")
            print(f"   Device Name: {amy_device.get('device_name', 'N/A')}")
            print(f"   Device Type: {amy_device.get('device_type', 'N/A')}")
            print(f"   Patient ID: {amy_device.get('patient_id', 'N/A')}")
            print(f"   Box ID: {amy_device.get('box_id', 'N/A')}")
            print(f"   Status: {amy_device.get('status', 'N/A')}")
            print(f"   Is Active: {amy_device.get('is_active', 'N/A')}")
            
            # If patient_id exists, get patient info
            if amy_device.get('patient_id'):
                patient = db.patients.find_one({'_id': amy_device['patient_id']})
                if patient:
                    print(f"   Patient Name: {patient.get('first_name', '')} {patient.get('last_name', '')}")
                else:
                    print(f"   ⚠️ Patient not found for ID: {amy_device['patient_id']}")
        else:
            print(f"❌ Not found in amy_devices collection")
        
        # 2. Check patients collection for blood pressure MAC
        print("\n2️⃣ Checking patients collection for blood_pressure_mac_address...")
        blood_pressure_patient = db.patients.find_one({'blood_pressure_mac_address': ble_mac})
        if blood_pressure_patient:
            print(f"✅ Found patient with blood_pressure_mac_address:")
            print(f"   Patient ID: {blood_pressure_patient.get('_id')}")
            print(f"   Patient Name: {blood_pressure_patient.get('first_name', '')} {blood_pressure_patient.get('last_name', '')}")
            print(f"   Blood Pressure MAC: {blood_pressure_patient.get('blood_pressure_mac_address')}")
        else:
            print(f"❌ No patient found with blood_pressure_mac_address: {ble_mac}")
        
        # 3. Check all patient device fields
        print("\n3️⃣ Checking all patient device MAC fields...")
        device_fields = [
            'blood_pressure_mac_address',
            'fingertip_pulse_oximeter_mac_address',
            'body_temperature_mac_address',
            'weight_scale_mac_address',
            'blood_glucose_mac_address',
            'uric_mac_address',
            'cholesterol_mac_address'
        ]
        
        found_in_patient = False
        for field in device_fields:
            patient = db.patients.find_one({field: ble_mac})
            if patient:
                print(f"✅ Found in patient field '{field}':")
                print(f"   Patient ID: {patient.get('_id')}")
                print(f"   Patient Name: {patient.get('first_name', '')} {patient.get('last_name', '')}")
                print(f"   Field Value: {patient.get(field)}")
                found_in_patient = True
        
        if not found_in_patient:
            print(f"❌ Not found in any patient device fields")
        
        # 4. Check amy_boxes collection for AVA4 gateway
        print("\n4️⃣ Checking amy_boxes collection...")
        amy_boxes = list(db.amy_boxes.find({'mac_address': {'$regex': '.*', '$options': 'i'}}))
        print(f"   Found {len(amy_boxes)} AVA4 boxes in total")
        
        # 5. Show recent blood pressure data
        print("\n5️⃣ Checking recent blood pressure data...")
        recent_bp_data = list(db.blood_pressure_histories.find().sort('created_at', -1).limit(5))
        if recent_bp_data:
            print(f"   Found {len(recent_bp_data)} recent blood pressure records")
            for i, record in enumerate(recent_bp_data, 1):
                print(f"   {i}. Patient: {record.get('patient_id')}, Created: {record.get('created_at')}")
        else:
            print(f"   No recent blood pressure data found")
        
        # 6. Check if BLE MAC exists in any collection
        print("\n6️⃣ Searching for BLE MAC in all collections...")
        collections = db.list_collection_names()
        found_in_collections = []
        
        for collection_name in collections:
            try:
                # Search in the collection for the BLE MAC
                count = db[collection_name].count_documents({
                    '$or': [
                        {'mac_address': ble_mac},
                        {'ble_mac': ble_mac},
                        {'device_mac': ble_mac},
                        {'mac': ble_mac}
                    ]
                })
                if count > 0:
                    found_in_collections.append((collection_name, count))
            except Exception as e:
                continue
        
        if found_in_collections:
            print(f"✅ Found BLE MAC in collections:")
            for collection_name, count in found_in_collections:
                print(f"   {collection_name}: {count} records")
        else:
            print(f"❌ BLE MAC not found in any collection")
        
        print("\n" + "=" * 60)
        print("🔍 Investigation Complete")
        
    except Exception as e:
        print(f"❌ Error during investigation: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    ble_mac = "c12488906de0"
    check_ble_device_mapping(ble_mac) 