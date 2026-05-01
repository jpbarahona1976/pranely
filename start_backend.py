import subprocess

# Start backend with .env
print("Starting backend...")
result = subprocess.run([
    'docker', 'run', '-d', '--name', 'pranely-backend',
    '--env-file', 'C:/Projects/Pranely/packages/backend/.env',
    '-e', 'DATABASE_URL=postgresql+asyncpg://pranely:pranely_dev@pranely-postgres:5432/pranely',
    '-e', 'REDIS_URL=redis://pranely-redis:6379/0',
    'pranely-backend:dev'
], capture_output=True, text=True)

print(result.stdout or result.stderr)

# Wait for backend to be ready
import time
print("Waiting for backend...")
time.sleep(15)

# Check status
print("\nContainer status:")
result = subprocess.run(['docker', 'ps', '--format', '{{.Names}}\t{{.Status}}'], capture_output=True, text=True)
print(result.stdout)

# Test health
print("\nTesting /health...")
result = subprocess.run(['curl', '-s', 'http://localhost:8000/health'], capture_output=True, text=True)
print(result.stdout or result.stderr)

# Get backend logs
print("\nBackend logs (last 20):")
result = subprocess.run(['docker', 'logs', '--tail', '20', 'pranely-backend'], capture_output=True, text=True)
print(result.stdout or result.stderr)
