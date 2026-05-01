// 8A MOBILE BRIDGE - Status Badge Component
// Glassmorphism status indicators

import { useState, useEffect, useRef } from "react";
import { BridgeWSState } from "@/lib/bridge-api";

// QR Code generator using canvas (no external dependency)
function generateQRCanvas(data: string, size: number = 200): string {
  // Simple QR code encoding using canvas
  const canvas = typeof document !== "undefined" ? document.createElement("canvas") : null;
  if (!canvas) return "";
  
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext("2d");
  if (!ctx) return "";
  
  // Simple visual representation (not a real QR encoder)
  // For production, use a proper library
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, size, size);
  ctx.fillStyle = "#000000";
  
  // Draw a simple pattern based on hash of the string
  const cellSize = Math.floor(size / 21);
  const hash = data.split("").reduce((a, c) => a + c.charCodeAt(0), 0);
  
  for (let y = 0; y < 21; y++) {
    for (let x = 0; x < 21; x++) {
      // Position patterns (corners)
      const isCorner = (
        (x < 7 && y < 7) ||
        (x > 13 && y < 7) ||
        (x < 7 && y > 13)
      );
      if (isCorner) {
        // Corner squares
        const innerSize = 5;
        if (x >= 1 && x <= innerSize && y >= 1 && y <= innerSize) {
          if ((x + y) % 2 === 0) {
            ctx.fillRect(x * cellSize, y * cellSize, cellSize, cellSize);
          }
        }
        if (x > 13 && x <= 19 && y >= 1 && y <= innerSize) {
          if ((x + y) % 2 === 0) {
            ctx.fillRect(x * cellSize, y * cellSize, cellSize, cellSize);
          }
        }
        if (x >= 1 && x <= innerSize && y > 13 && y <= 19) {
          if ((x + y) % 2 === 0) {
            ctx.fillRect(x * cellSize, y * cellSize, cellSize, cellSize);
          }
        }
      } else {
        // Data area - pseudo-random based on hash
        const shouldFill = ((hash * (x + 1) * (y + 1)) % 3) === 0;
        if (shouldFill) {
          ctx.fillRect(x * cellSize, y * cellSize, cellSize, cellSize);
        }
      }
    }
  }
  
  return canvas.toDataURL("image/png");
}

interface BridgeStatusBadgeProps {
  state: BridgeWSState;
  scannedCount?: number;
  size?: "sm" | "md" | "lg";
}

const sizeClasses = {
  sm: "px-2 py-1 text-xs",
  md: "px-3 py-1.5 text-sm",
  lg: "px-4 py-2 text-base",
};

const statusConfig: Record<BridgeWSState, { label: string; bg: string; text: string; border: string; icon: string }> = {
  connecting: {
    label: "Conectando",
    bg: "bg-blue-400/20",
    text: "text-blue-300",
    border: "border-blue-400/30",
    icon: "animate-spin",
  },
  connected: {
    label: "Conectado",
    bg: "bg-emerald-400/20",
    text: "text-emerald-300",
    border: "border-emerald-400/30",
    icon: "",
  },
  syncing: {
    label: "Sincronizando",
    bg: "bg-amber-400/20",
    text: "text-amber-300",
    border: "border-amber-400/30",
    icon: "animate-pulse",
  },
  offline: {
    label: "Offline",
    bg: "bg-white/10",
    text: "text-white/70",
    border: "border-white/20",
    icon: "",
  },
  expired: {
    label: "Expirado",
    bg: "bg-rose-400/20",
    text: "text-rose-300",
    border: "border-rose-400/30",
    icon: "",
  },
  error: {
    label: "Error",
    bg: "bg-rose-400/20",
    text: "text-rose-300",
    border: "border-rose-400/30",
    icon: "",
  },
};

