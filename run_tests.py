import subprocess
import os

os.chdir('C:/Projects/Pranely/packages/backend')

# Run bridge tests
print("Running bridge tests...")
result = subprocess.run(
    ['python', '-m', 'pytest', 'tests/test_bridge.py', '-v', '--tb=short', '-x'],
    capture_output=True,
    text=True,
    timeout=120
)

print(f"Exit code: {result.returncode}")
print(result.stdout)
if result.stderr and len(result.stderr) > 100:
    print("STDERR:", result.stderr[-2000:])
