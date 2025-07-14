# Error Handling Migration Plan

## 🎯 **Migration Objective**
Update all existing API endpoints to use the new enhanced error handling system for consistency, better debugging, and improved external system integration.

## 📊 **Current Status Analysis**

### ✅ **Already Updated (3 endpoints):**
- `main.py` - Global exception handlers ✅
- `/health` - Health check endpoint ✅  
- `/` - Root endpoint ✅
- `/admin/device-mapping/ava4-box` (POST) - One device mapping endpoint ✅

### ❌ **Needs Migration (47+ endpoints):**

#### **Phase 1: Critical Priority (6 endpoints)**
🔴 **Authentication Endpoints** - Used by all clients
- `/login` (POST) - app/routes/__init__.py
- `/refresh` (POST) - app/routes/__init__.py

🔴 **Device Data Endpoints** - Used by IoT devices  
- `/ava4/data` (POST) - app/routes/ava4.py
- `/kati/data` (POST) - app/routes/kati.py  
- `/qube-vital/data` (POST) - app/routes/qube_vital.py

🔴 **Device Management**
- `/ava4/devices/{device_id}` (GET) - app/routes/ava4.py

#### **Phase 2: High Priority (11 endpoints)**
🟠 **Remaining Device Mapping Endpoints**
- `/admin/device-mapping/` (GET) - Get all mappings
- `/admin/device-mapping/{patient_id}` (GET) - Get patient mapping  
- `/admin/device-mapping/device-types` (GET) - Get device types
- `/admin/device-mapping/available/ava4-boxes` (GET) - Available boxes
- `/admin/device-mapping/available/kati-watches` (GET) - Available watches
- `/admin/device-mapping/kati-watch` (POST) - Assign watch
- `/admin/device-mapping/medical-device` (POST) - Assign medical device
- `/admin/device-mapping/medical-device/{device_id}` (PUT) - Update device
- `/admin/device-mapping/ava4-box/{box_id}` (DELETE) - Unassign box
- `/admin/device-mapping/kati-watch/{watch_id}` (DELETE) - Unassign watch
- `/admin/device-mapping/medical-device/{device_id}` (DELETE) - Remove device

#### **Phase 3: Medium Priority (15 endpoints)**
🟡 **Core Admin Endpoints**
- `/admin/patients` (GET) - Get patients list
- `/admin/medical-history/{history_type}` (GET) - Get medical history
- `/admin/audit-log` (GET) - Get audit logs

🟡 **Device Management Endpoints**
- `/ava4/devices` (GET) - Get AVA4 devices
- `/kati/devices` (GET) - Get Kati devices  
- `/kati/test` (GET) - Test endpoint

🟡 **Device Data Management**
- `/device/data` (GET) - Get device data
- `/device/data/{observation_id}` (GET) - Get specific record
- `/device/data/{observation_id}` (DELETE) - Delete record

🟡 **Patient CRUD Operations**
- `/admin-crud/patients` (POST) - Create patient
- `/admin-crud/patients/{patient_id}` (PUT) - Update patient  
- `/admin-crud/patients/{patient_id}` (DELETE) - Delete patient
- `/admin-crud/patients/{patient_id}` (GET) - Get patient
- `/admin-crud/patients/{patient_id}/medical-history` (GET) - Patient history
- `/admin-crud/patients/{patient_id}/devices` (GET) - Patient devices

#### **Phase 4: Lower Priority (15+ endpoints)**
🟢 **Medical History CRUD**
- Medical history record operations
- Master data operations
- Device CRUD operations
- Bulk operations

## 🚀 **Implementation Strategy**

### **Step 1: Preparation**
1. ✅ Create error definitions (`app/utils/error_definitions.py`)
2. ✅ Add global exception handlers (`main.py`)
3. ✅ Create migration documentation

### **Step 2: Phase 1 - Critical Priority**
**Target: Authentication + Core Device Data (6 endpoints)**

#### 2.1 Authentication Endpoints (2 endpoints)
- **File**: `app/routes/__init__.py`
- **Impact**: All API clients
- **Error Types**: Authentication errors, validation errors
- **Estimated Time**: 30 minutes

#### 2.2 Device Data Endpoints (4 endpoints)  
- **Files**: `app/routes/ava4.py`, `app/routes/kati.py`, `app/routes/qube_vital.py`
- **Impact**: IoT device integrations
- **Error Types**: Validation errors, device not found, data processing errors
- **Estimated Time**: 45 minutes

### **Step 3: Phase 2 - High Priority**
**Target: Device Mapping Completion (11 endpoints)**

#### 3.1 Remaining Device Mapping Endpoints
- **File**: `app/routes/device_mapping.py`
- **Impact**: Device management operations
- **Error Types**: Resource not found, business logic errors, validation errors
- **Estimated Time**: 60 minutes

### **Step 4: Phase 3 - Medium Priority**
**Target: Admin & CRUD Operations (15 endpoints)**

#### 4.1 Core Admin Endpoints
- **File**: `app/routes/admin.py`
- **Impact**: Admin dashboard functionality
- **Estimated Time**: 45 minutes

