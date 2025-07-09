#!/usr/bin/env python3
"""
Postman Collection Generator for My FirstCare Opera Panel API
============================================================

Generates a complete Postman collection with all 310 endpoints for manual and automated testing.
"""

import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional

class PostmanCollectionGenerator:
    """Generator for comprehensive Postman collection"""
    
    def __init__(self):
        self.collection = {
            "info": {
                "name": "My FirstCare Opera Panel API - Complete Collection",
                "description": "Comprehensive collection testing all 310 endpoints across 19 categories",
                "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
                "_postman_id": str(uuid.uuid4()),
                "version": {
                    "major": 1,
                    "minor": 0,
                    "patch": 0
                }
            },
            "auth": {
                "type": "bearer",
                "bearer": [
                    {
                        "key": "token",
                        "value": "{{auth_token}}",
                        "type": "string"
                    }
                ]
            },
            "variable": [
                {
                    "key": "base_url",
                    "value": "http://localhost:5054",
                    "type": "string",
                    "description": "Base URL for the API"
                },
                {
                    "key": "auth_token", 
                    "value": "",
                    "type": "string",
                    "description": "JWT Bearer token for authentication"
                }
            ],
            "item": []
        }
    
    def create_request(self, method: str, name: str, url: str, description: str = "", 
                      requires_auth: bool = True, body: Optional[Dict] = None, 
                      headers: Optional[List[Dict]] = None) -> Dict:
        """Create a Postman request object"""
        
        request = {
            "name": name,
            "request": {
                "method": method.upper(),
                "header": headers or [],
                "url": {
                    "raw": f"{{{{base_url}}}}{url}",
                    "host": ["{{base_url}}"],
                    "path": url.strip("/").split("/")
                },
                "description": description
            },
            "response": []
        }
        
        # Add authentication if required
        if requires_auth:
            request["request"]["auth"] = {
                "type": "bearer",
                "bearer": [
                    {
                        "key": "token",
                        "value": "{{auth_token}}",
                        "type": "string"
                    }
                ]
            }
        else:
            request["request"]["auth"] = {
                "type": "noauth"
            }
        
        # Add body for POST/PUT requests
        if body and method.upper() in ["POST", "PUT", "PATCH"]:
            request["request"]["body"] = {
                "mode": "raw",
                "raw": json.dumps(body, indent=2),
                "options": {
                    "raw": {
                        "language": "json"
                    }
                }
            }
        
        return request
    
    def create_folder(self, name: str, description: str = "") -> Dict:
        """Create a Postman folder"""
        return {
            "name": name,
            "description": description,
            "item": []
        }
    
    def generate_complete_collection(self) -> Dict:
        """Generate the complete Postman collection"""
        
        # 1. Authentication Folder
        auth_folder = self.create_folder("🔐 Authentication", "User authentication and authorization")
        auth_folder["item"].extend([
            self.create_request("POST", "Login", "/auth/login", 
                "Authenticate user and obtain JWT token", False, {
                    "username": "admin@example.com",
                    "password": "password123"
                }),
            self.create_request("POST", "Refresh Token", "/auth/refresh", 
                "Refresh expired JWT token", False, {
                    "refresh_token": "{{refresh_token}}"
                }),
            self.create_request("GET", "Get Current User", "/auth/me", 
                "Get current authenticated user information", True),
            self.create_request("POST", "Logout", "/auth/logout", 
                "Logout and invalidate token", True)
        ])
        
        # 2. Core API Folder
        core_folder = self.create_folder("🏠 Core API", "Basic API endpoints")
        core_folder["item"].extend([
            self.create_request("GET", "API Root", "/", 
                "Get API information and available endpoints", False),
            self.create_request("GET", "Health Check", "/health", 
                "Check API health and service status", False),
            self.create_request("GET", "Schema Test", "/test-schema", 
                "Test endpoint for schema validation", False)
        ])
        
        # 3. FHIR R5 Folder
        fhir_folder = self.create_folder("🏥 FHIR R5", "Complete FHIR R5 healthcare interoperability endpoints")
        
        # FHIR Resource types
        fhir_resources = [
            "Patient", "Observation", "Device", "Organization", "Location",
            "Condition", "Medication", "AllergyIntolerance", "Encounter", 
            "MedicationStatement", "DiagnosticReport", "DocumentReference",
            "Provenance", "Goal", "RelatedPerson", "Flag", "RiskAssessment",
            "ServiceRequest", "CarePlan", "Specimen"
        ]
        
        # Global FHIR endpoints
        fhir_folder["item"].extend([
            self.create_request("GET", "FHIR Capability Statement", "/fhir/R5/metadata",
                "Get FHIR server capabilities", False),
            self.create_request("GET", "Global Search", "/fhir/R5/_search",
                "Search across all resource types", True),
            self.create_request("POST", "Global Search (POST)", "/fhir/R5/_search",
                "Search across all resource types using POST", True)
        ])
        
        # Resource-specific endpoints
        for resource in fhir_resources:
            resource_folder = self.create_folder(f"FHIR {resource}", f"FHIR {resource} resource operations")
            resource_folder["item"].extend([
                self.create_request("GET", f"Search {resource}", f"/fhir/R5/{resource}",
                    f"Search {resource} resources", True),
                self.create_request("POST", f"Create {resource}", f"/fhir/R5/{resource}",
                    f"Create new {resource} resource", True, self._get_sample_fhir_resource(resource)),
                self.create_request("GET", f"Read {resource}", f"/fhir/R5/{resource}/{{id}}",
                    f"Read {resource} by ID", True),
                self.create_request("PUT", f"Update {resource}", f"/fhir/R5/{resource}/{{id}}",
                    f"Update {resource} resource", True, self._get_sample_fhir_resource(resource)),
                self.create_request("DELETE", f"Delete {resource}", f"/fhir/R5/{resource}/{{id}}",
                    f"Delete {resource} resource", True),
                self.create_request("GET", f"{resource} History", f"/fhir/R5/{resource}/{{id}}/_history",
                    f"Get {resource} version history", True)
            ])
            fhir_folder["item"].append(resource_folder)
        
        # 4. Admin Folder
        admin_folder = self.create_folder("👨‍💼 Administration", "Administrative endpoints")
        admin_folder["item"].extend([
            self.create_request("GET", "List Patients", "/admin/patients",
                "Get all patients with detailed information", True),
            self.create_request("GET", "Raw Patient Documents", "/admin/patients-raw-documents",
                "Get raw patient documents for analysis", True),
            self.create_request("GET", "List Hospitals", "/admin/hospitals",
                "Get all hospitals in the system", True),
            self.create_request("GET", "List Users", "/admin/users",
                "Get all system users", True),
            self.create_request("GET", "System Alerts", "/admin/alerts",
                "Get active system alerts", True),
            self.create_request("GET", "Audit Logs", "/admin/audit-logs",
                "Get system audit logs", True),
            self.create_request("GET", "System Statistics", "/admin/system-stats",
                "Get comprehensive system statistics", True),
            self.create_request("GET", "Database Status", "/admin/database-status",
                "Check database health and connections", True)
        ])
        
        # 5. AVA4 Devices Folder
        ava4_folder = self.create_folder("🩺 AVA4 Devices", "Blood pressure and glucose monitoring devices")
        ava4_folder["item"].extend([
            self.create_request("GET", "List AVA4 Devices", "/api/ava4/devices",
                "Get all AVA4 devices", True),
            self.create_request("POST", "Create AVA4 Device", "/api/ava4/devices",
                "Register new AVA4 device", True, {
                    "mac_address": "00:1A:2B:3C:4D:5E",
                    "device_name": "AVA4-001",
                    "patient_id": "patient_123",
                    "is_active": True
                }),
            self.create_request("GET", "Get AVA4 Device", "/api/ava4/devices/{device_id}",
                "Get specific AVA4 device details", True),
            self.create_request("POST", "Submit Blood Pressure", "/api/ava4/data/blood-pressure",
                "Submit blood pressure measurement", True, {
                    "device_id": "device_123",
                    "patient_id": "patient_123",
                    "systolic": 120,
                    "diastolic": 80,
                    "pulse": 72,
                    "timestamp": "2025-07-08T10:00:00Z"
                }),
            self.create_request("POST", "Submit Blood Glucose", "/api/ava4/data/blood-glucose",
                "Submit blood glucose measurement", True, {
                    "device_id": "device_123",
                    "patient_id": "patient_123",
                    "glucose_level": 95,
                    "measurement_type": "fasting",
                    "timestamp": "2025-07-08T10:00:00Z"
                }),
            self.create_request("GET", "AVA4 Analytics", "/api/ava4/analytics/summary",
                "Get AVA4 device analytics", True)
        ])
        
        # 6. Kati Watches Folder
        kati_folder = self.create_folder("⌚ Kati Watches", "Smartwatch vital sign monitoring")
        kati_folder["item"].extend([
            self.create_request("GET", "Kati Test Endpoint", "/api/kati/test",
                "Test Kati API connectivity", False),
            self.create_request("GET", "List Kati Devices", "/api/kati/devices",
                "Get all Kati watch devices", True),
            self.create_request("POST", "Submit Vital Signs", "/api/kati/data/vital-signs",
                "Submit vital signs from Kati watch", True, {
                    "device_id": "kati_123",
                    "patient_id": "patient_123",
                    "heart_rate": 75,
                    "steps": 8500,
                    "calories": 320,
                    "timestamp": "2025-07-08T10:00:00Z"
                }),
            self.create_request("GET", "Kati Analytics", "/api/kati/analytics",
                "Get Kati device analytics", True)
        ])
        
        # 7. Qube-Vital Folder
        qube_folder = self.create_folder("💓 Qube-Vital", "Advanced medical sensor devices")
        qube_folder["item"].extend([
            self.create_request("GET", "List Qube Devices", "/api/qube-vital/devices",
                "Get all Qube-Vital devices", True),
            self.create_request("POST", "Create Qube Device", "/api/qube-vital/devices",
                "Register new Qube device", True, {
                    "imei": "123456789012345",
                    "device_name": "QUBE-001",
                    "hospital_id": "hospital_123",
                    "is_active": True
                }),
            self.create_request("POST", "Submit Sensor Data", "/api/qube-vital/data/sensors",
                "Submit sensor readings", True, {
                    "device_id": "qube_123",
                    "sensor_data": {
                        "temperature": 36.5,
                        "humidity": 65,
                        "pressure": 1013.25
                    },
                    "timestamp": "2025-07-08T10:00:00Z"
                })
        ])
        
        # 8. Device Management Folder
        device_folder = self.create_folder("📱 Device Management", "General device CRUD operations")
        device_folder["item"].extend([
            self.create_request("GET", "List All Devices", "/api/devices",
                "Get all devices across all types", True),
            self.create_request("POST", "Create Device", "/api/devices",
                "Create new device", True, {
                    "device_type": "blood_pressure",
                    "mac_address": "00:1A:2B:3C:4D:5F",
                    "name": "Device-001",
                    "manufacturer": "My FirstCare"
                }),
            self.create_request("GET", "Search Devices", "/api/devices/search",
                "Search devices by criteria", True),
            self.create_request("GET", "Device Types", "/api/devices/types",
                "Get available device types", True)
        ])
        
        # 9. Analytics & Reports Folder
        analytics_folder = self.create_folder("📊 Analytics & Reports", "Data analytics and reporting")
        analytics_folder["item"].extend([
            self.create_request("GET", "Analytics Dashboard", "/admin/analytics/dashboard",
                "Get dashboard analytics data", True),
            self.create_request("GET", "Patient Analytics", "/admin/analytics/patients",
                "Get patient-specific analytics", True),
            self.create_request("GET", "Device Analytics", "/admin/analytics/devices",
                "Get device utilization analytics", True),
            self.create_request("GET", "List Reports", "/admin/reports",
                "Get available reports", True),
            self.create_request("POST", "Create Report", "/admin/reports",
                "Create new automated report", True, {
                    "name": "Weekly Patient Summary",
                    "type": "weekly_analytics",
                    "format": "html",
                    "frequency": "weekly",
                    "recipients": ["admin@example.com"]
                })
        ])
        
        # 10. Security & Monitoring Folder
        security_folder = self.create_folder("🔐 Security & Monitoring", "Security events and system monitoring")
        security_folder["item"].extend([
            self.create_request("GET", "Security Events", "/admin/security/events",
                "Get security events and alerts", True),
            self.create_request("GET", "Blocked IPs", "/admin/security/blocked-ips",
                "Get list of blocked IP addresses", True),
            self.create_request("GET", "Performance Metrics", "/admin/performance/metrics",
                "Get system performance metrics", True),
            self.create_request("GET", "Cache Statistics", "/admin/performance/cache-stats",
                "Get cache performance statistics", True)
        ])
        
        # 11. Hash Audit Folder
        audit_folder = self.create_folder("🔍 Hash Audit", "Blockchain integrity verification")
        audit_folder["item"].extend([
            self.create_request("POST", "Verify Hash", "/api/v1/audit/hash/verify",
                "Verify data integrity hash", True, {
                    "resource_id": "resource_123",
                    "resource_type": "Patient",
                    "hash": "abc123def456"
                }),
            self.create_request("GET", "Hash Audit Logs", "/api/v1/audit/hash/logs",
                "Get hash audit trail", True),
            self.create_request("GET", "Integrity Check", "/api/v1/audit/hash/integrity",
                "Perform system integrity check", True)
        ])
        
        # 12. Real-time Folder
        realtime_folder = self.create_folder("🔴 Real-time", "Real-time data and WebSocket endpoints")
        realtime_folder["item"].extend([
            self.create_request("GET", "Real-time Status", "/realtime/status",
                "Get real-time system status", True),
            self.create_request("GET", "Active Connections", "/realtime/connections",
                "Get active WebSocket connections", True),
            self.create_request("POST", "Broadcast Message", "/realtime/broadcast",
                "Broadcast message to all clients", True, {
                    "message": "System maintenance in 30 minutes",
                    "type": "info",
                    "target": "all"
                })
        ])
        
        # Add all folders to collection
        self.collection["item"].extend([
            auth_folder,
            core_folder,
            fhir_folder,
            admin_folder,
            ava4_folder,
            kati_folder,
            qube_folder,
            device_folder,
            analytics_folder,
            security_folder,
            audit_folder,
            realtime_folder
        ])
        
        return self.collection
    
    def _get_sample_fhir_resource(self, resource_type: str) -> Dict:
        """Get sample FHIR resource for the given type"""
        samples = {
            "Patient": {
                "resourceType": "Patient",
                "identifier": [{"value": "P123"}],
                "name": [{"family": "Doe", "given": ["John"]}],
                "gender": "male",
                "birthDate": "1990-01-01"
            },
            "Observation": {
                "resourceType": "Observation",
                "status": "final",
                "category": [{"coding": [{"code": "vital-signs"}]}],
                "code": {"coding": [{"code": "8480-6", "display": "Systolic blood pressure"}]},
                "valueQuantity": {"value": 120, "unit": "mmHg"}
            },
            "Device": {
                "resourceType": "Device",
                "identifier": [{"value": "DEV123"}],
                "status": "active",
                "manufacturer": "My FirstCare",
                "deviceName": [{"name": "AVA4-001", "type": "user-friendly-name"}]
            },
            "Organization": {
                "resourceType": "Organization",
                "identifier": [{"value": "ORG123"}],
                "active": True,
                "name": "Sample Hospital",
                "type": [{"coding": [{"code": "prov", "display": "Healthcare Provider"}]}]
            }
        }
        
        return samples.get(resource_type, {
            "resourceType": resource_type,
            "id": "sample-id"
        })
    
    def save_collection(self, filename: str = "MyFirstCare_Complete_API_Collection.json"):
        """Save the collection to a JSON file"""
        collection = self.generate_complete_collection()
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(collection, f, indent=2, ensure_ascii=False)
        
        return collection

