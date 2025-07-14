#!/usr/bin/env python3
"""
Real MQTT Data Monitoring and Analysis
======================================
Script to monitor real MQTT messages, log payloads, and verify data processing
"""

import asyncio
import json
import time
import logging
from datetime import datetime
import paho.mqtt.client as mqtt
import requests
from typing import Dict, Any, List
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('mqtt_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# MQTT Configuration
MQTT_BROKER = "adam.amy.care"
MQTT_PORT = 1883
MQTT_USERNAME = "webapi"
MQTT_PASSWORD = "Sim!4433"

# API Configuration
API_BASE_URL = "https://stardust.my-firstcare.com"
API_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiYWRtaW4iLCJ1c2VybmFtZSI6ImFkbWluIiwicm9sZSI6ImFkbWluIiwiZXhwIjoxNzM0MTQ0NzE5fQ.Ej8Ej8Ej8Ej8Ej8Ej8Ej8Ej8Ej8Ej8Ej8Ej8Ej8Ej8"

# Topics to monitor
TOPICS_TO_MONITOR = [
    "iMEDE_watch/#",      # Kati Watch
    "ESP32_BLE_GW_TX",    # AVA4
    "dusun_sub",          # AVA4 sub-devices
    "CM4_BLE_GW_TX",      # Qube-Vital
    "qube/#"              # Qube-Vital (alternative)
]

class MQTTDataMonitor:
    """Monitor and analyze real MQTT data"""
    
    def __init__(self):
        self.mqtt_client = None
        self.message_count = 0
        self.messages_by_topic = {}
        self.messages_by_device = {}
        self.processing_results = []
        self.start_time = datetime.utcnow()
        
    def on_connect(self, client, userdata, flags, rc):
        """Callback when connected to MQTT broker"""
        if rc == 0:
            logger.info(f"✅ Connected to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}")
            # Subscribe to all topics
            for topic in TOPICS_TO_MONITOR:
                client.subscribe(topic, 1)
                logger.info(f"📡 Subscribed to topic: {topic}")
        else:
            logger.error(f"❌ Failed to connect to MQTT broker, return code: {rc}")
    
    def on_message(self, client, userdata, msg):
        """Callback when message is received"""
        try:
            self.message_count += 1
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            timestamp = datetime.utcnow()
            
            logger.info(f"📨 Message #{self.message_count} received on topic: {topic}")
            logger.info(f"   Timestamp: {timestamp}")
            logger.info(f"   Payload length: {len(payload)} bytes")
            
            # Parse JSON payload
            try:
                data = json.loads(payload)
                logger.info(f"   JSON parsed successfully")
                
                # Analyze payload structure
                self.analyze_payload(topic, data, timestamp)
                
                # Check transaction logging
                self.check_transaction_logging(topic, data, timestamp)
                
            except json.JSONDecodeError as e:
                logger.error(f"   ❌ Invalid JSON payload: {e}")
                logger.info(f"   Raw payload: {payload[:200]}...")
                
        except Exception as e:
            logger.error(f"❌ Error processing message: {e}")
    
    def analyze_payload(self, topic: str, data: Dict[str, Any], timestamp: datetime):
        """Analyze the structure and content of MQTT payload"""
        logger.info(f"🔍 Analyzing payload structure:")
        
        # Track messages by topic
        if topic not in self.messages_by_topic:
            self.messages_by_topic[topic] = []
        self.messages_by_topic[topic].append({
            'timestamp': timestamp,
            'data': data,
            'message_count': self.message_count
        })
        
        # Extract device identifiers
        device_id = self.extract_device_id(topic, data)
        if device_id:
            if device_id not in self.messages_by_device:
                self.messages_by_device[device_id] = []
            self.messages_by_device[device_id].append({
                'timestamp': timestamp,
                'topic': topic,
                'data': data,
                'message_count': self.message_count
            })
            logger.info(f"   Device ID: {device_id}")
        
        # Log key fields based on topic
        if topic.startswith("iMEDE_watch/"):
            self.analyze_kati_payload(data)
        elif topic == "ESP32_BLE_GW_TX":
            self.analyze_ava4_payload(data)
        elif topic == "dusun_sub":
            self.analyze_ava4_sub_payload(data)
        elif topic == "CM4_BLE_GW_TX":
            self.analyze_qube_payload(data)
        elif topic.startswith("qube/"):
            self.analyze_qube_alt_payload(data)
    
    def extract_device_id(self, topic: str, data: Dict[str, Any]) -> str:
        """Extract device identifier from payload"""
        if topic.startswith("iMEDE_watch/"):
            return data.get('IMEI', 'unknown_imei')
        elif topic == "ESP32_BLE_GW_TX":
            return data.get('mac', data.get('mac_address', 'unknown_mac'))
        elif topic == "dusun_sub":
            return data.get('mac', 'unknown_mac')
        elif topic == "CM4_BLE_GW_TX":
            return data.get('mac', data.get('device_id', 'unknown_device'))
        elif topic.startswith("qube/"):
            return data.get('device_id', 'unknown_device')
        return 'unknown'
    
    def analyze_kati_payload(self, data: Dict[str, Any]):
        """Analyze Kati Watch payload structure"""
        logger.info(f"   📱 Kati Watch Data Analysis:")
        logger.info(f"      IMEI: {data.get('IMEI', 'N/A')}")
        logger.info(f"      Timestamp: {data.get('timestamp', 'N/A')}")
        
        # Check for vital signs
        vital_signs = []
        if 'heart_rate' in data:
            vital_signs.append(f"HR: {data['heart_rate']}")
        if 'blood_pressure_systolic' in data:
            vital_signs.append(f"BP: {data['blood_pressure_systolic']}/{data.get('blood_pressure_diastolic', 'N/A')}")
        if 'temperature' in data:
            vital_signs.append(f"Temp: {data['temperature']}")
        if 'spo2' in data:
            vital_signs.append(f"SpO2: {data['spo2']}")
        
        if vital_signs:
            logger.info(f"      Vital Signs: {', '.join(vital_signs)}")
        
        # Check for location data
        if 'latitude' in data and 'longitude' in data:
            logger.info(f"      Location: {data['latitude']}, {data['longitude']}")
    
    def analyze_ava4_payload(self, data: Dict[str, Any]):
        """Analyze AVA4 payload structure"""
        logger.info(f"   📱 AVA4 Data Analysis:")
        logger.info(f"      MAC: {data.get('mac', data.get('mac_address', 'N/A'))}")
        logger.info(f"      Type: {data.get('type', 'N/A')}")
        logger.info(f"      Message Type: {data.get('message_type', 'N/A')}")
        
        # Check for vital signs
        vital_signs = []
        if 'heart_rate' in data:
            vital_signs.append(f"HR: {data['heart_rate']}")
        if 'blood_pressure_systolic' in data:
            vital_signs.append(f"BP: {data['blood_pressure_systolic']}/{data.get('blood_pressure_diastolic', 'N/A')}")
        if 'temperature' in data:
            vital_signs.append(f"Temp: {data['temperature']}")
        if 'spo2' in data:
            vital_signs.append(f"SpO2: {data['spo2']}")
        
        if vital_signs:
            logger.info(f"      Vital Signs: {', '.join(vital_signs)}")
    
    def analyze_ava4_sub_payload(self, data: Dict[str, Any]):
        """Analyze AVA4 sub-device payload structure"""
        logger.info(f"   📱 AVA4 Sub-Device Data Analysis:")
        logger.info(f"      MAC: {data.get('mac', 'N/A')}")
        logger.info(f"      Type: {data.get('type', 'N/A')}")
        logger.info(f"      Device Code: {data.get('deviceCode', 'N/A')}")
        
        # Check for medical data
        if 'data' in data and 'attribute' in data['data']:
            logger.info(f"      Attribute: {data['data']['attribute']}")
            logger.info(f"      Value: {data['data'].get('value', 'N/A')}")
    
    def analyze_qube_payload(self, data: Dict[str, Any]):
        """Analyze Qube-Vital payload structure"""
        logger.info(f"   📱 Qube-Vital Data Analysis:")
        logger.info(f"      MAC: {data.get('mac', 'N/A')}")
        logger.info(f"      Type: {data.get('type', 'N/A')}")
        logger.info(f"      Citizen ID: {data.get('citiz', 'N/A')}")
        
        # Check for medical data
        if 'data' in data and 'attribute' in data['data']:
            logger.info(f"      Attribute: {data['data']['attribute']}")
            logger.info(f"      Value: {data['data'].get('value', 'N/A')}")
    
    def analyze_qube_alt_payload(self, data: Dict[str, Any]):
        """Analyze Qube-Vital alternative payload structure"""
        logger.info(f"   📱 Qube-Vital Alt Data Analysis:")
        logger.info(f"      Device ID: {data.get('device_id', 'N/A')}")
        logger.info(f"      Timestamp: {data.get('timestamp', 'N/A')}")
        
        # Check for vital signs
        vital_signs = []
        if 'heart_rate' in data:
            vital_signs.append(f"HR: {data['heart_rate']}")
        if 'blood_pressure_systolic' in data:
            vital_signs.append(f"BP: {data['blood_pressure_systolic']}/{data.get('blood_pressure_diastolic', 'N/A')}")
        if 'temperature' in data:
            vital_signs.append(f"Temp: {data['temperature']}")
        if 'spo2' in data:
            vital_signs.append(f"SpO2: {data['spo2']}")
        
        if vital_signs:
            logger.info(f"      Vital Signs: {', '.join(vital_signs)}")
    
    def check_transaction_logging(self, topic: str, data: Dict[str, Any], timestamp: datetime):
        """Check if transaction was logged for this message"""
        try:
            # Wait a moment for transaction to be logged
            time.sleep(2)
            
            # Get recent transactions
            headers = {'Authorization': f'Bearer {API_TOKEN}'}
            response = requests.get(
                f"{API_BASE_URL}/api/transactions/recent?minutes=2&limit=10",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                transactions = response.json().get('data', {}).get('transactions', [])
                
                # Look for matching transaction
                device_id = self.extract_device_id(topic, data)
                matching_transactions = [
                    t for t in transactions 
                    if t.get('device_id') == device_id and 
                    abs((datetime.fromisoformat(t['timestamp'].replace('Z', '+00:00')) - timestamp).total_seconds()) < 30
                ]
                
                if matching_transactions:
                    logger.info(f"   ✅ Transaction logged: {matching_transactions[0]['operation']} - {matching_transactions[0]['status']}")
                    self.processing_results.append({
                        'message_count': self.message_count,
                        'topic': topic,
                        'device_id': device_id,
                        'transaction_found': True,
                        'transaction_status': matching_transactions[0]['status'],
                        'timestamp': timestamp
                    })
                else:
                    logger.warning(f"   ⚠️ No transaction found for device {device_id}")
                    self.processing_results.append({
                        'message_count': self.message_count,
                        'topic': topic,
                        'device_id': device_id,
                        'transaction_found': False,
                        'timestamp': timestamp
                    })
            else:
                logger.error(f"   ❌ Failed to get transactions: {response.status_code}")
                
        except Exception as e:
            logger.error(f"   ❌ Error checking transaction logging: {e}")
    
    def start_monitoring(self, duration_minutes: int = 10):
        """Start MQTT monitoring for specified duration"""
        logger.info(f"🚀 Starting MQTT Data Monitoring for {duration_minutes} minutes")
        logger.info(f"📊 Monitoring topics: {', '.join(TOPICS_TO_MONITOR)}")
        
        # Create MQTT client
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_message = self.on_message
        
        try:
            # Connect to MQTT broker
            self.mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
            self.mqtt_client.loop_start()
            
            # Monitor for specified duration
            start_time = time.time()
            while time.time() - start_time < (duration_minutes * 60):
                time.sleep(5)
                
                # Print periodic summary
                if int(time.time() - start_time) % 30 == 0:
                    self.print_summary()
            
        except KeyboardInterrupt:
            logger.info("🛑 Monitoring stopped by user")
        except Exception as e:
            logger.error(f"❌ Error during monitoring: {e}")
        finally:
            # Cleanup
            if self.mqtt_client:
                self.mqtt_client.loop_stop()
                self.mqtt_client.disconnect()
            
            # Print final summary
            self.print_final_summary()
    
    def print_summary(self):
        """Print periodic monitoring summary"""
        logger.info(f"📊 Summary - Messages: {self.message_count}, Topics: {len(self.messages_by_topic)}, Devices: {len(self.messages_by_device)}")
    
    def print_final_summary(self):
        """Print final monitoring summary"""
        logger.info("=" * 80)
        logger.info("📊 FINAL MQTT MONITORING SUMMARY")
        logger.info("=" * 80)
        
        # Overall statistics
        duration = datetime.utcnow() - self.start_time
        logger.info(f"⏱️  Monitoring Duration: {duration}")
        logger.info(f"📨 Total Messages Received: {self.message_count}")
        logger.info(f"📡 Topics Monitored: {len(self.messages_by_topic)}")
        logger.info(f"📱 Unique Devices: {len(self.messages_by_device)}")
        
        # Messages by topic
        logger.info("\n📡 Messages by Topic:")
        for topic, messages in self.messages_by_topic.items():
            logger.info(f"   {topic}: {len(messages)} messages")
        
        # Messages by device
        logger.info("\n📱 Messages by Device:")
        for device_id, messages in self.messages_by_device.items():
            logger.info(f"   {device_id}: {len(messages)} messages")
        
        # Processing results
        logger.info("\n✅ Transaction Processing Results:")
        successful = [r for r in self.processing_results if r.get('transaction_found')]
        failed = [r for r in self.processing_results if not r.get('transaction_found')]
        
        logger.info(f"   ✅ Successfully logged: {len(successful)}")
        logger.info(f"   ❌ Not logged: {len(failed)}")
        
        if failed:
            logger.info("\n❌ Messages without transactions:")
            for result in failed[:5]:  # Show first 5
                logger.info(f"   Message #{result['message_count']} - Topic: {result['topic']} - Device: {result['device_id']}")
        
        # Save detailed log
        self.save_detailed_log()
    
    def save_detailed_log(self):
        """Save detailed monitoring log to file"""
        log_data = {
            'monitoring_session': {
                'start_time': self.start_time.isoformat(),
                'end_time': datetime.utcnow().isoformat(),
                'total_messages': self.message_count,
                'topics_monitored': list(self.messages_by_topic.keys()),
                'unique_devices': list(self.messages_by_device.keys())
            },
            'messages_by_topic': {
                topic: [
                    {
                        'timestamp': msg['timestamp'].isoformat(),
                        'message_count': msg['message_count'],
                        'data': msg['data']
                    }
                    for msg in messages
                ]
                for topic, messages in self.messages_by_topic.items()
            },
            'processing_results': self.processing_results
        }
        
        with open(f'mqtt_monitoring_session_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}.json', 'w') as f:
            json.dump(log_data, f, indent=2, default=str)
        
        logger.info(f"💾 Detailed log saved to: mqtt_monitoring_session_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json")

def main():
    """Main function"""
    print("🔍 Real MQTT Data Monitoring and Analysis")
    print("=" * 60)
    
    # Use default duration of 5 minutes for monitoring
    duration = 5
    print(f"Monitoring for {duration} minutes...")
    
    # Start monitoring
    monitor = MQTTDataMonitor()
    monitor.start_monitoring(duration)

if __name__ == "__main__":
    main() 