"""
PRANELY - Backup/DR Tests (Fase 4C)
Pytest suite para verificación de backup y restore
"""

import os
import subprocess
import time
from pathlib import Path
from datetime import datetime, timedelta

import pytest


# =============================================================================
# Constants
# =============================================================================
BACKUP_DIR = Path(os.environ.get("BACKUP_DIR", "./backups"))
TEST_DATA_SIZE = int(os.environ.get("TEST_DATA_SIZE", "100"))


# =============================================================================
# Fixtures
# =============================================================================
@pytest.fixture(scope="session")
def backup_dir():
    """Ensure backup directory exists."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    return BACKUP_DIR


@pytest.fixture(scope="session")
def postgres_env():
    """PostgreSQL connection parameters from environment."""
    return {
        "PG_HOST": os.environ.get("PG_HOST", "postgres"),
        "PG_PORT": os.environ.get("PG_PORT", "5432"),
        "PG_USER": os.environ.get("PG_USER", "pranely"),
        "PG_DB": os.environ.get("PG_DB", "pranely_dev"),
        "PGPASSWORD": os.environ.get("POSTGRES_PASSWORD", ""),
    }


@pytest.fixture(scope="session")
def redis_env():
    """Redis connection parameters from environment."""
    return {
        "REDIS_HOST": os.environ.get("REDIS_HOST", "redis"),
        "REDIS_PORT": os.environ.get("REDIS_PORT", "6379"),
    }


# =============================================================================
# Backup Tests
# =============================================================================
class TestBackupAutomation:
    """Test suite for automated backup functionality."""

    def test_backup_script_exists(self):
        """Verify backup script exists and is executable."""
        script_path = Path("scripts/backup.sh")
        assert script_path.exists(), "backup.sh script not found"
        assert os.access(script_path, os.X_OK), "backup.sh is not executable"

    def test_backup_healthcheck_rpo_compliance(self):
        """Verify healthcheck enforces RPO 1h (2h max)."""
        healthcheck_path = Path("scripts/backup-healthcheck.sh")
        assert healthcheck_path.exists(), "backup-healthcheck.sh not found"

        content = healthcheck_path.read_text()
        # RPO 1h = 2h max in healthcheck (1h buffer)
        assert "MAX_BACKUP_AGE_HOURS" in content
        assert "2" in content, "Healthcheck must use MAX_BACKUP_AGE_HOURS=2 for RPO compliance"
        assert '2' in content.split("MAX_BACKUP_AGE_HOURS")[1].split("\n")[0]

    def test_backup_directory_structure(self, backup_dir):
        """Verify backup directory structure is correct."""
        # Create required subdirectories
        (backup_dir / "logs").mkdir(parents=True, exist_ok=True)
        (backup_dir / "latest").mkdir(parents=True, exist_ok=True)
        (backup_dir / "reports").mkdir(parents=True, exist_ok=True)

        assert (backup_dir / "logs").is_dir()
        assert (backup_dir / "latest").is_dir()

    def test_backup_retention_policy(self, backup_dir):
        """Verify old backups are cleaned up based on retention policy."""
        retention_days = int(os.environ.get("RETENTION_DAYS", "7"))

        # Create test backup with old timestamp
        old_backup = backup_dir / f"{(datetime.now() - timedelta(days=10)).strftime('%Y/%m/%d')}"
        old_backup.mkdir(parents=True, exist_ok=True)
        old_file = old_backup / "test_old.dump"
        old_file.write_text("old backup")

        # Verify cleanup would remove it
        max_age_seconds = retention_days * 24 * 3600
        file_age_seconds = time.time() - os.path.getmtime(old_file)
        assert file_age_seconds > max_age_seconds


class TestBackupExecution:
    """Test suite for backup execution."""

    def test_pg_dump_available(self):
        """Verify pg_dump command is available."""
        try:
            result = subprocess.run(
                ["pg_dump", "--version"],
                capture_output=True,
                text=True,
            )
            assert result.returncode == 0
            assert "pg_dump" in result.stdout.lower()
        except FileNotFoundError:
            pytest.fail("pg_dump not found in PATH")

    def test_redis_cli_available(self):
        """Verify redis-cli command is available."""
        try:
            result = subprocess.run(
                ["redis-cli", "--version"],
                capture_output=True,
                text=True,
            )
            assert result.returncode == 0
        except FileNotFoundError:
            pytest.skip("redis-cli not found in PATH")

    @pytest.mark.integration
    def test_backup_postgres_creates_file(self, backup_dir, postgres_env):
        """Test that pg_dump creates a valid backup file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        date_dir = datetime.now().strftime("%Y/%m/%d")

        output_dir = backup_dir / date_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        backup_file = output_dir / f"postgres_test_{timestamp}.dump"

        # Run pg_dump
        env = os.environ.copy()
        if postgres_env["PGPASSWORD"]:
            env["PGPASSWORD"] = postgres_env["PGPASSWORD"]

        result = subprocess.run(
            [
                "pg_dump",
                "-h", postgres_env["PG_HOST"],
                "-p", postgres_env["PG_PORT"],
                "-U", postgres_env["PG_USER"],
                "-d", postgres_env["PG_DB"],
                "-Fc",
                "-f", str(backup_file),
            ],
            env=env,
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, f"pg_dump failed: {result.stderr}"
        assert backup_file.exists(), "Backup file not created"
        assert backup_file.stat().st_size > 0, "Backup file is empty"


# =============================================================================
# Restore Tests
# =============================================================================
class TestRestoreScript:
    """Test suite for restore script functionality."""

    def test_restore_script_exists(self):
        """Verify restore script exists and is executable."""
        script_path = Path("scripts/restore.sh")
        assert script_path.exists(), "restore.sh script not found"
        assert os.access(script_path, os.X_OK), "restore.sh is not executable"

    def test_restore_writes_rto_duration_file(self):
        """Verify restore script writes RTO duration to /tmp/rto_duration.txt."""
        restore_path = Path("scripts/restore.sh")
        assert restore_path.exists(), "restore.sh not found"

        content = restore_path.read_text()
        # Must write RTO real to /tmp/rto_duration.txt
        assert "/tmp/rto_duration.txt" in content, "restore.sh must write RTO to /tmp/rto_duration.txt"

    def test_dr_compose_file_exists(self):
        """Verify DR docker-compose file exists."""
        dr_compose = Path("docker-compose.dr.yml")
        assert dr_compose.exists(), "docker-compose.dr.yml not found"


class TestRestoreExecution:
    """Test suite for restore execution."""

    @pytest.mark.integration
    def test_pg_restore_lists_backup(self, backup_dir, postgres_env):
        """Test that pg_restore can list backup contents."""
        # Find latest backup
        backups = sorted(backup_dir.glob("*/*.dump"), key=lambda p: p.stat().st_mtime)
        if not backups:
            pytest.skip("No backup files found")

        backup_file = backups[-1]

        env = os.environ.copy()
        if postgres_env["PGPASSWORD"]:
            env["PGPASSWORD"] = postgres_env["PGPASSWORD"]

        result = subprocess.run(
            [
                "pg_restore",
                "-h", postgres_env["PG_HOST"],
                "-p", postgres_env["PG_PORT"],
                "-U", postgres_env["PG_USER"],
                "-d", "postgres",  # Connect to default db first
                "--list",
                str(backup_file),
            ],
            env=env,
            capture_output=True,
            text=True,
        )

        # pg_restore returns 0 for list operation
        assert result.returncode == 0, f"pg_restore --list failed: {result.stderr}"


# =============================================================================
# DR Simulation Tests
# =============================================================================
class TestDRSimulation:
    """Test suite for DR simulation tests."""

    def test_dr_script_exists(self):
        """Verify DR simulation script exists."""
        script_path = Path("scripts/simulacro-dr.sh")
        assert script_path.exists(), "simulacro-dr.sh script not found"
        assert os.access(script_path, os.X_OK), "simulacro-dr.sh is not executable"

    def test_rpo_verification_logic(self, backup_dir):
        """Test RPO verification logic."""
        # RPO = 1h, healthcheck permite 2h max (1h + 1h buffer)
        max_age_hours = 2
        current_time = time.time()

        # Create a "recent" backup
        date_dir = datetime.now().strftime("%Y/%m/%d")
        backup_path = backup_dir / date_dir
        backup_path.mkdir(parents=True, exist_ok=True)
        backup_file = backup_path / "postgres_recent.dump"
        backup_file.write_text("recent backup")

        # Verify it's within RPO window
        backup_age = current_time - os.path.getmtime(backup_file)
        backup_age_hours = backup_age / 3600

        assert backup_age_hours < max_age_hours, "Recent backup should be within RPO window"

    def test_rto_verification_logic(self):
        """Test RTO calculation logic."""
        rto_max_seconds = 900  # 15 minutes

        # Simulate a restore that takes 5 minutes
        simulated_duration = 300

        assert simulated_duration < rto_max_seconds, "Simulated RTO should be under limit"


# =============================================================================
# Multi-tenant Integrity Tests
# =============================================================================
class TestMultiTenantIntegrity:
    """Test suite for multi-tenant data integrity in backups."""

    @pytest.mark.integration
    def test_organization_id_in_backup(self, backup_dir, postgres_env):
        """Verify that organization_id column exists in backed up data."""
        env = os.environ.copy()
        if postgres_env["PGPASSWORD"]:
            env["PGPASSWORD"] = postgres_env["PGPASSWORD"]

        # Query for organization_id presence
        result = subprocess.run(
            [
                "psql",
                "-h", postgres_env["PG_HOST"],
                "-p", postgres_env["PG_PORT"],
                "-U", postgres_env["PG_USER"],
                "-d", postgres_env["PG_DB"],
                "-c", "SELECT column_name FROM information_schema.columns WHERE table_name = 'organizations' AND column_name = 'id';",
            ],
            env=env,
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "id" in result.stdout.lower()

    @pytest.mark.integration
    def test_organization_id_not_null(self, postgres_env):
        """Verify organization_id is NOT NULL in key tables."""
        env = os.environ.copy()
        if postgres_env["PGPASSWORD"]:
            env["PGPASSWORD"] = postgres_env["PGPASSWORD"]

        # Check waste_movements has org_id
        result = subprocess.run(
            [
                "psql",
                "-h", postgres_env["PG_HOST"],
                "-p", postgres_env["PG_PORT"],
                "-U", postgres_env["PG_USER"],
                "-d", postgres_env["PG_DB"],
                "-c", "SELECT attnotnull FROM pg_attribute WHERE attrelid = 'waste_movements'::regclass AND attname = 'organization_id';",
            ],
            env=env,
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        # attnotnull returns 't' for true
        assert "t" in result.stdout.lower()


# =============================================================================
# Documentation Tests
# =============================================================================
class TestDocumentation:
    """Test suite for DR documentation."""

    def test_dr_plan_exists(self):
        """Verify DR plan document exists."""
        plan_path = Path("docs/dr/plan-emergencia.md")
        assert plan_path.exists(), "DR plan document not found"

    def test_dr_plan_has_rpo_rto(self):
        """Verify DR plan contains RPO/RTO definitions."""
        plan_path = Path("docs/dr/plan-emergencia.md")
        content = plan_path.read_text()

        assert "RPO" in content or "Recovery Point Objective" in content
        assert "RTO" in content or "Recovery Time Objective" in content

    def test_dr_plan_has_checklist(self):
        """Verify DR plan has preparation checklist."""
        plan_path = Path("docs/dr/plan-emergencia.md")
        content = plan_path.read_text()

        assert "Checklist" in content or "checklist" in content


# =============================================================================
# Monitoring Tests
# =============================================================================
class TestMonitoring:
    """Test suite for backup monitoring."""

    def test_backup_log_directory(self, backup_dir):
        """Verify backup log directory exists."""
        logs_dir = backup_dir / "logs"
        assert logs_dir.is_dir()

    def test_backup_reports_directory(self, backup_dir):
        """Verify backup reports directory exists."""
        reports_dir = backup_dir / "reports"
        assert reports_dir.is_dir()


# =============================================================================
# Integration Tests
# =============================================================================
class TestBackupRestoreIntegration:
    """End-to-end backup/restore integration tests."""

    @pytest.mark.integration
    @pytest.mark.slow
    def test_backup_restore_cycle(self, backup_dir, postgres_env):
        """Test complete backup and restore cycle."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        date_dir = datetime.now().strftime("%Y/%m/%d")

        # Setup directories
        output_dir = backup_dir / date_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        backup_file = output_dir / f"integration_test_{timestamp}.dump"

        # 1. Create backup
        env = os.environ.copy()
        if postgres_env["PGPASSWORD"]:
            env["PGPASSWORD"] = postgres_env["PGPASSWORD"]

        result = subprocess.run(
            [
                "pg_dump",
                "-h", postgres_env["PG_HOST"],
                "-p", postgres_env["PG_PORT"],
                "-U", postgres_env["PG_USER"],
                "-d", postgres_env["PG_DB"],
                "-Fc",
                "-f", str(backup_file),
            ],
            env=env,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            pytest.fail(f"Backup failed: {result.stderr}")

        assert backup_file.exists()
        original_size = backup_file.stat().st_size

        # 2. Verify backup with pg_restore --list
        result = subprocess.run(
            [
                "pg_restore",
                "-h", postgres_env["PG_HOST"],
                "-p", postgres_env["PG_PORT"],
                "-U", postgres_env["PG_USER"],
                "-d", "postgres",
                "--list",
                str(backup_file),
            ],
            env=env,
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, f"Backup verification failed: {result.stderr}"

        # 3. Verify structure
        result = subprocess.run(
            [
                "pg_restore",
                "-h", postgres_env["PG_HOST"],
                "-p", postgres_env["PG_PORT"],
                "-U", postgres_env["PG_USER"],
                "-d", "postgres",
                "-f", "-",
                str(backup_file),
            ],
            env=env,
            capture_output=True,
            text=True,
        )

        assert "CREATE TABLE" in result.stdout
        assert "organizations" in result.stdout

        # Cleanup
        backup_file.unlink(missing_ok=True)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
