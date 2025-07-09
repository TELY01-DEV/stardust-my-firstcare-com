"""
Kati Watch to FHIR R5 Integration Service
========================================
Converts real-time IoT data from Kati Watch devices to FHIR R5 resources.

This service processes MQTT messages from the MQTTDataParser and creates
appropriate FHIR resources linked to patient records.

Data Flow:
    Kati Watch → MQTT Parser → This Service → FHIR R5 Resources → Patient Records
"""

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from bson import ObjectId

from app.services.fhir_r5_service import FHIRR5Service
from app.services.mongo import mongodb_service
from app.utils.structured_logging import get_logger

logger = get_logger(__name__)

class KatiWatchFHIRService:
    """Service for converting Kati Watch MQTT data to FHIR R5 resources"""
    
    def __init__(self):
        self.fhir_service = FHIRR5Service()
        # IMEI to Patient mapping cache
        self.imei_patient_cache = {}
        
    async def process_mqtt_message(self, topic: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process MQTT message from Kati Watch and create FHIR resources
        
        Args:
            topic: MQTT topic (e.g., 'iMEDE_watch/VitalSign')
            payload: Parsed message payload
            
        Returns:
            Dictionary with processing results and created resource IDs
        """
        try:
            imei = payload.get('IMEI')
            if not imei:
                raise ValueError("IMEI not found in payload")
                
            # Get patient reference from IMEI
            patient_ref = await self._get_patient_reference_from_imei(imei)
            if not patient_ref:
                logger.warning(f"No patient found for IMEI: {imei}")
                return {"status": "skipped", "reason": "patient_not_found", "imei": imei}
            
            # Route to appropriate processor based on topic
            if topic == 'iMEDE_watch/VitalSign':
                return await self._process_vital_signs(payload, patient_ref)
            elif topic == 'iMEDE_watch/AP55':
                return await self._process_batch_health_data(payload, patient_ref)
            elif topic == 'iMEDE_watch/location':
                return await self._process_location_data(payload, patient_ref)
            elif topic == 'iMEDE_watch/sleepdata':
                return await self._process_sleep_data(payload, patient_ref)
            elif topic == 'iMEDE_watch/sos':
                return await self._process_emergency_alert(payload, patient_ref, "SOS")
            elif topic == 'iMEDE_watch/fallDown':
                return await self._process_emergency_alert(payload, patient_ref, "FALL_DOWN")
            elif topic == 'iMEDE_watch/hb':
                return await self._process_heartbeat_status(payload, patient_ref)
            else:
                logger.warning(f"Unknown MQTT topic: {topic}")
                return {"status": "skipped", "reason": "unknown_topic", "topic": topic}
                
        except Exception as e:
            logger.error(f"Failed to process MQTT message: {e}")
            return {"status": "error", "error": str(e)}
    
    async def _get_patient_reference_from_imei(self, imei: str) -> Optional[str]:
        """Get FHIR Patient reference from device IMEI"""
        # Check cache first
        if imei in self.imei_patient_cache:
            return self.imei_patient_cache[imei]
            
        try:
            # Look up device registration in database
            device_collection = mongodb_service.get_collection("device_registrations")
            device_doc = await device_collection.find_one({"imei": imei})
            
            if device_doc and device_doc.get("patient_id"):
                patient_id = str(device_doc["patient_id"])
                patient_ref = f"Patient/{patient_id}"
                
                # Cache the mapping
                self.imei_patient_cache[imei] = patient_ref
                return patient_ref
                
        except Exception as e:
            logger.error(f"Failed to lookup patient for IMEI {imei}: {e}")
            
        return None
    
    async def _process_vital_signs(self, payload: Dict[str, Any], patient_ref: str) -> Dict[str, Any]:
        """Process vital signs data and create FHIR Observation resources"""
        results = {"status": "success", "observations": []}
        timestamp = payload.get('timeStamps', datetime.now(timezone.utc).isoformat())
        
        # Heart Rate Observation
        if 'heartRate' in payload:
            heart_rate_obs = {
                "resourceType": "Observation",
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
                        "code": "8867-4",
                        "display": "Heart rate"
                    }]
                },
                "subject": {"reference": patient_ref},
                "effectiveDateTime": timestamp,
                "valueQuantity": {
                    "value": payload['heartRate'],
                    "unit": "beats/min",
                    "system": "http://unitsofmeasure.org",
                    "code": "/min"
                },
                "device": {
                    "display": f"Kati Watch IMEI: {payload.get('IMEI')}"
                }
            }
            
            obs_result = await self.fhir_service.create_fhir_resource("Observation", heart_rate_obs)
            results["observations"].append({"type": "heart_rate", "id": obs_result["resource_id"]})
        
        # Blood Pressure Observation
        if 'bloodPressure' in payload:
            bp_data = payload['bloodPressure']
            bp_obs = {
                "resourceType": "Observation",
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
                "subject": {"reference": patient_ref},
                "effectiveDateTime": timestamp,
                "component": [
                    {
                        "code": {
                            "coding": [{
                                "system": "http://loinc.org",
                                "code": "8480-6",
                                "display": "Systolic blood pressure"
                            }]
                        },
                        "valueQuantity": {
                            "value": bp_data.get('bp_sys'),
                            "unit": "mmHg",
                            "system": "http://unitsofmeasure.org",
                            "code": "mm[Hg]"
                        }
                    },
                    {
                        "code": {
                            "coding": [{
                                "system": "http://loinc.org", 
                                "code": "8462-4",
                                "display": "Diastolic blood pressure"
                            }]
                        },
                        "valueQuantity": {
                            "value": bp_data.get('bp_dia'),
                            "unit": "mmHg",
                            "system": "http://unitsofmeasure.org",
                            "code": "mm[Hg]"
                        }
                    }
                ],
                "device": {
                    "display": f"Kati Watch IMEI: {payload.get('IMEI')}"
                }
            }
            
            obs_result = await self.fhir_service.create_fhir_resource("Observation", bp_obs)
            results["observations"].append({"type": "blood_pressure", "id": obs_result["resource_id"]})
        
        # SpO2 Observation
        if 'spO2' in payload:
            spo2_obs = {
                "resourceType": "Observation",
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
                        "code": "2708-6",
                        "display": "Oxygen saturation in Arterial blood"
                    }]
                },
                "subject": {"reference": patient_ref},
                "effectiveDateTime": timestamp,
                "valueQuantity": {
                    "value": payload['spO2'],
                    "unit": "%",
                    "system": "http://unitsofmeasure.org",
                    "code": "%"
                },
                "device": {
                    "display": f"Kati Watch IMEI: {payload.get('IMEI')}"
                }
            }
            
            obs_result = await self.fhir_service.create_fhir_resource("Observation", spo2_obs)
            results["observations"].append({"type": "spo2", "id": obs_result["resource_id"]})
        
        # Body Temperature Observation
        if 'bodyTemperature' in payload:
            temp_obs = {
                "resourceType": "Observation",
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
                "subject": {"reference": patient_ref},
                "effectiveDateTime": timestamp,
                "valueQuantity": {
                    "value": payload['bodyTemperature'],
                    "unit": "Cel",
                    "system": "http://unitsofmeasure.org",
                    "code": "Cel"
                },
                "device": {
                    "display": f"Kati Watch IMEI: {payload.get('IMEI')}"
                }
            }
            
            obs_result = await self.fhir_service.create_fhir_resource("Observation", temp_obs)
            results["observations"].append({"type": "temperature", "id": obs_result["resource_id"]})
        
        logger.info(f"Created {len(results['observations'])} vital sign observations for patient {patient_ref}")
        return results
    
    async def _process_batch_health_data(self, payload: Dict[str, Any], patient_ref: str) -> Dict[str, Any]:
        """Process AP55 batch health data and create multiple FHIR Observations"""
        results = {"status": "success", "observations": []}
        
        data_points = payload.get('data', [])
        logger.info(f"Processing {len(data_points)} batch health data points")
        
        imei = payload.get('IMEI', 'unknown')
        
        for data_point in data_points:
            # Convert timestamp to ISO format
            timestamp = datetime.fromtimestamp(data_point.get('timestamp', 0), tz=timezone.utc).isoformat()
            
            # Create individual observations for each vital sign
            for vital_type, value in data_point.items():
                if vital_type == 'timestamp':
                    continue
                    
                if vital_type == 'heartRate' and value:
                    obs = await self._create_heart_rate_observation(value, timestamp, patient_ref, imei)
                    results["observations"].append({"type": "heart_rate", "id": obs["resource_id"]})
                    
                elif vital_type == 'bloodPressure' and value:
                    obs = await self._create_blood_pressure_observation(value, timestamp, patient_ref, imei)
                    results["observations"].append({"type": "blood_pressure", "id": obs["resource_id"]})
                    
                elif vital_type == 'spO2' and value:
                    obs = await self._create_spo2_observation(value, timestamp, patient_ref, imei)
                    results["observations"].append({"type": "spo2", "id": obs["resource_id"]})
                    
                elif vital_type == 'bodyTemperature' and value:
                    obs = await self._create_temperature_observation(value, timestamp, patient_ref, imei)
                    results["observations"].append({"type": "temperature", "id": obs["resource_id"]})
        
        logger.info(f"Created {len(results['observations'])} batch observations for patient {patient_ref}")
        return results
    
    async def _process_location_data(self, payload: Dict[str, Any], patient_ref: str) -> Dict[str, Any]:
        """Process location data and create FHIR Observation for location tracking"""
        location_data = payload.get('location', {})
        
        location_obs = {
            "resourceType": "Observation",
            "status": "final",
            "category": [{
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                    "code": "survey",
                    "display": "Survey"
                }]
            }],
            "code": {
                "coding": [{
                    "system": "http://loinc.org",
                    "code": "33747-0",
                    "display": "Patient location"
                }]
            },
            "subject": {"reference": patient_ref},
            "effectiveDateTime": datetime.now(timezone.utc).isoformat(),
            "device": {
                "display": f"Kati Watch IMEI: {payload.get('IMEI', 'unknown')}"
            }
        }
        
        # Add GPS coordinates if available
        if 'GPS' in location_data:
            gps = location_data['GPS']
            location_obs['component'] = [
                {
                    "code": {"coding": [{"system": "http://loinc.org", "code": "33748-8", "display": "GPS Latitude"}]},
                    "valueQuantity": {"value": gps.get('latitude'), "unit": "deg"}
                },
                {
                    "code": {"coding": [{"system": "http://loinc.org", "code": "33749-6", "display": "GPS Longitude"}]},
                    "valueQuantity": {"value": gps.get('longitude'), "unit": "deg"}
                }
            ]
            
        obs_result = await self.fhir_service.create_fhir_resource("Observation", location_obs)
        
        return {
            "status": "success",
            "observations": [{"type": "location", "id": obs_result["resource_id"]}]
        }
    
    async def _process_sleep_data(self, payload: Dict[str, Any], patient_ref: str) -> Dict[str, Any]:
        """Process sleep data and create FHIR Observation for sleep study"""
        sleep_data = payload.get('sleep', {})
        
        sleep_obs = {
            "resourceType": "Observation",
            "status": "final",
            "category": [{
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                    "code": "activity",
                    "display": "Activity"
                }]
            }],
            "code": {
                "coding": [{
                    "system": "http://loinc.org",
                    "code": "93832-4",
                    "display": "Sleep study"
                }]
            },
            "subject": {"reference": patient_ref},
            "effectiveDateTime": sleep_data.get('timeStamps'),
            "valueString": f"Sleep period: {sleep_data.get('time')}, Data points: {sleep_data.get('num')}",
            "component": [
                {
                    "code": {
                        "coding": [{
                            "system": "http://loinc.org",
                            "code": "93831-6",
                            "display": "Sleep period time"
                        }]
                    },
                    "valueString": sleep_data.get('time')
                },
                {
                    "code": {
                        "coding": [{
                            "system": "http://loinc.org", 
                            "code": "93833-2",
                            "display": "Sleep study raw data"
                        }]
                    },
                    "valueString": sleep_data.get('data')
                }
            ],
            "device": {
                "display": f"Kati Watch IMEI: {payload.get('IMEI')}"
            }
        }
        
        obs_result = await self.fhir_service.create_fhir_resource("Observation", sleep_obs)
        
        return {
            "status": "success",
            "observations": [{"type": "sleep_study", "id": obs_result["resource_id"]}]
        }
    
    async def _process_emergency_alert(self, payload: Dict[str, Any], patient_ref: str, alert_type: str) -> Dict[str, Any]:
        """Process emergency alerts (SOS, Fall Down) and create FHIR Observation"""
        
        alert_obs = {
            "resourceType": "Observation",
            "status": "final",
            "category": [{
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                    "code": "safety",
                    "display": "Safety"
                }]
            }],
            "code": {
                "coding": [{
                    "system": "http://snomed.info/sct",
                    "code": "182836005" if alert_type == "SOS" else "217082002",
                    "display": "Emergency alert" if alert_type == "SOS" else "Fall detected"
                }]
            },
            "subject": {"reference": patient_ref},
            "effectiveDateTime": datetime.now(timezone.utc).isoformat(),
            "valueString": payload.get('status', alert_type),
            "device": {
                "display": f"Kati Watch IMEI: {payload.get('IMEI')}"
            }
        }
        
        # Add location if available
        if 'location' in payload:
            location = payload['location']
            if 'GPS' in location:
                gps = location['GPS']
                alert_obs['component'] = [{
                    "code": {
                        "coding": [{
                            "system": "http://loinc.org",
                            "code": "33747-0",
                            "display": "Location"
                        }]
                    },
                    "valueString": f"GPS: {gps.get('latitude')}, {gps.get('longitude')}"
                }]
        
        obs_result = await self.fhir_service.create_fhir_resource("Observation", alert_obs)
        
        return {
            "status": "success",
            "alert_type": alert_type,
            "observations": [{"type": f"emergency_{alert_type.lower()}", "id": obs_result["resource_id"]}]
        }
    
    async def _process_heartbeat_status(self, payload: Dict[str, Any], patient_ref: str) -> Dict[str, Any]:
        """Process heartbeat/status data and create device status observation"""
        
        status_obs = {
            "resourceType": "Observation",
            "status": "final",
            "category": [{
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                    "code": "survey",
                    "display": "Survey"
                }]
            }],
            "code": {
                "coding": [{
                    "system": "http://loinc.org",
                    "code": "67504-6",
                    "display": "Device status"
                }]
            },
            "subject": {"reference": patient_ref},
            "effectiveDateTime": payload.get('timeStamps', datetime.now(timezone.utc).isoformat()),
            "component": [
                {
                    "code": {"coding": [{"system": "http://loinc.org", "code": "33747-0", "display": "Battery level"}]},
                    "valueQuantity": {"value": payload.get('battery'), "unit": "%"}
                },
                {
                    "code": {"coding": [{"system": "http://loinc.org", "code": "33748-8", "display": "Signal strength"}]},
                    "valueQuantity": {"value": payload.get('signalGSM'), "unit": "dBm"}
                },
                {
                    "code": {"coding": [{"system": "http://loinc.org", "code": "33749-6", "display": "Step count"}]},
                    "valueQuantity": {"value": payload.get('step'), "unit": "steps"}
                }
            ],
            "device": {
                "display": f"Kati Watch IMEI: {payload.get('IMEI')}"
            }
        }
        
        obs_result = await self.fhir_service.create_fhir_resource("Observation", status_obs)
        
        return {
            "status": "success",
            "observations": [{"type": "device_status", "id": obs_result["resource_id"]}]
        }
    
    # Helper methods for creating specific observation types
    async def _create_heart_rate_observation(self, value: int, timestamp: str, patient_ref: str, imei: str):
        """Create heart rate observation"""
        obs = {
            "resourceType": "Observation",
            "status": "final",
            "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "vital-signs"}]}],
            "code": {"coding": [{"system": "http://loinc.org", "code": "8867-4", "display": "Heart rate"}]},
            "subject": {"reference": patient_ref},
            "effectiveDateTime": timestamp,
            "valueQuantity": {"value": value, "unit": "beats/min", "system": "http://unitsofmeasure.org", "code": "/min"},
            "device": {"display": f"Kati Watch IMEI: {imei}"}
        }
        return await self.fhir_service.create_fhir_resource("Observation", obs)
    
    async def _create_blood_pressure_observation(self, bp_data: Dict, timestamp: str, patient_ref: str, imei: str):
        """Create blood pressure observation"""
        obs = {
            "resourceType": "Observation",
            "status": "final",
            "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "vital-signs"}]}],
            "code": {"coding": [{"system": "http://loinc.org", "code": "85354-9", "display": "Blood pressure panel"}]},
            "subject": {"reference": patient_ref},
            "effectiveDateTime": timestamp,
            "component": [
                {
                    "code": {"coding": [{"system": "http://loinc.org", "code": "8480-6", "display": "Systolic blood pressure"}]},
                    "valueQuantity": {"value": bp_data.get('bp_sys'), "unit": "mmHg", "system": "http://unitsofmeasure.org", "code": "mm[Hg]"}
                },
                {
                    "code": {"coding": [{"system": "http://loinc.org", "code": "8462-4", "display": "Diastolic blood pressure"}]},
                    "valueQuantity": {"value": bp_data.get('bp_dia'), "unit": "mmHg", "system": "http://unitsofmeasure.org", "code": "mm[Hg]"}
                }
            ],
            "device": {"display": f"Kati Watch IMEI: {imei}"}
        }
        return await self.fhir_service.create_fhir_resource("Observation", obs)
    
    async def _create_spo2_observation(self, value: int, timestamp: str, patient_ref: str, imei: str):
        """Create SpO2 observation"""
        obs = {
            "resourceType": "Observation",
            "status": "final",
            "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "vital-signs"}]}],
            "code": {"coding": [{"system": "http://loinc.org", "code": "2708-6", "display": "Oxygen saturation"}]},
            "subject": {"reference": patient_ref},
            "effectiveDateTime": timestamp,
            "valueQuantity": {"value": value, "unit": "%", "system": "http://unitsofmeasure.org", "code": "%"},
            "device": {"display": f"Kati Watch IMEI: {imei}"}
        }
        return await self.fhir_service.create_fhir_resource("Observation", obs)
    
    async def _create_temperature_observation(self, value: float, timestamp: str, patient_ref: str, imei: str):
        """Create temperature observation"""
        obs = {
            "resourceType": "Observation",
            "status": "final",
            "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "vital-signs"}]}],
            "code": {"coding": [{"system": "http://loinc.org", "code": "8310-5", "display": "Body temperature"}]},
            "subject": {"reference": patient_ref},
            "effectiveDateTime": timestamp,
            "valueQuantity": {"value": value, "unit": "Cel", "system": "http://unitsofmeasure.org", "code": "Cel"},
            "device": {"display": f"Kati Watch IMEI: {imei}"}
        }
        return await self.fhir_service.create_fhir_resource("Observation", obs) 