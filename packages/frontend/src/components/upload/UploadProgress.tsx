// UploadProgress - Glassmorphism progress bars with states
"use client";

import { useState, useEffect, useCallback } from "react";

export type UploadStatus = "idle" | "uploading" | "queued" | "processing" | "completed" | "error";

interface UploadFile {
  id: string;
  name: string;
  size: number;
  status: UploadStatus;
  progress: number;
  error?: string;
  jobId?: string;
  result?: {
    confidence: number;
    manifestNumber: string;
  };
}

interface UploadProgressProps {
  files: UploadFile[];
  onCancel: (id: string) => void;
  onRetry: (id: string) => void;
  onRemove: (id: string) => void;
}

// Status configuration
const STATUS_CONFIG = {
  idle: {
    label: "Esperando",
    color: "white",
    bgColor: "bg-white/5",
    borderColor: "border-white/10",
    icon: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
  },
  uploading: {
    label: "Subiendo",
    color: "blue",
    bgColor: "bg-blue-500/10",
    borderColor: "border-blue-500/30",
    icon: (
      <svg className="w-4 h-4 animate-bounce" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
      </svg>
    ),
  },
  queued: {
    label: "En cola RQ",
    color: "amber",
    bgColor: "bg-amber-500/10",
    borderColor: "border-amber-500/30",
    icon: (
      <svg className="w-4 h-4 animate-pulse" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
      </svg>
    ),
  },
  processing: {
    label: "IA procesando",
    color: "emerald",
    bgColor: "bg-emerald-500/10",
    borderColor: "border-emerald-500/30",
    icon: (
      <div className="relative">
        <div className="w-4 h-4 border-2 border-emerald-500/30 border-t-emerald-500 rounded-full animate-spin" />
      </div>
    ),
  },
  completed: {
    label: "Completado",
    color: "emerald",
    bgColor: "bg-emerald-500/10",
    borderColor: "border-emerald-500/30",
    icon: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
      </svg>
    ),
  },
  error: {
    label: "Error",
    color: "rose",
    bgColor: "bg-rose-500/10",
    borderColor: "border-rose-500/30",
    icon: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
      </svg>
    ),
  },
};

function formatFileSize(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
}

