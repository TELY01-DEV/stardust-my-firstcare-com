#!/usr/bin/env python3
"""
Update existing AVA4 medical data records with correct patient names and device names
"""

import pymongo
from bson import ObjectId
import ssl
import os

# MongoDB Configuration
MONGODB_URI = os.getenv('MONGODB_URI', "mongodb://opera_admin:Sim!443355@coruscant.my-firstcare.com:27023/admin?ssl=true&authSource=admin&tlsAllowInvalidCertificates=true&tlsAllowInvalidHostnames=true")
MONGODB_DATABASE = os.getenv('MONGODB_DATABASE', "AMY")

def connect_to_mongodb():
    """Connect to MongoDB with SSL"""
    try:
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

def update_ava4_medical_data():
    """Update existing AVA4 medical data records"""
    client = connect_to_mongodb()
    if not client:
        return
    
    try:
        db = client[MONGODB_DATABASE]
        medical_data_collection = db.medical_data
        ava4_status_collection = db.ava4_status
        patients_collection = db.patients
        
        # Get all AVA4 medical data records
        ava4_records = list(medical_data_collection.find({'source': 'AVA4'}))
        print(f"📊 Found {len(ava4_records)} AVA4 medical data records")
        
        updated_count = 0
        
        for record in ava4_records:
            patient_id = record.get('patient_id')
            device_mac = record.get('raw_data', {}).get('device_mac')
            
            if not patient_id or not device_mac:
                continue
            
            # Get patient name
            try:
                if isinstance(patient_id, str):
                    patient_obj_id = ObjectId(patient_id)
                else:
                    patient_obj_id = patient_id
                
                patient = patients_collection.find_one({'_id': patient_obj_id})
                if patient:
                    patient_name = f"{patient.get('first_name', '')} {patient.get('last_name', '')}".strip()
                else:
                    patient_name = "Unknown Patient"
            except Exception as e:
                print(f"⚠️ Error getting patient name for {patient_id}: {e}")
                patient_name = "Unknown Patient"
            
            # Get AVA4 device name from status collection
            ava4_status = ava4_status_collection.find_one({'ava4_mac': device_mac})
            device_name = None
            if ava4_status:
                device_name = ava4_status.get('ava4_name')
            
            # Update the record
            update_data = {
                'patient_name': patient_name
            }
            if device_name:
                update_data['device_name'] = device_name
            
            result = medical_data_collection.update_one(
                {'_id': record['_id']},
                {'$set': update_data}
            )
            
            if result.modified_count > 0:
                updated_count += 1
                print(f"✅ Updated record {record['_id']}: patient_name='{patient_name}', device_name='{device_name}'")
        
        print(f"\n📊 Update Summary:")
        print(f"   Total AVA4 records: {len(ava4_records)}")
        print(f"   Updated records: {updated_count}")
        
    except Exception as e:
        print(f"❌ Error updating AVA4 medical data: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    update_ava4_medical_data() 