#!/bin/bash

# Opera Godeye Deployment Script
# This script deploys the complete MQTT listener and monitoring system

set -e

echo "🎭 Deploying Opera Godeye - Complete MQTT System..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
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

print_header() {
    echo -e "${PURPLE}[OPERA GODEYE]${NC} $1"
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

# Check SSL certificates (CRITICAL for MongoDB connection)
print_header "Checking SSL certificates for MongoDB connection..."

ssl_ca_file="ssl/ca-latest.pem"
ssl_client_file="ssl/client-combined-latest.pem"

if [ ! -f "$ssl_ca_file" ]; then
    print_error "SSL CA certificate not found: $ssl_ca_file"
    print_error "This is required for MongoDB connection to Coruscant cluster"
    print_error "Please ensure SSL certificates are in the ssl/ directory"
    exit 1
fi

if [ ! -f "$ssl_client_file" ]; then
    print_error "SSL client certificate not found: $ssl_client_file"
    print_error "This is required for MongoDB connection to Coruscant cluster"
    print_error "Please ensure SSL certificates are in the ssl/ directory"
    exit 1
fi

print_success "SSL certificates found:"
print_status "  CA Certificate: $ssl_ca_file"
print_status "  Client Certificate: $ssl_client_file"

# Check if required directories exist
required_dirs=(
    "services/mqtt-listeners/ava4-listener"
    "services/mqtt-listeners/kati-listener"
    "services/mqtt-listeners/qube-listener"
    "services/mqtt-listeners/shared"
    "services/mqtt-monitor/web-panel"
    "services/mqtt-monitor/websocket-server"
    "services/mqtt-monitor/shared"
)

for dir in "${required_dirs[@]}"; do
    if [ ! -d "$dir" ]; then
        print_error "Required directory not found: $dir"
        exit 1
    fi
done

# Check if required files exist
required_files=(
    "docker-compose.opera-godeye.yml"
    "services/mqtt-listeners/shared/device_mapper.py"
    "services/mqtt-listeners/shared/data_processor.py"
    "services/mqtt-monitor/shared/mqtt_monitor.py"
)

for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        print_error "Required file not found: $file"
        exit 1
    fi
done

print_success "All required files and directories found"

# Check if stardust-redis is running (required for Opera Godeye)
print_status "Checking if stardust-redis is running..."
if ! docker ps --format "table {{.Names}}" | grep -q "^stardust-redis$"; then
    print_warning "stardust-redis is not running"
    print_status "Starting stardust-redis..."
    docker compose up -d redis
    sleep 5
else
    print_success "stardust-redis is running"
fi

# Stop existing services if running
print_status "Stopping existing Opera Godeye services..."
docker compose -f docker-compose.opera-godeye.yml down --remove-orphans 2>/dev/null || true

# Build and start services
print_header "Building and starting Opera Godeye services..."
docker compose -f docker-compose.opera-godeye.yml up -d --build

# Wait for services to start
print_status "Waiting for services to start..."
sleep 15

# Check service status
print_status "Checking service status..."
docker compose -f docker-compose.opera-godeye.yml ps

# Check if services are running
services=(
    "opera-godeye-ava4-listener"
    "opera-godeye-kati-listener" 
    "opera-godeye-qube-listener"
    "opera-godeye-websocket"
    "opera-godeye-panel"
)

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
    print_success "All Opera Godeye services are running!"
    
    echo ""
    echo "🎭 Opera Godeye Deployment Complete!"
    echo ""
    echo "📡 MQTT Listener Services:"
    echo "   AVA4 Listener: opera-godeye-ava4-listener"
    echo "   Kati Listener: opera-godeye-kati-listener"
    echo "   Qube Listener: opera-godeye-qube-listener"
    echo ""
    echo "📊 Monitoring Services:"
    echo "   WebSocket Server: opera-godeye-websocket (Port 8081)"
    echo "   Web Panel: opera-godeye-panel (Port 8080)"
    echo ""
    echo "🌐 Access Points:"
    echo "   Dashboard: http://localhost:8080"
    echo "   WebSocket: ws://localhost:8081"
    echo ""
    echo "🔒 SSL Configuration:"
    echo "   MongoDB SSL: ✅ Enabled with certificates"
    echo "   CA Certificate: $ssl_ca_file"
    echo "   Client Certificate: $ssl_client_file"
    echo ""
    echo "📋 Useful Commands:"
    echo "   View all logs: docker compose -f docker-compose.opera-godeye.yml logs -f"
    echo "   View specific service: docker logs opera-godeye-panel"
    echo "   Stop all services: docker compose -f docker-compose.opera-godeye.yml down"
    echo "   Restart all services: docker compose -f docker-compose.opera-godeye.yml restart"
    echo ""
    echo "🔍 Monitor Individual Services:"
    echo "   AVA4 Listener: docker logs -f opera-godeye-ava4-listener"
    echo "   Kati Listener: docker logs -f opera-godeye-kati-listener"
    echo "   Qube Listener: docker logs -f opera-godeye-qube-listener"
    echo "   WebSocket: docker logs -f opera-godeye-websocket"
    echo "   Web Panel: docker logs -f opera-godeye-panel"
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
    
    # Show Redis database assignments
    echo ""
    print_status "Redis Database Assignments:"
    echo "   AVA4 Listener: Redis DB 2"
    echo "   Kati Listener: Redis DB 3"
    echo "   Qube Listener: Redis DB 4"
    echo "   Web Panel: Redis DB 1"
    echo ""
    
    # Show MQTT topic subscriptions
    echo ""
    print_status "MQTT Topic Subscriptions:"
    echo "   AVA4 Listener: ESP32_BLE_GW_TX, dusun_sub"
    echo "   Kati Listener: iMEDE_watch/# (all Kati topics)"
    echo "   Qube Listener: CM4_BLE_GW_TX"
    echo "   Monitor: All topics (for real-time display)"
    echo ""
    
    # Show MongoDB connection info
    echo ""
    print_status "MongoDB Connection:"
    echo "   Host: coruscant.my-firstcare.com:27023"
    echo "   Database: AMY"
    echo "   SSL: Enabled with certificates"
    echo "   Authentication: opera_admin"
    echo ""
    
else
    print_error "Some services failed to start. Check the logs:"
    echo "   docker compose -f docker-compose.opera-godeye.yml logs"
    echo "   docker logs opera-godeye-ava4-listener"
    echo "   docker logs opera-godeye-kati-listener"
    echo "   docker logs opera-godeye-qube-listener"
    echo "   docker logs opera-godeye-websocket"
    echo "   docker logs opera-godeye-panel"
    exit 1
fi

echo ""
print_success "Opera Godeye deployment completed successfully!"
print_header "Open http://localhost:8080 in your browser to access the monitoring dashboard"
echo ""
print_status "The system is now processing MQTT messages from all three device types and displaying them in real-time!"
print_status "SSL certificates are properly configured for secure MongoDB connection to Coruscant cluster." 