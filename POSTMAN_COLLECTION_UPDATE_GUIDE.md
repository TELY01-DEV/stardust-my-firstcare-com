# Postman Collection Update Guide

## ✅ **Updated Collections Available**

Following the resolution of FastAPI duplicate Operation ID warnings, the Postman collections have been completely updated to reflect the current API structure.

## 📁 **New Collection Files**

### **Main Collection** 
- **File**: `My_FirstCare_Opera_Panel_API_UPDATED.postman_collection.json`
- **Environment**: `My_FirstCare_Opera_Panel_UPDATED.postman_environment.json`

### **Legacy Collections** (Still Available)
- `My_FirstCare_Opera_Panel_API.postman_collection.json`
- `My_FirstCare_Opera_Panel_API_CRUD.postman_collection.json`
- `Device_Mapping_API.postman_collection.json`

## 🆕 **Latest Update: Request ID Validation (2024-07-07)**

### **🔧 Request ID Fix Validation**

The collection has been updated to test the recent **request_id null issue fix**:

#### **What Was Fixed**
- All API endpoints previously returned `"request_id": null`
- Now automatically generates UUID when no `X-Request-ID` header provided
- Preserves custom `X-Request-ID` headers when provided

#### **New Test Scripts Added**

**1. Request ID Presence Validation**
```javascript
pm.test('Response contains valid request_id', function () {
    const jsonData = pm.response.json();
    pm.expect(jsonData).to.have.property('request_id');
    pm.expect(jsonData.request_id).to.not.be.null;
    pm.expect(jsonData.request_id).to.not.be.undefined;
    pm.expect(jsonData.request_id).to.be.a('string');
    pm.expect(jsonData.request_id.length).to.be.above(0);
});
```

**2. UUID Format Validation**
```javascript
pm.test('Request ID is valid UUID format', function () {
    const jsonData = pm.response.json();
    const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
    pm.expect(jsonData.request_id).to.match(uuidRegex);
});
```

**3. Custom Header Preservation Test**
```javascript
pm.test('Custom Request ID is preserved', function () {
    const jsonData = pm.response.json();
    pm.expect(jsonData.request_id).to.eql('test-postman-12345');
});
```

#### **Updated Endpoints**

✅ **Authentication Endpoints**:
- `GET /auth/me` - Now validates request_id is valid UUID
- `GET /health` - Tests both auto-generated and custom request IDs
- `GET /health` (with custom header) - Tests header preservation

#### **Recommended Test Script for All Endpoints**

Add this test script to **any endpoint** to validate request_id behavior:

```javascript
// Standard Request ID Validation
pm.test('API Response Structure - Request ID', function () {
    const jsonData = pm.response.json();
    
    // Test request_id is present
    pm.expect(jsonData).to.have.property('request_id');
    pm.expect(jsonData.request_id).to.not.be.null;
    pm.expect(jsonData.request_id).to.be.a('string');
    pm.expect(jsonData.request_id.length).to.be.above(0);
    
    // Test it's either a UUID or custom value
    const customRequestId = pm.request.headers.get('X-Request-ID');
    if (customRequestId) {
        pm.expect(jsonData.request_id).to.eql(customRequestId);
        console.log('Custom Request ID preserved:', jsonData.request_id);
    } else {
        const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
        pm.expect(jsonData.request_id).to.match(uuidRegex);
        console.log('Auto-generated UUID:', jsonData.request_id);
    }
});
```

#### **Testing Both Scenarios**

**Scenario 1: Auto-Generated UUID**
```bash
# Request without X-Request-ID header
curl -X GET "http://localhost:5054/health"
# Response: "request_id": "a3c3ee46-ddfa-4d94-9e8a-ca2590d9d9fd"
```

**Scenario 2: Custom Request ID**
```bash
# Request with custom X-Request-ID header
curl -X GET "http://localhost:5054/health" -H "X-Request-ID: my-custom-id-123"
# Response: "request_id": "my-custom-id-123"
```

