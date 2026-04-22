"""
PRANELY - Security Tests for Secrets Management
Fase 3A: Secretos Remediation
"""

import os
import re
from pathlib import Path

import pytest

# Root of the project (PRANELY)
ROOT = Path(__file__).parent.parent.parent.parent


class TestSecretsHardening:
    """Test suite for secrets management and hardening."""

    def test_no_hardcoded_secrets_in_config(self):
        """SECURITY: Verify no hardcoded secrets in config.py."""
        config_path = ROOT / "packages" / "backend" / "app" / "core" / "config.py"
        content = config_path.read_text()

        # SECRET_KEY should be defined but not assigned a value
        assert "SECRET_KEY: str" in content, "SECRET_KEY must be defined"
        
        # Should NOT have SECRET_KEY = "something"
        forbidden_patterns = [
            'SECRET_KEY = "dev-',
            "SECRET_KEY = 'dev-",
            'SECRET_KEY="',
            "SECRET_KEY='",
        ]
        
        for pattern in forbidden_patterns:
            assert pattern not in content, f"Forbidden pattern found: {pattern}"

    def test_env_file_gitignored(self):
        """SECURITY: Verify .env files are in .gitignore."""
        gitignore_path = ROOT / ".gitignore"
        content = gitignore_path.read_text(encoding="utf-8")

        # Must contain .env ignore patterns
        assert ".env" in content, ".env must be in .gitignore"
        assert ".env.local" in content, ".env.local must be in .gitignore"

    def test_token_module_uses_settings(self):
        """SECURITY: Verify tokens.py uses settings.SECRET_KEY."""
        tokens_path = ROOT / "packages" / "backend" / "app" / "core" / "tokens.py"
        content = tokens_path.read_text()

        # Must use settings.SECRET_KEY, not hardcoded
        assert "settings.SECRET_KEY" in content, "Must use settings.SECRET_KEY"
        
        # Should NOT have hardcoded secrets
        forbidden = [
            'SECRET_KEY="dev-',
            "SECRET_KEY='test-",
        ]
        
        for pattern in forbidden:
            assert pattern not in content, f"Found hardcoded secret: {pattern}"

    def test_gitleaks_config_exists(self):
        """SECURITY: Verify .gitleaks.toml exists."""
        gitleaks_path = ROOT / ".gitleaks.toml"
        assert gitleaks_path.exists(), ".gitleaks.toml must exist"

    def test_gitleaks_config_has_critical_rules(self):
        """SECURITY: Verify .gitleaks.toml has critical rules."""
        gitleaks_path = ROOT / ".gitleaks.toml"
        content = gitleaks_path.read_text()

        required_rules = [
            "jwt",
            "database",
            "aws",
            "stripe",
            "private",
        ]

        for rule in required_rules:
            assert rule in content.lower(), f"Missing gitleaks rule: {rule}"

    def test_gitleaks_env_allowlist(self):
        """SECURITY: Verify .env.example is in gitleaks allowlist."""
        gitleaks_path = ROOT / ".gitleaks.toml"
        content = gitleaks_path.read_text()

        # .env.example should be allowed (clean template)
        assert ".env.example" in content, ".env.example should be in allowlist"


class TestDockerComposeSecurity:
    """Test suite for Docker Compose secrets handling."""

    def test_no_secret_fallbacks_in_staging(self):
        """SECURITY: Verify no insecure fallbacks in staging compose."""
        compose_path = ROOT / "docker-compose.staging.yml"
        content = compose_path.read_text(encoding="utf-8")

        # Insecure patterns that should NOT exist
        insecure_patterns = [
            ":-changeme",
            ":-staging-",
            "SECRET_KEY = 'dev-",
        ]

        for pattern in insecure_patterns:
            assert pattern not in content, f"Insecure pattern found: {pattern}"
        
        # Should have env_file for secrets
        assert "env_file:" in content, "Must use env_file for secrets"
        
        # Should have required POSTGRES_PASSWORD
        assert "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD required}" in content, \
            "POSTGRES_PASSWORD must be required"

    def test_production_requires_secrets(self):
        """SECURITY: Verify production compose requires secrets."""
        compose_path = ROOT / "docker-compose.prod.yml"
        content = compose_path.read_text()

        # Must use :? for required variables
        assert "${SECRET_KEY:?SECRET_KEY required}" in content, \
            "SECRET_KEY must be required in production"

        # Should NOT have fallbacks
        assert ":-changeme" not in content, \
            "No default fallbacks in production"


class TestEnvExample:
    """Test suite for .env.example template."""

    def test_env_example_is_clean(self):
        """SECURITY: Verify .env.example has no real secrets."""
        env_example_path = ROOT / "packages" / "backend" / ".env.example"
        content = env_example_path.read_text()

        # Should have placeholders
        assert "<INSERT_SECRET_KEY_HERE>" in content, \
            "Must have SECRET_KEY placeholder"

        # Should NOT have real credentials
        forbidden = [
            "pranely123",
            "changeme",
            "dev-secret-key",
            "test-secret",
            "staging-secret",
        ]

        for secret in forbidden:
            assert secret not in content.lower(), \
                f"Found real secret in template: {secret}"

    def test_env_example_has_documentation(self):
        """SECURITY: Verify .env.example is well documented."""
        env_example_path = ROOT / "packages" / "backend" / ".env.example"
        content = env_example_path.read_text()

        # Must have header comment
        assert "=" * 20 in content, "Must have separator lines"
        assert "# " in content, "Must have comments"


class TestSecretsManagementDoc:
    """Test suite for secrets management documentation."""

    def test_secrets_policy_exists(self):
        """SECURITY: Verify secrets-management.md exists."""
        doc_path = ROOT / "docs" / "security" / "secrets-management.md"
        assert doc_path.exists(), "secrets-management.md must exist"

    def test_secrets_policy_has_rotation_schedule(self):
        """SECURITY: Verify policy documents rotation schedule."""
        doc_path = ROOT / "docs" / "security" / "secrets-management.md"
        content = doc_path.read_text(encoding="utf-8", errors="replace")

        required_sections = [
            "Rotación",
            "90 días",
            "30 días",
            "Generación",
        ]

        for section in required_sections:
            assert section in content, f"Missing section: {section}"

    def test_secrets_policy_has_incident_response(self):
        """SECURITY: Verify policy has incident response protocol."""
        doc_path = ROOT / "docs" / "security" / "secrets-management.md"
        content = doc_path.read_text(encoding="utf-8", errors="replace")

        # Must have incident response steps
        incident_keywords = [
            "Revocar",
            "Rotar",
            "Verificar",
            "Documentar",
        ]

        for keyword in incident_keywords:
            assert keyword in content, f"Missing incident response step: {keyword}"


class TestEnvFilesExist:
    """Test suite for environment files."""

    def test_env_example_exists(self):
        """SECURITY: Verify .env.example exists."""
        env_example_path = ROOT / "packages" / "backend" / ".env.example"
        assert env_example_path.exists(), ".env.example must exist"
    
    def test_env_staging_exists(self):
        """SECURITY: Verify .env.staging exists."""
        env_staging_path = ROOT / "packages" / "backend" / ".env.staging"
        assert env_staging_path.exists(), ".env.staging must exist"

    def test_env_file_gitignored(self):
        """SECURITY: Verify .env is gitignored."""
        gitignore_path = ROOT / ".gitignore"
        content = gitignore_path.read_text(encoding="utf-8", errors="replace")
        assert ".env" in content, ".env must be in .gitignore"
