import subprocess
import os

os.chdir('C:/Projects/Pranely/packages/backend')

print("Removing old backend...")
subprocess.run(['docker', 'rm', '-f', 'pranely-backend'], capture_output=True)

print("Rebuilding backend (DOCKER_BUILDKIT=0)...")
result = subprocess.run(
    ['docker', 'build', '-f', 'Dockerfile', '-t', 'pranely-backend:dev', '.', '--no-cache'],
    capture_output=True,
    text=True,
    timeout=180,
    env={**os.environ, 'DOCKER_BUILDKIT': '0'}
)

print(f"Exit code: {result.returncode}")
if result.returncode != 0:
    print(f"STDERR:\n{result.stderr[-2000:]}")
else:
    print("Build SUCCESS")
    # Start backend
    print("\nStarting backend...")
    subprocess.run([
        'docker', 'run', '-d', '--name', 'pranely-backend',
        '--env-file', 'C:/Projects/Pranely/packages/backend/.env',
        '-e', 'DATABASE_URL=postgresql+asyncpg://pranely:pranely_dev@pranely-postgres:5432/pranely',
        '-e', 'REDIS_URL=redis://pranely-redis:6379/0',
        '-p', '8000:8000',
        'pranely-backend:dev'
    ], capture_output=True)
    
    import time
    print("Waiting 20s for backend...")
    time.sleep(20)
    
    print("\nContainer status:")
    result = subprocess.run(['docker', 'ps', '--format', '{{.Names}}\t{{.Status}}'], capture_output=True, text=True)
    print(result.stdout)
    
    print("\nBackend logs:")
    result = subprocess.run(['docker', 'logs', '--tail', '40', 'pranely-backend'], capture_output=True, text=True)
    print(result.stdout or result.stderr)
    
    print("\nTesting API health...")
    result = subprocess.run(['curl', '-s', 'http://localhost:8000/health'], capture_output=True, text=True)
    print(f"Health: {result.stdout or result.stderr}")
