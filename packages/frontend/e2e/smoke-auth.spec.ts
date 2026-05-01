/**
 * PRANELY - Auth Smoke Tests (Playwright)
 * 5 E2E smoke tests para validar flujo de autenticación
 * 
 * SECURITY: All test credentials MUST be provided via environment variables:
 * - E2E_API_URL: API base URL
 * - E2E_TEST_PASSWORD: Test user password
 * - E2E_ALT_PASSWORD: Alternative test password  
 * - E2E_WRONG_PASSWORD: Wrong password for negative tests
 */
import { test, expect } from '@playwright/test';

const API_URL = process.env.E2E_API_URL || 'http://localhost:8000';

// Credentials MUST be provided via env vars - no hardcoded fallbacks
const TEST_PASSWORD = process.env.E2E_TEST_PASSWORD;
const ALT_PASSWORD = process.env.E2E_ALT_PASSWORD;
const WRONG_PASSWORD = process.env.E2E_WRONG_PASSWORD;

test.describe('Auth Smoke Tests', () => {
  
  test.describe.configure({ mode: 'serial' });

  /**
   * Smoke Test 1: Registro de usuario nuevo
   */
  test('1. Registro exitoso crea usuario y organización', async ({ request }) => {
    const timestamp = Date.now();
    const testUser = {
      email: `smoke_test_${timestamp}@example.com`,
      password: TEST_PASSWORD,
      full_name: 'Smoke Test User',
      organization_name: `Smoke Test Org ${timestamp}`,
    };

    const response = await request.post(`${API_URL}/api/auth/register`, {
      headers: { 'Content-Type': 'application/json' },
      data: JSON.stringify(testUser),
    });

    expect(response.status()).toBe(201);
    const data = await response.json();
    expect(data.user.email).toBe(testUser.email);
    expect(data.organization.name).toBe(testUser.organization_name);
    expect(data.user).not.toHaveProperty('hashed_password');
  });

  /**
   * Smoke Test 2: Login con credenciales válidas
   */
  test('2. Login con credenciales válidas retorna JWT', async ({ request }) => {
    const timestamp = Date.now();
    const testUser = {
      email: `login_test_${timestamp}@example.com`,
      password: TEST_PASSWORD,
      full_name: 'Login Test User',
      organization_name: `Login Test Org ${timestamp}`,
    };

    // registrar
    await request.post(`${API_URL}/api/auth/register`, {
      headers: { 'Content-Type': 'application/json' },
      data: JSON.stringify(testUser),
    });

    // Login
    const response = await request.post(`${API_URL}/api/auth/login`, {
      headers: { 'Content-Type': 'application/json' },
      data: JSON.stringify({
        email: testUser.email,
        password: testUser.password,
      }),
    });

    expect(response.status()).toBe(200);
    const data = await response.json();
    expect(data.token.access_token).toBeDefined();
    expect(data.token.token_type).toBe('bearer');
    expect(data.token.expires_in).toBe(86400);
    expect(data.user.email).toBe(testUser.email);
  });

  /**
   * Smoke Test 3: Login falla con contraseña incorrecta
   */
  test('3. Login con contraseña incorrecta retorna 401', async ({ request }) => {
    const response = await request.post(`${API_URL}/api/auth/login`, {
      headers: { 'Content-Type': 'application/json' },
      data: JSON.stringify({
        email: 'nonexistent_user_pranely@example.com',
        password: WRONG_PASSWORD,
      }),
    });

    expect(response.status()).toBe(401);
    const data = await response.json();
    expect(data.detail.detail).toContain('Invalid credentials');
  });

  /**
   * Smoke Test 4: Registro falla con email duplicado
   */
  test('4. Registro con email duplicado retorna 400', async ({ request }) => {
    const timestamp = Date.now();
    const testEmail = `duplicate_test_${timestamp}@example.com`;
    
    // Primer registro
    await request.post(`${API_URL}/api/auth/register`, {
      headers: { 'Content-Type': 'application/json' },
      data: JSON.stringify({
        email: testEmail,
        password: TEST_PASSWORD,
        full_name: 'First User',
        organization_name: `First Org ${timestamp}`,
      }),
    });

    // Segundo registro con mismo email
    const response = await request.post(`${API_URL}/api/auth/register`, {
      headers: { 'Content-Type': 'application/json' },
      data: JSON.stringify({
        email: testEmail,
        password: ALT_PASSWORD,
        full_name: 'Second User',
        organization_name: `Second Org ${timestamp}`,
      }),
    });

    expect(response.status()).toBe(400);
    const data = await response.json();
    expect(data.detail.detail).toContain('already registered');
  });

  /**
   * Smoke Test 5: Validación de esquema rechazar datos inválidos
   */
  test('5. Registro con email inválido retorna 422', async ({ request }) => {
    const response = await request.post(`${API_URL}/api/auth/register`, {
      headers: { 'Content-Type': 'application/json' },
      data: JSON.stringify({
        email: 'not-a-valid-email',
        password: TEST_PASSWORD,
        full_name: 'Test User',
        organization_name: 'Test Org',
      }),
    });

    expect(response.status()).toBe(422);
  });

});
