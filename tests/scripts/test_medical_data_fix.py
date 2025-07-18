#!/usr/bin/env python3
"""
Test script to verify medical data type classification fixes
"""

import requests
import json
from datetime import datetime

def test_medical_data_api():
    """Test the medical data API to check data type classification"""
    
    # Test the recent medical data API endpoint
    url = "http://localhost:8098/api/recent-medical-data"
    
    try:
        print("🔍 Testing medical data API...")
        print(f"📡 URL: {url}")
        
        # Make request to the API
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('success'):
                medical_data = data.get('data', {}).get('recent_medical_data', [])
                
                print(f"✅ API Response: {len(medical_data)} medical records found")
                print()
                
                # Analyze the data types
                data_types = {}
                unknown_count = 0
                
                for record in medical_data[:10]:  # Check first 10 records
                    source = record.get('source', 'Unknown')
                    medical_values = record.get('medical_values', {})
                    patient_name = record.get('patient_name', 'Unknown')
                    device_id = record.get('device_id', 'Unknown')
                    
                    # Count data types
                    if source not in data_types:
                        data_types[source] = 0
                    data_types[source] += 1
                    
                    # Check for unknown data types
                    if source == 'Unknown':
                        unknown_count += 1
                        print(f"⚠️  Unknown source found:")
                        print(f"   Device ID: {device_id}")
                        print(f"   Patient: {patient_name}")
                        print(f"   Medical Values: {medical_values}")
                        print()
                
                print("📊 Data Type Analysis:")
                for source, count in data_types.items():
                    print(f"   {source}: {count} records")
                
                print()
                print(f"🔍 Unknown data types: {unknown_count}")
                
                if unknown_count == 0:
                    print("✅ SUCCESS: No unknown data types found!")
                else:
                    print(f"⚠️  WARNING: {unknown_count} records with unknown data types")
                
                # Show sample of recent records
                print()
                print("📋 Sample Recent Records:")
                for i, record in enumerate(medical_data[:5]):
                    source = record.get('source', 'Unknown')
                    patient_name = record.get('patient_name', 'Unknown')
                    device_id = record.get('device_id', 'Unknown')
                    medical_values = record.get('medical_values', {})
                    
                    print(f"   {i+1}. {patient_name} ({device_id}) - {source}")
                    if medical_values:
                        print(f"      Medical Values: {medical_values}")
                    print()
                
            else:
                print(f"❌ API Error: {data.get('error', 'Unknown error')}")
                
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request Error: {e}")
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")

def test_medical_monitor_page():
    """Test the medical monitor page directly"""
    
    url = "http://localhost:8098/medical-monitor"
    
    try:
        print("🔍 Testing medical monitor page...")
        print(f"📡 URL: {url}")
        
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            print("✅ Medical monitor page is accessible")
            
            # Check if the page contains our improved JavaScript functions
            content = response.text
            
            if 'getDataType' in content and 'source.includes' in content:
                print("✅ Improved getDataType function found")
            else:
                print("⚠️  getDataType function not found or not improved")
                
            if 'getDataValue' in content and 'medicalValues.heart_rate' in content:
                print("✅ Improved getDataValue function found")
            else:
                print("⚠️  getDataValue function not found or not improved")
                
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request Error: {e}")
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")

if __name__ == "__main__":
    print("🧪 Medical Data Type Classification Test")
    print("=" * 50)
    print()
    
    test_medical_data_api()
    print()
    test_medical_monitor_page()
    
    print()
    print("🏁 Test completed!") 