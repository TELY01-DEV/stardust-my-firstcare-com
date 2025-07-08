# Real-time Features Implementation Guide

## Overview

This guide documents the real-time features implemented in the My FirstCare Opera Panel API, including WebSocket support, Server-Sent Events (SSE), and real-time device data streaming.

## Architecture

### Components

1. **WebSocket Manager** (`app/services/websocket_manager.py`)
   - Manages WebSocket connections
   - Room-based subscriptions
   - User-to-connection mapping
   - Message broadcasting

2. **Real-time Event Handler** (`app/services/realtime_events.py`)
   - Redis Pub/Sub integration
   - Event routing
   - Event publishing utilities

3. **Real-time Routes** (`app/routes/realtime.py`)
   - WebSocket endpoints
   - SSE endpoints
   - Statistics and monitoring

## WebSocket Endpoints

### 1. Main WebSocket Endpoint
```
ws://localhost:5054/realtime/ws?token=YOUR_JWT_TOKEN
```

**Features:**
- Authenticated connections
- Dynamic room subscriptions
- Bidirectional communication

**Message Types:**
```json
// Subscribe to a room
{
  "type": "subscribe",
  "room": "patient:507f1f77bcf86cd799439011:vitals"
}

// Unsubscribe from a room
{
  "type": "unsubscribe",
  "room": "patient:507f1f77bcf86cd799439011:vitals"
}

// Ping/Pong for keepalive
{
  "type": "ping"
}
```

### 2. Patient-Specific WebSocket
```
ws://localhost:5054/realtime/ws/patient/{patient_id}?token=YOUR_JWT_TOKEN
```

**Auto-subscriptions:**
- `patient:{patient_id}` - General updates
- `patient:{patient_id}:vitals` - Vital signs
- `patient:{patient_id}:alerts` - Alerts

### 3. Hospital-Specific WebSocket
```
ws://localhost:5054/realtime/ws/hospital/{hospital_id}?token=YOUR_JWT_TOKEN
```

**Auto-subscriptions:**
- `hospital:{hospital_id}` - General updates
- `hospital:{hospital_id}:alerts` - Hospital alerts
- `hospital:{hospital_id}:devices` - Device status

## Server-Sent Events (SSE) Endpoints

### 1. Global Events
```
GET /realtime/events
Authorization: Bearer YOUR_JWT_TOKEN
```

### 2. Patient Events
```
GET /realtime/events/patient/{patient_id}
Authorization: Bearer YOUR_JWT_TOKEN
```

### 3. Hospital Events
```
GET /realtime/events/hospital/{hospital_id}
Authorization: Bearer YOUR_JWT_TOKEN
```

### 4. Device Events
```
GET /realtime/events/device/{device_type}/{device_id}
Authorization: Bearer YOUR_JWT_TOKEN
```

## Event Types

### Patient Events
- `patient.vitals.update` - Vital signs updated
- `patient.alert` - Patient alert triggered
- `patient.status.change` - Patient status changed
- `patient.admission` - Patient admitted
- `patient.discharge` - Patient discharged

### Device Events
- `device.data.update` - Device data received
- `device.status.change` - Device status changed
- `device.connected` - Device connected
- `device.disconnected` - Device disconnected
- `device.alert` - Device alert triggered

### Hospital Events
- `hospital.alert` - Hospital-wide alert
- `hospital.capacity.update` - Bed capacity updated
- `hospital.emergency` - Emergency situation

### System Events
- `system.alert` - System-wide alert
- `system.maintenance` - Maintenance notification
- `system.update` - System update notification

## Integration Example

### Device Data with Real-time Updates

When device data is created via the API, it automatically publishes real-time events:

