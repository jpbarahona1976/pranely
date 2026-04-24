#!/usr/bin/env python
"""Run webhook tests with correct environment variables."""
import os
import subprocess
import sys

# Set environment variables BEFORE importing app modules
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only-32chars"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///file::memory:"
os.environ["REDIS_URL"] = "redis://localhost:6379"
os.environ["ENV"] = "test"
os.environ["DEBUG"] = "false"

if __name__ == "__main__":
    result = subprocess.run(
        ["python", "-m", "pytest", "tests/test_api_v1/test_webhook.py", "-v", "--tb=short"],
        env=os.environ.copy()
    )
    sys.exit(result.returncode)
