// FAB - Floating Action Button glassmorphism
"use client";

import { useState } from "react";

interface FABProps {
  onAddMovement?: () => void;
  onUploadDocument?: () => void;
  canCreate?: boolean;
}

export function FAB({ onAddMovement, onUploadDocument, canCreate = true }: FABProps) {
  const [expanded, setExpanded] = useState(false);

  if (!canCreate) return null;

  return (
    <div className="fixed bottom-8 right-8 z-40 flex flex-col items-end gap-4">
      {/* Expanded Actions */}
      <div 
        className={`
          flex flex-col gap-3 transition-all duration-300 origin-bottom-right
          ${expanded ? "opacity-100 scale-100" : "opacity-0 scale-90 pointer-events-none"}
        `}
      >
        <button
          onClick={() => {
            onUploadDocument?.();
            setExpanded(false);
          }}
          className="group flex items-center gap-3 px-5 py-3 rounded-2xl bg-white/10 backdrop-blur-xl border border-white/20 shadow-lg hover:bg-white/20 transition-all"
        >
          <div className="w-10 h-10 rounded-xl bg-blue-500/20 flex items-center justify-center">
            <svg className="w-5 h-5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
          </div>
          <span className="text-white font-medium whitespace-nowrap">Subir documento</span>
          <span className="w-6 h-6 rounded-full bg-white/10 flex items-center justify-center text-xs text-white/60 opacity-0 group-hover:opacity-100 transition-opacity">
            2
          </span>
        </button>

        <button
          onClick={() => {
            onAddMovement?.();
            setExpanded(false);
          }}
          className="group flex items-center gap-3 px-5 py-3 rounded-2xl bg-white/10 backdrop-blur-xl border border-white/20 shadow-lg hover:bg-white/20 transition-all"
        >
          <div className="w-10 h-10 rounded-xl bg-emerald-500/20 flex items-center justify-center">
            <svg className="w-5 h-5 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          <span className="text-white font-medium whitespace-nowrap">Nuevo movimiento</span>
          <span className="w-6 h-6 rounded-full bg-white/10 flex items-center justify-center text-xs text-white/60 opacity-0 group-hover:opacity-100 transition-opacity">
            1
          </span>
        </button>
      </div>

      {/* Main FAB */}
      <button
        onClick={() => setExpanded(!expanded)}
        className={`
          relative w-16 h-16 rounded-2xl
          bg-gradient-to-br from-emerald-500 to-teal-600
          shadow-2xl shadow-emerald-500/40
          flex items-center justify-center
          transition-all duration-300
          hover:shadow-emerald-500/60 hover:scale-110
          active:scale-95
          ${expanded ? "rotate-45" : "rotate-0"}
        `}
      >
        {/* Glow effect */}
        <div className="absolute inset-0 rounded-2xl bg-gradient-to-br from-emerald-400 to-teal-500 blur-xl opacity-50" />
        
        {/* Icon */}
        <svg 
          className="w-7 h-7 text-white relative z-10 transition-transform duration-300" 
          fill="none" 
          stroke="currentColor" 
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M12 4v16m8-8H4" />
        </svg>

        {/* Pulse ring when not expanded */}
        {!expanded && (
          <span className="absolute inset-0 rounded-2xl border-2 border-emerald-400/50 animate-ping" />
        )}
      </button>

      {/* Tooltip when collapsed */}
      {!expanded && (
        <div className="absolute right-20 top-1/2 -translate-y-1/2 px-3 py-1.5 bg-slate-800/90 backdrop-blur-md border border-white/10 rounded-lg text-sm text-white whitespace-nowrap opacity-0 hover:opacity-100 transition-opacity pointer-events-none">
          Agregar movimiento
        </div>
      )}
    </div>
  );
}
