#!/bin/bash

echo "🚀 Starting Medical Data Monitor with Telegram Alerts"
echo "=================================================="

# Check if .env file exists and load Telegram configuration
if [ -f ".env" ]; then
    echo "✅ Found .env file"
    
    # Source the .env file to get environment variables
    export $(grep -v '^#' .env | xargs)
    
    # Check if Telegram environment variables are set
    if [ -n "$TELEGRAM_BOT_TOKEN" ] && [ -n "$TELEGRAM_CHAT_ID" ]; then
        echo "✅ Telegram alerts are configured"
        echo "   Bot Token: ${TELEGRAM_BOT_TOKEN:0:10}..."
        echo "   Chat ID: $TELEGRAM_CHAT_ID"
        echo ""
    else
        echo "⚠️  Telegram alerts are not configured in .env file"
        echo ""
        echo "To enable Telegram alerts, add these lines to your .env file:"
        echo "TELEGRAM_BOT_TOKEN='your_bot_token_here'"
        echo "TELEGRAM_CHAT_ID='your_chat_id_here'"
        echo ""
        echo "To get these values:"
        echo "1. Create a bot with @BotFather on Telegram"
        echo "2. Get the bot token from BotFather"
        echo "3. Start a chat with your bot"
        echo "4. Get your chat ID by sending a message to @userinfobot"
        echo ""
        echo "Continuing without Telegram alerts..."
        echo ""
    fi
else
    echo "⚠️  No .env file found"
    echo ""
    echo "To enable Telegram alerts, create a .env file with:"
    echo "TELEGRAM_BOT_TOKEN='your_bot_token_here'"
    echo "TELEGRAM_CHAT_ID='your_chat_id_here'"
    echo ""
    echo "Continuing without Telegram alerts..."
    echo ""
fi

# Set default failure alert settings if not provided
export FAILURE_ALERT_THRESHOLD=${FAILURE_ALERT_THRESHOLD:-5}
export FAILURE_WINDOW_MINUTES=${FAILURE_WINDOW_MINUTES:-10}

echo "🚨 Failure Alert Settings:"
echo "   Threshold: $FAILURE_ALERT_THRESHOLD failures"
echo "   Window: $FAILURE_WINDOW_MINUTES minutes"
echo ""

# Check if Python and required packages are available
echo "🔍 Checking dependencies..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 is not installed"
    exit 1
fi

# Check for required Python packages
python3 -c "import paho.mqtt.client, requests, dotenv" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ Required Python packages are missing"
    echo "Installing required packages..."
    pip3 install paho-mqtt requests python-dotenv
fi

echo "✅ Dependencies check passed"
echo ""

# Start the monitor
echo "🚀 Starting monitor..."
echo "Press Ctrl+C to stop"
echo ""

python3 monitor_complete_data_flow.py 