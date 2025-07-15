#!/bin/bash

# Emergency Dashboard Deployment Script
# MyFirstCare Emergency Response System

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DASHBOARD_PORT=5056
CONTAINER_NAME="opera-godeye-emergency-dashboard"
NETWORK_NAME="mqtt-network"

echo -e "${BLUE}🚨 Emergency Dashboard Deployment Script${NC}"
echo -e "${BLUE}==========================================${NC}"

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Check if Docker is running
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        print_error "Docker is not running. Please start Docker and try again."
        exit 1
    fi
    print_status "Docker is running"
}

# Check if required network exists
check_network() {
    if ! docker network ls | grep -q "$NETWORK_NAME"; then
        print_warning "Network '$NETWORK_NAME' not found. Creating..."
        docker network create "$NETWORK_NAME"
        print_status "Network '$NETWORK_NAME' created"
    else
        print_status "Network '$NETWORK_NAME' exists"
    fi
}

# Check if port is available
check_port() {
    if lsof -Pi :$DASHBOARD_PORT -sTCP:LISTEN -t >/dev/null ; then
        print_error "Port $DASHBOARD_PORT is already in use. Please stop the service using this port and try again."
        exit 1
    fi
    print_status "Port $DASHBOARD_PORT is available"
}

# Stop existing container if running
stop_existing() {
    if docker ps -q -f name="$CONTAINER_NAME" | grep -q .; then
        print_warning "Stopping existing emergency dashboard container..."
        docker stop "$CONTAINER_NAME"
        docker rm "$CONTAINER_NAME"
        print_status "Existing container stopped and removed"
    fi
}

# Build and start the service
deploy_service() {
    print_info "Building emergency dashboard..."
    docker-compose build --no-cache
    
    print_info "Starting emergency dashboard..."
    docker-compose up -d
    
    print_status "Emergency dashboard deployment completed"
}

# Wait for service to be ready
wait_for_service() {
    print_info "Waiting for emergency dashboard to be ready..."
    
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s http://localhost:$DASHBOARD_PORT/api/emergency-stats > /dev/null 2>&1; then
            print_status "Emergency dashboard is ready!"
            return 0
        fi
        
        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    print_error "Emergency dashboard failed to start within 60 seconds"
    return 1
}

# Show service status
show_status() {
    echo ""
    print_info "Emergency Dashboard Status:"
    echo "================================"
    
    if docker ps -q -f name="$CONTAINER_NAME" | grep -q .; then
        print_status "Container is running"
        echo "Container ID: $(docker ps -q -f name="$CONTAINER_NAME")"
        echo "Port: $DASHBOARD_PORT"
        echo "URL: http://localhost:$DASHBOARD_PORT"
    else
        print_error "Container is not running"
    fi
    
    echo ""
    print_info "Container logs (last 10 lines):"
    docker logs --tail 10 "$CONTAINER_NAME" 2>/dev/null || print_warning "No logs available"
}

# Test the service
test_service() {
    print_info "Testing emergency dashboard..."
    
    # Test basic connectivity
    if curl -s http://localhost:$DASHBOARD_PORT/api/emergency-stats > /dev/null 2>&1; then
        print_status "Dashboard API is responding"
    else
        print_error "Dashboard API is not responding"
        return 1
    fi
    
    # Test emergency alerts endpoint
    if curl -s http://localhost:$DASHBOARD_PORT/api/emergency-alerts > /dev/null 2>&1; then
        print_status "Emergency alerts endpoint is working"
    else
        print_error "Emergency alerts endpoint is not working"
        return 1
    fi
    
    print_status "All tests passed!"
    return 0
}

# Show usage information
show_usage() {
    echo ""
    print_info "Emergency Dashboard Usage:"
    echo "=============================="
    echo "URL: http://localhost:$DASHBOARD_PORT"
    echo ""
    echo "Available endpoints:"
    echo "  - /                    : Main dashboard"
    echo "  - /api/emergency-alerts: Get emergency alerts"
    echo "  - /api/emergency-stats : Get emergency statistics"
    echo "  - /api/patients        : Get patient list"
    echo ""
    echo "Management commands:"
    echo "  docker logs $CONTAINER_NAME     : View logs"
    echo "  docker stop $CONTAINER_NAME     : Stop service"
    echo "  docker start $CONTAINER_NAME    : Start service"
    echo "  docker restart $CONTAINER_NAME  : Restart service"
    echo ""
    print_info "For more information, see README.md"
}

# Main deployment function
main() {
    case "${1:-deploy}" in
        "deploy")
            check_docker
            check_network
            check_port
            stop_existing
            deploy_service
            wait_for_service
            test_service
            show_status
            show_usage
            ;;
        "stop")
            print_info "Stopping emergency dashboard..."
            docker-compose down
            print_status "Emergency dashboard stopped"
            ;;
        "restart")
            print_info "Restarting emergency dashboard..."
            docker-compose restart
            wait_for_service
            test_service
            show_status
            ;;
        "logs")
            docker logs -f "$CONTAINER_NAME"
            ;;
        "status")
            show_status
            ;;
        "test")
            test_service
            ;;
        "help")
            echo "Usage: $0 [deploy|stop|restart|logs|status|test|help]"
            echo ""
            echo "Commands:"
            echo "  deploy  : Deploy the emergency dashboard (default)"
            echo "  stop    : Stop the emergency dashboard"
            echo "  restart : Restart the emergency dashboard"
            echo "  logs    : Show container logs"
            echo "  status  : Show service status"
            echo "  test    : Test the service"
            echo "  help    : Show this help message"
            ;;
        *)
            print_error "Unknown command: $1"
            echo "Use '$0 help' for usage information"
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@" 