# ================================================
# PRANELY.AI - Validar Entorno
# Ejecutar dentro de Ubuntu/WSL
# =============================================

set -e

echo "========================================"
echo "  PRANELY.AI - Validacion del Entorno"
echo "========================================"
echo ""

check() {
    if [ $? -eq 0 ]; then
        echo "[OK] $1"
    else
        echo "[FAIL] $1"
    fi
}

echo "[1] Ubuntu"
cat /etc/os-release | grep PRETTY_NAME
check "Ubuntu detectado"

echo ""
echo "[2] Python 3.12"
python3.12 --version
check "Python 3.12 instalado"

echo ""
echo "[3] Git"
git --version
git config --global user.name
git config --global user.email
check "Git configurado"

echo ""
echo "[4] Docker (desde Ubuntu)"
if command -v docker &> /dev/null; then
    docker --version
    docker ps
    check "Docker accesible"
else
    echo "[INFO] Docker no instalado en Ubuntu (normal si usas Docker Desktop en Windows)"
fi

echo ""
echo "[5] Python packages basicos"
pip3.12 list 2>/dev/null | head -5 || echo "[INFO] Sin paquetes instalados aun"

echo ""
echo "[6] Espacio en disco"
df -h ~

echo ""
echo "========================================"
echo "  Validacion completada"
echo "========================================"
