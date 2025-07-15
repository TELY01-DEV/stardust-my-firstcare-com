#!/usr/bin/env python3
"""
MQTT Data Processing Test Script
Tests the complete MQTT payload processing workflow with debug logging
"""

import os
import sys
import json
import logging
from datetime import datetime
from typing import Dict, Any

# Add the services directory to path
sys.path.append('./services/mqtt-listeners/shared')

from device_mapper import DeviceMapper
from data_processor import DataProcessor

# Configure comprehensive logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('mqtt_processing_test.log')
    ]
)
logger = logging.getLogger(__name__)

class MQTTDataProcessingTester:
    """Test MQTT data processing workflow"""
    
    def __init__(self):
        # MongoDB Configuration
        self.mongodb_uri = os.getenv('MONGODB_URI', 'mongodb://localhost:27017')
        self.mongodb_database = os.getenv('MONGODB_DATABASE', 'AMY')
        
        # Initialize services
        self.device_mapper = DeviceMapper(self.mongodb_uri, self.mongodb_database)
        self.data_processor = DataProcessor(self.mongodb_uri, self.mongodb_database)
        
        logger.info("🧪 MQTT Data Processing Tester initialized")
    
    def test_ava4_blood_pressure_payload(self):
        """Test AVA4 blood pressure payload processing"""
        logger.info("=" * 60)
        logger.info("🧪 TESTING AVA4 BLOOD PRESSURE PAYLOAD")
        logger.info("=" * 60)
        
        # Sample AVA4 blood pressure payload
        payload = {
            "from": "BLE",
            "to": "CLOUD",
            "time": 1836942771,
            "deviceCode": "08:F9:E0:D1:F7:B4",
            "mac": "08:F9:E0:D1:F7:B4",
            "type": "reportAttribute",
            "device": "WBP BIOLIGHT",
            "data": {
                "attribute": "BP_BIOLIGTH",
                "mac": "08:F9:E0:D1:F7:B4",
                "value": {
                    "device_list": [{
                        "scan_time": 1836942771,
                        "ble_addr": "d616f9641622",
                        "bp_high": 137,
                        "bp_low": 95,
                        "PR": 74
                    }]
                }
            }
        }
        
        logger.info(f"📊 Testing AVA4 payload: {json.dumps(payload, indent=2)}")
        
        # Extract data
        device_mac = payload.get('mac')
        attribute = payload.get('data', {}).get('attribute')
        value = payload.get('data', {}).get('value', {})
        
        logger.info(f"🔍 Extracted - MAC: {device_mac}, Attribute: {attribute}")
        
        # Test patient lookup
        patient = self.device_mapper.find_patient_by_device_mac(device_mac, "blood_pressure")
        if not patient:
            logger.warning("⚠️ No patient found, testing with sample patient ID")
            # Use a sample patient ID for testing
            from bson import ObjectId
            patient = {"_id": ObjectId("507f1f77bcf86cd799439011")}
        
        if patient:
            logger.info(f"✅ Patient found: {patient.get('_id')}")
            
            # Test data processing
            success = self.data_processor.process_ava4_data(
                patient['_id'], 
                device_mac, 
                attribute, 
                value
            )
            
            if success:
                logger.info("✅ AVA4 blood pressure processing successful")
            else:
                logger.error("❌ AVA4 blood pressure processing failed")
        else:
            logger.error("❌ No patient found for testing")
    
    def test_kati_vital_signs_payload(self):
        """Test Kati Watch vital signs payload processing"""
        logger.info("=" * 60)
        logger.info("🧪 TESTING KATI WATCH VITAL SIGNS PAYLOAD")
        logger.info("=" * 60)
        
        # Sample Kati Watch vital signs payload
        payload = {
            "IMEI": "865067123456789",
            "heartRate": 72,
            "bloodPressure": {
                "bp_sys": 122,
                "bp_dia": 74
            },
            "bodyTemperature": 36.6,
            "spO2": 97,
            "signalGSM": 80,
            "battery": 67,
            "location": {
                "GPS": {"latitude": 22.5678, "longitude": 112.3456},
                "WiFi": "[{...}]",
                "LBS": {"MCC": "520", "MNC": "3", "LAC": "1815", "CID": "79474300"}
            },
            "timeStamps": "16/06/2025 12:30:45"
        }
        
        logger.info(f"📊 Testing Kati payload: {json.dumps(payload, indent=2)}")
        
        # Extract IMEI
        imei = payload.get('IMEI')
        topic = "iMEDE_watch/VitalSign"
        
        logger.info(f"🔍 Extracted - IMEI: {imei}, Topic: {topic}")
        
        # Test patient lookup
        patient = self.device_mapper.find_patient_by_kati_imei(imei)
        if not patient:
            logger.warning("⚠️ No patient found, testing with sample patient ID")
            # Use a sample patient ID for testing
            from bson import ObjectId
            patient = {"_id": ObjectId("507f1f77bcf86cd799439012")}
        
        if patient:
            logger.info(f"✅ Patient found: {patient.get('_id')}")
            
            # Test data processing
            success = self.data_processor.process_kati_data(
                patient['_id'], 
                topic, 
                payload
            )
            
            if success:
                logger.info("✅ Kati vital signs processing successful")
            else:
                logger.error("❌ Kati vital signs processing failed")
        else:
            logger.error("❌ No patient found for testing")
    
    def test_qube_vital_payload(self):
        """Test Qube-Vital payload processing"""
        logger.info("=" * 60)
        logger.info("🧪 TESTING QUBE-VITAL PAYLOAD")
        logger.info("=" * 60)
        
        # Sample Qube-Vital payload
        payload = {
            "from": "CM4_BLE_GW",
            "to": "CLOUD",
            "time": 1836942771,
            "mac": "AA:BB:CC:DD:EE:FF",
            "IMEI": "123456789012345",
            "type": "reportAttribute",
            "data": {
                "attribute": "WBP_JUMPER",
                "mac": "AA:BB:CC:DD:EE:FF",
                "value": {
                    "bp_high": 120,
                    "bp_low": 80,
                    "pr": 72
                }
            }
        }
        
        logger.info(f"📊 Testing Qube-Vital payload: {json.dumps(payload, indent=2)}")
        
        # Extract data
        attribute = payload.get('data', {}).get('attribute')
        value = payload.get('data', {}).get('value', {})
        
        logger.info(f"🔍 Extracted - Attribute: {attribute}")
        
        # For Qube-Vital, we need a patient (usually created from citizen ID)
        # Use a sample patient ID for testing
        from bson import ObjectId
        patient = {"_id": ObjectId("507f1f77bcf86cd799439013")}
        
        logger.info(f"✅ Using test patient: {patient.get('_id')}")
        
        # Test data processing
        success = self.data_processor.process_qube_data(
            patient['_id'], 
            attribute, 
            value
        )
        
        if success:
            logger.info("✅ Qube-Vital processing successful")
        else:
            logger.error("❌ Qube-Vital processing failed")
    
    def test_database_verification(self):
        """Verify data was stored correctly in database"""
        logger.info("=" * 60)
        logger.info("🧪 VERIFYING DATABASE STORAGE")
        logger.info("=" * 60)
        
        try:
            # Check recent blood pressure history
            recent_bp = list(self.data_processor.db.blood_pressure_histories.find().sort("timestamp", -1).limit(5))
            logger.info(f"📊 Recent blood pressure records: {len(recent_bp)}")
            for bp in recent_bp:
                logger.info(f"  - Patient: {bp.get('patient_id')}, Source: {bp.get('source')}, Data: {bp.get('data')}")
            
            # Check recent patients with last data
            recent_patients = list(self.data_processor.db.patients.find(
                {"last_blood_pressure": {"$exists": True}}
            ).sort("updated_at", -1).limit(5))
            logger.info(f"📊 Patients with last blood pressure: {len(recent_patients)}")
            for patient in recent_patients:
                logger.info(f"  - Patient: {patient.get('_id')}, Last BP: {patient.get('last_blood_pressure')}")
            
            # Check device mappings
            device_mappings = list(self.device_mapper.db.amy_devices.find().limit(5))
            logger.info(f"📊 Device mappings: {len(device_mappings)}")
            for device in device_mappings:
                logger.info(f"  - MAC: {device.get('mac_address')}, Type: {device.get('device_type')}, Patient: {device.get('patient_id')}")
            
        except Exception as e:
            logger.error(f"❌ Error verifying database: {e}")
    
    def run_all_tests(self):
        """Run all tests"""
        logger.info("🚀 Starting MQTT Data Processing Tests")
        logger.info(f"📅 Test started at: {datetime.utcnow()}")
        
        try:
            # Test AVA4 processing
            self.test_ava4_blood_pressure_payload()
            
            # Test Kati Watch processing
            self.test_kati_vital_signs_payload()
            
            # Test Qube-Vital processing
            self.test_qube_vital_payload()
            
            # Verify database storage
            self.test_database_verification()
            
            logger.info("✅ All tests completed successfully")
            
        except Exception as e:
            logger.error(f"❌ Test execution failed: {e}")
        finally:
            # Clean up
            self.device_mapper.close()
            self.data_processor.close()
            logger.info("🔌 Connections closed")

def main():
    """Main test execution"""
    tester = MQTTDataProcessingTester()
    tester.run_all_tests()

if __name__ == "__main__":
    main() 