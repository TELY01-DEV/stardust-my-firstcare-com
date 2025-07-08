from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from bson import ObjectId

from app.services.analytics import healthcare_analytics
from app.services.auth import get_current_user
from app.services.cache_service import cache_service, cache_result
from app.models.base import SuccessResponse
from app.utils.structured_logging import get_logger

router = APIRouter()
logger = get_logger(__name__)
analytics_service = healthcare_analytics

@router.get("/analytics/patients/statistics",
            response_model=SuccessResponse,
            responses={
                200: {"description": "Patient statistics retrieved successfully"},
                401: {"description": "Unauthorized"},
                500: {"description": "Internal server error"}
            })
@cache_result("analytics_patients_stats", ttl=300)  # Cache for 5 minutes
async def get_patient_statistics(
    hospital_id: Optional[str] = Query(None, description="Filter by hospital ID"),
    start_date: Optional[datetime] = Query(None, description="Start date for analysis"),
    end_date: Optional[datetime] = Query(None, description="End date for analysis"),
    current_user: dict = Depends(get_current_user)
):
    """Get comprehensive patient statistics and analytics"""
    try:
        # Validate hospital_id if provided
        if hospital_id and not ObjectId.is_valid(hospital_id):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid hospital_id format: '{hospital_id}'. Must be a valid ObjectId."
            )
        
        # Get analytics data
        analytics = await analytics_service.get_patient_statistics(
            hospital_id=hospital_id,
            start_date=start_date,
            end_date=end_date
        )
        
        return SuccessResponse(
            success=True,
            message="Patient statistics retrieved successfully",
            data=analytics
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting patient statistics: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve patient statistics"
        )

@router.get("/analytics/vitals/{patient_id}",
            response_model=SuccessResponse,
            responses={
                200: {"description": "Vital signs analytics retrieved successfully"},
                401: {"description": "Unauthorized"},
                404: {"description": "Patient not found"},
                500: {"description": "Internal server error"}
            })
@cache_result("analytics_vitals", ttl=180)  # Cache for 3 minutes
async def get_vital_signs_analytics(
    patient_id: str,
    vital_type: Optional[str] = Query(None, description="Type of vital sign (blood_pressure, heart_rate, temperature, spo2)"),
    period: str = Query("weekly", description="Analysis period (daily, weekly, monthly, quarterly, yearly)"),
    current_user: dict = Depends(get_current_user)
):
    """Get vital signs analytics for a patient"""
    try:
        # Validate patient_id
        if not ObjectId.is_valid(patient_id):
            raise HTTPException(
                status_code=400,
                detail="Invalid patient ID format"
            )
        
        # Validate period
        valid_periods = ["daily", "weekly", "monthly", "quarterly", "yearly"]
        if period not in valid_periods:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid period. Must be one of: {', '.join(valid_periods)}"
            )
        
        # Get analytics
        analytics = await analytics_service.get_vital_signs_analytics(
            patient_id=patient_id,
            vital_type=vital_type,
            period=period
        )
        
        return SuccessResponse(
            success=True,
            message="Vital signs analytics retrieved successfully",
            data=analytics
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting vital signs analytics: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve vital signs analytics"
        )

@router.get("/analytics/devices/utilization",
            response_model=SuccessResponse,
            responses={
                200: {"description": "Device utilization analytics retrieved successfully"},
                401: {"description": "Unauthorized"},
                500: {"description": "Internal server error"}
            })
@cache_result("analytics_devices", ttl=600)  # Cache for 10 minutes
async def get_device_utilization(
    hospital_id: Optional[str] = Query(None, description="Filter by hospital ID"),
    device_type: Optional[str] = Query(None, description="Filter by device type"),
    period: str = Query("monthly", description="Analysis period"),
    current_user: dict = Depends(get_current_user)
):
    """Get device utilization analytics"""
    try:
        # Validate hospital_id if provided
        if hospital_id and not ObjectId.is_valid(hospital_id):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid hospital_id format: '{hospital_id}'. Must be a valid ObjectId."
            )
        
        # Get analytics
        analytics = await analytics_service.get_device_utilization_analytics(
            hospital_id=hospital_id,
            device_type=device_type,
            period=period
        )
        
        return SuccessResponse(
            success=True,
            message="Device utilization analytics retrieved successfully",
            data=analytics
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting device utilization: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve device utilization analytics"
        )

@router.get("/analytics/health-risks/{patient_id}",
            response_model=SuccessResponse,
            responses={
                200: {"description": "Health risk predictions retrieved successfully"},
                401: {"description": "Unauthorized"},
                404: {"description": "Patient not found"},
                500: {"description": "Internal server error"}
            })
