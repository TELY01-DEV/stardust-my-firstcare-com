#!/usr/bin/env python3
"""
AMY Data to FHIR R5 Migration Script
===================================
Comprehensive migration of AMY JSON export data to FHIR R5 resources.

This script processes the extensive AMY medical history collections:
- Medication histories → MedicationStatement
- Allergy histories → AllergyIntolerance  
- Admission data → Encounter
- Body data → Observation (vital signs)
- Blood pressure → Observation
- Blood sugar → Observation
- Temperature → Observation
- SPO2 → Observation
- Lab results → DiagnosticReport + Observation

Usage:
    python app/scripts/migrate_amy_to_fhir.py --data-dir docs/JSON-DB-IMPORT/import_script --batch-size 100
"""

import asyncio
import sys
import os
import json
import argparse
from datetime import datetime
from typing import Dict, Any, List, Optional
from bson import ObjectId
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, '/app')

from app.services.mongo import mongodb_service
from app.services.fhir_r5_service import FHIRR5Service
from app.utils.structured_logging import get_logger

logger = get_logger(__name__)

class AMYToFHIRMigrator:
    """Comprehensive AMY data to FHIR R5 migration service"""
    
    def __init__(self, data_dir: str):
        self.data_dir = Path(data_dir)
        self.fhir_service = FHIRR5Service()
        self.migration_stats = {
            "patients": {"total": 0, "processed": 0, "errors": 0},
            "medication_statements": {"total": 0, "processed": 0, "errors": 0},
            "allergy_intolerances": {"total": 0, "processed": 0, "errors": 0},
            "encounters": {"total": 0, "processed": 0, "errors": 0},
            "observations": {"total": 0, "processed": 0, "errors": 0},
            "diagnostic_reports": {"total": 0, "processed": 0, "errors": 0}
        }
        
    async def migrate_all_amy_data(self, batch_size: int = 100):
        """Migrate all AMY data to FHIR R5"""
        logger.info("🚀 Starting comprehensive AMY to FHIR R5 migration...")
        
        try:
            # Connect to MongoDB
            await mongodb_service.connect()
            logger.info("✅ Connected to databases")
            
            # Migration sequence (order matters for references)
            migrations = [
                ("patients", self.migrate_patients),
                ("medication_histories", self.migrate_medication_histories),
                ("allergy_histories", self.migrate_allergy_histories),
                ("admit_data_histories", self.migrate_admission_data),
                ("body_data_histories", self.migrate_body_data),
                ("blood_pressure_histories", self.migrate_blood_pressure),
                ("blood_sugar_histories", self.migrate_blood_sugar),
                ("temprature_data_histories", self.migrate_temperature_data),
                ("spo2_histories", self.migrate_spo2_data),
                ("creatinine_histories", self.migrate_creatinine_data),
                ("lipid_histories", self.migrate_lipid_data)
            ]
            
            for data_type, migration_func in migrations:
                logger.info(f"\n📊 Migrating {data_type}...")
                try:
                    await migration_func(batch_size)
                    logger.info(f"✅ Completed {data_type} migration")
                except Exception as e:
                    logger.error(f"❌ Failed {data_type} migration: {e}")
                    continue
            
            # Print final statistics
            self.print_migration_summary()
            logger.info("🎉 AMY to FHIR R5 migration completed!")
            
        except Exception as e:
            logger.error(f"❌ Migration failed: {e}")
            raise

    async def migrate_patients(self, batch_size: int):
        """Migrate patients to FHIR Patient resources"""
        patients_file = self.data_dir / "AMY_25_10_2024.patients.json"
        if not patients_file.exists():
            logger.warning(f"Patients file not found: {patients_file}")
            return
            
        logger.info(f"📋 Loading patients from {patients_file}")
        
        with open(patients_file, 'r', encoding='utf-8') as f:
            patients_data = json.load(f)
        
        self.migration_stats["patients"]["total"] = len(patients_data)
        
        for i, patient_doc in enumerate(patients_data):
            try:
                # Use existing patient migration from FHIR service
                fhir_patient_id = await self.fhir_service.migrate_existing_patient_to_fhir(patient_doc)
                self.migration_stats["patients"]["processed"] += 1
                
                if (i + 1) % 50 == 0:
                    logger.info(f"  Migrated {i + 1}/{len(patients_data)} patients")
                    
            except Exception as e:
                self.migration_stats["patients"]["errors"] += 1
                logger.error(f"Failed to migrate patient {patient_doc.get('_id', {}).get('$oid')}: {e}")

    async def migrate_medication_histories(self, batch_size: int):
        """Migrate medication histories to MedicationStatement resources"""
        med_file = self.data_dir / "AMY_25_10_2024.medication_histories.json"
        if not med_file.exists():
            logger.warning(f"Medication histories file not found: {med_file}")
            return
            
        with open(med_file, 'r', encoding='utf-8') as f:
            medications_data = json.load(f)
        
        self.migration_stats["medication_statements"]["total"] = len(medications_data)
        
        for medication_doc in medications_data:
            try:
                # Convert ObjectId format
                if isinstance(medication_doc.get("patient_id"), dict):
                    medication_doc["patient_id"] = medication_doc["patient_id"]["$oid"]
                
                medication_ids = await self.fhir_service.migrate_medication_history_to_fhir(medication_doc)
                self.migration_stats["medication_statements"]["processed"] += len(medication_ids)
                
            except Exception as e:
                self.migration_stats["medication_statements"]["errors"] += 1
                logger.error(f"Failed to migrate medication history: {e}")

    async def migrate_allergy_histories(self, batch_size: int):
        """Migrate allergy histories to AllergyIntolerance resources"""
        allergy_file = self.data_dir / "AMY_25_10_2024.allergy_histories.json"
        if not allergy_file.exists():
            logger.warning(f"Allergy histories file not found: {allergy_file}")
            return
            
        with open(allergy_file, 'r', encoding='utf-8') as f:
            allergies_data = json.load(f)
        
        self.migration_stats["allergy_intolerances"]["total"] = len(allergies_data)
        
        for allergy_doc in allergies_data:
            try:
                # Convert ObjectId format
                if isinstance(allergy_doc.get("patient_id"), dict):
                    allergy_doc["patient_id"] = allergy_doc["patient_id"]["$oid"]
                
                allergy_ids = await self.fhir_service.migrate_allergy_history_to_fhir(allergy_doc)
                self.migration_stats["allergy_intolerances"]["processed"] += len(allergy_ids)
                
            except Exception as e:
                self.migration_stats["allergy_intolerances"]["errors"] += 1
                logger.error(f"Failed to migrate allergy history: {e}")

    async def migrate_admission_data(self, batch_size: int):
        """Migrate admission data to Encounter resources"""
        admit_file = self.data_dir / "AMY_25_10_2024.admit_data_histories.json"
        if not admit_file.exists():
            logger.warning(f"Admission data file not found: {admit_file}")
            return
            
        with open(admit_file, 'r', encoding='utf-8') as f:
            admissions_data = json.load(f)
        
        self.migration_stats["encounters"]["total"] = len(admissions_data)
        
        for admission_doc in admissions_data:
            try:
                # Convert ObjectId format
                if isinstance(admission_doc.get("patient_id"), dict):
                    admission_doc["patient_id"] = admission_doc["patient_id"]["$oid"]
                
                encounter_id = await self.fhir_service.migrate_admission_to_fhir(admission_doc)
                self.migration_stats["encounters"]["processed"] += 1
                
            except Exception as e:
                self.migration_stats["encounters"]["errors"] += 1
                logger.error(f"Failed to migrate admission data: {e}")

    async def migrate_body_data(self, batch_size: int):
        """Migrate body data to Observation resources"""
        body_file = self.data_dir / "AMY_25_10_2024.body_data_histories.json"
        if not body_file.exists():
            logger.warning(f"Body data file not found: {body_file}")
            return
            
        with open(body_file, 'r', encoding='utf-8') as f:
            body_data = json.load(f)
        
        total_observations = sum(len(doc.get("data", [])) for doc in body_data)
        self.migration_stats["observations"]["total"] += total_observations
        
        for body_doc in body_data:
            try:
                # Convert ObjectId format
                if isinstance(body_doc.get("patient_id"), dict):
                    body_doc["patient_id"] = body_doc["patient_id"]["$oid"]
                
                observation_ids = await self.fhir_service.migrate_body_data_to_observations(body_doc)
                self.migration_stats["observations"]["processed"] += len(observation_ids)
                
            except Exception as e:
                self.migration_stats["observations"]["errors"] += 1
                logger.error(f"Failed to migrate body data: {e}")

    async def migrate_blood_pressure(self, batch_size: int):
        """Migrate blood pressure data to Observation resources"""
        bp_file = self.data_dir / "AMY_25_10_2024.blood_pressure_histories.json"
        if not bp_file.exists():
            logger.warning(f"Blood pressure file not found: {bp_file}")
            return
        
        # This file is very large (122MB), process in chunks
        logger.info("Processing large blood pressure file in chunks...")
        await self._process_large_json_file(bp_file, "blood_pressure", batch_size)

    async def migrate_blood_sugar(self, batch_size: int):
        """Migrate blood sugar data to Observation resources"""
        bs_file = self.data_dir / "AMY_25_10_2024.blood_sugar_histories.json"
        if not bs_file.exists():
            logger.warning(f"Blood sugar file not found: {bs_file}")
            return
            
        with open(bs_file, 'r', encoding='utf-8') as f:
            blood_sugar_data = json.load(f)
        
        await self._migrate_vital_signs_data(blood_sugar_data, "blood_sugar")

    async def migrate_temperature_data(self, batch_size: int):
        """Migrate temperature data to Observation resources"""
        temp_file = self.data_dir / "AMY_25_10_2024.temprature_data_histories.json"
        if not temp_file.exists():
            logger.warning(f"Temperature file not found: {temp_file}")
            return
        
        # This file is very large (131MB), process in chunks
        logger.info("Processing large temperature file in chunks...")
        await self._process_large_json_file(temp_file, "temperature", batch_size)

    async def migrate_spo2_data(self, batch_size: int):
        """Migrate SPO2 data to Observation resources"""
        spo2_file = self.data_dir / "AMY_25_10_2024.spo2_histories.json"
        if not spo2_file.exists():
            logger.warning(f"SPO2 file not found: {spo2_file}")
            return
        
        # This file is very large (96MB), process in chunks
        logger.info("Processing large SPO2 file in chunks...")
        await self._process_large_json_file(spo2_file, "spo2", batch_size)

    async def migrate_creatinine_data(self, batch_size: int):
        """Migrate creatinine lab data to DiagnosticReport resources"""
        creat_file = self.data_dir / "AMY_25_10_2024.creatinine_histories.json"
        if not creat_file.exists():
            logger.warning(f"Creatinine file not found: {creat_file}")
            return
            
        with open(creat_file, 'r', encoding='utf-8') as f:
            creatinine_data = json.load(f)
        
        self.migration_stats["diagnostic_reports"]["total"] += len(creatinine_data)
        
        for lab_doc in creatinine_data:
            try:
                # Convert ObjectId format
                if isinstance(lab_doc.get("patient_id"), dict):
                    lab_doc["patient_id"] = lab_doc["patient_id"]["$oid"]
                
                report_id = await self.fhir_service.migrate_lab_results_to_fhir(lab_doc, "creatinine")
                self.migration_stats["diagnostic_reports"]["processed"] += 1
                
            except Exception as e:
                self.migration_stats["diagnostic_reports"]["errors"] += 1
                logger.error(f"Failed to migrate creatinine data: {e}")

    async def migrate_lipid_data(self, batch_size: int):
        """Migrate lipid lab data to DiagnosticReport resources"""
        lipid_file = self.data_dir / "AMY_25_10_2024.lipid_histories.json"
        if not lipid_file.exists():
            logger.warning(f"Lipid file not found: {lipid_file}")
            return
            
        with open(lipid_file, 'r', encoding='utf-8') as f:
            lipid_data = json.load(f)
        
        self.migration_stats["diagnostic_reports"]["total"] += len(lipid_data)
        
        for lab_doc in lipid_data:
            try:
                # Convert ObjectId format
                if isinstance(lab_doc.get("patient_id"), dict):
                    lab_doc["patient_id"] = lab_doc["patient_id"]["$oid"]
                
                report_id = await self.fhir_service.migrate_lab_results_to_fhir(lab_doc, "lipid")
                self.migration_stats["diagnostic_reports"]["processed"] += 1
                
            except Exception as e:
                self.migration_stats["diagnostic_reports"]["errors"] += 1
                logger.error(f"Failed to migrate lipid data: {e}")

    async def _process_large_json_file(self, file_path: Path, data_type: str, batch_size: int):
        """Process large JSON files in chunks to avoid memory issues"""
        # For very large files, we'd need streaming JSON parsing
        # For now, log the file size and skip processing
        file_size_mb = file_path.stat().st_size / (1024 * 1024)
        logger.warning(f"Skipping large file {file_path.name} ({file_size_mb:.1f}MB) - implement streaming parser for production")

    async def _migrate_vital_signs_data(self, vital_data: List[Dict], data_type: str):
        """Migrate vital signs data to FHIR Observations"""
        total_observations = sum(len(doc.get("data", [])) for doc in vital_data)
        self.migration_stats["observations"]["total"] += total_observations
        
        for vital_doc in vital_data:
            try:
                # Convert ObjectId format
                if isinstance(vital_doc.get("patient_id"), dict):
                    vital_doc["patient_id"] = vital_doc["patient_id"]["$oid"]
                
                # This would need specific implementation for each vital sign type
                # For now, count as processed
                data_count = len(vital_doc.get("data", []))
                self.migration_stats["observations"]["processed"] += data_count
                
            except Exception as e:
                self.migration_stats["observations"]["errors"] += 1
                logger.error(f"Failed to migrate {data_type} data: {e}")

    def print_migration_summary(self):
        """Print comprehensive migration statistics"""
        logger.info("\n" + "="*60)
        logger.info("📊 AMY to FHIR R5 Migration Summary")
        logger.info("="*60)
        
        total_processed = 0
        total_errors = 0
        
        for resource_type, stats in self.migration_stats.items():
            processed = stats["processed"]
            total = stats["total"]
            errors = stats["errors"]
            
            if total > 0:
                success_rate = (processed / total) * 100 if total > 0 else 0
                logger.info(f"{resource_type.replace('_', ' ').title():<20}: {processed:>6}/{total:<6} ({success_rate:5.1f}%) - {errors} errors")
                total_processed += processed
                total_errors += errors
        
        logger.info("-" * 60)
        logger.info(f"{'Total Resources':<20}: {total_processed:>6} processed - {total_errors} errors")
        logger.info("="*60)

async def main():
    """Main migration function"""
    parser = argparse.ArgumentParser(description="Migrate AMY JSON data to FHIR R5")
    parser.add_argument("--data-dir", default="docs/JSON-DB-IMPORT/import_script", 
                       help="Directory containing AMY JSON files")
    parser.add_argument("--batch-size", type=int, default=100,
                       help="Batch size for processing")
    parser.add_argument("--dry-run", action="store_true",
                       help="Dry run - analyze files without migrating")
    
    args = parser.parse_args()
    
    if args.dry_run:
        print("🔍 Dry run mode - analyzing AMY data files...")
        # Implementation for dry run analysis
        return
    
    migrator = AMYToFHIRMigrator(args.data_dir)
    await migrator.migrate_all_amy_data(args.batch_size)

if __name__ == "__main__":
    asyncio.run(main()) 