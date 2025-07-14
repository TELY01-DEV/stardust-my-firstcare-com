"""
Device Status Service
====================
Manages device status tracking and reporting for all IoT medical devices
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from pymongo import MongoClient
from bson import ObjectId

logger = logging.getLogger(__name__)

class DeviceStatusService:
    """Service for managing device status across all IoT medical devices"""
    
    def __init__(self, mongodb_uri: str, database_name: str = "AMY"):
        self.client = MongoClient(mongodb_uri)
        self.db = self.client[database_name]
        self.collection = self.db.device_status
        
        # Create indexes for efficient querying
        self._create_indexes()
    
    def _create_indexes(self):
        """Create database indexes for efficient querying"""
        try:
            # Primary index on device_id
            self.collection.create_index("device_id", unique=True)
            
            # Index for patient queries
            self.collection.create_index("patient_id")
            
            # Index for device type queries
            self.collection.create_index("device_type")
            
            # Index for status queries
            self.collection.create_index("status.online")
            self.collection.create_index("status.last_seen")
            
            # Index for alert queries
            self.collection.create_index("alerts.sos_triggered")
            self.collection.create_index("alerts.low_battery")
            self.collection.create_index("alerts.poor_signal")
            
            # Compound index for monitoring
            self.collection.create_index([
                ("device_type", 1),
                ("status.online", 1),
                ("status.last_seen", 1)
            ])
            
            logger.info("Device status indexes created successfully")
            
        except Exception as e:
            logger.error(f"Error creating device status indexes: {e}")
    
    def update_device_status(self, device_id: str, device_type: str, 
                           status_data: Dict[str, Any], patient_id: Optional[ObjectId] = None) -> bool:
        """Update or create device status record"""
        try:
            current_time = datetime.utcnow()
            
            # Prepare update data
            update_data = {
                "device_id": device_id,
                "device_type": device_type,
                "status": {
                    "online": True,
                    "last_seen": current_time,
                    "updated_at": current_time
                },
                "metadata": {
                    "updated_at": current_time,
                    "last_processed_by": f"{device_type.lower()}_listener"
                }
            }
            
            # Add patient_id if provided
            if patient_id:
                update_data["patient_id"] = patient_id
            
            # Update status fields based on device type
            if device_type == "Kati":
                update_data["status"].update({
                    "battery_level": status_data.get("battery"),
                    "signal_strength": status_data.get("signalGSM"),
                    "working_mode": status_data.get("workingMode"),
                    "satellites": status_data.get("satellites")
                })
                
                # Update location if available
                if "location" in status_data:
                    location_info = status_data["location"]
                    gps_data = location_info.get("GPS", {})
                    update_data["location"] = {
                        "latitude": gps_data.get("latitude"),
                        "longitude": gps_data.get("longitude"),
                        "speed": gps_data.get("speed"),
                        "header": gps_data.get("header"),
                        "last_updated": current_time
                    }
                
                # Update health metrics if available
                health_metrics = {}
                if "heartRate" in status_data:
                    health_metrics["last_heart_rate"] = status_data["heartRate"]
                if "bloodPressure" in status_data:
                    bp_data = status_data["bloodPressure"]
                    health_metrics["last_blood_pressure"] = {
                        "systolic": bp_data.get("bp_sys"),
                        "diastolic": bp_data.get("bp_dia")
                    }
                if "spO2" in status_data:
                    health_metrics["last_spo2"] = status_data["spO2"]
                if "bodyTemperature" in status_data:
                    health_metrics["last_temperature"] = status_data["bodyTemperature"]
                if "step" in status_data:
                    health_metrics["last_step_count"] = status_data["step"]
                
                if health_metrics:
                    update_data["health_metrics"] = health_metrics
                
                # Update alerts
                alerts = {}
                if status_data.get("battery", 100) < 20:
                    alerts["low_battery"] = True
                if status_data.get("signalGSM", 100) < 30:
                    alerts["poor_signal"] = True
                
                if alerts:
                    alerts["last_alert_time"] = current_time
                    update_data["alerts"] = alerts
                
            elif device_type == "AVA4":
                update_data["status"].update({
                    "hardware_status": "OK" if status_data.get("type") == "HB_Msg" else "WARNING"
                })
                
                # Update communication info
                update_data["communication"] = {
                    "mqtt_topic": "ESP32_BLE_GW_TX",
                    "last_message_size": len(str(status_data)),
                    "connection_quality": "GOOD"
                }
                
            elif device_type == "Qube-Vital":
                update_data["status"].update({
                    "hardware_status": "OK"
                })
                
                # Update communication info
                update_data["communication"] = {
                    "mqtt_topic": "CM4_BLE_GW_TX",
                    "last_message_size": len(str(status_data)),
                    "connection_quality": "GOOD"
                }
            
            # Use upsert to create or update
            result = self.collection.update_one(
                {"device_id": device_id},
                {"$set": update_data},
                upsert=True
            )
            
            if result.modified_count > 0 or result.upserted_id:
                logger.info(f"Updated device status for {device_type} device: {device_id}")
                return True
            else:
                logger.warning(f"No changes made to device status for {device_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating device status for {device_id}: {e}")
            return False
    
    def get_device_status(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get current device status"""
        try:
            return self.collection.find_one({"device_id": device_id})
        except Exception as e:
            logger.error(f"Error getting device status for {device_id}: {e}")
            return None
    
    def get_all_devices_status(self, device_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get status of all devices or by type"""
        try:
            filter_query = {}
            if device_type:
                filter_query["device_type"] = device_type
            
            return list(self.collection.find(filter_query).sort("status.last_seen", -1))
        except Exception as e:
            logger.error(f"Error getting all devices status: {e}")
            return []
    
    def get_offline_devices(self, hours_offline: int = 24) -> List[Dict[str, Any]]:
        """Get devices that haven't reported in X hours"""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours_offline)
            return list(self.collection.find({
                "status.last_seen": {"$lt": cutoff_time}
            }).sort("status.last_seen", -1))
        except Exception as e:
            logger.error(f"Error getting offline devices: {e}")
            return []
    
    def get_low_battery_devices(self, threshold: int = 20) -> List[Dict[str, Any]]:
        """Get devices with low battery"""
        try:
            return list(self.collection.find({
                "status.battery_level": {"$lt": threshold}
            }).sort("status.battery_level", 1))
        except Exception as e:
            logger.error(f"Error getting low battery devices: {e}")
            return []
    
    def get_poor_signal_devices(self, threshold: int = 30) -> List[Dict[str, Any]]:
        """Get devices with poor signal"""
        try:
            return list(self.collection.find({
                "status.signal_strength": {"$lt": threshold}
            }).sort("status.signal_strength", 1))
        except Exception as e:
            logger.error(f"Error getting poor signal devices: {e}")
            return []
    
    def get_emergency_devices(self) -> List[Dict[str, Any]]:
        """Get devices with active emergency alerts"""
        try:
            return list(self.collection.find({
                "$or": [
                    {"alerts.sos_triggered": True},
                    {"alerts.fall_detected": True}
                ]
            }).sort("alerts.last_alert_time", -1))
        except Exception as e:
            logger.error(f"Error getting emergency devices: {e}")
            return []
    
    def get_device_summary(self) -> Dict[str, Any]:
        """Get summary statistics of all devices"""
        try:
            total_devices = self.collection.count_documents({})
            online_devices = self.collection.count_documents({"status.online": True})
            offline_devices = self.collection.count_documents({"status.online": False})
            
            # Count by device type
            kati_devices = self.collection.count_documents({"device_type": "Kati"})
            ava4_devices = self.collection.count_documents({"device_type": "AVA4"})
            qube_devices = self.collection.count_documents({"device_type": "Qube-Vital"})
            
            # Count alerts
            low_battery_count = self.collection.count_documents({"alerts.low_battery": True})
            poor_signal_count = self.collection.count_documents({"alerts.poor_signal": True})
            emergency_count = self.collection.count_documents({
                "$or": [
                    {"alerts.sos_triggered": True},
                    {"alerts.fall_detected": True}
                ]
            })
            
            return {
                "total_devices": total_devices,
                "online_devices": online_devices,
                "offline_devices": offline_devices,
                "device_types": {
                    "Kati": kati_devices,
                    "AVA4": ava4_devices,
                    "Qube-Vital": qube_devices
                },
                "alerts": {
                    "low_battery": low_battery_count,
                    "poor_signal": poor_signal_count,
                    "emergency": emergency_count
                },
                "last_updated": datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Error getting device summary: {e}")
            return {}
    
    def mark_device_offline(self, device_id: str) -> bool:
        """Mark device as offline"""
        try:
            result = self.collection.update_one(
                {"device_id": device_id},
                {
                    "$set": {
                        "status.online": False,
                        "status.last_seen": datetime.utcnow(),
                        "metadata.updated_at": datetime.utcnow()
                    }
                }
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error marking device offline: {e}")
            return False
    
    def clear_emergency_alert(self, device_id: str, alert_type: str) -> bool:
        """Clear emergency alert for device"""
        try:
            update_data = {}
            if alert_type == "sos":
                update_data["alerts.sos_triggered"] = False
            elif alert_type == "fall":
                update_data["alerts.fall_detected"] = False
            
            update_data["alerts.last_alert_time"] = datetime.utcnow()
            
            result = self.collection.update_one(
                {"device_id": device_id},
                {"$set": update_data}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error clearing emergency alert: {e}")
            return False
    
    def close(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close() 