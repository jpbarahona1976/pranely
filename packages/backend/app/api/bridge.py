# 8A MOBILE BRIDGE - FastAPI Endpoints & WebSocket
# Session QR + realtime sync para app móvil

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, Request
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis

from app.api.deps import get_current_active_user, get_current_active_admin
from app.core.config import settings
from app.core.database import get_db
from app.models import User
from app.schemas.bridge import (
    BridgeSessionCreate,
    BridgeSessionResponse,
    BridgeSessionStatus,
    BridgeSessionExtendResponse,
    BridgeSessionCloseResponse,
)

logger = logging.getLogger("pranely.bridge")

router = APIRouter(prefix="/bridge", tags=["bridge"])

# Token config for bridge WS
BRIDGE_TOKEN_EXPIRY_MINUTES = 5
BRIDGE_SESSION_TTL = BRIDGE_TOKEN_EXPIRY_MINUTES * 60  # Redis TTL in seconds
BRIDGE_ALGORITHM = "HS256"

# Redis key prefixes
BRIDGE_SESSION_PREFIX = "pranely:bridge:session:"
BRIDGE_WS_PREFIX = "pranely:bridge:ws:"


async def _get_redis() -> redis.Redis:
    """Get Redis client for bridge sessions."""
    return redis.from_url(settings.REDIS_URL, decode_responses=True)


async def _store_session(qr_token: str, session_data: dict) -> None:
    """Store session in Redis with TTL."""
    r = await _get_redis()
    key = f"{BRIDGE_SESSION_PREFIX}{qr_token}"
    # Serialize datetime objects
    serializable = {
        k: v.isoformat() if isinstance(v, datetime) else v
        for k, v in session_data.items()
    }
    await r.setex(key, BRIDGE_SESSION_TTL, json.dumps(serializable))


async def _get_session(qr_token: str) -> Optional[dict]:
    """Get session from Redis."""
    r = await _get_redis()
    key = f"{BRIDGE_SESSION_PREFIX}{qr_token}"
    data = await r.get(key)
    if data:
        return json.loads(data)
    return None


async def _delete_session(qr_token: str) -> None:
    """Delete session from Redis."""
    r = await _get_redis()
    key = f"{BRIDGE_SESSION_PREFIX}{qr_token}"
    await r.delete(key)


async def _store_ws_session(session_id: str, ws_data: dict) -> None:
    """Store WebSocket session data."""
    r = await _get_redis()
    key = f"{BRIDGE_WS_PREFIX}{session_id}"
    await r.setex(key, BRIDGE_SESSION_TTL, json.dumps(ws_data))


async def _get_ws_session(session_id: str) -> Optional[dict]:
    """Get WebSocket session data."""
    r = await _get_redis()
    key = f"{BRIDGE_WS_PREFIX}{session_id}"
    data = await r.get(key)
    if data:
        return json.loads(data)
    return None


async def _delete_ws_session(session_id: str) -> None:
    """Delete WebSocket session data."""
    r = await _get_redis()
    key = f"{BRIDGE_WS_PREFIX}{session_id}"
    await r.delete(key)


def _create_bridge_token(session_id: str, user_id: int, org_id: int) -> str:
    """Create a temporary JWT token for bridge WebSocket auth."""
    expire = datetime.utcnow() + timedelta(minutes=BRIDGE_TOKEN_EXPIRY_MINUTES)
    payload = {
        "sub": str(user_id),
        "org_id": org_id,
        "session_id": session_id,
        "type": "bridge",
        "exp": expire,
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=BRIDGE_ALGORITHM)


