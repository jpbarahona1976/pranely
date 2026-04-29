/**
 * PRANELY - Auth Smoke Tests (Playwright)
 * 5 E2E smoke tests para validar flujo de autenticación
 */
import { test, expect } from '@playwright/test';

const API_URL = process.env.E2E_API_URL || 'http://localhost:8000';

test.describe('Auth Smoke Tests', () => {
  
  test.describe.configure({ mode: 'serial' });

  /**
   * Smoke Test 1: Registro de usuario nuevo
   */
  test('1. Registro exitoso crea usuario y organización', async ({ request }) => {
    const timestamp = Date.now();
    const testUser = {
      email: `smoke_test_${timestamp}@example.com`,
      password: 'SecurePass123!',
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
      password: 'SecurePass123!',
      full_name: 'Login Test User',
      organization_name: `Login Test Org ${timestamp}`,
    };

    // Registrar
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
        password: 'WrongPassword123!',
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
        password: 'SecurePass123!',
        full_name: 'First User',
        organization_name: `First Org ${timestamp}`,
      }),
    });

    // Segundo registro con mismo email
    const response = await request.post(`${API_URL}/api/auth/register`, {
      headers: { 'Content-Type': 'application/json' },
      data: JSON.stringify({
        email: testEmail,
        password: 'AnotherPass456!',
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
        password: 'SecurePass123!',
        full_name: 'Test User',
        organization_name: 'Test Org',
      }),
    });

    expect(response.status()).toBe(422);
  });

});
