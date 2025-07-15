#!/bin/bash

# Comprehensive MQTT System Monitor
# Monitors real-time data upload from patients and verifies MQTT topic+payload capture

set -e

echo "🚀 Starting Comprehensive MQTT System Monitor"
echo "=============================================="
echo "📅 Monitor started at: $(date)"
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
        "VERIFY")
            echo -e "${PURPLE}🔍 $message${NC}"
            ;;
        "MONITOR")
            echo -e "${CYAN}📡 $message${NC}"
            ;;
    esac
}

# Function to check system prerequisites
check_prerequisites() {
    print_status "INFO" "Checking system prerequisites..."
    
    # Check if Docker is running
    if ! docker info >/dev/null 2>&1; then
        print_status "ERROR" "Docker is not running"
        exit 1
    fi
    
    # Check if MQTT listener containers exist
    containers=("ava4-mqtt-listener" "kati-mqtt-listener" "qube-mqtt-listener")
    for container in "${containers[@]}"; do
        if ! docker ps -a --format "table {{.Names}}" | grep -q "^$container$"; then
            print_status "WARNING" "Container $container not found"
        fi
    done
    
    # Check Python dependencies
    if ! python3 -c "import paho.mqtt.client" 2>/dev/null; then
        print_status "WARNING" "paho-mqtt library not installed. Installing..."
        pip3 install paho-mqtt
    fi
    
    print_status "SUCCESS" "Prerequisites check completed"
    echo ""
}

# Function to check MQTT listener status
check_mqtt_listeners() {
    print_status "INFO" "Checking MQTT listener status..."
    
    containers=("ava4-mqtt-listener" "kati-mqtt-listener" "qube-mqtt-listener")
    
    for container in "${containers[@]}"; do
        if docker ps --format "table {{.Names}}" | grep -q "^$container$"; then
            print_status "SUCCESS" "Container $container is running"
            
            # Check recent logs for connection status
            if docker logs $container --tail 10 2>&1 | grep -q "Connected to MQTT broker successfully"; then
                print_status "SUCCESS" "  ✅ MQTT connection established"
            else
                print_status "WARNING" "  ⚠️  MQTT connection not found in recent logs"
            fi
            
            # Check for recent activity
            recent_logs=$(docker logs $container --tail 20 2>&1 | grep -E "(Processing|Received|Successfully)" | wc -l)
            print_status "INFO" "  📊 Recent activity: $recent_logs messages in last 20 logs"
            
        else
            print_status "ERROR" "Container $container is not running"
        fi
    done
    echo ""
}

# Function to enable debug logging
enable_debug_logging() {
    print_status "INFO" "Enabling debug logging for MQTT listeners..."
    
    # Set debug log level
    export LOG_LEVEL=DEBUG
    
    # Restart containers with debug logging
    containers=("ava4-mqtt-listener" "kati-mqtt-listener" "qube-mqtt-listener")
    
    for container in "${containers[@]}"; do
        if docker ps --format "table {{.Names}}" | grep -q "^$container$"; then
            print_status "INFO" "Restarting $container with debug logging..."
            docker compose -f docker-compose.mqtt.yml restart $container
        fi
    done
    
    # Wait for containers to start
    sleep 10
    
    print_status "SUCCESS" "Debug logging enabled"
    echo ""
}

# Function to start real-time MQTT monitoring
start_realtime_monitoring() {
    print_status "MONITOR" "Starting real-time MQTT monitoring..."
    
    # Check if monitoring script exists
    if [ ! -f "mqtt_realtime_monitor.py" ]; then
        print_status "ERROR" "Real-time monitoring script not found"
        return 1
    fi
    
    # Start monitoring in background
    print_status "INFO" "Starting real-time monitor in background..."
    python3 mqtt_realtime_monitor.py > mqtt_realtime_monitor.log 2>&1 &
    MONITOR_PID=$!
    
    print_status "SUCCESS" "Real-time monitoring started (PID: $MONITOR_PID)"
    print_status "INFO" "Monitor logs: mqtt_realtime_monitor.log"
    echo ""
}

