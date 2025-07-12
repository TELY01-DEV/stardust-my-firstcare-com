from datetime import datetime
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field

# Error Code Constants for easy import
class ErrorCode:
    """Error code constants for easy access in other modules"""
    # Validation Errors (1000-1999)
    VALIDATION_MISSING_FIELD = "VALIDATION_MISSING_FIELD"
    VALIDATION_INVALID_TYPE = "VALIDATION_INVALID_TYPE"
    VALIDATION_INVALID_FORMAT = "VALIDATION_INVALID_FORMAT"
    VALIDATION_INVALID_JSON = "VALIDATION_INVALID_JSON"
    VALIDATION_FIELD_TOO_SHORT = "VALIDATION_FIELD_TOO_SHORT"
    VALIDATION_FIELD_TOO_LONG = "VALIDATION_FIELD_TOO_LONG"
    
    # Resource Errors (2000-2999)
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    ENDPOINT_NOT_FOUND = "ENDPOINT_NOT_FOUND"
    PATIENT_NOT_FOUND = "PATIENT_NOT_FOUND"
    DEVICE_NOT_FOUND = "DEVICE_NOT_FOUND"
    AVA4_BOX_NOT_FOUND = "AVA4_BOX_NOT_FOUND"
    KATI_WATCH_NOT_FOUND = "KATI_WATCH_NOT_FOUND"
    MEDICAL_DEVICE_NOT_FOUND = "MEDICAL_DEVICE_NOT_FOUND"
    
    # Business Logic Errors (3000-3999)
    DEVICE_ALREADY_ASSIGNED = "DEVICE_ALREADY_ASSIGNED"
    DEVICE_NOT_ASSIGNED = "DEVICE_NOT_ASSIGNED"
    INVALID_DEVICE_TYPE = "INVALID_DEVICE_TYPE"
    INVALID_OBJECT_ID = "INVALID_OBJECT_ID"
    INVALID_MAC_ADDRESS = "INVALID_MAC_ADDRESS"
    DUPLICATE_ASSIGNMENT = "DUPLICATE_ASSIGNMENT"
    
    # Authentication Errors (4000-4999)
    AUTHENTICATION_REQUIRED = "AUTHENTICATION_REQUIRED"
    INVALID_TOKEN = "INVALID_TOKEN"
    INSUFFICIENT_PERMISSIONS = "INSUFFICIENT_PERMISSIONS"
    
    # System Errors (5000-5999)
    DATABASE_ERROR = "DATABASE_ERROR"
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
    INTERNAL_ERROR = "INTERNAL_SERVER_ERROR"  # Alias for convenience
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    TIMEOUT_ERROR = "TIMEOUT_ERROR"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"

# Error Response Models
class ErrorDetail(BaseModel):
    error_code: str = Field(..., description="Unique error code")
    error_type: str = Field(..., description="Type of error")
    message: str = Field(..., description="Human-readable error message")
    field: Optional[str] = Field(None, description="Field that caused the error")
    value: Optional[Any] = Field(None, description="Value that caused the error")
    suggestion: Optional[str] = Field(None, description="Suggestion to fix the error")

class ErrorResponse(BaseModel):
    success: bool = Field(False, description="Request success status")
    error_count: int = Field(..., description="Number of errors")
    errors: List[ErrorDetail] = Field(..., description="List of error details")
    request_id: Optional[str] = Field(None, description="Request ID for tracking")
    timestamp: str = Field(..., description="Error timestamp")

