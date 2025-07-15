#!/usr/bin/env python3
"""
Script to register the BodyScale device A0779E1C14D7 to patient กิจกมน ไมตรี
"""

import os
import sys
from pymongo import MongoClient
from bson import ObjectId

# MongoDB connection
MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
DB_NAME = 'AMY'

def connect_to_mongodb():
    """Connect to MongoDB"""
    try:
        client = MongoClient(MONGODB_URI)
        db = client[DB_NAME]
        return client, db
    except Exception as e:
        print(f"Error connecting to MongoDB: {e}")
        return None, None

def find_patient_by_name(db, first_name, last_name):
    """Find patient by name"""
    try:
        patient = db.patients.find_one({
            'first_name': first_name,
            'last_name': last_name
        })
        return patient
    except Exception as e:
        print(f"Error finding patient: {e}")
        return None

def register_device_to_patient(db, patient_id, device_mac, device_type):
    """Register device to patient"""
    try:
        # First, check if the device_type field exists and what type it is
        patient = db.patients.find_one({'_id': ObjectId(patient_id)})
        if not patient:
            print(f"❌ Patient not found with ID {patient_id}")
            return False
            
        current_value = patient.get(device_type)
        print(f"Current {device_type} field: {current_value} (type: {type(current_value)})")
        
        if isinstance(current_value, dict):
            # Field is already an object, add mac to it
            update_data = {f'{device_type}.mac': device_mac}
        elif current_value is not None:
            # Field exists but is not an object (e.g., numeric value)
            # We need to replace it with an object
            update_data = {
                device_type: {
                    'value': current_value,
                    'mac': device_mac
                }
            }
        else:
            # Field doesn't exist, create new object
            update_data = {
                device_type: {
                    'mac': device_mac
                }
            }
        
        # Update patient's device field
        result = db.patients.update_one(
            {'_id': ObjectId(patient_id)},
            {'$set': update_data}
        )
        
        if result.modified_count > 0:
            print(f"✅ Successfully registered {device_type} device {device_mac} to patient {patient_id}")
            return True
        else:
            print(f"❌ Failed to register device - no changes made")
            return False
            
    except Exception as e:
        print(f"Error registering device: {e}")
        return False

def main():
    print("🔧 Registering BodyScale device A0779E1C14D7 to patient กิจกมน ไมตรี")
    
    # Connect to MongoDB
    client, db = connect_to_mongodb()
    if client is None or db is None:
        return
    
    try:
        # Find patient กิจกมน ไมตรี
        patient = find_patient_by_name(db, "กิจกมน", "ไมตรี")
        
        if not patient:
            print("❌ Patient กิจกมน ไมตรี not found")
            print("🔍 Searching for patients with similar names...")
            
            # Search for patients with "กิจกมน" in first_name
            patients = list(db.patients.find({'first_name': {'$regex': 'กิจกมน', '$options': 'i'}}))
            
            if patients:
                print(f"Found {len(patients)} patients with similar names:")
                for p in patients:
                    print(f"  - ID: {p['_id']}, Name: {p.get('first_name', '')} {p.get('last_name', '')}")
                
                # Use the first one found
                patient = patients[0]
                print(f"Using patient: {patient.get('first_name', '')} {patient.get('last_name', '')}")
            else:
                print("❌ No patients found with name containing 'กิจกมน'")
                return
        else:
            print(f"✅ Found patient: {patient.get('first_name', '')} {patient.get('last_name', '')} (ID: {patient['_id']})")
        
        # Register the BodyScale device
        device_mac = "A0779E1C14D7"
        device_type = "weight"
        patient_id = str(patient['_id'])
        
        success = register_device_to_patient(db, patient_id, device_mac, device_type)
        
        if success:
            print(f"🎉 Device registration completed!")
            print(f"   Device: {device_mac}")
            print(f"   Type: {device_type}")
            print(f"   Patient: {patient.get('first_name', '')} {patient.get('last_name', '')}")
        else:
            print("❌ Device registration failed")
            
    except Exception as e:
        print(f"Error in main: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    main() 