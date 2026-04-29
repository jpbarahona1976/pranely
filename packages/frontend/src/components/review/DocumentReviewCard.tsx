// DocumentReviewCard - Glassmorphism review card with IA fields
"use client";

import { useState } from "react";
import type { ReviewDocument } from "./ReviewQueue";

interface DocumentReviewCardProps {
  document: ReviewDocument;
  onApprove: (id: number) => void;
  onReject: (id: number, reason: string) => void;
  onReprocess: (id: number) => void;
  onUpdate: (id: number, data: Partial<ReviewDocument>) => void;
  loading?: boolean;
}

function getConfidenceColor(confidence: number): {
  bg: string;
  border: string;
  text: string;
  bgProgress: string;
} {
  if (confidence >= 0.85) {
    return {
      bg: "bg-emerald-500/10",
      border: "border-emerald-500/30",
      text: "text-emerald-300",
      bgProgress: "bg-emerald-500",
    };
  } else if (confidence >= 0.75) {
    return {
      bg: "bg-blue-500/10",
      border: "border-blue-500/30",
      text: "text-blue-300",
      bgProgress: "bg-blue-500",
    };
  } else {
    return {
      bg: "bg-rose-500/10",
      border: "border-rose-500/30",
      text: "text-rose-300",
      bgProgress: "bg-rose-500",
    };
  }
}

