from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel

from app.services.reporting_engine import reporting_engine, ReportType, ReportFormat, ReportFrequency
from app.services.auth import get_current_user
from app.models.base import SuccessResponse
from app.utils.error_definitions import ErrorCode, ErrorResponse, create_error_response, create_success_response
from app.utils.structured_logging import get_logger

router = APIRouter(prefix="/reports", tags=["reports"])
logger = get_logger(__name__)

# Pydantic models for request/response
class CreateReportTemplateRequest(BaseModel):
    name: str
    description: Optional[str] = ""
    type: str  # ReportType enum value
    format: str  # ReportFormat enum value
    frequency: str  # ReportFrequency enum value
    recipients: Optional[List[str]] = []
    filters: Optional[Dict[str, Any]] = {}
    template_config: Optional[Dict[str, Any]] = {}

class UpdateReportTemplateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    type: Optional[str] = None
    format: Optional[str] = None
    frequency: Optional[str] = None
    recipients: Optional[List[str]] = None
    filters: Optional[Dict[str, Any]] = None
    template_config: Optional[Dict[str, Any]] = None
    active: Optional[bool] = None

@router.post("/templates",
             response_model=SuccessResponse,
             responses={
                 201: {"description": "Report template created successfully"},
                 400: {"model": ErrorResponse, "description": "Invalid request data"},
                 401: {"model": ErrorResponse, "description": "Unauthorized"},
                 500: {"model": ErrorResponse, "description": "Internal server error"}
             })
