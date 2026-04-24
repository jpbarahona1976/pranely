-- PRANELY - Create Schema + Multi-Tenant Seed Data for DR Tests
-- PostgreSQL 16 compatible

-- =============================================================================
-- SCHEMA CREATION (simplified from alembic/versions/001_initial_baseline.py)
-- =============================================================================

-- Organizations (multi-tenant root) - WITHOUT RFC (no such column in baseline)
DROP TABLE IF EXISTS waste_movements CASCADE;
DROP TABLE IF EXISTS memberships CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS organizations CASCADE;

CREATE TABLE organizations (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    legal_name VARCHAR(255),
    industry VARCHAR(100),
    segment VARCHAR(100),
    stripe_customer_id VARCHAR(255),
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ
);

-- Users (authentication)
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    locale VARCHAR(10) NOT NULL DEFAULT 'es',
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ
);
CREATE INDEX ix_users_email ON users (email);

-- Memberships (user-organization relationship with role)
CREATE TABLE memberships (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    organization_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, organization_id)
);

-- Waste Movements (NOM-052 compliance manifests)
CREATE TABLE waste_movements (
    id SERIAL PRIMARY KEY,
    organization_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    manifest_number VARCHAR(100) NOT NULL,
    movement_type VARCHAR(50),
    quantity FLOAT,
    unit VARCHAR(20),
    date TIMESTAMPTZ,
    confidence_score FLOAT,
    status VARCHAR(20) NOT NULL,
    is_immutable BOOLEAN NOT NULL DEFAULT false,
    archived_at TIMESTAMPTZ,
    file_path VARCHAR(500),
    orig_filename VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ
);
CREATE INDEX ix_waste_movement_org_timestamp ON waste_movements (organization_id, created_at);
CREATE INDEX ix_waste_movement_manifest ON waste_movements (manifest_number);

-- =============================================================================
-- SEED DATA - Multi-Tenant
-- =============================================================================

-- Tenant A: Industrial del Norte (organization_id = 1)
INSERT INTO organizations (id, name, legal_name, industry, is_active, created_at, updated_at)
VALUES (1, 'Industrial del Norte', 'Industrial del Norte S.A. de C.V.', 'manufactura', true, NOW(), NOW());

INSERT INTO users (id, email, hashed_password, full_name, is_active, created_at, updated_at)
VALUES (1, 'admin@norte.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4qUUQYrXvCqjTC.W', 'Admin Norte', true, NOW(), NOW());

INSERT INTO memberships (id, user_id, organization_id, role, created_at)
VALUES (1, 1, 1, 'owner', NOW());

-- Waste movements Tenant A (3 registros)
INSERT INTO waste_movements (id, organization_id, manifest_number, movement_type, quantity, unit, status, is_immutable, created_at)
VALUES 
    (1, 1, 'MAN-2024-001-NORTE', 'transport', 150.5, 'kg', 'validated', true, NOW()),
    (2, 1, 'MAN-2024-002-NORTE', 'disposal', 300.0, 'L', 'pending', false, NOW()),
    (3, 1, 'MAN-2024-003-NORTE', 'recycling', 500.0, 'kg', 'validated', true, NOW());

-- Tenant B: Reciclajes del Sur (organization_id = 2)
INSERT INTO organizations (id, name, legal_name, industry, is_active, created_at, updated_at)
VALUES (2, 'Reciclajes del Sur', 'Reciclajes del Sur S.A. de C.V.', 'reciclaje', true, NOW(), NOW());

INSERT INTO users (id, email, hashed_password, full_name, is_active, created_at, updated_at)
VALUES (2, 'admin@sur.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4qUUQYrXvCqjTC.W', 'Admin Sur', true, NOW(), NOW());

INSERT INTO memberships (id, user_id, organization_id, role, created_at)
VALUES (2, 2, 2, 'owner', NOW());

-- Waste movements Tenant B (2 registros)
INSERT INTO waste_movements (id, organization_id, manifest_number, movement_type, quantity, unit, status, is_immutable, created_at)
VALUES 
    (4, 2, 'MAN-2024-001-SUR', 'transport', 200.0, 'm3', 'validated', true, NOW()),
    (5, 2, 'MAN-2024-002-SUR', 'storage', 150.0, 'kg', 'in_review', false, NOW());

-- =============================================================================
-- VERIFICATION QUERIES
-- =============================================================================

SELECT '=== SEED DATA VERIFICATION ===' AS info;

SELECT 'Organizations:' AS entity, COUNT(*) AS count FROM organizations;
SELECT 'Users:' AS entity, COUNT(*) AS count FROM users;
SELECT 'Memberships:' AS entity, COUNT(*) AS count FROM memberships;
SELECT 'Waste Movements:' AS entity, COUNT(*) AS count FROM waste_movements;

SELECT '=== MULTI-TENANT ISOLATION ===' AS info;

-- Tenant A movements
SELECT 'Tenant A (org_id=1) waste movements:' AS info;
SELECT organization_id, COUNT(*) FROM waste_movements WHERE organization_id = 1 GROUP BY organization_id;

-- Tenant B movements
SELECT 'Tenant B (org_id=2) waste movements:' AS info;
SELECT organization_id, COUNT(*) FROM waste_movements WHERE organization_id = 2 GROUP BY organization_id;

-- Cross-tenant (should be 0 if properly filtered)
SELECT 'Cross-tenant movements (should be 0):' AS info;
SELECT COUNT(*) FROM waste_movements WHERE organization_id NOT IN (1, 2);

-- Schema tables
SELECT '=== SCHEMA TABLES ===' AS info;
SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;

-- All data summary
SELECT '=== ALL DATA ===' AS info;
SELECT 'organizations' AS table_name, COUNT(*) AS row_count FROM organizations
UNION ALL
SELECT 'users', COUNT(*) FROM users
UNION ALL
SELECT 'memberships', COUNT(*) FROM memberships
UNION ALL
SELECT 'waste_movements', COUNT(*) FROM waste_movements
ORDER BY table_name;
