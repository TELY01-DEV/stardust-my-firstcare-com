# 🚀 MQTT Operations Quick Reference
## Daily Operations & Troubleshooting Guide

> **📋 Quick Reference**: This guide provides essential commands and procedures for daily MQTT data processing operations.

---

## 📊 **System Status Commands**

### **Check Service Status**
```bash
# Check all MQTT listener services
docker compose -f docker-compose.mqtt.yml ps

# Expected output:
# ava4-mqtt-listener     Up    ESP32_BLE_GW_TX, dusun_sub
# kati-mqtt-listener     Up    iMEDE_watch/#
# qube-mqtt-listener     Up    CM4_BLE_GW_TX
# websocket-server       Up    Real-time monitoring
```

### **Check Service Health**
```bash
# Health check for each service
docker compose -f docker-compose.mqtt.yml exec ava4-mqtt-listener python -c "import sys; sys.exit(0)"
docker compose -f docker-compose.mqtt.yml exec kati-mqtt-listener python -c "import sys; sys.exit(0)"
docker compose -f docker-compose.mqtt.yml exec qube-mqtt-listener python -c "import sys; sys.exit(0)"
```

---

## 📈 **Real-time Monitoring**

### **Monitor Live Logs**
```bash
# Monitor all MQTT listeners
docker logs -f ava4-mqtt-listener
docker logs -f kati-mqtt-listener
docker logs -f qube-mqtt-listener

# Monitor specific events
docker logs -f ava4-mqtt-listener | grep "Connected"
docker logs -f kati-mqtt-listener | grep "Processing"
docker logs -f qube-mqtt-listener | grep "Successfully processed"
```

### **Check MQTT Connection Status**
```bash
# Test MQTT broker connectivity
ping adam.amy.care
telnet adam.amy.care 1883

# Monitor MQTT topics (if mosquitto-clients installed)
mosquitto_sub -h adam.amy.care -u webapi -P Sim!4433 -t "dusun_sub" -v
mosquitto_sub -h adam.amy.care -u webapi -P Sim!4433 -t "iMEDE_watch/#" -v
mosquitto_sub -h adam.amy.care -u webapi -P Sim!4433 -t "CM4_BLE_GW_TX" -v
```

---

## 🔧 **Troubleshooting Commands**

### **1. MQTT Connection Issues**
```bash
# Symptoms: "Connection lost", "Failed to connect"

# Check network connectivity
ping adam.amy.care
telnet adam.amy.care 1883

# Check credentials
echo "MQTT_USERNAME: $MQTT_USERNAME"
echo "MQTT_PASSWORD: $MQTT_PASSWORD"

# Restart services
docker compose -f docker-compose.mqtt.yml restart
```

### **2. Patient Mapping Failures**
```bash
# Symptoms: "No patient found" errors

# Check AVA4 device mappings
mongo "mongodb://coruscant.my-firstcare.com:27023/AMY" --username opera_admin --password Sim!443355
db.amy_devices.find({"mac_address": "DEVICE_MAC"})

# Check Kati Watch mappings
db.watches.find({"imei": "DEVICE_IMEI"})

# Check Qube-Vital patient
db.patients.find({"id_card": "CITIZEN_ID"})
```

### **3. Database Connection Issues**
```bash
# Symptoms: "Database error", "MongoDB not connected"

# Test MongoDB connection
mongo "mongodb://coruscant.my-firstcare.com:27023/AMY" --username opera_admin --password Sim!443355
db.runCommand({ping: 1})

# Check SSL certificates
ls -la /app/ssl/
```

### **4. High Error Rates**
```bash
# Symptoms: Many error logs, data loss

# Analyze error patterns
grep "ERROR" /var/log/mqtt-listeners/*.log | tail -100
grep "JSONDecodeError" /var/log/mqtt-listeners/*.log
grep "PatientNotFoundError" /var/log/mqtt-listeners/*.log
```

---

## 📊 **Data Validation Commands**

### **Check Data Processing Statistics**
```bash
# Count recent medical records
mongo "mongodb://coruscant.my-firstcare.com:27023/AMY" --username opera_admin --password Sim!443355

# Blood pressure records (last 24 hours)
db.blood_pressure_histories.countDocuments({
  "created_at": {
    "$gte": new Date(Date.now() - 24*60*60*1000)
  }
})

# Patient mapping success rate
db.blood_pressure_histories.aggregate([
  {
    $match: {
      "created_at": {
        "$gte": new Date(Date.now() - 24*60*60*1000)
      }
    }
  },
  {
    $group: {
      "_id": "$source",
      "count": {$sum: 1}
    }
  }
])
```

