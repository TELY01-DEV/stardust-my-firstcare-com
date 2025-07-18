# Enhanced Error Handling System

## Overview

The device mapping API now includes a comprehensive error handling system that provides detailed, structured error responses to external systems. This system categorizes errors, provides specific error codes, and includes helpful suggestions for resolution.

## Error Response Structure

All error responses follow a standardized format:

```json
{
  "success": false,
  "error_count": 1,
  "errors": [
    {
      "error_code": "PATIENT_NOT_FOUND",
      "error_type": "resource_error",
      "message": "Patient not found",
      "field": "patient_id",
      "value": "507f1f77bcf86cd799439011",
      "suggestion": "Please verify the patient ID exists in the system"
    }
  ],
  "request_id": "test-123",
  "timestamp": "2025-07-06T04:15:30.123Z"
}
```

## Error Categories

### 1. Validation Errors (1000-1999)

Errors related to request validation and data format issues.

| Error Code | Description | HTTP Status |
|------------|-------------|-------------|
| `VALIDATION_MISSING_FIELD` | Required field is missing | 422 |
| `VALIDATION_INVALID_TYPE` | Field has invalid data type | 422 |
| `VALIDATION_INVALID_FORMAT` | Field has invalid format | 422 |
| `VALIDATION_INVALID_JSON` | Request body contains invalid JSON | 422 |
| `VALIDATION_FIELD_TOO_SHORT` | Field value is too short | 422 |
| `VALIDATION_FIELD_TOO_LONG` | Field value is too long | 422 |

#### Examples:

**Missing Required Field:**
```json
{
  "success": false,
  "error_count": 2,
  "errors": [
    {
      "error_code": "VALIDATION_MISSING_FIELD",
      "error_type": "validation_error",
      "message": "Field required",
      "field": "patient_id",
      "value": null,
      "suggestion": "Please provide the required field in your request"
    },
    {
      "error_code": "VALIDATION_MISSING_FIELD", 
      "error_type": "validation_error",
      "message": "Field required",
      "field": "box_id",
      "value": null,
      "suggestion": "Please provide the required field in your request"
    }
  ],
  "request_id": "req-001",
  "timestamp": "2025-07-06T04:15:30.123Z"
}
```

**Invalid Data Type:**
```json
{
  "success": false,
  "error_count": 1,
  "errors": [
    {
      "error_code": "VALIDATION_INVALID_TYPE",
      "error_type": "validation_error",
      "message": "Input should be a valid string",
      "field": "patient_id",
      "value": 123,
      "suggestion": "Please check the field type requirements in the API documentation"
    }
  ],
  "request_id": "req-002",
  "timestamp": "2025-07-06T04:16:30.123Z"
}
```

### 2. Resource Errors (2000-2999)

Errors when requested resources are not found in the system.

| Error Code | Description | HTTP Status |
|------------|-------------|-------------|
| `RESOURCE_NOT_FOUND` | Generic resource not found | 404 |
| `PATIENT_NOT_FOUND` | Patient not found | 404 |
| `DEVICE_NOT_FOUND` | Device not found | 404 |
| `AVA4_BOX_NOT_FOUND` | AVA4 box not found | 404 |
| `KATI_WATCH_NOT_FOUND` | Kati watch not found | 404 |
| `MEDICAL_DEVICE_NOT_FOUND` | Medical device record not found | 404 |

#### Example:

```json
{
  "success": false,
  "error_count": 1,
  "errors": [
    {
      "error_code": "PATIENT_NOT_FOUND",
      "error_type": "resource_error",
      "message": "Patient not found",
      "field": "patient_id",
      "value": "507f1f77bcf86cd799439011",
      "suggestion": "Please verify the patient ID exists in the system"
    }
  ],
  "request_id": "req-003",
  "timestamp": "2025-07-06T04:17:30.123Z"
}
```

### 3. Business Logic Errors (3000-3999)

Errors related to business rules and constraints.

| Error Code | Description | HTTP Status |
|------------|-------------|-------------|
| `DEVICE_ALREADY_ASSIGNED` | Device is already assigned to another patient | 409 |
| `DEVICE_NOT_ASSIGNED` | Device is not assigned to any patient | 400 |
| `INVALID_DEVICE_TYPE` | Invalid device type specified | 400 |
| `INVALID_OBJECT_ID` | Invalid ObjectId format | 400 |
| `INVALID_MAC_ADDRESS` | Invalid MAC address format | 400 |
| `DUPLICATE_ASSIGNMENT` | Cannot assign same device type multiple times | 409 |

#### Examples:

