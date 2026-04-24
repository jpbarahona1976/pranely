#!/usr/bin/env python
"""Run tests with correct environment variables."""
import os
import sys

# Set environment variables BEFORE importing app modules
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only-32chars"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///file::memory:"
os.environ["REDIS_URL"] = "redis://localhost:6379"
os.environ["ENV"] = "test"
os.environ["DEBUG"] = "false"

if __name__ == "__main__":
    import subprocess
    result = subprocess.run(
        ["python", "-m", "pytest", "tests/test_api_v1/", "-v", "--tb=short"],
        env=os.environ.copy()
    )
    sys.exit(result.returncode)
