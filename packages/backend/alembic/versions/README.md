# Alembic Versions Directory

This directory contains Alembic migration scripts for PRANELY.

## Migration Files

### 001_initial_baseline.py
**Revision ID**: 001_initial_baseline  
**Creates**: 13 tables for PRANELY core entities

Creates all tables aligned with Phase 4A model definitions:
- `organizations` - Multi-tenant root entity
- `users` - Authentication entity
- `memberships` - User-Org relationship with role
- `employers` - Waste generator companies
- `transporters` - Waste carrier companies
- `residues` - Tracked waste entities
- `employer_transporter_links` - N:M relationship
- `audit_logs` - NOM-151 compliance
- `billing_plans` - Subscription plans (global)
- `subscriptions` - Org-billing link
- `usage_cycles` - Monthly usage tracking
- `legal_alerts` - Regulatory compliance
- `waste_movements` - NOM-052 manifests

## Creating New Migrations

```bash
# With autogenerate (compare model changes)
python -m alembic revision --autogenerate -m "description"

# Empty migration
python -m alembic revision -m "description"
```

## Naming Convention

Migrations follow the pattern: `{sequence}_{description}.py`

Examples:
- `002_add_user_preferences.py`
- `003_rename_waste_type_column.py`
- `004_add_movement_status_index.py`

## Expand/Contract Strategy

For schema changes:
1. **Expand**: Add new columns/tables (non-breaking)
2. **Migrate**: Backfill data, update application logic
3. **Contract**: Remove old columns after verification

Always include both `upgrade()` and `downgrade()` functions.

## Multi-Tenancy Notes

- All tables with `organization_id` enforce tenant isolation
- Foreign keys include `ondelete="CASCADE"` for org deletion
- See docs/migrations/alembic-guide.md for detailed strategy