async def create_report_template(
    request: CreateReportTemplateRequest,
    current_user: dict = Depends(get_current_user)
):
    """Create a new report template"""
    try:
        # Validate enum values
        try:
            ReportType(request.type)
            ReportFormat(request.format)
            ReportFrequency(request.frequency)
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid enum value: {str(e)}"
            )
        
        # Create template
        template_id = await reporting_engine.create_template(request.dict())
        
        return create_success_response(
            message="Report template created successfully",
            data={
                "template_id": template_id,
                "name": request.name,
                "type": request.type,
                "frequency": request.frequency
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating report template: {str(e)}")
        return create_error_response(
            ErrorCode.INTERNAL_ERROR,
            "Failed to create report template"
        )

@router.get("/templates",
            response_model=SuccessResponse,
            responses={
                200: {"description": "Report templates retrieved successfully"},
                401: {"model": ErrorResponse, "description": "Unauthorized"},
                500: {"model": ErrorResponse, "description": "Internal server error"}
            })
async def list_report_templates(
    active_only: bool = Query(True, description="Show only active templates"),
    current_user: dict = Depends(get_current_user)
):
    """List all report templates"""
    try:
        templates = await reporting_engine.list_templates(active_only=active_only)
        
        return create_success_response(
            message="Report templates retrieved successfully",
            data={
                "templates": templates,
                "count": len(templates)
            }
        )
        
    except Exception as e:
        logger.error(f"Error listing report templates: {str(e)}")
        return create_error_response(
            ErrorCode.INTERNAL_ERROR,
            "Failed to retrieve report templates"
        )

@router.get("/templates/{template_id}",
            response_model=SuccessResponse,
            responses={
                200: {"description": "Report template retrieved successfully"},
                404: {"model": ErrorResponse, "description": "Template not found"},
                401: {"model": ErrorResponse, "description": "Unauthorized"},
                500: {"model": ErrorResponse, "description": "Internal server error"}
            })
async def get_report_template(
    template_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get a specific report template"""
    try:
        templates = await reporting_engine.list_templates(active_only=False)
        template = next((t for t in templates if t["id"] == template_id), None)
        
        if not template:
            raise HTTPException(
                status_code=404,
                detail="Report template not found"
            )
        
        return create_success_response(
            message="Report template retrieved successfully",
            data={"template": template}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting report template: {str(e)}")
        return create_error_response(
            ErrorCode.INTERNAL_ERROR,
            "Failed to retrieve report template"
        )

@router.put("/templates/{template_id}",
            response_model=SuccessResponse,
            responses={
                200: {"description": "Report template updated successfully"},
                404: {"model": ErrorResponse, "description": "Template not found"},
                400: {"model": ErrorResponse, "description": "Invalid request data"},
                401: {"model": ErrorResponse, "description": "Unauthorized"},
                500: {"model": ErrorResponse, "description": "Internal server error"}
            })
async def update_report_template(
    template_id: str,
    request: UpdateReportTemplateRequest,
    current_user: dict = Depends(get_current_user)
):
    """Update an existing report template"""
    try:
        # Validate enum values if provided
        updates = request.dict(exclude_unset=True)
        
        if "type" in updates:
            try:
                ReportType(updates["type"])
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid report type")
        
        if "format" in updates:
            try:
                ReportFormat(updates["format"])
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid report format")
        
        if "frequency" in updates:
            try:
                ReportFrequency(updates["frequency"])
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid report frequency")
        
        # Update template
        success = await reporting_engine.update_template(template_id, updates)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail="Report template not found"
            )
        
        return create_success_response(
            message="Report template updated successfully",
            data={
                "template_id": template_id,
                "updated_fields": list(updates.keys())
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating report template: {str(e)}")
        return create_error_response(
            ErrorCode.INTERNAL_ERROR,
            "Failed to update report template"
        )

@router.delete("/templates/{template_id}",
               response_model=SuccessResponse,
               responses={
                   200: {"description": "Report template deleted successfully"},
                   404: {"model": ErrorResponse, "description": "Template not found"},
                   401: {"model": ErrorResponse, "description": "Unauthorized"},
                   500: {"model": ErrorResponse, "description": "Internal server error"}
               })
async def delete_report_template(
    template_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a report template"""
    try:
        success = await reporting_engine.delete_template(template_id)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail="Report template not found"
            )
        
        return create_success_response(
            message="Report template deleted successfully",
            data={"template_id": template_id}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting report template: {str(e)}")
        return create_error_response(
            ErrorCode.INTERNAL_ERROR,
            "Failed to delete report template"
        )

@router.post("/generate/{template_id}",
             response_model=SuccessResponse,
             responses={
                 202: {"description": "Report generation started"},
                 404: {"model": ErrorResponse, "description": "Template not found"},
                 401: {"model": ErrorResponse, "description": "Unauthorized"},
                 500: {"model": ErrorResponse, "description": "Internal server error"}
             })
async def generate_report(
    template_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Generate a report immediately"""
    try:
        job_id = await reporting_engine.generate_report_now(template_id)
        
        return create_success_response(
            message="Report generation started",
            data={
                "job_id": job_id,
                "template_id": template_id,
                "status": "pending"
            }
        )
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error generating report: {str(e)}")
        return create_error_response(
            ErrorCode.INTERNAL_ERROR,
            "Failed to start report generation"
        )

@router.get("/jobs",
            response_model=SuccessResponse,
            responses={
                200: {"description": "Report jobs retrieved successfully"},
                401: {"model": ErrorResponse, "description": "Unauthorized"},
                500: {"model": ErrorResponse, "description": "Internal server error"}
            })
async def list_report_jobs(
    template_id: Optional[str] = Query(None, description="Filter by template ID"),
    limit: int = Query(50, description="Maximum number of jobs to return", ge=1, le=100),
    current_user: dict = Depends(get_current_user)
):
    """List report generation jobs"""
    try:
        jobs = await reporting_engine.get_report_jobs(template_id=template_id, limit=limit)
        
        return create_success_response(
            message="Report jobs retrieved successfully",
            data={
                "jobs": jobs,
                "count": len(jobs)
            }
        )
        
    except Exception as e:
        logger.error(f"Error listing report jobs: {str(e)}")
        return create_error_response(
            ErrorCode.INTERNAL_ERROR,
            "Failed to retrieve report jobs"
        )

@router.get("/jobs/{job_id}",
            response_model=SuccessResponse,
            responses={
                200: {"description": "Report job retrieved successfully"},
                404: {"model": ErrorResponse, "description": "Job not found"},
                401: {"model": ErrorResponse, "description": "Unauthorized"},
                500: {"model": ErrorResponse, "description": "Internal server error"}
            })
async def get_report_job(
    job_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get a specific report job"""
    try:
        jobs = await reporting_engine.get_report_jobs(limit=1000)  # Get all jobs
        job = next((j for j in jobs if j["id"] == job_id), None)
        
        if not job:
            raise HTTPException(
                status_code=404,
                detail="Report job not found"
            )
        
        return create_success_response(
            message="Report job retrieved successfully",
            data={"job": job}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting report job: {str(e)}")
        return create_error_response(
            ErrorCode.INTERNAL_ERROR,
            "Failed to retrieve report job"
        )

@router.get("/jobs/{job_id}/output",
            response_model=SuccessResponse,
            responses={
                200: {"description": "Report output retrieved successfully"},
                404: {"model": ErrorResponse, "description": "Job or output not found"},
                401: {"model": ErrorResponse, "description": "Unauthorized"},
                500: {"model": ErrorResponse, "description": "Internal server error"}
            })
async def get_report_output(
    job_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get the output of a completed report job"""
    try:
        output = await reporting_engine.get_report_output(job_id)
        
        if not output:
            raise HTTPException(
                status_code=404,
                detail="Report output not found"
            )
        
        return create_success_response(
            message="Report output retrieved successfully",
            data={
                "job_id": job_id,
                "format": output["format"],
                "size": output["size"],
                "content": output["content"],
                "created_at": output["created_at"].isoformat() if output.get("created_at") else None
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting report output: {str(e)}")
        return create_error_response(
            ErrorCode.INTERNAL_ERROR,
            "Failed to retrieve report output"
        )

@router.get("/types",
            response_model=SuccessResponse,
            responses={
                200: {"description": "Report types retrieved successfully"},
                401: {"model": ErrorResponse, "description": "Unauthorized"}
            })
async def get_report_types(
    current_user: dict = Depends(get_current_user)
):
    """Get available report types, formats, and frequencies"""
    try:
        return create_success_response(
            message="Report types retrieved successfully",
            data={
                "report_types": [
                    {
                        "value": rt.value,
                        "label": rt.value.replace("_", " ").title(),
                        "description": _get_report_type_description(rt)
                    }
                    for rt in ReportType
                ],
                "formats": [
                    {
                        "value": rf.value,
                        "label": rf.value.upper(),
                        "description": _get_format_description(rf)
                    }
                    for rf in ReportFormat
                ],
                "frequencies": [
                    {
                        "value": freq.value,
                        "label": freq.value.title(),
                        "description": _get_frequency_description(freq)
                    }
                    for freq in ReportFrequency
                ]
            }
        )
        
    except Exception as e:
        logger.error(f"Error getting report types: {str(e)}")
        return create_error_response(
            ErrorCode.INTERNAL_ERROR,
            "Failed to retrieve report types"
        )

@router.post("/schedule/check",
             response_model=SuccessResponse,
             responses={
                 200: {"description": "Scheduled reports checked"},
                 401: {"model": ErrorResponse, "description": "Unauthorized"},
                 500: {"model": ErrorResponse, "description": "Internal server error"}
             })
async def check_scheduled_reports(
    current_user: dict = Depends(get_current_user)
):
    """Manually trigger scheduled report check (for testing)"""
    try:
        await reporting_engine.check_scheduled_reports()
        
        return create_success_response(
            message="Scheduled reports check completed",
            data={"check_time": datetime.utcnow().isoformat()}
        )
        
    except Exception as e:
        logger.error(f"Error checking scheduled reports: {str(e)}")
        return create_error_response(
            ErrorCode.INTERNAL_ERROR,
            "Failed to check scheduled reports"
        )

def _get_report_type_description(report_type: ReportType) -> str:
    """Get description for report type"""
    descriptions = {
        ReportType.DAILY_SUMMARY: "Daily summary of patient statistics and device usage",
        ReportType.WEEKLY_ANALYTICS: "Weekly analytics with trends and anomaly detection",
        ReportType.MONTHLY_OVERVIEW: "Monthly overview of hospital performance",
        ReportType.PATIENT_REPORT: "Individual patient health report with risk assessment",
        ReportType.HOSPITAL_PERFORMANCE: "Hospital performance metrics and KPIs",
        ReportType.DEVICE_UTILIZATION: "Device usage statistics and compliance rates",
        ReportType.RISK_ASSESSMENT: "Patient risk analysis across hospital or system",
        ReportType.ANOMALY_ALERT: "Real-time alerts for detected anomalies",
        ReportType.SYSTEM_HEALTH: "System health and performance monitoring"
    }
    return descriptions.get(report_type, "")

def _get_format_description(report_format: ReportFormat) -> str:
    """Get description for report format"""
    descriptions = {
        ReportFormat.JSON: "Machine-readable JSON format",
        ReportFormat.HTML: "Human-readable HTML format for web viewing",
        ReportFormat.PDF: "Printable PDF document (future implementation)",
        ReportFormat.CSV: "Comma-separated values for spreadsheet import",
        ReportFormat.EXCEL: "Microsoft Excel format (future implementation)"
    }
    return descriptions.get(report_format, "")

def _get_frequency_description(frequency: ReportFrequency) -> str:
    """Get description for report frequency"""
    descriptions = {
        ReportFrequency.ONCE: "Generate report once",
        ReportFrequency.DAILY: "Generate report daily at midnight",
        ReportFrequency.WEEKLY: "Generate report weekly on Sundays",
        ReportFrequency.MONTHLY: "Generate report monthly on the 1st",
        ReportFrequency.QUARTERLY: "Generate report quarterly"
    }
    return descriptions.get(frequency, "") 