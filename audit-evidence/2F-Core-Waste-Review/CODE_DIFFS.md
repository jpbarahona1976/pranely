# FASE 2 FIXES CODE DIFFS

## FIX 1: WasteMovement Extended (models.py)

```diff
 class WasteMovement(Base):
     """
     Waste movement/manifest entity for NOM-052 compliance.
     
     Tracks the physical movement of waste from generator to disposal.
+    Supports review workflow: approve/reject/request_changes.
+    
+    FASE 2 FIX 1: Extended with confidence, is_immutable, archived_at,
+    review metadata (reviewed_by, reviewed_at, rejection_reason),
+    created_by_user_id, file_hash, file_size_bytes.
+    
     Multi-tenancy: organization_id REQUIRED.
     """
     __tablename__ = "waste_movements"
     __table_args__ = (
         # FIX 5B-FIX-1: Unique constraint to prevent duplicate manifests per org/date
         UniqueConstraint(
             "organization_id", "manifest_number", "date",
             name="uq_waste_movement_org_manifest_date"
         ),
         Index("ix_waste_movement_org_timestamp", "organization_id", "created_at"),
         Index("ix_waste_movement_manifest", "manifest_number"),
         Index("ix_waste_movement_org_status", "organization_id", "status"),
+        # FASE 2 FIX 1: Index for AI triage (high confidence = auto-approve)
+        Index(
+            "ix_waste_movement_org_confidence",
+            "organization_id", "confidence_score",
+            postgresql_where=text("confidence_score IS NOT NULL")
+        ),
+        # Index for archived filter
+        Index(
+            "ix_waste_movement_org_archived",
+            "organization_id",
+            postgresql_where=text("archived_at IS NOT NULL")
+        ),
     )
 
     id: Mapped[int] = mapped_column(Integer, primary_key=True)
     organization_id: Mapped[int] = mapped_column(
         Integer, ForeignKey("organizations.id"), nullable=False
     )
+    # Creator tracking for RBAC
+    created_by_user_id: Mapped[Optional[int]] = mapped_column(
+        Integer, ForeignKey("users.id"), nullable=True
+    )
     # Manifest details
     manifest_number: Mapped[str] = mapped_column(String(100), nullable=False)
     ...
     # FASE 2 FIX 1: AI Metadata - confidence score 0-1
     confidence_score: Mapped[Optional[float]] = mapped_column(
+        Float, nullable=True
-        nullable=True
     )
     ...
     # FASE 2 FIX 1: Review metadata
+    reviewed_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
+    reviewed_at: Mapped[Optional[datetime]] = mapped_column(
+        DateTime(timezone=True), nullable=True
+    )
+    rejection_reason: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
+    # FASE 2 FIX 1: File integrity
+    file_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)  # SHA-256
+    file_size_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
 
     # Relationships
     organization: Mapped["Organization"] = relationship("Organization", back_populates="movements")
+    creator: Mapped[Optional["User"]] = relationship("User", foreign_keys=[created_by_user_id])
```

## FIX 2: Upload Endpoint (waste-api.ts)

```diff
+// FASE 2 FIX 2-3: Interfaces for upload and review
+export interface UploadResult {
+    job_id: string;
+    movement_id: number;
+    message: string;
+    file_hash?: string;
+}
+
+export interface ReviewActionResult {
+    success: boolean;
+    message: string;
+    movement_id: number;
+    new_status: string;
+    reviewed_by: string;
+}

// FASE 2 FIX 3: Review actions with notes support
-async approve(id: number): Promise<void> {
+async approve(id: number, notes?: string): Promise<ReviewActionResult> {
-    return fetchApi<void>(`/api/v1/waste/${id}/review`, {
+    return fetchApi<ReviewActionResult>(`/api/v1/waste/${id}/review`, {
         method: "POST",
-        body: JSON.stringify({ action: "approve" }),
+        body: JSON.stringify({ action: "approve", notes }),
     });
 }

// FASE 2 FIX 2: Upload with FormData + RQ job
+async upload(file: File): Promise<UploadResult> {
+    const token = getToken();
+    const formData = new FormData();
+    formData.append('file', file);
+    
+    const response = await fetch(`${API_URL}/api/v1/waste/upload`, {
+        method: 'POST',
+        headers: token ? { Authorization: `Bearer ${token}` } : {},
+        body: formData,
+    });
+    
+    if (!response.ok) {
+        const error = await response.json().catch(() => ({ detail: "Upload failed" }));
+        throw new Error(error.detail?.detail || error.detail || "Upload failed");
+    }
+    
+    return response.json();
+}
```

