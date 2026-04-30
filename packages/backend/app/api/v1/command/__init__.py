"""
Command Center API v1 - Admin panel for configuration, operators, quotas, feature flags.

RBAC FIX 8B:
- Owner: full access
- Admin: full access
- Director: full access (8B fix - now included)
- Member: GET/read only (8B fix - no mutations allowed)
- Viewer: NO ACCESS (403)

PERSISTENCE FIX 8B:
- Feature flags stored in Organization.extra_data JSON field
- Persists across restarts/reboots
"""

from app.api.v1.command import router

__all__ = ["router"]