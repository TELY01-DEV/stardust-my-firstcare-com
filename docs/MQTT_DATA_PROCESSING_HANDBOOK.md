# 📡 MQTT Data Processing Handbook
## Core Medical Device Data Processing Workflow

> **⚠️ CRITICAL SYSTEM**: This document describes the core data processing workflow for medical device data from AVA4, Kati Watch, and Qube-Vital devices. This system handles real-time medical data ingestion, patient mapping, and database storage.

---

## 📋 **Table of Contents**

1. [System Overview](#system-overview)
2. [Architecture](#architecture)
3. [Device Types & Payloads](#device-types--payloads)
4. [Data Processing Flow](#data-processing-flow)
5. [Database Storage Patterns](#database-storage-patterns)
6. [Patient Mapping Logic](#patient-mapping-logic)
7. [Error Handling & Monitoring](#error-handling--monitoring)
8. [Operational Procedures](#operational-procedures)
9. [Troubleshooting Guide](#troubleshooting-guide)
10. [Performance Optimization](#performance-optimization)

---

## 🎯 **System Overview**

### **Purpose**
The MQTT Data Processing System is the core infrastructure that:
- Receives real-time medical data from IoT devices
- Maps device data to patient records
- Stores medical measurements in standardized collections
- Maintains patient's latest medical data
- Provides real-time monitoring and alerting

### **Key Components**
- **3 MQTT Listener Services** (AVA4, Kati Watch, Qube-Vital)
- **Device Mapper** (Patient identification logic)
- **Data Processor** (Data transformation and storage)
- **MongoDB Database** (AMY database)
- **Real-time Monitoring** (WebSocket server)

---

## 🏗️ **Architecture**

### **High-Level Architecture**
```mermaid
graph TD
    A[Medical Devices] --> B[MQTT Broker]
    B --> C[MQTT Listeners]
    C --> D[Device Mapper]
    D --> E[Data Processor]
    E --> F[MongoDB]
    
    A1[AVA4 + Sub-devices] --> B
    A2[Kati Watch] --> B
    A3[Qube-Vital] --> B
    
    C1[AVA4 Listener] --> D
    C2[Kati Listener] --> D
    C3[Qube Listener] --> D
    
    D --> G[Patient Lookup]
    E --> H[Update Last Data]
    E --> I[Store History]
    
    J[Monitoring] --> K[WebSocket Server]
    K --> L[Real-time Dashboard]
```

### **Service Architecture**
```mermaid
graph LR
    A[MQTT Broker<br/>adam.amy.care:1883] --> B[AVA4 Listener<br/>Topics: ESP32_BLE_GW_TX, dusun_sub]
    A --> C[Kati Listener<br/>Topics: iMEDE_watch/#]
    A --> D[Qube Listener<br/>Topics: CM4_BLE_GW_TX]
    
    B --> E[Device Mapper<br/>Patient Identification]
    C --> E
    D --> E
    
    E --> F[Data Processor<br/>Storage Logic]
    F --> G[MongoDB<br/>AMY Database]
    
    H[WebSocket Server<br/>Real-time Monitoring] --> I[Monitoring Dashboard]
```

---

## 📱 **Device Types & Payloads**

### **1. AVA4 + Medical Sub-devices**

#### **Device Characteristics**
- **Ownership**: Personal devices (individual patients)
- **Communication**: BLE sub-devices via AVA4 gateway
- **Data Structure**: Nested `device_list` array
- **Patient Mapping**: Device MAC address lookup

#### **MQTT Topics**
- `ESP32_BLE_GW_TX`: Status messages (heartbeat, online/offline)
- `dusun_sub`: Medical device data

#### **Payload Structure**
```json
{
  "from": "BLE",
  "to": "CLOUD",
  "time": 1836942771,
  "deviceCode": "08:F9:E0:D1:F7:B4",  // Sub-device MAC
  "mac": "08:F9:E0:D1:F7:B4",         // Sub-device MAC
  "type": "reportAttribute",
  "device": "WBP BIOLIGHT",           // Device name
  "data": {
    "attribute": "BP_BIOLIGTH",       // Device type identifier
    "mac": "08:F9:E0:D1:F7:B4",       // Sub-device MAC
    "value": {
      "device_list": [{
        "scan_time": 1836942771,
        "ble_addr": "d616f9641622",   // BLE device address
        "bp_high": 137,               // Systolic
        "bp_low": 95,                 // Diastolic
        "PR": 74                      // Pulse Rate
      }]
    }
  }
}
```

#### **Supported Device Types**
| Attribute | Device Type | Data Fields |
|-----------|-------------|-------------|
| `BP_BIOLIGTH` | Blood Pressure | `bp_high`, `bp_low`, `PR` |
| `Contour_Elite` | Blood Sugar | `blood_glucose`, `marker` |
| `AccuChek_Instant` | Blood Sugar | `blood_glucose`, `marker` |
| `Oximeter JUMPER` | SpO2 | `spo2`, `pulse`, `pi` |
| `IR_TEMO_JUMPER` | Body Temperature | `temp`, `mode` |
| `BodyScale_JUMPER` | Weight Scale | `weight`, `resistance` |
| `MGSS_REF_UA` | Uric Acid | `uric_acid` |
| `MGSS_REF_CHOL` | Cholesterol | `cholesterol` |

### **2. Kati Watch**

#### **Device Characteristics**
- **Ownership**: Personal devices (individual patients)
- **Communication**: Direct MQTT messages
- **Data Structure**: Direct field access
- **Patient Mapping**: IMEI lookup

#### **MQTT Topics**
- `iMEDE_watch/VitalSign`: Single vital signs measurement
- `iMEDE_watch/AP55`: Batch vital signs data
- `iMEDE_watch/hb`: Heartbeat with step count
- `iMEDE_watch/sleepdata`: Sleep pattern data
- `iMEDE_watch/sos`: Emergency SOS alert
- `iMEDE_watch/fallDown`: Fall detection alert
- `iMEDE_watch/location`: GPS location data

#### **Payload Structure (VitalSign)**
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
    "signalGSM": 80,
    "battery": 67,
    "location": {
        "GPS": {"latitude": 22.5678, "longitude": 112.3456},
        "WiFi": "[{...}]",
        "LBS": {"MCC": "520", "MNC": "3", "LAC": "1815", "CID": "79474300"}
    },
    "timeStamps": "16/06/2025 12:30:45"
}
```

### **3. Qube-Vital**

#### **Device Characteristics**
- **Ownership**: Hospital devices (institutional)
- **Communication**: Direct MQTT messages
- **Data Structure**: Direct `value` object
- **Patient Mapping**: Citizen ID (CID) lookup with auto-creation

#### **MQTT Topics**
- `CM4_BLE_GW_TX`: All Qube-Vital messages (status + medical data)

#### **Payload Structure**
```json
{
  "from": "PI",
  "to": "CLOUD",
  "time": 1739360702,
  "mac": "e4:5f:01:ed:82:59",        // Qube-Vital device MAC
  "type": "reportAttribute",
  "citiz": "3570300400000",          // Citizen ID (CID)
  "nameTH": "นาย#เดพ##เอชวีศูนย์หนึ่ง",  // Thai name
  "nameEN": "Mr.#DEV##HV01",         // English name
  "brith": "25220713",               // Birth date (YYYYMMDD)
  "gender": "1",                     // 1=male, 0=female
  "data": {
    "attribute": "WBP_JUMPER",       // Device type
    "ble_mac": "FF:22:09:08:31:31",  // BLE sub-device MAC
    "value": {
      "bp_high": 120,                // Systolic
      "bp_low": 78,                  // Diastolic
      "pr": 71                       // Pulse Rate
    }
  }
}
```

#### **Supported Device Types**
| Attribute | Device Type | Data Fields |
|-----------|-------------|-------------|
| `WBP_JUMPER` | Blood Pressure | `bp_high`, `bp_low`, `pr` |
| `CONTOUR` | Blood Sugar | `blood_glucose`, `marker` |
| `BodyScale_JUMPER` | Weight Scale | `weight`, `Resistance` |
| `TEMO_Jumper` | Body Temperature | `Temp`, `mode` |
| `Oximeter_JUMPER` | SpO2 | `spo2`, `pulse`, `pi` |

---

## 🔄 **Data Processing Flow**

### **Step 1: MQTT Message Reception**
```python
# Each listener receives MQTT messages
def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        self.process_message(msg.topic, payload)
    except Exception as e:
        logger.error(f"Error processing message: {e}")
```

### **Step 2: Message Parsing & Validation**
```python
def process_message(self, topic: str, payload: str):
    # Parse JSON payload
    data = json.loads(payload)
    
    # Validate required fields based on device type
    if topic == "dusun_sub":
        self.process_ava4_medical_data(data)
    elif topic.startswith("iMEDE_watch/"):
        self.process_kati_data(topic, data)
    elif topic == "CM4_BLE_GW_TX":
        self.process_qube_data(data)
```

### **Step 3: Patient Identification**
```python
# AVA4: Device MAC lookup
patient = self.device_mapper.find_patient_by_device_mac(device_mac, device_type)

# Kati Watch: IMEI lookup
patient = self.device_mapper.find_patient_by_kati_imei(imei)

# Qube-Vital: Citizen ID lookup with auto-creation
patient = self.device_mapper.find_patient_by_citiz(citiz)
if not patient:
    patient = self.device_mapper.create_unregistered_patient(citiz, name_th, name_en, birth_date, gender)
```

### **Step 4: Data Processing & Storage**
```python
# Process device-specific data
success = self.data_processor.process_device_data(
    patient_id=patient['_id'],
    device_type=device_type,
    data=processed_data,
    source=device_source
)

# This triggers:
# 1. Update patient's last data
# 2. Store in medical history collection
```

---

## 💾 **Database Storage Patterns**

### **Two-Collection Storage System**

#### **1. Patient Collection (Latest Data)**
```python
# patients collection - stores latest medical data
{
    "_id": ObjectId("..."),
    "first_name": "John",
    "last_name": "Doe",
    "id_card": "1234567890123",  # For Qube-Vital lookup
    
    # Device identification
    "ava_mac_address": "DC:DA:0C:5A:80:64",  # AVA4 box
    "watch_mac_address": "865067123456789",   # Kati Watch IMEI
    
    # Latest medical data (updated via update_patient_last_data)
    "last_blood_pressure": {
        "systolic": 137,
        "diastolic": 95,
        "pulse": 74,
        "timestamp": "2024-01-15T10:30:00Z",
        "source": "AVA4",
        "device_mac": "08:F9:E0:D1:F7:B4"
    },
    "last_blood_sugar": {...},
    "last_spo2": {...},
    "last_body_temperature": {...},
    "last_weight": {...},
    "last_uric_acid": {...},
    "last_cholesterol": {...},
    "last_heart_rate": {...},
    "last_step_count": {...},
    "last_sleep_data": {...}
}
```

#### **2. Medical History Collections (Historical Data)**
```python
# blood_pressure_histories collection
{
    "_id": ObjectId("..."),
    "patient_id": ObjectId("..."),  # Links to patients collection
    "timestamp": "2024-01-15T10:30:00Z",
    "data": {
        "systolic": 137,
        "diastolic": 95,
        "pulse": 74,
        "scan_time": 1836942771,
        "ble_addr": "d616f9641622"
    },
    "source": "AVA4",  # Device source
    "device_id": "08:F9:E0:D1:F7:B4",  # Device MAC/IMEI
    "created_at": "2024-01-15T10:30:00Z"
}
```

### **Collection Mapping**
```python
collection_mapping = {
    "blood_pressure": "blood_pressure_histories",
    "blood_sugar": "blood_sugar_histories", 
    "spo2": "spo2_histories",
    "body_temp": "temprature_data_histories",
    "weight": "body_data_histories",
    "uric_acid": "uric_acid_histories",
    "cholesterol": "cholesterol_histories",
    "heart_rate": "heart_rate_histories",
    "step_count": "step_histories",
    "sleep_data": "sleep_data_histories"
}
```

---

## 🔗 **Patient Mapping Logic**

### **AVA4 Device Mapping**
```python
# AVA4 Box mapping
amy_boxes.mac_address → patients.ava_mac_address

# Medical sub-devices mapping via amy_devices collection
amy_devices.patient_id → patients._id
amy_devices.mac_dusun_bps → patients.blood_pressure_mac_address
amy_devices.mac_oxymeter → patients.fingertip_pulse_oximeter_mac_address
amy_devices.mac_body_temp → patients.body_temperature_mac_address
amy_devices.mac_weight → patients.weight_scale_mac_address
amy_devices.mac_gluc → patients.blood_glucose_mac_address
amy_devices.mac_ua → patients.uric_mac_address
amy_devices.mac_chol → patients.cholesterol_mac_address
```

### **Kati Watch Mapping**
```python
# Kati Watch mapping
watches.imei → patients.watch_mac_address

# Alternative lookup
watches.patient_id → patients._id
```

### **Qube-Vital Mapping**
```python
# Qube-Vital device belongs to hospital
mfc_hv01_boxes.imei_of_hv01_box → hospitals.mac_hv01_box
mfc_hv01_boxes.hospital_id → hospitals._id

# Patient identification via Citizen ID (CID)
payload.citiz → patients.id_card

# Auto-create unregistered patient if not found
create_unregistered_patient(citiz, name_th, name_en, birth_date, gender)
```

---

## ⚠️ **Error Handling & Monitoring**

### **Error Categories**
1. **MQTT Connection Errors**: Broker connectivity issues
2. **JSON Parsing Errors**: Malformed payloads
3. **Patient Mapping Errors**: Device not found
4. **Database Errors**: Storage failures
5. **Data Validation Errors**: Invalid medical values

### **Error Handling Strategy**
```python
def process_message(self, topic: str, payload: str):
    try:
        # Parse JSON payload
        data = json.loads(payload)
        
        # Process message
        self.process_device_data(data)
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON payload: {e}")
        # Store in error collection for analysis
        
    except PatientNotFoundError as e:
        logger.warning(f"Patient not found: {e}")
        # Create unregistered patient (Qube-Vital) or skip (others)
        
    except DatabaseError as e:
        logger.error(f"Database error: {e}")
        # Retry logic or store in queue for later processing
        
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        # Store in error collection with full context
```

### **Monitoring & Alerting**
```python
# Health checks
- MQTT connection status
- Database connectivity
- Message processing rate
- Error rate monitoring
- Patient mapping success rate

# Alerts
- MQTT connection lost
- High error rate (>5%)
- Database connection issues
- Patient mapping failures
- Device data anomalies
```

---

## 🚀 **Operational Procedures**

### **Service Deployment**
```bash
# Deploy MQTT listener services
docker compose -f docker-compose.mqtt.yml up -d --build

# Verify services
docker compose -f docker-compose.mqtt.yml ps

# Check logs
docker logs -f ava4-mqtt-listener
docker logs -f kati-mqtt-listener
docker logs -f qube-mqtt-listener
```

### **Configuration Management**
```bash
# Environment variables
MQTT_BROKER_HOST=adam.amy.care
MQTT_BROKER_PORT=1883
MQTT_USERNAME=webapi
MQTT_PASSWORD=Sim!4433
MQTT_QOS=1
MQTT_KEEPALIVE=60

MONGODB_URI=mongodb://opera_admin:Sim!443355@coruscant.my-firstcare.com:27023/admin?ssl=true&authSource=admin
MONGODB_DATABASE=AMY
```

### **Health Monitoring**
```bash
# Service health checks
docker compose -f docker-compose.mqtt.yml exec ava4-mqtt-listener python -c "import sys; sys.exit(0)"
docker compose -f docker-compose.mqtt.yml exec kati-mqtt-listener python -c "import sys; sys.exit(0)"
docker compose -f docker-compose.mqtt.yml exec qube-mqtt-listener python -c "import sys; sys.exit(0)"

# Monitor real-time logs
docker logs -f ava4-mqtt-listener | grep "Connected"
docker logs -f kati-mqtt-listener | grep "Processing"
docker logs -f qube-mqtt-listener | grep "Successfully processed"
```

### **Data Validation**
```bash
# Check data processing statistics
# Monitor patient mapping success rates
# Validate medical data ranges
# Check for duplicate entries
# Monitor storage performance
```

---

## 🔧 **Troubleshooting Guide**

### **Common Issues & Solutions**

#### **1. MQTT Connection Issues**
```bash
# Symptoms: Connection lost, no data processing
# Solution: Check broker connectivity
ping adam.amy.care
telnet adam.amy.care 1883

# Check credentials
echo "MQTT_USERNAME: $MQTT_USERNAME"
echo "MQTT_PASSWORD: $MQTT_PASSWORD"
```

#### **2. Patient Mapping Failures**
```bash
# Symptoms: "No patient found" errors
# Solution: Check device-patient mappings

# For AVA4
db.amy_devices.find({"mac_address": "DEVICE_MAC"})

# For Kati Watch
db.watches.find({"imei": "DEVICE_IMEI"})

# For Qube-Vital
db.patients.find({"id_card": "CITIZEN_ID"})
```

#### **3. Database Connection Issues**
```bash
# Symptoms: Database errors, storage failures
# Solution: Check MongoDB connectivity
mongo "mongodb://coruscant.my-firstcare.com:27023/AMY" --username opera_admin --password Sim!443355

# Test connection
db.runCommand({ping: 1})
```

#### **4. High Error Rates**
```bash
# Symptoms: Many error logs, data loss
# Solution: Analyze error patterns
grep "ERROR" /var/log/mqtt-listeners/*.log | tail -100

# Check specific error types
grep "JSONDecodeError" /var/log/mqtt-listeners/*.log
grep "PatientNotFoundError" /var/log/mqtt-listeners/*.log
```

### **Debug Procedures**
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Restart services with debug
docker compose -f docker-compose.mqtt.yml restart

# Monitor specific topics
mosquitto_sub -h adam.amy.care -u webapi -P Sim!4433 -t "dusun_sub" -v
mosquitto_sub -h adam.amy.care -u webapi -P Sim!4433 -t "iMEDE_watch/#" -v
mosquitto_sub -h adam.amy.care -u webapi -P Sim!4433 -t "CM4_BLE_GW_TX" -v
```

---

## ⚡ **Performance Optimization**

### **Database Optimization**
```javascript
// Create indexes for performance
db.patients.createIndex({"ava_mac_address": 1})
db.patients.createIndex({"watch_mac_address": 1})
db.patients.createIndex({"id_card": 1})

db.amy_devices.createIndex({"mac_address": 1})
db.watches.createIndex({"imei": 1})

db.blood_pressure_histories.createIndex({"patient_id": 1, "timestamp": -1})
db.blood_sugar_histories.createIndex({"patient_id": 1, "timestamp": -1})
db.spo2_histories.createIndex({"patient_id": 1, "timestamp": -1})
```

### **Service Optimization**
```python
# Connection pooling
MONGODB_MAX_POOL_SIZE=50
MONGODB_MIN_POOL_SIZE=10

# Batch processing for high-frequency data
BATCH_SIZE=100
BATCH_TIMEOUT=5  # seconds

# Memory optimization
MAX_MESSAGE_HISTORY=1000
CLEANUP_INTERVAL=300  # seconds
```

### **Monitoring Metrics**
```python
# Key performance indicators
- Messages processed per second
- Database write latency
- Patient mapping success rate
- Error rate percentage
- Memory usage
- CPU utilization
- Network I/O
```

---

## 📚 **Additional Resources**

### **Related Documentation**
- [MQTT Listeners Deployment Guide](MQTT_LISTENERS_DEPLOYMENT_GUIDE.md)
- [AVA4 MQTT Examples](ava4_mqtt_examples.md)
- [Kati Watch MQTT Payload](KATI_WATCH_MQTT_PAYLOAD.md)
- [Qube-Vital MQTT Payload](Qube-Vital_MQTT_PAYLOAD.md)
- [Device Mapping Guide](AVA4_KATI-WATCH_QUBE-VITAL.md)

### **API Endpoints**
- `/api/patients/{patient_id}/medical-history` - Get patient medical history
- `/api/admin/medical-history/{history_type}` - Admin medical history management
- `/api/ava4/data` - AVA4 data endpoint
- `/api/kati/data` - Kati Watch data endpoint
- `/api/qube-vital/data` - Qube-Vital data endpoint

### **Monitoring Tools**
- WebSocket Server: Real-time MQTT message monitoring
- MongoDB Compass: Database inspection
- Grafana: Performance dashboards
- ELK Stack: Log analysis

---

## 🔒 **Security Considerations**

### **Data Protection**
- All medical data encrypted in transit (MQTT over TLS)
- Database connections use SSL/TLS
- Patient data anonymized in logs
- Access control via JWT authentication

### **Audit Trail**
- All data modifications logged
- Patient mapping changes tracked
- Error conditions recorded
- Performance metrics collected

---

**📞 Support**: For technical issues, contact the development team or refer to the troubleshooting guide above.

**🔄 Version**: This document is maintained and updated as the system evolves. 