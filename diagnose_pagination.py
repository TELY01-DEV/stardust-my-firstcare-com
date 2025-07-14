#!/usr/bin/env python3
"""
Comprehensive Patient Pagination Diagnostic Script
Run this on the production server to identify the pagination issue
"""

import requests
import json
import time
from datetime import datetime

def test_api_pagination():
    """Test the API pagination endpoints"""
    base_url = "http://stardust.my-firstcare.com/api/v1/admin/patients"
    
    print("🔍 PATIENT PAGINATION DIAGNOSTIC")
    print("=" * 60)
    print(f"⏰ Test started at: {datetime.now()}")
    print(f"🌐 API Base URL: {base_url}")
    print()
    
    # Test cases
    test_cases = [
        {"limit": 5, "skip": 0, "page": "1st"},
        {"limit": 5, "skip": 5, "page": "2nd"},
        {"limit": 5, "skip": 10, "page": "3rd"},
        {"limit": 10, "skip": 0, "page": "1st (10 items)"},
        {"limit": 10, "skip": 10, "page": "2nd (10 items)"},
    ]
    
    all_patients = []
    all_patient_ids = []
    
    for i, test_case in enumerate(test_cases, 1):
        limit = test_case["limit"]
        skip = test_case["skip"]
        page = test_case["page"]
        
        print(f"📋 Test {i}: {page} page (limit={limit}, skip={skip})")
        print("-" * 50)
        
        try:
            # Make API request
            url = f"{base_url}?limit={limit}&skip={skip}"
            print(f"🔗 URL: {url}")
            
            response = requests.get(url, timeout=15)
            print(f"📡 HTTP Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("success"):
                    patients = data.get("data", {}).get("patients", [])
                    total = data.get("data", {}).get("total", 0)
                    returned_limit = data.get("data", {}).get("limit", 0)
                    returned_skip = data.get("data", {}).get("skip", 0)
                    
                    print(f"✅ Success: True")
                    print(f"📊 Total patients in DB: {total}")
                    print(f"📄 Patients returned: {len(patients)}")
                    print(f"🔢 Requested limit: {limit}, Returned: {returned_limit}")
                    print(f"🔢 Requested skip: {skip}, Returned: {returned_skip}")
                    
                    # Extract patient IDs and info
                    page_patient_ids = []
                    for j, patient in enumerate(patients, 1):
                        patient_id = patient.get("_id", "N/A")
                        name = f"{patient.get('first_name', '')} {patient.get('last_name', '')}".strip()
                        page_patient_ids.append(patient_id)
                        all_patient_ids.append(patient_id)
                        
                        print(f"   {j}. {name} (ID: {patient_id})")
                    
                    # Check for duplicates on this page
                    unique_ids = set(page_patient_ids)
                    if len(unique_ids) != len(page_patient_ids):
                        print(f"⚠️  WARNING: {len(page_patient_ids) - len(unique_ids)} duplicate patients on this page!")
                    
                    all_patients.extend(patients)
                    
                else:
                    print(f"❌ API returned success=False")
                    print(f"📝 Error: {data.get('message', 'Unknown error')}")
                    
            else:
                print(f"❌ HTTP Error: {response.status_code}")
                print(f"📝 Response: {response.text[:200]}...")
                
        except Exception as e:
            print(f"❌ Request failed: {str(e)}")
        
        print()
        time.sleep(1)  # Small delay between requests
    
    # Analyze results
    print("=" * 60)
    print("📈 PAGINATION ANALYSIS")
    print("=" * 60)
    
    total_unique_ids = len(set(all_patient_ids))
    total_returned = len(all_patient_ids)
    
    print(f"📊 Total patient records returned: {total_returned}")
    print(f"📊 Unique patient IDs: {total_unique_ids}")
    
    if total_returned > total_unique_ids:
        duplicates = total_returned - total_unique_ids
        print(f"🚨 CRITICAL ISSUE: {duplicates} duplicate patient records detected!")
        print(f"   This confirms the pagination is showing the same data on different pages.")
        
        # Find which patients are duplicated
        from collections import Counter
        id_counts = Counter(all_patient_ids)
        duplicated_ids = [pid for pid, count in id_counts.items() if count > 1]
        
        print(f"🔍 Duplicated patient IDs:")
        for dup_id in duplicated_ids[:10]:  # Show first 10
            count = id_counts[dup_id]
            print(f"   - {dup_id} (appears {count} times)")
        
        if len(duplicated_ids) > 10:
            print(f"   ... and {len(duplicated_ids) - 10} more")
            
    else:
        print(f"✅ No duplicate patients detected in the test.")
    
    # Check if first page data is repeated
    if len(all_patients) >= 10:
        first_page_ids = set(all_patient_ids[:5])  # First 5 patients
        
        repeated_count = 0
        for i in range(5, len(all_patient_ids), 5):  # Check every 5th patient
            if i < len(all_patient_ids):
                patient_id = all_patient_ids[i]
                if patient_id in first_page_ids:
                    repeated_count += 1
        
        if repeated_count > 0:
            print(f"⚠️  Found {repeated_count} patients from first page repeated in later pages")
        else:
            print(f"✅ No obvious repetition of first page data detected")
    
    print()
    print("=" * 60)
    print("🔧 POSSIBLE CAUSES & SOLUTIONS")
    print("=" * 60)
    
    if total_returned > total_unique_ids:
        print("🚨 The pagination is definitely broken. Possible causes:")
        print("   1. Missing database indexes causing inconsistent ordering")
        print("   2. API caching returning stale data")
        print("   3. Database connection issues")
        print("   4. MongoDB configuration problems")
        print()
        print("🔧 Recommended fixes:")
        print("   1. Check MongoDB indexes on the patients collection")
        print("   2. Verify database connection settings")
        print("   3. Check for any caching middleware")
        print("   4. Review the pagination query logic")
    else:
        print("✅ Pagination appears to be working correctly in this test.")
        print("   If you're still seeing issues, it might be:")
        print("   1. Frontend caching")
        print("   2. Browser caching")
        print("   3. Network/proxy caching")

def test_database_connection():
    """Test if we can connect to the database directly"""
    print("\n" + "=" * 60)
    print("🗄️  DATABASE CONNECTION TEST")
    print("=" * 60)
    
    try:
        # Try to get database info from the API
        response = requests.get("http://stardust.my-firstcare.com/health", timeout=10)
        if response.status_code == 200:
            print("✅ Health endpoint accessible")
            health_data = response.json()
            print(f"📊 Health data: {health_data}")
        else:
            print(f"⚠️  Health endpoint returned {response.status_code}")
            
    except Exception as e:
        print(f"❌ Cannot access health endpoint: {str(e)}")

if __name__ == "__main__":
    test_api_pagination()
    test_database_connection()
    
    print("\n" + "=" * 60)
    print("🏁 DIAGNOSTIC COMPLETE")
    print("=" * 60)
    print(f"⏰ Test completed at: {datetime.now()}") 