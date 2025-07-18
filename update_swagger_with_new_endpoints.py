#!/usr/bin/env python3
"""
Safe Swagger/OpenAPI Documentation Updater
==========================================

This script safely updates your OpenAPI specification by:
1. Reading your existing spec file
2. Adding new endpoints from your code
3. Creating a new spec file with everything combined
4. Showing you a diff of what's new

Usage:
    python update_swagger_with_new_endpoints.py

Features:
- Safe: Never modifies existing endpoints
- Backup: Creates backup of current spec
- Diff: Shows what's being added
- Validation: Validates the final spec
"""

import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional
import re

class SwaggerUpdater:
    def __init__(self, existing_spec_path: str = "current_openapi.json"):
        self.existing_spec_path = existing_spec_path
        self.backup_path = f"{existing_spec_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.new_spec_path = f"updated_openapi_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
    def backup_existing_spec(self) -> bool:
        """Create a backup of the existing spec file."""
        try:
            if os.path.exists(self.existing_spec_path):
                with open(self.existing_spec_path, 'r', encoding='utf-8') as f:
                    existing_spec = json.load(f)
                
                with open(self.backup_path, 'w', encoding='utf-8') as f:
                    json.dump(existing_spec, f, indent=2, ensure_ascii=False)
                
                print(f"✅ Backup created: {self.backup_path}")
                return True
            else:
                print(f"⚠️  Existing spec file not found: {self.existing_spec_path}")
                return False
        except Exception as e:
            print(f"❌ Error creating backup: {e}")
            return False
    
    def load_existing_spec(self) -> Dict[str, Any]:
        """Load the existing OpenAPI specification."""
        try:
            if os.path.exists(self.existing_spec_path):
                with open(self.existing_spec_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                # Create a minimal spec if none exists
                return {
                    "openapi": "3.1.0",
                    "info": {
                        "title": "My FirstCare Opera Panel",
                        "description": "Updated API with new endpoints",
                        "version": "1.0.0"
                    },
                    "paths": {},
                    "components": {
                        "schemas": {},
                        "securitySchemes": {
                            "HTTPBearer": {
                                "type": "http",
                                "scheme": "bearer"
                            }
                        }
                    }
                }
        except Exception as e:
            print(f"❌ Error loading existing spec: {e}")
            return {}
    
    def get_new_endpoints(self) -> Dict[str, Any]:
        """Define new endpoints to add to the specification."""
        new_endpoints = {
            # MQTT Monitor Web Panel Endpoints
            "/api/recent-medical-data": {
                "get": {
                    "tags": ["medical-monitor"],
                    "summary": "Get Recent Medical Data",
                    "description": "Get recent medical data from the medical_data collection with AP55 batch vital signs support",
                    "operationId": "get_recent_medical_data",
                    "security": [{"HTTPBearer": []}],
                    "parameters": [
                        {
                            "name": "limit",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "integer", "default": 100, "maximum": 1000},
                            "description": "Number of records to return"
                        },
                        {
                            "name": "device_id",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "string"},
                            "description": "Filter by device ID"
                        },
                        {
                            "name": "patient_id",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "string"},
                            "description": "Filter by patient ID"
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Recent medical data retrieved successfully",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "success": {"type": "boolean"},
                                            "data": {
                                                "type": "object",
                                                "properties": {
                                                    "recent_medical_data": {
                                                        "type": "array",
                                                        "items": {
                                                            "type": "object",
                                                            "properties": {
                                                                "device_id": {"type": "string"},
                                                                "patient_name": {"type": "string"},
                                                                "medical_values": {"type": "object"},
                                                                "batch_data": {"type": "array"},
                                                                "batch_count": {"type": "integer"},
                                                                "data_type": {"type": "string"}
                                                            }
                                                        }
                                                    },
                                                    "total_count": {"type": "integer"},
                                                    "last_updated": {"type": "string"}
                                                }
                                            }
                                        }
                                    },
                                    "example": {
                                        "success": True,
                                        "data": {
                                            "recent_medical_data": [
                                                {
                                                    "device_id": "861265061481799",
                                                    "patient_name": "Adisak Inthanomkit",
                                                    "medical_values": {
                                                        "heart_rate": 80,
                                                        "systolic": 118,
                                                        "diastolic": 77,
                                                        "spO2": 97,
                                                        "temperature": 36.8,
                                                        "battery": 92,
                                                        "signal_gsm": 80,
                                                        "steps": 5080
                                                    },
                                                    "batch_data": [
                                                        {
                                                            "heartRate": 80,
                                                            "bloodPressure": {"bp_sys": 118, "bp_dia": 77},
                                                            "spO2": 97,
                                                            "bodyTemperature": 36.8,
                                                            "timestamp": 1752787955
                                                        }
                                                    ],
                                                    "batch_count": 2,
                                                    "data_type": "batch_vital_signs"
                                                }
                                            ],
                                            "total_count": 100,
                                            "last_updated": "2025-07-17T15:30:00Z"
                                        }
                                    }
                                }
                            }
                        },
                        "401": {"description": "Authentication required"},
                        "500": {"description": "Internal server error"}
                    }
                }
            },
            
            "/api/data-flow/events": {
                "get": {
                    "tags": ["data-flow"],
                    "summary": "Get Data Flow Events",
                    "description": "Get data flow events for monitoring system performance",
                    "operationId": "get_data_flow_events",
                    "security": [{"HTTPBearer": []}],
                    "parameters": [
                        {
                            "name": "limit",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "integer", "default": 100},
                            "description": "Number of events to return"
                        }
                    ],
                    "responses": {
                        "200": {"description": "Data flow events retrieved successfully"},
                        "401": {"description": "Authentication required"}
                    }
                }
            },
            
            "/api/data-flow/emit": {
                "post": {
                    "tags": ["data-flow"],
                    "summary": "Emit Data Flow Event",
                    "description": "Emit a new data flow event for monitoring",
                    "operationId": "emit_data_flow_event",
                    "security": [{"HTTPBearer": []}],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "step": {"type": "string"},
                                        "status": {"type": "string"},
                                        "device_type": {"type": "string"},
                                        "topic": {"type": "string"},
                                        "payload": {"type": "object"}
                                    }
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {"description": "Event emitted successfully"},
                        "401": {"description": "Authentication required"}
                    }
                }
            },
            
            "/api/emergency-alerts": {
                "get": {
                    "tags": ["emergency"],
                    "summary": "Get Emergency Alerts",
                    "description": "Get emergency alerts and notifications",
                    "operationId": "get_emergency_alerts",
                    "security": [{"HTTPBearer": []}],
                    "parameters": [
                        {
                            "name": "limit",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "integer", "default": 50},
                            "description": "Number of alerts to return"
                        },
                        {
                            "name": "status",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "string", "enum": ["active", "processed", "all"]},
                            "description": "Filter by alert status"
                        }
                    ],
                    "responses": {
                        "200": {"description": "Emergency alerts retrieved successfully"},
                        "401": {"description": "Authentication required"}
                    }
                }
            },
            
            "/api/emergency-stats": {
                "get": {
                    "tags": ["emergency"],
                    "summary": "Get Emergency Statistics",
                    "description": "Get emergency alert statistics and metrics",
                    "operationId": "get_emergency_stats",
                    "security": [{"HTTPBearer": []}],
                    "responses": {
                        "200": {"description": "Emergency statistics retrieved successfully"},
                        "401": {"description": "Authentication required"}
                    }
                }
            },
            
            "/api/mark-processed/{alert_id}": {
                "post": {
                    "tags": ["emergency"],
                    "summary": "Mark Alert as Processed",
                    "description": "Mark an emergency alert as processed",
                    "operationId": "mark_alert_processed",
                    "security": [{"HTTPBearer": []}],
                    "parameters": [
                        {
                            "name": "alert_id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                            "description": "Alert ID to mark as processed"
                        }
                    ],
                    "responses": {
                        "200": {"description": "Alert marked as processed successfully"},
                        "404": {"description": "Alert not found"},
                        "401": {"description": "Authentication required"}
                    }
                }
            },
            
            "/api/event-log": {
                "get": {
                    "tags": ["event-log"],
                    "summary": "Get Event Logs",
                    "description": "Get system event logs with filtering and pagination",
                    "operationId": "get_event_logs",
                    "security": [{"HTTPBearer": []}],
                    "parameters": [
                        {
                            "name": "limit",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "integer", "default": 100},
                            "description": "Number of logs to return"
                        },
                        {
                            "name": "skip",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "integer", "default": 0},
                            "description": "Number of logs to skip"
                        },
                        {
                            "name": "event_type",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "string"},
                            "description": "Filter by event type"
                        }
                    ],
                    "responses": {
                        "200": {"description": "Event logs retrieved successfully"},
                        "401": {"description": "Authentication required"}
                    }
                },
                "post": {
                    "tags": ["event-log"],
                    "summary": "Add Event Log",
                    "description": "Add a new event log entry",
                    "operationId": "add_event_log",
                    "security": [{"HTTPBearer": []}],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "event_type": {"type": "string"},
                                        "message": {"type": "string"},
                                        "data": {"type": "object"}
                                    }
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {"description": "Event log added successfully"},
                        "401": {"description": "Authentication required"}
                    }
                }
            },
            
            "/api/streaming/events": {
                "get": {
                    "tags": ["streaming"],
                    "summary": "Get Streaming Events",
                    "description": "Get real-time streaming events",
                    "operationId": "get_streaming_events",
                    "security": [{"HTTPBearer": []}],
                    "parameters": [
                        {
                            "name": "limit",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "integer", "default": 100},
                            "description": "Number of events to return"
                        }
                    ],
                    "responses": {
                        "200": {"description": "Streaming events retrieved successfully"},
                        "401": {"description": "Authentication required"}
                    }
                }
            },
            
            "/api/redis/events": {
                "get": {
                    "tags": ["redis"],
                    "summary": "Get Redis Events",
                    "description": "Get Redis event cache data",
                    "operationId": "get_redis_events",
                    "security": [{"HTTPBearer": []}],
                    "parameters": [
                        {
                            "name": "limit",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "integer", "default": 100},
                            "description": "Number of events to return"
                        }
                    ],
                    "responses": {
                        "200": {"description": "Redis events retrieved successfully"},
                        "401": {"description": "Authentication required"}
                    }
                }
            },
            
            "/api/redis/stats": {
                "get": {
                    "tags": ["redis"],
                    "summary": "Get Redis Statistics",
                    "description": "Get Redis cache statistics and metrics",
                    "operationId": "get_redis_stats",
                    "security": [{"HTTPBearer": []}],
                    "responses": {
                        "200": {"description": "Redis statistics retrieved successfully"},
                        "401": {"description": "Authentication required"}
                    }
                }
            },
            
            "/api/ava4-status": {
                "get": {
                    "tags": ["ava4-status"],
                    "summary": "Get AVA4 Device Status",
                    "description": "Get status of all AVA4 devices",
                    "operationId": "get_ava4_status",
                    "security": [{"HTTPBearer": []}],
                    "responses": {
                        "200": {"description": "AVA4 status retrieved successfully"},
                        "401": {"description": "Authentication required"}
                    }
                }
            },
            
            "/api/ava4-status/{ava4_mac}": {
                "get": {
                    "tags": ["ava4-status"],
                    "summary": "Get Specific AVA4 Device Status",
                    "description": "Get status for a specific AVA4 device by MAC address",
                    "operationId": "get_ava4_device_status",
                    "security": [{"HTTPBearer": []}],
                    "parameters": [
                        {
                            "name": "ava4_mac",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                            "description": "AVA4 device MAC address"
                        }
                    ],
                    "responses": {
                        "200": {"description": "AVA4 device status retrieved successfully"},
                        "404": {"description": "Device not found"},
                        "401": {"description": "Authentication required"}
                    }
                }
            }
        }
        
        return new_endpoints
    
    def merge_endpoints(self, existing_spec: Dict[str, Any], new_endpoints: Dict[str, Any]) -> Dict[str, Any]:
        """Merge new endpoints into existing specification."""
        merged_spec = existing_spec.copy()
        
        # Ensure paths exist
        if "paths" not in merged_spec:
            merged_spec["paths"] = {}
        
        # Add new endpoints
        added_count = 0
        for path, methods in new_endpoints.items():
            if path not in merged_spec["paths"]:
                merged_spec["paths"][path] = {}
                added_count += 1
            
            for method, definition in methods.items():
                if method not in merged_spec["paths"][path]:
                    merged_spec["paths"][path][method] = definition
                    added_count += 1
                else:
                    print(f"⚠️  Endpoint already exists: {method.upper()} {path}")
        
        print(f"✅ Added {added_count} new endpoint definitions")
        return merged_spec
    
    def validate_spec(self, spec: Dict[str, Any]) -> bool:
        """Basic validation of the OpenAPI specification."""
        try:
            required_fields = ["openapi", "info", "paths"]
            for field in required_fields:
                if field not in spec:
                    print(f"❌ Missing required field: {field}")
                    return False
            
            if not isinstance(spec["paths"], dict):
                print("❌ Paths must be an object")
                return False
            
            print("✅ OpenAPI specification validation passed")
            return True
        except Exception as e:
            print(f"❌ Validation error: {e}")
            return False
    
    def save_spec(self, spec: Dict[str, Any], filename: str) -> bool:
        """Save the specification to a file."""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(spec, f, indent=2, ensure_ascii=False)
            print(f"✅ Specification saved to: {filename}")
            return True
        except Exception as e:
            print(f"❌ Error saving specification: {e}")
            return False
    
    def show_diff(self, existing_spec: Dict[str, Any], new_spec: Dict[str, Any]) -> None:
        """Show a summary of what's new in the specification."""
        existing_paths = set(existing_spec.get("paths", {}).keys())
        new_paths = set(new_spec.get("paths", {}).keys())
        
        added_paths = new_paths - existing_paths
        
        print("\n📋 SUMMARY OF CHANGES:")
        print("=" * 50)
        
        if added_paths:
            print(f"✅ Added {len(added_paths)} new endpoints:")
            for path in sorted(added_paths):
                methods = list(new_spec["paths"][path].keys())
                print(f"   • {', '.join(methods.upper())} {path}")
        else:
            print("ℹ️  No new endpoints added")
        
        print(f"\n📊 Total endpoints: {len(new_paths)}")
        print(f"📊 New endpoints: {len(added_paths)}")
        print("=" * 50)
    
    def run(self) -> bool:
        """Run the complete update process."""
        print("🚀 Starting Swagger/OpenAPI Documentation Update")
        print("=" * 60)
        
        # Step 1: Backup existing spec
        print("\n1️⃣ Creating backup...")
        self.backup_existing_spec()
        
        # Step 2: Load existing spec
        print("\n2️⃣ Loading existing specification...")
        existing_spec = self.load_existing_spec()
        if not existing_spec:
            print("❌ Failed to load existing specification")
            return False
        
        # Step 3: Get new endpoints
        print("\n3️⃣ Getting new endpoint definitions...")
        new_endpoints = self.get_new_endpoints()
        
        # Step 4: Merge endpoints
        print("\n4️⃣ Merging new endpoints...")
        updated_spec = self.merge_endpoints(existing_spec, new_endpoints)
        
        # Step 5: Validate spec
        print("\n5️⃣ Validating specification...")
        if not self.validate_spec(updated_spec):
            return False
        
        # Step 6: Show diff
        print("\n6️⃣ Analyzing changes...")
        self.show_diff(existing_spec, updated_spec)
        
        # Step 7: Save new spec
        print("\n7️⃣ Saving updated specification...")
        if not self.save_spec(updated_spec, self.new_spec_path):
            return False
        
        print("\n🎉 Update completed successfully!")
        print(f"📁 New specification: {self.new_spec_path}")
        print(f"📁 Backup created: {self.backup_path}")
        print("\n💡 Next steps:")
        print("   1. Review the new specification")
        print("   2. Test the endpoints")
        print("   3. Replace current_openapi.json if satisfied")
        
        return True

def main():
    """Main function to run the Swagger updater."""
    updater = SwaggerUpdater()
    
    try:
        success = updater.run()
        if success:
            print("\n✅ Swagger documentation updated successfully!")
            sys.exit(0)
        else:
            print("\n❌ Failed to update Swagger documentation")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Update cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 