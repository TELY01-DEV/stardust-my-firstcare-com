#!/bin/bash

echo "🐳 Starting Medical Data Monitor as Docker Service"
echo "=================================================="

# Check if .env file exists
if [ -f ".env" ]; then
    echo "✅ Found .env file"
    
    # Check if Telegram configuration exists
    if grep -q "TELEGRAM_BOT_TOKEN" .env && grep -q "TELEGRAM_CHAT_ID" .env; then
        echo "✅ Telegram alerts are configured"
        echo "   Bot Token: $(grep TELEGRAM_BOT_TOKEN .env | cut -d'=' -f2 | cut -c1-10)..."
        echo "   Chat ID: $(grep TELEGRAM_CHAT_ID .env | cut -d'=' -f2)"
        echo ""
    else
        echo "⚠️  Telegram alerts are not configured in .env file"
        echo "   The monitor will run without Telegram alerts"
        echo ""
    fi
else
    echo "⚠️  No .env file found"
    echo "   The monitor will run without Telegram alerts"
    echo ""
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

echo "🔍 Checking Docker Compose configuration..."
if ! docker-compose config > /dev/null 2>&1; then
    echo "❌ Docker Compose configuration is invalid"
    exit 1
fi
echo "✅ Docker Compose configuration is valid"

echo ""
echo "🚀 Starting Medical Data Monitor service..."
echo ""

# Start only the medical monitor service
docker-compose up -d Opera-GodEye-Medical-Data-Monitor

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Medical Data Monitor service started successfully!"
    echo ""
    echo "📊 Monitor Information:"
    echo "   Container: stardust-opera-godeye-medical-data-monitor"
    echo "   Health Check: http://localhost:8099/health"
    echo "   Statistics: http://localhost:8099/stats"
    echo "   Logs: docker logs stardust-opera-godeye-medical-data-monitor"
    echo ""
    echo "🔍 To view logs:"
    echo "   docker logs -f stardust-opera-godeye-medical-data-monitor"
    echo ""
    echo "🛑 To stop the service:"
    echo "   docker-compose stop Opera-GodEye-Medical-Data-Monitor"
    echo ""
    echo "🔄 To restart the service:"
    echo "   docker-compose restart Opera-GodEye-Medical-Data-Monitor"
    echo ""
    
    # Show initial logs
    echo "📋 Initial logs (last 10 lines):"
    echo "----------------------------------------"
    docker logs --tail 10 stardust-opera-godeye-medical-data-monitor 2>/dev/null || echo "No logs available yet"
    echo "----------------------------------------"
    
else
    echo "❌ Failed to start Medical Data Monitor service"
    echo ""
    echo "🔍 Troubleshooting:"
    echo "   1. Check if all required services are running:"
    echo "      docker-compose ps"
    echo "   2. Check the logs:"
    echo "      docker-compose logs Opera-GodEye-Medical-Data-Monitor"
    echo "   3. Rebuild the service:"
    echo "      docker-compose build Opera-GodEye-Medical-Data-Monitor"
    echo "      docker-compose up -d Opera-GodEye-Medical-Data-Monitor"
    exit 1
fi 