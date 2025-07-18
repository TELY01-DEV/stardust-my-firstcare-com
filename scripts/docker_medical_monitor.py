#!/usr/bin/env python3
"""
Docker Medical Data Monitor
Monitors Docker container logs for medical data storage failures
Real-time monitoring of AVA4, Kati Watch, and Qube-Vital data processing
"""

import subprocess
import json
import time
import logging
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import threading
import queue

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('docker_medical_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DockerMedicalMonitor:
    def __init__(self):
        # Container names to monitor
        self.containers = {
            'AVA4': 'stardust-ava4-listener',
            'Kati': 'stardust-kati-listener', 
            'Qube-Vital': 'stardust-qube-listener',
            'API': 'stardust-my-firstcare-com',
            'MQTT-Panel': 'stardust-mqtt-panel'
        }
        
        # Medical data patterns to monitor
        self.medical_patterns = {
            'success_patterns': [
                r'✅ Successfully processed.*data for patient',
                r'✅ PATIENT COLLECTION UPDATED SUCCESSFULLY',
                r'✅ MEDICAL HISTORY STORED SUCCESSFULLY',
                r'✅ FHIR R5 Observation created for patient',
                r'✅ Successfully stored.*history for patient'
            ],
            'failure_patterns': [
                r'❌.*failed',
                r'ERROR.*Error processing',
                r'WARNING.*No FHIR Observation data generated',
                r'ERROR.*FHIR R5 processing failed',
                r'ERROR.*No module named',
                r'ERROR.*Kati Data validation failed',
                r'ERROR.*Failed to process.*data'
            ],
            'medical_topics': [
                r'iMEDE_watch/AP55',      # Kati vital signs
                r'iMEDE_watch/hb',        # Kati heartbeat
                r'iMEDE_watch/VitalSign', # Kati vital signs
                r'ESP32_BLE_GW_TX',       # AVA4 medical data
                r'qube_vital',            # Qube-Vital data
                r'dusun_pub',             # AVA4 sub-devices
                r'dusun_sub'              # AVA4 sub-devices
            ]
        }
        
        # Monitoring state
        self.device_status = {
            'AVA4': {'active': False, 'last_seen': None, 'success_count': 0, 'failure_count': 0, 'errors': []},
            'Kati': {'active': False, 'last_seen': None, 'success_count': 0, 'failure_count': 0, 'errors': []},
            'Qube-Vital': {'active': False, 'last_seen': None, 'success_count': 0, 'failure_count': 0, 'errors': []}
        }
        
        # Alert thresholds
        self.alert_thresholds = {
            'no_data_minutes': 10,        # Alert if no data for 10 minutes
            'consecutive_failures': 3,    # Alert if 3 consecutive failures
            'failure_rate_threshold': 0.3 # Alert if failure rate > 30%
        }
        
        # Message queues
        self.alert_queue = queue.Queue()
        self.running = True
        
        # Start monitoring threads
        self.start_monitoring_threads()

    def start_monitoring_threads(self):
        """Start all monitoring threads"""
        threads = [
            threading.Thread(target=self.monitor_container_logs, daemon=True),
            threading.Thread(target=self.monitor_device_activity, daemon=True),
            threading.Thread(target=self.process_alerts, daemon=True),
            threading.Thread(target=self.monitor_fhir_database, daemon=True)
        ]
        
        for thread in threads:
            thread.start()
            logger.info(f"Started monitoring thread: {thread.name}")

    def monitor_container_logs(self):
        """Monitor container logs for medical data processing"""
        logger.info("Starting container log monitoring...")
        
        # Start log monitoring for each container
        for device_type, container_name in self.containers.items():
            if device_type in ['AVA4', 'Kati', 'Qube-Vital']:
                threading.Thread(
                    target=self.monitor_container_log,
                    args=(device_type, container_name),
                    daemon=True
                ).start()

    def monitor_container_log(self, device_type: str, container_name: str):
        """Monitor logs for a specific container"""
        logger.info(f"Monitoring {device_type} container: {container_name}")
        
        try:
            # Use docker logs with follow to get real-time logs
            process = subprocess.Popen(
                ['docker', 'logs', '-f', '--tail', '0', container_name],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            
            if process.stdout:
                for line in iter(process.stdout.readline, ''):
                    if not self.running:
                        break
                        
                    if line.strip():
                        self.process_log_line(device_type, line.strip())
                    
        except Exception as e:
            logger.error(f"Error monitoring {container_name}: {e}")
            # Try to restart monitoring after delay
            time.sleep(30)
            if self.running:
                self.monitor_container_log(device_type, container_name)

    def process_log_line(self, device_type: str, log_line: str):
        """Process a single log line for medical data patterns"""
        try:
            # Check if this is medical data related
            if not self.is_medical_data_log(log_line):
                return
            
            # Update device activity
            self.device_status[device_type]['active'] = True
            self.device_status[device_type]['last_seen'] = datetime.now()
            
            # Check for success patterns
            if self.matches_patterns(log_line, self.medical_patterns['success_patterns']):
                self.device_status[device_type]['success_count'] += 1
                logger.info(f"✅ {device_type} Medical Data Success: {log_line[:100]}...")
            
            # Check for failure patterns
            elif self.matches_patterns(log_line, self.medical_patterns['failure_patterns']):
                self.device_status[device_type]['failure_count'] += 1
                self.handle_medical_failure(device_type, log_line)
            
        except Exception as e:
            logger.error(f"Error processing log line: {e}")

    def is_medical_data_log(self, log_line: str) -> bool:
        """Check if log line contains medical data"""
        return any(re.search(pattern, log_line) for pattern in self.medical_patterns['medical_topics'])

    def matches_patterns(self, text: str, patterns: List[str]) -> bool:
        """Check if text matches any of the patterns"""
        return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)

    def handle_medical_failure(self, device_type: str, log_line: str):
        """Handle medical data processing failure"""
        error_info = {
            'timestamp': datetime.now(),
            'device_type': device_type,
            'log_line': log_line,
            'error_type': self.classify_error(log_line)
        }
        
        # Add to device error list
        self.device_status[device_type]['errors'].append(error_info)
        
        # Keep only recent errors (last 30 minutes)
        recent_errors = [
            err for err in self.device_status[device_type]['errors']
            if datetime.now() - err['timestamp'] < timedelta(minutes=30)
        ]
        self.device_status[device_type]['errors'] = recent_errors
        
        # Log the failure
        logger.error(f"❌ {device_type} Medical Data Failure: {log_line}")
        
        # Check for alert conditions
        self.check_alert_conditions(device_type)

    def classify_error(self, log_line: str) -> str:
        """Classify the type of error"""
        if 'No module named' in log_line:
            return 'Import Error'
        elif 'FHIR R5 processing failed' in log_line:
            return 'FHIR Processing Error'
        elif 'No FHIR Observation data generated' in log_line:
            return 'FHIR Generation Error'
        elif 'validation failed' in log_line:
            return 'Validation Error'
        elif 'Failed to process' in log_line:
            return 'Processing Error'
        else:
            return 'Unknown Error'

    def check_alert_conditions(self, device_type: str):
        """Check if alert conditions are met"""
        status = self.device_status[device_type]
        
        # Check consecutive failures
        if len(status['errors']) >= self.alert_thresholds['consecutive_failures']:
            self.send_alert(
                f"CRITICAL: Multiple failures for {device_type}",
                {
                    'device_type': device_type,
                    'error_count': len(status['errors']),
                    'recent_errors': status['errors'][-3:]  # Last 3 errors
                }
            )
        
        # Check failure rate
        total_operations = status['success_count'] + status['failure_count']
        if total_operations > 0:
            failure_rate = status['failure_count'] / total_operations
            if failure_rate > self.alert_thresholds['failure_rate_threshold']:
                self.send_alert(
                    f"HIGH FAILURE RATE: {device_type}",
                    {
                        'device_type': device_type,
                        'failure_rate': f"{failure_rate:.1%}",
                        'success_count': status['success_count'],
                        'failure_count': status['failure_count']
                    }
                )

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

    def monitor_fhir_database(self):
        """Monitor FHIR database for medical data storage"""
        logger.info("Starting FHIR database monitoring...")
        
        last_count = 0
        
        while self.running:
            try:
                # Check FHIR Observation count using curl
                result = subprocess.run(
                    ['curl', '-s', 'http://localhost:5054/fhir/R5/Observation'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode == 0:
                    try:
                        data = json.loads(result.stdout)
                        current_count = data.get('total', 0)
                        
                        if current_count > last_count:
                            new_observations = current_count - last_count
                            logger.info(f"📊 FHIR Database: {new_observations} new observations added (Total: {current_count})")
                            last_count = current_count
                        
                        # Check for vital signs
                        vital_signs = self.check_vital_signs()
                        if vital_signs:
                            logger.info(f"💓 Vital Signs detected: {vital_signs}")
                    
                    except json.JSONDecodeError:
                        logger.error("Failed to parse FHIR API response")
                
                time.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"FHIR database monitoring error: {e}")
                time.sleep(60)

    def check_vital_signs(self) -> List[dict]:
        """Check for vital signs observations"""
        try:
            result = subprocess.run(
                ['curl', '-s', 'http://localhost:5054/fhir/R5/Observation?_count=50'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
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
                            'unit': resource.get('valueQuantity', {}).get('unit')
                        })
                
                return vital_signs
                
        except Exception as e:
            logger.error(f"Error checking vital signs: {e}")
        
        return []

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
🚨 DOCKER MEDICAL DATA MONITOR ALERT 🚨
Title: {title}
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Data: {json.dumps(data, indent=2, default=str)}

Current System Status:
{self.get_system_status_summary()}

Device Status:
{self.get_device_status_summary()}
"""
        
        logger.critical(alert_message)
        
        # Additional alert mechanisms can be added here:
        # - Email notification
        # - Slack/Teams webhook
        # - SMS notification
        # - Telegram bot

    def get_system_status_summary(self) -> str:
        """Get system status summary"""
        total_success = sum(status['success_count'] for status in self.device_status.values())
        total_failures = sum(status['failure_count'] for status in self.device_status.values())
        total_operations = total_success + total_failures
        
        success_rate = (total_success / max(total_operations, 1)) * 100
        
        return f"""
- Total Operations: {total_operations}
- Successful: {total_success}
- Failed: {total_failures}
- Success Rate: {success_rate:.1f}%
"""

    def get_device_status_summary(self) -> str:
        """Get device status summary"""
        summary = []
        for device_type, status in self.device_status.items():
            active_status = "🟢 ACTIVE" if status['active'] else "🔴 INACTIVE"
            last_seen = status['last_seen'].strftime('%H:%M:%S') if status['last_seen'] else "Never"
            error_count = len(status['errors'])
            success_rate = (status['success_count'] / max(status['success_count'] + status['failure_count'], 1)) * 100
            
            summary.append(
                f"  {device_type}: {active_status} (Last: {last_seen}, "
                f"Success: {status['success_count']}, Failures: {status['failure_count']}, "
                f"Rate: {success_rate:.1f}%, Errors: {error_count})"
            )
        
        return "\n".join(summary)

    def generate_status_report(self):
        """Generate periodic status report"""
        report = f"""
📊 DOCKER MEDICAL DATA MONITOR STATUS REPORT
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

{self.get_system_status_summary()}

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
                all_errors.append(
                    f"  {device_type}: {error['error_type']} ({error['timestamp'].strftime('%H:%M:%S')})"
                )
        
        return "\n".join(all_errors) if all_errors else "  No recent errors"

    def stop_monitoring(self):
        """Stop all monitoring"""
        logger.info("Stopping Docker medical data monitor...")
        self.running = False

def main():
    """Main function to run the Docker medical data monitor"""
    logger.info("🚀 Starting Docker Medical Data Monitor...")
    
    monitor = DockerMedicalMonitor()
    
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