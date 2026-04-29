"""
Run worker tests for PRANELY (Subfase 7A).
"""
import subprocess
import sys

if __name__ == "__main__":
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/test_workers_rq.py", "-v", "--tb=short"],
        cwd=r"C:\Projects\Pranely\packages\backend",
    )
    sys.exit(result.returncode)