# FHIR R5 Services Implementation Guide

## Overview

This guide explains how to implement separate Docker services for FHIR R5 data processing to improve performance and scalability of your medical IoT system.

## Current vs New Architecture

### **Current (Synchronous)**
```
IoT Device → API → [FHIR + Legacy + Audit] → Response (500ms)
```

### **New (Asynchronous)**
```
IoT Device → API → Queue → Response (50ms)
                     ↓
              FHIR Service → [Process Data] → Database
```

## Benefits

- **10x faster** device response times (50ms vs 500ms)
- **Better reliability** - device communication never fails due to FHIR issues
- **Scalability** - handle thousands of concurrent device readings
- **Independent scaling** - scale FHIR processing separately from API
- **Better monitoring** - dedicated health checks per service

## Implementation Plan

### Phase 0: Migrate FHIR Data to New Database (Required First)

1. **Run database migration analysis**:
   ```bash
   # Check what FHIR data exists in current database
   python app/scripts/migrate_fhir_to_new_database.py --dry-run
   ```

2. **Migrate existing FHIR data**:
   ```bash
   # Move FHIR data to dedicated MFC_FHIR_R5 database
   python app/scripts/migrate_fhir_to_new_database.py
   
   # This will:
   # - Move fhir_observations, fhir_devices, etc. to MFC_FHIR_R5 database
   # - Create proper indexes for performance
   # - Validate data integrity
   ```

3. **Update configuration**:
   ```bash
   # Add to your .env file
   MONGODB_MAIN_DB=AMY
   MONGODB_FHIR_DB=MFC_FHIR_R5
   ```

### Phase 1: Add Queue Service (Low Risk)

1. **Enable async processing in existing API**:
   ```bash
   # Add to your .env file
   ENABLE_ASYNC_FHIR=true
   FHIR_QUEUE_NAME=fhir_processing_queue
   ```

2. **Update device endpoints** to use queuing:
   ```python
   # In your device endpoints, replace:
   await create_fhir_observations_from_ava4(data, patient_id, device_id)
   
   # With:
   from app.services.queue_service import queue_service
   
   # Try async first, fallback to sync
   queued = await queue_service.queue_device_data(
       device_data=data.dict(),
       patient_id=patient_id,
       device_id=device_id
   )
   
   if not queued:
       # Fallback to synchronous processing
       await create_fhir_observations_from_ava4(data, patient_id, device_id)
   ```

3. **Deploy and test** with existing docker-compose.yml

### Phase 2: Add FHIR Parser Service (Medium Risk)

1. **Deploy separate services**:
   ```bash
   # Use the new docker-compose configuration
   docker-compose -f docker-compose.fhir.yml up -d
   ```

2. **Monitor both services** running in parallel

3. **Gradually switch traffic** to the new architecture

### Phase 3: Migration Service (Low Risk)

1. **Run one-time migration**:
   ```bash
   # Start migration service manually
   docker-compose -f docker-compose.fhir.yml up fhir-migrator
   ```

2. **Monitor progress** and verify data integrity

## Configuration Options

### Environment Variables

```bash
# Main API Service
ENABLE_ASYNC_FHIR=true
FHIR_QUEUE_NAME=fhir_processing_queue
REDIS_URL=redis://redis:6374/0

# FHIR Parser Service
FHIR_BATCH_SIZE=10          # Process 10 items at a time
FHIR_WORKER_THREADS=4       # Use 4 concurrent workers
ENABLE_LEGACY_ROUTING=true  # Also write to legacy collections

# FHIR Migration Service
MIGRATION_BATCH_SIZE=50     # Migrate 50 records at a time
AUTO_START_MIGRATION=false  # Don't auto-start migration
```

## Monitoring & Health Checks

### Queue Monitoring

```bash
# Check queue status
curl http://localhost:5054/admin/queue/stats

# Expected response:
{
  "enabled": true,
  "queue_size": 0,
  "status": "healthy",
  "queue_name": "fhir_processing_queue"
}
```

### Service Health Checks

```bash
# Main API health
curl http://localhost:5054/health

# FHIR Parser health (via Docker)
docker inspect stardust-fhir-parser --format='{{.State.Health.Status}}'

# FHIR Migration status
docker logs stardust-fhir-migrator
```

### Performance Monitoring

```bash
# Monitor queue size over time
docker logs stardust-fhir-parser | grep "📊 FHIR Parser Statistics"

# Expected output every 60 seconds:
# 📊 FHIR Parser Statistics:
#    Uptime: 1:23:45.123456
#    Processed: 1,234
#    Errors: 0
#    Queue size: 5
#    Last processed: 2024-01-15T10:30:00.000000
```

## Deployment Commands

