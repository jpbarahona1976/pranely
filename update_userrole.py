"""Script to update UserRole in models.py"""
import re

with open('C:/Projects/Pranely/packages/backend/app/models.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find and replace UserRole enum
old_pattern = r'class UserRole\(PyEnum\):.*?VIEWER = "viewer"'
new_text = '''class UserRole(PyEnum):
    """User roles within an organization.
    
    RBAC hierarchy (least to most permission):
    - viewer: read-only, no mutations
    - member: read + basic operations (8B fix: GET allowed, mutations denied)
    - admin: full ops access within tenant
    - owner: tenant owner, can delete org
    - director: platform-wide supervisor, full tenant access (8B fix: now included)
    """
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"
    DIRECTOR = "director"'''

if re.search(old_pattern, content, re.DOTALL):
    content = re.sub(old_pattern, new_text, content, count=1, flags=re.DOTALL)
    with open('C:/Projects/Pranely/packages/backend/app/models.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('✅ UserRole updated with DIRECTOR role')
else:
    # Try simpler approach
    if 'VIEWER = "viewer"' in content and 'DIRECTOR' not in content:
        old = '    VIEWER = "viewer"'
        new = '    VIEWER = "viewer"\n    DIRECTOR = "director"'
        content = content.replace(old, new, 1)
        with open('C:/Projects/Pranely/packages/backend/app/models.py', 'w', encoding='utf-8') as f:
            f.write(content)
        print('✅ DIRECTOR added to UserRole')
    else:
        print('⚠️ UserRole already has DIRECTOR or pattern not found')
        # Show current UserRole section
        match = re.search(r'class UserRole.*?(?=\nclass )', content, re.DOTALL)
        if match:
            print('Current UserRole:')
            print(match.group())