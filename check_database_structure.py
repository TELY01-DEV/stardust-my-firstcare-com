#!/usr/bin/env python3
"""
Check Database Structure Script

This script checks the MongoDB database structure to understand what collections exist
and how the data is organized.
"""

import pymongo
import ssl
from datetime import datetime
import json

# MongoDB Configuration
MONGODB_URI = "mongodb://opera_admin:Sim!443355@coruscant.my-firstcare.com:27023/admin?ssl=true&authSource=admin&tlsAllowInvalidCertificates=true&tlsAllowInvalidHostnames=true"
MONGODB_DATABASE = "AMY"

def connect_to_mongodb():
    """Connect to MongoDB with SSL"""
    try:
        # Connect to MongoDB with proper SSL certificates
        client = pymongo.MongoClient(
            MONGODB_URI,
            tls=True,
            tlsCAFile='ssl/ca-latest.pem',
            tlsCertificateKeyFile='ssl/client-combined-latest.pem',
            tlsAllowInvalidCertificates=True,
            tlsAllowInvalidHostnames=True
        )
        
        # Test connection
        client.admin.command('ping')
        print("✅ Successfully connected to MongoDB")
        return client
    except Exception as e:
        print(f"❌ Failed to connect to MongoDB: {e}")
        return None

def check_database_structure(client):
    """Check the database structure"""
    try:
        db = client[MONGODB_DATABASE]
        
        # Get all collections
        collections = db.list_collection_names()
        print(f"\n📊 Database: {MONGODB_DATABASE}")
        print(f"📋 Collections found: {len(collections)}")
        
        for collection in collections:
            count = db[collection].count_documents({})
            print(f"   - {collection}: {count} documents")
            
            # Show sample document structure for key collections
            if collection in ['devices', 'patients', 'events', 'event_logs']:
                sample = db[collection].find_one()
                if sample:
                    print(f"     Sample structure: {list(sample.keys())}")
        
        return collections
        
    except Exception as e:
        print(f"❌ Error checking database structure: {e}")
        return []

def check_devices_collection(client):
    """Check the devices collection specifically"""
    try:
        db = client[MONGODB_DATABASE]
        
        # Check if devices collection exists
        if 'devices' in db.list_collection_names():
            devices = list(db.devices.find({}))
            print(f"\n📱 Devices Collection:")
            print(f"   Total devices: {len(devices)}")
            
            if devices:
                print(f"   Sample device structure:")
                sample_device = devices[0]
                for key, value in sample_device.items():
                    if key != '_id':
                        print(f"     {key}: {value}")
            else:
                print("   No devices found in collection")
        else:
            print("\n❌ Devices collection not found")
            
            # Check for similar collections
            collections = db.list_collection_names()
            device_like = [c for c in collections if 'device' in c.lower()]
            if device_like:
                print(f"   Similar collections found: {device_like}")
                
    except Exception as e:
        print(f"❌ Error checking devices collection: {e}")

def check_events_collection(client):
    """Check the events collection for device data"""
    try:
        db = client[MONGODB_DATABASE]
        
        # Check for events or event_logs collection
        events_collections = [c for c in db.list_collection_names() if 'event' in c.lower()]
        
        for collection_name in events_collections:
            print(f"\n📊 {collection_name} Collection:")
            count = db[collection_name].count_documents({})
            print(f"   Total events: {count}")
            
            if count > 0:
                # Get sample events with device information
                sample_events = list(db[collection_name].find({}, {'device_id': 1, 'source': 1, 'patient_id': 1}).limit(5))
                print(f"   Sample events with device info:")
                for event in sample_events:
                    print(f"     Device: {event.get('device_id', 'N/A')}, Source: {event.get('source', 'N/A')}, Patient: {event.get('patient_id', 'N/A')}")
                    
    except Exception as e:
        print(f"❌ Error checking events collection: {e}")

def main():
    """Main function to check database structure"""
    print("🔍 Database Structure Check")
    print("=" * 50)
    
    # Step 1: Connect to MongoDB
    print("\n1. Connecting to MongoDB...")
    client = connect_to_mongodb()
    if not client:
        return
    
    # Step 2: Check database structure
    print("\n2. Checking database structure...")
    collections = check_database_structure(client)
    
    # Step 3: Check devices collection
    print("\n3. Checking devices collection...")
    check_devices_collection(client)
    
    # Step 4: Check events collection
    print("\n4. Checking events collection...")
    check_events_collection(client)
    
    # Step 5: Summary
    print("\n" + "=" * 50)
    print("🎯 DATABASE STRUCTURE SUMMARY")
    print("=" * 50)
    
    if 'devices' in collections:
        print("✅ Devices collection exists")
    else:
        print("❌ Devices collection not found")
        print("💡 We may need to create it or use a different collection name")
    
    # Close connection
    client.close()
    print("\n✅ Database connection closed")

if __name__ == "__main__":
    main() 