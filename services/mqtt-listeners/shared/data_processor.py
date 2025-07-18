"""
Data Processing Utility
Handles storage of medical data to patient records and history collections
"""

import os
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from pymongo import MongoClient
from bson import ObjectId

logger = logging.getLogger(__name__)

class DataProcessor:
    """Processes and stores medical data"""
    
    def __init__(self, mongodb_uri: str, database_name: str = "AMY"):
        # Parse MongoDB URI to extract components
        if mongodb_uri.startswith("mongodb://"):
            # Handle mongodb:// format
            self._setup_mongodb_connection(mongodb_uri, database_name)
        else:
            # Handle mongodb+srv:// format or other formats
            self.client = MongoClient(mongodb_uri)
            self.db = self.client[database_name]
        
        logger.info(f"DataProcessor initialized for database: {database_name}")
    
    def _setup_mongodb_connection(self, mongodb_uri: str, database_name: str):
        """Setup MongoDB connection with SSL certificates"""
        try:
            # Check if SSL certificate files exist
            ssl_ca_file = "/app/ssl/ca-latest.pem"
            ssl_client_file = "/app/ssl/client-combined-latest.pem"
            
            ssl_ca_exists = os.path.exists(ssl_ca_file)
            ssl_client_exists = os.path.exists(ssl_client_file)
            
            # MongoDB configuration
            mongodb_config = {
                "tls": True,
                "tlsAllowInvalidCertificates": True,
                "tlsAllowInvalidHostnames": True,
                "serverSelectionTimeoutMS": 20000,
                "connectTimeoutMS": 20000
            }
            
            # Only add SSL certificate files if they exist
            if ssl_ca_exists:
                mongodb_config["tlsCAFile"] = ssl_ca_file
                logger.info(f"✅ Using SSL CA file: {ssl_ca_file}")
            else:
                logger.warning(f"⚠️ SSL CA file not found: {ssl_ca_file}, proceeding without it")
                
            if ssl_client_exists:
                mongodb_config["tlsCertificateKeyFile"] = ssl_client_file
                logger.info(f"✅ Using SSL client file: {ssl_client_file}")
            else:
                logger.warning(f"⚠️ SSL client file not found: {ssl_client_file}, proceeding without it")
            
            # Create client with SSL configuration
            self.client = MongoClient(mongodb_uri, **mongodb_config)
            self.db = self.client[database_name]
            
            # Test connection
            self.client.admin.command('ping')
            logger.info("✅ Connected to MongoDB with SSL certificates")
            
        except Exception as e:
            logger.error(f"❌ MongoDB connection with SSL failed: {e}")
            # Fallback to simple connection
            logger.warning("⚠️ Falling back to simple MongoDB connection")
            self.client = MongoClient(mongodb_uri)
            self.db = self.client[database_name]
        
    def update_patient_last_data(self, patient_id: ObjectId, data_type: str, 
                                data: Dict[str, Any], source: str = "device", 
                                patient_name: Optional[str] = None) -> bool:
        """Update patient's last/latest medical data"""
        try:
            logger.debug(f"🔄 Updating last data - Patient: {patient_id}, Type: {data_type}, Source: {source}")
            logger.debug(f"📊 Data payload: {data}")
            
            # Map data types to patient fields
            field_mapping = {
                "blood_pressure": "last_blood_pressure",
                "blood_sugar": "last_blood_sugar", 
                "spo2": "last_spo2",
                "body_temp": "last_body_temperature",
                "weight": "last_weight",
                "uric_acid": "last_uric_acid",
                "cholesterol": "last_cholesterol",
                "heart_rate": "last_heart_rate",
                "step_count": "last_step_count",
                "sleep_data": "last_sleep_data"
            }
            
            field_name = field_mapping.get(data_type)
            if not field_name:
                logger.warning(f"❌ Unknown data type for last data update: {data_type}")
                return False
            
            logger.debug(f"📝 Field mapping: {data_type} -> {field_name}")
            
            # Add timestamp and source
            update_data = {
                **data,
                "timestamp": datetime.utcnow(),
                "source": source,
                "updated_at": datetime.utcnow()
            }
            
            logger.debug(f"💾 Update data prepared: {update_data}")
            
            result = self.db.patients.update_one(
                {"_id": patient_id},
                {
                    "$set": {
                        field_name: update_data,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            logger.debug(f"📊 Update result - Matched: {result.matched_count}, Modified: {result.modified_count}")
            
            patient_display = f"{patient_id} ({patient_name})" if patient_name else str(patient_id)
            if result.modified_count > 0:
                logger.info(f"✅ Successfully updated last {data_type} data for patient {patient_display} - Field: {field_name}")
                logger.info(f"📊 Updated data: {update_data}")
                return True
            else:
                logger.warning(f"⚠️ No patient found or no changes made for {patient_display} - Field: {field_name}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error updating last data for patient {patient_id}: {e}")
            return False
    
    def store_medical_history(self, patient_id: ObjectId, data_type: str, 
                             data: Dict[str, Any], source: str = "device", 
                             device_id: Optional[str] = None, 
                             patient_name: Optional[str] = None) -> bool:
        """Store medical data to history collection"""
        try:
            logger.debug(f"📚 Storing medical history - Patient: {patient_id}, Type: {data_type}, Source: {source}")
            logger.debug(f"📊 History data: {data}")
            
            # Map data types to history collections
            collection_mapping = {
                "blood_pressure": "blood_pressure_histories",
                "blood_sugar": "blood_sugar_histories",
                "spo2": "spo2_histories", 
                "body_temp": "temprature_data_histories",
                "weight": "body_data_histories",
                "uric_acid": "uric_acid_histories",
                "cholesterol": "cholesterol_histories",
                "heart_rate": "heart_rate_histories",
                "step_count": "step_histories",
                "sleep_data": "sleep_data_histories"
            }
            
            collection_name = collection_mapping.get(data_type, "")
            if not collection_name:
                logger.warning(f"❌ Unknown data type for history storage: {data_type}")
                return False
            
            logger.debug(f"📝 Collection mapping: {data_type} -> {collection_name}")
            
            # Prepare history document
            history_doc = {
                "patient_id": patient_id,
                "timestamp": datetime.utcnow(),
                "data": data,
                "source": source,
                "device_id": device_id or "",
                "created_at": datetime.utcnow()
            }
            
            logger.debug(f"💾 History document prepared: {history_doc}")
            
            result = self.db[collection_name].insert_one(history_doc)
            
            patient_display = f"{patient_id} ({patient_name})" if patient_name else str(patient_id)
            if result.inserted_id:
                logger.info(f"✅ Successfully stored {data_type} history for patient {patient_display} (ID: {result.inserted_id}) - Collection: {collection_name}")
                logger.info(f"📊 Stored history data: {history_doc}")
                return True
            else:
                logger.error(f"❌ Failed to store {data_type} history for patient {patient_display} - Collection: {collection_name}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error storing {data_type} history for patient {patient_id}: {e}")
            return False
    
    def store_medical_data(self, data: dict) -> bool:
        """Store generic medical data in the 'medical_data' collection."""
        try:
            result = self.db['medical_data'].insert_one(data)
            if result.inserted_id:
                logger.info(f"✅ Successfully stored generic medical data (ID: {result.inserted_id}) in 'medical_data' collection.")
                return True
            else:
                logger.error("❌ Failed to store generic medical data in 'medical_data' collection.")
                return False
        except Exception as e:
            logger.error(f"❌ Error storing generic medical data: {e}")
            return False
    
    def process_ava4_data(self, patient_id: ObjectId, device_mac: str, 
                         attribute: str, value: Dict[str, Any], ble_addr: Optional[str] = None, device_name: Optional[str] = None) -> bool:
        """Process AVA4 sub-device data"""
        try:
            logger.info(f"🔧 Processing AVA4 data - Patient: {patient_id}, AVA4 MAC: {device_mac}, BLE: {ble_addr}, Attribute: {attribute}")
            logger.debug(f"📊 AVA4 RAW VALUE PAYLOAD: {value}")
            logger.debug(f"🔍 AVA4 ATTRIBUTE: {attribute}")
            logger.debug(f"📱 AVA4 GATEWAY MAC: {device_mac}")
            logger.debug(f"📱 SUB-DEVICE BLE ADDR: {ble_addr}")
            logger.debug(f"👤 AVA4 PATIENT ID: {patient_id}")
            
            # Map AVA4 attributes to data types
            attribute_mapping = {
                "BP_BIOLIGTH": "blood_pressure",
                "WBP BIOLIGHT": "blood_pressure",  # Added this variant
                "BLE_BPG": "blood_pressure",
                "Contour_Elite": "blood_sugar",
                "AccuChek_Instant": "blood_sugar", 
                "Oximeter JUMPER": "spo2",
                "IR_TEMO_JUMPER": "body_temp",
                "BodyScale_JUMPER": "weight",
                "MGSS_REF_UA": "uric_acid",
                "MGSS_REF_CHOL": "cholesterol"
            }
            
            data_type = attribute_mapping.get(attribute)
            if not data_type:
                logger.warning(f"❌ Unknown AVA4 attribute: {attribute}")
                return False
            
            logger.debug(f"📝 Attribute mapping: {attribute} -> {data_type}")
            
            # Extract data from device_list
            device_list = value.get("device_list", [])
            if not device_list:
                logger.warning(f"❌ No device data found for attribute {attribute}")
                return False
            
            logger.debug(f"📊 Found {len(device_list)} device readings")
            
            # Process each device reading
            success_count = 0
            for i, device_data in enumerate(device_list):
                logger.debug(f"🔧 Processing device reading {i+1}/{len(device_list)}: {device_data}")
                logger.debug(f"📊 RAW DEVICE DATA BEFORE PROCESSING: {device_data}")
                
                processed_data = self._process_ava4_device_data(data_type, device_data)
                if processed_data:
                    logger.debug(f"✅ Device data processed: {processed_data}")
                    logger.debug(f"📊 PARSED DATA READY FOR STORAGE: {processed_data}")
                    
                    # Update last data
                    logger.info(f"💾 UPDATING PATIENT COLLECTION - Field: {data_type}, Data: {processed_data}")
                    last_update_success = self.update_patient_last_data(patient_id, data_type, processed_data, "AVA4")
                    if last_update_success:
                        logger.info(f"✅ PATIENT COLLECTION UPDATED SUCCESSFULLY - Field: {data_type}")
                    else:
                        logger.warning(f"⚠️ FAILED TO UPDATE PATIENT COLLECTION - Field: {data_type}")
                    
                    # Store history - Use BLE address for device identification
                    device_identifier = ble_addr if ble_addr else device_mac
                    
                    # Map data type to collection name for logging
                    collection_mapping = {
                        "blood_pressure": "blood_pressure_histories",
                        "blood_sugar": "blood_sugar_histories",
                        "spo2": "spo2_histories", 
                        "body_temp": "temprature_data_histories",
                        "weight": "body_data_histories",
                        "uric_acid": "uric_acid_histories",
                        "cholesterol": "cholesterol_histories"
                    }
                    collection_name = collection_mapping.get(data_type, f"{data_type}_histories")
                    
                    logger.info(f"📚 STORING MEDICAL HISTORY - Collection: {collection_name}, Device: {device_identifier}, Data: {processed_data}")
                    history_success = self.store_medical_history(patient_id, data_type, processed_data, "AVA4", device_identifier)
                    if history_success:
                        logger.info(f"✅ MEDICAL HISTORY STORED SUCCESSFULLY - Collection: {collection_name}")
                        
                        # Also store in medical_data collection for web panel display
                        # Always get the real patient name from database
                        patient_doc = self.db.patients.find_one({"_id": patient_id})
                        patient_name = "Unknown"
                        if patient_doc:
                            patient_name = f"{patient_doc.get('first_name', '')} {patient_doc.get('last_name', '')}".strip()
                            logger.info(f"✅ Found patient name: {patient_name}")
                        else:
                            logger.warning(f"⚠️ Patient not found in database: {patient_id}")
                        
                        medical_data_doc = {
                            "device_id": ble_addr if ble_addr else device_mac,
                            "device_type": "AVA4",
                            "device_name": device_name,  # Store AVA4 name from status collection
                            "source": "AVA4",
                            "patient_id": str(patient_id),  # Convert ObjectId to string
                            "patient_name": patient_name,
                            "timestamp": datetime.utcnow(),
                            "attribute": attribute,
                            "value": value,
                            "processed_data": processed_data,
                            "raw_data": {
                                "device_mac": device_mac,
                                "ble_addr": ble_addr,
                                "attribute": attribute,
                                "device_data": device_data
                            }
                        }
                        
                        # Store in medical_data collection
                        medical_data_success = self.store_medical_data(medical_data_doc)
                        if medical_data_success:
                            logger.info(f"✅ MEDICAL DATA STORED SUCCESSFULLY - Collection: medical_data")
                        else:
                            logger.warning(f"⚠️ FAILED TO STORE MEDICAL DATA - Collection: medical_data")
                        
                        success_count += 1
                    else:
                        logger.warning(f"⚠️ FAILED TO STORE MEDICAL HISTORY - Collection: {collection_name}")
                else:
                    logger.warning(f"❌ Failed to process device data: {device_data}")
            
            logger.info(f"📊 AVA4 processing complete - {success_count}/{len(device_list)} readings processed successfully")
            return success_count > 0
            
        except Exception as e:
            logger.error(f"❌ Error processing AVA4 data: {e}")
            return False
    
    def _process_ava4_device_data(self, data_type: str, device_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process individual AVA4 device data"""
        try:
            logger.debug(f"🔧 Processing AVA4 device data - Type: {data_type}, Data: {device_data}")
            
            if data_type == "blood_pressure":
                processed = {
                    "systolic": device_data.get("bp_high"),
                    "diastolic": device_data.get("bp_low"),
                    "pulse": device_data.get("PR"),
                    "scan_time": device_data.get("scan_time")
                }
            elif data_type == "blood_sugar":
                processed = {
                    "value": device_data.get("blood_glucose"),
                    "marker": device_data.get("marker"),
                    "scan_time": device_data.get("scan_time")
                }
            elif data_type == "spo2":
                processed = {
                    "value": device_data.get("spo2"),
                    "pulse": device_data.get("pulse"),
                    "pi": device_data.get("pi"),
                    "scan_time": device_data.get("scan_time")
                }
            elif data_type == "body_temp":
                processed = {
                    "value": device_data.get("temp"),
                    "mode": device_data.get("mode"),
                    "scan_time": device_data.get("scan_time")
                }
            elif data_type == "weight":
                processed = {
                    "value": device_data.get("weight"),
                    "resistance": device_data.get("resistance"),
                    "scan_time": device_data.get("scan_time")
                }
            elif data_type == "uric_acid":
                processed = {
                    "value": device_data.get("uric_acid"),
                    "scan_time": device_data.get("scan_time")
                }
            elif data_type == "cholesterol":
                processed = {
                    "value": device_data.get("cholesterol"),
                    "scan_time": device_data.get("scan_time")
                }
            else:
                logger.warning(f"❌ Unknown data type for AVA4 processing: {data_type}")
                return None
            
            logger.debug(f"✅ AVA4 data processed: {processed}")
            return processed
                
        except Exception as e:
            logger.error(f"❌ Error processing AVA4 device data: {e}")
            return None
    
    def process_kati_data(self, patient_id: ObjectId, topic: str, payload: Dict[str, Any], 
                         patient_name: Optional[str] = None) -> bool:
        """Process Kati Watch data"""
        try:
            logger.info(f"⌚ Processing Kati Watch data - Patient: {patient_id}, Topic: {topic}")
            logger.debug(f"📊 KATI RAW PAYLOAD: {payload}")
            logger.debug(f"🔍 KATI TOPIC: {topic}")
            logger.debug(f"👤 KATI PATIENT ID: {patient_id}")
            
            if topic == "iMEDE_watch/VitalSign":
                return self._process_kati_vital_signs(patient_id, payload, patient_name)
            elif topic == "iMEDE_watch/AP55":
                return self._process_kati_batch_vital_signs(patient_id, payload, patient_name)
            elif topic == "iMEDE_watch/hb":
                return self._process_kati_heartbeat(patient_id, payload, patient_name)
            elif topic in ["iMEDE_watch/SOS", "iMEDE_watch/fallDown"]:
                return self._process_kati_emergency(patient_id, topic, payload, patient_name)
            else:
                logger.info(f"ℹ️ Unhandled Kati topic: {topic}")
                return True
                
        except Exception as e:
            logger.error(f"❌ Error processing Kati data: {e}")
            return False
    
    def _process_kati_vital_signs(self, patient_id: ObjectId, payload: Dict[str, Any], 
                                 patient_name: Optional[str] = None) -> bool:
        """Process Kati vital signs data"""
        try:
            logger.debug(f"💓 Processing Kati vital signs - Patient: {patient_id}")
            logger.debug(f"📊 KATI VITAL SIGNS RAW PAYLOAD: {payload}")
            logger.debug(f"👤 KATI VITAL SIGNS PATIENT ID: {patient_id}")
            
            success_count = 0
            total_metrics = 0
            
            # Process heart rate
            if "heartRate" in payload:
                total_metrics += 1
                heart_data = {"value": payload["heartRate"]}
                logger.info(f"💓 Processing heart rate: {heart_data}")
                
                logger.info(f"💾 UPDATING PATIENT COLLECTION - Field: heart_rate, Data: {heart_data}")
                last_update_success = self.update_patient_last_data(patient_id, "heart_rate", heart_data, "Kati", patient_name)
                if last_update_success:
                    logger.info(f"✅ PATIENT COLLECTION UPDATED SUCCESSFULLY - Field: heart_rate")
                else:
                    logger.warning(f"⚠️ FAILED TO UPDATE PATIENT COLLECTION - Field: heart_rate")
                
                logger.info(f"📚 STORING MEDICAL HISTORY - Collection: heart_rate_histories, Data: {heart_data}")
                history_success = self.store_medical_history(patient_id, "heart_rate", heart_data, "Kati", None, patient_name)
                if history_success:
                    logger.info(f"✅ MEDICAL HISTORY STORED SUCCESSFULLY - Collection: heart_rate_histories")
                    success_count += 1
                else:
                    logger.warning(f"⚠️ FAILED TO STORE MEDICAL HISTORY - Collection: heart_rate_histories")
            
            # Process blood pressure
            if "bloodPressure" in payload:
                total_metrics += 1
                bp_data = payload["bloodPressure"]
                bp_processed = {
                    "systolic": bp_data.get("bp_sys"),
                    "diastolic": bp_data.get("bp_dia")
                }
                logger.info(f"🩸 Processing blood pressure: {bp_processed}")
                
                logger.info(f"💾 UPDATING PATIENT COLLECTION - Field: blood_pressure, Data: {bp_processed}")
                last_update_success = self.update_patient_last_data(patient_id, "blood_pressure", bp_processed, "Kati", patient_name)
                if last_update_success:
                    logger.info(f"✅ PATIENT COLLECTION UPDATED SUCCESSFULLY - Field: blood_pressure")
                else:
                    logger.warning(f"⚠️ FAILED TO UPDATE PATIENT COLLECTION - Field: blood_pressure")
                
                logger.info(f"📚 STORING MEDICAL HISTORY - Collection: blood_pressure_histories, Data: {bp_processed}")
                history_success = self.store_medical_history(patient_id, "blood_pressure", bp_processed, "Kati", None, patient_name)
                if history_success:
                    logger.info(f"✅ MEDICAL HISTORY STORED SUCCESSFULLY - Collection: blood_pressure_histories")
                    success_count += 1
                else:
                    logger.warning(f"⚠️ FAILED TO STORE MEDICAL HISTORY - Collection: blood_pressure_histories")
            
            # Process SpO2
            if "spO2" in payload:
                total_metrics += 1
                spo2_data = {"value": payload["spO2"]}
                logger.info(f"🫁 Processing SpO2: {spo2_data}")
                
                logger.info(f"💾 UPDATING PATIENT COLLECTION - Field: spo2, Data: {spo2_data}")
                last_update_success = self.update_patient_last_data(patient_id, "spo2", spo2_data, "Kati", patient_name)
                if last_update_success:
                    logger.info(f"✅ PATIENT COLLECTION UPDATED SUCCESSFULLY - Field: spo2")
                else:
                    logger.warning(f"⚠️ FAILED TO UPDATE PATIENT COLLECTION - Field: spo2")
                
                logger.info(f"📚 STORING MEDICAL HISTORY - Collection: spo2_histories, Data: {spo2_data}")
                history_success = self.store_medical_history(patient_id, "spo2", spo2_data, "Kati", None, patient_name)
                if history_success:
                    logger.info(f"✅ MEDICAL HISTORY STORED SUCCESSFULLY - Collection: spo2_histories")
                    success_count += 1
                else:
                    logger.warning(f"⚠️ FAILED TO STORE MEDICAL HISTORY - Collection: spo2_histories")
            
            # Process body temperature
            if "bodyTemperature" in payload:
                total_metrics += 1
                temp_data = {"value": payload["bodyTemperature"]}
                logger.info(f"🌡️ Processing body temperature: {temp_data}")
                
                logger.info(f"💾 UPDATING PATIENT COLLECTION - Field: body_temp, Data: {temp_data}")
                last_update_success = self.update_patient_last_data(patient_id, "body_temp", temp_data, "Kati", patient_name)
                if last_update_success:
                    logger.info(f"✅ PATIENT COLLECTION UPDATED SUCCESSFULLY - Field: body_temp")
                else:
                    logger.warning(f"⚠️ FAILED TO UPDATE PATIENT COLLECTION - Field: body_temp")
                
                logger.info(f"📚 STORING MEDICAL HISTORY - Collection: temprature_data_histories, Data: {temp_data}")
                history_success = self.store_medical_history(patient_id, "body_temp", temp_data, "Kati", None, patient_name)
                if history_success:
                    logger.info(f"✅ MEDICAL HISTORY STORED SUCCESSFULLY - Collection: temprature_data_histories")
                    success_count += 1
                else:
                    logger.warning(f"⚠️ FAILED TO STORE MEDICAL HISTORY - Collection: temprature_data_histories")
            
            logger.info(f"📊 Kati vital signs processing complete - {success_count}/{total_metrics} metrics processed successfully")
            return success_count > 0
            
        except Exception as e:
            logger.error(f"❌ Error processing Kati vital signs: {e}")
            return False
    
    def _process_kati_batch_vital_signs(self, patient_id: ObjectId, payload: Dict[str, Any], 
                                       patient_name: Optional[str] = None) -> bool:
        """Process Kati batch vital signs data (AP55)"""
        try:
            logger.info(f"📦 Processing Kati batch vital signs - Patient: {patient_id}")
            logger.info(f"📊 Batch payload keys: {list(payload.keys())}")
            
            data_list = payload.get("data", [])
            logger.info(f"📊 Processing {len(data_list)} batch readings")
            
            # Store the complete batch data in medical_data collection for web panel access
            batch_doc = {
                "patient_id": patient_id,
                "patient_name": patient_name,
                "device_type": "Kati_Watch",
                "source": "Kati",
                "data_type": "batch_vital_signs",
                "batch_count": len(data_list),
                "data": data_list,
                "timestamp": datetime.utcnow(),
                "created_at": datetime.utcnow()
            }
            
            logger.info(f"💾 STORING BATCH DATA - Collection: medical_data, Count: {len(data_list)}")
            batch_result = self.db.medical_data.insert_one(batch_doc)
            if batch_result.inserted_id:
                logger.info(f"✅ BATCH DATA STORED SUCCESSFULLY - ID: {batch_result.inserted_id}")
            else:
                logger.warning(f"⚠️ FAILED TO STORE BATCH DATA")
            
            # Process each vital sign in the batch for individual storage
            for i, data_item in enumerate(data_list):
                logger.debug(f"🔧 Processing batch item {i+1}/{len(data_list)}: {data_item}")
                
                # Process heart rate
                if "heartRate" in data_item:
                    heart_data = {"value": data_item["heartRate"]}
                    self.update_patient_last_data(patient_id, "heart_rate", heart_data, "Kati", patient_name)
                    self.store_medical_history(patient_id, "heart_rate", heart_data, "Kati", None, patient_name)
                
                # Process blood pressure
                if "bloodPressure" in data_item:
                    bp_data = data_item["bloodPressure"]
                    bp_processed = {
                        "systolic": bp_data.get("bp_sys"),
                        "diastolic": bp_data.get("bp_dia")
                    }
                    self.update_patient_last_data(patient_id, "blood_pressure", bp_processed, "Kati", patient_name)
                    self.store_medical_history(patient_id, "blood_pressure", bp_processed, "Kati", None, patient_name)
                
                # Process SpO2
                if "spO2" in data_item:
                    spo2_data = {"value": data_item["spO2"]}
                    self.update_patient_last_data(patient_id, "spo2", spo2_data, "Kati", patient_name)
                    self.store_medical_history(patient_id, "spo2", spo2_data, "Kati", None, patient_name)
                
                # Process body temperature
                if "bodyTemperature" in data_item:
                    temp_data = {"value": data_item["bodyTemperature"]}
                    self.update_patient_last_data(patient_id, "body_temp", temp_data, "Kati", patient_name)
                    self.store_medical_history(patient_id, "body_temp", temp_data, "Kati", None, patient_name)
            
            logger.info(f"✅ Successfully processed {len(data_list)} batch vital signs")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error processing Kati batch vital signs: {e}")
            return False
    
    def _process_kati_heartbeat(self, patient_id: ObjectId, payload: Dict[str, Any], 
                               patient_name: Optional[str] = None) -> bool:
        """Process Kati heartbeat data"""
        try:
            logger.info(f"💓 Processing Kati heartbeat data - Patient: {patient_id}")
            logger.info(f"📊 Heartbeat payload keys: {list(payload.keys())}")
            
            # Process step count
            if "step" in payload:
                step_data = {"value": payload["step"]}
                logger.info(f"👟 Processing step count: {step_data}")
                
                logger.info(f"💾 UPDATING PATIENT COLLECTION - Field: step_count, Data: {step_data}")
                last_update_success = self.update_patient_last_data(patient_id, "step_count", step_data, "Kati", patient_name)
                if last_update_success:
                    logger.info(f"✅ PATIENT COLLECTION UPDATED SUCCESSFULLY - Field: step_count")
                else:
                    logger.warning(f"⚠️ FAILED TO UPDATE PATIENT COLLECTION - Field: step_count")
                
                logger.info(f"📚 STORING MEDICAL HISTORY - Collection: step_histories, Data: {step_data}")
                history_success = self.store_medical_history(patient_id, "step_count", step_data, "Kati", None, patient_name)
                if history_success:
                    logger.info(f"✅ MEDICAL HISTORY STORED SUCCESSFULLY - Collection: step_histories")
                else:
                    logger.warning(f"⚠️ FAILED TO STORE MEDICAL HISTORY - Collection: step_histories")
            
            # Process battery level
            if "battery" in payload:
                battery_data = {"value": payload["battery"]}
                logger.info(f"🔋 Processing battery level: {battery_data}")
                
                logger.info(f"💾 UPDATING PATIENT COLLECTION - Field: battery_level, Data: {battery_data}")
                last_update_success = self.update_patient_last_data(patient_id, "battery_level", battery_data, "Kati", patient_name)
                if last_update_success:
                    logger.info(f"✅ PATIENT COLLECTION UPDATED SUCCESSFULLY - Field: battery_level")
                else:
                    logger.warning(f"⚠️ FAILED TO UPDATE PATIENT COLLECTION - Field: battery_level")
            
            # Process signal strength
            if "signalGSM" in payload:
                signal_data = {"value": payload["signalGSM"]}
                logger.info(f"📶 Processing signal strength: {signal_data}")
                
                logger.info(f"💾 UPDATING PATIENT COLLECTION - Field: signal_strength, Data: {signal_data}")
                last_update_success = self.update_patient_last_data(patient_id, "signal_strength", signal_data, "Kati", patient_name)
                if last_update_success:
                    logger.info(f"✅ PATIENT COLLECTION UPDATED SUCCESSFULLY - Field: signal_strength")
                else:
                    logger.warning(f"⚠️ FAILED TO UPDATE PATIENT COLLECTION - Field: signal_strength")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error processing Kati heartbeat: {e}")
            return False
    
    def _process_kati_emergency(self, patient_id: ObjectId, topic: str, payload: Dict[str, Any], 
                               patient_name: Optional[str] = None) -> bool:
        """Process Kati emergency alerts"""
        try:
            logger.info(f"🚨 Processing Kati emergency alert - Patient: {patient_id}, Topic: {topic}")
            logger.info(f"📊 Emergency payload keys: {list(payload.keys())}")
            logger.info(f"📊 Emergency payload data: {payload}")
            
            # Determine alert type based on topic
            if topic == "iMEDE_watch/sos":
                alert_type = "sos"
                logger.warning(f"🚨 SOS EMERGENCY ALERT DETECTED!")
            elif topic == "iMEDE_watch/fallDown":
                alert_type = "fall_down"
                logger.warning(f"⚠️ FALL DETECTION ALERT DETECTED!")
            else:
                alert_type = "unknown"
                logger.warning(f"❓ UNKNOWN EMERGENCY ALERT TYPE: {topic}")
            
            # Prepare alert data
            alert_data = {
                "type": alert_type,
                "status": payload.get("status", "ACTIVE"),
                "location": payload.get("location"),
                "imei": payload.get("IMEI"),
                "timestamp": datetime.utcnow(),
                "source": "Kati",
                "priority": "CRITICAL" if alert_type == "sos" else "HIGH"
            }
            
            # Store emergency alert in AMY.emergency_alarm collection
            emergency_doc = {
                "patient_id": patient_id,
                "patient_name": patient_name,
                "alert_type": alert_type,
                "alert_data": alert_data,
                "timestamp": datetime.utcnow(),
                "source": "Kati",
                "device_type": "Kati_Watch",
                "topic": topic,
                "status": "ACTIVE",
                "created_at": datetime.utcnow(),
                "processed": False
            }
            
            logger.info(f"🚨 STORING EMERGENCY ALERT - Collection: emergency_alarm, Type: {alert_type}")
            logger.info(f"📊 Emergency document: {emergency_doc}")
            
            result = self.db.emergency_alarm.insert_one(emergency_doc)
            
            if result.inserted_id:
                logger.warning(f"🚨 EMERGENCY ALERT STORED SUCCESSFULLY - ID: {result.inserted_id}")
                logger.warning(f"🚨 {alert_type.upper()} ALERT for patient {patient_id} ({patient_name})")
                logger.warning(f"🚨 Collection: emergency_alarm, Priority: {alert_data['priority']}")
                return True
            else:
                logger.error(f"❌ FAILED TO STORE EMERGENCY ALERT - Type: {alert_type}")
                return False
            
        except Exception as e:
            logger.error(f"❌ Error processing Kati emergency: {e}")
            return False
    
    def process_qube_data(self, patient_id: ObjectId, attribute: str, value: Dict[str, Any]) -> bool:
        """Process Qube-Vital data"""
        try:
            logger.info(f"🏥 Processing Qube-Vital data - Patient: {patient_id}, Attribute: {attribute}")
            logger.debug(f"📊 QUBE-VITAL RAW VALUE PAYLOAD: {value}")
            logger.debug(f"🔍 QUBE-VITAL ATTRIBUTE: {attribute}")
            logger.debug(f"👤 QUBE-VITAL PATIENT ID: {patient_id}")
            
            # Map Qube-Vital attributes to data types
            attribute_mapping = {
                "WBP_JUMPER": "blood_pressure",
                "CONTOUR": "blood_sugar",
                "BodyScale_JUMPER": "weight",
                "TEMO_Jumper": "body_temp",
                "Oximeter_JUMPER": "spo2"
            }
            
            data_type = attribute_mapping.get(attribute)
            if not data_type:
                logger.warning(f"❌ Unknown Qube-Vital attribute: {attribute}")
                return False
            
            logger.debug(f"📝 Attribute mapping: {attribute} -> {data_type}")
            
            processed_data = self._process_qube_device_data(data_type, value)
            if processed_data:
                logger.debug(f"✅ Qube-Vital data processed: {processed_data}")
                
                # Update last data
                last_update_success = self.update_patient_last_data(patient_id, data_type, processed_data, "Qube-Vital")
                if last_update_success:
                    logger.debug(f"✅ Last data updated successfully")
                else:
                    logger.warning(f"⚠️ Failed to update last data")
                
                # Store history
                history_success = self.store_medical_history(patient_id, data_type, processed_data, "Qube-Vital")
                if history_success:
                    logger.debug(f"✅ History stored successfully")
                else:
                    logger.warning(f"⚠️ Failed to store history")
                
                return last_update_success and history_success
            else:
                logger.warning(f"❌ Failed to process Qube-Vital device data")
                return False
            
        except Exception as e:
            logger.error(f"❌ Error processing Qube-Vital data: {e}")
            return False
    
    def _process_qube_device_data(self, data_type: str, value: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process individual Qube-Vital device data"""
        try:
            if data_type == "blood_pressure":
                return {
                    "systolic": value.get("bp_high"),
                    "diastolic": value.get("bp_low"),
                    "pulse": value.get("pr")
                }
            elif data_type == "blood_sugar":
                return {
                    "value": value.get("blood_glucose"),
                    "marker": value.get("marker")
                }
            elif data_type == "weight":
                return {
                    "value": value.get("weight"),
                    "resistance": value.get("Resistance")
                }
            elif data_type == "body_temp":
                return {
                    "value": value.get("Temp"),
                    "mode": value.get("mode")
                }
            elif data_type == "spo2":
                return {
                    "value": value.get("spo2"),
                    "pulse": value.get("pulse"),
                    "pi": value.get("pi")
                }
            else:
                logger.warning(f"Unknown data type for Qube-Vital processing: {data_type}")
                return None
                
        except Exception as e:
            logger.error(f"Error processing Qube-Vital device data: {e}")
            return None
    
    def close(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close() 