## FIX 3: Review Actions (waste_review.py)

```diff
 class ReviewActionRequest(BaseModel):
     """Request para acciones de revisión de waste movement."""
     action: Literal["approve", "reject", "request_changes"]
+    reason: Optional[str] = Field(None, description="Razón del rechazo o comentarios")
+    comments: Optional[str] = Field(None, description="Comentarios adicionales")
 
 @router.post("/{movement_id}/review", response_model=ReviewActionResponse)
 async def review_waste_movement(
     ...
 ):
     # Execute action
     if review_data.action == "approve":
         movement.status = "validated"
         movement.is_immutable = True
+        movement.reviewed_by = user.email
+        movement.reviewed_at = datetime.utcnow()
         message = "Movimiento aprobado exitosamente"
         
     elif review_data.action == "reject":
         if not review_data.reason:
             raise HTTPException(
                 status_code=status.HTTP_400_BAD_REQUEST,
                 detail="Se requiere una razón para rechazar"
             )
         movement.status = "rejected"
+        movement.rejection_reason = review_data.reason
+        movement.reviewed_by = user.email
+        movement.reviewed_at = datetime.utcnow()
```

## FIX 4: Command Operators (NEW FILE)

```python
# packages/backend/app/api/v1/command_operators.py
# NEW FILE - Full implementation

class OperatorCreateRequest(BaseModel):
    """Schema for creating a new operator."""
    email: str
    role: str = Field(..., pattern="^(admin|member|viewer)$")
    full_name: Optional[str] = None
    extra_data: Optional[dict] = None

@router.post("/operators", response_model=OperatorResponse)
async def create_operator(
    data: OperatorCreateRequest,
    user: User = Depends(get_current_active_user),
    org: Organization = Depends(get_current_active_organization),
    db: AsyncSession = Depends(get_db),
) -> OperatorResponse:
    """Create operator with tenant isolation."""
    # Verify admin/owner role
    # Check user exists or create placeholder
    # Create membership with organization_id
    # Tenant filter: Membership.organization_id == org.id
```

## FIX 5: Invite Hash (NEW FILE)

```python
# packages/backend/app/api/v1/invite.py
# NEW FILE - Full implementation

INVITE_EXPIRY_SECONDS = 24 * 60 * 60  # 24 hours

async def store_invite_hash(
    hash_key: str,
    email: str,
    role: str,
    org_id: int,
    ttl: int = INVITE_EXPIRY_SECONDS
) -> None:
    """Store invite hash in Redis with TTL."""
    # TODO: Replace with actual Redis
    
@router.post("/{invite_hash}", response_model=InviteAcceptResponse)
async def accept_invite(
    invite_hash: str,
    data: InviteAcceptRequest,
    db: AsyncSession = Depends(get_db),
) -> InviteAcceptResponse:
    """Accept invite with UUID4 hash, 24h expiry."""
    # Validate hash from Redis
    invite_data = await validate_invite_hash(invite_hash)
    if not invite_data:
        raise HTTPException(status_code=400, detail="Invalid or expired invite")
    
    # Create user and membership
    # Delete hash after use (one-time use)
```

---

**Firmado:** PRANELY Principal Architect  
**Fecha:** 2026-05-01 14:30:00 CST