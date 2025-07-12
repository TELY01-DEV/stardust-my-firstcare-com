from datetime import datetime
from typing import Dict, Any, Optional
from bson import ObjectId
from app.services.mongo import mongodb_service
from config import logger

class AuditLogger:
    def __init__(self):
        self.collection_name = "fhir_provenance"
    
    async def log_device_data_received(self, device_id: str, device_type: str, data_type: str, 
                                      observation_id: str, user_id: Optional[str] = None):
        """Log device data reception as FHIR R5 Provenance"""
        try:
            provenance = {
                "resourceType": "Provenance",
                "recorded": datetime.utcnow().isoformat() + "Z",
                "agent": [
                    {
                        "type": {
                            "coding": [
                                {
                                    "system": "http://terminology.hl7.org/CodeSystem/provenance-participant-type",
                                    "code": "device",
                                    "display": "Device"
                                }
                            ],
                            "text": "device"
                        },
                        "who": {
                            "identifier": {
                                "system": "https://my-firstcare.com/devices",
                                "value": device_id
                            }
                        }
                    }
                ],
                "entity": [
                    {
                        "role": "source",
                        "what": {
                            "identifier": {
                                "system": "https://my-firstcare.com/observations",
                                "value": data_type
                            }
                        }
                    }
                ],
                "target": [
                    {
                        "reference": f"Observation/{observation_id}"
                    }
                ],
                "meta": {
                    "source": "https://opera.my-firstcare.com",
                    "profile": ["http://hl7.org/fhir/StructureDefinition/Provenance"]
                }
            }
            
            # Add user agent if available
            if user_id:
                provenance["agent"].append({
                    "type": {
                        "coding": [
                            {
                                "system": "http://terminology.hl7.org/CodeSystem/provenance-participant-type",
                                "code": "author",
                                "display": "Author"
                            }
                        ],
                        "text": "author"
                    },
                    "who": {
                        "identifier": {
                            "system": "https://stardust-v1.my-firstcare.com/users",
                            "value": user_id
                        }
                    }
                })
            
            # Save to audit log database
            collection = mongodb_service.get_collection(self.collection_name)
            result = await collection.insert_one(provenance)
            
            logger.info(f"Audit log created: {result.inserted_id} for device {device_id}")
            return str(result.inserted_id)
            
        except Exception as e:
            logger.error(f"Failed to create audit log: {e}")
            raise
    
    async def log_admin_action(self, action: str, resource_type: str, resource_id: str, 
                              user_id: str, details: Optional[Dict[str, Any]] = None):
        """Log admin panel actions as FHIR R5 Provenance"""
        try:
            provenance = {
                "resourceType": "Provenance",
                "recorded": datetime.utcnow().isoformat() + "Z",
                "agent": [
                    {
                        "type": {
                            "coding": [
                                {
                                    "system": "http://terminology.hl7.org/CodeSystem/provenance-participant-type",
                                    "code": "author",
                                    "display": "Author"
                                }
                            ],
                            "text": "author"
                        },
                        "who": {
                            "identifier": {
                                "system": "https://stardust-v1.my-firstcare.com/users",
                                "value": user_id
                            }
                        }
                    }
                ],
                "entity": [
                    {
                        "role": "source",
                        "what": {
                            "identifier": {
                                "system": "https://my-firstcare.com/admin-actions",
                                "value": action
                            }
                        }
                    }
                ],
                "target": [
                    {
                        "reference": f"{resource_type}/{resource_id}"
                    }
                ],
                "meta": {
                    "source": "https://opera.my-firstcare.com",
                    "profile": ["http://hl7.org/fhir/StructureDefinition/Provenance"]
                }
            }
            
            # Add details if provided
            if details:
                provenance["reason"] = [
                    {
                        "coding": [
                            {
                                "system": "https://my-firstcare.com/admin-actions",
                                "code": action,
                                "display": action
                            }
                        ]
                    }
                ]
                provenance["note"] = [
                    {
                        "text": str(details)
                    }
                ]
            
            # Save to audit log database
            collection = mongodb_service.get_collection(self.collection_name)
            result = await collection.insert_one(provenance)
            
            logger.info(f"Admin action logged: {action} by {user_id}")
            return str(result.inserted_id)
            
        except Exception as e:
            logger.error(f"Failed to log admin action: {e}")
            raise
    
    async def log_action(self, user_id: str, action: str, resource_type: str, resource_id: str, 
                        details: str, request_id: Optional[str] = None):
        """Log general actions as FHIR R5 Provenance (alias for log_admin_action)"""
        return await self.log_admin_action(
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            user_id=user_id,
            details={"details": details, "request_id": request_id}
        )
    
    async def get_audit_logs(self, limit: int = 100, skip: int = 0, 
                            resource_type: Optional[str] = None,
                            user_id: Optional[str] = None,
                            start_date: Optional[datetime] = None,
                            end_date: Optional[datetime] = None):
        """Retrieve audit logs with filtering"""
        try:
            collection = mongodb_service.get_collection(self.collection_name)
            
            # Build filter
            filter_query = {}
            
            if resource_type:
                filter_query["target.reference"] = {"$regex": f"^{resource_type}/"}
            
            if user_id:
                filter_query["agent.who.identifier.value"] = user_id
            
            if start_date or end_date:
                filter_query["recorded"] = {}
                if start_date:
                    filter_query["recorded"]["$gte"] = start_date.isoformat() + "Z"
                if end_date:
                    filter_query["recorded"]["$lte"] = end_date.isoformat() + "Z"
            
            # Get logs
            cursor = collection.find(filter_query).sort("recorded", -1).skip(skip).limit(limit)
            logs = await cursor.to_list(length=limit)
            
            return logs
            
        except Exception as e:
            logger.error(f"Failed to retrieve audit logs: {e}")
            raise

# Global audit logger instance
audit_logger = AuditLogger() 