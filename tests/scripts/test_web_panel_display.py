#!/usr/bin/env python3
"""
Test script to check web panel AVA4 display
"""

import requests
import json

def test_web_panel_display():
    """Test if web panel is displaying AVA4 data correctly"""
    
    print("🧪 Testing Web Panel AVA4 Display")
    print("=" * 40)
    
    try:
        # Get the web panel page
        response = requests.get('http://localhost:8098', timeout=10)
        
        if response.status_code == 200:
            print("✅ Web panel page loaded successfully")
            
            # Check if the page contains our updated JavaScript functions
            content = response.text
            
            if 'getDeviceInfo' in content:
                print("✅ getDeviceInfo function found in web panel")
            else:
                print("❌ getDeviceInfo function not found in web panel")
                
            if 'getMedicalDeviceType' in content:
                print("✅ getMedicalDeviceType function found in web panel")
            else:
                print("❌ getMedicalDeviceType function not found in web panel")
                
            if 'rawData.device_mac' in content:
                print("✅ MAC address lookup in rawData found")
            else:
                print("❌ MAC address lookup in rawData not found")
                
            if 'rawData.ble_addr' in content:
                print("✅ BLE address lookup in rawData found")
            else:
                print("❌ BLE address lookup in rawData not found")
                
        else:
            print(f"❌ Web panel returned status code: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error testing web panel: {e}")

def test_ava4_data_structure():
    """Test AVA4 data structure to understand what's available"""
    
    print("\n📊 Testing AVA4 Data Structure")
    print("=" * 35)
    
    try:
        response = requests.get('http://localhost:8098/api/recent-medical-data', timeout=10)
        data = response.json()
        
        if data.get('success'):
            ava4_records = [r for r in data['data']['recent_medical_data'] if r['source'] == 'AVA4']
            
            if ava4_records:
                record = ava4_records[0]  # Get first AVA4 record
                
                print(f"📋 AVA4 Record Structure:")
                print(f"   Device ID: {record.get('device_id')}")
                print(f"   Patient Name: {record.get('patient_name')}")
                print(f"   Source: {record.get('source')}")
                
                # Check raw_data structure
                raw_data = record.get('raw_data', {})
                print(f"\n📄 Raw Data Structure:")
                print(f"   Keys: {list(raw_data.keys())}")
                
                # Look for MAC addresses
                if 'device_mac' in raw_data:
                    print(f"   ✅ device_mac: {raw_data['device_mac']}")
                else:
                    print(f"   ❌ device_mac: Not found")
                    
                if 'ble_addr' in raw_data:
                    print(f"   ✅ ble_addr: {raw_data['ble_addr']}")
                else:
                    print(f"   ❌ ble_addr: Not found")
                    
                # Check nested raw_data
                nested_raw = raw_data.get('raw_data', {})
                if nested_raw:
                    print(f"\n📄 Nested Raw Data:")
                    print(f"   Keys: {list(nested_raw.keys())}")
                    
                    if 'device_mac' in nested_raw:
                        print(f"   ✅ nested device_mac: {nested_raw['device_mac']}")
                    else:
                        print(f"   ❌ nested device_mac: Not found")
                        
                    if 'ble_addr' in nested_raw:
                        print(f"   ✅ nested ble_addr: {nested_raw['ble_addr']}")
                    else:
                        print(f"   ❌ nested ble_addr: Not found")
                
            else:
                print("❌ No AVA4 records found")
                
        else:
            print(f"❌ API call failed: {data.get('error')}")
            
    except Exception as e:
        print(f"❌ Error testing AVA4 data structure: {e}")

if __name__ == "__main__":
    test_web_panel_display()
    test_ava4_data_structure()
    print("\n✅ Test completed!") 