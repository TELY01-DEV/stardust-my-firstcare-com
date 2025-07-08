import json
import os
from datetime import datetime
from bson import ObjectId
import pymongo
from pymongo import MongoClient
import ssl

# MongoDB connection configuration for Coruscant cluster - using opera_admin
MONGODB_CONFIG = {
    "host": "coruscant.my-firstcare.com",
    "port": 27023,
    "username": "opera_admin",
    "password": "Sim!443355",
    "authSource": "admin",
    "tls": True,
    "tlsAllowInvalidCertificates": True,
    "tlsAllowInvalidHostnames": True,
    "serverSelectionTimeoutMS": 15000,
    "connectTimeoutMS": 15000,
}

DATABASE_NAME = "amy"
COLLECTION_NAME = "hospital_users"

class HospitalUserImporter:
    def __init__(self):
        self.client = None
        self.db = None
        self.collection = None
        self.imported_count = 0
        self.error_count = 0
        
    def connect(self):
        """Connect to MongoDB with SSL configuration"""
        try:
            print("🔍 Establishing MongoDB connection to Coruscant...")
            self.client = pymongo.MongoClient(**MONGODB_CONFIG)
            self.db = self.client[DATABASE_NAME]
            self.collection = self.db[COLLECTION_NAME]
            
            # Test connection
            self.client.admin.command('ping')
            print(f"✅ Connected to MongoDB cluster: {DATABASE_NAME}")
            
        except Exception as e:
            print(f"❌ Failed to connect to MongoDB: {e}")
            raise
    
    def convert_object_ids(self, document):
        """Convert ObjectId strings to actual ObjectId objects"""
        if "_id" in document and "$oid" in document["_id"]:
            document["_id"] = ObjectId(document["_id"]["$oid"])
        
        if "hospital_id" in document and isinstance(document["hospital_id"], dict) and "$oid" in document["hospital_id"]:
            document["hospital_id"] = ObjectId(document["hospital_id"]["$oid"])
        
        if "type" in document and isinstance(document["type"], dict) and "$oid" in document["type"]:
            document["type"] = ObjectId(document["type"]["$oid"])
        
        return document
    
    def convert_dates(self, document):
        """Convert date strings to datetime objects"""
        date_fields = ["created_at", "updated_at"]
        
        for field in date_fields:
            if field in document and isinstance(document[field], dict) and "$date" in document[field]:
                try:
                    date_str = document[field]["$date"]
                    # Parse ISO date string
                    document[field] = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                except ValueError as e:
                    print(f"⚠️  Failed to parse date for field {field}: {e}")
                    document[field] = datetime.utcnow()
        
        return document
    
    def clean_document(self, document):
        """Clean and validate document data"""
        # Convert ObjectIds
        document = self.convert_object_ids(document)
        
        # Convert dates
        document = self.convert_dates(document)
        
        # Ensure required fields have default values
        defaults = {
            "server_token": "",
            "device_token": "",
            "device_type": "",
            "app_version": "",
            "image_url": "",
            "country_phone_code": "+66",
            "country_code": "Th",
            "country_name": "Thailand",
            "user_title": "Mr.",
            "__v": 0
        }
        
        for field, default_value in defaults.items():
            if field not in document:
                document[field] = default_value
        
        # Validate required fields
        required_fields = ["email", "first_name", "last_name", "hospital_id", "type"]
        for field in required_fields:
            if field not in document or document[field] is None:
                raise ValueError(f"Missing required field: {field}")
        
        return document
    
    def import_batch(self, documents):
        """Import a batch of documents"""
        try:
            if not documents:
                return 0
            
            # Clean documents
            cleaned_docs = []
            for doc in documents:
                try:
                    cleaned_doc = self.clean_document(doc.copy())
                    cleaned_docs.append(cleaned_doc)
                except Exception as e:
                    print(f"⚠️  Skipping invalid document: {e}")
                    self.error_count += 1
                    continue
            
            if not cleaned_docs:
                return 0
            
            # Insert batch with upsert to handle duplicates
            operations = []
            for doc in cleaned_docs:
                operations.append(pymongo.ReplaceOne(
                    filter={"_id": doc["_id"]},
                    replacement=doc,
                    upsert=True
                ))
            
            result = self.collection.bulk_write(operations, ordered=False)
            imported_count = result.upserted_count + result.modified_count
            
            print(f"✅ Imported batch: {imported_count} hospital users")
            return imported_count
            
        except Exception as e:
            print(f"❌ Failed to import batch: {e}")
            self.error_count += len(documents)
            return 0
    
    def import_hospital_users(self, file_path):
        """Import hospital users from JSON file"""
        try:
            print(f"📂 Loading hospital users data from: {file_path}")
            
            with open(file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
            
            if not isinstance(data, list):
                raise ValueError("JSON file must contain an array of hospital user documents")
            
            total_records = len(data)
            print(f"📊 Found {total_records} hospital user records to import")
            
            # Process in batches of 50
            batch_size = 50
            for i in range(0, total_records, batch_size):
                batch = data[i:i + batch_size]
                batch_num = (i // batch_size) + 1
                total_batches = (total_records + batch_size - 1) // batch_size
                
                print(f"🔄 Processing batch {batch_num}/{total_batches} ({len(batch)} records)")
                
                imported = self.import_batch(batch)
                self.imported_count += imported
                
                # Progress update
                progress = ((i + len(batch)) / total_records) * 100
                print(f"📈 Progress: {progress:.1f}% - Imported: {self.imported_count}, Errors: {self.error_count}")
            
            # Final summary
            print(f"\n🎉 Import completed!")
            print(f"📊 Total records processed: {total_records}")
            print(f"✅ Successfully imported: {self.imported_count}")
            print(f"❌ Errors: {self.error_count}")
            print(f"📈 Success rate: {(self.imported_count/total_records)*100:.1f}%")
            
            # Verify collection count
            total_in_db = self.collection.count_documents({})
            print(f"🗄️  Total hospital users in database: {total_in_db}")
            
        except Exception as e:
            print(f"❌ Import failed: {e}")
            raise
    
    def create_indexes(self):
        """Create indexes for better query performance"""
        try:
            print("📇 Creating database indexes...")
            
            indexes = [
                # Single field indexes
                ("email", 1),
                ("hospital_id", 1),
                ("type", 1),
                ("first_name", 1),
                ("last_name", 1),
                ("phone", 1),
                ("unique_id", 1),
                ("created_at", 1),
                
                # Compound indexes
                [("hospital_id", 1), ("type", 1)],
                [("hospital_id", 1), ("email", 1)],
                [("first_name", 1), ("last_name", 1)],
            ]
            
            for index in indexes:
                if isinstance(index, tuple):
                    self.collection.create_index([index])
                else:
                    self.collection.create_index(index)
            
            print("✅ Indexes created successfully")
            
        except Exception as e:
            print(f"⚠️  Failed to create indexes: {e}")
    
    def close(self):
        """Close database connection"""
        if self.client:
            self.client.close()
            print("🔌 Database connection closed")

def main():
    """Main import function"""
    importer = HospitalUserImporter()
    
    try:
        # Connect to database
        importer.connect()
        
        # Import data
        file_path = "AMY_25_10_2024.hospital_users.json"
        importer.import_hospital_users(file_path)
        
        # Create indexes
        importer.create_indexes()
        
    except Exception as e:
        print(f"💥 Import process failed: {e}")
        return 1
    finally:
        importer.close()
    
    return 0

if __name__ == "__main__":
    import sys
    exit_code = main()
    sys.exit(exit_code) 