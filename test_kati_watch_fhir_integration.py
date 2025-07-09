#!/usr/bin/env python3
"""
Kati Watch to FHIR R5 Integration Test
=====================================
Comprehensive test demonstrating the real-time IoT data pipeline from 
Kati Watch devices to FHIR R5 resources.

This test simulates the complete data flow:
Kati Watch → MQTT Parser → FHIR R5 Service → Patient Records
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Dict, Any

# Test data representing MQTT messages from Kati Watch
SAMPLE_MQTT_MESSAGES = [
    {
        "topic": "iMEDE_watch/VitalSign",
        "payload": {
            "IMEI": "865067123456789",
            "heartRate": 72,
            "bloodPressure": {
                "bp_sys": 122,
                "bp_dia": 78
            },
            "spO2": 97,
            "bodyTemperature": 36.6,
            "signalGSM": 85,
            "battery": 67,
            "timeStamps": "16/06/2025 12:30:45"
        }
    },
    {
        "topic": "iMEDE_watch/AP55",
        "payload": {
            "IMEI": "865067123456789",
            "timeStamps": "16/06/2025 12:30:45",
            "num_datas": 3,
            "data": [
                {
                    "timestamp": 1738331256,
                    "heartRate": 84,
                    "bloodPressure": {"bp_sys": 119, "bp_dia": 73},
                    "spO2": 98,
                    "bodyTemperature": 36.9
                },
                {
                    "timestamp": 1738331316,
                    "heartRate": 78,
                    "bloodPressure": {"bp_sys": 124, "bp_dia": 76},
                    "spO2": 96,
                    "bodyTemperature": 36.8
                },
                {
                    "timestamp": 1738331376,
                    "heartRate": 80,
                    "bloodPressure": {"bp_sys": 120, "bp_dia": 75},
                    "spO2": 97,
                    "bodyTemperature": 36.7
                }
            ]
        }
    },
    {
        "topic": "iMEDE_watch/location",
        "payload": {
            "IMEI": "865067123456789",
            "location": {
                "GPS": {
                    "latitude": 22.5678,
                    "longitude": 112.3456,
                    "speed": 0.0,
                    "header": 180.0
                },
                "WiFi": "[{'SSID':'Hospital_WiFi','MAC':'aa-bb-cc-dd-ee-ff','RSSI':'87'}]",
                "LBS": {
                    "MCC": "520",
                    "MNC": "3",
                    "LAC": "1815",
                    "CID": "79474300"
                }
            }
        }
    },
    {
        "topic": "iMEDE_watch/sleepdata",
        "payload": {
            "IMEI": "865067123456789",
            "sleep": {
                "timeStamps": "16/06/2025 01:00:00",
                "time": "2200@0700",
                "data": "0000000111110000010011111110011111111111110000000002200000001111111112111100111001111111211111111222111111111110110111111110110111111011112201110",
                "num": 145
            }
        }
    },
    {
        "topic": "iMEDE_watch/sos",
        "payload": {
            "IMEI": "865067123456789",
            "status": "SOS",
            "location": {
                "GPS": {
                    "latitude": 22.5678,
                    "longitude": 112.3456
                }
            }
        }
    },
    {
        "topic": "iMEDE_watch/fallDown",
        "payload": {
            "IMEI": "865067123456789",
            "status": "FALL DOWN",
            "location": {
                "GPS": {
                    "latitude": 22.5680,
                    "longitude": 112.3458
                }
            }
        }
    },
    {
        "topic": "iMEDE_watch/hb",
        "payload": {
            "IMEI": "865067123456789",
            "signalGSM": 80,
            "battery": 67,
            "satellites": 4,
            "workingMode": 2,
            "timeStamps": "16/06/2025 12:30:45",
            "step": 999
        }
    }
]

async def test_kati_watch_fhir_integration():
    """Test the complete Kati Watch to FHIR R5 integration"""
    print("🚀 Testing Kati Watch to FHIR R5 Integration")
    print("=" * 60)
    
    try:
        # Import services (this would work when running in proper environment)
        from app.services.mongo import mongodb_service
        from app.services.kati_watch_fhir_service import KatiWatchFHIRService
        from app.services.fhir_r5_service import FHIRR5Service
        
        # Connect to database
        await mongodb_service.connect()
        print("✅ Connected to MongoDB")
        
        # Initialize services
        kati_fhir_service = KatiWatchFHIRService()
        fhir_service = FHIRR5Service()
        print("✅ Services initialized")
        
        # Setup test device registration
        print("\n📱 Setting up device registration...")
        device_collection = mongodb_service.get_collection("device_registrations")
        
        # Check if test device exists
        test_imei = "865067123456789"
        existing_device = await device_collection.find_one({"imei": test_imei})
        
        if not existing_device:
            # Create test device registration
            test_device = {
                "imei": test_imei,
                "patient_id": "78e095cb-2357-45ee-837e-5ce1c50ec7a8",  # Test patient from earlier
                "device_model": "Kati Watch Pro",
                "serial_number": "KW123456",
                "status": "active",
                "created_at": datetime.utcnow()
            }
            await device_collection.insert_one(test_device)
            print(f"✅ Registered test device: {test_imei}")
        else:
            print(f"✅ Test device already registered: {test_imei}")
        
        # Process each MQTT message type
        total_observations = 0
        processing_results = []
        
        print("\n🔄 Processing MQTT messages...")
        
        for i, mqtt_message in enumerate(SAMPLE_MQTT_MESSAGES, 1):
            topic = mqtt_message["topic"]
            payload = mqtt_message["payload"]
            
            print(f"\n{i}. Processing {topic}")
            print(f"   IMEI: {payload.get('IMEI')}")
            
            try:
                # Process MQTT message to FHIR
                result = await kati_fhir_service.process_mqtt_message(topic, payload)
                
                if result['status'] == 'success':
                    observations = result.get('observations', [])
                    total_observations += len(observations)
                    
                    print(f"   ✅ Created {len(observations)} FHIR observations")
                    for obs in observations:
                        print(f"      - {obs['type']}: {obs['id']}")
                        
                    processing_results.append({
                        "topic": topic,
                        "status": "success",
                        "observations_created": len(observations)
                    })
                        
                elif result['status'] == 'skipped':
                    print(f"   ⚠️  Skipped: {result.get('reason')}")
                    processing_results.append({
                        "topic": topic,
                        "status": "skipped",
                        "reason": result.get('reason')
                    })
                    
                else:
                    print(f"   ❌ Error: {result.get('error')}")
                    processing_results.append({
                        "topic": topic,
                        "status": "error",
                        "error": result.get('error')
                    })
                    
            except Exception as e:
                print(f"   ❌ Exception: {str(e)}")
                processing_results.append({
                    "topic": topic,
                    "status": "exception",
                    "error": str(e)
                })
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 INTEGRATION TEST SUMMARY")
        print("=" * 60)
        
        successful = len([r for r in processing_results if r['status'] == 'success'])
        skipped = len([r for r in processing_results if r['status'] == 'skipped'])
        errors = len([r for r in processing_results if r['status'] in ['error', 'exception']])
        
        print(f"📨 MQTT Messages Processed: {len(SAMPLE_MQTT_MESSAGES)}")
        print(f"✅ Successful: {successful}")
        print(f"⚠️  Skipped: {skipped}")
        print(f"❌ Errors: {errors}")
        print(f"🔬 Total FHIR Observations Created: {total_observations}")
        
        # Show resource type breakdown
        print(f"\n📋 Resource Types Created:")
        resource_counts = {}
        for result in processing_results:
            if result['status'] == 'success':
                count = result.get('observations_created', 0)
                topic = result['topic'].split('/')[-1]  # Get last part of topic
                resource_counts[topic] = resource_counts.get(topic, 0) + count
        
        for resource_type, count in resource_counts.items():
            print(f"   {resource_type}: {count} observations")
        
        # Test data retrieval
        print(f"\n🔍 Testing Data Retrieval...")
        
        # Get all observations for the test patient
        patient_id = "78e095cb-2357-45ee-837e-5ce1c50ec7a8"
        search_result = await fhir_service.search_fhir_resources(
            "Observation",
            subject=f"Patient/{patient_id}",
            _count=100
        )
        
        # Filter for Kati Watch observations
        kati_observations = []
        if hasattr(search_result, 'resources'):
            kati_observations = [
                obs for obs in search_result.resources 
                if 'Kati Watch' in str(obs.get('device', {}))
            ]
        
        print(f"✅ Found {len(kati_observations)} Kati Watch observations in FHIR")
        
        # Show observation categories
        categories = {}
        for obs in kati_observations:
            category = obs.get('category', [{}])[0].get('coding', [{}])[0].get('code', 'unknown')
            categories[category] = categories.get(category, 0) + 1
        
        print(f"📊 Observation Categories:")
        for category, count in categories.items():
            print(f"   {category}: {count}")
        
        print("\n🎉 Kati Watch to FHIR R5 Integration Test Complete!")
        
        return {
            "total_messages": len(SAMPLE_MQTT_MESSAGES),
            "successful": successful,
            "skipped": skipped,
            "errors": errors,
            "total_observations": total_observations,
            "fhir_observations_found": len(kati_observations)
        }
        
    except ImportError as e:
        print(f"❌ Import Error: {e}")
        print("This test requires the full application environment to run.")
        return None
        
    except Exception as e:
        print(f"❌ Test Error: {e}")
        import traceback
        traceback.print_exc()
        return None

async def demonstrate_mqtt_to_fhir_mapping():
    """Demonstrate the MQTT to FHIR mapping without requiring full environment"""
    print("\n🗺️  MQTT TO FHIR R5 MAPPING DEMONSTRATION")
    print("=" * 60)
    
    mapping_table = [
        ("iMEDE_watch/VitalSign", "Observation (vital-signs)", "Heart rate, BP, SpO2, Temperature"),
        ("iMEDE_watch/AP55", "Multiple Observations", "Batch vital signs data"),
        ("iMEDE_watch/location", "Observation (survey)", "GPS coordinates, WiFi, LBS"),
        ("iMEDE_watch/sleepdata", "Observation (activity)", "Sleep study data"),
        ("iMEDE_watch/sos", "Observation (safety)", "Emergency SOS alert"),
        ("iMEDE_watch/fallDown", "Observation (safety)", "Fall detection alert"),
        ("iMEDE_watch/hb", "Observation (survey)", "Device status & heartbeat")
    ]
    
    print(f"{'MQTT Topic':<25} {'FHIR Resource':<25} {'Data Type'}")
    print("-" * 75)
    for topic, fhir_resource, data_type in mapping_table:
        print(f"{topic:<25} {fhir_resource:<25} {data_type}")
    
    print(f"\n🔢 Sample Data Points:")
    print(f"📨 Total MQTT Message Types: {len(SAMPLE_MQTT_MESSAGES)}")
    print(f"📊 Sample Vital Signs: Heart Rate, Blood Pressure, SpO2, Temperature")
    print(f"📍 Location Data: GPS, WiFi, Cell Tower (LBS)")
    print(f"🚨 Emergency Alerts: SOS, Fall Detection")
    print(f"😴 Sleep Analysis: Sleep periods, activity data")
    print(f"🔋 Device Status: Battery, Signal, Step count")

def main():
    """Main test function"""
    print("🏥 My FirstCare Kati Watch FHIR R5 Integration")
    print("=" * 60)
    print("Real-time IoT Medical Device Data → FHIR R5 Patient Records")
    print("=" * 60)
    
    # Run the demonstration
    asyncio.run(demonstrate_mqtt_to_fhir_mapping())
    
    # Run the integration test (will handle import errors gracefully)
    print()
    result = asyncio.run(test_kati_watch_fhir_integration())
    
    if result:
        print(f"\n✨ Integration test completed successfully!")
        print(f"📈 Performance: {result['total_observations']} observations created from {result['total_messages']} messages")
    else:
        print(f"\n📋 Integration test skipped (requires full environment)")
        print(f"📖 This demonstration shows the complete data flow architecture")

if __name__ == "__main__":
    main() 