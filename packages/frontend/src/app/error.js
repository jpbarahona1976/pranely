'use client';

import { useEffect } from 'react';
 
export default function Error({ error, reset }) {
  useEffect(() => {
    console.error('Application error:', error);
  }, [error]);
 
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
        backgroundColor: '#fef2f2'
      }}>
        <h1 style={{ fontSize: '3rem', margin: '0 0 1rem', color: '#dc2626' }}>Error</h1>
        <h2 style={{ fontSize: '1.25rem', margin: '0 0 1rem', color: '#7f1d1d' }}>
          Algo salió mal
        </h2>
        <p style={{ color: '#991b1b', marginBottom: '2rem', textAlign: 'center', maxWidth: '400px' }}>
          {error?.message || 'Ha ocurrido un error inesperado. Por favor intenta de nuevo.'}
        </p>
        <div style={{ display: 'flex', gap: '1rem' }}>
          <button
            onClick={reset}
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
            Reintentar
          </button>
          <a 
            href="/"
            style={{
              padding: '0.75rem 1.5rem',
              backgroundColor: '#64748b',
              color: 'white',
              borderRadius: '0.5rem',
              textDecoration: 'none',
              fontWeight: '500'
            }}
          >
            Ir al inicio
          </a>
        </div>
      </body>
    </html>
  );
}