def _decode_bridge_token(token: str) -> Optional[dict]:
    """Decode and validate a bridge token."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[BRIDGE_ALGORITHM])
        if payload.get("type") != "bridge":
            return None
        return payload
    except Exception:
        return None


@router.post("/session", response_model=BridgeSessionResponse)
async def create_bridge_session(
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Crear sesión QR temporal para conectar app móvil.
    Token expira en 5 minutos.
    Requiere rol: owner, admin, o member.
    """
    # RBAC: Owner/Admin/Member pueden crear bridge sessions
    # Viewer NO puede crear sesiones (no muta)
    allowed_roles = {"owner", "admin", "member"}
    user_role = getattr(user, "role", None) or "member"
    
    if user_role not in allowed_roles:
        logger.warning(f"Bridge session denied for user {user.id}, role={user_role}")
        raise HTTPException(403, "Rol no autorizado para crear sesiones bridge")
    
    session_id = str(uuid4())
    qr_token = str(uuid4())[:16].upper()
    expires_at = datetime.utcnow() + timedelta(minutes=BRIDGE_TOKEN_EXPIRY_MINUTES)
    
    # Get org_id from user
    org_id = getattr(user, "org_id", None) or 1  # Default fallback
    
    # Create bridge token for WS auth
    ws_token = _create_bridge_token(session_id, user.id, org_id)
    
    # Store session in Redis with TTL
    session_data = {
        "session_id": session_id,
        "user_id": user.id,
        "org_id": org_id,
        "qr_token": qr_token,
        "expires_at": expires_at,
        "connected": False,
        "last_sync": None,
        "scanned_count": 0,
        "created_at": datetime.utcnow(),
    }
    await _store_session(qr_token, session_data)
    
    # Build WS URL based on environment
    ws_base = settings.API_URL.replace("http", "ws") if hasattr(settings, "API_URL") else "ws://localhost:8000"
    ws_url = f"{ws_base}/ws/bridge/{session_id}"
    
    logger.info(
        f"Bridge session created: session_id={session_id}, qr_token={qr_token}, "
        f"user_id={user.id}, org_id={org_id}"
    )
    
    return BridgeSessionResponse(
        session_id=session_id,
        qr_token=qr_token,
        expires_at=expires_at,
        ws_url=ws_url,
        ws_token=ws_token,
    )


@router.get("/session/{qr_token}", response_model=BridgeSessionStatus)
async def get_bridge_session_status(
    qr_token: str,
    user: User = Depends(get_current_active_user),
):
    """Verificar estado de una sesión QR."""
    session = await _get_session(qr_token)
    
    if not session:
        raise HTTPException(404, "Sesión no encontrada")
    
    # Tenant isolation: solo el dueño puede ver su sesión
    if session["user_id"] != user.id:
        logger.warning(f"Bridge session access denied: user {user.id} tried session owned by {session['user_id']}")
        raise HTTPException(403, "No tienes acceso a esta sesión")
    
    is_expired = datetime.utcnow() > session["expires_at"]
    
    return BridgeSessionStatus(
        session_id=session["session_id"],
        status="expired" if is_expired else ("connected" if session["connected"] else "waiting"),
        scanned_count=session["scanned_count"],
        expires_at=datetime.fromisoformat(session["expires_at"]) if isinstance(session["expires_at"], str) else session["expires_at"],
        is_expired=is_expired,
    )


@router.post("/session/{qr_token}/extend", response_model=BridgeSessionExtendResponse)
async def extend_bridge_session(
    qr_token: str,
    user: User = Depends(get_current_active_user),
):
    """Extender sesión QR por 5 minutos más."""
    session = await _get_session(qr_token)
    
    if not session:
        raise HTTPException(404, "Sesión no encontrada")
    
    if session["user_id"] != user.id:
        raise HTTPException(403, "No tienes acceso a esta sesión")
    
    if session["connected"]:
        raise HTTPException(400, "No se puede extender sesión mientras está conectada")
    
    new_expires = datetime.utcnow() + timedelta(minutes=BRIDGE_TOKEN_EXPIRY_MINUTES)
    session["expires_at"] = new_expires
    await _store_session(qr_token, session)
    
    logger.info(f"Bridge session extended: qr_token={qr_token}, new_expires={new_expires}")
    
    return BridgeSessionExtendResponse(
        status="extended",
        expires_at=new_expires,
    )


