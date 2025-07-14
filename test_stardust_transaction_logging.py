#!/usr/bin/env python3
"""
Test Stardust Transaction Logging
Tests the new transaction logging endpoints in the local Stardust API
"""

import requests
import json
from datetime import datetime

def test_transaction_logging():
    """Test the transaction logging endpoints"""
    
    # Local Stardust API URL
    base_url = "http://localhost:8000"
    
    print("🧪 Testing Stardust Transaction Logging...")
    print(f"📍 API URL: {base_url}")
    print()
    
    # Test 1: Check if endpoints exist (should get auth error, not 404)
    print("1️⃣ Testing endpoint availability...")
    
    try:
        response = requests.get(f"{base_url}/api/transactions/logs", timeout=5)
        if response.status_code == 401:
            print("✅ Transaction logs endpoint exists (requires authentication)")
        elif response.status_code == 404:
            print("❌ Transaction logs endpoint not found")
            return False
        else:
            print(f"⚠️ Unexpected response: {response.status_code}")
    except Exception as e:
        print(f"❌ Error testing endpoint: {e}")
        return False
    
    # Test 2: Try to log a transaction (should get auth error, not 404)
    print("\n2️⃣ Testing transaction logging...")
    
    try:
        transaction_data = {
            "operation": "test_operation",
            "data_type": "test_data",
            "collection": "test_collection",
            "patient_id": "test_patient_123",
            "details": "Test transaction from MQTT listener",
            "device_id": "test_device_456"
        }
        
        response = requests.post(
            f"{base_url}/api/transactions/log",
            json=transaction_data,
            headers={"Content-Type": "application/json"},
            timeout=5
        )
        
        if response.status_code == 401:
            print("✅ Transaction log endpoint exists (requires authentication)")
        elif response.status_code == 404:
            print("❌ Transaction log endpoint not found")
            return False
        else:
            print(f"⚠️ Unexpected response: {response.status_code}")
            print(f"Response: {response.text}")
    except Exception as e:
        print(f"❌ Error testing transaction logging: {e}")
        return False
    
    # Test 3: Check recent transactions endpoint
    print("\n3️⃣ Testing recent transactions endpoint...")
    
    try:
        response = requests.get(f"{base_url}/api/transactions/recent", timeout=5)
        if response.status_code == 401:
            print("✅ Recent transactions endpoint exists (requires authentication)")
        elif response.status_code == 404:
            print("❌ Recent transactions endpoint not found")
            return False
        else:
            print(f"⚠️ Unexpected response: {response.status_code}")
    except Exception as e:
        print(f"❌ Error testing recent transactions: {e}")
        return False
    
    # Test 4: Check statistics endpoint
    print("\n4️⃣ Testing transaction statistics endpoint...")
    
    try:
        response = requests.get(f"{base_url}/api/transactions/statistics", timeout=5)
        if response.status_code == 401:
            print("✅ Transaction statistics endpoint exists (requires authentication)")
        elif response.status_code == 404:
            print("❌ Transaction statistics endpoint not found")
            return False
        else:
            print(f"⚠️ Unexpected response: {response.status_code}")
    except Exception as e:
        print(f"❌ Error testing transaction statistics: {e}")
        return False
    
    print("\n✅ All transaction logging endpoints are available!")
    print("📝 Note: Endpoints require authentication (401 errors are expected)")
    print("🚀 The MQTT listeners should now be able to log transactions once deployed to production")
    
    return True

if __name__ == "__main__":
    test_transaction_logging() 