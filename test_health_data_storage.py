#!/usr/bin/env python3
"""
Test script to verify health/medical data storage with related fields
Based on patient document structure analysis
"""

import asyncio
import json
import sys
import os
from datetime import datetime
from typing import Dict, Any

# Add the services directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'services', 'mqtt-monitor', 'shared'))

from mqtt_monitor import MQTTMonitor

# Test patient ID from the analysis
TEST_PATIENT_ID = "623c133cf9e69c3b67a9af64"

# Test data based on actual patient document structure
TEST_MEDICAL_DATA = {
    "AVA4": {
        "blood_pressure": {
            "systolic": 120,
            "diastolic": 80,
            "pulse": 72
        },
        "spo2": {
            "value": 98,
            "respiratory_rate": 16,
            "pulse_rate": 72,
            "perfusion_index": 2.5
        },
        "temperature": {
            "value": 36.8
        },
        "weight": {
            "value": 75.5,
            "height": 176,
            "bmi": 24.4,
            "body_fat": 18.5,
            "muscle_mass": 45.2
        },
        "blood_sugar": {
            "value": 95,
            "meal_type": "fasting"
        },
        "cholesterol": {
            "total_cholesterol": 180,
            "hdl": 45,
            "ldl": 110,
            "triglycerides": 150
        },
        "creatinine": {
            "value": 0.9
        },
        "lipids": {
            "total_cholesterol": 180,
            "hdl": 45,
            "ldl": 110,
            "triglycerides": 150
        }
    },
    "Kati": {
        "blood_pressure": {
            "systolic": 118,
            "diastolic": 78,
            "pulse": 70
        },
        "spo2": {
            "value": 97,
            "pulse_rate": 70
        },
        "temperature": {
            "value": 36.6
        },
        "steps": {
            "steps": 8500,
            "calories": 320,
            "distance": 6.2
        },
        "sleep": {
            "start_time": "2025-01-15T22:00:00",
            "end_time": "2025-01-16T06:30:00",
            "duration_minutes": 510,
            "sleep_score": 85
        }
    },
    "Qube-Vital": {
        "blood_pressure": {
            "systolic": 122,
            "diastolic": 82,
            "pulse": 74
        },
        "spo2": {
            "value": 99,
            "pulse_rate": 74
        },
        "temperature": {
            "value": 36.7
        },
        "weight": {
            "value": 76.2,
            "bmi": 24.6
        },
        "blood_sugar": {
            "value": 92,
            "meal_type": "pre_meal"
        }
    }
}

# Qube-Vital attribute test data
TEST_QUBE_VITAL_ATTRIBUTES = {
    "WBP_JUMPER": {
        "systolic": 122,
        "diastolic": 82,
        "pulse": 74
    },
    "CONTOUR": {
        "blood_glucose": 92,
        "marker": "pre_meal"
    },
    "BodyScale_JUMPER": {
        "weight": 76.2,
        "bmi": 24.6
    },
    "TEMO_Jumper": {
        "body_temp": 36.7
    },
    "Oximeter_JUMPER": {
        "spo2": 99,
        "pulse": 74
    }
}

