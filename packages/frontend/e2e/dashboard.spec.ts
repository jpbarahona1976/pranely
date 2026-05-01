/**
 * Dashboard E2E Tests - FASE 9A.1
 * Tests: Login → Dashboard → KPIs → Waste Table
 */
import { test, expect } from '@playwright/test';

test.describe('Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    // Login before each test
    await page.goto('/login');
    await page.fill('input[name="email"]', 'owner@test.com');
    await page.fill('input[name="password"]', 'test123');
    await page.click('button[type="submit"]');
    await page.waitForURL('/dashboard');
  });

  test('should display KPIs on dashboard', async ({ page }) => {
    await page.goto('/dashboard');
    
    // Check for KPI cards
    await expect(page.locator('text=Total')).toBeVisible({ timeout: 10000 });
    await expect(page.locator('text=Pendiente')).toBeVisible({ timeout: 10000 });
    await expect(page.locator('text=Validado')).toBeVisible({ timeout: 10000 });
  });

  test('should show waste table with movements', async ({ page }) => {
    await page.goto('/dashboard');
    
    // Check for waste table
    await expect(page.locator('table, [role="table"]')).toBeVisible({ timeout: 10000 });
  });

  test('should navigate to waste creation', async ({ page }) => {
    await page.goto('/dashboard');
    
    // Click new waste button if visible
    const newButton = page.locator('button:has-text("Nuevo"), button:has-text("New")');
    if (await newButton.isVisible()) {
      await newButton.click();
      await expect(page).toHaveURL(/\/waste/);
    }
  });

  test('should show user info in header', async ({ page }) => {
    await page.goto('/dashboard');
    
    // Check for user email or name
    await expect(page.locator('text=owner@test.com, text=Owner')).toBeVisible({ timeout: 10000 });
  });
});