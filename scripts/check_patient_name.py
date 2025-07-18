#!/usr/bin/env python3
"""
Script to check patient name for a specific patient ID
"""

import os
import sys
from pymongo import MongoClient
from bson import ObjectId

# Add shared utilities to path
sys.path.append('/app/shared')

def check_patient_name(patient_id):
    """Check patient name for a specific patient ID"""
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
        
        print(f"🔍 Checking patient name for ID: {patient_id}")
        print("=" * 60)
        
        # Convert patient_id to ObjectId
        if isinstance(patient_id, str):
            patient_id = ObjectId(patient_id)
        
        # Find patient
        patient = db.patients.find_one({"_id": patient_id})
        
        if patient:
            print(f"✅ Found patient:")
            print(f"   Patient ID: {patient['_id']}")
            print(f"   First Name: '{patient.get('first_name', 'N/A')}'")
            print(f"   Last Name: '{patient.get('last_name', 'N/A')}'")
            print(f"   Full Name: '{patient.get('first_name', '')} {patient.get('last_name', '')}'.strip()")
            
            # Check for other name fields
            print(f"   Nickname: '{patient.get('nickname', 'N/A')}'")
            print(f"   Display Name: '{patient.get('display_name', 'N/A')}'")
            
            # Check AVA4 related fields
            print(f"\nAVA4 Device Information:")
            print(f"   AVA4 MAC: {patient.get('ava_mac_address', 'N/A')}")
            print(f"   Blood Pressure MAC: {patient.get('blood_pressure_mac_address', 'N/A')}")
            print(f"   Blood Glucose MAC: {patient.get('blood_glucose_mac_address', 'N/A')}")
            print(f"   SpO2 MAC: {patient.get('fingertip_pulse_oximeter_mac_address', 'N/A')}")
            print(f"   Body Temp MAC: {patient.get('body_temperature_mac_address', 'N/A')}")
            print(f"   Weight Scale MAC: {patient.get('weight_scale_mac_address', 'N/A')}")
            print(f"   Uric Acid MAC: {patient.get('uric_mac_address', 'N/A')}")
            print(f"   Cholesterol MAC: {patient.get('cholesterol_mac_address', 'N/A')}")
            
            # Check if this is a test/development patient
            print(f"\nPatient Status:")
            print(f"   Registration Status: {patient.get('registration_status', 'N/A')}")
            print(f"   Patient Type: {patient.get('patient_type', 'N/A')}")
            print(f"   Is Test Patient: {patient.get('is_test_patient', False)}")
            print(f"   Notes: {patient.get('notes', 'N/A')}")
            
        else:
            print(f"❌ Patient not found for ID: {patient_id}")
        
        client.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    patient_id = "623c133cf9e69c3b67a9af64"  # TELY 01 DEV patient ID
    check_patient_name(patient_id) 