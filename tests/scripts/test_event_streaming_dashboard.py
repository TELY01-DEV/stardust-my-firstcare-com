#!/usr/bin/env python3
"""
Test script for the Real-time Event Streaming Dashboard
Tests the new streaming dashboard functionality and API endpoints
"""

import requests
import json
import time
from datetime import datetime, timezone
import random

# Configuration
BASE_URL = "http://localhost:8098"
API_BASE = f"{BASE_URL}/api"

def test_streaming_dashboard():
    """Test the real-time event streaming dashboard"""
    print("🚀 Testing Real-time Event Streaming Dashboard")
    print("=" * 60)
    
    # Test 1: Check if the streaming dashboard page is accessible
    print("\n1. Testing streaming dashboard page access...")
    try:
        response = requests.get(f"{BASE_URL}/event-streaming", timeout=10)
        if response.status_code == 200:
            print("✅ Streaming dashboard page is accessible")
        else:
            print(f"❌ Streaming dashboard page returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error accessing streaming dashboard: {e}")
        return False
    
    # Test 2: Test streaming events API
    print("\n2. Testing streaming events API...")
    try:
        response = requests.get(f"{API_BASE}/streaming/events", timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                events = data.get("data", [])
                print(f"✅ Streaming events API working - {len(events)} events retrieved")
            else:
                print(f"❌ Streaming events API error: {data.get('error')}")
        else:
            print(f"❌ Streaming events API returned status {response.status_code}")
    except Exception as e:
        print(f"❌ Error testing streaming events API: {e}")
    
    # Test 3: Test streaming stats API
    print("\n3. Testing streaming stats API...")
    try:
        response = requests.get(f"{API_BASE}/streaming/stats", timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                stats = data.get("data", {})
                print(f"✅ Streaming stats API working")
                print(f"   - Total events (1h): {stats.get('total_events', 0)}")
                print(f"   - Events per minute: {stats.get('events_per_minute', 0)}")
                print(f"   - Error rate: {stats.get('error_rate', 0)}%")
                print(f"   - Active devices: {stats.get('active_devices', 0)}")
            else:
                print(f"❌ Streaming stats API error: {data.get('error')}")
        else:
            print(f"❌ Streaming stats API returned status {response.status_code}")
    except Exception as e:
        print(f"❌ Error testing streaming stats API: {e}")
    
    # Test 4: Test event correlation API
    print("\n4. Testing event correlation API...")
    try:
        response = requests.get(f"{API_BASE}/streaming/correlation", timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                correlations = data.get("data", {})
                print(f"✅ Event correlation API working")
                print(f"   - Device-patient pairs: {len(correlations.get('device_patient_pairs', {}))}")
                print(f"   - Event sequences: {len(correlations.get('event_sequences', {}))}")
                print(f"   - Error patterns: {len(correlations.get('error_patterns', {}))}")
            else:
                print(f"❌ Event correlation API error: {data.get('error')}")
        else:
            print(f"❌ Event correlation API returned status {response.status_code}")
    except Exception as e:
        print(f"❌ Error testing event correlation API: {e}")
    
    # Test 5: Generate test events for streaming
    print("\n5. Generating test events for streaming...")
    test_events = generate_test_events(10)
    success_count = 0
    
    for i, event in enumerate(test_events):
        try:
            response = requests.post(f"{API_BASE}/event-log", 
                                   json=event, 
                                   headers={'Content-Type': 'application/json'},
                                   timeout=5)
            if response.status_code == 200:
                success_count += 1
                print(f"   ✅ Event {i+1} logged successfully")
            else:
                print(f"   ❌ Event {i+1} failed: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Event {i+1} error: {e}")
    
    print(f"\n📊 Test events summary: {success_count}/{len(test_events)} successful")
    
    # Test 6: Test real-time updates via Socket.IO
    print("\n6. Testing real-time updates...")
    print("   Note: This requires a WebSocket client to test properly")
    print("   The streaming dashboard should show real-time updates")
    
    # Test 7: Test filtering and time ranges
    print("\n7. Testing filtering and time ranges...")
    test_filters = [
        {"source": "ava4-listener"},
        {"event_type": "DATA_RECEIVED"},
        {"status": "success"},
        {"time_range": "15"}
    ]
    
    for filter_params in test_filters:
        try:
            response = requests.get(f"{API_BASE}/streaming/events", 
                                  params=filter_params,
                                  timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    events = data.get("data", [])
                    print(f"   ✅ Filter {filter_params} working - {len(events)} events")
                else:
                    print(f"   ❌ Filter {filter_params} error: {data.get('error')}")
            else:
                print(f"   ❌ Filter {filter_params} returned status {response.status_code}")
        except Exception as e:
            print(f"   ❌ Filter {filter_params} error: {e}")
    
    print("\n" + "=" * 60)
    print("🎉 Real-time Event Streaming Dashboard Test Complete!")
    print("\nNext steps:")
    print("1. Open http://localhost:8098/event-streaming in your browser")
    print("2. Verify real-time event streaming is working")
    print("3. Test the interactive charts and visualizations")
    print("4. Check event correlation and timeline features")
    
    return True

def generate_test_events(count=10):
    """Generate test events for streaming"""
    sources = ["ava4-listener", "kati-listener", "qube-listener", "medical-monitor"]
    event_types = ["DATA_RECEIVED", "DATA_PROCESSED", "DATA_STORED", "FHIR_CONVERTED", "ERROR_OCCURRED"]
    statuses = ["success", "error", "warning", "info"]
    devices = ["AVA4_001", "KATI_002", "QUBE_003", "MONITOR_004"]
    patients = ["PAT_001", "PAT_002", "PAT_003", "PAT_004"]
    
    events = []
    for i in range(count):
        source = random.choice(sources)
        event_type = random.choice(event_types)
        status = random.choice(statuses)
        device_id = random.choice(devices)
        patient_id = random.choice(patients)
        
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": source,
            "event_type": event_type,
            "status": status,
            "device_id": device_id,
            "patient_id": patient_id,
            "message": f"Test event {i+1} from {source} - {event_type}",
            "data": {
                "test_data": f"value_{i+1}",
                "random_value": random.randint(1, 100),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        }
        
        # Add some delay between events to simulate real-time
        time.sleep(0.1)
        events.append(event)
    
    return events

def test_streaming_features():
    """Test specific streaming features"""
    print("\n🔍 Testing Advanced Streaming Features")
    print("=" * 40)
    
    # Test 1: Event timeline
    print("\n1. Testing event timeline...")
    try:
        response = requests.get(f"{API_BASE}/streaming/stats", timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                timeline_events = data.get("data", {}).get("timeline_events", [])
                print(f"✅ Timeline events: {len(timeline_events)} events available")
            else:
                print(f"❌ Timeline error: {data.get('error')}")
        else:
            print(f"❌ Timeline API returned status {response.status_code}")
    except Exception as e:
        print(f"❌ Timeline error: {e}")
    
    # Test 2: Event distribution
    print("\n2. Testing event distribution...")
    try:
        response = requests.get(f"{API_BASE}/streaming/stats", timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                sources = data.get("data", {}).get("sources", [])
                event_types = data.get("data", {}).get("event_types", [])
                print(f"✅ Event distribution:")
                print(f"   - Sources: {len(sources)}")
                print(f"   - Event types: {len(event_types)}")
                for source in sources[:3]:  # Show top 3
                    print(f"     {source['_id']}: {source['count']} events")
            else:
                print(f"❌ Distribution error: {data.get('error')}")
        else:
            print(f"❌ Distribution API returned status {response.status_code}")
    except Exception as e:
        print(f"❌ Distribution error: {e}")
    
    # Test 3: Real-time metrics
    print("\n3. Testing real-time metrics...")
    try:
        response = requests.get(f"{API_BASE}/streaming/stats", timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                stats = data.get("data", {})
                print(f"✅ Real-time metrics:")
                print(f"   - Events per minute: {stats.get('events_per_minute', 0)}")
                print(f"   - Events last minute: {stats.get('events_last_minute', 0)}")
                print(f"   - Error rate: {stats.get('error_rate', 0)}%")
                print(f"   - Active devices: {stats.get('active_devices', 0)}")
            else:
                print(f"❌ Metrics error: {data.get('error')}")
        else:
            print(f"❌ Metrics API returned status {response.status_code}")
    except Exception as e:
        print(f"❌ Metrics error: {e}")

if __name__ == "__main__":
    print("🚀 Starting Real-time Event Streaming Dashboard Tests")
    print("Make sure the web panel is running on http://localhost:8098")
    print("=" * 60)
    
    try:
        # Test basic functionality
        test_streaming_dashboard()
        
        # Test advanced features
        test_streaming_features()
        
        print("\n🎉 All tests completed!")
        print("\nTo view the streaming dashboard:")
        print("1. Open http://localhost:8098/event-streaming")
        print("2. Watch real-time events stream in")
        print("3. Interact with charts and visualizations")
        print("4. Test filtering and time range controls")
        
    except KeyboardInterrupt:
        print("\n⏹️ Tests interrupted by user")
    except Exception as e:
        print(f"\n❌ Test suite error: {e}") 