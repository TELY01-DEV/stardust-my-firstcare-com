"""
MQTT Monitor Shared Utilities
Handles MQTT message processing and patient mapping for monitoring
"""

import os
import json
import logging
import ssl
from datetime import datetime
from typing import Dict, Any, Optional, List
from pymongo import MongoClient
from bson import ObjectId

logger = logging.getLogger(__name__)

class MQTTMonitor:
    """MQTT Message Monitor and Patient Mapper"""
    
    def __init__(self, mongodb_uri: str, database_name: str = "AMY"):
        self.client = None
        self.db = None
        self.connect_to_mongodb(mongodb_uri, database_name)
        
    def connect_to_mongodb(self, mongodb_uri: str, database_name: str):
        """Connect to MongoDB with SSL certificate support"""
        try:
            # Check if SSL certificate files exist
            ssl_ca_file = os.getenv('MONGODB_SSL_CA_FILE', '/app/ssl/ca-latest.pem')
            ssl_client_file = os.getenv('MONGODB_SSL_CLIENT_FILE', '/app/ssl/client-combined-latest.pem')
            
            ssl_ca_exists = os.path.exists(ssl_ca_file)
            ssl_client_exists = os.path.exists(ssl_client_file)
            
            # MongoDB configuration with SSL
            mongodb_config = {
                "host": os.getenv('MONGODB_HOST', 'coruscant.my-firstcare.com'),
                "port": int(os.getenv('MONGODB_PORT', 27023)),
                "username": os.getenv('MONGODB_USERNAME', 'opera_admin'),
                "password": os.getenv('MONGODB_PASSWORD', 'Sim!443355'),
                "authSource": os.getenv('MONGODB_AUTH_DB', 'admin'),
                "tls": True,
                "tlsAllowInvalidCertificates": True,
                "tlsAllowInvalidHostnames": True,
                "serverSelectionTimeoutMS": 10000,
                "connectTimeoutMS": 10000
            }
            
            # Add SSL certificate files if they exist
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
            
            # Create client
            self.client = MongoClient(**mongodb_config)
            
            # Test connection
            self.client.admin.command('ping')
            logger.info("✅ Connected to production MongoDB cluster with SSL")
            
            # Set database
            self.db = self.client[database_name]
            logger.info(f"📊 Connected to database: {database_name}")
            
        except Exception as e:
            logger.error(f"❌ MongoDB connection failed: {e}")
            logger.warning(f"⚠️ MQTT Monitor will continue without MongoDB connection")
            logger.warning(f"⚠️ Patient mapping features will not work")
            self.client = None
            self.db = None
        
    def process_ava4_message(self, topic: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process AVA4 MQTT message and map to patient"""
        try:
            result = {
                "timestamp": datetime.utcnow(),
                "topic": topic,
                "device_type": "AVA4",
                "message_type": payload.get('type', 'unknown'),
                "raw_payload": payload,
                "patient_mapping": None,
                "medical_data": None,
                "status": "processed"
            }
            
            if self.db is None:
                result["status"] = "error"
                result["error"] = "MongoDB not connected"
                return result
            
            if topic == "ESP32_BLE_GW_TX":
                # AVA4 status message
                mac_address = payload.get('mac')
                imei = payload.get('IMEI')
                
                if mac_address:
                    patient = self.db.patients.find_one({"ava_mac_address": mac_address})
                    if patient:
                        result["patient_mapping"] = {
                            "patient_id": str(patient['_id']),
                            "patient_name": f"{patient.get('first_name', '')} {patient.get('last_name', '')}".strip(),
                            "mapping_type": "ava_mac_address",
                            "mapping_value": mac_address
                        }
                    else:
                        result["status"] = "patient_not_found"
                        result["patient_mapping"] = {
                            "mapping_type": "ava_mac_address",
                            "mapping_value": mac_address,
                            "error": "No patient found for this AVA4 MAC"
                        }
                
                result["device_info"] = {
                    "mac": mac_address,
                    "imei": imei,
                    "device_name": payload.get('name', 'Unknown')
                }
                
            elif topic == "dusun_sub":
                # AVA4 medical device data
                device_mac = payload.get('mac')
                attribute = payload.get('data', {}).get('attribute')
                value = payload.get('data', {}).get('value', {})
                
                # Try to find patient by device MAC in amy_devices
                device_info = self.db.amy_devices.find_one({"mac_address": device_mac})
                patient = None
                
                if device_info and device_info.get('patient_id'):
                    # Convert patient_id to ObjectId
                    patient_id = device_info['patient_id']
                    
                    try:
                        from bson import ObjectId
                        
                        if isinstance(patient_id, dict) and '$oid' in patient_id:
                            # MongoDB extended JSON format as dict: {'$oid': '507f1f77bcf86cd799439011'}
                            patient_id = ObjectId(patient_id['$oid'])
                        elif isinstance(patient_id, str):
                            # Handle various string ObjectId formats
                            if patient_id.startswith('{"$oid":') and patient_id.endswith('}'):
                                # MongoDB extended JSON format: {"$oid": "507f1f77bcf86cd799439011"}
                                import json
                                oid_data = json.loads(patient_id)
                                patient_id = ObjectId(oid_data['$oid'])
                            elif patient_id.startswith('ObjectId(') and patient_id.endswith(')'):
                                # Python ObjectId string format: ObjectId("507f1f77bcf86cd799439011")
                                oid_str = patient_id[9:-1].strip('"\'')
                                patient_id = ObjectId(oid_str)
                            elif len(patient_id) == 24 and all(c in '0123456789abcdef' for c in patient_id.lower()):
                                # Direct 24-character hex string: 507f1f77bcf86cd799439011
                                patient_id = ObjectId(patient_id)
                            else:
                                # Try direct conversion (might fail)
                                patient_id = ObjectId(patient_id)
                        elif isinstance(patient_id, ObjectId):
                            # Already an ObjectId
                            pass
                        else:
                            logger.warning(f"Unknown patient_id format: {patient_id} (type: {type(patient_id)})")
                            patient_id = None
                            
                    except Exception as e:
                        logger.warning(f"Invalid ObjectId format: {patient_id}, error: {e}")
                        patient_id = None
                    
                    if patient_id:
                        patient = self.db.patients.find_one({"_id": patient_id})
                
                # If not found, try device type mapping
                if not patient and attribute:
                    device_type_mapping = {
                        "BP_BIOLIGTH": "blood_pressure",
                        "Contour_Elite": "blood_sugar",
                        "AccuChek_Instant": "blood_sugar",
                        "Oximeter JUMPER": "spo2",
                        "IR_TEMO_JUMPER": "body_temp",
                        "BodyScale_JUMPER": "weight",
                        "MGSS_REF_UA": "uric",
                        "MGSS_REF_CHOL": "cholesterol"
                    }
                    
                    device_type = device_type_mapping.get(attribute)
                    if device_type:
                        field_mapping = {
                            "blood_pressure": "blood_pressure_mac_address",
                            "blood_sugar": "blood_glucose_mac_address",
                            "spo2": "fingertip_pulse_oximeter_mac_address",
                            "body_temp": "body_temperature_mac_address",
                            "weight": "weight_scale_mac_address",
                            "uric": "uric_mac_address",
                            "cholesterol": "cholesterol_mac_address"
                        }
                        
                        field_name = field_mapping.get(device_type)
                        if field_name:
                            patient = self.db.patients.find_one({field_name: device_mac})
                
                if patient:
                    result["patient_mapping"] = {
                        "patient_id": str(patient['_id']),
                        "patient_name": f"{patient.get('first_name', '')} {patient.get('last_name', '')}".strip(),
                        "mapping_type": "device_mac",
                        "mapping_value": device_mac,
                        "device_type": device_type if 'device_type' in locals() else "unknown"
                    }
                else:
                    result["status"] = "patient_not_found"
                    result["patient_mapping"] = {
                        "mapping_type": "device_mac",
                        "mapping_value": device_mac,
                        "error": "No patient found for this device MAC"
                    }
                
                result["medical_data"] = {
                    "attribute": attribute,
                    "device_mac": device_mac,
                    "device_code": payload.get('deviceCode'),
                    "device_name": payload.get('device'),
                    "value": value
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing AVA4 message: {e}")
            return {
                "timestamp": datetime.utcnow(),
                "topic": topic,
                "device_type": "AVA4",
                "raw_payload": payload,
                "status": "error",
                "error": str(e)
            }
    
    def process_kati_message(self, topic: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process Kati Watch MQTT message and map to patient"""
        try:
            result = {
                "timestamp": datetime.utcnow(),
                "topic": topic,
                "device_type": "Kati Watch",
                "raw_payload": payload,
                "patient_mapping": None,
                "medical_data": None,
                "status": "processed"
            }
            
            if self.db is None:
                result["status"] = "error"
                result["error"] = "MongoDB not connected"
                return result
            
            imei = payload.get('IMEI')
            if not imei:
                result["status"] = "error"
                result["error"] = "No IMEI found in Kati message"
                return result
            
            # Find patient by Kati IMEI
            watch = self.db.watches.find_one({"imei": imei})
            patient = None
            
            if watch and watch.get('patient_id'):
                # Convert patient_id to ObjectId
                patient_id = watch['patient_id']
                logger.info(f"Found watch with patient_id: {patient_id} (type: {type(patient_id)})")
                
                # Convert to proper ObjectId
                try:
                    from bson import ObjectId
                    
                    if isinstance(patient_id, dict) and '$oid' in patient_id:
                        # MongoDB extended JSON format as dict: {'$oid': '507f1f77bcf86cd799439011'}
                        converted_patient_id = ObjectId(patient_id['$oid'])
                        logger.info(f"✅ Converted patient_id from dict format: {patient_id} -> {converted_patient_id}")
                    elif isinstance(patient_id, str):
                        # Handle various string ObjectId formats
                        if patient_id.startswith('{"$oid":') and patient_id.endswith('}'):
                            # MongoDB extended JSON format: {"$oid": "507f1f77bcf86cd799439011"}
                            import json
                            oid_data = json.loads(patient_id)
                            converted_patient_id = ObjectId(oid_data['$oid'])
                            logger.info(f"✅ Converted patient_id from JSON string: {patient_id} -> {converted_patient_id}")
                        elif patient_id.startswith('ObjectId(') and patient_id.endswith(')'):
                            # Python ObjectId string format: ObjectId("507f1f77bcf86cd799439011")
                            oid_str = patient_id[9:-1].strip('"\'')
                            converted_patient_id = ObjectId(oid_str)
                            logger.info(f"✅ Converted patient_id from ObjectId string: {patient_id} -> {converted_patient_id}")
                        elif len(patient_id) == 24 and all(c in '0123456789abcdef' for c in patient_id.lower()):
                            # Direct 24-character hex string: 507f1f77bcf86cd799439011
                            converted_patient_id = ObjectId(patient_id)
                            logger.info(f"✅ Converted patient_id from hex string: {patient_id} -> {converted_patient_id}")
                        else:
                            # Try direct conversion (might fail)
                            converted_patient_id = ObjectId(patient_id)
                            logger.info(f"✅ Converted patient_id from direct string: {patient_id} -> {converted_patient_id}")
                    elif isinstance(patient_id, ObjectId):
                        # Already an ObjectId
                        converted_patient_id = patient_id
                        logger.info(f"✅ Patient_id already ObjectId: {converted_patient_id}")
                    else:
                        logger.warning(f"❌ Unknown patient_id format: {patient_id} (type: {type(patient_id)})")
                        converted_patient_id = None
                        
                except Exception as e:
                    logger.warning(f"❌ Invalid ObjectId format: {patient_id}, error: {e}")
                    converted_patient_id = None
                
                # Use the converted patient_id
                if converted_patient_id:
                    patient = self.db.patients.find_one({"_id": converted_patient_id})
            
            # Fallback: check patients collection directly
            if not patient:
                patient = self.db.patients.find_one({"watch_mac_address": imei})
            
            if patient:
                result["patient_mapping"] = {
                    "patient_id": str(patient['_id']),
                    "patient_name": f"{patient.get('first_name', '')} {patient.get('last_name', '')}".strip(),
                    "mapping_type": "kati_imei",
                    "mapping_value": imei
                }
            else:
                result["status"] = "patient_not_found"
                result["patient_mapping"] = {
                    "mapping_type": "kati_imei",
                    "mapping_value": imei,
                    "error": "No patient found for this Kati IMEI"
                }
            
            # Extract medical data based on topic
            if topic == "iMEDE_watch/VitalSign":
                result["medical_data"] = {
                    "data_type": "vital_signs",
                    "heart_rate": payload.get('heartRate'),
                    "blood_pressure": payload.get('bloodPressure'),
                    "spO2": payload.get('spO2'),
                    "body_temperature": payload.get('bodyTemperature'),
                    "location": payload.get('location')
                }
            elif topic == "iMEDE_watch/AP55":
                result["medical_data"] = {
                    "data_type": "batch_vital_signs",
                    "num_datas": payload.get('num_datas'),
                    "data": payload.get('data', [])
                }
            elif topic == "iMEDE_watch/hb":
                result["medical_data"] = {
                    "data_type": "heartbeat",
                    "signal_gsm": payload.get('signalGSM'),
                    "battery": payload.get('battery'),
                    "satellites": payload.get('satellites'),
                    "working_mode": payload.get('workingMode'),
                    "step": payload.get('step')
                }
            elif topic in ["iMEDE_watch/SOS", "iMEDE_watch/fallDown"]:
                alert_type = "sos" if topic == "iMEDE_watch/SOS" else "fall_down"
                result["medical_data"] = {
                    "data_type": "emergency_alert",
                    "alert_type": alert_type.upper(),
                    "status": payload.get('status'),
                    "location": payload.get('location')
                }
                # Save emergency alert to database if patient is found
                if patient:
                    try:
                        alert_data = {
                            "type": alert_type,
                            "status": payload.get('status', 'ACTIVE'),
                            "location": payload.get('location'),
                            "imei": imei,
                            "timestamp": datetime.utcnow(),
                            "source": "Kati",
                            "priority": "CRITICAL" if alert_type == "sos" else "HIGH"
                        }
                        emergency_doc = {
                            "patient_id": patient['_id'],
                            "patient_name": f"{patient.get('first_name', '')} {patient.get('last_name', '')}".strip(),
                            "alert_type": alert_type,
                            "alert_data": alert_data,
                            "timestamp": datetime.utcnow(),
                            "source": "Kati",
                            "status": "ACTIVE",
                            "created_at": datetime.utcnow(),
                            "processed": False
                        }
                        emergency_result = self.db.emergency_alarm.insert_one(emergency_doc)
                        if emergency_result.inserted_id:
                            logger.warning(f"🚨 EMERGENCY ALERT SAVED BY WEBSOCKET - ID: {emergency_result.inserted_id}")
                            logger.warning(f"🚨 {alert_type.upper()} ALERT for patient {patient['_id']} ({emergency_doc['patient_name']})")
                            logger.warning(f"🚨 Collection: emergency_alarm, Priority: {alert_data['priority']}")
                        else:
                            logger.error(f"❌ FAILED TO SAVE EMERGENCY ALERT - Type: {alert_type}")
                    except Exception as e:
                        logger.error(f"❌ Error saving emergency alert: {e}")
            else:
                result["medical_data"] = {
                    "data_type": "unknown",
                    "payload": payload
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing Kati message: {e}")
            return {
                "timestamp": datetime.utcnow(),
                "topic": topic,
                "device_type": "Kati Watch",
                "raw_payload": payload,
                "status": "error",
                "error": str(e)
            }
    
    def process_qube_message(self, topic: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process Qube-Vital MQTT message and map to patient"""
        try:
            result = {
                "timestamp": datetime.utcnow(),
                "topic": topic,
                "device_type": "Qube-Vital",
                "message_type": payload.get('type', 'unknown'),
                "raw_payload": payload,
                "patient_mapping": None,
                "medical_data": None,
                "hospital_mapping": None,
                "status": "processed"
            }
            
            if self.db is None:
                result["status"] = "error"
                result["error"] = "MongoDB not connected"
                return result
            
            if payload.get('type') == "HB_Msg":
                # Qube-Vital status message
                mac_address = payload.get('mac')
                imei = payload.get('IMEI')
                
                # Check hospital mapping
                if imei:
                    hospital = self.db.hospitals.find_one({"mac_hv01_box": imei})
                    if hospital:
                        result["hospital_mapping"] = {
                            "hospital_id": str(hospital['_id']),
                            "hospital_name": hospital.get('name', 'Unknown'),
                            "mapping_type": "hv01_box_imei",
                            "mapping_value": imei
                        }
                
                result["device_info"] = {
                    "mac": mac_address,
                    "imei": imei,
                    "device_name": payload.get('name', 'Unknown')
                }
                
            elif payload.get('type') == "reportAttribute":
                # Qube-Vital medical data
                citiz = payload.get('citiz')
                attribute = payload.get('data', {}).get('attribute')
                value = payload.get('data', {}).get('value', {})
                mac_address = payload.get('mac')
                
                # Find patient by citizen ID
                patient = self.db.patients.find_one({"id_card": citiz})
                
                if patient:
                    result["patient_mapping"] = {
                        "patient_id": str(patient['_id']),
                        "patient_name": f"{patient.get('first_name', '')} {patient.get('last_name', '')}".strip(),
                        "mapping_type": "citizen_id",
                        "mapping_value": citiz,
                        "registration_status": patient.get('registration_status', 'registered')
                    }
                else:
                    result["status"] = "patient_not_found"
                    result["patient_mapping"] = {
                        "mapping_type": "citizen_id",
                        "mapping_value": citiz,
                        "registration_status": "unregistered",
                        "error": "Patient not found - would be auto-created"
                    }
                
                # Check hospital mapping
                if mac_address:
                    hospital = self.db.hospitals.find_one({"mac_hv01_box": mac_address})
                    if hospital:
                        result["hospital_mapping"] = {
                            "hospital_id": str(hospital['_id']),
                            "hospital_name": hospital.get('name', 'Unknown'),
                            "mapping_type": "hv01_box_mac",
                            "mapping_value": mac_address
                        }
                
                result["medical_data"] = {
                    "attribute": attribute,
                    "device_mac": payload.get('data', {}).get('ble_mac'),
                    "value": value,
                    "patient_info": {
                        "citizen_id": citiz,
                        "name_th": payload.get('nameTH'),
                        "name_en": payload.get('nameEN'),
                        "birth_date": payload.get('brith'),
                        "gender": payload.get('gender')
                    }
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing Qube-Vital message: {e}")
            return {
                "timestamp": datetime.utcnow(),
                "topic": topic,
                "device_type": "Qube-Vital",
                "raw_payload": payload,
                "status": "error",
                "error": str(e)
            }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get monitoring statistics"""
        try:
            if self.db is None:
                return {
                    "totalMessages": 0,
                    "ava4Count": 0,
                    "katiCount": 0,
                    "qubeCount": 0,
                    "ava4Active": 0,
                    "katiActive": 0,
                    "qubeActive": 0,
                    "processingRate": 0
                }
            
            now = datetime.utcnow()
            one_hour_ago = now.replace(hour=now.hour - 1)
            
            # Get device counts
            ava4_count = self.db.amy_boxes.count_documents({})
            kati_count = self.db.watches.count_documents({})
            qube_count = self.db.hospitals.count_documents({"mac_hv01_box": {"$exists": True}})
            
            # Get active devices (devices with recent activity - simplified for now)
            ava4_active = ava4_count  # Assume all are active for now
            kati_active = kati_count
            qube_active = qube_count
            
            # Calculate processing rate (messages per minute) - simplified
            processing_rate = 0  # Will be updated by real-time data
            
            stats = {
                "totalMessages": 0,  # Will be updated by real-time data
                "ava4Count": ava4_count,
                "katiCount": kati_count,
                "qubeCount": qube_count,
                "ava4Active": ava4_active,
                "katiActive": kati_active,
                "qubeActive": qube_active,
                "processingRate": processing_rate
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {
                "totalMessages": 0,
                "ava4Count": 0,
                "katiCount": 0,
                "qubeCount": 0,
                "ava4Active": 0,
                "katiActive": 0,
                "qubeActive": 0,
                "processingRate": 0
            }
    
    def close(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close() 