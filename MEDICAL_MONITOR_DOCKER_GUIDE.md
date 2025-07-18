# Medical Data Monitor - Docker Service Guide

This guide explains how to use the Medical Data Monitor as a Docker service with Telegram alerts.

## 🐳 **Docker Service Overview**

The Medical Data Monitor is now available as a Docker service that integrates seamlessly with your existing Stardust infrastructure.

### **Service Details**
- **Service Name**: `Opera-GodEye-Medical-Data-Monitor`
- **Container Name**: `stardust-opera-godeye-medical-data-monitor`
- **Port**: `8099` (Health check endpoint)
- **Health Check**: `http://localhost:8099/health`
- **Statistics**: `http://localhost:8099/stats`

## 🚀 **Quick Start**

### **1. Start the Monitor Service**
```bash
# Start only the medical monitor
./start_medical_monitor_docker.sh

# Or start with all services
docker-compose up -d Opera-GodEye-Medical-Data-Monitor
```

### **2. Check Service Status**
```bash
# Check if service is running
docker ps | grep opera-godeye-medical-data-monitor

# Check service health
curl http://localhost:8099/health

# View service statistics
curl http://localhost:8099/stats
```

### **3. View Logs**
```bash
# View real-time logs
docker logs -f stardust-opera-godeye-medical-data-monitor

# View last 50 lines
docker logs --tail 50 stardust-opera-godeye-medical-data-monitor
```

## 📊 **Service Features**

### **✅ Automatic Monitoring**
- **MQTT Data Flow**: Monitors all medical device topics
- **Container Health**: Checks all Stardust containers
- **Failure Detection**: Identifies errors in real-time
- **Telegram Alerts**: Sends notifications on failures

### **✅ Health Checks**
- **Self-Monitoring**: Health check endpoint at `/health`
- **Container Status**: Monitors all related containers
- **Automatic Restart**: `restart: unless-stopped` policy
- **Dependency Management**: Waits for required services

### **✅ Configuration**
- **Environment Variables**: Loaded from `.env` file
- **Telegram Integration**: Automatic alert configuration
- **Failure Thresholds**: Configurable alert settings
- **Log Levels**: Adjustable logging verbosity

## 🔧 **Configuration Options**

### **Environment Variables**
```bash
# MQTT Configuration
MQTT_BROKER_HOST=adam.amy.care
MQTT_BROKER_PORT=1883
MQTT_USERNAME=webapi
MQTT_PASSWORD=Sim!4433

# Telegram Configuration (from .env file)
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Monitor Configuration
FAILURE_THRESHOLD=5
FAILURE_WINDOW_MINUTES=10
LOG_LEVEL=INFO
```

### **Health Check Endpoint**
```json
{
  "status": "connected",
  "uptime": 3600,
  "total_messages": 150,
  "success_rate": 98.5,
  "last_message": "2025-07-16T10:30:00",
  "telegram_enabled": true,
  "containers_healthy": true
}
```

### **Statistics Endpoint**
```json
{
  "uptime": 3600,
  "total_messages": 150,
  "success_rate": 98.5,
  "telegram_enabled": true,
  "containers_healthy": true,
  "recent_failures": 2
}
```

## 🚨 **Alert Types**

### **Critical Alerts**
- High failure rate detected
- Missing containers
- System startup failures
- Critical processing errors

### **Warning Alerts**
- Individual failure events
- Low battery/signal warnings
- Container log errors
- Processing timeouts

### **Info Alerts**
- Monitor startup/shutdown
- Connection status changes
- Configuration updates

## 🛠️ **Management Commands**

### **Service Control**
```bash
# Start the service
docker-compose up -d Opera-GodEye-Medical-Data-Monitor

# Stop the service
docker-compose stop Opera-GodEye-Medical-Data-Monitor

# Restart the service
docker-compose restart Opera-GodEye-Medical-Data-Monitor

# Remove the service
docker-compose rm -f Opera-GodEye-Medical-Data-Monitor
```

