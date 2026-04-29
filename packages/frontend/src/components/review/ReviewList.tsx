// ReviewList - Lista de movimientos pendientes de revisión
"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useAuth } from "@/contexts/AuthContext";
import { wasteApi, type WasteMovement } from "@/lib/waste-api";
import { StatusBadge } from "@/components/dashboard/StatusBadge";
import { ConfidenceBar } from "@/components/dashboard/ConfidenceBar";

type ReviewStatus = "pending" | "in_review" | "validated" | "rejected" | "exception" | "all";

interface ReviewListProps {
  filter?: ReviewStatus;
  onSelect?: (movement: WasteMovement) => void;
}

function ReviewCard({ 
  movement, 
  onView 
}: { 
  movement: WasteMovement; 
  onView?: () => void;
}) {
  return (
    <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl p-5 hover:bg-white/10 transition-all group">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          {/* Header */}
          <div className="flex items-center gap-3 mb-3">
            <span className="text-white font-mono font-bold">#{movement.id}</span>
            <StatusBadge status={movement.status} />
            {movement.is_immutable && (
              <span className="px-2 py-0.5 rounded-full bg-violet-500/20 text-violet-300 text-xs font-medium">
                ✓ Validado
              </span>
            )}
          </div>

          {/* Manifest */}
          <h4 className="text-white font-semibold text-lg mb-1 truncate">
            {movement.manifest_number}
          </h4>

          {/* Details */}
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-white/40">Tipo:</span>
              <span className="text-white/70 ml-2">{movement.waste_type}</span>
            </div>
            <div>
              <span className="text-white/40">Cantidad:</span>
              <span className="text-white/70 ml-2">{movement.quantity} {movement.unit}</span>
            </div>
            <div>
              <span className="text-white/40">Fecha:</span>
              <span className="text-white/70 ml-2">
                {movement.date ? new Date(movement.date).toLocaleDateString("es-MX") : "—"}
              </span>
            </div>
            <div>
              <span className="text-white/40">Confianza:</span>
              <div className="inline-flex ml-2">
                <ConfidenceBar score={movement.confidence_score ?? 0} size="sm" />
              </div>
            </div>
          </div>

          {/* Rejection reason */}
          {movement.rejection_reason && (
            <div className="mt-3 p-3 rounded-xl bg-rose-500/10 border border-rose-500/20">
              <p className="text-rose-300 text-sm font-medium">Razón del rechazo:</p>
              <p className="text-rose-400/80 text-sm">{movement.rejection_reason}</p>
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="flex flex-col gap-2">
          <Link
            href={`/review/${movement.id}`}
            className="px-4 py-2 rounded-xl bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-400 text-sm font-medium text-center transition-colors"
          >
            {movement.status === "in_review" ? "Revisar" : "Ver detalles"}
          </Link>
        </div>
      </div>
    </div>
  );
}

function SkeletonCard() {
  return (
    <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl p-5 animate-pulse">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1">
          <div className="flex gap-3 mb-3">
            <div className="h-6 w-12 rounded bg-white/10" />
            <div className="h-6 w-20 rounded bg-white/10" />
          </div>
          <div className="h-7 w-40 rounded bg-white/10 mb-2" />
          <div className="grid grid-cols-2 gap-4">
            <div className="h-4 w-24 rounded bg-white/10" />
            <div className="h-4 w-24 rounded bg-white/10" />
          </div>
        </div>
        <div className="h-10 w-24 rounded-xl bg-white/10" />
      </div>
    </div>
  );
}

function StatusFilter({ 
  current, 
  onChange,
  counts
}: { 
  current: ReviewStatus; 
  onChange: (status: ReviewStatus) => void;
  counts: Record<ReviewStatus, number>;
}) {
  const filters: { status: ReviewStatus; label: string }[] = [
    { status: "all", label: "Todos" },
    { status: "in_review", label: "En revisión" },
    { status: "pending", label: "Pendientes" },
    { status: "validated", label: "Validados" },
    { status: "rejected", label: "Rechazados" },
  ];

  return (
    <div className="flex flex-wrap gap-2">
      {filters.map(({ status, label }) => (
        <button
          key={status}
          onClick={() => onChange(status)}
          className={`
            px-4 py-2 rounded-xl text-sm font-medium transition-all
            ${current === status 
              ? "bg-emerald-500/30 text-emerald-300 border border-emerald-500/40" 
              : "bg-white/5 text-white/60 border border-white/10 hover:bg-white/10"
            }
          `}
        >
          {label}
          {counts[status] !== undefined && (
            <span className="ml-2 px-2 py-0.5 rounded-full text-xs bg-white/10">
              {counts[status]}
            </span>
          )}
        </button>
      ))}
    </div>
  );
}

export function ReviewList({ filter: initialFilter = "all", onSelect }: ReviewListProps) {
  const { token } = useAuth();
  const [movements, setMovements] = useState<WasteMovement[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<ReviewStatus>(initialFilter);
  const [counts, setCounts] = useState<Record<ReviewStatus, number>>({
    all: 0, pending: 0, in_review: 0, validated: 0, rejected: 0, exception: 0
  });

  const fetchMovements = useCallback(async () => {
    if (!token) return;
    
    try {
      setLoading(true);
      setError(null);
      
      const params = filter !== "all" ? { status: filter } : {};
      const response = await wasteApi.list({ page_size: 50, ...params });
      
      setMovements(response.items);
      
      // Calculate counts from stats
      try {
        const stats = await wasteApi.stats();
        setCounts({
          all: stats.total,
          pending: stats.pending,
          in_review: stats.in_review,
          validated: stats.validated,
          rejected: stats.rejected,
          exception: stats.exception,
        });
      } catch {
        // Stats might fail, use items count as fallback
        setCounts(prev => ({ ...prev, all: response.total }));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al cargar movimientos");
    } finally {
      setLoading(false);
    }
  }, [token, filter]);

  useEffect(() => {
    fetchMovements();
  }, [fetchMovements]);

  // Polling cada 30s
  useEffect(() => {
    if (!token) return;
    const interval = setInterval(fetchMovements, 30000);
    return () => clearInterval(interval);
  }, [fetchMovements, token]);

  if (error) {
    return (
      <div className="p-6 rounded-2xl bg-rose-500/10 border border-rose-500/20">
        <p className="text-rose-300 font-medium">Error al cargar</p>
        <p className="text-rose-400/80 text-sm mt-1">{error}</p>
        <button 
          onClick={fetchMovements}
          className="mt-4 px-4 py-2 rounded-xl bg-white/10 hover:bg-white/20 text-white text-sm transition-colors"
        >
          Reintentar
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Filters */}
      <StatusFilter current={filter} onChange={setFilter} counts={counts} />

      {/* Stats summary */}
      <div className="flex gap-4 text-sm">
        <span className="text-white/40">
          Mostrando <span className="text-white font-medium">{movements.length}</span> movimientos
        </span>
        {filter === "all" && (
          <span className="text-white/40">
            · <span className="text-amber-400">{counts.pending} pendientes</span> de revisar
          </span>
        )}
      </div>

      {/* List */}
      {loading ? (
        <div className="space-y-4">
          {[...Array(3)].map((_, i) => <SkeletonCard key={i} />)}
        </div>
      ) : movements.length === 0 ? (
        <div className="text-center py-16">
          <div className="w-20 h-20 mx-auto mb-4 rounded-2xl bg-white/5 flex items-center justify-center">
            <span className="text-4xl">📋</span>
          </div>
          <h3 className="text-xl font-bold text-white mb-2">
            {filter === "all" 
              ? "No hay movimientos" 
              : `No hay movimientos en "${filter}"`}
          </h3>
          <p className="text-white/50 max-w-md mx-auto">
            {filter === "in_review" 
              ? "Todos los movimientos han sido revisados. ¡Buen trabajo!"
              : "Los movimientos aparecerán aquí una vez creados."}
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {movements.map((movement) => (
            <ReviewCard 
              key={movement.id} 
              movement={movement}
              onView={() => onSelect?.(movement)}
            />
          ))}
        </div>
      )}

      {/* Refresh button */}
      <div className="flex justify-center pt-4">
        <button
          onClick={fetchMovements}
          className="px-4 py-2 rounded-xl bg-white/5 hover:bg-white/10 text-white/60 text-sm flex items-center gap-2 transition-colors"
        >
          <svg className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          Actualizar
        </button>
      </div>
    </div>
  );
}