**Device Already Assigned:**
```json
{
  "success": false,
  "error_count": 1,
  "errors": [
    {
      "error_code": "DEVICE_ALREADY_ASSIGNED",
      "error_type": "business_logic_error",
      "message": "AVA4 box is already assigned to patient 661f2b5d818cc24bd96a8722",
      "field": "box_id",
      "value": "65ee589eeb4259c2eab88527",
      "suggestion": "Please unassign the device first or choose a different device"
    }
  ],
  "request_id": "req-004",
  "timestamp": "2025-07-06T04:18:30.123Z"
}
```

**Invalid Device Type:**
```json
{
  "success": false,
  "error_count": 1,
  "errors": [
    {
      "error_code": "INVALID_DEVICE_TYPE",
      "error_type": "business_logic_error",
      "message": "Invalid device type 'invalid_type'. Supported types: mac_gw, mac_dusun_bps, mac_oxymeter, mac_mgss_oxymeter, mac_weight, mac_gluc, mac_body_temp, mac_chol, mac_ua, mac_salt_meter, mac_watch",
      "field": "device_type",
      "value": "invalid_type",
      "suggestion": "Please use one of the supported device types"
    }
  ],
  "request_id": "req-005",
  "timestamp": "2025-07-06T04:19:30.123Z"
}
```

### 4. Authentication Errors (4000-4999)

Errors related to authentication and authorization.

| Error Code | Description | HTTP Status |
|------------|-------------|-------------|
| `AUTHENTICATION_REQUIRED` | Authentication required | 401 |
| `INVALID_TOKEN` | Invalid or expired authentication token | 401 |
| `INSUFFICIENT_PERMISSIONS` | Insufficient permissions for operation | 403 |

#### Example:

```json
{
  "success": false,
  "error_count": 1,
  "errors": [
    {
      "error_code": "INVALID_TOKEN",
      "error_type": "authentication_error",
      "message": "Invalid or expired authentication token",
      "field": null,
      "value": null,
      "suggestion": "Please provide a valid authentication token or refresh your token"
    }
  ],
  "request_id": "req-006",
  "timestamp": "2025-07-06T04:20:30.123Z"
}
```

### 5. System Errors (5000-5999)

Errors related to system issues and internal server problems.

| Error Code | Description | HTTP Status |
|------------|-------------|-------------|
| `DATABASE_ERROR` | Database operation failed | 500 |
| `INTERNAL_SERVER_ERROR` | Internal server error occurred | 500 |
| `SERVICE_UNAVAILABLE` | Service temporarily unavailable | 503 |
| `TIMEOUT_ERROR` | Request timeout | 504 |

#### Example:

```json
{
  "success": false,
  "error_count": 1,
  "errors": [
    {
      "error_code": "DATABASE_ERROR",
      "error_type": "system_error",
      "message": "Failed to validate patient: Connection timeout",
      "field": null,
      "value": null,
      "suggestion": "Please try again later or contact support if the issue persists"
    }
  ],
  "request_id": "req-007",
  "timestamp": "2025-07-06T04:21:30.123Z"
}
```

## Enhanced Field Validation

The API now includes enhanced field validation with specific constraints:

### ObjectId Fields
- **Length**: Exactly 24 characters
- **Format**: Hexadecimal string
- **Examples**: `661f2b5d818cc24bd96a8722`, `65ee589eeb4259c2eab88527`

### MAC Address Fields
- **Length**: 1-17 characters
- **Format**: Standard MAC address format (XX:XX:XX:XX:XX:XX)
- **Examples**: `DC:DA:0C:5A:80:64`, `08:F9:E0:D1:FB:74`

### Text Fields
- **Device Name**: Maximum 100 characters
- **Notes**: Maximum 500 characters
- **Location**: Maximum 200 characters

## Request Tracking

### X-Request-ID Header

Include an `X-Request-ID` header in your requests for better tracking and debugging:

```bash
curl -X POST http://localhost:5054/admin/device-mapping/ava4-box \
  -H "Content-Type: application/json" \
  -H "X-Request-ID: unique-request-123" \
  -d '{"patient_id": "661f2b5d818cc24bd96a8722", "box_id": "65ee589eeb4259c2eab88527"}'
```

The request ID will be included in all error and success responses for easier correlation with logs.

## Success Response Format

Successful operations return a standardized success response:

```json
{
  "success": true,
  "message": "AVA4 box assigned successfully",
  "data": {
    "patient_id": "661f2b5d818cc24bd96a8722",
    "box_id": "65ee589eeb4259c2eab88527",
    "mac_address": "DC:DA:0C:5A:80:64"
  },
  "request_id": "unique-request-123",
  "timestamp": "2025-07-06T04:22:30.123Z"
}
```

