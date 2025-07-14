#!/usr/bin/env python3
"""
Check patient database directly to understand pagination issue
Run this on the production server to check the database state
"""

import os
import sys
import asyncio
from pymongo import MongoClient
from bson import ObjectId

# MongoDB connection (adjust as needed for production)
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "stardust")

async def check_patient_database():
    print("🔍 Checking Patient Database Directly")
    print("=" * 50)
    
    try:
        # Connect to MongoDB
        client = MongoClient(MONGODB_URI)
        db = client[DB_NAME]
        collection = db.patients
        
        print(f"📊 Connected to database: {DB_NAME}")
        print(f"📊 Collection: patients")
        
        # Check total count
        total_patients = collection.count_documents({"is_deleted": {"$ne": True}})
        print(f"📊 Total active patients: {total_patients}")
        
        # Check if there are any patients at all
        if total_patients == 0:
            print("⚠️  No patients found in database!")
            return
        
        # Test pagination queries directly
        print("\n📋 Testing Database Pagination Queries")
        print("-" * 40)
        
        test_cases = [
            {"limit": 5, "skip": 0, "description": "First 5 patients"},
            {"limit": 5, "skip": 5, "description": "Next 5 patients (skip=5)"},
            {"limit": 5, "skip": 10, "description": "Next 5 patients (skip=10)"},
        ]
        
        all_patient_ids = []
        
        for i, test_case in enumerate(test_cases, 1):
            limit = test_case["limit"]
            skip = test_case["skip"]
            description = test_case["description"]
            
            print(f"\n📋 Test {i}: {description}")
            print(f"   Query: limit={limit}, skip={skip}")
            
            # Execute the same query as the API
            filter_query = {"is_deleted": {"$ne": True}}
            cursor = collection.find(filter_query).skip(skip).limit(limit)
            patients = list(cursor)
            
            print(f"   📄 Patients returned: {len(patients)}")
            
            # Extract patient IDs
            patient_ids = []
            for patient in patients:
                patient_id = str(patient.get("_id"))
                patient_ids.append(patient_id)
                all_patient_ids.append(patient_id)
                
                # Show patient info
                name = f"{patient.get('first_name', '')} {patient.get('last_name', '')}".strip()
                print(f"      - {name} (ID: {patient_id})")
            
            # Check for duplicates in this page
            unique_ids = set(patient_ids)
            if len(unique_ids) != len(patient_ids):
                print(f"   ⚠️  WARNING: Duplicate patients on this page!")
                print(f"      Unique IDs: {len(unique_ids)}, Total patients: {len(patient_ids)}")
        
        # Analyze overall results
        print("\n" + "=" * 50)
        print("📈 DATABASE ANALYSIS")
        print("=" * 50)
        
        total_returned = len(all_patient_ids)
        unique_returned = len(set(all_patient_ids))
        
        print(f"📊 Total patient records returned: {total_returned}")
        print(f"📊 Unique patient IDs returned: {unique_returned}")
        
        if total_returned > unique_returned:
            print(f"🚨 CRITICAL ISSUE: {total_returned - unique_returned} duplicate patient records detected!")
            print(f"   This confirms the database query is returning the same data.")
        else:
            print(f"✅ No duplicate patients detected in database queries.")
        
        # Check if we're getting the same patients repeatedly
        if len(all_patient_ids) > 0:
            first_page_ids = set(all_patient_ids[:5])  # First 5 patients
            
            print(f"\n🔍 Checking for repeated first page data:")
            repeated_count = 0
            for i in range(5, len(all_patient_ids), 5):  # Check every 5th patient
                if i < len(all_patient_ids):
                    patient_id = all_patient_ids[i]
                    if patient_id in first_page_ids:
                        repeated_count += 1
            
            if repeated_count > 0:
                print(f"   ⚠️  Found {repeated_count} patients from first page repeated in later pages")
            else:
                print(f"   ✅ No obvious repetition of first page data detected")
        
        # Check database indexes
        print(f"\n🔍 Checking Database Indexes")
        print("-" * 30)
        
        indexes = collection.list_indexes()
        index_list = list(indexes)
        
        print(f"📊 Total indexes: {len(index_list)}")
        for idx, index in enumerate(index_list, 1):
            print(f"   {idx}. {index['name']}: {index['key']}")
        
        # Check if there's a proper index for pagination
        has_id_index = any('_id' in str(index.get('key', {})) for index in index_list)
        if has_id_index:
            print(f"   ✅ _id index found (good for pagination)")
        else:
            print(f"   ⚠️  No _id index found (may cause pagination issues)")
        
        client.close()
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        print(f"   Make sure MongoDB is running and accessible")

if __name__ == "__main__":
    asyncio.run(check_patient_database()) 