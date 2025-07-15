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
        logger.info(f"DeviceMapper initialized for database: {database_name}")
        
    def find_patient_by_ava4_mac(self, mac_address: str) -> Optional[Dict[str, Any]]:
        """Find patient by AVA4 box MAC address"""
        try:
            logger.debug(f"🔍 AVA4 PATIENT LOOKUP - MAC: {mac_address}")
            logger.debug(f"📊 AVA4 LOOKUP QUERY: {{'ava_mac_address': '{mac_address}'}}")
            
            patient = self.db.patients.find_one({"ava_mac_address": mac_address})
            
            if patient:
                logger.info(f"✅ AVA4 PATIENT FOUND - ID: {patient.get('_id')} - Name: {patient.get('first_name', '')} {patient.get('last_name', '')}")
                logger.debug(f"📊 AVA4 PATIENT DATA: {patient}")
                return patient
            else:
                logger.warning(f"⚠️ AVA4 PATIENT NOT FOUND - MAC: {mac_address}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error finding patient by AVA4 MAC {mac_address}: {e}")
            return None
    
    def find_patient_by_device_mac(self, device_mac: str, device_type: str) -> Optional[Dict[str, Any]]:
        """Find patient by medical device MAC address"""
        try:
            logger.debug(f"🔍 Looking up patient by device MAC: {device_mac}, Type: {device_type}")
            
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
                logger.warning(f"❌ Unknown device type: {device_type}")
                return None
            
            logger.debug(f"📝 Field mapping: {device_type} -> {field_name}")
                
            patient = self.db.patients.find_one({field_name: device_mac})
            
            if patient:
                logger.info(f"✅ Found patient by device MAC: {patient.get('_id')} - {patient.get('first_name', '')} {patient.get('last_name', '')}")
                return patient
            else:
                logger.warning(f"⚠️ No patient found for device MAC: {device_mac}, Type: {device_type}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error finding patient by device MAC {device_mac}: {e}")
            return None
    
    def find_patient_by_kati_imei(self, imei: str) -> Optional[Dict[str, Any]]:
        """Find patient by Kati Watch IMEI"""
        try:
            logger.debug(f"🔍 KATI PATIENT LOOKUP - IMEI: {imei}")
            logger.debug(f"📊 KATI WATCH LOOKUP QUERY: {{'imei': '{imei}'}}")
            
            # First check watches collection
            watch = self.db.watches.find_one({"imei": imei})
            if watch and watch.get("patient_id"):
                logger.debug(f"📱 KATI WATCH FOUND - Patient ID: {watch.get('patient_id')}")
                logger.debug(f"📊 KATI WATCH DATA: {watch}")
                
                # Convert patient_id to ObjectId - handle various formats
                patient_id = watch["patient_id"]
                logger.debug(f"🔄 KATI PATIENT ID FORMAT: {patient_id} (type: {type(patient_id)})")
                
                try:
                    if isinstance(patient_id, dict) and '$oid' in patient_id:
                        # MongoDB extended JSON format as dict: {'$oid': '507f1f77bcf86cd799439011'}
                        patient_id = ObjectId(patient_id['$oid'])
                        logger.debug(f"🔄 KATI CONVERTED FROM DICT: {patient_id}")
                    elif isinstance(patient_id, str):
                        # Handle various string ObjectId formats
                        if patient_id.startswith('{"$oid":') and patient_id.endswith('}'):
                            # MongoDB extended JSON format: {"$oid": "507f1f77bcf86cd799439011"}
                            import json
                            oid_data = json.loads(patient_id)
                            patient_id = ObjectId(oid_data['$oid'])
                            logger.debug(f"🔄 KATI CONVERTED FROM JSON STRING: {patient_id}")
                        elif patient_id.startswith('ObjectId(') and patient_id.endswith(')'):
                            # Python ObjectId string format: ObjectId("507f1f77bcf86cd799439011")
                            oid_str = patient_id[9:-1].strip('"\'')
                            patient_id = ObjectId(oid_str)
                            logger.debug(f"🔄 KATI CONVERTED FROM PYTHON STRING: {patient_id}")
                        elif len(patient_id) == 24 and all(c in '0123456789abcdef' for c in patient_id.lower()):
                            # Direct 24-character hex string: 507f1f77bcf86cd799439011
                            patient_id = ObjectId(patient_id)
                            logger.debug(f"🔄 KATI CONVERTED FROM HEX STRING: {patient_id}")
                        else:
                            # Try direct conversion (might fail)
                            patient_id = ObjectId(patient_id)
                            logger.debug(f"🔄 KATI CONVERTED FROM DIRECT: {patient_id}")
                    elif isinstance(patient_id, ObjectId):
                        # Already an ObjectId
                        logger.debug(f"🔄 KATI ALREADY OBJECTID: {patient_id}")
                    else:
                        logger.warning(f"❌ KATI UNKNOWN PATIENT_ID FORMAT: {patient_id} (type: {type(patient_id)})")
                        return None
                        
                except Exception as e:
                    logger.warning(f"❌ KATI INVALID OBJECTID: {patient_id}, error: {e}")
                    return None
                
                logger.debug(f"📊 KATI PATIENT LOOKUP QUERY: {{'_id': {patient_id}}}")
                patient = self.db.patients.find_one({"_id": patient_id})
                if patient:
                    logger.info(f"✅ KATI PATIENT FOUND - ID: {patient.get('_id')} - Name: {patient.get('first_name', '')} {patient.get('last_name', '')}")
                    logger.debug(f"📊 KATI PATIENT DATA: {patient}")
                    return patient
                else:
                    logger.warning(f"⚠️ KATI PATIENT NOT FOUND - Patient ID: {patient_id}")
            
            # Fallback: check patients collection directly
            logger.debug(f"🔄 KATI FALLBACK LOOKUP - Query: {{'watch_mac_address': '{imei}'}}")
            patient = self.db.patients.find_one({"watch_mac_address": imei})
            
            if patient:
                logger.info(f"✅ KATI PATIENT FOUND (FALLBACK) - ID: {patient.get('_id')} - Name: {patient.get('first_name', '')} {patient.get('last_name', '')}")
                logger.debug(f"📊 KATI PATIENT DATA (FALLBACK): {patient}")
                return patient
            else:
                logger.warning(f"⚠️ KATI PATIENT NOT FOUND - IMEI: {imei}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error finding patient by Kati IMEI {imei}: {e}")
            return None
    
    def find_patient_by_citiz(self, citiz: str) -> Optional[Dict[str, Any]]:
        """Find patient by citizen ID (Qube-Vital)"""
        try:
            logger.debug(f"🔍 Looking up patient by citizen ID: {citiz}")
            
            patient = self.db.patients.find_one({"id_card": citiz})
            
            if patient:
                logger.info(f"✅ Found patient by citizen ID: {patient.get('_id')} - {patient.get('first_name', '')} {patient.get('last_name', '')}")
                return patient
            else:
                logger.warning(f"⚠️ No patient found for citizen ID: {citiz}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error finding patient by citizen ID {citiz}: {e}")
            return None
    
    def create_unregistered_patient(self, citiz: str, name_th: str, name_en: str, 
                                   birth_date: str, gender: str) -> Optional[Dict[str, Any]]:
        """Create new patient for unregistered Qube-Vital user"""
        try:
            logger.info(f"👤 Creating unregistered patient - Citizen ID: {citiz}, Name: {name_en}")
            logger.debug(f"📊 Patient data - Thai Name: {name_th}, English Name: {name_en}, Birth: {birth_date}, Gender: {gender}")
            
            # Parse birth date (format: YYYYMMDD)
            try:
                birth_datetime = datetime.strptime(birth_date, "%Y%m%d")
                logger.debug(f"📅 Parsed birth date: {birth_datetime}")
            except ValueError:
                birth_datetime = None
                logger.warning(f"⚠️ Invalid birth date format: {birth_date}")
            
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
            
            logger.debug(f"💾 Patient data prepared: {patient_data}")
            
            result = self.db.patients.insert_one(patient_data)
            if result.inserted_id:
                patient_data["_id"] = result.inserted_id
                logger.info(f"✅ Created unregistered patient with ID: {result.inserted_id}")
                return patient_data
            else:
                logger.error(f"❌ Failed to create unregistered patient")
                return None
            
        except Exception as e:
            logger.error(f"❌ Error creating unregistered patient: {e}")
            return None
    
    def get_device_info(self, device_mac: str) -> Optional[Dict[str, Any]]:
        """Get device information from amy_devices collection"""
        try:
            logger.debug(f"🔍 Looking up device info for MAC: {device_mac}")
            
            device = self.db.amy_devices.find_one({"mac_address": device_mac})
            
            if device:
                logger.debug(f"✅ Found device info: {device.get('device_type', 'unknown')} - Patient ID: {device.get('patient_id', 'none')}")
                return device
            else:
                logger.debug(f"⚠️ No device info found for MAC: {device_mac}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error getting device info for {device_mac}: {e}")
            return None
    
    def close(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            logger.info("🔌 MongoDB connection closed") 