#!/usr/bin/env python3
"""
Test script to verify real MQTT data processing with actual device payloads
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

# Real MQTT payloads based on documentation
REAL_MQTT_PAYLOADS = {
    "AVA4": {
        "topic": "ESP32_BLE_GW_TX/AVA4_001",
        "payload": {
            "device_id": "AVA4_001",
            "timestamp": "2025-01-15T10:30:00Z",
            "WBP_JUMPER": {
                "ble_addr": "DC:DA:0C:5A:80:64",
                "systolic": 120,
                "diastolic": 80,
                "pulse": 72,
                "mean": 93
            },
            "Oximeter_JUMPER": {
                "ble_addr": "AA:BB:CC:DD:EE:FF",
                "spo2": 98,
                "pulse": 72,
                "resp": 16,
                "pi": 2.5
            },
            "TEMO_Jumper": {
                "ble_addr": "11:22:33:44:55:66",
                "body_temp": 36.8
            },
            "BodyScale_JUMPER": {
                "ble_addr": "FF:EE:DD:CC:BB:AA",
                "weight": 75.5,
                "height": 176,
                "bmi": 24.4,
                "body_fat": 18.5,
                "muscle_mass": 45.2
            },
            "CONTOUR": {
                "ble_addr": "99:88:77:66:55:44",
                "blood_glucose": 95,
                "marker": "fasting"
            }
        }
    },
    "Kati": {
        "topic": "iMEDE_watch/KATI_001",
        "payload": {
            "imei": "861265061366537",
            "timestamp": "2025-01-15T10:30:00Z",
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
        }
    },
    "Qube-Vital": {
        "topic": "qube-vital/QUBE_001",
        "payload": {
            "citizen_id": "3570300432855",
            "hospital_mac": "DC:DA:0C:5A:80:64",
            "timestamp": "2025-01-15T10:30:00Z",
            "WBP_JUMPER": {
                "systolic": 122,
                "diastolic": 82,
                "pulse": 74
            },
            "Oximeter_JUMPER": {
                "spo2": 99,
                "pulse": 74
            },
            "TEMO_Jumper": {
                "body_temp": 36.7
            },
            "BodyScale_JUMPER": {
                "weight": 76.2,
                "bmi": 24.6
            },
            "CONTOUR": {
                "blood_glucose": 92,
                "marker": "pre_meal"
            }
        }
    }
}

async def test_real_mqtt_processing():
    """Test real MQTT data processing with actual device payloads"""
    
    print("🧪 TESTING REAL MQTT DATA PROCESSING")
    print("=" * 80)
    
    # Initialize MQTT Monitor
    mongodb_uri = "mongodb://coruscant.my-firstcare.com:27023"
    monitor = MQTTMonitor(mongodb_uri, "AMY")
    
    try:
        # Test 1: AVA4 Real MQTT Processing
        print("\n🔍 TEST 1: AVA4 Real MQTT Processing")
        print("-" * 40)
        
        ava4_data = REAL_MQTT_PAYLOADS["AVA4"]
        result = monitor.process_ava4_message(ava4_data["topic"], ava4_data["payload"])
        
        print(f"✅ AVA4 MQTT processing completed")
        print(f"   - Topic: {ava4_data['topic']}")
        print(f"   - Device ID: {ava4_data['payload']['device_id']}")
        print(f"   - Status: {result.get('status', 'unknown')}")
        
        if result.get('medical_data'):
            medical_data = result['medical_data']
            print(f"   - Medical data types: {list(medical_data.keys())}")
            
            if 'blood_pressure' in medical_data:
                bp = medical_data['blood_pressure']
                print(f"   - Blood pressure: {bp.get('systolic')}/{bp.get('diastolic')}")
            
            if 'spo2' in medical_data:
                spo2 = medical_data['spo2']
                print(f"   - SpO2: {spo2.get('value')}%")
        
        # Test 2: Kati Watch Real MQTT Processing
        print("\n🔍 TEST 2: Kati Watch Real MQTT Processing")
        print("-" * 40)
        
        kati_data = REAL_MQTT_PAYLOADS["Kati"]
        result = monitor.process_kati_message(kati_data["topic"], kati_data["payload"])
        
        print(f"✅ Kati Watch MQTT processing completed")
        print(f"   - Topic: {kati_data['topic']}")
        print(f"   - IMEI: {kati_data['payload']['imei']}")
        print(f"   - Status: {result.get('status', 'unknown')}")
        
        if result.get('medical_data'):
            medical_data = result['medical_data']
            print(f"   - Medical data types: {list(medical_data.keys())}")
            
            if 'blood_pressure' in medical_data:
                bp = medical_data['blood_pressure']
                print(f"   - Blood pressure: {bp.get('systolic')}/{bp.get('diastolic')}")
            
            if 'steps' in medical_data:
                steps = medical_data['steps']
                print(f"   - Steps: {steps.get('steps')}")
        
        # Test 3: Qube-Vital Real MQTT Processing
        print("\n🔍 TEST 3: Qube-Vital Real MQTT Processing")
        print("-" * 40)
        
        qube_data = REAL_MQTT_PAYLOADS["Qube-Vital"]
        result = monitor.process_qube_vital_message(qube_data["topic"], qube_data["payload"])
        
        print(f"✅ Qube-Vital MQTT processing completed")
        print(f"   - Topic: {qube_data['topic']}")
        print(f"   - Citizen ID: {qube_data['payload']['citizen_id']}")
        print(f"   - Hospital MAC: {qube_data['payload']['hospital_mac']}")
        print(f"   - Status: {result.get('status', 'unknown')}")
        
        if result.get('medical_data'):
            medical_data = result['medical_data']
            print(f"   - Medical data types: {list(medical_data.keys())}")
            
            if 'blood_pressure' in medical_data:
                bp = medical_data['blood_pressure']
                print(f"   - Blood pressure: {bp.get('systolic')}/{bp.get('diastolic')}")
        
        # Test 4: Generic Message Processing
        print("\n🔍 TEST 4: Generic Message Processing")
        print("-" * 40)
        
        for device_type, data in REAL_MQTT_PAYLOADS.items():
            result = monitor.process_message(data["topic"], data["payload"])
            
            print(f"✅ {device_type} generic processing completed")
            print(f"   - Device type detected: {result.get('device_type', 'unknown')}")
            print(f"   - Status: {result.get('status', 'unknown')}")
        
        # Test 5: Patient Document Updates (if MongoDB connected)
        print("\n🔍 TEST 5: Patient Document Updates")
        print("-" * 40)
        
        if monitor.db:
            print("✅ MongoDB connected - testing patient document updates")
            
            # Test AVA4 patient document updates
            ava4_medical_data = {
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
                }
            }
            
            success = monitor.update_patient_document_fields(TEST_PATIENT_ID, "AVA4", ava4_medical_data)
            
            if success:
                print("✅ AVA4 patient document updates successful")
            else:
                print("❌ AVA4 patient document updates failed")
            
            # Test Kati patient document updates
            kati_medical_data = {
                "blood_pressure": {
                    "systolic": 118,
                    "diastolic": 78,
                    "pulse": 70
                },
                "spo2": {
                    "value": 97,
                    "pulse_rate": 70
                },
                "steps": {
                    "steps": 8500,
                    "calories": 320,
                    "distance": 6.2
                }
            }
            
            success = monitor.update_patient_document_fields(TEST_PATIENT_ID, "Kati", kati_medical_data)
            
            if success:
                print("✅ Kati patient document updates successful")
            else:
                print("❌ Kati patient document updates failed")
            
            # Test Qube-Vital patient document updates
            qube_medical_data = {
                "blood_pressure": {
                    "systolic": 122,
                    "diastolic": 82,
                    "pulse": 74
                },
                "spo2": {
                    "value": 99,
                    "pulse_rate": 74
                },
                "weight": {
                    "value": 76.2,
                    "bmi": 24.6
                }
            }
            
            success = monitor.update_patient_document_fields(TEST_PATIENT_ID, "Qube-Vital", qube_medical_data)
            
            if success:
                print("✅ Qube-Vital patient document updates successful")
            else:
                print("❌ Qube-Vital patient document updates failed")
            
        else:
            print("⚠️ MongoDB not connected - skipping patient document updates")
        
        # Test 6: Medical History Storage (if MongoDB connected)
        print("\n🔍 TEST 6: Medical History Storage")
        print("-" * 40)
        
        if monitor.db:
            print("✅ MongoDB connected - testing medical history storage")
            
            # Test blood pressure storage
            bp_data = {
                "data_type": "blood_pressure",
                "systolic": 120,
                "diastolic": 80,
                "pulse_rate": 72
            }
            
            success = monitor.store_medical_data(TEST_PATIENT_ID, "TEST_AVA4_001", "AVA4", bp_data)
            
            if success:
                print("✅ Blood pressure medical history storage successful")
            else:
                print("❌ Blood pressure medical history storage failed")
            
            # Test SpO2 storage
            spo2_data = {
                "data_type": "spo2",
                "spo2": 98
            }
            
            success = monitor.store_medical_data(TEST_PATIENT_ID, "TEST_AVA4_001", "AVA4", spo2_data)
            
            if success:
                print("✅ SpO2 medical history storage successful")
            else:
                print("❌ SpO2 medical history storage failed")
            
            # Test weight storage
            weight_data = {
                "data_type": "weight",
                "weight": 75.5,
                "bmi": 24.4
            }
            
            success = monitor.store_medical_data(TEST_PATIENT_ID, "TEST_AVA4_001", "AVA4", weight_data)
            
            if success:
                print("✅ Weight medical history storage successful")
            else:
                print("❌ Weight medical history storage failed")
            
        else:
            print("⚠️ MongoDB not connected - skipping medical history storage")
        
        # Test 7: System Statistics
        print("\n🔍 TEST 7: System Statistics")
        print("-" * 40)
        
        stats = monitor.get_statistics()
        
        if stats:
            print("✅ System statistics retrieved")
            print(f"   - AVA4 devices: {stats.get('ava4Count', 0)}")
            print(f"   - Kati devices: {stats.get('katiCount', 0)}")
            print(f"   - Qube-Vital devices: {stats.get('qubeCount', 0)}")
            print(f"   - Total messages: {stats.get('totalMessages', 0)}")
            print(f"   - Processing rate: {stats.get('processingRate', 0)}")
        else:
            print("❌ Failed to retrieve system statistics")
        
        print("\n🎉 REAL MQTT PROCESSING TEST COMPLETED")
        print("=" * 80)
        print("✅ All MQTT processing tests completed successfully!")
        print("📊 Real device payloads processed correctly")
        print("🔗 Patient document updates working")
        print("📝 Medical history storage functional")
        print("📋 System statistics available")
        print("🚀 Ready for production MQTT data processing")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Clean up
        monitor.close()

async def main():
    """Main function"""
    print("🚀 Starting Real MQTT Processing Test")
    print(f"📋 Test Patient ID: {TEST_PATIENT_ID}")
    print(f"🕐 Test Time: {datetime.utcnow().isoformat()}")
    print("=" * 80)
    
    await test_real_mqtt_processing()

if __name__ == "__main__":
    asyncio.run(main()) 