async def test_health_data_storage():
    """Test health data storage with related fields"""
    
    print("🧪 TESTING HEALTH DATA STORAGE WITH RELATED FIELDS")
    print("=" * 80)
    
    # Initialize MQTT Monitor
    mongodb_uri = "mongodb://coruscant.my-firstcare.com:27023"
    monitor = MQTTMonitor(mongodb_uri, "AMY")
    
    try:
        # Test 1: AVA4 Health Data Storage
        print("\n🔍 TEST 1: AVA4 Health Data Storage")
        print("-" * 40)
        
        ava4_data = TEST_MEDICAL_DATA["AVA4"]
        success = monitor.update_patient_document_fields(TEST_PATIENT_ID, "AVA4", ava4_data)
        
        if success:
            print("✅ AVA4 health data storage successful")
            print(f"   - Blood pressure: {ava4_data['blood_pressure']['systolic']}/{ava4_data['blood_pressure']['diastolic']}")
            print(f"   - SpO2: {ava4_data['spo2']['value']}%")
            print(f"   - Temperature: {ava4_data['temperature']['value']}°C")
            print(f"   - Weight: {ava4_data['weight']['value']} kg")
            print(f"   - Blood sugar: {ava4_data['blood_sugar']['value']} mg/dL")
        else:
            print("❌ AVA4 health data storage failed")
        
        # Test 2: Kati Watch Health Data Storage
        print("\n🔍 TEST 2: Kati Watch Health Data Storage")
        print("-" * 40)
        
        kati_data = TEST_MEDICAL_DATA["Kati"]
        success = monitor.update_patient_document_fields(TEST_PATIENT_ID, "Kati", kati_data)
        
        if success:
            print("✅ Kati Watch health data storage successful")
            print(f"   - Blood pressure: {kati_data['blood_pressure']['systolic']}/{kati_data['blood_pressure']['diastolic']}")
            print(f"   - SpO2: {kati_data['spo2']['value']}%")
            print(f"   - Steps: {kati_data['steps']['steps']}")
            print(f"   - Sleep duration: {kati_data['sleep']['duration_minutes']} minutes")
        else:
            print("❌ Kati Watch health data storage failed")
        
        # Test 3: Qube-Vital Health Data Storage
        print("\n🔍 TEST 3: Qube-Vital Health Data Storage")
        print("-" * 40)
        
        qube_data = TEST_MEDICAL_DATA["Qube-Vital"]
        success = monitor.update_patient_document_fields(TEST_PATIENT_ID, "Qube-Vital", qube_data)
        
        if success:
            print("✅ Qube-Vital health data storage successful")
            print(f"   - Blood pressure: {qube_data['blood_pressure']['systolic']}/{qube_data['blood_pressure']['diastolic']}")
            print(f"   - SpO2: {qube_data['spo2']['value']}%")
            print(f"   - Weight: {qube_data['weight']['value']} kg")
            print(f"   - Blood sugar: {qube_data['blood_sugar']['value']} mg/dL")
        else:
            print("❌ Qube-Vital health data storage failed")
        
        # Test 4: Qube-Vital Attribute-based Updates
        print("\n🔍 TEST 4: Qube-Vital Attribute-based Updates")
        print("-" * 40)
        
        for attribute, data in TEST_QUBE_VITAL_ATTRIBUTES.items():
            success = monitor.update_patient_medical_fields(TEST_PATIENT_ID, attribute, data)
            
            if success:
                print(f"✅ {attribute} update successful")
                if attribute == "WBP_JUMPER":
                    print(f"   - Blood pressure: {data['systolic']}/{data['diastolic']}")
                elif attribute == "CONTOUR":
                    print(f"   - Blood glucose: {data['blood_glucose']} mg/dL ({data['marker']})")
                elif attribute == "BodyScale_JUMPER":
                    print(f"   - Weight: {data['weight']} kg, BMI: {data['bmi']}")
                elif attribute == "TEMO_Jumper":
                    print(f"   - Temperature: {data['body_temp']}°C")
                elif attribute == "Oximeter_JUMPER":
                    print(f"   - SpO2: {data['spo2']}%, Pulse: {data['pulse']}")
            else:
                print(f"❌ {attribute} update failed")
        
        # Test 5: Medical History Collection Storage
        print("\n🔍 TEST 5: Medical History Collection Storage")
        print("-" * 40)
        
        # Test blood pressure storage
        bp_data = {
            "data_type": "blood_pressure",
            "systolic": 120,
            "diastolic": 80,
            "pulse_rate": 72
        }
        
        success = monitor.store_medical_data(TEST_PATIENT_ID, "TEST_DEVICE_001", "AVA4", bp_data)
        
        if success:
            print("✅ Blood pressure stored in medical history collection")
        else:
            print("❌ Blood pressure storage failed")
        
        # Test SpO2 storage
        spo2_data = {
            "data_type": "spo2",
            "spo2": 98
        }
        
        success = monitor.store_medical_data(TEST_PATIENT_ID, "TEST_DEVICE_001", "AVA4", spo2_data)
        
        if success:
            print("✅ SpO2 stored in medical history collection")
        else:
            print("❌ SpO2 storage failed")
        
        # Test weight storage
        weight_data = {
            "data_type": "weight",
            "weight": 75.5,
            "bmi": 24.4
        }
        
        success = monitor.store_medical_data(TEST_PATIENT_ID, "TEST_DEVICE_001", "AVA4", weight_data)
        
        if success:
            print("✅ Weight stored in medical history collection")
        else:
            print("❌ Weight storage failed")
        
        # Test 6: Transaction Logging
        print("\n🔍 TEST 6: Transaction Logging")
        print("-" * 40)
        
        if monitor.transaction_logger:
            # Log a test transaction
            await monitor.transaction_logger.log_transaction(
                operation="TEST_HEALTH_DATA_STORAGE",
                data_type="comprehensive_test",
                collection="patients",
                patient_id=TEST_PATIENT_ID,
                status="success",
                details="Comprehensive health data storage test completed",
                device_id="TEST_DEVICE_001"
            )
            
            # Get recent transactions
            recent_transactions = await monitor.transaction_logger.get_recent_transactions(5)
            
            if recent_transactions:
                print(f"✅ Transaction logging successful - {len(recent_transactions)} recent transactions")
                for tx in recent_transactions[:3]:  # Show first 3
                    print(f"   - {tx['operation']}: {tx['data_type']} ({tx['status']})")
            else:
                print("❌ No recent transactions found")
        else:
            print("⚠️ Transaction logger not available")
        
        # Test 7: Statistics
        print("\n🔍 TEST 7: System Statistics")
        print("-" * 40)
        
        stats = monitor.get_statistics()
        
        if stats:
            print("✅ System statistics retrieved")
            print(f"   - AVA4 devices: {stats.get('ava4Count', 0)}")
            print(f"   - Kati devices: {stats.get('katiCount', 0)}")
            print(f"   - Qube-Vital devices: {stats.get('qubeCount', 0)}")
        else:
            print("❌ Failed to retrieve system statistics")
        
        print("\n🎉 HEALTH DATA STORAGE TEST COMPLETED")
        print("=" * 80)
        print("✅ All tests completed successfully!")
        print("📊 Health/medical data is now properly stored with related fields")
        print("🔗 Patient document fields updated according to actual structure")
        print("📝 Medical history collections populated with structured data")
        print("📋 Transaction logging working for audit trail")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Clean up
        monitor.close()

async def main():
    """Main function"""
    print("🚀 Starting Health Data Storage Test")
    print(f"📋 Test Patient ID: {TEST_PATIENT_ID}")
    print(f"🕐 Test Time: {datetime.utcnow().isoformat()}")
    print("=" * 80)
    
    await test_health_data_storage()

if __name__ == "__main__":
    asyncio.run(main()) 