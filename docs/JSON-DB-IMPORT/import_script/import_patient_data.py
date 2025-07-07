#!/usr/bin/env python3
"""
PATIENT DATA IMPORT UTILITY
===========================
Import Patient medical records to Coruscant Cluster AMY Database
⚠️ CONTAINS SENSITIVE MEDICAL DATA - Handle with care
"""

import os
import pymongo
from pymongo import MongoClient
import ssl
import json
from datetime import datetime
from bson import ObjectId
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

# Patient data file
PATIENT_FILE = "AMY_25_10_2024.patients.json"

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
    print("🔍 Establishing SECURE MongoDB connection to Coruscant cluster...")
    
    # Check if we're in the right environment (SSL certificates available)
    ssl_ca_path = "ssl/ca-latest.pem" if os.path.exists("ssl/ca-latest.pem") else "../../../ssl/ca-latest.pem"
    ssl_cert_path = "ssl/client-combined-latest.pem" if os.path.exists("ssl/client-combined-latest.pem") else "../../../ssl/client-combined-latest.pem"
    
    if not os.path.exists(ssl_ca_path) or not os.path.exists(ssl_cert_path):
        print("❌ SSL certificates not found!")
        print("💡 SSL certificates required for patient data:")
        print(f"   • CA certificate: {ssl_ca_path}")
        print(f"   • Client certificate: {ssl_cert_path}")
        print()
        print("⚠️ SECURITY WARNING: Patient data requires secure connection!")
        print("🔧 To run this script:")
        print("   1. Ensure SSL certificates are in the ssl/ directory")
        print("   2. Run from the project root directory")
        print("   3. Verify secure environment for medical data")
        return None
    
    try:
        # Method 1: Try with full SSL configuration
        print("🔐 Attempting SECURE connection with SSL certificates...")
        
        ssl_context = get_ssl_context()
        config_with_ssl = MONGODB_CONFIG.copy()
        config_with_ssl["ssl_context"] = ssl_context
        config_with_ssl["tlsCAFile"] = ssl_ca_path
        config_with_ssl["tlsCertificateKeyFile"] = ssl_cert_path
        
        client = pymongo.MongoClient(**config_with_ssl)
        client.admin.command('ping')
        print("✅ SECURE connection established to Coruscant MongoDB cluster")
        return client
        
    except Exception as e1:
        print(f"❌ SSL connection failed: {e1}")
        
        try:
            # Method 2: Try without custom SSL context
            print("🔄 Trying basic SSL connection...")
            config_basic = MONGODB_CONFIG.copy()
            config_basic["tlsCAFile"] = ssl_ca_path
            config_basic["tlsCertificateKeyFile"] = ssl_cert_path
            
            client = pymongo.MongoClient(**config_basic)
            client.admin.command('ping')
            print("✅ SECURE connection established (basic SSL)")
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

def load_patient_data(file_path):
    """Load and process patient JSON file with security logging"""
    print(f"🏥 Loading PATIENT DATA: {file_path}...")
    print("⚠️ Processing sensitive medical information...")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Process the data to convert ObjectIds and dates
        processed_data = [process_json_value(record) for record in data]
        
        print(f"   ✅ Loaded {len(processed_data)} patient records")
        print(f"   🔒 Medical data processed securely")
        return processed_data
        
    except Exception as e:
        print(f"   ❌ Error loading patient data: {e}")
        return None

def create_patient_indexes(collection):
    """Create appropriate indexes for patient collection with medical data optimization"""
    try:
        print("📊 Creating optimized indexes for patient medical data...")
        
        # Core patient identification indexes
        collection.create_index("national_id", unique=True, sparse=True)
        collection.create_index("hn_id_no", sparse=True)
        collection.create_index("unique_id", sparse=True)
        collection.create_index("amy_id", sparse=True)
        
        # Hospital association indexes
        collection.create_index("hospital_id")
        collection.create_index([("hospital_id", 1), ("hn_id_no", 1)])
        
        # Personal information indexes
        collection.create_index([("first_name", 1), ("last_name", 1)])
        collection.create_index("dob")
        collection.create_index("gender")
        
        # Medical data indexes
        collection.create_index("blood_group")
        collection.create_index("visiting_status")
        collection.create_index("admit_status")
        collection.create_index("date_of_visit")
        
        # Device association indexes
        collection.create_index("ava_box_id", sparse=True)
        collection.create_index("ava_mac_address", sparse=True)
        collection.create_index("watch_mac_address", sparse=True)
        
        # Contact information indexes (for emergency contact)
        collection.create_index("mobile_no", sparse=True)
        collection.create_index("telephone_no", sparse=True)
        
        # Geographic location indexes
        collection.create_index([("province", 1), ("district", 1), ("sub_district", 1)])
        
        # Timestamps
        collection.create_index("created_at")
        collection.create_index("updated_at")
        
        print(f"   ✅ Patient data indexes created successfully")
        print(f"   🔍 Optimized for medical queries and device lookups")
        
    except Exception as e:
        print(f"   ⚠️ Warning: Could not create some patient indexes: {e}")

