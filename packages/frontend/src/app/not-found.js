'use client';

import Link from 'next/link';
 
export default function NotFound() {
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
        backgroundColor: '#f8fafc'
      }}>
        <h1 style={{ fontSize: '4rem', margin: '0 0 1rem', color: '#1e293b' }}>404</h1>
        <h2 style={{ fontSize: '1.5rem', margin: '0 0 1rem', color: '#475569' }}>
          Página no encontrada
        </h2>
        <p style={{ color: '#64748b', marginBottom: '2rem' }}>
          La página que buscas no existe o fue movida.
        </p>
        <Link 
          href="/"
          style={{
            padding: '0.75rem 1.5rem',
            backgroundColor: '#2563eb',
            color: 'white',
            borderRadius: '0.5rem',
            textDecoration: 'none',
            fontWeight: '500'
          }}
        >
          Volver al inicio
        </Link>
      </body>
    </html>
  );
}