@router.delete("/session/{qr_token}", response_model=BridgeSessionCloseResponse)
async def close_bridge_session(
    qr_token: str,
    user: User = Depends(get_current_active_user),
):
    """Cerrar sesión QR."""
    session = await _get_session(qr_token)
    
    if not session:
        raise HTTPException(404, "Sesión no encontrada")
    
    if session["user_id"] != user.id:
        raise HTTPException(403, "No tienes acceso a esta sesión")
    
    # Clean up websocket if active
    session_id = session["session_id"]
    ws_session = await _get_ws_session(session_id)
    if ws_session and ws_session.get("websocket_active"):
        # Note: Actual WS closure handled by the WS endpoint itself
        pass
    
    await _delete_session(qr_token)
    await _delete_ws_session(session_id)
    logger.info(f"Bridge session closed: qr_token={qr_token}")
    
    return BridgeSessionCloseResponse()


@router.websocket("/ws/bridge/{session_id}")
async def bridge_websocket(websocket: WebSocket, session_id: str):
    """
    WebSocket para sync en tiempo real entre dashboard y app móvil.
    - Auth via bridge token (limited JWT)
    - Heartbeat
    - Reconnect con backoff exponencial (client-side)
    - Expiración de sesión
    """
    bridge_token = websocket.query_params.get("token")
    request_id = str(uuid4())[:8]
    
    logger.info(f"WS bridge attempt: session_id={session_id}, request_id={request_id}")
    
    # Validate bridge token
    if not bridge_token:
        logger.warning(f"WS bridge rejected: no token, session_id={session_id}")
        await websocket.close(code=4001, reason="Token requerido")
        return
    
    payload = _decode_bridge_token(bridge_token)
    if not payload:
        logger.warning(f"WS bridge rejected: invalid token, session_id={session_id}")
        await websocket.close(code=4002, reason="Token inválido")
        return
    
    # Validate session_id matches token
    if payload.get("session_id") != session_id:
        logger.warning(f"WS bridge rejected: session mismatch, token={payload.get('session_id')}, ws={session_id}")
        await websocket.close(code=4003, reason="Sesión no coincide")
        return
    
    # Find session by ID (not QR token) - search all sessions
    # This requires iterating through Redis keys
    r = await _get_redis()
    session = None
    qr_token = None
    expires_at_str = None
    
    async for key in r.scan_iter(match=f"{BRIDGE_SESSION_PREFIX}*"):
        data = await r.get(key)
        if data:
            sess_data = json.loads(data)
            if sess_data.get("session_id") == session_id:
                session = sess_data
                qr_token = key.replace(BRIDGE_SESSION_PREFIX, "")
                expires_at_str = sess_data.get("expires_at")
                break
    
    if not session:
        logger.warning(f"WS bridge rejected: session not found, session_id={session_id}")
        await websocket.close(code=4004, reason="Sesión no encontrada")
        return
    
    # Check expiration
    expires_at = datetime.fromisoformat(expires_at_str) if isinstance(expires_at_str, str) else expires_at_str
    if datetime.utcnow() > expires_at:
        logger.warning(f"WS bridge rejected: session expired, session_id={session_id}")
        await websocket.close(code=4010, reason="Sesión expirada")
        return
    
    # Accept connection
    await websocket.accept()
    
    # Update session as connected in Redis
    session["connected"] = True
    await _store_session(qr_token, session)
    await _store_ws_session(session_id, {"websocket_active": True})
    
    logger.info(f"WS bridge connected: session_id={session_id}, user_id={payload['sub']}, request_id={request_id}")
    
    # Send initial state
    await websocket.send_json({
        "type": "connected",
        "data": {
            "session_id": session_id,
            "scanned_count": session["scanned_count"],
            "server_time": datetime.utcnow().isoformat(),
            "request_id": request_id,
        }
    })
    
    reconnect_count = 0
    
    try:
        while True:
            try:
                # Wait for messages
                data = await websocket.receive_json()
                msg_type = data.get("type", "")
                
                logger.debug(f"WS message: session_id={session_id}, type={msg_type}")
                
                if msg_type == "scan":
                    # Mobile scanned a QR/document
                    session["scanned_count"] = session.get("scanned_count", 0) + 1
                    session["last_sync"] = datetime.utcnow()
                    
                    # Update in Redis
                    await _store_session(qr_token, session)
                    
                    await websocket.send_json({
                        "type": "scan_ack",
                        "data": {
                            "scanned_count": session["scanned_count"],
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                    })
                    logger.debug(f"Scan processed: session_id={session_id}, total={session['scanned_count']}")
                    
                elif msg_type == "sync_request":
                    await websocket.send_json({
                        "type": "sync_response",
                        "data": {
                            "session_id": session_id,
                            "scanned_count": session.get("scanned_count", 0),
                            "last_sync": session.get("last_sync"),
                            "server_time": datetime.utcnow().isoformat(),
                        }
                    })
                    
                elif msg_type == "heartbeat":
                    await websocket.send_json({
                        "type": "heartbeat_ack",
                        "data": {"server_time": datetime.utcnow().isoformat()}
                    })
                    reconnect_count = 0  # Reset on successful communication
                    
            except Exception as e:
                logger.error(f"WS message parse error: session_id={session_id}, error={e}")
                continue
                
    except WebSocketDisconnect:
        logger.info(f"WS bridge disconnected: session_id={session_id}, request_id={request_id}")
    except Exception as e:
        logger.error(f"WS bridge error: session_id={session_id}, error={e}")
    finally:
        # Cleanup - update session in Redis
        session["connected"] = False
        if qr_token:
            await _store_session(qr_token, session)
        await _delete_ws_session(session_id)
        logger.info(f"WS bridge cleanup: session_id={session_id}")


# Background task: cleanup expired sessions
_cleanup_task: Optional[asyncio.Task] = None


async def _cleanup_expired_sessions_periodic():
    """Periodic cleanup of expired sessions."""
    r = await _get_redis()
    while True:
        try:
            await asyncio.sleep(60)  # Check every minute
            now = datetime.utcnow()
            
            # Scan for expired sessions
            async for key in r.scan_iter(match=f"{BRIDGE_SESSION_PREFIX}*"):
                data = await r.get(key)
                if data:
                    sess = json.loads(data)
                    expires_at = datetime.fromisoformat(sess["expires_at"]) if isinstance(sess["expires_at"], str) else sess["expires_at"]
                    if now > expires_at:
                        await r.delete(key)
                        session_id = sess.get("session_id")
                        if session_id:
                            await _delete_ws_session(session_id)
                        logger.info(f"Expired session cleaned: {key}")
        except Exception as e:
            logger.error(f"Cleanup task error: {e}")


async def start_cleanup_task():
    """Start the background cleanup task."""
    global _cleanup_task
    if _cleanup_task is None or _cleanup_task.done():
        _cleanup_task = asyncio.create_task(_cleanup_expired_sessions_periodic())
    await asyncio.sleep(0)  # Ensure task starts


def stop_cleanup_task():
    """Stop the background cleanup task."""
    global _cleanup_task
    if _cleanup_task:
        _cleanup_task.cancel()
        _cleanup_task = None


async def get_bridge_stats() -> dict:
    """Get current bridge session statistics."""
    r = await _get_redis()
    now = datetime.utcnow()
    sessions = []
    total = 0
    expired = 0
    active = 0
    
    async for key in r.scan_iter(match=f"{BRIDGE_SESSION_PREFIX}*"):
        data = await r.get(key)
        if data:
            total += 1
            s = json.loads(data)
            expires_at = datetime.fromisoformat(s["expires_at"]) if isinstance(s["expires_at"], str) else s["expires_at"]
            is_expired = now > expires_at
            if is_expired:
                expired += 1
            if s.get("connected"):
                active += 1
            sessions.append({
                "qr_token": key.replace(BRIDGE_SESSION_PREFIX, ""),
                "session_id": s["session_id"],
                "connected": s.get("connected", False),
                "scanned_count": s.get("scanned_count", 0),
                "expires_at": s["expires_at"],
                "is_expired": is_expired,
            })
    
    return {
        "total_sessions": total,
        "active_connections": active,
        "expired_sessions": expired,
        "sessions": sessions
    }
