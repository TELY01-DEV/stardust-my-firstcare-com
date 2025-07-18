#!/usr/bin/env python3
"""
Test Telegram Alert Functionality
"""

import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_telegram_alert():
    """Test sending a Telegram alert"""
    
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    
    if not bot_token or not chat_id:
        print("❌ Telegram configuration not found in .env file")
        print("Please set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in your .env file")
        return False
    
    print(f"✅ Found Telegram configuration:")
    print(f"   Bot Token: {bot_token[:10]}...")
    print(f"   Chat ID: {chat_id}")
    
    # Test message
    message = "🧪 **Test Alert**\n\nThis is a test message from the Medical Data Monitor.\n\nIf you receive this, Telegram alerts are working correctly! 🎉"
    
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        data = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "Markdown"
        }
        
        print(f"\n📤 Sending test message...")
        response = requests.post(url, data=data, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('ok'):
                print("✅ Test message sent successfully!")
                print(f"   Message ID: {result['result']['message_id']}")
                return True
            else:
                print(f"❌ Telegram API error: {result.get('description', 'Unknown error')}")
                return False
        else:
            print(f"❌ HTTP error: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ Request timeout - check your internet connection")
        return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Request error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing Telegram Alert Configuration")
    print("=" * 50)
    
    success = test_telegram_alert()
    
    if success:
        print("\n🎉 Telegram alerts are ready to use!")
        print("You can now run the medical data monitor with alerts enabled.")
    else:
        print("\n⚠️ Please check your Telegram configuration:")
        print("1. Verify the bot token is correct")
        print("2. Make sure you've started a chat with your bot")
        print("3. Check that the chat ID is correct")
        print("4. Ensure the bot has permission to send messages") 