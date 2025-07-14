#!/usr/bin/env python3
"""
Check transaction_logs collection directly in MongoDB
Uses the same configuration as the web panel
"""

import os
import sys
import ssl
from datetime import datetime
from pymongo import MongoClient
from bson import ObjectId

def check_transaction_logs():
    """Check transaction_logs collection in MongoDB"""
    
    # MongoDB configuration (same as web panel)
    mongodb_config = {
        "host": "coruscant.my-firstcare.com",
        "port": 27023,
        "username": "opera_admin",
        "password": "Sim!443355",
        "authSource": "admin",
        "tls": True,
        "tlsAllowInvalidCertificates": True,
        "tlsAllowInvalidHostnames": True,
        "serverSelectionTimeoutMS": 10000,
        "connectTimeoutMS": 10000
    }
    
    # Add SSL certificate files if they exist
    ssl_ca_file = "./ssl/ca-latest.pem"
    ssl_client_file = "./ssl/client-combined-latest.pem"
    
    if os.path.exists(ssl_ca_file):
        mongodb_config["tlsCAFile"] = ssl_ca_file
        print(f"✅ Using SSL CA file: {ssl_ca_file}")
    else:
        print(f"⚠️ SSL CA file not found: {ssl_ca_file}")
        
    if os.path.exists(ssl_client_file):
        mongodb_config["tlsCertificateKeyFile"] = ssl_client_file
        print(f"✅ Using SSL client file: {ssl_client_file}")
    else:
        print(f"⚠️ SSL client file not found: {ssl_client_file}")
    
    try:
        # Create client
        print("🔌 Connecting to MongoDB...")
        client = MongoClient(**mongodb_config)
        
        # Test connection
        client.admin.command('ping')
        print("✅ Connected to MongoDB successfully")
        
        # Set database
        db = client["AMY"]
        print(f"📊 Connected to database: AMY")
        
        # Check transaction_logs collection
        collection = db.transaction_logs
        
        # Get total count
        total_count = collection.count_documents({})
        print(f"📈 Total transaction logs: {total_count}")
        
        if total_count == 0:
            print("❌ No transaction logs found in the collection")
            
            # List all collections to see what's available
            print("\n📋 Available collections:")
            collections = db.list_collection_names()
            for coll in sorted(collections):
                count = db[coll].count_documents({})
                print(f"  - {coll}: {count} documents")
        else:
            # Get recent transactions
            print(f"\n📝 Recent transaction logs (last 10):")
            recent_transactions = collection.find().sort("timestamp", -1).limit(10)
            
            for i, transaction in enumerate(recent_transactions, 1):
                print(f"\n{i}. Transaction:")
                print(f"   - Operation: {transaction.get('operation', 'N/A')}")
                print(f"   - Data Type: {transaction.get('data_type', 'N/A')}")
                print(f"   - Collection: {transaction.get('collection', 'N/A')}")
                print(f"   - Patient ID: {transaction.get('patient_id', 'N/A')}")
                print(f"   - Device ID: {transaction.get('device_id', 'N/A')}")
                print(f"   - Status: {transaction.get('status', 'N/A')}")
                print(f"   - Details: {transaction.get('details', 'N/A')}")
                print(f"   - Timestamp: {transaction.get('timestamp', 'N/A')}")
                print(f"   - Created At: {transaction.get('created_at', 'N/A')}")
        
        client.close()
        print("\n✅ MongoDB connection closed")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("🔍 Checking transaction_logs collection in MongoDB...")
    print("=" * 60)
    success = check_transaction_logs()
    print("=" * 60)
    if success:
        print("✅ Check completed successfully")
    else:
        print("❌ Check failed")
        sys.exit(1) 