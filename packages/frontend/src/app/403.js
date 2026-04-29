'use client';

import Link from 'next/link';
 
export default function Forbidden() {
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
        backgroundColor: '#fef3c7'
      }}>
        <h1 style={{ fontSize: '4rem', margin: '0 0 1rem', color: '#92400e' }}>403</h1>
        <h2 style={{ fontSize: '1.5rem', margin: '0 0 1rem', color: '#78350f' }}>
          Acceso denegado
        </h2>
        <p style={{ color: '#a16207', marginBottom: '2rem', textAlign: 'center' }}>
          No tienes permisos para acceder a esta página.
        </p>
        <div style={{ display: 'flex', gap: '1rem' }}>
          <button
            onClick={() => window.history.back()}
            style={{
              padding: '0.75rem 1.5rem',
              backgroundColor: '#d97706',
              color: 'white',
              border: 'none',
              borderRadius: '0.5rem',
              fontWeight: '500',
              cursor: 'pointer'
            }}
          >
            Volver atrás
          </button>
          <Link 
            href="/"
            style={{
              padding: '0.75rem 1.5rem',
              backgroundColor: '#92400e',
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
