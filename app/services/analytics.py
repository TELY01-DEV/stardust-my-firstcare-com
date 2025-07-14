from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
import numpy as np
from bson import ObjectId
from app.services.mongo import mongodb_service
from app.services.cache_service import cache_service, cache_result
from config import logger, settings
import asyncio
from enum import Enum
from app.utils.structured_logging import get_logger

logger = get_logger(__name__)

class AnalyticsTimeframe(Enum):
    """Time periods for analytics"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    CUSTOM = "custom"

class AnalyticsMetric(Enum):
    """Available analytics metrics"""
    # Patient metrics
    PATIENT_COUNT = "patient_count"
    PATIENT_ADMISSIONS = "patient_admissions"
    PATIENT_READMISSIONS = "patient_readmissions"
    PATIENT_AVG_STAY = "patient_avg_stay"
    
    # Vital signs metrics
    VITALS_BLOOD_PRESSURE = "vitals_blood_pressure"
    VITALS_HEART_RATE = "vitals_heart_rate"
    VITALS_TEMPERATURE = "vitals_temperature"
    VITALS_SPO2 = "vitals_spo2"
    VITALS_GLUCOSE = "vitals_glucose"
    
    # Device metrics
    DEVICE_UTILIZATION = "device_utilization"
    DEVICE_READINGS_COUNT = "device_readings_count"
    DEVICE_COMPLIANCE = "device_compliance"
    DEVICE_ALERTS = "device_alerts"
    
    # Health outcomes
    HEALTH_RISK_SCORE = "health_risk_score"
    MEDICATION_ADHERENCE = "medication_adherence"
    TREATMENT_EFFECTIVENESS = "treatment_effectiveness"

class HealthcareAnalytics:
    """
    Advanced analytics service for healthcare data insights
    """
    
    def __init__(self):
        self.db = mongodb_service  # Add db attribute for compatibility
        self.collections = {
            "patients": "patients",
            "medical_history": "medical_history",
            "observations": "fhir_observations",
            "devices": ["ava4_sub_devices", "kati_watches", "qube_vital_devices"],
            "hospitals": "hospitals",
            "device_data": "device_data"  # Add device_data collection
        }
        
        # Cache configuration
        self.cache_ttl = {
            AnalyticsTimeframe.DAILY: 3600,      # 1 hour
            AnalyticsTimeframe.WEEKLY: 7200,     # 2 hours
            AnalyticsTimeframe.MONTHLY: 14400,   # 4 hours
            AnalyticsTimeframe.QUARTERLY: 28800, # 8 hours
            AnalyticsTimeframe.YEARLY: 86400     # 24 hours
        }
        
        # Statistical thresholds
        self.thresholds = {
            "blood_pressure": {
                "normal": {"systolic": (90, 120), "diastolic": (60, 80)},
                "elevated": {"systolic": (120, 130), "diastolic": (80, 80)},
                "high": {"systolic": (130, 180), "diastolic": (80, 120)},
                "critical": {"systolic": (180, float('inf')), "diastolic": (120, float('inf'))}
            },
            "heart_rate": {
                "low": (0, 60),
                "normal": (60, 100),
                "high": (100, 150),
                "critical": (150, float('inf'))
            },
            "temperature": {
                "low": (0, 36.0),
                "normal": (36.0, 37.5),
                "fever": (37.5, 39.0),
                "high_fever": (39.0, float('inf'))
            },
            "spo2": {
                "critical": (0, 90),
                "low": (90, 95),
                "normal": (95, 100)
            },
            "glucose": {
                "low": (0, 70),
                "normal": (70, 140),
                "high": (140, 200),
                "critical": (200, float('inf'))
            }
        }
    
    async def get_patient_statistics(
        self,
        hospital_id: Optional[str] = None,
        timeframe: AnalyticsTimeframe = AnalyticsTimeframe.MONTHLY,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get comprehensive patient statistics"""
        try:
            # Set date range
            if not end_date:
                end_date = datetime.utcnow()
            if not start_date:
                start_date = self._get_start_date(end_date, timeframe)
            
            # Build base filter
            base_filter = {}
            if hospital_id:
                base_filter["hospital_id"] = ObjectId(hospital_id)
            
            # Get patient counts
            patients_collection = mongodb_service.get_collection(self.collections["patients"])
            
            # Total patients
            total_patients = await patients_collection.count_documents(base_filter)
            
            # New patients in period
            period_filter = {**base_filter, "created_at": {"$gte": start_date, "$lte": end_date}}
            new_patients = await patients_collection.count_documents(period_filter)
            
            # Active patients (had readings in period)
            active_filter = {**base_filter, "last_activity": {"$gte": start_date}}
            active_patients = await patients_collection.count_documents(active_filter)
            
            # Age distribution
            age_pipeline = [
                {"$match": base_filter},
                {
                    "$project": {
                        "age_group": {
                            "$switch": {
                                "branches": [
                                    {"case": {"$lt": ["$age", 18]}, "then": "0-17"},
                                    {"case": {"$lt": ["$age", 30]}, "then": "18-29"},
                                    {"case": {"$lt": ["$age", 45]}, "then": "30-44"},
                                    {"case": {"$lt": ["$age", 60]}, "then": "45-59"},
                                    {"case": {"$lt": ["$age", 75]}, "then": "60-74"},
                                    {"case": {"$gte": ["$age", 75]}, "then": "75+"}
                                ],
                                "default": "Unknown"
                            }
                        }
                    }
                },
                {"$group": {"_id": "$age_group", "count": {"$sum": 1}}},
                {"$sort": {"_id": 1}}
            ]
            
            age_distribution = await patients_collection.aggregate(age_pipeline).to_list(None)
            
            # Gender distribution
            gender_pipeline = [
                {"$match": base_filter},
                {"$group": {"_id": "$gender", "count": {"$sum": 1}}},
                {"$sort": {"_id": 1}}
            ]
            
            gender_distribution = await patients_collection.aggregate(gender_pipeline).to_list(None)
            
            # Risk level distribution
            risk_pipeline = [
                {"$match": base_filter},
                {"$group": {"_id": "$risk_level", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}}
            ]
            
            risk_distribution = await patients_collection.aggregate(risk_pipeline).to_list(None)
            
            # Add total_count for compatibility
            result = {
                "total_count": total_patients,  # Add this for compatibility
                "summary": {
                    "total_patients": total_patients,
                    "new_patients": new_patients,
                    "active_patients": active_patients,
                    "inactive_patients": total_patients - active_patients
                },
                "demographics": {
                    "age_distribution": {item["_id"]: item["count"] for item in age_distribution},
                    "gender_distribution": {item["_id"]: item["count"] for item in gender_distribution}
                },
                "risk_analysis": {
                    "distribution": {item["_id"]: item["count"] for item in risk_distribution if item["_id"]},
                    "high_risk_count": sum(item["count"] for item in risk_distribution if item["_id"] == "high")
                },
                "timeframe": {
                    "period": timeframe.value if hasattr(timeframe, 'value') else timeframe,
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat()
                }
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting patient statistics: {e}")
            raise
    
    def _get_start_date(self, end_date: datetime, timeframe: AnalyticsTimeframe) -> datetime:
        """Calculate start date based on timeframe"""
        if timeframe == AnalyticsTimeframe.DAILY:
            return end_date - timedelta(days=1)
        elif timeframe == AnalyticsTimeframe.WEEKLY:
            return end_date - timedelta(weeks=1)
        elif timeframe == AnalyticsTimeframe.MONTHLY:
            return end_date - timedelta(days=30)
        elif timeframe == AnalyticsTimeframe.QUARTERLY:
            return end_date - timedelta(days=90)
        elif timeframe == AnalyticsTimeframe.YEARLY:
            return end_date - timedelta(days=365)
        else:
            return end_date - timedelta(days=30)  # Default to monthly


    async def get_vital_signs_analytics(
        self,
        patient_id: Optional[str] = None,
        hospital_id: Optional[str] = None,
        vital_type: Optional[str] = None,  # Change from str = "all" to Optional[str]
        period: Optional[str] = None,  # Add period parameter
        timeframe: Optional[AnalyticsTimeframe] = None,  # Make optional
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Analyze vital signs data with trends and anomalies"""
        try:
            # Handle period parameter for compatibility
            if period and not timeframe:
                period_map = {
                    "daily": AnalyticsTimeframe.DAILY,
                    "weekly": AnalyticsTimeframe.WEEKLY,
                    "monthly": AnalyticsTimeframe.MONTHLY,
                    "quarterly": AnalyticsTimeframe.QUARTERLY,
                    "yearly": AnalyticsTimeframe.YEARLY
                }
                timeframe = period_map.get(period, AnalyticsTimeframe.WEEKLY)
            elif not timeframe:
                timeframe = AnalyticsTimeframe.WEEKLY
            
            # Default vital_type to "all" if not specified
            if not vital_type:
                vital_type = "all"
            
            # Set date range
            if not end_date:
                end_date = datetime.utcnow()
            if not start_date:
                start_date = self._get_start_date(end_date, timeframe)
            
            # Build filter
            filter_query = {
                "resourceType": "Observation",
                "effectiveDateTime": {
                    "$gte": start_date.isoformat() + "Z",
                    "$lte": end_date.isoformat() + "Z"
                }
            }
            
            if patient_id:
                filter_query["subject.reference"] = f"Patient/{patient_id}"
            
            # Get observations
            observations_collection = mongodb_service.get_collection(self.collections["observations"])
            
            # Aggregate by vital type
            vital_types = ["blood_pressure", "heart_rate", "temperature", "spo2", "glucose"]
            if vital_type != "all":
                vital_types = [vital_type]
            
            analytics = {}
            
            for vtype in vital_types:
                type_filter = {**filter_query, "code.coding.code": vtype.upper()}
                
                # Get all readings
                readings = await observations_collection.find(type_filter).to_list(None)
                
                if not readings:
                    analytics[vtype] = {"no_data": True}
                    continue
                
                # Extract values
                values = []
                timestamps = []
                
                for reading in readings:
                    if vtype == "blood_pressure":
                        if "component" in reading:
                            systolic = next((c["valueQuantity"]["value"] for c in reading["component"] 
                                           if c["code"]["coding"][0]["code"] == "SYSTOLIC"), None)
                            diastolic = next((c["valueQuantity"]["value"] for c in reading["component"] 
                                            if c["code"]["coding"][0]["code"] == "DIASTOLIC"), None)
                            if systolic and diastolic:
                                values.append({"systolic": systolic, "diastolic": diastolic})
                                timestamps.append(datetime.fromisoformat(reading["effectiveDateTime"].rstrip("Z")))
                    else:
                        if "valueQuantity" in reading:
                            values.append(reading["valueQuantity"]["value"])
                            timestamps.append(datetime.fromisoformat(reading["effectiveDateTime"].rstrip("Z")))
                
                if not values:
                    analytics[vtype] = {"no_data": True}
                    continue
                
                # Calculate statistics
                if vtype == "blood_pressure":
                    systolic_values = [v["systolic"] for v in values]
                    diastolic_values = [v["diastolic"] for v in values]
                    
                    stats = {
                        "count": len(values),
                        "latest": values[-1],
                        "systolic": {
                            "mean": np.mean(systolic_values),
                            "std": np.std(systolic_values),
                            "min": np.min(systolic_values),
                            "max": np.max(systolic_values),
                            "median": np.median(systolic_values)
                        },
                        "diastolic": {
                            "mean": np.mean(diastolic_values),
                            "std": np.std(diastolic_values),
                            "min": np.min(diastolic_values),
                            "max": np.max(diastolic_values),
                            "median": np.median(diastolic_values)
                        }
                    }
                    
                    # Categorize readings
                    categories = self._categorize_blood_pressure(values)
                    stats["categories"] = categories
                    
                    # Detect anomalies
                    anomalies = self._detect_bp_anomalies(values, timestamps)
                    stats["anomalies"] = anomalies
                    
                else:
                    stats = {
                        "count": len(values),
                        "latest": values[-1],
                        "mean": np.mean(values),
                        "std": np.std(values),
                        "min": np.min(values),
                        "max": np.max(values),
                        "median": np.median(values)
                    }
                    
                    # Categorize readings
                    categories = self._categorize_vital_signs(values, vtype)
                    stats["categories"] = categories
                    
                    # Detect anomalies
                    anomalies = self._detect_anomalies(values, timestamps, vtype)
                    stats["anomalies"] = anomalies
                
                # Calculate trends
                if len(values) > 1:
                    trend = self._calculate_trend(values, timestamps)
                    stats["trend"] = trend
                
                analytics[vtype] = stats
            
            return {
                "vital_signs": analytics,
                "timeframe": {
                    "period": timeframe.value,
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat()
                },
                "summary": {
                    "total_readings": sum(a.get("count", 0) for a in analytics.values() if "count" in a),
                    "vital_types_analyzed": len([k for k, v in analytics.items() if not v.get("no_data")])
                }
            }
            
        except Exception as e:
            logger.error(f"Error analyzing vital signs: {e}")
            raise
    
    def _categorize_blood_pressure(self, readings: List[Dict]) -> Dict[str, int]:
        """Categorize blood pressure readings"""
        categories = defaultdict(int)
        
        for reading in readings:
            systolic = reading["systolic"]
            diastolic = reading["diastolic"]
            
            if systolic >= 180 or diastolic >= 120:
                categories["critical"] += 1
            elif systolic >= 130 or diastolic >= 80:
                categories["high"] += 1
            elif systolic >= 120:
                categories["elevated"] += 1
            else:
                categories["normal"] += 1
        
        return dict(categories)
    
    def _categorize_vital_signs(self, values: List[float], vital_type: str) -> Dict[str, int]:
        """Categorize vital sign readings"""
        categories = defaultdict(int)
        
        if vital_type not in self.thresholds:
            return {}
        
        thresholds = self.thresholds[vital_type]
        
        for value in values:
            categorized = False
            for category, (low, high) in thresholds.items():
                if low <= value < high:
                    categories[category] += 1
                    categorized = True
                    break
            
            if not categorized:
                categories["unknown"] += 1
        
        return dict(categories)
    
    def _detect_bp_anomalies(self, readings: List[Dict], timestamps: List[datetime]) -> List[Dict]:
        """Detect anomalies in blood pressure readings"""
        anomalies = []
        
        for i, reading in enumerate(readings):
            systolic = reading["systolic"]
            diastolic = reading["diastolic"]
            
            # Critical values
            if systolic >= 180 or diastolic >= 120:
                anomalies.append({
                    "type": "critical_high",
                    "timestamp": timestamps[i].isoformat(),
                    "value": reading,
                    "severity": "critical"
                })
            elif systolic < 90 or diastolic < 60:
                anomalies.append({
                    "type": "critical_low",
                    "timestamp": timestamps[i].isoformat(),
                    "value": reading,
                    "severity": "critical"
                })
            
            # Rapid changes
            if i > 0:
                prev_systolic = readings[i-1]["systolic"]
                prev_diastolic = readings[i-1]["diastolic"]
                
                systolic_change = abs(systolic - prev_systolic)
                diastolic_change = abs(diastolic - prev_diastolic)
                
                if systolic_change > 30 or diastolic_change > 20:
                    anomalies.append({
                        "type": "rapid_change",
                        "timestamp": timestamps[i].isoformat(),
                        "value": reading,
                        "change": {"systolic": systolic_change, "diastolic": diastolic_change},
                        "severity": "warning"
                    })
        
        return anomalies
    
    def _detect_anomalies(self, values: List[float], timestamps: List[datetime], vital_type: str) -> List[Dict]:
        """Detect anomalies in vital sign readings"""
        anomalies = []
        
        if vital_type not in self.thresholds:
            return anomalies
        
        thresholds = self.thresholds[vital_type]
        
        # Statistical anomalies (outliers)
        if len(values) > 3:
            mean = np.mean(values)
            std = np.std(values)
            
            for i, value in enumerate(values):
                # Z-score method
                z_score = abs((value - mean) / std) if std > 0 else 0
                
                if z_score > 3:  # 3 standard deviations
                    anomalies.append({
                        "type": "statistical_outlier",
                        "timestamp": timestamps[i].isoformat(),
                        "value": value,
                        "z_score": z_score,
                        "severity": "warning"
                    })
        
        # Critical values
        critical_ranges = {
            "heart_rate": (50, 150),
            "temperature": (35.0, 40.0),
            "spo2": (90, 100),
            "glucose": (50, 400)
        }
        
        if vital_type in critical_ranges:
            low, high = critical_ranges[vital_type]
            
            for i, value in enumerate(values):
                if value < low or value > high:
                    anomalies.append({
                        "type": "critical_value",
                        "timestamp": timestamps[i].isoformat(),
                        "value": value,
                        "severity": "critical"
                    })
        
        return anomalies
    
    def _calculate_trend(self, values: List, timestamps: List[datetime]) -> Dict[str, Any]:
        """Calculate trend in vital signs"""
        if len(values) < 2:
            return {"direction": "stable", "change": 0}
        
        # Convert to numeric values for BP
        if isinstance(values[0], dict):
            # Blood pressure - use mean arterial pressure
            numeric_values = [(v["systolic"] + 2 * v["diastolic"]) / 3 for v in values]
        else:
            numeric_values = values
        
        # Simple linear regression
        x = np.arange(len(numeric_values))
        y = np.array(numeric_values)
        
        # Calculate slope
        slope = np.polyfit(x, y, 1)[0]
        
        # Percentage change
        change_percent = ((numeric_values[-1] - numeric_values[0]) / numeric_values[0]) * 100
        
        # Determine trend direction
        if abs(slope) < 0.1:
            direction = "stable"
        elif slope > 0:
            direction = "increasing"
        else:
            direction = "decreasing"
        
        return {
            "direction": direction,
            "slope": float(slope),
            "change_percent": float(change_percent),
            "confidence": self._calculate_trend_confidence(numeric_values)
        }
    
    def _calculate_trend_confidence(self, values: List[float]) -> float:
        """Calculate confidence in trend based on consistency"""
        if len(values) < 3:
            return 0.0
        
        # Calculate R-squared for linear fit
        x = np.arange(len(values))
        y = np.array(values)
        
        # Fit line
        coeffs = np.polyfit(x, y, 1)
        p = np.poly1d(coeffs)
        
        # Calculate R-squared
        yhat = p(x)
        ybar = np.mean(y)
        ssreg = np.sum((yhat - ybar) ** 2)
        sstot = np.sum((y - ybar) ** 2)
        
        r_squared = ssreg / sstot if sstot > 0 else 0
        
        return float(r_squared)


    async def get_device_analytics(
        self,
        hospital_id: Optional[str] = None,
        device_type: Optional[str] = None,
        timeframe: AnalyticsTimeframe = AnalyticsTimeframe.MONTHLY,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Analyze device utilization and performance"""
        try:
            # Set date range
            if not end_date:
                end_date = datetime.utcnow()
            if not start_date:
                start_date = self._get_start_date(end_date, timeframe)
            
            analytics = {
                "utilization": {},
                "performance": {},
                "alerts": {}
            }
            
            # Analyze each device type
            device_types = ["ava4", "kati", "qube-vital"] if not device_type else [device_type]
            
            for dtype in device_types:
                # Get device collection
                collection_map = {
                    "ava4": "ava4_sub_devices",
                    "kati": "kati_watches",
                    "qube-vital": "qube_vital_devices"
                }
                
                if dtype not in collection_map:
                    continue
                
                device_collection = mongodb_service.get_collection(collection_map[dtype])
                
                # Build filter
                filter_query = {}
                if hospital_id:
                    filter_query["hospital_id"] = ObjectId(hospital_id)
                
                # Get device count
                total_devices = await device_collection.count_documents(filter_query)
                
                # Get active devices (had readings in period)
                observations_collection = mongodb_service.get_collection("fhir_observations")
                
                active_pipeline = [
                    {
                        "$match": {
                            "resourceType": "Observation",
                            "effectiveDateTime": {
                                "$gte": start_date.isoformat() + "Z",
                                "$lte": end_date.isoformat() + "Z"
                            },
                            "device.type": dtype.upper()
                        }
                    },
                    {"$group": {"_id": "$device.reference"}},
                    {"$count": "active_devices"}
                ]
                
                active_result = await observations_collection.aggregate(active_pipeline).to_list(1)
                active_devices = active_result[0]["active_devices"] if active_result else 0
                
                # Get reading counts
                reading_pipeline = [
                    {
                        "$match": {
                            "resourceType": "Observation",
                            "effectiveDateTime": {
                                "$gte": start_date.isoformat() + "Z",
                                "$lte": end_date.isoformat() + "Z"
                            },
                            "device.type": dtype.upper()
                        }
                    },
                    {
                        "$group": {
                            "_id": "$code.coding.code",
                            "count": {"$sum": 1}
                        }
                    }
                ]
                
                reading_counts = await observations_collection.aggregate(reading_pipeline).to_list(None)
                
                analytics["utilization"][dtype] = {
                    "total_devices": total_devices,
                    "active_devices": active_devices,
                    "inactive_devices": total_devices - active_devices,
                    "utilization_rate": (active_devices / total_devices * 100) if total_devices > 0 else 0,
                    "readings_by_type": {item["_id"]: item["count"] for item in reading_counts},
                    "total_readings": sum(item["count"] for item in reading_counts)
                }
            
            # Calculate overall metrics
            analytics["summary"] = {
                "total_devices": sum(u["total_devices"] for u in analytics["utilization"].values()),
                "active_devices": sum(u["active_devices"] for u in analytics["utilization"].values()),
                "total_readings": sum(u["total_readings"] for u in analytics["utilization"].values()),
                "average_utilization": np.mean([u["utilization_rate"] for u in analytics["utilization"].values()])
            }
            
            analytics["timeframe"] = {
                "period": timeframe.value,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            }
            
            return analytics
            
        except Exception as e:
            logger.error(f"Error analyzing devices: {e}")
            raise
    
    async def get_health_risk_predictions(
        self,
        patient_id: str,
        prediction_window: int = 30  # days
    ) -> Dict[str, Any]:
        """Predict health risks based on historical data"""
        try:
            # Get patient data
            patients_collection = mongodb_service.get_collection("patients")
            patient = await patients_collection.find_one({"_id": ObjectId(patient_id)})
            
            if not patient:
                raise ValueError(f"Patient {patient_id} not found")
            
            # Get recent vital signs
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=90)  # 3 months of data
            
            vitals_data = await self.get_vital_signs_analytics(
                patient_id=patient_id,
                vital_type="all",
                start_date=start_date,
                end_date=end_date
            )
            
            risk_factors = {}
            risk_score = 0
            
            # Analyze each vital type
            for vital_type, data in vitals_data["vital_signs"].items():
                if data.get("no_data"):
                    continue
                
                vital_risk = self._calculate_vital_risk(vital_type, data)
                risk_factors[vital_type] = vital_risk
                risk_score += vital_risk["score"]
            
            # Patient demographics risk
            demo_risk = self._calculate_demographic_risk(patient)
            risk_factors["demographics"] = demo_risk
            risk_score += demo_risk["score"]
            
            # Normalize risk score (0-100)
            max_possible_score = len(risk_factors) * 25  # Max 25 per factor
            normalized_score = (risk_score / max_possible_score) * 100 if max_possible_score > 0 else 0
            
            # Determine risk level
            if normalized_score < 20:
                risk_level = "low"
            elif normalized_score < 40:
                risk_level = "moderate"
            elif normalized_score < 60:
                risk_level = "high"
            else:
                risk_level = "critical"
            
            # Generate recommendations
            recommendations = self._generate_health_recommendations(risk_factors, risk_level)
            
            return {
                "patient_id": patient_id,
                "risk_assessment": {
                    "overall_score": round(normalized_score, 2),
                    "risk_level": risk_level,
                    "risk_factors": risk_factors
                },
                "predictions": {
                    "window_days": prediction_window,
                    "health_events": self._predict_health_events(risk_factors, prediction_window)
                },
                "recommendations": recommendations,
                "assessment_date": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error predicting health risks: {e}")
            raise
    
    def _calculate_vital_risk(self, vital_type: str, vital_data: Dict) -> Dict[str, Any]:
        """Calculate risk score for a vital sign"""
        risk = {
            "score": 0,
            "factors": []
        }
        
        # Check for anomalies
        if vital_data.get("anomalies"):
            critical_anomalies = [a for a in vital_data["anomalies"] if a["severity"] == "critical"]
            if critical_anomalies:
                risk["score"] += 15
                risk["factors"].append(f"{len(critical_anomalies)} critical anomalies detected")
        
        # Check categories
        categories = vital_data.get("categories", {})
        if vital_type == "blood_pressure":
            if categories.get("critical", 0) > 0:
                risk["score"] += 20
                risk["factors"].append("Critical blood pressure readings")
            elif categories.get("high", 0) > categories.get("normal", 0):
                risk["score"] += 10
                risk["factors"].append("Predominantly high blood pressure")
        
        # Check trends
        trend = vital_data.get("trend", {})
        if trend.get("direction") == "increasing" and vital_type in ["blood_pressure", "heart_rate"]:
            risk["score"] += 5
            risk["factors"].append(f"Increasing {vital_type} trend")
        elif trend.get("direction") == "decreasing" and vital_type in ["spo2"]:
            risk["score"] += 5
            risk["factors"].append(f"Decreasing {vital_type} trend")
        
        return risk
    
    def _calculate_demographic_risk(self, patient: Dict) -> Dict[str, Any]:
        """Calculate risk based on demographics"""
        risk = {
            "score": 0,
            "factors": []
        }
        
        # Age risk
        age = patient.get("age", 0)
        if age > 70:
            risk["score"] += 10
            risk["factors"].append("Age > 70")
        elif age > 60:
            risk["score"] += 5
            risk["factors"].append("Age > 60")
        
        # Existing conditions
        conditions = patient.get("medical_conditions", [])
        high_risk_conditions = ["diabetes", "hypertension", "heart_disease", "copd"]
        
        for condition in high_risk_conditions:
            if any(condition in c.lower() for c in conditions):
                risk["score"] += 8
                risk["factors"].append(f"Pre-existing {condition}")
        
        return risk
    
    def _predict_health_events(self, risk_factors: Dict, window_days: int) -> List[Dict]:
        """Predict potential health events"""
        events = []
        
        # High blood pressure risk
        bp_risk = risk_factors.get("blood_pressure", {})
        if bp_risk.get("score", 0) > 15:
            events.append({
                "event": "Hypertensive crisis",
                "probability": min(bp_risk["score"] * 3, 90),
                "timeframe": "Within 30 days",
                "severity": "high"
            })
        
        # Overall high risk
        total_score = sum(rf.get("score", 0) for rf in risk_factors.values())
        if total_score > 50:
            events.append({
                "event": "Hospital admission",
                "probability": min(total_score, 80),
                "timeframe": f"Within {window_days} days",
                "severity": "moderate"
            })
        
        return events
    
    def _generate_health_recommendations(self, risk_factors: Dict, risk_level: str) -> List[Dict]:
        """Generate personalized health recommendations"""
        recommendations = []
        
        # General recommendations based on risk level
        if risk_level in ["high", "critical"]:
            recommendations.append({
                "priority": "urgent",
                "action": "Schedule immediate medical consultation",
                "reason": f"Overall risk level is {risk_level}"
            })
        
        # Specific recommendations for each risk factor
        for factor_type, factor_data in risk_factors.items():
            if factor_data.get("score", 0) > 10:
                if factor_type == "blood_pressure":
                    recommendations.append({
                        "priority": "high",
                        "action": "Monitor blood pressure daily",
                        "reason": "High blood pressure risk detected"
                    })
                elif factor_type == "heart_rate":
                    recommendations.append({
                        "priority": "medium",
                        "action": "Implement stress reduction techniques",
                        "reason": "Abnormal heart rate patterns"
                    })
        
        return recommendations

    async def predict_health_events(self, patient_id: str, days_ahead: int = 30) -> List[Dict]:
        """Predict potential health events"""
        # This would use ML models in production
        # For now, returning example predictions based on risk factors
        risk_data = await self.predict_health_risks(patient_id)
        events = []
        
        if risk_data["risk_score"] > 0.7:
            events.append({
                "event_type": "high_risk_alert",
                "probability": risk_data["risk_score"],
                "expected_date": (datetime.utcnow() + timedelta(days=7)).isoformat(),
                "description": "Patient at high risk - immediate attention recommended"
            })
        
        return events

    async def _analyze_aggregate_trends(
        self,
        vital_type: str,
        hospital_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict:
        """Analyze aggregate trends for vitals across patients"""
        try:
            # Build query
            query = {}
            if hospital_id:
                # Get all patients from this hospital
                patients_collection = mongodb_service.get_collection("patients")
                patients = await patients_collection.find(
                    {"hospital_id": ObjectId(hospital_id)},
                    {"_id": 1}
                ).to_list(None)
                patient_ids = [p["_id"] for p in patients]
                query["patient_id"] = {"$in": patient_ids}
            
            if start_date:
                query["timestamp"] = {"$gte": start_date}
            if end_date:
                query.setdefault("timestamp", {})["$lte"] = end_date
            
            # Map vital types to device types
            device_type_map = {
                "blood_pressure": "blood_pressure_monitor",
                "heart_rate": "heart_rate_monitor",
                "temperature": "thermometer",
                "spo2": "pulse_oximeter"
            }
            
            if vital_type in device_type_map:
                query["device_type"] = device_type_map[vital_type]
            
            # Get vital data
            device_data_collection = mongodb_service.get_collection("device_data")
            vital_data = await device_data_collection.find(query).to_list(None)
            
            if not vital_data:
                return {
                    "trend": "insufficient_data",
                    "data_points": 0,
                    "message": "Not enough data for trend analysis"
                }
            
            # Extract values based on vital type
            values = []
            timestamps = []
            
            for data in vital_data:
                timestamp = data.get("timestamp", data.get("created_at"))
                if vital_type == "blood_pressure" and "systolic" in data.get("data", {}):
                    values.append(data["data"]["systolic"])
                    timestamps.append(timestamp)
                elif vital_type == "heart_rate" and "heart_rate" in data.get("data", {}):
                    values.append(data["data"]["heart_rate"])
                    timestamps.append(timestamp)
                elif vital_type == "temperature" and "temperature" in data.get("data", {}):
                    values.append(data["data"]["temperature"])
                    timestamps.append(timestamp)
                elif vital_type == "spo2" and "spo2" in data.get("data", {}):
                    values.append(data["data"]["spo2"])
                    timestamps.append(timestamp)
            
            if len(values) < 2:
                return {
                    "trend": "insufficient_data",
                    "data_points": len(values),
                    "message": "Not enough data points for trend analysis"
                }
            
            # Calculate trend
            x = np.arange(len(values))
            slope, intercept = np.polyfit(x, values, 1)
            
            # Determine trend direction
            if abs(slope) < 0.01:
                trend = "stable"
            elif slope > 0:
                trend = "increasing"
            else:
                trend = "decreasing"
            
            return {
                "trend": trend,
                "slope": float(slope),
                "average": float(np.mean(values)),
                "std_dev": float(np.std(values)),
                "data_points": len(values),
                "period": {
                    "start": min(timestamps).isoformat() if timestamps else None,
                    "end": max(timestamps).isoformat() if timestamps else None
                }
            }
            
        except Exception as e:
            logger.error(f"Error analyzing aggregate trends: {str(e)}")
            return {
                "trend": "error",
                "message": str(e)
            }

    async def _generate_hospital_report(
        self,
        hospital_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict:
        """Generate comprehensive hospital performance report"""
        try:
            report = {
                "hospital_id": hospital_id,
                "period": {
                    "start": start_date.isoformat() if start_date else "all_time",
                    "end": end_date.isoformat() if end_date else "current"
                },
                "metrics": {}
            }
            
            # Patient metrics
            patient_stats = await self.get_patient_statistics(
                hospital_id=hospital_id,
                start_date=start_date,
                end_date=end_date
            )
            report["metrics"]["patients"] = patient_stats
            
            # Device utilization
            device_stats = await self.get_device_utilization_analytics(
                hospital_id=hospital_id,
                period="monthly"
            )
            report["metrics"]["devices"] = device_stats
            
            # Calculate additional metrics
            if hospital_id:
                # Get hospital info
                hospitals_collection = mongodb_service.get_collection("hospitals")
                hospital = await hospitals_collection.find_one({"_id": ObjectId(hospital_id)})
                if hospital:
                    report["hospital_name"] = hospital.get("name", "Unknown")
                    
                # Calculate bed occupancy if available
                total_beds = hospital.get("total_beds", 0) if hospital else 0
                if total_beds > 0 and patient_stats.get("total_count", 0) > 0:
                    report["metrics"]["bed_occupancy"] = {
                        "rate": patient_stats["total_count"] / total_beds,
                        "total_beds": total_beds,
                        "occupied_beds": patient_stats["total_count"]
                    }
            
            # Performance indicators
            report["performance_indicators"] = {
                "patient_satisfaction": "Not implemented",  # Placeholder
                "average_stay_duration": "Not implemented",  # Placeholder
                "readmission_rate": "Not implemented"  # Placeholder
            }
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating hospital report: {str(e)}")
            return {"error": str(e)}

    async def _generate_health_risk_report(
        self,
        hospital_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict:
        """Generate aggregate health risk analysis report"""
        try:
            # Build query for patients
            query = {}
            if hospital_id:
                query["hospital_id"] = ObjectId(hospital_id)
            if start_date:
                query["created_at"] = {"$gte": start_date}
            if end_date:
                query.setdefault("created_at", {})["$lte"] = end_date
            
            # Get patients
            patients_collection = mongodb_service.get_collection("patients")
            patients = await patients_collection.find(query).to_list(None)
            
            # Analyze risks for all patients
            risk_analysis = {
                "total_patients": len(patients),
                "risk_distribution": {
                    "low": 0,
                    "medium": 0,
                    "high": 0,
                    "critical": 0
                },
                "common_risk_factors": {},
                "average_risk_score": 0.0
            }
            
            total_risk_score = 0.0
            risk_factors_count = {}
            
            for patient in patients:
                # Get risk prediction for each patient
                risk_data = await self.predict_health_risks(str(patient["_id"]))
                risk_score = risk_data.get("risk_score", 0)
                total_risk_score += risk_score
                
                # Categorize risk level
                if risk_score < 0.3:
                    risk_analysis["risk_distribution"]["low"] += 1
                elif risk_score < 0.5:
                    risk_analysis["risk_distribution"]["medium"] += 1
                elif risk_score < 0.7:
                    risk_analysis["risk_distribution"]["high"] += 1
                else:
                    risk_analysis["risk_distribution"]["critical"] += 1
                
                # Count risk factors
                for factor in risk_data.get("risk_factors", []):
                    risk_factors_count[factor] = risk_factors_count.get(factor, 0) + 1
            
            # Calculate averages and top risk factors
            if patients:
                risk_analysis["average_risk_score"] = total_risk_score / len(patients)
                
                # Get top 5 risk factors
                sorted_factors = sorted(
                    risk_factors_count.items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:5]
                
                risk_analysis["common_risk_factors"] = {
                    factor: {
                        "count": count,
                        "percentage": (count / len(patients)) * 100
                    }
                    for factor, count in sorted_factors
                }
            
            return risk_analysis
            
        except Exception as e:
            logger.error(f"Error generating health risk report: {str(e)}")
            return {"error": str(e)}

    async def detect_vital_anomalies(
        self,
        hospital_id: Optional[str] = None,
        patient_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        threshold: float = 2.0
    ) -> List[Dict]:
        """Detect anomalies in vital signs using statistical methods"""
        try:
            # Build query
            query = {}
            if patient_id:
                query["patient_id"] = ObjectId(patient_id)
            elif hospital_id:
                # Get patients from hospital
                patients_collection = mongodb_service.get_collection("patients")
                patients = await patients_collection.find(
                    {"hospital_id": ObjectId(hospital_id)},
                    {"_id": 1}
                ).to_list(None)
                patient_ids = [p["_id"] for p in patients]
                query["patient_id"] = {"$in": patient_ids}
            
            if start_date:
                query["timestamp"] = {"$gte": start_date}
            if end_date:
                query.setdefault("timestamp", {})["$lte"] = end_date
            
            # Get device data
            device_data_collection = mongodb_service.get_collection("device_data")
            device_data = await device_data_collection.find(query).to_list(None)
            
            anomalies = []
            
            # Group data by device type for analysis
            device_groups = {}
            for data in device_data:
                device_type = data.get("device_type", "unknown")
                if device_type not in device_groups:
                    device_groups[device_type] = []
                device_groups[device_type].append(data)
            
            # Analyze each device type
            for device_type, readings in device_groups.items():
                if len(readings) < 10:  # Need minimum data for statistics
                    continue
                
                # Extract values based on device type
                values = []
                reading_map = {}
                
                for reading in readings:
                    if device_type == "blood_pressure_monitor":
                        if "systolic" in reading.get("data", {}):
                            value = reading["data"]["systolic"]
                            values.append(value)
                            reading_map[value] = reading
                    elif device_type == "heart_rate_monitor":
                        if "heart_rate" in reading.get("data", {}):
                            value = reading["data"]["heart_rate"]
                            values.append(value)
                            reading_map[value] = reading
                    elif device_type == "thermometer":
                        if "temperature" in reading.get("data", {}):
                            value = reading["data"]["temperature"]
                            values.append(value)
                            reading_map[value] = reading
                    elif device_type == "pulse_oximeter":
                        if "spo2" in reading.get("data", {}):
                            value = reading["data"]["spo2"]
                            values.append(value)
                            reading_map[value] = reading
                
                if len(values) < 10:
                    continue
                
                # Calculate statistics
                mean = np.mean(values)
                std = np.std(values)
                
                if std == 0:  # All values are the same
                    continue
                
                # Detect anomalies using Z-score
                for i, value in enumerate(values):
                    z_score = abs((value - mean) / std)
                    if z_score > threshold:
                        # Find the original reading
                        original_reading = reading_map.get(value)
                        if original_reading:
                            anomaly = {
                                "device_type": device_type,
                                "patient_id": str(original_reading.get("patient_id", "")),
                                "timestamp": original_reading.get("timestamp", original_reading.get("created_at")).isoformat(),
                                "value": value,
                                "z_score": float(z_score),
                                "mean": float(mean),
                                "std_dev": float(std),
                                "severity": "high" if z_score > 3 else "medium",
                                "data": original_reading.get("data", {})
                            }
                            
                            # Add context based on device type
                            if device_type == "blood_pressure_monitor":
                                anomaly["vital_type"] = "blood_pressure"
                                anomaly["context"] = "Abnormal blood pressure reading"
                            elif device_type == "heart_rate_monitor":
                                anomaly["vital_type"] = "heart_rate"
                                anomaly["context"] = "Abnormal heart rate"
                            elif device_type == "thermometer":
                                anomaly["vital_type"] = "temperature"
                                anomaly["context"] = "Abnormal temperature"
                            elif device_type == "pulse_oximeter":
                                anomaly["vital_type"] = "spo2"
                                anomaly["context"] = "Abnormal oxygen saturation"
                            
                            anomalies.append(anomaly)
            
            # Sort by severity and timestamp
            anomalies.sort(key=lambda x: (x["z_score"], x["timestamp"]), reverse=True)
            
            return anomalies
            
        except Exception as e:
            logger.error(f"Error detecting anomalies: {str(e)}")
            return []

    async def get_device_utilization_analytics(
        self,
        hospital_id: Optional[str] = None,
        device_type: Optional[str] = None,
        period: str = "monthly"
    ) -> Dict[str, Any]:
        """Get device utilization analytics - wrapper for get_device_analytics"""
        # Map period to timeframe
        period_map = {
            "daily": AnalyticsTimeframe.DAILY,
            "weekly": AnalyticsTimeframe.WEEKLY,
            "monthly": AnalyticsTimeframe.MONTHLY,
            "quarterly": AnalyticsTimeframe.QUARTERLY,
            "yearly": AnalyticsTimeframe.YEARLY
        }
        timeframe = period_map.get(period, AnalyticsTimeframe.MONTHLY)
        
        return await self.get_device_analytics(
            hospital_id=hospital_id,
            device_type=device_type,
            timeframe=timeframe
        )

    async def predict_health_risks(self, patient_id: str) -> Dict[str, Any]:
        """Predict health risks for a patient - wrapper for get_health_risk_predictions"""
        result = await self.get_health_risk_predictions(patient_id)
        # Ensure risk_score and risk_factors are present
        if "risk_score" not in result:
            result["risk_score"] = result.get("risk_level", {}).get("score", 0)
        if "risk_factors" not in result:
            result["risk_factors"] = [factor["name"] for factor in result.get("risk_factors", [])]
        return result
    
    async def get_health_recommendations(
        self,
        patient_id: str,
        risk_factors: List[str]
    ) -> List[Dict[str, Any]]:
        """Get health recommendations based on risk factors"""
        # Get patient data
        patients_collection = mongodb_service.get_collection(self.collections["patients"])
        patient = await patients_collection.find_one({"_id": ObjectId(patient_id)})
        
        if not patient:
            return []
        
        # Generate recommendations based on risk factors
        risk_level = "high" if len(risk_factors) > 3 else "medium" if len(risk_factors) > 1 else "low"
        risk_factors_dict = {factor: True for factor in risk_factors}
        
        return self._generate_health_recommendations(risk_factors_dict, risk_level)


# Global analytics instance
healthcare_analytics = HealthcareAnalytics()

# Create alias for compatibility
AnalyticsService = HealthcareAnalytics 