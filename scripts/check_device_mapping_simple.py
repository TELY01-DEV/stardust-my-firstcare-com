#!/usr/bin/env python3
"""
Simple Device Mapping Check Script
"""

import asyncio
import json
from app.services.mongo import mongodb_service
from app.models.devices import AmyDevice
from app.models.patient import Patient

async def check_device_mapping():
    """Check device mapping for BLE MAC c12488906de0"""
    try:
        # Connect to MongoDB
        await mongodb_service.connect()
        print("✅ Connected to MongoDB")
        
        # Check amy_devices collection
        print("\n🔍 Checking amy_devices collection...")
        device = AmyDevice.objects(mac_address='c12488906de0').first()
        
        if device:
            print(f"✅ Found device in amy_devices:")
            device_data = device.to_mongo().to_dict()
            print(f"   Device Name: {device_data.get('device_name', 'N/A')}")
            print(f"   Device Type: {device_data.get('device_type', 'N/A')}")
            print(f"   Patient ID: {device_data.get('patient_id', 'N/A')}")
            print(f"   Box ID: {device_data.get('box_id', 'N/A')}")
            print(f"   Status: {device_data.get('status', 'N/A')}")
            print(f"   Is Active: {device_data.get('is_active', 'N/A')}")
            
            # If patient_id exists, get patient info
            if device_data.get('patient_id'):
                patient = Patient.objects(id=device_data['patient_id']).first()
                if patient:
                    patient_data = patient.to_mongo().to_dict()
                    print(f"   Patient Name: {patient_data.get('first_name', '')} {patient_data.get('last_name', '')}")
                else:
                    print(f"   ⚠️ Patient not found for ID: {device_data['patient_id']}")
        else:
            print(f"❌ Device not found in amy_devices collection")
        
        # Check patients collection for blood pressure MAC
        print("\n🔍 Checking patients collection for blood_pressure_mac_address...")
        patient = Patient.objects(blood_pressure_mac_address='c12488906de0').first()
        
        if patient:
            patient_data = patient.to_mongo().to_dict()
            print(f"✅ Found patient with blood_pressure_mac_address:")
            print(f"   Patient ID: {patient_data.get('_id')}")
            print(f"   Patient Name: {patient_data.get('first_name', '')} {patient_data.get('last_name', '')}")
            print(f"   Blood Pressure MAC: {patient_data.get('blood_pressure_mac_address')}")
        else:
            print(f"❌ No patient found with blood_pressure_mac_address: c12488906de0")
        
        # Check all patient device fields
        print("\n🔍 Checking all patient device MAC fields...")
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
            patient = Patient.objects(**{field: 'c12488906de0'}).first()
            if patient:
                patient_data = patient.to_mongo().to_dict()
                print(f"✅ Found in patient field '{field}':")
                print(f"   Patient ID: {patient_data.get('_id')}")
                print(f"   Patient Name: {patient_data.get('first_name', '')} {patient_data.get('last_name', '')}")
                print(f"   Field Value: {patient_data.get(field)}")
                found_in_patient = True
        
        if not found_in_patient:
            print(f"❌ Not found in any patient device fields")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await mongodb_service.disconnect()

if __name__ == "__main__":
    asyncio.run(check_device_mapping()) 