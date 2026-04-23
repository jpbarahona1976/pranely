# PRANELY - Alembic Migration Guide

## Overview

Alembic is configured for PRANELY to manage PostgreSQL 16 schema evolution with multi-tenant isolation.

## Structure

```
packages/backend/
├── alembic/
│   ├── env.py           # Alembic environment config
│   ├── script.py.mako   # Migration template
│   └── versions/
│       └── 001_initial_baseline.py  # Baseline migration
├── alembic.ini          # Alembic configuration
└── scripts/
    ├── migrate.py       # Migration CLI helper
    └── verify_migrations.py  # Verification script
```

## Quick Reference

### Check Status
```bash
cd packages/backend
python -m alembic current
python -m alembic history
```

### Upgrade
```bash
# Upgrade to latest
python -m alembic upgrade head

# Upgrade to specific revision
python -m alembic upgrade 001_initial_baseline
```

### Downgrade / Rollback
```bash
# Downgrade one step
python -m alembic downgrade -1

# Downgrade to specific revision
python -m alembic downgrade 001_initial_baseline

# Downgrade all (clean state)
python -m alembic downgrade base
```

### Create New Migration
```bash
# With autogenerate (compare model changes)
python -m alembic revision --autogenerate -m "description"

# Empty migration
python -m alembic revision -m "description"
```

## Migration Files

### 001_initial_baseline
Creates all 13 PRANELY tables:
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

### Strategy: Expand/Contract

For future changes:
1. **Expand**: Add new tables/columns (non-breaking)
2. **Migrate**: Backfill data, move logic
3. **Contract**: Remove old columns (after verification)

Example adding a new column:
```python
# migration_add_field.py
def upgrade():
    op.add_column("residues", sa.Column("new_field", sa.String(100), nullable=True))

def downgrade():
    op.drop_column("residues", "new_field")
```

## Rollback Verification

Test rollback locally before deploying:
```bash
# 1. Apply migration
python -m alembic upgrade head

# 2. Verify data (if any)

# 3. Rollback
python -m alembic downgrade -1

# 4. Verify schema returned to previous state

# 5. Re-apply
python -m alembic upgrade head
```

## Multi-Tenancy Notes

- All tables with `organization_id` enforce tenant isolation
- Foreign keys include `ondelete="CASCADE"` for org deletion
- No cross-tenant queries are possible (enforced at application level)

## PostgreSQL vs SQLite

- **Production**: PostgreSQL 16 with asyncpg driver
- **Testing**: SQLite for local tests (compatible with batch mode)
- **Migration script**: Auto-detects driver and uses appropriate config

## Environment Variables

```bash
# Required
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db

# For local testing
DATABASE_URL=sqlite:///test.db
```

## Scripts

### verify_migrations.py
Verify model alignment with migrations:
```bash
python scripts/verify_migrations.py
```

### migrate.py
Convenience CLI:
```bash
python scripts/migrate.py status
python scripts/migrate.py upgrade
python scripts/migrate.py downgrade
```

## Troubleshooting

### "Can't locate revision"
```bash
# Verify versions directory
ls alembic/versions/

# Check heads
python -m alembic heads
```

### "Already at revision"
Migration already applied. Use `current` to verify:
```bash
python -m alembic current --verbose
```

### "Connection refused"
Check DATABASE_URL and database service:
```bash
echo $DATABASE_URL
# Verify PostgreSQL is running
```

## Next Steps

1. Run `python -m alembic upgrade head` to apply baseline
2. Continue with **4C: Endpoints CRUD** (WasteMovement, Subscription, LegalAlert)
3. Run tests after each migration: `pytest tests/`

## Security Notes

- Never run migrations on production without verification
- Test rollback procedure in staging first
- Maintain backup before applying destructive migrations
- Document all schema changes in CHANGELOG.md