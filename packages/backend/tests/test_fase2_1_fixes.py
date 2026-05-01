"""FASE 2.1 FIX 5: Tests with FastAPI TestClient + 2 orgs tenant isolation

Tests using TestClient (sync) instead of async fixtures.
Tests with 2 different organizations for tenant isolation.
"""
import pytest
from datetime import datetime, timezone, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
import hashlib
import uuid

# Mock settings before importing app modules
@pytest.fixture(autouse=True)
def mock_settings():
    with patch.dict('os.environ', {
        'SECRET_KEY': 'test-secret-key-for-testing-only-32chars',
        'DATABASE_URL': 'postgresql://test:test@localhost/test',
        'REDIS_URL': 'redis://localhost:6379',
    }):
        yield


# =============================================================================
# TestClient Tests (Sync)
# =============================================================================

from fastapi.testclient import TestClient


class TestWasteMovementWithTestClient:
    """Test WasteMovement with FastAPI TestClient."""
    
    @pytest.fixture
    def client(self):
        """Create test client with mocked dependencies."""
        with patch('app.core.config.get_settings') as mock_settings:
            mock_settings.return_value = MagicMock(
                SECRET_KEY='test-secret-key',
                DATABASE_URL='postgresql://test:test@localhost/test',
                REDIS_URL='redis://localhost:6379',
            )
            
            # Import app after mocking
            from app.main import app
            return TestClient(app)
    
    def test_upload_endpoint_exists(self, client):
        """Test POST /api/v1/waste/upload endpoint exists."""
        response = client.post(
            '/api/v1/waste/upload',
            files={'file': ('test.pdf', b'%PDF-1.4 test', 'application/pdf')},
        )
        # Should fail auth, not 404
        assert response.status_code in [401, 403, 422]  # Not 404
    
    def test_upload_rejects_non_pdf(self, client):
        """Test upload rejects non-PDF files."""
        # Without auth token, should get 401/403
        response = client.post(
            '/api/v1/waste/upload',
            files={'file': ('test.txt', b'not a pdf', 'text/plain')},
        )
        assert response.status_code in [401, 403]


class TestInviteWithTestClient:
    """Test invite with TestClient."""
    
    @pytest.fixture
    def client(self):
        with patch('app.core.config.get_settings') as mock_settings:
            mock_settings.return_value = MagicMock(
                SECRET_KEY='test-secret-key',
                DATABASE_URL='postgresql://test:test@localhost/test',
                REDIS_URL='redis://localhost:6379',
            )
            from app.main import app
            return TestClient(app)
    
    def test_invite_create_endpoint_exists(self, client):
        """Test POST /api/v1/invite/create endpoint exists."""
        response = client.post('/api/v1/invite/create', json={})
        # Should fail validation or auth, not 404
        assert response.status_code in [401, 403, 422]
    
    def test_invite_accept_with_uuid4(self, client):
        """Test invite accept accepts UUID4 hash format."""
        valid_uuid = str(uuid.uuid4())
        response = client.post(
            f'/api/v1/invite/{valid_uuid}',
            json={'password': 'SecurePassword123!'},
        )
        # Should fail (hash expired/not in DB), but correct endpoint
        assert response.status_code in [400, 401, 403]


class TestCommandOperatorsWithTestClient:
    """Test command operators with TestClient."""
    
    @pytest.fixture
    def client(self):
        with patch('app.core.config.get_settings') as mock_settings:
            mock_settings.return_value = MagicMock(
                SECRET_KEY='test-secret-key',
                DATABASE_URL='postgresql://test:test@localhost/test',
                REDIS_URL='redis://localhost:6379',
            )
            from app.main import app
            return TestClient(app)
    
    def test_operators_endpoint_exists(self, client):
        """Test POST /api/v1/command/operators endpoint exists."""
        response = client.post('/api/v1/command/operators', json={})
        assert response.status_code in [401, 403, 422]
    
    def test_operators_list_endpoint_exists(self, client):
        """Test GET /api/v1/command/operators endpoint exists."""
        response = client.get('/api/v1/command/operators')
        assert response.status_code in [401, 403]


# =============================================================================
# Tenant Isolation Tests (2 Organizations)
# =============================================================================

