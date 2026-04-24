#!/bin/bash
# PRANELY - DR Tests execution script for Docker

pip install --quiet pytest pytest-asyncio aiosqlite httpx

pytest packages/backend/tests/test_backup_dr.py -v --tb=short -m integration
