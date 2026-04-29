// Extraction page - Placeholder para pipeline IA (Fase 7A)
"use client";

import { ProtectedRoute } from "@/components/ProtectedRoute";

function ExtractionContent() {
  return (
    <div className="min-h-screen relative overflow-hidden">
      {/* Background */}
      <div className="fixed inset-0 -z-10">
        <div className="absolute inset-0 bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900" />
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-emerald-500/20 rounded-full blur-3xl animate-pulse" />
      </div>

      {/* Header */}
      <header className="sticky top-0 z-50 backdrop-blur-xl bg-white/5 border-b border-white/10">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center gap-4">
            <a href="/review" className="p-2 rounded-xl hover:bg-white/10 transition-colors">
              <svg className="w-6 h-6 text-white/60" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
              </svg>
            </a>
            <div>
              <h1 className="text-2xl font-bold text-white">Extracción IA</h1>
              <p className="text-white/50 text-sm">Fase 7A - No implementado aún</p>
            </div>
          </div>
        </div>
      </header>

      {/* Main */}
      <main className="max-w-4xl mx-auto px-6 py-16">
        <div className="text-center mb-12">
          <div className="w-24 h-24 mx-auto mb-6 rounded-3xl bg-gradient-to-br from-emerald-500/30 to-teal-500/10 flex items-center justify-center border border-emerald-500/20">
            <span className="text-5xl">🤖</span>
          </div>
          <h2 className="text-3xl font-bold text-white mb-4">Extracción Automática con IA</h2>
          <p className="text-white/60 max-w-xl mx-auto">
            Esta funcionalidad estará disponible en la Fase 7A. 
            Permitirá subir documentos y extraer automáticamente los datos de manifiestos.
          </p>
        </div>

        {/* Features */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
          <FeatureCard 
            icon="📄"
            title="Upload de documentos"
            description="Sube manifiestos en PDF, imágenes o fotos"
          />
          <FeatureCard 
            icon="🔍"
            title="OCR inteligente"
            description="Reconocimiento óptico de caracteres con IA"
          />
          <FeatureCard 
            icon="✅"
            title="Validación automática"
            description="Verificación de datos extraídos contra NOM-052"
          />
        </div>

        {/* Coming soon badge */}
        <div className="text-center">
          <span className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-amber-500/20 border border-amber-500/30 text-amber-300 text-sm font-medium">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            Disponible en Fase 7A
          </span>
        </div>

        {/* Navigation */}
        <div className="flex justify-center gap-4 mt-12">
          <a 
            href="/review"
            className="px-6 py-3 rounded-xl bg-white/10 hover:bg-white/20 text-white/80 transition-colors"
          >
            ← Volver a Revisión
          </a>
          <a 
            href="/dashboard"
            className="px-6 py-3 rounded-xl bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 border border-emerald-500/30 transition-colors"
          >
            Dashboard →
          </a>
        </div>
      </main>
    </div>
  );
}

function FeatureCard({ icon, title, description }: { icon: string; title: string; description: string }) {
  return (
    <div className="p-6 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-xl text-center">
      <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-white/10 flex items-center justify-center text-3xl">
        {icon}
      </div>
      <h3 className="text-white font-semibold mb-2">{title}</h3>
      <p className="text-white/50 text-sm">{description}</p>
    </div>
  );
}

export default function ExtractionPage() {
  return (
    <ProtectedRoute fallbackPath="/login">
      <ExtractionContent />
    </ProtectedRoute>
  );
}
