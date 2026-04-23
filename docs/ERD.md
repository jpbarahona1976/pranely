# PRANELY - Entity Relationship Diagram

## Overview

This document shows the complete data model for PRANELY SaaS B2B waste management system.
Includes entities from all phases: Organization/User management, Domain entities, Audit, and Billing.

**Compliance**: NOM-052-SEMARNAT-2005, NOM-151, LFPDPPP
**Multi-tenancy**: All tenant-scoped entities include `organization_id` FK and index.

---

## ERD Diagram (Mermaid)

```mermaid
erDiagram
    Organization ||--|{ Membership : has
    Organization ||--|| Subscription : has
    Organization ||--|{ Employer : has
    Organization ||--|{ Transporter : has
    Organization ||--|{ Residue : has
    Organization ||--|{ AuditLog : has
    Organization ||--|{ LegalAlert : has
    Organization ||--|{ WasteMovement : has
    
    User ||--|{ Membership : has
    
    Membership }|--|| Organization : belongs_to
    Membership }|--|| User : belongs_to
    
    Subscription }|--|| Organization : for
    Subscription }|--|| BillingPlan : uses
    Subscription ||--|{ UsageCycle : tracks
    
    Employer ||--|{ Residue : generates
    Employer ||--|{ EmployerTransporterLink : authorized_with
    Transporter ||--|{ EmployerTransporterLink : authorized_with
    Transporter ||--|{ Residue : transports
    Residue }|--|| Employer : belongs_to
    Residue }|--o| Transporter : transported_by
    
    EmployerTransporterLink }|--|| Organization : belongs_to
    EmployerTransporterLink }|--|| Employer : links
    EmployerTransporterLink }|--|| Transporter : links

    %% Enums shown as annotations
    Membership::role {
        enum: OWNER ADMIN MEMBER VIEWER
    }
    
    Residue::waste_type {
        enum: PELIGROSO ESPECIAL INERTE ORGANICO RECICLABLE
    }
    
    Residue::status {
        enum: PENDING ACTIVE DISPOSED ARCHIVED
    }
    
    LegalAlert::severity {
        enum: LOW MEDIUM HIGH CRITICAL
    }
    
    LegalAlert::status {
        enum: OPEN ACKNOWLEDGED RESOLVED DISMISSED
    }
    
    Subscription::status {
        enum: ACTIVE PAUSED CANCELLED PAST_DUE
    }
    
    WasteMovement::status {
        enum: PENDING IN_REVIEW VALIDATED REJECTED EXCEPTION
    }
```

---

## Entity Definitions

### Core Entities (Phase 0-1)

#### Organization
| Field | Type | Constraints | Description |
|-------|------|------------|-------------|
| id | INTEGER | PK | Primary key |
| name | VARCHAR(255) | NOT NULL | Organization name |
| legal_name | VARCHAR(255) | NULLABLE | Legal business name |
| industry | VARCHAR(100) | NULLABLE | Industry sector |
| segment | VARCHAR(100) | NULLABLE | generator, gestor |
| stripe_customer_id | VARCHAR(255) | NULLABLE | Stripe customer ID |
| is_active | BOOLEAN | NOT NULL DEFAULT TRUE | Active status |
| created_at | TIMESTAMPTZ | NOT NULL | Creation timestamp |
| updated_at | TIMESTAMPTZ | NULLABLE | Last update timestamp |

**Indexes**: None (PK default)

#### User
| Field | Type | Constraints | Description |
|-------|------|------------|-------------|
| id | INTEGER | PK | Primary key |
| email | VARCHAR(255) | UNIQUE NOT NULL | User email |
| hashed_password | VARCHAR(255) | NOT NULL | Argon2id hashed password |
| full_name | VARCHAR(255) | NULLABLE | Display name |
| locale | VARCHAR(10) | DEFAULT 'es' | Language preference |
| is_active | BOOLEAN | NOT NULL DEFAULT TRUE | Active status |
| created_at | TIMESTAMPTZ | NOT NULL | Creation timestamp |
| updated_at | TIMESTAMPTZ | NULLABLE | Last update timestamp |

**Indexes**: `email` (unique)

