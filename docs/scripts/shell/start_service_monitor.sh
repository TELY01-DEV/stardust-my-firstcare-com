#!/bin/bash

# Service Monitor Startup Script with Telegram Alerts
# =================================================

echo "🚀 Starting Service Monitor with Telegram Alerts"
echo "================================================"

# Check if .env file exists
if [ -f ".env" ]; then
    echo "✅ Found .env file"
    export $(grep -v '^#' .env | xargs)
else
    echo "❌ .env file not found"
    exit 1
fi

# Check Telegram configuration
if [ -z "$TELEGRAM_BOT_TOKEN" ] || [ -z "$TELEGRAM_CHAT_ID" ]; then
    echo "❌ Telegram configuration missing in .env file"
    echo "   Please add:"
    echo "   TELEGRAM_BOT_TOKEN=your_bot_token"
    echo "   TELEGRAM_CHAT_ID=your_chat_id"
    exit 1
else
    echo "✅ Telegram alerts are configured"
    echo "   Bot Token: ${TELEGRAM_BOT_TOKEN:0:10}..."
    echo "   Chat ID: $TELEGRAM_CHAT_ID"
fi

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed or not in PATH"
    exit 1
fi

echo "🔍 Checking dependencies..."
cd services/mqtt-monitor

# Install Python dependencies
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

echo "📦 Installing dependencies..."
source venv/bin/activate
pip install -r requirements-service-monitor.txt

echo "🚀 Starting service monitor..."
echo "Press Ctrl+C to stop"
echo ""

# Run the service monitor
python3 service-monitor.py 