# Device Mapping API - Comprehensive Guide

## Overview

The Device Mapping API provides comprehensive CRUD operations for assigning AVA4 boxes, Kati watches, and medical devices to patients. This system manages the relationship between patients and their monitoring devices.

## API Base URL
```
http://localhost:5055/admin/device-mapping
```

## Authentication

All endpoints require JWT authentication. Include the bearer token in the Authorization header:
```
Authorization: Bearer <jwt_token>
```

## Device Types Supported

### AVA4 Ecosystem
- **AVA4 Boxes**: Main gateway devices for home monitoring
- **Kati Watches**: Wearable devices for continuous monitoring

### Medical Devices
- `mac_gw`: AVA4 Gateway
- `mac_dusun_bps`: Blood Pressure Monitor
- `mac_oxymeter`: Oximeter
- `mac_mgss_oxymeter`: MGSS Oximeter
- `mac_weight`: Weight Scale
- `mac_gluc`: Glucose Meter
- `mac_body_temp`: Body Temperature Sensor
- `mac_chol`: Cholesterol Meter
- `mac_ua`: Uric Acid Meter
- `mac_salt_meter`: Salt Meter
- `mac_watch`: Smart Watch

## Core Endpoints

### 1. Get All Device Mappings
```http
GET /admin/device-mapping/
```

**Query Parameters:**
- `patient_id` (optional): Filter by specific patient
- `device_type` (optional): Filter by device type
- `limit` (default: 100): Number of records to return
- `skip` (default: 0): Number of records to skip

**Response:**
```json
{
  "mappings": [
    {
      "patient_id": "string",
      "patient_name": "string",
      "ava4_boxes": [...],
      "kati_watches": [...],
      "medical_devices": [...],
      "created_at": "datetime",
      "updated_at": "datetime"
    }
  ],
  "total": 0,
  "limit": 100,
  "skip": 0,
  "device_types": {...}
}
```

### 2. Get Patient Device Mapping
```http
GET /admin/device-mapping/{patient_id}
```

**Response:**
```json
{
  "patient_id": "string",
  "patient_name": "string",
  "patient_details": {...},
  "ava4_boxes": [...],
  "kati_watches": [...],
  "medical_devices": [...],
  "device_types": {...}
}
```

### 3. Get Device Types
```http
GET /admin/device-mapping/device-types
```

**Response:**
```json
{
  "device_types": {
    "mac_gw": "AVA4 Gateway",
    "mac_dusun_bps": "Blood Pressure Monitor",
    ...
  },
  "description": "Available medical device types for assignment"
}
```

## AVA4 Box Management

### 1. Get Available AVA4 Boxes
```http
GET /admin/device-mapping/available/ava4-boxes
```

**Query Parameters:**
- `limit` (default: 100): Number of boxes to return
- `skip` (default: 0): Number of boxes to skip

**Response:**
```json
{
  "available_boxes": [
    {
      "id": "string",
      "box_name": "string",
      "mac_address": "string",
      "model": "string",
      "version": "string",
      "status": 0
    }
  ],
  "total": 0,
  "limit": 100,
  "skip": 0
}
```

### 2. Assign AVA4 Box to Patient
```http
POST /admin/device-mapping/ava4-box
```

**Request Body:**
```json
{
  "patient_id": "string",
  "box_id": "string",
  "location": "string (optional)",
  "notes": "string (optional)"
}
```

**Response:**
```json
{
  "message": "AVA4 box assigned successfully",
  "patient_id": "string",
  "box_id": "string",
  "mac_address": "string"
}
```

### 3. Unassign AVA4 Box
```http
DELETE /admin/device-mapping/ava4-box/{box_id}
```

**Response:**
```json
{
  "message": "AVA4 box unassigned successfully",
  "box_id": "string",
  "patient_id": "string"
}
```

## Kati Watch Management

### 1. Get Available Kati Watches
```http
GET /admin/device-mapping/available/kati-watches
```

