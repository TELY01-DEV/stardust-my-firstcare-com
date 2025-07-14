#!/usr/bin/env python3
"""
Test script for My FirstCare Opera Panel API
"""

import requests
import json
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:5055"
STARDUST_URL = "https://stardust-v1.my-firstcare.com"

def test_health_check():
    """Test health check endpoint"""
    print("🔍 Testing health check...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False

def test_root_endpoint():
    """Test root endpoint"""
    print("\n🔍 Testing root endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Root endpoint failed: {e}")
        return False

def test_stardust_connection():
    """Test Stardust-V1 connection"""
    print("\n🔍 Testing Stardust-V1 connection...")
    try:
        response = requests.get(f"{STARDUST_URL}/auth/me", 
                              headers={"Authorization": "Bearer test"})
        print(f"Status: {response.status_code}")
        # Should return 401 for invalid token, which means service is reachable
        return response.status_code in [401, 200]
    except Exception as e:
        print(f"❌ Stardust-V1 connection failed: {e}")
        return False

def test_ava4_endpoint():
    """Test AVA4 endpoint (should require auth)"""
    print("\n🔍 Testing AVA4 endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/api/ava4/devices")
        print(f"Status: {response.status_code}")
        # Should return 401 for missing auth
        return response.status_code == 401
    except Exception as e:
        print(f"❌ AVA4 endpoint failed: {e}")
        return False

def test_admin_endpoint():
    """Test admin endpoint (should require auth)"""
    print("\n🔍 Testing admin endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/admin/patients")
        print(f"Status: {response.status_code}")
        # Should return 401 for missing auth
        return response.status_code == 401
    except Exception as e:
        print(f"❌ Admin endpoint failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 My FirstCare Opera Panel API Tests")
    print("=" * 50)
    
    tests = [
        ("Health Check", test_health_check),
        ("Root Endpoint", test_root_endpoint),
        ("Stardust-V1 Connection", test_stardust_connection),
        ("AVA4 Endpoint (Auth Required)", test_ava4_endpoint),
        ("Admin Endpoint (Auth Required)", test_admin_endpoint),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        if test_func():
            print(f"✅ {test_name}: PASSED")
            passed += 1
        else:
            print(f"❌ {test_name}: FAILED")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All tests passed! API is ready for production.")
    else:
        print("⚠️  Some tests failed. Please check the configuration.")

if __name__ == "__main__":
    main() 