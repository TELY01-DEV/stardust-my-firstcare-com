# My FirstCare Opera Panel - External Access Configuration

## 🌐 External API Access

The My FirstCare Opera Panel API is now configured for external system integration with the following specifications:

### **Access Point Configuration**
- **Domain**: `stardust.myfirstcare.com`
- **Port**: `5054`
- **Base URL**: `http://stardust.myfirstcare.com:5054`
- **Protocol**: HTTP (can be upgraded to HTTPS as needed)

### **CORS Policy**
- **Allow Origins**: `*` (All domains allowed)
- **Allow Methods**: `*` (GET, POST, PUT, DELETE, OPTIONS)
- **Allow Headers**: `*` (All headers including Authorization)
- **Allow Credentials**: `true`

## 🔗 API Endpoints

### **System Endpoints**
```bash
# Health Check (No authentication required)
GET http://stardust.myfirstcare.com:5054/health

# API Documentation (No authentication required)
GET http://stardust.myfirstcare.com:5054/docs

# Root Information (No authentication required)
GET http://stardust.myfirstcare.com:5054/
```

### **Authentication Endpoints**
```bash
# Login
POST http://stardust.myfirstcare.com:5054/auth/login
Content-Type: application/json
{
    "username": "your_username",
    "password": "your_password"
}

# Get Current User
GET http://stardust.myfirstcare.com:5054/auth/me
Authorization: Bearer <access_token>

# Refresh Token
POST http://stardust.myfirstcare.com:5054/auth/refresh
Authorization: Bearer <refresh_token>
```

### **Device Data Endpoints**
```bash
# Submit AVA4 Device Data
POST http://stardust.myfirstcare.com:5054/api/ava4/data
Authorization: Bearer <access_token>
Content-Type: application/json

# Submit Kati Watch Data
POST http://stardust.myfirstcare.com:5054/api/kati/data
Authorization: Bearer <access_token>
Content-Type: application/json

# Submit Qube-Vital Data
POST http://stardust.myfirstcare.com:5054/api/qube-vital/data
Authorization: Bearer <access_token>
Content-Type: application/json
```

### **Admin Panel Endpoints**
```bash
# Get Patients
GET http://stardust.myfirstcare.com:5054/admin/patients
Authorization: Bearer <access_token>

# Get Devices
GET http://stardust.myfirstcare.com:5054/admin/devices?device_type=ava4
Authorization: Bearer <access_token>

# Get Medical History
GET http://stardust.myfirstcare.com:5054/admin/medical-history/blood_pressure
Authorization: Bearer <access_token>

# Get Master Data
GET http://stardust.myfirstcare.com:5054/admin/master-data/hospitals
Authorization: Bearer <access_token>
```

## 🔐 Authentication Flow

### **1. Login Process**
```bash
curl -X POST "http://stardust.myfirstcare.com:5054/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "your_username",
    "password": "your_password"
  }'
```

**Response:**
```json
{
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "token_type": "bearer",
    "expires_in": 3600,
    "user_id": "user_123",
    "username": "your_username"
}
```

### **2. Using Access Token**
```bash
curl -X GET "http://stardust.myfirstcare.com:5054/admin/patients" \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
```

## 🌍 External System Integration Examples

### **JavaScript/Node.js**
```javascript
const BASE_URL = 'http://stardust.myfirstcare.com:5054';

// Login
const login = async (username, password) => {
    const response = await fetch(`${BASE_URL}/auth/login`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ username, password })
    });
    return await response.json();
};

// Get Patients
const getPatients = async (accessToken) => {
    const response = await fetch(`${BASE_URL}/admin/patients`, {
        headers: {
            'Authorization': `Bearer ${accessToken}`
        }
    });
    return await response.json();
};

// Submit Device Data
const submitDeviceData = async (accessToken, deviceData) => {
    const response = await fetch(`${BASE_URL}/api/ava4/data`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${accessToken}`
        },
        body: JSON.stringify(deviceData)
    });
    return await response.json();
};
```

### **Python**
```python
import requests

