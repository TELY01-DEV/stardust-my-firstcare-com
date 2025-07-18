#!/usr/bin/env python3
import os
import requests
from datetime import datetime

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

def test_telegram_alert():
    """Test sending a Telegram alert"""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not token or not chat_id:
        print("❌ Telegram bot token or chat ID not configured in .env file")
        return False
    
    try:
        message = f"""🚨 <b>Test Alert</b>
Level: <b>CRITICAL</b>
Source: <b>test_system</b>
Time: <b>{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}</b>

This is a test alert from the My FirstCare Opera Panel system.

Alert: Test Alert
Message: This is a test alert from the system.
Timestamp: {datetime.utcnow().isoformat()}"""
        
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML"
        }
        
        print(f"📤 Sending test alert to Telegram...")
        print(f"   Bot Token: {token[:10]}...")
        print(f"   Chat ID: {chat_id}")
        
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        
        result = response.json()
        if result.get("ok"):
            print("✅ Telegram alert sent successfully!")
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
    print("🧪 Testing Telegram Alert System")
    print("=" * 40)
    success = test_telegram_alert()
    print("=" * 40)
    if success:
        print("🎉 Test completed successfully!")
    else:
        print("💥 Test failed!") 