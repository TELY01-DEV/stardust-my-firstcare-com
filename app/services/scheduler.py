import asyncio
from datetime import datetime, timedelta
from typing import Optional
import logging

from app.services.reporting_engine import reporting_engine
from app.utils.structured_logging import get_logger

logger = get_logger(__name__)

class ReportScheduler:
    """Scheduler service for automated report generation"""
    
    def __init__(self):
        self.running = False
        self.task: Optional[asyncio.Task] = None
        self.check_interval = 300  # Check every 5 minutes
    
    async def start(self):
        """Start the scheduler"""
        if self.running:
            logger.warning("Scheduler is already running")
            return
        
        self.running = True
        self.task = asyncio.create_task(self._scheduler_loop())
        logger.info("Report scheduler started")
    
    async def stop(self):
        """Stop the scheduler"""
        if not self.running:
            return
        
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        
        logger.info("Report scheduler stopped")
    
    async def _scheduler_loop(self):
        """Main scheduler loop"""
        while self.running:
            try:
                logger.debug("Checking for scheduled reports...")
                await reporting_engine.check_scheduled_reports()
                
                # Wait for next check
                await asyncio.sleep(self.check_interval)
                
            except asyncio.CancelledError:
                logger.info("Scheduler loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in scheduler loop: {str(e)}")
                # Continue running even if there's an error
                await asyncio.sleep(self.check_interval)

# Global scheduler instance
report_scheduler = ReportScheduler() 