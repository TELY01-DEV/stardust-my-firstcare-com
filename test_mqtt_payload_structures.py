#!/usr/bin/env python3
"""
Test MQTT Payload Structures
Validates payload structures from AVA4, Kati Watch, and Qube-Vital documentation
"""

import json
from typing import Dict, Any, List

class MQTTPayloadStructureValidator:
    """Validate MQTT payload structures from documentation"""
    
    def __init__(self):
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
    
    def validate_json_structure(self, payload: Dict[str, Any]) -> bool:
        """Validate JSON structure can be serialized/deserialized"""
        try:
            # Test JSON serialization
            json_str = json.dumps(payload, ensure_ascii=False, indent=2)
            # Test JSON deserialization
            parsed = json.loads(json_str)
            return True
        except Exception as e:
            print(f"❌ JSON validation failed: {e}")
            return False
    
    def validate_ava4_payloads(self):
        """Validate AVA4 payload structures"""
        print("\n" + "="*60)
        print("🔹 VALIDATING AVA4 MQTT PAYLOAD STRUCTURES")
        print("="*60)
        
        ava4_payloads = {k: v for k, v in self.test_payloads.items() if k.startswith('ava4_')}
        
        success_count = 0
        total_count = len(ava4_payloads)
        
        for payload_name, payload in ava4_payloads.items():
            print(f"\n📡 Validating {payload_name}...")
            
            # Check required fields
            required_fields = ["from", "to", "time", "mac", "type"]
            missing_fields = [field for field in required_fields if field not in payload]
            
            if missing_fields:
                print(f"❌ Missing required fields: {missing_fields}")
                continue
            
            # Validate JSON structure
            if not self.validate_json_structure(payload):
                continue
            
            # Check specific payload types
            if payload.get('type') == 'HB_Msg':
                if 'data' not in payload or 'msg' not in payload.get('data', {}):
                    print("❌ HB_Msg missing data.msg field")
                    continue
            elif payload.get('type') == 'reportAttribute':
                if 'data' not in payload or 'attribute' not in payload.get('data', {}):
                    print("❌ reportAttribute missing data.attribute field")
                    continue
            
            print(f"✅ {payload_name} - Valid structure")
            success_count += 1
        
        print(f"\n📊 AVA4 Results: {success_count}/{total_count} valid payloads")
        return success_count == total_count
    
    def validate_kati_payloads(self):
        """Validate Kati Watch payload structures"""
        print("\n" + "="*60)
        print("🔹 VALIDATING KATI WATCH MQTT PAYLOAD STRUCTURES")
        print("="*60)
        
        kati_payloads = {k: v for k, v in self.test_payloads.items() if k.startswith('kati_')}
        
        success_count = 0
        total_count = len(kati_payloads)
        
        for payload_name, payload in kati_payloads.items():
            print(f"\n📡 Validating {payload_name}...")
            
            # Check required IMEI field
            if 'IMEI' not in payload:
                print("❌ Missing required IMEI field")
                continue
            
            # Validate JSON structure
            if not self.validate_json_structure(payload):
                continue
            
            # Check specific payload types
            if payload_name == 'kati_heartbeat':
                required_fields = ['signalGSM', 'battery', 'timeStamps', 'step']
            elif payload_name == 'kati_vital_signs':
                required_fields = ['heartRate', 'bloodPressure', 'bodyTemperature', 'spO2', 'timeStamps']
            elif payload_name == 'kati_batch_vital_signs':
                required_fields = ['location', 'timeStamps', 'num_datas', 'data']
            elif payload_name == 'kati_location':
                required_fields = ['location']
            elif payload_name == 'kati_sleep_data':
                required_fields = ['sleep']
            elif payload_name in ['kati_sos', 'kati_fall_detection']:
                required_fields = ['status', 'location']
            elif payload_name == 'kati_online_trigger':
                required_fields = ['status']
            else:
                required_fields = []
            
            missing_fields = [field for field in required_fields if field not in payload]
            if missing_fields:
                print(f"❌ Missing required fields: {missing_fields}")
                continue
            
            print(f"✅ {payload_name} - Valid structure")
            success_count += 1
        
        print(f"\n📊 Kati Results: {success_count}/{total_count} valid payloads")
        return success_count == total_count
    
    def validate_qube_payloads(self):
        """Validate Qube-Vital payload structures"""
        print("\n" + "="*60)
        print("🔹 VALIDATING QUBE-VITAL MQTT PAYLOAD STRUCTURES")
        print("="*60)
        
        qube_payloads = {k: v for k, v in self.test_payloads.items() if k.startswith('qube_')}
        
        success_count = 0
        total_count = len(qube_payloads)
        
        for payload_name, payload in qube_payloads.items():
            print(f"\n📡 Validating {payload_name}...")
            
            # Check required fields
            required_fields = ["from", "to", "time", "mac", "type"]
            missing_fields = [field for field in required_fields if field not in payload]
            
            if missing_fields:
                print(f"❌ Missing required fields: {missing_fields}")
                continue
            
            # Validate JSON structure
            if not self.validate_json_structure(payload):
                continue
            
            # Check specific payload types
            if payload.get('type') == 'HB_Msg':
                if 'data' not in payload or 'msg' not in payload.get('data', {}):
                    print("❌ HB_Msg missing data.msg field")
                    continue
            elif payload.get('type') == 'reportAttribute':
                if 'data' not in payload or 'attribute' not in payload.get('data', {}):
                    print("❌ reportAttribute missing data.attribute field")
                    continue
                if 'citiz' not in payload:
                    print("❌ reportAttribute missing citiz field")
                    continue
            
            print(f"✅ {payload_name} - Valid structure")
            success_count += 1
        
        print(f"\n📊 Qube-Vital Results: {success_count}/{total_count} valid payloads")
        return success_count == total_count
    
    def run_all_validations(self):
        """Run all payload structure validations"""
        print("🚀 Starting MQTT Payload Structure Validation")
        print("Based on AVA4, Kati Watch, and Qube-Vital Documentation")
        print("=" * 80)
        
        # Validate all device types
        ava4_success = self.validate_ava4_payloads()
        kati_success = self.validate_kati_payloads()
        qube_success = self.validate_qube_payloads()
        
        # Summary
        print("\n" + "=" * 80)
        print("📊 FINAL VALIDATION RESULTS")
        print("=" * 80)
        print(f"🔹 AVA4: {'✅ PASSED' if ava4_success else '❌ FAILED'}")
        print(f"🔹 Kati Watch: {'✅ PASSED' if kati_success else '❌ FAILED'}")
        print(f"🔹 Qube-Vital: {'✅ PASSED' if qube_success else '❌ FAILED'}")
        
        total_success = sum([ava4_success, kati_success, qube_success])
        total_devices = 3
        
        print(f"\n🎯 Overall: {total_success}/{total_devices} device types passed validation")
        
        if total_success == total_devices:
            print("🎉 All MQTT payload structures are valid!")
        else:
            print(f"⚠️  {total_devices - total_success} device types failed validation")
        
        return total_success == total_devices

def main():
    """Main validation function"""
    validator = MQTTPayloadStructureValidator()
    
    try:
        success = validator.run_all_validations()
        return 0 if success else 1
    except Exception as e:
        print(f"❌ Validation failed: {e}")
        return 1

if __name__ == "__main__":
    exit(main()) 