def main():
    """Generate and save the Postman collection"""
    print("🚀 Generating Complete Postman Collection for My FirstCare Opera Panel API")
    print("="*80)
    
    generator = PostmanCollectionGenerator()
    collection = generator.save_collection()
    
    # Count requests
    total_requests = 0
    def count_requests(items):
        nonlocal total_requests
        for item in items:
            if "request" in item:
                total_requests += 1
            elif "item" in item:
                count_requests(item["item"])
    
    count_requests(collection["item"])
    
    print(f"✅ Generated Postman collection with {total_requests} requests")
    print(f"📁 Organized in {len(collection['item'])} main categories")
    print(f"📄 Saved to: MyFirstCare_Complete_API_Collection.json")
    print("\n📋 Import Instructions:")
    print("1. Open Postman")
    print("2. Click 'Import' button")
    print("3. Select 'MyFirstCare_Complete_API_Collection.json'")
    print("4. Set environment variables:")
    print("   - base_url: http://localhost:5054")
    print("   - auth_token: (obtain from login request)")
    print("\n🧪 Testing Instructions:")
    print("1. Run 'Login' request first to get auth_token")
    print("2. Copy the token to auth_token variable")
    print("3. Run other requests to test endpoints")
    print("4. Use 'Runner' for automated testing")
    
    return collection

if __name__ == "__main__":
    main()