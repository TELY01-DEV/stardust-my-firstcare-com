#!/usr/bin/env python3
"""
FHIR R5 Parser Service
=====================
Dedicated service for processing medical device data into FHIR R5 format.
Runs as a separate Docker container for improved performance and scalability.

Features:
- Asynchronous processing from Redis queue
- Concurrent processing with configurable worker threads
- FHIR R5 resource creation with LOINC codes
- Legacy medical history routing
- Comprehensive error handling and retry logic
- Health monitoring and metrics
"""

import asyncio
import json
import os
import sys
import signal
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Dict, Any, Optional

try:
    import redis
except ImportError:
    redis = None

# Add app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'app'))

from app.services.fhir_r5_service import fhir_service
from app.services.mongo import mongodb_service
from app.utils.structured_logging import get_logger

logger = get_logger(__name__)

class FHIRParserService:
    """
    Dedicated FHIR R5 parser service for asynchronous data processing
    """
    
    def __init__(self):
        self.redis_client = None
        self.queue_name = os.getenv("FHIR_QUEUE_NAME", "fhir_processing_queue")
        self.batch_size = int(os.getenv("FHIR_BATCH_SIZE", "10"))
        self.worker_threads = int(os.getenv("FHIR_WORKER_THREADS", "4"))
        self.enable_legacy_routing = os.getenv("ENABLE_LEGACY_ROUTING", "true").lower() == "true"
        
        self.running = False
        self.workers = []
        self.stats = {
            "processed": 0,
            "errors": 0,
            "start_time": datetime.utcnow(),
            "last_processed": None
        }
        
        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)
    
    async def initialize(self):
        """Initialize connections and services"""
        try:
            # Initialize Redis connection
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6374/0")
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            
            # Test Redis connection
            self.redis_client.ping()
            logger.info(f"✅ Connected to Redis: {redis_url}")
            
            # Initialize MongoDB connection
            await mongodb_service.connect()
            logger.info("✅ Connected to MongoDB")
            
            # Initialize FHIR service
            # fhir_service is already initialized globally
            logger.info("✅ FHIR R5 service initialized")
            
            logger.info(f"🔧 Configuration:")
            logger.info(f"   Queue: {self.queue_name}")
            logger.info(f"   Batch size: {self.batch_size}")
            logger.info(f"   Worker threads: {self.worker_threads}")
            logger.info(f"   Legacy routing: {self.enable_legacy_routing}")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize FHIR parser service: {e}")
            raise
    
    async def start(self):
        """Start the FHIR parser service"""
        logger.info("🚀 Starting FHIR R5 Parser Service...")
        
        try:
            await self.initialize()
            
            self.running = True
            
            # Start worker threads
            with ThreadPoolExecutor(max_workers=self.worker_threads) as executor:
                # Submit worker tasks
                worker_futures = []
                for i in range(self.worker_threads):
                    future = executor.submit(self._worker_thread, i)
                    worker_futures.append(future)
                    logger.info(f"📊 Started worker thread {i}")
                
                # Start monitoring thread
                monitor_future = executor.submit(self._monitor_thread)
                
                logger.info(f"✅ FHIR Parser Service started with {self.worker_threads} workers")
                
                # Wait for shutdown signal
                while self.running:
                    await asyncio.sleep(1)
                
                logger.info("🛑 Shutting down FHIR Parser Service...")
                
                # Wait for workers to finish
                for future in worker_futures:
                    future.result(timeout=30)
                
                monitor_future.result(timeout=5)
                
        except Exception as e:
            logger.error(f"❌ FHIR Parser Service error: {e}")
            raise
        finally:
            self._cleanup()
    
    def _worker_thread(self, worker_id: int):
        """Worker thread for processing FHIR queue"""
        logger.info(f"🔄 Worker {worker_id} started")
        
        while self.running:
            try:
                # Get batch of items from queue
                items = []
                for _ in range(self.batch_size):
                    if not self.running:
                        break
                    
                    # Block for up to 1 second waiting for items
                    item = self.redis_client.blpop(self.queue_name, timeout=1)
                    if item:
                        items.append(json.loads(item[1]))
                    else:
                        break
                
                if not items:
                    continue
                
                logger.info(f"🔄 Worker {worker_id} processing {len(items)} items")
                
                # Process batch
                for item in items:
                    if not self.running:
                        break
                    
                    try:
                        asyncio.run(self._process_device_data(item))
                        self.stats["processed"] += 1
                        self.stats["last_processed"] = datetime.utcnow()
                        
                    except Exception as e:
                        self.stats["errors"] += 1
                        logger.error(f"❌ Worker {worker_id} processing error: {e}")
                        logger.error(f"   Item: {item}")
                        
                        # Re-queue failed item with retry count
                        retry_count = item.get("retry_count", 0)
                        if retry_count < 3:
                            item["retry_count"] = retry_count + 1
                            self.redis_client.rpush(self.queue_name, json.dumps(item))
                            logger.info(f"🔄 Re-queued item for retry {retry_count + 1}/3")
                
            except Exception as e:
                logger.error(f"❌ Worker {worker_id} thread error: {e}")
                time.sleep(5)  # Wait before retrying
        
        logger.info(f"✅ Worker {worker_id} stopped")
    
    def _monitor_thread(self):
        """Monitor thread for health checks and statistics"""
        logger.info("📊 Monitor thread started")
        
        while self.running:
            try:
                # Log statistics every 60 seconds
                uptime = datetime.utcnow() - self.stats["start_time"]
                queue_size = self.redis_client.llen(self.queue_name)
                
                logger.info(f"📊 FHIR Parser Statistics:")
                logger.info(f"   Uptime: {uptime}")
                logger.info(f"   Processed: {self.stats['processed']}")
                logger.info(f"   Errors: {self.stats['errors']}")
                logger.info(f"   Queue size: {queue_size}")
                logger.info(f"   Last processed: {self.stats['last_processed']}")
                
                # Health check - ensure we're processing data
                if queue_size > 1000:
                    logger.warning(f"⚠️ High queue size: {queue_size} items")
                
                time.sleep(60)
                
            except Exception as e:
                logger.error(f"❌ Monitor thread error: {e}")
                time.sleep(30)
        
        logger.info("✅ Monitor thread stopped")
    
    async def _process_device_data(self, item: Dict[str, Any]):
        """Process a single device data item into FHIR R5 format"""
        try:
            data_type = item.get("type")
            device_id = item.get("device_id")
            patient_id = item.get("patient_id")
            
            logger.debug(f"📋 Processing {data_type} from device {device_id}")
            
            # Create FHIR R5 Observations
            observations = await fhir_service.transform_ava4_mqtt_to_fhir(
                mqtt_payload=item,
                patient_id=patient_id,
                device_id=device_id
            )
            
            # Save FHIR observations
            for obs in observations:
                await fhir_service.create_fhir_resource(
                    resource_type="Observation",
                    resource_data=obs,
                    source_system="fhir-parser-service",
                    device_mac_address=device_id
                )
            
            # Route to legacy collections if enabled
            if self.enable_legacy_routing:
                await self._route_to_legacy_collections(item, patient_id)
            
            logger.debug(f"✅ Processed {data_type} from device {device_id} -> {len(observations)} FHIR observations")
            
        except Exception as e:
            logger.error(f"❌ Failed to process device data: {e}")
            logger.error(f"   Item: {item}")
            raise
    
    async def _route_to_legacy_collections(self, item: Dict[str, Any], patient_id: str):
        """Route data to legacy medical history collections"""
        try:
            from bson import ObjectId
            
            data_type = item.get("type", "").upper()
            device_id = item.get("device_id")
            timestamp = datetime.fromisoformat(item.get("timestamp", "").replace("Z", "+00:00"))
            data = item.get("data", {})
            
            # Map data type to collection
            collection_mapping = {
                "BLOOD_PRESSURE": "blood_pressure_histories",
                "BLOOD_SUGAR": "blood_sugar_histories", 
                "TEMPERATURE": "temprature_data_histories",
                "WEIGHT": "body_data_histories",
                "SPO2": "spo2_histories",
                "STEPS": "step_histories",
                "SLEEP": "sleep_data_histories",
                "CREATININE": "creatinine_histories",
                "LIPID": "lipid_histories"
            }
            
            collection_name = collection_mapping.get(data_type)
            if collection_name and patient_id:
                collection = mongodb_service.get_collection(collection_name)
                
                history_entry = {
                    "patient_id": ObjectId(patient_id),
                    "device_id": device_id,
                    "device_type": item.get("device_type", "UNKNOWN"),
                    "data": [data],
                    "timestamp": timestamp,
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                    "source": "fhir-parser-service"
                }
                
                await collection.insert_one(history_entry)
                logger.debug(f"📝 Routed to legacy collection: {collection_name}")
            
        except Exception as e:
            logger.error(f"❌ Failed to route to legacy collections: {e}")
            # Don't raise - legacy routing failure shouldn't stop FHIR processing
    
    def _handle_shutdown(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logger.info(f"🛑 Received shutdown signal {signum}")
        self.running = False
    
    def _cleanup(self):
        """Cleanup resources"""
        try:
            if self.redis_client:
                self.redis_client.close()
            logger.info("✅ Cleanup completed")
        except Exception as e:
            logger.error(f"❌ Cleanup error: {e}")

async def main():
    """Main entry point"""
    parser_service = FHIRParserService()
    await parser_service.start()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Service interrupted by user")
    except Exception as e:
        logger.error(f"❌ Service failed: {e}")
        sys.exit(1) 