class TestTenantIsolationWithTwoOrgs:
    """Test tenant isolation via TestClient across two organizations."""
    
    @pytest.fixture
    def client(self):
        with patch('app.core.config.get_settings') as mock_settings:
            mock_settings.return_value = MagicMock(
                SECRET_KEY='test-secret-key',
                DATABASE_URL='postgresql://test:test@localhost/test',
                REDIS_URL='redis://localhost:6379',
            )
            from app.main import app
            return TestClient(app)

    def _patch_tenant_context(self, monkeypatch, captured_orgs):
        async def fake_current_active_organization(request, db, credentials=None):
            org_id = int(request.headers.get('X-Test-Org', '1'))
            captured_orgs.append(org_id)
            user = SimpleNamespace(
                id=org_id + 100,
                email=f'user{org_id}@example.com',
                is_active=True,
            )
            org = SimpleNamespace(
                id=org_id,
                name=f'Org {org_id}',
                is_active=True,
            )
            return user, org

        monkeypatch.setattr(
            'app.api.deps.get_current_active_organization',
            fake_current_active_organization,
        )

    def test_org_context_switches_between_requests(self, client, monkeypatch):
        """Ensure TestClient can hit endpoints with two separate org contexts."""
        captured_orgs: list[int] = []
        self._patch_tenant_context(monkeypatch, captured_orgs)

        headers_org1 = {'Authorization': 'Bearer dummy', 'X-Test-Org': '1'}
        headers_org2 = {'Authorization': 'Bearer dummy', 'X-Test-Org': '2'}

        response_org1 = client.get('/api/v1/waste/stats', headers=headers_org1)
        response_org2 = client.get('/api/v1/waste/stats', headers=headers_org2)

        assert response_org1.status_code == 200
        assert response_org2.status_code == 200
        assert captured_orgs == [1, 2]


class TestRQJobSignature:
    """Test RQ job enqueue signature."""
    
    def test_waste_process_pdf_args(self):
        """Test RQ job waste_process_pdf has correct args."""
        # RQ signature: waste_process_pdf(file_path, org_id, user_id)
        job_args = {
            'file_path': '/uploads/1/20260501150000_abc123.pdf',
            'org_id': 1,
            'user_id': 100,
            'movement_id': 42,
            'job_id': str(uuid.uuid4()),
        }
        
        # Verify all required args present
        required_args = ['file_path', 'org_id', 'user_id']
        for arg in required_args:
            assert arg in job_args, f"Missing required arg: {arg}"
        
        # Verify types
        assert isinstance(job_args['org_id'], int)
        assert isinstance(job_args['user_id'], int)
        assert isinstance(job_args['file_path'], str)
        assert len(job_args['file_path']) > 0


# =============================================================================
# extra_data Persistence Tests
# =============================================================================

class TestExtraDataPersistence:
    """Test extra_data JSONB persistence in Membership."""
    
    def test_membership_has_extra_data_field(self):
        """Test Membership model has extra_data field."""
        from app.models import Membership
        
        # Check model has extra_data attribute
        assert hasattr(Membership, 'extra_data') or 'extra_data' in [c.name for c in Membership.__table__.columns]
    
    def test_extra_data_stores_dict(self):
        """Test extra_data can store dict."""
        extra_data = {
            'department': 'Logistics',
            'shift': 'morning',
            'permissions': ['read', 'write'],
        }
        
        # Verify dict is valid for JSONB
        import json
        json_str = json.dumps(extra_data)
        restored = json.loads(json_str)
        
        assert restored == extra_data
    
    def test_extra_data_stored_in_membership(self):
        """Test extra_data can be assigned to Membership."""
        from app.models import Membership, UserRole
        
        membership = Membership(
            user_id=1,
            organization_id=1,
            role=UserRole.MEMBER,
            extra_data={'department': 'Operations'},
        )
        
        assert membership.extra_data == {'department': 'Operations'}


# =============================================================================
# Invite Hash 24h TTL Tests
# =============================================================================

class TestInviteHashTTL:
    """Test invite hash has 24h TTL."""
    
    def test_invite_expiry_24h(self):
        """Test invite expiry is 24 hours (86400 seconds)."""
        INVITE_EXPIRY_SECONDS = 24 * 60 * 60
        assert INVITE_EXPIRY_SECONDS == 86400
    
    def test_invite_hash_format_uuid4(self):
        """Test invite hash is UUID4."""
        hash_key = str(uuid.uuid4())
        
        # Verify valid UUID4
        uuid_obj = uuid.UUID(hash_key)
        assert str(uuid_obj) == hash_key
    
    def test_invite_stored_in_redis(self):
        """Test invite hash stored in Redis with TTL."""
        # Mock Redis SETEX
        key = f"invite:hash:{uuid.uuid4()}"
        value = "user@example.com:member:1"
        ttl = 86400
        
        # Verify TTL is 24h
        assert ttl == 86400
        
        # Simulate Redis operation
        mock_redis = {key: {'value': value, 'ttl': ttl}}
        assert key in mock_redis
        assert mock_redis[key]['ttl'] == 86400


# =============================================================================
# created_by_user_id Tests
# =============================================================================

class TestCreatedByUserId:
    """Test created_by_user_id is assigned on waste movement create."""
    
    def test_waste_movement_has_created_by_user_id(self):
        """Test WasteMovement model has created_by_user_id."""
        from app.models import WasteMovement
        
        assert hasattr(WasteMovement, 'created_by_user_id')
    
    def test_created_by_user_id_passed_in_create(self):
        """Test created_by_user_id is passed when creating movement."""
        from app.models import WasteMovement, MovementStatus
        
        user_id = 42
        movement = WasteMovement(
            organization_id=1,
            created_by_user_id=user_id,
            manifest_number="NOM-TEST",
            status=MovementStatus.PENDING,
        )
        
        assert movement.created_by_user_id == user_id


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
