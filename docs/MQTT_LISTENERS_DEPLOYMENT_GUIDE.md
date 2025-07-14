# 🚀 MQTT Listeners Deployment Guide

## 📋 **Overview**

This guide covers the deployment of three MQTT listener services for processing medical device data from:
- **AVA4 + Sub-devices** (Blood pressure, glucometer, oximeter, etc.)
- **Kati Watch** (Vital signs, location, emergency alerts)
- **Qube-Vital** (Hospital-based medical devices)

## 🏗️ **Architecture**

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   AVA4 Devices  │    │   Kati Watch    │    │  Qube-Vital     │
│   + Sub-devices │    │     Devices     │    │    Devices      │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          ▼                      ▼                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                    MQTT Broker (adam.amy.care)                 │
│  Topics: ESP32_BLE_GW_TX, dusun_sub | iMEDE_watch/# | CM4_BLE_GW_TX │
└─────────────────────────────────────────────────────────────────┘
          │                      │                      │
          ▼                      ▼                      ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ AVA4 Listener   │    │ Kati Listener   │    │ Qube Listener   │
│   Service       │    │   Service       │    │   Service       │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                                 ▼
                    ┌─────────────────────┐
                    │   MongoDB (AMY)     │
                    │ • patients          │
                    │ • medical histories │
                    │ • device mappings   │
                    └─────────────────────┘
```

## 🔧 **Prerequisites**

### **1. MQTT Broker Configuration**
- **Host**: `adam.amy.care:1883`
- **Credentials**: `webapi` / `Sim!4433`
- **QoS**: 1
- **Keepalive**: 60 seconds

### **2. MongoDB Configuration**
- **URI**: `mongodb://opera_admin:Sim!443355@coruscant.my-firstcare.com:27023/admin?ssl=true&authSource=admin`
- **Database**: `AMY`

### **3. Device-Patient Mapping**
- **AVA4**: `amy_boxes.mac_address` → `patients.ava_mac_address`
- **Medical Devices**: `amy_devices.patient_id` → `patients._id`
- **Kati Watch**: `watches.imei` → `patients.watch_mac_address`
- **Qube-Vital**: `payload.citiz` → `patients.id_card` (auto-create if not found)

## 🚀 **Deployment Steps**

### **Step 1: Build and Deploy Services**

```bash
# Navigate to project root
cd /path/to/stardust-my-firstcare-com

# Build and start MQTT listener services
docker compose -f docker-compose.mqtt.yml up -d --build
```

### **Step 2: Verify Services**

```bash
# Check service status
docker compose -f docker-compose.mqtt.yml ps

# Check logs
docker logs ava4-mqtt-listener
docker logs kati-mqtt-listener
docker logs qube-mqtt-listener
```

### **Step 3: Monitor Connections**

```bash
# Monitor MQTT connections
docker logs -f ava4-mqtt-listener | grep "Connected"
docker logs -f kati-mqtt-listener | grep "Connected"
docker logs -f qube-mqtt-listener | grep "Connected"
```

## 📊 **Data Processing Flow**

### **AVA4 Data Processing**
1. **Status Messages** (`ESP32_BLE_GW_TX`):
   - Heartbeat messages
   - Online/offline triggers
   - Device status monitoring

2. **Medical Data** (`dusun_sub`):
   - Blood pressure readings
   - Blood glucose measurements
   - SpO2 levels
   - Body temperature
   - Weight measurements
   - Uric acid levels
   - Cholesterol readings

### **Kati Watch Data Processing**
1. **Vital Signs** (`iMEDE_watch/VitalSign`):
   - Heart rate
   - Blood pressure
   - SpO2
   - Body temperature

2. **Batch Data** (`iMEDE_watch/AP55`):
   - Multiple vital signs in one message

3. **Device Status** (`iMEDE_watch/hb`):
   - Step count
   - Battery level
   - Signal strength

4. **Emergency Alerts** (`iMEDE_watch/sos`, `iMEDE_watch/fallDown`):
   - SOS signals
   - Fall detection

### **Qube-Vital Data Processing**
1. **Status Messages** (`CM4_BLE_GW_TX`):
   - Device heartbeat
   - Online status

2. **Medical Data** (`CM4_BLE_GW_TX`):
   - Blood pressure
   - Blood glucose
   - Weight
   - Body temperature
   - SpO2

## 🔍 **Monitoring and Troubleshooting**

### **Health Checks**

```bash
# Check service health
docker compose -f docker-compose.mqtt.yml exec ava4-mqtt-listener python -c "import sys; sys.exit(0)"
docker compose -f docker-compose.mqtt.yml exec kati-mqtt-listener python -c "import sys; sys.exit(0)"
docker compose -f docker-compose.mqtt.yml exec qube-mqtt-listener python -c "import sys; sys.exit(0)"
```

### **Log Monitoring**

```bash
# Monitor real-time logs
docker logs -f ava4-mqtt-listener
docker logs -f kati-mqtt-listener
docker logs -f qube-mqtt-listener

# Search for errors
docker logs ava4-mqtt-listener | grep ERROR
docker logs kati-mqtt-listener | grep ERROR
docker logs qube-mqtt-listener | grep ERROR
```

### **Database Verification**

