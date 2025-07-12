"""
Device-Patient Mapping Utility
Handles mapping between device identifiers and patient records
"""

import os
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from pymongo import MongoClient
from bson import ObjectId

logger = logging.getLogger(__name__)

class DeviceMapper:
    """Maps device identifiers to patient records"""
    
    def __init__(self, mongodb_uri: str, database_name: str = "AMY"):
        self.client = MongoClient(mongodb_uri)
        self.db = self.client[database_name]
        
    def find_patient_by_ava4_mac(self, mac_address: str) -> Optional[Dict[str, Any]]:
        """Find patient by AVA4 box MAC address"""
        try:
            patient = self.db.patients.find_one({"ava_mac_address": mac_address})
            return patient
        except Exception as e:
            logger.error(f"Error finding patient by AVA4 MAC {mac_address}: {e}")
            return None
    
    def find_patient_by_device_mac(self, device_mac: str, device_type: str) -> Optional[Dict[str, Any]]:
        """Find patient by medical device MAC address"""
        try:
            # Map device types to patient fields
            mac_field_mapping = {
                "blood_pressure": "blood_pressure_mac_address",
                "spo2": "fingertip_pulse_oximeter_mac_address", 
                "body_temp": "body_temperature_mac_address",
                "weight": "weight_scale_mac_address",
                "blood_sugar": "blood_glucose_mac_address",
                "uric": "uric_mac_address",
                "cholesterol": "cholesterol_mac_address"
            }
            
            field_name = mac_field_mapping.get(device_type)
            if not field_name:
                logger.warning(f"Unknown device type: {device_type}")
                return None
                
            patient = self.db.patients.find_one({field_name: device_mac})
            return patient
        except Exception as e:
            logger.error(f"Error finding patient by device MAC {device_mac}: {e}")
            return None
    
    def find_patient_by_kati_imei(self, imei: str) -> Optional[Dict[str, Any]]:
        """Find patient by Kati Watch IMEI"""
        try:
            # First check watches collection
            watch = self.db.watches.find_one({"imei": imei})
            if watch and watch.get("patient_id"):
                # Convert patient_id to ObjectId if it's a string
                patient_id = watch["patient_id"]
                if isinstance(patient_id, str):
                    try:
                        patient_id = ObjectId(patient_id)
                    except Exception:
                        logger.warning(f"Invalid ObjectId format: {patient_id}")
                        return None
                
                patient = self.db.patients.find_one({"_id": patient_id})
                return patient
            
            # Fallback: check patients collection directly
            patient = self.db.patients.find_one({"watch_mac_address": imei})
            return patient
        except Exception as e:
            logger.error(f"Error finding patient by Kati IMEI {imei}: {e}")
            return None
    
    def find_patient_by_citiz(self, citiz: str) -> Optional[Dict[str, Any]]:
        """Find patient by citizen ID (Qube-Vital)"""
        try:
            patient = self.db.patients.find_one({"id_card": citiz})
            return patient
        except Exception as e:
            logger.error(f"Error finding patient by citizen ID {citiz}: {e}")
            return None
    
    def create_unregistered_patient(self, citiz: str, name_th: str, name_en: str, 
                                   birth_date: str, gender: str) -> Optional[Dict[str, Any]]:
        """Create new patient for unregistered Qube-Vital user"""
        try:
            # Parse birth date (format: YYYYMMDD)
            try:
                birth_datetime = datetime.strptime(birth_date, "%Y%m%d")
            except ValueError:
                birth_datetime = None
            
            patient_data = {
                "id_card": citiz,
                "first_name": name_en.split()[0] if name_en else "",
                "last_name": " ".join(name_en.split()[1:]) if name_en and len(name_en.split()) > 1 else "",
                "nickname": name_th if name_th else "",
                "gender": "male" if gender == "1" else "female",
                "birth_date": birth_datetime,
                "is_active": True,
                "is_deleted": False,
                "registration_status": "unregistered",  # Mark as unregistered
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            result = self.db.patients.insert_one(patient_data)
            if result.inserted_id:
                patient_data["_id"] = result.inserted_id
                logger.info(f"Created unregistered patient with ID: {result.inserted_id}")
                return patient_data
            
            return None
        except Exception as e:
            logger.error(f"Error creating unregistered patient: {e}")
            return None
    
    def get_device_info(self, device_mac: str) -> Optional[Dict[str, Any]]:
        """Get device information from amy_devices collection"""
        try:
            device = self.db.amy_devices.find_one({"mac_address": device_mac})
            return device
        except Exception as e:
            logger.error(f"Error getting device info for {device_mac}: {e}")
            return None
    
    def close(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close() 