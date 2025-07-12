from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query, Request, HTTPException
from fastapi.responses import StreamingResponse
from typing import Dict, Any, Optional, AsyncGenerator
import asyncio
import json
from datetime import datetime
from sse_starlette.sse import EventSourceResponse

from app.services.auth import require_auth, auth_service
from app.services.websocket_manager import websocket_manager, Rooms
from app.services.realtime_events import realtime_events
from app.utils.error_definitions import create_error_response
from config import logger

router = APIRouter(prefix="/realtime", tags=["realtime"])

# WebSocket endpoints

@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None)
):
    """
    Main WebSocket endpoint for real-time communication
    
    Authentication: Pass JWT token as query parameter
    Example: ws://localhost:5054/realtime/ws?token=YOUR_JWT_TOKEN
    """
    connection_id = None
    
    try:
        # Authenticate user
        if not token:
            await websocket.close(code=4001, reason="Authentication required")
            return
        
        try:
            user_info = auth_service.verify_token_with_stardust(token)
            user_id = user_info.get("username", "unknown")
        except Exception as e:
            await websocket.close(code=4001, reason="Invalid token")
            return
        
        # Accept connection
        connection_id = await websocket_manager.connect(
            websocket, 
            user_id,
            metadata={
                "user_info": user_info,
                "connected_from": websocket.client.host if websocket.client else "unknown"
            }
        )
        
        # Handle messages
        while True:
            data = await websocket.receive_json()
            await handle_websocket_message(connection_id, data)
            
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {connection_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        if connection_id:
            await websocket_manager.disconnect(connection_id)


async def handle_websocket_message(connection_id: str, data: Dict[str, Any]):
    """Handle incoming WebSocket messages"""
    message_type = data.get("type")
    
    if message_type == "subscribe":
        # Subscribe to a room
        room = data.get("room")
        if room:
            await websocket_manager.subscribe_to_room(connection_id, room)
    
    elif message_type == "unsubscribe":
        # Unsubscribe from a room
        room = data.get("room")
        if room:
            await websocket_manager.leave_room(connection_id, room)
    
    elif message_type == "ping":
        # Respond to ping
        await websocket_manager.send_to_connection(connection_id, {
            "type": "pong",
            "timestamp": datetime.utcnow().isoformat()
        })
    
    elif message_type == "message":
        # Handle custom messages (for future use)
        logger.debug(f"Received message from {connection_id}: {data}")
    
    else:
        # Unknown message type
        await websocket_manager.send_to_connection(connection_id, {
            "type": "error",
            "message": f"Unknown message type: {message_type}",
            "timestamp": datetime.utcnow().isoformat()
        })


# Patient-specific WebSocket endpoints

@router.websocket("/ws/patient/{patient_id}")
async def patient_websocket(
    websocket: WebSocket,
    patient_id: str,
    token: Optional[str] = Query(None)
):
    """
    WebSocket endpoint for patient-specific updates
    Automatically subscribes to patient vitals, alerts, and general updates
    """
    connection_id = None
    
    try:
        # Authenticate user
        if not token:
            await websocket.close(code=4001, reason="Authentication required")
            return
        
        try:
            user_info = auth_service.verify_token_with_stardust(token)
            user_id = user_info.get("username", "unknown")
        except Exception as e:
            await websocket.close(code=4001, reason="Invalid token")
            return
        
        # Accept connection
        connection_id = await websocket_manager.connect(
            websocket, 
            user_id,
            metadata={
                "patient_id": patient_id,
                "user_info": user_info
            }
        )
        
        # Auto-subscribe to patient rooms
        await websocket_manager.subscribe_to_room(connection_id, Rooms.patient_updates(patient_id))
        await websocket_manager.subscribe_to_room(connection_id, Rooms.patient_vitals(patient_id))
        await websocket_manager.subscribe_to_room(connection_id, Rooms.patient_alerts(patient_id))
        
        # Keep connection alive
        while True:
            # Wait for client messages (mainly for ping/pong)
            try:
                data = await asyncio.wait_for(websocket.receive_json(), timeout=30.0)
                await handle_websocket_message(connection_id, data)
            except asyncio.TimeoutError:
                # Send ping to keep connection alive
                await websocket_manager.send_to_connection(connection_id, {
                    "type": "ping",
                    "timestamp": datetime.utcnow().isoformat()
                })
                
    except WebSocketDisconnect:
        logger.info(f"Patient WebSocket disconnected: {connection_id}")
    except Exception as e:
        logger.error(f"Patient WebSocket error: {e}")
    finally:
        if connection_id:
            await websocket_manager.disconnect(connection_id)


# Hospital-specific WebSocket endpoints

@router.websocket("/ws/hospital/{hospital_id}")
async def hospital_websocket(
    websocket: WebSocket,
    hospital_id: str,
    token: Optional[str] = Query(None)
):
    """
    WebSocket endpoint for hospital-specific updates
    Automatically subscribes to hospital alerts, device updates, and general updates
    """
    connection_id = None
    
    try:
        # Authenticate user
        if not token:
            await websocket.close(code=4001, reason="Authentication required")
            return
        
        try:
            user_info = auth_service.verify_token_with_stardust(token)
            user_id = user_info.get("username", "unknown")
        except Exception as e:
            await websocket.close(code=4001, reason="Invalid token")
            return
        
        # Accept connection
        connection_id = await websocket_manager.connect(
            websocket, 
            user_id,
            metadata={
                "hospital_id": hospital_id,
                "user_info": user_info
            }
        )
        
        # Auto-subscribe to hospital rooms
        await websocket_manager.subscribe_to_room(connection_id, Rooms.hospital_updates(hospital_id))
        await websocket_manager.subscribe_to_room(connection_id, Rooms.hospital_alerts(hospital_id))
        await websocket_manager.subscribe_to_room(connection_id, Rooms.hospital_devices(hospital_id))
        
        # Keep connection alive
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_json(), timeout=30.0)
                await handle_websocket_message(connection_id, data)
            except asyncio.TimeoutError:
                await websocket_manager.send_to_connection(connection_id, {
                    "type": "ping",
                    "timestamp": datetime.utcnow().isoformat()
                })
                
    except WebSocketDisconnect:
        logger.info(f"Hospital WebSocket disconnected: {connection_id}")
    except Exception as e:
        logger.error(f"Hospital WebSocket error: {e}")
    finally:
        if connection_id:
            await websocket_manager.disconnect(connection_id)


