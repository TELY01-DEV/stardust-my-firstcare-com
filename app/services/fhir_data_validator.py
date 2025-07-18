"""
FHIR Data Validation Service
Validates medical data integrity, completeness, and correctness in FHIR format
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from app.services.mongo import mongodb_service
from app.services.fhir_r5_service import fhir_service

logger = logging.getLogger(__name__)

class ValidationSeverity(Enum):
    """Validation severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class ValidationResult:
    """Validation result structure"""
    resource_type: str
    resource_id: str
    severity: ValidationSeverity
    field: str
    message: str
    expected_value: Any = None
    actual_value: Any = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

class FHIRDataValidator:
    """Comprehensive FHIR data validation service"""
    
    def __init__(self):
        self.validation_rules = {
            "Patient": self._validate_patient,
            "Observation": self._validate_observation,
            "Device": self._validate_device,
            "Organization": self._validate_organization,
            "Location": self._validate_location,
            "MedicationStatement": self._validate_medication_statement,
            "DiagnosticReport": self._validate_diagnostic_report,
            "DocumentReference": self._validate_document_reference,
            "Goal": self._validate_goal,
            "RelatedPerson": self._validate_related_person,
            "Flag": self._validate_flag,
            "RiskAssessment": self._validate_risk_assessment,
            "ServiceRequest": self._validate_service_request,
            "CarePlan": self._validate_care_plan,
            "Specimen": self._validate_specimen
        }
        
        # Required fields for each resource type
        self.required_fields = {
            "Patient": ["resourceType", "id", "identifier", "name", "gender", "birthDate"],
            "Observation": ["resourceType", "id", "status", "code", "subject", "effectiveDateTime"],
            "Device": ["resourceType", "id", "identifier", "type", "status"],
            "Organization": ["resourceType", "id", "name", "type"],
            "Location": ["resourceType", "id", "name", "status", "type"],
            "MedicationStatement": ["resourceType", "id", "status", "medication", "subject", "effectiveDateTime"],
            "DiagnosticReport": ["resourceType", "id", "status", "code", "subject", "effectiveDateTime"],
            "DocumentReference": ["resourceType", "id", "status", "type", "subject", "date"],
            "Goal": ["resourceType", "id", "lifecycleStatus", "description", "subject"],
            "RelatedPerson": ["resourceType", "id", "patient", "relationship"],
            "Flag": ["resourceType", "id", "status", "code", "subject"],
            "RiskAssessment": ["resourceType", "id", "status", "method", "subject"],
            "ServiceRequest": ["resourceType", "id", "status", "intent", "code", "subject"],
            "CarePlan": ["resourceType", "id", "status", "intent", "subject"],
            "Specimen": ["resourceType", "id", "status", "type", "subject"]
        }
        
        # Value validation rules
        self.value_rules = {
            "Observation": {
                "status": ["registered", "preliminary", "final", "amended", "corrected", "cancelled", "entered-in-error", "unknown"],
                "code.coding.code": {
                    "8867-4": "Heart rate",
                    "85354-9": "Blood pressure panel",
                    "2708-6": "Oxygen saturation",
                    "8310-5": "Body temperature",
                    "41981-2": "Step count"
                }
            },
            "Patient": {
                "gender": ["male", "female", "other", "unknown"]
            },
            "Device": {
                "status": ["active", "inactive", "entered-in-error", "unknown"]
            }
        }
    
    async def validate_resource(self, resource_type: str, resource_data: Dict[str, Any]) -> List[ValidationResult]:
        """Validate a single FHIR resource"""
        results = []
        
        try:
            # Basic structure validation
            results.extend(self._validate_basic_structure(resource_type, resource_data))
            
            # Required fields validation
            results.extend(self._validate_required_fields(resource_type, resource_data))
            
            # Value validation
            results.extend(self._validate_values(resource_type, resource_data))
            
            # Resource-specific validation
            if resource_type in self.validation_rules:
                results.extend(await self.validation_rules[resource_type](resource_data))
            
            # Cross-reference validation
            results.extend(await self._validate_cross_references(resource_type, resource_data))
            
        except Exception as e:
            results.append(ValidationResult(
                resource_type=resource_type,
                resource_id=resource_data.get("id", "unknown"),
                severity=ValidationSeverity.ERROR,
                field="validation_error",
                message=f"Validation error: {str(e)}"
            ))
        
        return results
    
    def _validate_basic_structure(self, resource_type: str, resource_data: Dict[str, Any]) -> List[ValidationResult]:
        """Validate basic FHIR resource structure"""
        results = []
        
        # Check resourceType
        if "resourceType" not in resource_data:
            results.append(ValidationResult(
                resource_type=resource_type,
                resource_id="unknown",
                severity=ValidationSeverity.ERROR,
                field="resourceType",
                message="Missing resourceType field"
            ))
        elif resource_data["resourceType"] != resource_type:
            results.append(ValidationResult(
                resource_type=resource_type,
                resource_id=resource_data.get("id", "unknown"),
                severity=ValidationSeverity.ERROR,
                field="resourceType",
                message=f"ResourceType mismatch: expected {resource_type}, got {resource_data['resourceType']}",
                expected_value=resource_type,
                actual_value=resource_data["resourceType"]
            ))
        
        # Check for required id field
        if "id" not in resource_data:
            results.append(ValidationResult(
                resource_type=resource_type,
                resource_id="unknown",
                severity=ValidationSeverity.ERROR,
                field="id",
                message="Missing id field"
            ))
        
        return results
    
    def _validate_required_fields(self, resource_type: str, resource_data: Dict[str, Any]) -> List[ValidationResult]:
        """Validate required fields for the resource type"""
        results = []
        
        if resource_type not in self.required_fields:
            return results
        
        for field in self.required_fields[resource_type]:
            if not self._field_exists(resource_data, field):
                results.append(ValidationResult(
                    resource_type=resource_type,
                    resource_id=resource_data.get("id", "unknown"),
                    severity=ValidationSeverity.ERROR,
                    field=field,
                    message=f"Missing required field: {field}"
                ))
        
        return results
    
    def _validate_values(self, resource_type: str, resource_data: Dict[str, Any]) -> List[ValidationResult]:
        """Validate field values against expected values"""
        results = []
        
        if resource_type not in self.value_rules:
            return results
        
        for field, expected_values in self.value_rules[resource_type].items():
            actual_value = self._get_field_value(resource_data, field)
            if actual_value is not None:
                if isinstance(expected_values, list):
                    if actual_value not in expected_values:
                        results.append(ValidationResult(
                            resource_type=resource_type,
                            resource_id=resource_data.get("id", "unknown"),
                            severity=ValidationSeverity.WARNING,
                            field=field,
                            message=f"Unexpected value for {field}",
                            expected_value=expected_values,
                            actual_value=actual_value
                        ))
                elif isinstance(expected_values, dict):
                    # For coded values like LOINC codes
                    if actual_value in expected_values:
                        # Valid code found
                        pass
                    else:
                        results.append(ValidationResult(
                            resource_type=resource_type,
                            resource_id=resource_data.get("id", "unknown"),
                            severity=ValidationSeverity.WARNING,
                            field=field,
                            message=f"Unknown code value for {field}",
                            actual_value=actual_value
                        ))
        
        return results
    
    async def _validate_observation(self, observation_data: Dict[str, Any]) -> List[ValidationResult]:
        """Validate Observation-specific rules"""
        results = []
        
        # Validate valueQuantity for numeric observations
        if "valueQuantity" in observation_data:
            value_quantity = observation_data["valueQuantity"]
            if "value" not in value_quantity:
                results.append(ValidationResult(
                    resource_type="Observation",
                    resource_id=observation_data.get("id", "unknown"),
                    severity=ValidationSeverity.ERROR,
                    field="valueQuantity.value",
                    message="Missing value in valueQuantity"
                ))
            elif not isinstance(value_quantity["value"], (int, float)):
                results.append(ValidationResult(
                    resource_type="Observation",
                    resource_id=observation_data.get("id", "unknown"),
                    severity=ValidationSeverity.ERROR,
                    field="valueQuantity.value",
                    message="Value must be numeric",
                    actual_value=value_quantity["value"]
                ))
        
        # Validate component structure for blood pressure
        if "component" in observation_data:
            components = observation_data["component"]
            if not isinstance(components, list):
                results.append(ValidationResult(
                    resource_type="Observation",
                    resource_id=observation_data.get("id", "unknown"),
                    severity=ValidationSeverity.ERROR,
                    field="component",
                    message="Component must be an array"
                ))
            else:
                for i, component in enumerate(components):
                    if "code" not in component:
                        results.append(ValidationResult(
                            resource_type="Observation",
                            resource_id=observation_data.get("id", "unknown"),
                            severity=ValidationSeverity.ERROR,
                            field=f"component[{i}].code",
                            message="Missing code in component"
                        ))
                    if "valueQuantity" not in component:
                        results.append(ValidationResult(
                            resource_type="Observation",
                            resource_id=observation_data.get("id", "unknown"),
                            severity=ValidationSeverity.ERROR,
                            field=f"component[{i}].valueQuantity",
                            message="Missing valueQuantity in component"
                        ))
        
        # Validate effectiveDateTime format
        if "effectiveDateTime" in observation_data:
            try:
                datetime.fromisoformat(observation_data["effectiveDateTime"].replace("Z", "+00:00"))
            except ValueError:
                results.append(ValidationResult(
                    resource_type="Observation",
                    resource_id=observation_data.get("id", "unknown"),
                    severity=ValidationSeverity.ERROR,
                    field="effectiveDateTime",
                    message="Invalid datetime format",
                    actual_value=observation_data["effectiveDateTime"]
                ))
        
        return results
    
    async def _validate_patient(self, patient_data: Dict[str, Any]) -> List[ValidationResult]:
        """Validate Patient-specific rules"""
        results = []
        
        # Validate birthDate format
        if "birthDate" in patient_data:
            try:
                datetime.strptime(patient_data["birthDate"], "%Y-%m-%d")
            except ValueError:
                results.append(ValidationResult(
                    resource_type="Patient",
                    resource_id=patient_data.get("id", "unknown"),
                    severity=ValidationSeverity.ERROR,
                    field="birthDate",
                    message="Invalid birth date format (expected YYYY-MM-DD)",
                    actual_value=patient_data["birthDate"]
                ))
        
        # Validate identifier structure
        if "identifier" in patient_data:
            identifiers = patient_data["identifier"]
            if not isinstance(identifiers, list):
                results.append(ValidationResult(
                    resource_type="Patient",
                    resource_id=patient_data.get("id", "unknown"),
                    severity=ValidationSeverity.ERROR,
                    field="identifier",
                    message="Identifier must be an array"
                ))
            else:
                for i, identifier in enumerate(identifiers):
                    if "system" not in identifier or "value" not in identifier:
                        results.append(ValidationResult(
                            resource_type="Patient",
                            resource_id=patient_data.get("id", "unknown"),
                            severity=ValidationSeverity.ERROR,
                            field=f"identifier[{i}]",
                            message="Identifier must have system and value"
                        ))
        
        return results
    
    async def _validate_device(self, device_data: Dict[str, Any]) -> List[ValidationResult]:
        """Validate Device-specific rules"""
        results = []
        
        # Validate identifier structure
        if "identifier" in device_data:
            identifiers = device_data["identifier"]
            if not isinstance(identifiers, list):
                results.append(ValidationResult(
                    resource_type="Device",
                    resource_id=device_data.get("id", "unknown"),
                    severity=ValidationSeverity.ERROR,
                    field="identifier",
                    message="Identifier must be an array"
                ))
        
        return results
    
    async def _validate_organization(self, organization_data: Dict[str, Any]) -> List[ValidationResult]:
        """Validate Organization-specific rules"""
        results = []
        
        # Validate name
        if "name" in organization_data and not organization_data["name"]:
            results.append(ValidationResult(
                resource_type="Organization",
                resource_id=organization_data.get("id", "unknown"),
                severity=ValidationSeverity.WARNING,
                field="name",
                message="Organization name is empty"
            ))
        
        return results
    
    async def _validate_location(self, location_data: Dict[str, Any]) -> List[ValidationResult]:
        """Validate Location-specific rules"""
        results = []
        
        # Validate position if present
        if "position" in location_data:
            position = location_data["position"]
            if "longitude" not in position or "latitude" not in position:
                results.append(ValidationResult(
                    resource_type="Location",
                    resource_id=location_data.get("id", "unknown"),
                    severity=ValidationSeverity.WARNING,
                    field="position",
                    message="Position should have longitude and latitude"
                ))
        
        return results
    
    async def _validate_medication_statement(self, medication_data: Dict[str, Any]) -> List[ValidationResult]:
        """Validate MedicationStatement-specific rules"""
        results = []
        
        # Validate effectiveDateTime
        if "effectiveDateTime" in medication_data:
            try:
                datetime.fromisoformat(medication_data["effectiveDateTime"].replace("Z", "+00:00"))
            except ValueError:
                results.append(ValidationResult(
                    resource_type="MedicationStatement",
                    resource_id=medication_data.get("id", "unknown"),
                    severity=ValidationSeverity.ERROR,
                    field="effectiveDateTime",
                    message="Invalid datetime format",
                    actual_value=medication_data["effectiveDateTime"]
                ))
        
        return results
    
    async def _validate_diagnostic_report(self, report_data: Dict[str, Any]) -> List[ValidationResult]:
        """Validate DiagnosticReport-specific rules"""
        results = []
        
        # Validate issued date
        if "issued" in report_data:
            try:
                datetime.fromisoformat(report_data["issued"].replace("Z", "+00:00"))
            except ValueError:
                results.append(ValidationResult(
                    resource_type="DiagnosticReport",
                    resource_id=report_data.get("id", "unknown"),
                    severity=ValidationSeverity.ERROR,
                    field="issued",
                    message="Invalid issued date format",
                    actual_value=report_data["issued"]
                ))
        
        return results
    
    async def _validate_document_reference(self, document_data: Dict[str, Any]) -> List[ValidationResult]:
        """Validate DocumentReference-specific rules"""
        results = []
        
        # Validate date
        if "date" in document_data:
            try:
                datetime.fromisoformat(document_data["date"].replace("Z", "+00:00"))
            except ValueError:
                results.append(ValidationResult(
                    resource_type="DocumentReference",
                    resource_id=document_data.get("id", "unknown"),
                    severity=ValidationSeverity.ERROR,
                    field="date",
                    message="Invalid date format",
                    actual_value=document_data["date"]
                ))
        
        return results
    
    async def _validate_goal(self, goal_data: Dict[str, Any]) -> List[ValidationResult]:
        """Validate Goal-specific rules"""
        results = []
        
        # Validate lifecycleStatus
        if "lifecycleStatus" in goal_data:
            valid_statuses = ["proposed", "planned", "accepted", "active", "on-hold", "completed", "cancelled", "entered-in-error", "rejected"]
            if goal_data["lifecycleStatus"] not in valid_statuses:
                results.append(ValidationResult(
                    resource_type="Goal",
                    resource_id=goal_data.get("id", "unknown"),
                    severity=ValidationSeverity.WARNING,
                    field="lifecycleStatus",
                    message="Invalid lifecycle status",
                    expected_value=valid_statuses,
                    actual_value=goal_data["lifecycleStatus"]
                ))
        
        return results
    
    async def _validate_related_person(self, related_person_data: Dict[str, Any]) -> List[ValidationResult]:
        """Validate RelatedPerson-specific rules"""
        results = []
        
        # Validate relationship
        if "relationship" in related_person_data:
            relationship = related_person_data["relationship"]
            if "coding" not in relationship:
                results.append(ValidationResult(
                    resource_type="RelatedPerson",
                    resource_id=related_person_data.get("id", "unknown"),
                    severity=ValidationSeverity.WARNING,
                    field="relationship.coding",
                    message="Relationship should have coding"
                ))
        
        return results
    
    async def _validate_flag(self, flag_data: Dict[str, Any]) -> List[ValidationResult]:
        """Validate Flag-specific rules"""
        results = []
        
        # Validate status
        if "status" in flag_data:
            valid_statuses = ["active", "inactive", "entered-in-error"]
            if flag_data["status"] not in valid_statuses:
                results.append(ValidationResult(
                    resource_type="Flag",
                    resource_id=flag_data.get("id", "unknown"),
                    severity=ValidationSeverity.WARNING,
                    field="status",
                    message="Invalid flag status",
                    expected_value=valid_statuses,
                    actual_value=flag_data["status"]
                ))
        
        return results
    
    async def _validate_risk_assessment(self, risk_data: Dict[str, Any]) -> List[ValidationResult]:
        """Validate RiskAssessment-specific rules"""
        results = []
        
        # Validate status
        if "status" in risk_data:
            valid_statuses = ["registered", "preliminary", "final", "amended", "corrected", "cancelled", "entered-in-error", "unknown"]
            if risk_data["status"] not in valid_statuses:
                results.append(ValidationResult(
                    resource_type="RiskAssessment",
                    resource_id=risk_data.get("id", "unknown"),
                    severity=ValidationSeverity.WARNING,
                    field="status",
                    message="Invalid risk assessment status",
                    expected_value=valid_statuses,
                    actual_value=risk_data["status"]
                ))
        
        return results
    
    async def _validate_service_request(self, request_data: Dict[str, Any]) -> List[ValidationResult]:
        """Validate ServiceRequest-specific rules"""
        results = []
        
        # Validate intent
        if "intent" in request_data:
            valid_intents = ["proposal", "plan", "directive", "order", "original-order", "reflex-order", "filler-order", "instance-order", "option"]
            if request_data["intent"] not in valid_intents:
                results.append(ValidationResult(
                    resource_type="ServiceRequest",
                    resource_id=request_data.get("id", "unknown"),
                    severity=ValidationSeverity.WARNING,
                    field="intent",
                    message="Invalid service request intent",
                    expected_value=valid_intents,
                    actual_value=request_data["intent"]
                ))
        
        return results
    
    async def _validate_care_plan(self, care_plan_data: Dict[str, Any]) -> List[ValidationResult]:
        """Validate CarePlan-specific rules"""
        results = []
        
        # Validate status
        if "status" in care_plan_data:
            valid_statuses = ["draft", "active", "suspended", "completed", "entered-in-error", "cancelled", "unknown"]
            if care_plan_data["status"] not in valid_statuses:
                results.append(ValidationResult(
                    resource_type="CarePlan",
                    resource_id=care_plan_data.get("id", "unknown"),
                    severity=ValidationSeverity.WARNING,
                    field="status",
                    message="Invalid care plan status",
                    expected_value=valid_statuses,
                    actual_value=care_plan_data["status"]
                ))
        
        return results
    
    async def _validate_specimen(self, specimen_data: Dict[str, Any]) -> List[ValidationResult]:
        """Validate Specimen-specific rules"""
        results = []
        
        # Validate status
        if "status" in specimen_data:
            valid_statuses = ["available", "unavailable", "unsatisfactory", "entered-in-error"]
            if specimen_data["status"] not in valid_statuses:
                results.append(ValidationResult(
                    resource_type="Specimen",
                    resource_id=specimen_data.get("id", "unknown"),
                    severity=ValidationSeverity.WARNING,
                    field="status",
                    message="Invalid specimen status",
                    expected_value=valid_statuses,
                    actual_value=specimen_data["status"]
                ))
        
        return results
    
    async def _validate_cross_references(self, resource_type: str, resource_data: Dict[str, Any]) -> List[ValidationResult]:
        """Validate cross-references between resources"""
        results = []
        
        # Validate subject reference
        if "subject" in resource_data:
            subject_ref = resource_data["subject"]["reference"]
            if not subject_ref.startswith("Patient/"):
                results.append(ValidationResult(
                    resource_type=resource_type,
                    resource_id=resource_data.get("id", "unknown"),
                    severity=ValidationSeverity.WARNING,
                    field="subject.reference",
                    message="Subject reference should point to a Patient",
                    actual_value=subject_ref
                ))
        
        # Validate device reference
        if "device" in resource_data:
            device_ref = resource_data["device"]["reference"]
            if not device_ref.startswith("Device/"):
                results.append(ValidationResult(
                    resource_type=resource_type,
                    resource_id=resource_data.get("id", "unknown"),
                    severity=ValidationSeverity.WARNING,
                    field="device.reference",
                    message="Device reference should point to a Device",
                    actual_value=device_ref
                ))
        
        return results
    
    def _field_exists(self, data: Dict[str, Any], field_path: str) -> bool:
        """Check if a field exists in nested dictionary"""
        keys = field_path.split(".")
        current = data
        
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return False
        
        return True
    
    def _get_field_value(self, data: Dict[str, Any], field_path: str) -> Any:
        """Get field value from nested dictionary"""
        keys = field_path.split(".")
        current = data
        
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        
        return current
    
    async def validate_all_resources(self, resource_type: Optional[str] = None, 
                                   limit: int = 100) -> Dict[str, List[ValidationResult]]:
        """Validate all resources of a specific type or all types"""
        await mongodb_service.connect()
        db = mongodb_service.get_database('MFC_FHIR_R5')
        
        results = {}
        
        if resource_type:
            collections = [resource_type]
        else:
            collections = self.validation_rules.keys()
        
        for collection_name in collections:
            try:
                collection = db.get_collection(collection_name)
                cursor = collection.find({}).limit(limit)
                
                collection_results = []
                async for resource in cursor:
                    resource_results = await self.validate_resource(collection_name, resource)
                    collection_results.extend(resource_results)
                
                results[collection_name] = collection_results
                
            except Exception as e:
                logger.error(f"Error validating {collection_name}: {e}")
                results[collection_name] = [ValidationResult(
                    resource_type=collection_name,
                    resource_id="unknown",
                    severity=ValidationSeverity.ERROR,
                    field="validation_error",
                    message=f"Collection validation error: {str(e)}"
                )]
        
        return results
    
    async def generate_validation_report(self, results: Dict[str, List[ValidationResult]]) -> Dict[str, Any]:
        """Generate a comprehensive validation report"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_resources": 0,
                "total_errors": 0,
                "total_warnings": 0,
                "total_info": 0,
                "total_critical": 0
            },
            "by_resource_type": {},
            "by_severity": {
                "critical": [],
                "error": [],
                "warning": [],
                "info": []
            },
            "recommendations": []
        }
        
        for resource_type, validation_results in results.items():
            resource_summary = {
                "total": len(validation_results),
                "errors": len([r for r in validation_results if r.severity == ValidationSeverity.ERROR]),
                "warnings": len([r for r in validation_results if r.severity == ValidationSeverity.WARNING]),
                "info": len([r for r in validation_results if r.severity == ValidationSeverity.INFO]),
                "critical": len([r for r in validation_results if r.severity == ValidationSeverity.CRITICAL])
            }
            
            report["by_resource_type"][resource_type] = resource_summary
            report["summary"]["total_resources"] += resource_summary["total"]
            report["summary"]["total_errors"] += resource_summary["errors"]
            report["summary"]["total_warnings"] += resource_summary["warnings"]
            report["summary"]["total_info"] += resource_summary["info"]
            report["summary"]["total_critical"] += resource_summary["critical"]
            
            # Group by severity
            for result in validation_results:
                report["by_severity"][result.severity.value].append({
                    "resource_type": result.resource_type,
                    "resource_id": result.resource_id,
                    "field": result.field,
                    "message": result.message,
                    "expected_value": result.expected_value,
                    "actual_value": result.actual_value
                })
        
        # Generate recommendations
        if report["summary"]["total_critical"] > 0:
            report["recommendations"].append("Critical issues found - immediate attention required")
        
        if report["summary"]["total_errors"] > 0:
            report["recommendations"].append("Data integrity errors detected - review and fix required")
        
        if report["summary"]["total_warnings"] > 0:
            report["recommendations"].append("Data quality warnings - consider improvements")
        
        if report["summary"]["total_errors"] == 0 and report["summary"]["total_critical"] == 0:
            report["recommendations"].append("All data appears to be valid")
        
        return report

# Global validator instance
fhir_validator = FHIRDataValidator() 