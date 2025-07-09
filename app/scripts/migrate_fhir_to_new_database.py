#!/usr/bin/env python3
"""
FHIR Database Migration Script
=============================
Migrate existing FHIR R5 collections from AMY database to MFC_FHIR_R5 database.

This script:
- Moves FHIR collections to dedicated database
- Creates proper indexes for performance
- Validates data integrity after migration
- Provides rollback capability
"""

import asyncio
import sys
import os
from datetime import datetime
from typing import Dict, Any, List
from bson import ObjectId

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.mongo import mongodb_service
from app.utils.structured_logging import get_logger
from config import settings

logger = get_logger(__name__)

class FHIRDatabaseMigrator:
    """Migrate FHIR data to dedicated database"""
    
    def __init__(self):
        self.fhir_collections = [
            "fhir_patients",
            "fhir_observations", 
            "fhir_devices",
            "fhir_organizations",
            "fhir_locations",
            "fhir_conditions",
            "fhir_medications",
            "fhir_allergies",
            "fhir_encounters",
            "fhir_provenance"
        ]
        
        self.migration_stats = {
            "collections_migrated": 0,
            "total_documents": 0,
            "documents_migrated": 0,
            "errors": 0,
            "start_time": None,
            "end_time": None
        }
    
    async def migrate_fhir_database(self, dry_run: bool = False):
        """Migrate FHIR collections to dedicated database"""
        logger.info("🚀 Starting FHIR database migration...")
        logger.info(f"📊 Source: {settings.mongodb_main_db}")
        logger.info(f"🎯 Target: {settings.mongodb_fhir_db}")
        
        if dry_run:
            logger.info("🔍 DRY RUN MODE - No data will be moved")
        
        self.migration_stats["start_time"] = datetime.utcnow()
        
        try:
            # Connect to MongoDB
            await mongodb_service.connect()
            
            # Get database references
            source_db = mongodb_service.main_db
            target_db = mongodb_service.fhir_db
            
            # Analyze source collections
            await self._analyze_source_collections(source_db)
            
            if not dry_run:
                # Migrate each FHIR collection
                for collection_name in self.fhir_collections:
                    await self._migrate_collection(
                        source_db, 
                        target_db, 
                        collection_name
                    )
                
                # Create indexes on target database
                await self._create_fhir_indexes(target_db)
                
                # Validate migration
                await self._validate_migration(source_db, target_db)
            
            self.migration_stats["end_time"] = datetime.utcnow()
            self._print_migration_summary()
            
            logger.info("✅ FHIR database migration completed successfully!")
            
        except Exception as e:
            logger.error(f"❌ FHIR database migration failed: {e}")
            raise
    
    async def _analyze_source_collections(self, source_db):
        """Analyze existing FHIR collections in source database"""
        logger.info("🔍 Analyzing source FHIR collections...")
        
        for collection_name in self.fhir_collections:
            try:
                collection = source_db[collection_name]
                count = await collection.count_documents({})
                
                if count > 0:
                    logger.info(f"📊 {collection_name}: {count:,} documents")
                    self.migration_stats["total_documents"] += count
                else:
                    logger.info(f"📊 {collection_name}: empty")
                    
            except Exception as e:
                logger.warning(f"⚠️ Could not analyze {collection_name}: {e}")
        
        logger.info(f"📋 Total FHIR documents to migrate: {self.migration_stats['total_documents']:,}")
    
    async def _migrate_collection(self, source_db, target_db, collection_name: str):
        """Migrate a single FHIR collection"""
        try:
            source_collection = source_db[collection_name]
            target_collection = target_db[collection_name]
            
            # Check if source collection exists and has data
            count = await source_collection.count_documents({})
            if count == 0:
                logger.info(f"⏭️ Skipping {collection_name} (empty)")
                return
            
            logger.info(f"🔄 Migrating {collection_name} ({count:,} documents)...")
            
            # Copy all documents in batches
            batch_size = 1000
            migrated = 0
            
            async for batch in source_collection.find().batch_size(batch_size):
                batch_docs = []
                async for doc in source_collection.find().skip(migrated).limit(batch_size):
                    batch_docs.append(doc)
                
                if batch_docs:
                    await target_collection.insert_many(batch_docs)
                    migrated += len(batch_docs)
                    
                    logger.info(f"   📤 Migrated {migrated:,}/{count:,} documents...")
                
                if migrated >= count:
                    break
            
            # Verify counts match
            target_count = await target_collection.count_documents({})
            if target_count == count:
                logger.info(f"✅ {collection_name} migrated successfully ({target_count:,} documents)")
                self.migration_stats["collections_migrated"] += 1
                self.migration_stats["documents_migrated"] += target_count
            else:
                raise Exception(f"Count mismatch: source={count}, target={target_count}")
            
        except Exception as e:
            logger.error(f"❌ Failed to migrate {collection_name}: {e}")
            self.migration_stats["errors"] += 1
            raise
    
    async def _create_fhir_indexes(self, target_db):
        """Create performance indexes on FHIR collections"""
        logger.info("🔧 Creating FHIR database indexes...")
        
        index_definitions = {
            "fhir_observations": [
                ("resource_id", 1),
                ("patient_id", 1),
                ("device_id", 1),
                ("effective_datetime", -1),
                ("resource_data.code.coding.code", 1),
                ("is_deleted", 1)
            ],
            "fhir_patients": [
                ("resource_id", 1),
                ("resource_data.identifier.value", 1),
                ("is_deleted", 1)
            ],
            "fhir_devices": [
                ("resource_id", 1),
                ("resource_data.identifier.value", 1),
                ("is_deleted", 1)
            ],
            "fhir_organizations": [
                ("resource_id", 1),
                ("resource_data.identifier.value", 1),
                ("is_deleted", 1)
            ],
            "fhir_provenance": [
                ("resource_id", 1),
                ("recorded_datetime", -1),
                ("expires_at", 1)  # TTL index
            ]
        }
        
        for collection_name, indexes in index_definitions.items():
            try:
                collection = target_db[collection_name]
                
                for index_spec in indexes:
                    if isinstance(index_spec, tuple):
                        field, direction = index_spec
                        await collection.create_index([(field, direction)])
                        logger.info(f"   📇 Created index on {collection_name}.{field}")
                
                # Special TTL index for provenance
                if collection_name == "fhir_provenance":
                    await collection.create_index(
                        "expires_at", 
                        expireAfterSeconds=0
                    )
                    logger.info(f"   ⏰ Created TTL index on {collection_name}.expires_at")
                    
            except Exception as e:
                logger.warning(f"⚠️ Could not create indexes for {collection_name}: {e}")
    
    async def _validate_migration(self, source_db, target_db):
        """Validate migration was successful"""
        logger.info("🔍 Validating migration...")
        
        validation_errors = []
        
        for collection_name in self.fhir_collections:
            try:
                source_count = await source_db[collection_name].count_documents({})
                target_count = await target_db[collection_name].count_documents({})
                
                if source_count != target_count:
                    error = f"{collection_name}: source={source_count}, target={target_count}"
                    validation_errors.append(error)
                    logger.error(f"❌ Count mismatch: {error}")
                else:
                    logger.info(f"✅ {collection_name}: {target_count:,} documents")
                    
            except Exception as e:
                error = f"{collection_name}: {str(e)}"
                validation_errors.append(error)
                logger.error(f"❌ Validation error: {error}")
        
        if validation_errors:
            raise Exception(f"Migration validation failed: {validation_errors}")
        
        logger.info("✅ Migration validation passed!")
    
    async def rollback_migration(self):
        """Rollback migration by dropping FHIR database collections"""
        logger.warning("⚠️ ROLLBACK: Dropping FHIR database collections...")
        
        try:
            target_db = mongodb_service.fhir_db
            
            for collection_name in self.fhir_collections:
                try:
                    await target_db[collection_name].drop()
                    logger.info(f"🗑️ Dropped {collection_name}")
                except Exception as e:
                    logger.warning(f"⚠️ Could not drop {collection_name}: {e}")
            
            logger.info("✅ Rollback completed")
            
        except Exception as e:
            logger.error(f"❌ Rollback failed: {e}")
            raise
    
    def _print_migration_summary(self):
        """Print migration statistics"""
        logger.info("\n" + "="*60)
        logger.info("📊 FHIR DATABASE MIGRATION SUMMARY")
        logger.info("="*60)
        
        duration = None
        if self.migration_stats["start_time"] and self.migration_stats["end_time"]:
            duration = self.migration_stats["end_time"] - self.migration_stats["start_time"]
        
        logger.info(f"Collections migrated: {self.migration_stats['collections_migrated']}")
        logger.info(f"Documents migrated: {self.migration_stats['documents_migrated']:,}")
        logger.info(f"Errors: {self.migration_stats['errors']}")
        logger.info(f"Duration: {duration}")
        logger.info("="*60)

async def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Migrate FHIR data to dedicated database")
    parser.add_argument("--dry-run", action="store_true", help="Analyze only, don't migrate")
    parser.add_argument("--rollback", action="store_true", help="Rollback migration")
    
    args = parser.parse_args()
    
    migrator = FHIRDatabaseMigrator()
    
    try:
        if args.rollback:
            await migrator.rollback_migration()
        else:
            await migrator.migrate_fhir_database(dry_run=args.dry_run)
            
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 