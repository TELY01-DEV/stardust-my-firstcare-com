#!/bin/bash

# Complete Data Flow Monitoring System
# Starts all monitoring components for the 5-step data flow

set -e

echo "🚀 Starting Complete Data Flow Monitoring System"
echo "================================================"
echo "📅 Started at: $(date)"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    local status=$1
    local message=$2
    case $status in
        "INFO")
            echo -e "${BLUE}ℹ️  $message${NC}"
            ;;
        "SUCCESS")
            echo -e "${GREEN}✅ $message${NC}"
            ;;
        "WARNING")
            echo -e "${YELLOW}⚠️  $message${NC}"
            ;;
        "ERROR")
            echo -e "${RED}❌ $message${NC}"
            ;;
        "STEP")
            echo -e "${PURPLE}🔍 $message${NC}"
            ;;
        "DASHBOARD")
            echo -e "${CYAN}📊 $message${NC}"
            ;;
    esac
}

# Function to check if containers are running
check_containers() {
    print_status "INFO" "Checking MQTT monitoring containers..."
    
    containers=(
        "opera-godeye-ava4-listener"
        "opera-godeye-kati-listener" 
        "opera-godeye-qube-listener"
        "opera-godeye-websocket"
        "opera-godeye-panel"
    )
    
    all_running=true
    for container in "${containers[@]}"; do
        if docker ps --format "table {{.Names}}" | grep -q "^$container$"; then
            print_status "SUCCESS" "Container $container is running"
        else
            print_status "ERROR" "Container $container is not running"
            all_running=false
        fi
    done
    
    if [ "$all_running" = false ]; then
        print_status "WARNING" "Some containers are not running. Starting them..."
        docker compose -f docker-compose.opera-godeye.yml up -d
        sleep 10
    fi
    
    echo ""
}

# Function to show the 5-step data flow
show_data_flow_steps() {
    print_status "STEP" "The Complete Data Flow Monitoring System tracks these 5 steps:"
    echo ""
    echo "📨 STEP 1: MQTT Payload Reception"
    echo "   - Raw JSON payload from medical devices"
    echo "   - Topic identification and device type detection"
    echo "   - Payload size and timestamp tracking"
    echo ""
    
    echo "🔧 STEP 2: Parser Processing"
    echo "   - JSON payload parsing and validation"
    echo "   - Device-specific data extraction"
    echo "   - Attribute mapping and data structure analysis"
    echo ""
    
    echo "👤 STEP 3: Patient Mapping"
    echo "   - Device identifier to patient lookup"
    echo "   - Database queries for patient identification"
    echo "   - Patient record retrieval and validation"
    echo ""
    
    echo "🔄 STEP 4: Data Transformation"
    echo "   - Raw device data to structured format conversion"
    echo "   - Field mapping and data normalization"
    echo "   - Medical data validation and formatting"
    echo ""
    
    echo "💾 STEP 5: Database Storage"
    echo "   - Patient collection updates (last data fields)"
    echo "   - Medical history collection inserts"
    echo "   - Transaction logging and error handling"
    echo ""
}

# Function to start Python monitoring
start_python_monitoring() {
    print_status "INFO" "Starting Python monitoring components..."
    
    # Check if virtual environment exists
    if [ ! -d "mqtt_monitor_env" ]; then
        print_status "WARNING" "Virtual environment not found. Creating..."
        python3 -m venv mqtt_monitor_env
        source mqtt_monitor_env/bin/activate
        pip install paho-mqtt
    fi
    
    # Start complete data flow monitor in background
    print_status "INFO" "Starting Complete Data Flow Monitor..."
    source mqtt_monitor_env/bin/activate
    python monitor_complete_data_flow.py > complete_flow_monitor.log 2>&1 &
    COMPLETE_FLOW_PID=$!
    
    print_status "SUCCESS" "Complete Data Flow Monitor started (PID: $COMPLETE_FLOW_PID)"
    print_status "INFO" "Log file: complete_flow_monitor.log"
    echo ""
}

# Function to show dashboard access
show_dashboard_access() {
    print_status "DASHBOARD" "Dashboard Access Information:"
    echo ""
    echo "🌐 Web Dashboard URLs:"
    echo "   📊 Main Dashboard: http://localhost:8098"
    echo "   🔄 Data Flow Monitor: http://localhost:8098/data-flow"
    echo ""
    echo "🔐 Login Credentials:"
    echo "   - Use your Stardust-V1 credentials"
    echo "   - JWT authentication required"
    echo ""
    echo "📱 WebSocket Connection:"
    echo "   - WebSocket Server: ws://localhost:8097"
    echo "   - Real-time data streaming"
    echo ""
}

