# =============================================================================
# PRANELY - Secret Rotation Script
# Usage: ./scripts/rotate-secrets.sh [--dry-run]
# =============================================================================

set -e

DRY_RUN=false
if [ "$1" == "--dry-run" ]; then
    DRY_RUN=true
    echo "DRY RUN MODE - No changes will be made"
fi

echo "🔄 PRANELY Secret Rotation"
echo "=========================="

# Generate new SECRET_KEY
NEW_SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(64))")

# PostgreSQL password
NEW_DB_PASSWORD=$(python -c "import secrets; print(secrets.token_urlsafe(32))")

if [ "$DRY_RUN" == "true" ]; then
    echo "Would generate:"
    echo "  SECRET_KEY: ${NEW_SECRET_KEY:0:20}..."
    echo "  DB_PASSWORD: ${NEW_DB_PASSWORD:0:16}..."
else
    echo "Generated new secrets:"
    echo "  SECRET_KEY: ${NEW_SECRET_KEY:0:20}..."
    echo "  DB_PASSWORD: ${NEW_DB_PASSWORD:0:16}..."
    echo ""
    echo "⚠️  IMPORTANT: Update your secrets manager with these values!"
fi

# Verify no secrets in code
echo ""
echo "🔍 Checking for exposed secrets..."
gitleaks detect --redact --no-color

echo ""
echo "✅ Secret rotation check complete"
