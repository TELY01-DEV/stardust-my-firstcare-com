"""
FHIR Data Validation API Endpoints
Provides endpoints for validating FHIR data integrity and correctness
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import JSONResponse

from app.services.auth import require_auth
from app.services.fhir_data_validator import fhir_validator, ValidationSeverity
from app.services.rate_limiter import rate_limiter
from app.utils.performance_decorators import api_endpoint_timing

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/fhir/validation", tags=["FHIR Validation"])

@router.get("/health", summary="FHIR Data Health Check")
@api_endpoint_timing("fhir_validation_health")
async def check_fhir_data_health(
    resource_type: Optional[str] = Query(None, description="Specific resource type to validate"),
    limit: int = Query(100, description="Maximum number of resources to validate per type"),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Quick health check of FHIR data integrity"""
    try:
        # Rate limiting
        await rate_limiter.check_rate_limit(current_user)
        
        # Run validation
        results = await fhir_validator.validate_all_resources(resource_type, limit)
        
        # Generate summary
        total_errors = 0
        total_warnings = 0
        total_critical = 0
        
        for resource_type, validation_results in results.items():
            total_errors += len([r for r in validation_results if r.severity == ValidationSeverity.ERROR])
            total_warnings += len([r for r in validation_results if r.severity == ValidationSeverity.WARNING])
            total_critical += len([r for r in validation_results if r.severity == ValidationSeverity.CRITICAL])
        
        health_status = "healthy"
        if total_critical > 0:
            health_status = "critical"
        elif total_errors > 0:
            health_status = "unhealthy"
        elif total_warnings > 0:
            health_status = "warning"
        
        return {
            "status": "success",
            "health_status": health_status,
            "summary": {
                "total_errors": total_errors,
                "total_warnings": total_warnings,
                "total_critical": total_critical,
                "resource_types_checked": len(results)
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in FHIR health check: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/report", summary="Generate FHIR Validation Report")
@api_endpoint_timing("fhir_validation_report")
async def generate_validation_report(
    resource_type: Optional[str] = Query(None, description="Specific resource type to validate"),
    limit: int = Query(100, description="Maximum number of resources to validate per type"),
    include_details: bool = Query(False, description="Include detailed validation results"),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Generate comprehensive FHIR data validation report"""
    try:
        # Rate limiting
        await rate_limiter.check_rate_limit(current_user)
        
        # Run validation
        results = await fhir_validator.validate_all_resources(resource_type, limit)
        
        # Generate report
        report = await fhir_validator.generate_validation_report(results)
        
        # Include detailed results if requested
        if include_details:
            report["detailed_results"] = {}
            for resource_type, validation_results in results.items():
                report["detailed_results"][resource_type] = [
                    {
                        "resource_id": r.resource_id,
                        "severity": r.severity.value,
                        "field": r.field,
                        "message": r.message,
                        "expected_value": r.expected_value,
                        "actual_value": r.actual_value,
                        "timestamp": r.timestamp.isoformat()
                    }
                    for r in validation_results
                ]
        
        return {
            "status": "success",
            "report": report
        }
        
    except Exception as e:
        logger.error(f"Error generating validation report: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/validate-resource", summary="Validate Single FHIR Resource")
@api_endpoint_timing("fhir_validate_single_resource")
async def validate_single_resource(
    resource_data: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Validate a single FHIR resource"""
    try:
        # Rate limiting
        await rate_limiter.check_rate_limit(current_user)
        
        # Get resource type
        resource_type = resource_data.get("resourceType")
        if not resource_type:
            raise HTTPException(status_code=400, detail="Missing resourceType in resource data")
        
        # Validate resource
        results = await fhir_validator.validate_resource(resource_type, resource_data)
        
        # Count issues by severity
        errors = len([r for r in results if r.severity == ValidationSeverity.ERROR])
        warnings = len([r for r in results if r.severity == ValidationSeverity.WARNING])
        critical = len([r for r in results if r.severity == ValidationSeverity.CRITICAL])
        
        return {
            "status": "success",
            "resource_type": resource_type,
            "resource_id": resource_data.get("id"),
            "validation_summary": {
                "total_issues": len(results),
                "errors": errors,
                "warnings": warnings,
                "critical": critical,
                "is_valid": errors == 0 and critical == 0
            },
            "validation_results": [
                {
                    "severity": r.severity.value,
                    "field": r.field,
                    "message": r.message,
                    "expected_value": r.expected_value,
                    "actual_value": r.actual_value
                }
                for r in results
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating single resource: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/data-quality-metrics", summary="Get FHIR Data Quality Metrics")
@api_endpoint_timing("fhir_data_quality_metrics")
async def get_data_quality_metrics(
    resource_type: Optional[str] = Query(None, description="Specific resource type to analyze"),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get data quality metrics for FHIR resources"""
    try:
        # Rate limiting
        await rate_limiter.check_rate_limit(current_user)
        
        from app.services.mongo import mongodb_service
        await mongodb_service.connect()
        db = mongodb_service.get_database('MFC_FHIR_R5')
        
        metrics = {}
        
        if resource_type:
            collections = [resource_type]
        else:
            collections = ["Patient", "Observation", "Device", "Organization", "Location"]
        
        for collection_name in collections:
            try:
                collection = db.get_collection(collection_name)
                
                # Get total count
                total_count = await collection.count_documents({})
                
                # Get recent count (last 24 hours)
                yesterday = datetime.now() - timedelta(days=1)
                recent_count = await collection.count_documents({
                    "meta.lastUpdated": {"$gte": yesterday.isoformat()}
                })
                
                # Get resources with missing required fields
                missing_fields_count = 0
                if collection_name == "Patient":
                    missing_fields_count = await collection.count_documents({
                        "$or": [
                            {"name": {"$exists": False}},
                            {"gender": {"$exists": False}},
                            {"birthDate": {"$exists": False}}
                        ]
                    })
                elif collection_name == "Observation":
                    missing_fields_count = await collection.count_documents({
                        "$or": [
                            {"status": {"$exists": False}},
                            {"code": {"$exists": False}},
                            {"subject": {"$exists": False}}
                        ]
                    })
                
                metrics[collection_name] = {
                    "total_count": total_count,
                    "recent_count_24h": recent_count,
                    "missing_required_fields": missing_fields_count,
                    "completeness_rate": round(((total_count - missing_fields_count) / total_count * 100) if total_count > 0 else 100, 2)
                }
                
            except Exception as e:
                logger.error(f"Error getting metrics for {collection_name}: {e}")
                metrics[collection_name] = {
                    "error": str(e)
                }
        
        return {
            "status": "success",
            "metrics": metrics,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting data quality metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/fix-common-issues", summary="Fix Common FHIR Data Issues")
@api_endpoint_timing("fhir_fix_common_issues")
async def fix_common_issues(
    resource_type: Optional[str] = Query(None, description="Specific resource type to fix"),
    dry_run: bool = Query(True, description="Dry run mode (don't actually fix)"),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Fix common FHIR data issues automatically"""
    try:
        # Rate limiting
        await rate_limiter.check_rate_limit(current_user)
        
        from app.services.mongo import mongodb_service
        await mongodb_service.connect()
        db = mongodb_service.get_database('MFC_FHIR_R5')
        
        fixes_applied = []
        
        if resource_type:
            collections = [resource_type]
        else:
            collections = ["Patient", "Observation", "Device"]
        
        for collection_name in collections:
            try:
                collection = db.get_collection(collection_name)
                
                if collection_name == "Observation":
                    # Fix missing status
                    missing_status = await collection.find({"status": {"$exists": False}}).to_list(length=100)
                    for doc in missing_status:
                        if not dry_run:
                            await collection.update_one(
                                {"_id": doc["_id"]},
                                {"$set": {"status": "final"}}
                            )
                        fixes_applied.append({
                            "resource_type": collection_name,
                            "resource_id": doc.get("id"),
                            "fix": "Added missing status field",
                            "value": "final"
                        })
                    
                    # Fix missing effectiveDateTime
                    missing_date = await collection.find({"effectiveDateTime": {"$exists": False}}).to_list(length=100)
                    for doc in missing_date:
                        if not dry_run:
                            await collection.update_one(
                                {"_id": doc["_id"]},
                                {"$set": {"effectiveDateTime": datetime.now().isoformat()}}
                            )
                        fixes_applied.append({
                            "resource_type": collection_name,
                            "resource_id": doc.get("id"),
                            "fix": "Added missing effectiveDateTime",
                            "value": datetime.now().isoformat()
                        })
                
                elif collection_name == "Patient":
                    # Fix missing gender
                    missing_gender = await collection.find({"gender": {"$exists": False}}).to_list(length=100)
                    for doc in missing_gender:
                        if not dry_run:
                            await collection.update_one(
                                {"_id": doc["_id"]},
                                {"$set": {"gender": "unknown"}}
                            )
                        fixes_applied.append({
                            "resource_type": collection_name,
                            "resource_id": doc.get("id"),
                            "fix": "Added missing gender field",
                            "value": "unknown"
                        })
                
            except Exception as e:
                logger.error(f"Error fixing issues for {collection_name}: {e}")
        
        return {
            "status": "success",
            "dry_run": dry_run,
            "fixes_applied": fixes_applied,
            "total_fixes": len(fixes_applied),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error fixing common issues: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/validation-history", summary="Get Validation History")
@api_endpoint_timing("fhir_validation_history")
async def get_validation_history(
    days: int = Query(7, description="Number of days to look back"),
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get validation history and trends"""
    try:
        # Rate limiting
        await rate_limiter.check_rate_limit(current_user)
        
        from app.services.mongo import mongodb_service
        await mongodb_service.connect()
        db = mongodb_service.get_database('MFC_FHIR_R5')
        
        # This would typically query a validation history collection
        # For now, we'll return a placeholder
        history = {
            "validation_runs": [],
            "trends": {
                "total_errors": [],
                "total_warnings": [],
                "data_quality_score": []
            }
        }
        
        return {
            "status": "success",
            "history": history,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting validation history: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 