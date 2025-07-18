#!/usr/bin/env python3
"""
Real-time MQTT Monitor for Medical Device Data
Captures and displays all MQTT topics and payloads for verification
"""

import os
import json
import time
import logging
from datetime import datetime
from typing import Dict, Any
from paho.mqtt import client as mqtt_client
import threading
from collections import deque, defaultdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MQTTRealTimeMonitor:
    """Real-time MQTT monitoring for medical device data"""
    
    def __init__(self):
        # MQTT Configuration
        self.mqtt_broker = os.getenv('MQTT_BROKER_HOST', 'adam.amy.care')
        self.mqtt_port = int(os.getenv('MQTT_BROKER_PORT', 1883))
        self.mqtt_username = os.getenv('MQTT_USERNAME', 'webapi')
        self.mqtt_password = os.getenv('MQTT_PASSWORD', 'Sim!4433')
        self.mqtt_qos = int(os.getenv('MQTT_QOS', 1))
        
        # All medical device topics
        self.topics = [
            # AVA4 Topics
            'ESP32_BLE_GW_TX',  # AVA4 status messages
            'dusun_sub',        # AVA4 medical device data
            
            # Kati Watch Topics
            'iMEDE_watch/VitalSign',    # Real-time vital signs
            'iMEDE_watch/AP55',         # Batch vital signs
            'iMEDE_watch/hb',           # Heartbeat/step data
            'iMEDE_watch/location',     # Location data
            'iMEDE_watch/sleepdata',    # Sleep data
            'iMEDE_watch/sos',          # Emergency SOS
            'iMEDE_watch/fallDown',     # Fall detection
            'iMEDE_watch/onlineTrigger', # Online/offline status
            
            # Qube-Vital Topics
            'CM4_BLE_GW_TX'    # Qube-Vital data
        ]
        
        # Message storage
        self.message_history = deque(maxlen=1000)  # Keep last 1000 messages
        self.topic_stats = defaultdict(int)
        self.device_stats = defaultdict(int)
        
        # MQTT client
        self.client = None
        self.connected = False
        
        # Statistics
        self.start_time = datetime.utcnow()
        self.total_messages = 0
        
    def connect_mqtt(self) -> mqtt_client.Client:
        """Connect to MQTT broker"""
        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                logger.info("✅ Connected to MQTT broker successfully")
                self.connected = True
                # Subscribe to all topics
                for topic in self.topics:
                    client.subscribe(topic, self.mqtt_qos)
                    logger.info(f"📡 Subscribed to topic: {topic}")
            else:
                logger.error(f"❌ Failed to connect to MQTT broker, return code: {rc}")
                self.connected = False
        
        def on_disconnect(client, userdata, rc):
            logger.warning(f"⚠️ Disconnected from MQTT broker, return code: {rc}")
            self.connected = False
        
        def on_message(client, userdata, msg):
            try:
                self.process_message(msg.topic, msg.payload.decode())
            except Exception as e:
                logger.error(f"❌ Error processing message: {e}")
        
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
    
    def process_message(self, topic: str, payload: str):
        """Process incoming MQTT message"""
        try:
            # Parse JSON payload
            data = json.loads(payload)
            
            # Update statistics
            self.total_messages += 1
            self.topic_stats[topic] += 1
            
            # Identify device type
            device_type = self.identify_device_type(topic, data)
            self.device_stats[device_type] += 1
            
            # Create message record
            message_record = {
                "timestamp": datetime.utcnow(),
                "topic": topic,
                "device_type": device_type,
                "payload": data,
                "message_size": len(payload),
                "message_number": self.total_messages
            }
            
            # Add to history
            self.message_history.append(message_record)
            
            # Display message
            self.display_message(message_record)
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ Invalid JSON payload on topic {topic}: {e}")
            logger.error(f"📄 Raw payload: {payload[:200]}...")
        except Exception as e:
            logger.error(f"❌ Error processing message on topic {topic}: {e}")
    
    def identify_device_type(self, topic: str, data: Dict[str, Any]) -> str:
        """Identify device type from topic and payload"""
        if topic in ['ESP32_BLE_GW_TX', 'dusun_sub']:
            return "AVA4"
        elif topic.startswith('iMEDE_watch/'):
            return "Kati_Watch"
        elif topic == 'CM4_BLE_GW_TX':
            return "Qube_Vital"
        else:
            return "Unknown"
    
    def display_message(self, message_record: Dict[str, Any]):
        """Display message in a formatted way"""
        timestamp = message_record["timestamp"].strftime("%H:%M:%S")
        topic = message_record["topic"]
        device_type = message_record["device_type"]
        payload = message_record["payload"]
        msg_num = message_record["message_number"]
        
        print(f"\n{'='*80}")
        print(f"📨 MESSAGE #{msg_num} | {timestamp} | {device_type}")
        print(f"📡 TOPIC: {topic}")
        print(f"{'='*80}")
        
        # Display payload based on device type
        if device_type == "AVA4":
            self.display_ava4_payload(payload)
        elif device_type == "Kati_Watch":
            self.display_kati_payload(topic, payload)
        elif device_type == "Qube_Vital":
            self.display_qube_payload(payload)
        else:
            print(f"📊 PAYLOAD: {json.dumps(payload, indent=2)}")
        
        print(f"{'='*80}")
    
    def display_ava4_payload(self, payload: Dict[str, Any]):
        """Display AVA4 payload in a readable format"""
        msg_type = payload.get('type', 'unknown')
        mac = payload.get('mac', 'N/A')
        imei = payload.get('IMEI', 'N/A')
        
        print(f"🔧 AVA4 Message Type: {msg_type}")
        print(f"📱 MAC Address: {mac}")
        print(f"📞 IMEI: {imei}")
        
        if msg_type == "reportAttribute":
            attribute = payload.get('data', {}).get('attribute', 'N/A')
            device = payload.get('device', 'N/A')
            value = payload.get('data', {}).get('value', {})
            
            print(f"🏥 Device: {device}")
            print(f"📊 Attribute: {attribute}")
            
            # Display medical data
            if 'device_list' in value:
                print(f"📈 Medical Data:")
                for i, device_data in enumerate(value['device_list']):
                    print(f"  Reading {i+1}: {json.dumps(device_data, indent=4)}")
            else:
                print(f"📊 Value: {json.dumps(value, indent=2)}")
        else:
            print(f"📊 Full Payload: {json.dumps(payload, indent=2)}")
    
    def display_kati_payload(self, topic: str, payload: Dict[str, Any]):
        """Display Kati Watch payload in a readable format"""
        imei = payload.get('IMEI', 'N/A')
        
        print(f"⌚ Kati Watch Topic: {topic}")
        print(f"📞 IMEI: {imei}")
        
        if topic == "iMEDE_watch/VitalSign":
            print(f"💓 Vital Signs Data:")
            if 'heartRate' in payload:
                print(f"  ❤️  Heart Rate: {payload['heartRate']} bpm")
            if 'bloodPressure' in payload:
                bp = payload['bloodPressure']
                print(f"  🩸 Blood Pressure: {bp.get('bp_sys', 'N/A')}/{bp.get('bp_dia', 'N/A')} mmHg")
            if 'spO2' in payload:
                print(f"  🫁 SpO2: {payload['spO2']}%")
            if 'bodyTemperature' in payload:
                print(f"  🌡️  Body Temperature: {payload['bodyTemperature']}°C")
            if 'battery' in payload:
                print(f"  🔋 Battery: {payload['battery']}%")
            if 'signalGSM' in payload:
                print(f"  📶 Signal: {payload['signalGSM']}%")
        
        elif topic == "iMEDE_watch/AP55":
            print(f"📦 Batch Vital Signs Data:")
            data_list = payload.get('data', [])
            print(f"  📊 Number of readings: {len(data_list)}")
            for i, data_item in enumerate(data_list[:3]):  # Show first 3
                print(f"  Reading {i+1}: {json.dumps(data_item, indent=4)}")
        
        elif topic in ["iMEDE_watch/sos", "iMEDE_watch/fallDown"]:
            print(f"🚨 Emergency Alert: {topic}")
            print(f"  Status: {payload.get('status', 'N/A')}")
            if 'location' in payload:
                print(f"  📍 Location: {json.dumps(payload['location'], indent=4)}")
        
        else:
            print(f"📊 Full Payload: {json.dumps(payload, indent=2)}")
    
    def display_qube_payload(self, payload: Dict[str, Any]):
        """Display Qube-Vital payload in a readable format"""
        msg_type = payload.get('type', 'unknown')
        mac = payload.get('mac', 'N/A')
        imei = payload.get('IMEI', 'N/A')
        citiz = payload.get('citiz', 'N/A')
        
        print(f"🏥 Qube-Vital Message Type: {msg_type}")
        print(f"📱 MAC Address: {mac}")
        print(f"📞 IMEI: {imei}")
        print(f"🆔 Citizen ID: {citiz}")
        
        if msg_type == "reportAttribute":
            attribute = payload.get('data', {}).get('attribute', 'N/A')
            value = payload.get('data', {}).get('value', {})
            
            print(f"📊 Attribute: {attribute}")
            print(f"📈 Medical Data: {json.dumps(value, indent=2)}")
        else:
            print(f"📊 Full Payload: {json.dumps(payload, indent=2)}")
    
    def display_statistics(self):
        """Display real-time statistics"""
        runtime = datetime.utcnow() - self.start_time
        runtime_seconds = runtime.total_seconds()
        messages_per_second = self.total_messages / runtime_seconds if runtime_seconds > 0 else 0
        
        print(f"\n{'='*80}")
        print(f"📊 REAL-TIME STATISTICS")
        print(f"{'='*80}")
        print(f"⏱️  Runtime: {runtime}")
        print(f"📨 Total Messages: {self.total_messages}")
        print(f"🚀 Messages/sec: {messages_per_second:.2f}")
        print(f"📡 Connected: {'✅ Yes' if self.connected else '❌ No'}")
        
        print(f"\n📈 Topic Statistics:")
        for topic, count in sorted(self.topic_stats.items(), key=lambda x: x[1], reverse=True):
            print(f"  {topic}: {count} messages")
        
        print(f"\n📱 Device Statistics:")
        for device, count in sorted(self.device_stats.items(), key=lambda x: x[1], reverse=True):
            print(f"  {device}: {count} messages")
        
        print(f"\n🕒 Recent Messages:")
        for msg in list(self.message_history)[-5:]:  # Last 5 messages
            timestamp = msg["timestamp"].strftime("%H:%M:%S")
            print(f"  {timestamp} | {msg['topic']} | {msg['device_type']}")
        
        print(f"{'='*80}")
    
    def start_monitoring(self):
        """Start real-time monitoring"""
        print("🚀 Starting Real-time MQTT Monitor for Medical Devices")
        print("="*80)
        print(f"📡 Broker: {self.mqtt_broker}:{self.mqtt_port}")
        print(f"👤 Username: {self.mqtt_username}")
        print(f"📋 Topics: {', '.join(self.topics)}")
        print("="*80)
        
        # Connect to MQTT broker
        self.client = self.connect_mqtt()
        if not self.client:
            logger.error("❌ Failed to connect to MQTT broker")
            return
        
        # Start statistics display thread
        stats_thread = threading.Thread(target=self.stats_loop, daemon=True)
        stats_thread.start()
        
        try:
            # Keep monitoring
            while True:
                time.sleep(1)
                
        except KeyboardInterrupt:
            print("\n🛑 Stopping MQTT monitor...")
        except Exception as e:
            logger.error(f"❌ Unexpected error: {e}")
        finally:
            if self.client:
                self.client.loop_stop()
                self.client.disconnect()
    
    def stats_loop(self):
        """Display statistics periodically"""
        while True:
            time.sleep(30)  # Update every 30 seconds
            self.display_statistics()

def main():
    """Main function"""
    monitor = MQTTRealTimeMonitor()
    monitor.start_monitoring()

if __name__ == "__main__":
    main() 