import asyncio
import json
import smtplib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dataclasses import dataclass
from enum import Enum
import requests
from config import logger, settings


class AlertLevel(Enum):
    """Alert severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertChannel(Enum):
    """Available alert channels"""
    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"
    LOG = "log"
    TELEGRAM = "telegram"


@dataclass
class Alert:
    """Alert data structure"""
    id: str
    title: str
    message: str
    level: AlertLevel
    timestamp: datetime
    source: str
    details: Dict[str, Any]
    tags: List[str]
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None


class AlertManager:
    """
    Centralized alert management system
    Handles alert creation, deduplication, and routing to appropriate channels
    """
    
    def __init__(self):
        self.alerts: Dict[str, Alert] = {}
        self.alert_rules: List[Dict[str, Any]] = []
        self.channels: Dict[AlertChannel, Any] = {}
        self.alert_history: List[Alert] = []
        self.rate_limits: Dict[str, datetime] = {}
        self.alert_counts: Dict[str, List[datetime]] = {}  # Track alert counts for smart rate limiting
        self._setup_default_rules()
    
    def _setup_default_rules(self):
        """Setup default alert rules"""
        self.alert_rules = [
            {
                "name": "database_connection_failure",
                "condition": lambda event: event.get("error_type") == "database_connection_error",
                "level": AlertLevel.CRITICAL,
                "channels": [AlertChannel.EMAIL, AlertChannel.SLACK, AlertChannel.TELEGRAM, AlertChannel.LOG],
                "rate_limit_minutes": 5
            },
            {
                "name": "authentication_failures",
                "condition": lambda event: event.get("event_type") == "security_event" and \
                           "authentication_failure" in event.get("security_events", []),
                "level": AlertLevel.HIGH,
                "channels": [AlertChannel.EMAIL, AlertChannel.TELEGRAM, AlertChannel.LOG],
                "rate_limit_minutes": 10
            },
            {
                "name": "brute_force_attack",
                "condition": lambda event: event.get("event_type") == "security_alert" and \
                           "BRUTE_FORCE_DETECTED" in event.get("message", ""),
                "level": AlertLevel.CRITICAL,
                "channels": [AlertChannel.EMAIL, AlertChannel.SLACK, AlertChannel.TELEGRAM, AlertChannel.LOG],
                "rate_limit_minutes": 1
            },
            {
                "name": "slow_database_queries",
                "condition": lambda event: event.get("event_type") == "database_performance" and \
                           event.get("duration_ms", 0) > 5000,
                "level": AlertLevel.MEDIUM,
                "channels": [AlertChannel.LOG],
                "rate_limit_minutes": 30
            },
            {
                "name": "high_error_rate",
                "condition": lambda event: event.get("event_type") == "http_error" and \
                           event.get("status_code", 0) >= 500,
                "level": AlertLevel.HIGH,
                "channels": [AlertChannel.EMAIL, AlertChannel.TELEGRAM, AlertChannel.LOG],
                "rate_limit_minutes": 15  # Rate limit after first 5 alerts in 5 minutes
            },
            {
                "name": "invalid_data_type_error",
                "condition": lambda event: event.get("event_type") == "http_error" and \
                           event.get("status_code", 0) == 400 and \
                           ("INVALID_DATA_TYPE" in event.get("error_message", "") or "Invalid data type" in event.get("error_message", "")),
                "level": AlertLevel.MEDIUM,
                "channels": [AlertChannel.TELEGRAM, AlertChannel.LOG],
                "rate_limit_minutes": 10  # Rate limit after first 5 alerts in 5 minutes
            },
            {
                "name": "disk_space_low",
                "condition": lambda event: event.get("event_type") == "system_resource" and \
                           event.get("disk_usage_percent", 0) > 90,
                "level": AlertLevel.HIGH,
                "channels": [AlertChannel.EMAIL, AlertChannel.SLACK, AlertChannel.TELEGRAM, AlertChannel.LOG],
                "rate_limit_minutes": 60
            }
        ]
    
    def configure_channel(self, channel: AlertChannel, config: Dict[str, Any]):
        """Configure an alert channel"""
        self.channels[channel] = config
    
    async def process_event(self, event: Dict[str, Any]):
        """Process an event and generate alerts if rules match"""
        for rule in self.alert_rules:
            try:
                if rule["condition"](event):
                    await self._create_alert(rule, event)
            except Exception as e:
                logger.error(f"Error processing alert rule {rule['name']}: {str(e)}")
    
    async def _create_alert(self, rule: Dict[str, Any], event: Dict[str, Any]):
        """Create an alert based on rule and event"""
        alert_key = f"{rule['name']}_{event.get('source', 'unknown')}"
        
        # Check rate limiting
        if self._is_rate_limited(alert_key, rule.get("rate_limit_minutes", 0)):
            return
        
        # Create alert
        alert = Alert(
            id=alert_key,
            title=rule["name"].replace("_", " ").title(),
            message=self._format_alert_message(rule, event),
            level=rule["level"],
            timestamp=datetime.utcnow(),
            source=event.get("source", "system"),
            details=event,
            tags=rule.get("tags", [])
        )
        
        # Store alert
        self.alerts[alert.id] = alert
        self.alert_history.append(alert)
        
        # Send to configured channels
        for channel in rule.get("channels", []):
            await self._send_alert(alert, channel)
    
    def _is_rate_limited(self, alert_key: str, rate_limit_minutes: int) -> bool:
        """Check if alert is rate limited using smart rate limiting"""
        if rate_limit_minutes <= 0:
            return False
        
        now = datetime.utcnow()
        
        # Initialize alert count tracking for this key
        if alert_key not in self.alert_counts:
            self.alert_counts[alert_key] = []
        
        # Clean old timestamps (older than 5 minutes)
        self.alert_counts[alert_key] = [
            ts for ts in self.alert_counts[alert_key] 
            if (now - ts).total_seconds() < 300  # 5 minutes = 300 seconds
        ]
        
        # Smart rate limiting logic
        recent_alerts = len(self.alert_counts[alert_key])
        
        if recent_alerts < 5:
            # Allow first 5 alerts in 5 minutes
            self.alert_counts[alert_key].append(now)
            return False
        else:
            # After 5 alerts, apply normal rate limiting
            if alert_key in self.rate_limits:
                time_diff = now - self.rate_limits[alert_key]
                if time_diff.total_seconds() < (rate_limit_minutes * 60):
                    return True
            
            # Reset rate limit and allow one more alert
            self.rate_limits[alert_key] = now
            self.alert_counts[alert_key].append(now)
            return False
    
    def _format_alert_message(self, rule: Dict[str, Any], event: Dict[str, Any]) -> str:
        """Format alert message"""
        base_message = f"Alert: {rule['name'].replace('_', ' ').title()}"
        
        if event.get("message"):
            base_message += f"\nMessage: {event['message']}"
        
        if event.get("error_message"):
            base_message += f"\nError: {event['error_message']}"
        
        if event.get("client_ip"):
            base_message += f"\nClient IP: {event['client_ip']}"
        
        if event.get("user_id"):
            base_message += f"\nUser: {event['user_id']}"
        
        if event.get("duration_ms"):
            base_message += f"\nDuration: {event['duration_ms']}ms"
        
        base_message += f"\nTimestamp: {event.get('timestamp', datetime.utcnow().isoformat())}"
        
        return base_message
    
    async def _send_alert(self, alert: Alert, channel: AlertChannel):
        """Send alert to specific channel"""
        try:
            if channel == AlertChannel.EMAIL:
                await self._send_email_alert(alert)
            elif channel == AlertChannel.SLACK:
                await self._send_slack_alert(alert)
            elif channel == AlertChannel.WEBHOOK:
                await self._send_webhook_alert(alert)
            elif channel == AlertChannel.TELEGRAM:
                await self._send_telegram_alert(alert)
            elif channel == AlertChannel.LOG:
                self._log_alert(alert)
        except Exception as e:
            logger.error(f"Failed to send alert via {channel.value}: {str(e)}")
    
    async def _send_email_alert(self, alert: Alert):
        """Send alert via email"""
        email_config = self.channels.get(AlertChannel.EMAIL)
        if not email_config:
            return
        
        try:
            msg = MIMEMultipart()
            msg['From'] = email_config['from_email']
            msg['To'] = ', '.join(email_config['to_emails'])
            msg['Subject'] = f"[{alert.level.value.upper()}] {alert.title}"
            
            body = f"""
