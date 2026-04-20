#!/bin/bash
# =============================================================================
# PRANELY - Dev Container Init Script
# Post-create command para configurar el entorno de desarrollo
# =============================================================================

set -e

echo "🔧 PRANELY Dev Container - Iniciando configuración..."

# =============================================================================
# Node.js setup
# =============================================================================
echo "📦 Configurando Node.js 22..."
if command -v nvm &> /dev/null; then
    nvm install 22
    nvm use 22
else
    echo "⚠️ NVM no encontrado, usando node global"
fi

# =============================================================================
# Python setup
# =============================================================================
echo "🐍 Configurando Python 3.12..."
if command -v pyenv &> /dev/null; then
    pyenv install 3.12
    pyenv global 3.12
else
    echo "⚠️ pyenv no encontrado, usando python global"
fi

# Verificar Poetry si está disponible
if command -v poetry &> /dev/null; then
    echo "✅ Poetry disponible"
    poetry --version
fi

# =============================================================================
# Docker compose validate
# =============================================================================
echo "🐳 Validando docker-compose files..."
docker compose -f docker-compose.base.yml config --quiet && echo "✅ Base compose válido"
docker compose -f docker-compose.dev.yml config --quiet && echo "✅ Dev compose válido" || echo "⚠️ Dev compose necesita servicios (OK para baseline)"

# =============================================================================
# Permisos
# =============================================================================
echo "🔐 Configurando permisos..."
chmod +x scripts/*.sh 2>/dev/null || true

echo ""
echo "✅ PRANELY Dev Container configurado correctamente"
echo ""
echo " Próximos pasos:"
echo "   1. cd packages/frontend && npm install"
echo "   2. cd packages/backend && poetry install"
echo "   3. docker compose -f docker-compose.base.yml up -d"
echo ""
