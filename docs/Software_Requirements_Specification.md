# 📋 Software Requirements Specification (SRS)
## My FirstCare Opera Panel

**Document Version**: 1.0  
**Date**: June 27, 2025  
**Prepared by**: Requirements Team  
**Reviewed by**: [Technical Lead]  
**Approved by**: [Project Manager]  

---

## 1. Introduction

### 1.1 Purpose
This Software Requirements Specification (SRS) document describes the functional and non-functional requirements for the My FirstCare Opera Panel system. This document serves as the foundation for system design and development activities.

### 1.2 Scope
The My FirstCare Opera Panel is a comprehensive medical IoT device management system that integrates with AVA4, Kati Watch, and Qube-Vital devices to provide centralized monitoring, data collection, and administrative capabilities for healthcare providers.

### 1.3 Definitions and Acronyms
- **API**: Application Programming Interface
- **AVA4**: Medical monitoring device for vital signs
- **FHIR**: Fast Healthcare Interoperability Resources
- **IoT**: Internet of Things
- **JWT**: JSON Web Token
- **Kati Watch**: Wearable health monitoring device
- **MongoDB**: NoSQL document database
- **Qube-Vital**: Hospital-grade vital signs monitoring device
- **RBAC**: Role-Based Access Control
- **REST**: Representational State Transfer
- **SRS**: Software Requirements Specification
- **UI**: User Interface
- **UX**: User Experience

### 1.4 References
- ISO 29110-4-1:2011 Software Engineering Standards
- FHIR R5 Specification
- HL7 Healthcare Standards
- FastAPI Documentation
- MongoDB Documentation

---

## 2. Overall Description

### 2.1 Product Perspective
The My FirstCare Opera Panel system is a standalone web-based application that interfaces with:
- External medical IoT devices (AVA4, Kati Watch, Qube-Vital)
- Stardust-V1 authentication service
- MongoDB database for data persistence
- FHIR-compliant audit logging system

### 2.2 Product Functions
1. **Device Data Collection**: Receive and process data from medical IoT devices
2. **Data Storage**: Store device data in appropriate medical history collections
3. **User Authentication**: Integrate with Stardust-V1 for centralized authentication
4. **Administrative Interface**: Provide web-based admin panel for system management
5. **Audit Logging**: Generate FHIR R5 compliant audit logs
6. **Real-time Monitoring**: Provide real-time device status and data updates
7. **Reporting**: Generate reports and analytics for healthcare providers

### 2.3 User Classes and Characteristics
| User Class | Characteristics | Responsibilities |
|------------|-----------------|------------------|
| **System Administrator** | Technical expertise, full system access | System configuration, user management, troubleshooting |
| **Healthcare Administrator** | Healthcare domain knowledge, administrative access | Patient management, device assignment, reporting |
| **Medical Operator** | Clinical knowledge, operational access | Data monitoring, patient care coordination |
| **Data Viewer** | Basic system knowledge, read-only access | View reports, monitor patient data |

### 2.4 Operating Environment
- **Server Environment**: Linux-based Docker containers
- **Database**: MongoDB 4.4 or higher
- **Web Server**: FastAPI with Uvicorn
- **Client Environment**: Modern web browsers (Chrome, Firefox, Safari, Edge)
- **Network**: HTTPS-enabled network connectivity
- **Integration**: REST API connections to external services

---

## 3. Functional Requirements

### 3.1 User Authentication and Authorization

#### 3.1.1 User Login (REQ-AUTH-001)
**Description**: Users must authenticate using Stardust-V1 centralized authentication service.

**Functional Requirements**:
- System shall integrate with Stardust-V1 authentication API
- System shall validate user credentials via `/auth/login` endpoint
- System shall store JWT tokens securely
- System shall handle token expiration and refresh

**Input**: Username and password
**Output**: JWT access token and refresh token
**Priority**: High

#### 3.1.2 Role-Based Access Control (REQ-AUTH-002)
**Description**: System shall implement role-based access control for different user types.

**Functional Requirements**:
- System shall support roles: admin, operator, viewer
- System shall restrict access to functions based on user roles
- System shall validate user permissions for each API endpoint
- System shall provide role-based UI element visibility

**Input**: User role information from JWT token
**Output**: Authorized access to system functions
**Priority**: High