# Function to run MQTT capture verification
run_capture_verification() {
    print_status "VERIFY" "Running MQTT capture verification..."
    
    # Check if verification script exists
    if [ ! -f "verify_mqtt_capture.py" ]; then
        print_status "ERROR" "Verification script not found"
        return 1
    fi
    
    # Run verification for 3 minutes
    print_status "INFO" "Running verification for 3 minutes..."
    timeout 180s python3 verify_mqtt_capture.py > mqtt_verification.log 2>&1
    
    if [ $? -eq 124 ]; then
        print_status "SUCCESS" "Verification completed (timeout reached)"
    else
        print_status "SUCCESS" "Verification completed"
    fi
    
    print_status "INFO" "Verification logs: mqtt_verification.log"
    echo ""
}

# Function to monitor database storage
monitor_database_storage() {
    print_status "INFO" "Monitoring database storage..."
    
    # Check recent database activity
    print_status "INFO" "Checking recent database activity..."
    
    # Try to connect to MongoDB and check recent data
    if docker ps --format "table {{.Names}}" | grep -q "mongodb"; then
        print_status "INFO" "Checking recent blood pressure records..."
        docker exec -it mongodb mongosh --eval "
            use AMY;
            print('📊 Recent blood pressure records:');
            db.blood_pressure_histories.find().sort({timestamp: -1}).limit(3).forEach(function(doc) {
                print('  - Patient: ' + doc.patient_id + ', Source: ' + doc.source + ', Time: ' + doc.timestamp);
            });
            
            print('\\n📊 Recent patient updates:');
            db.patients.find({last_blood_pressure: {\$exists: true}}).sort({updated_at: -1}).limit(3).forEach(function(doc) {
                print('  - Patient: ' + doc._id + ', Updated: ' + doc.updated_at);
            });
        " 2>/dev/null || print_status "WARNING" "Could not connect to MongoDB"
    else
        print_status "WARNING" "MongoDB container not found"
    fi
    
    echo ""
}

# Function to display real-time statistics
display_realtime_stats() {
    print_status "INFO" "Displaying real-time statistics..."
    
    # Check monitoring log for statistics
    if [ -f "mqtt_realtime_monitor.log" ]; then
        print_status "INFO" "Recent monitoring activity:"
        tail -20 mqtt_realtime_monitor.log | grep -E "(STATISTICS|MESSAGE|TOPIC)" || echo "No recent activity found"
    fi
    
    # Check verification results
    if [ -f "mqtt_verification.log" ]; then
        print_status "INFO" "Verification results:"
        tail -10 mqtt_verification.log | grep -E "(VERIFICATION|Status|PASS|FAIL)" || echo "No verification results found"
    fi
    
    echo ""
}

# Function to check MQTT topic coverage
check_topic_coverage() {
    print_status "VERIFY" "Checking MQTT topic coverage..."
    
    # Expected topics
    expected_topics=(
        "ESP32_BLE_GW_TX"      # AVA4 status
        "dusun_sub"            # AVA4 medical data
        "iMEDE_watch/VitalSign" # Kati vital signs
        "iMEDE_watch/AP55"     # Kati batch data
        "iMEDE_watch/hb"       # Kati heartbeat
        "iMEDE_watch/location" # Kati location
        "iMEDE_watch/sleepdata" # Kati sleep
        "iMEDE_watch/sos"      # Kati emergency
        "iMEDE_watch/fallDown" # Kati fall detection
        "iMEDE_watch/onlineTrigger" # Kati online status
        "CM4_BLE_GW_TX"        # Qube-Vital data
    )
    
    print_status "INFO" "Expected MQTT topics:"
    for topic in "${expected_topics[@]}"; do
        print_status "INFO" "  📡 $topic"
    done
    
    echo ""
}

# Function to analyze payload structures
analyze_payload_structures() {
    print_status "VERIFY" "Analyzing payload structures..."
    
    # Check for captured messages in verification log
    if [ -f "mqtt_verification.log" ]; then
        print_status "INFO" "Payload structure analysis from verification:"
        
        # Extract sample payloads
        echo "📊 Sample payloads found:"
        grep -A 10 -B 2 "sample_messages" mqtt_verification.log || echo "No sample messages found"
        
        # Extract field verification results
        echo ""
        echo "📝 Field verification results:"
        grep -A 5 "Field verification" mqtt_verification.log || echo "No field verification results found"
    fi
    
    echo ""
}

