// Playwright E2E tests for Command Center - Phase 8B
import { test, expect } from "@playwright/test";

const BASE_URL = process.env.E2E_BASE_URL || "http://localhost:3000";
const API_URL = process.env.E2E_API_URL || "http://localhost:8000";

// Test users - these should exist in test database
const OWNER_EMAIL = "owner@test.com";
const ADMIN_EMAIL = "admin@test.com";
const MEMBER_EMAIL = "member@test.com";
const VIEWER_EMAIL = "viewer@test.com";
const TEST_PASSWORD = "password123";

// Helper to login via API and get token
async function loginApi(email: string): Promise<string> {
  const response = await fetch(`${API_URL}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password: TEST_PASSWORD }),
  });
  
  if (!response.ok) {
    throw new Error(`Login failed for ${email}`);
  }
  
  const data = await response.json();
  return data.token.access_token;
}

// Helper to set token in localStorage
async function setAuthToken(page: any, token: string) {
  await page.evaluate((t: string) => {
    localStorage.setItem("pranely_token", t);
  }, token);
}

// ============================================================================
// ACCESS CONTROL TESTS
// ============================================================================

test.describe("Command Center Access Control", () => {
  test.beforeEach(async ({ page }) => {
    // Clear storage
    await page.goto(BASE_URL);
    await page.evaluate(() => localStorage.clear());
  });

  test("owner can access command center", async ({ page }) => {
    const token = await loginApi(OWNER_EMAIL);
    await setAuthToken(page, token);
    
    await page.goto(`${BASE_URL}/command`);
    await page.waitForLoadState("networkidle");
    
    // Should see Command Center header
    await expect(page.locator("h1:has-text('Command Center')")).toBeVisible({ timeout: 10000 });
  });

  test("admin can access command center", async ({ page }) => {
    const token = await loginApi(ADMIN_EMAIL);
    await setAuthToken(page, token);
    
    await page.goto(`${BASE_URL}/command`);
    await page.waitForLoadState("networkidle");
    
    // Should see Command Center header
    await expect(page.locator("h1:has-text('Command Center')")).toBeVisible({ timeout: 10000 });
  });

  test("member cannot access command center", async ({ page }) => {
    const token = await loginApi(MEMBER_EMAIL);
    await setAuthToken(page, token);
    
    await page.goto(`${BASE_URL}/command`);
    await page.waitForLoadState("networkidle");
    
    // Should either redirect to login or show 403
    const url = page.url();
    expect(url).toMatch(/login|403/);
  });

  test("viewer cannot access command center", async ({ page }) => {
    const token = await loginApi(VIEWER_EMAIL);
    await setAuthToken(page, token);
    
    await page.goto(`${BASE_URL}/command`);
    await page.waitForLoadState("networkidle");
    
    // Should either redirect to login or show 403
    const url = page.url();
    expect(url).toMatch(/login|403/);
  });

  test("unauthenticated user redirected to login", async ({ page }) => {
    await page.goto(`${BASE_URL}/command`);
    await page.waitForLoadState("networkidle");
    
    // Should redirect to login
    await expect(page).toHaveURL(/login/);
  });
});

// ============================================================================
// OPERATORS TAB TESTS
// ============================================================================

test.describe("Operators Tab", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(BASE_URL);
    await page.evaluate(() => localStorage.clear());
    
    const token = await loginApi(OWNER_EMAIL);
    await setAuthToken(page, token);
    
    await page.goto(`${BASE_URL}/command`);
    await page.waitForLoadState("networkidle");
    
    // Ensure operators tab is active
    await page.click('button:has-text("Operadores")');
  });

  test("displays operators list", async ({ page }) => {
    // Should show operators count
    await expect(page.locator("text=operadores")).toBeVisible({ timeout: 10000 });
    
    // Should show some operator entries
    const operatorCards = page.locator('[class*="bg-white/5"]');
    await expect(operatorCards.first()).toBeVisible();
  });

  test("shows role badges", async ({ page }) => {
    // Should show role badges (owner, admin, etc.)
    const roleBadges = page.locator("span:has-text('owner'), span:has-text('admin')");
    await expect(roleBadges.first()).toBeVisible({ timeout: 5000 });
  });

  test("invite button visible for owner", async ({ page }) => {
    // Owner should see invite button
    const inviteButton = page.locator('button:has-text("Invitar operador")');
    await expect(inviteButton).toBeVisible();
  });
});

// ============================================================================
// CONFIGURATION TAB TESTS
// ============================================================================

test.describe("Configuration Tab", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(BASE_URL);
    await page.evaluate(() => localStorage.clear());
    
    const token = await loginApi(OWNER_EMAIL);
    await setAuthToken(page, token);
    
    await page.goto(`${BASE_URL}/command`);
    await page.waitForLoadState("networkidle");
    
    // Navigate to config tab
    await page.click('button:has-text("Configuración")');
  });

  test("displays configuration form", async ({ page }) => {
    // Should show form fields
    await expect(page.locator('input[placeholder*="Nombre de la organización"]')).toBeVisible({ timeout: 5000 });
    await expect(page.locator('input[placeholder*="Industria"]')).toBeVisible();
  });

  test("form fields are editable for owner", async ({ page }) => {
    // Owner should be able to edit
    const nameInput = page.locator('input[placeholder*="Nombre de la organización"]');
    await expect(nameInput).toBeEnabled();
  });

  test("shows timezone field", async ({ page }) => {
    // Should show timezone
    await expect(page.locator('input[value*="America/Mexico"]')).toBeVisible({ timeout: 5000 });
  });
});

// ============================================================================
// QUOTAS TAB TESTS
// ============================================================================

test.describe("Quotas Tab", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(BASE_URL);
    await page.evaluate(() => localStorage.clear());
    
    const token = await loginApi(OWNER_EMAIL);
    await setAuthToken(page, token);
    
    await page.goto(`${BASE_URL}/command`);
    await page.waitForLoadState("networkidle");
    
    // Navigate to quotas tab
    await page.click('button:has-text("Cuotas")');
  });

  test("displays current plan", async ({ page }) => {
    // Should show plan name
    await expect(page.locator("text=/Plan actual/i")).toBeVisible({ timeout: 5000 });
  });

  test("shows usage progress bar", async ({ page }) => {
    // Should show progress bar
    const progressBar = page.locator('[class*="rounded-full"][class*="bg-emerald"]');
    await expect(progressBar.first()).toBeVisible({ timeout: 5000 });
  });

  test("shows remaining docs count", async ({ page }) => {
    // Should show remaining count
    await expect(page.locator("text=/Restantes/i")).toBeVisible();
  });
});

// ============================================================================
// FEATURES TAB TESTS
// ============================================================================

test.describe("Features Tab", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(BASE_URL);
    await page.evaluate(() => localStorage.clear());
    
    const token = await loginApi(OWNER_EMAIL);
    await setAuthToken(page, token);
    
    await page.goto(`${BASE_URL}/command`);
    await page.waitForLoadState("networkidle");
    
    // Navigate to features tab
    await page.click('button:has-text("Funciones")');
  });

  test("lists feature flags", async ({ page }) => {
    // Should show feature toggles
    const toggles = page.locator('[class*="w-12 h-6"][class*="rounded-full"]');
    await expect(toggles.first()).toBeVisible({ timeout: 5000 });
  });

  test("toggles are interactive for owner", async ({ page }) => {
    // Should be able to toggle features
    const toggle = page.locator('[class*="w-12 h-6"][class*="rounded-full"]').first();
    await expect(toggle).toBeEnabled();
  });
});

// ============================================================================
// AUDIT TAB TESTS
// ============================================================================

test.describe("Audit Tab", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(BASE_URL);
    await page.evaluate(() => localStorage.clear());
    
    const token = await loginApi(OWNER_EMAIL);
    await setAuthToken(page, token);
    
    await page.goto(`${BASE_URL}/command`);
    await page.waitForLoadState("networkidle");
    
    // Navigate to audit tab
    await page.click('button:has-text("Auditoría")');
  });

  test("displays audit entries", async ({ page }) => {
    // Should show audit log entries or empty state
    const auditEntries = page.locator("text=/operator\\.|config\\.|feature\\./i");
    
    // Either has entries or shows empty state
    const hasEntries = await auditEntries.count() > 0;
    const hasEmptyState = await page.locator("text=/Sin registros|No hay/i").count() > 0;
    
    expect(hasEntries || hasEmptyState).toBeTruthy();
  });
});

// ============================================================================
// STATS DISPLAY TESTS
// ============================================================================

test.describe("Stats Display", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(BASE_URL);
    await page.evaluate(() => localStorage.clear());
    
    const token = await loginApi(OWNER_EMAIL);
    await setAuthToken(page, token);
    
    await page.goto(`${BASE_URL}/command`);
    await page.waitForLoadState("networkidle");
  });

  test("shows stats cards at top", async ({ page }) => {
    // Should show stats cards
    await expect(page.locator("text=/Operadores/i").first()).toBeVisible({ timeout: 5000 });
    await expect(page.locator("text=/Plan/i").first()).toBeVisible();
    await expect(page.locator("text=/Uso docs/i").first()).toBeVisible();
  });

  test("stats update button works", async ({ page }) => {
    // Refresh button should be present
    const refreshButton = page.locator('[title="Actualizar"]');
    await expect(refreshButton).toBeVisible();
    
    // Click should trigger reload
    await refreshButton.click();
    
    // Page should still be functional
    await expect(page.locator("h1:has-text('Command Center')")).toBeVisible();
  });
});

// ============================================================================
// VISUAL CONSISTENCY TESTS
// ============================================================================

test.describe("Visual Consistency", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(BASE_URL);
    await page.evaluate(() => localStorage.clear());
    
    const token = await loginApi(OWNER_EMAIL);
    await setAuthToken(page, token);
    
    await page.goto(`${BASE_URL}/command`);
    await page.waitForLoadState("networkidle");
  });

  test("uses glassmorphism styling", async ({ page }) => {
    // Should have backdrop-blur elements
    const glassElements = page.locator('[class*="backdrop-blur"]');
    await expect(glassElements.first()).toBeVisible({ timeout: 5000 });
  });

  test("uses consistent color palette", async ({ page }) => {
    // Should have emerald accents (consistent with PRANELY branding)
    const emeraldElements = page.locator('[class*="emerald"]');
    await expect(emeraldElements.first()).toBeVisible({ timeout: 5000 });
  });

  test("tab navigation is consistent", async ({ page }) => {
    // Tabs should use consistent glassmorphism style
    const tabs = page.locator('[class*="rounded-2xl"][class*="bg-white/5"]');
    await expect(tabs.first()).toBeVisible();
  });
});

// ============================================================================
// ERROR HANDLING TESTS
// ============================================================================

test.describe("Error Handling", () => {
  test("shows error state on API failure", async ({ page }) => {
    await page.goto(BASE_URL);
    await page.evaluate(() => localStorage.clear());
    
    // Set invalid token
    await page.evaluate(() => {
      localStorage.setItem("pranely_token", "invalid_token");
    });
    
    await page.goto(`${BASE_URL}/command`);
    await page.waitForLoadState("networkidle");
    
    // Should either redirect or show error
    const hasError = await page.locator("text=/Error|401|403").count() > 0;
    const isRedirected = page.url().includes("login");
    
    expect(hasError || isRedirected).toBeTruthy();
  });
});

// ============================================================================
// MOBILE RESPONSIVENESS TESTS
// ============================================================================

test.describe("Mobile Responsiveness", () => {
  test.use({ viewport: { width: 375, height: 667 } }); // iPhone SE

  test.beforeEach(async ({ page }) => {
    await page.goto(BASE_URL);
    await page.evaluate(() => localStorage.clear());
    
    const token = await loginApi(OWNER_EMAIL);
    await setAuthToken(page, token);
    
    await page.goto(`${BASE_URL}/command`);
    await page.waitForLoadState("networkidle");
  });

  test("command center is accessible on mobile", async ({ page }) => {
    // Should still render
    await expect(page.locator("h1:has-text('Command Center')")).toBeVisible({ timeout: 10000 });
  });

  test("tabs are scrollable on mobile", async ({ page }) => {
    // Should have horizontally scrollable tabs
    const tabsContainer = page.locator('[class*="overflow-x-auto"], [class*="flex gap-1"]');
    await expect(tabsContainer.first()).toBeVisible({ timeout: 5000 });
  });
});