import subprocess

# Check containers
print("Current containers:")
result = subprocess.run(['docker', 'ps', '-a', '--format', '{{.Names}}\t{{.Status}}'], capture_output=True, text=True)
print(result.stdout)

# Remove old backend container
print("\nRemoving old backend container...")
subprocess.run(['docker', 'rm', '-f', 'pranely-backend'], capture_output=True)

# Start backend
print("Starting backend...")
result = subprocess.run([
    'docker', 'run', '-d', '--name', 'pranely-backend',
    '--env-file', 'C:/Projects/Pranely/packages/backend/.env',
    '-e', 'DATABASE_URL=postgresql+asyncpg://pranely:pranely_dev@pranely-postgres:5432/pranely',
    '-e', 'REDIS_URL=redis://pranely-redis:6379/0',
    '-p', '8000:8000',
    'pranely-backend:dev'
], capture_output=True, text=True)

print(result.stdout or result.stderr)

# Wait for backend
import time
print("Waiting for backend (15s)...")
time.sleep(15)

# Test
print("\nTesting API...")
result = subprocess.run(['curl', '-s', 'http://localhost:8000/health'], capture_output=True, text=True)
print(f"Response: {result.stdout or result.stderr}")

print("\nBackend logs:")
result = subprocess.run(['docker', 'logs', '--tail', '30', 'pranely-backend'], capture_output=True, text=True)
print(result.stdout or result.stderr)
