import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass, asdict
import uuid

from app.services.analytics import healthcare_analytics
from app.services.mongo import mongodb_service
from app.utils.structured_logging import get_logger
from app.utils.json_encoder import MongoJSONEncoder
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import io
import base64

logger = get_logger(__name__)

class ReportType(Enum):
    """Types of reports that can be generated"""
    DAILY_SUMMARY = "daily_summary"
    WEEKLY_ANALYTICS = "weekly_analytics"
    MONTHLY_OVERVIEW = "monthly_overview"
    PATIENT_REPORT = "patient_report"
    HOSPITAL_PERFORMANCE = "hospital_performance"
    DEVICE_UTILIZATION = "device_utilization"
    RISK_ASSESSMENT = "risk_assessment"
    ANOMALY_ALERT = "anomaly_alert"
    SYSTEM_HEALTH = "system_health"

class ReportFormat(Enum):
    """Report output formats"""
    JSON = "json"
    HTML = "html"
    PDF = "pdf"
    CSV = "csv"
    EXCEL = "excel"

class ReportFrequency(Enum):
    """Report generation frequencies"""
    ONCE = "once"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"

@dataclass
class ReportTemplate:
    """Report template configuration"""
    id: str
    name: str
    description: str
    type: ReportType
    format: ReportFormat
    frequency: ReportFrequency
    recipients: List[str]  # Email addresses
    filters: Dict[str, Any]  # hospital_id, patient_id, etc.
    template_config: Dict[str, Any]  # Specific configuration
    active: bool = True
    created_at: datetime = None
    updated_at: datetime = None
    last_generated: datetime = None
    next_generation: datetime = None

@dataclass
class ReportJob:
    """Report generation job"""
    id: str
    template_id: str
    status: str  # pending, running, completed, failed
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    output_path: Optional[str] = None
    output_size: Optional[int] = None

