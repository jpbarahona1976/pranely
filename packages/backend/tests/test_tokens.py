"""Tests for JWT token utilities."""
import pytest

from app.core.tokens import create_access_token, decode_token


def test_create_access_token():
    """Test creating access token."""
    user_id = 123
    org_id = 456
    
    token = create_access_token(user_id, org_id)
    
    assert token is not None
    assert len(token) > 0
    # JWT has 3 parts separated by dots
    assert len(token.split(".")) == 3


def test_decode_valid_token():
    """Test decoding valid token."""
    user_id = 123
    org_id = 456
    
    token = create_access_token(user_id, org_id)
    payload = decode_token(token)
    
    assert payload is not None
    assert payload.sub == str(user_id)
    assert payload.org_id == org_id


def test_decode_invalid_token():
    """Test decoding invalid token returns None."""
    invalid_token = "not.a.valid.token"
    
    payload = decode_token(invalid_token)
    
    assert payload is None


def test_decode_token_without_org():
    """Test decoding token without org_id."""
    user_id = 789
    token = create_access_token(user_id)
    payload = decode_token(token)
    
    assert payload is not None
    assert payload.sub == str(user_id)
    assert payload.org_id is None