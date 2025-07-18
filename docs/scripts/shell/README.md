# Shell Scripts

This directory contains shell scripts for various system operations and monitoring tasks.

## Files

### Service Management Scripts
- `start_service_monitor.sh` - Start the service monitoring system
- `start_medical_monitor.sh` - Start medical data monitoring
- `start_medical_monitor_docker.sh` - Start medical monitoring in Docker
- `start_complete_monitoring.sh` - Start complete monitoring system

### MQTT System Scripts
- `monitor_mqtt_system.sh` - Monitor MQTT system status and performance
- `test_mqtt_workflow.sh` - Test MQTT workflow and data flow

## Usage

### Service Monitoring
```bash
# Start service monitor
./start_service_monitor.sh

# Start medical monitor
./start_medical_monitor.sh

# Start complete monitoring
./start_complete_monitoring.sh
```

### MQTT Monitoring
```bash
# Monitor MQTT system
./monitor_mqtt_system.sh

# Test MQTT workflow
./test_mqtt_workflow.sh
```

## Features

### Service Monitor
- Monitors all Docker containers
- Checks service health
- Sends Telegram alerts
- Logs system status

### Medical Monitor
- Monitors medical data flow
- Tracks device connectivity
- Alerts on data anomalies
- Monitors patient data

### MQTT Monitor
- Monitors MQTT broker connection
- Tracks message flow
- Monitors device connectivity
- Performance metrics

## Prerequisites

- Docker and Docker Compose installed
- Telegram bot configured (for alerts)
- MQTT broker accessible
- MongoDB connection configured

## Configuration

Most scripts use environment variables from the main project:
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `MQTT_BROKER_HOST`
- `MONGODB_URI`

## Logging

Scripts generate logs in the `logs/` directory:
- Service status logs
- Error logs
- Performance metrics
- Alert history 