**Query Parameters:**
- `limit` (default: 100): Number of watches to return
- `skip` (default: 0): Number of watches to skip

**Response:**
```json
{
  "available_watches": [
    {
      "id": "string",
      "imei": "string",
      "model": "string",
      "status": "string",
      "battery": 0
    }
  ],
  "total": 0,
  "limit": 100,
  "skip": 0
}
```

### 2. Assign Kati Watch to Patient
```http
POST /admin/device-mapping/kati-watch
```

**Request Body:**
```json
{
  "patient_id": "string",
  "watch_id": "string",
  "notes": "string (optional)"
}
```

**Response:**
```json
{
  "message": "Kati watch assigned successfully",
  "patient_id": "string",
  "watch_id": "string",
  "imei": "string"
}
```

### 3. Unassign Kati Watch
```http
DELETE /admin/device-mapping/kati-watch/{watch_id}
```

**Response:**
```json
{
  "message": "Kati watch unassigned successfully",
  "watch_id": "string",
  "patient_id": "string"
}
```

## Medical Device Management

### 1. Assign Medical Device to Patient
```http
POST /admin/device-mapping/medical-device
```

**Request Body:**
```json
{
  "patient_id": "string",
  "device_type": "string",
  "mac_address": "string",
  "device_name": "string (optional)",
  "notes": "string (optional)"
}
```

**Example - Blood Pressure Monitor:**
```json
{
  "patient_id": "661f2b5d818cc24bd96a8722",
  "device_type": "mac_dusun_bps",
  "mac_address": "AA:BB:CC:DD:EE:FF",
  "device_name": "Dusun Blood Pressure Monitor",
  "notes": "Primary BP monitoring device"
}
```

**Response:**
```json
{
  "message": "Medical device assigned successfully",
  "patient_id": "string",
  "device_id": "string",
  "device_type": "string",
  "device_name": "string",
  "mac_address": "string"
}
```

### 2. Update Medical Device
```http
PUT /admin/device-mapping/medical-device/{device_id}
```

**Request Body:**
```json
{
  "device_type": "string (optional)",
  "mac_address": "string (optional)",
  "device_name": "string (optional)",
  "notes": "string (optional)"
}
```

**Response:**
```json
{
  "message": "Medical device updated successfully",
  "device_id": "string",
  "device_type": "string",
  "mac_address": "string"
}
```

### 3. Remove Medical Device
```http
DELETE /admin/device-mapping/medical-device/{device_id}?device_type={device_type}
```

**Query Parameters:**
- `device_type`: The specific device type to remove

**Response:**
```json
{
  "message": "Medical device removed successfully",
  "device_id": "string",
  "device_type": "string",
  "device_name": "string"
}
```

## Testing Workflow

### 1. Setup and Authentication
1. Start the API server: `docker-compose up -d`
2. Import the Postman collection: `Device_Mapping_API.postman_collection.json`
3. Import the environment: `Device_Mapping_API.postman_environment.json`
4. Run the "Login" request to get JWT token

### 2. Basic Testing Flow
1. **Get Device Types** - Understand available device categories
2. **Get Available Devices** - Check what devices are available for assignment
3. **Get Patient Mapping** - Check current device assignments for a patient
4. **Assign Devices** - Test device assignment to patients
5. **Update Assignments** - Test device updates
6. **Remove Assignments** - Test device removal

### 3. Complete Patient Setup Example
```bash
# 1. Get available AVA4 box
GET /admin/device-mapping/available/ava4-boxes

# 2. Assign AVA4 box to patient
POST /admin/device-mapping/ava4-box
{
  "patient_id": "661f2b5d818cc24bd96a8722",
  "box_id": "663cb21bf4969eea358a1c46",
  "location": "Living Room",
  "notes": "Primary monitoring location"
}

# 3. Assign blood pressure monitor
POST /admin/device-mapping/medical-device
{
  "patient_id": "661f2b5d818cc24bd96a8722",
  "device_type": "mac_dusun_bps",
  "mac_address": "AA:BB:CC:DD:EE:FF"
}

# 4. Assign glucose meter
POST /admin/device-mapping/medical-device
{
  "patient_id": "661f2b5d818cc24bd96a8722",
  "device_type": "mac_gluc",
  "mac_address": "11:22:33:44:55:66"
}

# 5. Verify complete setup
GET /admin/device-mapping/661f2b5d818cc24bd96a8722
```

