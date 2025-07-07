#!/usr/bin/env python3
"""
GEOGRAPHIC & HOSPITAL DATA IMPORT UTILITY
=========================================
Import Province, District, Sub-district, and Hospital data to Coruscant Cluster
"""

import os
import pymongo
from pymongo import MongoClient
import ssl
import json
from datetime import datetime
from bson import ObjectId
import glob
import sys

# Coruscant Production configuration
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

# Target collections for geographic and hospital data
TARGET_COLLECTIONS = {
    "provinces": "AMY_25_10_2024.provinces.json",
    "districts": "AMY_25_10_2024.districts.json", 
    "sub_districts": "AMY_25_10_2024.sub_districts.json",
    "hospitals": "AMY_25_10_2024.hospitals.json"
}

def get_ssl_context():
    """Create SSL context for MongoDB connection"""
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    
    # Try different SSL certificate paths
    ssl_ca_path = "ssl/ca-latest.pem" if os.path.exists("ssl/ca-latest.pem") else "../../../ssl/ca-latest.pem"
    ssl_cert_path = "ssl/client-combined-latest.pem" if os.path.exists("ssl/client-combined-latest.pem") else "../../../ssl/client-combined-latest.pem"
    
    # Load CA certificate if available
    if os.path.exists(ssl_ca_path):
        context.load_verify_locations(ssl_ca_path)
        print(f"🔒 Loaded CA certificate from {ssl_ca_path}")
    
    # Load client certificate if available
    if os.path.exists(ssl_cert_path):
        context.load_cert_chain(ssl_cert_path)
        print(f"🔐 Loaded client certificate from {ssl_cert_path}")
    
    return context

def connect_to_coruscant():
    """Get MongoDB client for Coruscant cluster with SSL"""
    print("🔍 Establishing MongoDB connection to Coruscant cluster...")
    
    # Check if we're in the right environment (SSL certificates available)
    ssl_ca_path = "ssl/ca-latest.pem" if os.path.exists("ssl/ca-latest.pem") else "../../../ssl/ca-latest.pem"
    ssl_cert_path = "ssl/client-combined-latest.pem" if os.path.exists("ssl/client-combined-latest.pem") else "../../../ssl/client-combined-latest.pem"
    
    if not os.path.exists(ssl_ca_path) or not os.path.exists(ssl_cert_path):
        print("❌ SSL certificates not found!")
        print("💡 SSL certificates required:")
        print(f"   • CA certificate: {ssl_ca_path}")
        print(f"   • Client certificate: {ssl_cert_path}")
        print()
        print("🔧 To run this script:")
        print("   1. Copy this script to your server environment")
        print("   2. Ensure SSL certificates are in the ssl/ directory")
        print("   3. Run from the project root directory")
        print()
        print("🌐 Or run from server with:")
        print("   cd /path/to/stardust-my-firstcare-com")
        print("   python3 docs/JSON-DB-IMPORT/import_script/import_geo_hospital_data.py")
        return None
    
    try:
        # Method 1: Try with full SSL configuration
        print("🔐 Attempting connection with SSL certificates...")
        
        ssl_context = get_ssl_context()
        config_with_ssl = MONGODB_CONFIG.copy()
        config_with_ssl["ssl_context"] = ssl_context
        config_with_ssl["tlsCAFile"] = ssl_ca_path
        config_with_ssl["tlsCertificateKeyFile"] = ssl_cert_path
        
        client = pymongo.MongoClient(**config_with_ssl)
        client.admin.command('ping')
        print("✅ Connected to Coruscant MongoDB cluster with SSL")
        return client
        
    except Exception as e1:
        print(f"❌ SSL connection failed: {e1}")
        
        try:
            # Method 2: Try without custom SSL context
            print("🔄 Trying connection with basic SSL...")
            config_basic = MONGODB_CONFIG.copy()
            config_basic["tlsCAFile"] = ssl_ca_path
            config_basic["tlsCertificateKeyFile"] = ssl_cert_path
            
            client = pymongo.MongoClient(**config_basic)
            client.admin.command('ping')
            print("✅ Connected to Coruscant MongoDB cluster (basic SSL)")
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

