# 🚀 My FirstCare Opera Panel

**FastAPI + MongoDB Medical IoT Device Management System**

A comprehensive backend system for managing medical IoT devices (AVA4, Kati Watch, Qube-Vital) with FHIR R5 audit logging and admin panel functionality.

## 🏗️ Architecture

- **FastAPI** - Modern, fast web framework
- **MongoDB** - Production cluster with SSL/TLS
- **Stardust-V1** - Centralized JWT authentication
- **FHIR R5** - Audit logging with Provenance resources
- **Docker** - Containerized deployment

## 📊 System Overview

### Device Support
- **AVA4** - Blood pressure, weight, temperature monitoring
- **Kati Watch** - SPO2, steps, sleep, temperature monitoring  
- **Qube-Vital** - Hospital-based vital signs monitoring

### Medical History Collections
- Blood Pressure History (2,243 records)
- Blood Sugar History (13 records)
- Body Data History (15 records)
- Creatinine History (3 records)
- Lipid History (4 records)
- Sleep Data History (79 records)
- SPO2 History (1,724 records)
- Step History (133 records)
- Temperature Data History (2,574 records)
- Medication History (12 records)
- Allergy History (11 records)
- Underlying Disease History (13 records)
- Admit Data History (74 records)

**Total: 6,898 medical records across 14 collections**

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- SSL certificates in `/ssl/` directory
- MongoDB production cluster access

### 1. Environment Setup

Create `.env` file:
```bash
# MongoDB Production Configuration
MONGODB_URI=mongodb://opera_admin:Sim!443355@coruscant.my-firstcare.com:27023/admin?ssl=true&authSource=admin
MONGODB_HOST=coruscant.my-firstcare.com
MONGODB_PORT=27023
MONGODB_USERNAME=opera_admin
MONGODB_PASSWORD=Sim!443355
MONGODB_AUTH_DB=admin
MONGODB_SSL=true

# JWT Authentication
JWT_AUTH_BASE_URL=https://stardust-v1.my-firstcare.com
ENABLE_JWT_AUTH=true

# Application Settings
DEBUG=false
DEV_MODE=false
PORT=5054
HOST=0.0.0.0
LOG_LEVEL=INFO
NODE_ENV=production
```

### 2. SSL Certificates

Ensure SSL certificates are in `/ssl/` directory:
```
ssl/
├── ca-latest.pem
└── client-combined-latest.pem
```

### 3. Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose up -d

# Check logs
docker-compose logs -f opera-panel

# Health check
curl http://stardust.myfirstcare.com:5054/health
```

### 4. Development Mode

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
python main.py

# Or with uvicorn
uvicorn main:app --host 0.0.0.0 --port 5054 --reload
```

## 📡 API Endpoints

### Device APIs
- `POST /api/ava4/data` - Receive AVA4 device data
- `GET /api/ava4/devices` - List AVA4 devices
- `POST /api/kati/data` - Receive Kati Watch data
- `GET /api/kati/devices` - List Kati devices
- `POST /api/qube-vital/data` - Receive Qube-Vital data
- `GET /api/qube-vital/devices` - List Qube-Vital devices

### Admin Panel APIs
- `GET /admin/patients` - List patients with filtering
- `POST /admin/patients` - Create new patient
- `PUT /admin/patients/{id}` - Update patient
- `DELETE /admin/patients/{id}` - Soft delete patient
- `GET /admin/devices` - List devices by type
- `GET /admin/medical-history/{type}` - Get medical history
- `GET /admin/master-data/{type}` - Get master data
- `GET /admin/audit-log` - Get audit logs
- `GET /admin/analytics` - Dashboard analytics

### System APIs
- `GET /health` - Health check
- `GET /docs` - API documentation (Swagger UI)

## 🔐 Authentication

The system integrates with **Stardust-V1** for centralized JWT authentication:

### Login
```bash
curl -X POST "https://stardust-v1.my-firstcare.com/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "Sim!443355"}'
```

### API Usage
```bash
curl -H "Authorization: Bearer <access_token>" \
  http://stardust.myfirstcare.com:5054/admin/patients
```

## 📊 Data Flow

