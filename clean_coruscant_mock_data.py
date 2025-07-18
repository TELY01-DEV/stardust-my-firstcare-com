#!/usr/bin/env python3import os
import pymongo

def clean_mock_data():
    print("🧹 Cleaning mock/test data from Coruscant DB (AMY.event_logs)...")
    
    try:
        # Use the same configuration as the web panel
        mongodb_uri = os.getenv('MONGODB_URI)
        mongodb_database = os.getenv('MONGODB_DATABASE', 'AMY')
        
        if not mongodb_uri:
            print("❌ MONGODB_URI environment variable not set")
            return
        
        print(f📊 Connecting to: {mongodb_database} database")
        
        # Connect to MongoDB
        client = pymongo.MongoClient(mongodb_uri)
        db = client[mongodb_database]
        collection = db['event_logs']
        
        # Count total events
        total_events = collection.count_documents({})
        print(f"📊 Total events in collection: {total_events}")
        
        # Find mock/test events
        mock_query = [object Object]   $or                {"message": {"$regex":^Test event, $options": "i"}},
                {"message": {$regex: from qube-listener, $options": "i"}},
                {"message": {"$regex: from kati-listener, $options": "i"}},
                {"message": {$regex: from ava4-listener, $options": "i"}},
                {"message": {"$regex":from medical-monitor, $options": "i"}},
                {"data.test_data": {$existsTrue}}
            ]
        }
        
        mock_count = collection.count_documents(mock_query)
        real_count = total_events - mock_count
        
        print(f"🔍 Analysis:)
        print(f"  - Mock/Test events: {mock_count})
        print(f"  - Real events: {real_count}")
        
        if mock_count == 0:
            print("✅ No mock/test events found. Database is clean!")
            return
        
        # Show sample of mock events to be deleted
        print(f"\n🗑️  Mock events to be deleted:")
        mock_events = list(collection.find(mock_query).limit(5      for i, event in enumerate(mock_events):
            timestamp = event.get('timestamp', N/A            source = event.get('source', N/A           message = event.get('message', 'N/A')[:50]
            print(f"  {i+1}. {timestamp} - {source} - {message}...")
        
        if mock_count > 5:
            print(f"  ... and {mock_count - 5} more")
        
        # Confirm deletion
        confirm = input(f"\n❓ Do you want to delete {mock_count} mock/test events from Coruscant DB? (y/N): ")
        if confirm.lower() != 'y':
            print("❌ Operation cancelled")
            return
        
        # Delete mock events
        result = collection.delete_many(mock_query)
        deleted_count = result.deleted_count
        
        print(f"\n✅ Successfully deleted {deleted_count} mock/test events from Coruscant DB!)
        print(f📊 Remaining real events: {real_count}")
        
        # Verify deletion
        remaining_total = collection.count_documents({})
        print(f"📊 Total events remaining: {remaining_total}")
        
        client.close()
        
    except Exception as e:
        print(f"❌ Error: {e})if __name__ == "__main__":
    clean_mock_data() 