```bash
# Check patient data updates
docker exec -it mongodb mongo --eval "db.patients.find({}, {last_blood_pressure: 1, last_blood_sugar: 1, last_spo2: 1}).limit(5)"

# Check medical history
docker exec -it mongodb mongo --eval "db.blood_pressure_histories.find().sort({timestamp: -1}).limit(5)"
```

## 🛠️ **Configuration Options**

### **Environment Variables**

| Variable | Description | Default |
|----------|-------------|---------|
| `MQTT_BROKER_HOST` | MQTT broker hostname | `adam.amy.care` |
| `MQTT_BROKER_PORT` | MQTT broker port | `1883` |
| `MQTT_USERNAME` | MQTT username | `webapi` |
| `MQTT_PASSWORD` | MQTT password | `Sim!4433` |
| `MQTT_QOS` | Quality of Service | `1` |
| `MQTT_KEEPALIVE` | Keepalive interval | `60` |
| `MONGODB_URI` | MongoDB connection string | Required |
| `MONGODB_DATABASE` | MongoDB database name | `AMY` |
| `LOG_LEVEL` | Logging level | `INFO` |

### **Topic Configuration**

| Service | Topics | Description |
|---------|--------|-------------|
| AVA4 | `ESP32_BLE_GW_TX,dusun_sub` | Status and medical data |
| Kati | `iMEDE_watch/#` | All Kati Watch topics |
| Qube | `CM4_BLE_GW_TX` | Qube-Vital data |

## 📈 **Performance Monitoring**

### **Metrics to Track**
- **Message Processing Rate**: Messages per second
- **Patient Lookup Success Rate**: Percentage of successful patient mappings
- **Data Storage Success Rate**: Percentage of successful data storage
- **Error Rates**: Failed processing percentage
- **Connection Stability**: MQTT connection uptime

### **Alerting**
- MQTT connection failures
- High error rates (>5%)
- Patient mapping failures
- Database connection issues

## 🔒 **Security Considerations**

### **MQTT Security**
- Use TLS encryption for MQTT connections
- Implement proper authentication
- Monitor for unauthorized access

### **Data Security**
- Encrypt sensitive patient data
- Implement access controls
- Audit data access logs

## 🚨 **Emergency Procedures**

### **Service Restart**
```bash
# Restart all services
docker compose -f docker-compose.mqtt.yml restart

# Restart specific service
docker compose -f docker-compose.mqtt.yml restart ava4-mqtt-listener
```

### **Data Recovery**
```bash
# Check for data loss
docker exec -it mongodb mongo --eval "db.blood_pressure_histories.find({timestamp: {\$gte: new Date(Date.now() - 3600000)}}).count()"

# Verify patient mappings
docker exec -it mongodb mongo --eval "db.patients.find({ava_mac_address: {\$exists: true}}).count()"
```

## 📝 **Testing**

### **Test MQTT Messages**

```bash
# Test AVA4 blood pressure
mosquitto_pub -h adam.amy.care -u webapi -P Sim!4433 -t dusun_sub -m '{
  "from": "BLE",
  "to": "CLOUD",
  "time": 1836942771,
  "deviceCode": "08:F9:E0:D1:F7:B4",
  "mac": "08:F9:E0:D1:F7:B4",
  "type": "reportAttribute",
  "device": "WBP BIOLIGHT",
  "data": {
    "attribute": "BP_BIOLIGTH",
    "mac": "08:F9:E0:D1:F7:B4",
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
}'

# Test Kati Watch vital signs
mosquitto_pub -h adam.amy.care -u webapi -P Sim!4433 -t iMEDE_watch/VitalSign -m '{
  "IMEI": "865067123456789",
  "heartRate": 72,
  "bloodPressure": {"bp_sys": 122, "bp_dia": 78},
  "spO2": 97,
  "bodyTemperature": 36.6,
  "timeStamps": "16/06/2025 12:30:45"
}'

# Test Qube-Vital blood pressure
mosquitto_pub -h adam.amy.care -u webapi -P Sim!4433 -t CM4_BLE_GW_TX -m '{
  "from": "PI",
  "to": "CLOUD",
  "time": 1739360702,
  "mac": "e4:5f:01:ed:82:59",
  "type": "reportAttribute",
  "citiz": "3570300400000",
  "nameTH": "นาย#เดพ##เอชวีศูนย์หนึ่ง",
  "nameEN": "Mr.#DEV##HV01",
  "brith": "25220713",
  "gender": "1",
  "data": {
    "attribute": "WBP_JUMPER",
    "ble_mac": "FF:22:09:08:31:31",
    "value": {
      "bp_high": 120,
      "bp_low": 78,
      "pr": 71
    }
  }
}'
```

## 📚 **Additional Resources**

- [MQTT Protocol Documentation](https://mqtt.org/documentation)
- [Paho MQTT Python Client](https://pypi.org/project/paho-mqtt/)
- [MongoDB Python Driver](https://pymongo.readthedocs.io/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)

---

**🏥 My FirstCare MQTT Listeners**  
*Real-time medical device data processing system*

**Status**: ✅ **Ready for Deployment**  
**MQTT Compliance**: ✅ **Standard Protocol**  
**Data Processing**: ✅ **Real-time**  
**Scalability**: ✅ **Horizontal scaling ready** 