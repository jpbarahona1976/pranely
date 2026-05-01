// PRANELY Load Test Script - FASE 9C Performance
// Target: 100 concurrent users, p95 < 500ms SLO
// Usage: k6 run load_test.js --env BASE_URL=https://api.pranely.com

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

// =============================================================================
// Configuration
// =============================================================================

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const VUS = 100;  // Virtual users
const DURATION = '2m';  // Test duration

// Custom metrics
const wasteListLatency = new Trend('waste_list_latency');
const wasteStatsLatency = new Trend('waste_stats_latency');
const wasteCreateLatency = new Trend('waste_create_latency');
const errorRate = new Rate('error_rate');

// =============================================================================
// Test Scenarios
// =============================================================================

export const options = {
    // Load test configuration
    scenarios: {
        // Warmup - Ramp up to target load
        warmup: {
            executor: 'ramping-vus',
            startVUs: 0,
            targetVUs: 20,
            duration: '30s',
            tags: { scenario: 'warmup' },
        },
        
        // Steady state - 100 concurrent users
        steady_state: {
            executor: 'ramping-vus',
            startVUs: 20,
            targetVUs: VUS,
            duration: DURATION,
            tags: { scenario: 'steady_state' },
        },
        
        // Cool down
        cooldown: {
            executor: 'ramping-vus',
            startVUs: VUS,
            targetVUs: 0,
            duration: '30s',
            tags: { scenario: 'cooldown' },
        },
    },
    
    // Thresholds for SLO compliance
    thresholds: {
        // p95 latency must be under 500ms
        'waste_list_latency': ['p(95)<500'],
        'waste_stats_latency': ['p(95)<500'],
        'waste_create_latency': ['p(95)<600'],  // Slightly higher for write ops
        
        // Error rate must be below 1%
        'error_rate': ['rate<0.01'],
        
        // HTTP status checks
        'http_req_duration': ['p(95)<500'],
    },
};

// =============================================================================
// Test Data
// =============================================================================

// Generate test manifest numbers
function generateManifestNumber() {
    const timestamp = Date.now().toString(36);
    const random = Math.random().toString(36).substring(2, 8);
    return `MAN-${timestamp}-${random}`.toUpperCase();
}

// Test waste movement payload
const testMovement = {
    manifest_number: generateManifestNumber(),
    movement_type: 'transport',
    quantity: 100.5,
    unit: 'kg',
    status: 'pending',
};

// =============================================================================
// Helper Functions
// =============================================================================

// Get auth token (mock for load testing - replace with real auth flow)
function getAuthToken(orgId = 1, userId = 1) {
    // In production, implement actual authentication
    // For load testing, assume token is obtained via separate auth endpoint
    return `mock_token_org${orgId}_user${userId}`;
}

// Make authenticated request with common headers
function authRequest(method, url, body = null, orgId = 1) {
    const headers = {
        'Authorization': `Bearer ${getAuthToken(orgId)}`,
        'Content-Type': 'application/json',
        'X-Org-Id': orgId.toString(),
    };
    
    const params = { headers };
    
    if (body && (method === 'POST' || method === 'PATCH')) {
        return http[method](url, JSON.stringify(body), params);
    }
    
    return http[method](url, params);
}

// =============================================================================
// Test Scenarios
// =============================================================================

export default function () {
    const orgId = (Math.floor(Math.random() * 10) + 1);  // Simulate 10 orgs
    
    // Scenario 1: List waste movements (most common)
    {
        const url = `${BASE_URL}/api/v1/waste?page=1&page_size=20`;
        const start = Date.now();
        
        const res = authRequest('GET', url, null, orgId);
        
        wasteListLatency.add(Date.now() - start);
        
        const success = check(res, {
            'waste list: status 200': (r) => r.status === 200,
            'waste list: has items': (r) => {
                try {
                    const body = JSON.parse(r.body);
                    return body.items !== undefined;
                } catch (e) {
                    return false;
                }
            },
        });
        
        if (!success) {
            errorRate.add(1);
        }
        
        sleep(Math.random() * 2 + 1);  // Random think time 1-3s
    }
    
    // Scenario 2: Get waste stats (dashboard endpoint - critical)
    {
        const url = `${BASE_URL}/api/v1/waste/stats`;
        const start = Date.now();
        
        const res = authRequest('GET', url, null, orgId);
        
        wasteStatsLatency.add(Date.now() - start);
        
        const success = check(res, {
            'waste stats: status 200': (r) => r.status === 200,
            'waste stats: has total': (r) => {
                try {
                    const body = JSON.parse(r.body);
                    return body.total !== undefined;
                } catch (e) {
                    return false;
                }
            },
        });
        
        if (!success) {
            errorRate.add(1);
        }
        
        sleep(Math.random() * 1 + 0.5);  // Random think time 0.5-1.5s
    }
    
    // Scenario 3: Create waste movement (less frequent - 20% of users)
    if (Math.random() < 0.2) {
        const url = `${BASE_URL}/api/v1/waste`;
        
        // Generate unique manifest number
        const movement = { ...testMovement, manifest_number: generateManifestNumber() };
        
        const start = Date.now();
        
        const res = authRequest('POST', url, movement, orgId);
        
        wasteCreateLatency.add(Date.now() - start);
        
        const success = check(res, {
            'waste create: status 201 or 402': (r) => r.status === 201 || r.status === 402,
            'waste create: has id or error': (r) => {
                try {
                    const body = JSON.parse(r.body);
                    return body.id !== undefined || body.detail !== undefined;
                } catch (e) {
                    return false;
                }
            },
        });
        
        if (!success) {
            errorRate.add(1);
        }
        
        sleep(Math.random() * 3 + 2);  // Random think time 2-5s after creation
    }
    
    // Scenario 4: Get single waste movement (random)
    if (Math.random() < 0.3) {
        // Random movement ID 1-100
        const movementId = Math.floor(Math.random() * 100) + 1;
        const url = `${BASE_URL}/api/v1/waste/${movementId}`;
        
        const res = authRequest('GET', url, null, orgId);
        
        check(res, {
            'waste get: status 200 or 404': (r) => r.status === 200 || r.status === 404,
        });
        
        sleep(Math.random() * 2 + 1);
    }
}

