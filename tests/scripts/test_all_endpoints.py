#!/usr/bin/env python3
"""
Comprehensive Endpoint Testing Script
Tests all critical endpoints to ensure system functionality after removing duplicate routes
"""

import requests
import json
import time
from typing import Dict, List, Tuple
import sys

# Configuration
BASE_URL = "http://localhost:5054"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "Sim!443355"

# Load test data
def load_test_data():
    """Load test data from file"""
    try:
        with open("test_data.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print("⚠️  test_data.json not found, using default values")
        return {
            "hospitals_id": "6241716c2420fcbc3cab2c77",
            "provinces_id": "61a9f12fa47a09ab11267306",
            "districts_id": "61aeea669ba0391a4fa154fe",
            "sub-districts_id": "61aeea839ba0391a4fa158a5"
        }

TEST_DATA = load_test_data()

class EndpointTester:
    def __init__(self):
        self.session = requests.Session()
        self.token = None
        self.results = {
            "passed": [],
            "failed": [],
            "skipped": []
        }
        
    def login(self):
        """Login to get JWT token"""
        try:
            login_data = {
                "username": ADMIN_USERNAME,
                "password": ADMIN_PASSWORD
            }
            response = self.session.post(f"{BASE_URL}/auth/login", json=login_data)
            if response.status_code == 200:
                data = response.json()
                # Token is in the root, not nested under 'data'
                self.token = data.get("access_token")
                if self.token:
                    self.session.headers.update({"Authorization": f"Bearer {self.token}"})
                    print("✅ Login successful")
                    return True
            print(f"❌ Login failed: {response.status_code}")
            return False
        except Exception as e:
            print(f"❌ Login error: {e}")
            return False
    
    def test_endpoint(self, method: str, path: str, expected_status: int = 200, 
                     data: dict = None, description: str = "") -> bool:
        """Test a single endpoint"""
        try:
            url = f"{BASE_URL}{path}"
            
            if method.upper() == "GET":
                response = self.session.get(url)
            elif method.upper() == "POST":
                response = self.session.post(url, json=data if data is not None else {})
            elif method.upper() == "PUT":
                response = self.session.put(url, json=data if data is not None else {})
            elif method.upper() == "DELETE":
                response = self.session.delete(url)
            else:
                print(f"❌ Unknown method: {method}")
                return False
            
            success = response.status_code == expected_status
            status_icon = "✅" if success else "❌"
            
            print(f"{status_icon} {method} {path} - {response.status_code}")
            
            if success:
                self.results["passed"].append(f"{method} {path}")
            else:
                # Print detailed error message
                try:
                    error_detail = response.json()
                except Exception:
                    error_detail = response.text
                print(f"   ↳ Response: {error_detail}")
                self.results["failed"].append(f"{method} {path} - Expected {expected_status}, got {response.status_code} - {error_detail}")
            
            return success
            
        except Exception as e:
            print(f"❌ {method} {path} - Error: {e}")
            self.results["failed"].append(f"{method} {path} - Error: {e}")
            return False
    
    def test_health_endpoints(self):
        """Test health and basic endpoints"""
        print("\n🔍 Testing Health Endpoints...")
        
        # Health check
        self.test_endpoint("GET", "/health")
        
        # Root endpoint
        self.test_endpoint("GET", "/")
        
        # OpenAPI docs
        self.test_endpoint("GET", "/docs", 200)
        self.test_endpoint("GET", "/openapi.json", 200)
    
    def test_auth_endpoints(self):
        """Test authentication endpoints"""
        print("\n🔐 Testing Authentication Endpoints...")
        
        # Test login (we already did this)
        self.test_endpoint("POST", "/auth/login", 200, {
            "username": ADMIN_USERNAME,
            "password": ADMIN_PASSWORD
        })
        
        # Test logout
        self.test_endpoint("POST", "/auth/logout", 200)
        
        # Test refresh token
        self.test_endpoint("POST", "/auth/refresh", 200)
    
    def test_master_data_endpoints(self):
        """Test master data CRUD operations"""
        print("\n📊 Testing Master Data Endpoints...")
        
        # Test GET with pagination
        self.test_endpoint("GET", "/admin/master-data/hospitals?limit=10&page=1")
        
        # Test GET by ID (using real hospital ID)
        self.test_endpoint("GET", f"/admin/master-data/hospitals/{TEST_DATA['hospitals_id']}")
        
        # Test bulk export
        self.test_endpoint("GET", "/admin/master-data/hospitals/bulk-export?format=json")
        
        # Test other data types
        self.test_endpoint("GET", "/admin/master-data/provinces?limit=5")
        self.test_endpoint("GET", "/admin/master-data/districts?limit=5")
        self.test_endpoint("GET", "/admin/master-data/sub-districts?limit=5")
    
    def test_device_endpoints(self):
        """Test device management endpoints"""
        print("\n📱 Testing Device Endpoints...")
        
        # Test GET devices with pagination
        self.test_endpoint("GET", "/admin/devices?limit=10&page=1")
        
        # Test GET device by ID (using real device ID if available)
        if "device_id" in TEST_DATA:
            self.test_endpoint("GET", f"/admin/devices/{TEST_DATA['device_id']}")
        else:
            # Skip this test if no device ID available
            self.results["skipped"].append("GET /admin/devices/{device_id} - No device ID available")
            print("⏭️  GET /admin/devices/{device_id} - Skipped (no device ID available)")
        
        # Test device mapping endpoints
        self.test_endpoint("GET", "/admin/device-mapping/")
        self.test_endpoint("GET", "/admin/device-mapping/device-types")
        self.test_endpoint("GET", "/admin/device-mapping/available/ava4-boxes")
        self.test_endpoint("GET", "/admin/device-mapping/available/kati-watches")
    
    def test_patient_endpoints(self):
        """Test patient management endpoints"""
        print("\n👥 Testing Patient Endpoints...")
        
        # Test GET patients with pagination
        self.test_endpoint("GET", "/admin/patients?limit=10&page=1")
        
        # Test patient search
        self.test_endpoint("GET", "/admin/patients/search?query=test")
        
        # Test GET patient by ID (using real patient ID if available)
        if "patient_id" in TEST_DATA:
            self.test_endpoint("GET", f"/admin/patients/{TEST_DATA['patient_id']}")
        else:
            # Skip this test if no patient ID available
            self.results["skipped"].append("GET /admin/patients/{patient_id} - No patient ID available")
            print("⏭️  GET /admin/patients/{patient_id} - Skipped (no patient ID available)")
    
    def test_medical_history_endpoints(self):
        """Test medical history endpoints"""
        print("\n🏥 Testing Medical History Endpoints...")
        
        # Test GET medical history with pagination
        self.test_endpoint("GET", "/admin/medical-history/blood_pressure?limit=10&page=1")
        
        # Test GET by ID (using real history ID if available)
        if "medical_history_id" in TEST_DATA:
            self.test_endpoint("GET", f"/admin/medical-history/blood_pressure/{TEST_DATA['medical_history_id']}")
        else:
            # Skip this test if no history ID available
            self.results["skipped"].append("GET /admin/medical-history/blood_pressure/{record_id} - No history ID available")
            print("⏭️  GET /admin/medical-history/blood_pressure/{record_id} - Skipped (no history ID available)")
        
        # Test medical history management
        self.test_endpoint("GET", "/admin/medical-history-management/blood_pressure?limit=10&page=1")
        self.test_endpoint("GET", "/admin/medical-history-management/blood_pressure/search?query=test")
    
    def test_hospital_user_endpoints(self):
        """Test hospital user endpoints"""
        print("\n👨‍⚕️ Testing Hospital User Endpoints...")
        
        # Test GET hospital users with pagination
        self.test_endpoint("GET", "/admin/hospital-users?limit=10&page=1")
        
        # Test hospital user search
        self.test_endpoint("GET", "/admin/hospital-users/search?query=test")
        
        # Test stats
        self.test_endpoint("GET", "/admin/hospital-users/stats/summary")
        
        # Test GET by ID (using real user ID if available)
        if "hospital_user_id" in TEST_DATA:
            self.test_endpoint("GET", f"/admin/hospital-users/{TEST_DATA['hospital_user_id']}")
        else:
            # Skip this test if no user ID available
            self.results["skipped"].append("GET /admin/hospital-users/{user_id} - No user ID available")
            print("⏭️  GET /admin/hospital-users/{user_id} - Skipped (no user ID available)")
    
    def test_analytics_endpoints(self):
        """Test analytics endpoints"""
        print("\n📈 Testing Analytics Endpoints...")
        
        # Test analytics overview
        self.test_endpoint("GET", "/admin/analytics")
        
        # Test performance endpoints
        self.test_endpoint("GET", "/admin/performance/cache/stats")
        self.test_endpoint("GET", "/admin/performance/database/stats")
        self.test_endpoint("GET", "/admin/performance/slow-queries")
    
    def test_security_endpoints(self):
        """Test security endpoints"""
        print("\n🔒 Testing Security Endpoints...")
        
        # Test security alerts
        self.test_endpoint("GET", "/admin/security/alerts/active")
        
        # Test rate limiting
        self.test_endpoint("GET", "/admin/rate-limit/blacklist")
        self.test_endpoint("GET", "/admin/rate-limit/whitelist")
    
    def test_dropdown_endpoints(self):
        """Test dropdown endpoints"""
        print("\n📋 Testing Dropdown Endpoints...")
        
        # Test geographic dropdowns
        self.test_endpoint("GET", "/admin/dropdown/provinces")
        
        # Test districts with province code
        if "province_code" in TEST_DATA:
            self.test_endpoint("GET", f"/admin/dropdown/districts?province_code={TEST_DATA['province_code']}")
        else:
            # Try with a default province code
            self.test_endpoint("GET", "/admin/dropdown/districts?province_code=10")
        
        # Test sub-districts with province and district codes
        if "province_code" in TEST_DATA and "district_code" in TEST_DATA:
            self.test_endpoint("GET", f"/admin/dropdown/sub-districts?province_code={TEST_DATA['province_code']}&district_code={TEST_DATA['district_code']}")
        else:
            # Try with default codes
            self.test_endpoint("GET", "/admin/dropdown/sub-districts?province_code=10&district_code=1001")
    
    def run_all_tests(self):
        """Run all endpoint tests"""
        print("🚀 Starting Comprehensive Endpoint Testing...")
        print(f"📍 Testing against: {BASE_URL}")
        
        # Login first
        if not self.login():
            print("❌ Cannot proceed without authentication")
            return False
        
        # Run all test suites
        self.test_health_endpoints()
        self.test_auth_endpoints()
        self.test_master_data_endpoints()
        self.test_device_endpoints()
        self.test_patient_endpoints()
        self.test_medical_history_endpoints()
        self.test_hospital_user_endpoints()
        self.test_analytics_endpoints()
        self.test_security_endpoints()
        self.test_dropdown_endpoints()
        
        # Print results
        self.print_results()
        
        return len(self.results["failed"]) == 0
    
    def print_results(self):
        """Print test results summary"""
        print("\n" + "="*60)
        print("📊 TEST RESULTS SUMMARY")
        print("="*60)
        
        total_tests = len(self.results["passed"]) + len(self.results["failed"]) + len(self.results["skipped"])
        
        print(f"✅ Passed: {len(self.results['passed'])}")
        print(f"❌ Failed: {len(self.results['failed'])}")
        print(f"⏭️  Skipped: {len(self.results['skipped'])}")
        print(f"📊 Total: {total_tests}")
        
        if self.results["failed"]:
            print("\n❌ FAILED TESTS:")
            for failure in self.results["failed"]:
                print(f"   - {failure}")
        
        success_rate = (len(self.results["passed"]) / total_tests * 100) if total_tests > 0 else 0
        print(f"\n🎯 Success Rate: {success_rate:.1f}%")
        
        if len(self.results["failed"]) == 0:
            print("\n🎉 ALL TESTS PASSED! System is working correctly.")
        else:
            print(f"\n⚠️  {len(self.results['failed'])} tests failed. Please review.")

if __name__ == "__main__":
    tester = EndpointTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1) 