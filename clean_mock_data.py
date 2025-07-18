#!/usr/bin/env python3
""
Script to remove all mock/test events from the event log database
""

import requests
import json

def clean_mock_data():
    print("🧹 Cleaning mock/test data from event log database...")
    
    try:
        response = requests.get(http://localhost:8098vent-log")
        data = response.json()
        
        if not data.get('success'):
            print("❌ Failed to get event log data")
            return
            
        events = data[data['events]
        print(f"📊 Found {len(events)} total events")
        
        # Count mock vs real events
        mock_count = 0
        real_count = 0      
        for event in events:
            message = event.get('message,        if message.startswith('Test event'):
                mock_count += 1            else:
                real_count += 1    
        print(f"🔍 Analysis:)
        print(f"  - Mock/Test events: {mock_count})
        print(f"  - Real events: {real_count}")
        
        if mock_count == 0:
            print("✅ No mock/test events found. Database is clean!")
            return
        
        print(f"\n🗑️  Found {mock_count} mock/test events to remove)       print(Note: You'll need to manually delete these from your database)
        print("or implement a delete endpoint in your API")
        
    except Exception as e:
        print(f"❌ Error: {e})if __name__ == "__main__":
    clean_mock_data() 