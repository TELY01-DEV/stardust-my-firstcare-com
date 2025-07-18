#!/usr/bin/env python3
"""
Script to find AVA4 device ownership by BLE address
Run this inside the AVA4 listener container
"""

import os
import sys
from pymongo import MongoClient
from bson import ObjectId

# Add shared utilities to path
sys.path.append('/app/shared')

def find_ava4_device(ble_address):
    """Find AVA4 device and its patient owner"""
    try:
        # Use the same MongoDB configuration as the AVA4 listener
        mongodb_uri = os.getenv('MONGODB_URI')
        mongodb_database = os.getenv('MONGODB_DATABASE', 'AMY')
        
        if not mongodb_uri:
            print("❌ MONGODB_URI environment variable not set")
            return
        
        # Connect to MongoDB
        client = MongoClient(mongodb_uri)
        db = client[mongodb_database]
        
        print(f"🔍 Searching for AVA4 device with BLE address: {ble_address}")
        print("=" * 60)
        
        # Search in amy_devices collection
        print("1. Searching in amy_devices collection...")
        device = db.amy_devices.find_one({"mac_address": ble_address})
        
        if device:
            print(f"✅ Found device in amy_devices:")
            print(f"   Device ID: {device.get('_id')}")
            print(f"   MAC Address: {device.get('mac_address')}")
            print(f"   Device Type: {device.get('device_type')}")
            print(f"   Patient ID: {device.get('patient_id')}")
            
            # Get patient information
            if device.get('patient_id'):
                patient_id = device['patient_id']
                
                # Handle ObjectId conversion
                if isinstance(patient_id, dict) and '$oid' in patient_id:
                    patient_id = ObjectId(patient_id['$oid'])
                elif isinstance(patient_id, str):
                    patient_id = ObjectId(patient_id)
                
                patient = db.patients.find_one({"_id": patient_id})
                if patient:
                    patient_name = f"{patient.get('first_name', '')} {patient.get('last_name', '')}".strip()
                    print(f"   Patient Name: {patient_name}")
                    print(f"   Patient ID: {patient['_id']}")
                else:
                    print(f"   ❌ Patient not found for ID: {patient_id}")
            else:
                print(f"   ⚠️ No patient_id associated with this device")
        else:
            print(f"❌ Device not found in amy_devices collection")
        
        # Search in patients collection by various AVA4-related fields
        print("\n2. Searching in patients collection...")
        
        # Search by AVA4 MAC address
        patient = db.patients.find_one({"ava_mac_address": ble_address})
        if patient:
            patient_name = f"{patient.get('first_name', '')} {patient.get('last_name', '')}".strip()
            print(f"✅ Found patient by ava_mac_address:")
            print(f"   Patient Name: {patient_name}")
            print(f"   Patient ID: {patient['_id']}")
            print(f"   AVA4 MAC: {patient.get('ava_mac_address')}")
            return
        
        # Search by various device MAC addresses
        device_fields = [
            "blood_pressure_mac_address",
            "blood_glucose_mac_address", 
            "fingertip_pulse_oximeter_mac_address",
            "body_temperature_mac_address",
            "weight_scale_mac_address",
            "uric_mac_address",
            "cholesterol_mac_address"
        ]
        
        for field in device_fields:
            patient = db.patients.find_one({field: ble_address})
            if patient:
                patient_name = f"{patient.get('first_name', '')} {patient.get('last_name', '')}".strip()
                print(f"✅ Found patient by {field}:")
                print(f"   Patient Name: {patient_name}")
                print(f"   Patient ID: {patient['_id']}")
                print(f"   Device Field: {field}")
                print(f"   Device MAC: {patient.get(field)}")
                return
        
        print(f"❌ No patient found with this BLE address in any field")
        
        # Search for similar MAC addresses
        print("\n3. Searching for similar MAC addresses...")
        similar_devices = db.amy_devices.find({"mac_address": {"$regex": ble_address[-6:]}}).limit(5)
        similar_count = 0
        for device in similar_devices:
            similar_count += 1
            print(f"   Similar device: {device.get('mac_address')} (Type: {device.get('device_type')})")
        
        if similar_count == 0:
            print("   No similar devices found")
        
        client.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    ble_address = "ff23041920b4"
    find_ava4_device(ble_address) 