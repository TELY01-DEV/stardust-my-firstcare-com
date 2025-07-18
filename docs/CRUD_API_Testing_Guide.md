# My FirstCare Opera Panel - Complete CRUD API Testing Guide

## Overview

This guide provides comprehensive testing instructions for all CRUD (Create, Read, Update, Delete) operations in the My FirstCare Opera Panel API. The system now supports full CRUD operations for:

- **Patients** - Complete patient management
- **Devices** - IoT device management (AVA4, Kati, Qube-Vital)
- **Device Data** - Medical measurements and observations
- **Medical History** - Patient health records
- **Master Data** - Reference data (hospitals, provinces, districts, etc.)

## Quick Start

### 1. Import Postman Collection and Environment

1. **Import Collection**: `My_FirstCare_Opera_Panel_API_CRUD.postman_collection.json`
2. **Import Environment**: `My_FirstCare_Opera_Panel_CRUD.postman_environment.json`
3. **Set Environment**: Select the imported environment in Postman

### 2. Authentication

The collection includes automatic authentication. The first request will automatically log in using the credentials in the environment variables.

**Manual Login:**
```bash
POST {{base_url}}/auth/login
{
    "username": "admin",
    "password": "Sim!443355"
}
```

## CRUD Operations by Entity

### 1. Patients CRUD

#### Create Patient
```bash
POST {{base_url}}/admin/patients
{
    "first_name": "John",
    "last_name": "Doe",
    "nickname": "Johnny",
    "gender": "male",
    "birth_date": "1990-01-01T00:00:00Z",
    "id_card": "1234567890123",
    "phone": "0812345678",
    "email": "john.doe@example.com",
    "address": "123 Test Street",
    "province_code": "10",
    "district_code": "1001",
    "sub_district_code": "100101",
    "postal_code": "10110",
    "blood_type": "O+",
    "height": 175.5,
    "weight": 70.0,
    "bmi": 22.8,
    "new_hospital_ids": ["HOSPITAL_ID_HERE"]
}
```

#### Read Patients
```bash
# Get all patients
GET {{base_url}}/admin/patients?limit=50&skip=0

# Get specific patient
GET {{base_url}}/admin/patients/{{patient_id}}

# Search patients
GET {{base_url}}/admin/patients?search=John&limit=10
```

#### Update Patient
```bash
PUT {{base_url}}/admin/patients/{{patient_id}}
{
    "first_name": "John Updated",
    "phone": "0898765432",
    "weight": 72.0,
    "bmi": 23.5
}
```

#### Delete Patient
```bash
DELETE {{base_url}}/admin/patients/{{patient_id}}
```

### 2. Devices CRUD

#### Create Device
```bash
POST {{base_url}}/api/devices
{
    "device_type": "ava4",
    "mac_address": "AA:BB:CC:DD:EE:FF",
    "serial_number": "AVA4-2024-001",
    "model": "AVA4-Pro",
    "firmware_version": "1.2.3",
    "hospital_id": "HOSPITAL_ID_HERE",
    "patient_id": "PATIENT_ID_HERE",
    "location": "Room 101",
    "status": "active",
    "configuration": {
        "measurement_interval": 300,
        "auto_sync": true,
        "alerts_enabled": true
    }
}
```

#### Read Devices
```bash
# Get all devices
GET {{base_url}}/api/devices?limit=50&skip=0

# Get devices by type
GET {{base_url}}/api/devices?device_type=ava4&limit=50

# Get specific device
GET {{base_url}}/api/devices/{{device_id}}?device_type=ava4

# Filter by hospital
GET {{base_url}}/api/devices?hospital_id=HOSPITAL_ID&limit=50
```

#### Update Device
```bash
PUT {{base_url}}/api/devices/{{device_id}}?device_type=ava4
{
    "firmware_version": "1.2.4",
    "location": "Room 102",
    "status": "active",
    "configuration": {
        "measurement_interval": 600,
        "auto_sync": true,
        "alerts_enabled": false
    }
}
```

#### Delete Device
```bash
DELETE {{base_url}}/api/devices/{{device_id}}?device_type=ava4
```

### 3. Device Data CRUD

