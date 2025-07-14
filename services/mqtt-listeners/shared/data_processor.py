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

# Import transaction logger
from transaction_logger import TransactionLogger

class DataProcessor:
    """Processes and stores medical data"""
    
    def __init__(self, mongodb_uri: str, database_name: str = "AMY"):
        self.client = MongoClient(mongodb_uri)
        self.db = self.client[database_name]
        self.transaction_logger = TransactionLogger()
        
    def update_patient_last_data(self, patient_id: ObjectId, data_type: str, 
                                data: Dict[str, Any], source: str = "device") -> bool:
        """Update patient's last/latest medical data"""
        try:
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
                "sleep_data": "last_sleep_data",
                "location": "last_location",
                "online_status": "last_online_status"
            }
            
            field_name = field_mapping.get(data_type)
            if not field_name:
                logger.warning(f"Unknown data type for last data update: {data_type}")
                return False
            
            # Add timestamp and source
            update_data = {
                **data,
                "timestamp": datetime.utcnow(),
                "source": source,
                "updated_at": datetime.utcnow()
            }
            
            result = self.db.patients.update_one(
                {"_id": patient_id},
                {
                    "$set": {
                        field_name: update_data,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            if result.modified_count > 0:
                logger.info(f"Updated last {data_type} data for patient {patient_id}")
                # Log transaction
                self.transaction_logger.log_data_update(
                    str(patient_id), data_type, f"{data_type}_histories", 
                    source, f"Updated last {data_type} data"
                )
                return True
            else:
                logger.warning(f"No patient found or no changes made for {patient_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating last data for patient {patient_id}: {e}")
            return False
    
    def store_medical_history(self, patient_id: ObjectId, data_type: str, 
                             data: Dict[str, Any], source: str = "device", 
                             device_id: Optional[str] = None) -> bool:
        """Store medical data to history collection"""
        try:
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
                "sleep_data": "sleep_data_histories",
                "location": "location_histories",
                "online_status": "online_status_histories"
            }
            
            collection_name = collection_mapping.get(data_type, "")
            if not collection_name:
                logger.warning(f"Unknown data type for history storage: {data_type}")
                return False
            
            # Prepare history document
            history_doc = {
                "patient_id": patient_id,
                "timestamp": datetime.utcnow(),
                "data": data,
                "source": source,
                "device_id": device_id or "",
                "created_at": datetime.utcnow()
            }
            
            result = self.db[collection_name].insert_one(history_doc)
            
            if result.inserted_id:
                logger.info(f"Stored {data_type} history for patient {patient_id}")
                # Log transaction
                self.transaction_logger.log_data_storage(
                    str(patient_id), data_type, collection_name, 
                    device_id, f"Stored {data_type} history"
                )
                return True
            else:
                logger.error(f"Failed to store {data_type} history for patient {patient_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error storing {data_type} history for patient {patient_id}: {e}")
            return False
    
    def process_ava4_data(self, patient_id: ObjectId, device_mac: str, 
                         attribute: str, value: Dict[str, Any]) -> bool:
        """Process AVA4 sub-device data"""
        try:
            # Map AVA4 attributes to data types
            attribute_mapping = {
                "BP_BIOLIGTH": "blood_pressure",
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
                logger.warning(f"Unknown AVA4 attribute: {attribute}")
                return False
            
            # Extract data from device_list
            device_list = value.get("device_list", [])
            if not device_list:
                logger.warning(f"No device data found for attribute {attribute}")
                return False
            
            # Process each device reading
            for device_data in device_list:
                processed_data = self._process_ava4_device_data(data_type, device_data)
                if processed_data:
                    # Update last data
                    self.update_patient_last_data(patient_id, data_type, processed_data, "AVA4")
                    # Store history
                    self.store_medical_history(patient_id, data_type, processed_data, "AVA4", device_mac)
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing AVA4 data: {e}")
            return False
    
    def _process_ava4_device_data(self, data_type: str, device_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process individual AVA4 device data"""
        try:
            if data_type == "blood_pressure":
                return {
                    "systolic": device_data.get("bp_high"),
                    "diastolic": device_data.get("bp_low"),
                    "pulse": device_data.get("PR"),
                    "scan_time": device_data.get("scan_time")
                }
            elif data_type == "blood_sugar":
                return {
                    "value": device_data.get("blood_glucose"),
                    "marker": device_data.get("marker"),
                    "scan_time": device_data.get("scan_time")
                }
            elif data_type == "spo2":
                return {
                    "value": device_data.get("spo2"),
                    "pulse": device_data.get("pulse"),
                    "pi": device_data.get("pi"),
                    "scan_time": device_data.get("scan_time")
                }
            elif data_type == "body_temp":
                return {
                    "value": device_data.get("temp"),
                    "mode": device_data.get("mode"),
                    "scan_time": device_data.get("scan_time")
                }
            elif data_type == "weight":
                return {
                    "value": device_data.get("weight"),
                    "resistance": device_data.get("resistance"),
                    "scan_time": device_data.get("scan_time")
                }
            elif data_type == "uric_acid":
                return {
                    "value": device_data.get("uric_acid"),
                    "scan_time": device_data.get("scan_time")
                }
            elif data_type == "cholesterol":
                return {
                    "value": device_data.get("cholesterol"),
                    "scan_time": device_data.get("scan_time")
                }
            else:
                logger.warning(f"Unknown data type for AVA4 processing: {data_type}")
                return None
                
        except Exception as e:
            logger.error(f"Error processing AVA4 device data: {e}")
            return None
    
    def process_kati_data(self, patient_id: ObjectId, topic: str, payload: Dict[str, Any]) -> bool:
        """Process Kati Watch data"""
        try:
            if topic == "iMEDE_watch/VitalSign":
                return self._process_kati_vital_signs(patient_id, payload)
            elif topic == "iMEDE_watch/AP55":
                return self._process_kati_batch_vital_signs(patient_id, payload)
            elif topic == "iMEDE_watch/hb":
                return self._process_kati_heartbeat(patient_id, payload)
            elif topic == "iMEDE_watch/location":
                return self._process_kati_location(patient_id, payload)
            elif topic == "iMEDE_watch/onlineTrigger":
                return self._process_kati_online_trigger(patient_id, payload)
            elif topic == "iMEDE_watch/sleepdata":
                return self._process_kati_sleep_data(patient_id, payload)
            elif topic == "iMEDE_watch/sos":
                return self._process_kati_emergency(patient_id, topic, payload)
            elif topic == "iMEDE_watch/fallDown":
                return self._process_kati_emergency(patient_id, topic, payload)
            else:
                logger.info(f"Unhandled Kati topic: {topic}")
                return True
                
        except Exception as e:
            logger.error(f"Error processing Kati data: {e}")
            return False
    
    def _process_kati_vital_signs(self, patient_id: ObjectId, payload: Dict[str, Any]) -> bool:
        """Process Kati vital signs data"""
        try:
            # Process heart rate
            if "heartRate" in payload:
                heart_data = {"value": payload["heartRate"]}
                self.update_patient_last_data(patient_id, "heart_rate", heart_data, "Kati")
                self.store_medical_history(patient_id, "heart_rate", heart_data, "Kati")
            
            # Process blood pressure
            if "bloodPressure" in payload:
                bp_data = payload["bloodPressure"]
                bp_processed = {
                    "systolic": bp_data.get("bp_sys"),
                    "diastolic": bp_data.get("bp_dia")
                }
                self.update_patient_last_data(patient_id, "blood_pressure", bp_processed, "Kati")
                self.store_medical_history(patient_id, "blood_pressure", bp_processed, "Kati")
            
            # Process SpO2
            if "spO2" in payload:
                spo2_data = {"value": payload["spO2"]}
                self.update_patient_last_data(patient_id, "spo2", spo2_data, "Kati")
                self.store_medical_history(patient_id, "spo2", spo2_data, "Kati")
            
            # Process body temperature
            if "bodyTemperature" in payload:
                temp_data = {"value": payload["bodyTemperature"]}
                self.update_patient_last_data(patient_id, "body_temp", temp_data, "Kati")
                self.store_medical_history(patient_id, "body_temp", temp_data, "Kati")
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing Kati vital signs: {e}")
            return False
    
    def _process_kati_batch_vital_signs(self, patient_id: ObjectId, payload: Dict[str, Any]) -> bool:
        """Process Kati batch vital signs data (AP55)"""
        try:
            data_list = payload.get("data", [])
            for data_item in data_list:
                # Process each vital sign in the batch
                if "heartRate" in data_item:
                    heart_data = {"value": data_item["heartRate"]}
                    self.update_patient_last_data(patient_id, "heart_rate", heart_data, "Kati")
                    self.store_medical_history(patient_id, "heart_rate", heart_data, "Kati")
                
                if "bloodPressure" in data_item:
                    bp_data = data_item["bloodPressure"]
                    bp_processed = {
                        "systolic": bp_data.get("bp_sys"),
                        "diastolic": bp_data.get("bp_dia")
                    }
                    self.update_patient_last_data(patient_id, "blood_pressure", bp_processed, "Kati")
                    self.store_medical_history(patient_id, "blood_pressure", bp_processed, "Kati")
                
                if "spO2" in data_item:
                    spo2_data = {"value": data_item["spO2"]}
                    self.update_patient_last_data(patient_id, "spo2", spo2_data, "Kati")
                    self.store_medical_history(patient_id, "spo2", spo2_data, "Kati")
                
                if "bodyTemperature" in data_item:
                    temp_data = {"value": data_item["bodyTemperature"]}
                    self.update_patient_last_data(patient_id, "body_temp", temp_data, "Kati")
                    self.store_medical_history(patient_id, "body_temp", temp_data, "Kati")
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing Kati batch vital signs: {e}")
            return False
    
    def _process_kati_heartbeat(self, patient_id: ObjectId, payload: Dict[str, Any]) -> bool:
        """Process Kati heartbeat data"""
        try:
            if "step" in payload:
                step_data = {"value": payload["step"]}
                self.update_patient_last_data(patient_id, "step_count", step_data, "Kati")
                self.store_medical_history(patient_id, "step_count", step_data, "Kati")
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing Kati heartbeat: {e}")
            return False
    
    def _process_kati_location(self, patient_id: ObjectId, payload: Dict[str, Any]) -> bool:
        """Process Kati location data"""
        try:
            # Extract location data from the nested structure
            location_info = payload.get("location", {})
            gps_data = location_info.get("GPS", {})
            
            location_data = {
                "latitude": gps_data.get("latitude"),
                "longitude": gps_data.get("longitude"),
                "speed": gps_data.get("speed"),
                "header": gps_data.get("header"),
                "wifi_data": location_info.get("WiFi"),
                "lbs_data": location_info.get("LBS"),
                "timestamp": datetime.utcnow(),
                "source_time": payload.get("time")
            }
            
            # Update patient's last location
            result = self.db.patients.update_one(
                {"_id": patient_id},
                {
                    "$set": {
                        "last_location": location_data,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            if result.modified_count > 0:
                logger.info(f"Updated location data for patient {patient_id}")
                # Log transaction
                self.transaction_logger.log_data_update(
                    str(patient_id), "location", "location_histories", 
                    "Kati", f"Updated location data: {gps_data.get('latitude')}, {gps_data.get('longitude')}"
                )
            
            # Store location history
            history_doc = {
                "patient_id": patient_id,
                "timestamp": datetime.utcnow(),
                "data": location_data,
                "source": "Kati",
                "device_id": payload.get("IMEI", ""),
                "created_at": datetime.utcnow()
            }
            
            self.db.location_histories.insert_one(history_doc)
            logger.info(f"Stored location history for patient {patient_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing Kati location: {e}")
            return False

    def _process_kati_online_trigger(self, patient_id: ObjectId, payload: Dict[str, Any]) -> bool:
        """Process Kati online trigger data"""
        try:
            # Extract status from the payload (based on real data structure)
            status = payload.get("status", "unknown")
            
            online_data = {
                "status": status,
                "timestamp": datetime.utcnow(),
                "device_id": payload.get("IMEI", "")
            }
            
            # Update patient's last online status
            result = self.db.patients.update_one(
                {"_id": patient_id},
                {
                    "$set": {
                        "last_online_status": online_data,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            if result.modified_count > 0:
                logger.info(f"Updated online status for patient {patient_id}: {status}")
                # Log transaction
                self.transaction_logger.log_data_update(
                    str(patient_id), "online_status", "online_status_histories", 
                    "Kati", f"Updated online status: {status}"
                )
            
            # Store online status history
            history_doc = {
                "patient_id": patient_id,
                "timestamp": datetime.utcnow(),
                "data": online_data,
                "source": "Kati",
                "device_id": payload.get("IMEI", ""),
                "created_at": datetime.utcnow()
            }
            
            self.db.online_status_histories.insert_one(history_doc)
            logger.info(f"Stored online status history for patient {patient_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing Kati online trigger: {e}")
            return False
    
    def _process_kati_emergency(self, patient_id: ObjectId, topic: str, payload: Dict[str, Any]) -> bool:
        """Process Kati emergency alerts"""
        try:
            alert_type = "SOS" if topic == "iMEDE_watch/sos" else "FALL_DETECTION"
            alert_data = {
                "type": alert_type,
                "status": payload.get("status"),
                "location": payload.get("location")
            }
            
            # Store emergency alert in a special collection
            emergency_doc = {
                "patient_id": patient_id,
                "alert_type": alert_type,
                "data": alert_data,
                "timestamp": datetime.utcnow(),
                "source": "Kati",
                "created_at": datetime.utcnow()
            }
            
            self.db.emergency_alerts.insert_one(emergency_doc)
            logger.warning(f"Emergency alert from Kati: {alert_type} for patient {patient_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing Kati emergency: {e}")
            return False
    
    def process_qube_data(self, patient_id: ObjectId, attribute: str, value: Dict[str, Any]) -> bool:
        """Process Qube-Vital data"""
        try:
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
                logger.warning(f"Unknown Qube-Vital attribute: {attribute}")
                return False
            
            processed_data = self._process_qube_device_data(data_type, value)
            if processed_data:
                # Update last data
                self.update_patient_last_data(patient_id, data_type, processed_data, "Qube-Vital")
                # Store history
                self.store_medical_history(patient_id, data_type, processed_data, "Qube-Vital")
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing Qube-Vital data: {e}")
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