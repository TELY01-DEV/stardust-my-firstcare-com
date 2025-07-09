"""
Queue Service for Asynchronous FHIR Processing
==============================================
Provides Redis-based queuing for FHIR R5 data processing to improve
device endpoint response times and enable scalable data processing.
"""

import asyncio
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional, List
from app.utils.structured_logging import get_logger

logger = get_logger(__name__)

class QueueService:
    """
    Redis-based queue service for asynchronous FHIR processing
    """
    
    def __init__(self):
        self.redis_client = None
        self.queue_name = "fhir_processing_queue"
        self.enabled = os.getenv("ENABLE_ASYNC_FHIR", "false").lower() == "true"
        
    async def initialize(self):
        """Initialize Redis connection"""
        if not self.enabled:
            logger.info("📴 Async FHIR processing disabled")
            return
            
        try:
            # Import redis here to avoid import errors if not installed
            import redis
            
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6374/0")
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            
            # Test connection
            await asyncio.get_event_loop().run_in_executor(None, self.redis_client.ping)
            
            logger.info(f"✅ Queue service initialized: {redis_url}")
            
        except ImportError:
            logger.warning("⚠️ Redis not available, falling back to synchronous processing")
            self.enabled = False
        except Exception as e:
            logger.error(f"❌ Failed to initialize queue service: {e}")
            self.enabled = False
    
    async def queue_device_data(
        self, 
        device_data: Dict[str, Any], 
        patient_id: str,
        device_id: str
    ) -> bool:
        """
        Queue device data for asynchronous FHIR processing
        
        Args:
            device_data: Raw device data payload
            patient_id: Patient ID associated with the device
            device_id: Device MAC address or identifier
            
        Returns:
            True if queued successfully, False if queuing failed
        """
        if not self.enabled or not self.redis_client:
            return False
            
        try:
            queue_item = {
                "timestamp": datetime.utcnow().isoformat(),
                "patient_id": patient_id,
                "device_id": device_id,
                "device_data": device_data,
                "queued_at": datetime.utcnow().isoformat()
            }
            
            # Add to Redis queue
            await asyncio.get_event_loop().run_in_executor(
                None,
                self.redis_client.rpush,
                self.queue_name,
                json.dumps(queue_item)
            )
            
            logger.debug(f"📤 Queued device data: {device_data.get('type')} from {device_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to queue device data: {e}")
            return False
    
    async def get_queue_size(self) -> int:
        """Get current queue size"""
        if not self.enabled or not self.redis_client:
            return 0
            
        try:
            return await asyncio.get_event_loop().run_in_executor(
                None,
                self.redis_client.llen,
                self.queue_name
            )
        except Exception as e:
            logger.error(f"❌ Failed to get queue size: {e}")
            return 0
    
    async def clear_queue(self) -> bool:
        """Clear all items from the queue"""
        if not self.enabled or not self.redis_client:
            return False
            
        try:
            await asyncio.get_event_loop().run_in_executor(
                None,
                self.redis_client.delete,
                self.queue_name
            )
            logger.info("🗑️ Queue cleared")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to clear queue: {e}")
            return False
    
    async def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        if not self.enabled:
            return {
                "enabled": False,
                "queue_size": 0,
                "status": "disabled"
            }
        
        if not self.redis_client:
            return {
                "enabled": True,
                "queue_size": 0,
                "status": "error",
                "error": "Redis not connected"
            }
        
        try:
            queue_size = await self.get_queue_size()
            
            return {
                "enabled": True,
                "queue_size": queue_size,
                "status": "healthy",
                "queue_name": self.queue_name
            }
        except Exception as e:
            return {
                "enabled": True,
                "queue_size": 0,
                "status": "error",
                "error": str(e)
            }

# Global queue service instance
queue_service = QueueService() 