def create_indexes_for_collection(collection, collection_name):
    """Create appropriate indexes for each collection type"""
    try:
        if collection_name == "provinces":
            # Index for province queries
            collection.create_index("province_code", unique=True)
            collection.create_index("province_name")
            print(f"   📊 Created indexes for {collection_name}")
            
        elif collection_name == "districts":
            # Index for district queries
            collection.create_index([("province_code", 1), ("district_code", 1)], unique=True)
            collection.create_index("district_name")
            collection.create_index("province_code")
            print(f"   📊 Created indexes for {collection_name}")
            
        elif collection_name == "sub_districts":
            # Index for sub-district queries
            collection.create_index([("province_code", 1), ("district_code", 1), ("sub_district_code", 1)], unique=True)
            collection.create_index("sub_district_name")
            collection.create_index([("province_code", 1), ("district_code", 1)])
            print(f"   📊 Created indexes for {collection_name}")
            
        elif collection_name == "hospitals":
            # Index for hospital queries
            collection.create_index("hospital_code", unique=True)
            collection.create_index("hospital_name")
            collection.create_index("province_code")
            collection.create_index([("province_code", 1), ("district_code", 1)])
            collection.create_index("hospital_type")
            collection.create_index("is_active")
            print(f"   📊 Created indexes for {collection_name}")
            
    except Exception as e:
        print(f"   ⚠️  Warning: Could not create some indexes for {collection_name}: {e}")

def import_collection(db, collection_name, data, create_indexes=True):
    """Import data into a specific collection with proper indexing"""
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
        
        if current_count > 0:
            user_input = input(f"\n⚠️  REPLACE existing {collection_name} collection ({current_count} docs) with {len(data)} new docs? (type 'YES' to confirm): ")
            if user_input != 'YES':
                print(f"❌ Import cancelled for {collection_name}")
                return False
            
            # Drop existing collection
            collection.drop()
            print(f"✅ Dropped existing {collection_name} collection")
            collection = db[collection_name]  # Recreate collection reference
        
        # Import in batches
        batch_size = 1000  # Larger batch size for geographic data
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
        
        # Create indexes after importing data
        if create_indexes and total_inserted > 0:
            print(f"📊 Creating indexes for {collection_name}...")
            create_indexes_for_collection(collection, collection_name)
        
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

