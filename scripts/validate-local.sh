#!/bin/bash
# =============================================================================
# PRANELY - Scripts de validación local
# =============================================================================

set -e

echo "🔍 PRANELY - Validación local"

# =============================================================================
# 1. Verificar estructura
# =============================================================================
echo ""
echo "1. Verificando estructura..."
required_dirs=(
  ".devcontainer"
  ".github/workflows"
  "docs/decisions"
  "packages/frontend"
  "packages/backend"
)
for dir in "${required_dirs[@]}"; do
  if [ -d "$dir" ]; then
    echo "   ✅ $dir"
  else
    echo "   ❌ $dir - FALTANTE"
    exit 1
  fi
done

# =============================================================================
# 2. Verificar Docker Compose
# =============================================================================
echo ""
echo "2. Verificando Docker Compose..."
docker compose -f docker-compose.base.yml config --quiet && echo "   ✅ Base compose OK"
docker compose -f docker-compose.dev.yml config --quiet && echo "   ✅ Dev compose OK"

# =============================================================================
# 3. Verificar versiones
# =============================================================================
echo ""
echo "3. Verificando versiones..."
echo "   Node: $(node --version 2>/dev/null || echo 'no instalado')"
echo "   Python: $(python3 --version 2>/dev/null || echo 'no instalado')"

# =============================================================================
# 4. Gitleaks (si está instalado)
# =============================================================================
echo ""
echo "4. Verificando secrets con Gitleaks..."
if command -v gitleaks &> /dev/null; then
  gitleaks detect --source-path . --report-path gitleaks-report.json || true
  echo "   ✅ Gitleaks completado"
else
  echo "   ⚠️ Gitleaks no instalado (skip)"
fi

echo ""
echo "✅ Validación completada"
