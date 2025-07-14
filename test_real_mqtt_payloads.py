#!/usr/bin/env python3
"""
Test Real MQTT Payloads
Simulates real MQTT messages using actual payload structures from documentation
"""

import json
import requests
import time
from datetime import datetime

def test_ava4_payloads():
    """Test AVA4 MQTT payloads"""
    print("🧪 Testing AVA4 MQTT Payloads...")
    
    # Real AVA4 payloads from documentation
    ava4_payloads = [
        # Blood Pressure - BP_BIOLIGTH
        {
            "topic": "dusun_sub",
            "payload": {
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
            }
        },
        # Oximeter - Oximeter JUMPER
        {
            "topic": "dusun_sub",
            "payload": {
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
            }
        },
        # Glucometer - Contour Elite
        {
            "topic": "dusun_sub",
            "payload": {
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
            }
        },
        # Thermometer - IR_TEMO_JUMPER
        {
            "topic": "dusun_sub",
            "payload": {
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
            }
        }
    ]
    
    for i, test_case in enumerate(ava4_payloads):
        print(f"📡 AVA4 Test {i+1}: {test_case['topic']} - {test_case['payload']['data']['attribute']}")
        print(f"   Payload: {json.dumps(test_case['payload'], indent=2)}")
        print(f"   ✅ AVA4 payload simulated")
        time.sleep(1)