export function BridgeStatusBadge({ state, scannedCount, size = "md" }: BridgeStatusBadgeProps) {
  const config = statusConfig[state];
  
  return (
    <span
      className={`
        inline-flex items-center gap-2 rounded-full font-semibold border backdrop-blur-md
        shadow-lg ${config.bg} ${config.text} ${config.border}
        ${sizeClasses[size]}
      `}
    >
      {/* Status dot */}
      <span className={`relative flex h-2 w-2`}>
        <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${config.text.replace('text-', 'bg-')}`} />
        <span className={`relative inline-flex rounded-full h-2 w-2 ${config.text.replace('text-', 'bg-')}`} />
      </span>
      
      {config.label}
      
      {/* Scan count */}
      {scannedCount !== undefined && state === "connected" && (
        <span className="ml-1 px-1.5 py-0.5 rounded-full bg-white/10 text-xs">
          {scannedCount} escaneados
        </span>
      )}
    </span>
  );
}

interface BridgeStatusBarProps {
  state: BridgeWSState;
  scannedCount?: number;
  qrToken?: string;
  expiresAt?: string;
  onGenerateQR?: () => void;
  onManualEntry?: () => void;
  onSync?: () => void;
  onDisconnect?: () => void;
}

export function BridgeStatusBar({
  state,
  scannedCount,
  qrToken,
  expiresAt,
  onGenerateQR,
  onManualEntry,
  onSync,
  onDisconnect,
}: BridgeStatusBarProps) {
  const isConnected = state === "connected";
  const isExpired = state === "expired";
  
  return (
    <div className="space-y-4">
      {/* Main status */}
      <div className="flex items-center justify-between">
        <BridgeStatusBadge state={state} scannedCount={scannedCount} size="md" />
        
        {qrToken && (
          <div className="flex items-center gap-2">
            <span className="text-xs text-white/40">Token:</span>
            <code className="px-2 py-1 rounded bg-white/5 border border-white/10 text-white/80 font-mono text-xs">
              {qrToken.slice(0, 8)}...
            </code>
          </div>
        )}
      </div>
      
      {/* QR Code display when connected */}
      {isConnected && qrToken && (
        <div className="p-4 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-md">
          <div className="text-center">
            <p className="text-xs text-white/40 mb-2">Código para app móvil</p>
            <div className="inline-block p-3 rounded-xl bg-white">
              <img 
                src={generateQRCanvas(qrToken, 160)} 
                alt="QR Code" 
                className="w-40 h-40"
              />
            </div>
            <p className="mt-2 text-xs text-white/60">
              Escanea con la app móvil PRANELY
            </p>
          </div>
        </div>
      )}
      
      {/* Expiry countdown */}
      {expiresAt && !isExpired && (
        <div className="flex items-center justify-between text-xs text-white/40">
          <span>Expira:</span>
          <ExpiryCountdown expiresAt={expiresAt} />
        </div>
      )}
      
      {/* Action buttons */}
      <div className="flex gap-3">
        {!isConnected && !isExpired && (
          <>
            <button
              onClick={onGenerateQR}
              className="flex-1 px-4 py-3 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-500 text-white font-semibold shadow-lg shadow-emerald-500/30 hover:shadow-emerald-500/50 transition-all flex items-center justify-center gap-2"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v1m6 11h2m-6 0h-2v4m0-11v3m0 0h.01M12 12h4.01M16 20h4M4 12h4m12 0h.01M5 8h2a1 1 0 001-1V5a1 1 0 00-1-1H5a1 1 0 00-1 1v2a1 1 0 001 1zm12 0h2a1 1 0 001-1V5a1 1 0 00-1-1h-2a1 1 0 00-1 1v2a1 1 0 001 1zM5 20h2a1 1 0 001-1v-2a1 1 0 00-1-1H5a1 1 0 00-1 1v2a1 1 0 001 1z" />
              </svg>
              Generar QR
            </button>
            
            <button
              onClick={onManualEntry}
              className="flex-1 px-4 py-3 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-white/80 font-medium transition-all flex items-center justify-center gap-2"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
              </svg>
              Manual
            </button>
          </>
        )}
        
        {isConnected && (
          <>
            <button
              onClick={onSync}
              className="flex-1 px-4 py-3 rounded-xl bg-amber-500/20 hover:bg-amber-500/30 border border-amber-500/30 text-amber-300 font-medium transition-all flex items-center justify-center gap-2"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              Sincronizar
            </button>
            
            <button
              onClick={onDisconnect}
              className="px-4 py-3 rounded-xl bg-rose-500/20 hover:bg-rose-500/30 border border-rose-500/30 text-rose-300 font-medium transition-all"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
              </svg>
            </button>
          </>
        )}
        
        {isExpired && (
          <button
            onClick={onGenerateQR}
            className="flex-1 px-4 py-3 rounded-xl bg-gradient-to-r from-amber-500 to-orange-500 text-white font-semibold shadow-lg shadow-amber-500/30 hover:shadow-amber-500/50 transition-all flex items-center justify-center gap-2"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            Nueva Sesión
          </button>
        )}
      </div>
    </div>
  );
}

// Countdown timer component
function ExpiryCountdown({ expiresAt }: { expiresAt: string }) {
  const [timeLeft, setTimeLeft] = useState("");
  
  useEffect(() => {
    const update = () => {
      const expires = new Date(expiresAt).getTime();
      const now = Date.now();
      const diff = Math.max(0, expires - now);
      
      const minutes = Math.floor(diff / 60000);
      const seconds = Math.floor((diff % 60000) / 1000);
      
      setTimeLeft(`${minutes}:${seconds.toString().padStart(2, "0")}`);
    };
    
    update();
    const interval = setInterval(update, 1000);
    return () => clearInterval(interval);
  }, [expiresAt]);
  
  return <span className="font-mono">{timeLeft}</span>;
}
