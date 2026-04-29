// ReviewActions - Acciones de revisión approve/reject/request_changes
"use client";

import { useState } from "react";
import { wasteApi, type WasteMovement } from "@/lib/waste-api";

interface ReviewActionsProps {
  movement: WasteMovement;
  onSuccess?: (action: string) => void;
  onError?: (error: string) => void;
}

export function ReviewActions({ 
  movement, 
  onSuccess, 
  onError 
}: ReviewActionsProps) {
  const [loading, setLoading] = useState<string | null>(null);
  const [showRejectModal, setShowRejectModal] = useState(false);
  const [showChangesModal, setShowChangesModal] = useState(false);
  const [rejectReason, setRejectReason] = useState("");
  const [changesComments, setChangesComments] = useState("");

  const handleAction = async (action: "approve" | "reject" | "request_changes", data?: { reason?: string; comments?: string }) => {
    try {
      setLoading(action);
      
      if (action === "approve") {
        await wasteApi.approve(movement.id);
        onSuccess?.("approve");
      } else if (action === "reject") {
        if (!data?.reason) {
          setShowRejectModal(true);
          setLoading(null);
          return;
        }
        await wasteApi.reject(movement.id, data.reason);
        onSuccess?.("reject");
      } else if (action === "request_changes") {
        await wasteApi.requestChanges(movement.id, data?.comments || "Se requieren cambios");
        onSuccess?.("request_changes");
      }
    } catch (err) {
      onError?.(err instanceof Error ? err.message : "Error desconocido");
    } finally {
      setLoading(null);
      setShowRejectModal(false);
      setShowChangesModal(false);
      setRejectReason("");
      setChangesComments("");
    }
  };

  const isImmutable = movement.is_immutable || movement.status === "validated";

  if (isImmutable) {
    return (
      <div className="p-6 rounded-2xl bg-violet-500/10 border border-violet-500/20">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-10 h-10 rounded-xl bg-violet-500/20 flex items-center justify-center">
            <svg className="w-5 h-5 text-violet-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
            </svg>
          </div>
          <div>
            <p className="text-violet-300 font-semibold">Movimiento validado</p>
            <p className="text-violet-400/60 text-sm">No se puede modificar un movimiento validado</p>
          </div>
        </div>
        {movement.reviewed_by && (
          <p className="text-white/50 text-sm">
            Revisado por <span className="text-white/70">{movement.reviewed_by}</span>
          </p>
        )}
      </div>
    );
  }

  if (movement.status !== "in_review") {
    return (
      <div className="p-6 rounded-2xl bg-amber-500/10 border border-amber-500/20">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-amber-500/20 flex items-center justify-center">
            <svg className="w-5 h-5 text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <div>
            <p className="text-amber-300 font-semibold">Acción requerida</p>
            <p className="text-amber-400/60 text-sm">
              Este movimiento necesita pasar a &quot;En revisión&quot; para poder ser aprobado
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <>
      <div className="space-y-4">
        <h4 className="text-white font-semibold">Acciones de revisión</h4>
        
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {/* Approve */}
          <button
            onClick={() => handleAction("approve")}
            disabled={loading !== null}
            className="flex flex-col items-center gap-3 p-6 rounded-2xl bg-emerald-500/20 hover:bg-emerald-500/30 border border-emerald-500/30 transition-all disabled:opacity-50"
          >
            <div className="w-12 h-12 rounded-xl bg-emerald-500/30 flex items-center justify-center">
              {loading === "approve" ? (
                <svg className="w-6 h-6 text-emerald-400 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
              ) : (
                <svg className="w-6 h-6 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              )}
            </div>
            <span className="text-emerald-300 font-semibold">Aprobar</span>
            <span className="text-emerald-400/60 text-xs text-center">
              Valida y bloquea el movimiento
            </span>
          </button>

          {/* Request Changes */}
          <button
            onClick={() => setShowChangesModal(true)}
            disabled={loading !== null}
            className="flex flex-col items-center gap-3 p-6 rounded-2xl bg-amber-500/20 hover:bg-amber-500/30 border border-amber-500/30 transition-all disabled:opacity-50"
          >
            <div className="w-12 h-12 rounded-xl bg-amber-500/30 flex items-center justify-center">
              <svg className="w-6 h-6 text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
              </svg>
            </div>
            <span className="text-amber-300 font-semibold">Solicitar cambios</span>
            <span className="text-amber-400/60 text-xs text-center">
              Pide correcciones al creador
            </span>
          </button>

          {/* Reject */}
          <button
            onClick={() => setShowRejectModal(true)}
            disabled={loading !== null}
            className="flex flex-col items-center gap-3 p-6 rounded-2xl bg-rose-500/20 hover:bg-rose-500/30 border border-rose-500/30 transition-all disabled:opacity-50"
          >
            <div className="w-12 h-12 rounded-xl bg-rose-500/30 flex items-center justify-center">
              <svg className="w-6 h-6 text-rose-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </div>
            <span className="text-rose-300 font-semibold">Rechazar</span>
            <span className="text-rose-400/60 text-xs text-center">
              Marca como rechazado con razón
            </span>
          </button>
        </div>
      </div>

      {/* Reject Modal */}
      {showRejectModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div 
            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            onClick={() => setShowRejectModal(false)}
          />
          <div className="relative bg-slate-800/95 backdrop-blur-xl border border-white/10 rounded-3xl p-8 max-w-md w-full shadow-2xl">
            <h3 className="text-xl font-bold text-white mb-4">Rechazar movimiento</h3>
            <p className="text-white/60 mb-4">Ingresa la razón del rechazo:</p>
            <textarea
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
              placeholder="Motivo del rechazo..."
              className="w-full px-4 py-3 rounded-xl bg-white/10 border border-white/20 text-white placeholder-white/40 resize-none focus:outline-none focus:ring-2 focus:ring-rose-500/50 transition-colors"
              rows={4}
              autoFocus
            />
            <div className="flex gap-4 mt-6">
              <button
                onClick={() => setShowRejectModal(false)}
                className="flex-1 px-6 py-3 rounded-xl bg-white/10 text-white/70 hover:bg-white/20 transition-colors"
              >
                Cancelar
              </button>
              <button
                onClick={() => handleAction("reject", { reason: rejectReason })}
                disabled={!rejectReason.trim() || loading === "reject"}
                className="flex-1 px-6 py-3 rounded-xl bg-rose-500 text-white font-semibold hover:bg-rose-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                {loading === "reject" ? (
                  <svg className="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                ) : "Rechazar"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Request Changes Modal */}
      {showChangesModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div 
            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            onClick={() => setShowChangesModal(false)}
          />
          <div className="relative bg-slate-800/95 backdrop-blur-xl border border-white/10 rounded-3xl p-8 max-w-md w-full shadow-2xl">
            <h3 className="text-xl font-bold text-white mb-4">Solicitar cambios</h3>
            <p className="text-white/60 mb-4">Describe los cambios requeridos:</p>
            <textarea
              value={changesComments}
              onChange={(e) => setChangesComments(e.target.value)}
              placeholder="Cambios requeridos..."
              className="w-full px-4 py-3 rounded-xl bg-white/10 border border-white/20 text-white placeholder-white/40 resize-none focus:outline-none focus:ring-2 focus:ring-amber-500/50 transition-colors"
              rows={4}
              autoFocus
            />
            <div className="flex gap-4 mt-6">
              <button
                onClick={() => setShowChangesModal(false)}
                className="flex-1 px-6 py-3 rounded-xl bg-white/10 text-white/70 hover:bg-white/20 transition-colors"
              >
                Cancelar
              </button>
              <button
                onClick={() => handleAction("request_changes", { comments: changesComments || "Se requieren cambios" })}
                disabled={loading === "request_changes"}
                className="flex-1 px-6 py-3 rounded-xl bg-amber-500 text-white font-semibold hover:bg-amber-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                {loading === "request_changes" ? (
                  <svg className="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                ) : "Solicitar"}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
