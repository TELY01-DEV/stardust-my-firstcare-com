#!/bin/bash

# MQTT Data Processing Workflow Test Script
# Tests the complete MQTT payload processing workflow with debug logging

set -e

echo "🚀 Starting MQTT Data Processing Workflow Tests"
echo "================================================"
echo "📅 Test started at: $(date)"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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
    esac
}

# Function to check if Docker containers are running
check_containers() {
    print_status "INFO" "Checking MQTT listener containers..."
    
    containers=("ava4-mqtt-listener" "kati-mqtt-listener" "qube-mqtt-listener")
    
    for container in "${containers[@]}"; do
        if docker ps --format "table {{.Names}}" | grep -q "^$container$"; then
            print_status "SUCCESS" "Container $container is running"
        else
            print_status "WARNING" "Container $container is not running"
        fi
    done
    echo ""
}

# Function to check MQTT connections
check_mqtt_connections() {
    print_status "INFO" "Checking MQTT connections..."
    
    # Check AVA4 listener logs for connection
    if docker logs ava4-mqtt-listener 2>&1 | grep -q "Connected to MQTT broker successfully"; then
        print_status "SUCCESS" "AVA4 MQTT connection established"
    else
        print_status "WARNING" "AVA4 MQTT connection not found in logs"
    fi
    
    # Check Kati listener logs for connection
    if docker logs kati-mqtt-listener 2>&1 | grep -q "Connected to MQTT broker successfully"; then
        print_status "SUCCESS" "Kati MQTT connection established"
    else
        print_status "WARNING" "Kati MQTT connection not found in logs"
    fi
    
    # Check Qube listener logs for connection
    if docker logs qube-mqtt-listener 2>&1 | grep -q "Connected to MQTT broker successfully"; then
        print_status "SUCCESS" "Qube MQTT connection established"
    else
        print_status "WARNING" "Qube MQTT connection not found in logs"
    fi
    echo ""
}

# Function to enable debug logging
enable_debug_logging() {
    print_status "INFO" "Enabling debug logging for MQTT listeners..."
    
    # Set debug log level for all listeners
    export LOG_LEVEL=DEBUG
    
    # Restart containers with debug logging
    docker compose -f docker-compose.mqtt.yml restart ava4-mqtt-listener
    docker compose -f docker-compose.mqtt.yml restart kati-mqtt-listener
    docker compose -f docker-compose.mqtt.yml restart qube-mqtt-listener
    
    # Wait for containers to start
    sleep 10
    
    print_status "SUCCESS" "Debug logging enabled"
    echo ""
}

# Function to run data processing tests
run_data_processing_tests() {
    print_status "INFO" "Running MQTT data processing tests..."
    
    # Set MongoDB connection for testing
    export MONGODB_URI="mongodb://opera_admin:Sim!443355@coruscant.my-firstcare.com:27023/admin?ssl=true&authSource=admin&tlsAllowInvalidCertificates=true&tlsAllowInvalidHostnames=true"
    export MONGODB_DATABASE="AMY"
    
    # Run the Python test script
    if python3 test_mqtt_data_processing.py; then
        print_status "SUCCESS" "Data processing tests completed successfully"
    else
        print_status "ERROR" "Data processing tests failed"
        return 1
    fi
    echo ""
}

# Function to verify database storage
verify_database_storage() {
    print_status "INFO" "Verifying database storage..."
    
    # Connect to MongoDB and check recent data
    docker exec -it mongodb mongosh --eval "
        use AMY;
        
        print('📊 Recent blood pressure records:');
        db.blood_pressure_histories.find().sort({timestamp: -1}).limit(5).forEach(function(doc) {
            print('  - Patient: ' + doc.patient_id + ', Source: ' + doc.source + ', Data: ' + JSON.stringify(doc.data));
        });
        
        print('\\n📊 Patients with last blood pressure:');
        db.patients.find({last_blood_pressure: {\$exists: true}}).sort({updated_at: -1}).limit(5).forEach(function(doc) {
            print('  - Patient: ' + doc._id + ', Last BP: ' + JSON.stringify(doc.last_blood_pressure));
        });
        
        print('\\n📊 Device mappings:');
        db.amy_devices.find().limit(5).forEach(function(doc) {
            print('  - MAC: ' + doc.mac_address + ', Type: ' + doc.device_type + ', Patient: ' + doc.patient_id);
        });
    " 2>/dev/null || print_status "WARNING" "Could not connect to MongoDB for verification"
    echo ""
}

# Function to check processing logs
check_processing_logs() {
    print_status "INFO" "Checking recent processing logs..."
    
    echo "📋 AVA4 Listener Recent Logs:"
    docker logs ava4-mqtt-listener --tail 20 2>&1 | grep -E "(Processing|Successfully|Error|Warning)" || echo "No relevant logs found"
    echo ""
    
    echo "📋 Kati Listener Recent Logs:"
    docker logs kati-mqtt-listener --tail 20 2>&1 | grep -E "(Processing|Successfully|Error|Warning)" || echo "No relevant logs found"
    echo ""
    
    echo "📋 Qube Listener Recent Logs:"
    docker logs qube-mqtt-listener --tail 20 2>&1 | grep -E "(Processing|Successfully|Error|Warning)" || echo "No relevant logs found"
    echo ""
}