BASE_URL = 'http://stardust.myfirstcare.com:5054'

# Login
def login(username, password):
    response = requests.post(f'{BASE_URL}/auth/login', json={
        'username': username,
        'password': password
    })
    return response.json()

# Get Patients
def get_patients(access_token):
    headers = {'Authorization': f'Bearer {access_token}'}
    response = requests.get(f'{BASE_URL}/admin/patients', headers=headers)
    return response.json()

# Submit Device Data
def submit_device_data(access_token, device_data):
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    response = requests.post(f'{BASE_URL}/api/ava4/data', 
                           json=device_data, headers=headers)
    return response.json()
```

### **cURL Examples**
```bash
# Complete workflow example
#!/bin/bash

BASE_URL="http://stardust.myfirstcare.com:5054"

# 1. Login and get token
TOKEN=$(curl -s -X POST "$BASE_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"Sim!443355"}' \
  | jq -r '.access_token')

# 2. Get patients
curl -H "Authorization: Bearer $TOKEN" \
  "$BASE_URL/admin/patients?limit=10"

# 3. Submit device data
curl -X POST "$BASE_URL/api/ava4/data" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "timestamp": "2024-01-15T10:30:00Z",
    "device_id": "AA:BB:CC:DD:EE:FF",
    "type": "BLOOD_PRESSURE",
    "data": {
      "systolic": 120,
      "diastolic": 80,
      "pulse": 72
    }
  }'
```

## 🔧 Configuration Details

### **Docker Configuration**
The API is configured to run on port 5054 and accept external connections:

```yaml
# docker-compose.yml
services:
  opera-panel:
    ports:
      - "5054:5054"
    environment:
      - PORT=5054
      - HOST=0.0.0.0
```

### **CORS Configuration**
```python
# main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # Allows all domains
    allow_credentials=True,       # Allows cookies/auth headers
    allow_methods=["*"],          # Allows all HTTP methods
    allow_headers=["*"],          # Allows all headers
)
```

## 🚀 Deployment

### **Start the Service**
```bash
# Using Docker Compose
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f opera-panel
```

### **Verify External Access**
```bash
# Test from external system
curl http://stardust.myfirstcare.com:5054/health

# Expected response
{
    "status": "healthy",
    "mongodb": "connected",
    "version": "1.0.0",
    "environment": "production"
}
```

## 📊 Monitoring

### **Health Check**
```bash
# Regular health monitoring
curl http://stardust.myfirstcare.com:5054/health
```

### **API Documentation**
- **Swagger UI**: http://stardust.myfirstcare.com:5054/docs
- **ReDoc**: http://stardust.myfirstcare.com:5054/redoc
- **OpenAPI JSON**: http://stardust.myfirstcare.com:5054/openapi.json

## 🛡️ Security Considerations

### **Current Configuration**
- ✅ JWT Authentication required for protected endpoints
- ✅ CORS enabled for all domains (suitable for development/testing)
- ✅ HTTPS can be added via reverse proxy if needed
- ✅ Audit logging for all operations

### **Production Recommendations**
For production environments, consider:

1. **Restrict CORS Origins**:
   ```python
   allow_origins=["https://trusted-domain.com", "https://another-trusted-domain.com"]
   ```

2. **Enable HTTPS**:
   - Use reverse proxy (nginx/Apache)
   - SSL/TLS certificates
   - Force HTTPS redirects

3. **Rate Limiting**:
   - Implement API rate limiting
   - Monitor for abuse patterns

4. **IP Whitelisting**:
   - Restrict access to known IP ranges
   - Use firewall rules

## 📞 Support

For technical support or integration assistance:
- **API Documentation**: http://stardust.myfirstcare.com:5054/docs
- **Health Status**: http://stardust.myfirstcare.com:5054/health
- **Contact**: Development Team

---

**Last Updated**: January 2024  
**API Version**: 1.0.0  
**External Access**: Enabled on stardust.myfirstcare.com:5054 