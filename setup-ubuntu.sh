# ================================================
# PRANELY.AI - Setup Python 3.12 + Entorno
# Ejecutar dentro de Ubuntu/WSL despues de setup-wsl.ps1
# =============================================

set -e

echo "========================================"
echo "  PRANELY.AI - Ubuntu Setup Script"
echo "========================================"
echo ""

echo "[1/7] Actualizando sistema..."
sudo apt update

echo ""
echo "[2/7] Instalando dependencias..."
sudo apt install -y software-properties-common curl ca-certificates gnupg lsb-release

echo ""
echo "[3/7] Añadiendo repositorio deadsnakes..."
sudo add-apt-repository ppa:deadsnakes/ppa -y

echo ""
echo "[4/7] Instalando Python 3.12..."
sudo apt update
sudo apt install -y python3.12 python3.12-venv python3.12-dev

echo ""
echo "[5/7] Verificando Python..."
python3.12 --version
pip3.12 --version

echo ""
echo "[6/7] Configurando git global..."
git config --global user.name "jpbarahona"
git config --global user.email "barahonaj704@gmail.com"
git config --global core.autocrlf input
echo "Git configurado: $(git config --global user.name) <$(git config --global user.email)>"

echo ""
echo "[7/7] Creando estructura de carpetas..."
mkdir -p ~/pranely/{backend,frontend}
cd ~/pranely
echo "Carpeta creada: ~/pranely/"
echo "  - backend/"
echo "  - frontend/"

echo ""
echo "========================================"
echo "  Ubuntu configurado!"
echo "========================================"
echo ""
echo "Python 3.12 instalado: $(python3.12 --version)"
echo ""
echo "PROXIMOS PASOS:"
echo "1. Instalar VS Code en Windows: https://code.visualstudio.com/"
echo "2. Instalar extension 'WSL' en VS Code"
echo "3. Abrir VS Code y conectar a WSL: Ctrl+Shift+P > WSL Connect"
echo "4. Abrir terminal en VS Code (Ctrl+`) y ejecutar:"
echo ""
echo "   cd ~/pranely/backend"
echo "   python3.12 -m venv venv"
echo "   source venv/bin/activate"
echo "   pip install fastapi uvicorn sqlalchemy asyncpg alembic pydantic redis pytest httpx"
echo ""
echo "INSTALACIONES MANUALES RESTANTES:"
echo "- DBeaver: https://dbeaver.io/download/"
echo "- Insomnia: https://insomnia.rest/download"
echo "- Redis Insight: https://redis.com/redis-enterprise/redis-insight/"
