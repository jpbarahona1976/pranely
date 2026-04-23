#!/usr/bin/env python3
"""
PRANELY - Alembic Migration Management CLI

Usage:
    python scripts/migrate.py [command]

Commands:
    status      - Show current migration status
    upgrade     - Run next migration
    downgrade   - Revert last migration
    history     - Show migration history
    branches    - Show current branch
    current     - Show current revision
    show <rev>  - Show details of a revision

Environment:
    DATABASE_URL - PostgreSQL connection string
                  Format: postgresql+asyncpg://user:pass@host:5432/db

Examples:
    # Check status
    python scripts/migrate.py status

    # Upgrade to latest
    python scripts/migrate.py upgrade

    # Downgrade one step
    python scripts/migrate.py downgrade

    # Downgrade to specific revision
    python scripts/migrate.py downgrade 001_initial_baseline

    # Show revision details
    python scripts/migrate.py show 001_initial_baseline

Security Note:
    - 'gc' command removed: 'alembic purge' is destructive and unsafe
    - Use 'python -m alembic downgrade base' to clean state instead
"""
import os
import sys
import subprocess
from pathlib import Path

# Backend path
BACKEND_DIR = Path(__file__).parent.parent
os.chdir(BACKEND_DIR)

# Commands
ALEMBIC_CMD = [sys.executable, "-m", "alembic"]


def run_alembic(args: list[str]) -> int:
    """Run alembic command and return exit code."""
    cmd = ALEMBIC_CMD + args
    print(f"$ {' '.join(cmd)}")
    result = subprocess.run(cmd)
    return result.returncode


def cmd_status():
    """Show current migration status."""
    return run_alembic(["status"])


def cmd_upgrade(revision: str = "head"):
    """Upgrade to specified revision."""
    if revision == "head":
        return run_alembic(["upgrade", "head"])
    return run_alembic(["upgrade", revision])


def cmd_downgrade(revision: str = "-1"):
    """Downgrade to specified revision."""
    return run_alembic(["downgrade", revision])


def cmd_history():
    """Show migration history."""
    return run_alembic(["history", "--verbose"])


def cmd_branches():
    """Show current branches."""
    return run_alembic(["branches"])


def cmd_current():
    """Show current revision."""
    return run_alembic(["current", "--verbose"])


def cmd_show(revision: str):
    """Show details of a specific revision."""
    return run_alembic(["show", revision])


def cmd_check():
    """Check if there are pending upgrade operations."""
    return run_alembic(["check"])


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "status":
        sys.exit(cmd_status())
    elif command == "upgrade":
        revision = sys.argv[2] if len(sys.argv) > 2 else "head"
        sys.exit(cmd_upgrade(revision))
    elif command == "downgrade":
        revision = sys.argv[2] if len(sys.argv) > 2 else "-1"
        sys.exit(cmd_downgrade(revision))
    elif command == "history":
        sys.exit(cmd_history())
    elif command == "branches":
        sys.exit(cmd_branches())
    elif command == "current":
        sys.exit(cmd_current())
    elif command == "show":
        if len(sys.argv) < 3:
            print("Error: 'show' requires a revision argument")
            print("Usage: python scripts/migrate.py show <revision>")
            sys.exit(1)
        sys.exit(cmd_show(sys.argv[2]))
    elif command == "check":
        sys.exit(cmd_check())
    else:
        print(f"Unknown command: {command}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()