# Comprehensive Error Code Definitions
ERROR_CODES = {
    # Validation Errors (1000-1999)
    "VALIDATION_MISSING_FIELD": {
        "type": "validation_error",
        "message": "Required field is missing",
        "suggestion": "Please provide the required field in your request"
    },
    "VALIDATION_INVALID_TYPE": {
        "type": "validation_error", 
        "message": "Field has invalid data type",
        "suggestion": "Please check the field type requirements in the API documentation"
    },
    "VALIDATION_INVALID_FORMAT": {
        "type": "validation_error",
        "message": "Field has invalid format",
        "suggestion": "Please check the field format requirements"
    },
    "VALIDATION_INVALID_JSON": {
        "type": "validation_error",
        "message": "Request body contains invalid JSON",
        "suggestion": "Please check your JSON syntax and ensure all strings are properly quoted"
    },
    "VALIDATION_FIELD_TOO_SHORT": {
        "type": "validation_error",
        "message": "Field value is too short",
        "suggestion": "Please provide a longer value that meets the minimum length requirement"
    },
    "VALIDATION_FIELD_TOO_LONG": {
        "type": "validation_error",
        "message": "Field value is too long",
        "suggestion": "Please provide a shorter value that meets the maximum length requirement"
    },
    
    # Resource Errors (2000-2999)
    "RESOURCE_NOT_FOUND": {
        "type": "resource_error",
        "message": "Requested resource was not found",
        "suggestion": "Please verify the resource ID exists in the system"
    },
    "ENDPOINT_NOT_FOUND": {
        "type": "routing_error",
        "message": "The requested endpoint does not exist",
        "suggestion": "Check the API documentation for valid endpoints"
    },
    "PATIENT_NOT_FOUND": {
        "type": "resource_error",
        "message": "Patient not found",
        "suggestion": "Please verify the patient ID exists in the system"
    },
    "DEVICE_NOT_FOUND": {
        "type": "resource_error",
        "message": "Device not found",
        "suggestion": "Please verify the device ID exists in the system"
    },
    "AVA4_BOX_NOT_FOUND": {
        "type": "resource_error",
        "message": "AVA4 box not found",
        "suggestion": "Please verify the AVA4 box ID exists in the system"
    },
    "KATI_WATCH_NOT_FOUND": {
        "type": "resource_error",
        "message": "Kati watch not found",
        "suggestion": "Please verify the Kati watch ID exists in the system"
    },
    "MEDICAL_DEVICE_NOT_FOUND": {
        "type": "resource_error",
        "message": "Medical device record not found",
        "suggestion": "Please verify the medical device ID exists in the system"
    },
    
    # Business Logic Errors (3000-3999)
    "DEVICE_ALREADY_ASSIGNED": {
        "type": "business_logic_error",
        "message": "Device is already assigned to another patient",
        "suggestion": "Please unassign the device first or choose a different device"
    },
    "DEVICE_NOT_ASSIGNED": {
        "type": "business_logic_error",
        "message": "Device is not assigned to any patient",
        "suggestion": "Please assign the device to a patient first"
    },
    "INVALID_DEVICE_TYPE": {
        "type": "business_logic_error",
        "message": "Invalid device type specified",
        "suggestion": "Please use one of the supported device types"
    },
    "INVALID_OBJECT_ID": {
        "type": "business_logic_error",
        "message": "Invalid ObjectId format",
        "suggestion": "Please provide a valid 24-character hexadecimal ObjectId"
    },
    "INVALID_MAC_ADDRESS": {
        "type": "business_logic_error",
        "message": "Invalid MAC address format",
        "suggestion": "Please provide a valid MAC address in format XX:XX:XX:XX:XX:XX"
    },
    "DUPLICATE_ASSIGNMENT": {
        "type": "business_logic_error",
        "message": "Cannot assign the same device type multiple times to one patient",
        "suggestion": "Please update the existing assignment or remove it first"
    },
    
    # Authentication Errors (4000-4999)
    "AUTHENTICATION_REQUIRED": {
        "type": "authentication_error",
        "message": "Authentication required",
        "suggestion": "Please provide valid authentication credentials"
    },
    "INVALID_TOKEN": {
        "type": "authentication_error",
        "message": "Invalid or expired authentication token",
        "suggestion": "Please provide a valid authentication token or refresh your token"
    },
    "INSUFFICIENT_PERMISSIONS": {
        "type": "authentication_error",
        "message": "Insufficient permissions for this operation",
        "suggestion": "Please contact an administrator to grant the required permissions"
    },
    
    # System Errors (5000-5999)
    "DATABASE_ERROR": {
        "type": "system_error",
        "message": "Database operation failed",
        "suggestion": "Please try again later or contact support if the issue persists"
    },
    "INTERNAL_SERVER_ERROR": {
        "type": "system_error",
        "message": "Internal server error occurred",
        "suggestion": "Please try again later or contact support if the issue persists"
    },
    "SERVICE_UNAVAILABLE": {
        "type": "system_error",
        "message": "Service temporarily unavailable",
        "suggestion": "Please try again later"
    },
    "TIMEOUT_ERROR": {
        "type": "system_error",
        "message": "Request timeout",
        "suggestion": "Please try again with a smaller request or contact support"
    },
    "RATE_LIMIT_EXCEEDED": {
        "type": "system_error",
        "message": "Rate limit exceeded",
        "suggestion": "Please wait before making more requests"
    }
}