Alert Details:
- Level: {alert.level.value.upper()}
- Source: {alert.source}
- Timestamp: {alert.timestamp.isoformat()}

{alert.message}

Additional Details:
{json.dumps(alert.details, indent=2)}
"""
            
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP(email_config['smtp_server'], email_config['smtp_port'])
            if email_config.get('use_tls'):
                server.starttls()
            if email_config.get('username'):
                server.login(email_config['username'], email_config['password'])
            
            server.send_message(msg)
            server.quit()
            
            logger.info(f"Email alert sent for {alert.id}")
            
        except Exception as e:
            logger.error(f"Failed to send email alert: {str(e)}")
    
    async def _send_slack_alert(self, alert: Alert):
        """Send alert via Slack webhook"""
        slack_config = self.channels.get(AlertChannel.SLACK)
        if not slack_config:
            return
        
        try:
            color_map = {
                AlertLevel.LOW: "good",
                AlertLevel.MEDIUM: "warning",
                AlertLevel.HIGH: "danger",
                AlertLevel.CRITICAL: "danger"
            }
            
            payload = {
                "text": f"🚨 {alert.title}",
                "attachments": [{
                    "color": color_map.get(alert.level, "warning"),
                    "fields": [
                        {"title": "Level", "value": alert.level.value.upper(), "short": True},
                        {"title": "Source", "value": alert.source, "short": True},
                        {"title": "Timestamp", "value": alert.timestamp.isoformat(), "short": True}
                    ],
                    "text": alert.message
                }]
            }
            
            response = requests.post(
                slack_config['webhook_url'],
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            
            logger.info(f"Slack alert sent for {alert.id}")
            
        except Exception as e:
            logger.error(f"Failed to send Slack alert: {str(e)}")
    
    async def _send_webhook_alert(self, alert: Alert):
        """Send alert via webhook"""
        webhook_config = self.channels.get(AlertChannel.WEBHOOK)
        if not webhook_config:
            return
        
        try:
            payload = {
                "alert_id": alert.id,
                "title": alert.title,
                "message": alert.message,
                "level": alert.level.value,
                "timestamp": alert.timestamp.isoformat(),
                "source": alert.source,
                "details": alert.details,
                "tags": alert.tags
            }
            
            headers = webhook_config.get('headers', {})
            headers['Content-Type'] = 'application/json'
            
            response = requests.post(
                webhook_config['url'],
                json=payload,
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            
            logger.info(f"Webhook alert sent for {alert.id}")
            
        except Exception as e:
            logger.error(f"Failed to send webhook alert: {str(e)}")
    
    async def _send_telegram_alert(self, alert: Alert):
        """Send alert via Telegram bot"""
        token = settings.telegram_bot_token
        chat_id = settings.telegram_chat_id
        if not token or not chat_id:
            logger.warning("Telegram bot token or chat ID not configured.")
            return
        try:
            message = f"🚨 <b>{alert.title}</b>\nLevel: <b>{alert.level.value.upper()}</b>\nSource: <b>{alert.source}</b>\nTime: <b>{alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}</b>\n\n{alert.message}"
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "HTML"
            }
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            logger.info(f"Telegram alert sent for {alert.id}")
        except Exception as e:
            logger.error(f"Failed to send Telegram alert: {str(e)}")
    
    def _log_alert(self, alert: Alert):
        """Log alert to application logs"""
        log_level = {
            AlertLevel.LOW: "info",
            AlertLevel.MEDIUM: "warning",
            AlertLevel.HIGH: "warning",
            AlertLevel.CRITICAL: "error"
        }.get(alert.level, "warning")
        
        getattr(logger, log_level)(
            f"ALERT: {alert.title}",
            extra={
                "event_type": "alert",
                "alert_id": alert.id,
                "alert_level": alert.level.value,
                "alert_source": alert.source,
                "alert_message": alert.message,
                "alert_details": alert.details,
                "alert_tags": alert.tags,
                "timestamp": alert.timestamp.isoformat()
            }
        )
    
    def resolve_alert(self, alert_id: str, resolved_by: str = "system"):
        """Resolve an alert"""
        if alert_id in self.alerts:
            alert = self.alerts[alert_id]
            alert.resolved = True
            alert.resolved_at = datetime.utcnow()
            alert.resolved_by = resolved_by
            
            logger.info(f"Alert {alert_id} resolved by {resolved_by}")
    
    def get_active_alerts(self) -> List[Alert]:
        """Get all active (unresolved) alerts"""
        return [alert for alert in self.alerts.values() if not alert.resolved]
    
    def get_alert_summary(self) -> Dict[str, Any]:
        """Get alert summary statistics"""
        active_alerts = self.get_active_alerts()
        
        level_counts = {level.value: 0 for level in AlertLevel}
        for alert in active_alerts:
            level_counts[alert.level.value] += 1
        
        return {
            "total_active": len(active_alerts),
            "by_level": level_counts,
            "total_historical": len(self.alert_history),
            "last_24h": len([
                alert for alert in self.alert_history
                if alert.timestamp > datetime.utcnow() - timedelta(hours=24)
            ])
        }


class HealthChecker:
    """
    System health checker that can trigger alerts
    """
    
    def __init__(self, alert_manager: AlertManager):
        self.alert_manager = alert_manager
        self.health_checks: List[Callable] = []
    
    def add_health_check(self, name: str, check_func: Callable):
        """Add a health check function"""
        self.health_checks.append((name, check_func))
    
    async def run_health_checks(self):
        """Run all health checks and generate alerts if needed"""
        for name, check_func in self.health_checks:
            try:
                result = await check_func()
                if not result.get("healthy", True):
                    await self.alert_manager.process_event({
                        "event_type": "health_check_failure",
                        "check_name": name,
                        "message": result.get("message", f"Health check {name} failed"),
                        "details": result.get("details", {}),
                        "timestamp": datetime.utcnow().isoformat(),
                        "source": "health_checker"
                    })
            except Exception as e:
                await self.alert_manager.process_event({
                    "event_type": "health_check_error",
                    "check_name": name,
                    "message": f"Health check {name} encountered an error",
                    "error_message": str(e),
                    "timestamp": datetime.utcnow().isoformat(),
                    "source": "health_checker"
                })


# Global alert manager instance
alert_manager = AlertManager()
health_checker = HealthChecker(alert_manager)


# Helper functions
async def send_alert(
    title: str,
    message: str,
    level: AlertLevel = AlertLevel.MEDIUM,
    source: str = "application",
    details: Optional[Dict[str, Any]] = None,
    tags: Optional[List[str]] = None
):
    """Send a custom alert"""
    event = {
        "event_type": "custom_alert",
        "title": title,
        "message": message,
        "level": level.value,
        "source": source,
        "details": details or {},
        "tags": tags or [],
        "timestamp": datetime.utcnow().isoformat()
    }
    
    await alert_manager.process_event(event)


def configure_email_alerts(
    smtp_server: str,
    smtp_port: int,
    from_email: str,
    to_emails: List[str],
    username: Optional[str] = None,
    password: Optional[str] = None,
    use_tls: bool = True
):
    """Configure email alerts"""
    alert_manager.configure_channel(AlertChannel.EMAIL, {
        "smtp_server": smtp_server,
        "smtp_port": smtp_port,
        "from_email": from_email,
        "to_emails": to_emails,
        "username": username,
        "password": password,
        "use_tls": use_tls
    })


def configure_slack_alerts(webhook_url: str):
    """Configure Slack alerts"""
    alert_manager.configure_channel(AlertChannel.SLACK, {
        "webhook_url": webhook_url
    })


def configure_webhook_alerts(url: str, headers: Optional[Dict[str, str]] = None):
    """Configure webhook alerts"""
    alert_manager.configure_channel(AlertChannel.WEBHOOK, {
        "url": url,
        "headers": headers or {}
    }) 

if __name__ == "__main__":
    import asyncio
    from datetime import datetime
    class DummyAlert:
        id = "test"
        title = "Test Alert"
        level = AlertLevel.CRITICAL
        source = "test_system"
        timestamp = datetime.utcnow()
        message = "This is a test alert from the system."
    print("Sending test Telegram alert...")
    asyncio.run(alert_manager._send_telegram_alert(DummyAlert()))
    print("Done.") 