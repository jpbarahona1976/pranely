SELECT 'Organizations:' as info, COUNT(*) as count FROM organizations
UNION ALL
SELECT 'Users:', COUNT(*) FROM users
UNION ALL
SELECT 'Memberships:', COUNT(*) FROM memberships
UNION ALL
SELECT 'WasteMovements:', COUNT(*) FROM waste_movements
UNION ALL
SELECT 'AuditLogs:', COUNT(*) FROM audit_logs;
