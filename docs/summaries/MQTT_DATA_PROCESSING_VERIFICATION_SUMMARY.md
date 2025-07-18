# 📡 MQTT Data Processing Verification Summary
## Complete Implementation for Core Data Processing Workflow

> **🎯 OBJECTIVE**: Verify that all MQTT payload data is stored in the correct collections with comprehensive debug logging and monitoring.

---

## 📋 **Implementation Overview**

### **What Was Implemented**

1. **🔧 Enhanced Debug Logging** - Comprehensive logging for all MQTT data processing steps
2. **📊 Monitoring Dashboard** - Grafana dashboard for real-time metrics
3. **🧪 Test Suite** - Complete testing framework for data processing workflow
4. **📈 Metrics Collection** - Prometheus metrics for performance monitoring

---

## 🔧 **1. Enhanced Debug Logging Implementation**

### **Files Modified:**
- `services/mqtt-listeners/shared/data_processor.py` - Enhanced with detailed debug logging
- `services/mqtt-listeners/shared/device_mapper.py` - Added patient lookup logging

### **Debug Logging Features:**

#### **Data Processor Logging:**
```python
# Patient data updates
logger.debug(f"🔄 Updating last data - Patient: {patient_id}, Type: {data_type}, Source: {source}")
logger.debug(f"📊 Data payload: {data}")

# Database operations
logger.debug(f"📊 Update result - Matched: {result.matched_count}, Modified: {result.modified_count}")
logger.info(f"✅ Successfully updated last {data_type} data for patient {patient_id}")

# History storage
logger.debug(f"📚 Storing medical history - Patient: {patient_id}, Type: {data_type}, Source: {source}")
logger.info(f"✅ Successfully stored {data_type} history for patient {patient_id} (ID: {result.inserted_id})")
```

#### **Device Mapper Logging:**
```python
# Patient lookup operations
logger.debug(f"🔍 Looking up patient by AVA4 MAC: {mac_address}")
logger.info(f"✅ Found patient by AVA4 MAC: {patient.get('_id')} - {patient.get('first_name', '')} {patient.get('last_name', '')}")

# Device mapping
logger.debug(f"📝 Field mapping: {device_type} -> {field_name}")
logger.warning(f"⚠️ No patient found for device MAC: {device_mac}, Type: {device_type}")
```

### **Log Levels:**
- **DEBUG**: Detailed processing steps, data payloads, field mappings
- **INFO**: Successful operations, patient found, data stored
- **WARNING**: Patient not found, processing failures
- **ERROR**: Database errors, connection issues

---

## 📊 **2. Monitoring Dashboard Implementation**

### **Grafana Dashboard:**
- **File**: `grafana/dashboards/mqtt-data-processing-dashboard.json`
- **Dashboard ID**: `mqtt-data-processing`
- **Refresh Rate**: 30 seconds

### **Key Metrics Panels:**

#### **1. Processing Performance:**
- **MQTT Message Processing Rate** - Messages per second
- **Patient Mapping Success Rate** - Percentage of successful patient lookups
- **Data Storage Success Rate** - Percentage of successful database writes

#### **2. Device Distribution:**
- **Device Type Processing Distribution** - Pie chart of device types
- **Device Type Processing Timeline** - Time series of device processing

#### **3. System Health:**
- **MQTT Connection Status** - Connection state for all listeners
- **Error Rate by Type** - Error breakdown by error type
- **Database Storage Performance** - Read/write operations per second

#### **4. Performance Metrics:**
- **Data Processing Latency** - 50th and 95th percentile processing times
- **Patient Mapping Failures by Device Type** - Failure analysis

### **Prometheus Metrics Required:**
```yaml
# MQTT Processing Metrics
mqtt_messages_processed_total{device_type="ava4"}
mqtt_messages_processed_total{device_type="kati"}
mqtt_messages_processed_total{device_type="qube"}

# Patient Mapping Metrics
patient_mapping_attempts_total{device_type="ava4"}
patient_mapping_success_total{device_type="ava4"}
patient_mapping_failures_total{device_type="ava4"}

# Data Storage Metrics
data_storage_attempts_total{collection="blood_pressure_histories"}
data_storage_success_total{collection="blood_pressure_histories"}

# Performance Metrics
data_processing_duration_seconds_bucket
database_write_operations_total
database_read_operations_total

# Connection Metrics
mqtt_connection_status{listener="ava4"}
mqtt_connection_status{listener="kati"}
mqtt_connection_status{listener="qube"}
```

---

## 🧪 **3. Test Suite Implementation**

### **Test Files Created:**

#### **1. Python Test Script:**
- **File**: `test_mqtt_data_processing.py`
- **Purpose**: Unit testing of data processing logic
- **Features**:
  - Tests AVA4 blood pressure payload processing
  - Tests Kati Watch vital signs processing
  - Tests Qube-Vital data processing
  - Verifies database storage
  - Comprehensive logging output

