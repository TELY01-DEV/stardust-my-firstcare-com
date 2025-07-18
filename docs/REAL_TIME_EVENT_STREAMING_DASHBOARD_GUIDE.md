# Real-time Event Streaming Dashboard Guide

## 🚀 Overview

The Real-time Event Streaming Dashboard is an advanced monitoring interface that provides live visualization and analysis of all system events. It offers real-time event streaming, interactive charts, event correlation analysis, and comprehensive filtering capabilities.

## 🎯 Key Features

### 1. **Live Event Stream**
- Real-time event display with automatic updates
- Event categorization by source, type, and status
- Visual indicators for event priority and severity
- Click-to-view detailed event information

### 2. **Real-time Analytics**
- Live metrics dashboard with key performance indicators
- Events per minute tracking
- Error rate monitoring
- Active device count
- Trend analysis with visual indicators

### 3. **Interactive Charts**
- **Events Over Time Chart**: Line chart showing event frequency over time
- **Event Distribution Chart**: Doughnut chart showing events by source
- Real-time chart updates as new events arrive
- Responsive design for different screen sizes

### 4. **Event Timeline**
- Visual timeline of recent events
- Color-coded by event source
- Interactive event dots with hover information
- Automatic timeline updates

### 5. **Event Correlation**
- Analysis of event relationships and patterns
- Device-patient correlation mapping
- Event sequence analysis
- Error pattern identification

### 6. **Advanced Filtering**
- Filter by event source (AVA4, Kati, Qube, System)
- Filter by event type (Vitals, Alerts, Status, Data, System)
- Filter by status (Success, Error, Warning, Info)
- Time range filtering (5min, 15min, 30min, 1hour, All time)

## 🏗️ Architecture

### Frontend Components
```
┌─────────────────────────────────────────────────────────────┐
│                    Real-time Event Stream                   │
├─────────────────────────────────────────────────────────────┤
│  Live Event Display  │  Event Timeline  │  Correlation     │
│  - Auto-updating     │  - Visual dots   │  - Pattern       │
│  - Priority colors   │  - Color-coded   │  - Analysis      │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                    Real-time Analytics                      │
├─────────────────────────────────────────────────────────────┤
│  Metrics Cards      │  Events Chart     │  Distribution    │
│  - Total Events     │  - Time series    │  - Pie chart     │
│  - Events/Min       │  - Live updates   │  - Source breakdown│
│  - Error Rate       │  - Responsive     │  - Interactive   │
│  - Active Devices   │  - Zoom/pan       │  - Hover details │
└─────────────────────────────────────────────────────────────┘
```

### Backend API Endpoints

#### 1. **Streaming Events API**
```http
GET /api/streaming/events
```
**Parameters:**
- `limit` (int): Number of events to retrieve (default: 100)
- `source` (string): Filter by event source
- `event_type` (string): Filter by event type
- `status` (string): Filter by event status
- `time_range` (string): Time range in minutes or 'all'

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "timestamp": "2024-01-15T10:30:45.123Z",
      "source": "ava4-listener",
      "event_type": "DATA_RECEIVED",
      "status": "success",
      "device_id": "AVA4_001",
      "patient_id": "PAT_001",
      "message": "Blood pressure data received",
      "data": {...}
    }
  ],
  "timestamp": "2024-01-15T10:30:45.123Z"
}
```

#### 2. **Streaming Statistics API**
```http
GET /api/streaming/stats
```
**Response:**
```json
{
  "success": true,
  "data": {
    "total_events": 1250,
    "events_per_minute": 8.5,
    "events_last_minute": 12,
    "error_rate": 2.3,
    "active_devices": 15,
    "sources": [
      {"_id": "ava4-listener", "count": 450},
      {"_id": "kati-listener", "count": 380},
      {"_id": "qube-listener", "count": 320},
      {"_id": "medical-monitor", "count": 100}
    ],
    "event_types": [
      {"_id": "DATA_RECEIVED", "count": 600},
      {"_id": "DATA_PROCESSED", "count": 400},
      {"_id": "DATA_STORED", "count": 200},
      {"_id": "ERROR_OCCURRED", "count": 50}
    ],
    "timeline_events": [...]
  }
}
```

#### 3. **Event Correlation API**
```http
GET /api/streaming/correlation
```
**Response:**
```json
{
  "success": true,
  "data": {
    "device_patient_pairs": {
      "AVA4_001_PAT_001": {
        "device_id": "AVA4_001",
        "patient_id": "PAT_001",
        "event_count": 45,
        "last_event": "2024-01-15T10:30:45.123Z"
      }
    },
    "event_sequences": {
      "ava4-listener_DATA_RECEIVED": [
        {
          "event_type": "DATA_PROCESSED",
          "time_diff": 2.5
        }
      ]
    },
    "error_patterns": {
      "ava4-listener_DATA_RECEIVED": {
        "count": 3,
        "last_occurrence": "2024-01-15T10:25:30.456Z",
        "common_causes": ["Invalid data format", "Missing patient ID"]
      }
    }
  }
}
```

### Socket.IO Events

#### 1. **Client to Server**
```javascript
// Request streaming events
socket.emit('get_streaming_events');