// =============================================================================
// Setup and Teardown
// =============================================================================

export function setup() {
    console.log(`Starting PRANELY load test`);
    console.log(`Target: ${VUS} concurrent users for ${DURATION}`);
    console.log(`Base URL: ${BASE_URL}`);
    
    // Verify API is reachable
    const healthRes = http.get(`${BASE_URL}/health`);
    if (healthRes.status !== 200) {
        throw new Error(`API health check failed: ${healthRes.status}`);
    }
    
    console.log('API health check: OK');
    
    return { startTime: Date.now() };
}

export function teardown(data) {
    const duration = (Date.now() - data.startTime) / 1000;
    console.log(`Load test completed in ${duration.toFixed(1)}s`);
    
    // Log summary
    console.log('\n=== Load Test Summary ===');
    console.log(`Duration: ${duration.toFixed(1)}s`);
    console.log(`VUs: ${VUS}`);
}

// =============================================================================
// Handle Summary Report
// =============================================================================

export function handleSummary(data) {
    return {
        'stdout': textSummary(data, { indent: ' ', enableColors: true }),
        'load_test_results.json': JSON.stringify(data, null, 2),
    };
}

function textSummary(data, options) {
    const indent = options.indent || '';
    const enableColors = options.enableColors || false;
    
    const green = enableColors ? '\x1b[32m' : '';
    const red = enableColors ? '\x1b[31m' : '';
    const reset = enableColors ? '\x1b[0m' : '';
    
    let output = '\n' + indent + '=== PRANELY Load Test Results ===\n\n';
    
    // Latency metrics
    output += indent + 'Latency (p95):\n';
    const latency = data.metrics.waste_stats_latency || data.metrics.waste_list_latency;
    if (latency) {
        const p95 = latency.values['p(95)'];
        const status = p95 < 500 ? `${green}PASS${reset}` : `${red}FAIL${reset}`;
        output += indent + `  waste_stats: ${p95?.toFixed(2)}ms ${status}\n`;
    }
    
    if (data.metrics.waste_list_latency) {
        const p95 = data.metrics.waste_list_latency.values['p(95)'];
        const status = p95 < 500 ? `${green}PASS${reset}` : `${red}FAIL${reset}`;
        output += indent + `  waste_list: ${p95?.toFixed(2)}ms ${status}\n`;
    }
    
    if (data.metrics.waste_create_latency) {
        const p95 = data.metrics.waste_create_latency.values['p(95)'];
        const status = p95 < 600 ? `${green}PASS${reset}` : `${red}FAIL${reset}`;
        output += indent + `  waste_create: ${p95?.toFixed(2)}ms ${status}\n`;
    }
    
    // Error rate
    output += '\n' + indent + 'Error Rate:\n';
    if (data.metrics.error_rate) {
        const rate = data.metrics.error_rate.values['rate'];
        const status = rate < 0.01 ? `${green}PASS${reset}` : `${red}FAIL${reset}`;
        output += indent + `  errors: ${(rate * 100).toFixed(2)}% ${status}\n`;
    }
    
    // Request throughput
    if (data.metrics.http_reqs) {
        const rps = data.metrics.http_reqs.values['rate'];
        output += '\n' + indent + 'Throughput:\n';
        output += indent + `  requests/sec: ${rps.toFixed(2)}\n`;
    }
    
    // Overall status
    const allPassed = checkAllThresholds(data);
    output += '\n' + indent + `Overall: ${allPassed ? green + 'PASS' + reset : red + 'FAIL' + reset}\n`;
    
    return output;
}

function checkAllThresholds(data) {
    const checks = [
        { metric: 'waste_stats_latency', threshold: 500 },
        { metric: 'waste_list_latency', threshold: 500 },
    ];
    
    for (const check of checks) {
        if (data.metrics[check.metric]) {
            const p95 = data.metrics[check.metric].values['p(95)'];
            if (p95 > check.threshold) {
                return false;
            }
        }
    }
    
    if (data.metrics.error_rate) {
        if (data.metrics.error_rate.values['rate'] > 0.01) {
            return false;
        }
    }
    
    return true;
}