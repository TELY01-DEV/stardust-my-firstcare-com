# Emergency Alert Dashboard

A real-time emergency alert monitoring dashboard for MyFirstCare system with comprehensive notification capabilities.

## Features

### 🚨 Real-time Emergency Monitoring
- **Live Alert Display**: Real-time emergency alerts from Kati Watch and AVA4 devices
- **Alert Types**: SOS, Fall Detection, Low Battery, and other emergency alerts
- **Priority Classification**: Critical, High, Medium, Low priority levels
- **Patient Information**: Complete patient details with device mapping

### 📊 Dashboard Statistics
- **24-hour Alert Counts**: Total alerts, SOS, Fall Detection, Active alerts
- **Priority Breakdown**: Critical and High priority alert counts
- **Real-time Updates**: Auto-refresh every 30 seconds
- **Visual Indicators**: Color-coded priority badges and status indicators

### 🔔 Multi-Channel Notifications
- **Email Notifications**: SMTP-based email alerts
- **Telegram Bot**: Instant messaging via Telegram
- **SMS Alerts**: Text message notifications (Twilio support)
- **Webhook Integration**: Custom webhook notifications
- **Browser Notifications**: Desktop notifications with sound

### 🎯 Alert Management
- **Alert Processing**: Mark alerts as processed
- **Filtering**: Filter by type, priority, and status
- **Detailed View**: Complete alert information with location data
- **Bulk Operations**: Mark all alerts as processed

### 📍 Location Tracking
- **GPS Coordinates**: Exact location for emergency response
- **WiFi Networks**: WiFi-based location data
- **Cell Tower Data**: LBS location information
- **Speed & Heading**: Movement tracking data

## Quick Start

### 1. Build and Deploy

```bash
# Navigate to emergency dashboard directory
cd services/mqtt-monitor/emergency-dashboard

# Build and start the service
docker-compose up -d --build
```

### 2. Access Dashboard

Open your browser and navigate to:
```
http://localhost:5056
```

### 3. Configure Notifications (Optional)

Create a `.env` file in the emergency dashboard directory:

```env
# Email Configuration
EMAIL_USER=your-email@gmail.com
EMAIL_PASSWORD=your-app-password
TO_EMAILS=emergency@hospital.com,admin@hospital.com

# Telegram Configuration
TELEGRAM_BOT_TOKEN=your-bot-token
TELEGRAM_CHAT_ID=your-chat-id
TELEGRAM_ENABLED=true

# SMS Configuration (Twilio)
SMS_API_KEY=your-twilio-account-sid
SMS_API_SECRET=your-twilio-auth-token
SMS_FROM_NUMBER=+1234567890
SMS_TO_NUMBERS=+1234567890,+0987654321
SMS_ENABLED=true

# Webhook Configuration
WEBHOOK_URL=https://your-webhook-url.com/emergency
WEBHOOK_ENABLED=true
```

## API Endpoints

### Emergency Alerts
- `GET /api/emergency-alerts` - Get emergency alerts from last 24 hours
- `GET /api/emergency-stats` - Get emergency alert statistics
- `POST /api/mark-processed/<alert_id>` - Mark alert as processed
- `GET /api/patients` - Get patient list for filtering

### WebSocket Events
- `new_emergency_alert` - New emergency alert received
- `alert_processed` - Alert marked as processed
- `connected` - Client connected to dashboard

## Alert Data Structure

```json
{
  "_id": "alert_id",
  "patient_id": "patient_object_id",
  "patient_name": "Patient Name",
  "alert_type": "sos|fall_down|low_battery",
  "alert_data": {
    "type": "alert_type",
    "status": "alert_status",
    "priority": "CRITICAL|HIGH|MEDIUM|LOW",
    "location": {
      "GPS": {
        "latitude": 13.7563,
        "longitude": 100.5018,
        "speed": 0.1,
        "header": 350.01
      },
      "WiFi": "wifi_network_data",
      "LBS": {
        "MCC": "520",
        "MNC": "3",
        "LAC": "13015",
        "CID": "166155371"
      }
    },
    "imei": "device_imei",
    "timestamp": "2025-07-14T19:19:25.925732",
    "source": "Kati|AVA4"
  },
  "timestamp": "2025-07-14T19:19:25.925748",
  "source": "Kati",
  "status": "ACTIVE",
  "created_at": "2025-07-14T19:19:25.925749",
  "processed": false
}
```

