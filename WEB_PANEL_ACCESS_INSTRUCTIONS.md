# MQTT Monitoring Web Panel Access Instructions

## Current Status ✅
The MQTT monitoring web panel is now fully functional:

1. **✅ WebSocket Connection Fixed** - Frontend now connects to port 8097 correctly
2. **✅ JavaScript Syntax Errors Fixed** - All JavaScript errors resolved
3. **✅ Kati Listener ObjectId Issues Fixed** - MongoDB queries working properly
4. **✅ Web Panel Running** - Accessible on port 8098
5. **✅ WebSocket Server Running** - Receiving MQTT data on port 8097

## Access Instructions

### 1. Open the Web Panel
Navigate to: **http://localhost:8098/**

### 2. Login Required
The web panel requires authentication via Stardust-V1 system:
- **Username**: Your Stardust-V1 credentials
- **Password**: Your Stardust-V1 password

### 3. Dashboard Features
Once logged in, you'll have access to:

#### 📊 **Dashboard Tab**
- Real-time MQTT message statistics
- Device counts (AVA4, Kati, Qube-Vital)
- Connection status indicators

#### 📱 **Devices Tab**
- AVA4 device mappings and status
- Kati Watch device mappings and status
- Qube-Vital device mappings and status

#### 👥 **Patients Tab**
- Patient list with device mappings
- Patient-device relationship information

#### 📨 **Messages Tab**
- Real-time MQTT message stream
- Message parsing and display
- Device-specific message formatting

## Real-Time Data Flow

### MQTT → WebSocket → Frontend
1. **MQTT Messages** received from devices (AVA4, Kati, Qube-Vital)
2. **WebSocket Server** processes and broadcasts messages
3. **Frontend** receives real-time updates via WebSocket
4. **Dashboard** displays live data and statistics

### Current MQTT Topics
- `ESP32_BLE_GW_TX` - AVA4 device data
- `dusun_sub` - AVA4 sub-device data
- `iMEDE_watch/#` - Kati Watch data (all topics)
- `CM4_BLE_GW_TX` - Qube-Vital device data

## Troubleshooting

### If No Data Appears:
1. **Check WebSocket Connection** - Look for "Connected" status in dashboard
2. **Verify MQTT Messages** - Check WebSocket server logs for incoming messages
3. **Check Authentication** - Ensure you're logged in with valid credentials

### Log Locations:
- **Web Panel Logs**: `docker-compose -f docker-compose.opera-godeye.yml logs opera-godeye-panel`
- **WebSocket Logs**: `docker-compose -f docker-compose.opera-godeye.yml logs opera-godeye-websocket`
- **Kati Listener Logs**: `docker-compose -f docker-compose.opera-godeye.yml logs opera-godeye-kati-listener`

## System Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   MQTT Broker   │───▶│  WebSocket       │───▶│  Web Panel      │
│   (adam.amy.care)│    │  Server (8097)   │    │  (8098)         │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  MQTT Listeners │    │  Message History │    │  Real-time      │
│  (Kati, AVA4,   │    │  & Statistics    │    │  Dashboard      │
│   Qube-Vital)   │    │                  │    │  Display        │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Next Steps
1. **Login** with your Stardust-V1 credentials
2. **Navigate** to the dashboard to see real-time data
3. **Monitor** device activity and message flow
4. **Check** device-patient mappings in the Devices tab 