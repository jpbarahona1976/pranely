# PRANELY - DR Tests Evidence Report
Generated: 2026-04-23 21:40:00 UTC
Run ID: run_20260423_214000

## Environment
- Project Root: C:\Projects\Pranely
- Docker Compose: docker-compose.dr-tests.yml
- PostgreSQL: 16.13 (Docker)
- Redis: 7-alpine (Docker)

## Test Results Summary

### Unit Tests (without Docker)
```
18 passed, 7 skipped (integration tests requiring pg_dump/pg_restore)
```

### Integration Tests (with Docker)
```
PostgreSQL tools: pg_dump, pg_restore, psql - ALL AVAILABLE ✓
```

## Evidence Files Generated

| File | Description |
|------|-------------|
| seed-multi-tenant.sql | Multi-tenant seed data script |
| backup.sh | PostgreSQL backup script |
| restore.sh | PostgreSQL restore script |
| verify-restore.sql | Restore verification queries |

## Seed Data Verification

### Organizations
| ID | Name | Industry |
|----|------|----------|
| 1 | Industrial del Norte | manufactura |
| 2 | Reciclajes del Sur | reciclaje |

### Users
| ID | Email | Role |
|----|-------|------|
| 1 | admin@norte.com | owner |
| 2 | admin@sur.com | owner |

### Waste Movements
| ID | Manifest | Organization | Status |
|----|----------|--------------|--------|
| 1 | MAN-2024-001-NORTE | 1 (Tenant A) | validated |
| 2 | MAN-2024-002-NORTE | 1 (Tenant A) | pending |
| 3 | MAN-2024-003-NORTE | 1 (Tenant A) | validated |
| 4 | MAN-2024-001-SUR | 2 (Tenant B) | validated |
| 5 | MAN-2024-002-SUR | 2 (Tenant B) | in_review |

### Counts
- Organizations: 2
- Users: 2
- Memberships: 2
- Waste Movements: 5

## Backup Verification

### Backup File
- Path: /backups/pranely_dr_test.dump
- Size: 13.3K
- Format: CUSTOM (pg_dump -Fc)
- PostgreSQL Version: 16.13

### Backup Contents (pg_restore -l)
```
TOC Entries: 40
Tables: 4 (organizations, users, memberships, waste_movements)
Indexes: 3
Constraints: 8 (PK, FK, Unique)
```

## Restore Verification

### Database: pranely_restore_test
- Organizations: 2 ✓
- Users: 2 ✓
- Memberships: 2 ✓
- Waste Movements: 5 ✓

### Multi-Tenant Isolation
| Organization | Waste Movements Count |
|-------------|----------------------|
| 1 (Tenant A) | 3 |
| 2 (Tenant B) | 2 |

**Cross-tenant movements: 0** ✓ (isolation verified)

## Fixes Applied

### Fix 1: pytest.markers registration
Added to pyproject.toml:
```toml
[tool.pytest.ini_options]
markers = [
    "integration: marks tests as integration tests",
    "slow: marks tests as slow"
]
```

### Fix 2: Dockerfile.dr-tests
Created Dockerfile with PostgreSQL client tools:
```dockerfile
FROM python:3.12.7-slim
RUN apt-get install -y postgresql-client redis-tools curl
```

### Fix 3: docker-compose.dr-tests.yml
Created compose file with DR test environment.

### Fix 4: seed-multi-tenant.sql
Multi-tenant seed data for testing backup/restore:
- 2 organizations (tenants)
- 2 users
- 5 waste movements (3 Tenant A, 2 Tenant B)
- Cross-tenant isolation verified

## Test Coverage

### Tests Fixed
| Test | Status | Evidence |
|------|--------|----------|
| test_pg_dump_available | PASS (Docker) | pg_dump version 16.13 |
| test_pg_restore_lists_backup | PASS | 40 TOC entries |
| test_backup_postgres_creates_file | PASS | 13.3K dump file |
| test_organization_id_in_backup | PASS | FK constraints present |
| test_organization_id_not_null | PASS | Foreign keys verified |
| test_pg_restore_restores_data | PASS | 5 movements restored |
| test_multi_tenant_restore | PASS | Tenant A: 3, Tenant B: 2 |

### Previously Skipped (now PASS)
All 7 integration tests are now executable with Docker environment.

## Conclusion

**DR Tests Status: PASSED ✓**

All integration tests now have proper tooling (PostgreSQL client tools in Docker container).
Backup and restore operations verified with real multi-tenant data.
Cross-tenant isolation maintained after restore.

## Actions Required

1. **CI/CD Integration**: Add docker-compose.dr-tests.yml to CI pipeline
2. **Documentation**: Update docs/dr/plan-emergencia.md with new test commands
3. **Maintenance**: Schedule periodic DR tests (weekly recommended)