### Development/Testing
```bash
# Start with existing setup (synchronous)
docker-compose up -d

# Add Redis for queuing
docker-compose -f docker-compose.fhir.yml up -d redis

# Enable async processing
echo "ENABLE_ASYNC_FHIR=true" >> .env
docker-compose restart stardust-api
```

### Production Deployment
```bash
# Deploy all services
docker-compose -f docker-compose.fhir.yml up -d

# Verify all services are healthy
docker-compose -f docker-compose.fhir.yml ps

# Check logs
docker-compose -f docker-compose.fhir.yml logs -f
```

### Database Migration (Required First)
```bash
# 1. Migrate existing FHIR data to new database
python app/scripts/migrate_fhir_to_new_database.py --dry-run  # Analyze first
python app/scripts/migrate_fhir_to_new_database.py           # Migrate data

# 2. Verify FHIR data is now in MFC_FHIR_R5 database
```

### FHIR R5 Migration (One-time)
```bash
# Run data migration to FHIR R5 format
docker-compose -f docker-compose.fhir.yml run --rm fhir-migrator

# Migration will process:
# - 211 patients → FHIR Patient resources
# - 6,898 medical records → FHIR Observation resources  
# - 196 devices → FHIR Device resources
# - Hospital data → FHIR Organization resources
```

## Rollback Plan

If issues occur, you can quickly rollback:

### Quick Rollback (1 minute)
```bash
# Disable async processing
echo "ENABLE_ASYNC_FHIR=false" >> .env
docker-compose restart stardust-api

# This immediately returns to synchronous processing
```

### Full Rollback (5 minutes)
```bash
# Stop new services
docker-compose -f docker-compose.fhir.yml down fhir-parser fhir-migrator

# Return to original configuration  
docker-compose up -d

# System returns to exactly the previous state
```

## Resource Requirements

### Recommended Resource Allocation

```yaml
services:
  stardust-api:     # Main API (unchanged)
    memory: 1GB
    cpu: 1.0
    
  fhir-parser:      # FHIR processing service
    memory: 1GB     # Can handle 1000+ queued items
    cpu: 0.5        # 4 worker threads
    
  fhir-migrator:    # One-time migration
    memory: 2GB     # Processes large datasets
    cpu: 1.0        # Batch processing
    
  redis:            # Queue storage
    memory: 1GB     # Can queue 10,000+ items
```

### Scaling Considerations

- **Queue size > 1000**: Add more `fhir-parser` instances
- **High device traffic**: Increase `FHIR_WORKER_THREADS`
- **Large migration**: Increase `MIGRATION_BATCH_SIZE`

## Data Flow

### Device Data Ingestion (New)
```
1. Device sends data → FastAPI endpoint
2. API validates data and device (unchanged)
3. API queues data for FHIR processing (NEW)
4. API returns immediate response to device (50ms)
5. FHIR service processes queue asynchronously
6. FHIR service creates Observations + routes to legacy collections
7. FHIR service logs audit trail
```

### Benefits
- **Device sees 10x faster response**
- **Backend processing continues normally**
- **Zero data loss** (queue persistence)
- **Better error handling** (retry logic)

## Troubleshooting

### Common Issues

1. **Queue growing too large**
   ```bash
   # Check queue size
   curl http://localhost:5054/admin/queue/stats
   
   # If queue_size > 1000, scale up workers
   docker-compose -f docker-compose.fhir.yml scale fhir-parser=2
   ```

2. **FHIR processing errors**
   ```bash
   # Check parser logs
   docker logs stardust-fhir-parser | grep "❌"
   
   # Check error statistics
   docker logs stardust-fhir-parser | grep "📊 FHIR Parser Statistics"
   ```

3. **Redis connection issues**
   ```bash
   # Test Redis connectivity
   docker exec -it stardust-redis redis-cli ping
   
   # Should return: PONG
   ```

### Recovery Procedures

1. **Lost queue data**: 
   - Redis is persistent, data survives container restarts
   - For disaster recovery, re-process recent device data

2. **FHIR service crash**:
   - Queue data is preserved
   - Restart service, processing resumes automatically

3. **MongoDB issues**:
   - FHIR service will retry with exponential backoff
   - Queue preserves data until MongoDB is restored

## Success Metrics

After implementation, you should see:

- **Device response time**: < 100ms (down from 500ms)
- **System throughput**: 10x more concurrent device connections
- **Error rate**: < 0.1% for device communications
- **Queue processing**: < 1 second lag for FHIR processing
- **Resource usage**: 30% reduction in main API CPU usage

## Next Steps

1. **Start with Phase 1** (queue service) - minimal risk
2. **Monitor performance improvements**
3. **Move to Phase 2** when comfortable
4. **Run migration** during maintenance window
5. **Monitor and optimize** based on actual usage patterns 