"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

const TOKEN_KEY = "pranely_token";

export default function LandingContent() {
  const router = useRouter();
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    // Client-side check for auth token
    const token = localStorage.getItem(TOKEN_KEY);
    setIsAuthenticated(!!token);
    setMounted(true);
  }, []);

  const handleDashboardClick = () => {
    router.push("/dashboard");
  };

  // Avoid hydration mismatch - show nothing until mounted
  if (!mounted) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-400 via-teal-500 to-emerald-600 flex items-center justify-center">
          <span className="text-white font-black text-lg">P</span>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen relative overflow-hidden">
      {/* Background - Same system as login/dashboard */}
      <div className="fixed inset-0 -z-10">
        <div className="absolute inset-0 bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900" />
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-emerald-500/20 rounded-full blur-3xl animate-pulse" />
        <div className="absolute top-1/3 right-1/4 w-80 h-80 bg-violet-500/15 rounded-full blur-3xl animate-pulse" style={{ animationDelay: '1s' }} />
        <div className="absolute bottom-1/4 left-1/3 w-72 h-72 bg-blue-500/15 rounded-full blur-3xl animate-pulse" style={{ animationDelay: '2s' }} />
        <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHZpZXdCb3g9IjAgMCA2MCA2MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48ZyBmaWxsPSJub25lIiBmaWxsLXJ1bGU9ImV2ZW5vZGQiPjxnIGZpbGw9IiNmZmZmZmYiIGZpbGwtb3BhY2l0eT0iMC4wMyI+PGNpcmNsZSBjeD0iMzAiIGN5PSIzMCIgcj0iMS41Ii8+PC9nPjwvZz48L3N2Zz4=')] opacity-30" />
      </div>

      {/* Header */}
      <header className="relative z-50">
        <div className="max-w-7xl mx-auto px-6 py-5">
          <nav className="flex justify-between items-center">
            {/* Logo */}
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-400 via-teal-500 to-emerald-600 flex items-center justify-center shadow-lg shadow-emerald-500/30">
                <span className="text-white font-black text-lg">P</span>
              </div>
              <span className="text-xl font-bold text-white tracking-tight">PRANELY</span>
            </div>

            {/* Nav Links */}
            <div className="hidden md:flex items-center gap-8">
              <a href="#problema" className="text-sm text-white/60 hover:text-white/80 transition-colors">El problema</a>
              <a href="#beneficios" className="text-sm text-white/60 hover:text-white/80 transition-colors">Beneficios</a>
              <a href="#audiencia" className="text-sm text-white/60 hover:text-white/80 transition-colors">Para quién</a>
              <a href="#resultados" className="text-sm text-white/60 hover:text-white/80 transition-colors">Resultados</a>
            </div>

            {/* Actions */}
            <div className="flex items-center gap-3">
              {isAuthenticated ? (
                <>
                  <button
                    onClick={handleDashboardClick}
                    className="px-5 py-2.5 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 backdrop-blur-md text-white/80 text-sm font-medium transition-all"
                  >
                    Ir al dashboard
                  </button>
                  <Link
                    href="/dashboard"
                    className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-500 text-white text-sm font-semibold shadow-lg shadow-emerald-500/30 hover:shadow-emerald-500/50 transition-all"
                  >
                    Dashboard
                  </Link>
                </>
              ) : (
                <>
                  <Link
                    href="/login"
                    className="px-5 py-2.5 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 backdrop-blur-md text-white/80 text-sm font-medium transition-all"
                  >
                    Iniciar sesión
                  </Link>
                  <Link
                    href="/register"
                    className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-500 text-white text-sm font-semibold shadow-lg shadow-emerald-500/30 hover:shadow-emerald-500/50 transition-all"
                  >
                    Crear cuenta
                  </Link>
                </>
              )}
            </div>
          </nav>
        </div>
      </header>

      {/* Hero Section */}
      <section className="relative pt-16 pb-24 md:pt-24 md:pb-32">
        <div className="max-w-7xl mx-auto px-6">
          <div className="max-w-4xl mx-auto text-center">
            {/* Badge */}
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white/5 border border-white/10 backdrop-blur-md mb-8">
              <div className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse" />
              <span className="text-xs text-white/60 font-medium">Gestión documental para residuos industriales</span>
            </div>

            {/* Title */}
            <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold text-white tracking-tight leading-tight mb-6">
              Control total sobre la{" "}
              <span className="bg-gradient-to-r from-emerald-400 to-teal-400 bg-clip-text text-transparent">
                gestión de residuos
              </span>{" "}
              industriales.
            </h1>

            {/* Subtitle */}
            <p className="text-lg md:text-xl text-white/60 leading-relaxed max-w-3xl mx-auto mb-4">
              PRANELY centraliza trazabilidad, cumplimiento y operación diaria en una plataforma diseñada para equipos que necesitan visibilidad real, evidencia confiable y ejecución sin fricción.
            </p>

            {/* Microcopy */}
            <p className="text-sm text-white/40 mb-10">
              Menos seguimiento manual. Más control operativo. Más confianza ante auditorías.
            </p>

            {/* CTAs */}
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <button className="w-full sm:w-auto px-8 py-4 rounded-2xl bg-gradient-to-r from-emerald-500 to-teal-500 text-white font-semibold shadow-lg shadow-emerald-500/30 hover:shadow-emerald-500/50 transition-all">
                Solicitar demostración
              </button>
              <Link
                href="/login"
                className="w-full sm:w-auto px-8 py-4 rounded-2xl bg-white/5 hover:bg-white/10 border border-white/10 backdrop-blur-md text-white/80 font-medium transition-all"
              >
                Explorar plataforma
              </Link>
            </div>

            {/* Dashboard preview indicator */}
            <div className="mt-16 flex items-center justify-center gap-6 text-white/30 text-sm">
              <div className="flex items-center gap-2">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span>Trazabilidad completa</span>
              </div>
              <div className="flex items-center gap-2">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span>Cumplimiento normativo</span>
              </div>
              <div className="flex items-center gap-2">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span>Evidencia verificable</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Problem Section */}
      <section id="problema" className="relative py-20 md:py-28">
        <div className="max-w-7xl mx-auto px-6">
          <div className="max-w-3xl mx-auto">
            {/* Section Header */}
            <div className="mb-12">
              <span className="text-xs font-semibold text-emerald-400 uppercase tracking-wider">El problema</span>
              <h2 className="mt-3 text-3xl md:text-4xl font-bold text-white tracking-tight">
                El problema no es generar datos. Es poder confiar en ellos.
              </h2>
            </div>

            {/* Content Card */}
            <div className="relative rounded-3xl bg-white/5 backdrop-blur-xl border border-white/10 p-8 md:p-10">
              {/* Glow accent */}
              <div className="absolute -top-24 -right-24 w-48 h-48 bg-rose-500/10 rounded-full blur-3xl" />
              
              <p className="text-lg text-white/70 leading-relaxed">
                Cuando la operación depende de hojas de cálculo, mensajes dispersos y validaciones manuales, cada desvío cuesta tiempo, coordinación y capacidad de respuesta.
              </p>
              <p className="text-lg text-white/70 leading-relaxed mt-4">
                PRANELY convierte procesos fragmentados en un flujo visible, trazable y verificable de principio a fin.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Benefits Section */}
      <section id="beneficios" className="relative py-20 md:py-28">
        <div className="max-w-7xl mx-auto px-6">
          {/* Section Header */}
          <div className="mb-16 text-center">
            <span className="text-xs font-semibold text-emerald-400 uppercase tracking-wider">Beneficios</span>
            <h2 className="mt-3 text-3xl md:text-4xl font-bold text-white tracking-tight">
              Una plataforma creada para operar con rigor.
            </h2>
          </div>

          {/* Benefits Grid */}
          <div className="grid md:grid-cols-2 gap-6 max-w-5xl mx-auto">
            {/* Benefit 1 */}
            <div className="group relative rounded-3xl bg-gradient-to-br from-emerald-500/20 to-teal-500/10 backdrop-blur-xl border border-emerald-500/20 p-8 transition-all hover:border-emerald-500/40 hover:shadow-xl hover:shadow-emerald-500/10">
              <div className="w-12 h-12 rounded-2xl bg-emerald-500/20 flex items-center justify-center mb-6">
                <svg className="w-6 h-6 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
                </svg>
              </div>
              <h3 className="text-xl font-semibold text-white mb-3">Trazabilidad integral</h3>
              <p className="text-white/60 leading-relaxed">
                Registra eventos, responsables y estado de cada residuo en un historial auditable.
              </p>
            </div>

            {/* Benefit 2 */}
            <div className="group relative rounded-3xl bg-gradient-to-br from-blue-500/20 to-indigo-500/10 backdrop-blur-xl border border-blue-500/20 p-8 transition-all hover:border-blue-500/40 hover:shadow-xl hover:shadow-blue-500/10">
              <div className="w-12 h-12 rounded-2xl bg-blue-500/20 flex items-center justify-center mb-6">
                <svg className="w-6 h-6 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                </svg>
              </div>
              <h3 className="text-xl font-semibold text-white mb-3">Cumplimiento más claro</h3>
              <p className="text-white/60 leading-relaxed">
                Organiza la evidencia y los puntos de control en un sistema consistente y revisable.
              </p>
            </div>

            {/* Benefit 3 */}
            <div className="group relative rounded-3xl bg-gradient-to-br from-violet-500/20 to-purple-500/10 backdrop-blur-xl border border-violet-500/20 p-8 transition-all hover:border-violet-500/40 hover:shadow-xl hover:shadow-violet-500/10">
              <div className="w-12 h-12 rounded-2xl bg-violet-500/20 flex items-center justify-center mb-6">
                <svg className="w-6 h-6 text-violet-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                </svg>
              </div>
              <h3 className="text-xl font-semibold text-white mb-3">Coordinación multi-actor</h3>
              <p className="text-white/60 leading-relaxed">
                Conecta empresa, transportista y responsables internos sin depender de seguimiento informal.
              </p>
            </div>

            {/* Benefit 4 */}
            <div className="group relative rounded-3xl bg-gradient-to-br from-amber-500/20 to-orange-500/10 backdrop-blur-xl border border-amber-500/20 p-8 transition-all hover:border-amber-500/40 hover:shadow-xl hover:shadow-amber-500/10">
              <div className="w-12 h-12 rounded-2xl bg-amber-500/20 flex items-center justify-center mb-6">
                <svg className="w-6 h-6 text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
              </div>
              <h3 className="text-xl font-semibold text-white mb-3">Visibilidad ejecutiva</h3>
              <p className="text-white/60 leading-relaxed">
                Transforma la operación diaria en información útil para decidir más rápido y con menos incertidumbre.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Audience Section */}
      <section id="audiencia" className="relative py-20 md:py-28">
        <div className="max-w-7xl mx-auto px-6">
          <div className="max-w-3xl mx-auto">
            {/* Section Header */}
            <div className="mb-12">
              <span className="text-xs font-semibold text-emerald-400 uppercase tracking-wider">Para quién</span>
              <h2 className="mt-3 text-3xl md:text-4xl font-bold text-white tracking-tight">
                Pensado para equipos que no pueden improvisar.
              </h2>
            </div>

            {/* Content Card */}
            <div className="relative rounded-3xl bg-white/5 backdrop-blur-xl border border-white/10 p-8 md:p-10">
              <p className="text-lg text-white/70 leading-relaxed">
                PRANELY ayuda a organizaciones industriales, operadores ambientales y áreas de cumplimiento a trabajar con mayor orden, menos ambigüedad y mejor capacidad de respuesta.
              </p>
              <p className="text-lg text-white/70 leading-relaxed mt-4">
                Cuando intervienen múltiples sedes, terceros y obligaciones normativas, la plataforma reduce fricción sin perder control.
              </p>
            </div>

            {/* Target indicators */}
            <div className="mt-10 grid grid-cols-3 gap-4">
              <div className="text-center p-4 rounded-2xl bg-white/5 border border-white/10">
                <p className="text-2xl font-bold text-white mb-1">🏭</p>
                <p className="text-xs text-white/50">Industrias</p>
              </div>
              <div className="text-center p-4 rounded-2xl bg-white/5 border border-white/10">
                <p className="text-2xl font-bold text-white mb-1">🌿</p>
                <p className="text-xs text-white/50">Operadores ambientales</p>
              </div>
              <div className="text-center p-4 rounded-2xl bg-white/5 border border-white/10">
                <p className="text-2xl font-bold text-white mb-1">📋</p>
                <p className="text-xs text-white/50">Cumplimiento</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Results Section */}
      <section id="resultados" className="relative py-20 md:py-28">
        <div className="max-w-7xl mx-auto px-6">
          <div className="max-w-3xl mx-auto text-center">
            {/* Section Header */}
            <span className="text-xs font-semibold text-emerald-400 uppercase tracking-wider">Resultados</span>
            <h2 className="mt-3 text-3xl md:text-4xl font-bold text-white tracking-tight mb-12">
              Lo que cambia cuando todo está conectado.
            </h2>

            {/* Results Grid */}
            <div className="grid sm:grid-cols-2 gap-6">
              <div className="flex items-start gap-4 p-6 rounded-2xl bg-white/5 border border-white/10 text-left">
                <div className="w-10 h-10 rounded-xl bg-emerald-500/20 flex items-center justify-center flex-shrink-0">
                  <svg className="w-5 h-5 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                </div>
                <div>
                  <p className="font-medium text-white">Menos retrabajo administrativo</p>
                  <p className="text-sm text-white/50 mt-1">Procesos estandarizados, menos errores manuales</p>
                </div>
              </div>

              <div className="flex items-start gap-4 p-6 rounded-2xl bg-white/5 border border-white/10 text-left">
                <div className="w-10 h-10 rounded-xl bg-blue-500/20 flex items-center justify-center flex-shrink-0">
                  <svg className="w-5 h-5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                </div>
                <div>
                  <p className="font-medium text-white">Más claridad sobre responsables</p>
                  <p className="text-sm text-white/50 mt-1">Cada actor conoce su rol y estado</p>
                </div>
              </div>

              <div className="flex items-start gap-4 p-6 rounded-2xl bg-white/5 border border-white/10 text-left">
                <div className="w-10 h-10 rounded-xl bg-violet-500/20 flex items-center justify-center flex-shrink-0">
                  <svg className="w-5 h-5 text-violet-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                </div>
                <div>
                  <p className="font-medium text-white">Evidencia centralizada</p>
                  <p className="text-sm text-white/50 mt-1">Documentación lista para revisión y auditoría</p>
                </div>
              </div>

              <div className="flex items-start gap-4 p-6 rounded-2xl bg-white/5 border border-white/10 text-left">
                <div className="w-10 h-10 rounded-xl bg-amber-500/20 flex items-center justify-center flex-shrink-0">
                  <svg className="w-5 h-5 text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                </div>
                <div>
                  <p className="font-medium text-white">Operación más visible</p>
                  <p className="text-sm text-white/50 mt-1">Todos los actores clave informados</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Final CTA Section */}
      <section className="relative py-20 md:py-32">
        <div className="max-w-7xl mx-auto px-6">
          <div className="max-w-3xl mx-auto">
            <div className="relative rounded-3xl overflow-hidden">
              {/* Background gradient */}
              <div className="absolute inset-0 bg-gradient-to-br from-emerald-600/20 via-slate-900 to-violet-600/20" />
              <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHZpZXdCb3g9IjAgMCA2MCA2MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48ZyBmaWxsPSJub25lIiBmaWxsLXJ1bGU9ImV2ZW5vZGQiPjxnIGZpbGw9IiNmZmZmZmYiIGZpbGwtb3BhY2l0eT0iMC4wMyI+PGNpcmNsZSBjeD0iMzAiIGN5PSIzMCIgcj0iMS41Ii8+PC9nPjwvZz48L3N2Zz4=')] opacity-30" />
              
              {/* Content */}
              <div className="relative p-10 md:p-16 text-center">
                <h2 className="text-3xl md:text-4xl font-bold text-white tracking-tight mb-4">
                  Convierte el control operativo en una ventaja competitiva.
                </h2>
                <p className="text-lg text-white/60 max-w-xl mx-auto mb-10">
                  Deja atrás la gestión dispersa y lleva tus procesos a una plataforma preparada para trazabilidad, cumplimiento y ejecución real en campo.
                </p>
                <button className="px-10 py-4 rounded-2xl bg-gradient-to-r from-emerald-500 to-teal-500 text-white font-semibold shadow-lg shadow-emerald-500/30 hover:shadow-emerald-500/50 transition-all">
                  Agendar una demostración
                </button>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="relative border-t border-white/5 py-12">
        <div className="max-w-7xl mx-auto px-6">
          <div className="flex flex-col md:flex-row justify-between items-center gap-6">
            {/* Logo & Copyright */}
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-emerald-400 via-teal-500 to-emerald-600 flex items-center justify-center">
                <span className="text-white font-black text-sm">P</span>
              </div>
              <div>
                <p className="text-sm font-semibold text-white">PRANELY</p>
                <p className="text-xs text-white/40">© 2024. Gestión de residuos industriales.</p>
              </div>
            </div>

            {/* Links */}
            <div className="flex items-center gap-8 text-sm text-white/40">
              <a href="#" className="hover:text-white/60 transition-colors">Términos</a>
              <a href="#" className="hover:text-white/60 transition-colors">Privacidad</a>
              <a href="#" className="hover:text-white/60 transition-colors">Contacto</a>
            </div>

            {/* Tech stack */}
            <div className="flex items-center gap-4 text-xs text-white/30">
              <span>NOM-052-SEMARNAT-2005</span>
              <span>•</span>
              <span>México</span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
