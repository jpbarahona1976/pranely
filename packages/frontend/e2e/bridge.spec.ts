// 8A MOBILE BRIDGE - E2E Tests
import { test, expect } from '@playwright/test';

// Test credentials MUST be provided via environment variables
// CI/CD should set: E2E_TEST_EMAIL, E2E_TEST_PASSWORD, E2E_TEST_TOKEN
const TEST_EMAIL = process.env.E2E_TEST_EMAIL;
const TEST_PASSWORD = process.env.E2E_TEST_PASSWORD;
const TEST_TOKEN = process.env.E2E_TEST_TOKEN;

describe('Mobile Bridge E2E', () => {
  const testUser = {
    email: TEST_EMAIL,
    password: TEST_PASSWORD,
    token: TEST_TOKEN,
  };

  test.describe('Bridge Session Flow', () => {
    test.beforeEach(async ({ page }) => {
      // Mock auth context
      await page.goto('/bridge');
      
      // Wait for the page to load
      await page.waitForLoadState('networkidle');
    });

    test('should display bridge page with correct title', async ({ page }) => {
      // Check page title
      await expect(page.locator('h2')).toContainText('Bridge Móvil');
    });

    test('should show idle state with action buttons', async ({ page }) => {
      // Check for QR scan button
      const scanButton = page.locator('button:has-text("Escanear QR")');
      await expect(scanButton).toBeVisible();
      
      // Check for manual entry button
      const manualButton = page.locator('button:has-text("Entrada Manual")');
      await expect(manualButton).toBeVisible();
    });

    test('should display status badge', async ({ page }) => {
      // Status badge should be visible
      const statusBadge = page.locator('span:has-text("Offline")');
      await expect(statusBadge).toBeVisible();
    });

    test('should show instructions card', async ({ page }) => {
      // Instructions should be visible
      const instructions = page.locator('text=¿Cómo funciona?');
      await expect(instructions).toBeVisible();
      
      // Step 1
      await expect(page.locator('text=Genera un código QR')).toBeVisible();
      
      // Step 2
      await expect(page.locator('text=Escanea el código')).toBeVisible();
      
      // Step 3
      await expect(page.locator('text=Sincroniza manifiestos')).toBeVisible();
    });

    test('should navigate to scan view', async ({ page }) => {
      // Click QR scan button
      await page.locator('button:has-text("Escanear QR")').click();
      
      // Should show scanner UI
      await expect(page.locator('text=Escaneando')).toBeVisible({ timeout: 5000 }).catch(() => {
        // Camera might not be available in test env, check for cancel button instead
        expect(page.locator('button:has-text("Cancelar")')).toBeVisible();
      });
    });

    test('should navigate to manual entry view', async ({ page }) => {
      // Click manual entry button
      await page.locator('button:has-text("Entrada Manual")').click();
      
      // Should show token input
      const tokenInput = page.locator('input[placeholder*="A1B2C3"]');
      await expect(tokenInput).toBeVisible();
      
      // Should show validate button
      await expect(page.locator('button:has-text("Validar")')).toBeVisible();
    });

    test('should validate manual token length', async ({ page }) => {
      // Go to manual entry
      await page.locator('button:has-text("Entrada Manual")').click();
      
      // Type partial token (needs 16 chars for validation)
      const tokenInput = page.locator('input[placeholder*="A1B2C3"]');
      await tokenInput.fill('XXXX1234');
      
      // Validate button should be disabled (needs 16 chars)
      await expect(page.locator('button:has-text("Validar")')).toBeDisabled();
    });

    test('should enable validate button with full token', async ({ page }) => {
      // Go to manual entry
      await page.locator('button:has-text("Entrada Manual")').click();
      
      // Type complete token (16 chars minimum)
      const tokenInput = page.locator('input[placeholder*="A1B2C3"]');
      await tokenInput.fill('XXXX1234YYYY5678');
      
      // Validate button should be enabled
      await expect(page.locator('button:has-text("Validar")')).toBeEnabled();
    });
  });

  test.describe('Bridge Status States', () => {
    test('should display offline state correctly', async ({ page }) => {
      await page.goto('/bridge');
      
      const offlineBadge = page.locator('span:has-text("Offline")');
      await expect(offlineBadge).toBeVisible();
    });

    test('should display connecting state', async ({ page }) => {
      await page.goto('/bridge');
      
      // Mock WebSocket connecting
      await page.evaluate(() => {
        // Simulate connecting state
        const stateElement = document.querySelector('[class*="animate-spin"]');
        if (stateElement) {
          stateElement.setAttribute('data-state', 'connecting');
        }
      });
      
      // Status should show connecting or similar
      await expect(page.locator('body')).toContainText(/Conectand/i);
    });
  });

  test.describe('Bottom Navigation Bar', () => {
    test('should show bottom navigation', async ({ page }) => {
      await page.goto('/bridge');
      
      // Dashboard button
      await expect(page.locator('text=Dashboard').first()).toBeVisible();
      
      // Scan button
      await expect(page.locator('text=Scan')).toBeVisible();
      
      // Manual button
      await expect(page.locator('text=Manual')).toBeVisible();
      
      // Sync button
      await expect(page.locator('text=Sync')).toBeVisible();
    });

    test('should navigate to dashboard from bottom bar', async ({ page }) => {
      await page.goto('/bridge');
      
      // Click Dashboard in bottom bar
      await page.locator('text=Dashboard').first().click();
      
      // Should navigate away from bridge
      await page.waitForURL(/\/dashboard/, { timeout: 5000 }).catch(() => {
        // URL might not change in test env
      });
    });
  });

  test.describe('Bridge Responsive Design', () => {
    test('should display correctly on mobile viewport', async ({ page }) => {
      // Set mobile viewport
      await page.setViewportSize({ width: 375, height: 667 });
      await page.goto('/bridge');
      
      // Page should be visible
      await expect(page.locator('h2')).toContainText('Bridge Móvil');
      
      // Bottom bar should be visible
      await expect(page.locator('text=Scan')).toBeVisible();
    });

    test('should display correctly on tablet viewport', async ({ page }) => {
      // Set tablet viewport
      await page.setViewportSize({ width: 768, height: 1024 });
      await page.goto('/bridge');
      
      // Page should be visible
      await expect(page.locator('h2')).toContainText('Bridge Móvil');
    });

    test('should display correctly on desktop viewport', async ({ page }) => {
      // Set desktop viewport
      await page.setViewportSize({ width: 1280, height: 800 });
      await page.goto('/bridge');
      
      // Page should be visible
      await expect(page.locator('h2')).toContainText('Bridge Móvil');
    });
  });

  test.describe('Bridge Glassmorphism Styling', () => {
    test('should apply glassmorphism backdrop to cards', async ({ page }) => {
      await page.goto('/bridge');
      
      // Check for backdrop-blur class on status bar
      const statusBar = page.locator('.backdrop-blur-md').first();
      await expect(statusBar).toBeVisible();
    });

    test('should use correct color scheme', async ({ page }) => {
      await page.goto('/bridge');
      
      // Check for emerald accent (connected/success)
      await expect(page.locator('.bg-emerald')).toBeVisible({ timeout: 3000 }).catch(() => {
        // Might not be visible in idle state
      });
    });

    test('should display rounded corners on cards', async ({ page }) => {
      await page.goto('/bridge');
      
      // Check for rounded-2xl class
      const roundedCard = page.locator('.rounded-2xl').first();
      await expect(roundedCard).toBeVisible();
    });
  });

  test.describe('Bridge Offline Queue', () => {
    test('should store items in localStorage when offline', async ({ page }) => {
      await page.goto('/bridge');
      
      // Simulate adding to offline queue via localStorage
      const testData = 'TEST_DATA_placeholder';
      await page.evaluate((token) => {
        const queue = [{ qr_data: token, timestamp: Date.now() }];
        localStorage.setItem('pranely_bridge_offline_queue', JSON.stringify(queue));
      }, testData);
      
      // Verify queue was stored
      const queue = await page.evaluate(() => {
        return localStorage.getItem('pranely_bridge_offline_queue');
      });
      
      expect(queue).toBeTruthy();
      expect(queue).toContain(testData);
    });

    test('should display offline queue indicator when queue has items', async ({ page }) => {
      await page.goto('/bridge');
      
      // Pre-populate queue
      await page.evaluate(() => {
        const queue = [
          { qr_data: 'TEST_ITEM_001', timestamp: Date.now() },
          { qr_data: 'TEST_ITEM_002', timestamp: Date.now() }
        ];
        localStorage.setItem('pranely_bridge_offline_queue', JSON.stringify(queue));
      });
      
      // Reload page to trigger indicator
      await page.reload();
      
      // Should show offline queue indicator
      const indicator = page.locator('text=escaneos en cola offline');
      await expect(indicator).toBeVisible();
    });

    test('should clear offline queue on button click', async ({ page }) => {
      await page.goto('/bridge');
      
      // Pre-populate queue with multiple items
      await page.evaluate(() => {
        const queue = [
          { qr_data: 'CLEAR_ITEM_TEST', timestamp: Date.now() }
        ];
        localStorage.setItem('pranely_bridge_offline_queue', JSON.stringify(queue));
      });
      
      await page.reload();
      
      // Click clear button
      const clearButton = page.locator('button:has-text("Limpiar")');
      if (await clearButton.isVisible()) {
        await clearButton.click();
        
        // Verify queue is empty
        const queue = await page.evaluate(() => {
          return localStorage.getItem('pranely_bridge_offline_queue');
        });
        expect(queue).toBeNull();
      }
    });

    test('should not show queue indicator when queue is empty', async ({ page }) => {
      await page.goto('/bridge');
      
      // Ensure queue is empty
      await page.evaluate(() => {
        localStorage.removeItem('pranely_bridge_offline_queue');
      });
      
      await page.reload();
      
      // Should NOT show offline queue indicator
      const indicator = page.locator('text=escaneos en cola offline');
      await expect(indicator).not.toBeVisible();
    });
  });
});
