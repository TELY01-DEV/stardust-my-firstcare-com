#!/usr/bin/env python3
"""
Test script to check patient list pagination issue
Run this on the production server to diagnose the pagination problem
"""

import requests
import json
from datetime import datetime

def test_patient_pagination():
    base_url = "http://stardust.my-firstcare.com/api/v1/admin/patients"
    
    print("🔍 Testing Patient List Pagination")
    print("=" * 50)
    
    # Test different pagination scenarios
    test_cases = [
        {"limit": 5, "skip": 0, "description": "First 5 patients"},
        {"limit": 5, "skip": 5, "description": "Next 5 patients (skip=5)"},
        {"limit": 5, "skip": 10, "description": "Next 5 patients (skip=10)"},
        {"limit": 10, "skip": 0, "description": "First 10 patients"},
        {"limit": 10, "skip": 10, "description": "Next 10 patients (skip=10)"},
    ]
    
    all_patients = []
    patient_ids_seen = set()
    
    for i, test_case in enumerate(test_cases, 1):
        limit = test_case["limit"]
        skip = test_case["skip"]
        description = test_case["description"]
        
        print(f"\n📋 Test {i}: {description}")
        print(f"   URL: {base_url}?limit={limit}&skip={skip}")
        
        try:
            response = requests.get(f"{base_url}?limit={limit}&skip={skip}", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("success"):
                    patients = data.get("data", {}).get("patients", [])
                    total = data.get("data", {}).get("total", 0)
                    returned_limit = data.get("data", {}).get("limit", 0)
                    returned_skip = data.get("data", {}).get("skip", 0)
                    
                    print(f"   ✅ Status: 200 OK")
                    print(f"   📊 Total patients in DB: {total}")
                    print(f"   📄 Patients returned: {len(patients)}")
                    print(f"   🔢 Requested limit: {limit}, Returned limit: {returned_limit}")
                    print(f"   🔢 Requested skip: {skip}, Returned skip: {returned_skip}")
                    
                    # Check for duplicate patient IDs
                    current_page_ids = set()
                    for patient in patients:
                        patient_id = patient.get("_id")
                        if patient_id:
                            current_page_ids.add(patient_id)
                            patient_ids_seen.add(patient_id)
                    
                    if len(current_page_ids) != len(patients):
                        print(f"   ⚠️  WARNING: Duplicate patients on this page!")
                        print(f"      Unique IDs: {len(current_page_ids)}, Total patients: {len(patients)}")
                    
                    # Show first few patient names
                    if patients:
                        print(f"   👥 Sample patients:")
                        for j, patient in enumerate(patients[:3], 1):
                            name = f"{patient.get('first_name', '')} {patient.get('last_name', '')}".strip()
                            print(f"      {j}. {name} (ID: {patient.get('_id', 'N/A')})")
                    
                    all_patients.extend(patients)
                    
                else:
                    print(f"   ❌ API returned success=False")
                    print(f"   📝 Response: {data}")
                    
            else:
                print(f"   ❌ HTTP {response.status_code}")
                print(f"   📝 Response: {response.text}")
                
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
    
    # Analyze overall results
    print("\n" + "=" * 50)
    print("📈 PAGINATION ANALYSIS")
    print("=" * 50)
    
    total_unique_patients = len(patient_ids_seen)
    total_returned = len(all_patients)
    
    print(f"📊 Total unique patients seen: {total_unique_patients}")
    print(f"📊 Total patient records returned: {total_returned}")
    
    if total_returned > total_unique_patients:
        print(f"🚨 CRITICAL ISSUE: {total_returned - total_unique_patients} duplicate patient records detected!")
        print(f"   This confirms the pagination is showing the same data on different pages.")
    else:
        print(f"✅ No duplicate patients detected in the test.")
    
    # Check if we're getting the same patients repeatedly
    if len(all_patients) > 0:
        first_page_ids = set()
        for patient in all_patients[:5]:  # First 5 patients
            patient_id = patient.get("_id")
            if patient_id:
                first_page_ids.add(patient_id)
        
        print(f"\n🔍 Checking for repeated first page data:")
        repeated_count = 0
        for i in range(5, len(all_patients), 5):  # Check every 5th patient
            if i < len(all_patients):
                patient_id = all_patients[i].get("_id")
                if patient_id in first_page_ids:
                    repeated_count += 1
        
        if repeated_count > 0:
            print(f"   ⚠️  Found {repeated_count} patients from first page repeated in later pages")
        else:
            print(f"   ✅ No obvious repetition of first page data detected")

if __name__ == "__main__":
    test_patient_pagination() 