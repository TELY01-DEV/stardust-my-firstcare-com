#!/usr/bin/env python3
"""
FHIR Data Quality Testing Script
Comprehensive testing of FHIR data integrity, completeness, and correctness
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.services.mongo import mongodb_service
from app.services.fhir_data_validator import fhir_validator, ValidationSeverity
from app.services.fhir_data_monitor import fhir_monitor

class FHIRDataQualityTester:
    """Comprehensive FHIR data quality testing"""
    
    def __init__(self):
        self.test_results = {
            "timestamp": datetime.now().isoformat(),
            "tests": {},
            "summary": {
                "total_tests": 0,
                "passed": 0,
                "failed": 0,
                "warnings": 0
            }
        }
    
    async def run_all_tests(self):
        """Run all FHIR data quality tests"""
        print("🔍 Starting FHIR Data Quality Testing...")
        print("=" * 60)
        
        try:
            # Connect to MongoDB
            await mongodb_service.connect()
            print("✅ Connected to MongoDB")
            
            # Run all tests
            await self.test_data_existence()
            await self.test_data_completeness()
            await self.test_data_integrity()
            await self.test_data_freshness()
            await self.test_data_consistency()
            await self.test_cross_references()
            await self.test_validation_rules()
            await self.test_data_volume()
            
            # Generate summary
            self.generate_summary()
            
        except Exception as e:
            print(f"❌ Error during testing: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await mongodb_service.disconnect()
    
    async def test_data_existence(self):
        """Test if FHIR data exists in the database"""
        print("\n📊 Test 1: Data Existence")
        print("-" * 30)
        
        test_name = "data_existence"
        self.test_results["tests"][test_name] = {
            "name": "Data Existence Check",
            "status": "unknown",
            "details": {}
        }
        
        try:
            db = mongodb_service.get_database('MFC_FHIR_R5')
            resource_types = ["Patient", "Observation", "Device", "Organization", "Location"]
            
            for resource_type in resource_types:
                collection = db.get_collection(resource_type)
                count = await collection.count_documents({})
                
                self.test_results["tests"][test_name]["details"][resource_type] = {
                    "count": count,
                    "exists": count > 0
                }
                
                status = "✅" if count > 0 else "❌"
                print(f"{status} {resource_type}: {count} records")
            
            # Overall test result
            total_records = sum(detail["count"] for detail in self.test_results["tests"][test_name]["details"].values())
            if total_records > 0:
                self.test_results["tests"][test_name]["status"] = "passed"
                self.test_results["summary"]["passed"] += 1
                print(f"✅ Data existence test PASSED - {total_records} total records found")
            else:
                self.test_results["tests"][test_name]["status"] = "failed"
                self.test_results["summary"]["failed"] += 1
                print("❌ Data existence test FAILED - No records found")
            
        except Exception as e:
            self.test_results["tests"][test_name]["status"] = "failed"
            self.test_results["tests"][test_name]["error"] = str(e)
            self.test_results["summary"]["failed"] += 1
            print(f"❌ Data existence test FAILED - Error: {e}")
        
        self.test_results["summary"]["total_tests"] += 1
    
    async def test_data_completeness(self):
        """Test data completeness (required fields)"""
        print("\n📋 Test 2: Data Completeness")
        print("-" * 30)
        
        test_name = "data_completeness"
        self.test_results["tests"][test_name] = {
            "name": "Data Completeness Check",
            "status": "unknown",
            "details": {}
        }
        
        try:
            db = mongodb_service.get_database('MFC_FHIR_R5')
            
            # Define required fields for each resource type
            required_fields = {
                "Patient": ["name", "gender", "birthDate"],
                "Observation": ["status", "code", "subject", "effectiveDateTime"],
                "Device": ["identifier", "type", "status"],
                "Organization": ["name", "type"]
            }
            
            total_issues = 0
            
            for resource_type, fields in required_fields.items():
                collection = db.get_collection(resource_type)
                total_count = await collection.count_documents({})
                
                if total_count == 0:
                    continue
                
                resource_issues = {}
                
                for field in fields:
                    missing_count = await collection.count_documents({field: {"$exists": False}})
                    missing_rate = (missing_count / total_count) * 100 if total_count > 0 else 0
                    
                    resource_issues[field] = {
                        "missing_count": missing_count,
                        "missing_rate": round(missing_rate, 2),
                        "status": "good" if missing_rate < 10 else "warning" if missing_rate < 50 else "critical"
                    }
                    
                    if missing_rate > 10:
                        total_issues += 1
                
                self.test_results["tests"][test_name]["details"][resource_type] = resource_issues
                
                # Print results
                print(f"\n📁 {resource_type} ({total_count} records):")
                for field, details in resource_issues.items():
                    status_icon = "✅" if details["status"] == "good" else "⚠️" if details["status"] == "warning" else "❌"
                    print(f"  {status_icon} {field}: {details['missing_count']} missing ({details['missing_rate']}%)")
            
            # Overall test result
            if total_issues == 0:
                self.test_results["tests"][test_name]["status"] = "passed"
                self.test_results["summary"]["passed"] += 1
                print(f"\n✅ Data completeness test PASSED - All required fields present")
            elif total_issues <= 3:
                self.test_results["tests"][test_name]["status"] = "warning"
                self.test_results["summary"]["warnings"] += 1
                print(f"\n⚠️ Data completeness test WARNING - {total_issues} issues found")
            else:
                self.test_results["tests"][test_name]["status"] = "failed"
                self.test_results["summary"]["failed"] += 1
                print(f"\n❌ Data completeness test FAILED - {total_issues} critical issues found")
            
        except Exception as e:
            self.test_results["tests"][test_name]["status"] = "failed"
            self.test_results["tests"][test_name]["error"] = str(e)
            self.test_results["summary"]["failed"] += 1
            print(f"❌ Data completeness test FAILED - Error: {e}")
        
        self.test_results["summary"]["total_tests"] += 1
    
    async def test_data_integrity(self):
        """Test data integrity using validation rules"""
        print("\n🔍 Test 3: Data Integrity")
        print("-" * 30)
        
        test_name = "data_integrity"
        self.test_results["tests"][test_name] = {
            "name": "Data Integrity Check",
            "status": "unknown",
            "details": {}
        }
        
        try:
            # Run validation on a sample of data
            validation_results = await fhir_validator.validate_all_resources(limit=100)
            
            total_errors = 0
            total_warnings = 0
            total_critical = 0
            
            for resource_type, results in validation_results.items():
                if not results:
                    continue
                
                error_count = len([r for r in results if r.severity == ValidationSeverity.ERROR])
                warning_count = len([r for r in results if r.severity == ValidationSeverity.WARNING])
                critical_count = len([r for r in results if r.severity == ValidationSeverity.CRITICAL])
                total_count = len(results)
                
                total_errors += error_count
                total_warnings += warning_count
                total_critical += critical_count
                
                self.test_results["tests"][test_name]["details"][resource_type] = {
                    "total_validated": total_count,
                    "errors": error_count,
                    "warnings": warning_count,
                    "critical": critical_count,
                    "error_rate": round((error_count / total_count) * 100, 2) if total_count > 0 else 0
                }
                
                # Print results
                status_icon = "✅" if error_count == 0 and critical_count == 0 else "⚠️" if error_count < 5 else "❌"
                print(f"{status_icon} {resource_type}: {error_count} errors, {warning_count} warnings, {critical_count} critical")
            
            # Overall test result
            if total_critical > 0:
                self.test_results["tests"][test_name]["status"] = "failed"
                self.test_results["summary"]["failed"] += 1
                print(f"\n❌ Data integrity test FAILED - {total_critical} critical issues found")
            elif total_errors > 0:
                self.test_results["tests"][test_name]["status"] = "warning"
                self.test_results["summary"]["warnings"] += 1
                print(f"\n⚠️ Data integrity test WARNING - {total_errors} errors found")
            else:
                self.test_results["tests"][test_name]["status"] = "passed"
                self.test_results["summary"]["passed"] += 1
                print(f"\n✅ Data integrity test PASSED - No critical issues found")
            
        except Exception as e:
            self.test_results["tests"][test_name]["status"] = "failed"
            self.test_results["tests"][test_name]["error"] = str(e)
            self.test_results["summary"]["failed"] += 1
            print(f"❌ Data integrity test FAILED - Error: {e}")
        
        self.test_results["summary"]["total_tests"] += 1
    
    async def test_data_freshness(self):
        """Test data freshness (recent updates)"""
        print("\n🕒 Test 4: Data Freshness")
        print("-" * 30)
        
        test_name = "data_freshness"
        self.test_results["tests"][test_name] = {
            "name": "Data Freshness Check",
            "status": "unknown",
            "details": {}
        }
        
        try:
            db = mongodb_service.get_database('MFC_FHIR_R5')
            resource_types = ["Patient", "Observation", "Device", "Organization"]
            
            cutoff_time = datetime.now() - timedelta(hours=24)
            total_stale = 0
            
            for resource_type in resource_types:
                collection = db.get_collection(resource_type)
                total_count = await collection.count_documents({})
                
                if total_count == 0:
                    continue
                
                recent_count = await collection.count_documents({
                    "meta.lastUpdated": {"$gte": cutoff_time.isoformat()}
                })
                
                stale_count = total_count - recent_count
                stale_rate = (stale_count / total_count) * 100 if total_count > 0 else 0
                
                self.test_results["tests"][test_name]["details"][resource_type] = {
                    "total_count": total_count,
                    "recent_count": recent_count,
                    "stale_count": stale_count,
                    "stale_rate": round(stale_rate, 2)
                }
                
                status_icon = "✅" if stale_rate < 50 else "⚠️" if stale_rate < 90 else "❌"
                print(f"{status_icon} {resource_type}: {recent_count}/{total_count} recent ({stale_rate}% stale)")
                
                if stale_rate > 90:
                    total_stale += 1
            
            # Overall test result
            if total_stale == 0:
                self.test_results["tests"][test_name]["status"] = "passed"
                self.test_results["summary"]["passed"] += 1
                print(f"\n✅ Data freshness test PASSED - All data is recent")
            elif total_stale <= 2:
                self.test_results["tests"][test_name]["status"] = "warning"
                self.test_results["summary"]["warnings"] += 1
                print(f"\n⚠️ Data freshness test WARNING - {total_stale} resource types are stale")
            else:
                self.test_results["tests"][test_name]["status"] = "failed"
                self.test_results["summary"]["failed"] += 1
                print(f"\n❌ Data freshness test FAILED - {total_stale} resource types are stale")
            
        except Exception as e:
            self.test_results["tests"][test_name]["status"] = "failed"
            self.test_results["tests"][test_name]["error"] = str(e)
            self.test_results["summary"]["failed"] += 1
            print(f"❌ Data freshness test FAILED - Error: {e}")
        
        self.test_results["summary"]["total_tests"] += 1
    
    async def test_data_consistency(self):
        """Test data consistency across resources"""
        print("\n🔄 Test 5: Data Consistency")
        print("-" * 30)
        
        test_name = "data_consistency"
        self.test_results["tests"][test_name] = {
            "name": "Data Consistency Check",
            "status": "unknown",
            "details": {}
        }
        
        try:
            db = mongodb_service.get_database('MFC_FHIR_R5')
            
            # Check for orphaned observations (no patient reference)
            observation_collection = db.get_collection("Observation")
            patient_collection = db.get_collection("Patient")
            
            # Get all patient IDs
            patient_ids = set()
            async for patient in patient_collection.find({}, {"id": 1}):
                patient_ids.add(patient.get("id"))
            
            # Check observations with invalid patient references
            orphaned_count = 0
            async for observation in observation_collection.find({"subject.reference": {"$exists": True}}):
                subject_ref = observation.get("subject", {}).get("reference", "")
                if subject_ref.startswith("Patient/"):
                    patient_id = subject_ref.replace("Patient/", "")
                    if patient_id not in patient_ids:
                        orphaned_count += 1
            
            self.test_results["tests"][test_name]["details"]["orphaned_observations"] = {
                "count": orphaned_count,
                "status": "good" if orphaned_count == 0 else "critical"
            }
            
            status_icon = "✅" if orphaned_count == 0 else "❌"
            print(f"{status_icon} Orphaned observations: {orphaned_count}")
            
            # Overall test result
            if orphaned_count == 0:
                self.test_results["tests"][test_name]["status"] = "passed"
                self.test_results["summary"]["passed"] += 1
                print(f"\n✅ Data consistency test PASSED - No orphaned records found")
            else:
                self.test_results["tests"][test_name]["status"] = "failed"
                self.test_results["summary"]["failed"] += 1
                print(f"\n❌ Data consistency test FAILED - {orphaned_count} orphaned observations found")
            
        except Exception as e:
            self.test_results["tests"][test_name]["status"] = "failed"
            self.test_results["tests"][test_name]["error"] = str(e)
            self.test_results["summary"]["failed"] += 1
            print(f"❌ Data consistency test FAILED - Error: {e}")
        
        self.test_results["summary"]["total_tests"] += 1
    
    async def test_cross_references(self):
        """Test cross-references between resources"""
        print("\n🔗 Test 6: Cross-References")
        print("-" * 30)
        
        test_name = "cross_references"
        self.test_results["tests"][test_name] = {
            "name": "Cross-Reference Check",
            "status": "unknown",
            "details": {}
        }
        
        try:
            db = mongodb_service.get_database('MFC_FHIR_R5')
            
            # Check observation references
            observation_collection = db.get_collection("Observation")
            
            invalid_refs = 0
            total_refs = 0
            
            async for observation in observation_collection.find({"subject.reference": {"$exists": True}}):
                total_refs += 1
                subject_ref = observation.get("subject", {}).get("reference", "")
                
                if not subject_ref.startswith("Patient/"):
                    invalid_refs += 1
            
            self.test_results["tests"][test_name]["details"]["observation_references"] = {
                "total": total_refs,
                "invalid": invalid_refs,
                "valid_rate": round(((total_refs - invalid_refs) / total_refs) * 100, 2) if total_refs > 0 else 100
            }
            
            status_icon = "✅" if invalid_refs == 0 else "❌"
            print(f"{status_icon} Observation references: {total_refs - invalid_refs}/{total_refs} valid")
            
            # Overall test result
            if invalid_refs == 0:
                self.test_results["tests"][test_name]["status"] = "passed"
                self.test_results["summary"]["passed"] += 1
                print(f"\n✅ Cross-reference test PASSED - All references are valid")
            else:
                self.test_results["tests"][test_name]["status"] = "failed"
                self.test_results["summary"]["failed"] += 1
                print(f"\n❌ Cross-reference test FAILED - {invalid_refs} invalid references found")
            
        except Exception as e:
            self.test_results["tests"][test_name]["status"] = "failed"
            self.test_results["tests"][test_name]["error"] = str(e)
            self.test_results["summary"]["failed"] += 1
            print(f"❌ Cross-reference test FAILED - Error: {e}")
        
        self.test_results["summary"]["total_tests"] += 1
    
    async def test_validation_rules(self):
        """Test specific validation rules"""
        print("\n📏 Test 7: Validation Rules")
        print("-" * 30)
        
        test_name = "validation_rules"
        self.test_results["tests"][test_name] = {
            "name": "Validation Rules Check",
            "status": "unknown",
            "details": {}
        }
        
        try:
            db = mongodb_service.get_database('MFC_FHIR_R5')
            
            # Test observation status values
            observation_collection = db.get_collection("Observation")
            valid_statuses = ["registered", "preliminary", "final", "amended", "corrected", "cancelled", "entered-in-error", "unknown"]
            
            invalid_status_count = 0
            total_observations = 0
            
            async for observation in observation_collection.find({"status": {"$exists": True}}):
                total_observations += 1
                status = observation.get("status")
                if status not in valid_statuses:
                    invalid_status_count += 1
            
            self.test_results["tests"][test_name]["details"]["observation_status"] = {
                "total": total_observations,
                "invalid": invalid_status_count,
                "valid_rate": round(((total_observations - invalid_status_count) / total_observations) * 100, 2) if total_observations > 0 else 100
            }
            
            status_icon = "✅" if invalid_status_count == 0 else "❌"
            print(f"{status_icon} Observation status values: {total_observations - invalid_status_count}/{total_observations} valid")
            
            # Overall test result
            if invalid_status_count == 0:
                self.test_results["tests"][test_name]["status"] = "passed"
                self.test_results["summary"]["passed"] += 1
                print(f"\n✅ Validation rules test PASSED - All values are valid")
            else:
                self.test_results["tests"][test_name]["status"] = "failed"
                self.test_results["summary"]["failed"] += 1
                print(f"\n❌ Validation rules test FAILED - {invalid_status_count} invalid values found")
            
        except Exception as e:
            self.test_results["tests"][test_name]["status"] = "failed"
            self.test_results["tests"][test_name]["error"] = str(e)
            self.test_results["summary"]["failed"] += 1
            print(f"❌ Validation rules test FAILED - Error: {e}")
        
        self.test_results["summary"]["total_tests"] += 1
    
    async def test_data_volume(self):
        """Test data volume patterns"""
        print("\n📈 Test 8: Data Volume")
        print("-" * 30)
        
        test_name = "data_volume"
        self.test_results["tests"][test_name] = {
            "name": "Data Volume Check",
            "status": "unknown",
            "details": {}
        }
        
        try:
            db = mongodb_service.get_database('MFC_FHIR_R5')
            resource_types = ["Patient", "Observation", "Device"]
            
            now = datetime.now()
            last_hour = now - timedelta(hours=1)
            two_hours_ago = now - timedelta(hours=2)
            
            volume_issues = 0
            
            for resource_type in resource_types:
                collection = db.get_collection(resource_type)
                
                recent_count = await collection.count_documents({
                    "meta.lastUpdated": {"$gte": last_hour.isoformat()}
                })
                
                previous_count = await collection.count_documents({
                    "meta.lastUpdated": {
                        "$gte": two_hours_ago.isoformat(),
                        "$lt": last_hour.isoformat()
                    }
                })
                
                self.test_results["tests"][test_name]["details"][resource_type] = {
                    "recent_hour": recent_count,
                    "previous_hour": previous_count,
                    "change_percentage": round(((recent_count - previous_count) / previous_count) * 100, 2) if previous_count > 0 else 0
                }
                
                # Check for significant drop (more than 50% reduction)
                if previous_count > 10 and recent_count < previous_count * 0.5:
                    volume_issues += 1
                    status_icon = "❌"
                else:
                    status_icon = "✅"
                
                print(f"{status_icon} {resource_type}: {recent_count} (last hour) vs {previous_count} (previous hour)")
            
            # Overall test result
            if volume_issues == 0:
                self.test_results["tests"][test_name]["status"] = "passed"
                self.test_results["summary"]["passed"] += 1
                print(f"\n✅ Data volume test PASSED - No significant drops detected")
            else:
                self.test_results["tests"][test_name]["status"] = "warning"
                self.test_results["summary"]["warnings"] += 1
                print(f"\n⚠️ Data volume test WARNING - {volume_issues} resource types show volume drops")
            
        except Exception as e:
            self.test_results["tests"][test_name]["status"] = "failed"
            self.test_results["tests"][test_name]["error"] = str(e)
            self.test_results["summary"]["failed"] += 1
            print(f"❌ Data volume test FAILED - Error: {e}")
        
        self.test_results["summary"]["total_tests"] += 1
    
    def generate_summary(self):
        """Generate test summary"""
        print("\n" + "=" * 60)
        print("📊 FHIR Data Quality Test Summary")
        print("=" * 60)
        
        summary = self.test_results["summary"]
        
        print(f"Total Tests: {summary['total_tests']}")
        print(f"✅ Passed: {summary['passed']}")
        print(f"⚠️ Warnings: {summary['warnings']}")
        print(f"❌ Failed: {summary['failed']}")
        
        # Calculate overall score
        if summary['total_tests'] > 0:
            score = (summary['passed'] / summary['total_tests']) * 100
            print(f"\nOverall Score: {score:.1f}%")
            
            if score >= 90:
                print("🎉 Excellent data quality!")
            elif score >= 75:
                print("👍 Good data quality with minor issues")
            elif score >= 60:
                print("⚠️ Moderate data quality issues detected")
            else:
                print("🚨 Critical data quality issues detected")
        
        # Print detailed results
        print(f"\n📋 Detailed Results:")
        for test_name, test_result in self.test_results["tests"].items():
            status_icon = {
                "passed": "✅",
                "warning": "⚠️",
                "failed": "❌",
                "unknown": "❓"
            }.get(test_result["status"], "❓")
            
            print(f"{status_icon} {test_result['name']}: {test_result['status'].upper()}")
        
        # Save results to file
        import json
        with open("fhir_data_quality_report.json", "w") as f:
            json.dump(self.test_results, f, indent=2, default=str)
        
        print(f"\n📄 Detailed report saved to: fhir_data_quality_report.json")

async def main():
    """Main function"""
    tester = FHIRDataQualityTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main()) 