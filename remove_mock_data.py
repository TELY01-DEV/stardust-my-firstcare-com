#!/usr/bin/env python3
""
Script to remove mock/test events from the event_logs collection
Uses the same API approach that was used to add the mock data
""

import requests
import json
from datetime import datetime, timezone

# Configuration - same as test script
BASE_URL = http://localhost:8098API_BASE = f{BASE_URL}/api

def remove_mock_data():
    move all mock/test events from the event log"""
    print("🧹 Removing mock/test data from event log...")
    
    try:
        # First, get all events to identify mock data
        print("📊 Fetching all events from event log...")
        response = requests.get(f"{API_BASE}/event-log", timeout=10)
        
        if response.status_code != 200:
            print(f"❌ Failed to get events: {response.status_code}")
            return
        
        data = response.json()
        if not data.get("success"):
            print(f"❌ API error: {data.get('error')}")
            return
        
        events = data.get("data,[object Object]}).get("events",       total_events = len(events)
        print(f"📊 Found {total_events} total events")
        
        # Identify mock events
        mock_events = []
        real_events = []
        
        for event in events:
            message = event.get('message,           # Check for mock/test patterns
            if (message.startswith('Test event') or
             from qube-listener' in message or
             from kati-listener' in message or
             from ava4-listener' in message or
               from medical-monitor' in message or
                test_datain str(event.get('data', {}))):
                mock_events.append(event)
            else:
                real_events.append(event)
        
        print(f"🔍 Analysis:)
        print(f"  - Mock/Test events: {len(mock_events)})
        print(f"  - Real events: {len(real_events)}")
        
        if len(mock_events) == 0:
            print("✅ No mock/test events found. Database is clean!")
            return
        
        # Show sample of mock events to be removed
        print(f"\n🗑️  Mock events to be removed:")
        for i, event in enumerate(mock_events[:5]):
            timestamp = event.get('timestamp', N/A            source = event.get('source', N/A           message = event.get('message', 'N/A')[:50]
            print(f"  {i+1}. {timestamp} - {source} - {message}...")
        
        if len(mock_events) > 5:
            print(f"  ... and[object Object]len(mock_events) - 5} more")
        
        # Confirm deletion
        confirm = input(f"\n❓ Do you want to delete {len(mock_events)} mock/test events? (y/N): ")
        if confirm.lower() != 'y':
            print("❌ Operation cancelled")
            return
        
        # Since there's no DELETE endpoint, we need to use a different approach
        # We'll create a script that can be run directly against the database
        print(f"\n📝 Creating database cleanup script...")
        
        # Create MongoDB cleanup script
        cleanup_script = f"""
# MongoDB cleanup script for Coruscant DB
# Run this script in MongoDB shell to remove mock data

use AMY

# Delete all mock/test events
db.event_logs.deleteMany([object Object]{
  $or:    {{"message": {{"$regex":^Test event,$options: "i"}}}},
    {{"message": {{$regex: from qube-listener,$options: "i"}}}},
    {{"message":[object Object]{"$regex: from kati-listener,$options: "i"}}}},
    {{"message": {{$regex: from ava4-listener,$options: "i"}}}},
    {{"message": {{"$regex":from medical-monitor,$options: "i}}}},
   [object Object]{"data.test_data":[object Object]{"$exists:true}}}}
  ]
}})

# Verify deletion
print(Remaining events: + db.event_logs.countDocuments({{}}))
""        
        # Save the script
        with open(cleanup_mock_data.js', 'w') as f:
            f.write(cleanup_script)
        
        print(f"✅ Cleanup script saved as cleanup_mock_data.js')
        print(f"📋 To run the cleanup:)
        print(f"   1ct to your MongoDB: mongo <your_connection_string>)
        print(f   2. Run: load(cleanup_mock_data.js))
        print(f" 3 Or copy/paste the commands directly")
        
        # Also provide direct command
        print(f"\n🔧 Direct MongoDB command:)
        print(f"db.event_logs.deleteMany({{$or:)
        print(f"  [object Object][object Object]\"message\": {{\$regex\": \^Test event\", \$options\": \"i\"}}}},)
        print(f"  [object Object][object Object]\"message\": {{\"$regex\": \"from qube-listener\", \$options\": \"i\"}}}},)
        print(f"  [object Object][object Object]\"message\": {{\"$regex\": \"from kati-listener\", \$options\": \"i\"}}}},)
        print(f"  [object Object][object Object]\"message\": {{\"$regex\": \"from ava4-listener\", \$options\": \"i\"}}}},)
        print(f"  [object Object][object Object]\"message\": {{\"$regex\": \"from medical-monitor\", \$options\": \"i\"}}}},)
        print(f"  {{\data.test_data\": {{\"$exists\": true}}}})
        print(f"]}})")
        
    except Exception as e:
        print(f"❌ Error: {e})if __name__ == "__main__:  remove_mock_data() 