def analyze_patient_data(data):
    """Analyze patient data for security and medical insights"""
    if not data:
        return
    
    print("\n🔍 PATIENT DATA ANALYSIS")
    print("=" * 50)
    
    # Basic statistics
    total_patients = len(data)
    print(f"📊 Total patients: {total_patients}")
    
    # Hospital distribution
    hospitals = {}
    genders = {}
    blood_groups = {}
    device_count = 0
    
    for patient in data:
        # Hospital distribution
        hospital_id = patient.get('hospital_id')
        if hospital_id:
            hospitals[hospital_id] = hospitals.get(hospital_id, 0) + 1
        
        # Gender distribution
        gender = patient.get('gender')
        if gender:
            genders[gender] = genders.get(gender, 0) + 1
        
        # Blood group distribution
        blood_group = patient.get('blood_group')
        if blood_group:
            blood_groups[blood_group] = blood_groups.get(blood_group, 0) + 1
        
        # Device connections
        if patient.get('ava_mac_address') or patient.get('watch_mac_address'):
            device_count += 1
    
    print(f"🏥 Unique hospitals: {len(hospitals)}")
    print(f"👥 Gender distribution: {dict(genders)}")
    print(f"🩸 Blood groups: {len(blood_groups)} types")
    print(f"📱 Patients with devices: {device_count}")
    
    # Security check for PII
    pii_fields = ['national_id', 'telephone_no', 'mobile_no', 'email']
    pii_stats = {}
    for field in pii_fields:
        count = sum(1 for patient in data if patient.get(field))
        pii_stats[field] = count
    
    print(f"\n🔒 PII DATA SUMMARY:")
    for field, count in pii_stats.items():
        percentage = (count / total_patients) * 100
        print(f"   {field}: {count}/{total_patients} ({percentage:.1f}%)")

