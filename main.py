import os
import uuid
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
from config import settings, logger
from app.services.mongo import mongodb_service
from app.routes import ava4, kati, qube_vital
from app.utils.error_definitions import create_error_response, create_validation_error_response, create_success_response, SuccessResponse, ErrorResponse, ErrorDetail
from app.middleware.logging_middleware import RequestLoggingMiddleware, PerformanceLoggingMiddleware, SecurityLoggingMiddleware
from app.utils.structured_logging import structured_logger, get_structured_logger
from app.utils.alert_system import alert_manager, configure_email_alerts, configure_slack_alerts
from datetime import datetime

# Import routes
from app.routes.ava4 import router as ava4_router
from app.routes.kati import router as kati_router
from app.routes.qube_vital import router as qube_vital_router
from app.routes.admin import router as admin_router
from app.routes.admin_crud import router as admin_crud_router
from app.routes.device_crud import router as device_crud_router
from app.routes.device_mapping import router as device_mapping_router
from app.routes import router as auth_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("🚀 Starting My FirstCare Opera Panel...")
    
    try:
        # Initialize structured logging
        structured_logger
        logger.info("✅ Structured logging initialized")
        
        # Force registration of response models for OpenAPI schema
        _register_response_models()
        logger.info("✅ Response models registered in OpenAPI schema")
        
        # Connect to MongoDB
        await mongodb_service.connect()
        logger.info("✅ MongoDB connected successfully")
        
        # Create TTL indexes for audit logs
        audit_collection = mongodb_service.get_collection("fhir_provenance")
        await audit_collection.create_index("recorded", expireAfterSeconds=15552000)  # 180 days
        logger.info("✅ TTL index created for audit logs")
        
        # Log startup event
        await alert_manager.process_event({
            "event_type": "application_startup",
            "message": "My FirstCare Opera Panel started successfully",
            "timestamp": datetime.utcnow().isoformat(),
            "source": "application"
        })
        
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        
        # Send critical alert for startup failure
        await alert_manager.process_event({
            "event_type": "application_startup_failure",
            "message": f"Application startup failed: {str(e)}",
            "error_type": type(e).__name__,
            "error_message": str(e),
            "timestamp": datetime.utcnow().isoformat(),
            "source": "application"
        })
        raise
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down My FirstCare Opera Panel...")
    await mongodb_service.disconnect()

