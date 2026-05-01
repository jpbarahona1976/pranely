# PRANELY SLOs - Service Level Objectives
## FASE 9B: Observabilidad

**Fecha:** 30 Abril 2026  
**Fase:** 9B Observabilidad  
**Estado:** Implementado

---

## Service Level Indicators (SLIs)

| SLI | Métrica | Source |
|-----|---------|--------|
| **Availability** | `(total_requests - 5xx_errors) / total_requests` | `pranely_http_requests_total` |
| **Latency (p95)** | `histogram_quantile(0.95, rate(pranely_http_request_duration_seconds_bucket[5m]))` | `pranely_http_request_duration_seconds` |
| **Latency (p99)** | `histogram_quantile(0.99, rate(pranely_http_request_duration_seconds_bucket[5m]))` | `pranely_http_request_duration_seconds` |
| **Error Rate** | `rate(pranely_http_requests_total{status_code=~"5.."}[5m]) / rate(pranely_http_requests_total[5m])` | `pranely_http_requests_total` |
| **Queue Health** | `pranely_rq_queue_size < 100` | `pranely_rq_queue_size` |
| **Job Success Rate** | `jobs_finished / (jobs_finished + jobs_failed)` | `pranely_rq_jobs_total` |

---

## Service Level Objectives (SLOs)

| SLO | Target | Error Budget (monthly) | Window |
|-----|--------|------------------------|--------|
| **API Availability** | 99.5% | 3h 39m downtime/month | Rolling 30 days |
| **API Latency p95** | < 500ms | N/A (latency target) | Rolling 30 days |
| **API Latency p99** | < 1000ms | N/A (latency target) | Rolling 30 days |
| **Error Rate (5xx)** | < 0.5% | 0.5% of requests | Rolling 30 days |
| **Queue Processing** | < 100 jobs backlog | N/A | 1 hour |
| **Job Success Rate** | > 95% | 5% failures allowed | Rolling 24 hours |

---

## Error Budget Policy

### Budget Calculation (99.5% Availability)

| Period | Total Minutes | Allowed Downtime | Fast Burn Threshold |
|--------|---------------|-----------------|-------------------|
| Daily | 1,440 | 7.2 min | 14.4 min/hour |
| Weekly | 10,080 | 50.4 min | 50.4 min/hour |
| Monthly | 43,200 | 3h 39m | 3h 39m/window |

### Burn Rate Alerts

| Burn Rate | Meaning | Action |
|-----------|---------|--------|
| > 14.4x (1h) | Consuming 1 day budget in 1 hour | **Critical** - Page immediately |
| > 6x (6h) | Consuming 1 week budget in 1 day | **Warning** - Address within 4 hours |
| > 1x (long-term) | Consuming budget at expected rate | Monitor, no action |

---

## SLO Dashboard Queries

### Availability (Rolling 30 days)
```promql
(1 - (
  sum(rate(pranely_http_requests_total{status_code=~"5.."}[30d])) 
  / 
  sum(rate(pranely_http_requests_total[30d]))
)) * 100
```

### Latency p95 (SLO target: < 500ms)
```promql
histogram_quantile(0.95, 
  sum(rate(pranely_http_request_duration_seconds_bucket[5m])) by (le)
)
```

### Error Budget Remaining (30 days)
```promql
# Error budget = 100% - SLO target = 0.5%
# Current burn rate
(
  sum(rate(pranely_http_requests_total{status_code=~"5.."}[1h])) 
  / 
  sum(rate(pranely_http_requests_total[1h]))
) / 0.005
```

---

## Metrics Exposed

### HTTP Metrics
- `pranely_http_requests_total` - Total requests by method, endpoint, status_code, org_id
- `pranely_http_request_duration_seconds` - Request latency histogram
- `pranely_http_requests_in_progress` - Current in-flight requests

### Error Metrics
- `pranely_errors_total` - Errors by type, endpoint, org_id

### Queue Metrics
- `pranely_rq_jobs_total` - Jobs by name and status
- `pranely_rq_job_duration_seconds` - Job execution time histogram
- `pranely_rq_queue_size` - Current queue depth by queue
- `pranely_rq_workers_active` - Active workers

### Rate Limiting Metrics
- `pranely_rate_limit_hits_total` - Rate limit violations by org_id

### Auth Metrics
- `pranely_auth_attempts_total` - Auth attempts by result

### Infrastructure Health
- `pranely_health_check_status` - Component health (1=up, 0=down)

---

## Alert Summary

| Alert | Severity | SLO Impact | Response Time |
|-------|----------|-------------|---------------|
| API Down | Critical | Availability | Immediate |
| p95 Latency > 500ms | Warning | Latency | 30 min |
| p95 Latency > 1000ms | Critical | Latency | 15 min |
| Error Rate > 1% | Warning | Errors | 1 hour |
| Error Rate > 5% | Critical | Errors | Immediate |
| Queue Backlog > 100 | Warning | Queue Health | 2 hours |
| Queue Backlog > 500 | Critical | Queue Health | 30 min |
| Job Failure > 5% | Warning | Job Success | 4 hours |

---

## Implementation Notes

1. **Metrics Endpoint:** `/api/metrics` returns Prometheus format
2. **Scrape Interval:** 10s for API, 30s for infrastructure
3. **Retention:** 15 days in Prometheus, 30 days in Grafana
4. **Dashboard:** Available at Grafana `http://localhost:3001` (admin/admin123)

---

## Next Steps (Fase 9C Performance)

- Deep dive on p95 latency > 500ms endpoints
- Identify database query bottlenecks
- Optimize slow RQ jobs
- Add caching metrics
- Implement distributed tracing (OpenTelemetry) if needed
