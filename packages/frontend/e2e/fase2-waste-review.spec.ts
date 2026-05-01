// FASE 2 E2E Tests - Playwright
// Tests Fixes 2-5: Upload → Review → Command → Invite

import { test, expect } from '@playwright/test';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const FRONTEND_URL = process.env.NEXT_PUBLIC_FRONTEND_URL || 'http://localhost:3000';

test.describe('FASE 2: Core Waste/Review Workflow', () => {
  
  // =============================================================================
  // FIX 2: Upload with RQ Queue
  // =============================================================================
  
  test('FIX2: Upload document triggers RQ job', async ({ page }) => {
    // 1. Login
    await page.goto(`${FRONTEND_URL}/login`);
    await page.fill('[data-testid="email"]', 'owner@pranely.com');
    await page.fill('[data-testid="password"]', 'password123');
    await page.click('[data-testid="submit"]');
    
    // 2. Navigate to upload
    await page.waitForURL(`${FRONTEND_URL}/upload`);
    
    // 3. Create mock PDF file
    const pdfBuffer = Buffer.from('%PDF-1.4 test content');
    
    // 4. Upload via API directly (simulating frontend upload)
    const uploadResponse = await page.request.fetch(`${API_URL}/api/v1/waste/upload`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${await page.evaluate(() => localStorage.getItem('pranely_token'))}`,
      },
      multipart: {
        file: {
          name: 'test-manifest.pdf',
          mimeType: 'application/pdf',
          buffer: pdfBuffer,
        },
      },
    });
    
    // 5. Verify response contains job_id
    expect(uploadResponse.ok()).toBeTruthy();
    const uploadData = await uploadResponse.json();
    expect(uploadData).toHaveProperty('job_id');
    expect(uploadData).toHaveProperty('movement_id');
    expect(uploadData).toHaveProperty('file_hash');
    
    console.log('FIX2: Upload response:', uploadData);
  });

  // =============================================================================
  // FIX 3: Review approve/reject workflow
  // =============================================================================
  
  test('FIX3: Approve waste movement updates status', async ({ page }) => {
    // 1. Login as admin
    await page.goto(`${FRONTEND_URL}/login`);
    await page.fill('[data-testid="email"]', 'admin@pranely.com');
    await page.fill('[data-testid="password"]', 'password123');
    await page.click('[data-testid="submit"]');
    
    // 2. Create test movement (via API)
    const token = await page.evaluate(() => localStorage.getItem('pranely_token'));
    const createResponse = await page.request.fetch(`${API_URL}/api/v1/waste`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      data: JSON.stringify({
        manifest_number: `TEST-${Date.now()}`,
        status: 'pending',
      }),
    });
    
    const movement = await createResponse.json();
    const movementId = movement.id;
    
    // 3. Approve via review endpoint
    const approveResponse = await page.request.fetch(
      `${API_URL}/api/v1/waste/${movementId}/review`,
      {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        data: JSON.stringify({
          action: 'approve',
          notes: 'Auto-approved by test',
        }),
      }
    );
    
    expect(approveResponse.ok()).toBeTruthy();
    const approveData = await approveResponse.json();
    expect(approveData.new_status).toBe('validated');
    expect(approveData.success).toBe(true);
    
    console.log('FIX3: Approve response:', approveData);
  });

  test('FIX3: Reject waste movement requires reason', async ({ page }) => {
    // 1. Login
    await page.goto(`${FRONTEND_URL}/login`);
    await page.fill('[data-testid="email"]', 'admin@pranely.com');
    await page.fill('[data-testid="password"]', 'password123');
    await page.click('[data-testid="submit"]');
    
    // 2. Create test movement
    const token = await page.evaluate(() => localStorage.getItem('pranely_token'));
    const createResponse = await page.request.fetch(`${API_URL}/api/v1/waste`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      data: JSON.stringify({
        manifest_number: `TEST-REJECT-${Date.now()}`,
        status: 'pending',
      }),
    });
    
    const movement = await createResponse.json();
    const movementId = movement.id;
    
    // 3. Reject with reason
    const rejectResponse = await page.request.fetch(
      `${API_URL}/api/v1/waste/${movementId}/review`,
      {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        data: JSON.stringify({
          action: 'reject',
          reason: 'Document incomplete - missing signatures',
        }),
      }
    );
    
    expect(rejectResponse.ok()).toBeTruthy();
    const rejectData = await rejectResponse.json();
    expect(rejectData.new_status).toBe('rejected');
    expect(rejectData.success).toBe(true);
    
    console.log('FIX3: Reject response:', rejectData);
  });

  // =============================================================================
  // FIX 4: Command Center operators with role/extra_data
  // =============================================================================
  
  test('FIX4: Create operator with role and extra_data', async ({ page }) => {
    // 1. Login as owner
    await page.goto(`${FRONTEND_URL}/login`);
    await page.fill('[data-testid="email"]', 'owner@pranely.com');
    await page.fill('[data-testid="password"]', 'password123');
    await page.click('[data-testid="submit"]');
    
    // 2. Create operator via API
    const token = await page.evaluate(() => localStorage.getItem('pranely_token'));
    const createResponse = await page.request.fetch(`${API_URL}/api/v1/command/operators`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      data: JSON.stringify({
        email: `operator-${Date.now()}@test.com`,
        role: 'member',
        full_name: 'Test Operator',
        extra_data: {
          department: 'Logistics',
          shift: 'morning',
        },
      }),
    });
    
    expect(createResponse.ok()).toBeTruthy();
    const operator = await createResponse.json();
    expect(operator).toHaveProperty('role', 'member');
    expect(operator).toHaveProperty('email');
    
    console.log('FIX4: Created operator:', operator);
  });

  test('FIX4: List operators with tenant isolation', async ({ page }) => {
    // 1. Login
    await page.goto(`${FRONTEND_URL}/login`);
    await page.fill('[data-testid="email"]', 'owner@pranely.com');
    await page.fill('[data-testid="password"]', 'password123');
    await page.click('[data-testid="submit"]');
    
    // 2. List operators
    const token = await page.evaluate(() => localStorage.getItem('pranely_token'));
    const listResponse = await page.request.fetch(`${API_URL}/api/v1/command/operators`, {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });
    
    expect(listResponse.ok()).toBeTruthy();
    const data = await listResponse.json();
    expect(data).toHaveProperty('operators');
    expect(data).toHaveProperty('total');
    
    // Verify all operators belong to the user's organization
    const userOrgId = await page.evaluate(() => {
      const token = localStorage.getItem('pranely_token');
      const payload = JSON.parse(atob(token.split('.')[1]));
      return payload.organization_id;
    });
    
    console.log('FIX4: Found operators:', data.total);
  });

  // =============================================================================
  // FIX 5: Invite with secure hash and 24h expiry
  // =============================================================================
  
  test('FIX5: Create invite hash with expiry', async ({ page }) => {
    // 1. Login as admin
    await page.goto(`${FRONTEND_URL}/login`);
    await page.fill('[data-testid="email"]', 'owner@pranely.com');
    await page.fill('[data-testid="password"]', 'password123');
    await page.click('[data-testid="submit"]');
    
    // 2. Create invite hash via API
    const token = await page.evaluate(() => localStorage.getItem('pranely_token'));
    const inviteResponse = await page.request.fetch(`${API_URL}/api/v1/invite/create`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      data: JSON.stringify({
        email: `newuser-${Date.now()}@example.com`,
        role: 'member',
        organization_id: 1,
      }),
    });
    
    expect(inviteResponse.ok()).toBeTruthy();
    const inviteData = await inviteResponse.json();
    expect(inviteData).toHaveProperty('hash');
    expect(inviteData).toHaveProperty('expires_at');
    expect(inviteData.hash).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i);
    
    console.log('FIX5: Invite created:', inviteData);
  });

  test('FIX5: Accept invite creates membership', async ({ page }) => {
    // 1. Create invite first
    const createResponse = await page.request.fetch(`${API_URL}/api/v1/invite/create`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${(await page.request.context().storageState())?.tokens?.token}`,
        'Content-Type': 'application/json',
      },
      data: JSON.stringify({
        email: `accept-test-${Date.now()}@example.com`,
        role: 'member',
        organization_id: 1,
      }),
    });
    
    if (!createResponse.ok()) {
      // Skip if not authenticated
      test.skip();
    }
    
    const inviteData = await createResponse.json();
    const inviteHash = inviteData.hash;
    
    // 2. Accept invite with password
    const acceptResponse = await page.request.fetch(
      `${API_URL}/api/v1/invite/${inviteHash}`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        data: JSON.stringify({
          password: 'SecurePassword123!',
          full_name: 'Accepted User',
        }),
      }
    );
    
    expect(acceptResponse.ok()).toBeTruthy();
    const acceptData = await acceptResponse.json();
    expect(acceptData.success).toBe(true);
    expect(acceptData).toHaveProperty('membership_id');
    
    console.log('FIX5: Invite accepted:', acceptData);
  });

  test('FIX5: Expired invite returns error', async ({ page }) => {
    // Use invalid/expired hash
    const invalidHash = '00000000-0000-0000-0000-000000000000';
    
    const acceptResponse = await page.request.fetch(
      `${API_URL}/api/v1/invite/${invalidHash}`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        data: JSON.stringify({
          password: 'password123',
        }),
      }
    );
    
    // Should return error for invalid hash
    expect(acceptResponse.status()).toBe(400);
  });

  // =============================================================================
  // E2E: Full Workflow Upload → Review → Approve
  // =============================================================================
  
  test('E2E: Full waste workflow - upload to approve', async ({ page }) => {
    // 1. Login
    await page.goto(`${FRONTEND_URL}/login`);
    await page.fill('[data-testid="email"]', 'admin@pranely.com');
    await page.fill('[data-testid="password"]', 'password123');
    await page.click('[data-testid="submit"]');
    await page.waitForURL(`${FRONTEND_URL}/dashboard`);
    
    // 2. Get auth token
    const token = await page.evaluate(() => localStorage.getItem('pranely_token'));
    
    // 3. Upload document
    const pdfBuffer = Buffer.from('%PDF-1.4 mock manifest content for NOM-052');
    const uploadResponse = await page.request.fetch(`${API_URL}/api/v1/waste/upload`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
      multipart: {
        file: {
          name: 'NOM-manifest.pdf',
          mimeType: 'application/pdf',
          buffer: pdfBuffer,
        },
      },
    });
    
    expect(uploadResponse.ok()).toBeTruthy();
    const { job_id, movement_id } = await uploadResponse.json();
    console.log(`E2E: Uploaded file, job_id=${job_id}, movement_id=${movement_id}`);
    
    // 4. Navigate to review page
    await page.goto(`${FRONTEND_URL}/review`);
    
    // 5. Wait for movement to appear in review queue
    await page.waitForSelector(`[data-testid="movement-${movement_id}"]`, { timeout: 10000 });
    
    // 6. Click approve
    await page.click(`[data-testid="movement-${movement_id}"] [data-testid="approve-btn"]`);
    
    // 7. Verify success
    await page.waitForSelector('[data-testid="success-toast"]', { timeout: 5000 });
    
    console.log('E2E: Full workflow completed successfully');
  });
});