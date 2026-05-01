import subprocess
import os

os.chdir('C:/Projects/Pranely/packages/backend')

# Run bridge tests
result = subprocess.run(
    ['python', '-m', 'pytest', 'tests/test_bridge.py', '-v', '--tb=short'],
    capture_output=True,
    text=True,
    timeout=60
)

print(f"Exit code: {result.returncode}")
print(result.stdout)
if result.stderr:
    print("STDERR:", result.stderr[-1000:])
