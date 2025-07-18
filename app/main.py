from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.logger import logger
import asyncio

from app.routes.fhir_r5 import router as fhir_r5_router
from app.routes.fhir_validation import router as fhir_validation_router
from app.routes.kati_transaction import router as kati_transaction_router
from app.services.fhir_data_monitor import fhir_monitor
from app.services.mongodb_service import mongodb_service
from app.services.redis_service import redis_service

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(fhir_r5_router, prefix="/api/v1")
app.include_router(fhir_validation_router, prefix="/api/v1")
app.include_router(kati_transaction_router)

@app.on_event("startup")
async def startup_event():
    """Startup event handler"""
    try:
        # Initialize services
        await mongodb_service.connect()
        await redis_service.connect()
        
        # Start FHIR data quality monitoring
        asyncio.create_task(fhir_monitor.start_monitoring())
        logger.info("Started FHIR data quality monitoring")
        
        logger.info("Application startup completed successfully")
    except Exception as e:
        logger.error(f"Error during startup: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event handler"""
    try:
        # Stop FHIR data quality monitoring
        await fhir_monitor.stop_monitoring()
        logger.info("Stopped FHIR data quality monitoring")
        
        # Close connections
        await mongodb_service.close()
        await redis_service.close()
        
        logger.info("Application shutdown completed successfully")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}") 