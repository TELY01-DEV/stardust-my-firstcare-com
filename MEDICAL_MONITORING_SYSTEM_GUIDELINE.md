# Medical Monitoring System - Complete Guideline

## Table of Contents
1. [System Overview](#system-overview)
2. [Device Integration](#device-integration)
3. [Database Architecture](#database-architecture)
4. [Data Flow](#data-flow)
5. [API Endpoints](#api-endpoints)
6. [Web Panel Features](#web-panel-features)
7. [Emergency Alert System](#emergency-alert-system)
8. [Real-time Monitoring](#real-time-monitoring)
9. [Troubleshooting Guide](#troubleshooting-guide)
10. [Deployment Guide](#deployment-guide)

---

## System Overview

The Medical Monitoring System integrates multiple IoT devices to provide comprehensive health monitoring and emergency alert capabilities. The system processes data from AVA4 sub-devices, Kati Watch, and Qube-Vital devices through MQTT messaging and displays real-time information on a web-based dashboard.

### Key Components
- **MQTT Listeners**: Process device data from different sources
- **Data Processor**: Normalizes and stores device data
- **Web Panel**: Real-time monitoring dashboard
- **Emergency Dashboard**: Critical alert monitoring
- **WebSocket Server**: Real-time data streaming
- **Database**: MongoDB for data persistence

---

## Device Integration

### 1. AVA4 Devices (Sub-devices)

**Device Type**: Medical measurement devices connected to AVA4 gateway
**Communication**: MQTT via AVA4 gateway
**Data Format**: JSON payload with device_list array

#### Supported Devices:
| Device Attribute | Data Type | Measurements |
|------------------|-----------|--------------|
| `BP_BIOLIGTH` | Blood Pressure | systolic, diastolic, pulse |
| `WBP BIOLIGHT` | Blood Pressure | systolic, diastolic, pulse |
| `BLE_BPG` | Blood Pressure | systolic, diastolic, pulse |
| `Contour_Elite` | Blood Sugar | glucose value, marker |
| `AccuChek_Instant` | Blood Sugar | glucose value, marker |
| `Oximeter JUMPER` | SpO2 | oxygen saturation, pulse, pi |
| `IR_TEMO_JUMPER` | Body Temperature | temperature, mode |
| `BodyScale_JUMPER` | Weight | weight, resistance |
| `MGSS_REF_UA` | Uric Acid | uric acid value |
| `MGSS_REF_CHOL` | Cholesterol | cholesterol value |

#### MQTT Topic Format:
```
ava4/{ava4_mac}/data
```

#### Payload Structure:
```json
{
  "attribute": "BP_BIOLIGTH",
  "device_list": [
    {
      "bp_high": 120,
      "bp_low": 80,
      "PR": 72,
      "scan_time": "2024-01-01T10:00:00Z"
    }
  ]
}
```

### 2. Kati Watch

**Device Type**: Smartwatch with health monitoring
**Communication**: Direct MQTT
**Data Format**: JSON payload with health metrics

#### Supported Topics:
| Topic | Data Type | Description |
|-------|-----------|-------------|
| `iMEDE_watch/VitalSign` | Vital Signs | Heart rate, BP, SpO2, temperature |
| `iMEDE_watch/AP55` | Batch Vital Signs | Multiple readings in one payload |
| `iMEDE_watch/hb` | Heartbeat | Battery, signal, steps, status |
| `iMEDE_watch/SOS` | Emergency | SOS alert with location |
| `iMEDE_watch/fallDown` | Emergency | Fall detection alert |

#### Vital Signs Payload:
```json
{
  "heartRate": 75,
  "bloodPressure": {
    "bp_sys": 120,
    "bp_dia": 80
  },
  "spO2": 98,
  "bodyTemperature": 36.5,
  "battery": 85,
  "signalGSM": 4,
  "step": 5000
}
```

#### Batch Vital Signs Payload:
```json
{
  "data": [
    {
      "heartRate": 75,
      "bloodPressure": {"bp_sys": 120, "bp_dia": 80},
      "spO2": 98,
      "bodyTemperature": 36.5
    }
    // ... multiple readings
  ]
}
```

### 3. Qube-Vital

**Device Type**: Hospital-based medical devices
**Communication**: MQTT via hospital gateway
**Data Format**: JSON payload with medical measurements

#### Supported Devices:
| Device Attribute | Data Type | Measurements |
|------------------|-----------|--------------|
| `WBP_JUMPER` | Blood Pressure | systolic, diastolic, pulse |
| `CONTOUR` | Blood Sugar | glucose value, marker |
| `Oximeter_JUMPER` | SpO2 | oxygen saturation, pulse, pi |
| `TEMO_Jumper` | Body Temperature | temperature, mode |
| `BodyScale_JUMPER` | Weight | weight, resistance |

---

## Database Architecture

### Collections Overview

#### 1. Medical Data Collection (`medical_data`)
**Purpose**: Primary collection for web panel display
**Structure**:
```json
{
  "_id": "ObjectId",
  "device_id": "string",
  "device_type": "AVA4|Kati_Watch|Qube-Vital",
  "source": "AVA4|Kati|Qube-Vital",
  "patient_id": "ObjectId",
  "patient_name": "string",
  "timestamp": "datetime",
  "data_type": "string",
  "medical_values": {
    "systolic": 120,
    "diastolic": 80,
    "pulse": 72
  },
  "raw_data": {
    "device_mac": "string",
    "attribute": "string",
    "device_data": {}
  }
}
```

#### 2. Emergency Alarm Collection (`emergency_alarm`)
**Purpose**: Store SOS and fall detection alerts
**Structure**:
```json
{
  "_id": "ObjectId",
  "patient_id": "ObjectId",
  "patient_name": "string",
  "alert_type": "sos|fall_down",
  "alert_data": {
    "type": "string",
    "status": "ACTIVE",
    "location": "coordinates",
    "imei": "string",
    "priority": "CRITICAL|HIGH"
  },
  "timestamp": "datetime",
  "source": "Kati",
  "status": "ACTIVE",
  "processed": false
}
```

#### 3. Historical Collections
Each data type has its own historical collection:

| Data Type | Collection Name |
|-----------|-----------------|
| Blood Pressure | `blood_pressure_histories` |
| Blood Sugar | `blood_sugar_histories` |
| SpO2 | `spo2_histories` |
| Body Temperature | `temprature_data_histories` |
| Weight | `body_data_histories` |
| Heart Rate | `heart_rate_histories` |
| Steps | `step_histories` |
| Uric Acid | `uric_acid_histories` |
| Cholesterol | `cholesterol_histories` |

#### 4. Patient Collection (`patients`)
**Purpose**: Store patient information and latest data
**Structure**:
```json
{
  "_id": "ObjectId",
  "first_name": "string",
  "last_name": "string",
  "ava_mac_address": "string",
  "watch_mac_address": "string",
  "last_blood_pressure": {
    "systolic": 120,
    "diastolic": 80,
    "timestamp": "datetime",
    "source": "AVA4"
  },
  "last_heart_rate": {
    "value": 75,
    "timestamp": "datetime",
    "source": "Kati"
  }
  // ... other last data fields
}
```

---

## Data Flow

### 1. Device Data Processing Flow

```
Device → MQTT → Listener → Data Processor → Database Collections
```

#### Step-by-Step Process:

1. **Device Sends Data**: Device publishes MQTT message
2. **Listener Receives**: Appropriate listener (AVA4/Kati/Qube) processes message
3. **Data Processing**: Data processor normalizes and validates data
4. **Database Storage**: Data stored in multiple collections:
   - `medical_data` for web panel display
   - Specific history collection for historical data
   - `patients` collection updated with latest data
5. **Real-time Broadcasting**: WebSocket server broadcasts updates

### 2. Emergency Alert Flow

```
Emergency Event → MQTT → Listener → Emergency Processor → Emergency Collection → Alert Broadcasting
```

#### Emergency Processing:
1. **Alert Detection**: Listener detects SOS or fall detection
2. **Emergency Storage**: Stored in `emergency_alarm` collection
3. **Alert Broadcasting**: Real-time alerts sent to emergency dashboard
4. **Notification System**: Telegram/email notifications triggered

### 3. Web Panel Data Flow

```
Database → API → Web Panel → Real-time Updates via WebSocket
```

#### Data Retrieval Process:
1. **API Queries**: Web panel queries medical data API
2. **Data Aggregation**: Combines data from multiple collections
3. **Real-time Updates**: WebSocket provides live updates
4. **Display Rendering**: Frontend renders data with appropriate formatting

---

## API Endpoints

### Medical Data APIs

#### 1. Recent Medical Data
```
GET /api/recent-medical-data
```
**Purpose**: Get recent medical data for dashboard display
**Response**: Combined data from `medical_data` and `emergency_alarm` collections

#### 2. Medical Data by Device
```
GET /api/medical-data?device_type={device_type}
```
**Purpose**: Get medical data filtered by device type
**Parameters**: `device_type` (AVA4, Kati, Qube-Vital)

#### 3. Emergency Alerts
```
GET /api/emergency-alerts
```
**Purpose**: Get active emergency alerts
**Response**: Data from `emergency_alarm` collection

### Device Management APIs

#### 1. Device Status
```
GET /api/devices
```
**Purpose**: Get all registered devices
**Response**: List of AVA4, Kati, and Qube devices

#### 2. AVA4 Status
```
GET /api/ava4-status
```
**Purpose**: Get AVA4 gateway status
**Response**: AVA4 device status and sub-device information

### Real-time APIs

#### 1. WebSocket Events
```
WebSocket: /socket.io
```
**Events**:
- `get_medical_data`: Request medical data updates
- `get_statistics`: Request system statistics
- `get_data_flow_events`: Request data flow events

#### 2. Data Flow Events
```
GET /api/data-flow/events
```
**Purpose**: Get data flow monitoring events
**Response**: Real-time data processing events

---

## Web Panel Features

### 1. Medical Monitor Dashboard

#### Data Display:
- **Real-time Updates**: Live data from all devices
- **Device Filtering**: Filter by device type (AVA4, Kati, Qube)
- **Data Type Filtering**: Filter by measurement type
- **Time Range**: Last 24 hours for Kati/Qube, 7 days for AVA4

#### Data Visualization:
- **Medical Values**: Display actual measurements
- **Device Information**: Device ID, patient name, timestamp
- **Data Source**: Clear indication of data source
- **Batch Data**: Special handling for batch vital signs

### 2. Emergency Dashboard

#### Alert Monitoring:
- **SOS Alerts**: Critical emergency alerts
- **Fall Detection**: Fall detection alerts
- **Alert Status**: Active/processed status
- **Location Data**: GPS coordinates when available

#### Alert Management:
- **Mark as Processed**: Update alert status
- **Alert History**: View processed alerts
- **Real-time Updates**: Live alert notifications

### 3. Data Flow Monitoring

#### System Monitoring:
- **MQTT Messages**: Real-time MQTT message flow
- **Data Processing**: Processing status and errors
- **Device Connectivity**: Device online/offline status
- **System Statistics**: Performance metrics

### 4. Device Management

#### Device Overview:
- **Registered Devices**: List all connected devices
- **Device Status**: Online/offline status
- **Patient Mapping**: Device to patient relationships
- **Device Configuration**: Device settings and parameters

---

## Emergency Alert System

### Alert Types

#### 1. SOS Alerts
- **Trigger**: Manual SOS button press on Kati Watch
- **Priority**: CRITICAL
- **Data**: Location, timestamp, device ID
- **Response**: Immediate notification and alert display

#### 2. Fall Detection
- **Trigger**: Automatic fall detection by Kati Watch
- **Priority**: HIGH
- **Data**: Location, timestamp, device ID
- **Response**: Alert notification and monitoring

### Alert Processing

#### 1. Alert Storage
```json
{
  "alert_type": "sos",
  "status": "ACTIVE",
  "location": {
    "latitude": 13.7563,
    "longitude": 100.5018
  },
  "timestamp": "2024-01-01T10:00:00Z",
  "priority": "CRITICAL"
}
```

#### 2. Alert Broadcasting
- **WebSocket**: Real-time alert broadcasting
- **Emergency Dashboard**: Immediate display
- **Notification System**: Telegram/email alerts
- **Status Updates**: Alert processing status

### Alert Management

#### 1. Alert Lifecycle
1. **Detection**: Alert detected and stored
2. **Notification**: Real-time notification sent
3. **Processing**: Medical staff processes alert
4. **Resolution**: Alert marked as processed
5. **History**: Alert stored in history

#### 2. Alert Actions
- **View Details**: View complete alert information
- **Mark Processed**: Update alert status
- **Location View**: View patient location on map
- **Patient Info**: Access patient medical history

---

## Real-time Monitoring

### WebSocket Implementation

#### 1. Connection Management
```javascript
// Client-side connection
const socket = io('http://localhost:8098');

socket.on('connect', () => {
    console.log('Connected to WebSocket server');
});

socket.on('medical_data_update', (data) => {
    updateMedicalData(data);
});
```

#### 2. Event Broadcasting
```python
# Server-side broadcasting
@socketio.on('get_medical_data')
def handle_get_medical_data():
    # Send latest medical data
    emit('medical_data_update', medical_data)
```

### Data Streaming

#### 1. Real-time Updates
- **Medical Data**: Live updates from all devices
- **Emergency Alerts**: Immediate alert notifications
- **System Status**: Device connectivity updates
- **Data Flow**: Processing status updates

#### 2. Performance Optimization
- **Connection Pooling**: Efficient WebSocket connections
- **Data Caching**: Redis-based caching for performance
- **Event Filtering**: Client-side data filtering
- **Connection Limits**: Maximum connection management

---

## Troubleshooting Guide

### Common Issues

#### 1. No Data Display
**Symptoms**: Web panel shows "No Data" or "Unknown" sources
**Causes**:
- Device not connected to MQTT
- Data processing errors
- Database connection issues
- Cache issues

**Solutions**:
1. Check MQTT listener logs
2. Verify device connectivity
3. Clear browser cache
4. Restart containers

#### 2. Emergency Alerts Not Showing
**Symptoms**: SOS/fall detection not appearing
**Causes**:
- Emergency data not stored in correct collection
- API not querying emergency collection
- WebSocket not broadcasting alerts

**Solutions**:
1. Check emergency_alarm collection
2. Verify API endpoint configuration
3. Check WebSocket broadcasting
4. Review emergency processing logs

#### 3. Real-time Updates Not Working
**Symptoms**: Data not updating in real-time
**Causes**:
- WebSocket connection issues
- Event broadcasting problems
- Client-side connection errors

**Solutions**:
1. Check WebSocket server status
2. Verify client connection
3. Review event broadcasting logs
4. Test WebSocket connectivity

### Debug Commands

#### 1. Check MQTT Listeners
```bash
# Check AVA4 listener logs
docker logs ava4-listener

# Check Kati listener logs
docker logs kati-listener

# Check Qube listener logs
docker logs qube-listener
```

#### 2. Check Database Collections
```bash
# Check medical data
curl -s "http://localhost:8098/api/recent-medical-data" | jq '.data.recent_medical_data[] | {source, data_type: .medical_values.data_type}'

# Check emergency alerts
curl -s "http://localhost:8098/api/emergency-alerts" | jq '.data[] | {alert_type, device_id, source}'
```

#### 3. Check WebSocket Status
```bash
# Check WebSocket server logs
docker logs websocket-server

# Test WebSocket connection
curl -i -N -H "Connection: Upgrade" -H "Upgrade: websocket" -H "Sec-WebSocket-Version: 13" -H "Sec-WebSocket-Key: x3JJHMbDL1EzLkh9GBhXDw==" http://localhost:8099
```

### Log Analysis

#### 1. Key Log Patterns
- **✅ Success**: Data processed and stored successfully
- **❌ Error**: Processing or storage errors
- **🚨 Emergency**: Emergency alert processing
- **📊 Data**: Data flow and processing information

#### 2. Log Locations
- **MQTT Listeners**: Container logs for each listener
- **Web Panel**: Application logs in web-panel container
- **WebSocket Server**: WebSocket server logs
- **Database**: MongoDB logs for connection issues

---

## Deployment Guide

### Docker Setup

#### 1. Container Architecture
```yaml
# docker-compose.yml
services:
  ava4-listener:
    build: ./services/mqtt-listeners/ava4-listener
    environment:
      - MONGODB_URI=mongodb://mongo:27017/AMY
      - MQTT_BROKER=mqtt-broker:1883

  kati-listener:
    build: ./services/mqtt-listeners/kati-listener
    environment:
      - MONGODB_URI=mongodb://mongo:27017/AMY
      - MQTT_BROKER=mqtt-broker:1883

  qube-listener:
    build: ./services/mqtt-listeners/qube-listener
    environment:
      - MONGODB_URI=mongodb://mongo:27017/AMY
      - MQTT_BROKER=mqtt-broker:1883

  web-panel:
    build: ./services/mqtt-monitor/web-panel
    ports:
      - "8098:8098"
    environment:
      - MONGODB_URI=mongodb://mongo:27017/AMY

  websocket-server:
    build: ./services/mqtt-monitor/websocket-server
    ports:
      - "8099:8099"
    environment:
      - MONGODB_URI=mongodb://mongo:27017/AMY

  mongo:
    image: mongo:latest
    ports:
      - "27017:27017"
    volumes:
      - mongo_data:/data/db

  mqtt-broker:
    image: eclipse-mosquitto:latest
    ports:
      - "1883:1883"
      - "9001:9001"
```

#### 2. Environment Configuration
```bash
# Required environment variables
MONGODB_URI=mongodb://localhost:27017/AMY
MQTT_BROKER=localhost:1883
MQTT_USERNAME=your_username
MQTT_PASSWORD=your_password
REDIS_URL=redis://localhost:6379
```

### Production Deployment

#### 1. Security Considerations
- **MQTT Security**: Use TLS/SSL for MQTT connections
- **Database Security**: Enable MongoDB authentication
- **API Security**: Implement proper authentication
- **Network Security**: Use VPN for device connections

#### 2. Performance Optimization
- **Database Indexing**: Create indexes for frequently queried fields
- **Connection Pooling**: Optimize database connections
- **Caching**: Implement Redis caching for frequently accessed data
- **Load Balancing**: Use load balancer for high availability

#### 3. Monitoring and Logging
- **Health Checks**: Implement container health checks
- **Log Aggregation**: Use centralized logging (ELK stack)
- **Metrics Collection**: Monitor system performance
- **Alerting**: Set up alerts for system issues

### Backup and Recovery

#### 1. Database Backup
```bash
# MongoDB backup
mongodump --uri="mongodb://localhost:27017/AMY" --out=/backup/$(date +%Y%m%d)

# Restore from backup
mongorestore --uri="mongodb://localhost:27017/AMY" /backup/20240101/
```

#### 2. Configuration Backup
- **Docker Compose**: Backup docker-compose.yml
- **Environment Files**: Backup .env files
- **SSL Certificates**: Backup certificates and keys
- **Device Configurations**: Backup device mapping data

---

## Conclusion

This medical monitoring system provides comprehensive health monitoring capabilities through the integration of multiple IoT devices. The system architecture ensures reliable data processing, real-time monitoring, and emergency alert capabilities while maintaining data integrity and system performance.

### Key Benefits:
- **Multi-device Support**: Integrates AVA4, Kati Watch, and Qube-Vital devices
- **Real-time Monitoring**: Live data updates and emergency alerts
- **Comprehensive Storage**: Historical data tracking and analysis
- **Scalable Architecture**: Docker-based deployment for easy scaling
- **Emergency Response**: Immediate alert system for critical situations

### Future Enhancements:
- **AI/ML Integration**: Predictive health analytics
- **Mobile App**: Patient-facing mobile application
- **Advanced Analytics**: Trend analysis and health insights
- **Integration APIs**: Third-party system integration
- **Enhanced Security**: Advanced authentication and encryption

For technical support or questions, refer to the troubleshooting guide or contact the development team. 