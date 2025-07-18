#!/usr/bin/env python3
"""
Test script for the unified event log system
"""

import requests
import json
import time
from datetime import datetime, timezone

def test_event_log_api():
    """Test the event log API endpoints"""
    print("🚀 Event Log Test Script")
    print("=" * 60)
    
    api_url = "http://localhost:8098/api/event-log"
    
    # Test events
    test_events = [
        {
            "source": "ava4-listener",
            "event_type": "DATA_RECEIVED",
            "status": "success",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "device_id": "AVA4_001",
            "patient": "John Doe",
            "topic": "ava4/vitals",
            "medical_data": "vital_signs",
            "details": {
                "payload_size": 1024,
                "message": "Test AVA4 data received"
            }
        },
        {
            "source": "kati-listener",
            "event_type": "DATA_PROCESSED",
            "status": "success",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "device_id": "KATI_002",
            "patient": "Jane Smith",
            "topic": "kati/ecg",
            "medical_data": "ecg_data",
            "details": {
                "processing_time_ms": 150.5,
                "message": "Test Kati data processed"
            }
        },
        {
            "source": "qube-listener",
            "event_type": "DATA_STORED",
            "status": "success",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "device_id": "QUBE_003",
            "patient": "Bob Johnson",
            "topic": "qube/blood_pressure",
            "medical_data": "blood_pressure",
            "details": {
                "collection": "qube_data",
                "record_id": "qube_12345",
                "message": "Test Qube data stored"
            }
        },
        {
            "source": "medical-monitor",
            "event_type": "ERROR_OCCURRED",
            "status": "error",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "device_id": "AVA4_001",
            "patient": "John Doe",
            "topic": "ava4/vitals",
            "error": "Invalid data format",
            "details": {
                "error_type": "validation_error",
                "error_message": "Invalid data format",
                "message": "Test error occurred"
            }
        },
        {
            "source": "ava4-listener",
            "event_type": "FHIR_CONVERTED",
            "status": "success",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "device_id": "AVA4_001",
            "patient": "John Doe",
            "topic": "ava4/vitals",
            "medical_data": "vital_signs",
            "details": {
                "fhir_resource_type": "Observation",
                "fhir_id": "obs_12345",
                "message": "Test FHIR conversion"
            }
        }
    ]
    
    print("🧪 Testing Event Log API...")
    print(f"📡 API URL: {api_url}")
    print("=" * 60)
    
    successful_events = 0
    failed_events = 0
    
    for i, event in enumerate(test_events, 1):
        print(f"📝 Sending event {i}/{len(test_events)}: {event['source']} - {event['event_type']}")
        
        try:
            response = requests.post(
                api_url,
                json=event,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    print(f"✅ Event logged successfully")
                    successful_events += 1
                else:
                    print(f"❌ API returned error: {result.get('error')}")
                    failed_events += 1
            else:
                print(f"❌ HTTP error {response.status_code}: {response.text}")
                failed_events += 1
                
        except requests.RequestException as e:
            print(f"❌ Request failed: {e}")
            failed_events += 1
        
        print("-" * 40)
        time.sleep(0.5)  # Small delay between requests
    
    print("=" * 60)
    print("📊 Test Results:")
    print(f"   ✅ Successful: {successful_events}")
    print(f"   ❌ Failed: {failed_events}")
    print(f"   📈 Success Rate: {(successful_events / len(test_events) * 100):.1f}%")
    
    if failed_events > 0:
        print("\n⚠️  Event log API test failed. Please check:")
        print("   1. Is the web panel running on port 8098?")
        print("   2. Are there any network connectivity issues?")
        print("   3. Check the web panel logs for errors")
    
    # Test retrieving events
    print("\n🌐 Testing Event Log Web Interface...")
    try:
        # Test the web interface
        web_response = requests.get("http://localhost:8098/event-log", timeout=10)
        if web_response.status_code == 200:
            print("✅ Event log web page is accessible")
        else:
            print(f"❌ Web page returned status {web_response.status_code}")
        
        # Test API endpoint for retrieving events
        api_response = requests.get(f"{api_url}?limit=10", timeout=10)
        if api_response.status_code == 200:
            result = api_response.json()
            if result.get('success'):
                events = result.get('events', [])
                print(f"✅ API returned {len(events)} events")
                
                if events:
                    print("📋 Sample events:")
                    for event in events[:3]:  # Show first 3 events
                        print(f"   - {event.get('source', 'unknown')}: {event.get('event_type', 'unknown')} ({event.get('status', 'unknown')})")
            else:
                print(f"❌ API returned error: {result.get('error')}")
        else:
            print(f"❌ API retrieval failed with status {api_response.status_code}")
            
    except requests.RequestException as e:
        print(f"❌ Web interface test failed: {e}")
    
    print("\n✨ Test completed!")

if __name__ == "__main__":
    test_event_log_api() 