### 3.2 Device Data Management

#### 3.2.1 AVA4 Device Integration (REQ-DEV-001)
**Description**: System shall accept and process data from AVA4 devices.

**Functional Requirements**:
- System shall provide `POST /api/ava4/data` endpoint
- System shall validate AVA4 data format using Pydantic models
- System shall route data to appropriate medical history collections
- System shall link device data to patient records via MAC address
- System shall support data types: blood pressure, body data, temperature

**Input**: JSON payload with timestamp, device ID, type, data
**Output**: Confirmation of data storage and audit log entry
**Priority**: High

#### 3.2.2 Kati Watch Integration (REQ-DEV-002)
**Description**: System shall accept and process data from Kati Watch devices.

**Functional Requirements**:
- System shall provide `POST /api/kati/data` endpoint
- System shall validate Kati Watch data format
- System shall route data to spo2_histories, step_histories, sleep_data_histories
- System shall link device data to patient records via IMEI
- System shall support real-time data streaming

**Input**: JSON payload with timestamp, IMEI, type, data
**Output**: Confirmation of data storage and audit log entry
**Priority**: High

#### 3.2.3 Qube-Vital Integration (REQ-DEV-003)
**Description**: System shall accept and process data from Qube-Vital devices.

**Functional Requirements**:
- System shall provide `POST /api/qube-vital/data` endpoint
- System shall validate Qube-Vital data format
- System shall route data to blood_sugar_histories, bp_histories, spo2_histories
- System shall link device data to hospital records
- System shall support hospital-grade device authentication

**Input**: JSON payload with timestamp, device ID, type, data
**Output**: Confirmation of data storage and audit log entry
**Priority**: High

### 3.3 Data Retrieval and Management

#### 3.3.1 Device Data Retrieval (REQ-DATA-001)
**Description**: System shall provide endpoints to retrieve device data with filtering capabilities.

**Functional Requirements**:
- System shall provide `GET /api/{device}/data` endpoints
- System shall support filtering by patient ID, date range, device type
- System shall support pagination for large datasets
- System shall return data in JSON format
- System shall implement soft delete functionality

**Input**: Query parameters for filtering
**Output**: Filtered device data in JSON format
**Priority**: Medium

#### 3.3.2 Medical History Access (REQ-DATA-002)
**Description**: System shall provide access to medical history data across all device types.

**Functional Requirements**:
- System shall provide `GET /history/{type}` endpoint
- System shall support cross-device medical history queries
- System shall aggregate data from multiple sources
- System shall support temporal queries and trends

**Input**: History type, patient ID, date range
**Output**: Aggregated medical history data
**Priority**: Medium

### 3.4 Administrative Interface

#### 3.4.1 Patient Management (REQ-ADMIN-001)
**Description**: System shall provide administrative interface for patient management.

**Functional Requirements**:
- System shall display patient list with search and filter capabilities
- System shall provide patient profile pages
- System shall support patient-device assignment
- System shall display patient medical history
- System shall support patient data export

**Input**: User interactions via web interface
**Output**: Patient management interface
**Priority**: High

#### 3.4.2 Device Management (REQ-ADMIN-002)
**Description**: System shall provide administrative interface for device management.

**Functional Requirements**:
- System shall display device list for all device types
- System shall show device status and connectivity
- System shall support device configuration
- System shall provide device assignment to patients/hospitals
- System shall display device activity logs

**Input**: User interactions via web interface
**Output**: Device management interface
**Priority**: High

#### 3.4.3 Dashboard and Analytics (REQ-ADMIN-003)
**Description**: System shall provide dashboard with analytics and real-time monitoring.

**Functional Requirements**:
- System shall display real-time device status
- System shall provide vital signs charts and graphs
- System shall support date range filtering
- System shall provide statistical reports
- System shall support data export functionality

**Input**: User interactions and real-time data
**Output**: Interactive dashboard with analytics
**Priority**: Medium

### 3.5 Audit Logging and Compliance

#### 3.5.1 FHIR R5 Audit Logging (REQ-AUDIT-001)
**Description**: System shall generate FHIR R5 compliant audit logs for all data transactions.

