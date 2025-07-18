# Unified Event Log Implementation

## Overview

The Unified Event Log is a comprehensive monitoring system that aggregates real-time events from all listeners (AVA4, Kati, Qube-Vital) and monitors in the Opera-GodEye panel. This provides complete visibility into the medical data processing pipeline, ensuring data integrity and proper storage to the database.

## Features

### 🔍 **Complete Data Flow Monitoring**
- **Real-time Event Tracking**: Monitor every step of data processing
- **Multi-Source Integration**: Events from all listeners and monitors
- **Database Storage Verification**: Confirm data is properly stored
- **Error Tracking**: Comprehensive error logging and alerting

### 📊 **Advanced Filtering & Search**
- **Source Filtering**: Filter by listener (AVA4, Kati, Qube, Monitor)
- **Status Filtering**: Success, Error, Warning, Info, Processing
- **Event Type Filtering**: Data Received, Processed, Stored, FHIR Converted, etc.
- **Time Range Filtering**: Last hour, 6 hours, 24 hours, week, custom
- **Text Search**: Search across device IDs, patients, event types, messages

### 📈 **Real-time Statistics**
- **24-hour Event Count**: Total events in the last 24 hours
- **Success/Error Rates**: Track processing success rates
- **Active Sources**: Number of active event sources
- **Live Updates**: Real-time statistics updates

### 🎯 **Event Types Tracked**

#### Data Flow Events
- `DATA_RECEIVED`: When MQTT messages are received
- `DATA_PROCESSED`: When data is successfully parsed and processed
- `DATA_STORED`: When data is stored in MongoDB
- `FHIR_CONVERTED`: When data is converted to FHIR R5 format

#### System Events
- `ERROR_OCCURRED`: When errors occur during processing
- `WARNING_OCCURRED`: When warnings are generated
- `ALERT_SENT`: When alerts are sent (Telegram, etc.)
- `SYSTEM_STATUS`: System health and status updates

## Architecture

### Backend Components

#### 1. **Event Log API** (`/api/event-log`)
```python
# POST /api/event-log - Receive events from listeners
{
    "timestamp": "2025-07-16T23:51:00Z",
    "source": "ava4-listener",
    "event_type": "DATA_PROCESSED",
    "status": "success",
    "device_id": "TKH-AVA3-14",
    "patient": "John Doe",
    "topic": "ESP32_BLE_GW_TX",
    "medical_data": "Heartbeat Status",
    "details": {
        "processing_time_ms": 45.2,
        "message": "Data processed successfully"
    }
}
```

#### 2. **Event Query API** (`/api/event-log`)
```python
# GET /api/event-log?source=ava4-listener&status=success&limit=50
{
    "success": true,
    "data": {
        "events": [...],
        "pagination": {
            "page": 1,
            "limit": 50,
            "total": 1250,
            "pages": 25
        }
    }
}
```

#### 3. **Statistics API** (`/api/event-log/stats`)
```python
# GET /api/event-log/stats
{
    "success": true,
    "data": {
        "total_24h": 1250,
        "sources": [
            {"_id": "ava4-listener", "count": 450},
            {"_id": "kati-listener", "count": 380},
            {"_id": "qube-listener", "count": 320},
            {"_id": "medical-monitor", "count": 100}
        ],
        "statuses": [
            {"_id": "success", "count": 1100},
            {"_id": "error", "count": 150}
        ]
    }
}
```

### Database Schema

#### Event Log Collection (`event_logs`)
```javascript
{
    "_id": ObjectId,
    "timestamp": ISODate,           // Event timestamp
    "server_timestamp": ISODate,     // Server receipt timestamp
    "source": String,               // Event source (listener/monitor)
    "event_type": String,           // Type of event
    "status": String,               // success/error/warning/info/processing
    "device_id": String,            // Device identifier
    "patient": String,              // Patient name/ID
    "topic": String,                // MQTT topic
    "medical_data": String,         // Type of medical data
    "details": Object,              // Additional event details
    "error": String                 // Error message (if applicable)
}
```

#### Indexes
- **TTL Index**: Auto-delete events older than 30 days
- **Source Index**: For filtering by source
- **Status Index**: For filtering by status
- **Timestamp Index**: For sorting and time-based queries

## Frontend Implementation

### Event Log Page (`/event-log`)

#### Features
- **Real-time Updates**: New events appear automatically via WebSocket
- **Responsive Design**: Works on desktop and mobile devices
- **Interactive Filters**: Easy-to-use filter controls
- **Event Details Modal**: Click any event to see full details
- **Export Functionality**: Download filtered events as CSV

#### UI Components
- **Statistics Cards**: Real-time event counts and success rates
- **Filter Bar**: Source, status, event type, time range, search
- **Events Table**: Sortable table with pagination
- **Event Details Modal**: JSON viewer for event details

### Navigation Integration
The Event Log is integrated into the main Opera-GodEye navigation:
```
Dashboard → Messages → Emergency Alerts → Devices → Patients → Data Flow Monitor → Event Log
```

## Listener Integration

### Event Logger Utility (`event_logger.py`)

