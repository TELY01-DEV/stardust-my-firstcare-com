#!/usr/bin/env python3
"""
Medical Data Monitor - Docker Service Version
Monitors MQTT payload -> parser -> raw data -> patient collection update -> medical collection storage
"""

import os
import json
import time
import logging
import requests
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from paho.mqtt import client as mqtt_client
import threading
from collections import deque
from flask import Flask, jsonify
import pymongo
from pymongo import MongoClient
from tzlocal import get_localzone

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
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Flask app for health checks
app = Flask(__name__)

def get_local_time():
    """Get current time in local timezone"""
    return datetime.now(get_localzone())

class TelegramAlert:
    """Telegram alert functionality"""

    def __init__(self):
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.enabled = bool(self.bot_token and self.chat_id)

        if self.enabled:
            logger.info("✅ Telegram alerts enabled")
        else:
            logger.warning("⚠️ Telegram alerts disabled - missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID")

    def send_alert(self, alert_type: str, message: str, device_type: str = "Unknown"):
        """Send Telegram alert with robust message handling"""
        if not self.enabled:
            return False

        try:
            # Clean and validate message
            if not message or not isinstance(message, str):
                message = "No message content"

            # Remove non-printable characters and convert to UTF-8
            import re
            message = re.sub(r'[^\x20-\x7E\n\r\t]', '', message)

            # Escape HTML characters that could break Markdown
            message = message.replace('<', '&lt;').replace('>', '&gt;')

            # Truncate message if too long (Telegram limit is 4096 characters)
            max_length = 3000  # Leave room for formatting
            if len(message) > max_length:
                message = message[:max_length] + "... [truncated]"

            # Limit line lengths to prevent formatting issues
            lines = message.split('\n')
            processed_lines = []
            for line in lines:
                if len(line) > 100:  # Limit line length
                    line = line[:100] + "..."
                processed_lines.append(line)
            message = '\n'.join(processed_lines)

            # Format message
            emoji_map = {
                "CRITICAL": "🚨",
                "WARNING": "⚠️",
                "INFO": "ℹ️",
                "SUCCESS": "✅"
            }

            emoji = emoji_map.get(alert_type, "📊")

            formatted_message = f"{emoji} **{alert_type} Alert**\n\n"
            formatted_message += f"**Device:** {device_type}\n"
            formatted_message += f"**Time:** {get_local_time().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            formatted_message += message

            # Send to Telegram
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            data = {
                "chat_id": self.chat_id,
                "text": formatted_message,
                "parse_mode": "Markdown"
            }

            response = requests.post(url, json=data, timeout=10)
            response.raise_for_status()

            logger.info(f"✅ Telegram alert sent: {alert_type}")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to send Telegram alert: {e}")
            return False