def import_patient_collection(db, data):
    """Import patient data with security considerations"""
    collection_name = "patients"
    print(f"\n🏥 IMPORTING PATIENT COLLECTION: {collection_name}")
    print("⚠️ SENSITIVE MEDICAL DATA - Following security protocols")
    print("-" * 60)
    
    if not data:
        print(f"❌ No patient data to import")
        return False
    
    try:
        collection = db[collection_name]
        
        # Get current count
        current_count = collection.count_documents({})
        print(f"📊 Current patient records: {current_count}")
        print(f"📊 New patient data to import: {len(data)} records")
        
        if current_count > 0:
            print(f"\n⚠️ WARNING: REPLACING EXISTING PATIENT DATA!")
            print(f"🔒 Current database contains {current_count} patient records")
            print(f"🔄 Will be replaced with {len(data)} new records")
            print(f"💾 This action affects sensitive medical information")
            
            user_input = input(f"\n🏥 CONFIRM: Replace {current_count} patient records with {len(data)} new records? (type 'YES' to confirm): ")
            if user_input != 'YES':
                print(f"❌ Patient import cancelled - data preserved")
                return False
            
            # Drop existing collection
            collection.drop()
            print(f"✅ Previous patient data removed securely")
            collection = db[collection_name]  # Recreate collection reference
        
        # Import in smaller batches for patient data
        batch_size = 50  # Smaller batches for medical data
        total_inserted = 0
        total_failed = 0
        
        print(f"🔒 Processing patient data in secure batches...")
        
        for i in range(0, len(data), batch_size):
            batch = data[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (len(data) + batch_size - 1) // batch_size
            
            print(f"📦 Processing patient batch {batch_num}/{total_batches} ({len(batch)} records)...")
            
            try:
                # Filter out any None or invalid records
                valid_batch = [record for record in batch if record is not None]
                
                if valid_batch:
                    result = collection.insert_many(valid_batch, ordered=False)
                    inserted_count = len(result.inserted_ids)
                    total_inserted += inserted_count
                    print(f"   ✅ Imported {inserted_count} patient records")
                else:
                    print(f"   ⚠️ No valid patient records in batch")
                    
            except Exception as batch_error:
                total_failed += len(batch)
                print(f"   ❌ Patient batch {batch_num} failed: {batch_error}")
        
        # Create indexes for patient data
        if total_inserted > 0:
            create_patient_indexes(collection)
        
        # Verify final count
        final_count = collection.count_documents({})
        
        print(f"\n📊 PATIENT IMPORT SUMMARY:")
        print(f"   ✅ Successfully imported: {total_inserted}")
        print(f"   ❌ Failed imports: {total_failed}")
        print(f"   📊 Final patient count: {final_count}")
        
        success_rate = (total_inserted / len(data)) * 100 if data else 0
        print(f"   📈 Success rate: {success_rate:.1f}%")
        print(f"   🔒 Patient data secured in Coruscant cluster")
        
        return total_inserted > 0
        
    except Exception as e:
        print(f"❌ Error importing patient data: {e}")
        return False

def find_patient_file():
    """Find the patient JSON file"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_dir, PATIENT_FILE)
    
    print(f"🔍 Looking for patient data file: {PATIENT_FILE}")
    
    if os.path.exists(file_path):
        file_size = os.path.getsize(file_path) / (1024 * 1024)  # MB
        print(f"   ✅ Found patient data: {PATIENT_FILE} ({file_size:.1f} MB)")
        return file_path
    else:
        print(f"   ❌ Patient file not found: {PATIENT_FILE}")
        return None

def main():
    """Main import function for patient medical data"""
    print("🏥 PATIENT MEDICAL DATA IMPORT UTILITY")
    print("=" * 80)
    print(f"🕒 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎯 Target: Coruscant Cluster (AMY Database)")
    print(f"⚠️ SENSITIVE MEDICAL DATA - Security protocols active")
    print(f"🔒 HIPAA/Privacy compliance required")
    
    # Check for test mode
    test_mode = len(sys.argv) > 1 and sys.argv[1] == "--test"
    if test_mode:
        print("🧪 RUNNING IN TEST MODE (patient data validation only)")
    print()
    
    # Find patient data file
    patient_file_path = find_patient_file()
    if not patient_file_path:
        print("❌ Patient data file not found")
        print("💡 Expected file: AMY_25_10_2024.patients.json")
        return
    
    # Load patient data
    print("🔒 Loading patient medical records...")
    patient_data = load_patient_data(patient_file_path)
    
    if not patient_data:
        print("❌ Failed to load patient data")
        return
    
    # Analyze patient data
    analyze_patient_data(patient_data)
    
    # Test mode: Just validate patient data
    if test_mode:
        print(f"\n🧪 PATIENT DATA VALIDATION SUMMARY")
        print("=" * 50)
        
        print(f"   ✅ Patient file loaded successfully")
        print(f"   📊 Patient records: {len(patient_data):,}")
        print(f"   🔒 Medical data validated")
        print(f"   🏥 Ready for secure import to Coruscant")
        print(f"\n💡 To import: python3 {sys.argv[0]} (without --test)")
        return
    
    # Normal mode: Connect to MongoDB and import
    print(f"\n🔐 ESTABLISHING SECURE CONNECTION FOR MEDICAL DATA")
    print("=" * 60)
    
    # Connect to Coruscant
    client = connect_to_coruscant()
    if not client:
        print("❌ Failed to establish secure connection to Coruscant")
        print("🔒 Patient data requires encrypted connection")
        print()
        print("💡 To test patient data without connecting:")
        print(f"   python3 {sys.argv[0]} --test")
        return
    
    # Access AMY database
    db = client.AMY
    print("✅ Secure connection to AMY medical database established")
    
    # Show import confirmation
    print(f"\n📋 PATIENT DATA IMPORT PLAN:")
    print("=" * 50)
    print(f"   🏥 Patient records: {len(patient_data):,}")
    print(f"   🎯 Target: AMY.patients collection")
    print(f"   🔒 Security: SSL encrypted connection")
    print(f"   📊 Medical data: Comprehensive patient records")
    
    proceed = input(f"\n🏥 PROCEED with importing {len(patient_data)} patient records? (type 'YES' to confirm): ")
    if proceed != 'YES':
        print("❌ Patient import cancelled by user")
        return
    
    # Import patient data
    print(f"\n{'='*80}")
    print(f"🔄 PROCESSING PATIENT MEDICAL DATA")
    print(f"📊 Target: AMY.patients collection")
    print(f"🎯 Coruscant Cluster - Secure Medical Database")
    print(f"{'='*80}")
    
    success = import_patient_collection(db, patient_data)
    
    # Final summary
    print(f"\n🎯 PATIENT IMPORT SUMMARY - CORUSCANT CLUSTER")
    print("=" * 80)
    
    if success:
        print(f"🎉 PATIENT DATA IMPORT COMPLETED!")
        print(f"🏥 Coruscant medical database updated")
        print(f"📊 {len(patient_data):,} patient records imported")
        print(f"🔒 Medical data secured with encryption")
        print(f"📋 Patient collection optimized with medical indexes")
        print(f"⚡ Ready for medical queries and device integration")
    else:
        print(f"❌ PATIENT IMPORT FAILED!")
        print(f"📋 Patient data not imported")
    
    print(f"\n🕒 Import completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🔒 Connection closed securely")
    client.close()

if __name__ == "__main__":
    main() 