## Error Handling

### Common Error Responses

**400 Bad Request:**
```json
{
  "detail": "Invalid device type. Must be one of: [mac_gw, mac_dusun_bps, ...]"
}
```

**404 Not Found:**
```json
{
  "detail": "Patient not found"
}
```

**409 Conflict:**
```json
{
  "detail": "AVA4 box is already assigned to another patient"
}
```

**500 Internal Server Error:**
```json
{
  "detail": "Failed to assign medical device: Database connection error"
}
```

## Data Validation

### Device Type Validation
- Must be one of the predefined device types
- MAC addresses must be unique per device type
- Patient must exist before device assignment

### Assignment Rules
- AVA4 boxes can only be assigned to one patient at a time
- Kati watches can only be assigned to one patient at a time
- Medical devices are grouped by patient in the `amy_devices` collection
- Multiple medical devices of different types can be assigned to the same patient

## Audit Logging

All device mapping operations are automatically logged with:
- User ID performing the action
- Action type (assign_ava4_box, assign_medical_device, etc.)
- Resource type: "device_mapping"
- Detailed operation information

View audit logs:
```http
GET /admin/audit-log?resource_type=device_mapping
```

## Integration with Other Systems

### Patient Management
- Device assignments automatically update patient records
- Patient's `ava_mac_address` and `watch_mac_address` fields are maintained

### Device Status Monitoring
- Real-time device status can be monitored through device-specific endpoints
- Device health and connectivity status are tracked

### FHIR Compliance
- All device assignments create appropriate FHIR Device resources
- Patient-device relationships are maintained in FHIR format

## Best Practices

### 1. Device Assignment Workflow
1. Always check device availability before assignment
2. Verify patient exists and is active
3. Use meaningful location and notes for AVA4 boxes
4. Test device connectivity after assignment

### 2. Error Handling
- Implement retry logic for temporary failures
- Check device availability before attempting assignment
- Validate MAC address formats before submission

### 3. Performance Optimization
- Use pagination for large device lists
- Filter by patient_id when checking specific patient mappings
- Cache device type information

### 4. Security Considerations
- Always validate JWT tokens
- Implement rate limiting for device assignment operations
- Log all device mapping changes for audit purposes

## Troubleshooting

### Common Issues

**Device Already Assigned:**
- Check current device assignments before attempting new assignment
- Use unassign endpoints to remove existing assignments

**Patient Not Found:**
- Verify patient ID exists in the system
- Check patient is not soft-deleted (`is_deleted: false`)

**Invalid Device Type:**
- Use `/device-types` endpoint to get valid device types
- Ensure device type matches exactly (case-sensitive)

**MAC Address Conflicts:**
- Ensure MAC addresses are unique within device type
- Check existing assignments before adding new devices

### Debugging Steps
1. Check API logs for detailed error messages
2. Verify MongoDB connectivity and data integrity
3. Test with known good patient and device IDs
4. Use Postman collection tests to validate responses

## Sample Test Data

### Test Patient ID
```
661f2b5d818cc24bd96a8722
```

### Sample MAC Addresses for Testing
```
Blood Pressure: AA:BB:CC:DD:EE:FF
Glucose Meter: 11:22:33:44:55:66
Oximeter: 77:88:99:AA:BB:CC
Weight Scale: DD:EE:FF:00:11:22
Body Temperature: 33:44:55:66:77:88
```

This comprehensive guide covers all aspects of the Device Mapping API, from basic operations to advanced integration scenarios. 