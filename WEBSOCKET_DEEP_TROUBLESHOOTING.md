# WebSocket Deep Troubleshooting Guide 🔍

## 🎯 **Current Status**
- ✅ **WebSocket Server**: Running and accessible on port 8097
- ✅ **MQTT Data**: Flowing from all devices
- ❌ **Frontend Connection**: Still showing "Connecting..." status
- ❓ **JavaScript Execution**: Need to verify

## 🔍 **Step-by-Step Debugging**

### 1. **Open Browser Developer Tools**
- Press **F12** or right-click → "Inspect"
- Go to **Console** tab
- Clear the console (click the 🚫 icon)

### 2. **Refresh the Web Panel**
- Navigate to http://localhost:8098/
- Refresh the page (Ctrl+F5 or Cmd+Shift+R)

### 3. **Look for These Console Messages**

#### ✅ **Expected Success Messages**
```
🚀 MQTT Monitor App initializing...
🔌 Calling connectWebSocket()...
🔌 Starting WebSocket connection process...
🌐 Connection details: {isProduction: false, hostname: "localhost", wsHost: "localhost", wsPort: "8097", wsUrl: "ws://localhost:8097"}
🔗 Attempting to connect to WebSocket: ws://localhost:8097
✅ WebSocket object created successfully
🎉 WebSocket connection opened successfully!
📥 Received initial data from WebSocket: {...}
📊 Updating statistics: {...}
📨 Loading message history: 50 messages
✅ MQTT Monitor App initialization complete
```

#### ❌ **Error Messages to Look For**
- `💥 Error creating WebSocket:`
- `💥 WebSocket error occurred:`
- `❌ WebSocket connection closed:`
- `ReferenceError:` or `TypeError:`
- Any red error messages

### 4. **Check Network Tab**
- Go to **Network** tab in Developer Tools
- Filter by **WS** (WebSocket)
- Look for WebSocket connection attempts
- Check if connection is established or failed

### 5. **Check WebSocket Server Logs**
Run this command to see if the server receives connection attempts:
```bash
docker-compose -f docker-compose.opera-godeye.yml logs --tail=10 opera-godeye-websocket | grep -E "(🔗|connection|WebSocket)"
```

## 🚨 **Common Issues & Solutions**

### **Issue 1: No Console Messages**
**Problem**: No JavaScript console messages appear
**Solution**: JavaScript file not loading properly
- Check if `app.js` is accessible at http://localhost:8098/static/js/app.js
- Check for 404 errors in Network tab

### **Issue 2: WebSocket Creation Fails**
**Problem**: `💥 Error creating WebSocket:` appears
**Solution**: Browser security or network issue
- Check if browser blocks WebSocket connections
- Try different browser (Chrome, Firefox, Safari)

### **Issue 3: Connection Timeout**
**Problem**: WebSocket connects but immediately closes
**Solution**: Server configuration issue
- Check WebSocket server logs for connection errors
- Verify port 8097 is not blocked by firewall

### **Issue 4: CORS Issues**
**Problem**: Browser blocks WebSocket due to CORS
**Solution**: Check browser console for CORS errors
- Look for "Access-Control-Allow-Origin" errors

## 📊 **Expected Results After Fix**

### **Console Output**
```
🚀 MQTT Monitor App initializing...
🔌 Calling connectWebSocket()...
🔌 Starting WebSocket connection process...
🌐 Connection details: {isProduction: false, hostname: "localhost", wsHost: "localhost", wsPort: "8097", wsUrl: "ws://localhost:8097"}
🔗 Attempting to connect to WebSocket: ws://localhost:8097
✅ WebSocket object created successfully
🎉 WebSocket connection opened successfully!
📥 Received initial data from WebSocket: {...}
📊 Updating statistics: {...}
📨 Loading message history: 50 messages
✅ MQTT Monitor App initialization complete
```

### **WebSocket Server Logs**
```
🔗 New WebSocket connection from ('127.0.0.1', XXXXX) on path: /
✅ Sent initial data to ('127.0.0.1', XXXXX)
```

### **Dashboard Display**
- ✅ Connection Status: "Connected" (green)
- ✅ Real-time messages appearing
- ✅ Statistics updating
- ✅ Device tables populated

## 🆘 **If Still Not Working**

1. **Check Browser Console** for any error messages
2. **Check Network Tab** for failed requests
3. **Try Different Browser** to rule out browser-specific issues
4. **Check WebSocket Server Logs** for connection attempts
5. **Share Console Output** with me for further debugging

The enhanced debug logging will help us identify exactly where the connection is failing! 🔍 