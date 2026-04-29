// Review detail page - Detalle de un movimiento con acciones de revisión
"use client";

import { useEffect, useState, useCallback, use } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { wasteApi, type WasteMovement } from "@/lib/waste-api";
import { ReviewActions } from "@/components/review/ReviewActions";
import { StatusBadge } from "@/components/dashboard/StatusBadge";
import { ConfidenceBar } from "@/components/dashboard/ConfidenceBar";

interface PageProps {
  params: Promise<{ id: string }>;
}

function ReviewDetailContent({ id }: { id: string }) {
  const router = useRouter();
  const { token, permissions } = useAuth();
  const [movement, setMovement] = useState<WasteMovement | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const movementId = parseInt(id, 10);

  const fetchMovement = useCallback(async () => {
    if (!token || isNaN(movementId)) return;
    
    try {
      setLoading(true);
      setError(null);
      const data = await wasteApi.get(movementId);
      setMovement(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al cargar movimiento");
    } finally {
      setLoading(false);
    }
  }, [token, movementId]);

  useEffect(() => {
    fetchMovement();
  }, [fetchMovement]);

  const handleSuccess = (action: string) => {
    // Refrescar datos
    fetchMovement();
    
    // Mostrar feedback
    const messages: Record<string, string> = {
      approve: "Movimiento aprobado exitosamente",
      reject: "Movimiento rechazado",
      request_changes: "Cambios solicitados",
    };
    alert(messages[action] || "Acción completada");
  };

  const handleError = (error: string) => {
    alert(`Error: ${error}`);
  };

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto p-6 space-y-6">
        <div className="h-8 w-32 bg-white/10 rounded animate-pulse" />
        <div className="h-64 bg-white/10 rounded-2xl animate-pulse" />
        <div className="h-48 bg-white/10 rounded-2xl animate-pulse" />
      </div>
    );
  }

  if (error || !movement) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <a 
          href="/review"
          className="inline-flex items-center gap-2 text-white/60 hover:text-white mb-6"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
          </svg>
          Volver a revisión
        </a>
        
        <div className="p-6 rounded-2xl bg-rose-500/10 border border-rose-500/20">
          <p className="text-rose-300 font-semibold">Error al cargar movimiento</p>
          <p className="text-rose-400/80 mt-1">{error || "Movimiento no encontrado"}</p>
          <button 
            onClick={fetchMovement}
            className="mt-4 px-4 py-2 rounded-xl bg-white/10 hover:bg-white/20 text-white text-sm"
          >
            Reintentar
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      {/* Back link */}
      <a 
        href="/review"
        className="inline-flex items-center gap-2 text-white/60 hover:text-white transition-colors"
      >
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
        </svg>
        Volver a revisión
      </a>

      {/* Header */}
      <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-3xl p-6">
        <div className="flex items-start justify-between gap-4 mb-6">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <span className="text-white/40 text-sm">Movimiento</span>
              <StatusBadge status={movement.status} />
              {movement.is_immutable && (
                <span className="px-2 py-0.5 rounded-full bg-violet-500/20 text-violet-300 text-xs font-medium">
                  ✓ Validado
                </span>
              )}
            </div>
            <h1 className="text-3xl font-bold text-white">{movement.manifest_number}</h1>
            <p className="text-white/50 mt-1">ID: #{movement.id}</p>
          </div>
          
          <div className="text-right">
            <p className="text-white/40 text-sm">Confianza IA</p>
            <div className="mt-2">
              <ConfidenceBar score={movement.confidence_score ?? 0} size="lg" />
            </div>
          </div>
        </div>

        {/* Details grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
          <DetailField label="Tipo de residuo" value={movement.waste_type} />
          <DetailField label="Cantidad" value={`${movement.quantity} ${movement.unit}`} />
          <DetailField label="Fecha" value={movement.date ? new Date(movement.date).toLocaleDateString("es-MX") : "—"} />
          <DetailField label="Generador" value={movement.generator_name} />
          <DetailField label="Transportista" value={movement.transporter_name} />
          <DetailField label="Destino final" value={movement.final_destination} />
        </div>

        {/* Rejection reason */}
        {movement.rejection_reason && (
          <div className="mt-6 p-4 rounded-xl bg-rose-500/10 border border-rose-500/20">
            <p className="text-rose-300 font-medium mb-1">Razón del rechazo:</p>
            <p className="text-rose-400/80">{movement.rejection_reason}</p>
            {movement.reviewed_by && (
              <p className="text-white/40 text-sm mt-2">
                Rechazado por {movement.reviewed_by}
              </p>
            )}
          </div>
        )}

        {/* Reviewed info */}
        {movement.reviewed_by && (
          <div className="mt-6 p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20">
            <p className="text-emerald-300 font-medium mb-1">Movimiento validado</p>
            <p className="text-white/60 text-sm">
              Revisado por <span className="text-emerald-400">{movement.reviewed_by}</span>
              {movement.reviewed_at && (
                <> el {new Date(movement.reviewed_at).toLocaleDateString("es-MX")}</>
              )}
            </p>
          </div>
        )}
      </div>

      {/* Actions */}
      {permissions.canReview && (
        <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-3xl p-6">
          <ReviewActions 
            movement={movement}
            onSuccess={handleSuccess}
            onError={handleError}
          />
        </div>
      )}

      {/* Timestamps */}
      <div className="text-center text-white/30 text-sm">
        <p>Creado: {new Date(movement.created_at).toLocaleString("es-MX")}</p>
        <p>Actualizado: {new Date(movement.updated_at).toLocaleString("es-MX")}</p>
      </div>
    </div>
  );
}

function DetailField({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-white/40 text-xs uppercase tracking-wider mb-1">{label}</p>
      <p className="text-white font-medium">{value || "—"}</p>
    </div>
  );
}

export default function ReviewDetailPage({ params }: PageProps) {
  const { id } = use(params);
  
  return (
    <ProtectedRoute fallbackPath="/login">
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
        <ReviewDetailContent id={id} />
      </div>
    </ProtectedRoute>
  );
}