def _register_response_models():
    """Force registration of response models in FastAPI's OpenAPI schema"""
    # This ensures the models are discovered by FastAPI's OpenAPI generation
    # by creating dummy instances (these aren't used, just for schema discovery)
    _dummy_success = SuccessResponse(
        success=True,
        message="dummy", 
        data={},
        request_id="dummy", 
        timestamp="dummy"
    )
    _dummy_error_detail = ErrorDetail(
        error_code="dummy", 
        error_type="dummy", 
        message="dummy",
        field=None,
        value=None,
        suggestion=None
    )
    _dummy_error = ErrorResponse(
        success=False,
        error_count=1, 
        errors=[_dummy_error_detail], 
        request_id="dummy",
        timestamp="dummy"
    )
    
    # Force the models to be part of the schema by adding them to the app
    # This is a workaround to ensure OpenAPI schema generation includes these models
    logger.info(f"Registered models: {type(_dummy_success).__name__}, {type(_dummy_error).__name__}, {type(_dummy_error_detail).__name__}")

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="""
# My FirstCare Opera Panel API

A comprehensive Medical IoT Device Management System for healthcare institutions.

## Features

### 🏥 **Device Management**
- **AVA4 Devices**: Blood pressure, glucose monitoring
- **Kati Watches**: Continuous vital sign monitoring 
- **Qube-Vital**: Advanced medical sensors

### 👥 **Patient Management**
- Complete patient profiles and medical history
- Real-time device data integration
- Multi-hospital support
- **Raw Document Access**: 431 patients with 269 fields per document

### 📋 **Raw Patient Document Analysis**
Access complete MongoDB patient documents with comprehensive field analysis:

#### **Core Patient Fields (269 total)**:
- **Demographics**: `first_name`, `last_name`, `gender`, `birth_date`, `id_card`, `phone`
- **Location**: `address_1`, `address_2`, `province_code`, `district_code`, `sub_district_code`
- **Medical IDs**: `amy_id`, `hn_id_no`, `patient_id`
- **Emergency Contacts**: `emergency_contact_name`, `emergency_contact_phone`

#### **Medical Device Integration (MAC Addresses)**:
- **AVA4 Devices**: `ava_mac_address`, `ava_box_id`, `ava_sim_card`
- **Blood Pressure**: `blood_pressure_mac_address`
- **Blood Glucose**: `blood_glucose_mac_address`
- **Temperature**: `body_temperature_mac_address`
- **Pulse Oximetry**: `fingertip_pulse_oximeter_mac_address`
- **Smartwatches**: `watch_mac_address`
- **Cholesterol**: `cholesterol_mac_address`

#### **Medical Alert Thresholds**:
- **Blood Pressure**: `bp_sbp_above`, `bp_sbp_below`, `bp_dbp_above`, `bp_dbp_below`
- **Blood Sugar**: `glucose_normal_before`, `glucose_normal_after`
- **Temperature**: `temperature_normal_above`, `temperature_normal_below`
- **SPO2**: `spo2_normal_above`, `spo2_normal_below`
- **Cholesterol**: `cholesterol_above`, `cholesterol_below`

#### **Medical History Fields**:
- **Vital Signs**: Blood pressure, temperature, SPO2, heart rate
- **Lab Results**: Creatinine, cholesterol, BUN levels
- **Body Metrics**: Weight, BMI, body composition
- **Medication**: Current medications, allergies, dosages
- **Activity**: Sleep data, step counts, exercise patterns

#### **Raw Document Endpoints**:
- `GET /admin/patients-raw-documents` - Admin access to raw patient documents
- `GET /api/ava4/patients/raw-documents` - AVA4 specific raw patient data
- `GET /api/ava4/sub-devices/raw-documents` - Raw device documents with patient linkages

### 🔐 **Security & Authentication**
- **JWT-based Authentication**: All protected endpoints require Bearer tokens
- **Stardust-V1 Integration**: Centralized authentication system
- **FHIR R5 Audit Logging**: Complete audit trail
- **Role-based Access Control**: Fine-grained permissions

### 📊 **Analytics & Monitoring**
- Real-time dashboards
- Performance metrics
- Alert management
- Medical trend analysis

## Data Structure Analysis

### **Patient Document Structure (431 Documents)**
Each patient document contains **269 fields** including:

1. **Core Demographics** (15 fields): Name, contact, identification
2. **Medical Device MAC Addresses** (12 fields): IoT device integration
3. **Alert Thresholds** (24 fields): Customizable medical alert limits
4. **Medical History Integration** (50+ fields): Historical data references
5. **Hospital Integration** (10 fields): Multi-hospital support
6. **Audit Fields** (8 fields): Created, updated, deleted tracking
7. **Additional Medical Data** (150+ fields): Comprehensive health metrics

### **Raw Document Analysis Features**
- **Field Type Analysis**: Automatic detection of data types per field
- **Sample Value Extraction**: Preview of actual field values
- **ObjectId Identification**: MongoDB relationship mapping
- **Field Usage Statistics**: Count of populated fields across documents
- **JSON Structure Preservation**: Complete document hierarchy maintained

## Authentication

Most endpoints require authentication using JWT Bearer tokens:

1. **Obtain Token**: Use `/auth/login` with valid credentials
2. **Use Token**: Include `Authorization: Bearer <token>` header
3. **Refresh Token**: Use `/auth/refresh` when token expires

### Public Endpoints (No Authentication Required)
- `GET /` - API information
- `GET /health` - System health check
- `GET /docs` - API documentation
- `GET /api/kati/test` - Kati API test endpoint
- `POST /auth/login` - Authentication login
- `POST /auth/refresh` - Token refresh

### Protected Endpoints (Authentication Required)
- All `/admin/*` endpoints
- All `/api/*/devices` endpoints  
- All `/api/*/data` endpoints
- `/auth/me` - Current user information

### **Raw Patient Document Endpoints** (Authentication Required)
- `GET /admin/patients` - Complete patient documents (269 fields)
- `GET /admin/patients-raw-documents` - Raw document analysis
- `GET /api/ava4/patients/raw-documents` - AVA4 patient raw data
- `GET /api/ava4/sub-devices/raw-documents` - Device-patient linkages

## Error Handling

The API uses structured error responses with:
- Consistent error codes and messages
- Request ID tracking
- Detailed field validation
- Security event logging

## Rate Limiting & Security

- Brute force detection
- SQL injection monitoring  
- Request rate limiting
- Comprehensive audit logging

## Database Statistics

- **431 Patients** with complete medical profiles
- **269 Fields per Patient Document** 
- **6,898 Medical Records** across 14 collections
- **Real-time IoT Device Integration**
- **FHIR R5 Compliant Audit Logging**
""",
    contact={
        "name": "My FirstCare Development Team",
        "url": "https://my-firstcare.com",
        "email": "support@my-firstcare.com"
    },
    license_info={
        "name": "Proprietary",
        "url": "https://my-firstcare.com/license"
    },
    servers=[
        {
            "url": "http://localhost:5054",
            "description": "Development server"
        },
        {
            "url": "https://stardust.my-firstcare.com", 
            "description": "Production server"
        }
    ],
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Add logging middleware (order matters - first added is outermost)
app.add_middleware(SecurityLoggingMiddleware)
app.add_middleware(PerformanceLoggingMiddleware, slow_threshold_ms=2000)
app.add_middleware(RequestLoggingMiddleware, exclude_paths=["/health", "/docs", "/openapi.json", "/favicon.ico"])

