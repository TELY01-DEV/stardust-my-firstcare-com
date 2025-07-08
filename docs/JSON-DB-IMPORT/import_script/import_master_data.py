#!/usr/bin/env python3
"""
MASTER DATA IMPORT UTILITY
=========================
Import Blood Groups, Human Skin Colors, and Nations master data to Coruscant Database
"""

import os
import pymongo
from pymongo import MongoClient
import ssl
import json
from datetime import datetime
from bson import ObjectId

# Production configuration for Coruscant cluster
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

# Master data files to import
MASTER_DATA_FILES = {
    "blood_groups": {
        "file": "AMY_25_10_2024.blood_groups.json",
        "collection": "blood_groups",
        "description": "Blood Group Types"
    },
    "human_skin_colors": {
        "file": "AMY_25_10_2024.human_skin_colors.json", 
        "collection": "human_skin_colors",
        "description": "Human Skin Color Classifications"
    },
    "nations": {
        "file": "AMY_25_10_2024.nations.json",
        "collection": "nations", 
        "description": "Country/Nation Data"
    }
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
    """Get MongoDB client for production environment with SSL"""
    print("🔍 Establishing MongoDB connection to Coruscant...")
    
    try:
        # Method 1: Try with full SSL configuration
        print("🔐 Attempting connection with SSL certificates...")
        
        ssl_context = get_ssl_context()
        config_with_ssl = MONGODB_CONFIG.copy()
        config_with_ssl["ssl_context"] = ssl_context
        
        client = pymongo.MongoClient(**config_with_ssl)
        client.admin.command('ping')
        print("✅ Connected to production MongoDB cluster with SSL")
        return client
        
    except Exception as e1:
        print(f"❌ SSL connection failed: {e1}")
        
        try:
            # Method 2: Try without custom SSL context
            print("🔄 Trying connection with basic SSL...")
            client = pymongo.MongoClient(**MONGODB_CONFIG)
            client.admin.command('ping')
            print("✅ Connected to production MongoDB cluster (basic SSL)")
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

def import_collection(db, collection_name, data, description):
    """Import data into a specific collection"""
    print(f"\n📊 IMPORTING: {description}")
    print(f"📊 Collection: {collection_name}")
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

def analyze_current_data(db):
    """Analyze current master data in database"""
    print(f"\n📊 CURRENT MASTER DATA ANALYSIS")
    print("=" * 60)
    
    current_data = {}
    for data_type, config in MASTER_DATA_FILES.items():
        collection_name = config["collection"]
        description = config["description"]
        
        try:
            collection = db[collection_name]
            count = collection.count_documents({})
            current_data[data_type] = count
            print(f"📊 {description:30} | {collection_name:20} | {count:8,} records")
        except Exception as e:
            current_data[data_type] = 0
            print(f"❌ {description:30} | {collection_name:20} | Error: {e}")
    
    return current_data

def main():
    """Main import function for master data"""
    print("🚀 MASTER DATA IMPORT UTILITY")
    print("=" * 80)
    print(f"🕒 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📅 Importing AMY data from: October 25, 2024")
    print(f"📂 Source directory: docs/JSON-DB-IMPORT/import_script/")
    print()
    
    # Check if files exist
    script_dir = "docs/JSON-DB-IMPORT/import_script"
    missing_files = []
    
    for data_type, config in MASTER_DATA_FILES.items():
        file_path = os.path.join(script_dir, config["file"])
        if not os.path.exists(file_path):
            missing_files.append(config["file"])
            
    if missing_files:
        print("❌ Missing required files:")
        for missing_file in missing_files:
            print(f"   • {missing_file}")
        return
    
    print("✅ All required master data files found")
    
    # Connect to MongoDB
    client = connect_to_mongodb()
    if not client:
        print("❌ Failed to connect to MongoDB")
        return
    
    # Access AMY database
    db = client.AMY
    print("✅ Connected to AMY database")
    
    # Analyze current data
    current_data = analyze_current_data(db)
    
    # Show import plan
    print(f"\n📋 IMPORT PLAN:")
    print("=" * 50)
    total_new_records = 0
    
    for data_type, config in MASTER_DATA_FILES.items():
        file_path = os.path.join(script_dir, config["file"])
        description = config["description"]
        
        # Get file size
        file_size = os.path.getsize(file_path) / 1024  # KB
        
        # Preview record count
        data = load_json_file(file_path)
        record_count = len(data) if data else 0
        total_new_records += record_count
        
        current_count = current_data.get(data_type, 0)
        change = record_count - current_count
        change_indicator = "📈" if change > 0 else "📉" if change < 0 else "➡️"
        
        print(f"   {change_indicator} {description:30} | Current: {current_count:6,} | New: {record_count:6,} | Change: {change:+6,} | ({file_size:.1f} KB)")
    
    print(f"\n📊 Total records to import: {total_new_records:,}")
    proceed = input(f"\n🎯 Proceed with importing master data? (type 'YES' to confirm): ")
    if proceed != 'YES':
        print("❌ Import cancelled by user")
        return
    
    # Import each collection
    import_results = {}
    
    for data_type, config in MASTER_DATA_FILES.items():
        file_path = os.path.join(script_dir, config["file"])
        collection_name = config["collection"]
        description = config["description"]
        
        print(f"\n{'='*80}")
        print(f"🔄 PROCESSING: {config['file']}")
        print(f"📊 Collection: AMY.{collection_name}")
        print(f"📝 Description: {description}")
        print(f"{'='*80}")
        
        # Load JSON data
        data = load_json_file(file_path)
        
        if data is not None:
            # Import the collection
            success = import_collection(db, collection_name, data, description)
            import_results[data_type] = {
                'success': success,
                'records': len(data) if data else 0,
                'collection': collection_name,
                'description': description
            }
        else:
            import_results[data_type] = {
                'success': False,
                'records': 0,
                'collection': collection_name,
                'description': description,
                'error': 'Failed to load JSON'
            }
    
    # Final summary
    print(f"\n🎯 MASTER DATA IMPORT SUMMARY")
    print("=" * 80)
    
    successful_imports = 0
    failed_imports = 0
    total_records = 0
    
    for data_type, result in import_results.items():
        status = "✅ SUCCESS" if result['success'] else "❌ FAILED"
        records = result['records']
        description = result['description']
        total_records += records
        
        if result['success']:
            successful_imports += 1
        else:
            failed_imports += 1
        
        print(f"   {status:12} | {description:30} | {records:8,} records")
    
    print(f"\n📊 OVERALL STATISTICS:")
    print(f"   ✅ Successful imports: {successful_imports}")
    print(f"   ❌ Failed imports: {failed_imports}")
    print(f"   📊 Total records processed: {total_records:,}")
    
    success_rate = (successful_imports / len(import_results)) * 100 if import_results else 0
    print(f"   📈 Success rate: {success_rate:.1f}%")
    
    if successful_imports > 0:
        print(f"\n🎉 MASTER DATA IMPORT COMPLETED!")
        print(f"📋 {successful_imports} collections successfully updated")
        print(f"💾 Total records imported: {total_records:,}")
        print(f"📅 Master data now updated with October 25, 2024 data")
        
        # Show collections created
        print(f"\n📋 COLLECTIONS UPDATED:")
        for data_type, result in import_results.items():
            if result['success']:
                collection_name = result['collection']
                records = result['records']
                description = result['description']
                print(f"   • AMY.{collection_name}: {records:,} {description.lower()}")
    else:
        print(f"\n❌ IMPORT FAILED!")
        print(f"📋 No collections were successfully imported")
    
    print(f"\n🕒 Import completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    client.close()

if __name__ == "__main__":
    main() 