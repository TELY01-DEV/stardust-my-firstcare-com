#!/bin/bash

# MQTT Monitor Panel Deployment Script
# This script deploys the real-time MQTT monitoring dashboard

set -e

echo "🚀 Deploying MQTT Monitor Panel..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if docker-compose is available
if ! command -v docker compose &> /dev/null; then
    print_error "docker compose is not installed. Please install it and try again."
    exit 1
fi

# Navigate to project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

print_status "Current directory: $(pwd)"

# Check if MQTT monitor directory exists
if [ ! -d "services/mqtt-monitor" ]; then
    print_error "MQTT monitor directory not found. Please ensure the project structure is correct."
    exit 1
fi

# Check if required files exist
required_files=(
    "services/mqtt-monitor/docker-compose.yml"
    "services/mqtt-monitor/shared/mqtt_monitor.py"
    "services/mqtt-monitor/web-panel/app.py"
    "services/mqtt-monitor/websocket-server/main.py"
)

for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        print_error "Required file not found: $file"
        exit 1
    fi
done

print_success "All required files found"

# Stop existing services if running
print_status "Stopping existing MQTT monitor services..."
docker compose -f services/mqtt-monitor/docker-compose.yml down --remove-orphans 2>/dev/null || true

# Build and start services
print_status "Building and starting MQTT monitor services..."
docker compose -f services/mqtt-monitor/docker-compose.yml up -d --build

# Wait for services to start
print_status "Waiting for services to start..."
sleep 10

# Check service status
print_status "Checking service status..."
docker compose -f services/mqtt-monitor/docker-compose.yml ps

# Check if services are running
services=("mqtt-monitor-panel" "mqtt-monitor-websocket")
all_running=true

for service in "${services[@]}"; do
    if docker ps --format "table {{.Names}}" | grep -q "^$service$"; then
        print_success "$service is running"
    else
        print_error "$service is not running"
        all_running=false
    fi
done

if [ "$all_running" = true ]; then
    print_success "All MQTT monitor services are running!"
    
    echo ""
    echo "🎉 MQTT Monitor Panel Deployment Complete!"
    echo ""
    echo "📊 Access the dashboard:"
    echo "   Web Panel: http://localhost:8080"
    echo "   WebSocket: ws://localhost:8081"
    echo ""
    echo "📋 Useful commands:"
    echo "   View logs: docker logs mqtt-monitor-panel"
    echo "   View WebSocket logs: docker logs mqtt-monitor-websocket"
    echo "   Stop services: docker compose -f services/mqtt-monitor/docker-compose.yml down"
    echo "   Restart services: docker compose -f services/mqtt-monitor/docker-compose.yml restart"
    echo ""
    echo "🔍 Monitor real-time:"
    echo "   docker logs -f mqtt-monitor-websocket"
    echo ""
    
    # Check if services are healthy
    print_status "Checking service health..."
    
    # Check WebSocket server
    if curl -s http://localhost:8081 > /dev/null 2>&1; then
        print_success "WebSocket server is responding"
    else
        print_warning "WebSocket server may not be ready yet (this is normal during startup)"
    fi
    
    # Check web panel
    if curl -s http://localhost:8080 > /dev/null 2>&1; then
        print_success "Web panel is responding"
    else
        print_warning "Web panel may not be ready yet (this is normal during startup)"
    fi
    
else
    print_error "Some services failed to start. Check the logs:"
    echo "   docker logs mqtt-monitor-panel"
    echo "   docker logs mqtt-monitor-websocket"
    exit 1
fi

echo ""
print_success "MQTT Monitor Panel deployment completed successfully!"
print_status "Open http://localhost:8080 in your browser to access the dashboard" 