"""
FHIR Data Quality Monitor
Continuously monitors FHIR data quality and sends alerts for issues
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

from app.services.mongo import mongodb_service
from app.services.fhir_data_validator import fhir_validator, ValidationSeverity
from app.services.telegram_monitor import telegram_monitor

logger = logging.getLogger(__name__)

class AlertLevel(Enum):
    """Alert levels for data quality issues"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class DataQualityAlert:
    """Data quality alert structure"""
    level: AlertLevel
    resource_type: str
    message: str
    details: Dict[str, Any]
    timestamp: datetime
    alert_id: str = None
    
    def __post_init__(self):
        if self.alert_id is None:
            self.alert_id = f"{self.resource_type}_{self.timestamp.strftime('%Y%m%d_%H%M%S')}"

class FHIRDataMonitor:
    """Continuous FHIR data quality monitoring service"""
    
    def __init__(self):
        self.monitoring_active = False
        self.check_interval = 300  # 5 minutes
        self.alert_cooldown = 3600  # 1 hour
        self.last_alerts = {}
        self.quality_thresholds = {
            "error_rate": 0.05,  # 5% error rate threshold
            "warning_rate": 0.15,  # 15% warning rate threshold
            "missing_fields_rate": 0.10,  # 10% missing fields threshold
            "data_freshness_hours": 24  # Data should be updated within 24 hours
        }
    
    async def start_monitoring(self):
        """Start continuous monitoring"""
        if self.monitoring_active:
            logger.warning("Monitoring is already active")
            return
        
        self.monitoring_active = True
        logger.info("Starting FHIR data quality monitoring")
        
        while self.monitoring_active:
            try:
                await self.run_quality_check()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying
    
    async def stop_monitoring(self):
        """Stop continuous monitoring"""
        self.monitoring_active = False
        logger.info("Stopping FHIR data quality monitoring")
    
    async def run_quality_check(self):
        """Run a comprehensive quality check"""
        logger.info("Running FHIR data quality check")
        
        try:
            # Check data freshness
            freshness_alerts = await self.check_data_freshness()
            
            # Check data completeness
            completeness_alerts = await self.check_data_completeness()
            
            # Check data integrity
            integrity_alerts = await self.check_data_integrity()
            
            # Check data volume
            volume_alerts = await self.check_data_volume()
            
            # Combine all alerts
            all_alerts = freshness_alerts + completeness_alerts + integrity_alerts + volume_alerts
            
            # Send alerts
            await self.send_alerts(all_alerts)
            
            # Log summary
            if all_alerts:
                logger.warning(f"Quality check found {len(all_alerts)} issues")
            else:
                logger.info("Quality check passed - no issues found")
                
        except Exception as e:
            logger.error(f"Error in quality check: {e}")
    
    async def check_data_freshness(self) -> List[DataQualityAlert]:
        """Check if data is being updated regularly"""
        alerts = []
        
        try:
            await mongodb_service.connect()
            db = mongodb_service.get_database('MFC_FHIR_R5')
            
            # Check recent activity for each resource type
            resource_types = ["Patient", "Observation", "Device", "Organization"]
            cutoff_time = datetime.now() - timedelta(hours=self.quality_thresholds["data_freshness_hours"])
            
            for resource_type in resource_types:
                try:
                    collection = db.get_collection(resource_type)
                    
                    # Count recent documents
                    recent_count = await collection.count_documents({
                        "meta.lastUpdated": {"$gte": cutoff_time.isoformat()}
                    })
                    
                    # Count total documents
                    total_count = await collection.count_documents({})
                    
                    if total_count > 0 and recent_count == 0:
                        alerts.append(DataQualityAlert(
                            level=AlertLevel.WARNING,
                            resource_type=resource_type,
                            message=f"No {resource_type} data updated in the last {self.quality_thresholds['data_freshness_hours']} hours",
                            details={
                                "last_update_threshold_hours": self.quality_thresholds["data_freshness_hours"],
                                "total_documents": total_count,
                                "recent_documents": recent_count
                            },
                            timestamp=datetime.now()
                        ))
                    
                except Exception as e:
                    logger.error(f"Error checking freshness for {resource_type}: {e}")
                    
        except Exception as e:
            logger.error(f"Error in data freshness check: {e}")
        
        return alerts
    
    async def check_data_completeness(self) -> List[DataQualityAlert]:
        """Check for missing required fields"""
        alerts = []
        
        try:
            await mongodb_service.connect()
            db = mongodb_service.get_database('MFC_FHIR_R5')
            
            # Define required fields for each resource type
            required_fields = {
                "Patient": ["name", "gender", "birthDate"],
                "Observation": ["status", "code", "subject", "effectiveDateTime"],
                "Device": ["identifier", "type", "status"],
                "Organization": ["name", "type"]
            }
            
            for resource_type, fields in required_fields.items():
                try:
                    collection = db.get_collection(resource_type)
                    total_count = await collection.count_documents({})
                    
                    if total_count == 0:
                        continue
                    
                    # Check each required field
                    for field in fields:
                        missing_count = await collection.count_documents({field: {"$exists": False}})
                        missing_rate = missing_count / total_count if total_count > 0 else 0
                        
                        if missing_rate > self.quality_thresholds["missing_fields_rate"]:
                            alerts.append(DataQualityAlert(
                                level=AlertLevel.ERROR if missing_rate > 0.5 else AlertLevel.WARNING,
                                resource_type=resource_type,
                                message=f"High rate of missing {field} field in {resource_type}",
                                details={
                                    "field": field,
                                    "missing_count": missing_count,
                                    "total_count": total_count,
                                    "missing_rate": round(missing_rate * 100, 2),
                                    "threshold": round(self.quality_thresholds["missing_fields_rate"] * 100, 2)
                                },
                                timestamp=datetime.now()
                            ))
                    
                except Exception as e:
                    logger.error(f"Error checking completeness for {resource_type}: {e}")
                    
        except Exception as e:
            logger.error(f"Error in data completeness check: {e}")
        
        return alerts
    
    async def check_data_integrity(self) -> List[DataQualityAlert]:
        """Check data integrity using validation rules"""
        alerts = []
        
        try:
            # Run validation on a sample of data
            validation_results = await fhir_validator.validate_all_resources(limit=50)
            
            for resource_type, results in validation_results.items():
                if not results:
                    continue
                
                error_count = len([r for r in results if r.severity == ValidationSeverity.ERROR])
                warning_count = len([r for r in results if r.severity == ValidationSeverity.WARNING])
                critical_count = len([r for r in results if r.severity == ValidationSeverity.CRITICAL])
                total_count = len(results)
                
                error_rate = error_count / total_count if total_count > 0 else 0
                warning_rate = warning_count / total_count if total_count > 0 else 0
                
                if critical_count > 0:
                    alerts.append(DataQualityAlert(
                        level=AlertLevel.CRITICAL,
                        resource_type=resource_type,
                        message=f"Critical data integrity issues found in {resource_type}",
                        details={
                            "critical_count": critical_count,
                            "error_count": error_count,
                            "warning_count": warning_count,
                            "total_validated": total_count
                        },
                        timestamp=datetime.now()
                    ))
                elif error_rate > self.quality_thresholds["error_rate"]:
                    alerts.append(DataQualityAlert(
                        level=AlertLevel.ERROR,
                        resource_type=resource_type,
                        message=f"High error rate in {resource_type} data",
                        details={
                            "error_count": error_count,
                            "total_validated": total_count,
                            "error_rate": round(error_rate * 100, 2),
                            "threshold": round(self.quality_thresholds["error_rate"] * 100, 2)
                        },
                        timestamp=datetime.now()
                    ))
                elif warning_rate > self.quality_thresholds["warning_rate"]:
                    alerts.append(DataQualityAlert(
                        level=AlertLevel.WARNING,
                        resource_type=resource_type,
                        message=f"High warning rate in {resource_type} data",
                        details={
                            "warning_count": warning_count,
                            "total_validated": total_count,
                            "warning_rate": round(warning_rate * 100, 2),
                            "threshold": round(self.quality_thresholds["warning_rate"] * 100, 2)
                        },
                        timestamp=datetime.now()
                    ))
                    
        except Exception as e:
            logger.error(f"Error in data integrity check: {e}")
        
        return alerts
    
    async def check_data_volume(self) -> List[DataQualityAlert]:
        """Check for unusual data volume patterns"""
        alerts = []
        
        try:
            await mongodb_service.connect()
            db = mongodb_service.get_database('MFC_FHIR_R5')
            
            # Check for sudden drops in data volume
            resource_types = ["Patient", "Observation", "Device"]
            
            for resource_type in resource_types:
                try:
                    collection = db.get_collection(resource_type)
                    
                    # Count documents in last hour vs previous hour
                    now = datetime.now()
                    last_hour = now - timedelta(hours=1)
                    two_hours_ago = now - timedelta(hours=2)
                    
                    recent_count = await collection.count_documents({
                        "meta.lastUpdated": {"$gte": last_hour.isoformat()}
                    })
                    
                    previous_count = await collection.count_documents({
                        "meta.lastUpdated": {
                            "$gte": two_hours_ago.isoformat(),
                            "$lt": last_hour.isoformat()
                        }
                    })
                    
                    # Alert if there's a significant drop (more than 50% reduction)
                    if previous_count > 10 and recent_count < previous_count * 0.5:
                        alerts.append(DataQualityAlert(
                            level=AlertLevel.WARNING,
                            resource_type=resource_type,
                            message=f"Significant drop in {resource_type} data volume detected",
                            details={
                                "recent_hour_count": recent_count,
                                "previous_hour_count": previous_count,
                                "reduction_percentage": round((1 - recent_count / previous_count) * 100, 2)
                            },
                            timestamp=datetime.now()
                        ))
                    
                except Exception as e:
                    logger.error(f"Error checking volume for {resource_type}: {e}")
                    
        except Exception as e:
            logger.error(f"Error in data volume check: {e}")
        
        return alerts
    
    async def send_alerts(self, alerts: List[DataQualityAlert]):
        """Send alerts via Telegram and other channels"""
        if not alerts:
            return
        
        for alert in alerts:
            # Check cooldown to avoid spam
            alert_key = f"{alert.resource_type}_{alert.level.value}"
            if alert_key in self.last_alerts:
                time_since_last = datetime.now() - self.last_alerts[alert_key]
                if time_since_last.total_seconds() < self.alert_cooldown:
                    continue
            
            self.last_alerts[alert_key] = datetime.now()
            
            # Format alert message
            message = self._format_alert_message(alert)
            
            # Send via Telegram
            try:
                await telegram_monitor.send_alert(
                    message=message,
                    severity=alert.level.value,
                    category="FHIR Data Quality"
                )
                logger.info(f"Sent data quality alert: {alert.message}")
            except Exception as e:
                logger.error(f"Error sending alert: {e}")
    
    def _format_alert_message(self, alert: DataQualityAlert) -> str:
        """Format alert message for Telegram"""
        emoji_map = {
            AlertLevel.INFO: "ℹ️",
            AlertLevel.WARNING: "⚠️",
            AlertLevel.ERROR: "❌",
            AlertLevel.CRITICAL: "🚨"
        }
        
        emoji = emoji_map.get(alert.level, "ℹ️")
        
        message = f"{emoji} **FHIR Data Quality Alert**\n\n"
        message += f"**Level:** {alert.level.value.upper()}\n"
        message += f"**Resource:** {alert.resource_type}\n"
        message += f"**Message:** {alert.message}\n"
        message += f"**Time:** {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n"
        
        if alert.details:
            message += "\n**Details:**\n"
            for key, value in alert.details.items():
                message += f"• {key}: {value}\n"
        
        return message
    
    async def get_quality_summary(self) -> Dict[str, Any]:
        """Get current data quality summary"""
        try:
            await mongodb_service.connect()
            db = mongodb_service.get_database('MFC_FHIR_R5')
            
            summary = {
                "timestamp": datetime.now().isoformat(),
                "resource_types": {},
                "overall_health": "unknown"
            }
            
            resource_types = ["Patient", "Observation", "Device", "Organization", "Location"]
            total_issues = 0
            
            for resource_type in resource_types:
                try:
                    collection = db.get_collection(resource_type)
                    total_count = await collection.count_documents({})
                    
                    if total_count == 0:
                        summary["resource_types"][resource_type] = {
                            "total_count": 0,
                            "health": "no_data"
                        }
                        continue
                    
                    # Check recent activity
                    recent_count = await collection.count_documents({
                        "meta.lastUpdated": {
                            "$gte": (datetime.now() - timedelta(hours=24)).isoformat()
                        }
                    })
                    
                    # Check for missing required fields
                    missing_fields = 0
                    if resource_type == "Patient":
                        missing_fields = await collection.count_documents({
                            "$or": [
                                {"name": {"$exists": False}},
                                {"gender": {"$exists": False}}
                            ]
                        })
                    elif resource_type == "Observation":
                        missing_fields = await collection.count_documents({
                            "$or": [
                                {"status": {"$exists": False}},
                                {"code": {"$exists": False}}
                            ]
                        })
                    
                    missing_rate = missing_fields / total_count if total_count > 0 else 0
                    
                    # Determine health status
                    if missing_rate > 0.5:
                        health = "critical"
                        total_issues += 1
                    elif missing_rate > 0.1:
                        health = "warning"
                        total_issues += 1
                    elif recent_count == 0:
                        health = "stale"
                        total_issues += 1
                    else:
                        health = "healthy"
                    
                    summary["resource_types"][resource_type] = {
                        "total_count": total_count,
                        "recent_count_24h": recent_count,
                        "missing_fields": missing_fields,
                        "missing_rate": round(missing_rate * 100, 2),
                        "health": health
                    }
                    
                except Exception as e:
                    logger.error(f"Error getting summary for {resource_type}: {e}")
                    summary["resource_types"][resource_type] = {
                        "error": str(e)
                    }
            
            # Determine overall health
            if total_issues == 0:
                summary["overall_health"] = "healthy"
            elif total_issues <= 2:
                summary["overall_health"] = "warning"
            else:
                summary["overall_health"] = "critical"
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting quality summary: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

# Global monitor instance
fhir_monitor = FHIRDataMonitor() 