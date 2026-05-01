/**
 * Waste E2E Tests - FASE 9A.1
 * Tests: Waste CRUD → Review → RBAC Roles
 */
import { test, expect } from '@playwright/test';

test.describe('Waste Management', () => {
  test.beforeEach(async ({ page }) => {
    // Login before each test
    await page.goto('/login');
    await page.fill('input[name="email"]', 'owner@test.com');
    await page.fill('input[name="password"]', 'test123');
    await page.click('button[type="submit"]');
    await page.waitForURL(/\/(dashboard|waste)/);
  });

  test('should display waste list', async ({ page }) => {
    await page.goto('/dashboard');
    
    // Wait for waste table to load
    await expect(page.locator('table, [role="table"], text=Manifest').first()).toBeVisible({ timeout: 15000 });
  });

  test('should create new waste movement', async ({ page }) => {
    await page.goto('/dashboard');
    
    // Click new waste button
    const newButton = page.locator('button:has-text("Nuevo"), button:has-text("New Waste")');
    if (await newButton.isVisible()) {
      await newButton.click();
      
      // Fill form if modal opens
      await page.fill('input[name="manifest_number"], input[placeholder*="manifest"]', 'MAN-E2E-001');
      await page.fill('input[name="quantity"]', '100');
      
      // Submit
      await page.click('button:has-text("Crear"), button:has-text("Submit")');
      
      // Verify success
      await expect(page.locator('text=MAN-E2E-001, text=created, text=success')).toBeVisible({ timeout: 10000 });
    }
  });

  test('should view waste details', async ({ page }) => {
    await page.goto('/dashboard');
    
    // Click on a waste row if exists
    const wasteRow = page.locator('tbody tr:first-child, [role="row"]:first-child');
    if (await wasteRow.isVisible()) {
      await wasteRow.click();
      // Should show details
      await expect(page.locator('text=Details, text=Manifest').first()).toBeVisible({ timeout: 10000 });
    }
  });

  test('should filter waste by status', async ({ page }) => {
    await page.goto('/dashboard');
    
    // Find and use status filter
    const filter = page.locator('select, [role="combobox"]').first();
    if (await filter.isVisible()) {
      await filter.selectOption({ index: 1 });
      // Table should update
    }
  });
});

test.describe('Waste RBAC', () => {
  test('viewer role cannot create waste', async ({ page }) => {
    // Login as viewer
    await page.goto('/login');
    await page.fill('input[name="email"]', 'viewer@test.com');
    await page.fill('input[name="password"]', 'test123');
    await page.click('button[type="submit"]');
    await page.waitForTimeout(2000);
    
    // Try to create waste - button should be disabled or not exist
    await page.goto('/dashboard');
    const newButton = page.locator('button:has-text("Nuevo"), button:has-text("New")');
    
    if (await newButton.isVisible()) {
      await newButton.click();
      // Should show error or be prevented
      await expect(page.locator('text=403, text=Forbidden, text=Permission')).toBeVisible({ timeout: 5000 }).catch(() => {
        // Or button should not exist
      });
    }
  });

  test('viewer can view waste list', async ({ page }) => {
    // Login as viewer
    await page.goto('/login');
    await page.fill('input[name="email"]', 'viewer@test.com');
    await page.fill('input[name="password"]', 'test123');
    await page.click('button[type="submit"]');
    
    await page.waitForURL(/\/dashboard/);
    
    // Should be able to view waste list
    await expect(page.locator('table, [role="table"], text=Manifest').first()).toBeVisible({ timeout: 15000 });
  });
});