#### Create Device Data
```bash
POST {{base_url}}/api/devices/data
{
    "timestamp": "2024-01-15T10:30:00Z",
    "device_id": "AA:BB:CC:DD:EE:FF",
    "device_type": "ava4",
    "data_type": "blood_pressure",
    "values": {
        "systolic": 120,
        "diastolic": 80,
        "pulse": 72,
        "value": 120,
        "unit": "mmHg",
        "unit_code": "mm[Hg]"
    },
    "patient_id": "PATIENT_ID_HERE",
    "notes": "Morning measurement"
}
```

#### Read Device Data
```bash
# Get all device data
GET {{base_url}}/api/devices/data?limit=50&skip=0

# Get data by device
GET {{base_url}}/api/devices/data?device_id=AA:BB:CC:DD:EE:FF&limit=50

# Get data by patient
GET {{base_url}}/api/devices/data?patient_id=PATIENT_ID&limit=50

# Get specific observation
GET {{base_url}}/api/devices/data/{{observation_id}}
```

#### Update Device Data
```bash
PUT {{base_url}}/api/devices/data/{{observation_id}}
{
    "values": {
        "systolic": 125,
        "diastolic": 82,
        "pulse": 75,
        "value": 125,
        "unit": "mmHg",
        "unit_code": "mm[Hg]"
    },
    "notes": "Corrected measurement"
}
```

#### Delete Device Data
```bash
DELETE {{base_url}}/api/devices/data/{{observation_id}}
```

### 4. Medical History CRUD

#### Create Medical History
```bash
POST {{base_url}}/admin/medical-history
{
    "patient_id": "PATIENT_ID_HERE",
    "history_type": "blood_pressure",
    "timestamp": "2024-01-15T10:30:00Z",
    "device_id": "DEVICE_ID_HERE",
    "values": {
        "systolic": 120,
        "diastolic": 80,
        "pulse": 72,
        "measurement_time": "2024-01-15T10:30:00Z"
    },
    "notes": "Manual entry"
}
```

#### Read Medical History
```bash
# Get history by type
GET {{base_url}}/admin/medical-history/blood_pressure?limit=50&skip=0

# Get history by patient
GET {{base_url}}/admin/medical-history/blood_pressure?patient_id=PATIENT_ID&limit=50

# Get specific record
GET {{base_url}}/admin/medical-history/blood_pressure/{{record_id}}

# Available history types:
# - blood_pressure
# - blood_sugar
# - body_data
# - creatinine
# - lipid
# - sleep_data
# - spo2
# - step
# - temperature
# - medication
```

#### Update Medical History
```bash
PUT {{base_url}}/admin/medical-history/blood_pressure/{{record_id}}
{
    "values": {
        "systolic": 125,
        "diastolic": 82,
        "pulse": 75,
        "measurement_time": "2024-01-15T10:30:00Z"
    },
    "notes": "Updated measurement"
}
```

#### Delete Medical History
```bash
DELETE {{base_url}}/admin/medical-history/blood_pressure/{{record_id}}
```

### 5. Master Data CRUD

#### Create Master Data
```bash
POST {{base_url}}/admin/master-data
{
    "data_type": "hospitals",
    "name": [
        {"lang": "th", "name": "โรงพยาบาลทดสอบ"},
        {"lang": "en", "name": "Test Hospital"}
    ],
    "code": 9999,
    "is_active": true,
    "province_code": 10,
    "district_code": 1001,
    "sub_district_code": 100101,
    "additional_fields": {
        "en_name": "Test Hospital",
        "organizecode": 9999,
        "hospital_area_code": "TEST",
        "bed_capacity": 100,
        "location": [13.7563, 100.5018],
        "service_plan_type": "A"
    }
}
```

#### Read Master Data
```bash
# Get hospitals
GET {{base_url}}/admin/master-data/hospitals?limit=50&skip=0

# Get provinces
GET {{base_url}}/admin/master-data/provinces?limit=50

# Get districts by province
GET {{base_url}}/admin/master-data/districts?province_code=10&limit=50

# Get sub-districts by province and district
GET {{base_url}}/admin/master-data/sub_districts?province_code=10&district_code=1003&limit=50

# Get hospital types
GET {{base_url}}/admin/master-data/hospital_types?limit=50

# Get specific record
GET {{base_url}}/admin/master-data/hospitals/{{master_data_id}}

# Search master data
GET {{base_url}}/admin/master-data/hospitals?search=Bangkok&limit=10
```