## 🔧 **Key Updates Made**

### **1. Fixed Function Name Conflicts**
The API previously had duplicate function names across different routers that caused FastAPI Operation ID warnings:

**Before (Caused Warnings)**:
```
admin.py: get_device, create_device, update_device, delete_device
admin_crud.py: get_device, create_device, update_device, delete_device  
device_crud.py: get_device, create_device, update_device, delete_device
```

**After (No Warnings)**:
```
admin.py: legacy_get_device, legacy_create_device, legacy_update_device, legacy_delete_device
admin_crud.py: admin_get_device, admin_create_device, admin_update_device, admin_delete_device
device_crud.py: api_get_device, api_create_device, api_update_device, api_delete_device
```

### **2. Updated Collection Structure**

The new collection includes properly organized endpoints:

#### **Authentication**
- `POST /auth/login` - Get JWT token
- `GET /auth/me` - Get current user info  
- `GET /health` - System health check

#### **Admin - Patients CRUD**
- `GET /admin/patients` - List all patients
- `GET /admin/patients/{id}` - Get patient by ID
- `POST /admin/patients` - Create new patient

#### **Admin - Device CRUD** 
- `GET /admin/devices/{id}?device_type=X` - Get device by ID (admin)
- `POST /admin/devices` - Create device (admin)
- `PUT /admin/devices/{id}?device_type=X` - Update device (admin)
- `DELETE /admin/devices/{id}?device_type=X` - Delete device (admin)

#### **API - Device CRUD**
- `GET /api/devices?device_type=X` - List devices (API)
- `GET /api/devices/{id}?device_type=X` - Get device by ID (API)
- `POST /api/devices` - Create device (API)
- `PUT /api/devices/{id}?device_type=X` - Update device (API)
- `DELETE /api/devices/{id}?device_type=X` - Delete device (API)

#### **Device Data CRUD**
- `GET /api/devices/data` - Get device observations
- `POST /api/devices/data` - Create device data
- `GET /api/devices/data/{id}` - Get specific observation

#### **Device Specific APIs**
- `GET /admin/devices?device_type=ava4` - AVA4 devices
- `GET /api/kati/devices` - Kati devices
- `GET /api/kati/devices/{id}` - Specific Kati device

#### **Device Mapping**
- `GET /admin/device-mapping` - List mappings
- `GET /admin/device-mapping/{patient_id}` - Patient device mapping
- `GET /admin/device-mapping/device-types` - Available device types

#### **FHIR Audit Log**
- `GET /admin/audit-log` - FHIR R5 compliant audit logs

#### **Analytics**
- `GET /admin/analytics` - System analytics dashboard

## 🚀 **How to Use the Updated Collection**

### **1. Import the Collection**
1. Open Postman
2. Click **Import**
3. Select `My_FirstCare_Opera_Panel_API_UPDATED.postman_collection.json`
4. Import the environment: `My_FirstCare_Opera_Panel_UPDATED.postman_environment.json`

### **2. Configure Environment**
Set these variables in your environment:
```json
{
  "base_url": "http://localhost:5054",
  "username": "dev_user", 
  "password": "dev_password"
}
```

### **3. Auto-Authentication**
The collection includes **automatic JWT token management**:
- Pre-request script automatically logs in if no token exists
- Token is stored and reused across requests
- No manual token management needed

### **4. Test Automation**
Each request includes comprehensive test scripts:
```javascript
pm.test('Response successful', function () {
    pm.response.to.have.status(200);
    const jsonData = pm.response.json();
    pm.expect(jsonData.success).to.be.true;
});
```

## 🧪 **Running Tests**

### **Using Newman (Command Line)**
```bash
# Install Newman globally
npm install -g newman

# Run the entire collection
newman run My_FirstCare_Opera_Panel_API_UPDATED.postman_collection.json \
  -e My_FirstCare_Opera_Panel_UPDATED.postman_environment.json \
  --reporters cli,json \
  --reporter-json-export results.json

# Run specific folder
newman run My_FirstCare_Opera_Panel_API_UPDATED.postman_collection.json \
  -e My_FirstCare_Opera_Panel_UPDATED.postman_environment.json \
  --folder "Admin - Device CRUD"
```