class ReportingEngine:
    """Automated reporting engine with scheduling capabilities"""
    
    def __init__(self):
        self.collection_templates = "report_templates"
        self.collection_jobs = "report_jobs"
        self.collection_outputs = "report_outputs"
        self.running_jobs = {}
        
        # Email configuration (from environment or config)
        self.smtp_server = "smtp.gmail.com"  # Configure as needed
        self.smtp_port = 587
        self.email_user = None  # Set from config
        self.email_password = None  # Set from config
        
    async def create_template(self, template_data: Dict[str, Any]) -> str:
        """Create a new report template"""
        try:
            template = ReportTemplate(
                id=str(uuid.uuid4()),
                name=template_data["name"],
                description=template_data.get("description", ""),
                type=ReportType(template_data["type"]),
                format=ReportFormat(template_data["format"]),
                frequency=ReportFrequency(template_data["frequency"]),
                recipients=template_data.get("recipients", []),
                filters=template_data.get("filters", {}),
                template_config=template_data.get("template_config", {}),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            # Calculate next generation time
            template.next_generation = self._calculate_next_generation(
                template.frequency, datetime.utcnow()
            )
            
            # Save to database
            collection = mongodb_service.get_fhir_collection(self.collection_templates)
            await collection.insert_one(asdict(template))
            
            logger.info(f"Created report template: {template.name} ({template.id})")
            return template.id
            
        except Exception as e:
            logger.error(f"Error creating report template: {str(e)}")
            raise

    async def update_template(self, template_id: str, updates: Dict[str, Any]) -> bool:
        """Update an existing report template"""
        try:
            collection = mongodb_service.get_fhir_collection(self.collection_templates)
            
            # Add update timestamp
            updates["updated_at"] = datetime.utcnow()
            
            # Recalculate next generation if frequency changed
            if "frequency" in updates:
                updates["next_generation"] = self._calculate_next_generation(
                    ReportFrequency(updates["frequency"]), datetime.utcnow()
                )
            
            result = await collection.update_one(
                {"id": template_id},
                {"$set": updates}
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Error updating report template: {str(e)}")
            return False

    async def delete_template(self, template_id: str) -> bool:
        """Delete a report template"""
        try:
            collection = mongodb_service.get_fhir_collection(self.collection_templates)
            result = await collection.delete_one({"id": template_id})
            return result.deleted_count > 0
            
        except Exception as e:
            logger.error(f"Error deleting report template: {str(e)}")
            return False

    async def list_templates(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """List all report templates"""
        try:
            collection = mongodb_service.get_fhir_collection(self.collection_templates)
            filter_query = {"active": True} if active_only else {}
            
            templates = await collection.find(filter_query).to_list(None)
            return templates
            
        except Exception as e:
            logger.error(f"Error listing report templates: {str(e)}")
            return []

    async def generate_report_now(self, template_id: str) -> str:
        """Generate a report immediately"""
        try:
            # Get template
            collection = mongodb_service.get_fhir_collection(self.collection_templates)
            template_doc = await collection.find_one({"id": template_id})
            
            if not template_doc:
                raise ValueError(f"Template not found: {template_id}")
            
            template = ReportTemplate(**template_doc)
            
            # Create job
            job = ReportJob(
                id=str(uuid.uuid4()),
                template_id=template_id,
                status="pending",
                created_at=datetime.utcnow()
            )
            
            # Save job
            jobs_collection = mongodb_service.get_collection(self.collection_jobs)
            await jobs_collection.insert_one(asdict(job))
            
            # Start generation
            asyncio.create_task(self._execute_report_job(job, template))
            
            return job.id
            
        except Exception as e:
            logger.error(f"Error generating report: {str(e)}")
            raise

    async def _execute_report_job(self, job: ReportJob, template: ReportTemplate):
        """Execute a report generation job"""
        try:
            # Update job status
            await self._update_job_status(job.id, "running", started_at=datetime.utcnow())
            
            # Generate report data
            report_data = await self._generate_report_data(template)
            
            # Format report
            formatted_report = await self._format_report(report_data, template)
            
            # Save output
            output_path = await self._save_report_output(job.id, formatted_report, template.format)
            
            # Send email if recipients configured
            if template.recipients:
                await self._send_report_email(template, formatted_report, output_path)
            
            # Update job completion
            await self._update_job_status(
                job.id, "completed", 
                completed_at=datetime.utcnow(),
                output_path=output_path,
                output_size=len(formatted_report) if isinstance(formatted_report, str) else 0
            )
            
            # Update template last generated time
            await self._update_template_generation_time(template.id, datetime.utcnow())
            
            logger.info(f"Report job completed: {job.id}")
            
        except Exception as e:
            logger.error(f"Error executing report job {job.id}: {str(e)}")
            await self._update_job_status(job.id, "failed", error_message=str(e))

    async def _generate_report_data(self, template: ReportTemplate) -> Dict[str, Any]:
        """Generate the data for a report based on template type"""
        try:
            report_data = {
                "metadata": {
                    "report_type": template.type.value,
                    "generated_at": datetime.utcnow().isoformat(),
                    "template_id": template.id,
                    "template_name": template.name,
                    "filters": template.filters
                }
            }
            
            if template.type == ReportType.DAILY_SUMMARY:
                # Daily summary report
                yesterday = datetime.utcnow() - timedelta(days=1)
                
                patient_stats = await healthcare_analytics.get_patient_statistics(
                    hospital_id=template.filters.get("hospital_id"),
                    start_date=yesterday,
                    end_date=datetime.utcnow()
                )
                
                device_stats = await healthcare_analytics.get_device_utilization_analytics(
                    hospital_id=template.filters.get("hospital_id"),
                    period="daily"
                )
                
                report_data.update({
                    "summary": {
                        "date": yesterday.strftime("%Y-%m-%d"),
                        "new_patients": patient_stats["summary"]["new_patients"],
                        "active_patients": patient_stats["summary"]["active_patients"],
                        "high_risk_patients": patient_stats["risk_analysis"]["high_risk_count"]
                    },
                    "patient_statistics": patient_stats,
                    "device_utilization": device_stats
                })
                
            elif template.type == ReportType.WEEKLY_ANALYTICS:
                # Weekly analytics report
                week_start = datetime.utcnow() - timedelta(days=7)
                
                patient_stats = await healthcare_analytics.get_patient_statistics(
                    hospital_id=template.filters.get("hospital_id"),
                    start_date=week_start,
                    end_date=datetime.utcnow()
                )
                
                # Get anomalies for the week
                anomalies = await healthcare_analytics.detect_vital_anomalies(
                    hospital_id=template.filters.get("hospital_id"),
                    start_date=week_start,
                    end_date=datetime.utcnow()
                )
                
                report_data.update({
                    "period": {
                        "start": week_start.strftime("%Y-%m-%d"),
                        "end": datetime.utcnow().strftime("%Y-%m-%d")
                    },
                    "patient_analytics": patient_stats,
                    "anomalies": {
                        "count": len(anomalies),
                        "by_severity": self._group_anomalies_by_severity(anomalies),
                        "details": anomalies[:10]  # Top 10 anomalies
                    }
                })
                
            elif template.type == ReportType.PATIENT_REPORT:
                # Individual patient report
                patient_id = template.filters.get("patient_id")
                if not patient_id:
                    raise ValueError("Patient ID required for patient report")
                
                # Get patient info
                patients_collection = mongodb_service.get_collection("patients")
                patient = await patients_collection.find_one({"_id": patient_id})
                
                # Get vital signs analytics
                vitals_analytics = await healthcare_analytics.get_vital_signs_analytics(
                    patient_id=patient_id,
                    period="weekly"
                )
                
                # Get risk predictions
                risk_data = await healthcare_analytics.predict_health_risks(patient_id)
                
                # Get recommendations
                recommendations = await healthcare_analytics.get_health_recommendations(
                    patient_id, risk_data.get("risk_factors", [])
                )
                
                report_data.update({
                    "patient": {
                        "id": patient_id,
                        "name": f"{patient.get('first_name', '')} {patient.get('last_name', '')}".strip(),
                        "age": patient.get("age"),
                        "gender": patient.get("gender")
                    },
                    "vital_signs": vitals_analytics,
                    "risk_assessment": risk_data,
                    "recommendations": recommendations
                })
                
            elif template.type == ReportType.HOSPITAL_PERFORMANCE:
                # Hospital performance report
                hospital_id = template.filters.get("hospital_id")
                
                hospital_report = await healthcare_analytics._generate_hospital_report(
                    hospital_id=hospital_id,
                    start_date=datetime.utcnow() - timedelta(days=30),
                    end_date=datetime.utcnow()
                )
                
                report_data.update({
                    "hospital_performance": hospital_report
                })
                
            elif template.type == ReportType.RISK_ASSESSMENT:
                # Risk assessment report
                risk_report = await healthcare_analytics._generate_health_risk_report(
                    hospital_id=template.filters.get("hospital_id"),
                    start_date=datetime.utcnow() - timedelta(days=30),
                    end_date=datetime.utcnow()
                )
                
                report_data.update({
                    "risk_assessment": risk_report
                })
                
            elif template.type == ReportType.SYSTEM_HEALTH:
                # System health report
                # This would include database stats, performance metrics, etc.
                report_data.update({
                    "system_health": {
                        "database_status": "healthy",  # Mock data
                        "cache_status": "healthy",
                        "api_performance": {
                            "average_response_time": "125ms",
                            "error_rate": "0.2%"
                        },
                        "active_connections": 45,
                        "memory_usage": "78%",
                        "disk_usage": "45%"
                    }
                })
            
            return report_data
            
        except Exception as e:
            logger.error(f"Error generating report data: {str(e)}")
            raise

    async def _format_report(self, data: Dict[str, Any], template: ReportTemplate) -> str:
        """Format report data according to the specified format"""
        try:
            if template.format == ReportFormat.JSON:
                return json.dumps(data, cls=MongoJSONEncoder, indent=2)
                
            elif template.format == ReportFormat.HTML:
                return self._generate_html_report(data, template)
                
            elif template.format == ReportFormat.CSV:
                return self._generate_csv_report(data, template)
                
            else:
                # Default to JSON for unsupported formats
                return json.dumps(data, cls=MongoJSONEncoder, indent=2)
                
        except Exception as e:
            logger.error(f"Error formatting report: {str(e)}")
            raise

    def _generate_html_report(self, data: Dict[str, Any], template: ReportTemplate) -> str:
        """Generate HTML formatted report"""
        metadata = data.get("metadata", {})
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{template.name} - {metadata.get('generated_at', '')}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background-color: #f0f0f0; padding: 20px; border-radius: 5px; }}
                .section {{ margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }}
                .metric {{ display: inline-block; margin: 10px; padding: 10px; background-color: #e9f4ff; border-radius: 3px; }}
                .risk-low {{ color: #4CAF50; }}
                .risk-medium {{ color: #FFC107; }}
                .risk-high {{ color: #FF9800; }}
                .risk-critical {{ color: #F44336; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>{template.name}</h1>
                <p>Generated: {metadata.get('generated_at', '')}</p>
                <p>Report Type: {metadata.get('report_type', '').replace('_', ' ').title()}</p>
            </div>
        """
        
        # Add content based on report type
        if template.type == ReportType.DAILY_SUMMARY:
            summary = data.get("summary", {})
            html += f"""
            <div class="section">
                <h2>Daily Summary - {summary.get('date', '')}</h2>
                <div class="metric">New Patients: <strong>{summary.get('new_patients', 0)}</strong></div>
                <div class="metric">Active Patients: <strong>{summary.get('active_patients', 0)}</strong></div>
                <div class="metric">High Risk Patients: <strong>{summary.get('high_risk_patients', 0)}</strong></div>
            </div>
            """
            
        elif template.type == ReportType.PATIENT_REPORT:
            patient = data.get("patient", {})
            risk_assessment = data.get("risk_assessment", {})
            html += f"""
            <div class="section">
                <h2>Patient Information</h2>
                <p><strong>Name:</strong> {patient.get('name', 'N/A')}</p>
                <p><strong>Age:</strong> {patient.get('age', 'N/A')}</p>
                <p><strong>Gender:</strong> {patient.get('gender', 'N/A')}</p>
            </div>
            <div class="section">
                <h2>Risk Assessment</h2>
                <p><strong>Risk Score:</strong> {risk_assessment.get('risk_score', 0):.1%}</p>
                <p><strong>Risk Factors:</strong> {', '.join(risk_assessment.get('risk_factors', []))}</p>
            </div>
            """
        
        html += """
        </body>
        </html>
        """
        
        return html

    def _generate_csv_report(self, data: Dict[str, Any], template: ReportTemplate) -> str:
        """Generate CSV formatted report"""
        # Simple CSV generation - in production, use pandas or csv module
        lines = []
        
        # Add metadata
        metadata = data.get("metadata", {})
        lines.append(f"Report Name,{template.name}")
        lines.append(f"Generated At,{metadata.get('generated_at', '')}")
        lines.append(f"Report Type,{metadata.get('report_type', '')}")
        lines.append("")  # Empty line
        
        # Add data based on report type
        if template.type == ReportType.DAILY_SUMMARY:
            summary = data.get("summary", {})
            lines.append("Metric,Value")
            lines.append(f"Date,{summary.get('date', '')}")
            lines.append(f"New Patients,{summary.get('new_patients', 0)}")
            lines.append(f"Active Patients,{summary.get('active_patients', 0)}")
            lines.append(f"High Risk Patients,{summary.get('high_risk_patients', 0)}")
            
        return "\n".join(lines)

    async def _save_report_output(self, job_id: str, content: str, format: ReportFormat) -> str:
        """Save report output to database"""
        try:
            output_doc = {
                "job_id": job_id,
                "content": content,
                "format": format.value,
                "size": len(content),
                "created_at": datetime.utcnow(),
                "expires_at": datetime.utcnow() + timedelta(days=30)  # Auto-cleanup after 30 days
            }
            
            collection = mongodb_service.get_fhir_collection(self.collection_outputs)
            result = await collection.insert_one(output_doc)
            
            return str(result.inserted_id)
            
        except Exception as e:
            logger.error(f"Error saving report output: {str(e)}")
            raise

    async def _send_report_email(self, template: ReportTemplate, content: str, output_path: str):
        """Send report via email"""
        try:
            if not self.email_user or not self.email_password:
                logger.warning("Email configuration not set, skipping email send")
                return
            
            msg = MimeMultipart()
            msg['From'] = self.email_user
            msg['To'] = ", ".join(template.recipients)
            msg['Subject'] = f"Automated Report: {template.name}"
            
            # Email body
            body = f"""
            Dear Recipient,
            
            Please find attached the automated report: {template.name}
            
            Report Type: {template.type.value.replace('_', ' ').title()}
            Generated At: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}
            
            This is an automated message from the My FirstCare Analytics System.
            
            Best regards,
            Analytics Team
            """
            
            msg.attach(MimeText(body, 'plain'))
            
            # Attach report
            if template.format == ReportFormat.HTML:
                attachment = MimeText(content, 'html')
                attachment.add_header('Content-Disposition', f'attachment; filename="{template.name}.html"')
            else:
                attachment = MimeText(content, 'plain')
                attachment.add_header('Content-Disposition', f'attachment; filename="{template.name}.{template.format.value}"')
            
            msg.attach(attachment)
            
            # Send email
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.email_user, self.email_password)
            server.send_message(msg)
            server.quit()
            
            logger.info(f"Report email sent for template: {template.name}")
            
        except Exception as e:
            logger.error(f"Error sending report email: {str(e)}")

    async def _update_job_status(self, job_id: str, status: str, **kwargs):
        """Update job status in database"""
        try:
            collection = mongodb_service.get_fhir_collection(self.collection_jobs)
            update_data = {"status": status, **kwargs}
            
            await collection.update_one(
                {"id": job_id},
                {"$set": update_data}
            )
            
        except Exception as e:
            logger.error(f"Error updating job status: {str(e)}")

    async def _update_template_generation_time(self, template_id: str, generated_at: datetime):
        """Update template last generation time and calculate next generation"""
        try:
            collection = mongodb_service.get_fhir_collection(self.collection_templates)
            template_doc = await collection.find_one({"id": template_id})
            
            if template_doc:
                frequency = ReportFrequency(template_doc["frequency"])
                next_generation = self._calculate_next_generation(frequency, generated_at)
                
                await collection.update_one(
                    {"id": template_id},
                    {"$set": {
                        "last_generated": generated_at,
                        "next_generation": next_generation
                    }}
                )
                
        except Exception as e:
            logger.error(f"Error updating template generation time: {str(e)}")

    def _calculate_next_generation(self, frequency: ReportFrequency, current_time: datetime) -> Optional[datetime]:
        """Calculate next generation time based on frequency"""
        if frequency == ReportFrequency.ONCE:
            return None
        elif frequency == ReportFrequency.DAILY:
            return current_time + timedelta(days=1)
        elif frequency == ReportFrequency.WEEKLY:
            return current_time + timedelta(weeks=1)
        elif frequency == ReportFrequency.MONTHLY:
            return current_time + timedelta(days=30)
        elif frequency == ReportFrequency.QUARTERLY:
            return current_time + timedelta(days=90)
        else:
            return None

    def _group_anomalies_by_severity(self, anomalies: List[Dict]) -> Dict[str, int]:
        """Group anomalies by severity level"""
        severity_counts = {"medium": 0, "high": 0, "critical": 0}
        
        for anomaly in anomalies:
            severity = anomaly.get("severity", "medium")
            if severity in severity_counts:
                severity_counts[severity] += 1
        
        return severity_counts

    async def check_scheduled_reports(self):
        """Check for reports that need to be generated (called by scheduler)"""
        try:
            # Use FHIR database for report templates to avoid authorization issues
            collection = mongodb_service.get_fhir_collection(self.collection_templates)
            now = datetime.utcnow()
            
            # Find templates ready for generation
            templates = await collection.find({
                "active": True,
                "frequency": {"$ne": "once"},
                "next_generation": {"$lte": now}
            }).to_list(None)
            
            for template_doc in templates:
                template = ReportTemplate(**template_doc)
                logger.info(f"Generating scheduled report: {template.name}")
                await self.generate_report_now(template.id)
                
        except Exception as e:
            logger.error(f"Error checking scheduled reports: {str(e)}")

    async def get_report_jobs(self, template_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Get report generation jobs"""
        try:
            collection = mongodb_service.get_fhir_collection(self.collection_jobs)
            
            filter_query = {}
            if template_id:
                filter_query["template_id"] = template_id
            
            jobs = await collection.find(filter_query).sort("created_at", -1).limit(limit).to_list(None)
            return jobs
            
        except Exception as e:
            logger.error(f"Error getting report jobs: {str(e)}")
            return []

    async def get_report_output(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get report output by job ID"""
        try:
            collection = mongodb_service.get_fhir_collection(self.collection_outputs)
            output = await collection.find_one({"job_id": job_id})
            return output
            
        except Exception as e:
            logger.error(f"Error getting report output: {str(e)}")
            return None

# Global reporting engine instance
reporting_engine = ReportingEngine() 