#### Membership
| Field | Type | Constraints | Description |
|-------|------|------------|-------------|
| id | INTEGER | PK | Primary key |
| user_id | INTEGER | FK(users.id) NOT NULL | User reference |
| organization_id | INTEGER | FK(organizations.id) NOT NULL | Organization reference |
| role | ENUM | NOT NULL DEFAULT MEMBER | User role in org |
| created_at | TIMESTAMPTZ | NOT NULL | When membership created |

**Indexes**: `user_id, organization_id` (unique constraint)

---

### Domain Entities (Phase 1B)

#### Employer
| Field | Type | Constraints | Description |
|-------|------|------------|-------------|
| id | INTEGER | PK | Primary key |
| organization_id | INTEGER | FK(orgs.id) NOT NULL | **Tenant scope** |
| name | VARCHAR(255) | NOT NULL | Company name |
| rfc | VARCHAR(13) | NOT NULL | Mexican tax ID |
| address | VARCHAR(500) | NOT NULL | Physical address |
| contact_phone | VARCHAR(30) | NULLABLE | Contact phone |
| email | VARCHAR(255) | NULLABLE | Contact email |
| website | VARCHAR(255) | NULLABLE | Company website |
| industry | VARCHAR(100) | NULLABLE | Industry sector |
| status | ENUM | NOT NULL DEFAULT ACTIVE | Entity status |
| archived_at | TIMESTAMPTZ | NULLABLE INDEX | Soft delete timestamp |
| extra_data | JSON | NULLABLE | Additional metadata |
| created_at | TIMESTAMPTZ | NOT NULL | Creation timestamp |
| updated_at | TIMESTAMPTZ | NULLABLE | Last update timestamp |

**Indexes**: 
- `organization_id, rfc` (unique)
- `organization_id, status`

**Multi-tenancy**: Required

#### Transporter
| Field | Type | Constraints | Description |
|-------|------|------------|-------------|
| id | INTEGER | PK | Primary key |
| organization_id | INTEGER | FK(orgs.id) NOT NULL | **Tenant scope** |
| name | VARCHAR(255) | NOT NULL | Company name |
| rfc | VARCHAR(13) | NOT NULL | Mexican tax ID |
| address | VARCHAR(500) | NOT NULL | Business address |
| contact_phone | VARCHAR(30) | NULLABLE | Contact phone |
| email | VARCHAR(255) | NULLABLE | Contact email |
| license_number | VARCHAR(100) | NULLABLE | Transport license |
| vehicle_plate | VARCHAR(20) | NULLABLE | Primary vehicle |
| status | ENUM | NOT NULL DEFAULT ACTIVE | Entity status |
| archived_at | TIMESTAMPTZ | NULLABLE INDEX | Soft delete timestamp |
| extra_data | JSON | NULLABLE | Additional metadata |
| created_at | TIMESTAMPTZ | NOT NULL | Creation timestamp |
| updated_at | TIMESTAMPTZ | NULLABLE | Last update timestamp |

**Indexes**: 
- `organization_id, rfc` (unique)
- `organization_id, status`

**Multi-tenancy**: Required

#### Residue
| Field | Type | Constraints | Description |
|-------|------|------------|-------------|
| id | INTEGER | PK | Primary key |
| organization_id | INTEGER | FK(orgs.id) NOT NULL | **Tenant scope** |
| employer_id | INTEGER | FK(employers.id) NOT NULL | Waste generator |
| transporter_id | INTEGER | FK(transporters.id) NULLABLE | Waste transporter |
| name | VARCHAR(255) | NOT NULL | Residue name |
| waste_type | ENUM | NOT NULL | NOM-052 classification |
| un_code | VARCHAR(20) | NULLABLE | UN dangerous goods code |
| hs_code | VARCHAR(20) | NULLABLE | HS code |
| description | VARCHAR(1000) | NULLABLE | Waste description |
| weight_kg | FLOAT | NULLABLE | Weight in kg |
| volume_m3 | FLOAT | NULLABLE | Volume in m3 |
| status | ENUM | NOT NULL DEFAULT PENDING | Processing status |
| extra_data | JSON | NULLABLE | Additional metadata |
| created_at | TIMESTAMPTZ | NOT NULL | Creation timestamp |
| updated_at | TIMESTAMPTZ | NULLABLE | Last update timestamp |

