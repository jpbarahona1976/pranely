"""Tests for security utilities (password hashing)."""
import pytest

from app.core.security import hash_password, verify_password


def test_hash_password():
    """Test password hashing creates valid hash."""
    password = "SecurePassword123!"
    hashed = hash_password(password)
    
    # Hash should not be empty
    assert hashed is not None
    assert len(hashed) > 0
    
    # Hash should not be the same as password
    assert hashed != password
    
    # Argon2 hash starts with $argon2
    assert hashed.startswith("$argon2")


def test_verify_password_correct():
    """Test verifying correct password succeeds."""
    password = "SecurePassword123!"
    hashed = hash_password(password)
    
    assert verify_password(password, hashed) is True


def test_verify_password_incorrect():
    """Test verifying incorrect password fails."""
    password = "SecurePassword123!"
    wrong_password = "WrongPassword456!"
    hashed = hash_password(password)
    
    assert verify_password(wrong_password, hashed) is False


def test_verify_password_invalid_hash():
    """Test verifying with invalid hash fails gracefully."""
    result = verify_password("password", "invalid-hash")
    assert result is False


def test_different_passwords_different_hashes():
    """Test that different passwords produce different hashes."""
    password1 = "PasswordOne123!"
    password2 = "PasswordTwo456!"
    
    hash1 = hash_password(password1)
    hash2 = hash_password(password2)
    
    # Each hash should verify only with its own password
    assert verify_password(password1, hash1) is True
    assert verify_password(password2, hash2) is True
    assert verify_password(password1, hash2) is False
    assert verify_password(password2, hash1) is False