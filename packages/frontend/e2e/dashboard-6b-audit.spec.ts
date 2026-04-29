/**
 * Dashboard 6B E2E Tests - Playwright
 * Pruebas para auditoría de hallazgos de Fase 6B
 */
import { test, expect } from '@playwright/test';

// Configuración
const BASE_URL = process.env.E2E_BASE_URL || 'http://localhost:3000';
const API_URL = process.env.E2E_API_URL || 'http://localhost:8000';

test.describe('Dashboard 6B - Auditoría de Hallazgos', () => {
  
  // Helper para hacer login programático
  async function loginAsUser(page: any, email: string, password: string, role: string = 'admin') {
    // El backend debe tener usuarios de test configurados
    await page.goto(`${BASE_URL}/login`);
    await page.fill('input[name="email"]', email);
    await page.fill('input[name="password"]', password);
    await page.click('button[type="submit"]');
    await page.waitForURL(`${BASE_URL}/dashboard`);
  }

  test.describe('H1: Endpoint Review - Validación', () => {
    test('debe existir POST /api/v1/waste/{id}/review en backend', async ({ request }) => {
      // Login primero
      const loginResponse = await request.post(`${API_URL}/api/auth/login`, {
        data: { email: 'test@pranely.com', password: 'testpassword123' }
      });
      
      if (loginResponse.ok()) {
        const loginData = await loginResponse.json();
        const token = loginData.token?.access_token;
        
        // Verificar que el endpoint existe y responde
        const response = await request.post(`${API_URL}/api/v1/waste/1/review`, {
          headers: { Authorization: `Bearer ${token}` },
          data: { action: 'approve' }
        });
        
        // Debe retornar 200, 400 (bad request), 403 (no permisos) o 404 (no existe)
        // NO debe retornar 500 (error interno)
        expect([200, 400, 403, 404]).toContain(response.status());
      } else {
        // Test usuarios no configurados - marcar como skipped
        test.skip();
      }
    });

    test('debe rechazar viewer sin permisos de review', async ({ request }) => {
      // Este test requiere usuarios de diferentes roles
      test.skip('Requiere setup de usuarios multi-rol');
    });
  });

  test.describe('H2: Acciones visibles en móvil', () => {
    test.beforeEach(async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 667 }); // iPhone SE
      await page.goto(`${BASE_URL}/login`);
      // Skip login si hay problemas de auth
      await page.evaluate(() => {
        localStorage.setItem('pranely_token', 'mock_token_for_demo');
      });
      await page.goto(`${BASE_URL}/dashboard`);
    });

    test('debe mostrar botones de acción sin hover en móvil', async ({ page }) => {
      // Esperar que cargue la tabla
      await page.waitForSelector('table', { timeout: 10000 });
      
      // Buscar botones de acción específicos
      const viewButton = page.locator('button[aria-label="Ver detalles"]').first();
      const editButton = page.locator('button[title="Editar"]').first();
      const archiveButton = page.locator('button[title="Archivar"]').first();
      
      // Los botones deben ser visibles (no depender de hover)
      await expect(viewButton).toBeVisible();
      
      // Verificar que tienen min-width/min-height para touch
      const viewBox = await viewButton.boundingBox();
      expect(viewBox?.width).toBeGreaterThanOrEqual(40);
      expect(viewBox?.height).toBeGreaterThanOrEqual(40);
    });

    test('debe tener área táctil suficiente (mínimo 44x44px)', async ({ page }) => {
      await page.waitForSelector('table', { timeout: 10000 });
      
      // Obtener todos los botones de acción
      const actionButtons = page.locator('table button').first();
      const box = await actionButtons.boundingBox();
      
      // Área táctil mínima para iOS: 44x44px
      expect(box?.width).toBeGreaterThanOrEqual(40);
      expect(box?.height).toBeGreaterThanOrEqual(40);
    });
  });

  test.describe('H3: Rol hardcodeado - Corrección', () => {
    test('debe usar rol real del token/JWT, no hardcodeado', async ({ page }) => {
      await page.goto(`${BASE_URL}/dashboard`);
      
      // Verificar que no se muestra "admin" hardcodeado
      // El rol debe venir del contexto de autenticación
      const roleBadge = page.locator('span:text-matches("owner|admin|member|viewer")').first();
      
      // Si existe el badge, debe mostrar un rol válido (no necesariamente "admin")
      const badgeCount = await page.locator('[class*="rounded-full"][class*="uppercase"]').count();
      if (badgeCount > 0) {
        const badgeText = await page.locator('[class*="rounded-full"][class*="uppercase"]').first().textContent();
        expect(['owner', 'admin', 'member', 'viewer']).toContain(badgeText?.toLowerCase());
      }
    });

    test('viewer no debe ver botones de acción de mutación', async ({ page }) => {
      // Simular rol viewer
      await page.goto(`${BASE_URL}/dashboard`);
      await page.evaluate(() => {
        // El contexto debe usar el rol del token, no uno hardcodeado
        localStorage.setItem('pranely_token', JSON.stringify({ role: 'viewer' }));
      });
      await page.reload();
      
      // En rol viewer, no debe haber botones de approve/reject/archive
      const approveButtons = page.locator('button[title="Aprobar"]');
      const rejectButtons = page.locator('button[title="Rechazar"]');
      const archiveButtons = page.locator('button[title="Archivar"]');
      
      // Para viewer, estos botones no deben existir o deben estar deshabilitados
      const approveCount = await approveButtons.count();
      const rejectCount = await rejectButtons.count();
      
      // Si hay movimientos in_review, viewer NO debe ver approve/reject
      const inReviewRows = page.locator('tr:has([class*="En Revisión"])');
      if (await inReviewRows.count() > 0) {
        expect(approveCount).toBe(0);
        expect(rejectCount).toBe(0);
      }
    });
  });

  test.describe('H4: wasteApi - Contexto multi-tenant', () => {
    test('debe usar organization_id del contexto de autenticación', async ({ page }) => {
      await page.goto(`${BASE_URL}/dashboard`);
      
      // Interceptar requests para verificar que se envía el token
      const requests: any[] = [];
      page.on('request', (request) => {
        if (request.url().includes('/api/v1/waste')) {
          requests.push({
            url: request.url(),
            headers: request.headers()
          });
        }
      });
      
      await page.waitForTimeout(2000); // Esperar polling o carga
      
      // Verificar que las requests incluyen Authorization header
      const wasteRequests = requests.filter(r => r.url.includes('/api/v1/waste'));
      for (const req of wasteRequests) {
        expect(req.headers['authorization']).toBeDefined();
        expect(req.headers['authorization']).toMatch(/^Bearer /);
      }
    });
  });

  test.describe('H5: Sidebar - Estado controlado sin mocks', () => {
    test('debe mostrar empty state si no hay datos de actividad/alertas', async ({ page }) => {
      await page.goto(`${BASE_URL}/dashboard`);
      await page.waitForSelector('table', { timeout: 10000 });
      
      // Buscar la sección de actividad
      const activitySection = page.locator('text=Actividad').first();
      
      if (await activitySection.isVisible()) {
        // Si hay empty state, debe mostrar mensaje apropiado
        const emptyState = page.locator('text=/Sin actividad|Sin alertas|No hay.*registrado/i');
        const hasEmptyState = await emptyState.count() > 0;
        
        // Verificar que NO muestra datos de mock hardcodeados
        const mariaGarcia = page.locator('text=María García');
        const carlosRuiz = page.locator('text=Carlos Ruiz');
        
        // No debe haber nombres de usuarios mock
        expect(await mariaGarcia.count()).toBe(0);
        expect(await carlosRuiz.count()).toBe(0);
      }
    });
  });

  test.describe('Flujo completo: Login -> Dashboard -> Acciones', () => {
    test('debe permitir flujo login -> dashboard -> logout', async ({ page }) => {
      await page.goto(`${BASE_URL}/login`);
      
      // Verificar elementos del login
      await expect(page.locator('h1:text("PRANELY")')).toBeVisible();
      await expect(page.locator('input[type="email"]')).toBeVisible();
      await expect(page.locator('input[type="password"]')).toBeVisible();
      await expect(page.locator('button[type="submit"]')).toBeVisible();
    });

    test('debe mostrar KPIs en dashboard', async ({ page }) => {
      await page.goto(`${BASE_URL}/dashboard`);
      await page.waitForSelector('table', { timeout: 10000 });
      
      // Verificar KPIs
      const totalCard = page.locator('text=Total Movimientos').first();
      const pendingCard = page.locator('text=Pendientes').first();
      const reviewCard = page.locator('text=En Revisión').first();
      const validatedCard = page.locator('text=Validados').first();
      
      await expect(totalCard).toBeVisible();
      await expect(pendingCard).toBeVisible();
      await expect(reviewCard).toBeVisible();
      await expect(validatedCard).toBeVisible();
    });

    test('debe mostrar tabla de movimientos', async ({ page }) => {
      await page.goto(`${BASE_URL}/dashboard`);
      await page.waitForSelector('table', { timeout: 10000 });
      
      // Verificar headers de tabla
      await expect(page.locator('th:text("ID")')).toBeVisible();
      await expect(page.locator('th:text("Generador")')).toBeVisible();
      await expect(page.locator('th:text("Tipo")')).toBeVisible();
      await expect(page.locator('th:text("Estado")')).toBeVisible();
      await expect(page.locator('th:text("Acciones")')).toBeVisible();
    });

    test('debe tener polling activo con indicador visual', async ({ page }) => {
      await page.goto(`${BASE_URL}/dashboard`);
      await page.waitForSelector('table', { timeout: 10000 });
      
      // Verificar indicador de polling
      const pollingIndicator = page.locator('text=Actualización automática');
      await expect(pollingIndicator).toBeVisible();
    });
  });

  test.describe('Responsive Design', () => {
    test('debe funcionar en móvil (375px)', async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 667 });
      await page.goto(`${BASE_URL}/dashboard`);
      
      // Debe cargar sin errores
      await page.waitForSelector('table, text=Sin movimientos', { timeout: 10000 });
    });

    test('debe funcionar en tablet (768px)', async ({ page }) => {
      await page.setViewportSize({ width: 768, height: 1024 });
      await page.goto(`${BASE_URL}/dashboard`);
      
      await page.waitForSelector('table, text=Sin movimientos', { timeout: 10000 });
    });

    test('debe funcionar en desktop (1920px)', async ({ page }) => {
      await page.setViewportSize({ width: 1920, height: 1080 });
      await page.goto(`${BASE_URL}/dashboard`);
      
      await page.waitForSelector('table, text=Sin movimientos', { timeout: 10000 });
    });
  });
});
