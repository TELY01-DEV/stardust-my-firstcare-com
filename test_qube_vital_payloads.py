#!/usr/bin/env python3
"""
Test Qube-Vital MQTT Payload Processing
Tests all Qube-Vital message types from the documentation
"""

import os
import json
import sys
import asyncio
from datetime import datetime
from typing import Dict, Any

# Add shared utilities to path
sys.path.append('services/mqtt-listeners/shared')

from device_mapper import DeviceMapper
from data_processor import DataProcessor
from device_status_service import DeviceStatusService

class QubeVitalPayloadTester:
    """Test Qube-Vital MQTT payload processing"""
    
    def __init__(self):
        # MongoDB Configuration
        self.mongodb_uri = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
        self.mongodb_database = os.getenv('MONGODB_DATABASE', 'AMY')
        
        # Initialize services
        self.device_mapper = DeviceMapper(self.mongodb_uri, self.mongodb_database)
        self.data_processor = DataProcessor(self.mongodb_uri, self.mongodb_database)
        self.device_status_service = DeviceStatusService(self.mongodb_uri, self.mongodb_database)
        
        # Test data from Qube-Vital documentation
        self.test_payloads = {
            "online_status": {
                "from": "PI_GW",
                "to": "CLOUD",
                "name": "Vital Box PHAi#1",
                "time": 1714788661,
                "mac": "dc:a6:32:fe:a3:eb",
                "IMEI": "867395074089109",
                "ICCID": "520031008598593",
                "type": "HB_Msg",
                "data": {
                    "msg": "Online"
                }
            },
            "blood_pressure": {
                "from": "PI",
                "to": "CLOUD",
                "time": 1739360702,
                "mac": "e4:5f:01:ed:82:59",
                "type": "reportAttribute",
                "citiz": "3570300400000",
                "nameTH": "นาย#เดพ##เอชวีศูนย์หนึ่ง",
                "nameEN": "Mr.#DEV##HV01",
                "brith": "25220713",
                "gender": "1",
                "data": {
                    "attribute": "WBP_JUMPER",
                    "ble_mac": "FF:22:09:08:31:31",
                    "value": {
                        "bp_high": 120,
                        "bp_low": 78,
                        "pr": 71
                    }
                }
            },
            "blood_glucose": {
                "from": "PI",
                "to": "CLOUD",
                "time": 1739360702,
                "mac": "e4:5f:01:ed:82:59",
                "type": "reportAttribute",
                "citiz": "3570300400000",
                "nameTH": "นาย#เดพ##เอชวีศูนย์หนึ่ง",
                "nameEN": "Mr.#DEV##HV01",
                "brith": "25220713",
                "gender": "1",
                "data": {
                    "attribute": "CONTOUR",
                    "ble_mac": "00:5F:BF:97:6C:84",
                    "value": {
                        "blood_glucose": 97,
                        "marker": "After Meal"
                    }
                }
            },
            "weight": {
                "from": "PI",
                "to": "CLOUD",
                "time": 1714819151,
                "mac": "e4:5f:01:ed:82:59",
                "type": "reportAttribute",
                "citiz": "3570300400000",
                "data": {
                    "attribute": "BodyScale_JUMPER",
                    "ble_mac": "A0:77:9E:1C:18:26",
                    "value": {
                        "weight": 76.3,
                        "Resistance": 598.5
                    }
                },
                "nameTH": "นาย#เดพ##เอชวีศูนย์หนึ่ง",
                "nameEN": "Mr.#DEV##HV01",
                "brith": "25220713",
                "gender": "1"
            },
            "body_temperature": {
                "from": "PI",
                "to": "CLOUD",
                "time": 1739360702,
                "mac": "e4:5f:01:ed:82:59",
                "type": "reportAttribute",
                "citiz": "3570300400000",
                "nameTH": "นาย#เดพ##เอชวีศูนย์หนึ่ง",
                "nameEN": "Mr.#DEV##HV01",
                "brith": "25220713",
                "gender": "1",
                "data": {
                    "attribute": "TEMO_Jumper",
                    "ble_mac": "FF:23:01:28:10:39",
                    "value": {
                        "mode": "Head",
                        "Temp": 36.88
                    }
                }
            },
            "spo2": {
                "from": "PI",
                "to": "CLOUD",
                "time": 1714819151,
                "mac": "e4:5f:01:ed:82:59",
                "type": "reportAttribute",
                "citiz": "3570300432844",
                "nameTH": "นาย#กิจกมน##ไมตรี",
                "nameEN": "Mr.#Kitkamon##Maitree",
                "brith": "25220713",
                "gender": "1",
                "data": {
                    "attribute": "Oximeter_JUMPER",
                    "ble_mac": "40:2E:71:4A:38:84",
                    "value": {
                        "pulse": 70,
                        "spo2": 97,
                        "pi": 70
                    }
                }
            }
        }
    
    def test_online_status_processing(self):
        """Test Qube-Vital online status processing"""
        print("\n=== Testing Qube-Vital Online Status Processing ===")
        
        try:
            payload = self.test_payloads["online_status"]
            
            # Test device status update
            mac_address = payload.get('mac')
            imei = payload.get('IMEI')
            
            success = self.device_status_service.update_device_status(
                device_id=mac_address,
                device_type="Qube-Vital",
                status_data={
                    "type": "HB_Msg",
                    "mac": mac_address,
                    "imei": imei,
                    "name": payload.get('name', ''),
                    "data": payload.get('data', {}),
                    "online_status": "online"
                }
            )
            
            if success:
                print(f"✅ Online status processing successful for MAC: {mac_address}")
                
                # Verify device status was stored
                device_status = self.device_status_service.get_device_status(mac_address)
                if device_status:
                    print(f"✅ Device status stored: {device_status.get('online_status')}")
                else:
                    print("❌ Device status not found")
            else:
                print("❌ Online status processing failed")
                
        except Exception as e:
            print(f"❌ Error testing online status: {e}")
    
    def test_medical_data_processing(self, data_type: str):
        """Test Qube-Vital medical data processing"""
        print(f"\n=== Testing Qube-Vital {data_type.replace('_', ' ').title()} Processing ===")
        
        try:
            payload = self.test_payloads[data_type]
            
            citiz = payload.get('citiz')
            attribute = payload.get('data', {}).get('attribute')
            value = payload.get('data', {}).get('value', {})
            device_mac = payload.get('mac')
            
            print(f"Processing {attribute} data for citizen ID: {citiz}")
            
            # Find or create patient
            patient = self.device_mapper.find_patient_by_citiz(citiz)
            
            if not patient:
                print(f"Creating unregistered patient for citizen ID: {citiz}")
                patient = self.device_mapper.create_unregistered_patient(
                    citiz=citiz,
                    name_th=payload.get('nameTH', ''),
                    name_en=payload.get('nameEN', ''),
                    birth_date=payload.get('brith', ''),
                    gender=payload.get('gender', '')
                )
                
                if not patient:
                    print(f"❌ Failed to create unregistered patient for citizen ID: {citiz}")
                    return False
            
            print(f"Patient ID: {patient['_id']}")
            
            # Process the medical data
            success = self.data_processor.process_qube_data(
                patient['_id'], 
                attribute, 
                value,
                device_mac
            )
            
            if success:
                print(f"✅ {data_type} processing successful")
                
                # Verify data was stored in patient document
                patient_doc = self.device_mapper.db.patients.find_one({"_id": patient['_id']})
                if patient_doc:
                    # Check for last data field based on data type
                    field_mapping = {
                        "blood_pressure": "last_blood_pressure",
                        "blood_glucose": "last_blood_sugar",
                        "weight": "last_weight",
                        "body_temperature": "last_body_temperature",
                        "spo2": "last_spo2"
                    }
                    
                    field_name = field_mapping.get(data_type)
                    if field_name and field_name in patient_doc:
                        print(f"✅ Last {data_type} data stored in patient document")
                    else:
                        print(f"⚠️  Last {data_type} data not found in patient document")
                
                # Verify device status was updated
                if device_mac:
                    device_status = self.device_status_service.get_device_status(device_mac)
                    if device_status:
                        print(f"✅ Device status updated for MAC: {device_mac}")
                    else:
                        print(f"⚠️  Device status not found for MAC: {device_mac}")
                
                return True
            else:
                print(f"❌ {data_type} processing failed")
                return False
                
        except Exception as e:
            print(f"❌ Error testing {data_type}: {e}")
            return False
    
    def run_all_tests(self):
        """Run all Qube-Vital payload tests"""
        print("🚀 Starting Qube-Vital MQTT Payload Processing Tests")
        print("=" * 60)
        
        # Test online status
        self.test_online_status_processing()
        
        # Test all medical data types
        medical_data_types = ["blood_pressure", "blood_glucose", "weight", "body_temperature", "spo2"]
        
        success_count = 0
        total_tests = len(medical_data_types)
        
        for data_type in medical_data_types:
            if self.test_medical_data_processing(data_type):
                success_count += 1
        
        print("\n" + "=" * 60)
        print(f"📊 Test Results: {success_count}/{total_tests} medical data types processed successfully")
        
        if success_count == total_tests:
            print("🎉 All Qube-Vital payload tests passed!")
        else:
            print(f"⚠️  {total_tests - success_count} tests failed")
        
        return success_count == total_tests
    
    def cleanup(self):
        """Clean up test data"""
        try:
            # Close database connections
            self.device_mapper.close()
            self.data_processor.close()
            self.device_status_service.close()
            print("🧹 Cleanup completed")
        except Exception as e:
            print(f"⚠️  Cleanup error: {e}")

def main():
    """Main test function"""
    tester = QubeVitalPayloadTester()
    
    try:
        success = tester.run_all_tests()
        return 0 if success else 1
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        return 1
    finally:
        tester.cleanup()

if __name__ == "__main__":
    exit(main()) 