## Notification Setup

### Email Setup (Gmail)

1. Enable 2-factor authentication on your Gmail account
2. Generate an App Password
3. Set environment variables:
   ```env
   EMAIL_USER=your-email@gmail.com
   EMAIL_PASSWORD=your-app-password
   TO_EMAILS=recipient1@email.com,recipient2@email.com
   ```

### Telegram Setup

1. Create a Telegram bot via @BotFather
2. Get your bot token
3. Get your chat ID (send message to bot and check: https://api.telegram.org/bot<TOKEN>/getUpdates)
4. Set environment variables:
   ```env
   TELEGRAM_BOT_TOKEN=your-bot-token
   TELEGRAM_CHAT_ID=your-chat-id
   TELEGRAM_ENABLED=true
   ```

### SMS Setup (Twilio)

1. Create a Twilio account
2. Get your Account SID and Auth Token
3. Get a Twilio phone number
4. Set environment variables:
   ```env
   SMS_API_KEY=your-account-sid
   SMS_API_SECRET=your-auth-token
   SMS_FROM_NUMBER=+1234567890
   SMS_TO_NUMBERS=+1234567890,+0987654321
   SMS_ENABLED=true
   ```

## Integration with MQTT Listeners

The emergency dashboard integrates with the existing MQTT listeners:

### Kati Watch Listener
- Processes SOS and fall detection alerts
- Saves to `emergency_alarm` collection
- Broadcasts to emergency dashboard

### AVA4 Listener
- Processes medical device alerts
- Can trigger emergency conditions
- Integrates with patient mapping

### WebSocket Server
- Real-time data streaming
- Emergency alert broadcasting
- Dashboard connectivity

## Security Features

- **Connection Status**: Real-time connection monitoring
- **Alert Validation**: Data integrity checks
- **Access Control**: Environment-based configuration
- **Error Handling**: Comprehensive error logging
- **Data Sanitization**: Input validation and sanitization

## Monitoring and Logging

### Log Levels
- `INFO`: Normal operations and alerts
- `WARNING`: Emergency alerts and processing
- `ERROR`: System errors and failures

### Key Log Messages
```
🚨 EMERGENCY ALERT SAVED - ID: alert_id
🚨 SOS ALERT for patient patient_id (Patient Name)
🚨 FALL_DOWN ALERT for patient patient_id (Patient Name)
📊 External notifications sent: {'email': True, 'telegram': True}
```

## Troubleshooting

### Common Issues

1. **Dashboard not loading**
   - Check if MongoDB is running
   - Verify port 5056 is available
   - Check container logs: `docker logs opera-godeye-emergency-dashboard`

2. **No emergency alerts**
   - Verify MQTT listeners are running
   - Check emergency_alarm collection in MongoDB
   - Ensure patient mapping is correct

3. **Notifications not working**
   - Verify environment variables are set
   - Check notification service logs
   - Test individual notification channels

### Debug Commands

```bash
# Check container status
docker ps | grep emergency

# View logs
docker logs opera-godeye-emergency-dashboard

# Test notifications
docker exec opera-godeye-emergency-dashboard python notification_service.py

# Check MongoDB connection
docker exec opera-godeye-emergency-dashboard python -c "import pymongo; print(pymongo.MongoClient('mongodb://mongo:27017/').server_info())"
```

## Performance Optimization

- **Auto-refresh**: 30-second intervals
- **Data pagination**: 100 alerts per page
- **Connection pooling**: MongoDB connection management
- **Caching**: Static asset caching
- **Compression**: Gzip compression for responses

## Future Enhancements

- [ ] Mobile app integration
- [ ] Advanced analytics and reporting
- [ ] Multi-language support
- [ ] Custom alert rules and thresholds
- [ ] Integration with hospital systems
- [ ] Voice notifications
- [ ] Emergency response workflow
- [ ] Alert escalation procedures

## Support

For technical support or questions:
- Check the logs for error messages
- Verify configuration settings
- Test individual components
- Review the troubleshooting section

---

**Emergency Dashboard v1.0** - MyFirstCare Emergency Response System 