#### **2. Bash Test Script:**
- **File**: `test_mqtt_workflow.sh`
- **Purpose**: End-to-end workflow testing
- **Features**:
  - Container status checking
  - MQTT connection verification
  - Debug logging enablement
  - Sample message injection
  - Database verification
  - Test report generation

### **Test Coverage:**

#### **AVA4 Testing:**
```json
{
  "from": "BLE",
  "to": "CLOUD",
  "time": 1836942771,
  "deviceCode": "08:F9:E0:D1:F7:B4",
  "mac": "08:F9:E0:D1:F7:B4",
  "type": "reportAttribute",
  "device": "WBP BIOLIGHT",
  "data": {
    "attribute": "BP_BIOLIGTH",
    "value": {
      "device_list": [{
        "scan_time": 1836942771,
        "ble_addr": "d616f9641622",
        "bp_high": 137,
        "bp_low": 95,
        "PR": 74
      }]
    }
  }
}
```

#### **Kati Watch Testing:**
```json
{
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
```

#### **Qube-Vital Testing:**
```json
{
  "from": "CM4_BLE_GW",
  "to": "CLOUD",
  "time": 1836942771,
  "mac": "AA:BB:CC:DD:EE:FF",
  "type": "reportAttribute",
  "data": {
    "attribute": "WBP_JUMPER",
    "value": {
      "bp_high": 120,
      "bp_low": 80,
      "pr": 72
    }
  }
}
```

---

## 🚀 **4. Usage Instructions**

### **Running the Test Suite:**

#### **1. Enable Debug Logging:**
```bash
# Set debug log level
export LOG_LEVEL=DEBUG

# Restart MQTT listeners with debug logging
docker compose -f docker-compose.mqtt.yml restart ava4-mqtt-listener
docker compose -f docker-compose.mqtt.yml restart kati-mqtt-listener
docker compose -f docker-compose.mqtt.yml restart qube-mqtt-listener
```

#### **2. Run Complete Test Suite:**
```bash
# Make script executable (if not already)
chmod +x test_mqtt_workflow.sh

# Run the complete test suite
./test_mqtt_workflow.sh
```

#### **3. Run Individual Tests:**
```bash
# Run Python unit tests
python3 test_mqtt_data_processing.py

# Check container status
docker ps | grep mqtt-listener

# Monitor logs in real-time
docker logs -f ava4-mqtt-listener
docker logs -f kati-mqtt-listener
docker logs -f qube-mqtt-listener
```

### **Monitoring Dashboard Setup:**

#### **1. Import Grafana Dashboard:**
```bash
# Copy dashboard to Grafana provisioning
cp grafana/dashboards/mqtt-data-processing-dashboard.json grafana/provisioning/dashboards/

# Restart Grafana to load dashboard
docker compose restart grafana
```

#### **2. Access Dashboard:**
- **URL**: `http://localhost:3000` (or your Grafana URL)
- **Dashboard**: "MQTT Data Processing Monitor"
- **Refresh**: 30 seconds (configurable)

### **Database Verification:**

#### **1. Check Recent Data:**
```bash
# Connect to MongoDB
docker exec -it mongodb mongosh --eval "
use AMY;
db.blood_pressure_histories.find().sort({timestamp: -1}).limit(5);
db.patients.find({last_blood_pressure: {\$exists: true}}).limit(5);
"
```

#### **2. Verify Device Mappings:**
```bash
# Check device-patient mappings
docker exec -it mongodb mongosh --eval "
use AMY;
db.amy_devices.find().limit(10);
db.watches.find().limit(10);
"
```

---

## 📈 **5. Expected Results**

### **Successful Test Execution:**

#### **1. Debug Log Output:**
```
🧪 MQTT Data Processing Tester initialized
🔧 Processing AVA4 data - Patient: 507f1f77bcf86cd799439011, MAC: 08:F9:E0:D1:F7:B4, Attribute: BP_BIOLIGTH
📊 AVA4 value payload: {'device_list': [{'scan_time': 1836942771, 'ble_addr': 'd616f9641622', 'bp_high': 137, 'bp_low': 95, 'PR': 74}]}
📝 Attribute mapping: BP_BIOLIGTH -> blood_pressure
📊 Found 1 device readings
🔧 Processing device reading 1/1: {'scan_time': 1836942771, 'ble_addr': 'd616f9641622', 'bp_high': 137, 'bp_low': 95, 'PR': 74}
✅ AVA4 data processed: {'systolic': 137, 'diastolic': 95, 'pulse': 74, 'scan_time': 1836942771}
🔄 Updating last data - Patient: 507f1f77bcf86cd799439011, Type: blood_pressure, Source: AVA4
✅ Last data updated successfully
📚 Storing medical history - Patient: 507f1f77bcf86cd799439011, Type: blood_pressure, Source: AVA4
✅ History stored successfully
📊 AVA4 processing complete - 1/1 readings processed successfully
```