export function UploadProgress({ files, onCancel, onRetry, onRemove }: UploadProgressProps) {
  if (files.length === 0) return null;

  return (
    <div className="space-y-3">
      {files.map((file) => {
        const config = STATUS_CONFIG[file.status];
        
        return (
          <div
            key={file.id}
            className={`
              relative p-4 rounded-2xl backdrop-blur-md
              ${config.bgColor} ${config.borderColor}
              border transition-all duration-300
              ${file.status === "processing" ? "shadow-lg shadow-emerald-500/10" : ""}
            `}
          >
            {/* Header */}
            <div className="flex items-start gap-3">
              {/* File Icon */}
              <div className={`
                p-2 rounded-xl
                ${file.status === "completed" ? "bg-emerald-500/20" : ""}
                ${file.status === "error" ? "bg-rose-500/20" : ""}
                ${file.status === "processing" ? "bg-emerald-500/20" : ""}
                ${file.status === "uploading" ? "bg-blue-500/20" : ""}
                ${file.status === "queued" ? "bg-amber-500/20" : ""}
                ${file.status === "idle" ? "bg-white/10" : ""}
              `}>
                <svg className={`w-5 h-5 text-${config.color}-400`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>

              {/* File Info */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between gap-2 mb-1">
                  <p className="text-sm font-medium text-white truncate" title={file.name}>
                    {file.name}
                  </p>
                  <span className={`text-xs text-${config.color}-400 flex items-center gap-1 shrink-0`}>
                    {config.icon}
                    {config.label}
                  </span>
                </div>
                
                <p className="text-xs text-white/40 mb-3">
                  {formatFileSize(file.size)}
                  {file.jobId && (
                    <span className="ml-2 text-white/30">• Job: {file.jobId.slice(0, 8)}...</span>
                  )}
                </p>

                {/* Progress Bar */}
                {(file.status === "uploading" || file.status === "processing" || file.status === "queued") && (
                  <div className="space-y-1">
                    <div className="h-1.5 bg-white/5 rounded-full overflow-hidden">
                      <div
                        className={`
                          h-full rounded-full transition-all duration-300
                          ${file.status === "uploading" ? "bg-blue-500" : ""}
                          ${file.status === "queued" ? "bg-amber-500" : ""}
                          ${file.status === "processing" ? "bg-gradient-to-r from-emerald-500 to-teal-500 animate-pulse" : ""}
                        `}
                        style={{ width: `${file.progress}%` }}
                      />
                    </div>
                    <p className="text-xs text-white/30 text-right">
                      {file.progress}%
                      {file.status === "queued" && " • Esperando worker"}
                      {file.status === "processing" && " • Extrayendo datos NOM-052..."}
                    </p>
                  </div>
                )}

                {/* Result Summary */}
                {file.status === "completed" && file.result && (
                  <div className="flex items-center gap-4 p-2 bg-emerald-500/10 rounded-xl">
                    <div className="flex items-center gap-2">
                      <svg className="w-4 h-4 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      <span className="text-xs text-emerald-300">
                        Confianza: {Math.round(file.result.confidence * 100)}%
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-white/50">Manifiesto:</span>
                      <span className="text-xs font-mono text-white/70">{file.result.manifestNumber}</span>
                    </div>
                  </div>
                )}

                {/* Error Message */}
                {file.status === "error" && file.error && (
                  <div className="p-2 bg-rose-500/10 rounded-xl text-xs text-rose-300">
                    {file.error}
                  </div>
                )}
              </div>

              {/* Actions */}
              <div className="flex items-center gap-1 shrink-0">
                {file.status === "error" && (
                  <button
                    onClick={() => onRetry(file.id)}
                    className="p-2 rounded-xl bg-white/5 hover:bg-white/10 text-white/60 hover:text-white transition-colors"
                    title="Reintentar"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                  </button>
                )}
                
                {(file.status === "uploading" || file.status === "queued") && (
                  <button
                    onClick={() => onCancel(file.id)}
                    className="p-2 rounded-xl bg-white/5 hover:bg-rose-500/20 text-white/60 hover:text-rose-400 transition-colors"
                    title="Cancelar"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                )}
                
                {file.status === "completed" && (
                  <button
                    onClick={() => onRemove(file.id)}
                    className="p-2 rounded-xl bg-white/5 hover:bg-white/10 text-white/60 hover:text-white transition-colors"
                    title="Eliminar"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                )}
              </div>
            </div>

            {/* Processing Step Indicator */}
            {file.status === "processing" && (
              <div className="mt-4 pt-4 border-t border-white/5">
                <div className="flex items-center justify-between text-xs">
                  <div className="flex items-center gap-4">
                    {/* Step 1: Upload */}
                    <div className="flex items-center gap-2">
                      <div className="w-6 h-6 rounded-full bg-emerald-500/20 flex items-center justify-center">
                        <svg className="w-3 h-3 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                      </div>
                      <span className="text-emerald-400">Subido</span>
                    </div>
                    
                    {/* Arrow */}
                    <svg className="w-4 h-4 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                    </svg>
                    
                    {/* Step 2: Queue */}
                    <div className="flex items-center gap-2">
                      <div className="w-6 h-6 rounded-full bg-emerald-500/20 flex items-center justify-center">
                        <svg className="w-3 h-3 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                      </div>
                      <span className="text-emerald-400">Cola RQ</span>
                    </div>
                    
                    {/* Arrow */}
                    <svg className="w-4 h-4 text-emerald-400 animate-pulse" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                    </svg>
                    
                    {/* Step 3: AI Processing */}
                    <div className="flex items-center gap-2">
                      <div className="w-6 h-6 rounded-full bg-emerald-500/30 border border-emerald-500/50 flex items-center justify-center">
                        <div className="w-3 h-3 border border-emerald-400 border-t-transparent rounded-full animate-spin" />
                      </div>
                      <span className="text-emerald-300 font-medium">DeepInfra IA</span>
                    </div>
                  </div>
                  
                  {/* NOM-052 badge */}
                  <div className="px-3 py-1 bg-emerald-500/10 rounded-full border border-emerald-500/20">
                    <span className="text-xs text-emerald-400 font-medium">NOM-052-SEMARNAT</span>
                  </div>
                </div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

export default UploadProgress;