# Function to show monitoring commands
show_monitoring_commands() {
    print_status "INFO" "Useful Monitoring Commands:"
    echo ""
    echo "📊 Check Container Logs:"
    echo "   docker logs opera-godeye-ava4-listener -f"
    echo "   docker logs opera-godeye-kati-listener -f"
    echo "   docker logs opera-godeye-qube-listener -f"
    echo "   docker logs opera-godeye-websocket -f"
    echo "   docker logs opera-godeye-panel -f"
    echo ""
    echo "📝 Check Python Monitor Logs:"
    echo "   tail -f complete_flow_monitor.log"
    echo ""
    echo "🔄 Restart Services:"
    echo "   docker compose -f docker-compose.opera-godeye.yml restart"
    echo ""
    echo "🛑 Stop Monitoring:"
    echo "   ./stop_monitoring.sh"
    echo ""
}

# Function to show real-time monitoring tips
show_monitoring_tips() {
    print_status "INFO" "Real-time Monitoring Tips:"
    echo ""
    echo "👀 What to Watch For:"
    echo "   ✅ Green indicators = Successful processing"
    echo "   ⚠️  Yellow indicators = Processing in progress"
    echo "   ❌ Red indicators = Errors or failures"
    echo ""
    echo "📈 Key Metrics:"
    echo "   - Message processing rate"
    echo "   - Patient mapping success rate"
    echo "   - Database operation success rate"
    echo "   - Device type distribution"
    echo ""
    echo "🔍 Debug Information:"
    echo "   - Raw MQTT payloads in logs"
    echo "   - Patient lookup queries"
    echo "   - Data transformation steps"
    echo "   - Database operation details"
    echo ""
}

# Function to create stop script
create_stop_script() {
    cat > stop_monitoring.sh << 'EOF'
#!/bin/bash

echo "🛑 Stopping Complete Data Flow Monitoring System..."

# Stop Python monitoring processes
echo "📝 Stopping Python monitors..."
pkill -f "monitor_complete_data_flow.py" 2>/dev/null || true
pkill -f "mqtt_realtime_monitor.py" 2>/dev/null || true

# Stop containers (optional - uncomment if you want to stop them)
# echo "🐳 Stopping containers..."
# docker compose -f docker-compose.opera-godeye.yml stop

echo "✅ Monitoring stopped successfully!"
echo "📊 Dashboards may still be accessible at http://localhost:8098"
EOF

    chmod +x stop_monitoring.sh
    print_status "SUCCESS" "Stop script created: ./stop_monitoring.sh"
    echo ""
}

# Main execution
main() {
    echo "🧪 Complete Data Flow Monitoring System"
    echo "======================================="
    echo ""
    
    # Check containers
    check_containers
    
    # Show data flow steps
    show_data_flow_steps
    
    # Start Python monitoring
    start_python_monitoring
    
    # Show dashboard access
    show_dashboard_access
    
    # Show monitoring commands
    show_monitoring_commands
    
    # Show monitoring tips
    show_monitoring_tips
    
    # Create stop script
    create_stop_script
    
    print_status "SUCCESS" "Complete Data Flow Monitoring System is now running!"
    echo ""
    print_status "INFO" "Access the dashboard at: http://localhost:8098"
    print_status "INFO" "Access data flow monitor at: http://localhost:8098/data-flow"
    echo ""
    print_status "INFO" "Press Ctrl+C to stop this script (monitoring will continue)"
    print_status "INFO" "Use './stop_monitoring.sh' to stop all monitoring"
    echo ""
    
    # Keep script running to show status
    while true; do
        sleep 30
        echo ""
        print_status "INFO" "Monitoring Status Check:"
        
        # Check if containers are still running
        for container in "opera-godeye-ava4-listener" "opera-godeye-kati-listener" "opera-godeye-qube-listener" "opera-godeye-websocket" "opera-godeye-panel"; do
            if docker ps --format "table {{.Names}}" | grep -q "^$container$"; then
                echo "  ✅ $container: Running"
            else
                echo "  ❌ $container: Stopped"
            fi
        done
        
        # Check if Python monitor is running
        if pgrep -f "monitor_complete_data_flow.py" > /dev/null; then
            echo "  ✅ Python Monitor: Running"
        else
            echo "  ❌ Python Monitor: Stopped"
        fi
        
        echo "  📊 Dashboard: http://localhost:8098"
        echo "  🔄 Data Flow: http://localhost:8098/data-flow"
    done
}

# Trap cleanup on exit
cleanup() {
    echo ""
    print_status "INFO" "Stopping monitoring script..."
    print_status "INFO" "Monitoring services will continue running"
    print_status "INFO" "Use './stop_monitoring.sh' to stop all monitoring"
    exit 0
}

trap cleanup SIGINT SIGTERM

# Run main function
main "$@" 