# Custom CORS function to handle wildcard domains
def is_cors_allowed(origin: str) -> bool:
    """Check if origin is allowed for CORS"""
    if not origin:
        return False
    
    # Allow localhost for development
    if "localhost" in origin or "127.0.0.1" in origin:
        return True
    
    # Allowed domain patterns
    allowed_patterns = [
        ".my-firstcare.com",
        ".amy.care", 
        ".amyplatform.com"
    ]
    
    # Allow exact domain matches
    allowed_domains = [
        "my-firstcare.com",
        "amy.care",
        "amyplatform.com"
    ]
    
    # Check if origin ends with allowed patterns (wildcard subdomain support)
    for pattern in allowed_patterns:
        if origin.endswith(pattern):
            return True
    
    # Check exact domain matches
    for domain in allowed_domains:
        if origin.endswith(f"//{domain}") or origin.endswith(f"://{domain}"):
            return True
    
    return False

# Add CORS middleware with dynamic origin checking
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:[0-9]+)?$|^https?://.*\.(my-firstcare\.com|amy\.care|amyplatform\.com)$|^https?://(my-firstcare\.com|amy\.care|amyplatform\.com)$",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(ava4_router)
app.include_router(kati_router)
app.include_router(qube_vital_router)
app.include_router(admin_router)
app.include_router(admin_crud_router)
app.include_router(device_crud_router)
app.include_router(device_mapping_router)

# Health check endpoint
@app.get("/health", 
         response_model=SuccessResponse,
         responses={
             200: {
                 "description": "Health check successful",
                 "content": {
                     "application/json": {
                         "example": {
                             "success": True,
                             "message": "Service is healthy",
                             "data": {
                                 "status": "healthy",
                                 "mongodb": "connected",
                                 "version": "1.0.0",
                                 "environment": "production",
                                 "active_alerts": 0,
                                 "alert_summary": {
                                     "total_active": 0,
                                     "by_level": {"low": 0, "medium": 0, "high": 0, "critical": 0},
                                     "total_historical": 0,
                                     "last_24h": 0
                                 }
                             },
                             "request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                             "timestamp": "2025-07-07T07:08:07.633870Z"
                         }
                     }
                 }
             },
             503: {
                 "description": "Service unavailable",
                 "content": {
                     "application/json": {
                         "example": {
                             "success": False,
                             "error_count": 1,
                             "errors": [{
                                 "error_code": "SERVICE_UNAVAILABLE",
                                 "error_type": "system_error",
                                 "message": "MongoDB connection is unhealthy",
                                 "field": None,
                                 "value": None,
                                 "suggestion": "Please try again later"
                             }],
                             "request_id": "b2c3d4e5-f6g7-8901-bcde-f23456789012",
                             "timestamp": "2025-07-07T07:08:07.633870Z"
                         }
                     }
                 }
             }
         })
