# 8A MOBILE BRIDGE - FastAPI Endpoints & WebSocket
# Session QR + realtime sync para app móvil

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, Request
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession

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

router = APIRouter(prefix="/api/bridge", tags=["bridge"])

# In-memory session store (production: use Redis with TTL)
bridge_sessions: dict[str, dict] = {}
active_websockets: dict[str, WebSocket] = {}

# Token config for bridge WS
BRIDGE_TOKEN_EXPIRY_MINUTES = 5
BRIDGE_ALGORITHM = "HS256"


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
    
    # Store session with tenant isolation
    bridge_sessions[qr_token] = {
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
    session = bridge_sessions.get(qr_token)
    
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
        expires_at=session["expires_at"],
        is_expired=is_expired,
    )


@router.post("/session/{qr_token}/extend", response_model=BridgeSessionExtendResponse)
async def extend_bridge_session(
    qr_token: str,
    user: User = Depends(get_current_active_user),
):
    """Extender sesión QR por 5 minutos más."""
    session = bridge_sessions.get(qr_token)
    
    if not session:
        raise HTTPException(404, "Sesión no encontrada")
    
    if session["user_id"] != user.id:
        raise HTTPException(403, "No tienes acceso a esta sesión")
    
    if session["connected"]:
        raise HTTPException(400, "No se puede extender sesión mientras está conectada")
    
    session["expires_at"] = datetime.utcnow() + timedelta(minutes=BRIDGE_TOKEN_EXPIRY_MINUTES)
    
    logger.info(f"Bridge session extended: qr_token={qr_token}, new_expires={session['expires_at']}")
    
    return BridgeSessionExtendResponse(
        status="extended",
        expires_at=session["expires_at"],
    )


@router.delete("/session/{qr_token}", response_model=BridgeSessionCloseResponse)
async def close_bridge_session(
    qr_token: str,
    user: User = Depends(get_current_active_user),
):
    """Cerrar sesión QR."""
    session = bridge_sessions.get(qr_token)
    
    if not session:
        raise HTTPException(404, "Sesión no encontrada")
    
    if session["user_id"] != user.id:
        raise HTTPException(403, "No tienes acceso a esta sesión")
    
    # Clean up websocket if active
    session_id = session["session_id"]
    if session_id in active_websockets:
        try:
            await active_websockets[session_id].close(code=1000, reason="Session closed by user")
        except Exception as e:
            logger.warning(f"Error closing websocket for session {session_id}: {e}")
        finally:
            if session_id in active_websockets:
                del active_websockets[session_id]
    
    del bridge_sessions[qr_token]
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
    
    # Find session by ID (not QR token)
    session = None
    qr_token = None
    for qt, sess in bridge_sessions.items():
        if sess["session_id"] == session_id:
            session = sess
            qr_token = qt
            break
    
    if not session:
        logger.warning(f"WS bridge rejected: session not found, session_id={session_id}")
        await websocket.close(code=4004, reason="Sesión no encontrada")
        return
    
    # Check expiration
    if datetime.utcnow() > session["expires_at"]:
        logger.warning(f"WS bridge rejected: session expired, session_id={session_id}")
        await websocket.close(code=4010, reason="Sesión expirada")
        return
    
    # Accept connection
    await websocket.accept()
    active_websockets[session_id] = websocket
    session["connected"] = True
    
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
                    session["scanned_count"] += 1
                    session["last_sync"] = datetime.utcnow()
                    
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
                            "scanned_count": session["scanned_count"],
                            "last_sync": session["last_sync"].isoformat() if session["last_sync"] else None,
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
        # Cleanup
        session["connected"] = False
        if session_id in active_websockets:
            del active_websockets[session_id]
        logger.info(f"WS bridge cleanup: session_id={session_id}")


# Background task: cleanup expired sessions
_cleanup_task: Optional[asyncio.Task] = None


async def _cleanup_expired_sessions_periodic():
    """Periodic cleanup of expired sessions."""
    while True:
        try:
            await asyncio.sleep(60)  # Check every minute
            now = datetime.utcnow()
            expired_tokens = [
                qt for qt, sess in bridge_sessions.items()
                if now > sess["expires_at"]
            ]
            for qt in expired_tokens:
                session = bridge_sessions.pop(qt, None)
                if session and session.get("connected"):
                    session_id = session["session_id"]
                    if session_id in active_websockets:
                        try:
                            await active_websockets[session_id].close(code=4010, reason="Session expired")
                        except Exception:
                            pass
                        del active_websockets[session_id]
                logger.info(f"Expired session cleaned: qr_token={qt}")
        except Exception as e:
            logger.error(f"Cleanup task error: {e}")


def start_cleanup_task():
    """Start the background cleanup task."""
    global _cleanup_task
    if _cleanup_task is None or _cleanup_task.done():
        _cleanup_task = asyncio.create_task(_cleanup_expired_sessions_periodic())


def stop_cleanup_task():
    """Stop the background cleanup task."""
    global _cleanup_task
    if _cleanup_task:
        _cleanup_task.cancel()
        _cleanup_task = None


def get_bridge_stats() -> dict:
    """Get current bridge session statistics."""
    now = datetime.utcnow()
    return {
        "total_sessions": len(bridge_sessions),
        "active_connections": len(active_websockets),
        "expired_sessions": sum(1 for s in bridge_sessions.values() if now > s["expires_at"]),
        "sessions": [
            {
                "qr_token": qt,
                "session_id": s["session_id"],
                "connected": s["connected"],
                "scanned_count": s["scanned_count"],
                "expires_at": s["expires_at"].isoformat(),
                "is_expired": now > s["expires_at"],
            }
            for qt, s in bridge_sessions.items()
        ]
    }