**Functional Requirements**:
- System shall generate Provenance resources for all device data submissions
- System shall include recorded timestamp, agent information, entity details
- System shall store audit logs in separate audit_log_db database
- System shall implement TTL for automatic log expiration (180 days)
- System shall link audit logs to corresponding data entries

**Input**: Device data submission events
**Output**: FHIR R5 Provenance resources
**Priority**: High

#### 3.5.2 Data Integrity and Traceability (REQ-AUDIT-002)
**Description**: System shall maintain complete data integrity and traceability.

**Functional Requirements**:
- System shall track all data modifications
- System shall maintain audit trail for administrative actions
- System shall provide data lineage information
- System shall support audit log queries and reporting

**Input**: System events and user actions
**Output**: Comprehensive audit trail
**Priority**: Medium

---

## 4. Non-Functional Requirements

### 4.1 Performance Requirements

#### 4.1.1 Response Time (REQ-PERF-001)
- API endpoints shall respond within 200ms for 95% of requests
- Database queries shall execute within 100ms for standard operations
- Admin panel pages shall load within 2 seconds
- Real-time updates shall have latency less than 500ms

#### 4.1.2 Throughput (REQ-PERF-002)
- System shall support 1000 concurrent device data submissions per minute
- System shall handle 100 concurrent admin panel users
- Database shall support 10,000 read operations per minute
- System shall process 50,000 medical history records per hour

#### 4.1.3 Scalability (REQ-PERF-003)
- System shall support horizontal scaling via Docker containers
- Database shall support sharding for large datasets
- System shall support load balancing across multiple instances
- System shall maintain performance with 1TB+ of medical data

### 4.2 Security Requirements

#### 4.2.1 Authentication and Authorization (REQ-SEC-001)
- All API endpoints shall require valid JWT authentication
- System shall implement role-based access control
- System shall support API key authentication for system services
- System shall enforce strong password policies via Stardust-V1

#### 4.2.2 Data Protection (REQ-SEC-002)
- All data transmission shall use HTTPS/TLS encryption
- Sensitive data shall be encrypted at rest
- System shall implement data anonymization for reporting
- System shall comply with healthcare data protection regulations

#### 4.2.3 Audit and Monitoring (REQ-SEC-003)
- System shall log all security events
- System shall implement intrusion detection
- System shall provide security monitoring dashboard
- System shall support automated security scanning

### 4.3 Reliability Requirements

#### 4.3.1 Availability (REQ-REL-001)
- System shall maintain 99.9% uptime
- System shall support graceful degradation during partial failures
- System shall implement automatic failover mechanisms
- System shall provide redundancy for critical components

#### 4.3.2 Error Handling (REQ-REL-002)
- System shall provide comprehensive error handling
- System shall implement retry mechanisms for transient failures
- System shall provide meaningful error messages
- System shall log all errors for troubleshooting

#### 4.3.3 Data Backup and Recovery (REQ-REL-003)
- System shall perform automated daily backups
- System shall support point-in-time recovery
- System shall implement backup verification
- System shall provide disaster recovery procedures

### 4.4 Usability Requirements

#### 4.4.1 User Interface (REQ-UI-001)
- Admin panel shall use responsive design for multiple screen sizes
- Interface shall follow modern web design principles
- System shall provide consistent navigation and layout
- Interface shall support accessibility standards (WCAG 2.1)

#### 4.4.2 User Experience (REQ-UX-001)
- System shall provide intuitive user workflows
- System shall include contextual help and documentation
- System shall support keyboard navigation
- System shall provide clear feedback for user actions

### 4.5 Compatibility Requirements

#### 4.5.1 Browser Compatibility (REQ-COMPAT-001)
- System shall support modern web browsers (Chrome, Firefox, Safari, Edge)
- System shall maintain compatibility with browser versions up to 2 years old
- System shall provide graceful degradation for older browsers
- System shall support mobile browsers for responsive access

#### 4.5.2 Integration Compatibility (REQ-COMPAT-002)
- System shall integrate with Stardust-V1 authentication service
- System shall support FHIR R5 standard compliance
- System shall provide REST API compatibility
- System shall support standard database connection protocols

---

## 5. System Architecture Requirements

### 5.1 Architectural Constraints
- System shall use microservices architecture with Docker containers
- System shall implement RESTful API design principles
- System shall use event-driven architecture for real-time features
- System shall support cloud-native deployment patterns