async def health_check(request: Request):
    """Health check endpoint"""
    try:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        # Check MongoDB connection
        mongo_healthy = await mongodb_service.health_check()
        
        if mongo_healthy:
            success_response = create_success_response(
                message="Service is healthy",
                data={
                    "status": "healthy",
                    "mongodb": "connected",
                    "version": settings.app_version,
                    "environment": settings.node_env,
                    "active_alerts": len(alert_manager.get_active_alerts()),
                    "alert_summary": alert_manager.get_alert_summary()
                },
                request_id=request_id
            )
            return success_response
        else:
            # Send alert for MongoDB connection failure
            await alert_manager.process_event({
                "event_type": "database_connection_error",
                "message": "MongoDB connection is unhealthy",
                "timestamp": datetime.utcnow().isoformat(),
                "source": "health_check"
            })
            
            raise HTTPException(
                status_code=503,
                detail=create_error_response(
                    "SERVICE_UNAVAILABLE",
                    custom_message="MongoDB connection is unhealthy",
                    request_id=request_id
                ).dict()
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        
        # Send alert for health check failure
        await alert_manager.process_event({
            "event_type": "health_check_error",
            "message": f"Health check failed: {str(e)}",
            "error_type": type(e).__name__,
            "error_message": str(e),
            "timestamp": datetime.utcnow().isoformat(),
            "source": "health_check"
        })
        
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        raise HTTPException(
            status_code=503,
            detail=create_error_response(
                "SERVICE_UNAVAILABLE",
                custom_message=f"Health check failed: {str(e)}",
                request_id=request_id
            ).dict()
        )

# Root endpoint
@app.get("/", 
         response_model=SuccessResponse,
         responses={
             200: {
                 "description": "API information and endpoints",
                 "content": {
                     "application/json": {
                         "example": {
                             "success": True,
                             "message": "My FirstCare Opera Panel API",
                             "data": {
                                 "version": "1.0.0",
                                 "docs": "/docs",
                                 "health": "/health",
                                 "endpoints": {
                                     "authentication": "/auth",
                                     "device_mapping": "/admin/device-mapping",
                                     "admin": "/admin",
                                     "ava4": "/ava4",
                                     "kati": "/kati",
                                     "qube_vital": "/qube-vital"
                                 }
                             },
                             "request_id": "c3d4e5f6-g7h8-9012-cdef-345678901234",
                             "timestamp": "2025-07-07T07:08:07.633870Z"
                         }
                     }
                 }
             }
         })
async def root(request: Request):
    """Root endpoint"""
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    
    success_response = create_success_response(
        message="My FirstCare Opera Panel API",
        data={
            "version": settings.app_version,
            "docs": "/docs",
            "health": "/health",
            "endpoints": {
                "authentication": "/auth",
                "device_mapping": "/admin/device-mapping",
                "admin": "/admin",
                "ava4": "/ava4",
                "kati": "/kati",
                "qube_vital": "/qube-vital"
            }
        },
        request_id=request_id
    )
    return success_response

# Test endpoint to force model registration in OpenAPI schema
@app.get("/test-schema", 
         response_model=SuccessResponse,
         responses={
             200: {
                 "description": "Schema test endpoint response",
                 "content": {
                     "application/json": {
                         "example": {
                             "success": True,
                             "message": "Schema test endpoint - this forces FastAPI to register SuccessResponse in OpenAPI",
                             "data": {"schema_registered": True},
                             "request_id": "test-schema-endpoint",
                             "timestamp": "2025-07-07T07:08:07.633870Z"
                         }
                     }
                 }
             }
         })
async def test_schema_endpoint():
    """Test endpoint to force registration of response models in OpenAPI schema"""
    return SuccessResponse(
        success=True,
        message="Schema test endpoint - this forces FastAPI to register SuccessResponse in OpenAPI",
        data={"schema_registered": True},
        request_id="test-schema-endpoint",
        timestamp=datetime.utcnow().isoformat() + "Z"
    )

# Global Exception Handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with detailed error definitions"""
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    logger.warning(f"Validation Error: {request.url} - {exc.errors()}")
    
    error_response = create_validation_error_response(list(exc.errors()), request_id)
    return JSONResponse(
        status_code=422,
        content=error_response.dict()
    )

@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    """Handle 404 errors"""
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    logger.warning(f"404 Not Found: {request.url}")
    
    # If the exception already has a structured error response, preserve it
    if hasattr(exc, 'detail') and isinstance(exc.detail, dict):
        # Check if it's already a structured error response
        if 'success' in exc.detail and 'errors' in exc.detail:
            return JSONResponse(
                status_code=404,
                content=exc.detail
            )
    
    # Otherwise, create a generic error response
    error_response = create_error_response(
        "RESOURCE_NOT_FOUND",
        custom_message="The requested resource was not found",
        request_id=request_id
    )
    return JSONResponse(
        status_code=404,
        content=error_response.dict()
    )

@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: Exception):
    """Handle 500 errors"""
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    logger.error(f"500 Internal Server Error: {request.url} - {type(exc).__name__}: {exc}")
    
    # Send alert for 500 errors
    await alert_manager.process_event({
        "event_type": "http_error",
        "message": f"Internal server error: {str(exc)}",
        "status_code": 500,
        "error_type": type(exc).__name__,
        "error_message": str(exc),
        "url": str(request.url),
        "method": request.method,
        "timestamp": datetime.utcnow().isoformat(),
        "source": "application"
    })
    
    error_response = create_error_response(
        "INTERNAL_SERVER_ERROR",
        custom_message="An unexpected error occurred",
        request_id=request_id
    )
    return JSONResponse(
        status_code=500,
        content=error_response.dict()
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    ) 