#### 4.2 Device Management & CRUD
- **Files**: `app/routes/device_crud.py`, `app/routes/admin_crud.py`
- **Impact**: Data management operations
- **Estimated Time**: 60 minutes

### **Step 5: Phase 4 - Lower Priority**
**Target: Remaining CRUD Operations (15+ endpoints)**
- **Estimated Time**: 90 minutes

### **Step 6: Testing & Validation**
- Test all updated endpoints
- Verify error response consistency
- Update documentation
- **Estimated Time**: 45 minutes

## 📝 **Migration Checklist Per Endpoint**

### **For Each Endpoint:**
1. ✅ **Import error handling functions**
   ```python
   from app.utils.error_definitions import create_error_response, create_success_response
   ```

2. ✅ **Add Request parameter for tracking**
   ```python
   async def endpoint(request: Request, ...):
       request_id = request.headers.get("X-Request-ID")
   ```

3. ✅ **Replace old error handling**
   ```python
   # OLD
   raise HTTPException(status_code=500, detail=str(e))
   
   # NEW  
   raise HTTPException(
       status_code=500,
       detail=create_error_response(
           "INTERNAL_SERVER_ERROR",
           custom_message=f"Operation failed: {str(e)}",
           request_id=request_id
       ).dict()
   )
   ```

4. ✅ **Update success responses**
   ```python
   # OLD
   return {"message": "Success", "data": data}
   
   # NEW
   success_response = create_success_response(
       message="Operation completed successfully",
       data=data,
       request_id=request_id
   )
   return success_response.dict()
   ```

5. ✅ **Add proper error codes**
   - Use appropriate error codes from our definitions
   - Include field names and values where relevant
   - Add helpful suggestions

## 🧪 **Testing Strategy**

### **For Each Updated Endpoint:**
1. **Validation Error Testing**
   ```bash
   # Missing required fields
   curl -X POST endpoint -d '{"invalid": "data"}'
   
   # Invalid data types  
   curl -X POST endpoint -d '{"field": 123}' # when string expected
   ```

2. **Business Logic Error Testing**
   ```bash
   # Non-existent resources
   curl -X GET endpoint/nonexistent_id
   
   # Conflict scenarios
   curl -X POST endpoint -d '{"conflicting": "data"}'
   ```

3. **Success Response Testing**
   ```bash
   # Valid requests with request ID
   curl -X GET endpoint -H "X-Request-ID: test-123"
   ```

4. **Request ID Correlation Testing**
   ```bash
   # Verify request ID appears in response
   curl -H "X-Request-ID: correlation-test" endpoint
   ```

## 📊 **Progress Tracking**

### **Completion Metrics:**
- **Phase 1**: 6/6 endpoints (Critical) 
- **Phase 2**: 0/11 endpoints (High Priority)
- **Phase 3**: 0/15 endpoints (Medium Priority)  
- **Phase 4**: 0/15+ endpoints (Lower Priority)

### **Quality Metrics:**
- All endpoints return structured error responses ✅/❌
- Request ID tracking implemented ✅/❌  
- Appropriate error codes used ✅/❌
- Success responses standardized ✅/❌
- Documentation updated ✅/❌

## 🎯 **Success Criteria**

### **Technical Requirements:**
1. ✅ All endpoints use structured error responses
2. ✅ Request ID tracking implemented across all endpoints
3. ✅ Consistent error codes and messages
4. ✅ Standardized success response format
5. ✅ No breaking changes to existing API contracts

### **Quality Requirements:**
1. ✅ All endpoints tested with various error scenarios
2. ✅ Error responses include helpful suggestions
3. ✅ Request/response correlation works properly
4. ✅ Performance impact is minimal
5. ✅ Documentation is updated

## 🚨 **Risk Mitigation**

### **Potential Risks:**
1. **Breaking Changes**: Ensure response format changes don't break existing clients
2. **Performance Impact**: Minimize overhead from new error handling
3. **Testing Coverage**: Ensure all error paths are tested
4. **Rollback Plan**: Keep old error handling as backup during migration

### **Mitigation Strategies:**
1. **Gradual Rollout**: Update endpoints in phases
2. **Backward Compatibility**: Maintain existing response structure where possible
3. **Comprehensive Testing**: Test each phase before proceeding
4. **Monitoring**: Track error rates and response times during migration

## 📅 **Timeline Estimate**

- **Phase 1** (Critical): 1.5 hours
- **Phase 2** (High): 1 hour  
- **Phase 3** (Medium): 1.75 hours
- **Phase 4** (Lower): 1.5 hours
- **Testing & Documentation**: 0.75 hours

**Total Estimated Time**: ~6 hours

## 🎉 **Expected Benefits**

### **Immediate Benefits:**
- Consistent error handling across all endpoints
- Better debugging with request ID correlation
- Improved external system integration

### **Long-term Benefits:**
- Easier maintenance and troubleshooting
- Better API documentation and developer experience
- Enhanced monitoring and analytics capabilities
- Reduced support overhead with clearer error messages

---

**Next Step**: Begin Phase 1 implementation with authentication and device data endpoints. 