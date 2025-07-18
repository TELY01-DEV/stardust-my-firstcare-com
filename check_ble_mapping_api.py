#!/usr/bin/env python3
"""
Check BLE Device Mapping using API Endpoint
"""

import requests
import json
import sys

def check_ble_device_mapping(ble_mac: str, base_url: str = "http://localhost:5054"):
    """Check BLE device mapping using the API endpoint"""
    
    # API endpoint for device lookup
    endpoint = f"{base_url}/api/medical-devices/patient/{ble_mac}"
    
    # Headers (you'll need to add authentication)
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    print(f"🔍 Checking BLE device mapping for: {ble_mac}")
    print(f"📡 API Endpoint: {endpoint}")
    print("=" * 60)
    
    try:
        # Make the API request
        response = requests.get(endpoint, headers=headers, timeout=30)
        
        print(f"📊 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Device mapping found!")
            print("\n📋 Device Information:")
            print(f"   MAC Address: {data.get('data', {}).get('mac_address', 'N/A')}")
            print(f"   Device Type: {data.get('data', {}).get('device_type', 'N/A')}")
            print(f"   Device Name: {data.get('data', {}).get('device_name', 'N/A')}")
            print(f"   MAC Field: {data.get('data', {}).get('mac_field', 'N/A')}")
            
            # Patient information
            patient_info = data.get('data', {}).get('patient_info', {})
            if patient_info:
                print(f"\n👤 Patient Information:")
                print(f"   Patient ID: {patient_info.get('patient_id', 'N/A')}")
                print(f"   Name: {patient_info.get('name', 'N/A')}")
                print(f"   First Name: {patient_info.get('first_name', 'N/A')}")
                print(f"   Last Name: {patient_info.get('last_name', 'N/A')}")
                print(f"   HN: {patient_info.get('hn', 'N/A')}")
                print(f"   Phone: {patient_info.get('phone', 'N/A')}")
                print(f"   Email: {patient_info.get('email', 'N/A')}")
                print(f"   Birth Date: {patient_info.get('birth_date', 'N/A')}")
                print(f"   Gender: {patient_info.get('gender', 'N/A')}")
                print(f"   Is Active: {patient_info.get('is_active', 'N/A')}")
            
            # Healthcare provider information
            provider_info = data.get('data', {}).get('healthcare_provider', {})
            if provider_info:
                print(f"\n🏥 Healthcare Provider:")
                print(f"   User ID: {provider_info.get('user_id', 'N/A')}")
                print(f"   Username: {provider_info.get('username', 'N/A')}")
                print(f"   Name: {provider_info.get('name', 'N/A')}")
                print(f"   Email: {provider_info.get('email', 'N/A')}")
            
            # Registry information
            print(f"\n📝 Registry Information:")
            print(f"   Registry ID: {data.get('data', {}).get('registry_id', 'N/A')}")
            print(f"   Group: {data.get('data', {}).get('group', 'N/A')}")
            print(f"   Created At: {data.get('data', {}).get('registry_created_at', 'N/A')}")
            print(f"   Updated At: {data.get('data', {}).get('registry_updated_at', 'N/A')}")
            
            # All patient devices (if requested)
            all_devices = data.get('data', {}).get('all_patient_devices', [])
            if all_devices:
                print(f"\n📱 All Patient Devices ({len(all_devices)} devices):")
                for i, device in enumerate(all_devices, 1):
                    print(f"   {i}. {device.get('device_name', 'Unknown')}")
                    print(f"      Type: {device.get('device_type', 'N/A')}")
                    print(f"      MAC: {device.get('mac_address', 'N/A')}")
                    print(f"      Is Queried Device: {device.get('is_queried_device', False)}")
                    print()
            
            print("=" * 60)
            print("✅ Device mapping investigation complete!")
            
        elif response.status_code == 404:
            print("❌ Device not found!")
            error_data = response.json()
            print(f"   Error: {error_data.get('detail', {}).get('message', 'Unknown error')}")
            print(f"   Field: {error_data.get('detail', {}).get('field', 'N/A')}")
            print(f"   Value: {error_data.get('detail', {}).get('value', 'N/A')}")
            
        elif response.status_code == 401:
            print("❌ Authentication required!")
            print("   You need to provide a valid authentication token.")
            print("   Add the token to the headers: Authorization: Bearer <your_token>")
            
        else:
            print(f"❌ API Error: {response.status_code}")
            try:
                error_data = response.json()
                print(f"   Error: {error_data}")
            except:
                print(f"   Response: {response.text}")
                
    except requests.exceptions.ConnectionError:
        print("❌ Connection Error!")
        print("   Could not connect to the API server.")
        print(f"   Make sure the server is running at: {base_url}")
        
    except requests.exceptions.Timeout:
        print("❌ Timeout Error!")
        print("   The request timed out.")
        
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")

def check_with_auth(ble_mac: str, auth_token: str, base_url: str = "http://localhost:5054"):
    """Check BLE device mapping with authentication token"""
    
    endpoint = f"{base_url}/api/medical-devices/patient/{ble_mac}"
    
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {auth_token}"
    }
    
    print(f"🔍 Checking BLE device mapping with authentication for: {ble_mac}")
    print(f"📡 API Endpoint: {endpoint}")
    print("=" * 60)
    
    try:
        response = requests.get(endpoint, headers=headers, timeout=30)
        
        print(f"📊 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Device mapping found!")
            
            # Simplified output for authenticated request
            patient_info = data.get('data', {}).get('patient_info', {})
            if patient_info:
                print(f"\n👤 Patient: {patient_info.get('name', 'N/A')} (ID: {patient_info.get('patient_id', 'N/A')})")
                print(f"📱 Device: {data.get('data', {}).get('device_name', 'N/A')} ({data.get('data', {}).get('device_type', 'N/A')})")
                print(f"🔗 MAC: {data.get('data', {}).get('mac_address', 'N/A')}")
            else:
                print("⚠️ Device found but no patient information available")
                
        else:
            print(f"❌ Error: {response.status_code}")
            try:
                error_data = response.json()
                print(f"   Details: {error_data}")
            except:
                print(f"   Response: {response.text}")
                
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    ble_mac = "c12488906de0"
    
    print("BLE Device Mapping Check Tool")
    print("=" * 60)
    
    # Check without authentication first
    check_ble_device_mapping(ble_mac)
    
    print("\n" + "=" * 60)
    print("To check with authentication, use:")
    print(f"python3 check_ble_mapping_api.py --auth <your_token>")
    print("or modify the script to include your auth token.") 