```python
# In device_crud.py
# Publish device data update
await realtime_events.publish_device_data(
    device_type=data.device_type,
    device_id=data.device_id,
    data_type=data.data_type,
    values=data.values
)

# Publish patient vitals update
if data.data_type in ["blood_pressure", "heart_rate", "temperature", "spo2"]:
    await realtime_events.publish_patient_vitals(
        patient_id=patient_id,
        vitals_data={
            data.data_type: data.values,
            "device_id": data.device_id,
            "device_type": data.device_type,
            "timestamp": data.timestamp.isoformat()
        }
    )

# Trigger alerts for abnormal values
if data.data_type == "blood_pressure":
    systolic = data.values.get("systolic", 0)
    diastolic = data.values.get("diastolic", 0)
    if systolic > 140 or diastolic > 90:
        await realtime_events.publish_patient_alert(
            patient_id=patient_id,
            alert_type="high_blood_pressure",
            severity="warning",
            message=f"High blood pressure detected: {systolic}/{diastolic}",
            data={
                "systolic": systolic,
                "diastolic": diastolic,
                "device_id": data.device_id
            }
        )
```

## Client Implementation Examples

### JavaScript WebSocket Client

```javascript
// Connect to WebSocket
const token = 'YOUR_JWT_TOKEN';
const ws = new WebSocket(`ws://localhost:5054/realtime/ws?token=${token}`);

// Connection opened
ws.addEventListener('open', (event) => {
    console.log('Connected to WebSocket');
    
    // Subscribe to patient vitals
    ws.send(JSON.stringify({
        type: 'subscribe',
        room: 'patient:507f1f77bcf86cd799439011:vitals'
    }));
});

// Listen for messages
ws.addEventListener('message', (event) => {
    const data = JSON.parse(event.data);
    
    switch(data.type) {
        case 'vitals_update':
            console.log('Vitals updated:', data.data);
            updateVitalsDisplay(data.data);
            break;
            
        case 'patient_alert':
            console.log('Alert:', data.data);
            showAlert(data.data);
            break;
            
        case 'subscription':
            console.log('Subscription status:', data);
            break;
    }
});

// Error handling
ws.addEventListener('error', (event) => {
    console.error('WebSocket error:', event);
});

// Connection closed
ws.addEventListener('close', (event) => {
    console.log('WebSocket closed:', event.code, event.reason);
});

// Keep connection alive
setInterval(() => {
    if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'ping' }));
    }
}, 30000);
```

### JavaScript SSE Client

```javascript
// Connect to SSE
const token = 'YOUR_JWT_TOKEN';
const eventSource = new EventSource(
    `/realtime/events/patient/507f1f77bcf86cd799439011`,
    {
        headers: {
            'Authorization': `Bearer ${token}`
        }
    }
);

// Connection opened
eventSource.addEventListener('connected', (event) => {
    const data = JSON.parse(event.data);
    console.log('Connected to SSE:', data);
});

// Listen for vitals updates
eventSource.addEventListener('patient.vitals.update', (event) => {
    const data = JSON.parse(event.data);
    console.log('Vitals updated:', data);
    updateVitalsDisplay(data);
});

// Listen for alerts
eventSource.addEventListener('patient.alert', (event) => {
    const data = JSON.parse(event.data);
    console.log('Alert received:', data);
    showAlert(data);
});

// Error handling
eventSource.addEventListener('error', (event) => {
    if (event.readyState === EventSource.CLOSED) {
        console.log('SSE connection closed');
    } else {
        console.error('SSE error:', event);
    }
});
```

### Python WebSocket Client

```python
import asyncio
import websockets
import json

async def patient_monitor():
    token = 'YOUR_JWT_TOKEN'
    uri = f'ws://localhost:5054/realtime/ws/patient/507f1f77bcf86cd799439011?token={token}'
    
    async with websockets.connect(uri) as websocket:
        print("Connected to patient WebSocket")
        
        # Listen for messages
        async for message in websocket:
            data = json.loads(message)
            
            if data['type'] == 'vitals_update':
                print(f"Vitals updated: {data['data']}")
                await process_vitals(data['data'])
                
            elif data['type'] == 'patient_alert':
                print(f"Alert: {data['data']}")
                await handle_alert(data['data'])
                
            elif data['type'] == 'ping':
                # Respond to ping
                await websocket.send(json.dumps({'type': 'pong'}))

