#!/usr/bin/env python3
"""
AMY DATABASE IMPORT UTILITY (July 16, 2025 Data)
===============================================
Import the AMY_25_10_2024 JSON files from 16-07-25 folder to Coruscant Cluster
"""

import os
import pymongo
from pymongo import MongoClient
import ssl
import json
from datetime import datetime
from bson import ObjectId
import glob

# Production configuration for Coruscant Cluster
MONGODB_CONFIG = {
    "host": os.getenv("MONGODB_HOST", "coruscant.my-firstcare.com"),
    "port": int(os.getenv("MONGODB_PORT", 27023)),
    "username": os.getenv("MONGODB_USERNAME", "opera_admin"),
    "password": os.getenv("MONGODB_PASSWORD", "Sim!443355"),
    "authSource": os.getenv("MONGODB_AUTH_DB", "admin"),
    "tls": True,
    "tlsAllowInvalidCertificates": True,
    "tlsAllowInvalidHostnames": True,
    "tlsCAFile": "ssl/ca-latest.pem",
    "tlsCertificateKeyFile": "ssl/client-combined-latest.pem",
    "serverSelectionTimeoutMS": 15000,
    "connectTimeoutMS": 15000,
}

def get_ssl_context():
    """Create SSL context for MongoDB connection"""
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    
    # Load CA certificate if available
    if os.path.exists("ssl/ca-latest.pem"):
        context.load_verify_locations("ssl/ca-latest.pem")
        print("🔒 Loaded CA certificate")
    
    # Load client certificate if available
    if os.path.exists("ssl/client-combined-latest.pem"):
        context.load_cert_chain("ssl/client-combined-latest.pem")
        print("🔐 Loaded client certificate")
    
    return context

def connect_to_mongodb():
    """Get MongoDB client for Coruscant Cluster with SSL"""
    print("🔍 Establishing MongoDB connection to Coruscant Cluster...")
    
    try:
        # Method 1: Try with full SSL configuration
        print("🔐 Attempting connection with SSL certificates...")
        
        ssl_context = get_ssl_context()
        config_with_ssl = MONGODB_CONFIG.copy()
        config_with_ssl["ssl_context"] = ssl_context
        
        client = pymongo.MongoClient(**config_with_ssl)
        client.admin.command('ping')
        print("✅ Connected to Coruscant Cluster with SSL")
        return client
        
    except Exception as e1:
        print(f"❌ SSL connection failed: {e1}")
        
        try:
            # Method 2: Try without custom SSL context
            print("🔄 Trying connection with basic SSL...")
            client = pymongo.MongoClient(**MONGODB_CONFIG)
            client.admin.command('ping')
            print("✅ Connected to Coruscant Cluster (basic SSL)")
            return client
            
        except Exception as e2:
            print(f"❌ Basic SSL connection failed: {e2}")
            return None

def process_json_value(value):
    """Process JSON values to handle ObjectId and datetime conversions"""
    if isinstance(value, dict):
        if "$oid" in value:
            return ObjectId(value["$oid"])
        elif "$date" in value:
            date_str = value["$date"]
            try:
                # Handle ISO format dates
                if date_str.endswith('Z'):
                    return datetime.fromisoformat(date_str[:-1])
                else:
                    return datetime.fromisoformat(date_str)
            except:
                return date_str
        else:
            # Recursively process nested dictionaries
            return {k: process_json_value(v) for k, v in value.items()}
    elif isinstance(value, list):
        # Recursively process lists
        return [process_json_value(item) for item in value]
    else:
        return value

def load_json_file(file_path):
    """Load and process JSON file"""
    print(f"📥 Loading {file_path}...")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Process the data to convert ObjectIds and dates
        processed_data = [process_json_value(record) for record in data]
        
        print(f"   ✅ Loaded {len(processed_data)} records")
        return processed_data
        
    except Exception as e:
        print(f"   ❌ Error loading {file_path}: {e}")
        return None

def get_collection_name_from_filename(filename):
    """Extract collection name from AMY_25_10_2024.* filename"""
    # Remove path
    basename = os.path.basename(filename)
    
    # Handle AMY_25_10_2024.collection_name.json format
    if basename.startswith("AMY_25_10_2024."):
        # Remove "AMY_25_10_2024." prefix
        collection_name = basename[16:]  # len("AMY_25_10_2024.") = 16
    else:
        collection_name = basename
    
    if collection_name.endswith(".json"):
        collection_name = collection_name[:-5]  # Remove ".json"
    
    return collection_name

