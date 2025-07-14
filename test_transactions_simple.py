#!/usr/bin/env python3
"""
Simple test script to create sample transaction data for the Data Processing Transactions page
"""

import requests
import json
import time
from datetime import datetime

# Web panel base URL
BASE_URL = "http://localhost:8098"

def create_sample_transaction_data():
    """Create sample transaction data that shows what the user expects to see"""
    
    # Sample transaction data that demonstrates:
    # 1. Data source (device type, ID, MQTT topic)
    # 2. Data prepared to store (parsed vital signs)
    # 3. Database collection and stored data
    # 4. Transaction outcome
    
    sample_transactions = [
        {
            "operation": "Process Kati Watch Vital Signs",
            "data_type": "heart_rate",
            "collection": "heart_rate_histories",
            "patient_id": "6605084300df0d8b0c5a33ad",
            "device_id": "AP55",
            "details": "Data Source: iMEDE_watch/AP55 MQTT Topic | Raw Data: {'heart_rate': 75, 'timestamp': '2024-01-15T10:30:00Z'} | Parsed: Heart Rate: 75 BPM | Stored to: heart_rate_histories collection | Outcome: Success - Record created",
            "status": "success"
        },
        {
            "operation": "Process Kati Watch Blood Pressure",
            "data_type": "blood_pressure", 
            "collection": "blood_pressure_histories",
            "patient_id": "6605084300df0d8b0c5a33ad",
            "device_id": "AP55",
            "details": "Data Source: iMEDE_watch/AP55 MQTT Topic | Raw Data: {'systolic': 120, 'diastolic': 80, 'timestamp': '2024-01-15T10:30:00Z'} | Parsed: BP: 120/80 mmHg | Stored to: blood_pressure_histories collection | Outcome: Success - Record created",
            "status": "success"
        },
        {
            "operation": "Process Kati Watch SpO2",
            "data_type": "spo2",
            "collection": "spo2_histories", 
            "patient_id": "6605084300df0d8b0c5a33ad",
            "device_id": "AP55",
            "details": "Data Source: iMEDE_watch/AP55 MQTT Topic | Raw Data: {'spo2': 98, 'timestamp': '2024-01-15T10:30:00Z'} | Parsed: SpO2: 98% | Stored to: spo2_histories collection | Outcome: Success - Record created",
            "status": "success"
        },
        {
            "operation": "Process AVA4 Device Data",
            "data_type": "body_temp",
            "collection": "body_temp_histories",
            "patient_id": "6605084300df0d8b0c5a33ad", 
            "device_id": "AVA4_001",
            "details": "Data Source: ESP32_BLE_GW_TX MQTT Topic | Raw Data: {'temperature': 36.8, 'timestamp': '2024-01-15T10:30:00Z'} | Parsed: Body Temp: 36.8°C | Stored to: body_temp_histories collection | Outcome: Success - Record created",
            "status": "success"
        },
        {
            "operation": "Process Qube Device Data",
            "data_type": "step_count",
            "collection": "step_histories",
            "patient_id": "6605084300df0d8b0c5a33ad",
            "device_id": "QUBE_001", 
            "details": "Data Source: CM4_BLE_GW_TX MQTT Topic | Raw Data: {'steps': 1250, 'timestamp': '2024-01-15T10:30:00Z'} | Parsed: Steps: 1,250 | Stored to: step_histories collection | Outcome: Success - Record created",
            "status": "success"
        }
    ]
    
    return sample_transactions

def log_transaction_to_database(transaction_data):
    """Log a transaction directly to the database using the API"""
    try:
        url = f"{BASE_URL}/api/log-transaction"
        
        response = requests.post(url, json=transaction_data, timeout=10)
        
        if response.status_code == 200:
            print(f"✅ Logged: {transaction_data['operation']}")
            return True
        else:
            print(f"❌ Failed to log: {response.status_code} - {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"❌ Connection error - Is the web panel running on {BASE_URL}?")
        return False
    except Exception as e:
        print(f"❌ Error logging transaction: {e}")
        return False

def main():
    """Main function to create sample transaction data"""
    
    print("🚀 Creating sample transaction data for Data Processing Transactions page...")
    print("=" * 80)
    
    # Get sample transaction data
    transactions = create_sample_transaction_data()
    
    print(f"📊 Will create {len(transactions)} sample transactions")
    print("📋 Each transaction will show:")
    print("   1. Data Source (device type, ID, MQTT topic)")
    print("   2. Data prepared to store (parsed vital signs)")
    print("   3. Database collection and stored data")
    print("   4. Transaction outcome")
    print()
    
    success_count = 0
    
    for i, transaction in enumerate(transactions, 1):
        print(f"📝 Creating transaction {i}/{len(transactions)}:")
        print(f"   Operation: {transaction['operation']}")
        print(f"   Data Type: {transaction['data_type']}")
        print(f"   Collection: {transaction['collection']}")
        print(f"   Device: {transaction['device_id']}")
        print()
        
        if log_transaction_to_database(transaction):
            success_count += 1
        
        # Add delay between transactions
        time.sleep(2)
    
    print("=" * 80)
    print(f"✅ Created {success_count}/{len(transactions)} transactions successfully!")
    print()
    print("🌐 Next steps:")
    print("   1. Open your browser to: http://localhost:8098/")
    print("   2. Login with: operapanel / Sim!443355")
    print("   3. Go to the 'Data Transactions' tab")
    print("   4. You should now see the sample transaction data!")
    print()
    print("📊 The transactions will show exactly what you requested:")
    print("   - Data source information")
    print("   - Data prepared for storage")
    print("   - Database collection details")
    print("   - Transaction outcomes")

if __name__ == "__main__":
    main() 