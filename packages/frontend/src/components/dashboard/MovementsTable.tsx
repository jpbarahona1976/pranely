// MovementsTable - Tabla de movimientos glassmorphism con acciones siempre visibles
"use client";

import { useState } from "react";
import { type WasteMovement, wasteApi } from "@/lib/waste-api";
import { StatusBadge } from "./StatusBadge";
import { ConfidenceBar } from "./ConfidenceBar";
import type { UserPermissions } from "@/contexts/AuthContext";

interface MovementsTableProps {
  movements: WasteMovement[];
  loading?: boolean;
  permissions: UserPermissions;
  onRefresh: () => void;
  onApprove?: (id: number) => void;
  onReject?: (id: number, reason: string) => void;
  onView?: (movement: WasteMovement) => void;
  onEdit?: (movement: WasteMovement) => void;
  onArchive?: (id: number) => void;
}

function SkeletonRow() {
  return (
    <tr className="animate-pulse">
      <td className="px-4 py-4"><div className="h-4 w-16 rounded bg-white/10" /></td>
      <td className="px-4 py-4"><div className="h-4 w-24 rounded bg-white/10" /></td>
      <td className="px-4 py-4"><div className="h-4 w-20 rounded bg-white/10" /></td>
      <td className="px-4 py-4"><div className="h-4 w-32 rounded bg-white/10" /></td>
      <td className="px-4 py-4"><div className="h-5 w-20 rounded-full bg-white/10" /></td>
      <td className="px-4 py-4"><div className="h-4 w-20 rounded bg-white/10" /></td>
      <td className="px-4 py-4"><div className="h-6 w-28 rounded bg-white/10" /></td>
    </tr>
  );
}

// ActionButton - Siempre visible, accesible en touch
function ActionButton({
  icon,
  label,
  onClick,
  variant,
  disabled = false,
}: {
  icon: React.ReactNode;
  label: string;
  onClick?: () => void;
  variant: "default" | "success" | "danger" | "info";
  disabled?: boolean;
}) {
  const variants = {
    default: "bg-white/5 hover:bg-white/15 text-white/60 hover:text-white",
    success: "bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-400",
    danger: "bg-rose-500/20 hover:bg-rose-500/30 text-rose-400",
    info: "bg-blue-500/20 hover:bg-blue-500/30 text-blue-400",
  };

  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`
        p-2 rounded-xl backdrop-blur-md transition-all
        min-w-[40px] min-h-[40px] flex items-center justify-center
        focus:outline-none focus:ring-2 focus:ring-white/30
        touch-manipulation
        ${variants[variant]}
        ${disabled ? "opacity-30 cursor-not-allowed" : ""}
      `}
      title={label}
      aria-label={label}
    >
      {icon}
    </button>
  );
}

