from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from bson import ObjectId

from app.services.analytics import healthcare_analytics as analytics_service
from app.services.auth import get_current_user
from app.services.cache_service import cache_service, cache_result
from app.models.base import SuccessResponse
from app.utils.error_definitions import ErrorResponse
from app.utils.error_definitions import ErrorCode, create_error_response
from app.utils.structured_logging import get_logger

router = APIRouter(prefix="/visualization", tags=["visualization"])
logger = get_logger(__name__)

# Chart type configurations
CHART_TYPES = {
    "line": ["time_series", "trends", "vitals_over_time"],
    "bar": ["demographics", "risk_distribution", "device_utilization"],
    "pie": ["gender_distribution", "age_groups", "device_types"],
    "scatter": ["correlation", "anomalies"],
    "heatmap": ["patient_activity", "risk_matrix"],
    "gauge": ["risk_score", "compliance_rate", "utilization_rate"],
    "area": ["cumulative_patients", "device_readings"]
}

@router.get("/charts/patient-demographics",
            response_model=SuccessResponse,
            responses={
                200: {"description": "Patient demographics chart data retrieved successfully"},
                401: {"model": ErrorResponse, "description": "Unauthorized"},
                500: {"model": ErrorResponse, "description": "Internal server error"}
            })
@cache_result("viz_demographics", ttl=600)  # Cache for 10 minutes
async def get_patient_demographics_chart(
    hospital_id: Optional[str] = Query(None, description="Filter by hospital ID"),
    chart_type: str = Query("bar", description="Chart type (bar, pie, donut)"),
    current_user: dict = Depends(get_current_user)
):
    """Get patient demographics data formatted for charts"""
    try:
        # Validate hospital_id if provided
        if hospital_id and not ObjectId.is_valid(hospital_id):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid hospital_id format: '{hospital_id}'. Must be a valid ObjectId."
            )
        
        # Get patient statistics
        stats = await analytics_service.get_patient_statistics(hospital_id=hospital_id)
        
        # Format data based on chart type
        if chart_type in ["pie", "donut"]:
            # Format for pie/donut chart
            age_data = {
                "labels": list(stats["demographics"]["age_distribution"].keys()),
                "datasets": [{
                    "data": list(stats["demographics"]["age_distribution"].values()),
                    "backgroundColor": [
                        "#FF6384", "#36A2EB", "#FFCE56", 
                        "#4BC0C0", "#9966FF", "#FF9F40"
                    ]
                }]
            }
            
            gender_data = {
                "labels": list(stats["demographics"]["gender_distribution"].keys()),
                "datasets": [{
                    "data": list(stats["demographics"]["gender_distribution"].values()),
                    "backgroundColor": ["#36A2EB", "#FF6384", "#FFCE56"]
                }]
            }
        else:  # bar chart
            age_data = {
                "labels": list(stats["demographics"]["age_distribution"].keys()),
                "datasets": [{
                    "label": "Number of Patients",
                    "data": list(stats["demographics"]["age_distribution"].values()),
                    "backgroundColor": "#36A2EB",
                    "borderColor": "#2E86AB",
                    "borderWidth": 1
                }]
            }
            
            gender_data = {
                "labels": list(stats["demographics"]["gender_distribution"].keys()),
                "datasets": [{
                    "label": "Number of Patients",
                    "data": list(stats["demographics"]["gender_distribution"].values()),
                    "backgroundColor": ["#36A2EB", "#FF6384"],
                    "borderWidth": 1
                }]
            }
        
        return SuccessResponse(
            success=True,
            message="Patient demographics chart data retrieved successfully",
            data={
                "age_distribution": age_data,
                "gender_distribution": gender_data,
                "summary": stats["summary"],
                "chart_type": chart_type
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting demographics chart data: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve demographics chart data"
        )

@router.get("/charts/vital-trends/{patient_id}",
            response_model=SuccessResponse,
            responses={
                200: {"description": "Vital signs trend chart data retrieved successfully"},
                401: {"model": ErrorResponse, "description": "Unauthorized"},
                404: {"model": ErrorResponse, "description": "Patient not found"},
                500: {"model": ErrorResponse, "description": "Internal server error"}
            })
@cache_result("viz_vitals", ttl=180)  # Cache for 3 minutes
async def get_vital_trends_chart(
    patient_id: str,
    vital_type: str = Query(..., description="Type of vital sign"),
    days: int = Query(7, description="Number of days to display", ge=1, le=90),
    chart_type: str = Query("line", description="Chart type (line, area)"),
    current_user: dict = Depends(get_current_user)
):
    """Get vital signs trends formatted for time-series charts"""
    try:
        # Validate patient_id
        if not ObjectId.is_valid(patient_id):
            raise HTTPException(
                status_code=400,
                detail="Invalid patient ID format"
            )
        
        # Get vital signs analytics
        period = "daily" if days <= 30 else "weekly"
        analytics = await analytics_service.get_vital_signs_analytics(
            patient_id=patient_id,
            vital_type=vital_type,
            period=period
        )
        
        if analytics.get("no_data"):
            return SuccessResponse(
                success=True,
                message="No vital signs data available",
                data={"no_data": True}
            )
        
        # Generate time series data
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Mock time series data (in production, this would come from actual readings)
        dates = []
        current = start_date
        while current <= end_date:
            dates.append(current.strftime("%Y-%m-%d"))
            current += timedelta(days=1 if period == "daily" else 7)
        
        # Format chart data
        if vital_type == "blood_pressure":
            chart_data = {
                "labels": dates,
                "datasets": [
                    {
                        "label": "Systolic",
                        "data": [120 + i % 10 for i in range(len(dates))],  # Mock data
                        "borderColor": "#FF6384",
                        "backgroundColor": "rgba(255, 99, 132, 0.1)" if chart_type == "area" else "transparent",
                        "tension": 0.4,
                        "fill": chart_type == "area"
                    },
                    {
                        "label": "Diastolic",
                        "data": [80 + i % 5 for i in range(len(dates))],  # Mock data
                        "borderColor": "#36A2EB",
                        "backgroundColor": "rgba(54, 162, 235, 0.1)" if chart_type == "area" else "transparent",
                        "tension": 0.4,
                        "fill": chart_type == "area"
                    }
                ]
            }
        else:
            # Single value vital signs
            chart_data = {
                "labels": dates,
                "datasets": [{
                    "label": vital_type.replace("_", " ").title(),
                    "data": [analytics.get("mean", 0) + (i % 5 - 2) for i in range(len(dates))],  # Mock data
                    "borderColor": "#36A2EB",
                    "backgroundColor": "rgba(54, 162, 235, 0.1)" if chart_type == "area" else "transparent",
                    "tension": 0.4,
                    "fill": chart_type == "area"
                }]
            }
        
        # Add threshold lines
        thresholds = _get_vital_thresholds(vital_type)
        
        return SuccessResponse(
            success=True,
            message="Vital signs trend chart data retrieved successfully",
            data={
                "chart_data": chart_data,
                "statistics": {
                    "mean": analytics.get("mean"),
                    "min": analytics.get("min"),
                    "max": analytics.get("max"),
                    "trend": analytics.get("trend", {}).get("direction")
                },
                "thresholds": thresholds,
                "chart_type": chart_type,
                "period": period
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting vital trends chart data: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve vital trends chart data"
        )

@router.get("/charts/risk-distribution",
            response_model=SuccessResponse,
            responses={
                200: {"description": "Risk distribution chart data retrieved successfully"},
                401: {"model": ErrorResponse, "description": "Unauthorized"},
                500: {"model": ErrorResponse, "description": "Internal server error"}
            })
@cache_result("viz_risk", ttl=300)  # Cache for 5 minutes
async def get_risk_distribution_chart(
    hospital_id: Optional[str] = Query(None, description="Filter by hospital ID"),
    chart_type: str = Query("pie", description="Chart type (pie, donut, bar)"),
    current_user: dict = Depends(get_current_user)
):
    """Get patient risk distribution formatted for charts"""
    try:
        # Validate hospital_id if provided
        if hospital_id and not ObjectId.is_valid(hospital_id):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid hospital_id format: '{hospital_id}'. Must be a valid ObjectId."
            )
        
        # Get patient statistics
        stats = await analytics_service.get_patient_statistics(hospital_id=hospital_id)
        risk_dist = stats.get("risk_analysis", {}).get("distribution", {})
        
        # Define risk level colors
        risk_colors = {
            "low": "#4CAF50",      # Green
            "medium": "#FFC107",   # Amber
            "high": "#FF9800",     # Orange
            "critical": "#F44336"  # Red
        }
        
        # Ensure all risk levels are present
        for level in ["low", "medium", "high", "critical"]:
            if level not in risk_dist:
                risk_dist[level] = 0
        
        # Format data based on chart type
        if chart_type in ["pie", "donut"]:
            chart_data = {
                "labels": ["Low Risk", "Medium Risk", "High Risk", "Critical Risk"],
                "datasets": [{
                    "data": [
                        risk_dist.get("low", 0),
                        risk_dist.get("medium", 0),
                        risk_dist.get("high", 0),
                        risk_dist.get("critical", 0)
                    ],
                    "backgroundColor": [
                        risk_colors["low"],
                        risk_colors["medium"],
                        risk_colors["high"],
                        risk_colors["critical"]
                    ],
                    "borderWidth": 2,
                    "borderColor": "#fff"
                }]
            }
        else:  # bar chart
            chart_data = {
                "labels": ["Low", "Medium", "High", "Critical"],
                "datasets": [{
                    "label": "Number of Patients",
                    "data": [
                        risk_dist.get("low", 0),
                        risk_dist.get("medium", 0),
                        risk_dist.get("high", 0),
                        risk_dist.get("critical", 0)
                    ],
                    "backgroundColor": [
                        risk_colors["low"],
                        risk_colors["medium"],
                        risk_colors["high"],
                        risk_colors["critical"]
                    ],
                    "borderWidth": 1
                }]
            }
        
        return SuccessResponse(
            success=True,
            message="Risk distribution chart data retrieved successfully",
            data={
                "chart_data": chart_data,
                "summary": {
                    "total_patients": sum(risk_dist.values()),
                    "high_risk_percentage": (
                        (risk_dist.get("high", 0) + risk_dist.get("critical", 0)) / 
                        max(sum(risk_dist.values()), 1) * 100
                    )
                },
                "chart_type": chart_type
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting risk distribution chart data: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve risk distribution chart data"
        )

@router.get("/charts/device-utilization",
            response_model=SuccessResponse,
            responses={
                200: {"description": "Device utilization chart data retrieved successfully"},
                401: {"model": ErrorResponse, "description": "Unauthorized"},
                500: {"model": ErrorResponse, "description": "Internal server error"}
            })
@cache_result("viz_devices", ttl=600)  # Cache for 10 minutes
async def get_device_utilization_chart(
    hospital_id: Optional[str] = Query(None, description="Filter by hospital ID"),
    period: str = Query("weekly", description="Analysis period"),
    chart_type: str = Query("bar", description="Chart type (bar, line, area)"),
    current_user: dict = Depends(get_current_user)
):
    """Get device utilization data formatted for charts"""
    try:
        # Validate hospital_id if provided
        if hospital_id and not ObjectId.is_valid(hospital_id):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid hospital_id format: '{hospital_id}'. Must be a valid ObjectId."
            )
        
        # Get device analytics
        device_stats = await analytics_service.get_device_utilization_analytics(
            hospital_id=hospital_id,
            period=period
        )
        
        # Format data for charts
        device_types = []
        active_devices = []
        total_readings = []
        utilization_rates = []
        
        for device_type, stats in device_stats.items():
            if isinstance(stats, dict) and "active_devices" in stats:
                device_types.append(device_type.replace("_", " ").title())
                active_devices.append(stats.get("active_devices", 0))
                total_readings.append(stats.get("total_readings", 0))
                utilization_rates.append(stats.get("utilization_rate", 0) * 100)
        
        if chart_type == "line":
            chart_data = {
                "labels": device_types,
                "datasets": [
                    {
                        "label": "Active Devices",
                        "data": active_devices,
                        "borderColor": "#36A2EB",
                        "tension": 0.4,
                        "yAxisID": "y"
                    },
                    {
                        "label": "Utilization Rate (%)",
                        "data": utilization_rates,
                        "borderColor": "#FF6384",
                        "tension": 0.4,
                        "yAxisID": "y1"
                    }
                ]
            }
        else:  # bar or area
            chart_data = {
                "labels": device_types,
                "datasets": [
                    {
                        "label": "Active Devices",
                        "data": active_devices,
                        "backgroundColor": "#36A2EB",
                        "borderWidth": 1
                    },
                    {
                        "label": "Total Readings",
                        "data": total_readings,
                        "backgroundColor": "#4BC0C0",
                        "borderWidth": 1
                    }
                ]
            }
        
        return SuccessResponse(
            success=True,
            message="Device utilization chart data retrieved successfully",
            data={
                "chart_data": chart_data,
                "summary": {
                    "total_active_devices": sum(active_devices),
                    "total_readings": sum(total_readings),
                    "average_utilization": sum(utilization_rates) / len(utilization_rates) if utilization_rates else 0
                },
                "chart_type": chart_type,
                "period": period
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting device utilization chart data: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve device utilization chart data"
        )

@router.get("/charts/anomaly-scatter/{patient_id}",
            response_model=SuccessResponse,
            responses={
                200: {"description": "Anomaly scatter plot data retrieved successfully"},
                401: {"model": ErrorResponse, "description": "Unauthorized"},
                500: {"model": ErrorResponse, "description": "Internal server error"}
            })
async def get_anomaly_scatter_chart(
    patient_id: str,
    vital_type: str = Query(..., description="Type of vital sign"),
    days: int = Query(30, description="Number of days to analyze", ge=1, le=90),
    current_user: dict = Depends(get_current_user)
):
    """Get vital signs anomaly data formatted for scatter plot charts"""
    try:
        # Validate patient_id
        if not ObjectId.is_valid(patient_id):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid patient_id format: '{patient_id}'. Must be a valid ObjectId."
            )
        
        # Calculate date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Get anomaly detection results
        anomalies = await analytics_service.detect_vital_anomalies(
            patient_id=patient_id,
            start_date=start_date,
            end_date=end_date,
            threshold=2.0
        )
        
        # Filter by vital type
        filtered_anomalies = [
            a for a in anomalies 
            if a.get("vital_type") == vital_type
        ]
        
        # Format for scatter plot
        normal_data = []
        anomaly_data = []
        
        # Mock normal data points
        for i in range(days * 2):  # Assume 2 readings per day
            timestamp = (datetime.utcnow() - timedelta(days=days) + timedelta(hours=i*12)).isoformat()
            value = 120 + (i % 10) if vital_type == "blood_pressure" else 98.6 + (i % 3) * 0.1
            normal_data.append({
                "x": timestamp,
                "y": value
            })
        
        # Add anomaly points
        for anomaly in filtered_anomalies:
            anomaly_data.append({
                "x": anomaly["timestamp"],
                "y": anomaly["value"],
                "z_score": anomaly["z_score"]
            })
        
        chart_data = {
            "datasets": [
                {
                    "label": "Normal Readings",
                    "data": normal_data,
                    "backgroundColor": "#36A2EB",
                    "pointRadius": 3
                },
                {
                    "label": "Anomalies",
                    "data": anomaly_data,
                    "backgroundColor": "#FF6384",
                    "pointRadius": 6,
                    "pointStyle": "triangle"
                }
            ]
        }
        
        return SuccessResponse(
            success=True,
            message="Anomaly scatter plot data retrieved successfully",
            data={
                "chart_data": chart_data,
                "anomaly_count": len(anomaly_data),
                "total_readings": len(normal_data) + len(anomaly_data),
                "vital_type": vital_type
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting anomaly scatter data: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve anomaly scatter data"
        )

@router.get("/charts/risk-gauge/{patient_id}",
            response_model=SuccessResponse,
            responses={
                200: {"description": "Risk gauge chart data retrieved successfully"},
                401: {"model": ErrorResponse, "description": "Unauthorized"},
                404: {"model": ErrorResponse, "description": "Patient not found"},
                500: {"model": ErrorResponse, "description": "Internal server error"}
            })
@cache_result("viz_gauge", ttl=300)  # Cache for 5 minutes
async def get_risk_gauge_chart(
    patient_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get patient risk score formatted for gauge chart"""
    try:
        # Validate patient_id
        if not ObjectId.is_valid(patient_id):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid patient_id format: '{patient_id}'. Must be a valid ObjectId."
            )
        
        # Get risk prediction
        risk_data = await analytics_service.predict_health_risks(patient_id)
        risk_score = risk_data.get("risk_score", 0) * 100  # Convert to percentage
        
        # Format for gauge chart
        chart_data = {
            "value": round(risk_score, 1),
            "min": 0,
            "max": 100,
            "title": "Health Risk Score",
            "label": "%",
            "thresholds": {
                "0": {"color": "#4CAF50", "label": "Low"},      # 0-30: Green
                "30": {"color": "#FFC107", "label": "Medium"},  # 30-50: Amber
                "50": {"color": "#FF9800", "label": "High"},    # 50-70: Orange
                "70": {"color": "#F44336", "label": "Critical"} # 70-100: Red
            }
        }
        
        # Determine risk level
        if risk_score < 30:
            risk_level = "low"
        elif risk_score < 50:
            risk_level = "medium"
        elif risk_score < 70:
            risk_level = "high"
        else:
            risk_level = "critical"
        
        return SuccessResponse(
            success=True,
            message="Risk gauge chart data retrieved successfully",
            data={
                "chart_data": chart_data,
                "risk_factors": risk_data.get("risk_factors", []),
                "risk_level": risk_level,
                "recommendations": len(risk_data.get("recommendations", []))
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting risk gauge data: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve risk gauge data"
        )

@router.get("/charts/system-overview",
            response_model=SuccessResponse,
            responses={
                200: {"description": "System overview dashboard data retrieved successfully"},
                401: {"model": ErrorResponse, "description": "Unauthorized"},
                500: {"model": ErrorResponse, "description": "Internal server error"}
            })
@cache_result("viz_overview", ttl=300)  # Cache for 5 minutes
async def get_system_overview_charts(
    current_user: dict = Depends(get_current_user)
):
    """Get system overview data for dashboard"""
    try:
        # Get various statistics
        patient_stats = await analytics_service.get_patient_statistics()
        device_stats = await analytics_service.get_device_utilization_analytics()
        
        # Key metrics cards
        metrics = {
            "total_patients": {
                "value": patient_stats["summary"]["total_patients"],
                "label": "Total Patients",
                "icon": "users",
                "trend": "+5.2%",  # Mock trend
                "color": "#36A2EB"
            },
            "active_patients": {
                "value": patient_stats["summary"]["active_patients"],
                "label": "Active Patients",
                "icon": "user-check",
                "trend": "+2.8%",  # Mock trend
                "color": "#4CAF50"
            },
            "high_risk_patients": {
                "value": patient_stats["risk_analysis"]["high_risk_count"],
                "label": "High Risk Patients",
                "icon": "exclamation-triangle",
                "trend": "-1.5%",  # Mock trend
                "color": "#FF6384"
            },
            "device_compliance": {
                "value": "87.5%",  # Mock value
                "label": "Device Compliance",
                "icon": "chart-line",
                "trend": "+3.2%",  # Mock trend
                "color": "#4BC0C0"
            }
        }
        
        # Mini charts for dashboard
        mini_charts = {
            "patient_trend": {
                "type": "line",
                "data": {
                    "labels": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
                    "datasets": [{
                        "data": [420, 425, 422, 428, 431, 429, 431],
                        "borderColor": "#36A2EB",
                        "tension": 0.4,
                        "pointRadius": 0
                    }]
                }
            },
            "risk_summary": {
                "type": "doughnut",
                "data": {
                    "labels": ["Low", "Medium", "High", "Critical"],
                    "datasets": [{
                        "data": [250, 120, 45, 16],
                        "backgroundColor": ["#4CAF50", "#FFC107", "#FF9800", "#F44336"]
                    }]
                }
            }
        }
        
        return SuccessResponse(
            success=True,
            message="System overview dashboard data retrieved successfully",
            data={
                "metrics": metrics,
                "mini_charts": mini_charts,
                "last_updated": datetime.utcnow().isoformat()
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting system overview data: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve system overview data"
        )

def _get_vital_thresholds(vital_type: str) -> Dict[str, Any]:
    """Get threshold lines for vital signs charts"""
    thresholds = {
        "blood_pressure": {
            "systolic": {
                "normal": {"min": 90, "max": 120, "color": "#4CAF50"},
                "elevated": {"min": 120, "max": 130, "color": "#FFC107"},
                "high": {"min": 130, "max": 180, "color": "#FF9800"},
                "critical": {"min": 180, "color": "#F44336"}
            },
            "diastolic": {
                "normal": {"min": 60, "max": 80, "color": "#4CAF50"},
                "high": {"min": 80, "max": 120, "color": "#FF9800"},
                "critical": {"min": 120, "color": "#F44336"}
            }
        },
        "heart_rate": {
            "low": {"max": 60, "color": "#2196F3"},
            "normal": {"min": 60, "max": 100, "color": "#4CAF50"},
            "high": {"min": 100, "max": 150, "color": "#FF9800"},
            "critical": {"min": 150, "color": "#F44336"}
        },
        "temperature": {
            "low": {"max": 36.0, "color": "#2196F3"},
            "normal": {"min": 36.0, "max": 37.5, "color": "#4CAF50"},
            "fever": {"min": 37.5, "max": 39.0, "color": "#FF9800"},
            "high_fever": {"min": 39.0, "color": "#F44336"}
        },
        "spo2": {
            "critical": {"max": 90, "color": "#F44336"},
            "low": {"min": 90, "max": 95, "color": "#FF9800"},
            "normal": {"min": 95, "max": 100, "color": "#4CAF50"}
        }
    }
    
    return thresholds.get(vital_type, {}) 