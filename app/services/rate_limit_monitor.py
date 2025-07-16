import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import requests
from config import settings, logger

class RateLimitMonitor:
    """Monitor rate limit events and send Telegram alerts"""
    
    def __init__(self):
        self.telegram_bot_token = settings.telegram_bot_token
        self.telegram_chat_id = settings.telegram_chat_id
        self.alert_cooldown = 300  # 5 minutes between alerts
        self.last_alert_time = {}
        self.rate_limit_events = []
        self.max_events_to_store = 100
        
    async def record_rate_limit_event(
        self,
        ip_address: str,
        endpoint: str,
        limit_type: str,
        limit: int,
        window: int,
        user_id: Optional[str] = None,
        api_key: Optional[str] = None
    ):
        """Record a rate limit event and potentially send alert"""
        try:
            event = {
                "timestamp": datetime.utcnow(),
                "ip_address": ip_address,
                "endpoint": endpoint,
                "limit_type": limit_type,
                "limit": limit,
                "window": window,
                "user_id": user_id,
                "api_key": api_key
            }
            
            # Store event
            self.rate_limit_events.append(event)
            if len(self.rate_limit_events) > self.max_events_to_store:
                self.rate_limit_events.pop(0)
            
            # Check if we should send alert
            await self._check_and_send_alert(event)
            
            logger.warning(f"Rate limit event recorded: {ip_address} -> {endpoint} ({limit_type})")
            
        except Exception as e:
            logger.error(f"Error recording rate limit event: {e}")
    
    async def _check_and_send_alert(self, event: Dict[str, Any]):
        """Check if we should send an alert based on cooldown and severity"""
        try:
            # Create alert key
            alert_key = f"{event['ip_address']}_{event['limit_type']}"
            current_time = datetime.utcnow()
            
            # Check cooldown
            if alert_key in self.last_alert_time:
                time_since_last = (current_time - self.last_alert_time[alert_key]).total_seconds()
                if time_since_last < self.alert_cooldown:
                    return  # Still in cooldown period
            
            # Check severity (multiple events in short time)
            recent_events = [
                e for e in self.rate_limit_events 
                if (current_time - e['timestamp']).total_seconds() < 300  # Last 5 minutes
                and e['ip_address'] == event['ip_address']
                and e['limit_type'] == event['limit_type']
            ]
            
            # Determine alert level
            if len(recent_events) >= 10:
                alert_level = "🚨 CRITICAL"
                alert_emoji = "🚨"
            elif len(recent_events) >= 5:
                alert_level = "⚠️ HIGH"
                alert_emoji = "⚠️"
            elif len(recent_events) >= 2:
                alert_level = "🔶 MEDIUM"
                alert_emoji = "🔶"
            else:
                alert_level = "ℹ️ LOW"
                alert_emoji = "ℹ️"
            
            # Send alert
            await self._send_telegram_alert(event, alert_level, alert_emoji, len(recent_events))
            
            # Update last alert time
            self.last_alert_time[alert_key] = current_time
            
        except Exception as e:
            logger.error(f"Error checking and sending alert: {e}")
    
    async def _send_telegram_alert(
        self, 
        event: Dict[str, Any], 
        alert_level: str, 
        alert_emoji: str,
        recent_count: int
    ):
        """Send rate limit alert to Telegram"""
        try:
            if not self.telegram_bot_token or not self.telegram_chat_id:
                logger.warning("Telegram bot token or chat ID not configured")
                return
            
            # Format message
            message = f"""{alert_emoji} <b>Rate Limit Alert</b>

<b>Level:</b> {alert_level}
<b>IP Address:</b> <code>{event['ip_address']}</code>
<b>Endpoint:</b> <code>{event['endpoint']}</code>
<b>Limit Type:</b> {event['limit_type']}
<b>Limit:</b> {event['limit']} requests per {event['window']}s
<b>Recent Events:</b> {recent_count} in last 5 minutes

<b>Time:</b> {event['timestamp'].strftime('%Y-%m-%d %H:%M:%S UTC')}

<b>Details:</b>
• User ID: {event['user_id'] or 'Anonymous'}
• API Key: {'Yes' if event['api_key'] else 'No'}

<b>Action Required:</b>
• Monitor this IP for suspicious activity
• Check if legitimate user needs rate limit increase
• Consider adding to whitelist if trusted"""
            
            # Send to Telegram
            url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
            payload = {
                "chat_id": self.telegram_chat_id,
                "text": message,
                "parse_mode": "HTML"
            }
            
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            if result.get("ok"):
                logger.info(f"Rate limit alert sent to Telegram: {alert_level}")
            else:
                logger.error(f"Telegram API error: {result.get('description')}")
                
        except Exception as e:
            logger.error(f"Failed to send Telegram rate limit alert: {e}")
    
    async def get_rate_limit_summary(self) -> Dict[str, Any]:
        """Get summary of recent rate limit events"""
        try:
            current_time = datetime.utcnow()
            
            # Get events from last 24 hours
            recent_events = [
                e for e in self.rate_limit_events 
                if (current_time - e['timestamp']).total_seconds() < 86400
            ]
            
            # Group by IP address
            ip_stats = {}
            for event in recent_events:
                ip = event['ip_address']
                if ip not in ip_stats:
                    ip_stats[ip] = {
                        'total_events': 0,
                        'endpoints': set(),
                        'limit_types': set(),
                        'last_event': event['timestamp']
                    }
                
                ip_stats[ip]['total_events'] += 1
                ip_stats[ip]['endpoints'].add(event['endpoint'])
                ip_stats[ip]['limit_types'].add(event['limit_type'])
            
            # Convert sets to lists for JSON serialization
            for ip in ip_stats:
                ip_stats[ip]['endpoints'] = list(ip_stats[ip]['endpoints'])
                ip_stats[ip]['limit_types'] = list(ip_stats[ip]['limit_types'])
                ip_stats[ip]['last_event'] = ip_stats[ip]['last_event'].isoformat()
            
            return {
                'total_events_24h': len(recent_events),
                'unique_ips': len(ip_stats),
                'ip_statistics': ip_stats,
                'timestamp': current_time.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting rate limit summary: {e}")
            return {'error': str(e)}
    
    async def send_daily_summary(self):
        """Send daily rate limit summary to Telegram"""
        try:
            if not self.telegram_bot_token or not self.telegram_chat_id:
                return
            
            summary = await self.get_rate_limit_summary()
            
            if 'error' in summary:
                return
            
            # Format summary message
            message = f"""📊 <b>Daily Rate Limit Summary</b>

<b>Period:</b> Last 24 hours
<b>Total Events:</b> {summary['total_events_24h']}
<b>Unique IPs:</b> {summary['unique_ips']}

<b>Top IPs by Events:</b>"""
            
            # Sort IPs by event count
            sorted_ips = sorted(
                summary['ip_statistics'].items(),
                key=lambda x: x[1]['total_events'],
                reverse=True
            )[:5]  # Top 5
            
            for ip, stats in sorted_ips:
                message += f"""
• <code>{ip}</code>: {stats['total_events']} events
  - Endpoints: {', '.join(stats['endpoints'][:3])}{'...' if len(stats['endpoints']) > 3 else ''}
  - Last Event: {stats['last_event'][:19]}"""
            
            message += f"""

<b>Generated:</b> {summary['timestamp'][:19]} UTC"""
            
            # Send to Telegram
            url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
            payload = {
                "chat_id": self.telegram_chat_id,
                "text": message,
                "parse_mode": "HTML"
            }
            
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            if result.get("ok"):
                logger.info("Daily rate limit summary sent to Telegram")
            else:
                logger.error(f"Telegram API error: {result.get('description')}")
                
        except Exception as e:
            logger.error(f"Failed to send daily rate limit summary: {e}")

# Global instance
rate_limit_monitor = RateLimitMonitor() 