**Indexes**: 
- `organization_id, employer_id`
- `organization_id, status`

**Multi-tenancy**: Required
**Compliance**: NOM-052 waste classification

#### EmployerTransporterLink
| Field | Type | Constraints | Description |
|-------|------|------------|-------------|
| id | INTEGER | PK | Primary key |
| organization_id | INTEGER | FK(orgs.id) NOT NULL | **Tenant scope** |
| employer_id | INTEGER | FK(employers.id) NOT NULL | Employer reference |
| transporter_id | INTEGER | FK(transporters.id) NOT NULL | Transporter reference |
| is_authorized | BOOLEAN | NOT NULL DEFAULT TRUE | Authorization status |
| authorization_date | TIMESTAMPTZ | NULLABLE | When authorized |
| notes | VARCHAR(500) | NULLABLE | Additional notes |
| created_at | TIMESTAMPTZ | NOT NULL | Creation timestamp |

**Indexes**: 
- `organization_id, employer_id, transporter_id` (unique)
- `organization_id`

**Multi-tenancy**: Required

---

### Audit Entities (Phase 3C)

#### AuditLog
| Field | Type | Constraints | Description |
|-------|------|------------|-------------|
| id | INTEGER | PK | Primary key |
| organization_id | INTEGER | FK(orgs.id) NOT NULL | **Tenant scope** |
| user_id | INTEGER | NULLABLE | User who performed action |
| action | VARCHAR(50) | NOT NULL | Action type |
| resource_type | VARCHAR(50) | NOT NULL | Type of resource |
| resource_id | VARCHAR(100) | NULLABLE | ID of resource |
| result | ENUM | NOT NULL DEFAULT SUCCESS | Operation result |
| payload_json | JSON | NULLABLE | **PII-redacted** payload |
| ip_address | VARCHAR(45) | NULLABLE | Client IP (IPv6 ready) |
| user_agent | TEXT | NULLABLE | Client user agent |
| timestamp | TIMESTAMPTZ | NOT NULL INDEX | Event timestamp |

**Indexes**: 
- `organization_id, timestamp`
- `user_id, timestamp`
- `resource_type, resource_id`
- `timestamp`

**Multi-tenancy**: Required
**Compliance**: NOM-151, LFPDPPP (PII redaction)
**Retention**: 5 years

---

### Waste Movement Entities (Phase 4A)

#### WasteMovement
| Field | Type | Constraints | Description |
|-------|------|------------|-------------|
| id | INTEGER | PK | Primary key |
| organization_id | INTEGER | FK(orgs.id) NOT NULL | **Tenant scope** |
| manifest_number | VARCHAR(100) | NOT NULL | Manifest document number |
| movement_type | VARCHAR(50) | NULLABLE | Type of movement |
| quantity | FLOAT | NULLABLE | Quantity |
| unit | VARCHAR(20) | NULLABLE | Unit of measure |
| date | TIMESTAMPTZ | NULLABLE | Movement date |
| confidence_score | FLOAT | NULLABLE | AI confidence 0-1 |
| status | VARCHAR(20) | NOT NULL DEFAULT 'pending' | Processing status |
| is_immutable | BOOLEAN | NOT NULL DEFAULT FALSE | Cannot be modified |
| archived_at | TIMESTAMPTZ | NULLABLE | Archive timestamp |
| file_path | VARCHAR(500) | NULLABLE | Document file path |
| orig_filename | VARCHAR(255) | NULLABLE | Original filename |
| created_at | TIMESTAMPTZ | NOT NULL | Creation timestamp |
| updated_at | TIMESTAMPTZ | NULLABLE | Last update timestamp |

**Indexes**: 
- `organization_id, timestamp`
- `manifest_number`

**Multi-tenancy**: Required
**Compliance**: NOM-052-SEMARNAT-2005

---

### Billing Entities (Phase 4A)

