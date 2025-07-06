# My FirstCare Opera Panel API Testing Guide

## 🚀 Quick Start

### 1. Import Files to Postman
1. **Collection**: Import `My_FirstCare_Opera_Panel_API.postman_collection.json`
2. **Environment**: Import `My_FirstCare_Opera_Panel.postman_environment.json`
3. **Select Environment**: Choose "My FirstCare Opera Panel - Local" in Postman

### 2. Start Testing
1. **Login First**: Run the "Login" request in the Authentication folder
2. **Verify Token**: Check that `access_token` is populated in environment variables
3. **Test Endpoints**: All other requests will automatically use the JWT token

## 📋 API Endpoints Overview

### Authentication Endpoints
- `POST /auth/login` - Login with credentials
- `POST /auth/refresh` - Refresh JWT token
- `GET /auth/me` - Get current user info

### Master Data Endpoints (Thailand Administrative Hierarchy)
- `GET /admin/master-data/provinces` - 99 provinces
- `GET /admin/master-data/districts` - 952 districts
- `GET /admin/master-data/sub_districts` - Thousands of sub-districts
- `GET /admin/master-data/hospital_types` - 21 hospital types
- `GET /admin/master-data/hospitals` - 51+ hospitals

### Admin Panel Endpoints
- `GET /admin/patients` - 431 patient records
- `GET /admin/devices` - 308 devices (AVA4, Kati, Qube-Vital)
- `GET /admin/medical-history/{type}` - 21,853+ medical records
- `GET /admin/analytics` - Dashboard statistics
- `GET /admin/audit-log` - FHIR R5 audit logs

### Device API Endpoints
- `GET /api/ava4/devices` - 153 AVA4 devices
- `GET /api/kati/devices` - 154 Kati Watch devices
- `GET /api/qube-vital/devices` - Qube-Vital devices

## 🔧 Environment Variables

### Authentication
- `admin_username`: admin
- `admin_password`: Sim!443355
- `access_token`: Auto-populated from login
- `refresh_token`: Auto-populated from login

### API Configuration
- `base_url`: http://localhost:5055
- `api_version`: v2
- `environment`: local

### Test Data
- `test_province_code`: 10 (Bangkok)
- `test_district_code`: 1001 (Phra Nakhon)
- `test_sub_district_code`: 100101
- `pagination_limit`: 10
- `pagination_skip`: 0

## 📊 Testing Scenarios

### 1. Authentication Flow
```
1. POST /auth/login
   - Body: {"username": "admin", "password": "Sim!443355"}
   - Expected: 200 OK with access_token and refresh_token

2. GET /auth/me
   - Header: Authorization: Bearer {{access_token}}
   - Expected: 200 OK with user information

3. POST /auth/refresh
   - Body: {"refresh_token": "{{refresh_token}}"}
   - Expected: 200 OK with new access_token
```

### 2. Master Data Relationships
```
1. GET /admin/master-data/provinces
   - Expected: 99 provinces with relationship info

2. GET /admin/master-data/districts?province_code=10
   - Expected: 52 Bangkok districts

3. GET /admin/master-data/sub_districts?province_code=10&district_code=1003
   - Expected: 8 sub-districts in Dusit district

4. GET /admin/master-data/hospitals?province_code=10
   - Expected: 18 hospitals in Bangkok
```

### 3. Device Management
```
1. GET /admin/devices?device_type=ava4
   - Expected: 153 AVA4 devices

2. GET /admin/devices?device_type=kati
   - Expected: 154 Kati Watch devices

3. GET /api/ava4/devices
   - Expected: Device-specific API response

4. GET /api/kati/devices
   - Expected: Kati Watch devices with detailed status
```

### 4. Medical Data
```
1. GET /admin/medical-history/blood_pressure?limit=10
   - Expected: 10 blood pressure records from 21,748 total

2. GET /admin/medical-history/blood_sugar?limit=5
   - Expected: 5 blood sugar records from 105 total

3. GET /admin/patients?search=John&limit=5
   - Expected: Patients matching "John" in name fields
```

## 🎯 Common Query Parameters

### Pagination
- `limit`: Number of records to return (default: 10)
- `skip`: Number of records to skip (default: 0)

### Filtering
- `province_code`: Filter by province (e.g., 10 for Bangkok)
- `district_code`: Filter by district (e.g., 1001 for Phra Nakhon)
- `device_type`: Filter devices (ava4, kati, qube-vital)
- `active_only`: Show only active devices (true/false)

### Search
- `search`: Search by name (supports Thai and English)

## 📈 Expected Response Formats

### Success Response
```json
{
  "success": true,
  "data": [...],
  "total": 100,
  "limit": 10,
  "skip": 0,
  "relationships": {
    "parent": "provinces",
    "children": ["districts"]
  }
}
```

### Error Response
```json
{
  "success": false,
  "error": "Error message",
  "code": "ERROR_CODE"
}
```

### Authentication Response
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

## 🔍 Testing Best Practices

### 1. Pre-request Scripts
```javascript
// Set timestamp for data submissions
pm.environment.set('timestamp', new Date().toISOString());

// Generate test data
pm.environment.set('test_patient_id', 'TEST_' + Date.now());
```

### 2. Test Scripts
```javascript
// Check response status
pm.test("Status code is 200", function () {
    pm.response.to.have.status(200);
});

// Validate response structure
pm.test("Response has required fields", function () {
    const response = pm.response.json();
    pm.expect(response).to.have.property('success');
    pm.expect(response).to.have.property('data');
});

// Save response data for next requests
if (pm.response.code === 200) {
    const response = pm.response.json();
    if (response.data && response.data.length > 0) {
        pm.environment.set('patient_id', response.data[0]._id);
    }
}
```

### 3. Data Validation
```javascript
// Validate ObjectId format
pm.test("IDs are valid ObjectIds", function () {
    const response = pm.response.json();
    response.data.forEach(item => {
        pm.expect(item._id).to.match(/^[a-f\d]{24}$/i);
    });
});

// Validate relationships
pm.test("Relationships are correct", function () {
    const response = pm.response.json();
    if (response.relationships) {
        pm.expect(response.relationships).to.have.property('parent');
        pm.expect(response.relationships).to.have.property('children');
    }
});
```

## 🛠️ Troubleshooting

### Common Issues

1. **401 Unauthorized**
   - Solution: Run the Login request first
   - Check: `access_token` is set in environment variables

2. **500 Internal Server Error**
   - Check: Docker container is running
   - Check: MongoDB connection is active
   - Check: Logs in `/logs/app.log`

3. **Empty Response**
   - Check: Query parameters are correct
   - Check: Data exists in database
   - Try: Reduce filters or search terms

### Health Check
```
GET /health
Expected Response:
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00.000Z",
  "database": "connected",
  "auth": "active"
}
```

## 📚 Additional Resources

- **Swagger UI**: http://localhost:5055/docs
- **OpenAPI Schema**: http://localhost:5055/openapi.json
- **ReDoc**: http://localhost:5055/redoc
- **Application Logs**: `/logs/app.log`

## 🚀 Next Steps

1. **Automated Testing**: Set up Newman for CI/CD
2. **Performance Testing**: Use Postman monitors
3. **Load Testing**: Configure stress tests
4. **Documentation**: Generate API documentation from collection

---

**Note**: This API manages sensitive medical data. Always use proper authentication and follow data protection guidelines in production environments. 