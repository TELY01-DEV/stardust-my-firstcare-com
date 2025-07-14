# 🔧 Final Port Configuration - Official Ports

## 📋 **Official Port Configuration**

### **Production Environment**
- **Web Panel**: http://103.13.30.89:8098
- **WebSocket Server**: ws://103.13.30.89:8097

### **Development Environment**
- **Web Panel**: http://localhost:8080
- **WebSocket Server**: ws://localhost:8081

## ✅ **Current Configuration Status**

### **Docker Compose Configuration** ✅
**File**: `docker-compose.opera-godeye.yml`
```yaml
# MQTT Monitor WebSocket Server
opera-godeye-websocket:
  ports:
    - "8097:8097"  # ✅ Correct WebSocket port
  environment:
    - WS_PORT=8097  # ✅ Correct internal port

# MQTT Monitor Web Panel
opera-godeye-panel:
  ports:
    - "8098:8098"  # ✅ Correct Web Panel port
  environment:
    - WEB_PORT=8098  # ✅ Correct internal port
```

### **Dockerfile Configuration** ✅
**File**: `services/mqtt-monitor/web-panel/Dockerfile`
```dockerfile
EXPOSE 8098  # ✅ Correct port
CMD ["gunicorn", "--workers", "1", "--bind", "0.0.0.0:8098", "--timeout", "120", "--keep-alive", "5", "--log-level", "info", "app:app"]
```

### **Flask Application** ✅
**File**: `services/mqtt-monitor/web-panel/app.py`
```python
port = int(os.getenv('WEB_PORT', 8098))  # ✅ Correct default port
```

### **JavaScript Configuration** ✅
**File**: `services/mqtt-monitor/web-panel/static/js/app.js`
```javascript
const wsPort = isProduction ? '8097' : '8081';  # ✅ Correct WebSocket ports
```

## 🚀 **Deployment Commands**

### **Rebuild and Restart with Correct Ports**
```bash
# SSH to production server
ssh -i ~/.ssh/id_ed25519 root@103.13.30.89 -p 2222

# Navigate to project directory
cd /www/dk_project/dk_app/stardust-my-firstcare-com

# Stop current services
docker-compose -f docker-compose.opera-godeye.yml down

# Rebuild with correct port configuration
docker-compose -f docker-compose.opera-godeye.yml up -d --build

# Verify services are running
docker-compose -f docker-compose.opera-godeye.yml ps

# Check logs for production server
docker-compose -f docker-compose.opera-godeye.yml logs -f opera-godeye-panel
```

## 🔍 **Verification Steps**

### 1. **Check Service Status**
```bash
docker-compose -f docker-compose.opera-godeye.yml ps
```

### 2. **Verify Port Bindings**
```bash
# Check if ports are listening
netstat -tlnp | grep 8098  # Web Panel
netstat -tlnp | grep 8097  # WebSocket
```

### 3. **Test Web Panel Access**
```bash
# Health check
curl -f http://103.13.30.89:8098/health

# Check response headers
curl -I http://103.13.30.89:8098/
```

### 4. **Test WebSocket Connection**
```bash
# Check if WebSocket port is accessible
curl -I http://103.13.30.89:8097/
```

## 📋 **Port Summary**

| Service | External Port | Internal Port | Purpose |
|---------|---------------|---------------|---------|
| Web Panel | 8098 | 8098 | MQTT Monitor Dashboard |
| WebSocket | 8097 | 8097 | Real-time MQTT Updates |

## ✅ **Expected Results**

After deployment with correct ports:

1. **Web Panel Accessible**: http://103.13.30.89:8098
2. **WebSocket Working**: ws://103.13.30.89:8097
3. **No Port Conflicts**: All services using official ports
4. **Production Server**: Gunicorn instead of Flask development server
5. **Real-time Updates**: WebSocket connections working properly

## 🚨 **Important Notes**

- **Port 8098**: Official Web Panel port (unchanged)
- **Port 8097**: Official WebSocket port (unchanged)
- **No Port Changes**: All configurations use the official ports
- **Production Ready**: Gunicorn with simplified configuration

---
**Configuration Date**: July 13, 2025  
**Status**: ✅ Ready for Production Deployment (Official Ports) 