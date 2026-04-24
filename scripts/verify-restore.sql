SELECT '=== RESTORE VERIFICATION ===' AS info;

SELECT 'Organizations:' AS entity, COUNT(*) AS count FROM organizations;
SELECT 'Users:' AS entity, COUNT(*) AS count FROM users;
SELECT 'Memberships:' AS entity, COUNT(*) AS count FROM memberships;
SELECT 'Waste Movements:' AS entity, COUNT(*) AS count FROM waste_movements;

SELECT '=== MULTI-TENANT RESTORE ===' AS info;
SELECT organization_id, COUNT(*) FROM waste_movements GROUP BY organization_id;

SELECT '=== SAMPLE DATA ===' AS info;
SELECT * FROM organizations;
SELECT manifest_number, organization_id, status FROM waste_movements ORDER BY id;