// Request streaming statistics
socket.emit('get_streaming_stats');
```

#### 2. **Server to Client**
```javascript
// Receive streaming events
socket.on('streaming_events_response', function(data) {
  console.log('Streaming events:', data.events);
});

// Receive streaming statistics
socket.on('streaming_stats_response', function(data) {
  console.log('Streaming stats:', data.stats);
});

// Receive new event updates
socket.on('event_log_update', function(event) {
  console.log('New event:', event);
});
```

## 🎨 User Interface

### Dashboard Layout
```
┌─────────────────────────────────────────────────────────────┐
│                    Navigation Bar                           │
│ [Dashboard] [Data Flow] [Devices] [Patients] [Event Log]   │
│ [Live Stream] [Emergency]                                   │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                    Control Panel                            │
│ [Source Filter] [Type Filter] [Status Filter] [Time Range] │
│ [Pause Stream] [Clear Stream] [Export Data]                │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                    Real-time Metrics                        │
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────┐ │
│ │ Total Events│ │ Events/Min  │ │ Error Rate  │ │ Devices │ │
│ │    1,250    │ │    8.5      │ │    2.3%     │ │   15    │ │
│ │   +12/min   │ │   Stable    │ │   Good      │ │ Online  │ │
│ └─────────────┘ └─────────────┘ └─────────────┘ └─────────┘ │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                    Charts Row                               │
│ ┌─────────────────────────┐ ┌─────────────────────────────┐ │
│ │     Events Over Time    │ │    Event Distribution       │ │
│ │     [Line Chart]        │ │      [Doughnut Chart]       │ │
│ └─────────────────────────┘ └─────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                    Event Stream & Timeline                  │
│ ┌─────────────────────────────────┐ ┌─────────────────────┐ │
│ │        Live Event Stream        │ │   Event Timeline    │ │
│ │     [Real-time events]          │ │   [Visual dots]     │ │
│ │                                 │ │                     │ │
│ │                                 │ │   Event Correlation │ │
│ │                                 │ │   [Pattern analysis]│ │
│ └─────────────────────────────────┘ └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Event Display Format
Each event in the stream shows:
- **Timestamp**: When the event occurred
- **Source Badge**: Color-coded source identifier
- **Event Type Indicator**: Small colored dot
- **Status Badge**: Success/Error/Warning/Info
- **Message**: Human-readable event description
- **Details**: Device ID, event type, additional info

