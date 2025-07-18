#!/usr/bin/env python3
"""
Test script to send rate limit information to Telegram
"""

import os
import requests
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def send_rate_limit_alert_to_telegram():
    """Send a test rate limit alert to Telegram"""
    
    # Get Telegram configuration
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    
    if not bot_token or not chat_id:
        print("❌ Telegram bot token or chat ID not configured in .env file")
        return False
    
    try:
        # Create test rate limit alert message
        message = f"""🚨 <b>Rate Limit Alert</b>

<b>Level:</b> ⚠️ HIGH
<b>IP Address:</b> <code>172.18.0.5</code>
<b>Endpoint:</b> <code>/fhir/R5/Observation</code>
<b>Limit Type:</b> endpoint
<b>Limit:</b> 20 requests per 60s
<b>Recent Events:</b> 5 in last 5 minutes

<b>Time:</b> {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}

<b>Details:</b>
• User ID: mqtt_listener
• API Key: No

<b>Action Required:</b>
• Monitor this IP for suspicious activity
• Check if legitimate user needs rate limit increase
• Consider adding to whitelist if trusted

<b>System Status:</b>
• AVA4 Listener: ✅ Working
• Kati Listener: ✅ Working  
• Qube Listener: ✅ Connected
• FHIR Integration: ✅ Active

<b>Recent Activity:</b>
• Kati Watch: 165+ FHIR observations created
• AVA4 Gateway: Processing heartbeat data
• Rate Limiting: Fixed for internal services"""
        
        # Send to Telegram
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML"
        }
        
        print(f"📤 Sending rate limit alert to Telegram...")
        print(f"   Bot Token: {bot_token[:10]}...")
        print(f"   Chat ID: {chat_id}")
        
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        
        result = response.json()
        if result.get("ok"):
            print("✅ Rate limit alert sent successfully!")
            print(f"   Message ID: {result.get('result', {}).get('message_id')}")
            return True
        else:
            print(f"❌ Telegram API error: {result.get('description')}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def send_daily_summary_to_telegram():
    """Send a daily rate limit summary to Telegram"""
    
    # Get Telegram configuration
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    
    if not bot_token or not chat_id:
        print("❌ Telegram bot token or chat ID not configured in .env file")
        return False
    
    try:
        # Create daily summary message
        message = f"""📊 <b>Daily Rate Limit Summary</b>

<b>Period:</b> Last 24 hours
<b>Total Events:</b> 15
<b>Unique IPs:</b> 3

<b>Top IPs by Events:</b>
• <code>172.18.0.5</code>: 8 events
  - Endpoints: /fhir/R5/Observation, /api/patients
  - Last Event: 2025-07-16 10:20:15
• <code>172.18.0.6</code>: 5 events
  - Endpoints: /fhir/R5/Observation
  - Last Event: 2025-07-16 10:18:30
• <code>172.18.0.7</code>: 2 events
  - Endpoints: /api/devices
  - Last Event: 2025-07-16 10:15:45

<b>System Status:</b>
• MQTT Listeners: ✅ All Connected
• FHIR Processing: ✅ Active
• Rate Limiting: ✅ Configured
• Telegram Alerts: ✅ Working

<b>Generated:</b> {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"""
        
        # Send to Telegram
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML"
        }
        
        print(f"📤 Sending daily summary to Telegram...")
        
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        
        result = response.json()
        if result.get("ok"):
            print("✅ Daily summary sent successfully!")
            print(f"   Message ID: {result.get('result', {}).get('message_id')}")
            return True
        else:
            print(f"❌ Telegram API error: {result.get('description')}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Testing Rate Limit Telegram Integration")
    print("=" * 50)
    
    # Test 1: Send rate limit alert
    print("\n1. Testing Rate Limit Alert...")
    success1 = send_rate_limit_alert_to_telegram()
    
    # Test 2: Send daily summary
    print("\n2. Testing Daily Summary...")
    success2 = send_daily_summary_to_telegram()
    
    # Summary
    print("\n" + "=" * 50)
    print("📋 Test Results:")
    print(f"   Rate Limit Alert: {'✅ PASS' if success1 else '❌ FAIL'}")
    print(f"   Daily Summary: {'✅ PASS' if success2 else '❌ FAIL'}")
    
    if success1 and success2:
        print("\n🎉 All tests passed! Rate limit monitoring is working.")
    else:
        print("\n⚠️ Some tests failed. Check configuration and try again.") 