@cache_result("analytics_risks", ttl=300)  # Cache for 5 minutes
async def get_health_risk_predictions(
    patient_id: str,
    include_recommendations: bool = Query(True, description="Include health recommendations"),
    current_user: dict = Depends(get_current_user)
):
    """Get health risk predictions for a patient"""
    try:
        # Validate patient_id
        if not ObjectId.is_valid(patient_id):
            raise HTTPException(
                status_code=400,
                detail="Invalid patient ID format"
            )
        
        # Get predictions
        predictions = await analytics_service.predict_health_risks(patient_id)
        
        # Get recommendations if requested
        if include_recommendations and predictions.get("risk_score", 0) > 0:
            recommendations = await analytics_service.get_health_recommendations(
                patient_id,
                predictions.get("risk_factors", [])
            )
            predictions["recommendations"] = recommendations
        
        return SuccessResponse(
            success=True,
            message="Health risk predictions retrieved successfully",
            data=predictions
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting health risk predictions: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve health risk predictions"
        )

@router.get("/analytics/trends/vitals",
            response_model=SuccessResponse,
            responses={
                200: {"description": "Vital signs trends retrieved successfully"},
                400: {"description": "Invalid parameters"},
                401: {"description": "Unauthorized"},
                422: {"description": "Missing required parameters"},
                500: {"description": "Internal server error"}
            })
@cache_result("analytics_trends_vitals", ttl=300)  # Cache for 5 minutes
async def get_vital_trends(
    vital_type: str = Query(
        ..., 
        description="Type of vital sign (required): heart_rate, blood_pressure, temperature, spo2, respiratory_rate"
    ),
    patient_id: Optional[str] = Query(None, description="Filter by specific patient ID"),
    hospital_id: Optional[str] = Query(None, description="Filter by hospital ID"),
    days: int = Query(30, description="Number of days to analyze", ge=1, le=365),
    current_user: dict = Depends(get_current_user)
):
    """
    Get vital signs trends analysis
    
    **Required Parameters:**
    - vital_type: Type of vital sign to analyze (heart_rate, blood_pressure, temperature, spo2, respiratory_rate)
    
    **Optional Parameters:**
    - patient_id: Analyze trends for specific patient
    - hospital_id: Filter by hospital
    - days: Number of days to include in analysis (1-365)
    
    **Example Usage:**
    - `/analytics/trends/vitals?vital_type=heart_rate&days=7`
    - `/analytics/trends/vitals?vital_type=blood_pressure&patient_id=123&days=30`
    """
    try:
        # Validate vital_type against supported types
        valid_vital_types = ["heart_rate", "blood_pressure", "temperature", "spo2", "respiratory_rate"]
        if vital_type not in valid_vital_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid vital_type '{vital_type}'. Must be one of: {', '.join(valid_vital_types)}"
            )
        
        # Validate patient_id if provided
        if patient_id and not ObjectId.is_valid(patient_id):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid patient_id format: '{patient_id}'. Must be a valid ObjectId."
            )
        
        # Validate hospital_id if provided
        if hospital_id and not ObjectId.is_valid(hospital_id):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid hospital_id format: '{hospital_id}'. Must be a valid ObjectId."
            )
        
        # Calculate date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Get trends
        if patient_id:
            # Single patient trends
            analytics = await analytics_service.get_vital_signs_analytics(
                patient_id=patient_id,
                vital_type=vital_type,
                period="daily" if days <= 30 else "weekly"
            )
            trends = analytics.get("trends", {})
        else:
            # Aggregate trends for hospital or system
            trends = await analytics_service._analyze_aggregate_trends(
                vital_type=vital_type,
                hospital_id=hospital_id,
                start_date=start_date,
                end_date=end_date
            )
        
        return SuccessResponse(
            success=True,
            message="Vital signs trends retrieved successfully",
            data={
                "vital_type": vital_type,
                "period_days": days,
                "trends": trends,
                "analysis_date": datetime.utcnow().isoformat()
            }
        )
    except Exception as e:
        logger.error(f"Error getting vital trends: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve vital signs trends"
        )

@router.get("/analytics/anomalies/detect",
            response_model=SuccessResponse,
            responses={
                200: {"description": "Anomalies detected successfully"},
                401: {"description": "Unauthorized"},
                500: {"description": "Internal server error"}
            })
