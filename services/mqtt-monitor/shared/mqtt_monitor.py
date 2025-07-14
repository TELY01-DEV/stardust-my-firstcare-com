"""
MQTT Monitor Shared Utilities
Handles MQTT message processing and patient mapping for monitoring
"""

import os
import json
import logging
import ssl
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List
from pymongo import MongoClient
from bson import ObjectId

logger = logging.getLogger(__name__)

class TransactionLogger:
    """Transaction logging system for data processing events"""
    
    def __init__(self, db):
        self.db = db
        self.transactions_collection = db.transaction_logs
    
    async def log_transaction(self, operation: str, data_type: str, collection: str, 
                            patient_id: Optional[str] = None, status: str = "success", 
                            details: Optional[str] = None, device_id: Optional[str] = None):
        """Log a data processing transaction"""
        try:
            transaction = {
                "operation": operation,
                "data_type": data_type,
                "collection": collection,
                "patient_id": patient_id,
                "status": status,
                "details": details,
                "device_id": device_id,
                "timestamp": datetime.utcnow(),
                "created_at": datetime.utcnow()
            }
            
            await self.transactions_collection.insert_one(transaction)
            logger.info(f"📝 Transaction logged: {operation} - {data_type} - {collection}")
            
        except Exception as e:
            logger.error(f"Error logging transaction: {e}")
    
    async def get_recent_transactions(self, limit: int = 50):
        """Get recent transactions"""
        try:
            transactions = await self.transactions_collection.find().sort("timestamp", -1).limit(limit).to_list(length=limit)
            
            # Convert ObjectIds to strings
            for transaction in transactions:
                transaction["_id"] = str(transaction["_id"])
                transaction["timestamp"] = transaction["timestamp"].isoformat()
                transaction["created_at"] = transaction["created_at"].isoformat()
            
            return transactions
        except Exception as e:
            logger.error(f"Error getting transactions: {e}")
            return []

