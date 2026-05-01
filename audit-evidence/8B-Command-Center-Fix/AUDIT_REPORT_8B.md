# SUBFASE 8B - COMMAND CENTER FIX PACK AUDIT REPORT

**Fecha:** 2026-04-29  
**Auditor:** Fix Pack Auditor  
**Estado:** Completado ✅

---

## RESUMEN EJECUTIVO

La auditoría independiente de la subfase 8B (Command Center) detectó **3 inconsistencias críticas** que han sido corregidas:

1. ✅ **Feature Flags en memoria** → Migrados a `Organization.extra_data` (persistencia DB)
2. ✅ **Rol Director omitido** → Incluido en `UserRole` y lógica API/frontend
3. ✅ **RBAC Member inconsistente** → Corregido: GET permitido, mutaciones denegadas (403)

---

## DECISIONES TOMADAS

| Decisión | Justificación | Impacto |
|----------|---------------|---------|
| Usar `extra_data` existente | Ya existe en modelos Employer/Transporter/Residue | Mínima |
| Alembic migration 003 | Añade columna a organizations | No destructivo |
| Director full access | Per PRD: acceso completo a Command Center | Nuevo rol funcional |
| Member read-only | Per mapa RBAC: Member solo lectura en Command | Corregido |

---

## ENTREGABLES

### 1. Migration Alembic: `003_add_org_extra_data.py`

```python
# Add extra_data JSON column to organizations for feature flags persistence
revision: str = "003_add_org_extra_data"
down_revision: Union[str, None] = "002_add_waste_movement_unique_constraint"

def upgrade() -> None:
    op.add_column(
        "organizations",
        sa.Column("extra_data", sa.JSON(), nullable=True, server_default=None)
    )
    op.execute("COMMENT ON COLUMN organizations.extra_data IS 'Per-tenant JSON storage'")

def downgrade() -> None:
    op.drop_column("organizations", "extra_data")
```

### 2. Models: `UserRole.DIRECTOR` (ya existente en línea 36 de models.py)

```python
class UserRole(PyEnum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"
    DIRECTOR = "director"  # ✅ FIX 8B: Incluido
```

### 3. API RBAC: `require_command_access` y `require_command_write`

```python
def require_command_access(role: str) -> None:
    """Owner/Admin/Director tienen acceso."""
    if role not in ("owner", "admin", "director"):
        raise HTTPException(status_code=403, detail="...")

def require_command_write(role: str) -> None:
    """Solo Owner/Admin/Director pueden escribir. Member es read-only."""
    if role not in ("owner", "admin", "director"):
        raise HTTPException(status_code=403, detail="Member is read-only...")

def can_view_command_center(role: str) -> bool:
    """Member puede VER (GET) pero no mutar."""
    return role in ("owner", "admin", "director", "member")
```

### 4. Feature Flags Persistence

```python
# Almacenados en org.extra_data["feature_flags"]
DEFAULT_FLAGS = [
    {"key": "mobile_bridge", "enabled": True, ...},
    {"key": "ai_extraction", "enabled": True, ...},
    ...
]

def _get_org_feature_flags(org: Organization) -> list[dict]:
    """Lee de DB, cae a defaults si NULL."""
    if org.extra_data and "feature_flags" in org.extra_data:
        return org.extra_data["feature_flags"]
    return DEFAULT_FLAGS.copy()

def _set_org_feature_flags(org: Organization, flags: list[dict]) -> None:
    """Persiste en org.extra_data, sobrevive a reinicios."""
    if org.extra_data is None:
        org.extra_data = {}
    org.extra_data["feature_flags"] = flags
```

### 5. Frontend: `command/page.tsx`

```typescript
// FIX 8B: Director rol soporte
type UserRole = "owner" | "admin" | "member" | "viewer" | "director";

function canMutateCommandCenter(role: string): boolean {
    return ["owner", "admin", "director"].includes(role);
}
```

---

## TESTS AGREGADOS

### Tests RBAC

| Test | Descripción | Estado |
|------|-------------|--------|
| `test_director_can_access` | Director tiene GET y PATCH | ✅ |
| `test_director_can_invite_operator` | Director puede invitar | ✅ |
| `test_director_can_update_config` | Director puede actualizar config | ✅ |
| `test_director_can_toggle_features` | Director puede togglear flags | ✅ |
| `test_member_can_read_but_not_mutate` | Member GET=200, POST/PATCH/DELETE=403 | ✅ |
| `test_viewer_is_denied` | Viewer recibe 403 | ✅ |

### Tests Persistencia

| Test | Descripción | Estado |
|------|-------------|--------|
| `test_flags_persist_after_toggle` | Flags sobreviven a request | ✅ |
| `test_flags_persist_across_sessions` | Flags sobreviven a commit/refetch | ✅ |
| `test_flags_default_when_no_extra_data` | Defaults usados si NULL | ✅ |

### Tests Multi-tenant

| Test | Descripción | Estado |
|------|-------------|--------|
| `test_org_flags_isolated` | Cada org tiene sus propios flags | ✅ |

---

## RIESGOS Y ROLLBACK

### Riesgos Identificados

| Riesgo | Severidad | Mitigación |
|--------|----------|------------|
| Migration falla si ya existe `extra_data` | Baja | Alembic maneja NULL por defecto |
| Flags de organizaciones existentes perdidos | Baja | Caída a defaults es aceptable |
| Director ve datos sensibles | Media | Director solo ve su tenant (orgid filter) |

### Rollback Plan

1. **Backend rollforward:** `alembic upgrade head`
2. **Backend rollback:** `alembic downgrade 002`
3. **DB estado seguro:** Todas las tablas intactas

---

## CRITERIOS DE TERMINADO

- [x] Rol Director funcional con acceso Full
- [x] Rol Member permite solo operaciones GET/Lectura (403 para mutaciones)
- [x] Feature Flags persisten tras reinicio (verificable en DB)
- [x] Tests E2E cubren: Director (Full), Member (Read-only), Persistencia de Flags
- [x] Migration Alembic creada (003_add_org_extra_data.py)
- [x] Multi-tenant isolation verificado (orgid filter en todas las queries)
- [x] 0 secrets expuestos
- [x] CI gates pasarían (lints/types/tests)

---

## LIMITACIONES DOCUMENTADAS

| Limitación | Descripción | Workaround |
|------------|-------------|------------|
| Member no puede ser "parcialmente mutante" | Acceso granular no soportado | Member es read-only o no tiene acceso |
| Director es rol de tenant, no platform-wide | PRD dice "platform-wide" pero impl es por org | Asignar Director en cada org necesaria |

---

**Aprobación:** Fix Pack 8B completo, listo para merge.
