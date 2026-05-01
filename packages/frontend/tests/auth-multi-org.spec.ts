/** E2E tests for multi-org login flow (FIX 2). */
import { test, expect } from "@playwright/test";

const API_URL = "http://localhost:8000";

test.describe("Multi-org Login Flow", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/login");
  });

  test("single-org user: login succeeds and redirects to dashboard", async ({ page }) => {
    await page.route(`${API_URL}/api/auth/login`, (route) => {
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          token: { access_token: "test-token-single", token_type: "bearer" },
          user: { id: 1, email: "single@test.com", full_name: "Single User" },
          organization: { id: 1, name: "Test Org" },
        }),
      });
    });

    await page.fill('input[name="email"]', "single@test.com");
    await page.fill('input[name="password"]', "password123");
    await page.click('button[type="submit"]');

    await expect(page).toHaveURL("/dashboard", { timeout: 5000 });
  });

  test("multi-org user: shows org selector after credentials", async ({ page }) => {
    await page.route(`${API_URL}/api/auth/login`, (route) => {
      const url = new URL(route.request().url());
      const orgIdParam = url.searchParams.get("org_id");

      if (orgIdParam) {
        // Login with org_id
        route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            token: { access_token: "test-token-org2", token_type: "bearer" },
            user: { id: 1, email: "multi@test.com", full_name: "Multi User" },
            organization: { id: 2, name: "Beta Inc" },
          }),
        });
      } else {
        // First request: return available orgs list
        route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            token: null,
            user: { id: 1, email: "multi@test.com" },
            available_orgs: [
              { org_id: 1, org_name: "Acme Corp", role: "owner" },
              { org_id: 2, org_name: "Beta Inc", role: "member" },
            ],
            message: "Multiple organizations found",
          }),
        });
      }
    });

    await page.fill('input[name="email"]', "multi@test.com");
    await page.fill('input[name="password"]', "password123");
    await page.click('button[type="submit"]');

    // Should show org selector
    await expect(page.locator("text=Selecciona Organizacion")).toBeVisible({ timeout: 3000 });
    await expect(page.locator("text=Acme Corp")).toBeVisible();
    await expect(page.locator("text=Beta Inc")).toBeVisible();
  });

  test("org selection: click selects org and redirects to dashboard", async ({ page }) => {
    let requestCount = 0;
    await page.route(`${API_URL}/api/auth/login`, async (route) => {
      const url = new URL(route.request().url());
      const orgIdParam = url.searchParams.get("org_id");

      requestCount++;

      if (requestCount === 1) {
        // First request: return available orgs
        route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            token: null,
            user: { id: 1, email: "multi@test.com" },
            available_orgs: [{ org_id: 2, org_name: "Beta Inc", role: "member" }],
          }),
        });
      } else {
        // Second request: login with org_id=2
        expect(orgIdParam).toBe("2");
        route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            token: { access_token: "token-for-org2", token_type: "bearer" },
            user: { id: 1, email: "multi@test.com" },
            organization: { id: 2, name: "Beta Inc" },
          }),
        });
      }
    });

    await page.fill('input[name="email"]', "multi@test.com");
    await page.fill('input[name="password"]', "password123");
    await page.click('button[type="submit"]');

    // Wait for org selector
    await expect(page.locator("text=Selecciona Organizacion")).toBeVisible({ timeout: 3000 });
    // Click the org
    await page.locator("button:has-text('Beta Inc')").click();

    await expect(page).toHaveURL("/dashboard", { timeout: 5000 });
  });

  test("back button returns to credentials form", async ({ page }) => {
    await page.route(`${API_URL}/api/auth/login`, (route) => {
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          token: null,
          user: { id: 1, email: "multi@test.com" },
          available_orgs: [{ org_id: 1, org_name: "Org One", role: "owner" }],
        }),
      });
    });

    await page.fill('input[name="email"]', "multi@test.com");
    await page.fill('input[name="password"]', "password123");
    await page.click('button[type="submit"]');

    await expect(page.locator("text=Selecciona Organizacion")).toBeVisible({ timeout: 3000 });
    await page.click("text=Volver al inicio de sesion");

    await expect(page.locator('input[name="email"]')).toBeVisible();
    await expect(page.locator('input[name="password"]')).toBeVisible();
  });
});
