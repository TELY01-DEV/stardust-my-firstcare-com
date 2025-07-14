# WebSocket Connection Troubleshooting

## Current Status
- ✅ **WebSocket Server Running**: Listening on `ws://0.0.0.0:8097`
- ✅ **Port Exposed**: Port 8097 is properly exposed in Docker Compose
- ✅ **MQTT Data Flowing**: Server is receiving MQTT messages from devices
- ❌ **Frontend Connection**: WebSocket connection from frontend failing

## Issue Analysis
The frontend is showing "Connecting..." status, which means:
1. JavaScript is attempting to connect to `ws://localhost:8097/`
2. Connection attempts are being rejected with "400 Bad Request"
3. No successful WebSocket handshake

## Troubleshooting Steps

### 1. Verify WebSocket Server Status
```bash
# Check if WebSocket server is running
docker-compose -f docker-compose.opera-godeye.yml logs opera-godeye-websocket | grep "WebSocket server started"

# Check for connection attempts
docker-compose -f docker-compose.opera-godeye.yml logs opera-godeye-websocket | grep -E "(connection|WebSocket)"
```

### 2. Test WebSocket Connection Manually
```bash
# Test if port is accessible
curl -I http://localhost:8097

# Expected: HTTP/1.1 400 Bad Request (normal for WebSocket server)
```

### 3. Check Browser Console
1. Open browser developer tools (F12)
2. Go to Console tab
3. Look for WebSocket connection errors
4. Check for JavaScript errors

### 4. Verify Frontend JavaScript
The frontend should be connecting to:
```javascript
ws://localhost:8097/
```

### 5. Check Network Tab
1. Open browser developer tools
2. Go to Network tab
3. Filter by "WS" (WebSocket)
4. Look for connection attempts and their status

## Possible Solutions

### Solution 1: Check WebSocket Path
The WebSocket server might expect a specific path. Try:
- `ws://localhost:8097/` (current)
- `ws://localhost:8097` (without trailing slash)
- `ws://localhost:8097/ws`

### Solution 2: Check CORS Issues
The WebSocket server might have CORS restrictions. Check if the server allows connections from the web panel domain.

### Solution 3: Check WebSocket Protocol
Ensure the WebSocket server is using the correct protocol version and handshake.

### Solution 4: Debug WebSocket Server
Add more detailed logging to the WebSocket server to see exactly what's happening during connection attempts.

## Next Steps
1. **Check browser console** for specific error messages
2. **Test WebSocket connection** manually using a WebSocket client
3. **Add debug logging** to WebSocket server
4. **Verify frontend JavaScript** is executing correctly

## Current Configuration
- **WebSocket Server**: `opera-godeye-websocket` on port 8097
- **Web Panel**: `opera-godeye-panel` on port 8098
- **Frontend Connection**: `ws://localhost:8097/`
- **MQTT Topics**: `ESP32_BLE_GW_TX`, `dusun_sub`, `iMEDE_watch/#`, `CM4_BLE_GW_TX`

## Expected Behavior
Once connected, the frontend should:
1. Show "Connected" status
2. Receive initial data with message history
3. Display real-time MQTT messages
4. Update statistics and device information 