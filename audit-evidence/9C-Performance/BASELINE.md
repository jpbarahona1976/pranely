# PRANELY - Phase 9C Performance Benchmark Baseline
# Created: 2026-04-30
# Phase: 9C Performance Optimization

## Baseline Metrics (Pre-Optimization)

### Database Query Analysis

**1. GET /api/v1/waste/stats - BOTTLENECK IDENTIFIED**
```
Executing 6 separate COUNT queries:
  - COUNT for PENDING status
  - COUNT for IN_REVIEW status
  - COUNT for VALIDATED status
  - COUNT for REJECTED status
  - COUNT for EXCEPTION status
  - COUNT for total active
  - COUNT for archived
Total: 7 sequential queries with full table scans
Estimated latency: 800-1200ms (p95 > 500ms SLO)
```

**2. Missing Index on waste_movements**
```
Query: WHERE organization_id = ? AND archived_at IS NULL
Problem: No composite index for (organization_id, status, archived_at)
Impact: Full table scan on waste_movements as org grows
```

**3. validate_membership_and_role - N+1 Query**
```
Query: SELECT FROM memberships WHERE user_id = ? AND organization_id = ?
Called: Every write operation (create, update, archive)
Impact: 1 extra query per mutation
```

### Redis Cache Status

**Current Implementation:**
- RedisClient exists with circuit breaker ✅
- NO cache usage in waste endpoints
- NO session cache
- NO stats cache

**Target:**
- waste_stats: TTL 300s (5 min), hit rate >70%
- sessions: TTL 1800s (30 min)
- cache warming on startup

### Load Testing Script

**Status:** NOT EXISTS
**Required:** k6 script for 100 concurrent users

---

## SLO Targets

| Metric | Current (Est.) | Target | Status |
|--------|---------------|--------|--------|
| API p95 latency | 800-1200ms | <500ms | ❌ FAIL |
| DB query p95 | ~200ms | <100ms | ⚠️ WARN |
| Redis hit rate | 0% | >70% | ❌ FAIL |
| Load test 100 users | NOT RUN | pass | ⏳ PENDING |

---

## Endpoints to Optimize

1. `GET /api/v1/waste/stats` - 7 queries → 1 query + cache
2. `GET /api/v1/waste` - Add pagination index
3. `POST /api/v1/waste` - Add membership cache
4. All endpoints - Add organization_id index

## Implementation Plan

- [ ] Migration: Add composite index waste_movements
- [ ] Optimize waste_stats to single query
- [ ] Implement Redis cache layer
- [ ] Create k6 load test script
- [ ] Run benchmarks and document results
- [ ] Verify CI passes