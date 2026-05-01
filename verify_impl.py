import os

files = [
    r'C:\Projects\Pranely\packages\backend\app\api\middleware\tenant.py',
    r'C:\Projects\Pranely\packages\frontend\src\components\LoginForm.tsx',
    r'C:\Projects\Pranely\packages\backend\tests\test_tenant_x_org_id.py',
    r'C:\Projects\Pranely\packages\frontend\tests\auth-multi-org.spec.ts',
]

print("Archivos implementados:")
for f in files:
    if os.path.exists(f):
        size = os.path.getsize(f)
        print(f"  [OK] {os.path.basename(f)}: {size} bytes")
    else:
        print(f"  [FAIL] {os.path.basename(f)}: NOT FOUND")

# Verify FIX 1 key changes
print("\nFIX 1 verification:")
with open(r'C:\Projects\Pranely\packages\backend\app\api\middleware\tenant.py', 'r') as f:
    content = f.read()
    checks = [
        ('x-org-id in scope injection', 'x-org-id' in content and 'request.scope' in content),
        ('No duplicate logic', 'k != b"x-org-id"' in content),
        ('org_id None guard', 'tenant_ctx.org_id is not None' in content),
    ]
    for name, result in checks:
        print(f"  [{'OK' if result else 'FAIL'}] {name}")

# Verify FIX 2 key changes
print("\nFIX 2 verification:")
with open(r'C:\Projects\Pranely\packages\frontend\src\components\LoginForm.tsx', 'r') as f:
    content = f.read()
    checks = [
        ('available_orgs detection', 'available_orgs' in content),
        ('Org selection step', 'org_selection' in content),
        ('loginWithOrgSelection', 'loginWithOrgSelection' in content),
        ('Back button', 'Volver al inicio' in content or 'Volver al inicio de sesion' in content),
    ]
    for name, result in checks:
        print(f"  [{'OK' if result else 'FAIL'}] {name}")