def create_error_response(error_code: str, field: Optional[str] = None, value: Optional[Any] = None, 
                         custom_message: Optional[str] = None, request_id: Optional[str] = None) -> ErrorResponse:
    """Create standardized error response"""
    error_def = ERROR_CODES.get(error_code, ERROR_CODES["INTERNAL_SERVER_ERROR"])
    
    error_detail = ErrorDetail(
        error_code=error_code,
        error_type=error_def["type"],
        message=custom_message or error_def["message"],
        field=field,
        value=value,
        suggestion=error_def["suggestion"]
    )
    
    return ErrorResponse(
        success=False,
        error_count=1,
        errors=[error_detail],
        request_id=request_id,
        timestamp=datetime.utcnow().isoformat() + "Z"
    )

def create_validation_error_response(validation_errors: List[Dict[str, Any]], request_id: Optional[str] = None) -> ErrorResponse:
    """Create error response from FastAPI validation errors"""
    errors = []
    
    for error in validation_errors:
        error_type = error.get("type", "unknown")
        field = ".".join(str(loc) for loc in error.get("loc", []) if loc != "body")
        value = error.get("input")
        
        # Map FastAPI validation error types to our error codes
        if error_type == "missing":
            error_code = "VALIDATION_MISSING_FIELD"
        elif error_type in ["string_type", "int_type", "float_type", "bool_type"]:
            error_code = "VALIDATION_INVALID_TYPE"
        elif error_type == "json_invalid":
            error_code = "VALIDATION_INVALID_JSON"
            field = None
            value = None
        elif error_type in ["string_too_short", "too_short"]:
            error_code = "VALIDATION_FIELD_TOO_SHORT"
        elif error_type in ["string_too_long", "too_long"]:
            error_code = "VALIDATION_FIELD_TOO_LONG"
        else:
            error_code = "VALIDATION_INVALID_FORMAT"
        
        error_def = ERROR_CODES.get(error_code, ERROR_CODES["INTERNAL_SERVER_ERROR"])
        
        error_detail = ErrorDetail(
            error_code=error_code,
            error_type=error_def["type"],
            message=error.get("msg", error_def["message"]),
            field=field,
            value=value,
            suggestion=error_def["suggestion"]
        )
        errors.append(error_detail)
    
    return ErrorResponse(
        success=False,
        error_count=len(errors),
        errors=errors,
        request_id=request_id,
        timestamp=datetime.utcnow().isoformat() + "Z"
    )

def create_multiple_errors_response(error_details: List[ErrorDetail], request_id: Optional[str] = None) -> ErrorResponse:
    """Create error response with multiple error details"""
    return ErrorResponse(
        success=False,
        error_count=len(error_details),
        errors=error_details,
        request_id=request_id,
        timestamp=datetime.utcnow().isoformat() + "Z"
    )

# Success Response Model
class SuccessResponse(BaseModel):
    success: bool = Field(True, description="Request success status")
    message: str = Field(..., description="Success message")
    data: Optional[Dict[str, Any]] = Field(None, description="Response data")
    request_id: Optional[str] = Field(None, description="Request ID for tracking")
    timestamp: str = Field(..., description="Response timestamp")

def create_success_response(message: str, data: Optional[Dict[str, Any]] = None, 
                           request_id: Optional[str] = None) -> SuccessResponse:
    """Create standardized success response"""
    return SuccessResponse(
        success=True,
        message=message,
        data=data,
        request_id=request_id,
        timestamp=datetime.utcnow().isoformat() + "Z"
    ) 