#### **2. Database Verification:**
```javascript
// Blood pressure history collection
{
  "_id": ObjectId("..."),
  "patient_id": ObjectId("507f1f77bcf86cd799439011"),
  "timestamp": ISODate("2025-01-16T12:30:45.123Z"),
  "data": {
    "systolic": 137,
    "diastolic": 95,
    "pulse": 74,
    "scan_time": 1836942771
  },
  "source": "AVA4",
  "device_id": "08:F9:E0:D1:F7:B4",
  "created_at": ISODate("2025-01-16T12:30:45.123Z")
}

// Patient last data update
{
  "_id": ObjectId("507f1f77bcf86cd799439011"),
  "last_blood_pressure": {
    "systolic": 137,
    "diastolic": 95,
    "pulse": 74,
    "scan_time": 1836942771,
    "timestamp": ISODate("2025-01-16T12:30:45.123Z"),
    "source": "AVA4",
    "updated_at": ISODate("2025-01-16T12:30:45.123Z")
  },
  "updated_at": ISODate("2025-01-16T12:30:45.123Z")
}
```

#### **3. Grafana Dashboard Metrics:**
- **MQTT Message Processing Rate**: > 0 messages/sec
- **Patient Mapping Success Rate**: > 90%
- **Data Storage Success Rate**: > 98%
- **MQTT Connection Status**: All listeners connected (green)
- **Error Rate**: < 5%

---

## 🔍 **6. Troubleshooting Guide**

### **Common Issues & Solutions:**

#### **1. MQTT Connection Issues:**
```bash
# Check MQTT broker connectivity
ping adam.amy.care
telnet adam.amy.care 1883

# Check listener logs
docker logs ava4-mqtt-listener | grep "Connected"
```

#### **2. Patient Mapping Failures:**
```bash
# Check device mappings in database
docker exec -it mongodb mongosh --eval "
use AMY;
db.amy_devices.find({mac_address: 'DEVICE_MAC'});
db.watches.find({imei: 'DEVICE_IMEI'});
"
```

#### **3. Database Storage Issues:**
```bash
# Check MongoDB connectivity
docker exec -it mongodb mongosh --eval "db.runCommand({ping: 1})"

# Check collection permissions
docker exec -it mongodb mongosh --eval "
use AMY;
db.blood_pressure_histories.find().limit(1);
"
```

#### **4. Debug Logging Not Working:**
```bash
# Verify log level is set
echo $LOG_LEVEL

# Restart containers with explicit log level
docker compose -f docker-compose.mqtt.yml restart ava4-mqtt-listener
```

---

## 📋 **7. Verification Checklist**

### **Pre-Test Checklist:**
- [ ] MQTT listener containers are running
- [ ] MongoDB connection is established
- [ ] Debug logging is enabled (LOG_LEVEL=DEBUG)
- [ ] Grafana dashboard is imported
- [ ] Test scripts are executable

### **Test Execution Checklist:**
- [ ] Run `./test_mqtt_workflow.sh`
- [ ] Verify all containers are healthy
- [ ] Check MQTT connections are established
- [ ] Monitor debug logs for processing steps
- [ ] Verify database storage operations
- [ ] Check Grafana dashboard metrics

### **Post-Test Verification:**
- [ ] Review test report file
- [ ] Check database for new records
- [ ] Verify patient data updates
- [ ] Monitor error rates in dashboard
- [ ] Confirm all device types processed

---

## 🎯 **8. Success Criteria**

### **Functional Requirements:**
- ✅ All MQTT payloads are processed correctly
- ✅ Patient mapping works for all device types
- ✅ Data is stored in correct collections
- ✅ Last data fields are updated in patient records
- ✅ History collections receive new entries

### **Performance Requirements:**
- ✅ Processing latency < 5 seconds (95th percentile)
- ✅ Patient mapping success rate > 90%
- ✅ Data storage success rate > 98%
- ✅ MQTT connection uptime > 99%

### **Monitoring Requirements:**
- ✅ All metrics are visible in Grafana dashboard
- ✅ Debug logs provide detailed processing information
- ✅ Error rates are tracked and alertable
- ✅ Performance bottlenecks are identifiable

---

## 📞 **9. Support & Maintenance**

### **Regular Monitoring:**
- Monitor Grafana dashboard daily
- Check error rates and alert thresholds
- Review debug logs for anomalies
- Verify database storage performance

### **Maintenance Tasks:**
- Update test data periodically
- Review and adjust alert thresholds
- Clean up old test logs
- Update dashboard queries as needed

### **Contact Information:**
- **Technical Issues**: Check logs and dashboard metrics
- **Configuration Changes**: Update environment variables
- **Performance Issues**: Monitor latency and throughput metrics

---

**📅 Implementation Date**: January 16, 2025  
**🔧 Version**: 1.0  
**👤 Maintainer**: MQTT Data Processing Team 