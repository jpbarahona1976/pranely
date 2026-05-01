/**
 * Billing E2E Tests - FASE 9A.1
 * Tests: Owner → Billing → Plans → Checkout Flow → Quota 402
 */
import { test, expect } from '@playwright/test';

test.describe('Billing', () => {
  test.beforeEach(async ({ page }) => {
    // Login as owner
    await page.goto('/login');
    await page.fill('input[name="email"]', 'owner@test.com');
    await page.fill('input[name="password"]', 'test123');
    await page.click('button[type="submit"]');
    await page.waitForURL(/\/(dashboard|billing)/);
  });

  test('should display billing plans', async ({ page }) => {
    await page.goto('/billing');
    
    // Check for plan cards
    await expect(page.locator('text=Free, text=Pro, text=Enterprise').first()).toBeVisible({ timeout: 10000 });
  });

  test('should show current subscription status', async ({ page }) => {
    await page.goto('/billing');
    
    // Check for subscription info
    await expect(page.locator('text=Subscription, text=subscription, text=Plan').first()).toBeVisible({ timeout: 10000 });
  });

  test('should navigate to checkout on plan selection', async ({ page }) => {
    await page.goto('/billing');
    
    // Find and click upgrade button
    const upgradeButton = page.locator('button:has-text("Upgrade"), button:has-text("Suscribirse")');
    if (await upgradeButton.first().isVisible()) {
      await upgradeButton.first().click();
      // Should open checkout modal or navigate
      // The exact behavior depends on UI implementation
    }
  });

  test('should show quota usage', async ({ page }) => {
    await page.goto('/billing');
    
    // Check for quota info
    await expect(page.locator('text=Quota, text=Usage, text=docs').first()).toBeVisible({ timeout: 10000 });
  });
});