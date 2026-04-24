# Fase 1B: Modelos de dominio - Diagrama de Entidades

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              ORGANIZATION (Tenant)                           │
│  ┌─────────────────┐                                                        │
│  │ id: PK          │◄─────────────────────────────────────────┐             │
│  │ name            │                                          │             │
│  │ ...             │                                          │             │
│  └─────────────────┘                                          │             │
│         │                                                      │             │
│         │ 1:N                                                  │             │
│         ▼                                                      │             │
├─────────────────────────────────────────────────────────────────────────────┤
│                              EMPLOYER (Empresa)                             │
│  ┌─────────────────┐  1:N        ┌─────────────────────────┐              │
│  │ id: PK          │───────────►│ residues                │              │
│  │ organization_id │◄───────────│ employer_id: FK         │              │
│  │ name            │             └─────────────────────────┘              │
│  │ rfc             │                        ▲                              │
│  │ address         │                        │                              │
│  │ contact_phone   │                        │ 1:1 (optional)               │
│  │ email           │                        │                              │
│  │ status          │             ┌─────────────────────────┐              │
│  │ metadata_json   │             │ TRANSPORTER             │              │
│  └─────────────────┘  N:M         │ (Transportista)         │              │
│         │              ┌─────────►│                         │              │
│         │              │          │ id: PK                  │              │
│         ▼              │          │ organization_id        │              │
│  ┌───────────────────────────┐   │ name                    │              │
│  │ EMPLOYER_TRANSPORTER_LINK │   │ rfc                      │              │
│  │ (Association Table)       │   │ address                  │              │
│  ├───────────────────────────┤   │ license_number          │              │
│  │ id: PK                   │   │ vehicle_plate            │              │
│  │ employer_id: FK          │◄──│ status                   │              │
│  │ transporter_id: FK       │   │ metadata_json            │              │
│  │ is_authorized            │   └─────────────────────────┘              │
│  │ authorization_date       │                                          │
│  │ notes                    │             1:N                           │
│  └───────────────────────────┘             ▼                            │
│                                        ┌─────────────────────────┐        │
│                                        │ RESIDUE (Residuo)      │        │
│                                        ├─────────────────────────┤        │
│                                        │ id: PK                  │        │
│                                        │ organization_id: FK    │        │
│                                        │ employer_id: FK        │        │
│                                        │ transporter_id: FK (opt)│       │
│                                        │ name                    │        │
│                                        │ waste_type: ENUM        │        │
│                                        │ un_code                 │        │
│                                        │ hs_code                 │        │
│                                        │ description             │        │
│                                        │ weight_kg               │        │
│                                        │ volume_m3               │        │
│                                        │ status: ENUM            │        │
│                                        │ metadata_json           │        │
│                                        └─────────────────────────┘        │
└─────────────────────────────────────────────────────────────────────────────┘

ENUMERACIONES:
═══════════════════════════════════════════════════════════════════════════
EntityStatus: ACTIVE | INACTIVE | PENDING
WasteType:    PELIGROSO | ESPECIAL | INERTE | ORGANICO | RECICLABLE
WasteStatus:  PENDING | ACTIVE | DISPOSED | ARCHIVED

RELACIONES:
═══════════════════════════════════════════════════════════════════════════
• Organization → Employer: 1:N (cascade delete)
• Organization → Transporter: 1:N (cascade delete)
• Organization → Residue: 1:N
• Employer → Residue: 1:N (cascade delete)
• Employer ↔ Transporter: N:M via EmployerTransporterLink
• Transporter → Residue: 1:N (optional)

NOTAS:
═══════════════════════════════════════════════════════════════════════════
• Todos los modelos incluyen organization_id para multi-tenancy
• metadata_json permite campos adicionales sin cambiar esquema
• Timestamps automáticos (created_at, updated_at)
• Soft-delete via status (no hard delete en MVP)