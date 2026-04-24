-- PRANELY - Seed data multi-tenant para DR tests (schema real)
TRUNCATE TABLE waste_movements, memberships, users, organizations CASCADE;

-- Organization A (Tenant A) - id = 1
INSERT INTO organizations (id, name, legal_name, industry, is_active, created_at, updated_at)
VALUES (1, 'Industrial del Norte', 'Industrial del Norte S.A. de C.V.', 'manufacturing', true, NOW(), NOW());

-- Organization B (Tenant B) - id = 2
INSERT INTO organizations (id, name, legal_name, industry, is_active, created_at, updated_at)
VALUES (2, 'Reciclajes del Sur', 'Reciclajes del Sur S.A. de C.V.', 'recycling', true, NOW(), NOW());

-- Users
INSERT INTO users (id, email, hashed_password, full_name, is_active, created_at, updated_at)
VALUES (1, 'admin@norte.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4qUUQYrXvCqjTC.W', 'Admin Norte', true, NOW(), NOW()),
       (2, 'admin@sur.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4qUUQYrXvCqjTC.W', 'Admin Sur', true, NOW(), NOW());

-- Memberships
INSERT INTO memberships (id, user_id, organization_id, role, created_at)
VALUES (1, 1, 1, 'owner', NOW()),
       (2, 2, 2, 'owner', NOW());

-- Waste movements para Tenant A (org_id = 1)
INSERT INTO waste_movements (id, organization_id, manifest_number, movement_type, quantity, unit, status, created_at, updated_at)
VALUES (1, 1, 'MAN-2024-001-NORTE', 'PELIGROSO', 150.5, 'kg', 'validated', NOW(), NOW()),
       (2, 1, 'MAN-2024-002-NORTE', 'ESPECIAL', 300.0, 'L', 'pending', NOW(), NOW()),
       (3, 1, 'MAN-2024-003-NORTE', 'RECICLABLE', 500.0, 'kg', 'validated', NOW(), NOW());

-- Waste movements para Tenant B (org_id = 2)
INSERT INTO waste_movements (id, organization_id, manifest_number, movement_type, quantity, unit, status, created_at, updated_at)
VALUES (4, 2, 'MAN-2024-001-SUR', 'INERTE', 200.0, 'm3', 'validated', NOW(), NOW()),
       (5, 2, 'MAN-2024-002-SUR', 'ORGANICO', 150.0, 'kg', 'in_review', NOW(), NOW());