async def detect_anomalies(
    hospital_id: Optional[str] = Query(None, description="Filter by hospital ID"),
    patient_id: Optional[str] = Query(None, description="Filter by patient ID"),
    threshold: float = Query(2.0, description="Z-score threshold for anomaly detection", ge=1.0, le=4.0),
    days: int = Query(7, description="Number of days to analyze", ge=1, le=30),
    current_user: dict = Depends(get_current_user)
):
    """Detect anomalies in vital signs data"""
    try:
        # Validate hospital_id if provided
        if hospital_id and not ObjectId.is_valid(hospital_id):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid hospital_id format: '{hospital_id}'. Must be a valid ObjectId."
            )
        
        # Validate patient_id if provided
        if patient_id and not ObjectId.is_valid(patient_id):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid patient_id format: '{patient_id}'. Must be a valid ObjectId."
            )
        
        # Calculate date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Detect anomalies
        anomalies = await analytics_service.detect_vital_anomalies(
            hospital_id=hospital_id,
            patient_id=patient_id,
            start_date=start_date,
            end_date=end_date,
            threshold=threshold
        )
        
        return SuccessResponse(
            success=True,
            message="Anomaly detection completed successfully",
            data={
                "anomalies": anomalies,
                "threshold": threshold,
                "period_days": days,
                "detection_date": datetime.utcnow().isoformat()
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error detecting anomalies: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to detect anomalies"
        )

@router.get("/analytics/reports/summary/{report_type}",
            response_model=SuccessResponse,
            responses={
                200: {"description": "Summary report generated successfully"},
                401: {"description": "Unauthorized"},
                400: {"description": "Invalid report type"},
                500: {"description": "Internal server error"}
            })
@cache_result("analytics_reports", ttl=1800)  # Cache for 30 minutes
async def generate_summary_report(
    report_type: str,
    hospital_id: Optional[str] = Query(None, description="Filter by hospital ID"),
    start_date: Optional[datetime] = Query(None, description="Start date for report"),
    end_date: Optional[datetime] = Query(None, description="End date for report"),
    current_user: dict = Depends(get_current_user)
):
    """Generate summary analytics reports"""
    try:
        # Validate report type
        valid_reports = ["patient", "hospital", "device", "health_risk", "system_overview"]
        if report_type not in valid_reports:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid report type. Must be one of: {', '.join(valid_reports)}"
            )
        
        # Validate hospital_id if provided
        if hospital_id and not ObjectId.is_valid(hospital_id):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid hospital_id format: '{hospital_id}'. Must be a valid ObjectId."
            )
        
        # Generate report based on type
        report_data = {}
        
        if report_type == "patient":
            report_data = await analytics_service.get_patient_statistics(
                hospital_id=hospital_id,
                start_date=start_date,
                end_date=end_date
            )
        elif report_type == "hospital":
            # Hospital performance metrics
            report_data = await analytics_service._generate_hospital_report(
                hospital_id=hospital_id,
                start_date=start_date,
                end_date=end_date
            )
        elif report_type == "device":
            report_data = await analytics_service.get_device_utilization_analytics(
                hospital_id=hospital_id,
                period="monthly"
            )
        elif report_type == "health_risk":
            # Aggregate health risk analysis
            report_data = await analytics_service._generate_health_risk_report(
                hospital_id=hospital_id,
                start_date=start_date,
                end_date=end_date
            )
        elif report_type == "system_overview":
            # Complete system analytics overview
            report_data = {
                "patients": await analytics_service.get_patient_statistics(),
                "devices": await analytics_service.get_device_utilization_analytics(),
                "generated_at": datetime.utcnow().isoformat()
            }
        
        return SuccessResponse(
            success=True,
            message=f"{report_type.title()} report generated successfully",
            data={
                "report_type": report_type,
                "report_data": report_data,
                "generated_at": datetime.utcnow().isoformat(),
                "filters": {
                    "hospital_id": hospital_id,
                    "start_date": start_date.isoformat() if start_date else None,
                    "end_date": end_date.isoformat() if end_date else None
                }
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating {report_type} report: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate {report_type} report"
        )

@router.post("/analytics/export/{format}",
             response_model=SuccessResponse,
             responses={
                 200: {"description": "Analytics data exported successfully"},
                 401: {"description": "Unauthorized"},
                 400: {"description": "Invalid export format"},
                 500: {"description": "Internal server error"}
             })
async def export_analytics_data(
    format: str,
    report_type: str = Query(..., description="Type of report to export"),
    hospital_id: Optional[str] = Query(None, description="Filter by hospital ID"),
    start_date: Optional[datetime] = Query(None, description="Start date for export"),
    end_date: Optional[datetime] = Query(None, description="End date for export"),
    current_user: dict = Depends(get_current_user)
):
    """Export analytics data in various formats"""
    try:
        # Validate format
        valid_formats = ["json", "csv", "excel", "pdf"]
        if format not in valid_formats:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid export format. Must be one of: {', '.join(valid_formats)}"
            )
        
        # Validate hospital_id if provided
        if hospital_id and not ObjectId.is_valid(hospital_id):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid hospital_id format: '{hospital_id}'. Must be a valid ObjectId."
            )
        
        # For now, we'll return the data structure that would be exported
        # In a real implementation, this would generate actual files
        export_info = {
            "format": format,
            "report_type": report_type,
            "export_date": datetime.utcnow().isoformat(),
            "filters": {
                "hospital_id": hospital_id,
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None
            },
            "status": "ready_for_download",
            "download_url": f"/analytics/download/{format}/{report_type}"  # Placeholder
        }
        
        return SuccessResponse(
            success=True,
            message=f"Analytics data prepared for export in {format} format",
            data=export_info
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting analytics data: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to export analytics data"
        ) 