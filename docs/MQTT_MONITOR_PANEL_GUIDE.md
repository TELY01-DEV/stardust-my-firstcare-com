# 🖥️ MQTT Monitor Panel - Real-time Dashboard

## 📋 **Overview**

The MQTT Monitor Panel is a real-time web dashboard that displays live MQTT messages from medical devices and shows patient mapping status. It provides comprehensive monitoring for:

- **AVA4 + Medical Devices** - Blood pressure, glucometer, oximeter, etc.
- **Kati Watch** - Vital signs, location, emergency alerts
- **Qube-Vital** - Hospital-based medical devices with patient registration status

## 🏗️ **Architecture**

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   MQTT Broker   │    │  WebSocket      │    │   Web Panel     │
│  (adam.amy.care)│───▶│   Server        │───▶│   (Port 8080)   │
└─────────────────┘    │  (Port 8081)    │    └─────────────────┘
                       └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   MongoDB       │
                       │   (Patient DB)  │
                       └─────────────────┘
```

## 🚀 **Deployment**

### **Step 1: Build and Deploy**

```bash
# Navigate to project root
cd /path/to/stardust-my-firstcare-com

# Build and start MQTT monitor services
docker compose -f services/mqtt-monitor/docker-compose.yml up -d --build
```

### **Step 2: Access the Dashboard**

- **Web Panel**: http://your-server:8080
- **WebSocket Server**: ws://your-server:8081

### **Step 3: Verify Services**

```bash
# Check service status
docker compose -f services/mqtt-monitor/docker-compose.yml ps

# Check logs
docker logs mqtt-monitor-panel
docker logs mqtt-monitor-websocket
```

## 📊 **Dashboard Features**

### **1. Real-time Statistics Cards**
- **Total Patients**: Number of patients in the database
- **AVA4 Devices**: Number of AVA4 devices registered
- **Kati Watches**: Number of Kati Watch devices
- **Qube-Vital Devices**: Number of Qube-Vital devices

### **2. Live MQTT Message Stream**
- **Real-time Updates**: Messages appear instantly as they arrive
- **Device Filtering**: Filter by device type (All, AVA4, Kati, Qube-Vital)
- **Message Details**: Click any message to view full details
- **Status Indicators**: Visual status for processed, patient_not_found, error

### **3. Patient Mapping Status**
- **Success Rate**: Real-time mapping success percentage
- **Recent Mappings**: Last 10 patient mapping attempts
- **Mapping Details**: Shows mapping type and values used

### **4. Device Status Panel**
- **MQTT Broker**: Connection status to adam.amy.care
- **MongoDB**: Database connection status
- **WebSocket**: Real-time communication status

## 🔍 **Message Processing**

### **AVA4 Messages**
```
Topic: ESP32_BLE_GW_TX (Status)
- Device heartbeat and online status
- Maps AVA4 MAC address to patient

Topic: dusun_sub (Medical Data)
- Blood pressure, glucose, SpO2, temperature, weight, etc.
- Maps device MAC to patient via amy_devices collection
```

### **Kati Watch Messages**
```
Topics: iMEDE_watch/VitalSign, iMEDE_watch/AP55, iMEDE_watch/hb, etc.
- Vital signs, location, emergency alerts
- Maps IMEI to patient via watches collection
```

### **Qube-Vital Messages**
```
Topic: CM4_BLE_GW_TX
- Hospital-based medical devices
- Maps citizen ID to patient (auto-creates unregistered patients)
- Shows hospital mapping via mac_hv01_box
```

## 🎨 **User Interface**

### **Message Display**
Each message shows:
- **Timestamp**: When the message was received
- **Topic**: MQTT topic name
- **Device Type**: AVA4, Kati Watch, or Qube-Vital
- **Status**: processed, patient_not_found, or error
- **Preview**: Key medical data or device information
- **Patient Mapping**: Success/failure with patient details

### **Color Coding**
- **AVA4**: Green badges and borders
- **Kati Watch**: Blue badges and borders  
- **Qube-Vital**: Yellow badges and borders
- **Success**: Green backgrounds
- **Errors**: Red backgrounds
- **Warnings**: Yellow backgrounds

### **Interactive Features**
- **Click Messages**: View detailed JSON payload
- **Filter by Device**: Show only specific device types
- **Real-time Updates**: No page refresh needed
- **Responsive Design**: Works on desktop and mobile

## 📈 **Monitoring Capabilities**

### **Real-time Metrics**
- **Message Processing Rate**: Messages per minute
- **Patient Mapping Success Rate**: Percentage of successful mappings
- **Device Connection Status**: Live connection indicators
- **Error Tracking**: Failed processing attempts

### **Data Visualization**
- **Progress Bars**: Mapping success rates
- **Status Badges**: Connection and processing status
- **Timeline View**: Chronological message history
- **Statistics Cards**: Key metrics at a glance

## 🔧 **Configuration**

### **Environment Variables**

| Variable | Description | Default |
|----------|-------------|---------|
| `MQTT_BROKER_HOST` | MQTT broker hostname | `adam.amy.care` |
| `MQTT_BROKER_PORT` | MQTT broker port | `1883` |
| `MQTT_USERNAME` | MQTT username | `webapi` |
| `MQTT_PASSWORD` | MQTT password | `Sim!4433` |
| `MONGODB_URI` | MongoDB connection string | Required |
| `WEB_PORT` | Web panel port | `8080` |
| `WS_PORT` | WebSocket port | `8081` |

### **MQTT Topics Monitored**
- `ESP32_BLE_GW_TX` - AVA4 status messages
- `dusun_sub` - AVA4 medical device data
- `iMEDE_watch/#` - All Kati Watch topics
- `CM4_BLE_GW_TX` - Qube-Vital data

