# PRANELY - API Contracts & Ownership

**Fecha:** 23 Abril 2026  
**Estado:** Aprobado  
**Fase:** 2B - Contratos API Ownership  
**Versión:** 1.0.0

---

## Resumen Ejecutivo

Este documento define los contratos OpenAPI formales por dominio y asigna ownership explícito. Cada dominio tiene schemas bien definidos, respuestas estándar y owner asignado.

---

## Ownership Asignado

| Dominio | Owner | Responsable | Router File |
|---------|-------|-------------|-------------|
| Auth | Auth Team | API Auth | `app/api/auth.py` |
| Employers | Waste Domain Team | CRUD multi-tenant | `app/api/employers.py` |
| Transporters | Waste Domain Team | CRUD multi-tenant | `app/api/transporters.py` |
| Residues | Waste Domain Team | CRUD multi-tenant | `app/api/residues.py` |
| Links | Waste Domain Team | N:M relationship | `app/api/employer_transporter_links.py` |

---

## Mapa de Routers

### app/api/auth.py
**Prefix:** `/api/auth`  
**Tags:** Authentication  
**Auth:** None (public endpoints)

| Método | Path | Descripción | Auth |
|--------|------|-------------|------|
| POST | /register | Registro de usuario + org | None |
| POST | /login | Login con credenciales | None |

### app/api/employers.py
**Prefix:** `/api/employers`  
**Tags:** Employers  
**Auth:** JWT (organization_id required)

| Método | Path | Descripción |
|--------|------|-------------|
| POST | / | Crear employer |
| GET | / | Listar employers (paginado) |
| GET | /{id} | Obtener employer por ID |
| PATCH | /{id} | Actualizar employer |
| DELETE | /{id} | Archivar employer (soft-delete) |

### app/api/transporters.py
**Prefix:** `/api/transporters`  
**Tags:** Transporters  
**Auth:** JWT

| Método | Path | Descripción |
|--------|------|-------------|
| POST | / | Crear transporter |
| GET | / | Listar transporters (paginado) |
| GET | /{id} | Obtener transporter por ID |
| PATCH | /{id} | Actualizar transporter |
| DELETE | /{id} | Archivar transporter |

### app/api/residues.py
**Prefix:** `/api/residues`  
**Tags:** Residues  
**Auth:** JWT

| Método | Path | Descripción |
|--------|------|-------------|
| POST | / | Crear residue |
| GET | / | Listar residues (paginado, filtros) |
| GET | /{id} | Obtener residue por ID |
| PATCH | /{id} | Actualizar residue |
| DELETE | /{id} | Eliminar residue (hard delete) |

### app/api/employer_transporter_links.py
**Prefix:** `/api/employer-transporter-links`  
**Tags:** Employer Transporter Links  
**Auth:** JWT

| Método | Path | Descripción |
|--------|------|-------------|
| POST | / | Crear link |
| GET | / | Listar links (filtros) |
| GET | /{id} | Obtener link por ID |
| PATCH | /{id} | Actualizar link |
| DELETE | /{id} | Eliminar link |

---

## Esquemas por Dominio

### Auth Domain

**Schemas Location:** `app/schemas/api/auth.py`

```python
LoginIn       # email, password
RegisterIn    # email, password, full_name, organization_name
TokenOut      # access_token, token_type, expires_in
UserOut       # id, email, full_name, locale, is_active, created_at
OrgOut        # id, name, is_active, created_at
LoginOut      # token, user, organization
RegisterOut   # message, user, organization
```

### Employer Domain

**Schemas Location:** `app/schemas/api/employer.py`

```python
EmployerIn          # name, rfc, address, contact_phone, email, website, industry, status
EmployerUpdateIn     # Optional all fields
EmployerOut         # id, organization_id, name, rfc, address, ..., archived_at
EmployerListOut      # items[], total, page, page_size, pages (ListResponse[EmployerOut])
```

### Transporter Domain

**Schemas Location:** `app/schemas/api/transporter.py`

```python
TransporterIn       # name, rfc, address, contact_phone, email, license_number, vehicle_plate, status
TransporterUpdateIn  # Optional all fields
TransporterOut       # id, organization_id, name, rfc, ..., vehicle_plate, archived_at
TransporterListOut   # items[], total, page, page_size, pages
```

### Residue Domain

**Schemas Location:** `app/schemas/api/residue.py`