### **Using Postman Collection Runner**
1. Open Postman
2. Click on collection → **Run collection**
3. Select environment: "My FirstCare Opera Panel - Updated 2024"
4. Choose specific folders or run all
5. Click **Run**

## 📊 **Test Results Example**

Expected output when running tests:
```
┌─────────────────────────┬───────────────┬─────────────────┐
│                         │      executed │          failed │
├─────────────────────────┼───────────────┼─────────────────┤
│              iterations │             1 │               0 │
├─────────────────────────┼───────────────┼─────────────────┤
│                requests │            25 │               0 │
├─────────────────────────┼───────────────┼─────────────────┤
│            test-scripts │            50 │               0 │
├─────────────────────────┼───────────────┼─────────────────┤
│      prerequest-scripts │            25 │               0 │
├─────────────────────────┼───────────────┼─────────────────┤
│              assertions │            75 │               0 │
└─────────────────────────┴───────────────┴─────────────────┘
```

## 🔄 **API Endpoint Mapping**

| **Collection Name** | **HTTP Method** | **Endpoint** | **Function Name** |
|---------------------|-----------------|--------------|-------------------|
| Get Device by ID (Admin) | GET | `/admin/devices/{id}` | admin_get_device |
| Create Device (Admin) | POST | `/admin/devices` | admin_create_device |
| Update Device (Admin) | PUT | `/admin/devices/{id}` | admin_update_device |
| Delete Device (Admin) | DELETE | `/admin/devices/{id}` | admin_delete_device |
| Get Device by ID (API) | GET | `/api/devices/{id}` | api_get_device |
| Create Device (API) | POST | `/api/devices` | api_create_device |
| Update Device (API) | PUT | `/api/devices/{id}` | api_update_device |
| Delete Device (API) | DELETE | `/api/devices/{id}` | api_delete_device |
| Get Devices (Legacy) | GET | `/admin/devices` | legacy_get_device |

## 🛠 **Troubleshooting**

### **Common Issues**

1. **401 Unauthorized**
   - Check username/password in environment
   - Verify JWT token is being set correctly
   - Try manually running the Login request

2. **404 Not Found**
   - Ensure Docker container is running: `docker-compose ps`
   - Check base_url is correct: `http://localhost:5054`
   - Verify endpoint exists in API docs: `http://localhost:5054/docs`

3. **Validation Errors**
   - Check request body format matches expected schema
   - Ensure required fields are provided
   - Verify ObjectId format for IDs (24-character hex string)

### **Environment Variables**
Make sure these are set correctly:
```json
{
  "base_url": "http://localhost:5054",
  "username": "dev_user",
  "password": "dev_password",
  "patient_id": "622035a5fd26d7b6d9b7730c",
  "device_id": "620c83c68ae03f05312cb9b8",
  "hospital_id": "620c83a78ae03f05312cb9b5"
}
```

## 📈 **Benefits of Updated Collection**

✅ **No More Warnings**: Fixed all FastAPI Operation ID conflicts  
✅ **Comprehensive Coverage**: All endpoints included with tests  
✅ **Auto-Authentication**: Automatic JWT token management  
✅ **Better Organization**: Logical grouping of related endpoints  
✅ **Test Automation**: Built-in test scripts for validation  
✅ **Environment Support**: Configurable for different environments  
✅ **Newman Compatible**: Ready for CI/CD pipeline integration  

## 🚀 **Next Steps**

1. **Import** the updated collection and environment
2. **Configure** your environment variables
3. **Run** a few test requests to verify connectivity
4. **Automate** testing in your CI/CD pipeline using Newman
5. **Monitor** API health using the built-in test assertions

The updated Postman collection provides a comprehensive testing framework for the My FirstCare Opera Panel API with resolved warnings and improved organization. 