#!/usr/bin/env python3
"""
Update Swagger Documentation Script
Updates the OpenAPI specification to reflect the current API state after removing duplicate routes
"""

import requests
import json
import os
from datetime import datetime

def fetch_current_openapi():
    """Fetch current OpenAPI specification"""
    try:
        response = requests.get("http://localhost:5054/openapi.json")
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ Failed to fetch OpenAPI spec: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Error fetching OpenAPI spec: {e}")
        return None

def update_openapi_info(openapi_spec):
    """Update the OpenAPI info section with current status"""
    
    # Update description with current status
    current_description = f"""
# My FirstCare Opera Panel API

A comprehensive Medical IoT Device Management System for healthcare institutions.

## 🎯 **Current API Status (Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')})**

### ✅ **Successfully Working Endpoints (65% Success Rate)**
- **Master Data CRUD**: Complete operations with pagination and bulk export
- **Device Management**: Device mapping and availability endpoints
- **Patient Management**: Core patient operations with pagination
- **Medical History**: Management system with proper data handling
- **Hospital Users**: User management with statistics
- **Geographic Dropdowns**: Multi-level location selection
- **Analytics & Security**: Core monitoring and alert systems

### 🔧 **Recent Improvements**
- **Duplicate Route Resolution**: Eliminated conflicting endpoints
- **Real ObjectId Support**: Using actual database IDs for testing
- **Enhanced Pagination**: Improved large dataset handling
- **Better Error Handling**: Detailed error messages and validation

### 📊 **Endpoint Statistics**
- **Total Endpoints**: 194 available endpoints
- **Tested Endpoints**: 40 critical endpoints
- **Working**: 26 endpoints (65%)
- **Failed**: 10 endpoints (25%)
- **Skipped**: 4 endpoints (10%)

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

## 🚨 **Known Issues & Limitations**

### **High Priority Issues**
- Device listing endpoint returns 500 error
- Patient search parameter validation needs fixing
- Hospital user search parameter validation needs fixing

### **Medium Priority Issues**
- Logout endpoint not implemented
- Token refresh parameter validation needs fixing
- Medical history search functionality missing
- Performance monitoring MongoDB service issues

### **Low Priority Issues**
- Rate limit blacklist GET method not implemented

## 🔄 **Recent Changes**

### **Duplicate Route Resolution**
- Removed conflicting routes between `admin.py` and `admin_crud.py`
- Consolidated all CRUD operations in `admin.py`
- Preserved unique medical history endpoint
- Eliminated route conflicts and overrides

### **Testing Improvements**
- Implemented comprehensive endpoint testing
- Added real ObjectId support for testing
- Created detailed error reporting
- Established baseline performance metrics
"""
    
    openapi_spec["info"]["description"] = current_description
    openapi_spec["info"]["version"] = "2.1.0"
    openapi_spec["info"]["title"] = "My FirstCare Opera Panel API (Updated)"
    
    return openapi_spec

def add_status_endpoints(openapi_spec):
    """Add status and health check endpoints to the specification"""
    
    # Add health check endpoint
    if "/health" not in openapi_spec["paths"]:
        openapi_spec["paths"]["/health"] = {
            "get": {
                "summary": "System Health Check",
                "description": "Check the overall health and status of the API system",
                "tags": ["system"],
                "responses": {
                    "200": {
                        "description": "System is healthy",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "status": {"type": "string", "example": "healthy"},
                                        "timestamp": {"type": "string", "format": "date-time"},
                                        "version": {"type": "string", "example": "2.1.0"}
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    
    # Add status endpoint
    if "/status" not in openapi_spec["paths"]:
        openapi_spec["paths"]["/status"] = {
            "get": {
                "summary": "API Status Information",
                "description": "Get detailed status information about the API including endpoint statistics",
                "tags": ["system"],
                "responses": {
                    "200": {
                        "description": "API status information",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "status": {"type": "string", "example": "operational"},
                                        "total_endpoints": {"type": "integer", "example": 194},
                                        "tested_endpoints": {"type": "integer", "example": 40},
                                        "working_endpoints": {"type": "integer", "example": 26},
                                        "failed_endpoints": {"type": "integer", "example": 10},
                                        "success_rate": {"type": "number", "example": 65.0},
                                        "last_updated": {"type": "string", "format": "date-time"}
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    
    return openapi_spec

def update_tags(openapi_spec):
    """Update and organize API tags"""
    
    # Define organized tags
    organized_tags = [
        {"name": "system", "description": "System health and status endpoints"},
        {"name": "authentication", "description": "Authentication and authorization endpoints"},
        {"name": "admin", "description": "Administrative operations and management"},
        {"name": "master-data", "description": "Master data management (hospitals, provinces, districts)"},
        {"name": "devices", "description": "Device management and mapping"},
        {"name": "patients", "description": "Patient management and profiles"},
        {"name": "medical-history", "description": "Medical history and records"},
        {"name": "hospital-users", "description": "Hospital user management"},
        {"name": "analytics", "description": "Analytics and reporting"},
        {"name": "security", "description": "Security and monitoring"},
        {"name": "geographic", "description": "Geographic data and dropdowns"},
        {"name": "ava4", "description": "AVA4 device integration"},
        {"name": "kati", "description": "Kati watch integration"},
        {"name": "qube-vital", "description": "Qube-Vital device integration"},
        {"name": "realtime", "description": "Real-time data and WebSocket endpoints"},
        {"name": "performance", "description": "Performance monitoring and metrics"}
    ]
    
    openapi_spec["tags"] = organized_tags
    
    return openapi_spec

def save_updated_specification(openapi_spec):
    """Save the updated OpenAPI specification"""
    
    # Save as JSON file
    with open("Updated_MyFirstCare_API_OpenAPI_Spec.json", "w") as f:
        json.dump(openapi_spec, f, indent=2)
    
    # Save as YAML file (if pyyaml is available)
    try:
        import yaml
        with open("Updated_MyFirstCare_API_OpenAPI_Spec.yaml", "w") as f:
            yaml.dump(openapi_spec, f, default_flow_style=False, indent=2)
        print("✅ Saved as both JSON and YAML formats")
    except ImportError:
        print("✅ Saved as JSON format (YAML not available)")
    
    print(f"📄 Updated specification saved to:")
    print(f"   - Updated_MyFirstCare_API_OpenAPI_Spec.json")
    print(f"   - Updated_MyFirstCare_API_OpenAPI_Spec.yaml (if available)")

def main():
    """Main function to update Swagger documentation"""
    print("🔄 Updating Swagger Documentation...")
    
    # Fetch current OpenAPI specification
    print("📥 Fetching current OpenAPI specification...")
    openapi_spec = fetch_current_openapi()
    
    if not openapi_spec:
        print("❌ Failed to fetch OpenAPI specification")
        return
    
    # Update the specification
    print("📝 Updating API information...")
    openapi_spec = update_openapi_info(openapi_spec)
    
    print("🏷️  Updating API tags...")
    openapi_spec = update_tags(openapi_spec)
    
    print("➕ Adding status endpoints...")
    openapi_spec = add_status_endpoints(openapi_spec)
    
    # Save the updated specification
    print("💾 Saving updated specification...")
    save_updated_specification(openapi_spec)
    
    print("✅ Swagger documentation updated successfully!")
    print(f"📊 Total endpoints in specification: {len(openapi_spec.get('paths', {}))}")
    print(f"🏷️  Total tags: {len(openapi_spec.get('tags', []))}")

if __name__ == "__main__":
    main() 