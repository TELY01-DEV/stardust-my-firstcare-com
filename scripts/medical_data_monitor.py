#!/usr/bin/env python3
"""
Medical Data Monitor - Core System Monitoring
Monitors all medical data payloads from AVA4+sub devices, Kati Watch, and Qube-Vital
Alerts when medical data fails to store to database
"""

import json
import time
import requests
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import threading
import queue
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('medical_data_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class MedicalDataMonitor:
    def __init__(self):
        self.api_base_url = "http://localhost:5054"
        self.mqtt_panel_url = "http://localhost:8098"
        self.websocket_url = "ws://localhost:8097"
        
        # Monitoring state
        self.device_status = {
            'AVA4': {'active': False, 'last_seen': None, 'errors': []},
            'Kati': {'active': False, 'last_seen': None, 'errors': []},
            'Qube-Vital': {'active': False, 'last_seen': None, 'errors': []}
        }
        
        # Data flow tracking
        self.data_flow_stats = {
            'total_messages': 0,
            'successful_storage': 0,
            'failed_storage': 0,
            'pending_processing': 0
        }
        
        # Alert thresholds
        self.alert_thresholds = {
            'no_data_minutes': 10,  # Alert if no data for 10 minutes
            'error_threshold': 5,   # Alert if 5 consecutive errors
            'storage_failure_threshold': 3  # Alert if 3 storage failures
        }
        
        # Message queues for real-time processing
        self.message_queue = queue.Queue()
        self.alert_queue = queue.Queue()
        
        # Start monitoring threads
        self.running = True
        self.start_monitoring_threads()

    def start_monitoring_threads(self):
        """Start all monitoring threads"""
        threads = [
            threading.Thread(target=self.monitor_data_flow, daemon=True),
            threading.Thread(target=self.monitor_fhir_database, daemon=True),
            threading.Thread(target=self.monitor_device_activity, daemon=True),
            threading.Thread(target=self.process_alerts, daemon=True),
            threading.Thread(target=self.monitor_mqtt_panel, daemon=True)
        ]
        
        for thread in threads:
            thread.start()
            logger.info(f"Started monitoring thread: {thread.name}")

    def monitor_data_flow(self):
        """Monitor real-time data flow from MQTT panel"""
        logger.info("Starting data flow monitoring...")
        
        while self.running:
            try:
                # Check MQTT panel for recent data flow events
                response = requests.get(f"{self.mqtt_panel_url}/api/data-flow/status", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    self.process_data_flow_event(data)
                
                time.sleep(2)  # Check every 2 seconds
                
            except Exception as e:
                logger.error(f"Data flow monitoring error: {e}")
                time.sleep(5)

    def process_data_flow_event(self, event_data):
        """Process data flow events and track medical data storage"""
        try:
            event = event_data.get('event', {})
            step = event.get('step', '')
            status = event.get('status', '')
            device_type = event.get('device_type', '')
            topic = event.get('topic', '')
            error = event.get('error')
            
            # Update device activity
            if device_type in self.device_status:
                self.device_status[device_type]['active'] = True
                self.device_status[device_type]['last_seen'] = datetime.now()
            
            # Track medical data storage
            if self.is_medical_topic(topic):
                self.data_flow_stats['total_messages'] += 1
                
                if status == 'success':
                    if step in ['5_medical_stored', '6_fhir_r5_stored']:
                        self.data_flow_stats['successful_storage'] += 1
                        logger.info(f"✅ Medical data stored successfully - {device_type}: {topic}")
                    else:
                        self.data_flow_stats['pending_processing'] += 1
                
                elif status == 'error':
                    self.data_flow_stats['failed_storage'] += 1
                    self.handle_storage_failure(device_type, topic, error, event_data)
                    
        except Exception as e:
            logger.error(f"Error processing data flow event: {e}")

    def is_medical_topic(self, topic: str) -> bool:
        """Check if topic contains medical data"""
        medical_topics = [
            'ESP32_BLE_GW_TX',  # AVA4 medical data
            'iMEDE_watch/AP55',  # Kati vital signs
            'iMEDE_watch/hb',    # Kati heartbeat
            'iMEDE_watch/VitalSign',  # Kati vital signs
            'qube_vital',        # Qube-Vital data
            'dusun_pub',         # AVA4 sub-devices
            'dusun_sub'          # AVA4 sub-devices
        ]
        return any(med_topic in topic for med_topic in medical_topics)

    def handle_storage_failure(self, device_type: str, topic: str, error: str, event_data: dict):
        """Handle medical data storage failures"""
        error_info = {
            'timestamp': datetime.now(),
            'device_type': device_type,
            'topic': topic,
            'error': error,
            'event_data': event_data
        }
        
        # Add to device error list
        if device_type in self.device_status:
            self.device_status[device_type]['errors'].append(error_info)
            
            # Keep only recent errors
            recent_errors = [
                err for err in self.device_status[device_type]['errors']
                if datetime.now() - err['timestamp'] < timedelta(minutes=30)
            ]
            self.device_status[device_type]['errors'] = recent_errors
        
        # Log the failure
        logger.error(f"❌ MEDICAL DATA STORAGE FAILURE - {device_type}: {topic} - {error}")
        
        # Send alert if threshold exceeded
        if len(self.device_status[device_type]['errors']) >= self.alert_thresholds['storage_failure_threshold']:
            self.send_alert(f"CRITICAL: Multiple storage failures for {device_type}", error_info)

    def monitor_fhir_database(self):
        """Monitor FHIR database for medical data storage"""
        logger.info("Starting FHIR database monitoring...")
        
        last_count = 0
        
        while self.running:
            try:
                # Check FHIR Observation count
                response = requests.get(f"{self.api_base_url}/fhir/R5/Observation", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    current_count = data.get('total', 0)
                    
                    if current_count > last_count:
                        new_observations = current_count - last_count
                        logger.info(f"📊 FHIR Database: {new_observations} new observations added (Total: {current_count})")
                        last_count = current_count
                    
                    # Check for vital signs observations
                    vital_signs = self.check_vital_signs_observations()
                    if vital_signs:
                        logger.info(f"💓 Vital Signs detected: {vital_signs}")
                
                time.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                logger.error(f"FHIR database monitoring error: {e}")
                time.sleep(30)

    def check_vital_signs_observations(self) -> List[dict]:
        """Check for vital signs observations in FHIR database"""
        try:
            response = requests.get(f"{self.api_base_url}/fhir/R5/Observation?_count=50", timeout=5)
            if response.status_code == 200:
                data = response.json()
                entries = data.get('entry', [])
                
                vital_signs = []
                for entry in entries:
                    resource = entry.get('resource', {})
                    code = resource.get('code', {})
                    code_text = code.get('text', '')
                    
                    if code_text not in ['Step Count', 'Location']:
                        vital_signs.append({
                            'type': code_text,
                            'value': resource.get('valueQuantity', {}).get('value'),
                            'unit': resource.get('valueQuantity', {}).get('unit'),
                            'timestamp': resource.get('effectiveDateTime')
                        })
                
                return vital_signs
                
        except Exception as e:
            logger.error(f"Error checking vital signs: {e}")
        
        return []

    def monitor_device_activity(self):
        """Monitor device activity and alert if devices are inactive"""
        logger.info("Starting device activity monitoring...")
        
        while self.running:
            try:
                current_time = datetime.now()
                
                for device_type, status in self.device_status.items():
                    if status['last_seen']:
                        time_since_last = current_time - status['last_seen']
                        minutes_since_last = time_since_last.total_seconds() / 60
                        
                        if minutes_since_last > self.alert_thresholds['no_data_minutes']:
                            if status['active']:
                                logger.warning(f"⚠️ {device_type} has been inactive for {minutes_since_last:.1f} minutes")
                                status['active'] = False
                                
                                # Send alert
                                self.send_alert(
                                    f"DEVICE INACTIVE: {device_type}",
                                    {
                                        'device_type': device_type,
                                        'inactive_minutes': minutes_since_last,
                                        'last_seen': status['last_seen'].isoformat()
                                    }
                                )
                
                time.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Device activity monitoring error: {e}")
                time.sleep(60)

    def monitor_mqtt_panel(self):
        """Monitor MQTT panel for real-time events"""
        logger.info("Starting MQTT panel monitoring...")
        
        while self.running:
            try:
                # Check MQTT panel health
                response = requests.get(f"{self.mqtt_panel_url}/health", timeout=5)
                if response.status_code != 200:
                    logger.error(f"MQTT panel health check failed: {response.status_code}")
                    self.send_alert("MQTT Panel Health Issue", {"status_code": response.status_code})
                
                time.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"MQTT panel monitoring error: {e}")
                time.sleep(60)

    def process_alerts(self):
        """Process and send alerts"""
        logger.info("Starting alert processing...")
        
        while self.running:
            try:
                # Process alerts from queue
                try:
                    alert = self.alert_queue.get(timeout=1)
                    self.send_alert(alert['title'], alert['data'])
                except queue.Empty:
                    pass
                
                # Generate periodic status report
                self.generate_status_report()
                
                time.sleep(60)  # Process every minute
                
            except Exception as e:
                logger.error(f"Alert processing error: {e}")
                time.sleep(60)

    def send_alert(self, title: str, data: dict):
        """Send alert notification"""
        alert_message = f"""
🚨 MEDICAL DATA MONITOR ALERT 🚨
Title: {title}
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Data: {json.dumps(data, indent=2, default=str)}

Current System Status:
- Total Messages: {self.data_flow_stats['total_messages']}
- Successful Storage: {self.data_flow_stats['successful_storage']}
- Failed Storage: {self.data_flow_stats['failed_storage']}
- Pending Processing: {self.data_flow_stats['pending_processing']}

Device Status:
{self.get_device_status_summary()}
"""
        
        logger.critical(alert_message)
        
        # Here you can add additional alert mechanisms:
        # - Email notification
        # - Slack/Teams webhook
        # - SMS notification
        # - Telegram bot
        # - System notification

    def get_device_status_summary(self) -> str:
        """Get summary of device status"""
        summary = []
        for device_type, status in self.device_status.items():
            active_status = "🟢 ACTIVE" if status['active'] else "🔴 INACTIVE"
            last_seen = status['last_seen'].strftime('%H:%M:%S') if status['last_seen'] else "Never"
            error_count = len(status['errors'])
            summary.append(f"  {device_type}: {active_status} (Last: {last_seen}, Errors: {error_count})")
        
        return "\n".join(summary)

    def generate_status_report(self):
        """Generate periodic status report"""
        report = f"""
📊 MEDICAL DATA MONITOR STATUS REPORT
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Data Flow Statistics:
- Total Messages: {self.data_flow_stats['total_messages']}
- Successful Storage: {self.data_flow_stats['successful_storage']}
- Failed Storage: {self.data_flow_stats['failed_storage']}
- Pending Processing: {self.data_flow_stats['pending_processing']}
- Success Rate: {(self.data_flow_stats['successful_storage'] / max(self.data_flow_stats['total_messages'], 1)) * 100:.1f}%

Device Status:
{self.get_device_status_summary()}

Recent Errors:
{self.get_recent_errors_summary()}
"""
        
        logger.info(report)

    def get_recent_errors_summary(self) -> str:
        """Get summary of recent errors"""
        all_errors = []
        for device_type, status in self.device_status.items():
            for error in status['errors'][-3:]:  # Last 3 errors per device
                all_errors.append(f"  {device_type}: {error['error']} ({error['timestamp'].strftime('%H:%M:%S')})")
        
        return "\n".join(all_errors) if all_errors else "  No recent errors"

    def stop_monitoring(self):
        """Stop all monitoring"""
        logger.info("Stopping medical data monitor...")
        self.running = False

def main():
    """Main function to run the medical data monitor"""
    logger.info("🚀 Starting Medical Data Monitor...")
    
    monitor = MedicalDataMonitor()
    
    try:
        # Keep the main thread alive
        while monitor.running:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down...")
        monitor.stop_monitoring()
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        monitor.stop_monitoring()

if __name__ == "__main__":
    main() 