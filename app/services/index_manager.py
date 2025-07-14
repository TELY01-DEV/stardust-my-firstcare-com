from typing import Dict, List, Any, Optional
from datetime import datetime
from pymongo import ASCENDING, DESCENDING, TEXT, GEO2D
from pymongo.errors import OperationFailure
from app.services.mongo import mongodb_service
from config import logger
import asyncio

class IndexManager:
    """
    MongoDB Index Manager for creating and managing database indexes
    to optimize query performance
    """
    
    def __init__(self):
        self.index_definitions = self._define_indexes()
        self.created_indexes = {}
    
    def _define_indexes(self) -> Dict[str, List[Dict[str, Any]]]:
        """Define all indexes for each collection"""
        return {
            # Patients collection indexes
            "patients": [
                {
                    "name": "patient_lookup_idx",
                    "keys": [("is_deleted", ASCENDING), ("is_active", ASCENDING)],
                    "background": True
                },
                {
                    "name": "patient_search_idx",
                    "keys": [("first_name", TEXT), ("last_name", TEXT), ("phone", TEXT), ("email", TEXT)],
                    "background": True
                },
                {
                    "name": "patient_hospital_idx",
                    "keys": [("new_hospital_ids", ASCENDING), ("is_deleted", ASCENDING)],
                    "background": True
                },
                {
                    "name": "patient_device_idx",
                    "keys": [("watch_mac_address", ASCENDING), ("ava_mac_address", ASCENDING)],
                    "background": True,
                    "sparse": True
                },
                {
                    "name": "patient_created_idx",
                    "keys": [("created_at", DESCENDING)],
                    "background": True
                }
            ],
            
            # Hospitals collection indexes
            "hospitals": [
                {
                    "name": "hospital_lookup_idx",
                    "keys": [("is_deleted", ASCENDING), ("is_active", ASCENDING)],
                    "background": True
                },
                {
                    "name": "hospital_location_idx",
                    "keys": [("province_code", ASCENDING), ("district_code", ASCENDING), ("sub_district_code", ASCENDING)],
                    "background": True
                },
                {
                    "name": "hospital_search_idx",
                    "keys": [("name.en", TEXT), ("name.th", TEXT), ("en_name", TEXT)],
                    "background": True
                },
                {
                    "name": "hospital_code_idx",
                    "keys": [("code", ASCENDING)],
                    "unique": True,
                    "background": True,
                    "sparse": True
                }
            ],
            
            # Hospital users collection indexes
            "hospital_users": [
                {
                    "name": "user_auth_idx",
                    "keys": [("email", ASCENDING), ("is_deleted", ASCENDING)],
                    "unique": True,
                    "background": True
                },
                {
                    "name": "user_hospital_idx",
                    "keys": [("hospital_id", ASCENDING), ("is_active", ASCENDING), ("is_deleted", ASCENDING)],
                    "background": True
                },
                {
                    "name": "user_type_idx",
                    "keys": [("type", ASCENDING), ("is_active", ASCENDING)],
                    "background": True
                },
                {
                    "name": "user_search_idx",
                    "keys": [("first_name", TEXT), ("last_name", TEXT), ("email", TEXT), ("phone", TEXT)],
                    "background": True
                }
            ],
            
            # Medical history collections indexes (applied to all history collections)
            "medical_history_pattern": [
                {
                    "name": "history_patient_idx",
                    "keys": [("patient_id", ASCENDING), ("created_at", DESCENDING)],
                    "background": True
                },
                {
                    "name": "history_device_idx",
                    "keys": [("device_id", ASCENDING), ("device_type", ASCENDING)],
                    "background": True,
                    "sparse": True
                },
                {
                    "name": "history_date_idx",
                    "keys": [("created_at", DESCENDING)],
                    "background": True
                },
                {
                    "name": "history_timestamp_idx",
                    "keys": [("timestamp", DESCENDING)],
                    "background": True,
                    "sparse": True
                }
            ],
            
            # Device collections indexes
            "amy_boxes": [
                {
                    "name": "ava_box_lookup_idx",
                    "keys": [("is_deleted", ASCENDING), ("is_active", ASCENDING)],
                    "background": True
                },
                {
                    "name": "ava_box_mac_sparse_idx",
                    "keys": [("mac_address", ASCENDING)],
                    "background": True,
                    "sparse": True  # Allow multiple null values - some boxes don't have MAC address
                },
                {
                    "name": "ava_box_patient_idx",
                    "keys": [("patient_id", ASCENDING)],
                    "background": True,
                    "sparse": True
                }
            ],
            
            "amy_devices": [
                {
                    "name": "ava_device_lookup_idx",
                    "keys": [("is_deleted", ASCENDING), ("is_active", ASCENDING)],
                    "background": True
                },
                {
                    "name": "ava_device_mac_gw_idx",
                    "keys": [("mac_gw", ASCENDING)],
                    "background": True,
                    "sparse": True  # Gateway MAC address (device-specific field)
                },
                {
                    "name": "ava_device_mac_bps_idx",
                    "keys": [("mac_bps", ASCENDING)],
                    "background": True,
                    "sparse": True  # Blood pressure sensor MAC address
                },
                {
                    "name": "ava_device_mac_watch_idx",
                    "keys": [("mac_watch", ASCENDING)],
                    "background": True,
                    "sparse": True  # Watch MAC address
                },
                {
                    "name": "ava_device_box_idx",
                    "keys": [("box_id", ASCENDING)],
                    "background": True,
                    "sparse": True
                },
                {
                    "name": "ava_device_patient_idx",
                    "keys": [("patient_id", ASCENDING)],
                    "background": True,
                    "sparse": True
                }
            ],
            
            "watches": [
                {
                    "name": "watch_lookup_idx",
                    "keys": [("status", ASCENDING)],
                    "background": True
                },
                {
                    "name": "watch_imei_idx",
                    "keys": [("imei", ASCENDING)],
                    "background": True,
                    "sparse": True  # Allow multiple null values - some devices don't have IMEI
                },
                {
                    "name": "watch_patient_idx",
                    "keys": [("patient_id", ASCENDING)],
                    "background": True,
                    "sparse": True
                }
            ],
            
            "mfc_hv01_boxes": [
                {
                    "name": "qube_lookup_idx",
                    "keys": [("is_deleted", ASCENDING), ("is_active", ASCENDING)],
                    "background": True
                },
                {
                    "name": "qube_imei_idx",
                    "keys": [("imei_of_hv01_box", ASCENDING)],
                    "unique": True,
                    "background": True
                },
                {
                    "name": "qube_hospital_idx",
                    "keys": [("hospital_id", ASCENDING)],
                    "background": True,
                    "sparse": True
                }
            ],
            
            # Master data collections
            "blood_groups": [
                {
                    "name": "master_data_idx",
                    "keys": [("is_active", ASCENDING), ("is_deleted", ASCENDING)],
                    "background": True
                },
                {
                    "name": "master_data_name_idx",
                    "keys": [("en_name", ASCENDING)],
                    "background": True
                }
            ],
            
            # FHIR collections
            "fhir_observations": [
                {
                    "name": "observation_patient_idx",
                    "keys": [("subject.reference", ASCENDING), ("effectiveDateTime", DESCENDING)],
                    "background": True
                },
                {
                    "name": "observation_device_idx",
                    "keys": [("device.reference", ASCENDING)],
                    "background": True,
                    "sparse": True
                },
                {
                    "name": "observation_code_idx",
                    "keys": [("code.coding.code", ASCENDING)],
                    "background": True
                }
            ],
            
            "fhir_provenance": [
                {
                    "name": "audit_date_idx",
                    "keys": [("recorded", DESCENDING)],
                    "background": True
                },
                {
                    "name": "audit_target_idx",
                    "keys": [("target.reference", ASCENDING)],
                    "background": True
                },
                {
                    "name": "audit_agent_idx",
                    "keys": [("agent.who.identifier.value", ASCENDING)],
                    "background": True
                }
            ],
            
            # =============== FHIR R5 Collection Indexes ===============
            
            "fhir_patients": [
                {
                    "name": "resource_id_idx",
                    "keys": [("resource_id", ASCENDING)],
                    "unique": True,
                    "background": True
                },
                {
                    "name": "patient_active_idx",
                    "keys": [("is_active", ASCENDING), ("is_deleted", ASCENDING)],
                    "background": True
                },
                {
                    "name": "patient_identifier_idx",
                    "keys": [("resource_data.identifier.value", ASCENDING)],
                    "background": True
                },
                {
                    "name": "patient_name_idx",
                    "keys": [("resource_data.name.family", ASCENDING), ("resource_data.name.given", ASCENDING)],
                    "background": True
                },
                {
                    "name": "patient_birth_date_idx",
                    "keys": [("resource_data.birthDate", ASCENDING)],
                    "background": True
                },
                {
                    "name": "patient_organization_idx",
                    "keys": [("organization_id", ASCENDING)],
                    "background": True
                },
                {
                    "name": "patient_created_idx",
                    "keys": [("created_at", DESCENDING)],
                    "background": True
                }
            ],
            
            "fhir_observations": [
                {
                    "name": "resource_id_idx",
                    "keys": [("resource_id", ASCENDING)],
                    "unique": True,
                    "background": True
                },
                {
                    "name": "obs_patient_idx",
                    "keys": [("patient_id", ASCENDING)],
                    "background": True
                },
                {
                    "name": "obs_device_idx",
                    "keys": [("device_id", ASCENDING)],
                    "background": True
                },
                {
                    "name": "obs_effective_time_idx",
                    "keys": [("effective_datetime", DESCENDING)],
                    "background": True
                },
                {
                    "name": "obs_patient_time_idx",
                    "keys": [("patient_id", ASCENDING), ("effective_datetime", DESCENDING)],
                    "background": True
                },
                {
                    "name": "obs_status_idx",
                    "keys": [("status", ASCENDING), ("is_deleted", ASCENDING)],
                    "background": True
                },
                {
                    "name": "obs_category_idx",
                    "keys": [("resource_data.category.coding.code", ASCENDING)],
                    "background": True
                },
                {
                    "name": "obs_code_idx",
                    "keys": [("resource_data.code.coding.code", ASCENDING)],
                    "background": True
                },
                {
                    "name": "obs_device_mac_idx",
                    "keys": [("device_mac_address", ASCENDING)],
                    "background": True
                },
                {
                    "name": "obs_source_system_idx",
                    "keys": [("source_system", ASCENDING)],
                    "background": True
                },
                {
                    "name": "obs_encounter_idx",
                    "keys": [("encounter_id", ASCENDING)],
                    "background": True
                }
            ],
            
            "fhir_devices": [
                {
                    "name": "resource_id_idx",
                    "keys": [("resource_id", ASCENDING)],
                    "unique": True,
                    "background": True
                },
                {
                    "name": "device_identifier_idx",
                    "keys": [("resource_data.identifier.value", ASCENDING)],
                    "background": True
                },
                {
                    "name": "device_serial_idx",
                    "keys": [("resource_data.serialNumber", ASCENDING)],
                    "background": True
                },
                {
                    "name": "device_status_idx",
                    "keys": [("resource_data.status", ASCENDING), ("is_deleted", ASCENDING)],
                    "background": True
                },
                {
                    "name": "device_type_idx",
                    "keys": [("resource_data.type.coding.code", ASCENDING)],
                    "background": True
                },
                {
                    "name": "device_manufacturer_idx",
                    "keys": [("resource_data.manufacturer", ASCENDING)],
                    "background": True
                },
                {
                    "name": "device_model_idx",
                    "keys": [("resource_data.modelNumber", ASCENDING)],
                    "background": True
                },
                {
                    "name": "device_owner_idx",
                    "keys": [("resource_data.owner.reference", ASCENDING)],
                    "background": True
                }
            ],
            
            "fhir_organizations": [
                {
                    "name": "resource_id_idx",
                    "keys": [("resource_id", ASCENDING)],
                    "unique": True,
                    "background": True
                },
                {
                    "name": "org_identifier_idx",
                    "keys": [("resource_data.identifier.value", ASCENDING)],
                    "background": True
                },
                {
                    "name": "org_name_idx",
                    "keys": [("resource_data.name", ASCENDING)],
                    "background": True
                },
                {
                    "name": "org_type_idx",
                    "keys": [("resource_data.type.coding.code", ASCENDING)],
                    "background": True
                },
                {
                    "name": "org_active_idx",
                    "keys": [("resource_data.active", ASCENDING), ("is_deleted", ASCENDING)],
                    "background": True
                },
                {
                    "name": "org_part_of_idx",
                    "keys": [("resource_data.partOf.reference", ASCENDING)],
                    "background": True
                }
            ],
            
            "fhir_locations": [
                {
                    "name": "resource_id_idx",
                    "keys": [("resource_id", ASCENDING)],
                    "unique": True,
                    "background": True
                },
                {
                    "name": "location_identifier_idx",
                    "keys": [("resource_data.identifier.value", ASCENDING)],
                    "background": True
                },
                {
                    "name": "location_name_idx",
                    "keys": [("resource_data.name", ASCENDING)],
                    "background": True
                },
                {
                    "name": "location_type_idx",
                    "keys": [("resource_data.type.coding.code", ASCENDING)],
                    "background": True
                },
                {
                    "name": "location_status_idx",
                    "keys": [("resource_data.status", ASCENDING), ("is_deleted", ASCENDING)],
                    "background": True
                },
                {
                    "name": "location_managing_org_idx",
                    "keys": [("resource_data.managingOrganization.reference", ASCENDING)],
                    "background": True
                },
                {
                    "name": "location_part_of_idx",
                    "keys": [("resource_data.partOf.reference", ASCENDING)],
                    "background": True
                }
            ],
            
            "fhir_conditions": [
                {
                    "name": "resource_id_idx",
                    "keys": [("resource_id", ASCENDING)],
                    "unique": True,
                    "background": True
                },
                {
                    "name": "condition_patient_idx",
                    "keys": [("patient_id", ASCENDING)],
                    "background": True
                },
                {
                    "name": "condition_clinical_status_idx",
                    "keys": [("resource_data.clinicalStatus.coding.code", ASCENDING)],
                    "background": True
                },
                {
                    "name": "condition_verification_status_idx",
                    "keys": [("resource_data.verificationStatus.coding.code", ASCENDING)],
                    "background": True
                },
                {
                    "name": "condition_category_idx",
                    "keys": [("resource_data.category.coding.code", ASCENDING)],
                    "background": True
                },
                {
                    "name": "condition_code_idx",
                    "keys": [("resource_data.code.coding.code", ASCENDING)],
                    "background": True
                },
                {
                    "name": "condition_onset_idx",
                    "keys": [("resource_data.onsetDateTime", ASCENDING)],
                    "background": True
                },
                {
                    "name": "condition_recorded_idx",
                    "keys": [("resource_data.recordedDate", DESCENDING)],
                    "background": True
                },
                {
                    "name": "condition_encounter_idx",
                    "keys": [("encounter_id", ASCENDING)],
                    "background": True
                }
            ],
            
            "fhir_medications": [
                {
                    "name": "resource_id_idx",
                    "keys": [("resource_id", ASCENDING)],
                    "unique": True,
                    "background": True
                },
                {
                    "name": "medication_identifier_idx",
                    "keys": [("resource_data.identifier.value", ASCENDING)],
                    "background": True
                },
                {
                    "name": "medication_code_idx",
                    "keys": [("resource_data.code.coding.code", ASCENDING)],
                    "background": True
                },
                {
                    "name": "medication_status_idx",
                    "keys": [("resource_data.status", ASCENDING), ("is_deleted", ASCENDING)],
                    "background": True
                },
                {
                    "name": "medication_form_idx",
                    "keys": [("resource_data.doseForm.coding.code", ASCENDING)],
                    "background": True
                }
            ],
            
            "fhir_allergies": [
                {
                    "name": "resource_id_idx",
                    "keys": [("resource_id", ASCENDING)],
                    "unique": True,
                    "background": True
                },
                {
                    "name": "allergy_patient_idx",
                    "keys": [("patient_id", ASCENDING)],
                    "background": True
                },
                {
                    "name": "allergy_clinical_status_idx",
                    "keys": [("resource_data.clinicalStatus.coding.code", ASCENDING)],
                    "background": True
                },
                {
                    "name": "allergy_verification_status_idx",
                    "keys": [("resource_data.verificationStatus.coding.code", ASCENDING)],
                    "background": True
                },
                {
                    "name": "allergy_category_idx",
                    "keys": [("resource_data.category", ASCENDING)],
                    "background": True
                },
                {
                    "name": "allergy_criticality_idx",
                    "keys": [("resource_data.criticality", ASCENDING)],
                    "background": True
                },
                {
                    "name": "allergy_code_idx",
                    "keys": [("resource_data.code.coding.code", ASCENDING)],
                    "background": True
                },
                {
                    "name": "allergy_recorded_idx",
                    "keys": [("resource_data.recordedDate", DESCENDING)],
                    "background": True
                }
            ],
            
            "fhir_encounters": [
                {
                    "name": "resource_id_idx",
                    "keys": [("resource_id", ASCENDING)],
                    "unique": True,
                    "background": True
                },
                {
                    "name": "encounter_patient_idx",
                    "keys": [("patient_id", ASCENDING)],
                    "background": True
                },
                {
                    "name": "encounter_status_idx",
                    "keys": [("resource_data.status", ASCENDING), ("is_deleted", ASCENDING)],
                    "background": True
                },
                {
                    "name": "encounter_class_idx",
                    "keys": [("resource_data.class.code", ASCENDING)],
                    "background": True
                },
                {
                    "name": "encounter_type_idx",
                    "keys": [("resource_data.type.coding.code", ASCENDING)],
                    "background": True
                },
                {
                    "name": "encounter_service_provider_idx",
                    "keys": [("resource_data.serviceProvider.reference", ASCENDING)],
                    "background": True
                },
                {
                    "name": "encounter_period_idx",
                    "keys": [("resource_data.actualPeriod.start", DESCENDING)],
                    "background": True
                },
                {
                    "name": "encounter_identifier_idx",
                    "keys": [("resource_data.identifier.value", ASCENDING)],
                    "background": True
                }
            ],
            
            # =============== FHIR Pattern Indexes (applied to all FHIR collections) ===============
            
            "fhir_resource_pattern": [
                {
                    "name": "fhir_created_at_idx",
                    "keys": [("created_at", DESCENDING)],
                    "background": True
                },
                {
                    "name": "fhir_updated_at_idx",
                    "keys": [("updated_at", DESCENDING)],
                    "background": True
                },
                {
                    "name": "fhir_source_system_idx",
                    "keys": [("source_system", ASCENDING)],
                    "background": True
                },
                {
                    "name": "fhir_version_idx",
                    "keys": [("fhir_version", ASCENDING)],
                    "background": True
                },
                {
                    "name": "fhir_resource_type_idx",
                    "keys": [("resource_type", ASCENDING)],
                    "background": True
                },
                {
                    "name": "fhir_last_updated_idx",
                    "keys": [("resource_data.meta.lastUpdated", DESCENDING)],
                    "background": True
                },
                {
                    "name": "fhir_profile_idx",
                    "keys": [("resource_data.meta.profile", ASCENDING)],
                    "background": True
                }
            ]
        }
    
    async def create_all_indexes(self):
        """Create all defined indexes"""
        logger.info("🔧 Starting database index creation...")
        
        # Medical history collections
        medical_history_collections = [
            "blood_pressure_histories",
            "blood_sugar_histories",
            "body_data_histories",
            "creatinine_histories",
            "lipid_histories",
            "sleep_data_histories",
            "spo2_histories",
            "step_histories",
            "temprature_data_histories",
            "medication_histories",
            "allergy_histories",
            "underlying_disease_histories",
            "admit_data_histories"
        ]
        
        # FHIR R5 collections
        fhir_collections = [
            "fhir_patients", "fhir_observations", "fhir_devices", 
            "fhir_organizations", "fhir_locations", "fhir_conditions",
            "fhir_medications", "fhir_allergies", "fhir_encounters", "fhir_provenance"
        ]

        # Create indexes for each collection
        for collection_name, indexes in self.index_definitions.items():
            if collection_name == "medical_history_pattern":
                # Apply pattern to all medical history collections
                for history_collection in medical_history_collections:
                    await self._create_collection_indexes(history_collection, indexes)
            elif collection_name == "fhir_resource_pattern":
                # Apply pattern to all FHIR R5 collections
                for fhir_collection in fhir_collections:
                    await self._create_collection_indexes(fhir_collection, indexes)
            else:
                await self._create_collection_indexes(collection_name, indexes)
        
        # Apply master data pattern to all master data collections
        # Note: Some collections may have restricted permissions
        master_data_collections = [
            "nations", "human_skin_colors", "ward_lists",
            "staff_types", "underlying_diseases", "provinces",
            "districts", "sub_districts"
        ]
        
        master_data_indexes = self.index_definitions.get("blood_groups", [])
        
        # Test permissions first and only proceed with collections we can modify
        accessible_collections = await self._check_collection_permissions(master_data_collections)
        
        for collection in accessible_collections:
            await self._create_collection_indexes(collection, master_data_indexes)
        
        if len(accessible_collections) < len(master_data_collections):
            skipped = len(master_data_collections) - len(accessible_collections)
            logger.info(f"⚠️ Skipped {skipped} collections due to insufficient permissions")
        
        logger.info("✅ Database index creation completed")
        
        # Log summary
        await self._log_index_summary()
    
    async def _create_collection_indexes(self, collection_name: str, indexes: List[Dict[str, Any]]):
        """Create indexes for a specific collection"""
        try:
            # Use appropriate database based on collection name
            if collection_name.startswith('fhir_'):
                collection = mongodb_service.get_fhir_collection(collection_name)
            else:
                collection = mongodb_service.get_collection(collection_name)
            
            for index_def in indexes:
                try:
                    # Extract index parameters
                    keys = index_def["keys"]
                    name = index_def["name"]
                    
                    # Build index kwargs
                    index_kwargs = {
                        "name": name,
                        "background": index_def.get("background", True)
                    }
                    
                    # Add optional parameters
                    if "unique" in index_def:
                        index_kwargs["unique"] = index_def["unique"]
                    if "sparse" in index_def:
                        index_kwargs["sparse"] = index_def["sparse"]
                    if "expireAfterSeconds" in index_def:
                        index_kwargs["expireAfterSeconds"] = index_def["expireAfterSeconds"]
                    
                    # Create the index
                    await collection.create_index(keys, **index_kwargs)
                    
                    # Track created index
                    if collection_name not in self.created_indexes:
                        self.created_indexes[collection_name] = []
                    self.created_indexes[collection_name].append(name)
                    
                    logger.debug(f"Created index '{name}' on collection '{collection_name}'")
                    
                except OperationFailure as e:
                    if "already exists" in str(e):
                        logger.debug(f"Index '{name}' already exists on '{collection_name}'")
                    elif e.code == 13:  # Authorization error
                        logger.debug(f"Insufficient permissions to create index '{name}' on '{collection_name}' - skipping")
                    else:
                        logger.error(f"Failed to create index '{name}' on '{collection_name}': {e}")
                        
        except Exception as e:
            logger.error(f"Failed to create indexes for collection '{collection_name}': {e}")
    
    async def _check_collection_permissions(self, collection_names: List[str]) -> List[str]:
        """Check which collections we have permission to create indexes on"""
        accessible_collections = []
        
        for collection_name in collection_names:
            try:
                # Use appropriate database based on collection name
                if collection_name.startswith('fhir_'):
                    collection = mongodb_service.get_fhir_collection(collection_name)
                else:
                    collection = mongodb_service.get_collection(collection_name)
                
                # Test permission by trying to create a simple index
                test_index_name = f"_permission_test_{collection_name}"
                
                try:
                    # Try to create a test index
                    await collection.create_index([("_id", 1)], name=test_index_name, background=True)
                    # If successful, drop the test index
                    await collection.drop_index(test_index_name)
                    accessible_collections.append(collection_name)
                    logger.debug(f"✅ Index permissions confirmed for '{collection_name}'")
                    
                except Exception as e:
                    if hasattr(e, 'code') and getattr(e, 'code', None) == 13:  # Authorization error
                        logger.debug(f"⚠️ No index permissions for '{collection_name}' - skipping")
                    else:
                        # Other errors might indicate the collection doesn't exist yet, which is OK
                        logger.debug(f"⚠️ Cannot test permissions for '{collection_name}': {e}")
                        # Include it anyway, we'll handle the error during actual index creation
                        accessible_collections.append(collection_name)
                        
            except Exception as e:
                logger.debug(f"⚠️ Cannot access collection '{collection_name}': {e}")
                
        return accessible_collections
    
    async def _log_index_summary(self):
        """Log a summary of created indexes"""
        total_indexes = sum(len(indexes) for indexes in self.created_indexes.values())
        logger.info(f"📊 Index creation summary:")
        logger.info(f"   - Total collections indexed: {len(self.created_indexes)}")
        logger.info(f"   - Total indexes created: {total_indexes}")
        
        for collection, indexes in self.created_indexes.items():
            logger.info(f"   - {collection}: {len(indexes)} indexes")
    
    async def analyze_index_usage(self, collection_name: str) -> List[Dict[str, Any]]:
        """Analyze index usage for a collection"""
        try:
            collection = mongodb_service.get_collection(collection_name)
            
            # Get index statistics
            stats = await collection.aggregate([
                {"$indexStats": {}}
            ]).to_list(length=None)
            
            # Format results
            index_usage = []
            for stat in stats:
                index_usage.append({
                    "name": stat["name"],
                    "ops": stat.get("accesses", {}).get("ops", 0),
                    "since": stat.get("accesses", {}).get("since", None),
                    "size": stat.get("size", 0)
                })
            
            # Sort by usage
            index_usage.sort(key=lambda x: x["ops"], reverse=True)
            
            return index_usage
            
        except Exception as e:
            logger.error(f"Failed to analyze index usage for '{collection_name}': {e}")
            return []
    
    async def recommend_indexes(self, slow_queries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Recommend indexes based on slow queries"""
        recommendations = []
        
        for query in slow_queries:
            collection = query.get("collection")
            filter_fields = list(query.get("filter", {}).keys())
            sort_fields = query.get("sort", [])
            
            if filter_fields or sort_fields:
                # Build recommended index
                index_keys = []
                
                # Add filter fields first
                for field in filter_fields:
                    if field not in ["$or", "$and"]:
                        index_keys.append((field, ASCENDING))
                
                # Add sort fields
                for field, direction in sort_fields:
                    if (field, direction) not in index_keys:
                        index_keys.append((field, direction))
                
                if index_keys:
                    recommendations.append({
                        "collection": collection,
                        "keys": index_keys,
                        "reason": f"Optimize query with filter: {filter_fields}, sort: {sort_fields}",
                        "estimated_improvement": "50-90% query time reduction"
                    })
        
        return recommendations
    
    async def drop_unused_indexes(self, threshold_days: int = 30) -> List[str]:
        """Drop indexes that haven't been used in the specified threshold"""
        dropped_indexes = []
        
        # This is a placeholder - actual implementation would analyze index usage
        # and drop indexes that haven't been accessed in the threshold period
        
        logger.warning("Index cleanup is a manual process - review index usage before dropping")
        
        return dropped_indexes


# Global index manager instance
index_manager = IndexManager() 