### Device Data Reception
1. Device sends data to `/api/{device}/data`
2. System validates device exists
3. Creates FHIR Observation resource
4. Routes to appropriate medical history collection
5. Logs FHIR R5 Provenance for audit trail

### Admin Panel Operations
1. All CRUD operations require JWT authentication
2. Soft delete implemented for sensitive data
3. FHIR R5 Provenance logging for all actions
4. Real-time analytics and reporting

## 🗄️ Database Collections

### Core Collections
- `patients` - Patient information (211 records)
- `hospitals` - Hospital data
- `provinces`, `districts`, `sub_districts` - Geographic data
- `master_hospital_types` - Hospital type classifications

### Device Collections
- `amy_boxes` - AVA4 devices (99 boxes)
- `amy_devices` - AVA4 sub-devices (74 devices)
- `watches` - Kati Watch devices (121 watches)
- `mfc_hv01_boxes` - Qube-Vital devices (2 devices)

### Medical History Collections
- 14 collections with 6,898 total records
- All linked to patients with timestamps
- Device source tracking
- FHIR R5 Observation resources

### Audit Collections
- `fhir_provenance` - FHIR R5 audit logs
- `fhir_observations` - FHIR R5 observations
- TTL index for 180-day retention

## 🔧 Configuration

### Production Settings
- MongoDB SSL/TLS encryption
- JWT authentication required
- Audit logging enabled
- TTL indexes for data retention
- Health checks and monitoring

### Development Settings
- `DEV_MODE=true` - Bypass authentication
- `DEBUG=true` - Enable debug logging
- Local MongoDB connection

## 📈 Monitoring

### Health Check
```bash
curl http://localhost:5055/health
```

Response:
```json
{
  "status": "healthy",
  "mongodb": "connected",
  "version": "1.0.0",
  "environment": "production"
}
```

### Logging
- Application logs: `logs/app.log`
- Rotation: Daily
- Retention: 30 days
- Levels: INFO, WARNING, ERROR

## 🚨 Security Features

- **SSL/TLS** - Encrypted MongoDB connections
- **JWT Authentication** - Centralized with Stardust-V1
- **Soft Delete** - Data retention and recovery
- **Audit Logging** - FHIR R5 Provenance resources
- **Input Validation** - Pydantic models
- **Error Handling** - Comprehensive error responses

## 🔄 Data Import

The system includes JSON import scripts for initial data loading:

```bash
# Import patient data
python docs/JSON-DB-IMPORT/import_script/import_latest_amy_data.py
```

## 📚 Documentation

- [Project Management Plan](docs/ISO29110-4-1_Project_Management_Plan.md)
- [Software Architecture Document](docs/Software_Architecture_Document.md)
- [Software Requirements Specification](docs/Software_Requirements_Specification.md)
- [Test Plan](docs/Test_Plan.md)
- [Stardust-V1 Authentication Handbook](docs/Stardust-V1%20Centralized%20JWT%20Authentication%20Handbook.md)
- [Production Cluster Guide](docs/CORUSCANT_CLUSTER_PRODUCTION_GUIDE.md)

## 🐛 Troubleshooting

### Common Issues

1. **MongoDB Connection Failed**
   - Check SSL certificates in `/ssl/`
   - Verify network connectivity to `coruscant.my-firstcare.com:27023`
   - Confirm credentials: `opera_admin` / `Sim!443355`

2. **JWT Authentication Failed**
   - Verify Stardust-V1 is accessible
   - Check JWT token validity
   - Ensure `ENABLE_JWT_AUTH=true`

3. **Device Data Not Received**
   - Validate device exists in database
   - Check device MAC/IMEI format
   - Verify data payload structure

### Logs
```bash
# View application logs
docker-compose logs opera-panel

# View specific error logs
docker-compose logs opera-panel | grep ERROR
```

## 🤝 Contributing

1. Follow the established code structure
2. Add comprehensive error handling
3. Include audit logging for all operations
4. Update documentation for new features
5. Test with production data structure

## 📄 License

This project is proprietary to My FirstCare. All rights reserved.

---

**Status**: ✅ **PRODUCTION READY**  
**Version**: 1.0.0  
**Last Updated**: December 2024 