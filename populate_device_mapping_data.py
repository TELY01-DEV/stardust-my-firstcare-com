#!/usr/bin/env python3
"""
Script to populate database with sample patients and devices for device mapping testing
Creates realistic data that matches the device mapping requirements
"""

import requests
import json
from datetime import datetime
from bson import ObjectId

# API Configuration
BASE_URL = "http://localhost:5054"
ADMIN_API = f"{BASE_URL}/admin"

def get_auth_token():
    """Get JWT authentication token"""
    try:
        response = requests.post(f"{BASE_URL}/auth/login", json={
            "username": "operapanel",
            "password": "Sim!443355"
        })
        if response.status_code == 200:
            return response.json().get('access_token')
        else:
            print(f"Failed to get auth token: {response.status_code}")
            return None
    except Exception as e:
        print(f"Error getting auth token: {e}")
        return None

def create_sample_patients(token):
    """Create sample patients with device mappings"""
    print("Creating sample patients...")
    
    # Sample patient data with device mappings
    patients_data = [
        {
            "first_name": "John",
            "last_name": "Smith",
            "first_name_th": "จอห์น",
            "last_name_th": "สมิธ",
            "national_id": "1234567890123",
            "id_card": "1234567890123",
            "unique_id": "PAT001",
            "ava_mac_address": "AA:BB:CC:DD:EE:FF",  # AVA4 Box MAC
            "watch_mac_address": "987654321098765",   # Kati Watch IMEI
            "blood_pressure_mac_address": "11:22:33:44:55:66",  # AVA4 BP Device
            "fingertip_pulse_oximeter_mac_address": "AA:BB:CC:DD:EE:77",  # AVA4 SpO2 Device
            "blood_glucose_mac_address": "22:33:44:55:66:77",  # AVA4 Glucose Device
            "body_temperature_mac_address": "33:44:55:66:77:88",  # AVA4 Temp Device
            "weight_scale_mac_address": "44:55:66:77:88:99",  # AVA4 Weight Device
            "uric_mac_address": "55:66:77:88:99:AA",  # AVA4 Uric Device
            "cholesterol_mac_address": "66:77:88:99:AA:BB",  # AVA4 Cholesterol Device
            "dob": "1980-05-15",
            "gender": "male",
            "mobile_no": "0812345678",
            "email": "john.smith@example.com",
            "status": "active"
        },
        {
            "first_name": "Jane",
            "last_name": "Doe",
            "first_name_th": "เจน",
            "last_name_th": "โด",
            "national_id": "9876543210987",
            "id_card": "9876543210987",
            "unique_id": "PAT002",
            "ava_mac_address": "BB:CC:DD:EE:FF:00",  # AVA4 Box MAC
            "watch_mac_address": "123456789012345",   # Kati Watch IMEI
            "blood_pressure_mac_address": "77:88:99:AA:BB:CC",  # AVA4 BP Device
            "fingertip_pulse_oximeter_mac_address": "88:99:AA:BB:CC:DD",  # AVA4 SpO2 Device
            "blood_glucose_mac_address": "99:AA:BB:CC:DD:EE",  # AVA4 Glucose Device
            "body_temperature_mac_address": "AA:BB:CC:DD:EE:FF",  # AVA4 Temp Device
            "weight_scale_mac_address": "BB:CC:DD:EE:FF:00",  # AVA4 Weight Device
            "uric_mac_address": "CC:DD:EE:FF:00:11",  # AVA4 Uric Device
            "cholesterol_mac_address": "DD:EE:FF:00:11:22",  # AVA4 Cholesterol Device
            "dob": "1985-08-20",
            "gender": "female",
            "mobile_no": "0898765432",
            "email": "jane.doe@example.com",
            "status": "active"
        },
        {
            "first_name": "Somchai",
            "last_name": "Jai",
            "first_name_th": "สมชาย",
            "last_name_th": "ใจ",
            "national_id": "1112223334445",
            "id_card": "1112223334445",
            "unique_id": "PAT003",
            "ava_mac_address": "QUBE_VITAL_001",  # Qube-Vital Device ID
            "watch_mac_address": "555666777888999",   # Kati Watch IMEI
            "blood_pressure_mac_address": "EE:FF:00:11:22:33",  # AVA4 BP Device
            "fingertip_pulse_oximeter_mac_address": "FF:00:11:22:33:44",  # AVA4 SpO2 Device
            "blood_glucose_mac_address": "00:11:22:33:44:55",  # AVA4 Glucose Device
            "body_temperature_mac_address": "11:22:33:44:55:66",  # AVA4 Temp Device
            "weight_scale_mac_address": "22:33:44:55:66:77",  # AVA4 Weight Device
            "uric_mac_address": "33:44:55:66:77:88",  # AVA4 Uric Device
            "cholesterol_mac_address": "44:55:66:77:88:99",  # AVA4 Cholesterol Device
            "dob": "1975-12-10",
            "gender": "male",
            "mobile_no": "0876543210",
            "email": "somchai.jai@example.com",
            "status": "active"
        }
    ]
    
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    
    for patient_data in patients_data:
        try:
            response = requests.post(f"{ADMIN_API}/patients", json=patient_data, headers=headers)
            if response.status_code == 200:
                print(f"Created patient: {patient_data['first_name']} {patient_data['last_name']}")
            else:
                print(f"Failed to create patient {patient_data['first_name']}: {response.status_code}")
        except Exception as e:
            print(f"Error creating patient {patient_data['first_name']}: {e}")

