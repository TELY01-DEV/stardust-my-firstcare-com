# Qube-Vital Unregistered Patient Swagger Documentation Update

## 📅 **Update Date**: 2025-07-16

## 🎯 **Overview**

Updated the Swagger/OpenAPI documentation to properly document the Qube-Vital unregistered patient auto-creation behavior. This ensures API users understand what happens when Qube-Vital payloads don't match existing patient records.

## ✅ **Changes Made**

### **1. Qube-Vital Data Endpoint Documentation (`app/routes/qube_vital.py`)**

**Enhanced the `/api/qube-vital/data` endpoint documentation with comprehensive patient handling information:**

#### **📋 Patient Handling Behavior Section**
- **Registered Patients**: Normal data processing and storage
- **Unregistered Patients (Auto-Creation)**: Detailed explanation of auto-creation process
- **FHIR R5 Processing**: Clarification of processing flow
- **Data Flow**: Step-by-step process explanation

#### **🔍 Key Documentation Added:**

##### **Auto-Creation Process**
- **Auto-Creation**: If no patient exists with the provided citizen ID, a new patient is automatically created
- **Registration Status**: New patients are marked with `"registration_status": "unregistered"`
- **Data Sources**: Patient information is extracted from the Qube-Vital payload:
  - `citiz`: Citizen ID (Thai national ID)
  - `nameTH`: Thai name
  - `nameEN`: English name  
  - `brith`: Birth date (YYYYMMDD format)
  - `gender`: Gender (1=male, other=female)

##### **Medical Data Processing**
- **Medical Data Processing**: Data is processed and stored normally for unregistered patients
- **No Data Loss**: All medical data is preserved regardless of registration status

##### **FHIR R5 Processing**
- **MQTT Listener**: FHIR R5 processing is disabled in the Qube-Vital MQTT listener
- **Main API Service**: FHIR R5 resources are created by the main API service
- **Unregistered Patients**: FHIR processing applies to both registered and unregistered patients

##### **Data Flow**
1. **MQTT Reception**: Qube-Vital listener receives data on `CM4_BLE_GW_TX` topic
2. **Patient Lookup**: System searches for patient by citizen ID
3. **Auto-Creation**: If not found, creates unregistered patient
4. **Data Storage**: Stores medical data in patient collection and history collections
5. **FHIR Processing**: Main API service handles FHIR R5 resource creation

### **2. Main API Description (`main.py`)**

**Added unregistered patient handling information to the main API description:**

#### **👥 Patient Management Section**
Added: **"Unregistered Patient Auto-Creation**: Qube-Vital devices automatically create unregistered patients when citizen ID doesn't match existing records"

## 📊 **Impact**

### **✅ Benefits**
1. **Clear Documentation**: API users now understand the auto-creation behavior
2. **No Surprises**: Developers know what to expect when sending Qube-Vital data
3. **Data Integrity**: Documentation confirms no medical data is lost
4. **FHIR Compliance**: Clear explanation of FHIR R5 processing flow

### **🎯 Target Audience**
- **API Developers**: Understanding the data flow and patient creation
- **System Administrators**: Knowing how unregistered patients are handled
- **Healthcare Providers**: Understanding patient registration status
- **Integration Teams**: Planning for Qube-Vital device integration

## 🔄 **Swagger UI Updates**

### **Before Update**
- ❌ No mention of unregistered patient handling
- ❌ No explanation of auto-creation process
- ❌ No documentation of `registration_status` field
- ❌ Unclear data flow for unmatched citizen IDs

### **After Update**
- ✅ Comprehensive patient handling documentation
- ✅ Detailed auto-creation process explanation
- ✅ Clear data flow documentation
- ✅ FHIR R5 processing clarification
- ✅ No data loss guarantee documented

## 📋 **API Endpoints Affected**

### **Primary Endpoint**
- `POST /api/qube-vital/data` - Enhanced with comprehensive patient handling documentation

### **Related Endpoints**
- All Qube-Vital device management endpoints remain unchanged
- Main API description updated for overall context

## 🚀 **Next Steps**

### **Immediate Actions**
1. ✅ Documentation updated in code
2. ✅ Main API description enhanced
3. 🔄 **Restart application** to serve updated OpenAPI specification
4. 🔄 **Test Swagger UI** to verify documentation appears correctly

### **Verification Commands**
```bash
# Restart the application to apply changes
docker-compose restart opera-panel

# Check the updated OpenAPI specification
curl -s http://localhost:5054/openapi.json | jq '.paths."/api/qube-vital/data".post.description'

# Access Swagger UI to see the updated documentation
open http://localhost:5054/docs
```

## 📝 **Documentation Standards**

### **✅ Best Practices Applied**
- **Comprehensive Coverage**: All aspects of patient handling documented
- **Clear Structure**: Organized sections for different scenarios
- **Technical Details**: Specific field names and data formats
- **Process Flow**: Step-by-step explanation of data handling
- **No Data Loss**: Explicit guarantee of data preservation

### **🎯 Documentation Quality**
- **Completeness**: Covers all patient handling scenarios
- **Clarity**: Easy to understand for developers
- **Accuracy**: Reflects actual system behavior
- **Maintainability**: Structured for easy updates

## 🔗 **Related Documentation**

- **MQTT Data Processing Handbook**: `docs/MQTT_DATA_PROCESSING_HANDBOOK.md`
- **Qube-Vital MQTT Payload**: `docs/Qube-Vital_MQTT_PAYLOAD.md`
- **Device Mapping API Guide**: `Device_Mapping_API_Guide.md`
- **Patient Security Implementation**: `docs/patient_security_implementation.md`

---

**Status**: ✅ **COMPLETED** - Swagger documentation updated with comprehensive unregistered patient handling information. 