def import_collection(db, collection_name, data, update_mode="replace"):
    """Import data into a specific collection"""
    print(f"\n📊 IMPORTING COLLECTION: {collection_name}")
    print("-" * 60)
    
    if not data:
        print(f"❌ No data to import for {collection_name}")
        return False
    
    try:
        collection = db[collection_name]
        
        # Get current count
        current_count = collection.count_documents({})
        print(f"📊 Current documents in {collection_name}: {current_count}")
        print(f"📊 New data to import: {len(data)} records")
        
        if update_mode == "replace":
            if current_count > 0:
                user_input = input(f"\n⚠️  REPLACE existing {collection_name} collection ({current_count} docs) with {len(data)} new docs? (type 'YES' to confirm): ")
                if user_input != 'YES':
                    print(f"❌ Import cancelled for {collection_name}")
                    return False
                
                # Drop existing collection
                collection.drop()
                print(f"✅ Dropped existing {collection_name} collection")
        
        # Import in batches
        batch_size = 100
        total_inserted = 0
        total_failed = 0
        
        for i in range(0, len(data), batch_size):
            batch = data[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (len(data) + batch_size - 1) // batch_size
            
            print(f"📦 Processing batch {batch_num}/{total_batches} ({len(batch)} records)...")
            
            try:
                # Filter out any None or invalid records
                valid_batch = [record for record in batch if record is not None]
                
                if valid_batch:
                    result = collection.insert_many(valid_batch, ordered=False)
                    inserted_count = len(result.inserted_ids)
                    total_inserted += inserted_count
                    print(f"   ✅ Inserted {inserted_count} records")
                else:
                    print(f"   ⚠️  No valid records in batch")
                    
            except Exception as batch_error:
                total_failed += len(batch)
                print(f"   ❌ Batch {batch_num} failed: {batch_error}")
        
        # Verify final count
        final_count = collection.count_documents({})
        
        print(f"\n📊 IMPORT SUMMARY FOR {collection_name}:")
        print(f"   ✅ Successfully inserted: {total_inserted}")
        print(f"   ❌ Failed inserts: {total_failed}")
        print(f"   📊 Final count in database: {final_count}")
        
        success_rate = (total_inserted / len(data)) * 100 if data else 0
        print(f"   📈 Success rate: {success_rate:.1f}%")
        
        return total_inserted > 0
        
    except Exception as e:
        print(f"❌ Error importing {collection_name}: {e}")
        return False

def find_16_07_25_json_files():
    """Find all AMY_25_10_2024 JSON files in the 16-07-25 folder"""
    data_path = "docs/JSON-DB-IMPORT/import_script/16-07-25"
    pattern = os.path.join(data_path, "AMY_25_10_2024.*.json")
    
    json_files = glob.glob(pattern)
    print(f"🔍 Found {len(json_files)} AMY_25_10_2024 JSON files in 16-07-25 folder:")
    
    for file_path in sorted(json_files):
        filename = os.path.basename(file_path)
        collection_name = get_collection_name_from_filename(filename)
        file_size = os.path.getsize(file_path) / (1024 * 1024)  # MB
        print(f"   • {filename} → {collection_name} ({file_size:.1f} MB)")
    
    return json_files

def get_import_differences(client, json_files):
    """Analyze differences between current database and new JSON files"""
    print(f"\n📊 ANALYZING DATA DIFFERENCES")
    print("=" * 60)
    
    db = client.AMY
    differences = {}
    
    for file_path in json_files:
        filename = os.path.basename(file_path)
        collection_name = get_collection_name_from_filename(filename)
        
        try:
            # Get current count in database
            collection = db[collection_name]
            current_count = collection.count_documents({})
            
            # Get count in new JSON file
            data = load_json_file(file_path)
            new_count = len(data) if data else 0
            
            differences[collection_name] = {
                'current': current_count,
                'new': new_count,
                'change': new_count - current_count,
                'file': filename
            }
            
            change_indicator = "📈" if new_count > current_count else "📉" if new_count < current_count else "➡️"
            print(f"{change_indicator} {collection_name:25} | Current: {current_count:8,} | New: {new_count:8,} | Change: {new_count-current_count:+8,}")
            
        except Exception as e:
            print(f"❌ {collection_name:25} | Error: {e}")
            differences[collection_name] = {'error': str(e)}
    
    return differences

def main():
    """Main import function for 16-07-25 AMY data"""
    print("🚀 AMY DATABASE IMPORT UTILITY - 16-07-25 DATA")
    print("=" * 80)
    print(f"🕒 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📅 Importing data from: 16-07-25 folder")
    print(f"🎯 Target: Coruscant Cluster AMY Database")
    print()
    
    # Find all AMY_25_10_2024 JSON files in 16-07-25 folder
    json_files = find_16_07_25_json_files()
    
    if not json_files:
        print("❌ No AMY_25_10_2024 JSON files found in 16-07-25 folder")
        print("💡 Expected files like: AMY_25_10_2024.patients.json, AMY_25_10_2024.hospitals.json, etc.")
        return
    
    # Connect to MongoDB
    client = connect_to_mongodb()
    if not client:
        print("❌ Failed to connect to Coruscant Cluster")
        return
    
    # Access AMY database
    db = client.AMY
    print("✅ Connected to AMY database on Coruscant Cluster")
    
    # Analyze differences
    differences = get_import_differences(client, json_files)
    
    # Show import plan
    print(f"\n📋 IMPORT PLAN:")
    print("=" * 50)
    total_new_records = 0
    for file_path in sorted(json_files):
        filename = os.path.basename(file_path)
        collection_name = get_collection_name_from_filename(filename)
        diff_info = differences.get(collection_name, {})
        new_count = diff_info.get('new', 0)
        total_new_records += new_count
        print(f"   {filename} → AMY.{collection_name} ({new_count:,} records)")
    
    print(f"\n📊 Total records to import: {total_new_records:,}")
    proceed = input(f"\n🎯 Proceed with importing {len(json_files)} collections to Coruscant Cluster? (type 'YES' to confirm): ")
    if proceed != 'YES':
        print("❌ Import cancelled by user")
        return
    
    # Import each collection
    import_results = {}
    
    for file_path in sorted(json_files):
        filename = os.path.basename(file_path)
        collection_name = get_collection_name_from_filename(filename)
        
        print(f"\n{'='*80}")
        print(f"🔄 PROCESSING: {filename}")
        print(f"📊 Target Collection: AMY.{collection_name}")
        print(f"{'='*80}")
        
        # Load JSON data
        data = load_json_file(file_path)
        
        if data is not None:
            # Import the collection
            success = import_collection(db, collection_name, data)
            import_results[collection_name] = {
                'success': success,
                'records': len(data) if data else 0,
                'file': filename
            }
        else:
            import_results[collection_name] = {
                'success': False,
                'records': 0,
                'file': filename,
                'error': 'Failed to load JSON'
            }
    
    # Final summary
    print(f"\n🎯 16-07-25 DATA IMPORT SUMMARY")
    print("=" * 80)
    
    successful_imports = 0
    failed_imports = 0
    total_records = 0
    
    for collection_name, result in import_results.items():
        status = "✅ SUCCESS" if result['success'] else "❌ FAILED"
        records = result['records']
        total_records += records
        
        if result['success']:
            successful_imports += 1
        else:
            failed_imports += 1
        
        print(f"   {status:12} | {collection_name:25} | {records:8,} records | {result['file']}")
    
    print(f"\n📊 OVERALL STATISTICS:")
    print(f"   ✅ Successful imports: {successful_imports}")
    print(f"   ❌ Failed imports: {failed_imports}")
    print(f"   📊 Total records processed: {total_records:,}")
    
    success_rate = (successful_imports / len(import_results)) * 100 if import_results else 0
    print(f"   📈 Success rate: {success_rate:.1f}%")
    
    if successful_imports > 0:
        print(f"\n🎉 16-07-25 DATA IMPORT COMPLETED!")
        print(f"📋 {successful_imports} collections successfully updated on Coruscant Cluster")
        print(f"💾 Total records imported: {total_records:,}")
        print(f"📅 Database now contains data as of July 16, 2025")
        
        # Show key updates
        print(f"\n📋 KEY UPDATES:")
        for collection_name, diff_info in differences.items():
            if 'change' in diff_info and diff_info['change'] != 0:
                change = diff_info['change']
                indicator = "+" if change > 0 else ""
                print(f"   • {collection_name}: {indicator}{change:,} records")
    else:
        print(f"\n❌ IMPORT FAILED!")
        print(f"📋 No collections were successfully imported")
    
    print(f"\n🕒 Import completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    client.close()

if __name__ == "__main__":
    main() 