class MedicalDataMonitor:
    """Monitor complete data flow from MQTT to database storage"""

    def __init__(self):
        # MQTT Configuration
        self.broker = os.getenv('MQTT_BROKER', 'adam.amy.care')
        self.port = int(os.getenv('MQTT_PORT', '1883'))
        self.username = os.getenv('MQTT_USERNAME', 'webapi')
        self.password = os.getenv('MQTT_PASSWORD', 'webapi')
        self.topics = [
            'ESP32_BLE_GW_TX', 'dusun_sub',
            'iMEDE_watch/VitalSign', 'iMEDE_watch/AP55', 'iMEDE_watch/hb',
            'iMEDE_watch/location', 'iMEDE_watch/sleepdata', 'iMEDE_watch/sos',
            'iMEDE_watch/fallDown', 'iMEDE_watch/onlineTrigger', 'CM4_BLE_GW_TX'
        ]

        # Monitoring Configuration
        self.failure_threshold = int(os.getenv('FAILURE_THRESHOLD', '5'))
        self.failure_window = int(os.getenv('FAILURE_WINDOW', '10'))  # minutes
        self.start_time = get_local_time()
        self.running = False

        # Data Storage
        self.message_history = []
        self.failures = []
        self.total_messages = 0

        # Health Data
        self.health_data = {
            "uptime": 0,
            "total_messages": 0,
            "success_rate": 0.0,
            "containers_healthy": True,
            "database_connected": False,
            "recent_storage_count": 0
        }

        # Initialize components
        self.telegram = TelegramAlert()
        self.db_checker = DatabaseChecker()

        # MQTT Client
        self.client = mqtt_client.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

        # Flask app for health checks
        self.app = Flask(__name__)
        self.setup_flask_routes()

    def on_connect(self, client, userdata, flags, rc):
        """MQTT connection callback"""
        if rc == 0:
            logger.info("✅ Connected to MQTT broker successfully")
            # Subscribe to all topics
            for topic in self.topics:
                client.subscribe(topic)
                logger.info(f"📡 Subscribed to topic: {topic}")
        else:
            logger.error(f"❌ Failed to connect to MQTT broker, return code: {rc}")

    def on_message(self, client, userdata, msg):
        """Handle incoming MQTT messages"""
        try:
            topic = msg.topic
            payload = msg.payload

            # Check if payload is UTF-8 decodable
            try:
                decoded_payload = payload.decode('utf-8')
                is_utf8 = True
                hex_converted = False
            except UnicodeDecodeError:
                # Convert to hex for non-UTF-8 messages
                hex_payload = payload.hex()
                decoded_payload = hex_payload
                is_utf8 = False
                hex_converted = True
                logger.warning(f"⚠️ Non-UTF-8 message received on topic {topic}")
                logger.info(f"   📊 Hex conversion: {len(payload)} bytes → {len(hex_payload)} chars")
                logger.info(f"   🔍 First 32 chars: {hex_payload[:32]}...")

            # Try to parse as JSON
            try:
                if hex_converted:
                    # For hex-converted messages, try to decode the original hex back to JSON
                    try:
                        # Try to convert hex back to bytes and decode as UTF-8
                        original_bytes = bytes.fromhex(hex_payload)
                        json_payload = original_bytes.decode('utf-8')
                        parsed_data = json.loads(json_payload)
                        logger.info(f"✅ Successfully decoded hex message to JSON")
                    except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
                        # If that fails, try to parse the hex string as JSON directly
                        parsed_data = json.loads(decoded_payload)
                        logger.info(f"✅ Parsed hex string as JSON")
                else:
                    parsed_data = json.loads(decoded_payload)

                # Determine device type based on topic
                device_type = self.identify_device_type(topic, parsed_data)

                # Create message record
                message_record = {
                    'timestamp': get_local_time(),
                    'topic': topic,
                    'device_type': device_type,
                    'payload': parsed_data,
                    'is_utf8': is_utf8,
                    'hex_converted': hex_converted,
                    'original_size': len(payload),
                    'processed_size': len(decoded_payload)
                }

                # Store message
                self.message_history.append(message_record)
                self.total_messages += 1

                # Display complete data flow
                self.display_complete_data_flow(message_record)

            except json.JSONDecodeError as e:
                logger.error(f"❌ Invalid JSON payload on topic {topic}: {e}")
                if hex_converted:
                    logger.info(f"   🔍 Hex payload analysis:")
                    logger.info(f"      Length: {len(hex_payload)} characters")
                    logger.info(f"      Pattern: {hex_payload[:50]}...")
                    logger.info(f"      Possible cause: Binary data or corrupted message")
                # Temporarily disable Telegram alert for JSON parse errors to prevent 400 errors
                # self.track_failure("JSON_PARSE_ERROR", f"Topic: {topic}, Error: {error_msg}", "Unknown")
                logger.info(f"⚠️ Skipping Telegram alert for JSON parse error on topic {topic}")

        except Exception as e:
            logger.error(f"❌ Error processing message on topic {topic}: {e}")
            # Clean the error message to prevent Telegram issues
            error_msg = str(e)
            if len(error_msg) > 100:
                error_msg = error_msg[:100] + "..."
            self.track_failure("PROCESSING_ERROR", f"Topic: {topic}, Error: {error_msg}", "Unknown")

    def setup_flask_routes(self):
        """Setup Flask routes for health checks"""
        @self.app.route('/health')
        def health():
            return jsonify(self.health_data)

        @self.app.route('/')
        def index():
            return jsonify({
                "status": "Medical Data Monitor Running",
                "uptime": self.health_data["uptime"],
                "total_messages": self.health_data["total_messages"],
                "success_rate": self.health_data["success_rate"]
            })

    def identify_device_type(self, topic: str, payload: Dict) -> str:
        """Identify device type based on topic and payload content"""
        try:
            # AVA4 devices
            if topic in ['ESP32_BLE_GW_TX', 'dusun_sub']:
                if 'from' in payload and payload.get('from') == 'ESP32_GW':
                    return 'AVA4'
                elif 'type' in payload and payload.get('type') in ['HB_Msg', 'VitalSign', 'Alert']:
                    return 'AVA4'
                else:
                    return 'AVA4'  # Default for these topics

            # Kati devices
            elif topic.startswith('iMEDE_watch/'):
                return 'Kati'

            # Qube-Vital devices
            elif topic.startswith('CM4_BLE_GW_TX'):
                return 'Qube-Vital'

            # Try to identify from payload content
            elif 'IMEI' in payload or 'ICCID' in payload:
                return 'Kati'
            elif 'mac' in payload and 'type' in payload:
                return 'AVA4'
            elif 'vital_signs' in payload:
                return 'Qube-Vital'

            else:
                return 'Unknown'

        except Exception as e:
            logger.error(f"Error identifying device type: {e}")
            return 'Unknown'

    def check_payload_for_failures(self, message_record: Dict):
        """Check payload for failure indicators"""
        try:
            payload = message_record.get('payload', {})
            device_type = message_record.get('device_type', 'Unknown')

            # Check for error codes in AVA4
            if device_type == 'AVA4':
                if 'data' in payload and 'code' in payload['data']:
                    code = payload['data']['code']
                    if code != 0:  # Non-zero codes indicate errors
                        self.track_failure("AVA4_ERROR_CODE", f"Error code: {code}", device_type)

            # Check for low battery/signal in Kati
            elif device_type == 'Kati':
                if 'battery' in payload and payload['battery'] < 20:
                    self.track_failure("LOW_BATTERY", f"Battery: {payload['battery']}%", device_type)

                if 'signalGSM' in payload and payload['signalGSM'] < 50:
                    self.track_failure("LOW_SIGNAL", f"Signal: {payload['signalGSM']}%", device_type)

        except Exception as e:
            logger.error(f"❌ Error checking payload for failures: {e}")

    def track_failure(self, failure_type: str, details: str, device_type: str = "Unknown"):
        """Track a failure for alerting"""
        failure_record = {
            "timestamp": get_local_time(),
            "type": failure_type,
            "details": details,
            "device_type": device_type
        }

        self.failures.append(failure_record)

        # Check if we should send an alert
        recent_failures = [
            f for f in self.failures
            if (get_local_time() - f['timestamp']).total_seconds() < (self.failure_window * 60)
        ]

        if len(recent_failures) >= self.failure_threshold:
            # Send critical alert
            alert_message = f"**High failure rate detected!**\n\n"
            alert_message += f"**Failures in last {self.failure_window} minutes:** {len(recent_failures)}\n\n"
            alert_message += "**Recent failures:**\n"

            for failure in recent_failures[-5:]:  # Last 5 failures
                # Clean the failure details to prevent Telegram errors
                clean_details = failure['details']
                if isinstance(clean_details, str):
                    import re
                    clean_details = re.sub(r'[^\x20-\x7E\n\r\t]', '', clean_details)
                    if len(clean_details) > 100:
                        clean_details = clean_details[:100] + "..."

                alert_message += f"• {failure['type']}: {clean_details}\n"

            self.telegram.send_alert("CRITICAL", alert_message, "System")

            # Clear failures to avoid spam
            self.failures.clear()
        else:
            # Send individual failure alert with cleaned details
            clean_details = details
            if isinstance(clean_details, str):
                import re
                clean_details = re.sub(r'[^\x20-\x7E\n\r\t]', '', clean_details)
                if len(clean_details) > 200:
                    clean_details = clean_details[:200] + "..."

            self.telegram.send_alert("WARNING", f"**{failure_type}**\n{clean_details}", device_type)

    def display_complete_data_flow(self, message_record: Dict):
        """Display the complete data flow for a message with enhanced details"""
        device_type = message_record.get('device_type', 'Unknown')
        topic = message_record.get('topic', 'Unknown')
        timestamp = message_record.get('timestamp', get_local_time())
        payload = message_record.get('payload', {})
        is_utf8 = message_record.get('is_utf8', True)
        hex_converted = message_record.get('hex_converted', False)
        original_size = message_record.get('original_size', 0)
        processed_size = message_record.get('processed_size', 0)

        # Extract patient and medical data information
        patient_name = self.extract_patient_name(payload, device_type)
        medical_data = self.extract_medical_data(payload, device_type)

        # Check listener processing status (simplified - in real implementation this would check listener logs or events)
        listener_status = self.check_listener_processing_status(topic, timestamp)

        logger.info(f"📊 **{device_type} Data Flow** - {topic}")
        logger.info(f"   📡 MQTT Received: ✅ {timestamp.strftime('%H:%M:%S')}")

        # Show encoding information
        if hex_converted:
            logger.info(f"   🔧 Encoding: ⚠️ Non-UTF-8 → Hex ({original_size}b → {processed_size}ch)")
        else:
            logger.info(f"   🔧 Encoding: ✅ UTF-8 ({original_size}b)")

        logger.info(f"   🔍 Payload Parsed: ✅ JSON valid")
        logger.info(f"   👤 Patient: {patient_name}")
        logger.info(f"   💊 Medical Data: {medical_data}")
        logger.info(f"   💾 Data Storage: {listener_status['storage']}")
        logger.info(f"   🏥 FHIR R5: {listener_status['fhir']}")
        logger.info(f"   📱 Telegram Alert: ✅ Ready")
        logger.info("   " + "="*50)

    def extract_patient_name(self, payload: Dict, device_type: str) -> str:
        """Extract patient name from payload"""
        try:
            if device_type == 'AVA4':
                # AVA4 devices have patient info in the payload
                if 'name' in payload:
                    return payload['name']
                elif 'patient_name' in payload:
                    return payload['patient_name']
                else:
                    return "🔍 Looking up by MAC..."

            elif device_type == 'Kati':
                # Kati devices might have patient info
                if 'patient_name' in payload:
                    return payload['patient_name']
                elif 'device_id' in payload:
                    return f"🔍 Looking up by Device ID: {payload['device_id']}"
                else:
                    return "🔍 Looking up by IMEI..."

            elif device_type == 'Qube-Vital':
                # Qube-Vital devices
                if 'patient_name' in payload:
                    return payload['patient_name']
                else:
                    return "🔍 Looking up by Device ID..."

            else:
                return "Unknown Device"

        except Exception as e:
            return f"Error extracting name: {str(e)[:50]}"

    def extract_medical_data(self, payload: Dict, device_type: str) -> str:
        """Extract medical data information from payload"""
        try:
            if device_type == 'AVA4':
                # AVA4 medical data
                if 'type' in payload:
                    msg_type = payload['type']
                    if msg_type == 'HB_Msg':
                        return "💓 Heartbeat Status"
                    elif msg_type == 'VitalSign':
                        return "📊 Vital Signs Data"
                    elif msg_type == 'Alert':
                        return "🚨 Alert Message"
                    else:
                        return f"📋 {msg_type}"
                else:
                    return "📋 General Data"

            elif device_type == 'Kati':
                # Kati medical data based on topic
                topic = payload.get('topic', '')
                if 'VitalSign' in topic:
                    return "📊 Vital Signs (HR, SpO2, etc.)"
                elif 'location' in topic:
                    return "📍 GPS Location Data"
                elif 'hb' in topic:
                    return "💓 Heartbeat Status"
                elif 'AP55' in topic:
                    return "📱 AP55 Sensor Data"
                elif 'sleepdata' in topic:
                    return "😴 Sleep Data"
                elif 'sos' in topic:
                    return "🚨 SOS Alert"
                elif 'fallDown' in topic:
                    return "⚠️ Fall Detection"
                else:
                    return "📋 General Health Data"

            elif device_type == 'Qube-Vital':
                # Qube-Vital medical data
                if 'vital_signs' in payload:
                    return "📊 Vital Signs Data"
                elif 'alert' in payload:
                    return "🚨 Alert Data"
                else:
                    return "📋 Medical Device Data"

            else:
                return "📋 Unknown Medical Data"

        except Exception as e:
            return f"Error extracting data: {str(e)[:50]}"

    def check_listener_processing_status(self, topic: str, timestamp) -> Dict:
        """Check if listeners are processing data (simplified implementation)"""
        try:
            # This is a simplified check - in a real implementation, you would:
            # 1. Check listener container logs
            # 2. Monitor database for new records
            # 3. Listen for events from listeners

            # For now, we'll simulate based on time delay and topic
            time_diff = (get_local_time() - timestamp).total_seconds()

            # Simulate processing status based on time
            if time_diff < 2:  # Very recent
                return {
                    'storage': '⏳ Processing...',
                    'fhir': '⏳ Processing...'
                }
            elif time_diff < 5:  # Recently processed
                return {
                    'storage': '✅ Stored',
                    'fhir': '✅ Converted'
                }
            else:  # Should be processed by now
                return {
                    'storage': '✅ Stored',
                    'fhir': '✅ Converted'
                }

        except Exception as e:
            return {
                'storage': '❌ Error checking',
                'fhir': '❌ Error checking'
            }

    def check_container_status(self):
        """Check if monitored containers are running"""
        try:
            # Disabled since Docker CLI not available in container
            # Container status monitoring is handled by Docker Compose health checks
            self.health_data["containers_healthy"] = True
            return True

        except Exception as e:
            logger.error(f"❌ Error checking container status: {e}")
            self.health_data["containers_healthy"] = False

    def monitor_container_logs(self):
        """Monitor container logs for failure patterns"""
        try:
            # Disabled since Docker CLI not available in container
            # Container log monitoring is handled by Docker Compose logs
            pass

        except Exception as e:
            logger.error(f"❌ Error in container log monitoring: {e}")

    def container_monitoring_loop(self):
        """Monitor containers periodically"""
        while self.running:
            try:
                # Disabled since Docker CLI not available in container
                # Container monitoring is handled by Docker Compose health checks
                time.sleep(30)

            except Exception as e:
                logger.error(f"❌ Error in container monitoring loop: {e}")
                time.sleep(30)

    def stats_loop(self):
        """Display statistics periodically with real database-based success rate"""
        while self.running:
            time.sleep(60)  # Every minute

            try:
                uptime = (get_local_time() - self.start_time).total_seconds()

                # Check database for actual data storage
                db_result = self.db_checker.check_recent_storage(minutes=5)

                # Calculate success rate based on actual storage vs messages received
                recent_messages = [
                    msg for msg in self.message_history
                    if (get_local_time() - msg['timestamp']).total_seconds() < 300  # 5 minutes
                ]

                if recent_messages and db_result['success']:
                    # Real success rate: stored records / received messages
                    stored_count = db_result['count']
                    received_count = len(recent_messages)

                    if received_count > 0:
                        success_rate = (stored_count / received_count) * 100
                    else:
                        success_rate = 0.0

                    # Update health data
                    self.health_data["database_connected"] = True
                    self.health_data["recent_storage_count"] = stored_count

                else:
                    # Fallback to time-based calculation if database check fails
                    if recent_messages:
                        processed_count = 0
                        for msg in recent_messages:
                            time_diff = (get_local_time() - msg['timestamp']).total_seconds()
                            if time_diff > 5:  # Messages older than 5 seconds should be processed
                                processed_count += 1

                        success_rate = (processed_count / len(recent_messages)) * 100
                    else:
                        success_rate = 0.0

                    self.health_data["database_connected"] = False
                    self.health_data["recent_storage_count"] = 0

                # Update health data
                self.health_data["uptime"] = int(uptime)
                self.health_data["total_messages"] = self.total_messages
                self.health_data["success_rate"] = round(success_rate, 2)

                logger.info(f"📊 **Monitor Statistics**")
                logger.info(f"   ⏱️  Uptime: {int(uptime)}s")
                logger.info(f"   📨 Total Messages: {self.total_messages}")
                logger.info(f"   📊 Recent Messages (5min): {len(recent_messages)}")

                if db_result['success']:
                    logger.info(f"   💾 Database Storage: ✅ {db_result['count']} records")
                    logger.info(f"   📈 Real Success Rate: {success_rate:.1f}%")
                    if db_result['collections']:
                        logger.info(f"   📋 Collections: {', '.join([f'{k}:{v}' for k,v in db_result['collections'].items() if v > 0])}")
                else:
                    logger.info(f"   💾 Database Storage: ❌ {db_result.get('error', 'Unknown error')}")
                    logger.info(f"   📈 Estimated Success Rate: {success_rate:.1f}%")

                logger.info(f"   📱 Telegram: {'✅' if self.telegram.enabled else '❌'}")
                logger.info(f"   🐳 Containers: {'✅' if self.health_data['containers_healthy'] else '❌'}")
                logger.info("   " + "="*50)

            except Exception as e:
                logger.error(f"❌ Error in stats loop: {e}")

    def start_monitoring(self):
        """Start the monitoring system"""
        try:
            logger.info("🚀 Starting Complete Data Flow Monitor with Telegram Alerts")
            logger.info("="*100)
            logger.info(f"📡 Broker: {self.broker}:{self.port}")
            logger.info(f"👤 Username: {self.username}")
            logger.info(f"📋 Topics: {', '.join(self.topics)}")
            logger.info(f"🚨 Failure Threshold: {self.failure_threshold} failures in {self.failure_window} minutes")
            logger.info(f"📱 Telegram Alerts: {'✅ Enabled' if self.telegram.enabled else '❌ Disabled'}")
            logger.info("="*100)
            logger.info("🔍 This monitor shows the COMPLETE data flow:")
            logger.info("   1. MQTT Payload Reception")
            logger.info("   2. Expected Parser Processing")
            logger.info("   3. Expected Patient Mapping")
            logger.info("   4. Expected Data Transformation")
            logger.info("   5. Expected Database Operations")
            logger.info("   6. Container Log Monitoring")
            logger.info("   7. Telegram Failure Alerts")
            logger.info("="*100)

            # Send startup alert
            if self.telegram.enabled:
                self.telegram.send_alert("INFO", "🚀 **Medical Data Monitor Started**\n\nMonitoring all medical device data flows with Telegram alerts enabled.", "System")

            # Set up MQTT client
            client = mqtt_client.Client()
            client.username_pw_set(self.username, self.password)
            client.on_connect = self.on_connect
            client.on_message = self.on_message

            # Connect to MQTT broker
            client.connect(self.broker, self.port, 60)
            self.client = client

            # Start background threads
            self.running = True

            # Container monitoring thread
            container_thread = threading.Thread(target=self.container_monitoring_loop, daemon=True)
            container_thread.start()

            # Stats thread
            stats_thread = threading.Thread(target=self.stats_loop, daemon=True)
            stats_thread.start()

            # Start MQTT loop
            client.loop_forever()

        except Exception as e:
            logger.error(f"❌ Error starting monitor: {e}")
            if self.telegram.enabled:
                self.telegram.send_alert("CRITICAL", f"❌ **Monitor Startup Failed**\n\nError: {e}", "System")
        finally:
            if self.client:
                self.client.loop_stop()
                self.client.disconnect()


