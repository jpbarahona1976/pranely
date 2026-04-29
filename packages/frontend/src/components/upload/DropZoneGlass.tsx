// DropZoneGlass - Glassmorphism drag & drop zone for PDF files
"use client";

import { useState, useCallback, useRef, type DragEvent, type ChangeEvent } from "react";

interface DropZoneGlassProps {
  onFilesSelected: (files: File[]) => void;
  accept?: string;
  disabled?: boolean;
  maxSizeMB?: number;
}

export function DropZoneGlass({
  onFilesSelected,
  accept = ".pdf",
  disabled = false,
  maxSizeMB = 10,
}: DropZoneGlassProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [isHovering, setIsHovering] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDragEnter = useCallback((e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    if (!disabled) setIsDragging(true);
  }, [disabled]);

  const handleDragLeave = useCallback((e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.currentTarget.contains(e.relatedTarget as Node)) return;
    setIsDragging(false);
  }, []);

  const handleDragOver = useCallback((e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDrop = useCallback((e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    if (disabled) return;

    const files = Array.from(e.dataTransfer.files).filter(file => 
      file.type === "application/pdf" || file.name.endsWith(".pdf")
    );

    if (files.length > 0) {
      onFilesSelected(files);
    }
  }, [disabled, onFilesSelected]);

  const handleFileSelect = useCallback((e: ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []).filter(file => 
      file.type === "application/pdf" || file.name.endsWith(".pdf")
    );

    if (files.length > 0) {
      onFilesSelected(files);
    }

    // Reset input
    if (inputRef.current) {
      inputRef.current.value = "";
    }
  }, [onFilesSelected]);

  const handleClick = () => {
    if (!disabled && inputRef.current) {
      inputRef.current.click();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      handleClick();
    }
  };

  return (
    <div
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      onDragEnter={handleDragEnter}
      onDragLeave={handleDragLeave}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
      onMouseEnter={() => !disabled && setIsHovering(true)}
      onMouseLeave={() => setIsHovering(false)}
      tabIndex={disabled ? -1 : 0}
      role="button"
      aria-label="Arrastra archivos PDF aquí o haz clic para seleccionar"
      className={`
        relative w-full p-8 md:p-12 rounded-3xl
        border-2 border-dashed cursor-pointer
        transition-all duration-300 ease-out
        focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:ring-offset-2 focus:ring-offset-slate-900
        
        ${disabled ? `
          bg-white/5 border-white/10 cursor-not-allowed opacity-50
        ` : isDragging ? `
          bg-emerald-500/20 border-emerald-500/50 
          scale-[1.02] shadow-lg shadow-emerald-500/20
        ` : isHovering ? `
          bg-white/10 border-white/20 
          scale-[1.01] shadow-lg shadow-white/5
        ` : `
          bg-white/5 border-white/10 
          hover:bg-white/8 hover:border-white/15
        `}
      `}
    >
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        multiple
        onChange={handleFileSelect}
        disabled={disabled}
        className="hidden"
        aria-hidden="true"
      />

      {/* Animated border effect on drag */}
      {isDragging && (
        <div className="absolute inset-0 rounded-3xl overflow-hidden pointer-events-none">
          <div className="absolute inset-0 bg-gradient-to-r from-emerald-500/0 via-emerald-500/30 to-emerald-500/0 animate-pulse" />
        </div>
      )}

      <div className="flex flex-col items-center justify-center text-center gap-4">
        {/* Icon */}
        <div className={`
          relative p-4 rounded-2xl transition-all duration-300
          ${isDragging 
            ? "bg-emerald-500/20 scale-110" 
            : "bg-white/5 group-hover:bg-white/10"
          }
        `}>
          {/* PDF Icon */}
          <svg 
            className={`
              w-12 h-12 md:w-16 md:h-16 transition-all duration-300
              ${isDragging ? "text-emerald-400" : "text-white/60 group-hover:text-white/80"}
            `} 
            fill="none" 
            stroke="currentColor" 
            viewBox="0 0 24 24"
          >
            <path 
              strokeLinecap="round" 
              strokeLinejoin="round" 
              strokeWidth={1.5} 
              d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" 
            />
            <path 
              strokeLinecap="round" 
              strokeLinejoin="round" 
              strokeWidth={1.5} 
              d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" 
            />
            <path 
              strokeLinecap="round" 
              strokeLinejoin="round" 
              strokeWidth={1.5} 
              d="M14 2v6h6" 
            />
          </svg>
          
          {/* Animated plus on drag */}
          {isDragging && (
            <div className="absolute -top-2 -right-2 w-8 h-8 bg-emerald-500 rounded-full flex items-center justify-center animate-bounce">
              <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
            </div>
          )}
        </div>

        {/* Text */}
        <div className="space-y-2">
          <p className={`
            text-lg md:text-xl font-semibold transition-colors duration-300
            ${isDragging ? "text-emerald-300" : "text-white/80"}
          `}>
            {isDragging 
              ? "¡Suelta el archivo aquí!" 
              : "Arrastra archivos PDF aquí"
            }
          </p>
          <p className="text-sm text-white/40">
            o haz clic para seleccionar archivos
          </p>
        </div>

        {/* File info */}
        <div className={`
          flex items-center gap-2 px-4 py-2 rounded-xl text-xs
          transition-all duration-300
          ${isDragging 
            ? "bg-emerald-500/20 text-emerald-300" 
            : "bg-white/5 text-white/40"
          }
        `}>
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span>Solo archivos PDF • Máx. {maxSizeMB}MB por archivo</span>
        </div>
      </div>
    </div>
  );
}

export default DropZoneGlass;