### **Logging and Debugging**
```bash
# View real-time logs
docker logs -f stardust-opera-godeye-medical-data-monitor

# View logs with timestamps
docker logs -t stardust-opera-godeye-medical-data-monitor

# View logs since specific time
docker logs --since "2025-07-16T10:00:00" stardust-opera-godeye-medical-data-monitor

# View logs for specific time period
docker logs --since "1h" stardust-opera-godeye-medical-data-monitor
```

### **Health Monitoring**
```bash
# Check service health
curl http://localhost:8099/health

# Get statistics
curl http://localhost:8099/stats

# Check container status
docker ps | grep opera-godeye-medical-data-monitor

# Check container resources
docker stats stardust-opera-godeye-medical-data-monitor
```

## 🔍 **Troubleshooting**

### **Service Won't Start**
```bash
# Check Docker Compose configuration
docker-compose config

# Check for port conflicts
netstat -tulpn | grep 8099

# Check container logs
docker-compose logs Opera-GodEye-Medical-Data-Monitor

# Rebuild the service
docker-compose build Opera-GodEye-Medical-Data-Monitor
docker-compose up -d Opera-GodEye-Medical-Data-Monitor
```

### **Telegram Alerts Not Working**
```bash
# Check .env file
cat .env | grep TELEGRAM

# Test Telegram configuration
python3 test_telegram_alert.py

# Check monitor logs for Telegram errors
docker logs stardust-opera-godeye-medical-data-monitor | grep -i telegram
```

### **High Resource Usage**
```bash
# Check container resources
docker stats stardust-opera-godeye-medical-data-monitor

# Check memory usage
docker exec stardust-opera-godeye-medical-data-monitor ps aux

# Restart with resource limits
docker-compose stop Opera-GodEye-Medical-Data-Monitor
docker-compose up -d Opera-GodEye-Medical-Data-Monitor
```

## 📈 **Integration with Existing Services**

### **Dependencies**
The medical monitor depends on:
- `redis` - For data flow events
- `stardust-api` - Main API service
- `ava4-listener` - AVA4 device processing
- `kati-listener` - Kati Watch processing
- `qube-listener` - Qube-Vital processing

### **Network Integration**
- Uses `stardust-network` bridge network
- Communicates with all other services
- Accessible via port `8099` for health checks

### **Volume Mounts**
- `./ssl:/app/ssl:ro` - SSL certificates
- `/var/run/docker.sock:/var/run/docker.sock:ro` - Container monitoring

## 🎯 **Best Practices**

### **1. Monitoring Setup**
- Always start with `./start_medical_monitor_docker.sh`
- Verify Telegram configuration before deployment
- Check health endpoint after startup

### **2. Alert Management**
- Configure appropriate failure thresholds
- Monitor alert frequency to avoid spam
- Review and adjust alert settings based on usage

### **3. Maintenance**
- Regularly check service logs
- Monitor resource usage
- Update configuration as needed
- Restart service after configuration changes

### **4. Security**
- Keep `.env` file secure
- Regularly rotate Telegram bot tokens
- Monitor access to health endpoints
- Review container permissions

## 🔄 **Migration from Standalone**

If you were previously running the monitor as a standalone script:

### **1. Stop Standalone Monitor**
```bash
# Stop the standalone monitor
pkill -f monitor_complete_data_flow.py
```

### **2. Start Docker Service**
```bash
# Start the Docker service
./start_medical_monitor_docker.sh
```

### **3. Verify Migration**
```bash
# Check service is running
docker ps | grep opera-godeye-medical-data-monitor

# Verify health check
curl http://localhost:8099/health

# Check logs
docker logs stardust-opera-godeye-medical-data-monitor
```

## 📞 **Support**

For issues with the Medical Data Monitor Docker service:

1. **Check logs**: `docker logs stardust-opera-godeye-medical-data-monitor`
2. **Verify configuration**: Check `.env` file and Docker Compose
3. **Test health endpoint**: `curl http://localhost:8099/health`
4. **Restart service**: `docker-compose restart Opera-GodEye-Medical-Data-Monitor`

The Docker service provides better reliability, automatic restarts, and seamless integration with your existing Stardust infrastructure. 