### Color Coding
- **Sources**: 
  - AVA4: Green (#28a745)
  - Kati: Blue (#17a2b8)
  - Qube: Yellow (#ffc107)
  - System: Red (#dc3545)
- **Status**:
  - Success: Green
  - Error: Red
  - Warning: Yellow
  - Info: Blue
- **Priority**:
  - Critical: Red border
  - Warning: Yellow border
  - Success: Green border

## 🔧 Configuration

### Environment Variables
```bash
# Web Panel Configuration
MONGODB_URI=mongodb://localhost:27017
MONGODB_DATABASE=AMY

# Event Log Configuration
EVENT_LOG_TTL_DAYS=30
EVENT_LOG_COLLECTION=event_logs

# Real-time Configuration
SOCKETIO_CORS_ALLOWED_ORIGINS=*
```

### Performance Settings
```javascript
// Client-side configuration
const STREAMING_CONFIG = {
  maxEvents: 100,           // Maximum events in stream
  updateInterval: 5000,     // Stats update interval (ms)
  chartUpdateInterval: 1000, // Chart update interval (ms)
  timelineMaxEvents: 50,    // Maximum timeline events
  autoScroll: true,         // Auto-scroll to new events
  soundAlerts: false        // Sound alerts for critical events
};
```

## 📊 Monitoring & Analytics

### Key Metrics Tracked
1. **Event Volume**
   - Total events per time period
   - Events per minute rate
   - Peak event times

2. **System Health**
   - Error rate percentage
   - Success rate trends
   - Processing latency

3. **Device Activity**
   - Active device count
   - Device-specific event rates
   - Device health status

4. **Data Quality**
   - Data validation success rate
   - Missing data incidents
   - Data format errors

### Alert Thresholds
```javascript
const ALERT_THRESHOLDS = {
  errorRate: 5.0,        // Alert if error rate > 5%
  eventsPerMinute: 100,  // Alert if events/min > 100
  inactiveDevices: 0,    // Alert if no devices active
  processingDelay: 30    // Alert if processing delay > 30s
};
```

## 🚀 Deployment

### 1. **Build and Deploy**
```bash
# Navigate to project root
cd /path/to/stardust-my-firstcare-com

# Build and start MQTT monitor services
docker compose -f services/mqtt-monitor/docker-compose.yml up -d --build
```

### 2. **Access the Dashboard**
- **URL**: http://your-server:8080/event-streaming
- **Port**: 8080 (web panel)
- **Authentication**: JWT-based (temporarily disabled for testing)

### 3. **Verify Services**
```bash
# Check service status
docker compose -f services/mqtt-monitor/docker-compose.yml ps

# Check logs
docker logs mqtt-monitor-panel
```

## 🧪 Testing

### Test Script
```bash
# Run the test script
python test_event_streaming_dashboard.py
```

### Manual Testing Checklist
- [ ] Dashboard loads without errors
- [ ] Real-time events appear in stream
- [ ] Charts update automatically
- [ ] Filters work correctly
- [ ] Event details modal opens
- [ ] Export functionality works
- [ ] Timeline shows events
- [ ] Correlation analysis displays
- [ ] Metrics update in real-time
- [ ] Responsive design works on mobile

## 🔍 Troubleshooting

### Common Issues

#### 1. **No Events Appearing**
```bash
# Check if event log API is working
curl http://localhost:8080/api/event-log

# Check MongoDB connection
docker exec -it mqtt-monitor-panel python -c "
import pymongo
client = pymongo.MongoClient('mongodb://localhost:27017')
print('MongoDB connected:', client.admin.command('ping'))
"
```

#### 2. **Charts Not Updating**
- Check browser console for JavaScript errors
- Verify Socket.IO connection status
- Check if real-time events are being received

#### 3. **Performance Issues**
- Reduce event history size
- Increase update intervals
- Check server resources

#### 4. **Filter Not Working**
- Verify filter parameters are correct
- Check API response for errors
- Clear browser cache

### Debug Mode
```javascript
// Enable debug logging
localStorage.setItem('debug', 'true');
// Refresh page to see debug information
```

## 🔮 Future Enhancements

### Planned Features
1. **Advanced Analytics**
   - Machine learning-based anomaly detection
   - Predictive event forecasting
   - Custom alert rules

2. **Enhanced Visualizations**
   - 3D event correlation graphs
   - Heat maps for event patterns
   - Geographic event mapping

3. **Real-time Collaboration**
   - Multi-user event annotations
   - Shared event investigations
   - Team alert management

4. **Integration Features**
   - Slack/Teams notifications
   - Email alert integration
   - External monitoring system integration

5. **Advanced Filtering**
   - Custom filter presets
   - Saved filter configurations
   - Advanced search queries

6. **Performance Optimizations**
   - Event data compression
   - Lazy loading for large datasets
   - Caching strategies

## 📚 API Reference

### Complete API Documentation
For detailed API documentation, see the OpenAPI specification at:
```
http://localhost:8080/docs
```

### WebSocket Events Reference
For complete Socket.IO event documentation, see:
```
docs/WEBSOCKET_EVENTS_REFERENCE.md
```

## 🤝 Contributing

### Development Setup
1. Clone the repository
2. Install dependencies
3. Set up development environment
4. Run tests
5. Submit pull request

### Code Standards
- Follow PEP 8 for Python code
- Use ESLint for JavaScript
- Write comprehensive tests
- Document all new features

---

**Last Updated**: January 2024  
**Version**: 1.0.0  
**Maintainer**: My FirstCare Development Team 