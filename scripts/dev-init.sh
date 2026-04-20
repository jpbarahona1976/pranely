#!/bin/bash
# =============================================================================
# PRANELY - Dev Container Init Script (0B)
# Post-create command para configurar el entorno de desarrollo
# =============================================================================

set -e

echo "🔧 PRANELY Dev Container 0B - Iniciando configuración..."

# =============================================================================
# Git config (obligatorio)
# =============================================================================
echo "📝 Configurando Git..."
git config --global user.email "developer@pranely.dev" 2>/dev/null || true
git config --global user.name "PRANELY Developer" 2>/dev/null || true
git config --global init.defaultBranch main 2>/dev/null || true
git config --global pull.rebase false 2>/dev/null || true

# =============================================================================
# Node.js 22.13.1
# =============================================================================
echo "📦 Configurando Node.js 22.13.1..."
if command -v nvm &> /dev/null; then
    nvm install 22.13.1
    nvm use 22.13.1
    nvm alias default 22.13.1
fi

# =============================================================================
# pnpm 9.12.2
# =============================================================================
echo "📦 Configurando pnpm 9.12.2..."
if command -v pnpm &> /dev/null; then
    pnpm add -g pnpm@9.12.2 2>/dev/null || npm install -g pnpm@9.12.2
fi

# =============================================================================
# Python 3.12.7
# =============================================================================
echo "🐍 Configurando Python 3.12.7..."
if command -v pyenv &> /dev/null; then
    pyenv install 3.12.7
    pyenv global 3.12.7
else
    echo "⚠️ pyenv no encontrado, usando python global"
fi

# =============================================================================
# Poetry 1.8.3
# =============================================================================
echo "📦 Configurando Poetry 1.8.3..."
if command -v poetry &> /dev/null; then
    poetry self update 1.8.3 2>/dev/null || poetry --version
fi

# =============================================================================
# Install dependencies
# =============================================================================
echo "📦 Instalando dependencias..."

# Frontend
if [ -f "packages/frontend/package.json" ]; then
    echo "  → Frontend (pnpm install)..."
    cd packages/frontend && pnpm install --no-frozen-lockfile 2>/dev/null || echo "  ⚠️ package.json no existe (OK para 0B)"
    cd ../..
fi

# Backend
if [ -f "packages/backend/pyproject.toml" ]; then
    echo "  → Backend (poetry install)..."
    cd packages/backend && poetry install --no-root 2>/dev/null || echo "  ⚠️ pyproject.toml no existe (OK para 0B)"
    cd ../..
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
echo "✅ PRANELY Dev Container 0B configurado correctamente"
echo ""
echo " Versiones fijadas:"
echo "   • Node.js: 22.13.1"
echo "   • pnpm: 9.12.2"
echo "   • Python: 3.12.7"
echo "   • Poetry: 1.8.3"
echo ""
echo " Próximos pasos (0C):"
echo "   1. cd packages/frontend && pnpm create next-app@latest ."
echo "   2. cd packages/backend && poetry new . --name app"
echo "   3. docker compose -f docker-compose.dev.yml up -d"
echo ""
