#!/usr/bin/env python3
"""
Fetch Test Data Script
Extracts real ObjectIds and required parameters from the database for endpoint testing
"""

import requests
import json
from typing import Dict, List, Optional

# Configuration
BASE_URL = "http://localhost:5054"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "Sim!443355"

class TestDataFetcher:
    def __init__(self):
        self.session = requests.Session()
        self.token = None
        self.test_data = {}
        
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
    
    def fetch_master_data_ids(self):
        """Fetch ObjectIds from master data collections"""
        print("\n📊 Fetching Master Data ObjectIds...")
        
        master_data_types = ["hospitals", "provinces", "districts", "sub-districts"]
        
        for data_type in master_data_types:
            try:
                # Use bulk export for better data access
                response = self.session.get(f"{BASE_URL}/admin/master-data/{data_type}/bulk-export?format=json&limit=1")
                if response.status_code == 200:
                    data = response.json()
                    if data.get("success") and data.get("data", {}).get("data"):
                        records = data["data"]["data"]
                        if records and len(records) > 0:
                            record = records[0]
                            record_id = record.get("_id")
                            if record_id:
                                self.test_data[f"{data_type}_id"] = record_id
                                print(f"✅ {data_type}: {record_id}")
                            else:
                                print(f"⚠️  {data_type}: No _id found")
                        else:
                            print(f"⚠️  {data_type}: No records found")
                    else:
                        print(f"⚠️  {data_type}: No data found")
                else:
                    print(f"❌ {data_type}: {response.status_code}")
            except Exception as e:
                print(f"❌ {data_type}: Error - {e}")
    
    def fetch_device_ids(self):
        """Fetch device ObjectIds"""
        print("\n📱 Fetching Device ObjectIds...")
        
        try:
            # Try to get device mapping data instead
            response = self.session.get(f"{BASE_URL}/admin/device-mapping/")
            if response.status_code == 200:
                data = response.json()
                if data.get("success") and data.get("data"):
                    devices = data["data"]
                    if devices and len(devices) > 0:
                        device = devices[0]
                        device_id = device.get("_id") or device.get("device_id")
                        device_type = device.get("device_type")
                        if device_id:
                            self.test_data["device_id"] = device_id
                            if device_type:
                                self.test_data["device_type"] = device_type
                            print(f"✅ device_id: {device_id}")
                            print(f"✅ device_type: {device_type}")
                        else:
                            print("⚠️  No device _id found")
                    else:
                        print("⚠️  No device records found")
                else:
                    print("⚠️  No device data found")
            else:
                print(f"❌ Devices: {response.status_code}")
        except Exception as e:
            print(f"❌ Devices: Error - {e}")
    
    def fetch_patient_ids(self):
        """Fetch patient ObjectIds"""
        print("\n👥 Fetching Patient ObjectIds...")
        
        try:
            response = self.session.get(f"{BASE_URL}/admin/patients?limit=1")
            if response.status_code == 200:
                data = response.json()
                if data.get("success") and data.get("data", {}).get("records"):
                    records = data["data"]["records"]
                    if records and len(records) > 0:
                        record = records[0]
                        patient_id = record.get("_id")
                        if patient_id:
                            self.test_data["patient_id"] = patient_id
                            print(f"✅ patient_id: {patient_id}")
                        else:
                            print("⚠️  No patient _id found")
                    else:
                        print("⚠️  No patient records found")
                else:
                    print("⚠️  No patient data found")
            else:
                print(f"❌ Patients: {response.status_code}")
        except Exception as e:
            print(f"❌ Patients: Error - {e}")
    
    def fetch_hospital_user_ids(self):
        """Fetch hospital user ObjectIds"""
        print("\n👨‍⚕️ Fetching Hospital User ObjectIds...")
        
        try:
            response = self.session.get(f"{BASE_URL}/admin/hospital-users?limit=1")
            if response.status_code == 200:
                data = response.json()
                if data.get("success") and data.get("data", {}).get("records"):
                    records = data["data"]["records"]
                    if records and len(records) > 0:
                        record = records[0]
                        user_id = record.get("_id")
                        if user_id:
                            self.test_data["hospital_user_id"] = user_id
                            print(f"✅ hospital_user_id: {user_id}")
                        else:
                            print("⚠️  No hospital user _id found")
                    else:
                        print("⚠️  No hospital user records found")
                else:
                    print("⚠️  No hospital user data found")
            else:
                print(f"❌ Hospital Users: {response.status_code}")
        except Exception as e:
            print(f"❌ Hospital Users: Error - {e}")
    
    def fetch_medical_history_ids(self):
        """Fetch medical history ObjectIds"""
        print("\n🏥 Fetching Medical History ObjectIds...")
        
        try:
            response = self.session.get(f"{BASE_URL}/admin/medical-history/blood_pressure?limit=1")
            if response.status_code == 200:
                data = response.json()
                if data.get("success") and data.get("data", {}).get("history"):
                    history = data["data"]["history"]
                    if history and len(history) > 0:
                        record = history[0]
                        history_id = record.get("_id")
                        if history_id:
                            self.test_data["medical_history_id"] = history_id
                            print(f"✅ medical_history_id: {history_id}")
                        else:
                            print("⚠️  No medical history _id found")
                    else:
                        print("⚠️  No medical history records found")
                else:
                    print("⚠️  No medical history data found")
            else:
                print(f"❌ Medical History: {response.status_code}")
        except Exception as e:
            print(f"❌ Medical History: Error - {e}")
    
    def fetch_geographic_codes(self):
        """Fetch province and district codes for dropdown testing"""
        print("\n🗺️ Fetching Geographic Codes...")
        
        try:
            # Get provinces first
            response = self.session.get(f"{BASE_URL}/admin/dropdown/provinces")
            if response.status_code == 200:
                data = response.json()
                if data.get("success") and data.get("data"):
                    provinces = data["data"]
                    if provinces and len(provinces) > 0:
                        # Get first province code
                        first_province = provinces[0]
                        province_code = first_province.get("code")
                        if province_code:
                            self.test_data["province_code"] = province_code
                            print(f"✅ province_code: {province_code}")
                            
                            # Now get districts for this province
                            response2 = self.session.get(f"{BASE_URL}/admin/dropdown/districts?province_code={province_code}")
                            if response2.status_code == 200:
                                data2 = response2.json()
                                if data2.get("success") and data2.get("data"):
                                    districts = data2["data"]
                                    if districts and len(districts) > 0:
                                        first_district = districts[0]
                                        district_code = first_district.get("code")
                                        if district_code:
                                            self.test_data["district_code"] = district_code
                                            print(f"✅ district_code: {district_code}")
                                        else:
                                            print("⚠️  No district code found")
                                    else:
                                        print("⚠️  No districts found")
                                else:
                                    print("⚠️  No district data found")
                            else:
                                print(f"❌ Districts: {response2.status_code}")
                        else:
                            print("⚠️  No province code found")
                    else:
                        print("⚠️  No provinces found")
                else:
                    print("⚠️  No province data found")
            else:
                print(f"❌ Provinces: {response.status_code}")
        except Exception as e:
            print(f"❌ Geographic Codes: Error - {e}")
    
    def fetch_all_test_data(self):
        """Fetch all required test data"""
        print("🚀 Fetching All Test Data...")
        
        if not self.login():
            print("❌ Cannot proceed without authentication")
            return False
        
        self.fetch_master_data_ids()
        self.fetch_device_ids()
        self.fetch_patient_ids()
        self.fetch_hospital_user_ids()
        self.fetch_medical_history_ids()
        self.fetch_geographic_codes()
        
        # Save to file
        self.save_test_data()
        
        return True
    
    def save_test_data(self):
        """Save test data to file"""
        try:
            with open("test_data.json", "w") as f:
                json.dump(self.test_data, f, indent=2)
            print(f"\n💾 Test data saved to test_data.json")
            print(f"📊 Total items: {len(self.test_data)}")
            
            # Print summary
            print("\n📋 Test Data Summary:")
            for key, value in self.test_data.items():
                print(f"   {key}: {value}")
                
        except Exception as e:
            print(f"❌ Error saving test data: {e}")

if __name__ == "__main__":
    fetcher = TestDataFetcher()
    fetcher.fetch_all_test_data() 