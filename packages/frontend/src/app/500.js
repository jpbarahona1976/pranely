'use client';

import Link from 'next/link';
 
export default function ServerError() {
  return (
    <html lang="es">
      <body style={{ 
        display: 'flex', 
        flexDirection: 'column', 
        alignItems: 'center', 
        justifyContent: 'center', 
        minHeight: '100vh',
        fontFamily: 'system-ui, sans-serif',
        margin: 0,
        padding: '2rem',
        backgroundColor: '#fee2e2'
      }}>
        <h1 style={{ fontSize: '4rem', margin: '0 0 1rem', color: '#b91c1c' }}>500</h1>
        <h2 style={{ fontSize: '1.5rem', margin: '0 0 1rem', color: '#991b1b' }}>
          Error del servidor
        </h2>
        <p style={{ color: '#7f1d1d', marginBottom: '2rem', textAlign: 'center' }}>
          Estamos experimentando problemas técnicos. Por favor intenta más tarde.
        </p>
        <div style={{ display: 'flex', gap: '1rem' }}>
          <button
            onClick={() => window.location.reload()}
            style={{
              padding: '0.75rem 1.5rem',
              backgroundColor: '#dc2626',
              color: 'white',
              border: 'none',
              borderRadius: '0.5rem',
              fontWeight: '500',
              cursor: 'pointer'
            }}
          >
            Recargar página
          </button>
          <Link 
            href="/"
            style={{
              padding: '0.75rem 1.5rem',
              backgroundColor: '#b91c1c',
              color: 'white',
              borderRadius: '0.5rem',
              textDecoration: 'none',
              fontWeight: '500'
            }}
          >
            Ir al inicio
          </Link>
        </div>
      </body>
    </html>
  );
}