// ActionsCell - Contenedor de acciones siempre visible
function ActionsCell({
  movement,
  permissions,
  onView,
  onEdit,
  onArchive,
  onApprove,
  onReject,
}: {
  movement: WasteMovement;
  permissions: UserPermissions;
  onView?: (m: WasteMovement) => void;
  onEdit?: (m: WasteMovement) => void;
  onArchive?: (id: number) => void;
  onApprove?: (id: number) => void;
  onReject?: (id: number, reason: string) => void;
}) {
  const [rejectModal, setRejectModal] = useState<boolean>(false);
  const [rejectReason, setRejectReason] = useState("");
  const isInReview = movement.status === "in_review";
  const canModify = !movement.is_immutable;

  const handleRejectConfirm = () => {
    if (rejectReason.trim()) {
      onReject?.(movement.id, rejectReason);
      setRejectModal(false);
      setRejectReason("");
    }
  };

  return (
    <>
      <div className="flex items-center gap-1 flex-wrap">
        {/* View - Siempre visible */}
        <ActionButton
          icon={
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
            </svg>
          }
          label="Ver detalles"
          onClick={() => onView?.(movement)}
          variant="default"
        />

        {/* Approve - Solo para in_review y canReview */}
        {permissions.canReview && isInReview && (
          <ActionButton
            icon={
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            }
            label="Aprobar"
            onClick={() => onApprove?.(movement.id)}
            variant="success"
          />
        )}

        {/* Reject - Solo para in_review y canReview */}
        {permissions.canReview && isInReview && (
          <ActionButton
            icon={
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            }
            label="Rechazar"
            onClick={() => setRejectModal(true)}
            variant="danger"
          />
        )}

        {/* Edit - Solo si puede editar y no es inmutable */}
        {permissions.canEdit && canModify && (
          <ActionButton
            icon={
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
              </svg>
            }
            label="Editar"
            onClick={() => onEdit?.(movement)}
            variant="info"
          />
        )}

        {/* Archive - Solo si puede archivar y no es inmutable */}
        {permissions.canArchive && canModify && (
          <ActionButton
            icon={
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4" />
              </svg>
            }
            label="Archivar"
            onClick={() => onArchive?.(movement.id)}
            variant="default"
          />
        )}
      </div>

      {/* Reject Modal */}
      {rejectModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div 
            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            onClick={() => setRejectModal(false)}
          />
          <div className="relative bg-slate-800/95 backdrop-blur-xl border border-white/10 rounded-3xl p-8 max-w-md w-full shadow-2xl">
            <h3 className="text-xl font-bold text-white mb-4">Rechazar movimiento</h3>
            <p className="text-white/60 mb-6">Ingresa la razón del rechazo:</p>
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
                onClick={() => setRejectModal(false)}
                className="flex-1 px-6 py-3 rounded-xl bg-white/10 text-white/70 hover:bg-white/20 transition-colors"
              >
                Cancelar
              </button>
              <button
                onClick={handleRejectConfirm}
                disabled={!rejectReason.trim()}
                className="flex-1 px-6 py-3 rounded-xl bg-rose-500 text-white font-semibold hover:bg-rose-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Rechazar
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

export function MovementsTable({ 
  movements, 
  loading = false, 
  permissions,
  onRefresh,
  onApprove,
  onReject,
  onView,
  onEdit,
  onArchive,
}: MovementsTableProps) {
  if (loading) {
    return (
      <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-3xl overflow-hidden shadow-2xl">
        <div className="overflow-x-auto max-h-[600px]">
          <table className="w-full">
            <thead className="bg-white/5 sticky top-0 backdrop-blur-md border-b border-white/10">
              <tr className="text-white/40 text-xs uppercase tracking-widest">
                <th className="px-4 py-4 text-left font-semibold">ID</th>
                <th className="px-4 py-4 text-left font-semibold">Generador</th>
                <th className="px-4 py-4 text-left font-semibold">Tipo</th>
                <th className="px-4 py-4 text-left font-semibold">Fecha</th>
                <th className="px-4 py-4 text-left font-semibold">Estado</th>
                <th className="px-4 py-4 text-left font-semibold">Confianza</th>
                <th className="px-4 py-4 text-left font-semibold">Acciones</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {[...Array(5)].map((_, i) => <SkeletonRow key={i} />)}
            </tbody>
          </table>
        </div>
      </div>
    );
  }

  if (movements.length === 0) {
    return (
      <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-3xl p-16 text-center shadow-2xl">
        <div className="w-24 h-24 mx-auto mb-6 rounded-3xl bg-gradient-to-br from-white/10 to-white/5 flex items-center justify-center backdrop-blur-md border border-white/10">
          <span className="text-5xl">📋</span>
        </div>
        <h3 className="text-2xl font-bold text-white mb-3">Sin movimientos</h3>
        <p className="text-white/50 mb-8 max-w-md mx-auto">
          No hay movimientos de residuos registrados. Comienza agregando tu primer movimiento.
        </p>
        {permissions.canEdit && (
          <button className="px-8 py-4 rounded-2xl bg-gradient-to-r from-emerald-500 to-teal-500 text-white font-bold shadow-lg shadow-emerald-500/30 hover:shadow-emerald-500/50 transition-all">
            + Agregar movimiento
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-3xl overflow-hidden shadow-2xl">
      {/* Sticky Header */}
      <div className="bg-white/5 backdrop-blur-md border-b border-white/10">
        <div className="flex justify-between items-center px-6 py-4">
          <h3 className="text-lg font-semibold text-white">Movimientos de residuos</h3>
          <div className="flex items-center gap-4">
            <span className="px-3 py-1 rounded-full bg-white/10 backdrop-blur-md text-sm text-white/60">
              {movements.length} registros
            </span>
            <button 
              onClick={onRefresh}
              className="p-2 rounded-xl bg-white/10 hover:bg-white/20 backdrop-blur-md transition-colors"
              aria-label="Actualizar"
            >
              <svg className="w-4 h-4 text-white/60" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            </button>
          </div>
        </div>
      </div>

      {/* Scrollable Table */}
      <div className="overflow-x-auto max-h-[600px] overflow-y-auto">
        <table className="w-full">
          <thead className="bg-white/5 sticky top-0 backdrop-blur-md border-b border-white/10 z-10">
            <tr className="text-white/40 text-xs uppercase tracking-widest">
              <th className="px-4 py-4 text-left font-semibold">ID</th>
              <th className="px-4 py-4 text-left font-semibold">Generador</th>
              <th className="px-4 py-4 text-left font-semibold">Tipo Residuo</th>
              <th className="px-4 py-4 text-left font-semibold">Fecha</th>
              <th className="px-4 py-4 text-left font-semibold">Estado</th>
              <th className="px-4 py-4 text-left font-semibold">Confianza</th>
              <th className="px-4 py-4 text-left font-semibold min-w-[180px]">Acciones</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            {movements.map((movement) => (
              <tr 
                key={movement.id} 
                className="hover:bg-white/5 transition-colors duration-200"
              >
                {/* ID */}
                <td className="px-4 py-5">
                  <span className="text-white font-mono font-semibold">#{movement.id}</span>
                  <div className="text-xs text-white/40 mt-0.5">{movement.manifest_number}</div>
                </td>

                {/* Generator */}
                <td className="px-4 py-5">
                  <div className="text-white font-medium">{movement.generator_name}</div>
                  <div className="text-xs text-white/40">{movement.transporter_name}</div>
                </td>

                {/* Waste Type */}
                <td className="px-4 py-5">
                  <span className="text-white/70">{movement.waste_type}</span>
                  <div className="text-xs text-white/40 mt-0.5">
                    {movement.quantity} {movement.unit}
                  </div>
                </td>

                {/* Date */}
                <td className="px-4 py-5">
                  <span className="text-white/70">
                    {new Date(movement.date).toLocaleDateString("es-MX")}
                  </span>
                </td>

                {/* Status */}
                <td className="px-4 py-5">
                  <StatusBadge status={movement.status} />
                </td>

                {/* Confidence */}
                <td className="px-4 py-5">
                  <ConfidenceBar 
                    score={movement.confidence_score ?? 85} 
                    size="sm"
                  />
                </td>

                {/* Actions - SIEMPRE VISIBLES */}
                <td className="px-4 py-5">
                  <ActionsCell
                    movement={movement}
                    permissions={permissions}
                    onView={onView}
                    onEdit={onEdit}
                    onArchive={onArchive}
                    onApprove={onApprove}
                    onReject={onReject}
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
