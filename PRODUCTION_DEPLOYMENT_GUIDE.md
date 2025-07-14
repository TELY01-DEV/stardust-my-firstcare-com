# 🚀 Production Deployment Guide - Opera Godeye MQTT Services

## 📋 Overview
This guide covers the deployment of the new Opera Godeye MQTT monitoring services to the production server.

## 🎯 Services Deployed
1. **AVA4 MQTT Listener** - Processes AVA4 device messages
2. **Kati Watch MQTT Listener** - Processes Kati Watch device messages  
3. **Qube-Vital MQTT Listener** - Processes Qube-Vital device messages
4. **MQTT Monitor WebSocket Server** - Real-time message broadcasting
5. **MQTT Monitor Web Panel** - Web interface for monitoring

## 📁 Files Transferred
```
/www/dk_project/dk_app/stardust-my-firstcare-com/
├── docker-compose.opera-godeye.yml          # Main Docker Compose file
├── start.sh                                 # Deployment script
├── ssl/                                     # SSL certificates for MongoDB
│   ├── ca-latest.pem
│   └── client-combined-latest.pem
└── services/
    ├── mqtt-listeners/                      # MQTT Listener Services
    │   ├── ava4-listener/
    │   ├── kati-listener/
    │   ├── qube-listener/
    │   └── shared/
    └── mqtt-monitor/                        # MQTT Monitor Services
        ├── shared/
        ├── websocket-server/
        └── web-panel/
```

## 🔧 Production Deployment Steps

### 1. SSH to Production Server
```bash
ssh -i ~/.ssh/id_ed25519 root@103.13.30.89 -p 2222
```

### 2. Navigate to Project Directory
```bash
cd /www/dk_project/dk_app/stardust-my-firstcare-com
```

### 3. Set Proper Permissions
```bash
chmod +x start.sh
chmod 600 ssl/*.pem
```

### 4. Deploy Opera Godeye Services
```bash
# Deploy all services
docker-compose -f docker-compose.opera-godeye.yml up -d

# Or use the deployment script
./start.sh
```

### 5. Verify Services are Running
```bash
# Check service status
docker-compose -f docker-compose.opera-godeye.yml ps

# Check logs
docker-compose -f docker-compose.opera-godeye.yml logs -f
```

## 🌐 Service Access Points

### Web Panel
- **URL**: http://103.13.30.89:8098
- **Internal Port**: 8080
- **Login**: Use existing JWT authentication
- **Features**: Real-time MQTT monitoring, device management, patient mapping

### WebSocket Server
- **URL**: ws://103.13.30.89:8097
- **Internal Port**: 8097
- **Purpose**: Real-time MQTT message broadcasting

### MQTT Listeners
- **AVA4**: Processing ESP32_BLE_GW_TX, dusun_sub topics
- **Kati Watch**: Processing iMEDE_watch/* topics
- **Qube-Vital**: Processing CM4_BLE_GW_TX topics

## 🔍 Monitoring & Troubleshooting

### Check Service Logs
```bash
# All services
docker-compose -f docker-compose.opera-godeye.yml logs

# Specific service
docker-compose -f docker-compose.opera-godeye.yml logs opera-godeye-panel
docker-compose -f docker-compose.opera-godeye.yml logs opera-godeye-websocket
docker-compose -f docker-compose.opera-godeye.yml logs opera-godeye-ava4-listener
docker-compose -f docker-compose.opera-godeye.yml logs opera-godeye-kati-listener
docker-compose -f docker-compose.opera-godeye.yml logs opera-godeye-qube-listener
```

### Check Service Status
```bash
# Service status
docker-compose -f docker-compose.opera-godeye.yml ps

# Container details
docker ps | grep opera-godeye
```

### Restart Services
```bash
# Restart all services
docker-compose -f docker-compose.opera-godeye.yml restart

# Restart specific service
docker-compose -f docker-compose.opera-godeye.yml restart opera-godeye-panel
```

## 🔧 Configuration

### Environment Variables
The services are configured with production environment variables:
- **MongoDB**: SSL-secured connection to production cluster
- **MQTT Broker**: adam.amy.care:1883
- **JWT Authentication**: Integrated with Stardust-V1
- **Ports**: 8097 (WebSocket), 8098 (Web Panel, maps to internal 8080)

### SSL Certificates
- **Location**: `/www/dk_project/dk_app/stardust-my-firstcare-com/ssl/`
- **Files**: ca-latest.pem, client-combined-latest.pem
- **Permissions**: 600 (read-only for root)

## 🚨 Emergency Procedures

### Stop All Services
```bash
docker-compose -f docker-compose.opera-godeye.yml down
```

### Update Services
```bash
# Pull latest changes and rebuild
docker-compose -f docker-compose.opera-godeye.yml down
docker-compose -f docker-compose.opera-godeye.yml up -d --build
```

### Rollback
```bash
# Stop services
docker-compose -f docker-compose.opera-godeye.yml down

# Remove containers and images
docker-compose -f docker-compose.opera-godeye.yml down --rmi all

# Restart with previous version
docker-compose -f docker-compose.opera-godeye.yml up -d
```

## 📊 Health Checks

### Web Panel Health Check
```bash
curl -f http://103.13.30.89:8098/health
```

### WebSocket Health Check
```bash
# Check if port is listening
netstat -tlnp | grep 8097
```

### MQTT Connection Check
```bash
# Check MQTT listener logs for connection status
docker-compose -f docker-compose.opera-godeye.yml logs opera-godeye-ava4-listener | grep "Connected"
```

## 🔐 Security Notes
- All services use SSL-secured MongoDB connections
- JWT authentication is required for web panel access
- MQTT credentials are configured for production broker
- SSL certificates are properly secured with 600 permissions

## 📞 Support
For issues or questions:
1. Check service logs first
2. Verify network connectivity
3. Confirm SSL certificate validity
4. Check MongoDB connection status

---
**Deployment Date**: July 13, 2025  
**Version**: Opera Godeye v1.0  
**Status**: ✅ Production Ready 