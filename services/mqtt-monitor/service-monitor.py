#!/usr/bin/env python3
"""
Service Monitor with Telegram Alerts
Monitors Docker services and sends Telegram alerts for status changes
"""

import os
import json
import logging
import time
import requests
import subprocess
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import docker
from docker.errors import NotFound
from dataclasses import dataclass
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('service_monitor.log')
    ]
)
logger = logging.getLogger(__name__)

class ServiceStatus(Enum):
    RUNNING = "running"
    STOPPED = "stopped"
    RESTARTING = "restarting"
    PAUSED = "paused"
    EXITED = "exited"
    UNKNOWN = "unknown"

@dataclass
class ServiceInfo:
    name: str
    container_id: str
    status: ServiceStatus
    health: Optional[str] = None
    last_seen: Optional[datetime] = None
    restart_count: int = 0
    alert_sent: bool = False

class ServiceMonitor:
    def __init__(self):
        self.telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.check_interval = int(os.getenv('SERVICE_CHECK_INTERVAL', '30'))
        self.alert_cooldown = int(os.getenv('ALERT_COOLDOWN_MINUTES', '5'))
        
        # Service configurations
        self.services_to_monitor = [
            'stardust-my-firstcare-com',
            'stardust-ava4-listener',
            'stardust-kati-listener', 
            'stardust-qube-listener',
            'stardust-mqtt-panel',
            'stardust-mqtt-websocket',
            'stardust-redis'
        ]
        
        # Track service states
        self.service_states: Dict[str, ServiceInfo] = {}
        self.last_alert_time: Dict[str, datetime] = {}
        
        # Initialize Docker client
        try:
            self.docker_client = docker.from_env()
            logger.info("✅ Docker client initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Docker client: {e}")
            raise
        
        # Send startup alert
        self.send_telegram_alert("🚀 **Service Monitor Started**\n\nMonitoring services for status changes...")
    
    def get_container_status(self, container_name: str) -> Optional[ServiceInfo]:
        """Get current status of a Docker container"""
        try:
            container = self.docker_client.containers.get(container_name)
            container.reload()  # Refresh container info
            
            # Get health status
            health = None
            if container.attrs.get('State', {}).get('Health'):
                health = container.attrs['State']['Health']['Status']
            
            # Get restart count
            restart_count = container.attrs['RestartCount']
            
            return ServiceInfo(
                name=container_name,
                container_id=container.short_id,
                status=ServiceStatus(container.status),
                health=health,
                last_seen=datetime.now(),
                restart_count=restart_count
            )
        except NotFound:
            return ServiceInfo(
                name=container_name,
                container_id="N/A",
                status=ServiceStatus.STOPPED,
                last_seen=datetime.now()
            )
        except Exception as e:
            logger.error(f"❌ Error getting status for {container_name}: {e}")
            return None
    
    def can_send_alert(self, service_name: str) -> bool:
        """Check if enough time has passed since last alert for this service"""
        if service_name not in self.last_alert_time:
            return True
        
        time_since_last = datetime.now() - self.last_alert_time[service_name]
        return time_since_last.total_seconds() > (self.alert_cooldown * 60)
    
    def send_telegram_alert(self, message: str, service_name: Optional[str] = None):
        """Send Telegram alert"""
        if not self.telegram_token or not self.telegram_chat_id:
            logger.warning("⚠️ Telegram not configured, skipping alert")
            return
        
        try:
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            data = {
                'chat_id': self.telegram_chat_id,
                'text': message,
                'parse_mode': 'Markdown'
            }
            
            response = requests.post(url, data=data, timeout=10)
            response.raise_for_status()
            
            if service_name:
                self.last_alert_time[service_name] = datetime.now()
            
            logger.info(f"✅ Telegram alert sent: {message[:50]}...")
            
        except Exception as e:
            logger.error(f"❌ Failed to send Telegram alert: {e}")
    
    def format_status_emoji(self, status: ServiceStatus) -> str:
        """Get emoji for service status"""
        emoji_map = {
            ServiceStatus.RUNNING: "🟢",
            ServiceStatus.STOPPED: "🔴", 
            ServiceStatus.RESTARTING: "🟡",
            ServiceStatus.PAUSED: "⏸️",
            ServiceStatus.EXITED: "💀",
            ServiceStatus.UNKNOWN: "❓"
        }
        return emoji_map.get(status, "❓")
    
    def check_service_status(self):
        """Check status of all monitored services"""
        current_time = datetime.now()
        
        for service_name in self.services_to_monitor:
            current_status = self.get_container_status(service_name)
            
            if not current_status:
                continue
            
            # Check if this is a new service or status change
            if service_name not in self.service_states:
                # New service detected
                self.service_states[service_name] = current_status
                if current_status.status == ServiceStatus.RUNNING:
                    message = f"🚀 **Service Started**\n\n"
                    message += f"**Service:** `{service_name}`\n"
                    message += f"**Status:** {self.format_status_emoji(current_status.status)} Running\n"
                    message += f"**Container ID:** `{current_status.container_id}`\n"
                    message += f"**Time:** {current_time.strftime('%Y-%m-%d %H:%M:%S')}"
                    
                    self.send_telegram_alert(message, service_name)
                    logger.info(f"🚀 Service started: {service_name}")
                
            else:
                previous_status = self.service_states[service_name]
                
                # Check for status changes
                if current_status.status != previous_status.status:
                    # Status changed
                    if current_status.status == ServiceStatus.RUNNING:
                        message = f"✅ **Service Restored**\n\n"
                        message += f"**Service:** `{service_name}`\n"
                        message += f"**Previous Status:** {self.format_status_emoji(previous_status.status)} {previous_status.status.value.title()}\n"
                        message += f"**Current Status:** {self.format_status_emoji(current_status.status)} Running\n"
                        message += f"**Restart Count:** {current_status.restart_count}\n"
                        message += f"**Time:** {current_time.strftime('%Y-%m-%d %H:%M:%S')}"
                        
                        self.send_telegram_alert(message, service_name)
                        logger.info(f"✅ Service restored: {service_name}")
                    
                    elif current_status.status in [ServiceStatus.STOPPED, ServiceStatus.EXITED]:
                        message = f"🔴 **Service Stopped**\n\n"
                        message += f"**Service:** `{service_name}`\n"
                        message += f"**Previous Status:** {self.format_status_emoji(previous_status.status)} {previous_status.status.value.title()}\n"
                        message += f"**Current Status:** {self.format_status_emoji(current_status.status)} {current_status.status.value.title()}\n"
                        message += f"**Restart Count:** {current_status.restart_count}\n"
                        message += f"**Time:** {current_time.strftime('%Y-%m-%d %H:%M:%S')}"
                        
                        self.send_telegram_alert(message, service_name)
                        logger.info(f"🔴 Service stopped: {service_name}")
                    
                    elif current_status.status == ServiceStatus.RESTARTING:
                        message = f"🔄 **Service Restarting**\n\n"
                        message += f"**Service:** `{service_name}`\n"
                        message += f"**Previous Status:** {self.format_status_emoji(previous_status.status)} {previous_status.status.value.title()}\n"
                        message += f"**Current Status:** {self.format_status_emoji(current_status.status)} Restarting\n"
                        message += f"**Restart Count:** {current_status.restart_count}\n"
                        message += f"**Time:** {current_time.strftime('%Y-%m-%d %H:%M:%S')}"
                        
                        self.send_telegram_alert(message, service_name)
                        logger.info(f"🔄 Service restarting: {service_name}")
                
                # Check for malfunction (high restart count or unhealthy)
                elif (current_status.status == ServiceStatus.RUNNING and 
                      current_status.restart_count > previous_status.restart_count and
                      current_status.restart_count > 3):
                    
                    message = f"⚠️ **Service Malfunction Detected**\n\n"
                    message += f"**Service:** `{service_name}`\n"
                    message += f"**Status:** {self.format_status_emoji(current_status.status)} Running\n"
                    message += f"**Restart Count:** {current_status.restart_count} (High)\n"
                    message += f"**Health:** {current_status.health or 'Unknown'}\n"
                    message += f"**Time:** {current_time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                    message += "⚠️ Service is restarting frequently - possible malfunction!"
                    
                    self.send_telegram_alert(message, service_name)
                    logger.warning(f"⚠️ Service malfunction detected: {service_name} (restart count: {current_status.restart_count})")
                
                # Check for unhealthy status
                elif (current_status.status == ServiceStatus.RUNNING and 
                      current_status.health == 'unhealthy' and
                      self.can_send_alert(service_name)):
                    
                    message = f"🏥 **Service Unhealthy**\n\n"
                    message += f"**Service:** `{service_name}`\n"
                    message += f"**Status:** {self.format_status_emoji(current_status.status)} Running\n"
                    message += f"**Health:** 🏥 Unhealthy\n"
                    message += f"**Container ID:** `{current_status.container_id}`\n"
                    message += f"**Time:** {current_time.strftime('%Y-%m-%d %H:%M:%S')}"
                    
                    self.send_telegram_alert(message, service_name)
                    logger.warning(f"🏥 Service unhealthy: {service_name}")
            
            # Update service state
            self.service_states[service_name] = current_status
    
    def generate_status_report(self) -> str:
        """Generate a comprehensive status report"""
        report = "📊 **Service Status Report**\n\n"
        report += f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        running_count = 0
        stopped_count = 0
        restarting_count = 0
        
        for service_name in self.services_to_monitor:
            if service_name in self.service_states:
                status = self.service_states[service_name]
                emoji = self.format_status_emoji(status.status)
                
                report += f"{emoji} **{service_name}**\n"
                report += f"   Status: {status.status.value.title()}\n"
                report += f"   Health: {status.health or 'Unknown'}\n"
                report += f"   Restarts: {status.restart_count}\n"
                report += f"   Container: `{status.container_id}`\n\n"
                
                if status.status == ServiceStatus.RUNNING:
                    running_count += 1
                elif status.status in [ServiceStatus.STOPPED, ServiceStatus.EXITED]:
                    stopped_count += 1
                elif status.status == ServiceStatus.RESTARTING:
                    restarting_count += 1
            else:
                report += f"❓ **{service_name}**\n   Status: Unknown\n\n"
                stopped_count += 1
        
        report += f"**Summary:**\n"
        report += f"🟢 Running: {running_count}\n"
        report += f"🔴 Stopped: {stopped_count}\n"
        report += f"🟡 Restarting: {restarting_count}\n"
        
        return report
    
    def send_periodic_report(self):
        """Send periodic status report"""
        report = self.generate_status_report()
        self.send_telegram_alert(report)
        logger.info("📊 Periodic status report sent")
    
    def run(self):
        """Main monitoring loop"""
        logger.info("🚀 Starting Service Monitor with Telegram Alerts")
        logger.info(f"📋 Monitoring {len(self.services_to_monitor)} services")
        logger.info(f"⏰ Check interval: {self.check_interval} seconds")
        logger.info(f"🔔 Alert cooldown: {self.alert_cooldown} minutes")
        
        last_report_time = datetime.now()
        report_interval = timedelta(hours=6)  # Send report every 6 hours
        
        try:
            while True:
                self.check_service_status()
                
                # Send periodic report
                if datetime.now() - last_report_time > report_interval:
                    self.send_periodic_report()
                    last_report_time = datetime.now()
                
                time.sleep(self.check_interval)
                
        except KeyboardInterrupt:
            logger.info("🛑 Service monitor stopped by user")
            self.send_telegram_alert("🛑 **Service Monitor Stopped**\n\nMonitoring has been manually stopped.")
        except Exception as e:
            logger.error(f"❌ Service monitor error: {e}")
            self.send_telegram_alert(f"❌ **Service Monitor Error**\n\nError: {str(e)}")
            raise

if __name__ == "__main__":
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    monitor = ServiceMonitor()
    monitor.run() 