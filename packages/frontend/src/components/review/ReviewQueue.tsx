// ReviewQueue - Glassmorphism document queue table
"use client";

import { type WasteMovement } from "@/lib/waste-api";

interface ReviewQueueProps {
  documents: ReviewDocument[];
  selectedId: number | null;
  onSelect: (doc: ReviewDocument) => void;
  loading?: boolean;
}

export interface ReviewDocument {
  id: number;
  organization_id: number;
  manifest_number: string;
  date: string;
  waste_type: string;
  quantity: number;
  unit: string;
  generator_name: string;
  transporter_name: string;
  final_destination: string;
  status: "pending" | "in_review" | "validated" | "rejected" | "exception";
  confidence_score: number;
  is_immutable: boolean;
  created_at: string;
  updated_at: string;
  rejection_reason?: string;
  reviewed_by?: string;
  reviewed_at?: string;
  // IA extracted fields
  ia_extracted?: {
    manifest_number?: string;
    waste_type?: string;
    quantity?: number;
    unit?: string;
    generator_rfc?: string;
    transporter_rfc?: string;
    date?: string;
  };
}

function getConfidenceBadge(confidence: number): {
  label: string;
  bgColor: string;
  textColor: string;
  borderColor: string;
} {
  if (confidence >= 0.85) {
    return {
      label: "Alta",
      bgColor: "bg-emerald-500/20",
      textColor: "text-emerald-300",
      borderColor: "border-emerald-500/30",
    };
  } else if (confidence >= 0.75) {
    return {
      label: "Media",
      bgColor: "bg-blue-500/20",
      textColor: "text-blue-300",
      borderColor: "border-blue-500/30",
    };
  } else if (confidence >= 0.50) {
    return {
      label: "Baja",
      bgColor: "bg-amber-500/20",
      textColor: "text-amber-300",
      borderColor: "border-amber-500/30",
    };
  } else {
    return {
      label: "Muy Baja",
      bgColor: "bg-rose-500/20",
      textColor: "text-rose-300",
      borderColor: "border-rose-500/30",
    };
  }
}

function getStatusBadge(status: string): {
  label: string;
  bgColor: string;
  textColor: string;
  icon: JSX.Element;
} {
  switch (status) {
    case "pending":
      return {
        label: "Pendiente",
        bgColor: "bg-white/10",
        textColor: "text-white/70",
        icon: <span className="w-2 h-2 bg-white/50 rounded-full" />,
      };
    case "in_review":
      return {
        label: "En Revisión",
        bgColor: "bg-blue-500/20",
        textColor: "text-blue-300",
        icon: <span className="w-2 h-2 bg-blue-400 rounded-full animate-pulse" />,
      };
    case "validated":
      return {
        label: "Validado",
        bgColor: "bg-emerald-500/20",
        textColor: "text-emerald-300",
        icon: (
          <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        ),
      };
    case "rejected":
      return {
        label: "Rechazado",
        bgColor: "bg-rose-500/20",
        textColor: "text-rose-300",
        icon: (
          <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        ),
      };
    case "exception":
      return {
        label: "Excepción",
        bgColor: "bg-amber-500/20",
        textColor: "text-amber-300",
        icon: (
          <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
        ),
      };
    default:
      return {
        label: status,
        bgColor: "bg-white/10",
        textColor: "text-white/70",
        icon: <span className="w-2 h-2 bg-white/50 rounded-full" />,
      };
  }
}

function formatDate(dateStr: string): string {
  try {
    return new Date(dateStr).toLocaleDateString("es-MX", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    });
  } catch {
    return dateStr;
  }
}

export function ReviewQueue({ documents, selectedId, onSelect, loading }: ReviewQueueProps) {
  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-white/20 border-t-emerald-500 rounded-full animate-spin" />
      </div>
    );
  }

  if (documents.length === 0) {
    return (
      <div className="p-8 text-center">
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-white/5 mb-4">
          <svg className="w-8 h-8 text-white/30" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
          </svg>
        </div>
        <p className="text-white/40 text-sm">No hay documentos en cola</p>
      </div>
    );
  }

  return (
    <div className="divide-y divide-white/5">
      {documents.map((doc) => {
        const isSelected = selectedId === doc.id;
        const confidenceBadge = getConfidenceBadge(doc.confidence_score);
        const statusBadge = getStatusBadge(doc.status);
        const needsReview = doc.confidence_score < 0.75;

        return (
          <button
            key={doc.id}
            onClick={() => onSelect(doc)}
            className={`
              w-full p-4 text-left transition-all duration-200
              hover:bg-white/5 focus:outline-none focus:ring-2 focus:ring-emerald-500/50
              ${isSelected 
                ? "bg-emerald-500/10 border-l-2 border-l-emerald-500" 
                : "border-l-2 border-l-transparent"
              }
              ${needsReview && doc.status === "in_review" 
                ? "border-l-rose-500/50" 
                : ""
              }
            `}
          >
            <div className="flex items-start justify-between gap-3">
              {/* Left: Info */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-sm font-mono text-white/80 truncate">
                    {doc.manifest_number}
                  </span>
                  {needsReview && doc.status === "in_review" && (
                    <span className="px-1.5 py-0.5 text-[10px] font-bold uppercase bg-rose-500/20 text-rose-300 rounded">
                      Revisar
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-3 text-xs text-white/40">
                  <span>{formatDate(doc.date)}</span>
                  <span>•</span>
                  <span>{doc.waste_type}</span>
                  <span>•</span>
                  <span>{doc.quantity} {doc.unit}</span>
                </div>
              </div>

              {/* Right: Badges */}
              <div className="flex items-center gap-2 shrink-0">
                {/* Confidence */}
                <div className={`
                  flex items-center gap-1.5 px-2 py-1 rounded-lg text-xs
                  ${confidenceBadge.bgColor} ${confidenceBadge.textColor}
                `}>
                  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                  <span>{Math.round(doc.confidence_score * 100)}%</span>
                </div>

                {/* Status */}
                <div className={`
                  flex items-center gap-1.5 px-2 py-1 rounded-lg text-xs
                  ${statusBadge.bgColor} ${statusBadge.textColor}
                `}>
                  {statusBadge.icon}
                  <span>{statusBadge.label}</span>
                </div>
              </div>
            </div>
          </button>
        );
      })}
    </div>
  );
}

export default ReviewQueue;