#### Update Master Data
```bash
PUT {{base_url}}/admin/master-data/hospitals/{{master_data_id}}
{
    "name": [
        {"lang": "th", "name": "โรงพยาบาลทดสอบ (อัปเดต)"},
        {"lang": "en", "name": "Test Hospital (Updated)"}
    ],
    "is_active": true,
    "additional_fields": {
        "bed_capacity": 150,
        "service_plan_type": "F3"
    }
}
```

#### Delete Master Data
```bash
DELETE {{base_url}}/admin/master-data/hospitals/{{master_data_id}}
```

## Advanced Testing Scenarios

### 1. Complete Patient Workflow
```bash
# 1. Create patient
POST {{base_url}}/admin/patients
# Save patient_id from response

# 2. Create device for patient
POST {{base_url}}/api/devices
# Save device_id from response

# 3. Submit device data
POST {{base_url}}/api/devices/data

# 4. View patient's medical history
GET {{base_url}}/admin/medical-history/blood_pressure?patient_id={{patient_id}}

# 5. Update patient information
PUT {{base_url}}/admin/patients/{{patient_id}}

# 6. Delete patient (soft delete)
DELETE {{base_url}}/admin/patients/{{patient_id}}
```

### 2. Device Management Workflow
```bash
# 1. Create AVA4 device
POST {{base_url}}/api/devices
{
    "device_type": "ava4",
    "mac_address": "AA:BB:CC:DD:EE:FF",
    ...
}

# 2. Create Kati device
POST {{base_url}}/api/devices
{
    "device_type": "kati",
    "mac_address": "11:22:33:44:55:66",
    ...
}

# 3. Create Qube-Vital device
POST {{base_url}}/api/devices
{
    "device_type": "qube-vital",
    "mac_address": "77:88:99:AA:BB:CC",
    ...
}

# 4. Get all devices
GET {{base_url}}/api/devices

# 5. Filter devices by type
GET {{base_url}}/api/devices?device_type=ava4

# 6. Update device configuration
PUT {{base_url}}/api/devices/{{device_id}}?device_type=ava4

# 7. Delete device
DELETE {{base_url}}/api/devices/{{device_id}}?device_type=ava4
```

### 3. Data Collection and Analysis
```bash
# 1. Submit various types of device data
POST {{base_url}}/api/devices/data (blood_pressure)
POST {{base_url}}/api/devices/data (heart_rate)
POST {{base_url}}/api/devices/data (temperature)
POST {{base_url}}/api/devices/data (weight)

# 2. Retrieve data by different filters
GET {{base_url}}/api/devices/data?device_id=MAC_ADDRESS
GET {{base_url}}/api/devices/data?patient_id=PATIENT_ID
GET {{base_url}}/api/devices/data?data_type=blood_pressure

# 3. View consolidated medical history
GET {{base_url}}/admin/medical-history/blood_pressure?patient_id=PATIENT_ID
GET {{base_url}}/admin/medical-history/step?patient_id=PATIENT_ID
```

## Data Types and Validation

### Device Types
- `ava4` - AVA4 Blood Pressure Monitor
- `kati` - Kati Smartwatch
- `qube-vital` - Qube-Vital Monitoring Device

### Medical Data Types
- `blood_pressure` - Blood pressure measurements
- `blood_sugar` - Blood glucose measurements
- `heart_rate` - Heart rate data
- `spo2` - Oxygen saturation
- `temperature` - Body temperature
- `weight` - Body weight
- `steps` - Step count
- `sleep` - Sleep data

### Master Data Types
- `hospitals` - Hospital information
- `provinces` - Thai provinces
- `districts` - Thai districts
- `sub_districts` - Thai sub-districts
- `hospital_types` - Hospital type classifications

## Error Handling

### Common HTTP Status Codes
- `200` - Success
- `201` - Created
- `400` - Bad Request (validation error)
- `401` - Unauthorized (authentication required)
- `403` - Forbidden (insufficient permissions)
- `404` - Not Found
- `409` - Conflict (duplicate data)
- `500` - Internal Server Error

### Example Error Response
```json
{
    "error": "Validation Error",
    "detail": "Device with this MAC address already exists",
    "code": 400
}
```