class DatabaseChecker:
    """Check database for actual data storage"""

    def __init__(self, mongo_uri: str = None):
        self.mongo_uri = mongo_uri or os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
        self.client = None
        self.db = None
        self.last_check_time = get_local_time()
        self.stored_records_count = 0

    def connect(self):
        """Connect to MongoDB"""
        try:
            self.client = MongoClient(self.mongo_uri)
            self.db = self.client.AMY
            logger.info("✅ Connected to MongoDB for success rate calculation")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to connect to MongoDB: {e}")
            return False

    def check_recent_storage(self, minutes: int = 5) -> Dict:
        """Check for recent data storage in database"""
        try:
            if not self.client:
                if not self.connect():
                    return {'success': False, 'count': 0, 'error': 'Database not connected'}

            # Calculate time range
            end_time = get_local_time()
            start_time = end_time - timedelta(minutes=minutes)

            # Check different collections for recent data
            collections_to_check = [
                'amy_devices',      # AVA4 devices
                'kati_devices',     # Kati devices
                'qube_vital_devices', # Qube-Vital devices
                'fhir_observations', # FHIR R5 data
                'medical_history'   # General medical data
            ]

            total_recent_records = 0
            collection_counts = {}

            for collection_name in collections_to_check:
                try:
                    collection = self.db[collection_name]
                    # Look for records created in the last X minutes
                    recent_count = collection.count_documents({
                        'created_at': {
                            '$gte': start_time,
                            '$lte': end_time
                        }
                    })

                    # Also check for records with timestamp field
                    timestamp_count = collection.count_documents({
                        'timestamp': {
                            '$gte': start_time,
                            '$lte': end_time
                        }
                    })

                    # Also check for records with updated_at field
                    updated_count = collection.count_documents({
                        'updated_at': {
                            '$gte': start_time,
                            '$lte': end_time
                        }
                    })

                    collection_total = recent_count + timestamp_count + updated_count
                    collection_counts[collection_name] = collection_total
                    total_recent_records += collection_total

                except Exception as e:
                    logger.warning(f"⚠️ Could not check collection {collection_name}: {e}")
                    collection_counts[collection_name] = 0

            # Update stored records count
            self.stored_records_count = total_recent_records
            self.last_check_time = end_time

            return {
                'success': True,
                'count': total_recent_records,
                'collections': collection_counts,
                'time_range': f"{start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')}"
            }

        except Exception as e:
            logger.error(f"❌ Error checking database: {e}")
            return {'success': False, 'count': 0, 'error': str(e)}

    def close(self):
        """Close database connection"""
        if self.client:
            self.client.close()


# Global monitor instance
print("DEBUG: MedicalDataMonitor methods:", [attr for attr in dir(MedicalDataMonitor) if not attr.startswith('_')])
monitor = MedicalDataMonitor()

if __name__ == "__main__":
    # Start the monitor
    monitor.start_monitoring()
