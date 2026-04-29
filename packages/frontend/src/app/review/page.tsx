// Review page - Glassmorphism document review with AI extraction
"use client";

import { useState, useCallback, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { ReviewQueue, type ReviewDocument } from "@/components/review/ReviewQueue";
import { DocumentReviewCard } from "@/components/review/DocumentReviewCard";

// Mock data for demo
const mockDocuments: ReviewDocument[] = [
  {
    id: 1,
    organization_id: 1,
    manifest_number: "NOM-2026-001234",
    date: "2026-04-28",
    waste_type: "PELIGROSO Clase A",
    quantity: 250.5,
    unit: "kg",
    generator_name: "Industrias del Norte S.A. de C.V.",
    transporter_name: "Transportes Ecológicos MX",
    final_destination: "Centro de Acopio Norte",
    status: "in_review",
    confidence_score: 0.92,
    is_immutable: false,
    created_at: "2026-04-28T10:00:00Z",
    updated_at: "2026-04-28T10:00:00Z",
    ia_extracted: {
      manifest_number: "NOM-2026-001234",
      waste_type: "PELIGROSO Clase A",
      quantity: 250.5,
      unit: "kg",
      date: "2026-04-28",
    },
  },
  {
    id: 2,
    organization_id: 1,
    manifest_number: "NOM-2026-001235",
    date: "2026-04-27",
    waste_type: "RESIDUO ESPECIAL",
    quantity: 500,
    unit: "kg",
    generator_name: "Plásticos del Centro",
    transporter_name: "Residuos SA",
    final_destination: "Planta Tratadora Central",
    status: "in_review",
    confidence_score: 0.68, // Low confidence - needs manual review
    is_immutable: false,
    created_at: "2026-04-27T09:00:00Z",
    updated_at: "2026-04-27T09:00:00Z",
    ia_extracted: {
      manifest_number: "NOM-2026-001235",
      waste_type: "RESIDUO ESPECIAL",
      quantity: 480, // Different from original
      unit: "kg",
      date: "2026-04-27",
    },
  },
  {
    id: 3,
    organization_id: 1,
    manifest_number: "NOM-2026-001236",
    date: "2026-04-26",
    waste_type: "PELIGROSO Clase B",
    quantity: 120,
    unit: "kg",
    generator_name: "Químicos Mexicanos",
    transporter_name: "Transportes Especializados",
    final_destination: "Centro Especializado Norte",
    status: "validated",
    confidence_score: 0.98,
    is_immutable: true,
    created_at: "2026-04-26T08:00:00Z",
    updated_at: "2026-04-26T16:00:00Z",
    reviewed_by: "Carlos Ruiz",
    reviewed_at: "2026-04-26T16:00:00Z",
  },
  {
    id: 4,
    organization_id: 1,
    manifest_number: "NOM-2026-001237",
    date: "2026-04-25",
    waste_type: "INERTE",
    quantity: 1000,
    unit: "kg",
    generator_name: "Construcciones ABC",
    transporter_name: "Volquetes MX",
    final_destination: "Relleno Sanitario",
    status: "rejected",
    confidence_score: 0.45,
    is_immutable: false,
    created_at: "2026-04-25T11:00:00Z",
    updated_at: "2026-04-25T15:00:00Z",
    rejection_reason: "Falta manifest number en documento",
    reviewed_by: "María García",
    reviewed_at: "2026-04-25T15:00:00Z",
  },
  {
    id: 5,
    organization_id: 1,
    manifest_number: "NOM-2026-001238",
    date: "2026-04-24",
    waste_type: "RECICLABLE",
    quantity: 800,
    unit: "kg",
    generator_name: "Papelera del Valle",
    transporter_name: "Reciclajes SA",
    final_destination: "Planta Recycla",
    status: "pending",
    confidence_score: 0.78,
    is_immutable: false,
    created_at: "2026-04-24T10:00:00Z",
    updated_at: "2026-04-24T10:00:00Z",
  },
];

function ReviewContent() {
  const router = useRouter();
  const { user, organization, logout, permissions } = useAuth();
  const [documents, setDocuments] = useState<ReviewDocument[]>(mockDocuments);
  const [selectedDoc, setSelectedDoc] = useState<ReviewDocument | null>(null);
  const [loading, setLoading] = useState(false);
  const [filter, setFilter] = useState<"all" | "pending" | "in_review" | "low_confidence">("all");

  // Stats
  const stats = {
    total: documents.length,
    pending: documents.filter((d) => d.status === "pending").length,
    inReview: documents.filter((d) => d.status === "in_review").length,
    needsReview: documents.filter((d) => d.confidence_score < 0.75 && d.status === "in_review").length,
    validated: documents.filter((d) => d.status === "validated").length,
  };

  // Filtered documents
  const filteredDocs = documents.filter((doc) => {
    switch (filter) {
      case "pending":
        return doc.status === "pending";
      case "in_review":
        return doc.status === "in_review";
      case "low_confidence":
        return doc.confidence_score < 0.75;
      default:
        return true;
    }
  });

  // Actions
  const handleApprove = useCallback((id: number) => {
    setDocuments((prev) =>
      prev.map((d) =>
        d.id === id
          ? {
              ...d,
              status: "validated" as const,
              is_immutable: true,
              reviewed_by: user?.full_name || user?.email || "Sistema",
              reviewed_at: new Date().toISOString(),
            }
          : d
      )
    );
    setSelectedDoc(null);
  }, [user]);

  const handleReject = useCallback((id: number, reason: string) => {
    setDocuments((prev) =>
      prev.map((d) =>
        d.id === id
          ? {
              ...d,
              status: "rejected" as const,
              rejection_reason: reason,
              reviewed_by: user?.full_name || user?.email || "Sistema",
              reviewed_at: new Date().toISOString(),
            }
          : d
      )
    );
    setSelectedDoc(null);
  }, [user]);

  const handleReprocess = useCallback((id: number) => {
    setLoading(true);
    // Simulate reprocessing
    setTimeout(() => {
      setDocuments((prev) =>
        prev.map((d) =>
          d.id === id
            ? {
                ...d,
                status: "in_review" as const,
                confidence_score: 0.7 + Math.random() * 0.3, // New random confidence
              }
            : d
        )
      );
      setLoading(false);
    }, 1500);
  }, []);

  const handleUpdate = useCallback((id: number, data: Partial<ReviewDocument>) => {
    setDocuments((prev) =>
      prev.map((d) =>
        d.id === id
          ? { ...d, ...data }
          : d
      )
    );
  }, []);

  return (
    <div className="min-h-screen relative overflow-hidden">
      {/* Animated Background */}
      <div className="fixed inset-0 -z-10">
        <div className="absolute inset-0 bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900" />
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-emerald-500/20 rounded-full blur-3xl animate-pulse" />
        <div className="absolute top-1/3 right-1/4 w-80 h-80 bg-violet-500/15 rounded-full blur-3xl animate-pulse" style={{ animationDelay: '1s' }} />
        <div className="absolute bottom-1/4 left-1/3 w-72 h-72 bg-blue-500/15 rounded-full blur-3xl animate-pulse" style={{ animationDelay: '2s' }} />
      </div>

      {/* Header */}
      <header className="sticky top-0 z-50 backdrop-blur-xl bg-white/5 border-b border-white/10">
        <div className="max-w-[1920px] mx-auto px-6 py-4 flex justify-between items-center">
          <div className="flex items-center gap-4">
            <button
              onClick={() => router.push("/dashboard")}
              className="p-2 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 backdrop-blur-md transition-colors"
            >
              <svg className="w-5 h-5 text-white/60" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
              </svg>
            </button>
            
            <div className="relative group">
              <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-emerald-400 via-teal-500 to-emerald-600 flex items-center justify-center shadow-lg shadow-emerald-500/30">
                <span className="text-white font-black text-xl">P</span>
              </div>
            </div>
            <div>
              <h1 className="text-xl font-bold text-white tracking-tight">PRANELY</h1>
              <p className="text-xs text-white/40">Revisión de Documentos</p>
            </div>
          </div>
          
          <div className="flex items-center gap-4">
            <div className="px-4 py-2 rounded-2xl bg-white/10 backdrop-blur-md border border-white/10">
              <span className="text-sm font-medium text-white/80">{organization?.name || 'Org'}</span>
            </div>
            
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-2xl bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center text-white font-bold">
                {user?.email?.[0]?.toUpperCase() || 'U'}
              </div>
            </div>
            
            <button
              onClick={logout}
              className="p-3 rounded-2xl bg-white/5 hover:bg-white/10 border border-white/10 backdrop-blur-md transition-all"
            >
              <svg className="w-5 h-5 text-white/60 hover:text-rose-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
              </svg>
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-[1920px] mx-auto px-6 py-8">
        {/* Stats Bar */}
        <div className="flex flex-wrap items-center gap-4 mb-8">
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-white/20 rounded-full" />
              <span className="text-sm text-white/60">{stats.total} total</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-white/50 rounded-full" />
              <span className="text-sm text-white/60">{stats.pending} pendientes</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-blue-500 rounded-full animate-pulse" />
              <span className="text-sm text-white/60">{stats.inReview} en revisión</span>
            </div>
            {stats.needsReview > 0 && (
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 bg-rose-500 rounded-full" />
                <span className="text-sm text-rose-400">{stats.needsReview} requieren revisión</span>
              </div>
            )}
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-emerald-500 rounded-full" />
              <span className="text-sm text-emerald-400">{stats.validated} validados</span>
            </div>
          </div>

          {/* Filters */}
          <div className="ml-auto flex items-center gap-2">
            <button
              onClick={() => setFilter("all")}
              aria-pressed={filter === "all"}
              className={`px-4 py-2 rounded-xl text-sm font-medium transition-all ${
                filter === "all"
                  ? "bg-white/10 text-white border border-white/20"
                  : "text-white/60 hover:text-white/80"
              }`}
            >
              Todos{filter === "all" && " (activo)"}
            </button>
            <button
              onClick={() => setFilter("pending")}
              aria-pressed={filter === "pending"}
              className={`px-4 py-2 rounded-xl text-sm font-medium transition-all ${
                filter === "pending"
                  ? "bg-white/10 text-white border border-white/20"
                  : "text-white/60 hover:text-white/80"
              }`}
            >
              Pendientes{filter === "pending" && " (activo)"}
            </button>
            <button
              onClick={() => setFilter("in_review")}
              aria-pressed={filter === "in_review"}
              className={`px-4 py-2 rounded-xl text-sm font-medium transition-all ${
                filter === "in_review"
                  ? "bg-blue-500/20 text-blue-300 border border-blue-500/30"
                  : "text-white/60 hover:text-white/80"
              }`}
            >
              En Revisión{filter === "in_review" && " (activo)"}
            </button>
            <button
              onClick={() => setFilter("low_confidence")}
              aria-pressed={filter === "low_confidence"}
              className={`px-4 py-2 rounded-xl text-sm font-medium transition-all ${
                filter === "low_confidence"
                  ? "bg-rose-500/20 text-rose-300 border border-rose-500/30"
                  : "text-white/60 hover:text-white/80"
              }`}
            >
              Baja Confianza{filter === "low_confidence" && " (activo)"}
            </button>
          </div>
        </div>

        {/* Content Grid */}
        <div className="flex flex-col xl:flex-row gap-8">
          {/* Left: Document Queue */}
          <div className="xl:w-96 shrink-0">
            <div className="rounded-2xl bg-white/5 border border-white/10 backdrop-blur-md overflow-hidden">
              <div className="p-4 border-b border-white/5">
                <h3 className="text-sm font-semibold text-white/70 uppercase tracking-wider">
                  Cola de Documentos
                </h3>
              </div>
              <div className="max-h-[calc(100vh-320px)] overflow-y-auto">
                <ReviewQueue
                  documents={filteredDocs}
                  selectedId={selectedDoc?.id || null}
                  onSelect={setSelectedDoc}
                />
              </div>
            </div>
          </div>

          {/* Right: Document Detail */}
          <div className="flex-1 min-w-0">
            {selectedDoc ? (
              <div className="rounded-2xl bg-white/5 border border-white/10 backdrop-blur-md p-6">
                <DocumentReviewCard
                  document={selectedDoc}
                  onApprove={handleApprove}
                  onReject={handleReject}
                  onReprocess={handleReprocess}
                  onUpdate={handleUpdate}
                  loading={loading}
                />
              </div>
            ) : (
              <div className="rounded-2xl bg-white/5 border border-white/10 backdrop-blur-md p-12 text-center">
                <div className="inline-flex items-center justify-center w-20 h-20 rounded-2xl bg-white/5 mb-6">
                  <svg className="w-10 h-10 text-white/30" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
                  </svg>
                </div>
                <h3 className="text-xl font-semibold text-white/60 mb-2">
                  Selecciona un documento
                </h3>
                <p className="text-white/40 max-w-md mx-auto">
                  Elige un documento de la cola para ver los datos extraídos por IA 
                  y tomar una decisión de aprobación o rechazo.
                </p>

                {/* Quick Stats */}
                <div className="flex items-center justify-center gap-8 mt-8">
                  <div className="text-center">
                    <div className="text-3xl font-bold text-emerald-400">
                      {Math.round(
                        (documents.filter((d) => d.confidence_score >= 0.85).length / 
                         (documents.length || 1)) * 100
                      )}%
                    </div>
                    <div className="text-xs text-white/40 mt-1">Alta confianza</div>
                  </div>
                  <div className="text-center">
                    <div className="text-3xl font-bold text-blue-400">
                      {Math.round(
                        (documents.filter((d) => d.confidence_score >= 0.75 && d.confidence_score < 0.85).length / 
                         (documents.length || 1)) * 100
                      )}%
                    </div>
                    <div className="text-xs text-white/40 mt-1">Media confianza</div>
                  </div>
                  <div className="text-center">
                    <div className="text-3xl font-bold text-rose-400">
                      {Math.round(
                        (documents.filter((d) => d.confidence_score < 0.75).length / 
                         (documents.length || 1)) * 100
                      )}%
                    </div>
                    <div className="text-xs text-white/40 mt-1">Baja confianza</div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-white/5 py-6 mt-8">
        <div className="max-w-[1920px] mx-auto px-6 flex justify-between items-center text-sm text-white/30">
          <span>© 2024 PRANELY. Sistema Documental Maestro.</span>
          <div className="flex items-center gap-4">
            <span>NOM-052-SEMARNAT-2005</span>
            <span>•</span>
            <span>México</span>
          </div>
        </div>
      </footer>
    </div>
  );
}

export function ReviewPage() {
  return (
    <ProtectedRoute fallbackPath="/login">
      <ReviewContent />
    </ProtectedRoute>
  );
}

export default ReviewPage;
