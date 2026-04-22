#!/bin/bash
# smoke-test.sh - Smoke tests post-deploy
# PRANELY Phase 2C

set -e

ENV="${1:-staging}"
TIMEOUT="${2:-120}"

echo "=== PRANELY Smoke Tests ==="
echo "Env: $ENV"
echo "Timeout: ${TIMEOUT}s"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

FAILED=0

test_health() {
    local name="$1"
    local url="$2"
    
    echo -n "Testing $name... "
    
    if timeout "${TIMEOUT}" curl -sf "$url" > /dev/null 2>&1; then
        echo -e "${GREEN}OK${NC}"
        return 0
    else
        echo -e "${RED}FAIL${NC}"
        FAILED=$((FAILED + 1))
        return 1
    fi
}

test_auth() {
    echo -n "Testing auth login... "
    
    RESPONSE=$(timeout "${TIMEOUT}" curl -sf -X POST \
        "http://localhost:8000/api/auth/login" \
        -H "Content-Type: application/x-www-form-urlencoded" \
        -d "username=admin@pranely.test&password=admin123" 2>&1 || true)
    
    if echo "$RESPONSE" | grep -q "access_token"; then
        echo -e "${GREEN}OK${NC}"
        export TEST_TOKEN=$(echo "$RESPONSE" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)
        return 0
    else
        echo -e "${RED}FAIL${NC}"
        FAILED=$((FAILED + 1))
        return 1
    fi
}

test_crud() {
    local endpoint="$1"
    local name="$2"
    
    echo -n "Testing CRUD $name... "
    
    if [ -z "$TEST_TOKEN" ]; then
        echo -e "${YELLOW}SKIP (no token)${NC}"
        return 0
    fi
    
    if timeout "${TIMEOUT}" curl -sf \
        "http://localhost:8000/api/$endpoint" \
        -H "Authorization: Bearer $TEST_TOKEN" \
        | grep -q "data"; then
        echo -e "${GREEN}OK${NC}"
        return 0
    else
        echo -e "${RED}FAIL${NC}"
        FAILED=$((FAILED + 1))
        return 1
    fi
}

test_json() {
    local name="$1"
    local url="$2"
    local field="$3"
    
    echo -n "Testing $name... "
    
    RESPONSE=$(timeout "${TIMEOUT}" curl -sf "$url" 2>&1 || true)
    
    if echo "$RESPONSE" | grep -q "\"$field\""; then
        echo -e "${GREEN}OK${NC}"
        return 0
    else
        echo -e "${RED}FAIL${NC}"
        FAILED=$((FAILED + 1))
        return 1
    fi
}

# Run tests
echo "=== Health Checks ==="
test_health "Basic" "http://localhost:8000/api/health"
test_json "DB" "http://localhost:8000/api/health/db" "postgres"
test_json "Redis" "http://localhost:8000/api/health/redis" "redis"
test_json "Tenant" "http://localhost:8000/api/health/tenant" "tenant_isolation"

echo ""
echo "=== Auth Check ==="
test_auth

echo ""
echo "=== CRUD Checks ==="
test_crud "employers" "Employers"
test_crud "transporters" "Transporters"
test_crud "residues" "Residues"

echo ""
echo "=== Summary ==="
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}ALL TESTS PASSED${NC}"
    exit 0
else
    echo -e "${RED}$FAILED TESTS FAILED${NC}"
    exit 1
fi