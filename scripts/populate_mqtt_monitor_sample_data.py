#!/usr/bin/env python3
"""
Populate MongoDB with sample data for MQTT Monitor Web Panel
- Devices (amy_boxes, watches, hospitals)
- Patients
- Transaction logs
"""

from pymongo import MongoClient
from datetime import datetime

MONGODB_URI = "mongodb://opera_admin:Sim!443355@coruscant.my-firstcare.com:27023/admin?ssl=true&authSource=admin"
DB_NAME = "AMY"

client = MongoClient(MONGODB_URI, tls=True, tlsAllowInvalidCertificates=True)
db = client[DB_NAME]

# Sample patients
db.patients.delete_many({})
patients = [
    {
        "_id": "6605084300df0d8b0c5a33ad",
        "first_name": "John",
        "last_name": "Doe",
        "id_card": "1234567890123",
        "ava_mac_address": "AA:BB:CC:DD:EE:01",
        "watch_mac_address": "FF:EE:DD:CC:BB:01",
        "registration_status": "active"
    },
    {
        "_id": "6605084300df0d8b0c5a33ae",
        "first_name": "Jane",
        "last_name": "Smith",
        "id_card": "9876543210987",
        "ava_mac_address": "AA:BB:CC:DD:EE:02",
        "watch_mac_address": "FF:EE:DD:CC:BB:02",
        "registration_status": "active"
    }
]
db.patients.insert_many(patients)

# Sample devices
db.amy_boxes.delete_many({})
db.amy_boxes.insert_many([
    {"_id": "AVA4_001", "mac_address": "AA:BB:CC:DD:EE:01", "name": "AVA4 Box 1", "patient_id": "6605084300df0d8b0c5a33ad"},
    {"_id": "AVA4_002", "mac_address": "AA:BB:CC:DD:EE:02", "name": "AVA4 Box 2", "patient_id": "6605084300df0d8b0c5a33ae"}
])

db.watches.delete_many({})
db.watches.insert_many([
    {"_id": "AP55", "imei": "123456789012345", "patient_id": "6605084300df0d8b0c5a33ad"},
    {"_id": "AP56", "imei": "987654321098765", "patient_id": "6605084300df0d8b0c5a33ae"}
])

db.hospitals.delete_many({})
db.hospitals.insert_many([
    {"_id": "QUBE_001", "name": "Qube Hospital 1", "mac_hv01_box": "11:22:33:44:55:01"},
    {"_id": "QUBE_002", "name": "Qube Hospital 2", "mac_hv01_box": "11:22:33:44:55:02"}
])

# Sample transaction logs
db.transaction_logs.delete_many({})
now = datetime.utcnow()
transaction_logs = [
    {
        "operation": "Process Kati Watch Vital Signs",
        "data_type": "heart_rate",
        "collection": "heart_rate_histories",
        "patient_id": "6605084300df0d8b0c5a33ad",
        "device_id": "AP55",
        "details": "Data Source: iMEDE_watch/AP55 MQTT Topic | Raw Data: {'heart_rate': 75, 'timestamp': '2024-01-15T10:30:00Z'} | Parsed: Heart Rate: 75 BPM | Stored to: heart_rate_histories collection | Outcome: Success - Record created",
        "status": "success",
        "timestamp": now,
        "created_at": now
    },
    {
        "operation": "Process Kati Watch Blood Pressure",
        "data_type": "blood_pressure",
        "collection": "blood_pressure_histories",
        "patient_id": "6605084300df0d8b0c5a33ad",
        "device_id": "AP55",
        "details": "Data Source: iMEDE_watch/AP55 MQTT Topic | Raw Data: {'systolic': 120, 'diastolic': 80, 'timestamp': '2024-01-15T10:30:00Z'} | Parsed: BP: 120/80 mmHg | Stored to: blood_pressure_histories collection | Outcome: Success - Record created",
        "status": "success",
        "timestamp": now,
        "created_at": now
    },
    {
        "operation": "Process AVA4 Device Data",
        "data_type": "body_temp",
        "collection": "body_temp_histories",
        "patient_id": "6605084300df0d8b0c5a33ae",
        "device_id": "AVA4_002",
        "details": "Data Source: ESP32_BLE_GW_TX MQTT Topic | Raw Data: {'temperature': 36.8, 'timestamp': '2024-01-15T10:30:00Z'} | Parsed: Body Temp: 36.8°C | Stored to: body_temp_histories collection | Outcome: Success - Record created",
        "status": "success",
        "timestamp": now,
        "created_at": now
    },
    {
        "operation": "Process Qube Device Data",
        "data_type": "step_count",
        "collection": "step_histories",
        "patient_id": "6605084300df0d8b0c5a33ae",
        "device_id": "QUBE_002",
        "details": "Data Source: CM4_BLE_GW_TX MQTT Topic | Raw Data: {'steps': 1250, 'timestamp': '2024-01-15T10:30:00Z'} | Parsed: Steps: 1,250 | Stored to: step_histories collection | Outcome: Success - Record created",
        "status": "success",
        "timestamp": now,
        "created_at": now
    }
]
db.transaction_logs.insert_many(transaction_logs)

print("✅ Sample data inserted for patients, devices, and transactions!") 