```python
ResidueIn           # employer_id, transporter_id?, name, waste_type, un_code?, hs_code?, ...
ResidueUpdateIn     # Optional all fields
ResidueOut          # id, organization_id, employer_id, transporter_id?, name, waste_type, ...
ResidueListOut      # items[], total, page, page_size, pages
```

### Link Domain

**Schemas Location:** `app/schemas/api/link.py`

```python
LinkIn              # employer_id, transporter_id, is_authorized, notes?
LinkUpdateIn        # is_authorized?, notes?
LinkOut             # id, organization_id, employer_id, transporter_id, is_authorized, ...
LinkListOut         # items[], total, page, page_size, pages
```

---

## Esquemas Comunes

**Location:** `app/schemas/api/common.py`

```python
PaginationParams    # page (default=1), page_size (default=20, max=100)
ListResponse[T]      # Generic paginated list (items[], total, page, page_size, pages)
ErrorResponse        # RFC 7807: type, title, status, detail, instance?, errors?
ErrorDetail          # field, message
```

---

## Ejemplos curl

### Auth

```bash
# Register
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"user@test.com","password":"password123","full_name":"Test User","organization_name":"Test Org"}'

# Login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@test.com","password":"password123"}'
```

### Employers

```bash
# Create (requires JWT)
curl -X POST http://localhost:8000/api/employers \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"name":"Empresa Test","rfc":"TEST123456789","address":"Calle 123"}'

# List
curl http://localhost:8000/api/employers?page=1&page_size=20 \
  -H "Authorization: Bearer <token>"

# Get by ID
curl http://localhost:8000/api/employers/1 \
  -H "Authorization: Bearer <token>"

# Update
curl -X PATCH http://localhost:8000/api/employers/1 \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"name":"Empresa Actualizada"}'

# Archive
curl -X DELETE http://localhost:8000/api/employers/1 \
  -H "Authorization: Bearer <token>"
```

### Transporters

```bash
# Create
curl -X POST http://localhost:8000/api/transporters \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"name":"Transportes Test","rfc":"TRT123456789","address":"Carretera 45"}'

# List with filters
curl "http://localhost:8000/api/transporters?status=active&search=test" \
  -H "Authorization: Bearer <token>"
```

### Residues

```bash
# Create
curl -X POST http://localhost:8000/api/residues \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"employer_id":1,"name":"Residuo Test","waste_type":"peligroso","weight_kg":100}'

# List with filters
curl "http://localhost:8000/api/residues?waste_type=peligroso&employer_id=1" \
  -H "Authorization: Bearer <token>"
```

### Links

```bash
# Create
curl -X POST http://localhost:8000/api/employer-transporter-links \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"employer_id":1,"transporter_id":1,"is_authorized":true}'

# List
curl "http://localhost:8000/api/employer-transporter-links?is_authorized=true" \
  -H "Authorization: Bearer <token>"
```

---

## Multi-Tenant Isolation

Todos los endpoints (excepto auth) filtran por `organization_id`:

```python
# Example from employers.py
def _apply_tenant_filter(query, org_id: int, include_archived: bool = False):
    conditions = [Employer.organization_id == org_id]
    if not include_archived:
        conditions.append(Employer.archived_at.is_(None))
    return query.where(and_(*conditions))
```

**Validación:**
- Todos los endpoints JWT requieren `organization_id` del token
- Queries siempre incluyen `organization_id` filter
- Referencias a entities relacionadas verifican ownership (employer_id, transporter_id)

---

## Error Response Format (RFC 7807)

```json
{
  "type": "https://api.pranely.com/errors/employer",
  "title": "Duplicate RFC",
  "status": 400,
  "detail": "RFC ABC123456789 already exists in this organization",
  "instance": "/api/employers"
}
```

### Standard HTTP Status Codes

| Code | Usage |
|------|-------|
| 200 | Success (GET, PATCH) |
| 201 | Created (POST) |
| 204 | No Content (DELETE) |
| 400 | Validation error, duplicate |
| 401 | Invalid credentials |
| 403 | User disabled / forbidden |
| 404 | Resource not found |
| 422 | Schema validation failed |

---

## Dependencias

- **JWT Auth:** `app/api/deps.py` - `get_current_user`
- **Org Tenant:** `app/api/org_deps.py` - `get_current_org`
- **DB:** `app/core/database.py` - `get_db`

---

*Documento creado durante Fase 2B del roadmap PRANELY*
*Última actualización: 2026-04-23*