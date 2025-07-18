#!/usr/bin/env python3
"""
Test script to verify AVA4 data display in Recent Medical Data table
"""

import requests
import json
from datetime import datetime

def test_ava4_display():
    """Test AVA4 data display in web panel"""
    
    print("🧪 Testing AVA4 Data Display in Recent Medical Data Table")
    print("=" * 60)
    
    # Test the recent medical data API
    try:
        print("📡 Fetching recent medical data from API...")
        response = requests.get('http://localhost:8098/api/recent-medical-data', timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ API call successful")
            
            if data.get('success'):
                medical_data = data.get('data', {}).get('recent_medical_data', [])
                print(f"📊 Found {len(medical_data)} medical data records")
                
                # Look for AVA4 records
                ava4_records = [record for record in medical_data if record.get('source') == 'AVA4']
                print(f"🔍 Found {len(ava4_records)} AVA4 records")
                
                if ava4_records:
                    print("\n📋 AVA4 Records Details:")
                    print("-" * 40)
                    
                    for i, record in enumerate(ava4_records[:3]):  # Show first 3 records
                        print(f"\n📋 AVA4 Record {i+1}:")
                        print(f"   ID: {record.get('id', 'N/A')}")
                        print(f"   Device ID: {record.get('device_id', 'N/A')}")
                        print(f"   Patient Name: {record.get('patient_name', 'N/A')}")
                        print(f"   Patient ID: {record.get('patient_id', 'N/A')}")
                        print(f"   Source: {record.get('source', 'N/A')}")
                        print(f"   Timestamp: {record.get('timestamp', 'N/A')}")
                        
                        # Check medical values
                        medical_values = record.get('medical_values', {})
                        if medical_values:
                            print(f"   Medical Values: {json.dumps(medical_values, indent=6)}")
                        
                        # Check raw data for AVA4 device info
                        raw_data = record.get('raw_data', {})
                        if raw_data:
                            print(f"   Raw Data Keys: {list(raw_data.keys())}")
                            
                            # Look for AVA4 device information
                            ava4_device_name = raw_data.get('ava4_device_name') or raw_data.get('device_name')
                            ava4_mac = raw_data.get('ava4_mac') or raw_data.get('mac')
                            
                            if ava4_device_name:
                                print(f"   ✅ AVA4 Device Name: {ava4_device_name}")
                            else:
                                print(f"   ❌ AVA4 Device Name: Not found")
                                
                            if ava4_mac:
                                print(f"   ✅ AVA4 MAC: {ava4_mac}")
                            else:
                                print(f"   ❌ AVA4 MAC: Not found")
                        
                        # Check if this is the blood glucose record we saw in logs
                        if medical_values.get('blood_glucose') == '100':
                            print(f"   🩸 Found Blood Glucose Record: {medical_values.get('blood_glucose')} mg/dL")
                            if medical_values.get('marker'):
                                print(f"   📍 Marker: {medical_values.get('marker')}")
                
                else:
                    print("❌ No AVA4 records found in medical data")
                    
                    # Show all available sources
                    sources = set(record.get('source') for record in medical_data if record.get('source'))
                    print(f"📊 Available sources: {list(sources)}")
                    
                    # Show sample records
                    if medical_data:
                        print("\n📋 Sample Records:")
                        for i, record in enumerate(medical_data[:2]):
                            print(f"   Record {i+1}: {record.get('source')} - {record.get('device_id')} - {record.get('patient_name')}")
                
            else:
                print(f"❌ API returned error: {data.get('error', 'Unknown error')}")
                
        else:
            print(f"❌ API call failed with status code: {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to web panel API (localhost:8098)")
        print("💡 Make sure the web panel is running")
    except Exception as e:
        print(f"❌ Error testing AVA4 display: {e}")

def test_web_panel_access():
    """Test if web panel is accessible"""
    
    print("\n🌐 Testing Web Panel Access")
    print("=" * 30)
    
    try:
        response = requests.get('http://localhost:8098', timeout=5)
        if response.status_code == 200:
            print("✅ Web panel is accessible")
            return True
        else:
            print(f"❌ Web panel returned status code: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to web panel")
        return False
    except Exception as e:
        print(f"❌ Error accessing web panel: {e}")
        return False

if __name__ == "__main__":
    print("🚀 AVA4 Display Test Script")
    print("=" * 40)
    
    # Test web panel access
    if test_web_panel_access():
        # Test AVA4 data display
        test_ava4_display()
    else:
        print("\n💡 Please make sure the web panel is running:")
        print("   docker restart stardust-mqtt-panel")
    
    print("\n✅ Test completed!") 