def create_sample_devices(token):
    """Create sample devices with patient mappings"""
    print("Creating sample devices...")
    
    # Sample AVA4 devices
    ava4_devices = [
        {
            "mac_address": "AA:BB:CC:DD:EE:FF",
            "device_type": "AVA4_Box",
            "device_name": "AVA4_Box_001",
            "patient_id": "PAT001",  # Will be mapped to actual patient ID
            "status": "active"
        },
        {
            "mac_address": "BB:CC:DD:EE:FF:00",
            "device_type": "AVA4_Box",
            "device_name": "AVA4_Box_002",
            "patient_id": "PAT002",
            "status": "active"
        }
    ]
    
    # Sample Kati watches
    kati_watches = [
        {
            "imei": "987654321098765",
            "device_type": "Kati_Watch",
            "device_name": "Kati_Watch_001",
            "patient_id": "PAT001",
            "status": "active"
        },
        {
            "imei": "123456789012345",
            "device_type": "Kati_Watch",
            "device_name": "Kati_Watch_002",
            "patient_id": "PAT002",
            "status": "active"
        },
        {
            "imei": "555666777888999",
            "device_type": "Kati_Watch",
            "device_name": "Kati_Watch_003",
            "patient_id": "PAT003",
            "status": "active"
        }
    ]
    
    # Sample Qube-Vital devices
    qube_devices = [
        {
            "device_id": "QUBE_VITAL_001",
            "device_type": "Qube_Vital",
            "device_name": "Qube_Vital_001",
            "patient_id": "PAT003",
            "status": "active"
        }
    ]
    
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    
    # Create AVA4 devices
    for device in ava4_devices:
        try:
            response = requests.post(f"{ADMIN_API}/devices", json=device, headers=headers)
            if response.status_code == 200:
                print(f"Created AVA4 device: {device['device_name']}")
            else:
                print(f"Failed to create AVA4 device {device['device_name']}: {response.status_code}")
        except Exception as e:
            print(f"Error creating AVA4 device {device['device_name']}: {e}")
    
    # Create Kati watches
    for watch in kati_watches:
        try:
            response = requests.post(f"{ADMIN_API}/watches", json=watch, headers=headers)
            if response.status_code == 200:
                print(f"Created Kati watch: {watch['device_name']}")
            else:
                print(f"Failed to create Kati watch {watch['device_name']}: {response.status_code}")
        except Exception as e:
            print(f"Error creating Kati watch {watch['device_name']}: {e}")
    
    # Create Qube-Vital devices
    for device in qube_devices:
        try:
            response = requests.post(f"{ADMIN_API}/qube-devices", json=device, headers=headers)
            if response.status_code == 200:
                print(f"Created Qube-Vital device: {device['device_name']}")
            else:
                print(f"Failed to create Qube-Vital device {device['device_name']}: {response.status_code}")
        except Exception as e:
            print(f"Error creating Qube-Vital device {device['device_name']}: {e}")

def create_sample_amy_devices(token):
    """Create sample AMY devices with specific MAC field mappings"""
    print("Creating sample AMY devices...")
    
    # Sample AMY devices with specific MAC fields for AVA4 sub-devices
    amy_devices = [
        {
            "mac_address": "AA:BB:CC:DD:EE:FF",
            "mac_dusun_bps": "11:22:33:44:55:66",  # Blood Pressure
            "mac_oxymeter": "AA:BB:CC:DD:EE:77",   # SpO2
            "mac_body_temp": "33:44:55:66:77:88",  # Body Temperature
            "mac_weight": "44:55:66:77:88:99",     # Weight Scale
            "mac_gluc": "22:33:44:55:66:77",       # Blood Glucose
            "mac_ua": "55:66:77:88:99:AA",         # Uric Acid
            "mac_chol": "66:77:88:99:AA:BB",       # Cholesterol
            "patient_id": "PAT001",
            "device_type": "AMY_AVA4",
            "status": "active"
        },
        {
            "mac_address": "BB:CC:DD:EE:FF:00",
            "mac_dusun_bps": "77:88:99:AA:BB:CC",  # Blood Pressure
            "mac_oxymeter": "88:99:AA:BB:CC:DD",   # SpO2
            "mac_body_temp": "AA:BB:CC:DD:EE:FF",  # Body Temperature
            "mac_weight": "BB:CC:DD:EE:FF:00",     # Weight Scale
            "mac_gluc": "99:AA:BB:CC:DD:EE",       # Blood Glucose
            "mac_ua": "CC:DD:EE:FF:00:11",         # Uric Acid
            "mac_chol": "DD:EE:FF:00:11:22",       # Cholesterol
            "patient_id": "PAT002",
            "device_type": "AMY_AVA4",
            "status": "active"
        }
    ]
    
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    
    for device in amy_devices:
        try:
            response = requests.post(f"{ADMIN_API}/amy-devices", json=device, headers=headers)
            if response.status_code == 200:
                print(f"Created AMY device: {device['mac_address']}")
            else:
                print(f"Failed to create AMY device {device['mac_address']}: {response.status_code}")
        except Exception as e:
            print(f"Error creating AMY device {device['mac_address']}: {e}")