## Performance Testing

### Bulk Operations
```bash
# Test bulk patient creation
for i in {1..100}; do
    curl -X POST "{{base_url}}/admin/patients" \
    -H "Authorization: Bearer {{jwt_token}}" \
    -H "Content-Type: application/json" \
    -d '{"first_name":"Patient'$i'","last_name":"Test","gender":"male"}'
done

# Test pagination performance
GET {{base_url}}/admin/patients?limit=1000&skip=0
GET {{base_url}}/admin/patients?limit=1000&skip=1000
```

### Concurrent Testing
Use Postman's Collection Runner or Newman to test concurrent operations:
```bash
newman run collection.json -e environment.json --iteration-count 10 --parallel
```

## Security Testing

### Authentication Tests
```bash
# Test without token
GET {{base_url}}/admin/patients (should return 401)

# Test with invalid token
GET {{base_url}}/admin/patients
Authorization: Bearer invalid_token (should return 401)

# Test token refresh
POST {{base_url}}/auth/refresh
```

### Authorization Tests
```bash
# Test different user roles (if implemented)
# Test access to different endpoints with different user types
```

## Monitoring and Audit

### Audit Log Testing
```bash
# Perform various operations then check audit logs
POST {{base_url}}/admin/patients (create)
PUT {{base_url}}/admin/patients/{{patient_id}} (update)
DELETE {{base_url}}/admin/patients/{{patient_id}} (delete)

# Check audit logs
GET {{base_url}}/admin/audit-log?limit=50
```

### Analytics Testing
```bash
# Check dashboard analytics
GET {{base_url}}/admin/analytics

# Verify counts match actual data
GET {{base_url}}/admin/patients?limit=1 (check total)
GET {{base_url}}/admin/devices?device_type=ava4&limit=1 (check total)
```

## Troubleshooting

### Common Issues

1. **Authentication Errors**
   - Ensure JWT token is valid and not expired
   - Check username/password in environment variables

2. **404 Not Found**
   - Verify endpoint URLs are correct
   - Check if the resource exists before trying to access it

3. **Validation Errors**
   - Check required fields are provided
   - Verify data types match expected formats
   - Ensure ObjectIds are valid MongoDB ObjectIds

4. **Performance Issues**
   - Use pagination for large datasets
   - Implement proper indexing on frequently queried fields
   - Monitor query performance

### Debug Mode
Enable debug logging by setting environment variable:
```bash
export LOG_LEVEL=debug
```

## Best Practices

1. **Always use pagination** for list endpoints
2. **Implement proper error handling** in your client applications
3. **Use filters** to reduce data transfer
4. **Cache frequently accessed data** like master data
5. **Implement retry logic** for transient failures
6. **Monitor API performance** and usage patterns
7. **Keep audit logs** for compliance and troubleshooting
8. **Use HTTPS** in production environments
9. **Implement rate limiting** to prevent abuse
10. **Validate all input data** before processing

## Conclusion

This comprehensive CRUD API provides full lifecycle management for all entities in the My FirstCare Opera Panel system. The API follows RESTful principles and includes proper authentication, authorization, audit logging, and error handling.

## External Access Configuration

The API is now configured for external access:

- **Domain**: `stardust.myfirstcare.com`
- **Port**: `5054`
- **Full URL**: `http://stardust.myfirstcare.com:5054`
- **CORS**: Allows all domains (`*`)
- **API Documentation**: `http://stardust.myfirstcare.com:5054/docs`
- **Health Check**: `http://stardust.myfirstcare.com:5054/health`

### External System Integration

External systems can access the API using:

```bash
# Base URL for all API calls
BASE_URL="http://stardust.myfirstcare.com:5054"

# Example API calls
curl "$BASE_URL/health"
curl "$BASE_URL/docs"
curl -H "Authorization: Bearer <token>" "$BASE_URL/admin/patients"
```

### CORS Configuration

The API is configured to accept requests from any domain:
- `Access-Control-Allow-Origin: *`
- `Access-Control-Allow-Methods: *`
- `Access-Control-Allow-Headers: *`
- `Access-Control-Allow-Credentials: true`

For additional support or questions, refer to the API documentation at `http://stardust.myfirstcare.com:5054/docs` or contact the development team. 