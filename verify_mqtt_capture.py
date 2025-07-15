#!/usr/bin/env python3
"""
MQTT Topic and Payload Capture Verification
Validates that all medical device topics and payloads are correctly captured
"""

import os
import json
import time
import logging
from datetime import datetime
from typing import Dict, Any, List
from paho.mqtt import client as mqtt_client
from collections import defaultdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MQTTCaptureVerifier:
    """Verify MQTT topic and payload capture from medical devices"""
    
    def __init__(self):
        # MQTT Configuration
        self.mqtt_broker = os.getenv('MQTT_BROKER_HOST', 'adam.amy.care')
        self.mqtt_port = int(os.getenv('MQTT_BROKER_PORT', 1883))
        self.mqtt_username = os.getenv('MQTT_USERNAME', 'webapi')
        self.mqtt_password = os.getenv('MQTT_PASSWORD', 'Sim!4433')
        
        # Expected topics and payload structures
        self.expected_topics = {
            # AVA4 Topics
            'ESP32_BLE_GW_TX': {
                'description': 'AVA4 status messages (heartbeat, online/offline)',
                'expected_fields': ['from', 'to', 'name', 'time', 'mac', 'IMEI', 'type', 'data'],
                'message_types': ['HB_Msg', 'onlineTrigger']
            },
            'dusun_sub': {
                'description': 'AVA4 medical device data',
                'expected_fields': ['from', 'to', 'time', 'deviceCode', 'mac', 'type', 'device', 'data'],
                'message_types': ['reportAttribute'],
                'expected_attributes': ['BP_BIOLIGTH', 'Contour_Elite', 'AccuChek_Instant', 'Oximeter JUMPER', 'IR_TEMO_JUMPER', 'BodyScale_JUMPER', 'MGSS_REF_UA', 'MGSS_REF_CHOL']
            },
            
            # Kati Watch Topics
            'iMEDE_watch/VitalSign': {
                'description': 'Real-time vital signs',
                'expected_fields': ['IMEI', 'heartRate', 'bloodPressure', 'bodyTemperature', 'spO2', 'signalGSM', 'battery', 'location', 'timeStamps'],
                'optional_fields': ['location']
            },
            'iMEDE_watch/AP55': {
                'description': 'Batch vital signs data',
                'expected_fields': ['IMEI', 'location', 'timeStamps', 'num_datas', 'data'],
                'optional_fields': ['location']
            },
            'iMEDE_watch/hb': {
                'description': 'Heartbeat/step data',
                'expected_fields': ['IMEI', 'step'],
                'optional_fields': ['battery', 'signal']
            },
            'iMEDE_watch/location': {
                'description': 'Location data',
                'expected_fields': ['IMEI', 'location'],
                'location_fields': ['GPS', 'WiFi', 'LBS']
            },
            'iMEDE_watch/sleepdata': {
                'description': 'Sleep data',
                'expected_fields': ['IMEI', 'sleep'],
                'sleep_fields': ['timeStamps', 'time', 'data', 'num']
            },
            'iMEDE_watch/sos': {
                'description': 'Emergency SOS alert',
                'expected_fields': ['status', 'location', 'IMEI']
            },
            'iMEDE_watch/fallDown': {
                'description': 'Fall detection alert',
                'expected_fields': ['status', 'location', 'IMEI']
            },
            'iMEDE_watch/onlineTrigger': {
                'description': 'Online/offline status',
                'expected_fields': ['IMEI', 'status']
            },
            
            # Qube-Vital Topics
            'CM4_BLE_GW_TX': {
                'description': 'Qube-Vital data',
                'expected_fields': ['from', 'to', 'time', 'mac', 'IMEI', 'type', 'data'],
                'message_types': ['HB_Msg', 'reportAttribute'],
                'expected_attributes': ['WBP_JUMPER', 'CONTOUR', 'BodyScale_JUMPER', 'TEMO_Jumper', 'Oximeter_JUMPER'],
                'required_fields_for_medical': ['citiz']
            }
        }
        
        # Capture results
        self.captured_messages = defaultdict(list)
        self.verification_results = {}
        self.start_time = datetime.utcnow()
        
        # MQTT client
        self.client = None
        self.connected = False
        
    def connect_mqtt(self) -> mqtt_client.Client:
        """Connect to MQTT broker"""
        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                logger.info("✅ Connected to MQTT broker successfully")
                self.connected = True
                # Subscribe to all expected topics
                for topic in self.expected_topics.keys():
                    client.subscribe(topic, 1)
                    logger.info(f"📡 Subscribed to topic: {topic}")
            else:
                logger.error(f"❌ Failed to connect to MQTT broker, return code: {rc}")
                self.connected = False
        
        def on_disconnect(client, userdata, rc):
            logger.warning(f"⚠️ Disconnected from MQTT broker, return code: {rc}")
            self.connected = False
        
        def on_message(client, userdata, msg):
            try:
                self.capture_message(msg.topic, msg.payload.decode())
            except Exception as e:
                logger.error(f"❌ Error capturing message: {e}")
        
        # Create client
        client = mqtt_client.Client()
        client.username_pw_set(self.mqtt_username, self.mqtt_password)
        client.on_connect = on_connect
        client.on_disconnect = on_disconnect
        client.on_message = on_message
        
        # Connect
        try:
            client.connect(self.mqtt_broker, self.mqtt_port, 60)
            client.loop_start()
            return client
        except Exception as e:
            logger.error(f"❌ Failed to connect to MQTT broker: {e}")
            return None
    
    def capture_message(self, topic: str, payload: str):
        """Capture and store MQTT message"""
        try:
            # Parse JSON payload
            data = json.loads(payload)
            
            # Store message
            message_record = {
                "timestamp": datetime.utcnow(),
                "payload": data,
                "raw_payload": payload,
                "payload_size": len(payload)
            }
            
            self.captured_messages[topic].append(message_record)
            
            # Log capture
            logger.info(f"📨 Captured message on topic: {topic}")
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ Invalid JSON payload on topic {topic}: {e}")
        except Exception as e:
            logger.error(f"❌ Error capturing message on topic {topic}: {e}")
    
    def verify_topic_structure(self, topic: str, messages: List[Dict]) -> Dict[str, Any]:
        """Verify topic structure and payload format"""
        if topic not in self.expected_topics:
            return {
                "status": "UNKNOWN_TOPIC",
                "message": f"Topic {topic} not in expected topics list",
                "captured_count": len(messages)
            }
        
        expected = self.expected_topics[topic]
        verification = {
            "topic": topic,
            "description": expected["description"],
            "captured_count": len(messages),
            "field_verification": {},
            "message_type_verification": {},
            "attribute_verification": {},
            "overall_status": "PASS"
        }
        
        if not messages:
            verification["overall_status"] = "NO_DATA"
            verification["message"] = "No messages captured for this topic"
            return verification
        
        # Verify fields in each message
        field_verification = defaultdict(int)
        message_type_verification = defaultdict(int)
        attribute_verification = defaultdict(int)
        
        for msg in messages:
            payload = msg["payload"]
            
            # Check expected fields
            for field in expected.get("expected_fields", []):
                if field in payload:
                    field_verification[field] += 1
            
            # Check optional fields
            for field in expected.get("optional_fields", []):
                if field in payload:
                    field_verification[f"optional_{field}"] += 1
            
            # Check message types
            if "message_types" in expected:
                msg_type = payload.get("type", "unknown")
                if msg_type in expected["message_types"]:
                    message_type_verification[msg_type] += 1
                else:
                    message_type_verification[f"unexpected_{msg_type}"] += 1
            
            # Check attributes for medical data
            if "expected_attributes" in expected and "data" in payload:
                attribute = payload.get("data", {}).get("attribute", "unknown")
                if attribute in expected["expected_attributes"]:
                    attribute_verification[attribute] += 1
                else:
                    attribute_verification[f"unexpected_{attribute}"] += 1
        
        # Calculate field coverage
        total_messages = len(messages)
        for field in expected.get("expected_fields", []):
            coverage = (field_verification[field] / total_messages) * 100
            verification["field_verification"][field] = {
                "present_count": field_verification[field],
                "coverage_percent": coverage,
                "status": "PASS" if coverage >= 90 else "FAIL"
            }
            
            if coverage < 90:
                verification["overall_status"] = "FAIL"
        
        # Add verification results
        verification["field_verification"] = dict(verification["field_verification"])
        verification["message_type_verification"] = dict(message_type_verification)
        verification["attribute_verification"] = dict(attribute_verification)
        
        return verification
    
    def verify_ava4_payload_structure(self, messages: List[Dict]) -> Dict[str, Any]:
        """Verify AVA4 specific payload structure"""
        verification = {
            "device_identification": {},
            "medical_data_structure": {},
            "status_messages": {},
            "overall_status": "PASS"
        }
        
        for msg in messages:
            payload = msg["payload"]
            msg_type = payload.get("type", "unknown")
            
            if msg_type == "reportAttribute":
                # Verify medical data structure
                data = payload.get("data", {})
                attribute = data.get("attribute", "unknown")
                value = data.get("value", {})
                
                if "device_list" in value:
                    device_list = value["device_list"]
                    for device_data in device_list:
                        # Check for required medical data fields
                        if attribute == "BP_BIOLIGTH":
                            required_fields = ["bp_high", "bp_low", "PR", "scan_time"]
                        elif attribute in ["Contour_Elite", "AccuChek_Instant"]:
                            required_fields = ["blood_glucose", "marker", "scan_time"]
                        elif attribute == "Oximeter JUMPER":
                            required_fields = ["spo2", "pulse", "pi", "scan_time"]
                        else:
                            required_fields = ["scan_time"]
                        
                        for field in required_fields:
                            if field not in device_data:
                                verification["medical_data_structure"][f"missing_{field}"] = verification["medical_data_structure"].get(f"missing_{field}", 0) + 1
                                verification["overall_status"] = "FAIL"
            
            elif msg_type == "HB_Msg":
                # Verify status message structure
                verification["status_messages"]["heartbeat"] = verification["status_messages"].get("heartbeat", 0) + 1
        
        return verification
    
    def verify_kati_payload_structure(self, topic: str, messages: List[Dict]) -> Dict[str, Any]:
        """Verify Kati Watch specific payload structure"""
        verification = {
            "imei_presence": {},
            "vital_signs_data": {},
            "location_data": {},
            "emergency_alerts": {},
            "overall_status": "PASS"
        }
        
        for msg in messages:
            payload = msg["payload"]
            
            # Check IMEI presence
            if "IMEI" in payload:
                verification["imei_presence"]["present"] = verification["imei_presence"].get("present", 0) + 1
            else:
                verification["imei_presence"]["missing"] = verification["imei_presence"].get("missing", 0) + 1
                verification["overall_status"] = "FAIL"
            
            # Check vital signs data
            if topic == "iMEDE_watch/VitalSign":
                vital_signs = ["heartRate", "bloodPressure", "spO2", "bodyTemperature"]
                for vital in vital_signs:
                    if vital in payload:
                        verification["vital_signs_data"][vital] = verification["vital_signs_data"].get(vital, 0) + 1
            
            # Check location data
            if "location" in payload:
                location = payload["location"]
                if "GPS" in location:
                    verification["location_data"]["gps"] = verification["location_data"].get("gps", 0) + 1
                if "LBS" in location:
                    verification["location_data"]["lbs"] = verification["location_data"].get("lbs", 0) + 1
            
            # Check emergency alerts
            if topic in ["iMEDE_watch/sos", "iMEDE_watch/fallDown"]:
                if "status" in payload:
                    verification["emergency_alerts"]["status_present"] = verification["emergency_alerts"].get("status_present", 0) + 1
                else:
                    verification["emergency_alerts"]["status_missing"] = verification["emergency_alerts"].get("status_missing", 0) + 1
                    verification["overall_status"] = "FAIL"
        
        return verification
    
    def verify_qube_payload_structure(self, messages: List[Dict]) -> Dict[str, Any]:
        """Verify Qube-Vital specific payload structure"""
        verification = {
            "citizen_id_presence": {},
            "medical_data_structure": {},
            "status_messages": {},
            "overall_status": "PASS"
        }
        
        for msg in messages:
            payload = msg["payload"]
            msg_type = payload.get("type", "unknown")
            
            if msg_type == "reportAttribute":
                # Check for citizen ID
                if "citiz" in payload:
                    verification["citizen_id_presence"]["present"] = verification["citizen_id_presence"].get("present", 0) + 1
                else:
                    verification["citizen_id_presence"]["missing"] = verification["citizen_id_presence"].get("missing", 0) + 1
                    verification["overall_status"] = "FAIL"
                
                # Check medical data structure
                data = payload.get("data", {})
                attribute = data.get("attribute", "unknown")
                value = data.get("value", {})
                
                if attribute in ["WBP_JUMPER", "CONTOUR", "BodyScale_JUMPER", "TEMO_Jumper", "Oximeter_JUMPER"]:
                    verification["medical_data_structure"][attribute] = verification["medical_data_structure"].get(attribute, 0) + 1
            
            elif msg_type == "HB_Msg":
                verification["status_messages"]["heartbeat"] = verification["status_messages"].get("heartbeat", 0) + 1
        
        return verification
    
    def run_verification(self, duration_minutes: int = 5):
        """Run verification for specified duration"""
        print(f"🔍 Starting MQTT Capture Verification for {duration_minutes} minutes")
        print("="*80)
        
        # Connect to MQTT broker
        self.client = self.connect_mqtt()
        if not self.client:
            logger.error("❌ Failed to connect to MQTT broker")
            return
        
        try:
            # Monitor for specified duration
            print(f"⏱️  Monitoring for {duration_minutes} minutes...")
            time.sleep(duration_minutes * 60)
            
        except KeyboardInterrupt:
            print("\n🛑 Verification stopped by user")
        finally:
            if self.client:
                self.client.loop_stop()
                self.client.disconnect()
        
        # Run verification analysis
        self.analyze_captured_data()
    
    def analyze_captured_data(self):
        """Analyze captured data and generate verification report"""
        print(f"\n📊 Analyzing captured data...")
        print("="*80)
        
        total_messages = sum(len(messages) for messages in self.captured_messages.values())
        print(f"📨 Total messages captured: {total_messages}")
        print(f"⏱️  Duration: {datetime.utcnow() - self.start_time}")
        
        # Verify each topic
        for topic, messages in self.captured_messages.items():
            print(f"\n🔍 Verifying topic: {topic}")
            print("-" * 60)
            
            # Basic structure verification
            verification = self.verify_topic_structure(topic, messages)
            
            print(f"📋 Description: {verification['description']}")
            print(f"📊 Messages captured: {verification['captured_count']}")
            print(f"✅ Status: {verification['overall_status']}")
            
            # Field verification
            if verification['field_verification']:
                print(f"📝 Field verification:")
                for field, result in verification['field_verification'].items():
                    status_icon = "✅" if result['status'] == "PASS" else "❌"
                    print(f"  {status_icon} {field}: {result['coverage_percent']:.1f}% ({result['present_count']}/{verification['captured_count']})")
            
            # Device-specific verification
            if topic in ['ESP32_BLE_GW_TX', 'dusun_sub']:
                ava4_verification = self.verify_ava4_payload_structure(messages)
                print(f"🏥 AVA4 specific verification: {ava4_verification['overall_status']}")
                
            elif topic.startswith('iMEDE_watch/'):
                kati_verification = self.verify_kati_payload_structure(topic, messages)
                print(f"⌚ Kati Watch specific verification: {kati_verification['overall_status']}")
                
            elif topic == 'CM4_BLE_GW_TX':
                qube_verification = self.verify_qube_payload_structure(messages)
                print(f"🏥 Qube-Vital specific verification: {qube_verification['overall_status']}")
        
        # Generate summary report
        self.generate_summary_report()
    
    def generate_summary_report(self):
        """Generate summary verification report"""
        print(f"\n📋 VERIFICATION SUMMARY REPORT")
        print("="*80)
        
        # Calculate overall statistics
        total_messages = sum(len(messages) for messages in self.captured_messages.values())
        topics_with_data = len([t for t, m in self.captured_messages.items() if m])
        expected_topics = len(self.expected_topics)
        
        print(f"📊 Overall Statistics:")
        print(f"  📨 Total messages: {total_messages}")
        print(f"  📡 Topics with data: {topics_with_data}/{expected_topics}")
        print(f"  ⏱️  Monitoring duration: {datetime.utcnow() - self.start_time}")
        
        # Topic coverage
        print(f"\n📈 Topic Coverage:")
        for topic in self.expected_topics.keys():
            message_count = len(self.captured_messages.get(topic, []))
            status = "✅" if message_count > 0 else "❌"
            print(f"  {status} {topic}: {message_count} messages")
        
        # Recommendations
        print(f"\n💡 Recommendations:")
        if total_messages == 0:
            print("  ❌ No messages captured - check MQTT broker connectivity and device activity")
        elif topics_with_data < expected_topics:
            print("  ⚠️  Not all topics received data - verify device connectivity and topic subscriptions")
        else:
            print("  ✅ All expected topics received data")
        
        # Save detailed report
        self.save_detailed_report()
    
    def save_detailed_report(self):
        """Save detailed verification report to file"""
        report_file = f"mqtt_verification_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        
        report = {
            "verification_timestamp": datetime.utcnow().isoformat(),
            "monitoring_duration": str(datetime.utcnow() - self.start_time),
            "total_messages": sum(len(messages) for messages in self.captured_messages.values()),
            "topic_verification": {},
            "sample_messages": {}
        }
        
        # Add verification results for each topic
        for topic, messages in self.captured_messages.items():
            verification = self.verify_topic_structure(topic, messages)
            report["topic_verification"][topic] = verification
            
            # Add sample message
            if messages:
                report["sample_messages"][topic] = messages[0]["payload"]
        
        # Save to file
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"📄 Detailed report saved to: {report_file}")

def main():
    """Main function"""
    verifier = MQTTCaptureVerifier()
    
    # Run verification for 5 minutes (adjust as needed)
    verifier.run_verification(duration_minutes=5)

if __name__ == "__main__":
    main() 