def find_json_files():
    """Find the target JSON files in the current directory"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    found_files = {}
    
    print(f"🔍 Looking for JSON files in: {current_dir}")
    
    for collection_name, filename in TARGET_COLLECTIONS.items():
        file_path = os.path.join(current_dir, filename)
        if os.path.exists(file_path):
            file_size = os.path.getsize(file_path) / (1024 * 1024)  # MB
            found_files[collection_name] = file_path
            print(f"   ✅ Found {filename} → {collection_name} ({file_size:.1f} MB)")
        else:
            print(f"   ❌ Missing {filename}")
    
    return found_files

def get_import_preview(client, found_files):
    """Preview what will be imported"""
    print(f"\n📊 IMPORT PREVIEW")
    print("=" * 60)
    
    db = client.AMY
    preview_data = {}
    
    for collection_name, file_path in found_files.items():
        try:
            # Get current count in database
            collection = db[collection_name]
            current_count = collection.count_documents({})
            
            # Get count in new JSON file (quick check)
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                new_count = len(data) if data else 0
            
            preview_data[collection_name] = {
                'current': current_count,
                'new': new_count,
                'change': new_count - current_count,
                'file': os.path.basename(file_path)
            }
            
            change_indicator = "📈" if new_count > current_count else "📉" if new_count < current_count else "➡️"
            print(f"{change_indicator} {collection_name:15} | Current: {current_count:8,} | New: {new_count:8,} | Change: {new_count-current_count:+8,}")
            
        except Exception as e:
            print(f"❌ {collection_name:15} | Error: {e}")
            preview_data[collection_name] = {'error': str(e)}
    
    return preview_data

def main():
    """Main import function for geographic and hospital data"""
    print("🏥 GEOGRAPHIC & HOSPITAL DATA IMPORT UTILITY")
    print("=" * 80)
    print(f"🕒 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎯 Target: Coruscant Cluster (AMY Database)")
    print(f"📋 Collections: Provinces, Districts, Sub-districts, Hospitals")
    
    # Check for test mode
    test_mode = len(sys.argv) > 1 and sys.argv[1] == "--test"
    if test_mode:
        print("🧪 RUNNING IN TEST MODE (JSON validation only)")
    print()
    
    # Find target JSON files
    found_files = find_json_files()
    
    if not found_files:
        print("❌ No target JSON files found")
        print("💡 Expected files:")
        for collection_name, filename in TARGET_COLLECTIONS.items():
            print(f"   • {filename}")
        return
    
    if len(found_files) != len(TARGET_COLLECTIONS):
        missing = set(TARGET_COLLECTIONS.keys()) - set(found_files.keys())
        print(f"⚠️  Warning: Missing files for collections: {', '.join(missing)}")
        if not test_mode:
            proceed = input("Continue with available files? (type 'YES' to confirm): ")
            if proceed != 'YES':
                print("❌ Import cancelled")
                return
    
    # Test mode: Just validate JSON files
    if test_mode:
        print("\n🧪 JSON FILE VALIDATION")
        print("=" * 50)
        
        validation_results = {}
        for collection_name, file_path in found_files.items():
            print(f"\n📊 Validating {collection_name}...")
            data = load_json_file(file_path)
            
            if data is not None:
                validation_results[collection_name] = {
                    'valid': True,
                    'count': len(data),
                    'sample': data[0] if data else None
                }
                print(f"   ✅ Valid JSON with {len(data):,} records")
                
                # Show sample record structure
                if data and len(data) > 0:
                    sample = data[0]
                    if isinstance(sample, dict):
                        print(f"   📝 Sample record fields: {list(sample.keys())}")
                    else:
                        print(f"   📝 Sample record type: {type(sample).__name__}")
            else:
                validation_results[collection_name] = {
                    'valid': False,
                    'count': 0,
                    'error': 'Failed to load JSON'
                }
        
        # Summary
        print(f"\n📊 VALIDATION SUMMARY")
        print("=" * 50)
        valid_files = sum(1 for r in validation_results.values() if r['valid'])
        total_records = sum(r['count'] for r in validation_results.values() if r['valid'])
        
        for collection_name in ["provinces", "districts", "sub_districts", "hospitals"]:
            if collection_name in validation_results:
                result = validation_results[collection_name]
                status = "✅ VALID" if result['valid'] else "❌ INVALID"
                count = result['count']
                print(f"   {status:12} | {collection_name:15} | {count:8,} records")
        
        print(f"\n📈 Validation Results:")
        print(f"   ✅ Valid files: {valid_files}/{len(validation_results)}")
        print(f"   📊 Total records: {total_records:,}")
        
        if valid_files == len(validation_results):
            print(f"\n🎉 ALL JSON FILES ARE VALID!")
            print(f"📋 Ready for import to Coruscant cluster")
            print(f"💡 To import: python3 {sys.argv[0]} (without --test)")
        else:
            print(f"\n❌ VALIDATION FAILED!")
            print(f"📋 Fix invalid files before importing")
        
        return
    
    # Normal mode: Connect to MongoDB and import
    # Connect to Coruscant
    client = connect_to_coruscant()
    if not client:
        print("❌ Failed to connect to Coruscant MongoDB cluster")
        print()
        print("💡 To test JSON files without connecting:")
        print(f"   python3 {sys.argv[0]} --test")
        return
    
    # Access AMY database
    db = client.AMY
    print("✅ Connected to AMY database on Coruscant")
    
    # Preview import
    preview_data = get_import_preview(client, found_files)
    
    # Show import plan
    print(f"\n📋 IMPORT PLAN:")
    print("=" * 50)
    total_new_records = 0
    import_order = ["provinces", "districts", "sub_districts", "hospitals"]  # Hierarchical order
    
    for collection_name in import_order:
        if collection_name in found_files:
            preview = preview_data.get(collection_name, {})
            new_count = preview.get('new', 0)
            total_new_records += new_count
            filename = TARGET_COLLECTIONS[collection_name]
            print(f"   {collection_name:15} ← {filename} ({new_count:,} records)")
    
    print(f"\n📊 Total records to import: {total_new_records:,}")
    proceed = input(f"\n🎯 Proceed with importing to Coruscant cluster? (type 'YES' to confirm): ")
    if proceed != 'YES':
        print("❌ Import cancelled by user")
        return
    
    # Import each collection in hierarchical order
    import_results = {}
    
    for collection_name in import_order:
        if collection_name not in found_files:
            continue
            
        file_path = found_files[collection_name]
        filename = os.path.basename(file_path)
        
        print(f"\n{'='*80}")
        print(f"🔄 PROCESSING: {filename}")
        print(f"📊 Target Collection: AMY.{collection_name}")
        print(f"🎯 Coruscant Cluster")
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
    print(f"\n🎯 IMPORT SUMMARY - CORUSCANT CLUSTER")
    print("=" * 80)
    
    successful_imports = 0
    failed_imports = 0
    total_records = 0
    
    for collection_name in import_order:
        if collection_name not in import_results:
            continue
            
        result = import_results[collection_name]
        status = "✅ SUCCESS" if result['success'] else "❌ FAILED"
        records = result['records']
        total_records += records
        
        if result['success']:
            successful_imports += 1
        else:
            failed_imports += 1
        
        print(f"   {status:12} | {collection_name:15} | {records:8,} records | {result['file']}")
    
    print(f"\n📊 OVERALL STATISTICS:")
    print(f"   ✅ Successful imports: {successful_imports}")
    print(f"   ❌ Failed imports: {failed_imports}")
    print(f"   📊 Total records imported: {total_records:,}")
    
    success_rate = (successful_imports / len(import_results)) * 100 if import_results else 0
    print(f"   📈 Success rate: {success_rate:.1f}%")
    
    if successful_imports > 0:
        print(f"\n🎉 GEOGRAPHIC & HOSPITAL DATA IMPORT COMPLETED!")
        print(f"🏥 Coruscant cluster AMY database updated")
        print(f"📋 {successful_imports} collections successfully imported")
        print(f"💾 Total records imported: {total_records:,}")
        
        # Show hierarchy summary
        print(f"\n📊 DATA HIERARCHY IMPORTED:")
        if 'provinces' in import_results and import_results['provinces']['success']:
            prov_count = import_results['provinces']['records']
            print(f"   🗺️  Provinces: {prov_count:,}")
        if 'districts' in import_results and import_results['districts']['success']:
            dist_count = import_results['districts']['records']
            print(f"   🏘️  Districts: {dist_count:,}")
        if 'sub_districts' in import_results and import_results['sub_districts']['success']:
            sub_count = import_results['sub_districts']['records']
            print(f"   🏙️  Sub-districts: {sub_count:,}")
        if 'hospitals' in import_results and import_results['hospitals']['success']:
            hosp_count = import_results['hospitals']['records']
            print(f"   🏥 Hospitals: {hosp_count:,}")
    else:
        print(f"\n❌ IMPORT FAILED!")
        print(f"📋 No collections were successfully imported")
    
    print(f"\n🕒 Import completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    client.close()

if __name__ == "__main__":
    main() 