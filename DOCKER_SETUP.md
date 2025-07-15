# Stardust MyFirstCare Docker Setup

## Overview

This project uses a unified `docker-compose.yml` file that includes all services:

- **Main Stardust API** (port 5054)
- **Redis Cache** (port 6374)
- **MQTT Listeners** (AVA4, Kati Watch, Qube-Vital)
- **MQTT Monitoring Panel** (port 8098)
- **MQTT WebSocket Server** (port 8097)

## Quick Start

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop all services
docker-compose down
```

## Services

### Main API
- **Service**: `stardust-api`
- **Port**: 5054
- **URL**: http://localhost:5054
- **Description**: Main FastAPI application with patient/device management

### Redis
- **Service**: `redis`
- **Port**: 6374
- **Description**: Cache and queuing for all services

### MQTT Listeners
- **AVA4 Listener**: `ava4-listener` - Processes AVA4 device data
- **Kati Watch Listener**: `kati-listener` - Processes Kati Watch data including SOS alerts
- **Qube-Vital Listener**: `qube-listener` - Processes Qube-Vital device data

### MQTT Monitoring
- **Web Panel**: `mqtt-panel` - Port 8098
  - Dashboard: http://localhost:8098
  - Emergency Alerts: http://localhost:8098/emergency
  - Devices: http://localhost:8098/devices
  - Patients: http://localhost:8098/patients
  - Data Flow: http://localhost:8098/data-flow

- **WebSocket Server**: `mqtt-websocket` - Port 8097
  - Real-time updates for the web panel

## Development vs Production

### Development
```bash
docker-compose up -d
```

### Production (with FHIR)
```bash
docker-compose -f deployment/docker-compose.fhir.yml up -d
```

### Production (with Logging)
```bash
docker-compose -f deployment/docker-compose.fhir.yml up -d
docker-compose -f deployment/docker-compose.logging.yml up -d
```

## Environment Variables

All services use the same MongoDB and Redis configurations:
- **MongoDB**: `coruscant.my-firstcare.com:27023`
- **Redis**: `redis:6374` (internal network)
- **MQTT Broker**: `adam.amy.care:1883`

## SSL Certificates

SSL certificates are mounted from `./ssl/` directory:
- `ca-latest.pem`
- `client-combined-latest.pem`

## Network

All services use the `stardust-network` bridge network for internal communication.

## Health Checks

- **API**: HTTP health check on `/health` endpoint
- **Redis**: Redis ping command
- **MQTT Services**: Automatic reconnection with retry logic

## Troubleshooting

### View Service Logs
```bash
# All services
docker-compose logs

# Specific service
docker-compose logs stardust-api
docker-compose logs mqtt-panel
```

### Restart Services
```bash
# All services
docker-compose restart

# Specific service
docker-compose restart mqtt-panel
```

### Rebuild Services
```bash
# All services
docker-compose up -d --build

# Specific service
docker-compose up -d --build mqtt-panel
``` 