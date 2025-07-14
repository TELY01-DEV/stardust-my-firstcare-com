# Device Status Database Design
## Comprehensive Device Status Management System

### 🎯 **Purpose**
Create a dedicated database collection for tracking and reporting device status across all IoT medical devices (Kati Watch, AVA4, Qube-Vital).

### 📊 **Database Collection: `device_status`**

#### **Document Structure:**
```json
{
  "_id": ObjectId,
  "device_id": "string",           // Unique device identifier (IMEI/MAC)
  "device_type": "string",         // "Kati", "AVA4", "Qube-Vital"
  "patient_id": ObjectId,          // Associated patient (if mapped)
  "status": {
    "online": boolean,             // Device online/offline status
    "last_seen": datetime,         // Last communication timestamp
    "battery_level": number,       // Battery percentage (0-100)
    "signal_strength": number,     // Signal strength (0-100)
    "working_mode": number,        // Device working mode
    "satellites": number,          // GPS satellites (Kati)
    "error_code": string,          // Any error codes
    "firmware_version": string,    // Device firmware version
    "hardware_status": string      // "OK", "WARNING", "ERROR"
  },
  "location": {
    "latitude": number,
    "longitude": number,
    "speed": number,
    "header": number,
    "accuracy": number,
    "last_updated": datetime
  },
  "health_metrics": {
    "last_heart_rate": number,
    "last_blood_pressure": {
      "systolic": number,
      "diastolic": number
    },
    "last_spo2": number,
    "last_temperature": number,
    "last_step_count": number,
    "last_sleep_data": object
  },
  "communication": {
    "mqtt_topic": string,          // Last MQTT topic
    "message_count": number,       // Total messages received
    "last_message_size": number,   // Size of last message
    "connection_quality": string   // "EXCELLENT", "GOOD", "POOR"
  },
  "alerts": {
    "sos_triggered": boolean,
    "fall_detected": boolean,
    "low_battery": boolean,
    "poor_signal": boolean,
    "last_alert_time": datetime
  },
  "metadata": {
    "created_at": datetime,
    "updated_at": datetime,
    "created_by": "system",
    "last_processed_by": "string"  // Which listener processed it
  }
}
```

### 🔧 **Implementation Plan**

#### **1. Create Device Status Service**
```python
class DeviceStatusService:
    def __init__(self, mongodb_uri, database_name):
        self.client = MongoClient(mongodb_uri)
        self.db = self.client[database_name]
    
    def update_device_status(self, device_id, device_type, status_data):
        """Update or create device status record"""
        
    def get_device_status(self, device_id):
        """Get current device status"""
        
    def get_all_devices_status(self, device_type=None):
        """Get status of all devices or by type"""
        
    def get_offline_devices(self, hours_offline=24):
        """Get devices that haven't reported in X hours"""
        
    def get_low_battery_devices(self, threshold=20):
        """Get devices with low battery"""
        
    def get_poor_signal_devices(self, threshold=30):
        """Get devices with poor signal"""
```

#### **2. Update Data Processor**
```python
def update_device_status(self, device_id, device_type, status_data):
    """Update device status when processing MQTT messages"""
    device_status_service = DeviceStatusService(self.mongodb_uri, self.mongodb_database)
    device_status_service.update_device_status(device_id, device_type, status_data)
```

#### **3. Status Update Triggers**
- **Kati Watch:**
  - Heartbeat messages → Update battery, signal, working mode
  - Location messages → Update GPS coordinates
  - Online triggers → Update online status
  - Vital signs → Update health metrics
  
- **AVA4:**
  - Heartbeat messages → Update online status, device health
  - Sub-device data → Update connected devices status
  
- **Qube-Vital:**
  - Heartbeat messages → Update device status
  - Medical data → Update health metrics

### 📈 **Benefits**

#### **1. Real-time Monitoring**
- Dashboard showing all device statuses
- Quick identification of offline devices
- Battery level monitoring
- Signal strength tracking

#### **2. Historical Analysis**
- Device reliability trends
- Battery life analysis
- Signal quality patterns
- Usage statistics

#### **3. Alert System**
- Low battery alerts
- Poor signal warnings
- Device offline notifications
- Emergency alert tracking

#### **4. Reporting**
- Device health reports
- Patient device status reports
- System reliability metrics
- Maintenance scheduling

### 🚀 **Implementation Steps**

1. **Create Device Status Service**
2. **Update Data Processor** to call status service
3. **Create Database Indexes** for efficient querying
4. **Add Status Update Calls** to all MQTT listeners
5. **Create Status Dashboard** for monitoring
6. **Implement Alert System** for critical status changes

### 📋 **Database Indexes**
```javascript
// Primary index on device_id
db.device_status.createIndex({"device_id": 1}, {unique: true})

// Index for patient queries
db.device_status.createIndex({"patient_id": 1})

// Index for device type queries
db.device_status.createIndex({"device_type": 1})

// Index for status queries
db.device_status.createIndex({"status.online": 1})
db.device_status.createIndex({"status.last_seen": 1})

// Index for alert queries
db.device_status.createIndex({"alerts.sos_triggered": 1})
db.device_status.createIndex({"alerts.low_battery": 1})

// Compound index for monitoring
db.device_status.createIndex({
    "device_type": 1, 
    "status.online": 1, 
    "status.last_seen": 1
})
```

### 🎯 **Expected Outcomes**

1. **Better Device Management:** Centralized status tracking
2. **Improved Monitoring:** Real-time device health visibility
3. **Proactive Alerts:** Early warning for device issues
4. **Data Analytics:** Historical device performance analysis
5. **Patient Safety:** Better tracking of emergency-capable devices

This design will provide a robust foundation for comprehensive device status management and reporting. 