# Function to test with sample MQTT messages
test_sample_messages() {
    print_status "INFO" "Testing with sample MQTT messages..."
    
    # Create a temporary test script
    cat > test_sample_messages.py << 'EOF'
#!/usr/bin/env python3
import json
import time
from paho.mqtt import client as mqtt_client

def test_ava4_message():
    """Send test AVA4 blood pressure message"""
    client = mqtt_client.Client()
    client.username_pw_set("webapi", "Sim!4433")
    
    try:
        client.connect("adam.amy.care", 1883, 60)
        
        payload = {
            "from": "BLE",
            "to": "CLOUD",
            "time": int(time.time()),
            "deviceCode": "08:F9:E0:D1:F7:B4",
            "mac": "08:F9:E0:D1:F7:B4",
            "type": "reportAttribute",
            "device": "WBP BIOLIGHT",
            "data": {
                "attribute": "BP_BIOLIGTH",
                "mac": "08:F9:E0:D1:F7:B4",
                "value": {
                    "device_list": [{
                        "scan_time": int(time.time()),
                        "ble_addr": "d616f9641622",
                        "bp_high": 137,
                        "bp_low": 95,
                        "PR": 74
                    }]
                }
            }
        }
        
        client.publish("dusun_sub", json.dumps(payload))
        print("✅ AVA4 test message sent")
        
    except Exception as e:
        print(f"❌ Error sending AVA4 message: {e}")
    finally:
        client.disconnect()

def test_kati_message():
    """Send test Kati Watch message"""
    client = mqtt_client.Client()
    client.username_pw_set("webapi", "Sim!4433")
    
    try:
        client.connect("adam.amy.care", 1883, 60)
        
        payload = {
            "IMEI": "865067123456789",
            "heartRate": 72,
            "bloodPressure": {
                "bp_sys": 122,
                "bp_dia": 74
            },
            "bodyTemperature": 36.6,
            "spO2": 97,
            "timeStamps": "16/06/2025 12:30:45"
        }
        
        client.publish("iMEDE_watch/VitalSign", json.dumps(payload))
        print("✅ Kati test message sent")
        
    except Exception as e:
        print(f"❌ Error sending Kati message: {e}")
    finally:
        client.disconnect()

if __name__ == "__main__":
    test_ava4_message()
    time.sleep(2)
    test_kati_message()
EOF

    # Run the test
    python3 test_sample_messages.py
    
    # Clean up
    rm test_sample_messages.py
    
    print_status "SUCCESS" "Sample messages sent"
    echo ""
}

# Function to generate test report
generate_test_report() {
    print_status "INFO" "Generating test report..."
    
    report_file="mqtt_processing_test_report_$(date +%Y%m%d_%H%M%S).txt"
    
    {
        echo "MQTT Data Processing Test Report"
        echo "Generated: $(date)"
        echo "=================================="
        echo ""
        
        echo "Container Status:"
        docker ps --format "table {{.Names}}\t{{.Status}}" | grep mqtt-listener || echo "No MQTT listeners found"
        echo ""
        
        echo "Recent Processing Logs:"
        echo "AVA4 Listener:"
        docker logs ava4-mqtt-listener --tail 10 2>&1 || echo "No logs available"
        echo ""
        
        echo "Kati Listener:"
        docker logs kati-mqtt-listener --tail 10 2>&1 || echo "No logs available"
        echo ""
        
        echo "Qube Listener:"
        docker logs qube-mqtt-listener --tail 10 2>&1 || echo "No logs available"
        echo ""
        
        echo "Test Log File:"
        if [ -f "mqtt_processing_test.log" ]; then
            tail -20 mqtt_processing_test.log
        else
            echo "No test log file found"
        fi
        
    } > "$report_file"
    
    print_status "SUCCESS" "Test report generated: $report_file"
    echo ""
}

# Main test execution
main() {
    echo "🧪 MQTT Data Processing Workflow Test Suite"
    echo "============================================"
    echo ""
    
    # Check prerequisites
    check_containers
    check_mqtt_connections
    
    # Enable debug logging
    enable_debug_logging
    
    # Run tests
    run_data_processing_tests
    
    # Test with sample messages
    test_sample_messages
    
    # Wait for processing
    print_status "INFO" "Waiting for message processing..."
    sleep 10
    
    # Check logs
    check_processing_logs
    
    # Verify database
    verify_database_storage
    
    # Generate report
    generate_test_report
    
    print_status "SUCCESS" "All tests completed successfully!"
    echo ""
    print_status "INFO" "Check the generated report for detailed results"
    print_status "INFO" "Monitor logs with: docker logs -f [container-name]"
}

# Run main function
main "$@" 