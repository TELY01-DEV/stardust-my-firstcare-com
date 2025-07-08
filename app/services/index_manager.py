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
        
        # Create indexes for each collection
        for collection_name, indexes in self.index_definitions.items():
            if collection_name == "medical_history_pattern":
                # Apply pattern to all medical history collections
                for history_collection in medical_history_collections:
                    await self._create_collection_indexes(history_collection, indexes)
            else:
                await self._create_collection_indexes(collection_name, indexes)
        
        # Apply master data pattern to all master data collections
        master_data_collections = [
            "nations", "human_skin_colors", "ward_lists",
            "staff_types", "underlying_diseases", "provinces",
            "districts", "sub_districts"
        ]
        
        master_data_indexes = self.index_definitions.get("blood_groups", [])
        for collection in master_data_collections:
            await self._create_collection_indexes(collection, master_data_indexes)
        
        logger.info("✅ Database index creation completed")
        
        # Log summary
        await self._log_index_summary()
    
    async def _create_collection_indexes(self, collection_name: str, indexes: List[Dict[str, Any]]):
        """Create indexes for a specific collection"""
        try:
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
                    else:
                        logger.error(f"Failed to create index '{name}' on '{collection_name}': {e}")
                        
        except Exception as e:
            logger.error(f"Failed to create indexes for collection '{collection_name}': {e}")
    
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