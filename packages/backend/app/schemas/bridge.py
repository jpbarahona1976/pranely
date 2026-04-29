# 8A MOBILE BRIDGE - Pydantic Schemas
"""Schemas para Mobile Bridge API - Fase 8A."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class BridgeSessionCreate(BaseModel):
    """Request para crear sesión bridge (opcional, defaults válidos)."""
    pass


class BridgeSessionResponse(BaseModel):
    """Response de sesión bridge creada."""
    session_id: str
    qr_token: str
    expires_at: datetime
    ws_url: str
    ws_token: str  # Token temporal para WS
    

class BridgeSessionStatus(BaseModel):
    """Estado de sesión bridge existente."""
    session_id: str
    status: str  # "waiting" | "connected" | "expired"
    scanned_count: int
    expires_at: datetime
    is_expired: bool


class BridgeSessionExtendResponse(BaseModel):
    """Response de extensión de sesión."""
    status: str
    expires_at: datetime


class BridgeSessionCloseResponse(BaseModel):
    """Response de cierre de sesión."""
    status: str = "closed"


class BridgeWSMessage(BaseModel):
    """Mensaje WebSocket para bridge."""
    type: str  # "scan" | "sync_request" | "heartbeat"
    data: Optional[dict] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class BridgeWSConnected(BaseModel):
    """Mensaje de conexión exitosa WS."""
    type: str = "connected"
    session_id: str
    scanned_count: int
    server_time: str


class BridgeWSScanAck(BaseModel):
    """ACK de scan recibido."""
    type: str = "scan_ack"
    scanned_count: int
    timestamp: str


class BridgeWSSyncResponse(BaseModel):
    """Response de sync request."""
    type: str = "sync_response"
    session_id: str
    scanned_count: int
    last_sync: Optional[str]
    server_time: str


class BridgeWSError(BaseModel):
    """Error de WebSocket."""
    type: str = "error"
    code: int
    message: str
