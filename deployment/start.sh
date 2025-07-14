#!/bin/bash

# My FirstCare Opera Panel Startup Script

echo "🚀 Starting My FirstCare Opera Panel..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Check if SSL certificates exist
if [ ! -f "ssl/ca-latest.pem" ] || [ ! -f "ssl/client-combined-latest.pem" ]; then
    echo "⚠️  SSL certificates not found in ssl/ directory."
    echo "Please ensure the following files exist:"
    echo "  - ssl/ca-latest.pem"
    echo "  - ssl/client-combined-latest.pem"
    echo ""
    echo "Continuing without SSL certificates (may cause connection issues)..."
fi

# Create logs directory if it doesn't exist
mkdir -p logs

# Build and start the application
echo "📦 Building and starting containers..."
docker-compose up -d --build

# Wait for the application to start
echo "⏳ Waiting for application to start..."
sleep 10

# Check if the application is running
echo "🔍 Checking application status..."
if curl -f http://localhost:5055/health > /dev/null 2>&1; then
    echo "✅ Application is running successfully!"
    echo ""
    echo "📊 Application Information:"
    echo "  - URL: http://localhost:5055"
    echo "  - Health Check: http://localhost:5055/health"
    echo "  - API Documentation: http://localhost:5055/docs"
    echo "  - Admin Panel: http://localhost:5055/admin"
    echo ""
    echo "📝 Logs:"
    echo "  - View logs: docker-compose logs -f opera-panel"
    echo "  - Stop application: docker-compose down"
    echo ""
    echo "🎉 My FirstCare Opera Panel is ready!"
else
    echo "❌ Application failed to start. Check logs with:"
    echo "   docker-compose logs opera-panel"
    exit 1
fi 