def create_sample_hospitals(token):
    """Create sample hospitals with Qube-Vital MAC address mappings"""
    print("Creating sample hospitals...")
    
    # Sample hospitals with Qube-Vital MAC mappings
    hospitals_data = [
        {
            "name": [
                {"code": "en", "name": "Bangkok General Hospital"},
                {"code": "th", "name": "โรงพยาบาลกรุงเทพ"}
            ],
            "en_name": "Bangkok General Hospital",
            "th_name": "โรงพยาบาลกรุงเทพ",
            "mac_hv01_box": "QUBE_VITAL_001",  # Qube-Vital device mapping
            "province_code": 10,
            "district_code": 1003,
            "sub_district_code": 100301,
            "organizecode": 1001,
            "hospital_area_code": "10330",
            "is_active": True,
            "is_deleted": False,
            "address": "123 Rama IV Road, Pathum Wan, Bangkok 10330",
            "phone": "+66-2-123-4567",
            "email": "info@bgh.co.th",
            "website": "https://www.bgh.co.th",
            "bed_capacity": 500,
            "service_plan_type": "A"
        },
        {
            "name": [
                {"code": "en", "name": "Samut Prakan Medical Center"},
                {"code": "th", "name": "ศูนย์การแพทย์สมุทรปราการ"}
            ],
            "en_name": "Samut Prakan Medical Center",
            "th_name": "ศูนย์การแพทย์สมุทรปราการ",
            "mac_hv01_box": "QUBE_VITAL_002",  # Qube-Vital device mapping
            "province_code": 11,
            "district_code": 1101,
            "sub_district_code": 110101,
            "organizecode": 1101,
            "hospital_area_code": "10270",
            "is_active": True,
            "is_deleted": False,
            "address": "456 Sukhumvit Road, Samut Prakan 10270",
            "phone": "+66-2-234-5678",
            "email": "info@spmc.co.th",
            "website": "https://www.spmc.co.th",
            "bed_capacity": 300,
            "service_plan_type": "B"
        }
    ]
    
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    
    for hospital_data in hospitals_data:
        try:
            response = requests.post(f"{ADMIN_API}/hospitals", json=hospital_data, headers=headers)
            if response.status_code == 200:
                print(f"Created hospital: {hospital_data['en_name']}")
            else:
                print(f"Failed to create hospital {hospital_data['en_name']}: {response.status_code}")
        except Exception as e:
            print(f"Error creating hospital {hospital_data['en_name']}: {e}")

def verify_data_creation(token):
    """Verify that the sample data was created successfully"""
    print("Verifying data creation...")
    
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    
    try:
        # Check patients
        response = requests.get(f"{ADMIN_API}/patients-raw-documents", headers=headers)
        if response.status_code == 200:
            patients = response.json().get('data', {}).get('raw_documents', [])
            print(f"Found {len(patients)} patients")
            
            for patient in patients[:3]:  # Show first 3 patients
                print(f"  Patient: {patient.get('first_name')} {patient.get('last_name')}")
                print(f"    AVA MAC: {patient.get('ava_mac_address')}")
                print(f"    Watch MAC: {patient.get('watch_mac_address')}")
                print(f"    BP MAC: {patient.get('blood_pressure_mac_address')}")
        else:
            print(f"Failed to get patients: {response.status_code}")
    except Exception as e:
        print(f"Error verifying patients: {e}")
    
    try:
        # Check devices
        response = requests.get(f"{ADMIN_API}/devices", headers=headers)
        if response.status_code == 200:
            devices = response.json()
            print(f"Found {len(devices)} devices")
        else:
            print(f"Failed to get devices: {response.status_code}")
    except Exception as e:
        print(f"Error verifying devices: {e}")

def main():
    """Main function to populate database with sample data"""
    print("Starting database population for device mapping testing...")
    
    # Get authentication token
    token = get_auth_token()
    if not token:
        print("Warning: No authentication token available. Some operations may fail.")
    
    # Create sample data
    create_sample_patients(token)
    create_sample_devices(token)
    create_sample_amy_devices(token)
    create_sample_hospitals(token)
    
    # Verify data creation
    verify_data_creation(token)
    
    print("\n=== Database Population Complete ===")
    print("Sample data has been created for device mapping testing.")
    print("You can now run the device mapping test script.")

if __name__ == "__main__":
    main() 