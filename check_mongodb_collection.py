#!/usr/bin/env python3
"""
Script to check the latest_devices_status collection in MongoDB
"""

import os
from pymongo import MongoClient
from datetime import datetime

# MongoDB Configuration with SSL
mongodb_uri = "mongodb://opera_admin:Sim!443355@coruscant.my-firstcare.com:27023/admin?ssl=true&authSource=admin"

# SSL Certificate paths
ssl_ca_file = "ssl/ca-latest.pem"
ssl_client_file = "ssl/client-combined-latest.pem"

# Check if SSL certificate files exist
ssl_ca_exists = os.path.exists(ssl_ca_file)
ssl_client_exists = os.path.exists(ssl_client_file)

print(f"🔍 Checking MongoDB latest_devices_status collection...")
print(f"📁 SSL CA file exists: {ssl_ca_exists}")
print(f"📁 SSL Client file exists: {ssl_client_exists}")

# MongoDB configuration with SSL (PyMongo 4.x+)
mongodb_config = {
    "host": "coruscant.my-firstcare.com",
    "port": 27023,
    "username": "opera_admin",
    "password": "Sim!443355",
    "authSource": "admin",
    "tls": True,
    "tlsCAFile": ssl_ca_file if ssl_ca_exists else None,
    "tlsCertificateKeyFile": ssl_client_file if ssl_client_exists else None
}

try:
    # Connect to MongoDB
    client = MongoClient(**mongodb_config)
    
    # Test connection
    client.admin.command('ping')
    print("✅ Successfully connected to MongoDB")
    
    # Access the database
    db = client['AMY']  # Use the AMY database
    
    # Check if latest_devices_status collection exists
    collections = db.list_collection_names()
    if 'latest_devices_status' in collections:
        print("✅ latest_devices_status collection exists")
        
        # Count documents in the collection
        count = db.latest_devices_status.count_documents({})
        print(f"📊 Total documents in latest_devices_status: {count}")
        
        if count > 0:
            # Get recent documents
            recent_docs = list(db.latest_devices_status.find().sort("last_updated", -1).limit(5))
            print(f"\n📋 Recent device status records:")
            for i, doc in enumerate(recent_docs, 1):
                print(f"  {i}. Device ID: {doc.get('device_id', 'N/A')}")
                print(f"     Type: {doc.get('device_type', 'N/A')}")
                print(f"     Status: {doc.get('online_status', 'N/A')}")
                print(f"     Patient ID: {doc.get('patient_id', 'N/A')}")
                print(f"     Last Updated: {doc.get('last_updated', 'N/A')}")
                print(f"     Battery: {doc.get('battery_level', 'N/A')}")
                print(f"     Signal: {doc.get('signal_strength', 'N/A')}")
                print()
        else:
            print("📭 Collection is empty - no device status records found")
    else:
        print("❌ latest_devices_status collection does not exist")
        
except Exception as e:
    print(f"❌ Error connecting to MongoDB: {e}")
finally:
    if 'client' in locals():
        client.close() 