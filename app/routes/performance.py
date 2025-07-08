from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any
from app.services.auth import require_auth
from app.services.cache_service import cache_service
from app.services.index_manager import index_manager
from app.services.mongo import mongodb_service
from app.utils.error_definitions import create_success_response
from config import logger

router = APIRouter(
    prefix="/admin/performance",
    tags=["admin", "Performance Monitoring"],
    dependencies=[Depends(require_auth())]
)

@router.get("/cache/stats", response_model=Dict[str, Any])
async def get_cache_statistics(
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get Redis cache statistics"""
    try:
        stats = await cache_service.get_cache_stats()
        
        return create_success_response(
            message="Cache statistics retrieved successfully",
            data=stats
        ).dict()
        
    except Exception as e:
        logger.error(f"Failed to get cache stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/cache/clear", response_model=Dict[str, Any])
async def clear_cache(
    pattern: str = "*",
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Clear cache entries matching pattern"""
    try:
        if current_user.get("role") not in ["admin", "superadmin"]:
            raise HTTPException(status_code=403, detail="Admin privileges required")
        
        deleted_count = await cache_service.delete_pattern(pattern)
        
        return create_success_response(
            message=f"Cleared {deleted_count} cache entries",
            data={"deleted_count": deleted_count, "pattern": pattern}
        ).dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to clear cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/indexes/{collection_name}", response_model=Dict[str, Any])
async def get_index_usage(
    collection_name: str,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get index usage statistics for a collection"""
    try:
        usage_stats = await index_manager.analyze_index_usage(collection_name)
        
        return create_success_response(
            message=f"Index usage stats for {collection_name}",
            data={
                "collection": collection_name,
                "indexes": usage_stats
            }
        ).dict()
        
    except Exception as e:
        logger.error(f"Failed to get index usage: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/slow-queries", response_model=Dict[str, Any])
async def get_slow_queries(
    limit: int = 10,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get recent slow queries from MongoDB profiler"""
    try:
        # Get slow queries from system.profile collection
        profile_collection = mongodb_service.db.system.profile
        
        slow_queries = await profile_collection.find(
            {"millis": {"$gt": 100}},  # Queries taking more than 100ms
            {"ns": 1, "command": 1, "millis": 1, "ts": 1}
        ).sort("ts", -1).limit(limit).to_list(length=limit)
        
        # Clean up for JSON serialization
        for query in slow_queries:
            query["_id"] = str(query.get("_id", ""))
            query["ts"] = query.get("ts", "").isoformat() if hasattr(query.get("ts"), "isoformat") else str(query.get("ts", ""))
        
        return create_success_response(
            message="Recent slow queries retrieved",
            data={
                "queries": slow_queries,
                "count": len(slow_queries)
            }
        ).dict()
        
    except Exception as e:
        logger.error(f"Failed to get slow queries: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/indexes/recommend", response_model=Dict[str, Any])
async def recommend_indexes(
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get index recommendations based on slow queries"""
    try:
        if current_user.get("role") not in ["admin", "superadmin"]:
            raise HTTPException(status_code=403, detail="Admin privileges required")
        
        # Get recent slow queries
        profile_collection = mongodb_service.db.system.profile
        
        slow_queries = await profile_collection.find(
            {"millis": {"$gt": 100}},
            {"ns": 1, "command": 1}
        ).sort("ts", -1).limit(50).to_list(length=50)
        
        # Process queries for recommendations
        processed_queries = []
        for query in slow_queries:
            ns = query.get("ns", "")
            if "." in ns:
                db, collection = ns.split(".", 1)
                command = query.get("command", {})
                
                processed_queries.append({
                    "collection": collection,
                    "filter": command.get("filter", {}),
                    "sort": command.get("sort", [])
                })
        
        # Get recommendations
        recommendations = await index_manager.recommend_indexes(processed_queries)
        
        return create_success_response(
            message="Index recommendations generated",
            data={
                "recommendations": recommendations,
                "analyzed_queries": len(processed_queries)
            }
        ).dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate index recommendations: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/database/stats", response_model=Dict[str, Any])
async def get_database_statistics(
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get overall database performance statistics"""
    try:
        # Get database stats
        db_stats = await mongodb_service.db.command("dbStats")
        
        # Get collection stats for main collections
        collections = ["patients", "hospitals", "blood_pressure_histories", "fhir_observations"]
        collection_stats = {}
        
        for coll_name in collections:
            try:
                stats = await mongodb_service.db.command("collStats", coll_name)
                collection_stats[coll_name] = {
                    "count": stats.get("count", 0),
                    "size": stats.get("size", 0),
                    "avgObjSize": stats.get("avgObjSize", 0),
                    "indexSize": stats.get("totalIndexSize", 0),
                    "nindexes": stats.get("nindexes", 0)
                }
            except:
                pass
        
        return create_success_response(
            message="Database statistics retrieved",
            data={
                "database": {
                    "collections": db_stats.get("collections", 0),
                    "dataSize": db_stats.get("dataSize", 0),
                    "storageSize": db_stats.get("storageSize", 0),
                    "indexes": db_stats.get("indexes", 0),
                    "indexSize": db_stats.get("indexSize", 0)
                },
                "collections": collection_stats
            }
        ).dict()
        
    except Exception as e:
        logger.error(f"Failed to get database stats: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 