### 5.2 Technology Stack Requirements
- **Backend**: FastAPI framework with Python 3.9+
- **Database**: MongoDB 4.4+ with Motor async driver
- **Authentication**: JWT tokens with Stardust-V1 integration
- **Frontend**: Jinja2 templates with Tabler.io framework
- **Real-time**: Socket.IO for WebSocket connections
- **Containerization**: Docker and Docker Compose
- **Monitoring**: Logging and monitoring solutions

### 5.3 Data Architecture Requirements
- System shall use document-based data model
- System shall implement data partitioning for large datasets
- System shall support data archiving and purging policies
- System shall maintain referential integrity across collections

---

## 6. Interface Requirements

### 6.1 User Interfaces
- **Login Interface**: Stardust-V1 integrated authentication
- **Dashboard Interface**: Real-time monitoring and analytics
- **Patient Management Interface**: Patient list and profile management
- **Device Management Interface**: Device status and configuration
- **Reporting Interface**: Data export and report generation

### 6.2 Hardware Interfaces
- **AVA4 Device Interface**: HTTP/HTTPS communication
- **Kati Watch Interface**: Bluetooth/WiFi connectivity
- **Qube-Vital Interface**: Network-based communication
- **Server Hardware**: Standard x86-64 server architecture

### 6.3 Software Interfaces
- **Stardust-V1 API**: Authentication and user management
- **MongoDB Database**: Data persistence and retrieval
- **FHIR Services**: Healthcare data standards compliance
- **External APIs**: Third-party service integrations

### 6.4 Communication Interfaces
- **HTTP/HTTPS**: Primary communication protocol
- **WebSocket**: Real-time data streaming
- **REST API**: Standard API communication
- **JSON**: Data exchange format

---

## 7. Validation and Verification

### 7.1 Functional Testing Requirements
- Unit testing with minimum 80% code coverage
- Integration testing for all API endpoints
- System testing for end-to-end workflows
- User acceptance testing with stakeholder validation

### 7.2 Non-Functional Testing Requirements
- Performance testing for load and stress scenarios
- Security testing including penetration testing
- Compatibility testing across supported browsers
- Usability testing with representative users

### 7.3 Compliance Testing Requirements
- FHIR R5 compliance validation
- Healthcare data protection compliance
- ISO 29110 process compliance
- Security standards compliance testing

---

## 8. Requirements Traceability Matrix

| Requirement ID | Priority | Test Case ID | Implementation Status |
|----------------|----------|--------------|----------------------|
| REQ-AUTH-001 | High | TC-AUTH-001 | Not Started |
| REQ-AUTH-002 | High | TC-AUTH-002 | Not Started |
| REQ-DEV-001 | High | TC-DEV-001 | Not Started |
| REQ-DEV-002 | High | TC-DEV-002 | Not Started |
| REQ-DEV-003 | High | TC-DEV-003 | Not Started |
| REQ-DATA-001 | Medium | TC-DATA-001 | Not Started |
| REQ-DATA-002 | Medium | TC-DATA-002 | Not Started |
| REQ-ADMIN-001 | High | TC-ADMIN-001 | Not Started |
| REQ-ADMIN-002 | High | TC-ADMIN-002 | Not Started |
| REQ-ADMIN-003 | Medium | TC-ADMIN-003 | Not Started |
| REQ-AUDIT-001 | High | TC-AUDIT-001 | Not Started |
| REQ-AUDIT-002 | Medium | TC-AUDIT-002 | Not Started |

---

## 9. Appendices

### Appendix A: Data Models
- Patient data structure
- Device data formats
- Medical history schemas
- FHIR resource templates

### Appendix B: API Specifications
- RESTful endpoint definitions
- Request/response formats
- Error code specifications
- Authentication headers

### Appendix C: UI Mockups
- Dashboard layouts
- Patient management screens
- Device configuration interfaces
- Reporting templates

---

**Document Control:**
- **Version**: 1.0
- **Created**: June 27, 2025
- **Last Modified**: June 27, 2025
- **Next Review**: July 11, 2025
- **Approval Status**: Draft
- **Distribution**: Development Team, Stakeholders