## 🛠️ **Troubleshooting**

### **Common Issues**

**1. WebSocket Connection Failed**
```bash
# Check WebSocket server logs
docker logs mqtt-monitor-websocket

# Verify port 8081 is accessible
netstat -tlnp | grep 8081
```

**2. No MQTT Messages**
```bash
# Check MQTT connection
docker logs mqtt-monitor-websocket | grep "Connected to MQTT"

# Verify MQTT broker credentials
docker exec mqtt-monitor-websocket env | grep MQTT
```

**3. Patient Mapping Failures**
```bash
# Check MongoDB connection
docker logs mqtt-monitor-websocket | grep "MongoDB"

# Verify patient data exists
docker exec -it mongodb mongo --eval "db.patients.count()"
```

### **Log Monitoring**

```bash
# Monitor real-time logs
docker logs -f mqtt-monitor-panel
docker logs -f mqtt-monitor-websocket

# Search for errors
docker logs mqtt-monitor-websocket | grep ERROR
docker logs mqtt-monitor-panel | grep ERROR
```

### **Performance Monitoring**

```bash
# Check resource usage
docker stats mqtt-monitor-panel mqtt-monitor-websocket

# Monitor message processing rate
docker logs mqtt-monitor-websocket | grep "Received MQTT message" | wc -l
```

## 🔒 **Security Considerations**

### **Access Control**
- **Network Security**: Restrict access to monitoring ports
- **Authentication**: Consider adding login for sensitive data
- **HTTPS**: Use SSL/TLS for production deployment

### **Data Privacy**
- **Patient Data**: Ensure HIPAA compliance
- **Logging**: Avoid logging sensitive patient information
- **Access Logs**: Monitor who accesses the dashboard

## 📱 **Mobile Access**

The dashboard is fully responsive and works on:
- **Desktop Browsers**: Chrome, Firefox, Safari, Edge
- **Mobile Browsers**: iOS Safari, Android Chrome
- **Tablet Browsers**: iPad Safari, Android tablets

## 🔄 **Updates and Maintenance**

### **Service Restart**
```bash
# Restart all services
docker compose -f services/mqtt-monitor/docker-compose.yml restart

# Restart specific service
docker compose -f services/mqtt-monitor/docker-compose.yml restart mqtt-monitor-panel
```

### **Configuration Updates**
```bash
# Update environment variables
docker compose -f services/mqtt-monitor/docker-compose.yml down
# Edit docker-compose.yml
docker compose -f services/mqtt-monitor/docker-compose.yml up -d
```

### **Data Backup**
```bash
# Backup message history (if stored in database)
docker exec mongodb mongodump --collection mqtt_messages --db AMY

# Backup configuration
cp services/mqtt-monitor/docker-compose.yml backup/
```

## 🎯 **Use Cases**

### **1. Real-time Monitoring**
- Monitor live medical device data
- Track patient mapping success rates
- Identify device connection issues

### **2. Troubleshooting**
- Debug patient mapping failures
- Identify MQTT message processing errors
- Monitor device connectivity

### **3. Quality Assurance**
- Verify data integrity
- Monitor processing performance
- Track system health

### **4. Development Testing**
- Test new device integrations
- Validate patient mapping logic
- Monitor system behavior

## 📚 **API Endpoints**

### **Web Panel APIs**
- `GET /api/statistics` - Get monitoring statistics
- `GET /api/patients` - Get patient list
- `GET /api/devices` - Get device mappings

### **WebSocket Events**
- `mqtt_message` - Real-time MQTT message updates
- `statistics` - Updated statistics
- `initial_data` - Initial data on connection

## 🚀 **Scaling Considerations**

### **Horizontal Scaling**
- **Multiple WebSocket Servers**: Load balance WebSocket connections
- **Database Sharding**: Distribute patient data across MongoDB shards
- **Message Queuing**: Use Redis for message buffering

### **Performance Optimization**
- **Message Filtering**: Filter messages at the source
- **Data Compression**: Compress WebSocket messages
- **Caching**: Cache frequently accessed patient data

---

**🏥 My FirstCare MQTT Monitor Panel**  
*Real-time medical device data monitoring and patient mapping visualization*

**Status**: ✅ **Ready for Production**  
**Real-time Updates**: ✅ **WebSocket-powered**  
**Patient Mapping**: ✅ **Live tracking**  
**Device Support**: ✅ **All three device types** 