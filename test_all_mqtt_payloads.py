#!/usr/bin/env python3
"""
Test All MQTT Payload Processing
Tests AVA4, Kati Watch, and Qube-Vital MQTT payloads based on documentation
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

class AllMQTTPayloadTester:
    """Test all MQTT payload processing based on documentation"""
    
    def __init__(self):
        # MongoDB Configuration
        self.mongodb_uri = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
        self.mongodb_database = os.getenv('MONGODB_DATABASE', 'AMY')
        
        # Initialize services
        self.device_mapper = DeviceMapper(self.mongodb_uri, self.mongodb_database)
        self.data_processor = DataProcessor(self.mongodb_uri, self.mongodb_database)
        self.device_status_service = DeviceStatusService(self.mongodb_uri, self.mongodb_database)
        
        # Test payloads based on documentation
        self.test_payloads = {
            # AVA4 MQTT Payloads (from ava4_mqtt_examples.md)
            "ava4_heartbeat": {
                "from": "ESP32_GW",
                "to": "CLOUD",
                "name": "AVA4-No.1",
                "time": 1743963911,
                "mac": "DC:DA:0C:5A:80:64",
                "IMEI": "868334037510868",
                "ICCID": "8966032240112716129",
                "type": "HB_Msg",
                "data": {
                    "msg": "Online"
                }
            },
            "ava4_online_trigger": {
                "from": "ESP32_S3_GW",
                "to": "CLOUD",
                "time": 1743932465,
                "mac": "DC:DA:0C:5A:FF:FF",
                "IMEI": "868334037510868",
                "ICCID": "8966032240112716129",
                "type": "reportMsg",
                "data": {
                    "msg": "Online"
                }
            },
            "ava4_blood_pressure": {
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
                        "device_list": [
                            {
                                "scan_time": 1836942771,
                                "ble_addr": "d616f9641622",
                                "bp_high": 137,
                                "bp_low": 95,
                                "PR": 74
                            }
                        ]
                    }
                }
            },
            "ava4_oximeter": {
                "from": "BLE",
                "to": "CLOUD",
                "time": 1836946958,
                "deviceCode": "DC:DA:0C:5A:80:44",
                "mac": "DC:DA:0C:5A:80:44",
                "type": "reportAttribute",
                "device": "Oximeter Jumper",
                "data": {
                    "attribute": "Oximeter JUMPER",
                    "mac": "DC:DA:0C:5A:80:44",
                    "value": {
                        "device_list": [
                            {
                                "scan_time": 1836946958,
                                "ble_addr": "ff23041920b4",
                                "pulse": 72,
                                "spo2": 96,
                                "pi": 43
                            }
                        ]
                    }
                }
            },
            "ava4_glucometer_contour": {
                "from": "BLE",
                "to": "CLOUD",
                "time": 1841875953,
                "deviceCode": "DC:DA:0C:5A:80:88",
                "mac": "DC:DA:0C:5A:80:88",
                "type": "reportAttribute",
                "device": "SUGA Contour",
                "data": {
                    "attribute": "Contour_Elite",
                    "mac": "DC:DA:0C:5A:80:88",
                    "value": {
                        "device_list": [{
                            "scan_time": 1841875953,
                            "ble_addr": "806fb0750c88",
                            "scan_rssi": -66,
                            "blood_glucose": "108",
                            "marker": "After Meal"
                        }]
                    }
                }
            },
            "ava4_glucometer_accuchek": {
                "from": "BLE",
                "to": "CLOUD",
                "time": 1841875953,
                "deviceCode": "80:65:99:A1:DC:77",
                "mac": "80:65:99:A1:DC:77",
                "type": "reportAttribute",
                "device": "SUGA AccuCheck",
                "data": {
                    "attribute": "AccuChek_Instant",
                    "mac": "80:65:99:A1:DC:77",
                    "value": {
                        "device_list": [{
                            "scan_time": 1841875953,
                            "ble_addr": "60e85b7aab77",
                            "scan_rssi": -66,
                            "blood_glucose": "111",
                            "marker": "After Meal"
                        }]
                    }
                }
            },
            "ava4_thermometer": {
                "from": "BLE",
                "to": "CLOUD",
                "time": 1841932446,
                "deviceCode": "DC:DA:0C:5A:80:64",
                "mac": "DC:DA:0C:5A:80:64",
                "type": "reportAttribute",
                "device": "TEMO Jumper",
                "data": {
                    "attribute": "IR_TEMO_JUMPER",
                    "mac": "DC:DA:0C:5A:80:64",
                    "value": {
                        "device_list": [{
                            "scan_time": 1841932446,
                            "ble_addr": "ff2301283119",
                            "temp": 36.43000031,
                            "mode": "Head"
                        }]
                    }
                }
            },
            "ava4_weight_scale": {
                "from": "BLE",
                "to": "CLOUD",
                "time": 1773337306,
                "deviceCode": "DC:DA:0C:5A:80:33",
                "mac": "DC:DA:0C:5A:80:33",
                "type": "reportAttribute",
                "device": "JUMPER SCALE",
                "data": {
                    "attribute": "BodyScale_JUMPER",
                    "mac": "DC:DA:0C:5A:80:33",
                    "value": {
                        "device_list": [{
                            "scan_time": 1773337306,
                            "ble_addr": "A0779E1C14D8",
                            "weight": 79.30000305,
                            "resistance": 605.9000244
                        }]
                    }
                }
            },
            "ava4_uric_acid": {
                "from": "BLE",
                "to": "CLOUD",
                "time": 1841875953,
                "deviceCode": "34:20:03:9a:13:22",
                "mac": "34:20:03:9a:13:22",
                "type": "reportAttribute",
                "device": "Uric REF_UA",
                "data": {
                    "attribute": "MGSS_REF_UA",
                    "mac": "34:20:03:9a:13:22",
                    "value": {
                        "device_list": [{
                            "scan_time": 1841875953,
                            "ble_addr": "60e85b7aab77",
                            "scan_rssi": -66,
                            "uric_acid": "517.5"
                        }]
                    }
                }
            },
            "ava4_cholesterol": {
                "from": "BLE",
                "to": "CLOUD",
                "time": 1841875953,
                "deviceCode": "34:20:03:9a:13:11",
                "mac": "34:20:03:9a:13:11",
                "type": "reportAttribute",
                "device": "Cholesterol REF_CHOL",
                "data": {
                    "attribute": "MGSS_REF_CHOL",
                    "mac": "34:20:03:9a:13:11",
                    "value": {
                        "device_list": [{
                            "scan_time": 1841875953,
                            "ble_addr": "0035FF226907",
                            "scan_rssi": -66,
                            "cholesterol": "4.3"
                        }]
                    }
                }
            },
            
            # Kati Watch MQTT Payloads (from KATI_WATCH_MQTT_PAYLOAD.md)
            "kati_heartbeat": {
                "IMEI": "865067123456789",
                "signalGSM": 80,
                "battery": 67,
                "satellites": 4,
                "workingMode": 2,
                "timeStamps": "16/06/2025 12:30:45",
                "step": 999
            },
            "kati_vital_signs": {
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
                    "WiFi": "[{'SSID':'WiFi1','MAC':'aa-bb-cc-dd-ee-ff','RSSI':'87'}]",
                    "LBS": {"MCC": "520", "MNC": "3", "LAC": "1815", "CID": "79474300"}
                },
                "timeStamps": "16/06/2025 12:30:45"
            },
            "kati_batch_vital_signs": {
                "IMEI": "865067123456789",
                "location": {
                    "GPS": {"latitude": 22.5678, "longitude": 112.3456},
                    "WiFi": "[{'SSID':'WiFi1','MAC':'aa-bb-cc-dd-ee-ff','RSSI':'87'}]",
                    "LBS": {"MCC": "520", "MNC": "3", "LAC": "1815", "CID": "79474300"}
                },
                "timeStamps": "16/06/2025 12:30:45",
                "num_datas": 12,
                "data": [
                    {
                        "timestamp": 1738331256,
                        "heartRate": 84,
                        "bloodPressure": {"bp_sys": 119, "bp_dia": 73},
                        "spO2": 98,
                        "bodyTemperature": 36.9
                    }
                ]
            },
            "kati_location": {
                "IMEI": "865067123456789",
                "location": {
                    "GPS": {
                        "latitude": 22.5678,
                        "longitude": 112.3456,
                        "speed": 0.0,
                        "header": 180.0
                    },
                    "WiFi": "[{'SSID':'WiFi1','MAC':'aa-bb-cc-dd-ee-ff','RSSI':'87'}]",
                    "LBS": {
                        "MCC": "520",
                        "MNC": "3", 
                        "LAC": "1815",
                        "CID": "79474300",
                        "SetBase": "[{...}]"
                    }
                }
            },
            "kati_sleep_data": {
                "IMEI": "865067123456789",
                "sleep": {
                    "timeStamps": "16/06/2025 01:00:00",
                    "time": "2200@0700",
                    "data": "0000000111110000010011111110011111111111110000000002200000001111111112111100111001111111211111111222111111111110110111111110110111111011112201110",
                    "num": 145
                }
            },
            "kati_sos": {
                "status": "SOS",
                "location": {
                    "GPS": {"latitude": 22.5678, "longitude": 112.3456},
                    "WiFi": "[{'SSID':'WiFi1','MAC':'aa-bb-cc-dd-ee-ff','RSSI':'87'}]",
                    "LBS": {"MCC": "520", "MNC": "3", "LAC": "1815", "CID": "79474300"}
                },
                "IMEI": "865067123456789"
            },
            "kati_fall_detection": {
                "status": "FALL DOWN",
                "location": {
                    "GPS": {"latitude": 22.5678, "longitude": 112.3456},
                    "WiFi": "[{'SSID':'WiFi1','MAC':'aa-bb-cc-dd-ee-ff','RSSI':'87'}]",
                    "LBS": {"MCC": "520", "MNC": "3", "LAC": "1815", "CID": "79474300"}
                },
                "IMEI": "865067123456789"
            },
            "kati_online_trigger": {
                "IMEI": "865067123456789",
                "status": "online"
            },
            
            # Qube-Vital MQTT Payloads (from Qube-Vital_MQTT_PAYLOAD.md)
            "qube_online_status": {
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
            "qube_blood_pressure": {
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
            "qube_blood_glucose": {
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
            "qube_weight": {
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
            "qube_body_temperature": {
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
            "qube_spo2": {
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
    
    def test_ava4_payloads(self):
        """Test AVA4 MQTT payload processing"""
        print("\n" + "="*60)
        print("🔹 TESTING AVA4 MQTT PAYLOADS")
        print("="*60)
        
        test_cases = [
            ("ava4_heartbeat", "Heartbeat"),
            ("ava4_online_trigger", "Online Trigger"),
            ("ava4_blood_pressure", "Blood Pressure"),
            ("ava4_oximeter", "Oximeter"),
            ("ava4_glucometer_contour", "Glucometer Contour"),
            ("ava4_glucometer_accuchek", "Glucometer AccuChek"),
            ("ava4_thermometer", "Thermometer"),
            ("ava4_weight_scale", "Weight Scale"),
            ("ava4_uric_acid", "Uric Acid"),
            ("ava4_cholesterol", "Cholesterol")
        ]
        
        success_count = 0
        for payload_key, description in test_cases:
            print(f"\n📡 Testing AVA4 {description}...")
            if self._test_ava4_payload(payload_key):
                success_count += 1
                print(f"✅ AVA4 {description} - PASSED")
            else:
                print(f"❌ AVA4 {description} - FAILED")
        
        print(f"\n📊 AVA4 Results: {success_count}/{len(test_cases)} passed")
        return success_count == len(test_cases)
    
    def test_kati_payloads(self):
        """Test Kati Watch MQTT payload processing"""
        print("\n" + "="*60)
        print("🔹 TESTING KATI WATCH MQTT PAYLOADS")
        print("="*60)
        
        test_cases = [
            ("kati_heartbeat", "Heartbeat"),
            ("kati_vital_signs", "Vital Signs"),
            ("kati_batch_vital_signs", "Batch Vital Signs"),
            ("kati_location", "Location"),
            ("kati_sleep_data", "Sleep Data"),
            ("kati_sos", "SOS Alert"),
            ("kati_fall_detection", "Fall Detection"),
            ("kati_online_trigger", "Online Trigger")
        ]
        
        success_count = 0
        for payload_key, description in test_cases:
            print(f"\n📡 Testing Kati {description}...")
            if self._test_kati_payload(payload_key):
                success_count += 1
                print(f"✅ Kati {description} - PASSED")
            else:
                print(f"❌ Kati {description} - FAILED")
        
        print(f"\n📊 Kati Results: {success_count}/{len(test_cases)} passed")
        return success_count == len(test_cases)
    
    def test_qube_payloads(self):
        """Test Qube-Vital MQTT payload processing"""
        print("\n" + "="*60)
        print("🔹 TESTING QUBE-VITAL MQTT PAYLOADS")
        print("="*60)
        
        test_cases = [
            ("qube_online_status", "Online Status"),
            ("qube_blood_pressure", "Blood Pressure"),
            ("qube_blood_glucose", "Blood Glucose"),
            ("qube_weight", "Weight"),
            ("qube_body_temperature", "Body Temperature"),
            ("qube_spo2", "SpO2")
        ]
        
        success_count = 0
        for payload_key, description in test_cases:
            print(f"\n📡 Testing Qube-Vital {description}...")
            if self._test_qube_payload(payload_key):
                success_count += 1
                print(f"✅ Qube-Vital {description} - PASSED")
            else:
                print(f"❌ Qube-Vital {description} - FAILED")
        
        print(f"\n📊 Qube-Vital Results: {success_count}/{len(test_cases)} passed")
        return success_count == len(test_cases)
    
    def _test_ava4_payload(self, payload_key: str) -> bool:
        """Test individual AVA4 payload"""
        try:
            payload = self.test_payloads[payload_key]
            
            if payload.get('type') == 'HB_Msg':
                # Test heartbeat processing
                mac_address = payload.get('mac')
                success = self.device_status_service.update_device_status(
                    device_id=mac_address,
                    device_type="AVA4",
                    status_data={
                        "type": "HB_Msg",
                        "mac": mac_address,
                        "imei": payload.get('IMEI'),
                        "name": payload.get('name', ''),
                        "data": payload.get('data', {}),
                        "online_status": "online"
                    }
                )
                return success
            elif payload.get('type') == 'reportAttribute':
                # Test medical data processing
                device_mac = payload.get('mac')
                attribute = payload.get('data', {}).get('attribute')
                value = payload.get('data', {}).get('value', {})
                
                # Create test patient
                patient = self._create_test_patient("AVA4_TEST")
                
                success = self.data_processor.process_ava4_data(
                    patient['_id'],
                    device_mac,
                    attribute,
                    value
                )
                return success
            else:
                print(f"Unknown AVA4 payload type: {payload.get('type')}")
                return False
                
        except Exception as e:
            print(f"Error testing AVA4 payload {payload_key}: {e}")
            return False
    
    def _test_kati_payload(self, payload_key: str) -> bool:
        """Test individual Kati payload"""
        try:
            payload = self.test_payloads[payload_key]
            
            # Create test patient
            patient = self._create_test_patient("KATI_TEST")
            
            # Determine topic based on payload type
            topic_mapping = {
                "kati_heartbeat": "iMEDE_watch/hb",
                "kati_vital_signs": "iMEDE_watch/VitalSign",
                "kati_batch_vital_signs": "iMEDE_watch/AP55",
                "kati_location": "iMEDE_watch/location",
                "kati_sleep_data": "iMEDE_watch/sleepdata",
                "kati_sos": "iMEDE_watch/sos",
                "kati_fall_detection": "iMEDE_watch/fallDown",
                "kati_online_trigger": "iMEDE_watch/onlineTrigger"
            }
            
            topic = topic_mapping.get(payload_key, "iMEDE_watch/test")
            
            success = self.data_processor.process_kati_data(
                patient['_id'],
                topic,
                payload
            )
            return success
                
        except Exception as e:
            print(f"Error testing Kati payload {payload_key}: {e}")
            return False
    
    def _test_qube_payload(self, payload_key: str) -> bool:
        """Test individual Qube-Vital payload"""
        try:
            payload = self.test_payloads[payload_key]
            
            if payload.get('type') == 'HB_Msg':
                # Test heartbeat processing
                mac_address = payload.get('mac')
                success = self.device_status_service.update_device_status(
                    device_id=mac_address,
                    device_type="Qube-Vital",
                    status_data={
                        "type": "HB_Msg",
                        "mac": mac_address,
                        "imei": payload.get('IMEI'),
                        "name": payload.get('name', ''),
                        "data": payload.get('data', {}),
                        "online_status": "online"
                    }
                )
                return success
            elif payload.get('type') == 'reportAttribute':
                # Test medical data processing
                citiz = payload.get('citiz')
                attribute = payload.get('data', {}).get('attribute')
                value = payload.get('data', {}).get('value', {})
                device_mac = payload.get('mac')
                
                # Find or create patient by citizen ID
                patient = self.device_mapper.find_patient_by_citiz(citiz)
                if not patient:
                    patient = self.device_mapper.create_unregistered_patient(
                        citiz=citiz,
                        name_th=payload.get('nameTH', ''),
                        name_en=payload.get('nameEN', ''),
                        birth_date=payload.get('brith', ''),
                        gender=payload.get('gender', '')
                    )
                
                if patient:
                    success = self.data_processor.process_qube_data(
                        patient['_id'],
                        attribute,
                        value,
                        device_mac
                    )
                    return success
                else:
                    print(f"Failed to create/find patient for citizen ID: {citiz}")
                    return False
            else:
                print(f"Unknown Qube-Vital payload type: {payload.get('type')}")
                return False
                
        except Exception as e:
            print(f"Error testing Qube-Vital payload {payload_key}: {e}")
            return False
    
    def _create_test_patient(self, device_type: str):
        """Create a test patient for processing"""
        try:
            test_citiz = f"TEST_{device_type}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            patient = self.device_mapper.create_unregistered_patient(
                citiz=test_citiz,
                name_th=f"Test Patient {device_type}",
                name_en=f"Test Patient {device_type}",
                birth_date="19900101",
                gender="1"
            )
            return patient
        except Exception as e:
            print(f"Error creating test patient: {e}")
            return None
    
    def run_all_tests(self):
        """Run all MQTT payload tests"""
        print("🚀 Starting All MQTT Payload Processing Tests")
        print("Based on AVA4, Kati Watch, and Qube-Vital Documentation")
        print("=" * 80)
        
        # Test all device types
        ava4_success = self.test_ava4_payloads()
        kati_success = self.test_kati_payloads()
        qube_success = self.test_qube_payloads()
        
        # Summary
        print("\n" + "=" * 80)
        print("📊 FINAL TEST RESULTS")
        print("=" * 80)
        print(f"🔹 AVA4: {'✅ PASSED' if ava4_success else '❌ FAILED'}")
        print(f"🔹 Kati Watch: {'✅ PASSED' if kati_success else '❌ FAILED'}")
        print(f"🔹 Qube-Vital: {'✅ PASSED' if qube_success else '❌ FAILED'}")
        
        total_success = sum([ava4_success, kati_success, qube_success])
        total_devices = 3
        
        print(f"\n🎯 Overall: {total_success}/{total_devices} device types passed")
        
        if total_success == total_devices:
            print("🎉 All MQTT payload processing tests passed!")
        else:
            print(f"⚠️  {total_devices - total_success} device types failed")
        
        return total_success == total_devices
    
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
    tester = AllMQTTPayloadTester()
    
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