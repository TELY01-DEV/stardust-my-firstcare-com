#!/usr/bin/env python3
"""
Complete Data Flow Monitor
Shows MQTT payload -> parser -> raw data -> patient collection update -> medical collection storage
"""

import os
import json
import time
import logging
import requests
from datetime import datetime
from typing import Dict, Any
from paho.mqtt import client as mqtt_client
import threading
from collections import deque

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Loaded environment variables from .env file")
except ImportError:
    print("⚠️ python-dotenv not installed, using system environment variables")
except Exception as e:
    print(f"⚠️ Could not load .env file: {e}")

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TelegramAlert:
    """Telegram alert functionality"""
    
    def __init__(self):
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.enabled = bool(self.bot_token and self.chat_id)
        
        if self.enabled:
            logger.info("✅ Telegram alerts enabled")
        else:
            logger.warning("⚠️ Telegram alerts disabled - Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID environment variables")
    
    def send_alert(self, message: str, alert_type: str = "WARNING"):
        """Send alert to Telegram"""
        if not self.enabled:
            return
        
        try:
            # Add emoji based on alert type
            emoji_map = {
                "ERROR": "🚨",
                "WARNING": "⚠️", 
                "SUCCESS": "✅",
                "INFO": "ℹ️"
            }
            emoji = emoji_map.get(alert_type, "📢")
            
            # Format message
            formatted_message = f"{emoji} **{alert_type}**\n\n{message}\n\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            # Send to Telegram
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            data = {
                "chat_id": self.chat_id,
                "text": formatted_message,
                "parse_mode": "Markdown"
            }
            
            response = requests.post(url, data=data, timeout=10)
            if response.status_code == 200:
                logger.info(f"✅ Telegram alert sent: {alert_type}")
            else:
                logger.error(f"❌ Failed to send Telegram alert: {response.status_code} - {response.text}")
                
        except Exception as e:
            logger.error(f"❌ Error sending Telegram alert: {e}")

