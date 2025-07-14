#!/usr/bin/env python3
"""
Test script to check device status summary endpoint
"""

import requests
import json

def test_device_status_summary():
    """Test the device status summary endpoint"""
    
    # API base URL
    base_url = "https://stardust.my-firstcare.com:5054"
    
    # Login to get token
    login_data = {
        "username": "admin",
        "password": "Sim!443355"
    }
    
    try:
        # Login
        print("🔐 Logging in...")
        login_response = requests.post(f"{base_url}/auth/login", json=login_data)
        login_response.raise_for_status()
        
        token = login_response.json()["data"]["access_token"]
        print("✅ Login successful")
        
        # Test device status summary
        print("\n📊 Testing device status summary endpoint...")
        headers = {"Authorization": f"Bearer {token}"}
        
        summary_response = requests.get(f"{base_url}/api/devices/status/summary", headers=headers)
        summary_response.raise_for_status()
        
        summary_data = summary_response.json()
        print("✅ Device status summary retrieved successfully")
        
        # Print summary
        print("\n📈 Device Status Summary:")
        print(f"Total Devices: {summary_data['data']['total_devices']}")
        print(f"Online Devices: {summary_data['data']['online_devices']}")
        print(f"Offline Devices: {summary_data['data']['offline_devices']}")
        print(f"Online Percentage: {summary_data['data']['online_percentage']}%")
        print(f"Low Battery Devices: {summary_data['data']['low_battery_devices']}")
        print(f"Devices with Alerts: {summary_data['data']['devices_with_alerts']}")
        
        # Print by type
        print("\n📱 By Device Type:")
        for device_type, stats in summary_data['data']['by_type'].items():
            print(f"  {device_type.upper()}:")
            print(f"    Total: {stats['total']}")
            print(f"    Online: {stats['online']}")
            print(f"    Offline: {stats['offline']}")
        
        # Test recent device status
        print("\n🕒 Testing recent device status endpoint...")
        recent_response = requests.get(f"{base_url}/api/devices/status/recent?limit=5", headers=headers)
        recent_response.raise_for_status()
        
        recent_data = recent_response.json()
        print(f"✅ Recent device status retrieved: {recent_data['data']['count']} devices")
        
        # Print recent devices
        if recent_data['data']['devices']:
            print("\n📱 Recent Device Status:")
            for device in recent_data['data']['devices'][:3]:  # Show first 3
                print(f"  {device['device_type'].upper()} {device['device_id']}: {device['online_status']}")
                if device.get('last_updated'):
                    print(f"    Last Updated: {device['last_updated']}")
        
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Testing Device Status Endpoints")
    print("=" * 50)
    
    success = test_device_status_summary()
    
    if success:
        print("\n✅ All tests completed successfully!")
    else:
        print("\n❌ Tests failed!") 