## Error Handling Best Practices

### For External Systems

1. **Always check the `success` field** to determine if the request was successful
2. **Use the `error_code`** for programmatic error handling
3. **Display the `message`** to users for human-readable errors
4. **Show the `suggestion`** to help users resolve the issue
5. **Log the `request_id`** for debugging and support

### Example Error Handling Code

```javascript
// JavaScript example
async function assignAVA4Box(patientId, boxId) {
  const requestId = `req-${Date.now()}`;
  
  try {
    const response = await fetch('/admin/device-mapping/ava4-box', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Request-ID': requestId
      },
      body: JSON.stringify({
        patient_id: patientId,
        box_id: boxId
      })
    });
    
    const result = await response.json();
    
    if (result.success) {
      console.log('Success:', result.message);
      return result.data;
    } else {
      // Handle errors based on error codes
      result.errors.forEach(error => {
        switch (error.error_code) {
          case 'PATIENT_NOT_FOUND':
            showError('Patient not found. Please verify the patient ID.');
            break;
          case 'AVA4_BOX_NOT_FOUND':
            showError('AVA4 box not found. Please verify the box ID.');
            break;
          case 'DEVICE_ALREADY_ASSIGNED':
            showError('This AVA4 box is already assigned to another patient.');
            break;
          default:
            showError(error.message + ' ' + error.suggestion);
        }
      });
      throw new Error('Assignment failed');
    }
  } catch (error) {
    console.error('Request failed:', error);
    throw error;
  }
}
```

```python
# Python example
import requests

def assign_ava4_box(patient_id, box_id):
    request_id = f"req-{int(time.time())}"
    
    response = requests.post(
        'http://localhost:5054/admin/device-mapping/ava4-box',
        headers={
            'Content-Type': 'application/json',
            'X-Request-ID': request_id
        },
        json={
            'patient_id': patient_id,
            'box_id': box_id
        }
    )
    
    result = response.json()
    
    if result.get('success'):
        print(f"Success: {result['message']}")
        return result['data']
    else:
        # Handle errors based on error codes
        for error in result.get('errors', []):
            error_code = error['error_code']
            
            if error_code == 'PATIENT_NOT_FOUND':
                raise ValueError('Patient not found. Please verify the patient ID.')
            elif error_code == 'AVA4_BOX_NOT_FOUND':
                raise ValueError('AVA4 box not found. Please verify the box ID.')
            elif error_code == 'DEVICE_ALREADY_ASSIGNED':
                raise ValueError('This AVA4 box is already assigned to another patient.')
            else:
                raise ValueError(f"{error['message']} {error['suggestion']}")
```

## Common Error Scenarios

### 1. Invalid Request Format

**Problem**: Sending malformed JSON or missing required fields
**Solution**: Validate your JSON and ensure all required fields are included

### 2. Invalid ObjectId Format

**Problem**: Using IDs that are not valid MongoDB ObjectIds
**Solution**: Ensure IDs are exactly 24 characters and contain only hexadecimal characters

### 3. Resource Not Found

**Problem**: Referencing patients, devices, or other resources that don't exist
**Solution**: Verify the resource exists before attempting operations

### 4. Device Already Assigned

**Problem**: Trying to assign a device that's already assigned to another patient
**Solution**: Check device availability first or unassign from the current patient

### 5. Invalid Device Type

**Problem**: Using unsupported device types
**Solution**: Use only the supported device types listed in the API documentation

## Migration from Legacy Error Format

If you're migrating from the legacy error format, update your error handling code to:

1. Check for the new `success` field instead of just HTTP status codes
2. Use `error_code` for programmatic error handling instead of parsing error messages
3. Display the structured `message` and `suggestion` fields to users
4. Implement request ID tracking for better debugging

## Monitoring and Logging

### Request ID Correlation

Use the `X-Request-ID` header to correlate requests across your system and our API logs:

```bash
# Include request ID in all API calls
curl -H "X-Request-ID: your-system-req-123" ...
```

### Error Code Metrics

Track error codes to identify common issues:

- High `PATIENT_NOT_FOUND` rates may indicate data sync issues
- Frequent `DEVICE_ALREADY_ASSIGNED` errors may indicate workflow problems
- `VALIDATION_*` errors suggest client-side validation improvements needed

## Support and Troubleshooting

When contacting support, always include:

1. The `request_id` from the error response
2. The complete error response JSON
3. The original request payload (without sensitive data)
4. Timestamp of the request

This enhanced error handling system provides comprehensive, actionable error information to help external systems integrate more effectively with the device mapping API. 