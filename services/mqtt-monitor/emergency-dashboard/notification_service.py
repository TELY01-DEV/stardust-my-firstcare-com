import smtplib
import requests
import json
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import os
from typing import Dict, List, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EmergencyNotificationService:
    def __init__(self):
        self.email_config = {
            'smtp_server': os.environ.get('SMTP_SERVER', 'smtp.gmail.com'),
            'smtp_port': int(os.environ.get('SMTP_PORT', '587')),
            'email_user': os.environ.get('EMAIL_USER', ''),
            'email_password': os.environ.get('EMAIL_PASSWORD', ''),
            'from_email': os.environ.get('FROM_EMAIL', 'emergency@myfirstcare.com'),
            'to_emails': os.environ.get('TO_EMAILS', '').split(',') if os.environ.get('TO_EMAILS') else []
        }
        
        self.telegram_config = {
            'bot_token': os.environ.get('TELEGRAM_BOT_TOKEN', ''),
            'chat_id': os.environ.get('TELEGRAM_CHAT_ID', ''),
            'enabled': bool(os.environ.get('TELEGRAM_ENABLED', 'false').lower() == 'true')
        }
        
        self.sms_config = {
            'api_key': os.environ.get('SMS_API_KEY', ''),
            'api_secret': os.environ.get('SMS_API_SECRET', ''),
            'from_number': os.environ.get('SMS_FROM_NUMBER', ''),
            'to_numbers': os.environ.get('SMS_TO_NUMBERS', '').split(',') if os.environ.get('SMS_TO_NUMBERS') else [],
            'enabled': bool(os.environ.get('SMS_ENABLED', 'false').lower() == 'true')
        }
        
        self.webhook_config = {
            'url': os.environ.get('WEBHOOK_URL', ''),
            'enabled': bool(os.environ.get('WEBHOOK_ENABLED', 'false').lower() == 'true')
        }

    def send_emergency_notification(self, alert_data: Dict) -> Dict[str, bool]:
        """
        Send emergency notification through all configured channels
        """
        results = {
            'email': False,
            'telegram': False,
            'sms': False,
            'webhook': False
        }
        
        try:
            # Prepare notification message
            message = self._prepare_notification_message(alert_data)
            
            # Send via email
            if self.email_config['to_emails']:
                results['email'] = self._send_email_notification(message, alert_data)
            
            # Send via Telegram
            if self.telegram_config['enabled']:
                results['telegram'] = self._send_telegram_notification(message, alert_data)
            
            # Send via SMS
            if self.sms_config['enabled']:
                results['sms'] = self._send_sms_notification(message, alert_data)
            
            # Send via webhook
            if self.webhook_config['enabled']:
                results['webhook'] = self._send_webhook_notification(alert_data)
            
            logger.info(f"Emergency notification sent - Results: {results}")
            
        except Exception as e:
            logger.error(f"Error sending emergency notification: {e}")
        
        return results

    def _prepare_notification_message(self, alert_data: Dict) -> str:
        """
        Prepare notification message based on alert data
        """
        alert_type = alert_data.get('alert_type', 'unknown').upper()
        patient_name = alert_data.get('patient_name', 'Unknown Patient')
        priority = alert_data.get('alert_data', {}).get('priority', 'HIGH')
        timestamp = alert_data.get('timestamp', datetime.now()).strftime('%Y-%m-%d %H:%M:%S')
        
        # Get location info
        location = alert_data.get('alert_data', {}).get('location', {})
        location_text = "No location data"
        
        if location.get('GPS'):
            lat = location['GPS'].get('latitude', 'N/A')
            lng = location['GPS'].get('longitude', 'N/A')
            location_text = f"GPS: {lat}, {lng}"
        elif location.get('WiFi'):
            location_text = "WiFi location available"
        elif location.get('LBS'):
            location_text = "Cell tower location available"
        
        message = f"""
🚨 EMERGENCY ALERT 🚨

Type: {alert_type}
Patient: {patient_name}
Priority: {priority}
Time: {timestamp}
Location: {location_text}

This is an automated emergency notification from MyFirstCare system.
Please respond immediately if this is a real emergency.
        """.strip()
        
        return message

    def _send_email_notification(self, message: str, alert_data: Dict) -> bool:
        """
        Send email notification
        """
        try:
            if not all([self.email_config['email_user'], self.email_config['email_password'], self.email_config['to_emails']]):
                logger.warning("Email configuration incomplete")
                return False
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.email_config['from_email']
            msg['To'] = ', '.join(self.email_config['to_emails'])
            msg['Subject'] = f"🚨 EMERGENCY ALERT - {alert_data.get('alert_type', 'unknown').upper()}"
            
            # Add body
            msg.attach(MIMEText(message, 'plain'))
            
            # Send email
            server = smtplib.SMTP(self.email_config['smtp_server'], self.email_config['smtp_port'])
            server.starttls()
            server.login(self.email_config['email_user'], self.email_config['email_password'])
            
            text = msg.as_string()
            server.sendmail(self.email_config['from_email'], self.email_config['to_emails'], text)
            server.quit()
            
            logger.info(f"Email notification sent to {self.email_config['to_emails']}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending email notification: {e}")
            return False

    def _send_telegram_notification(self, message: str, alert_data: Dict) -> bool:
        """
        Send Telegram notification
        """
        try:
            if not all([self.telegram_config['bot_token'], self.telegram_config['chat_id']]):
                logger.warning("Telegram configuration incomplete")
                return False
            
            url = f"https://api.telegram.org/bot{self.telegram_config['bot_token']}/sendMessage"
            
            data = {
                'chat_id': self.telegram_config['chat_id'],
                'text': message,
                'parse_mode': 'HTML'
            }
            
            response = requests.post(url, data=data, timeout=10)
            response.raise_for_status()
            
            logger.info(f"Telegram notification sent to chat {self.telegram_config['chat_id']}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending Telegram notification: {e}")
            return False

    def _send_sms_notification(self, message: str, alert_data: Dict) -> bool:
        """
        Send SMS notification (using Twilio as example)
        """
        try:
            if not all([self.sms_config['api_key'], self.sms_config['api_secret'], self.sms_config['to_numbers']]):
                logger.warning("SMS configuration incomplete")
                return False
            
            # This is an example using Twilio - adjust for your SMS provider
            url = "https://api.twilio.com/2010-04-01/Accounts/{}/Messages.json".format(self.sms_config['api_key'])
            
            for to_number in self.sms_config['to_numbers']:
                data = {
                    'From': self.sms_config['from_number'],
                    'To': to_number,
                    'Body': message
                }
                
                response = requests.post(
                    url,
                    data=data,
                    auth=(self.sms_config['api_key'], self.sms_config['api_secret']),
                    timeout=10
                )
                response.raise_for_status()
            
            logger.info(f"SMS notification sent to {self.sms_config['to_numbers']}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending SMS notification: {e}")
            return False

    def _send_webhook_notification(self, alert_data: Dict) -> bool:
        """
        Send webhook notification
        """
        try:
            if not self.webhook_config['url']:
                logger.warning("Webhook URL not configured")
                return False
            
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'MyFirstCare-Emergency-System/1.0'
            }
            
            # Prepare webhook payload
            payload = {
                'timestamp': datetime.now().isoformat(),
                'type': 'emergency_alert',
                'data': alert_data,
                'source': 'myfirstcare_emergency_system'
            }
            
            response = requests.post(
                self.webhook_config['url'],
                json=payload,
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            
            logger.info(f"Webhook notification sent to {self.webhook_config['url']}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending webhook notification: {e}")
            return False

    def test_notifications(self) -> Dict[str, bool]:
        """
        Test all notification channels
        """
        test_alert = {
            'alert_type': 'test',
            'patient_name': 'Test Patient',
            'alert_data': {
                'priority': 'HIGH',
                'location': {
                    'GPS': {
                        'latitude': 13.7563,
                        'longitude': 100.5018
                    }
                }
            },
            'timestamp': datetime.now()
        }
        
        logger.info("Testing notification channels...")
        return self.send_emergency_notification(test_alert)

# Global notification service instance
notification_service = EmergencyNotificationService()

def send_emergency_notification(alert_data: Dict) -> Dict[str, bool]:
    """
    Global function to send emergency notification
    """
    return notification_service.send_emergency_notification(alert_data)

if __name__ == "__main__":
    # Test notifications
    results = notification_service.test_notifications()
    print(f"Test results: {results}") 