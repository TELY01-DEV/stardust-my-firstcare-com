"""
FHIR R5 Service Layer
====================
Service layer for FHIR R5 resource management, data transformation,
and integration with existing medical history collections.

Transforms AVA4 MQTT data and existing medical records into FHIR R5 format.
"""

import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union, Tuple
from bson import ObjectId
from pymongo import ASCENDING, DESCENDING

from app.services.mongo import mongodb_service
from app.services.blockchain_hash import blockchain_hash_service, BlockchainHash, HashVerificationResult
from app.models.fhir_r5 import (
    FHIRResourceDocument, Patient, Observation, Device, Organization,
    Location, Condition, Medication, AllergyIntolerance, Encounter,
    Provenance, Bundle, FHIRSearchParams, FHIRSearchResponse,
    Identifier, CodeableConcept, Quantity, Reference, HumanName,
    ContactPoint, Address, Period, ObservationComponent
)
from app.utils.structured_logging import get_logger

logger = get_logger(__name__)

class FHIRR5Service:
    """Service for FHIR R5 resource management and data transformation"""
    
    def __init__(self):
        self.fhir_version = "5.0.0"
        
        # FHIR R5 collection mappings
        self.fhir_collections = {
            "Patient": "fhir_patients",
            "Observation": "fhir_observations", 
            "Device": "fhir_devices",
            "Organization": "fhir_organizations",
            "Location": "fhir_locations",
            "Condition": "fhir_conditions",
            "Medication": "fhir_medications",
            "AllergyIntolerance": "fhir_allergies",
            "Encounter": "fhir_encounters",
            "MedicationStatement": "fhir_medication_statements",
            "DiagnosticReport": "fhir_diagnostic_reports",
            "DocumentReference": "fhir_documents",
            "Provenance": "fhir_provenance",
            "Goal": "fhir_goals",
            "RelatedPerson": "fhir_related_persons",
            "Flag": "fhir_flags",
            "RiskAssessment": "fhir_risk_assessments",
            "ServiceRequest": "fhir_service_requests",
            "CarePlan": "fhir_care_plans",
            "Specimen": "fhir_specimens"
        }
        
        # Medical device type mappings for LOINC codes
        self.device_loinc_mappings = {
            "blood_pressure": {
                "systolic": "8480-6",  # Systolic blood pressure
                "diastolic": "8462-4", # Diastolic blood pressure  
                "pulse": "8867-4"      # Heart rate
            },
            "blood_glucose": {
                "glucose": "33747-0"   # Blood glucose
            },
            "temperature": {
                "body_temp": "8310-5"  # Body temperature
            },
            "spo2": {
                "oxygen_sat": "59408-5", # Oxygen saturation
                "pulse_rate": "8867-4"   # Heart rate
            },
            "weight": {
                "body_weight": "29463-7" # Body weight
            },
            "cholesterol": {
                "total_chol": "2093-3"   # Cholesterol total
            },
            "uric_acid": {
                "uric_acid": "3084-1"    # Uric acid
            }
        }

    # =============== Core FHIR Resource Operations ===============

    async def create_fhir_resource(
        self, 
        resource_type: str, 
        resource_data: Dict[str, Any],
        source_system: str = "manual",
        device_mac_address: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new FHIR resource with blockchain hash"""
        try:
            # Validate resource type
            if resource_type not in self.fhir_collections:
                raise ValueError(f"Unsupported FHIR resource type: {resource_type}")
            
            # Generate FHIR resource ID if not provided
            if "id" not in resource_data:
                resource_data["id"] = str(uuid.uuid4())
            
            # Ensure resourceType is set
            resource_data["resourceType"] = resource_type
            
            # Add FHIR metadata
            resource_data["meta"] = {
                "versionId": "1",
                "lastUpdated": datetime.utcnow().isoformat() + "Z",
                "source": source_system,
                "profile": [f"http://hl7.org/fhir/StructureDefinition/{resource_type}"]
            }
            
            # Generate blockchain hash for the resource
            blockchain_hash_obj = blockchain_hash_service.generate_resource_hash(
                resource_data=resource_data,
                include_merkle=True
            )
            
            # Add blockchain metadata to FHIR resource
            resource_data["meta"]["blockchain_hash"] = blockchain_hash_obj.resource_hash
            resource_data["meta"]["blockchain_timestamp"] = blockchain_hash_obj.timestamp
            resource_data["meta"]["blockchain_nonce"] = blockchain_hash_obj.nonce
            resource_data["meta"]["blockchain_block_height"] = blockchain_hash_obj.block_height
            
            # Create MongoDB document
            fhir_doc = FHIRResourceDocument(
                resource_type=resource_type,
                resource_id=resource_data["id"],
                fhir_version=self.fhir_version,
                resource_data=resource_data,
                source_system=source_system,
                device_mac_address=device_mac_address,
                recorded_datetime=datetime.utcnow(),
                # Blockchain fields
                blockchain_hash=blockchain_hash_obj.resource_hash,
                blockchain_previous_hash=blockchain_hash_obj.previous_hash,
                blockchain_timestamp=blockchain_hash_obj.timestamp,
                blockchain_nonce=blockchain_hash_obj.nonce,
                blockchain_merkle_root=blockchain_hash_obj.merkle_root,
                blockchain_block_height=blockchain_hash_obj.block_height,
                blockchain_signature=blockchain_hash_obj.signature,
                blockchain_verified=True,
                blockchain_verification_date=datetime.utcnow()
            )
            
            # Extract references for indexing
            await self._extract_references(fhir_doc, resource_data)
            
            # Store in appropriate FHIR collection
            collection = mongodb_service.get_fhir_collection(self.fhir_collections[resource_type])
            result = await collection.insert_one(fhir_doc.dict(by_alias=True))
            
            logger.info(f"Created FHIR {resource_type} resource: {resource_data['id']} with blockchain hash: {blockchain_hash_obj.resource_hash[:16]}...")
            
            return {
                "success": True,
                "resource_id": resource_data["id"],
                "mongo_id": str(result.inserted_id),
                "resource": resource_data,
                "blockchain_hash": blockchain_hash_obj.resource_hash,
                "blockchain_metadata": {
                    "hash": blockchain_hash_obj.resource_hash,
                    "previous_hash": blockchain_hash_obj.previous_hash,
                    "timestamp": blockchain_hash_obj.timestamp,
                    "block_height": blockchain_hash_obj.block_height,
                    "merkle_root": blockchain_hash_obj.merkle_root
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to create FHIR {resource_type}: {e}")
            raise

    async def get_fhir_resource(
        self, 
        resource_type: str, 
        resource_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get a FHIR resource by ID"""
        try:
            collection = mongodb_service.get_fhir_collection(self.fhir_collections[resource_type])
            doc = await collection.find_one({
                "resource_id": resource_id,
                "is_deleted": False
            })
            
            if doc:
                return doc["resource_data"]
            return None
            
        except Exception as e:
            logger.error(f"Failed to get FHIR {resource_type} {resource_id}: {e}")
            raise

    async def update_fhir_resource(
        self, 
        resource_type: str, 
        resource_id: str, 
        resource_data: Dict[str, Any],
        source_system: str = "manual"
    ) -> Dict[str, Any]:
        """Update a FHIR resource with new blockchain hash"""
        try:
            collection = mongodb_service.get_fhir_collection(self.fhir_collections[resource_type])
            
            # Update metadata
            resource_data["id"] = resource_id
            resource_data["resourceType"] = resource_type
            
            current_doc = await collection.find_one({"resource_id": resource_id})
            if not current_doc:
                raise ValueError(f"FHIR {resource_type} {resource_id} not found")
            
            # Increment version
            current_version = int(current_doc["resource_data"].get("meta", {}).get("versionId", "1"))
            new_version = current_version + 1
            
            resource_data["meta"] = {
                "versionId": str(new_version),
                "lastUpdated": datetime.utcnow().isoformat() + "Z",
                "source": source_system,
                "profile": [f"http://hl7.org/fhir/StructureDefinition/{resource_type}"]
            }
            
            # Generate new blockchain hash for the updated resource
            previous_hash = current_doc.get("blockchain_hash")
            blockchain_hash_obj = blockchain_hash_service.generate_resource_hash(
                resource_data=resource_data,
                previous_hash=previous_hash,
                include_merkle=True
            )
            
            # Add blockchain metadata to FHIR resource
            resource_data["meta"]["blockchain_hash"] = blockchain_hash_obj.resource_hash
            resource_data["meta"]["blockchain_timestamp"] = blockchain_hash_obj.timestamp
            resource_data["meta"]["blockchain_nonce"] = blockchain_hash_obj.nonce
            resource_data["meta"]["blockchain_block_height"] = blockchain_hash_obj.block_height
            resource_data["meta"]["blockchain_previous_hash"] = blockchain_hash_obj.previous_hash
            
            # Update document
            update_data = {
                "resource_data": resource_data,
                "updated_at": datetime.utcnow(),
                # Update blockchain fields
                "blockchain_hash": blockchain_hash_obj.resource_hash,
                "blockchain_previous_hash": blockchain_hash_obj.previous_hash,
                "blockchain_timestamp": blockchain_hash_obj.timestamp,
                "blockchain_nonce": blockchain_hash_obj.nonce,
                "blockchain_merkle_root": blockchain_hash_obj.merkle_root,
                "blockchain_block_height": blockchain_hash_obj.block_height,
                "blockchain_signature": blockchain_hash_obj.signature,
                "blockchain_verified": True,
                "blockchain_verification_date": datetime.utcnow()
            }
            
            result = await collection.update_one(
                {"resource_id": resource_id},
                {"$set": update_data}
            )
            
            if result.modified_count == 0:
                raise ValueError(f"Failed to update FHIR {resource_type} {resource_id}")
            
            logger.info(f"Updated FHIR {resource_type} resource: {resource_id} with new blockchain hash: {blockchain_hash_obj.resource_hash[:16]}...")
            
            return {
                "success": True,
                "resource_id": resource_id,
                "resource": resource_data,
                "blockchain_hash": blockchain_hash_obj.resource_hash,
                "blockchain_metadata": {
                    "hash": blockchain_hash_obj.resource_hash,
                    "previous_hash": blockchain_hash_obj.previous_hash,
                    "timestamp": blockchain_hash_obj.timestamp,
                    "block_height": blockchain_hash_obj.block_height,
                    "merkle_root": blockchain_hash_obj.merkle_root
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to update FHIR {resource_type} {resource_id}: {e}")
            raise

    async def delete_fhir_resource(
        self, 
        resource_type: str, 
        resource_id: str
    ) -> Dict[str, Any]:
        """Soft delete a FHIR resource"""
        try:
            collection = mongodb_service.get_fhir_collection(self.fhir_collections[resource_type])
            
            result = await collection.update_one(
                {"resource_id": resource_id},
                {
                    "$set": {
                        "is_deleted": True,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            if result.modified_count == 0:
                raise ValueError(f"FHIR {resource_type} {resource_id} not found")
            
            logger.info(f"Deleted FHIR {resource_type} resource: {resource_id}")
            
            return {
                "success": True,
                "resource_id": resource_id
            }
            
        except Exception as e:
            logger.error(f"Failed to delete FHIR {resource_type} {resource_id}: {e}")
            raise

    async def search_fhir_resources(
        self,
        resource_type: str,
        search_params: FHIRSearchParams
    ) -> FHIRSearchResponse:
        """Search FHIR resources with standard parameters"""
        try:
            collection = mongodb_service.get_fhir_collection(self.fhir_collections[resource_type])
            
            # Build MongoDB query
            query = {"is_deleted": False}
            
            # Add search filters
            if search_params._id:
                query["resource_id"] = search_params._id
            
            if search_params.patient:
                query["patient_id"] = search_params.patient
                
            if search_params.status:
                query["status"] = search_params.status
                
            if search_params.identifier:
                query["resource_data.identifier.value"] = search_params.identifier
            
            # Date range search
            if search_params.date:
                date_filter = self._parse_date_range(search_params.date)
                if date_filter:
                    query["effective_datetime"] = date_filter
            
            # Count total results
            total = await collection.count_documents(query)
            
            # Apply pagination and sorting
            cursor = collection.find(query)
            
            if search_params._sort:
                sort_spec = self._parse_sort_spec(search_params._sort)
                cursor = cursor.sort(sort_spec)
            else:
                cursor = cursor.sort("recorded_datetime", DESCENDING)
            
            cursor = cursor.skip(search_params._offset).limit(search_params._count)
            
            # Get results
            docs = await cursor.to_list(length=search_params._count)
            
            # Format as FHIR Bundle entries
            entries = []
            for doc in docs:
                entries.append({
                    "fullUrl": f"/{resource_type}/{doc['resource_id']}",
                    "resource": doc["resource_data"],
                    "search": {
                        "mode": "match"
                    }
                })
            
            # Build navigation links
            links = self._build_search_links(resource_type, search_params, total)
            
            return FHIRSearchResponse(
                total=total,
                entry=entries,
                link=links
            )
            
        except Exception as e:
            logger.error(f"Failed to search FHIR {resource_type}: {e}")
            raise

    # =============== AVA4 MQTT Data Transformation ===============

    async def transform_ava4_mqtt_to_fhir(
        self, 
        mqtt_payload: Dict[str, Any],
        patient_id: str,
        device_id: str
    ) -> List[Dict[str, Any]]:
        """Transform AVA4 MQTT payload to FHIR R5 Observations"""
        try:
            observations = []
            
            # Extract data from MQTT payload
            device_data = mqtt_payload.get("data", {})
            attribute = device_data.get("attribute", "")
            value_data = device_data.get("value", {})
            device_list = value_data.get("device_list", [])
            
            # Process each device reading
            for reading in device_list:
                obs_list = await self._create_observations_from_reading(
                    reading, attribute, mqtt_payload, patient_id, device_id
                )
                observations.extend(obs_list)
            
            return observations
            
        except Exception as e:
            logger.error(f"Failed to transform AVA4 MQTT to FHIR: {e}")
            raise

    async def _create_observations_from_reading(
        self,
        reading: Dict[str, Any],
        attribute: str,
        mqtt_payload: Dict[str, Any],
        patient_id: str,
        device_id: str
    ) -> List[Dict[str, Any]]:
        """Create FHIR Observations from individual device reading"""
        observations = []
        
        # Determine measurement type and create appropriate observations
        if "bp_high" in reading and "bp_low" in reading:
            # Blood pressure reading
            obs = await self._create_blood_pressure_observation(
                reading, mqtt_payload, patient_id, device_id
            )
            observations.append(obs)
            
        elif "spo2" in reading and "pulse" in reading:
            # Pulse oximetry reading
            obs = await self._create_pulse_oximetry_observation(
                reading, mqtt_payload, patient_id, device_id
            )
            observations.append(obs)
            
        elif "blood_glucose" in reading:
            # Blood glucose reading
            obs = await self._create_glucose_observation(
                reading, mqtt_payload, patient_id, device_id
            )
            observations.append(obs)
            
        elif "temp" in reading:
            # Temperature reading
            obs = await self._create_temperature_observation(
                reading, mqtt_payload, patient_id, device_id
            )
            observations.append(obs)
            
        elif "weight" in reading:
            # Weight reading
            obs = await self._create_weight_observation(
                reading, mqtt_payload, patient_id, device_id
            )
            observations.append(obs)
            
        elif "cholesterol" in reading:
            # Cholesterol reading
            obs = await self._create_cholesterol_observation(
                reading, mqtt_payload, patient_id, device_id
            )
            observations.append(obs)
            
        elif "uric_acid" in reading:
            # Uric acid reading
            obs = await self._create_uric_acid_observation(
                reading, mqtt_payload, patient_id, device_id
            )
            observations.append(obs)
        
        return observations

    async def _create_blood_pressure_observation(
        self,
        reading: Dict[str, Any],
        mqtt_payload: Dict[str, Any],
        patient_id: str,
        device_id: str
    ) -> Dict[str, Any]:
        """Create FHIR Observation for blood pressure"""
        
        observation_id = str(uuid.uuid4())
        effective_time = self._convert_timestamp(reading.get("scan_time"))
        
        # Create components for systolic, diastolic, and pulse
        components = []
        
        if "bp_high" in reading:
            components.append({
                "code": {
                    "coding": [{
                        "system": "http://loinc.org",
                        "code": "8480-6",
                        "display": "Systolic blood pressure"
                    }]
                },
                "valueQuantity": {
                    "value": reading["bp_high"],
                    "unit": "mmHg",
                    "system": "http://unitsofmeasure.org",
                    "code": "mm[Hg]"
                }
            })
            
        if "bp_low" in reading:
            components.append({
                "code": {
                    "coding": [{
                        "system": "http://loinc.org",
                        "code": "8462-4",
                        "display": "Diastolic blood pressure"
                    }]
                },
                "valueQuantity": {
                    "value": reading["bp_low"],
                    "unit": "mmHg",
                    "system": "http://unitsofmeasure.org",
                    "code": "mm[Hg]"
                }
            })
            
        if "PR" in reading:
            components.append({
                "code": {
                    "coding": [{
                        "system": "http://loinc.org",
                        "code": "8867-4",
                        "display": "Heart rate"
                    }]
                },
                "valueQuantity": {
                    "value": reading["PR"],
                    "unit": "beats/min",
                    "system": "http://unitsofmeasure.org",
                    "code": "/min"
                }
            })
        
        observation = {
            "resourceType": "Observation",
            "id": observation_id,
            "status": "final",
            "category": [{
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                    "code": "vital-signs",
                    "display": "Vital Signs"
                }]
            }],
            "code": {
                "coding": [{
                    "system": "http://loinc.org",
                    "code": "85354-9",
                    "display": "Blood pressure panel with all children optional"
                }]
            },
            "subject": {
                "reference": f"Patient/{patient_id}"
            },
            "effectiveDateTime": effective_time.isoformat() + "Z",
            "issued": datetime.utcnow().isoformat() + "Z",
            "device": {
                "reference": f"Device/{device_id}",
                "display": mqtt_payload.get("data", {}).get("device", "Unknown Device")
            },
            "component": components
        }
        
        # Add provenance information
        if "ble_addr" in reading:
            observation["extension"] = [{
                "url": "http://my-firstcare.com/fhir/StructureDefinition/device-mac-address",
                "valueString": reading["ble_addr"]
            }]
        
        return observation

    async def _create_pulse_oximetry_observation(
        self,
        reading: Dict[str, Any],
        mqtt_payload: Dict[str, Any],
        patient_id: str,
        device_id: str
    ) -> Dict[str, Any]:
        """Create FHIR Observation for pulse oximetry"""
        
        observation_id = str(uuid.uuid4())
        effective_time = self._convert_timestamp(reading.get("scan_time"))
        
        # Create components for SpO2 and pulse
        components = []
        
        if "spo2" in reading:
            components.append({
                "code": {
                    "coding": [{
                        "system": "http://loinc.org",
                        "code": "59408-5",
                        "display": "Oxygen saturation in Arterial blood by Pulse oximetry"
                    }]
                },
                "valueQuantity": {
                    "value": reading["spo2"],
                    "unit": "%",
                    "system": "http://unitsofmeasure.org",
                    "code": "%"
                }
            })
            
        if "pulse" in reading:
            components.append({
                "code": {
                    "coding": [{
                        "system": "http://loinc.org",
                        "code": "8867-4",
                        "display": "Heart rate"
                    }]
                },
                "valueQuantity": {
                    "value": reading["pulse"],
                    "unit": "beats/min",
                    "system": "http://unitsofmeasure.org",
                    "code": "/min"
                }
            })
        
        if "pi" in reading:
            components.append({
                "code": {
                    "coding": [{
                        "system": "http://loinc.org",
                        "code": "61006-6",
                        "display": "Perfusion index"
                    }]
                },
                "valueQuantity": {
                    "value": reading["pi"],
                    "unit": "%",
                    "system": "http://unitsofmeasure.org",
                    "code": "%"
                }
            })
        
        observation = {
            "resourceType": "Observation",
            "id": observation_id,
            "status": "final",
            "category": [{
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                    "code": "vital-signs",
                    "display": "Vital Signs"
                }]
            }],
            "code": {
                "coding": [{
                    "system": "http://loinc.org",
                    "code": "59408-5",
                    "display": "Oxygen saturation in Arterial blood by Pulse oximetry"
                }]
            },
            "subject": {
                "reference": f"Patient/{patient_id}"
            },
            "effectiveDateTime": effective_time.isoformat() + "Z",
            "issued": datetime.utcnow().isoformat() + "Z",
            "device": {
                "reference": f"Device/{device_id}",
                "display": mqtt_payload.get("data", {}).get("device", "Unknown Device")
            },
            "component": components
        }
        
        return observation

    async def _create_glucose_observation(
        self,
        reading: Dict[str, Any],
        mqtt_payload: Dict[str, Any],
        patient_id: str,
        device_id: str
    ) -> Dict[str, Any]:
        """Create FHIR Observation for blood glucose"""
        
        observation_id = str(uuid.uuid4())
        effective_time = self._convert_timestamp(reading.get("scan_time"))
        
        observation = {
            "resourceType": "Observation",
            "id": observation_id,
            "status": "final",
            "category": [{
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                    "code": "laboratory",
                    "display": "Laboratory"
                }]
            }],
            "code": {
                "coding": [{
                    "system": "http://loinc.org",
                    "code": "33747-0",
                    "display": "Glucose measurement"
                }]
            },
            "subject": {
                "reference": f"Patient/{patient_id}"
            },
            "effectiveDateTime": effective_time.isoformat() + "Z",
            "issued": datetime.utcnow().isoformat() + "Z",
            "valueQuantity": {
                "value": float(reading["blood_glucose"]),
                "unit": "mg/dL",
                "system": "http://unitsofmeasure.org",
                "code": "mg/dL"
            },
            "device": {
                "reference": f"Device/{device_id}",
                "display": mqtt_payload.get("data", {}).get("device", "Unknown Device")
            }
        }
        
        # Add marker information if available
        if "marker" in reading:
            observation["note"] = [{
                "text": f"Measurement marker: {reading['marker']}"
            }]
        
        return observation

    async def _create_temperature_observation(
        self,
        reading: Dict[str, Any],
        mqtt_payload: Dict[str, Any],
        patient_id: str,
        device_id: str
    ) -> Dict[str, Any]:
        """Create FHIR Observation for body temperature"""
        
        observation_id = str(uuid.uuid4())
        effective_time = self._convert_timestamp(reading.get("scan_time"))
        
        observation = {
            "resourceType": "Observation",
            "id": observation_id,
            "status": "final",
            "category": [{
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                    "code": "vital-signs",
                    "display": "Vital Signs"
                }]
            }],
            "code": {
                "coding": [{
                    "system": "http://loinc.org",
                    "code": "8310-5",
                    "display": "Body temperature"
                }]
            },
            "subject": {
                "reference": f"Patient/{patient_id}"
            },
            "effectiveDateTime": effective_time.isoformat() + "Z",
            "issued": datetime.utcnow().isoformat() + "Z",
            "valueQuantity": {
                "value": reading["temp"],
                "unit": "°C",
                "system": "http://unitsofmeasure.org",
                "code": "Cel"
            },
            "device": {
                "reference": f"Device/{device_id}",
                "display": mqtt_payload.get("data", {}).get("device", "Unknown Device")
            }
        }
        
        # Add measurement mode if available
        if "mode" in reading:
            observation["bodySite"] = {
                "coding": [{
                    "system": "http://snomed.info/sct",
                    "code": "69536005" if reading["mode"].lower() == "head" else "181220002",
                    "display": reading["mode"]
                }]
            }
        
        return observation

    async def _create_weight_observation(
        self,
        reading: Dict[str, Any],
        mqtt_payload: Dict[str, Any],
        patient_id: str,
        device_id: str
    ) -> Dict[str, Any]:
        """Create FHIR Observation for body weight"""
        
        observation_id = str(uuid.uuid4())
        effective_time = self._convert_timestamp(reading.get("scan_time"))
        
        observation = {
            "resourceType": "Observation",
            "id": observation_id,
            "status": "final",
            "category": [{
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                    "code": "vital-signs",
                    "display": "Vital Signs"
                }]
            }],
            "code": {
                "coding": [{
                    "system": "http://loinc.org",
                    "code": "29463-7",
                    "display": "Body weight"
                }]
            },
            "subject": {
                "reference": f"Patient/{patient_id}"
            },
            "effectiveDateTime": effective_time.isoformat() + "Z",
            "issued": datetime.utcnow().isoformat() + "Z",
            "valueQuantity": {
                "value": reading["weight"],
                "unit": "kg",
                "system": "http://unitsofmeasure.org",
                "code": "kg"
            },
            "device": {
                "reference": f"Device/{device_id}",
                "display": mqtt_payload.get("data", {}).get("device", "Unknown Device")
            }
        }
        
        # Add resistance if available (body composition)
        if "resistance" in reading:
            observation["component"] = [{
                "code": {
                    "coding": [{
                        "system": "http://loinc.org",
                        "code": "91556-1",
                        "display": "Body impedance"
                    }]
                },
                "valueQuantity": {
                    "value": reading["resistance"],
                    "unit": "ohm",
                    "system": "http://unitsofmeasure.org",
                    "code": "Ohm"
                }
            }]
        
        return observation

    async def _create_cholesterol_observation(
        self,
        reading: Dict[str, Any],
        mqtt_payload: Dict[str, Any],
        patient_id: str,
        device_id: str
    ) -> Dict[str, Any]:
        """Create FHIR Observation for cholesterol"""
        
        observation_id = str(uuid.uuid4())
        effective_time = self._convert_timestamp(reading.get("scan_time"))
        
        observation = {
            "resourceType": "Observation",
            "id": observation_id,
            "status": "final",
            "category": [{
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                    "code": "laboratory",
                    "display": "Laboratory"
                }]
            }],
            "code": {
                "coding": [{
                    "system": "http://loinc.org",
                    "code": "2093-3",
                    "display": "Cholesterol [Mass/Volume] in Serum or Plasma"
                }]
            },
            "subject": {
                "reference": f"Patient/{patient_id}"
            },
            "effectiveDateTime": effective_time.isoformat() + "Z",
            "issued": datetime.utcnow().isoformat() + "Z",
            "valueQuantity": {
                "value": float(reading["cholesterol"]),
                "unit": "mmol/L",
                "system": "http://unitsofmeasure.org",
                "code": "mmol/L"
            },
            "device": {
                "reference": f"Device/{device_id}",
                "display": mqtt_payload.get("data", {}).get("device", "Unknown Device")
            }
        }
        
        return observation

    async def _create_uric_acid_observation(
        self,
        reading: Dict[str, Any],
        mqtt_payload: Dict[str, Any],
        patient_id: str,
        device_id: str
    ) -> Dict[str, Any]:
        """Create FHIR Observation for uric acid"""
        
        observation_id = str(uuid.uuid4())
        effective_time = self._convert_timestamp(reading.get("scan_time"))
        
        observation = {
            "resourceType": "Observation",
            "id": observation_id,
            "status": "final",
            "category": [{
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                    "code": "laboratory",
                    "display": "Laboratory"
                }]
            }],
            "code": {
                "coding": [{
                    "system": "http://loinc.org",
                    "code": "3084-1",
                    "display": "Urate [Mass/Volume] in Serum or Plasma"
                }]
            },
            "subject": {
                "reference": f"Patient/{patient_id}"
            },
            "effectiveDateTime": effective_time.isoformat() + "Z",
            "issued": datetime.utcnow().isoformat() + "Z",
            "valueQuantity": {
                "value": float(reading["uric_acid"]),
                "unit": "umol/L",
                "system": "http://unitsofmeasure.org",
                "code": "umol/L"
            },
            "device": {
                "reference": f"Device/{device_id}",
                "display": mqtt_payload.get("data", {}).get("device", "Unknown Device")
            }
        }
        
        return observation

    # =============== Data Migration Functions ===============

    async def migrate_existing_patient_to_fhir(self, patient_doc: Dict[str, Any]) -> str:
        """Migrate existing patient document to FHIR R5 Patient resource"""
        try:
            patient_id = str(uuid.uuid4())
            
            # Build HumanName
            names = []
            if patient_doc.get("first_name") or patient_doc.get("last_name"):
                names.append({
                    "use": "official",
                    "family": patient_doc.get("last_name", ""),
                    "given": [patient_doc.get("first_name", "")]
                })
            
            if patient_doc.get("nickname"):
                names.append({
                    "use": "nickname",
                    "text": patient_doc.get("nickname")
                })
            
            # Build identifiers
            identifiers = []
            if patient_doc.get("national_id"):
                identifiers.append({
                    "use": "official",
                    "type": {
                        "coding": [{
                            "system": "http://terminology.hl7.org/CodeSystem/v2-0203",
                            "code": "NI",
                            "display": "National identifier"
                        }]
                    },
                    "system": "http://thailand.gov.th/national-id",
                    "value": patient_doc["national_id"]
                })
            
            if patient_doc.get("hn_id_no"):
                identifiers.append({
                    "use": "usual",
                    "type": {
                        "coding": [{
                            "system": "http://terminology.hl7.org/CodeSystem/v2-0203",
                            "code": "MR",
                            "display": "Medical record number"
                        }]
                    },
                    "system": "http://my-firstcare.com/patient-id",
                    "value": patient_doc["hn_id_no"]
                })
            
            # Build contact points
            telecom = []
            if patient_doc.get("mobile_no"):
                telecom.append({
                    "system": "phone",
                    "value": patient_doc["mobile_no"],
                    "use": "mobile"
                })
            
            if patient_doc.get("telephone_no"):
                telecom.append({
                    "system": "phone",
                    "value": patient_doc["telephone_no"],
                    "use": "home"
                })
            
            if patient_doc.get("email"):
                telecom.append({
                    "system": "email",
                    "value": patient_doc["email"]
                })
            
            # Build address
            addresses = []
            if any([patient_doc.get("address"), patient_doc.get("province"), 
                   patient_doc.get("district"), patient_doc.get("sub_district")]):
                addresses.append({
                    "use": "home",
                    "type": "physical",
                    "text": patient_doc.get("address", ""),
                    "city": patient_doc.get("district", ""),
                    "state": patient_doc.get("province", ""),
                    "postalCode": patient_doc.get("postal_code", ""),
                    "country": "TH"
                })
            
            # Build Patient resource
            patient_resource = {
                "resourceType": "Patient",
                "id": patient_id,
                "active": patient_doc.get("is_active", True),
                "identifier": identifiers,
                "name": names,
                "telecom": telecom,
                "gender": self._map_gender(patient_doc.get("gender")),
                "birthDate": self._format_birth_date(patient_doc.get("dob")),
                "address": addresses
            }
            
            # Add managing organization if hospital_id exists
            if patient_doc.get("hospital_id"):
                patient_resource["managingOrganization"] = {
                    "reference": f"Organization/{patient_doc['hospital_id']}"
                }
            
            # Create FHIR Patient resource
            result = await self.create_fhir_resource(
                "Patient", 
                patient_resource,
                source_system="migration",
                device_mac_address=patient_doc.get("ava_mac_address")
            )
            
            logger.info(f"Migrated patient {patient_doc.get('_id')} to FHIR Patient {patient_id}")
            
            return patient_id
            
        except Exception as e:
            logger.error(f"Failed to migrate patient to FHIR: {e}")
            raise

    # =============== Utility Functions ===============

    async def _extract_references(self, fhir_doc: FHIRResourceDocument, resource_data: Dict[str, Any]):
        """Extract references for MongoDB indexing"""
        
        # Extract patient reference
        if "subject" in resource_data and "reference" in resource_data["subject"]:
            ref = resource_data["subject"]["reference"]
            if ref.startswith("Patient/"):
                fhir_doc.patient_id = ref.replace("Patient/", "")
        
        # Extract encounter reference
        if "encounter" in resource_data and "reference" in resource_data["encounter"]:
            ref = resource_data["encounter"]["reference"]
            if ref.startswith("Encounter/"):
                fhir_doc.encounter_id = ref.replace("Encounter/", "")
        
        # Extract device reference
        if "device" in resource_data and "reference" in resource_data["device"]:
            ref = resource_data["device"]["reference"]
            if ref.startswith("Device/"):
                fhir_doc.device_id = ref.replace("Device/", "")
        
        # Extract effective datetime
        if "effectiveDateTime" in resource_data:
            fhir_doc.effective_datetime = datetime.fromisoformat(
                resource_data["effectiveDateTime"].replace("Z", "+00:00")
            )
        
        # Extract status
        if "status" in resource_data:
            fhir_doc.status = resource_data["status"]

    def _convert_timestamp(self, timestamp: Union[int, str, None]) -> datetime:
        """Convert various timestamp formats to datetime"""
        if timestamp is None:
            return datetime.utcnow()
        
        if isinstance(timestamp, str):
            try:
                return datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            except:
                timestamp = int(timestamp)
        
        if isinstance(timestamp, int):
            # Handle both seconds and milliseconds
            if timestamp > 9999999999:  # milliseconds
                timestamp = timestamp / 1000
            return datetime.fromtimestamp(timestamp, tz=timezone.utc)
        
        return datetime.utcnow()

    def _map_gender(self, gender: str) -> str:
        """Map gender to FHIR values"""
        if not gender:
            return "unknown"
        
        gender_lower = gender.lower()
        if gender_lower in ["m", "male", "ชาย"]:
            return "male"
        elif gender_lower in ["f", "female", "หญิง"]:
            return "female"
        else:
            return "other"

    def _format_birth_date(self, birth_date: Any) -> Optional[str]:
        """Format birth date to FHIR date format"""
        if not birth_date:
            return None
        
        if isinstance(birth_date, datetime):
            return birth_date.strftime("%Y-%m-%d")
        elif isinstance(birth_date, str):
            try:
                dt = datetime.fromisoformat(birth_date.replace("Z", "+00:00"))
                return dt.strftime("%Y-%m-%d")
            except:
                return birth_date
        
        return str(birth_date)

    def _parse_date_range(self, date_param: str) -> Optional[Dict[str, Any]]:
        """Parse FHIR date range parameter"""
        try:
            if ".." in date_param:
                start, end = date_param.split("..")
                return {
                    "$gte": datetime.fromisoformat(start),
                    "$lte": datetime.fromisoformat(end)
                }
            elif date_param.startswith("ge"):
                return {"$gte": datetime.fromisoformat(date_param[2:])}
            elif date_param.startswith("le"):
                return {"$lte": datetime.fromisoformat(date_param[2:])}
            else:
                # Exact date
                return {"$eq": datetime.fromisoformat(date_param)}
        except:
            return None

    def _parse_sort_spec(self, sort_param: str) -> List[Tuple[str, int]]:
        """Parse FHIR sort parameter"""
        sort_spec = []
        for field in sort_param.split(","):
            if field.startswith("-"):
                sort_spec.append((field[1:], DESCENDING))
            else:
                sort_spec.append((field, ASCENDING))
        return sort_spec

    def _build_search_links(
        self, 
        resource_type: str, 
        search_params: FHIRSearchParams, 
        total: int
    ) -> List[Dict[str, str]]:
        """Build FHIR search navigation links"""
        links = []
        
        # Self link
        links.append({
            "relation": "self",
            "url": f"/{resource_type}?_count={search_params._count}&_offset={search_params._offset}"
        })
        
        # Next link
        next_offset = search_params._offset + search_params._count
        if next_offset < total:
            links.append({
                "relation": "next",
                "url": f"/{resource_type}?_count={search_params._count}&_offset={next_offset}"
            })
        
        # Previous link
        if search_params._offset > 0:
            prev_offset = max(0, search_params._offset - search_params._count)
            links.append({
                "relation": "previous",
                "url": f"/{resource_type}?_count={search_params._count}&_offset={prev_offset}"
            })
        
        return links

    # =============== AMY Data Migration Methods ===============

    async def migrate_medication_history_to_fhir(self, medication_doc: Dict[str, Any]) -> List[str]:
        """Migrate AMY medication history to FHIR R5 MedicationStatement resources"""
        try:
            patient_id = str(medication_doc.get("patient_id"))
            medication_ids = []
            
            for medication_entry in medication_doc.get("data", []):
                medication_id = str(uuid.uuid4())
                
                # Build MedicationStatement resource
                medication_statement = {
                    "resourceType": "MedicationStatement",
                    "id": medication_id,
                    "status": "completed",  # Historical medication records
                    "category": [{
                        "coding": [{
                            "system": "http://terminology.hl7.org/CodeSystem/medication-statement-category",
                            "code": "community",
                            "display": "Community"
                        }]
                    }],
                    "medicationCodeableConcept": {
                        "text": medication_entry.get("medication_detail", "Unknown medication")
                    },
                    "subject": {
                        "reference": f"Patient/{patient_id}",
                        "display": "Patient"
                    },
                    "effectiveDateTime": self._convert_timestamp(
                        medication_entry.get("medication_import_date")
                    ).isoformat() if medication_entry.get("medication_import_date") else None,
                    "dateAsserted": self._convert_timestamp(
                        medication_doc.get("created_at")
                    ).isoformat() if medication_doc.get("created_at") else None,
                    "note": [{
                        "text": f"Source: AMY medication history (source: {medication_entry.get('medication_source', 0)})"
                    }]
                }
                
                # Store in FHIR collection
                result = await self.create_fhir_resource(
                    "MedicationStatement", 
                    medication_statement,
                    source_system="amy_migration"
                )
                medication_ids.append(result["resource_id"])
                
            logger.info(f"Migrated {len(medication_ids)} medication statements for patient {patient_id}")
            return medication_ids
            
        except Exception as e:
            logger.error(f"Failed to migrate medication history: {e}")
            raise

    async def migrate_allergy_history_to_fhir(self, allergy_doc: Dict[str, Any]) -> List[str]:
        """Migrate AMY allergy history to FHIR R5 AllergyIntolerance resources"""
        try:
            patient_id = str(allergy_doc.get("patient_id"))
            allergy_ids = []
            
            for allergy_entry in allergy_doc.get("data", []):
                allergy_id = str(uuid.uuid4())
                
                # Determine allergy category and type based on content
                allergy_detail = allergy_entry.get("allergy_detail", "").lower()
                category = []
                allergy_type = "allergy"
                
                if any(keyword in allergy_detail for keyword in ["food", "อาหาร", "นม", "เนื้อ"]):
                    category.append("food")
                elif any(keyword in allergy_detail for keyword in ["drug", "medicine", "ยา", "antibiotic"]):
                    category.append("medication")
                elif any(keyword in allergy_detail for keyword in ["dust", "pollen", "ฝุ่น", "เสียงดัง"]):
                    category.append("environment")
                else:
                    category.append("environment")  # Default
                
                # Build AllergyIntolerance resource
                allergy_intolerance = {
                    "resourceType": "AllergyIntolerance",
                    "id": allergy_id,
                    "clinicalStatus": {
                        "coding": [{
                            "system": "http://terminology.hl7.org/CodeSystem/allergyintolerance-clinical",
                            "code": "active",
                            "display": "Active"
                        }]
                    },
                    "verificationStatus": {
                        "coding": [{
                            "system": "http://terminology.hl7.org/CodeSystem/allergyintolerance-verification",
                            "code": "confirmed",
                            "display": "Confirmed"
                        }]
                    },
                    "type": [allergy_type],
                    "category": category,
                    "criticality": "unable-to-assess",
                    "code": {
                        "text": allergy_entry.get("allergy_detail", "Unknown allergen")
                    },
                    "patient": {
                        "reference": f"Patient/{patient_id}",
                        "display": "Patient"
                    },
                    "recordedDate": self._convert_timestamp(
                        allergy_entry.get("allergy_import_date")
                    ).isoformat() if allergy_entry.get("allergy_import_date") else None,
                    "note": [{
                        "text": f"Source: AMY allergy history (source: {allergy_entry.get('allergy_source', 0)})"
                    }]
                }
                
                # Store in FHIR collection
                result = await self.create_fhir_resource(
                    "AllergyIntolerance", 
                    allergy_intolerance,
                    source_system="amy_migration"
                )
                allergy_ids.append(result["resource_id"])
                
            logger.info(f"Migrated {len(allergy_ids)} allergy intolerances for patient {patient_id}")
            return allergy_ids
            
        except Exception as e:
            logger.error(f"Failed to migrate allergy history: {e}")
            raise

    async def migrate_admission_to_fhir(self, admission_doc: Dict[str, Any]) -> str:
        """Migrate AMY admission data to FHIR R5 Encounter resource"""
        try:
            patient_id = str(admission_doc.get("patient_id"))
            encounter_id = str(uuid.uuid4())
            
            # Map admission status to FHIR encounter status
            admit_status = admission_doc.get("admit_status", 0)
            if admit_status == 1:
                status = "in-progress"
                encounter_class = {
                    "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
                    "code": "IMP",
                    "display": "inpatient encounter"
                }
            else:
                status = "completed"
                encounter_class = {
                    "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
                    "code": "AMB",
                    "display": "ambulatory"
                }
            
            # Build Encounter resource
            encounter = {
                "resourceType": "Encounter",
                "id": encounter_id,
                "status": status,
                "class": encounter_class,
                "type": [{
                    "coding": [{
                        "system": "http://snomed.info/sct",
                        "code": "185347001",
                        "display": "Encounter for problem"
                    }]
                }],
                "subject": {
                    "reference": f"Patient/{patient_id}",
                    "display": "Patient"
                },
                "actualPeriod": {
                    "start": self._convert_timestamp(
                        admission_doc.get("created_at")
                    ).isoformat() if admission_doc.get("created_at") else None,
                    "end": self._convert_timestamp(
                        admission_doc.get("updated_at")
                    ).isoformat() if admission_doc.get("updated_at") and admit_status == 0 else None
                }
            }
            
            # Add note if available
            if admission_doc.get("note"):
                encounter["note"] = [{
                    "text": admission_doc["note"]
                }]
            
            # Store in FHIR collection
            result = await self.create_fhir_resource(
                "Encounter", 
                encounter,
                source_system="amy_migration"
            )
            
            logger.info(f"Migrated encounter {encounter_id} for patient {patient_id}")
            return result["resource_id"]
            
        except Exception as e:
            logger.error(f"Failed to migrate admission data: {e}")
            raise

    async def migrate_lab_results_to_fhir(self, lab_data: Dict[str, Any], report_type: str) -> str:
        """Migrate AMY lab results to FHIR R5 DiagnosticReport and Observation resources"""
        try:
            patient_id = str(lab_data.get("patient_id"))
            report_id = str(uuid.uuid4())
            
            # Map report types to LOINC codes
            report_mappings = {
                "creatinine": {
                    "code": "2160-0",
                    "display": "Creatinine",
                    "category": "laboratory"
                },
                "lipid": {
                    "code": "24331-1", 
                    "display": "Lipid panel",
                    "category": "laboratory"
                }
            }
            
            report_info = report_mappings.get(report_type, {
                "code": "33747-0",
                "display": "General laboratory studies",
                "category": "laboratory"
            })
            
            # Create observation resources for each data point
            observation_refs = []
            for data_entry in lab_data.get("data", []):
                obs_id = str(uuid.uuid4())
                
                # Create observation for lab value
                observation = {
                    "resourceType": "Observation",
                    "id": obs_id,
                    "status": "final",
                    "category": [{
                        "coding": [{
                            "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                            "code": report_info["category"],
                            "display": "Laboratory"
                        }]
                    }],
                    "code": {
                        "coding": [{
                            "system": "http://loinc.org",
                            "code": report_info["code"],
                            "display": report_info["display"]
                        }]
                    },
                    "subject": {
                        "reference": f"Patient/{patient_id}",
                        "display": "Patient"
                    },
                    "effectiveDateTime": self._convert_timestamp(
                        data_entry.get(f"{report_type}_import_date")
                    ).isoformat() if data_entry.get(f"{report_type}_import_date") else None
                }
                
                # Add specific lab values based on type
                if report_type == "creatinine" and "creatinine" in data_entry:
                    observation["valueQuantity"] = {
                        "value": data_entry["creatinine"],
                        "unit": "mg/dL",
                        "system": "http://unitsofmeasure.org",
                        "code": "mg/dL"
                    }
                elif report_type == "lipid":
                    # Handle multiple lipid values
                    components = []
                    if "total_cholesterol" in data_entry:
                        components.append({
                            "code": {
                                "coding": [{
                                    "system": "http://loinc.org",
                                    "code": "2093-3",
                                    "display": "Cholesterol [Mass/volume] in Serum or Plasma"
                                }]
                            },
                            "valueQuantity": {
                                "value": data_entry["total_cholesterol"],
                                "unit": "mg/dL",
                                "system": "http://unitsofmeasure.org",
                                "code": "mg/dL"
                            }
                        })
                    
                    if components:
                        observation["component"] = components
                
                # Store observation
                obs_result = await self.create_fhir_resource(
                    "Observation", 
                    observation,
                    source_system="amy_migration"
                )
                observation_refs.append({
                    "reference": f"Observation/{obs_result['resource_id']}"
                })
            
            # Create DiagnosticReport
            diagnostic_report = {
                "resourceType": "DiagnosticReport",
                "id": report_id,
                "status": "final",
                "category": [{
                    "coding": [{
                        "system": "http://terminology.hl7.org/CodeSystem/v2-0074",
                        "code": "LAB",
                        "display": "Laboratory"
                    }]
                }],
                "code": {
                    "coding": [{
                        "system": "http://loinc.org",
                        "code": report_info["code"],
                        "display": report_info["display"]
                    }]
                },
                "subject": {
                    "reference": f"Patient/{patient_id}",
                    "display": "Patient"
                },
                "effectiveDateTime": self._convert_timestamp(
                    lab_data.get("created_at")
                ).isoformat() if lab_data.get("created_at") else None,
                "issued": self._convert_timestamp(
                    lab_data.get("updated_at")
                ).isoformat() if lab_data.get("updated_at") else None,
                "result": observation_refs
            }
            
            # Store diagnostic report
            result = await self.create_fhir_resource(
                "DiagnosticReport", 
                diagnostic_report,
                source_system="amy_migration"
            )
            
            logger.info(f"Migrated {report_type} diagnostic report {report_id} with {len(observation_refs)} observations for patient {patient_id}")
            return result["resource_id"]
            
        except Exception as e:
            logger.error(f"Failed to migrate lab results: {e}")
            raise

    async def migrate_body_data_to_observations(self, body_data_doc: Dict[str, Any]) -> List[str]:
        """Transform body data from medical_history to FHIR Observations"""
        observation_ids = []
        
        try:
            patient_id = str(body_data_doc.get("patient_id", ""))
            if not patient_id:
                logger.warning("No patient_id found in body data document")
                return observation_ids
            
            # Process each body measurement
            measurements = ["weight", "height", "waist", "bmi"]
            
            for measurement in measurements:
                value = body_data_doc.get(measurement)
                if value and value != 0:
                    observation = await self._create_body_measurement_observation(
                        measurement, value, patient_id, body_data_doc
                    )
                    
                    result = await self.create_fhir_resource(
                        "Observation", 
                        observation,
                        source_system="amy_migration"
                    )
                    
                    if result["success"]:
                        observation_ids.append(result["resource_id"])
                        
            logger.info(f"Migrated {len(observation_ids)} body measurements for patient {patient_id}")
            return observation_ids
            
        except Exception as e:
            logger.error(f"Failed to migrate body data to FHIR: {e}")
            raise

    async def _create_body_measurement_observation(
        self, 
        measurement_type: str, 
        value: Union[int, float], 
        patient_id: str,
        source_doc: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create FHIR Observation for body measurements"""
        
        # LOINC codes for body measurements
        loinc_mappings = {
            "weight": {"code": "29463-7", "display": "Body weight", "unit": "kg"},
            "height": {"code": "8302-2", "display": "Body height", "unit": "cm"},
            "waist": {"code": "8280-0", "display": "Waist circumference", "unit": "cm"},
            "bmi": {"code": "39156-5", "display": "Body mass index", "unit": "kg/m2"}
        }
        
        mapping = loinc_mappings.get(measurement_type, {})
        observation_id = str(uuid.uuid4())
        
        observation = {
            "resourceType": "Observation",
            "id": observation_id,
            "status": "final",
            "category": [{
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                    "code": "vital-signs",
                    "display": "Vital Signs"
                }]
            }],
            "code": {
                "coding": [{
                    "system": "http://loinc.org",
                    "code": mapping.get("code", "33747-0"),
                    "display": mapping.get("display", f"{measurement_type} measurement")
                }]
            },
            "subject": {
                "reference": f"Patient/{patient_id}"
            },
            "effectiveDateTime": self._convert_timestamp(
                source_doc.get("created_at")
            ).isoformat() + "Z",
            "valueQuantity": {
                "value": float(value),
                "unit": mapping.get("unit", "unit"),
                "system": "http://unitsofmeasure.org"
            }
        }
        
        return observation

    # =============== New FHIR R5 Resource Transformation Methods ===============

    async def migrate_patient_goals_to_fhir(self, patient_doc: Dict[str, Any]) -> List[str]:
        """Transform AMY patient goal data to FHIR Goal resources"""
        goal_ids = []
        
        try:
            patient_id = str(patient_doc.get("_id", ""))
            if not patient_id:
                logger.warning("No patient ID found in patient document")
                return goal_ids
            
            # Create goals for step tracking
            step_goal = patient_doc.get("step_goal", 0)
            if step_goal > 0:
                goal = await self._create_step_goal(patient_id, step_goal, patient_doc)
                result = await self.create_fhir_resource("Goal", goal, source_system="amy_migration")
                if result["success"]:
                    goal_ids.append(result["resource_id"])
            
            # Create goals for vital sign thresholds
            vitals_goals = await self._create_vitals_threshold_goals(patient_id, patient_doc)
            for goal in vitals_goals:
                result = await self.create_fhir_resource("Goal", goal, source_system="amy_migration")
                if result["success"]:
                    goal_ids.append(result["resource_id"])
            
            # Create weight management goals
            weight_goals = await self._create_weight_management_goals(patient_id, patient_doc)
            for goal in weight_goals:
                result = await self.create_fhir_resource("Goal", goal, source_system="amy_migration")
                if result["success"]:
                    goal_ids.append(result["resource_id"])
            
            logger.info(f"Created {len(goal_ids)} goals for patient {patient_id}")
            return goal_ids
            
        except Exception as e:
            logger.error(f"Failed to migrate patient goals to FHIR: {e}")
            raise

    async def _create_step_goal(self, patient_id: str, step_goal: int, patient_doc: Dict[str, Any]) -> Dict[str, Any]:
        """Create FHIR Goal resource for step tracking"""
        goal_id = str(uuid.uuid4())
        
        return {
            "resourceType": "Goal",
            "id": goal_id,
            "lifecycleStatus": "active",
            "achievementStatus": {
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/goal-achievement",
                    "code": "in-progress",
                    "display": "In Progress"
                }]
            },
            "category": [{
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/goal-category",
                    "code": "behavioral",
                    "display": "Behavioral"
                }]
            }],
            "priority": {
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/goal-priority",
                    "code": "medium-priority",
                    "display": "Medium Priority"
                }]
            },
            "description": {
                "coding": [{
                    "system": "http://snomed.info/sct",
                    "code": "226029000",
                    "display": "Exercise goal"
                }],
                "text": f"Daily step goal of {step_goal} steps"
            },
            "subject": {
                "reference": f"Patient/{patient_id}"
            },
            "start": {
                "coding": [{
                    "system": "http://snomed.info/sct",
                    "code": "32485007",
                    "display": "Admission to hospital"
                }]
            },
            "target": [{
                "measure": {
                    "coding": [{
                        "system": "http://loinc.org",
                        "code": "41950-7",
                        "display": "Number of steps in 24 hour Measured"
                    }]
                },
                "detailQuantity": {
                    "value": step_goal,
                    "unit": "steps",
                    "system": "http://unitsofmeasure.org",
                    "code": "{steps}"
                },
                "dueDate": "2024-12-31"
            }],
            "statusDate": datetime.utcnow().strftime("%Y-%m-%d"),
            "source": {
                "reference": f"Patient/{patient_id}"
            }
        }

    async def _create_vitals_threshold_goals(self, patient_id: str, patient_doc: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create FHIR Goal resources for vital sign thresholds"""
        goals = []
        
        # Blood pressure goals
        bp_sbp_above = patient_doc.get("bp_sbp_above", 0)
        bp_dbp_above = patient_doc.get("bp_dbp_above", 0)
        if bp_sbp_above > 0 or bp_dbp_above > 0:
            goal = {
                "resourceType": "Goal",
                "id": str(uuid.uuid4()),
                "lifecycleStatus": "active",
                "category": [{
                    "coding": [{
                        "system": "http://terminology.hl7.org/CodeSystem/goal-category",
                        "code": "physiological",
                        "display": "Physiological"
                    }]
                }],
                "description": {
                    "text": f"Maintain blood pressure below {bp_sbp_above}/{bp_dbp_above} mmHg"
                },
                "subject": {
                    "reference": f"Patient/{patient_id}"
                },
                "target": [{
                    "measure": {
                        "coding": [{
                            "system": "http://loinc.org",
                            "code": "85354-9",
                            "display": "Blood pressure panel"
                        }]
                    },
                    "detailRange": {
                        "low": {
                            "value": 90,
                            "unit": "mmHg",
                            "system": "http://unitsofmeasure.org",
                            "code": "mm[Hg]"
                        },
                        "high": {
                            "value": max(bp_sbp_above, 140),
                            "unit": "mmHg",
                            "system": "http://unitsofmeasure.org",
                            "code": "mm[Hg]"
                        }
                    }
                }]
            }
            goals.append(goal)
        
        # SpO2 goals
        spo2_above = patient_doc.get("spo2_data_above", 0)
        if spo2_above > 0:
            goal = {
                "resourceType": "Goal",
                "id": str(uuid.uuid4()),
                "lifecycleStatus": "active",
                "category": [{
                    "coding": [{
                        "system": "http://terminology.hl7.org/CodeSystem/goal-category",
                        "code": "physiological",
                        "display": "Physiological"
                    }]
                }],
                "description": {
                    "text": f"Maintain oxygen saturation above {spo2_above}%"
                },
                "subject": {
                    "reference": f"Patient/{patient_id}"
                },
                "target": [{
                    "measure": {
                        "coding": [{
                            "system": "http://loinc.org",
                            "code": "59408-5",
                            "display": "Oxygen saturation in Arterial blood by Pulse oximetry"
                        }]
                    },
                    "detailQuantity": {
                        "value": spo2_above,
                        "unit": "%",
                        "system": "http://unitsofmeasure.org",
                        "code": "%"
                    }
                }]
            }
            goals.append(goal)
        
        return goals

    async def _create_weight_management_goals(self, patient_id: str, patient_doc: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create FHIR Goal resources for weight management"""
        goals = []
        
        weight_above = patient_doc.get("weight_scale_above", 0)
        weight_below = patient_doc.get("weight_scale_below", 0)
        
        if weight_above > 0 or weight_below > 0:
            goal = {
                "resourceType": "Goal",
                "id": str(uuid.uuid4()),
                "lifecycleStatus": "active",
                "category": [{
                    "coding": [{
                        "system": "http://terminology.hl7.org/CodeSystem/goal-category",
                        "code": "physiological",
                        "display": "Physiological"
                    }]
                }],
                "description": {
                    "text": f"Maintain weight within target range"
                },
                "subject": {
                    "reference": f"Patient/{patient_id}"
                },
                "target": [{
                    "measure": {
                        "coding": [{
                            "system": "http://loinc.org",
                            "code": "29463-7",
                            "display": "Body weight"
                        }]
                    },
                    "detailRange": {
                        "low": {
                            "value": weight_below if weight_below > 0 else 50,
                            "unit": "kg",
                            "system": "http://unitsofmeasure.org",
                            "code": "kg"
                        },
                        "high": {
                            "value": weight_above if weight_above > 0 else 100,
                            "unit": "kg",
                            "system": "http://unitsofmeasure.org",
                            "code": "kg"
                        }
                    }
                }]
            }
            goals.append(goal)
        
        return goals

    async def migrate_emergency_contacts_to_fhir(self, patient_doc: Dict[str, Any]) -> List[str]:
        """Transform AMY emergency contact data to FHIR RelatedPerson resources"""
        related_person_ids = []
        
        try:
            patient_id = str(patient_doc.get("_id", ""))
            if not patient_id:
                logger.warning("No patient ID found in patient document")
                return related_person_ids
            
            # Create RelatedPerson for emergency contact
            emergency_name = patient_doc.get("emergency_contact_name", "")
            emergency_phone = patient_doc.get("emergency_contact_number", "")
            emergency_relation = patient_doc.get("emergency_contact_relation", "")
            emergency_title = patient_doc.get("emergency_contact_name_title", "")
            
            if emergency_name or emergency_phone:
                related_person = await self._create_emergency_contact_related_person(
                    patient_id, emergency_name, emergency_phone, emergency_relation, emergency_title
                )
                
                result = await self.create_fhir_resource(
                    "RelatedPerson", 
                    related_person,
                    source_system="amy_migration"
                )
                
                if result["success"]:
                    related_person_ids.append(result["resource_id"])
            
            logger.info(f"Created {len(related_person_ids)} related persons for patient {patient_id}")
            return related_person_ids
            
        except Exception as e:
            logger.error(f"Failed to migrate emergency contacts to FHIR: {e}")
            raise

    async def _create_emergency_contact_related_person(
        self,
        patient_id: str,
        name: str,
        phone: str,
        relation: str,
        title: str
    ) -> Dict[str, Any]:
        """Create FHIR RelatedPerson resource for emergency contact"""
        related_person_id = str(uuid.uuid4())
        
        # Parse name parts
        name_parts = name.strip().split() if name else []
        given_names = name_parts[:-1] if len(name_parts) > 1 else name_parts
        family_name = name_parts[-1] if len(name_parts) > 1 else ""
        
        related_person = {
            "resourceType": "RelatedPerson",
            "id": related_person_id,
            "active": True,
            "patient": {
                "reference": f"Patient/{patient_id}"
            },
            "relationship": [{
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/v3-RoleCode",
                    "code": self._map_relationship_code(relation),
                    "display": relation or "Emergency Contact"
                }],
                "text": relation or "Emergency Contact"
            }]
        }
        
        # Add name if available
        if name:
            related_person["name"] = [{
                "use": "usual",
                "text": f"{title} {name}".strip(),
                "family": family_name,
                "given": given_names,
                "prefix": [title] if title else []
            }]
        
        # Add telecom if available
        if phone:
            related_person["telecom"] = [{
                "system": "phone",
                "value": phone,
                "use": "mobile",
                "rank": 1
            }]
        
        return related_person

    def _map_relationship_code(self, relation: str) -> str:
        """Map AMY relationship to FHIR relationship code"""
        relation_mappings = {
            "spouse": "SPS",
            "mother": "MTH",
            "father": "FTH",
            "son": "SON",
            "daughter": "DAU",
            "brother": "BRO",
            "sister": "SIS",
            "friend": "FRND",
            "emergency": "ECON"
        }
        
        return relation_mappings.get(relation.lower(), "ECON")

    async def migrate_patient_alerts_to_flags(self, patient_doc: Dict[str, Any]) -> List[str]:
        """Transform AMY patient alert data to FHIR Flag resources"""
        flag_ids = []
        
        try:
            patient_id = str(patient_doc.get("_id", ""))
            if not patient_id:
                logger.warning("No patient ID found in patient document")
                return flag_ids
            
            # Create flags for triage level
            triage_data = patient_doc.get("TriageLevel_info", [])
            for triage in triage_data:
                flag = await self._create_triage_flag(patient_id, triage)
                result = await self.create_fhir_resource("Flag", flag, source_system="amy_migration")
                if result["success"]:
                    flag_ids.append(result["resource_id"])
            
            # Create flags for notification settings
            notify_info = patient_doc.get("notify_info", [])
            for notify in notify_info:
                if notify.get("is_notify", False):
                    flag = await self._create_notification_flag(patient_id, notify)
                    result = await self.create_fhir_resource("Flag", flag, source_system="amy_migration")
                    if result["success"]:
                        flag_ids.append(result["resource_id"])
            
            # Create flags for admission status
            admit_status = patient_doc.get("admit_status", 0)
            if admit_status == 1:
                flag = await self._create_admission_flag(patient_id, patient_doc)
                result = await self.create_fhir_resource("Flag", flag, source_system="amy_migration")
                if result["success"]:
                    flag_ids.append(result["resource_id"])
            
            logger.info(f"Created {len(flag_ids)} flags for patient {patient_id}")
            return flag_ids
            
        except Exception as e:
            logger.error(f"Failed to migrate patient alerts to flags: {e}")
            raise

    async def _create_triage_flag(self, patient_id: str, triage_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create FHIR Flag resource for triage level"""
        flag_id = str(uuid.uuid4())
        
        current_level = triage_data.get("currentTriageLevel", "WHITE")
        temp_color = triage_data.get("tempTriagecolor", current_level)
        
        # Map triage colors to severity
        severity_map = {
            "RED": {"code": "H", "display": "High", "color": "red"},
            "YELLOW": {"code": "M", "display": "Medium", "color": "yellow"},
            "GREEN": {"code": "L", "display": "Low", "color": "green"},
            "WHITE": {"code": "L", "display": "Low", "color": "white"}
        }
        
        severity = severity_map.get(current_level, severity_map["WHITE"])
        
        return {
            "resourceType": "Flag",
            "id": flag_id,
            "status": "active",
            "category": [{
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/flag-category",
                    "code": "clinical",
                    "display": "Clinical"
                }]
            }],
            "code": {
                "coding": [{
                    "system": "http://snomed.info/sct",
                    "code": "225728007",
                    "display": "Triage assessment"
                }],
                "text": f"Triage Level: {current_level}"
            },
            "subject": {
                "reference": f"Patient/{patient_id}"
            },
            "period": {
                "start": datetime.utcnow().strftime("%Y-%m-%d")
            }
        }

    async def _create_notification_flag(self, patient_id: str, notify_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create FHIR Flag resource for notification settings"""
        flag_id = str(uuid.uuid4())
        
        is_telegram = notify_data.get("is_telegram_notify", False)
        
        return {
            "resourceType": "Flag",
            "id": flag_id,
            "status": "active",
            "category": [{
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/flag-category",
                    "code": "administrative",
                    "display": "Administrative"
                }]
            }],
            "code": {
                "coding": [{
                    "system": "http://snomed.info/sct",
                    "code": "182836005",
                    "display": "Review of medication"
                }],
                "text": f"Notifications enabled {'(Telegram)' if is_telegram else '(Standard)'}"
            },
            "subject": {
                "reference": f"Patient/{patient_id}"
            }
        }

    async def _create_admission_flag(self, patient_id: str, patient_doc: Dict[str, Any]) -> Dict[str, Any]:
        """Create FHIR Flag resource for admission status"""
        flag_id = str(uuid.uuid4())
        
        admit_at = patient_doc.get("admit_at")
        ward_info = patient_doc.get("ward_info", [])
        
        return {
            "resourceType": "Flag",
            "id": flag_id,
            "status": "active",
            "category": [{
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/flag-category",
                    "code": "clinical",
                    "display": "Clinical"
                }]
            }],
            "code": {
                "coding": [{
                    "system": "http://snomed.info/sct",
                    "code": "32485007",
                    "display": "Admission to hospital"
                }],
                "text": "Patient currently admitted"
            },
            "subject": {
                "reference": f"Patient/{patient_id}"
            },
            "period": {
                "start": self._convert_timestamp(admit_at).strftime("%Y-%m-%d") if admit_at else datetime.utcnow().strftime("%Y-%m-%d")
            }
        }

    async def migrate_patient_devices_to_fhir(self, patient_doc: Dict[str, Any]) -> List[str]:
        """Transform AMY patient device data to FHIR Device resources"""
        device_ids = []
        
        try:
            patient_id = str(patient_doc.get("_id", ""))
            
            # Map device fields from patient document
            device_mappings = [
                ("watch_mac_address", "smartwatch", patient_doc.get("watch_model_name", "Smart Watch")),
                ("blood_pressure_mac_address", "blood_pressure_monitor", "Blood Pressure Monitor"),
                ("blood_glucose_mac_address", "glucose_meter", "Blood Glucose Meter"),
                ("body_temperature_mac_address", "thermometer", "Body Temperature Monitor"),
                ("fingertip_pulse_oximeter_mac_address", "pulse_oximeter", "Fingertip Pulse Oximeter"),
                ("weight_scale_mac_address", "weight_scale", "Weight Scale"),
                ("cholesterol_mac_address", "cholesterol_meter", "Cholesterol Meter"),
                ("uric_mac_address", "uric_acid_meter", "Uric Acid Meter"),
                ("salt_meter_mac_address", "salt_meter", "Salt Meter")
            ]
            
            for mac_field, device_type, display_name in device_mappings:
                mac_address = patient_doc.get(mac_field, "")
                if mac_address:
                    device = await self._create_medical_device(
                        mac_address, device_type, display_name, patient_id
                    )
                    
                    result = await self.create_fhir_resource(
                        "Device", 
                        device,
                        source_system="amy_migration"
                    )
                    
                    if result["success"]:
                        device_ids.append(result["resource_id"])
            
            logger.info(f"Created {len(device_ids)} devices for patient {patient_id}")
            return device_ids
            
        except Exception as e:
            logger.error(f"Failed to migrate patient devices to FHIR: {e}")
            raise

    async def _create_medical_device(
        self, 
        mac_address: str, 
        device_type: str, 
        display_name: str,
        patient_id: str
    ) -> Dict[str, Any]:
        """Create FHIR Device resource for medical device"""
        device_id = str(uuid.uuid4())
        
        # Map device types to SNOMED codes
        device_codes = {
            "smartwatch": {"code": "706689003", "display": "Activity tracker"},
            "blood_pressure_monitor": {"code": "43770009", "display": "Blood pressure monitor"},
            "glucose_meter": {"code": "33747003", "display": "Blood glucose meter"},
            "thermometer": {"code": "34263000", "display": "Digital thermometer"},
            "pulse_oximeter": {"code": "448337001", "display": "Pulse oximeter"},
            "weight_scale": {"code": "462242008", "display": "Patient scale"},
            "cholesterol_meter": {"code": "700615001", "display": "Point of care cholesterol analyzer"},
            "uric_acid_meter": {"code": "700616000", "display": "Point of care uric acid analyzer"},
            "salt_meter": {"code": "462242008", "display": "Electrolyte analyzer"}
        }
        
        device_info = device_codes.get(device_type, {"code": "462242008", "display": "Medical device"})
        
        return {
            "resourceType": "Device",
            "id": device_id,
            "identifier": [{
                "type": {
                    "coding": [{
                        "system": "http://terminology.hl7.org/CodeSystem/v2-0203",
                        "code": "MAC",
                        "display": "MAC Address"
                    }]
                },
                "system": "urn:ieee:mac",
                "value": mac_address
            }],
            "status": "active",
            "manufacturer": "My FirstCare",
            "deviceName": [{
                "name": display_name,
                "type": "model-name"
            }],
            "type": [{
                "coding": [{
                    "system": "http://snomed.info/sct",
                    "code": device_info["code"],
                    "display": device_info["display"]
                }]
            }],
            "patient": {
                "reference": f"Patient/{patient_id}"
            },
            "contact": [{
                "system": "url",
                "value": "https://my-firstcare.com"
            }],
            "note": [{
                "text": f"Medical device registered for patient monitoring - MAC: {mac_address}"
            }]
        }

    # =============== Comprehensive AMY Migration Method ===============

    async def migrate_comprehensive_patient_to_fhir(self, patient_doc: Dict[str, Any]) -> Dict[str, Any]:
        """Comprehensive migration of AMY patient data to all relevant FHIR resources"""
        migration_results = {
            "patient_id": "",
            "fhir_resources": {
                "Patient": [],
                "Goal": [],
                "RelatedPerson": [],
                "Flag": [],
                "Device": [],
                "Condition": [],
                "AllergyIntolerance": [],
                "MedicationStatement": [],
                "Observation": []
            },
            "errors": []
        }
        
        try:
            # 1. Migrate core patient data
            patient_id = await self.migrate_existing_patient_to_fhir(patient_doc)
            migration_results["patient_id"] = patient_id
            migration_results["fhir_resources"]["Patient"].append(patient_id)
            
            # 2. Migrate patient goals
            try:
                goal_ids = await self.migrate_patient_goals_to_fhir(patient_doc)
                migration_results["fhir_resources"]["Goal"].extend(goal_ids)
            except Exception as e:
                migration_results["errors"].append(f"Goal migration failed: {e}")
            
            # 3. Migrate emergency contacts
            try:
                related_person_ids = await self.migrate_emergency_contacts_to_fhir(patient_doc)
                migration_results["fhir_resources"]["RelatedPerson"].extend(related_person_ids)
            except Exception as e:
                migration_results["errors"].append(f"RelatedPerson migration failed: {e}")
            
            # 4. Migrate patient alerts and flags
            try:
                flag_ids = await self.migrate_patient_alerts_to_flags(patient_doc)
                migration_results["fhir_resources"]["Flag"].extend(flag_ids)
            except Exception as e:
                migration_results["errors"].append(f"Flag migration failed: {e}")
            
            # 5. Migrate patient devices
            try:
                device_ids = await self.migrate_patient_devices_to_fhir(patient_doc)
                migration_results["fhir_resources"]["Device"].extend(device_ids)
            except Exception as e:
                migration_results["errors"].append(f"Device migration failed: {e}")
            
            # 6. Migrate conditions (underlying diseases)
            try:
                underlying_diseases = patient_doc.get("underlying_desease", [])
                for disease in underlying_diseases:
                    if disease:  # Check if disease object is not empty
                        condition_ids = await self.migrate_underlying_disease_to_condition(disease, patient_id)
                        migration_results["fhir_resources"]["Condition"].extend(condition_ids)
            except Exception as e:
                migration_results["errors"].append(f"Condition migration failed: {e}")
            
            # 7. Migrate allergies
            try:
                allergy_detail = patient_doc.get("allergy_detail", "")
                if allergy_detail:
                    allergy_ids = await self.migrate_allergy_text_to_fhir(allergy_detail, patient_id)
                    migration_results["fhir_resources"]["AllergyIntolerance"].extend(allergy_ids)
            except Exception as e:
                migration_results["errors"].append(f"AllergyIntolerance migration failed: {e}")
            
            # 8. Migrate medications
            try:
                medication_detail = patient_doc.get("medication_detail", "")
                if medication_detail:
                    med_ids = await self.migrate_medication_text_to_fhir(medication_detail, patient_id)
                    migration_results["fhir_resources"]["MedicationStatement"].extend(med_ids)
            except Exception as e:
                migration_results["errors"].append(f"MedicationStatement migration failed: {e}")
            
            # 9. Migrate vital sign observations
            try:
                obs_ids = await self.migrate_patient_vitals_to_observations(patient_doc)
                migration_results["fhir_resources"]["Observation"].extend(obs_ids)
            except Exception as e:
                migration_results["errors"].append(f"Observation migration failed: {e}")
            
            total_resources = sum(len(resources) for resources in migration_results["fhir_resources"].values())
            logger.info(f"Comprehensive migration completed for patient {patient_id}: {total_resources} FHIR resources created")
            
            return migration_results
            
        except Exception as e:
            logger.error(f"Comprehensive patient migration failed: {e}")
            migration_results["errors"].append(f"Migration failed: {e}")
            return migration_results

    async def migrate_underlying_disease_to_condition(self, disease_data: Dict[str, Any], patient_id: str) -> List[str]:
        """Transform underlying disease data to FHIR Condition resource"""
        condition_ids = []
        
        try:
            condition_id = str(uuid.uuid4())
            
            condition = {
                "resourceType": "Condition",
                "id": condition_id,
                "clinicalStatus": {
                    "coding": [{
                        "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                        "code": "active",
                        "display": "Active"
                    }]
                },
                "verificationStatus": {
                    "coding": [{
                        "system": "http://terminology.hl7.org/CodeSystem/condition-ver-status",
                        "code": "confirmed",
                        "display": "Confirmed"
                    }]
                },
                "category": [{
                    "coding": [{
                        "system": "http://terminology.hl7.org/CodeSystem/condition-category",
                        "code": "problem-list-item",
                        "display": "Problem List Item"
                    }]
                }],
                "code": {
                    "text": str(disease_data.get("name", "Underlying disease"))
                },
                "subject": {
                    "reference": f"Patient/{patient_id}"
                },
                "recordedDate": datetime.utcnow().strftime("%Y-%m-%d")
            }
            
            result = await self.create_fhir_resource("Condition", condition, source_system="amy_migration")
            if result["success"]:
                condition_ids.append(result["resource_id"])
            
            return condition_ids
            
        except Exception as e:
            logger.error(f"Failed to migrate underlying disease to condition: {e}")
            return condition_ids

    async def migrate_allergy_text_to_fhir(self, allergy_text: str, patient_id: str) -> List[str]:
        """Transform allergy text to FHIR AllergyIntolerance resource"""
        allergy_ids = []
        
        try:
            allergy_id = str(uuid.uuid4())
            
            allergy = {
                "resourceType": "AllergyIntolerance",
                "id": allergy_id,
                "clinicalStatus": {
                    "coding": [{
                        "system": "http://terminology.hl7.org/CodeSystem/allergyintolerance-clinical",
                        "code": "active",
                        "display": "Active"
                    }]
                },
                "verificationStatus": {
                    "coding": [{
                        "system": "http://terminology.hl7.org/CodeSystem/allergyintolerance-verification",
                        "code": "confirmed",
                        "display": "Confirmed"
                    }]
                },
                "category": ["medication", "food", "environment"],
                "criticality": "low",
                "code": {
                    "text": allergy_text
                },
                "patient": {
                    "reference": f"Patient/{patient_id}"
                },
                "recordedDate": datetime.utcnow().strftime("%Y-%m-%d"),
                "note": [{
                    "text": f"Allergy information from patient record: {allergy_text}"
                }]
            }
            
            result = await self.create_fhir_resource("AllergyIntolerance", allergy, source_system="amy_migration")
            if result["success"]:
                allergy_ids.append(result["resource_id"])
            
            return allergy_ids
            
        except Exception as e:
            logger.error(f"Failed to migrate allergy text to FHIR: {e}")
            return allergy_ids

    async def migrate_medication_text_to_fhir(self, medication_text: str, patient_id: str) -> List[str]:
        """Transform medication text to FHIR MedicationStatement resource"""
        medication_ids = []
        
        try:
            medication_id = str(uuid.uuid4())
            
            medication_statement = {
                "resourceType": "MedicationStatement",
                "id": medication_id,
                "status": "active",
                "medicationCodeableConcept": {
                    "text": medication_text
                },
                "subject": {
                    "reference": f"Patient/{patient_id}"
                },
                "effectiveDateTime": datetime.utcnow().strftime("%Y-%m-%d"),
                "dateAsserted": datetime.utcnow().strftime("%Y-%m-%d"),
                "note": [{
                    "text": f"Medication information from patient record: {medication_text}"
                }]
            }
            
            result = await self.create_fhir_resource("MedicationStatement", medication_statement, source_system="amy_migration")
            if result["success"]:
                medication_ids.append(result["resource_id"])
            
            return medication_ids
            
        except Exception as e:
            logger.error(f"Failed to migrate medication text to FHIR: {e}")
            return medication_ids

    async def migrate_patient_vitals_to_observations(self, patient_doc: Dict[str, Any]) -> List[str]:
        """Transform patient vital signs to FHIR Observation resources"""
        observation_ids = []
        
        try:
            patient_id = str(patient_doc.get("_id", ""))
            
            # Vital sign mappings
            vital_mappings = [
                ("sys_data", "8480-6", "Systolic blood pressure", "mmHg"),
                ("dia_data", "8462-4", "Diastolic blood pressure", "mmHg"),
                ("pr_data", "8867-4", "Heart rate", "beats/min"),
                ("spo2_data", "59408-5", "Oxygen saturation", "%"),
                ("temprature_data", "8310-5", "Body temperature", "Cel"),
                ("weight", "29463-7", "Body weight", "kg"),
                ("height", "8302-2", "Body height", "cm"),
                ("bmi", "39156-5", "Body mass index", "kg/m2")
            ]
            
            for field, loinc_code, display, unit in vital_mappings:
                value = patient_doc.get(field)
                if value and value != 0:
                    observation = await self._create_vital_observation(
                        patient_id, field, value, loinc_code, display, unit, patient_doc
                    )
                    
                    result = await self.create_fhir_resource("Observation", observation, source_system="amy_migration")
                    if result["success"]:
                        observation_ids.append(result["resource_id"])
            
            return observation_ids
            
        except Exception as e:
            logger.error(f"Failed to migrate patient vitals to observations: {e}")
            return observation_ids

    async def _create_vital_observation(
        self,
        patient_id: str,
        field: str,
        value: Union[int, float],
        loinc_code: str,
        display: str,
        unit: str,
        patient_doc: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create FHIR Observation for vital sign"""
        observation_id = str(uuid.uuid4())
        
        return {
            "resourceType": "Observation",
            "id": observation_id,
            "status": "final",
            "category": [{
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                    "code": "vital-signs",
                    "display": "Vital Signs"
                }]
            }],
            "code": {
                "coding": [{
                    "system": "http://loinc.org",
                    "code": loinc_code,
                    "display": display
                }]
            },
            "subject": {
                "reference": f"Patient/{patient_id}"
            },
            "effectiveDateTime": self._convert_timestamp(
                patient_doc.get("updated_at", patient_doc.get("created_at"))
            ).isoformat() + "Z",
            "valueQuantity": {
                "value": float(value),
                "unit": unit,
                "system": "http://unitsofmeasure.org"
            }
        }

    # =============== Blockchain Hash Verification Methods ===============

    async def verify_fhir_resource_integrity(
        self,
        resource_type: str,
        resource_id: str
    ) -> Dict[str, Any]:
        """Verify the blockchain hash integrity of a FHIR resource"""
        try:
            collection = mongodb_service.get_fhir_collection(self.fhir_collections[resource_type])
            doc = await collection.find_one({
                "resource_id": resource_id,
                "is_deleted": False
            })
            
            if not doc:
                raise ValueError(f"FHIR {resource_type} {resource_id} not found")
            
            # Get stored blockchain data
            stored_hash = doc.get("blockchain_hash")
            previous_hash = doc.get("blockchain_previous_hash")
            
            if not stored_hash:
                return {
                    "verified": False,
                    "message": "No blockchain hash found for resource",
                    "resource_id": resource_id,
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }
            
            # Verify integrity using blockchain service
            verification_result = blockchain_hash_service.verify_resource_integrity(
                resource_data=doc["resource_data"],
                stored_hash=stored_hash,
                previous_hash=previous_hash
            )
            
            # Update verification status in database
            await collection.update_one(
                {"resource_id": resource_id},
                {
                    "$set": {
                        "blockchain_verified": verification_result.is_valid,
                        "blockchain_verification_date": datetime.utcnow()
                    }
                }
            )
            
            logger.info(f"Verified FHIR {resource_type} {resource_id}: {verification_result.message}")
            
            return {
                "verified": verification_result.is_valid,
                "message": verification_result.message,
                "resource_id": resource_id,
                "stored_hash": verification_result.stored_hash,
                "computed_hash": verification_result.current_hash,
                "tampered": verification_result.tampered,
                "verification_timestamp": verification_result.timestamp,
                "blockchain_metadata": {
                    "hash": stored_hash,
                    "previous_hash": previous_hash,
                    "block_height": doc.get("blockchain_block_height"),
                    "merkle_root": doc.get("blockchain_merkle_root"),
                    "timestamp": doc.get("blockchain_timestamp")
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to verify FHIR {resource_type} {resource_id}: {e}")
            raise

    async def verify_fhir_batch_integrity(
        self,
        resource_type: str,
        resource_ids: List[str]
    ) -> Dict[str, Any]:
        """Verify the integrity of a batch of FHIR resources"""
        try:
            verification_results = []
            valid_count = 0
            invalid_count = 0
            
            for resource_id in resource_ids:
                try:
                    result = await self.verify_fhir_resource_integrity(resource_type, resource_id)
                    verification_results.append({
                        "resource_id": resource_id,
                        "verified": result["verified"],
                        "message": result["message"]
                    })
                    
                    if result["verified"]:
                        valid_count += 1
                    else:
                        invalid_count += 1
                        
                except Exception as e:
                    verification_results.append({
                        "resource_id": resource_id,
                        "verified": False,
                        "message": f"Verification failed: {str(e)}"
                    })
                    invalid_count += 1
            
            overall_valid = invalid_count == 0
            
            return {
                "batch_verified": overall_valid,
                "total_resources": len(resource_ids),
                "valid_count": valid_count,
                "invalid_count": invalid_count,
                "verification_results": verification_results,
                "verification_timestamp": datetime.utcnow().isoformat() + "Z"
            }
            
        except Exception as e:
            logger.error(f"Failed to verify FHIR batch integrity: {e}")
            raise

    async def get_blockchain_chain_info(self) -> Dict[str, Any]:
        """Get information about the blockchain hash chain"""
        try:
            chain_info = blockchain_hash_service.get_hash_chain_info()
            
            # Add FHIR-specific statistics
            total_resources = 0
            verified_resources = 0
            
            for resource_type, collection_name in self.fhir_collections.items():
                collection = mongodb_service.get_fhir_collection(collection_name)
                
                type_total = await collection.count_documents({"is_deleted": False})
                type_verified = await collection.count_documents({
                    "is_deleted": False,
                    "blockchain_verified": True
                })
                
                total_resources += type_total
                verified_resources += type_verified
            
            return {
                "chain_info": chain_info,
                "fhir_statistics": {
                    "total_resources": total_resources,
                    "verified_resources": verified_resources,
                    "verification_rate": (verified_resources / total_resources * 100) if total_resources > 0 else 0
                },
                "resource_type_counts": {
                    resource_type: await mongodb_service.get_fhir_collection(collection_name).count_documents({"is_deleted": False})
                    for resource_type, collection_name in self.fhir_collections.items()
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get blockchain chain info: {e}")
            raise

    async def export_blockchain_chain(self) -> Dict[str, Any]:
        """Export the complete blockchain hash chain"""
        try:
            return blockchain_hash_service.export_hash_chain()
        except Exception as e:
            logger.error(f"Failed to export blockchain chain: {e}")
            raise

    async def verify_hash_chain_integrity(self) -> Dict[str, Any]:
        """Verify the integrity of the entire hash chain"""
        try:
            return blockchain_hash_service.verify_hash_chain()
        except Exception as e:
            logger.error(f"Failed to verify hash chain integrity: {e}")
            raise

# Global service instance
fhir_service = FHIRR5Service() 