#### BillingPlan
| Field | Type | Constraints | Description |
|-------|------|------------|-------------|
| id | INTEGER | PK | Primary key |
| code | ENUM | UNIQUE NOT NULL | Plan code (free/pro/enterprise) |
| name | VARCHAR(100) | NOT NULL | Display name |
| description | VARCHAR(500) | NULLABLE | Plan description |
| price_usd_cents | INTEGER | NOT NULL DEFAULT 0 | Price in USD cents |
| doc_limit | INTEGER | NOT NULL DEFAULT 100 | Document limit (0=unlimited) |
| doc_limit_period | VARCHAR(20) | NOT NULL DEFAULT 'monthly' | Limit period |
| features_json | JSON | NULLABLE | Feature flags |
| is_active | BOOLEAN | NOT NULL DEFAULT TRUE | Plan availability |
| created_at | TIMESTAMPTZ | NOT NULL | Creation timestamp |
| updated_at | TIMESTAMPTZ | NULLABLE | Last update timestamp |

**Indexes**: `code` (unique)

#### Subscription
| Field | Type | Constraints | Description |
|-------|------|------------|-------------|
| id | INTEGER | PK | Primary key |
| organization_id | INTEGER | FK(orgs.id) UNIQUE NOT NULL | **Tenant scope** |
| plan_id | INTEGER | FK(billing_plans.id) NOT NULL | Plan reference |
| stripe_sub_id | VARCHAR(255) | UNIQUE NULLABLE | Stripe subscription ID |
| stripe_customer_id | VARCHAR(255) | NULLABLE | Stripe customer ID |
| status | ENUM | NOT NULL DEFAULT ACTIVE | Subscription status |
| started_at | TIMESTAMPTZ | NOT NULL | Subscription start |
| current_period_start | TIMESTAMPTZ | NULLABLE | Current billing period start |
| current_period_end | TIMESTAMPTZ | NULLABLE | Current billing period end |
| cancelled_at | TIMESTAMPTZ | NULLABLE | Cancellation timestamp |
| metadata_json | JSON | NULLABLE | Additional metadata |
| created_at | TIMESTAMPTZ | NOT NULL | Creation timestamp |
| updated_at | TIMESTAMPTZ | NULLABLE | Last update timestamp |

**Indexes**: 
- `organization_id` (unique)
- `status`

**Multi-tenancy**: Required (one per org)

#### UsageCycle
| Field | Type | Constraints | Description |
|-------|------|------------|-------------|
| id | INTEGER | PK | Primary key |
| subscription_id | INTEGER | FK(subscriptions.id) NOT NULL | Subscription reference |
| month_year | VARCHAR(7) | NOT NULL | Period (YYYY-MM) |
| docs_used | INTEGER | NOT NULL DEFAULT 0 | Documents processed |
| docs_limit | INTEGER | NOT NULL DEFAULT 100 | Documents allowed |
| is_locked | BOOLEAN | NOT NULL DEFAULT FALSE | Period locked |
| overage_docs | INTEGER | NOT NULL DEFAULT 0 | Docs over limit |
| overage_charged_cents | INTEGER | NOT NULL DEFAULT 0 | Overage charges |
| created_at | TIMESTAMPTZ | NOT NULL | Creation timestamp |
| updated_at | TIMESTAMPTZ | NULLABLE | Last update timestamp |

**Indexes**: `subscription_id, month_year` (unique), `month_year`

**Multi-tenancy**: Via Subscription relationship

---

### Legal/Compliance Entities (Phase 4A)

#### LegalAlert
| Field | Type | Constraints | Description |
|-------|------|------------|-------------|
| id | INTEGER | PK | Primary key |
| organization_id | INTEGER | FK(orgs.id) NOT NULL | **Tenant scope** |
| norma | VARCHAR(50) | NOT NULL | Norma (NOM-052, LFPDPPP, etc.) |
| title | VARCHAR(255) | NOT NULL | Alert title |
| description | VARCHAR(2000) | NULLABLE | Alert description |
| severity | ENUM | NOT NULL DEFAULT MEDIUM | Alert severity |
| status | ENUM | NOT NULL DEFAULT OPEN | Alert status |
| related_resource_type | VARCHAR(50) | NULLABLE | Related entity type |
| related_resource_id | VARCHAR(100) | NULLABLE | Related entity ID |
| acknowledged_at | TIMESTAMPTZ | NULLABLE | When acknowledged |
| resolved_at | TIMESTAMPTZ | NULLABLE | When resolved |
| resolution_notes | VARCHAR(1000) | NULLABLE | Resolution details |
| metadata_json | JSON | NULLABLE | Additional metadata |
| created_at | TIMESTAMPTZ | NOT NULL | Creation timestamp |
| updated_at | TIMESTAMPTZ | NULLABLE | Last update timestamp |