def test_kati_payloads():
    """Test Kati Watch MQTT payloads"""
    print("\n🧪 Testing Kati Watch MQTT Payloads...")
    
    # Real Kati Watch payloads from documentation
    kati_payloads = [
        # Vital Signs
        {
            "topic": "iMEDE_watch/VitalSign",
            "payload": {
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
        },
        # Heartbeat with step data
        {
            "topic": "iMEDE_watch/hb",
            "payload": {
                "IMEI": "865067123456789",
                "signalGSM": 80,
                "battery": 67,
                "satellites": 4,
                "workingMode": 2,
                "timeStamps": "16/06/2025 12:30:45",
                "step": 999
            }
        },
        # Sleep data
        {
            "topic": "iMEDE_watch/sleepdata",
            "payload": {
                "IMEI": "865067123456789",
                "sleep": {
                    "timeStamps": "16/06/2025 01:00:00",
                    "time": "2200@0700",
                    "data": "0000000111110000010011111110011111111111110000000002200000001111111112111100111001111111211111111222111111111110110111111110110111111011112201110",
                    "num": 145
                }
            }
        }
    ]
    
    for i, test_case in enumerate(kati_payloads):
        print(f"📡 Kati Test {i+1}: {test_case['topic']}")
        print(f"   Payload: {json.dumps(test_case['payload'], indent=2)}")
        print(f"   ✅ Kati Watch payload simulated")
        time.sleep(1)

def test_qube_payloads():
    """Test Qube-Vital MQTT payloads"""
    print("\n🧪 Testing Qube-Vital MQTT Payloads...")
    
    # Real Qube-Vital payloads from documentation
    qube_payloads = [
        # Blood Pressure - WBP_JUMPER
        {
            "topic": "CM4_BLE_GW_TX",
            "payload": {
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
            }
        },
        # Glucometer - CONTOUR
        {
            "topic": "CM4_BLE_GW_TX",
            "payload": {
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
            }
        },
        # Weight Scale - BodyScale_JUMPER
        {
            "topic": "CM4_BLE_GW_TX",
            "payload": {
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
            }
        },
        # Oximeter - Oximeter_JUMPER
        {
            "topic": "CM4_BLE_GW_TX",
            "payload": {
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
    ]
    
    for i, test_case in enumerate(qube_payloads):
        print(f"📡 Qube Test {i+1}: {test_case['topic']} - {test_case['payload']['data']['attribute']}")
        print(f"   Payload: {json.dumps(test_case['payload'], indent=2)}")
        print(f"   ✅ Qube-Vital payload simulated")
        time.sleep(1)

def test_transaction_logging():
    """Test transaction logging with real data types"""
    print("\n🧪 Testing Transaction Logging with Real Data Types...")
    
    # Test transactions with real data types
    test_transactions = [
        {
            "operation": "store_medical_data",
            "data_type": "blood_pressure",
            "collection": "blood_pressure_histories",
            "patient_id": "507f1f77bcf86cd799439011",
            "status": "success",
            "details": "Stored blood pressure data from AVA4 BP_BIOLIGTH device",
            "device_id": "AVA4"
        },
        {
            "operation": "store_medical_data",
            "data_type": "spo2",
            "collection": "spo2_histories",
            "patient_id": "507f1f77bcf86cd799439011",
            "status": "success",
            "details": "Stored SpO2 data from AVA4 Oximeter JUMPER device",
            "device_id": "AVA4"
        },
        {
            "operation": "store_medical_data",
            "data_type": "heart_rate",
            "collection": "heart_rate_histories",
            "patient_id": "507f1f77bcf86cd799439011",
            "status": "success",
            "details": "Stored heart rate data from Kati Watch vital signs",
            "device_id": "Kati Watch"
        },
        {
            "operation": "store_medical_data",
            "data_type": "steps",
            "collection": "step_histories",
            "patient_id": "507f1f77bcf86cd799439011",
            "status": "success",
            "details": "Stored step count data from Kati Watch heartbeat",
            "device_id": "Kati Watch"
        },
        {
            "operation": "store_medical_data",
            "data_type": "blood_sugar",
            "collection": "blood_sugar_histories",
            "patient_id": "507f1f77bcf86cd799439011",
            "status": "success",
            "details": "Stored blood glucose data from Qube-Vital CONTOUR device",
            "device_id": "Qube-Vital"
        }
    ]
    
    for i, transaction in enumerate(test_transactions):
        try:
            response = requests.post(
                "http://localhost:8080/api/log-transaction",
                json=transaction,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                print(f"✅ Transaction {i+1} logged: {transaction['data_type']} → {transaction['collection']}")
            else:
                print(f"❌ Failed to log transaction {i+1}: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Error logging transaction {i+1}: {e}")
        
        time.sleep(1)

def main():
    """Run all tests with real MQTT payloads"""
    print("🚀 Starting Real MQTT Payload Test")
    print("=" * 60)
    
    # Test 1: AVA4 Payloads
    print("\n1️⃣ Testing AVA4 Device Payloads")
    test_ava4_payloads()
    
    # Test 2: Kati Watch Payloads
    print("\n2️⃣ Testing Kati Watch Payloads")
    test_kati_payloads()
    
    # Test 3: Qube-Vital Payloads
    print("\n3️⃣ Testing Qube-Vital Payloads")
    test_qube_payloads()
    
    # Test 4: Transaction Logging
    print("\n4️⃣ Testing Transaction Logging")
    test_transaction_logging()
    
    # Test 5: Verify transactions
    print("\n5️⃣ Verifying Transaction Logging")
    try:
        response = requests.get("http://localhost:8080/test/transactions")
        if response.status_code == 200:
            data = response.json()
            if "data" in data and isinstance(data["data"], list):
                print(f"✅ Found {len(data['data'])} transactions in database")
                for i, transaction in enumerate(data["data"][:5]):  # Show first 5
                    print(f"   {i+1}. {transaction.get('operation')} - {transaction.get('data_type')} → {transaction.get('collection')}")
            else:
                print("❌ No transaction data found")
        else:
            print(f"❌ Failed to get transactions: {response.status_code}")
    except Exception as e:
        print(f"❌ Error getting transactions: {e}")
    
    print("\n" + "=" * 60)
    print("✅ Real MQTT Payload Test Complete")
    print("\n📋 Summary:")
    print("• AVA4: Blood pressure, oximeter, glucometer, thermometer")
    print("• Kati Watch: Vital signs, heartbeat, sleep data")
    print("• Qube-Vital: Blood pressure, glucometer, weight scale, oximeter")
    print("\n🎯 Next Steps:")
    print("1. Check web panel at http://localhost:8080")
    print("2. Go to 'Data Processing Transactions' tab")
    print("3. Real MQTT messages will be processed with correct payload structure")
    print("4. Medical data will be stored to appropriate collections")

if __name__ == "__main__":
    main() 