# Server-Sent Events (SSE) endpoints

async def event_generator(request: Request, event_filter: Optional[Dict[str, Any]] = None) -> AsyncGenerator:
    """Generate SSE events based on filters"""
    client_id = f"sse_{datetime.utcnow().timestamp()}"
    
    try:
        # Send initial connection event
        yield {
            "event": "connected",
            "data": json.dumps({
                "client_id": client_id,
                "timestamp": datetime.utcnow().isoformat()
            })
        }
        
        # Create event queue
        event_queue = asyncio.Queue()
        
        # Register listener for events
        async def event_listener(data: Dict[str, Any]):
            await event_queue.put(data)
        
        # Register listeners based on filter
        if event_filter:
            if "patient_id" in event_filter:
                realtime_events.register_listener("patient.vitals.update", event_listener)
                realtime_events.register_listener("patient.alert", event_listener)
            if "hospital_id" in event_filter:
                realtime_events.register_listener("hospital.alert", event_listener)
            if "device_type" in event_filter and "device_id" in event_filter:
                realtime_events.register_listener("device.data.update", event_listener)
                realtime_events.register_listener("device.status.change", event_listener)
        else:
            # Register for all system alerts
            realtime_events.register_listener("system.alert", event_listener)
        
        # Send events as they arrive
        while True:
            # Check if client is still connected
            if await request.is_disconnected():
                break
            
            try:
                # Wait for event with timeout
                data = await asyncio.wait_for(event_queue.get(), timeout=30.0)
                
                # Filter event if needed
                if event_filter:
                    # Check if event matches filter
                    if "patient_id" in event_filter and data.get("patient_id") != event_filter["patient_id"]:
                        continue
                    if "hospital_id" in event_filter and data.get("hospital_id") != event_filter["hospital_id"]:
                        continue
                    if "device_id" in event_filter and data.get("device_id") != event_filter["device_id"]:
                        continue
                
                # Send event
                yield {
                    "event": data.get("event_type", "update"),
                    "data": json.dumps(data)
                }
                
            except asyncio.TimeoutError:
                # Send keepalive
                yield {
                    "event": "keepalive",
                    "data": json.dumps({
                        "timestamp": datetime.utcnow().isoformat()
                    })
                }
                
    except asyncio.CancelledError:
        logger.info(f"SSE client disconnected: {client_id}")
    finally:
        # Unregister all listeners
        # This is simplified - in production, track registered listeners properly
        logger.info(f"Cleaning up SSE client: {client_id}")


@router.get("/events")
async def sse_endpoint(
    request: Request,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """
    Server-Sent Events endpoint for real-time updates
    
    Returns all system-wide events
    """
    return EventSourceResponse(event_generator(request))


@router.get("/events/patient/{patient_id}")
async def patient_sse_endpoint(
    request: Request,
    patient_id: str,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """
    Server-Sent Events endpoint for patient-specific updates
    
    Returns events related to a specific patient
    """
    event_filter = {"patient_id": patient_id}
    return EventSourceResponse(event_generator(request, event_filter))


@router.get("/events/hospital/{hospital_id}")
async def hospital_sse_endpoint(
    request: Request,
    hospital_id: str,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """
    Server-Sent Events endpoint for hospital-specific updates
    
    Returns events related to a specific hospital
    """
    event_filter = {"hospital_id": hospital_id}
    return EventSourceResponse(event_generator(request, event_filter))


@router.get("/events/device/{device_type}/{device_id}")
async def device_sse_endpoint(
    request: Request,
    device_type: str,
    device_id: str,
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """
    Server-Sent Events endpoint for device-specific updates
    
    Returns events related to a specific device
    """
    event_filter = {
        "device_type": device_type,
        "device_id": device_id
    }
    return EventSourceResponse(event_generator(request, event_filter))


# WebSocket statistics endpoint

@router.get("/stats")
async def get_websocket_stats(
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """Get WebSocket connection statistics"""
    stats = websocket_manager.get_stats()
    
    return {
        "success": True,
        "data": stats,
        "timestamp": datetime.utcnow().isoformat()
    }


# Test event publishing endpoint (for development)

@router.post("/test/publish")
async def test_publish_event(
    event_data: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(require_auth())
):
    """
    Test endpoint to publish events (development only)
    
    Example payload:
    {
        "event_type": "patient.vitals.update",
        "patient_id": "507f1f77bcf86cd799439011",
        "vitals": {
            "blood_pressure": {"systolic": 120, "diastolic": 80},
            "heart_rate": 72,
            "temperature": 36.5
        }
    }
    """
    if current_user.get("role") not in ["admin", "superadmin"]:
        raise HTTPException(
            status_code=403,
            detail="Admin privileges required for test endpoints"
        )
    
    event_type = event_data.pop("event_type", "test.event")
    await realtime_events.publish_event(event_type, event_data)
    
    return {
        "success": True,
        "message": f"Event '{event_type}' published",
        "timestamp": datetime.utcnow().isoformat()
    } 