class CompleteDataFlowMonitor:
    """Monitor complete data flow from MQTT to database"""
    
    def __init__(self):
        # MQTT Configuration
        self.mqtt_broker = os.getenv('MQTT_BROKER_HOST', 'adam.amy.care')
        self.mqtt_port = int(os.getenv('MQTT_BROKER_PORT', 1883))
        self.mqtt_username = os.getenv('MQTT_USERNAME', 'webapi')
        self.mqtt_password = os.getenv('MQTT_PASSWORD', 'Sim!4433')
        
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
        self.message_history = deque(maxlen=100)
        self.flow_tracking = {}
        
        # MQTT client
        self.client = None
        self.connected = False
        
        # Statistics
        self.start_time = datetime.utcnow()
        self.total_messages = 0
        
        # Failure tracking for alerts
        self.failure_count = 0
        self.last_failure_time = None
        self.failure_threshold = int(os.getenv('FAILURE_ALERT_THRESHOLD', '5'))  # Alert after 5 failures
        self.failure_window = int(os.getenv('FAILURE_WINDOW_MINUTES', '10'))  # 10 minute window
        
        # Telegram alerts
        self.telegram = TelegramAlert()
        
        # Container monitoring
        self.container_status = {}
        self.last_container_check = None
        
    def check_container_status(self):
        """Check Docker container status for failures"""
        try:
            import subprocess
            result = subprocess.run(['docker', 'ps', '--format', 'table {{.Names}}\t{{.Status}}'], 
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')[1:]  # Skip header
                current_status = {}
                
                for line in lines:
                    if line.strip():
                        parts = line.split('\t')
                        if len(parts) >= 2:
                            container_name = parts[0]
                            status = parts[1]
                            current_status[container_name] = status
                            
                            # Check for failures
                            if 'Exited' in status or 'unhealthy' in status.lower():
                                if container_name not in self.container_status or self.container_status[container_name] != status:
                                    self.telegram.send_alert(
                                        f"🚨 **Container Failure Detected**\n\n"
                                        f"**Container:** {container_name}\n"
                                        f"**Status:** {status}\n\n"
                                        f"Please check the container immediately!",
                                        "ERROR"
                                    )
                
                self.container_status = current_status
                self.last_container_check = datetime.utcnow()
                
        except Exception as e:
            logger.error(f"❌ Error checking container status: {e}")
    
    def track_failure(self, failure_type: str, details: str, device_type: str = "Unknown"):
        """Track failures and send alerts if threshold is reached"""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        # Check if we should send an alert
        if self.failure_count >= self.failure_threshold:
            # Check if failures are within the time window
            if (self.last_failure_time - self.start_time).total_seconds() <= (self.failure_window * 60):
                self.telegram.send_alert(
                    f"🚨 **High Failure Rate Detected**\n\n"
                    f"**Failures:** {self.failure_count} in {self.failure_window} minutes\n"
                    f"**Latest Failure:** {failure_type}\n"
                    f"**Device:** {device_type}\n"
                    f"**Details:** {details}\n\n"
                    f"Please investigate the system immediately!",
                    "ERROR"
                )
                
                # Reset counter after alert
                self.failure_count = 0
        
        # Send immediate alert for critical failures
        if failure_type in ["FHIR_R5_ERROR", "DATABASE_ERROR", "PATIENT_NOT_FOUND"]:
            self.telegram.send_alert(
                f"⚠️ **Critical Failure Detected**\n\n"
                f"**Type:** {failure_type}\n"
                f"**Device:** {device_type}\n"
                f"**Details:** {details}\n\n"
                f"Please check the system!",
                "WARNING"
            )
    
    def connect_mqtt(self) -> mqtt_client.Client:
        """Connect to MQTT broker"""
        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                logger.info("✅ Connected to MQTT broker successfully")
                self.connected = True
                # Subscribe to all topics
                for topic in self.topics:
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
        """Process incoming MQTT message and track data flow"""
        try:
            # Parse JSON payload
            data = json.loads(payload)
            
            # Update statistics
            self.total_messages += 1
            message_id = f"MSG_{self.total_messages}"
            
            # Create message record
            message_record = {
                "id": message_id,
                "timestamp": datetime.utcnow(),
                "topic": topic,
                "payload": data,
                "raw_payload": payload,
                "device_type": self.identify_device_type(topic, data)
            }
            
            # Add to history
            self.message_history.append(message_record)
            
            # Track data flow
            self.flow_tracking[message_id] = {
                "mqtt_received": True,
                "mqtt_timestamp": datetime.utcnow(),
                "topic": topic,
                "device_type": message_record["device_type"],
                "payload_size": len(payload),
                "processing_steps": []
            }
            
            # Display complete data flow
            self.display_complete_data_flow(message_record)
            
            # Check for potential failures in the payload
            self.check_payload_for_failures(message_record)
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ Invalid JSON payload on topic {topic}: {e}")
            self.track_failure("JSON_PARSE_ERROR", f"Topic: {topic}, Error: {e}", "Unknown")
        except Exception as e:
            logger.error(f"❌ Error processing message on topic {topic}: {e}")
            self.track_failure("MESSAGE_PROCESSING_ERROR", f"Topic: {topic}, Error: {e}", "Unknown")
    
    def check_payload_for_failures(self, message_record: Dict[str, Any]):
        """Check payload for potential failure indicators"""
        topic = message_record["topic"]
        device_type = message_record["device_type"]
        payload = message_record["payload"]
        
        # Check for error indicators in payload
        if isinstance(payload, dict):
            # Check for error fields
            if 'error' in payload and payload['error']:
                self.track_failure("PAYLOAD_ERROR", f"Error in payload: {payload['error']}", device_type)
            
            # Check for status fields indicating failure
            if 'status' in payload and payload['status'] in ['error', 'failed', 'failure']:
                self.track_failure("PAYLOAD_STATUS_ERROR", f"Status: {payload['status']}", device_type)
            
            # Check for specific device failures
            if device_type == "AVA4":
                if topic == "dusun_sub":
                    msg_type = payload.get('type', '')
                    if msg_type == 'cmdResult':
                        code = payload.get('data', {}).get('code', 0)
                        if code != 101:  # 101 is success code
                            self.track_failure("AVA4_COMMAND_FAILURE", f"Command failed with code: {code}", device_type)
            
            elif device_type == "Kati_Watch":
                # Check for low battery or signal issues
                if 'battery' in payload and payload['battery'] < 20:
                    self.track_failure("KATI_LOW_BATTERY", f"Battery level: {payload['battery']}%", device_type)
                
                if 'signalGSM' in payload and payload['signalGSM'] < 50:
                    self.track_failure("KATI_LOW_SIGNAL", f"GSM signal: {payload['signalGSM']}%", device_type)
    
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
    
    def display_complete_data_flow(self, message_record: Dict[str, Any]):
        """Display complete data flow for a message"""
        timestamp = message_record["timestamp"].strftime("%H:%M:%S.%f")[:-3]
        topic = message_record["topic"]
        device_type = message_record["device_type"]
        payload = message_record["payload"]
        msg_id = message_record["id"]
        
        print(f"\n{'='*100}")
        print(f"🔄 COMPLETE DATA FLOW - {msg_id} | {timestamp} | {device_type}")
        print(f"{'='*100}")
        
        # Step 1: MQTT Payload Reception
        print(f"📨 STEP 1: MQTT PAYLOAD RECEPTION")
        print(f"   📡 Topic: {topic}")
        print(f"   📊 Raw Payload Size: {len(message_record['raw_payload'])} bytes")
        print(f"   📋 Device Type: {device_type}")
        print(f"   📄 JSON Payload: {json.dumps(payload, indent=6)}")
        
        # Step 2: Expected Parser Processing
        print(f"\n🔧 STEP 2: EXPECTED PARSER PROCESSING")
        self.display_expected_parser_processing(device_type, topic, payload)
        
        # Step 3: Expected Patient Mapping
        print(f"\n👤 STEP 3: EXPECTED PATIENT MAPPING")
        self.display_expected_patient_mapping(device_type, payload)
        
        # Step 4: Expected Data Transformation
        print(f"\n🔄 STEP 4: EXPECTED DATA TRANSFORMATION")
        self.display_expected_data_transformation(device_type, topic, payload)
        
        # Step 5: Expected Database Operations
        print(f"\n💾 STEP 5: EXPECTED DATABASE OPERATIONS")
        self.display_expected_database_operations(device_type, topic, payload)
        
        print(f"{'='*100}")
        
        # Update flow tracking
        self.flow_tracking[msg_id]["processing_steps"].append({
            "step": "mqtt_received",
            "timestamp": datetime.utcnow(),
            "details": f"Topic: {topic}, Device: {device_type}"
        })
    
    def display_expected_parser_processing(self, device_type: str, topic: str, payload: Dict[str, Any]):
        """Display expected parser processing steps"""
        if device_type == "AVA4":
            if topic == "dusun_sub":
                msg_type = payload.get('type', 'unknown')
                device_mac = payload.get('mac', 'N/A')
                attribute = payload.get('data', {}).get('attribute', 'N/A')
                value = payload.get('data', {}).get('value', {})
                
                print(f"   🔍 Message Type: {msg_type}")
                print(f"   📱 Device MAC: {device_mac}")
                print(f"   🏥 Attribute: {attribute}")
                print(f"   📊 Value Structure: {json.dumps(value, indent=8)}")
                
                if 'device_list' in value:
                    print(f"   📈 Device Readings: {len(value['device_list'])} items")
                    for i, reading in enumerate(value['device_list'][:2]):  # Show first 2
                        print(f"     Reading {i+1}: {json.dumps(reading, indent=8)}")
                
            elif topic == "ESP32_BLE_GW_TX":
                msg_type = payload.get('type', 'unknown')
                mac = payload.get('mac', 'N/A')
                imei = payload.get('IMEI', 'N/A')
                print(f"   🔍 Message Type: {msg_type}")
                print(f"   📱 MAC Address: {mac}")
                print(f"   📞 IMEI: {imei}")
        
        elif device_type == "Kati_Watch":
            imei = payload.get('IMEI', 'N/A')
            print(f"   📞 IMEI: {imei}")
            
            if topic == "iMEDE_watch/VitalSign":
                print(f"   💓 Vital Signs Data:")
                if 'heartRate' in payload:
                    print(f"     ❤️  Heart Rate: {payload['heartRate']} bpm")
                if 'bloodPressure' in payload:
                    bp = payload['bloodPressure']
                    print(f"     🩸 Blood Pressure: {bp.get('bp_sys', 'N/A')}/{bp.get('bp_dia', 'N/A')} mmHg")
                if 'spO2' in payload:
                    print(f"     🫁 SpO2: {payload['spO2']}%")
                if 'bodyTemperature' in payload:
                    print(f"     🌡️  Body Temperature: {payload['bodyTemperature']}°C")
            
            elif topic == "iMEDE_watch/AP55":
                data_list = payload.get('data', [])
                print(f"   📦 Batch Data: {len(data_list)} readings")
                for i, data_item in enumerate(data_list[:2]):  # Show first 2
                    print(f"     Reading {i+1}: {json.dumps(data_item, indent=8)}")
        
        elif device_type == "Qube_Vital":
            msg_type = payload.get('type', 'unknown')
            mac = payload.get('mac', 'N/A')
            imei = payload.get('IMEI', 'N/A')
            citiz = payload.get('citiz', 'N/A')
            
            print(f"   🔍 Message Type: {msg_type}")
            print(f"   📱 MAC Address: {mac}")
            print(f"   📞 IMEI: {imei}")
            print(f"   🆔 Citizen ID: {citiz}")
            
            if msg_type == "reportAttribute":
                attribute = payload.get('data', {}).get('attribute', 'N/A')
                value = payload.get('data', {}).get('value', {})
                print(f"   🏥 Attribute: {attribute}")
                print(f"   📊 Value: {json.dumps(value, indent=8)}")
    
    def display_expected_patient_mapping(self, device_type: str, payload: Dict[str, Any]):
        """Display expected patient mapping logic"""
        print(f"   🔍 Expected Patient Lookup:")
        
        if device_type == "AVA4":
            mac = payload.get('mac', 'N/A')
            print(f"     📱 AVA4 MAC: {mac}")
            print(f"     🔍 Query: {{'ava_mac_address': '{mac}'}}")
            print(f"     📊 Expected: Find patient by AVA4 MAC address")
        
        elif device_type == "Kati_Watch":
            imei = payload.get('IMEI', 'N/A')
            print(f"     📞 Kati IMEI: {imei}")
            print(f"     🔍 Query 1: {{'imei': '{imei}'}} in watches collection")
            print(f"     🔍 Query 2: {{'watch_mac_address': '{imei}'}} in patients collection")
            print(f"     📊 Expected: Find patient by Kati IMEI")
        
        elif device_type == "Qube_Vital":
            citiz = payload.get('citiz', 'N/A')
            print(f"     🆔 Citizen ID: {citiz}")
            print(f"     🔍 Query: {{'id_card': '{citiz}'}}")
            print(f"     📊 Expected: Find patient by citizen ID")
            if not citiz or citiz == 'N/A':
                print(f"     ⚠️  WARNING: No citizen ID - may create unregistered patient")
    
    def display_expected_data_transformation(self, device_type: str, topic: str, payload: Dict[str, Any]):
        """Display expected data transformation steps"""
        print(f"   🔄 Expected Data Transformation:")
        
        if device_type == "AVA4" and topic == "dusun_sub":
            attribute = payload.get('data', {}).get('attribute', 'N/A')
            value = payload.get('data', {}).get('value', {})
            
            print(f"     🏥 Attribute: {attribute}")
            print(f"     📊 Raw Value: {json.dumps(value, indent=8)}")
            
            # Show expected transformations
            if attribute == "BP_BIOLIGTH":
                print(f"     🔄 Expected Transform:")
                print(f"       Input: device_list with bp_high, bp_low, PR, scan_time")
                print(f"       Output: {{'systolic': value, 'diastolic': value, 'pulse_rate': value}}")
            
            elif attribute in ["Contour_Elite", "AccuChek_Instant"]:
                print(f"     🔄 Expected Transform:")
                print(f"       Input: device_list with blood_glucose, marker, scan_time")
                print(f"       Output: {{'value': value, 'marker': value}}")
            
            elif attribute == "Oximeter JUMPER":
                print(f"     🔄 Expected Transform:")
                print(f"       Input: device_list with spo2, pulse, pi, scan_time")
                print(f"       Output: {{'value': value, 'pulse_rate': value}}")
        
        elif device_type == "Kati_Watch" and topic == "iMEDE_watch/VitalSign":
            print(f"     🔄 Expected Transforms:")
            if 'heartRate' in payload:
                print(f"       Heart Rate: {payload['heartRate']} -> {{'value': {payload['heartRate']}}}")
            if 'bloodPressure' in payload:
                bp = payload['bloodPressure']
                print(f"       Blood Pressure: {bp} -> {{'systolic': {bp.get('bp_sys')}, 'diastolic': {bp.get('bp_dia')}}}")
            if 'spO2' in payload:
                print(f"       SpO2: {payload['spO2']} -> {{'value': {payload['spO2']}}}")
            if 'bodyTemperature' in payload:
                print(f"       Temperature: {payload['bodyTemperature']} -> {{'value': {payload['bodyTemperature']}}}")
        
        elif device_type == "Qube_Vital":
            attribute = payload.get('data', {}).get('attribute', 'N/A')
            value = payload.get('data', {}).get('value', {})
            print(f"     🏥 Attribute: {attribute}")
            print(f"     📊 Raw Value: {json.dumps(value, indent=8)}")
    
    def display_expected_database_operations(self, device_type: str, topic: str, payload: Dict[str, Any]):
        """Display expected database operations"""
        print(f"   💾 Expected Database Operations:")
        
        if device_type == "AVA4" and topic == "dusun_sub":
            attribute = payload.get('data', {}).get('attribute', 'N/A')
            
            # Map attribute to data type
            attribute_mapping = {
                "BP_BIOLIGTH": "blood_pressure",
                "Contour_Elite": "blood_sugar",
                "AccuChek_Instant": "blood_sugar",
                "Oximeter JUMPER": "spo2",
                "IR_TEMO_JUMPER": "body_temp",
                "BodyScale_JUMPER": "weight",
                "MGSS_REF_UA": "uric_acid",
                "MGSS_REF_CHOL": "cholesterol"
            }
            
            data_type = attribute_mapping.get(attribute, "unknown")
            
            print(f"     📝 1. UPDATE PATIENT COLLECTION:")
            print(f"        Collection: patients")
            print(f"        Field: last_{data_type}")
            print(f"        Data: {{'value': processed_data, 'timestamp': now, 'source': 'AVA4'}}")
            
            print(f"     📚 2. INSERT MEDICAL HISTORY:")
            print(f"        Collection: {data_type}_histories")
            print(f"        Data: {{'patient_id': patient_id, 'data': processed_data, 'source': 'AVA4', 'timestamp': now}}")
        
        elif device_type == "Kati_Watch" and topic == "iMEDE_watch/VitalSign":
            print(f"     📝 1. UPDATE PATIENT COLLECTION:")
            if 'heartRate' in payload:
                print(f"        Field: last_heart_rate")
                print(f"        Data: {{'value': {payload['heartRate']}, 'source': 'Kati'}}")
            if 'bloodPressure' in payload:
                print(f"        Field: last_blood_pressure")
                print(f"        Data: {{'systolic': {payload['bloodPressure'].get('bp_sys')}, 'diastolic': {payload['bloodPressure'].get('bp_dia')}, 'source': 'Kati'}}")
            if 'spO2' in payload:
                print(f"        Field: last_spo2")
                print(f"        Data: {{'value': {payload['spO2']}, 'source': 'Kati'}}")
            if 'bodyTemperature' in payload:
                print(f"        Field: last_body_temperature")
                print(f"        Data: {{'value': {payload['bodyTemperature']}, 'source': 'Kati'}}")
            
            print(f"     📚 2. INSERT MEDICAL HISTORY:")
            print(f"        Collections: heart_rate_histories, blood_pressure_histories, spo2_histories, temprature_data_histories")
        
        elif device_type == "Qube_Vital":
            attribute = payload.get('data', {}).get('attribute', 'N/A')
            
            # Map attribute to data type
            attribute_mapping = {
                "WBP_JUMPER": "blood_pressure",
                "CONTOUR": "blood_sugar",
                "BodyScale_JUMPER": "weight",
                "TEMO_Jumper": "body_temp",
                "Oximeter_JUMPER": "spo2"
            }
            
            data_type = attribute_mapping.get(attribute, "unknown")
            
            print(f"     📝 1. UPDATE PATIENT COLLECTION:")
            print(f"        Collection: patients")
            print(f"        Field: last_{data_type}")
            print(f"        Data: {{'value': processed_data, 'timestamp': now, 'source': 'Qube-Vital'}}")
            
            print(f"     📚 2. INSERT MEDICAL HISTORY:")
            print(f"        Collection: {data_type}_histories")
            print(f"        Data: {{'patient_id': patient_id, 'data': processed_data, 'source': 'Qube-Vital', 'timestamp': now}}")
    
    def display_statistics(self):
        """Display real-time statistics"""
        runtime = datetime.utcnow() - self.start_time
        runtime_seconds = runtime.total_seconds()
        messages_per_second = self.total_messages / runtime_seconds if runtime_seconds > 0 else 0
        
        print(f"\n{'='*100}")
        print(f"📊 COMPLETE DATA FLOW STATISTICS")
        print(f"{'='*100}")
        print(f"⏱️  Runtime: {runtime}")
        print(f"📨 Total Messages: {self.total_messages}")
        print(f"🚀 Messages/sec: {messages_per_second:.2f}")
        print(f"📡 Connected: {'✅ Yes' if self.connected else '❌ No'}")
        
        # Device type breakdown
        device_counts = {}
        for msg in self.message_history:
            device_type = msg["device_type"]
            device_counts[device_type] = device_counts.get(device_type, 0) + 1
        
        print(f"\n📱 Device Type Breakdown:")
        for device, count in sorted(device_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"  {device}: {count} messages")
        
        print(f"\n🕒 Recent Messages:")
        for msg in list(self.message_history)[-5:]:  # Last 5 messages
            timestamp = msg["timestamp"].strftime("%H:%M:%S")
            print(f"  {timestamp} | {msg['id']} | {msg['topic']} | {msg['device_type']}")
        
        print(f"{'='*100}")
    
    def monitor_container_logs(self):
        """Monitor container logs for failure patterns"""
        try:
            import subprocess
            
            # List of containers to monitor
            containers = [
                'stardust-ava4-listener',
                'stardust-kati-listener', 
                'stardust-qube-listener',
                'stardust-my-firstcare-com',
                'stardust-mqtt-panel',
                'stardust-mqtt-websocket'
            ]
            
            for container in containers:
                try:
                    # Get recent logs (last 10 lines)
                    result = subprocess.run([
                        'docker', 'logs', '--tail', '10', container
                    ], capture_output=True, text=True, timeout=10)
                    
                    if result.returncode == 0:
                        logs = result.stdout
                        
                        # Check for failure patterns
                        failure_patterns = [
                            ('ERROR', 'Error'),
                            ('FHIR_R5_ERROR', 'FHIR R5 processing failed'),
                            ('DATABASE_ERROR', 'Database error'),
                            ('PATIENT_NOT_FOUND', 'No patient found'),
                            ('JSON_PARSE_ERROR', 'Invalid JSON'),
                            ('CONNECTION_ERROR', 'Connection failed'),
                            ('MODULE_ERROR', 'No module named'),
                            ('EXCEPTION', 'Exception'),
                            ('FAILED', 'Failed'),
                            ('CRITICAL', 'Critical')
                        ]
                        
                        for pattern_name, pattern in failure_patterns:
                            if pattern.lower() in logs.lower():
                                # Check if we haven't already alerted for this container/pattern recently
                                alert_key = f"{container}_{pattern_name}"
                                current_time = datetime.utcnow()
                                
                                if (alert_key not in getattr(self, '_last_alerts', {}) or 
                                    (current_time - getattr(self, '_last_alerts', {}).get(alert_key, datetime.min)).total_seconds() > 300):  # 5 minutes
                                    
                                    # Extract relevant log lines
                                    relevant_lines = []
                                    for line in logs.split('\n'):
                                        if pattern.lower() in line.lower():
                                            relevant_lines.append(line.strip())
                                    
                                    # Send alert
                                    self.telegram.send_alert(
                                        f"🚨 **Container Log Failure Detected**\n\n"
                                        f"**Container:** {container}\n"
                                        f"**Pattern:** {pattern_name}\n"
                                        f"**Recent Logs:**\n```\n" + "\n".join(relevant_lines[-3:]) + "\n```\n\n"
                                        f"Please check the container immediately!",
                                        "ERROR"
                                    )
                                    
                                    # Track alert time
                                    if not hasattr(self, '_last_alerts'):
                                        self._last_alerts = {}
                                    self._last_alerts[alert_key] = current_time
                                    
                                    # Track failure
                                    self.track_failure(f"CONTAINER_{pattern_name}", f"Container: {container}", "System")
                
                except subprocess.TimeoutExpired:
                    logger.warning(f"⚠️ Timeout checking logs for {container}")
                except subprocess.CalledProcessError:
                    logger.warning(f"⚠️ Container {container} not found or not running")
                except Exception as e:
                    logger.error(f"❌ Error monitoring logs for {container}: {e}")
                    
        except Exception as e:
            logger.error(f"❌ Error in container log monitoring: {e}")
    
    def start_monitoring(self):
        """Start complete data flow monitoring"""
        print("🚀 Starting Complete Data Flow Monitor with Telegram Alerts")
        print("="*100)
        print(f"📡 Broker: {self.mqtt_broker}:{self.mqtt_port}")
        print(f"👤 Username: {self.mqtt_username}")
        print(f"📋 Topics: {', '.join(self.topics)}")
        print(f"🚨 Failure Threshold: {self.failure_threshold} failures in {self.failure_window} minutes")
        print(f"📱 Telegram Alerts: {'✅ Enabled' if self.telegram.enabled else '❌ Disabled'}")
        print("="*100)
        print("🔍 This monitor shows the COMPLETE data flow:")
        print("   1. MQTT Payload Reception")
        print("   2. Expected Parser Processing")
        print("   3. Expected Patient Mapping")
        print("   4. Expected Data Transformation")
        print("   5. Expected Database Operations")
        print("   6. Container Log Monitoring")
        print("   7. Telegram Failure Alerts")
        print("="*100)
        
        # Send startup notification
        if self.telegram.enabled:
            self.telegram.send_alert(
                "🚀 **Medical Data Monitor Started**\n\n"
                f"Monitoring {len(self.topics)} MQTT topics\n"
                f"Failure threshold: {self.failure_threshold} in {self.failure_window} minutes\n"
                f"Container log monitoring: Enabled\n\n"
                f"System is now actively monitoring for failures!",
                "INFO"
            )
        
        # Connect to MQTT broker
        self.client = self.connect_mqtt()
        if not self.client:
            logger.error("❌ Failed to connect to MQTT broker")
            if self.telegram.enabled:
                self.telegram.send_alert(
                    "❌ **MQTT Connection Failed**\n\n"
                    f"Failed to connect to {self.mqtt_broker}:{self.mqtt_port}\n"
                    f"Please check the MQTT broker status!",
                    "ERROR"
                )
            return
        
        # Start statistics display thread
        stats_thread = threading.Thread(target=self.stats_loop, daemon=True)
        stats_thread.start()
        
        # Start container monitoring thread
        container_thread = threading.Thread(target=self.container_monitoring_loop, daemon=True)
        container_thread.start()
        
        try:
            # Keep monitoring
            while True:
                time.sleep(1)
                
        except KeyboardInterrupt:
            print("\n🛑 Stopping complete data flow monitor...")
            if self.telegram.enabled:
                self.telegram.send_alert(
                    "🛑 **Medical Data Monitor Stopped**\n\n"
                    "Monitor has been manually stopped.\n"
                    "Please restart if monitoring is needed!",
                    "WARNING"
                )
        except Exception as e:
            logger.error(f"❌ Unexpected error: {e}")
            if self.telegram.enabled:
                self.telegram.send_alert(
                    f"❌ **Monitor Unexpected Error**\n\n"
                    f"Error: {str(e)}\n\n"
                    f"Please check the monitor immediately!",
                    "ERROR"
                )
        finally:
            if self.client:
                self.client.loop_stop()
                self.client.disconnect()
    
    def container_monitoring_loop(self):
        """Monitor containers periodically"""
        while True:
            try:
                # Check container status every 30 seconds
                self.check_container_status()
                
                # Monitor container logs every 60 seconds
                self.monitor_container_logs()
                
                time.sleep(30)
                
            except Exception as e:
                logger.error(f"❌ Error in container monitoring loop: {e}")
                time.sleep(30)
    
    def stats_loop(self):
        """Display statistics periodically"""
        while True:
            time.sleep(60)  # Update every 60 seconds
            self.display_statistics()

def main():
    """Main function"""
    monitor = CompleteDataFlowMonitor()
    monitor.start_monitoring()

if __name__ == "__main__":
    main() 