**Indexes**: 
- `organization_id, status`
- `severity`

**Multi-tenancy**: Required
**Compliance**: NOM-052, NOM-151, LFPDPPP

---

## Enums Reference

### UserRole
```python
OWNER = "owner"    # Full access
ADMIN = "admin"    # Admin access
MEMBER = "member"  # Standard access
VIEWER = "viewer"  # Read-only access
```

### EntityStatus
```python
ACTIVE = "active"
INACTIVE = "inactive"
PENDING = "pending"
```

### WasteType (NOM-052)
```python
PELIGROSO = "peligroso"    # Hazardous - requires special handling
ESPECIAL = "especial"      # Special - requires authorization
INERTE = "inerte"          # Inert - minimal regulation
ORGANICO = "organico"      # Organic - biodegradable
RECICLABLE = "reciclable"  # Recyclable - recovery encouraged
```

### WasteStatus
```python
PENDING = "pending"
ACTIVE = "active"
DISPOSED = "disposed"
ARCHIVED = "archived"
```

### MovementStatus (NOM-052 compliance)
```python
PENDING = "pending"
IN_REVIEW = "in_review"
VALIDATED = "validated"
REJECTED = "rejected"
EXCEPTION = "exception"
```

### AlertSeverity
```python
LOW = "low"
MEDIUM = "medium"
HIGH = "high"
CRITICAL = "critical"
```

### AlertStatus
```python
OPEN = "open"
ACKNOWLEDGED = "acknowledged"
RESOLVED = "resolved"
DISMISSED = "dismissed"
```

### SubscriptionStatus
```python
ACTIVE = "active"
PAUSED = "paused"
CANCELLED = "cancelled"
PAST_DUE = "past_due"
```

### BillingPlanCode
```python
FREE = "free"
PRO = "pro"
ENTERPRISE = "enterprise"
```

### AuditLogResult
```python
SUCCESS = "success"
FAILURE = "failure"
PARTIAL = "partial"
```

---

## Multi-Tenancy Model

All tenant-scoped entities include:
1. `organization_id` foreign key to `organizations.id`
2. Index on `organization_id`
3. Query filters always include `organization_id`

```
┌─────────────────────────────────────────────────────────────┐
│                    TENANT ISOLATION MODEL                    │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Query Pattern:                                              │
│  ─────────────                                               │
│  SELECT * FROM entities                                      │
│  WHERE organization_id = :current_org_id                      │
│                                                              │
│  Index Strategy:                                              │
│  ─────────────                                               │
│  ✓ organization_id + timestamp (for lists)                   │
│  ✓ organization_id + status (for filters)                     │
│  ✓ organization_id + resource_id (for lookups)                │
│                                                              │
│  Forbidden Pattern:                                          │
│  ───────────────                                             │
│  ✗ SELECT * FROM entities  ← MUST include org_id filter     │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Data Residency (Mexico)

All data is stored with timezone awareness:
- PostgreSQL: `TIMESTAMPTZ` for all timestamps
- Backend: UTC timezone (`datetime.now(timezone.utc)`)
- Configuration: `TZ=America/Mexico_City`

**Retention Policies**:
| Entity | Retention | Basis |
|--------|-----------|-------|
| AuditLog | 5 years | NOM-151 |
| WasteMovement | 5 years | NOM-052 |
| LegalAlert | 5 years | LFPDPPP |
| Subscription | Duration + 1 year | Billing records |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-04-24 | Initial ERD with all Phase 1-4A entities |

---

**Document Status**: Active
**Last Updated**: 2026-04-24
