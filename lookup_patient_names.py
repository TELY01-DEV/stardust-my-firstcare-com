#!/usr/bin/env python3
"""
Patient Name Lookup Script
Lookup patient names by ObjectId from the database
"""

import os
from pymongo import MongoClient
from bson import ObjectId

# MongoDB Configuration
MONGODB_URI = "mongodb://opera_admin:Sim!443355@coruscant.my-firstcare.com:27023/admin?ssl=true&authSource=admin&tlsAllowInvalidCertificates=true&tlsAllowInvalidHostnames=true&tlsCAFile=./ssl/ca-latest.pem&tlsCertificateKeyFile=./ssl/client-combined-latest.pem"
DATABASE_NAME = "AMY"

def connect_to_database():
    """Connect to MongoDB database"""
    try:
        client = MongoClient(MONGODB_URI)
        db = client[DATABASE_NAME]
        # Test connection
        db.command('ping')
        print("✅ Connected to MongoDB successfully")
        return db
    except Exception as e:
        print(f"❌ Failed to connect to MongoDB: {e}")
        return None

def lookup_patient(patient_id):
    """Lookup patient by ObjectId and print full document"""
    try:
        # Convert string to ObjectId
        obj_id = ObjectId(patient_id)
        
        # Query patients collection
        patient = db.patients.find_one({"_id": obj_id})
        
        if patient:
            return patient
        else:
            return None
    except Exception as e:
        print(f"❌ Error looking up patient {patient_id}: {e}")
        return None

def main():
    """Main function to lookup patient names"""
    global db
    db = connect_to_database()
    if db is None:
        return
    
    # Patient IDs to lookup
    patient_ids = [
        "6605084300df0d8b0c5a33ad",
        "660508c400df0d8b0c5a343b"
    ]
    
    print("🔍 Looking up patient information...")
    print("=" * 60)
    
    for patient_id in patient_ids:
        print(f"\n📋 Patient ID: {patient_id}")
        print("-" * 40)
        
        patient_info = lookup_patient(patient_id)
        
        if patient_info:
            print(f"✅ Found Patient Document:")
            for k, v in patient_info.items():
                print(f"   {k}: {v}")
        else:
            print(f"❌ Patient not found in database")
    
    print("\n" + "=" * 60)
    print("🎯 Patient lookup completed!")

if __name__ == "__main__":
    main() 