function FieldDisplay({
  label,
  value,
  iaValue,
  confidence,
  editable = false,
  onChange,
}: {
  label: string;
  value: string | number | undefined;
  iaValue?: string | number;
  confidence?: number;
  editable?: boolean;
  onChange?: (value: string) => void;
}) {
  const hasIaDiff = iaValue !== undefined && iaValue !== value;
  const colors = confidence !== undefined ? getConfidenceColor(confidence) : getConfidenceColor(1);
  const [editValue, setEditValue] = useState(String(value || ""));

  return (
    <div className="space-y-1">
      <label className="text-xs text-white/40 uppercase tracking-wider">{label}</label>
      <div className="relative">
        {editable ? (
          <input
            type="text"
            value={editValue}
            onChange={(e) => {
              setEditValue(e.target.value);
              onChange?.(e.target.value);
            }}
            className="w-full px-3 py-2 rounded-xl bg-white/5 border border-white/10 text-white text-sm
                       focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500/50
                       transition-all"
          />
        ) : (
          <div className={`
            px-3 py-2 rounded-xl text-sm
            ${hasIaDiff ? colors.bg : "bg-white/5"}
            ${hasIaDiff ? colors.border : "border-white/10"}
            border
            ${hasIaDiff ? colors.text : "text-white/80"}
          `}>
            <div className="flex items-center justify-between gap-2">
              <span>{value || "—"}</span>
              {hasIaDiff && iaValue && (
                <span className="text-xs text-white/40">
                  IA: {iaValue}
                </span>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export function DocumentReviewCard({
  document,
  onApprove,
  onReject,
  onReprocess,
  onUpdate,
  loading,
}: DocumentReviewCardProps) {
  const [showRejectModal, setShowRejectModal] = useState(false);
  const [rejectReason, setRejectReason] = useState("");
  const [editableFields, setEditableFields] = useState<Set<string>>(new Set());
  const [editedValues, setEditedValues] = useState<Record<string, string>>({});
  const colors = getConfidenceColor(document.confidence_score);
  const needsManualReview = document.confidence_score < 0.75;

  const handleToggleEdit = (field: string) => {
    setEditableFields((prev) => {
      const next = new Set(prev);
      if (next.has(field)) {
        next.delete(field);
      } else {
        next.add(field);
      }
      return next;
    });
  };

  const handleApprove = () => {
    if (Object.keys(editedValues).length > 0) {
      onUpdate(document.id, editedValues as unknown as Partial<ReviewDocument>);
    }
    onApprove(document.id);
  };

  const handleReject = () => {
    if (rejectReason.trim()) {
      onReject(document.id, rejectReason);
      setShowRejectModal(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h3 className="text-xl font-bold text-white mb-1">
            {document.manifest_number}
          </h3>
          <div className="flex items-center gap-3 text-sm text-white/40">
            <span>{document.generator_name}</span>
            <span>•</span>
            <span>{new Date(document.date).toLocaleDateString("es-MX")}</span>
          </div>
        </div>

        {/* Confidence Badge */}
        <div className={`
          px-4 py-2 rounded-2xl text-center
          ${colors.bg} ${colors.border} border
        `}>
          <div className={`text-2xl font-bold ${colors.text}`}>
            {Math.round(document.confidence_score * 100)}%
          </div>
          <div className="text-xs text-white/50">Confianza IA</div>
        </div>
      </div>

      {/* Manual Review Warning */}
      {needsManualReview && (
        <div className={`
          p-4 rounded-2xl border
          bg-rose-500/10 border-rose-500/30
        `}>
          <div className="flex items-start gap-3">
            <div className="p-2 rounded-xl bg-rose-500/20">
              <svg className="w-5 h-5 text-rose-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </div>
            <div>
              <p className="font-semibold text-rose-300">Revisión Manual Requerida</p>
              <p className="text-sm text-rose-400/80 mt-1">
                La confianza de extracción es menor al 75%. Por favor verifica los datos 
                extraídos antes de aprobar.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Extracted Fields Grid */}
      <div className={`
        p-6 rounded-2xl
        bg-white/5 border border-white/10
        ${needsManualReview ? "border-rose-500/30" : ""}
      `}>
        <div className="flex items-center justify-between mb-4">
          <h4 className="text-sm font-semibold text-white/70 uppercase tracking-wider">
            Datos Extraídos por IA
          </h4>
          {needsManualReview && (
            <button
              onClick={() => {
                // Enable all fields for editing
                setEditableFields(new Set(["quantity", "waste_type", "generator_name"]));
              }}
              className="text-xs text-emerald-400 hover:text-emerald-300 flex items-center gap-1"
            >
              <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
              </svg>
              Editar campos
            </button>
          )}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <FieldDisplay
            label="No. Manifiesto"
            value={document.manifest_number}
            iaValue={document.ia_extracted?.manifest_number}
            confidence={document.confidence_score}
          />
          
          <FieldDisplay
            label="Fecha"
            value={document.date}
            iaValue={document.ia_extracted?.date}
            confidence={document.confidence_score}
          />
          
          <FieldDisplay
            label="Tipo Residuo"
            value={document.waste_type}
            iaValue={document.ia_extracted?.waste_type}
            confidence={document.confidence_score}
            editable={needsManualReview && editableFields.has("waste_type")}
            onChange={(v) => setEditedValues((p) => ({ ...p, waste_type: v }))}
          />
          
          <FieldDisplay
            label="Cantidad"
            value={`${document.quantity} ${document.unit}`}
            iaValue={document.ia_extracted?.quantity ? `${document.ia_extracted.quantity} ${document.ia_extracted.unit || document.unit}` : undefined}
            confidence={document.confidence_score}
            editable={needsManualReview && editableFields.has("quantity")}
            onChange={(v) => setEditedValues((p) => ({ ...p, quantity: v }))}
          />
          
          <FieldDisplay
            label="Generador"
            value={document.generator_name}
            confidence={document.confidence_score}
          />
          
          <FieldDisplay
            label="Transportista"
            value={document.transporter_name}
            confidence={document.confidence_score}
          />
          
          <div className="md:col-span-2">
            <FieldDisplay
              label="Destino Final"
              value={document.final_destination}
              confidence={document.confidence_score}
            />
          </div>
        </div>
      </div>

      {/* Rejection Reason (if exists) */}
      {document.status === "rejected" && document.rejection_reason && (
        <div className="p-4 rounded-2xl bg-rose-500/10 border border-rose-500/30">
          <div className="flex items-start gap-3">
            <div className="p-2 rounded-xl bg-rose-500/20">
              <svg className="w-5 h-5 text-rose-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </div>
            <div>
              <p className="font-semibold text-rose-300">Razón de Rechazo</p>
              <p className="text-sm text-rose-400/80 mt-1">
                {document.rejection_reason}
              </p>
              {document.reviewed_by && (
                <p className="text-xs text-rose-400/60 mt-2">
                  Por: {document.reviewed_by} • {document.reviewed_at && new Date(document.reviewed_at).toLocaleString("es-MX")}
                </p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Action Buttons */}
      {!document.is_immutable && document.status !== "validated" && (
        <div className="flex flex-col sm:flex-row gap-3">
          <button
            onClick={handleApprove}
            disabled={loading}
            className={`
              flex-1 flex items-center justify-center gap-2 px-6 py-3 rounded-2xl
              font-semibold transition-all
              ${loading
                ? "bg-emerald-500/50 cursor-not-allowed"
                : "bg-gradient-to-r from-emerald-500 to-teal-500 hover:shadow-lg hover:shadow-emerald-500/30"
              }
              text-white
            `}
          >
            {loading ? (
              <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            ) : (
              <>
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                Aprobar
              </>
            )}
          </button>

          <button
            onClick={() => setShowRejectModal(true)}
            disabled={loading}
            className="flex items-center justify-center gap-2 px-6 py-3 rounded-2xl
                       bg-white/5 hover:bg-rose-500/20 border border-white/10 hover:border-rose-500/30
                       text-white/80 hover:text-rose-300 font-medium transition-all"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
            Rechazar
          </button>

          <button
            onClick={() => onReprocess(document.id)}
            disabled={loading}
            className="flex items-center justify-center gap-2 px-6 py-3 rounded-2xl
                       bg-white/5 hover:bg-blue-500/20 border border-white/10 hover:border-blue-500/30
                       text-white/80 hover:text-blue-300 font-medium transition-all"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            Reprocesar
          </button>
        </div>
      )}

      {/* Immutable Badge */}
      {document.is_immutable && (
        <div className="flex items-center justify-center gap-2 p-4 rounded-2xl bg-emerald-500/10 border border-emerald-500/30">
          <svg className="w-5 h-5 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
          </svg>
          <span className="text-emerald-300 font-medium">Documento Validado - Inmutable</span>
        </div>
      )}

      {/* Reject Modal */}
      {showRejectModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div 
            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            onClick={() => setShowRejectModal(false)}
          />
          <div className="relative w-full max-w-md p-6 rounded-3xl bg-slate-800 border border-white/10 shadow-2xl">
            <h3 className="text-lg font-bold text-white mb-4">Rechazar Documento</h3>
            <p className="text-sm text-white/60 mb-4">
              Ingresa la razón del rechazo. El documento será marcado como inválido.
            </p>
            <textarea
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
              placeholder="Ej: Datos incorrectos en el manifiesto, falta información required..."
              rows={4}
              className="w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white text-sm
                         placeholder-white/30 focus:outline-none focus:ring-2 focus:ring-rose-500/50 resize-none"
            />
            <div className="flex gap-3 mt-4">
              <button
                onClick={() => setShowRejectModal(false)}
                className="flex-1 px-4 py-2.5 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-white/80 font-medium transition-all"
              >
                Cancelar
              </button>
              <button
                onClick={handleReject}
                disabled={!rejectReason.trim()}
                className="flex-1 px-4 py-2.5 rounded-xl bg-rose-500 hover:bg-rose-600 text-white font-semibold transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Rechazar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default DocumentReviewCard;