#### Usage Example
```python
from event_logger import EventLogger

# Initialize logger
event_logger = EventLogger(source_name='ava4-listener')

# Log data received
event_logger.log_data_received(
    device_id="TKH-AVA3-14",
    topic="ESP32_BLE_GW_TX",
    payload_size=192,
    patient="John Doe",
    medical_data="Heartbeat Status"
)

# Log data processed
event_logger.log_data_processed(
    device_id="TKH-AVA3-14",
    topic="ESP32_BLE_GW_TX",
    processing_time=0.045,
    patient="John Doe",
    medical_data="Heartbeat Status"
)

# Log data stored
event_logger.log_data_stored(
    device_id="TKH-AVA3-14",
    collection="amy_devices",
    record_id="507f1f77bcf86cd799439011",
    patient="John Doe",
    medical_data="Heartbeat Status"
)

# Log errors
event_logger.log_error(
    device_id="TKH-AVA3-14",
    error_type="JSON_PARSE_ERROR",
    error_message="Invalid JSON format",
    topic="ESP32_BLE_GW_TX"
)
```

#### Convenience Functions
```python
from event_logger import log_data_received, log_error

# Quick logging
log_data_received("ava4-listener", "TKH-AVA3-14", "ESP32_BLE_GW_TX", 192)
log_error("ava4-listener", "TKH-AVA3-14", "JSON_PARSE_ERROR", "Invalid JSON")
```

## Implementation Status

### ✅ **Completed**
- [x] Backend API endpoints for event ingestion and querying
- [x] Database schema with TTL indexes
- [x] Frontend event log page with real-time updates
- [x] Event logger utility for listeners
- [x] Navigation integration
- [x] Statistics and filtering
- [x] Export functionality
- [x] WebSocket real-time updates

### 🔄 **In Progress**
- [ ] Integration with AVA4 listener
- [ ] Integration with Kati listener  
- [ ] Integration with Qube-Vital listener
- [ ] Integration with medical monitor

### 📋 **Next Steps**
1. **Deploy Event Logger**: Add event logging to all listeners
2. **Test Integration**: Verify events are being logged correctly
3. **Monitor Performance**: Ensure event logging doesn't impact performance
4. **Add Alerts**: Configure alerts for high error rates
5. **Documentation**: Create user guide for monitoring team

## Testing

### Test Script
Run the test script to verify functionality:
```bash
python test_event_log.py
```

### Manual Testing
1. **Access Event Log**: Navigate to `http://localhost:8098/event-log`
2. **Send Test Events**: Use the test script to send sample events
3. **Verify Real-time Updates**: Check that new events appear automatically
4. **Test Filters**: Try different filter combinations
5. **Export Data**: Test CSV export functionality

## Configuration

### Environment Variables
```bash
# Event Log API URL (for listeners)
EVENT_LOG_API_URL=http://localhost:8098

# Database TTL (days)
EVENT_LOG_TTL_DAYS=30

# Web Panel Port
WEB_PANEL_PORT=8098
```

### Database Configuration
The event log uses the same MongoDB instance as the main application:
```bash
MONGODB_URI=mongodb://localhost:27017/
MONGODB_DATABASE=AMY
```

## Monitoring & Maintenance

### Health Checks
- **API Health**: `GET /api/event-log/stats` - Should return 200
- **Database Health**: Check MongoDB connection and indexes
- **WebSocket Health**: Verify real-time updates are working

### Performance Considerations
- **TTL Index**: Automatically removes old events (30 days)
- **Pagination**: Limits results to prevent memory issues
- **Indexes**: Optimized for common query patterns
- **WebSocket**: Efficient real-time updates

### Backup & Recovery
- **Event Log Backup**: Include `event_logs` collection in MongoDB backups
- **Retention Policy**: Events are automatically deleted after 30 days
- **Recovery**: Restore from MongoDB backup if needed

## Troubleshooting

### Common Issues

#### Events Not Appearing
1. Check listener connectivity to event log API
2. Verify API endpoint is accessible
3. Check listener logs for error messages
4. Verify database connection

#### Performance Issues
1. Check MongoDB indexes are created
2. Monitor database query performance
3. Consider reducing event frequency if needed
4. Check for memory leaks in web interface

#### Real-time Updates Not Working
1. Verify WebSocket connection
2. Check browser console for errors
3. Verify Socket.IO is running
4. Check network connectivity

### Log Locations
- **Web Panel Logs**: Docker logs for `stardust-mqtt-panel`
- **Listener Logs**: Docker logs for respective listeners
- **Database Logs**: MongoDB logs
- **Application Logs**: Check `/var/log/` or Docker logs

## Benefits

### 🎯 **Complete Visibility**
- Track every step of data processing
- Identify bottlenecks and failures
- Monitor system health in real-time

### 🔒 **Data Integrity**
- Verify data is properly stored
- Track FHIR conversion success
- Monitor database operations

### 🚨 **Proactive Monitoring**
- Early error detection
- Performance monitoring
- System health tracking

### 📊 **Operational Intelligence**
- Success rate tracking
- Performance metrics
- Historical analysis

## Conclusion

The Unified Event Log provides comprehensive monitoring of the entire medical data processing pipeline, ensuring data integrity and providing complete visibility into system operations. This implementation enables proactive monitoring, quick issue resolution, and confidence that all medical data is being processed and stored correctly.

The system is designed to be scalable, performant, and easy to use, making it an essential tool for monitoring the Opera-GodEye medical data system. 