# Function to generate monitoring report
generate_monitoring_report() {
    print_status "INFO" "Generating monitoring report..."
    
    report_file="mqtt_monitoring_report_$(date +%Y%m%d_%H%M%S).txt"
    
    {
        echo "MQTT System Monitoring Report"
        echo "Generated: $(date)"
        echo "=================================="
        echo ""
        
        echo "System Status:"
        docker ps --format "table {{.Names}}\t{{.Status}}" | grep mqtt-listener || echo "No MQTT listeners found"
        echo ""
        
        echo "Container Logs Summary:"
        for container in "ava4-mqtt-listener" "kati-mqtt-listener" "qube-mqtt-listener"; do
            echo "=== $container ==="
            docker logs $container --tail 10 2>&1 || echo "Container not found"
            echo ""
        done
        
        echo "Real-time Monitor Log:"
        if [ -f "mqtt_realtime_monitor.log" ]; then
            tail -20 mqtt_realtime_monitor.log
        else
            echo "No real-time monitor log found"
        fi
        echo ""
        
        echo "Verification Results:"
        if [ -f "mqtt_verification.log" ]; then
            tail -30 mqtt_verification.log
        else
            echo "No verification log found"
        fi
        
    } > "$report_file"
    
    print_status "SUCCESS" "Monitoring report generated: $report_file"
    echo ""
}

# Function to cleanup monitoring processes
cleanup_monitoring() {
    print_status "INFO" "Cleaning up monitoring processes..."
    
    # Stop real-time monitoring if running
    if [ ! -z "$MONITOR_PID" ]; then
        print_status "INFO" "Stopping real-time monitor (PID: $MONITOR_PID)..."
        kill $MONITOR_PID 2>/dev/null || true
    fi
    
    # Kill any remaining Python monitoring processes
    pkill -f "mqtt_realtime_monitor.py" 2>/dev/null || true
    pkill -f "verify_mqtt_capture.py" 2>/dev/null || true
    
    print_status "SUCCESS" "Cleanup completed"
    echo ""
}

# Function to show help
show_help() {
    echo "Usage: $0 [OPTION]"
    echo ""
    echo "Options:"
    echo "  --check-only      Only check system status"
    echo "  --monitor-only    Only run real-time monitoring"
    echo "  --verify-only     Only run capture verification"
    echo "  --full-monitor    Run complete monitoring (default)"
    echo "  --help           Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 --check-only     # Quick system check"
    echo "  $0 --monitor-only   # Real-time monitoring only"
    echo "  $0 --verify-only    # Verification only"
    echo "  $0 --full-monitor   # Complete monitoring"
}

# Main monitoring function
main_monitoring() {
    echo "🧪 Comprehensive MQTT System Monitor"
    echo "===================================="
    echo ""
    
    # Parse command line arguments
    case "${1:---full-monitor}" in
        --check-only)
            print_status "INFO" "Running system check only..."
            check_prerequisites
            check_mqtt_listeners
            check_topic_coverage
            ;;
        --monitor-only)
            print_status "INFO" "Running real-time monitoring only..."
            check_prerequisites
            enable_debug_logging
            start_realtime_monitoring
            echo "Press Ctrl+C to stop monitoring..."
            wait
            ;;
        --verify-only)
            print_status "INFO" "Running verification only..."
            check_prerequisites
            run_capture_verification
            analyze_payload_structures
            ;;
        --full-monitor)
            print_status "INFO" "Running complete monitoring..."
            check_prerequisites
            check_mqtt_listeners
            check_topic_coverage
            enable_debug_logging
            start_realtime_monitoring
            run_capture_verification
            monitor_database_storage
            display_realtime_stats
            analyze_payload_structures
            generate_monitoring_report
            ;;
        --help)
            show_help
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
    
    print_status "SUCCESS" "Monitoring completed!"
    echo ""
    print_status "INFO" "Check the generated reports for detailed results"
    print_status "INFO" "Monitor logs with: tail -f mqtt_realtime_monitor.log"
}

# Trap cleanup on exit
trap cleanup_monitoring EXIT

# Run main monitoring
main_monitoring "$@" 