#!/usr/bin/env python3
"""
Test script to simulate real Kati listener transactions
This will log actual transaction data based on your Kati listener logs
"""

import requests
import json
import time
from datetime import datetime, timedelta

# Web panel base URL
BASE_URL = "http://localhost:8098"

def log_transaction(operation, data_type, collection, patient_id=None, details=None, device_id=None):
    """Log a transaction to the web panel"""
    try:
        url = f"{BASE_URL}/api/log-transaction"
        
        data = {
            "operation": operation,
            "data_type": data_type,
            "collection": collection,
            "patient_id": patient_id,
            "details": details,
            "device_id": device_id,
            "status": "success"
        }
        
        response = requests.post(url, json=data)
        if response.status_code == 200:
            print(f"✅ Logged: {operation} - {data_type}")
        else:
            print(f"❌ Failed to log: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"❌ Error logging transaction: {e}")

def simulate_kati_listener_transactions():
    """Simulate the actual Kati listener transactions from your logs"""
    
    patient_id = "6605084300df0d8b0c5a33ad"
    device_id = "AP55"
    
    # Simulate the exact transactions from your logs
    transactions = [
        # Heart Rate transactions
        ("Updated last heart_rate data", "heart_rate", "heart_rate_histories", 
         patient_id, "Processed iMEDE_watch/AP55 data", device_id),
        ("Stored heart_rate history", "heart_rate", "heart_rate_histories", 
         patient_id, "Added to historical records", device_id),
        
        # Blood Pressure transactions
        ("Updated last blood_pressure data", "blood_pressure", "blood_pressure_histories", 
         patient_id, "Processed iMEDE_watch/AP55 data", device_id),
        ("Stored blood_pressure history", "blood_pressure", "blood_pressure_histories", 
         patient_id, "Added to historical records", device_id),
        
        # SpO2 transactions
        ("Updated last spo2 data", "spo2", "spo2_histories", 
         patient_id, "Processed iMEDE_watch/AP55 data", device_id),
        ("Stored spo2 history", "spo2", "spo2_histories", 
         patient_id, "Added to historical records", device_id),
        
        # Body Temperature transactions
        ("Updated last body_temp data", "body_temp", "body_temp_histories", 
         patient_id, "Processed iMEDE_watch/AP55 data", device_id),
        ("Stored body_temp history", "body_temp", "body_temp_histories", 
         patient_id, "Added to historical records", device_id),
    ]
    
    print("🚀 Starting Kati listener transaction simulation...")
    print(f"📊 Will log {len(transactions)} transactions")
    print(f"👤 Patient ID: {patient_id}")
    print(f"📱 Device ID: {device_id}")
    print()
    
    for i, (operation, data_type, collection, patient_id, details, device_id) in enumerate(transactions, 1):
        print(f"📝 Transaction {i}/{len(transactions)}:")
        log_transaction(operation, data_type, collection, patient_id, details, device_id)
        
        # Add a small delay between transactions to simulate real processing
        time.sleep(2)
    
    print()
    print("✅ Transaction simulation complete!")
    print("🌐 Check the web panel at http://localhost:8098/")
    print("📊 Go to the 'Data Transactions' tab to see the real-time updates")

def simulate_continuous_transactions():
    """Simulate continuous real-time transactions"""
    
    patient_id = "6605084300df0d8b0c5a33ad"
    device_id = "AP55"
    
    print("🔄 Starting continuous transaction simulation...")
    print("Press Ctrl+C to stop")
    print()
    
    try:
        while True:
            # Simulate different vital signs being processed
            vital_signs = [
                ("heart_rate", "heart_rate_histories"),
                ("blood_pressure", "blood_pressure_histories"),
                ("spo2", "spo2_histories"),
                ("body_temp", "body_temp_histories")
            ]
            
            for data_type, collection in vital_signs:
                # Update operation
                log_transaction(
                    f"Updated last {data_type} data",
                    data_type,
                    collection,
                    patient_id,
                    f"Processed iMEDE_watch/AP55 data at {datetime.now().strftime('%H:%M:%S')}",
                    device_id
                )
                
                time.sleep(1)
                
                # Store operation
                log_transaction(
                    f"Stored {data_type} history",
                    data_type,
                    collection,
                    patient_id,
                    "Added to historical records",
                    device_id
                )
                
                time.sleep(1)
            
            print(f"⏰ Cycle completed at {datetime.now().strftime('%H:%M:%S')}")
            time.sleep(5)  # Wait 5 seconds before next cycle
            
    except KeyboardInterrupt:
        print("\n🛑 Continuous simulation stopped")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "continuous":
        simulate_continuous_transactions()
    else:
        simulate_kati_listener_transactions() 