### **Validate Medical Data Ranges**
```bash
# Check for anomalous blood pressure values
db.blood_pressure_histories.find({
  "$or": [
    {"data.systolic": {"$gt": 200}},
    {"data.systolic": {"$lt": 50}},
    {"data.diastolic": {"$gt": 150}},
    {"data.diastolic": {"$lt": 30}}
  ]
})

# Check for missing required fields
db.blood_pressure_histories.find({
  "$or": [
    {"data.systolic": {"$exists": false}},
    {"data.diastolic": {"$exists": false}},
    {"patient_id": {"$exists": false}}
  ]
})
```

---

## 🚀 **Service Management**

### **Restart Services**
```bash
# Restart all MQTT services
docker compose -f docker-compose.mqtt.yml restart

# Restart specific service
docker compose -f docker-compose.mqtt.yml restart ava4-mqtt-listener
docker compose -f docker-compose.mqtt.yml restart kati-mqtt-listener
docker compose -f docker-compose.mqtt.yml restart qube-mqtt-listener
```

### **Update Services**
```bash
# Pull latest code and rebuild
git pull origin main
docker compose -f docker-compose.mqtt.yml up -d --build
```

### **View Service Logs**
```bash
# View recent logs
docker logs --tail 100 ava4-mqtt-listener
docker logs --tail 100 kati-mqtt-listener
docker logs --tail 100 qube-mqtt-listener

# Follow logs in real-time
docker logs -f ava4-mqtt-listener
```

---

## 📋 **Daily Checklist**

### **Morning Check (9:00 AM)**
- [ ] Check service status: `docker compose -f docker-compose.mqtt.yml ps`
- [ ] Verify MQTT connections: `docker logs ava4-mqtt-listener | grep "Connected"`
- [ ] Check error rates: `grep "ERROR" /var/log/mqtt-listeners/*.log | wc -l`
- [ ] Monitor data processing: Check recent medical records count
- [ ] Verify database connectivity: `mongo --eval "db.runCommand({ping: 1})"`

### **Afternoon Check (2:00 PM)**
- [ ] Review processing statistics
- [ ] Check patient mapping success rates
- [ ] Monitor system performance
- [ ] Review any error alerts

### **Evening Check (6:00 PM)**
- [ ] Final status check
- [ ] Review daily processing summary
- [ ] Check for any unresolved issues
- [ ] Update monitoring dashboards

---

## 🚨 **Emergency Procedures**

### **Service Down**
```bash
# 1. Check service status
docker compose -f docker-compose.mqtt.yml ps

# 2. Check logs for errors
docker logs --tail 50 ava4-mqtt-listener

# 3. Restart service
docker compose -f docker-compose.mqtt.yml restart ava4-mqtt-listener

# 4. Verify recovery
docker logs -f ava4-mqtt-listener | grep "Connected"
```

### **Data Processing Stopped**
```bash
# 1. Check MQTT connection
ping adam.amy.care
telnet adam.amy.care 1883

# 2. Check database connection
mongo --eval "db.runCommand({ping: 1})"

# 3. Restart all services
docker compose -f docker-compose.mqtt.yml restart

# 4. Monitor data flow
docker logs -f ava4-mqtt-listener | grep "Processing"
```

### **High Error Rate**
```bash
# 1. Identify error types
grep "ERROR" /var/log/mqtt-listeners/*.log | tail -20

# 2. Check specific error patterns
grep "PatientNotFoundError" /var/log/mqtt-listeners/*.log
grep "JSONDecodeError" /var/log/mqtt-listeners/*.log

# 3. Check device mappings
# (Use patient mapping commands above)

# 4. Contact development team if needed
```

---

## 📞 **Contact Information**

### **Escalation Path**
1. **First Level**: Operations Team
2. **Second Level**: Development Team
3. **Third Level**: System Administrator

### **Emergency Contacts**
- **Operations Lead**: [Contact Info]
- **Development Lead**: [Contact Info]
- **System Admin**: [Contact Info]

### **Documentation Links**
- [Full MQTT Handbook](MQTT_DATA_PROCESSING_HANDBOOK.md)
- [Deployment Guide](MQTT_LISTENERS_DEPLOYMENT_GUIDE.md)
- [Troubleshooting Guide](MQTT_DATA_PROCESSING_HANDBOOK.md#troubleshooting-guide)

---

## 📊 **Key Metrics to Monitor**

### **Performance Metrics**
- Messages processed per second
- Database write latency
- Patient mapping success rate
- Error rate percentage
- Memory usage
- CPU utilization

### **Business Metrics**
- Total medical records processed
- Device data sources (AVA4/Kati/Qube-Vital)
- Patient data coverage
- Data quality indicators

### **Alert Thresholds**
- Error rate > 5%
- MQTT connection lost
- Database connection issues
- Patient mapping failures > 10%
- High memory usage > 80%

---

**📝 Note**: This quick reference should be updated whenever the system configuration changes.

**🔄 Last Updated**: [Date]
**📋 Version**: 1.0 