async def process_vitals(vitals_data):
    # Process vital signs data
    pass

async def handle_alert(alert_data):
    # Handle patient alert
    pass

# Run the monitor
asyncio.run(patient_monitor())
```

## Testing Real-time Features

### 1. Test Event Publishing

Use the test endpoint to publish events:

```bash
curl -X POST http://localhost:5054/realtime/test/publish \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "patient.vitals.update",
    "patient_id": "507f1f77bcf86cd799439011",
    "vitals": {
      "blood_pressure": {"systolic": 120, "diastolic": 80},
      "heart_rate": 72,
      "temperature": 36.5
    }
  }'
```

### 2. WebSocket Connection Statistics

Get real-time connection statistics:

```bash
curl -X GET http://localhost:5054/realtime/stats \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

Response:
```json
{
  "success": true,
  "data": {
    "total_connections": 15,
    "unique_users": 8,
    "active_rooms": 12,
    "connections_by_room": {
      "patient:507f1f77bcf86cd799439011:vitals": 3,
      "hospital:507f1f77bcf86cd799439012:alerts": 2
    },
    "connections_by_user": {
      "operapanel": 2,
      "nurse1": 1
    }
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## Room Naming Convention

Rooms follow a hierarchical naming pattern:

- **Patient Rooms:**
  - `patient:{patient_id}` - General patient updates
  - `patient:{patient_id}:vitals` - Vital signs updates
  - `patient:{patient_id}:alerts` - Patient alerts

- **Hospital Rooms:**
  - `hospital:{hospital_id}` - General hospital updates
  - `hospital:{hospital_id}:alerts` - Hospital alerts
  - `hospital:{hospital_id}:devices` - Device status updates

- **Device Rooms:**
  - `device:{device_type}:{device_id}` - Device data updates
  - `device:{device_type}:{device_id}:status` - Device status changes

- **System Rooms:**
  - `system:alerts` - System-wide alerts
  - `admin:updates` - Administrative updates

## Performance Considerations

1. **Connection Limits:**
   - Monitor active connections
   - Implement connection pooling for high-traffic scenarios
   - Consider horizontal scaling with Redis Pub/Sub

2. **Message Rate Limiting:**
   - Implement rate limiting for message publishing
   - Batch updates when possible
   - Use debouncing for frequent updates

3. **Resource Management:**
   - Properly close connections on client disconnect
   - Clean up subscriptions when no longer needed
   - Monitor Redis memory usage

## Security Best Practices

1. **Authentication:**
   - Always require JWT token for connections
   - Validate tokens before accepting connections
   - Implement token refresh for long-lived connections

2. **Authorization:**
   - Check user permissions for room subscriptions
   - Validate data access based on user role
   - Implement room-level access control

3. **Data Validation:**
   - Validate all incoming messages
   - Sanitize data before broadcasting
   - Implement message size limits

## Troubleshooting

### Common Issues

1. **Connection Refused:**
   - Check if Redis is running
   - Verify JWT token is valid
   - Ensure correct WebSocket URL

2. **Messages Not Received:**
   - Verify room subscription
   - Check event type matching
   - Monitor Redis Pub/Sub channels

3. **Connection Drops:**
   - Implement reconnection logic
   - Check network stability
   - Monitor server resources

### Debug Logging

Enable debug logging for real-time features:

```python
# In config.py
LOGGING_CONFIG = {
    'loggers': {
        'app.services.websocket_manager': {
            'level': 'DEBUG'
        },
        'app.services.realtime_events': {
            'level': 'DEBUG'
        }
    }
}
```

## Next Steps

1. **Implement Message History:**
   - Store recent messages in Redis
   - Replay missed messages on reconnection

2. **Add Presence System:**
   - Track online users
   - Show user activity status

3. **Enhance Security:**
   - Implement message encryption
   - Add rate limiting per user

4. **Scale Horizontally:**
   - Use Redis Cluster for Pub/Sub
   - Implement WebSocket load balancing
   - Add connection persistence 