class MQTTMonitor:
    """MQTT Message Monitor and Patient Mapper"""
    
    def __init__(self, mongodb_uri: str, database_name: str = "AMY"):
        self.client = None
        self.db = None
        self.transaction_logger = None
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
            
            # Initialize transaction logger
            self.transaction_logger = TransactionLogger(self.db)
            logger.info("✅ Transaction logger initialized")
            
        except Exception as e:
            logger.error(f"❌ MongoDB connection failed: {e}")
            logger.warning(f"⚠️ MQTT Monitor will continue without MongoDB connection")
            logger.warning(f"⚠️ Patient mapping features will not work")
            self.client = None
            self.db = None
            self.transaction_logger = None

    def store_medical_data(self, patient_id: str, device_id: str, device_type: str, medical_data: Dict[str, Any]) -> bool:
        """Store medical data in the appropriate medical history collection"""
        try:
            if self.db is None:
                logger.error("MongoDB not connected")
                return False
            
            # Map data type to history type and collection
            history_type_mapping = {
                "blood_pressure": "blood_pressure_histories",
                "blood_sugar": "blood_sugar_histories", 
                "body_temperature": "temprature_data_histories",
                "spo2": "spo2_histories",
                "weight": "body_data_histories",
                "activity": "step_histories",
                "sleep": "sleep_data_histories",
                "uric_acid": "creatinine_histories",
                "cholesterol": "lipid_histories"
            }
            
            data_type = medical_data.get("data_type", "unknown")
            collection_name = history_type_mapping.get(data_type)
            
            if not collection_name:
                logger.warning(f"Unknown data type: {data_type}")
                return False
            
            collection = self.db[collection_name]
            
            # Prepare the data entry based on history type
            data_entry = {
                "timestamp": datetime.utcnow(),
                "device_id": device_id,
                "device_type": device_type
            }
            
            # Map fields according to the medical history models
            if data_type == "blood_pressure":
                data_entry.update({
                    "systolic": medical_data.get("systolic"),
                    "diastolic": medical_data.get("diastolic"),
                    "pulse": medical_data.get("pulse_rate") or medical_data.get("pulse")
                })
            elif data_type == "blood_sugar":
                data_entry.update({
                    "value": medical_data.get("blood_glucose") or medical_data.get("glucose_value"),
                    "unit": "mg/dL",
                    "meal_type": medical_data.get("meal_context") or medical_data.get("marker")
                })
            elif data_type == "body_temperature":
                data_entry.update({
                    "value": medical_data.get("body_temp") or medical_data.get("temperature"),
                    "unit": "°C"
                })
            elif data_type == "spo2":
                data_entry.update({
                    "value": medical_data.get("spo2") or medical_data.get("spO2")
                })
            elif data_type == "weight":
                data_entry.update({
                    "weight": medical_data.get("weight") or medical_data.get("weight_value"),
                    "height": medical_data.get("height"),
                    "bmi": medical_data.get("bmi"),
                    "body_fat": medical_data.get("body_fat")
                })
            elif data_type == "activity":
                data_entry.update({
                    "steps": medical_data.get("steps") or medical_data.get("step"),
                    "calories": medical_data.get("calories"),
                    "distance": medical_data.get("distance")
                })
            elif data_type == "sleep":
                data_entry.update({
                    "start_time": datetime.utcnow(),
                    "end_time": datetime.utcnow(),
                    "duration_minutes": int(medical_data.get("sleep_duration", 0) * 60),
                    "sleep_score": medical_data.get("sleep_quality"),
                    "deep_sleep_minutes": medical_data.get("deep_sleep"),
                    "light_sleep_minutes": medical_data.get("light_sleep"),
                    "rem_sleep_minutes": medical_data.get("rem_sleep")
                })
            elif data_type == "uric_acid":
                data_entry.update({
                    "value": medical_data.get("uric_acid"),
                    "unit": "mg/dL"
                })
            elif data_type == "cholesterol":
                data_entry.update({
                    "total_cholesterol": medical_data.get("cholesterol"),
                    "hdl": medical_data.get("hdl"),
                    "ldl": medical_data.get("ldl"),
                    "triglycerides": medical_data.get("triglycerides")
                })
            
            # Check if patient already has a record in this collection
            existing_record = collection.find_one({"patient_id": ObjectId(patient_id)})
            
            if existing_record:
                # Update existing record by adding to data array
                collection.update_one(
                    {"patient_id": ObjectId(patient_id)},
                    {
                        "$push": {"data": data_entry},
                        "$set": {
                            "updated_at": datetime.utcnow(),
                            "device_id": device_id,
                            "device_type": device_type
                        }
                    }
                )
            else:
                # Create new record
                new_record = {
                    "patient_id": ObjectId(patient_id),
                    "device_id": device_id,
                    "device_type": device_type,
                    "data": [data_entry],
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
                collection.insert_one(new_record)
            
            logger.info(f"Stored {data_type} data for patient {patient_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error storing medical data: {e}")
            return False
    
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
                    # Map AVA4 box to patient via amy_boxes.mac_address → patients.ava_mac_address
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
                # AVA4 medical device data - REAL PAYLOAD STRUCTURE
                device_mac = payload.get('mac')
                attribute = payload.get('data', {}).get('attribute')
                value_data = payload.get('data', {}).get('value', {})
                
                # Extract device_list from value (real AVA4 structure)
                device_list = value_data.get('device_list', [])
                if not device_list:
                    result["status"] = "error"
                    result["error"] = "No device_list found in AVA4 payload"
                    return result
                
                # Get the first device reading
                device_reading = device_list[0] if device_list else {}
                ble_addr = device_reading.get('ble_addr')
                
                # Find patient by device mapping according to requirements
                patient = None
                
                # First try: amy_devices.patient_id → patients._id
                device_info = self.db.amy_devices.find_one({"mac_address": device_mac})
                if device_info and device_info.get('patient_id'):
                    try:
                        patient_id = ObjectId(device_info['patient_id'])
                        patient = self.db.patients.find_one({"_id": patient_id})
                    except:
                        pass
                
                # Second try: Device-specific MAC mapping using ble_addr
                if not patient and ble_addr:
                    device_type_mapping = {
                        "BP_BIOLIGTH": "blood_pressure_mac_address",
                        "Contour_Elite": "blood_glucose_mac_address",
                        "AccuChek_Instant": "blood_glucose_mac_address",
                        "Oximeter JUMPER": "fingertip_pulse_oximeter_mac_address",
                        "IR_TEMO_JUMPER": "body_temperature_mac_address",
                        "BodyScale_JUMPER": "weight_scale_mac_address",
                        "MGSS_REF_UA": "uric_mac_address",
                        "MGSS_REF_CHOL": "cholesterol_mac_address"
                    }
                    
                    field_name = device_type_mapping.get(attribute)
                    if field_name:
                        patient = self.db.patients.find_one({field_name: ble_addr})
                
                # Third try: amy_devices with specific MAC fields
                if not patient and ble_addr:
                    amy_device_mapping = {
                        "BP_BIOLIGTH": "mac_dusun_bps",
                        "Oximeter JUMPER": "mac_oxymeter",
                        "IR_TEMO_JUMPER": "mac_body_temp",
                        "BodyScale_JUMPER": "mac_weight",
                        "Contour_Elite": "mac_gluc",
                        "AccuChek_Instant": "mac_gluc",
                        "MGSS_REF_UA": "mac_ua",
                        "MGSS_REF_CHOL": "mac_chol"
                    }
                    
                    mac_field = amy_device_mapping.get(attribute)
                    if mac_field:
                        device_info = self.db.amy_devices.find_one({mac_field: ble_addr})
                        if device_info and device_info.get('patient_id'):
                            try:
                                patient_id = ObjectId(device_info['patient_id'])
                                patient = self.db.patients.find_one({"_id": patient_id})
                            except:
                                pass
                
                if patient:
                    result["patient_mapping"] = {
                        "patient_id": str(patient['_id']),
                        "patient_name": f"{patient.get('first_name', '')} {patient.get('last_name', '')}".strip(),
                        "mapping_type": "device_ble_addr",
                        "mapping_value": ble_addr,
                        "device_type": attribute
                    }
                    
                    # Store medical data in medical history collections
                    if result["medical_data"] and result["medical_data"].get("data_type"):
                        device_id = f"{device_mac}_{ble_addr}"
                        self.store_medical_data(
                            patient_id=str(patient['_id']),
                            device_id=device_id,
                            device_type="AVA4",
                            medical_data=result["medical_data"]
                        )
                else:
                    result["status"] = "patient_not_found"
                    result["patient_mapping"] = {
                        "mapping_type": "device_ble_addr",
                        "mapping_value": ble_addr,
                        "error": "No patient found for this device BLE address",
                        "device_type": attribute
                    }
                
                # Parse medical data based on attribute (REAL AVA4 STRUCTURE)
                medical_data = {
                    "attribute": attribute,
                    "device_mac": device_mac,
                    "device_code": payload.get('deviceCode'),
                    "device_name": payload.get('device'),
                    "ble_addr": ble_addr,
                    "scan_time": device_reading.get('scan_time'),
                    "scan_rssi": device_reading.get('scan_rssi')
                }
                
                # Extract specific values based on attribute
                if attribute == "BP_BIOLIGTH":
                    medical_data.update({
                        "data_type": "blood_pressure",
                        "systolic": device_reading.get('bp_high'),
                        "diastolic": device_reading.get('bp_low'),
                        "pulse_rate": device_reading.get('PR')
                    })
                elif attribute == "Oximeter JUMPER":
                    medical_data.update({
                        "data_type": "spo2",
                        "spo2": device_reading.get('spo2'),
                        "pulse": device_reading.get('pulse'),
                        "pi": device_reading.get('pi')
                    })
                elif attribute in ["Contour_Elite", "AccuChek_Instant"]:
                    medical_data.update({
                        "data_type": "blood_sugar",
                        "blood_glucose": device_reading.get('blood_glucose'),
                        "marker": device_reading.get('marker')
                    })
                elif attribute == "IR_TEMO_JUMPER":
                    medical_data.update({
                        "data_type": "body_temperature",
                        "body_temp": device_reading.get('temp'),
                        "mode": device_reading.get('mode')
                    })
                elif attribute == "BodyScale_JUMPER":
                    medical_data.update({
                        "data_type": "weight",
                        "weight": device_reading.get('weight'),
                        "resistance": device_reading.get('resistance')
                    })
                elif attribute == "MGSS_REF_UA":
                    medical_data.update({
                        "data_type": "uric_acid",
                        "uric_acid": device_reading.get('uric_acid')
                    })
                elif attribute == "MGSS_REF_CHOL":
                    medical_data.update({
                        "data_type": "cholesterol",
                        "cholesterol": device_reading.get('cholesterol')
                    })
                else:
                    medical_data.update({
                        "data_type": "unknown",
                        "raw_device_data": device_reading
                    })
                
                result["medical_data"] = medical_data
            
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
            
            # Find patient by Kati IMEI according to requirements: watches.imei → patients.watch_mac_address
            patient = None
            
            # First try: watches.imei → patients.watch_mac_address
            watch = self.db.watches.find_one({"imei": imei})
            if watch and watch.get('patient_id'):
                try:
                    patient_id = ObjectId(watch['patient_id'])
                    patient = self.db.patients.find_one({"_id": patient_id})
                except:
                    pass
            
            # Second try: direct mapping in patients collection
            if not patient:
                patient = self.db.patients.find_one({"watch_mac_address": imei})
            
            # Third try: check if IMEI is stored in watch_mac_address field
            if not patient:
                # Some systems might store IMEI in watch_mac_address field
                patient = self.db.patients.find_one({
                    "$or": [
                        {"watch_mac_address": imei},
                        {"watch_mac_address": {"$regex": imei, "$options": "i"}}
                    ]
                })
            
            if patient:
                result["patient_mapping"] = {
                    "patient_id": str(patient['_id']),
                    "patient_name": f"{patient.get('first_name', '')} {patient.get('last_name', '')}".strip(),
                    "mapping_type": "kati_imei",
                    "mapping_value": imei
                }
                
                # Store medical data in medical history collections
                if result["medical_data"] and result["medical_data"].get("data_type"):
                    self.store_medical_data(
                        patient_id=str(patient['_id']),
                        device_id=imei,
                        device_type="Kati Watch",
                        medical_data=result["medical_data"]
                    )
            else:
                result["status"] = "patient_not_found"
                result["patient_mapping"] = {
                    "mapping_type": "kati_imei",
                    "mapping_value": imei,
                    "error": "No patient found for this Kati IMEI"
                }
            
            # Extract medical data based on topic (REAL KATI STRUCTURE)
            if topic == "iMEDE_watch/VitalSign":
                # Single vital signs data
                blood_pressure = payload.get('bloodPressure', {})
                result["medical_data"] = {
                    "data_type": "vital_signs",
                    "heart_rate": payload.get('heartRate'),
                    "blood_pressure": {
                        "systolic": blood_pressure.get('bp_sys'),
                        "diastolic": blood_pressure.get('bp_dia')
                    },
                    "spO2": payload.get('spO2'),
                    "body_temperature": payload.get('bodyTemperature'),
                    "signal_gsm": payload.get('signalGSM'),
                    "battery": payload.get('battery'),
                    "location": payload.get('location'),
                    "time_stamps": payload.get('timeStamps')
                }
            elif topic == "iMEDE_watch/AP55":
                # Batch vital signs data
                result["medical_data"] = {
                    "data_type": "batch_vital_signs",
                    "num_datas": payload.get('num_datas'),
                    "location": payload.get('location'),
                    "time_stamps": payload.get('timeStamps'),
                    "data": payload.get('data', [])
                }
            elif topic == "iMEDE_watch/hb":
                # Heartbeat with step data
                result["medical_data"] = {
                    "data_type": "heartbeat",
                    "signal_gsm": payload.get('signalGSM'),
                    "battery": payload.get('battery'),
                    "satellites": payload.get('satellites'),
                    "working_mode": payload.get('workingMode'),
                    "step": payload.get('step'),
                    "time_stamps": payload.get('timeStamps')
                }
            elif topic == "iMEDE_watch/sleepdata":
                # Sleep data
                sleep_data = payload.get('sleep', {})
                result["medical_data"] = {
                    "data_type": "sleep_data",
                    "sleep_duration": sleep_data.get('time'),
                    "sleep_quality": sleep_data.get('data'),
                    "sleep_count": sleep_data.get('num'),
                    "time_stamps": sleep_data.get('timeStamps')
                }
            elif topic in ["iMEDE_watch/sos", "iMEDE_watch/fallDown"]:
                # Emergency alerts
                result["medical_data"] = {
                    "data_type": "emergency_alert",
                    "alert_type": "SOS" if topic == "iMEDE_watch/sos" else "FALL_DETECTION",
                    "status": payload.get('status'),
                    "location": payload.get('location')
                }
            elif topic == "iMEDE_watch/location":
                # Location data
                result["medical_data"] = {
                    "data_type": "location",
                    "location": payload.get('location')
                }
            elif topic == "iMEDE_watch/onlineTrigger":
                # Online/offline status
                result["medical_data"] = {
                    "data_type": "status",
                    "status": payload.get('status')
                }
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
    
    def process_qube_vital_message(self, topic: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process Qube-Vital MQTT message and map to patient"""
        try:
            result = {
                "timestamp": datetime.utcnow(),
                "topic": topic,
                "device_type": "Qube-Vital",
                "raw_payload": payload,
                "patient_mapping": None,
                "medical_data": None,
                "status": "processed"
            }
            
            if self.db is None:
                result["status"] = "error"
                result["error"] = "MongoDB not connected"
                return result
            
            # Extract device identifier and citizen ID from Qube-Vital payload
            device_id = payload.get('device_id') or payload.get('deviceId') or payload.get('mac')
            citizen_id = payload.get('citiz')  # This maps to patients.national_id
            attribute = payload.get('attribute') or payload.get('data', {}).get('attribute')  # Device attribute
            
            if not device_id:
                result["status"] = "error"
                result["error"] = "No device ID found in Qube-Vital message"
                return result
            
            if not citizen_id:
                result["status"] = "error"
                result["error"] = "No citizen ID (citiz) found in Qube-Vital message"
                return result
            
            # Find patient by Qube-Vital mapping according to requirements
            # 1. MAC address → hospitals.mac_hv01_box
            # 2. citiz field → patients.national_id
            patient = None
            hospital = None
            
            # First: Check hospital mapping via MAC address
            hospital = self.db.hospitals.find_one({"mac_hv01_box": device_id})
            if hospital:
                result["hospital_mapping"] = {
                    "hospital_id": str(hospital['_id']),
                    "hospital_name": hospital.get('name', 'Unknown'),
                    "mapping_type": "hospital_mac",
                    "mapping_value": device_id
                }
            
            # Second: Find patient by citizen ID (citiz field)
            patient = self.db.patients.find_one({"national_id": citizen_id})
            
            # Third: If not found by national_id, try id_card field
            if not patient:
                patient = self.db.patients.find_one({"id_card": citizen_id})
            
            # Fourth: Try with cleaned citizen ID (remove any formatting)
            if not patient:
                clean_citizen_id = citizen_id.replace('-', '').replace(' ', '')
                patient = self.db.patients.find_one({
                    "$or": [
                        {"national_id": clean_citizen_id},
                        {"id_card": clean_citizen_id}
                    ]
                })
            
            if patient:
                result["patient_mapping"] = {
                    "patient_id": str(patient['_id']),
                    "patient_name": f"{patient.get('first_name', '')} {patient.get('last_name', '')}".strip(),
                    "mapping_type": "citizen_id",
                    "mapping_value": citizen_id,
                    "citizen_id": citizen_id
                }
                
                # Store medical data in medical history collections
                if result["medical_data"] and result["medical_data"].get("data_type"):
                    self.store_medical_data(
                        patient_id=str(patient['_id']),
                        device_id=device_id,
                        device_type="Qube-Vital",
                        medical_data=result["medical_data"]
                    )
                
                # Update patient document fields with Qube-Vital data
                if attribute and result["medical_data"]:
                    self.update_patient_medical_fields(
                        patient_id=str(patient['_id']),
                        attribute=attribute,
                        medical_data=result["medical_data"]
                    )
            else:
                result["status"] = "patient_not_found"
                result["patient_mapping"] = {
                    "mapping_type": "citizen_id",
                    "mapping_value": citizen_id,
                    "error": "No patient found for this citizen ID",
                    "citizen_id": citizen_id
                }
            
            # Extract medical data based on Qube-Vital payload structure and attribute
            data_type = payload.get('data_type') or payload.get('type', 'unknown')
            value_data = payload.get('data', {}).get('value', {}) if payload.get('data') else {}
            
            # Map attribute to data type and extract values
            if attribute == "WBP_JUMPER":
                result["medical_data"] = {
                    "data_type": "blood_pressure",
                    "systolic": value_data.get('bp_high') or value_data.get('systolic'),
                    "diastolic": value_data.get('bp_low') or value_data.get('diastolic'),
                    "mean": value_data.get('map'),
                    "pulse": value_data.get('pr') or value_data.get('pulse'),
                    "timestamp": payload.get('timestamp') or payload.get('time')
                }
            elif attribute == "CONTOUR":
                result["medical_data"] = {
                    "data_type": "blood_sugar",
                    "blood_glucose": value_data.get('blood_glucose') or value_data.get('glucose'),
                    "marker": value_data.get('marker'),
                    "timestamp": payload.get('timestamp') or payload.get('time')
                }
            elif attribute == "BodyScale_JUMPER":
                result["medical_data"] = {
                    "data_type": "weight",
                    "weight": value_data.get('weight'),
                    "bmi": value_data.get('bmi'),
                    "body_fat": value_data.get('body_fat'),
                    "timestamp": payload.get('timestamp') or payload.get('time')
                }
            elif attribute == "TEMO_Jumper":
                result["medical_data"] = {
                    "data_type": "body_temperature",
                    "body_temp": value_data.get('temp') or value_data.get('body_temp'),
                    "mode": value_data.get('mode'),
                    "timestamp": payload.get('timestamp') or payload.get('time')
                }
            elif attribute == "Oximeter_JUMPER":
                result["medical_data"] = {
                    "data_type": "spo2",
                    "spo2": value_data.get('spo2'),
                    "pulse": value_data.get('pulse'),
                    "pi": value_data.get('pi'),
                    "timestamp": payload.get('timestamp') or payload.get('time')
                }
            elif data_type == 'vital_signs' or 'vital' in topic.lower():
                result["medical_data"] = {
                    "data_type": "blood_pressure",  # Qube-Vital typically sends blood pressure
                    "systolic": payload.get('systolic') or payload.get('sbp'),
                    "diastolic": payload.get('diastolic') or payload.get('dbp'),
                    "pulse": payload.get('pulse') or payload.get('heart_rate') or payload.get('hr'),
                    "timestamp": payload.get('timestamp') or payload.get('time')
                }
            elif data_type == 'blood_glucose' or 'glucose' in topic.lower():
                result["medical_data"] = {
                    "data_type": "blood_sugar",
                    "blood_glucose": payload.get('glucose') or payload.get('value'),
                    "marker": payload.get('meal_context') or payload.get('context'),
                    "timestamp": payload.get('timestamp') or payload.get('time')
                }
            elif data_type == 'weight' or 'weight' in topic.lower():
                result["medical_data"] = {
                    "data_type": "weight",
                    "weight": payload.get('weight') or payload.get('value'),
                    "bmi": payload.get('bmi'),
                    "body_fat": payload.get('body_fat'),
                    "timestamp": payload.get('timestamp') or payload.get('time')
                }
            elif data_type == 'activity' or 'step' in topic.lower():
                result["medical_data"] = {
                    "data_type": "activity",
                    "steps": payload.get('steps') or payload.get('step_count'),
                    "calories": payload.get('calories'),
                    "distance": payload.get('distance'),
                    "timestamp": payload.get('timestamp') or payload.get('time')
                }
            elif data_type == 'sleep' or 'sleep' in topic.lower():
                result["medical_data"] = {
                    "data_type": "sleep",
                    "sleep_duration": payload.get('sleep_duration') or payload.get('duration'),
                    "sleep_quality": payload.get('sleep_quality') or payload.get('quality'),
                    "deep_sleep": payload.get('deep_sleep'),
                    "light_sleep": payload.get('light_sleep'),
                    "rem_sleep": payload.get('rem_sleep'),
                    "timestamp": payload.get('timestamp') or payload.get('time')
                }
            else:
                result["medical_data"] = {
                    "data_type": "unknown",
                    "raw_data": payload
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
    
    def process_message(self, topic: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process MQTT message based on topic and device type"""
        try:
            # Determine device type from topic
            if "ESP32_BLE_GW_TX" in topic or "dusun_sub" in topic:
                return self.process_ava4_message(topic, payload)
            elif "iMEDE_watch" in topic:
                return self.process_kati_message(topic, payload)
            elif "qube" in topic.lower() or "vital" in topic.lower():
                return self.process_qube_vital_message(topic, payload)
            else:
                # Unknown device type
                return {
                    "timestamp": datetime.utcnow(),
                    "topic": topic,
                    "device_type": "Unknown",
                    "raw_payload": payload,
                    "status": "unknown_device",
                    "error": f"Unknown device type for topic: {topic}"
                }
                
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return {
                "timestamp": datetime.utcnow(),
                "topic": topic,
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

    def update_patient_medical_fields(self, patient_id: str, attribute: str, medical_data: Dict[str, Any]) -> bool:
        """Update patient document fields with Qube-Vital medical data based on attribute"""
        try:
            if self.db is None:
                logger.error("MongoDB not connected")
                return False
            
            patients_collection = self.db.patients
            update_data = {}
            current_time = datetime.utcnow()
            
            # Map attributes to patient document fields based on actual patient document structure
            if attribute == "WBP_JUMPER":
                # Blood pressure data
                update_data.update({
                    "last_blood_pressure": {
                        "systolic": medical_data.get("systolic"),
                        "diastolic": medical_data.get("diastolic"),
                        "timestamp": current_time.isoformat()
                    },
                    "gateway_blood_preassure_import_date": current_time,
                    "gateway_blood_preassure_source": 1,  # Qube-Vital source
                    "updated_at": current_time
                })
                
            elif attribute == "CONTOUR":
                # Blood glucose data
                meal_type = medical_data.get("marker", "no_marker")
                update_data.update({
                    "dtx_type_import_date": current_time,
                    "gateway_dtx_type_import_date": current_time,
                    "updated_at": current_time
                })
                
                # Handle different meal types
                if meal_type == "fasting":
                    update_data["fasting_dtx_import_date"] = current_time
                elif meal_type == "pre_meal":
                    update_data["pre_meal_dtx_import_date"] = current_time
                elif meal_type == "post_meal":
                    update_data["post_meal_dtx_import_date"] = current_time
                else:
                    update_data["no_marker_dtx_import_date"] = current_time
                
            elif attribute == "BodyScale_JUMPER":
                # Weight/Body data
                update_data.update({
                    "weight": medical_data.get("weight"),
                    "bmi": medical_data.get("bmi"),
                    "gateway_weight": medical_data.get("weight"),
                    "gateway_body_data_import_date": current_time,
                    "last_weight": medical_data.get("weight"),
                    "updated_at": current_time
                })
                
            elif attribute == "TEMO_Jumper":
                # Body temperature data
                update_data.update({
                    "gateway_temprature_import_date": current_time,
                    "gateway_temprature_source": 0,  # Qube-Vital source
                    "last_body_temperature": {
                        "value": medical_data.get("body_temp"),
                        "timestamp": current_time.isoformat()
                    },
                    "updated_at": current_time
                })
                
            elif attribute == "Oximeter_JUMPER":
                # SpO2 data
                update_data.update({
                    "gateway_spo2_data": medical_data.get("spo2"),
                    "gateway_spo2_pr_data": medical_data.get("pulse"),
                    "gateway_spo2_import_date": current_time,
                    "gateway_spo2_source": 0,  # Qube-Vital source
                    "last_spo2": {
                        "value": medical_data.get("spo2"),
                        "timestamp": current_time.isoformat()
                    },
                    "updated_at": current_time
                })
            
            if update_data:
                # Update patient document
                result = patients_collection.update_one(
                    {"_id": ObjectId(patient_id)},
                    {"$set": update_data, "$inc": {"__v": 1}}
                )
                
                if result.modified_count > 0:
                    logger.info(f"Updated patient {patient_id} with {attribute} data")
                    return True
                else:
                    logger.warning(f"No patient document updated for {patient_id}")
                    return False
            else:
                logger.warning(f"No update data for attribute: {attribute}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating patient medical fields: {e}")
            return False

    def update_patient_document_fields(self, patient_id: str, device_type: str, medical_data: Dict[str, Any]) -> bool:
        """
        Update patient document fields with medical data based on actual patient document structure
        """
        try:
            if self.db is None:
                logger.error("MongoDB not connected")
                return False
            
            patients_collection = self.db.patients
            
            # Convert patient_id to ObjectId
            if isinstance(patient_id, str):
                patient_object_id = ObjectId(patient_id)
            else:
                patient_object_id = patient_id
            
            # Get current timestamp
            current_time = datetime.utcnow()
            
            # Prepare update data based on device type and medical data
            update_data: Dict[str, Any] = {
                "updated_at": current_time
            }
            
            if device_type == "AVA4":
                # AVA4 device updates
                if "blood_pressure" in medical_data:
                    bp_data = medical_data["blood_pressure"]
                    update_data.update({
                        "last_blood_pressure": {
                            "systolic": bp_data.get("systolic"),
                            "diastolic": bp_data.get("diastolic"),
                            "timestamp": current_time.isoformat()
                        },
                        "blood_preassure_import_date": current_time,
                        "blood_preassure_source": 4  # AVA4 source
                    })
                
                if "spo2" in medical_data:
                    spo2_data = medical_data["spo2"]
                    update_data.update({
                        "spo2_data": spo2_data.get("value"),
                        "spo2_resp_data": spo2_data.get("respiratory_rate"),
                        "spo2_pr_data": spo2_data.get("pulse_rate"),
                        "spo2_pi_data": spo2_data.get("perfusion_index"),
                        "spo2_import_date": current_time,
                        "spo2_source": 4,  # AVA4 source
                        "last_spo2": {
                            "value": spo2_data.get("value"),
                            "timestamp": current_time.isoformat()
                        }
                    })
                
                if "temperature" in medical_data:
                    temp_data = medical_data["temperature"]
                    update_data.update({
                        "temprature_import_date": current_time,
                        "temprature_source": 4,  # AVA4 source
                        "last_body_temperature": {
                            "value": temp_data.get("value"),
                            "timestamp": current_time.isoformat()
                        }
                    })
                
                if "weight" in medical_data:
                    weight_data = medical_data["weight"]
                    update_data.update({
                        "weight": weight_data.get("value"),
                        "bmi": weight_data.get("bmi"),
                        "body_data_import_date": current_time,
                        "body_data_source": 1,  # AVA4 source
                        "last_weight": weight_data.get("value"),
                        "gateway_weight": weight_data.get("value"),
                        "gateway_body_data_import_date": current_time
                    })
                
                if "blood_sugar" in medical_data:
                    bs_data = medical_data["blood_sugar"]
                    update_data.update({
                        "blood_sugar_import_date": current_time,
                        "blood_sugar_source": 4  # AVA4 source
                    })
                    
                    # Handle different meal types
                    meal_type = bs_data.get("meal_type", "no_marker")
                    if meal_type == "fasting":
                        update_data["fasting_dtx_import_date"] = current_time
                    elif meal_type == "pre_meal":
                        update_data["pre_meal_dtx_import_date"] = current_time
                    elif meal_type == "post_meal":
                        update_data["post_meal_dtx_import_date"] = current_time
                    else:
                        update_data["no_marker_dtx_import_date"] = current_time
                
                if "cholesterol" in medical_data:
                    chol_data = medical_data["cholesterol"]
                    update_data.update({
                        "cholesterol": chol_data.get("total_cholesterol"),
                        "cholesterol_data_import_date": current_time,
                        "last_cholesterol": chol_data.get("total_cholesterol")
                    })
                
                if "creatinine" in medical_data:
                    update_data.update({
                        "cretinines_import_date": current_time,
                        "cretinines_source": 4  # AVA4 source
                    })
                
                if "lipids" in medical_data:
                    update_data.update({
                        "lipids_import_date": current_time,
                        "lipids_source": 4  # AVA4 source
                    })
            
            elif device_type == "Kati":
                # Kati Watch updates
                if "blood_pressure" in medical_data:
                    bp_data = medical_data["blood_pressure"]
                    update_data.update({
                        "watch_blood_preassure_import_date": current_time,
                        "watch_blood_preassure_source": 4  # Kati source
                    })
                
                if "spo2" in medical_data:
                    spo2_data = medical_data["spo2"]
                    update_data.update({
                        "watch_spo2_data": spo2_data.get("value"),
                        "watch_spo2_pr_data": spo2_data.get("pulse_rate"),
                        "watch_spo2_import_date": current_time,
                        "watch_spo2_source": 4  # Kati source
                    })
                
                if "temperature" in medical_data:
                    update_data.update({
                        "watch_temprature_import_date": current_time,
                        "watch_temprature_source": 4  # Kati source
                    })
                
                if "steps" in medical_data:
                    update_data.update({
                        "step_import_date": current_time,
                        "step_source": 2  # Kati source
                    })
                
                if "sleep" in medical_data:
                    update_data.update({
                        "sleep_data_import_date": current_time
                    })
            
            elif device_type == "Qube-Vital":
                # Qube-Vital updates
                if "blood_pressure" in medical_data:
                    bp_data = medical_data["blood_pressure"]
                    update_data.update({
                        "gateway_blood_preassure_import_date": current_time,
                        "gateway_blood_preassure_source": 1  # Qube-Vital source
                    })
                
                if "spo2" in medical_data:
                    spo2_data = medical_data["spo2"]
                    update_data.update({
                        "gateway_spo2_data": spo2_data.get("value"),
                        "gateway_spo2_pr_data": spo2_data.get("pulse_rate"),
                        "gateway_spo2_import_date": current_time,
                        "gateway_spo2_source": 0  # Qube-Vital source
                    })
                
                if "temperature" in medical_data:
                    update_data.update({
                        "gateway_temprature_import_date": current_time,
                        "gateway_temprature_source": 0  # Qube-Vital source
                    })
                
                if "weight" in medical_data:
                    weight_data = medical_data["weight"]
                    update_data.update({
                        "gateway_weight": weight_data.get("value"),
                        "gateway_body_data_import_date": current_time
                    })
                
                if "blood_sugar" in medical_data:
                    bs_data = medical_data["blood_sugar"]
                    update_data.update({
                        "dtx_type_import_date": current_time,
                        "gateway_dtx_type_import_date": current_time
                    })
                    
                    # Handle different meal types
                    meal_type = bs_data.get("meal_type", "no_marker")
                    if meal_type == "fasting":
                        update_data["fasting_dtx_import_date"] = current_time
                    elif meal_type == "pre_meal":
                        update_data["pre_meal_dtx_import_date"] = current_time
                    elif meal_type == "post_meal":
                        update_data["post_meal_dtx_import_date"] = current_time
                    else:
                        update_data["no_marker_dtx_import_date"] = current_time
            
            # Update the patient document
            if update_data:
                result = patients_collection.update_one(
                    {"_id": patient_object_id},
                    {"$set": update_data, "$inc": {"__v": 1}}
                )
                
                if result.modified_count > 0:
                    logger.info(f"Updated patient document fields for patient {patient_id} with {device_type} data")
                    return True
                else:
                    logger.warning(f"No changes made to patient document for patient {patient_id}")
                    return False
            else:
                logger.warning(f"No update data for device type: {device_type}")
                return False
                    
        except Exception as e:
            logger.error(f"Error updating patient document fields: {e}")
            return False 