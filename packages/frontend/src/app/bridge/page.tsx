// 8A MOBILE BRIDGE - Bridge Page
// Mobile-first bridge interface with QR scanner and WebSocket sync
"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { QRScanner, BridgeStatusBadge, BridgeStatusBar } from "@/components/bridge";
import {
  createBridgeSession,
  getBridgeStatus,
  extendBridgeSession,
  closeBridgeSession,
  BridgeWSClient,
  BridgeWSState,
  getOfflineQueue,
  addToOfflineQueue,
  clearOfflineQueue,
  type BridgeSession,
} from "@/lib/bridge-api";

// Register Service Worker on mount
if (typeof window !== "undefined" && "serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/sw-bridge.js").catch(() => {
      // SW registration optional - ignore errors
    });
  });
}

type ViewMode = "idle" | "scan" | "manual" | "connected";

function BridgeContent() {
  const router = useRouter();
  const { user, organization, token, logout, permissions } = useAuth();
  const wsClientRef = useRef<BridgeWSClient | null>(null);
  
  // State
  const [viewMode, setViewMode] = useState<ViewMode>("idle");
  const [session, setSession] = useState<BridgeSession | null>(null);
  const [wsState, setWsState] = useState<BridgeWSState>("offline");
  const [scannedCount, setScannedCount] = useState(0);
  const [lastScan, setLastScan] = useState<string | null>(null);
  const [manualToken, setManualToken] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [offlineQueueCount, setOfflineQueueCount] = useState(0);

  // Check offline queue on mount
  useEffect(() => {
    const queue = getOfflineQueue();
    setOfflineQueueCount(queue.length);
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (wsClientRef.current) {
        wsClientRef.current.disconnect();
      }
    };
  }, []);

  // WS state listener
  useEffect(() => {
    if (!wsClientRef.current) return;

    const unsubscribe = wsClientRef.current.on("state", (state: BridgeWSState) => {
      setWsState(state);
    });

    return unsubscribe;
  }, []);

  // Scan listener
  useEffect(() => {
    if (!wsClientRef.current) return;

    const unsubscribe = wsClientRef.current.on("scan_ack", () => {
      setScannedCount(wsClientRef.current?.getScannedCount() || 0);
    });

    return unsubscribe;
  }, []);

  const handleCreateSession = useCallback(async () => {
    if (!token) return;
    
    setIsLoading(true);
    setError(null);
    
    try {
      const newSession = await createBridgeSession(token);
      setSession(newSession);
      
      // Connect WebSocket
      const wsClient = new BridgeWSClient(newSession.ws_url, newSession.ws_token);
      wsClientRef.current = wsClient;
      
      await wsClient.connect();
      setViewMode("connected");
    } catch (e: any) {
      setError(e.message || "Error al crear sesión");
    } finally {
      setIsLoading(false);
    }
  }, [token]);

  const handleManualEntry = useCallback(async () => {
    if (!token || !manualToken.trim()) return;
    
    setIsLoading(true);
    setError(null);
    
    try {
      const status = await getBridgeStatus(manualToken.trim(), token);
      
      if (status.is_expired) {
        setError("Sesión expirada. Genera una nueva.");
        return;
      }
      
      // For manual entry, we just validate the session exists
      // In a real app, we'd also connect to the WS
      setLastScan(`Sesión validada: ${status.session_id}`);
      setScannedCount(status.scanned_count);
      setViewMode("connected");
    } catch (e: any) {
      if (e.message?.includes("404")) {
        setError("Sesión no encontrada");
      } else {
        setError(e.message || "Error al validar sesión");
      }
    } finally {
      setIsLoading(false);
    }
  }, [token, manualToken]);

  const handleQRScan = useCallback(async (data: string) => {
    setLastScan(data);
    
    // Check if it's a bridge QR token
    if (data.length === 16 && /^[A-Z0-9]+$/.test(data)) {
      // This looks like a bridge token - validate it
      if (token) {
        try {
          await getBridgeStatus(data, token);
          addToOfflineQueue(data);
          setOfflineQueueCount(getOfflineQueue().length);
          setLastScan("Token añadido a cola offline");
        } catch (e) {
          setLastScan("Token no válido para este usuario");
        }
      }
    } else if (wsClientRef.current?.getState() === "connected") {
      // Send scan to WS
      wsClientRef.current.sendScan({ qr_data: data });
      setScannedCount(wsClientRef.current.getScannedCount());
    } else {
      // Add to offline queue
      addToOfflineQueue(data);
      setOfflineQueueCount(getOfflineQueue().length);
      setLastScan("Añadido a cola offline");
    }
  }, [token]);

  const handleSync = useCallback(() => {
    if (wsClientRef.current) {
      wsClientRef.current.requestSync();
      setWsState("syncing");
    }
  }, []);

  const handleDisconnect = useCallback(async () => {
    if (session && token) {
      try {
        await closeBridgeSession(session.qr_token, token);
      } catch (e) {
        // Ignore errors on disconnect
      }
    }
    
    if (wsClientRef.current) {
      wsClientRef.current.disconnect();
      wsClientRef.current = null;
    }
    
    setSession(null);
    setViewMode("idle");
    setScannedCount(0);
    setLastScan(null);
    setWsState("offline");
  }, [session, token]);

  const handleBack = useCallback(() => {
    if (viewMode === "connected") {
      handleDisconnect();
    }
    setViewMode("idle");
    setError(null);
  }, [viewMode, handleDisconnect]);

  // Determine effective state
  const effectiveState: BridgeWSState = wsClientRef.current?.getState() || wsState;
  const effectiveScannedCount = wsClientRef.current?.getScannedCount() || scannedCount;

  return (
    <div className="min-h-screen relative overflow-hidden">
      {/* Animated Background - Same as Dashboard */}
      <div className="fixed inset-0 -z-10">
        <div className="absolute inset-0 bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900" />
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-emerald-500/20 rounded-full blur-3xl animate-pulse" />
        <div className="absolute top-1/3 right-1/4 w-80 h-80 bg-violet-500/15 rounded-full blur-3xl animate-pulse" style={{ animationDelay: '1s' }} />
        <div className="absolute bottom-1/4 left-1/3 w-72 h-72 bg-blue-500/15 rounded-full blur-3xl animate-pulse" style={{ animationDelay: '2s' }} />
        <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHZpZXdCb3g9IjAgMCA2MCA2MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48ZyBmaWxsPSJub25lIiBmaWxsLXJ1bGU9ImV2ZW5vZGQiPjxnIGZpbGw9IiNmZmZmZmYiIGZpbGwtb3BhY2l0eT0iMC4wMyI+PGNpcmNsZSBjeD0iMzAiIGN5PSIzMCIgcj0iMS41Ii8+PC9nPjwvZz48L3N2Zz4=')] opacity-30" />
      </div>

      {/* Header */}
      <header className="sticky top-0 z-50 backdrop-blur-xl bg-white/5 border-b border-white/10">
        <div className="max-w-lg mx-auto px-4 py-3 flex justify-between items-center">
          <div className="flex items-center gap-3">
            <button
              onClick={() => router.push("/dashboard")}
              className="p-2 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 backdrop-blur-md transition-colors"
              title="Volver al dashboard"
            >
              <svg className="w-5 h-5 text-white/60" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
              </svg>
            </button>
            
            <div className="relative group">
              <div className="w-10 h-10 rounded-2xl bg-gradient-to-br from-emerald-400 via-teal-500 to-emerald-600 flex items-center justify-center shadow-lg shadow-emerald-500/30">
                <span className="text-white font-black text-lg">P</span>
              </div>
            </div>
            <div>
              <h1 className="text-lg font-bold text-white tracking-tight">PRANELY</h1>
              <p className="text-xs text-white/40">Mobile Bridge</p>
            </div>
          </div>
          
          <div className="flex items-center gap-2">
            {/* Role Badge */}
            <div className="px-2 py-1 rounded-xl bg-white/10 backdrop-blur-md border border-white/10">
              <span className="text-xs font-medium text-white/80">{organization?.name?.slice(0, 12) || 'Org'}</span>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content - Mobile First 375px */}
      <main className="max-w-lg mx-auto px-4 py-6">
        {/* Page Title */}
        <div className="text-center mb-6">
          <h2 className="text-2xl font-bold text-white mb-2">
            Bridge Móvil
          </h2>
          <p className="text-sm text-white/50">
            Conecta tu dispositivo móvil para sincronizar escaneos en tiempo real
          </p>
        </div>

        {/* Offline Queue Indicator */}
        {offlineQueueCount > 0 && (
          <div className="mb-4 p-3 rounded-xl bg-amber-500/20 border border-amber-500/30 backdrop-blur-md flex items-center gap-3">
            <svg className="w-5 h-5 text-amber-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            <div className="flex-1 min-w-0">
              <p className="text-sm text-amber-300 font-medium">{offlineQueueCount} escaneos en cola offline</p>
              <p className="text-xs text-amber-300/60">Se sincronizarán al reconectar</p>
            </div>
            <button
              onClick={() => {
                clearOfflineQueue();
                setOfflineQueueCount(0);
              }}
              className="px-2 py-1 rounded-lg bg-white/10 hover:bg-white/20 text-amber-300 text-xs font-medium transition-colors"
            >
              Limpiar
            </button>
          </div>
        )}

        {/* Error Alert */}
        {error && (
          <div className="mb-4 p-3 rounded-xl bg-rose-500/20 border border-rose-500/30 backdrop-blur-md flex items-center gap-3">
            <svg className="w-5 h-5 text-rose-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p className="text-sm text-rose-300 flex-1">{error}</p>
            <button
              onClick={() => setError(null)}
              className="p-1 rounded hover:bg-white/10 transition-colors"
            >
              <svg className="w-4 h-4 text-rose-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        )}

        {/* Status Bar */}
        <div className="mb-6 p-4 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-md">
          <BridgeStatusBar
            state={effectiveState}
            scannedCount={effectiveScannedCount}
            qrToken={session?.qr_token}
            expiresAt={session?.expires_at}
            onGenerateQR={handleCreateSession}
            onManualEntry={() => setViewMode("manual")}
            onSync={handleSync}
            onDisconnect={handleDisconnect}
          />
        </div>

        {/* Scan Results */}
        {lastScan && (
          <div className="mb-6 p-4 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 backdrop-blur-md">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-emerald-500/20 flex items-center justify-center">
                <svg className="w-5 h-5 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm text-emerald-300 font-medium">Último escaneo</p>
                <p className="text-xs text-emerald-300/60 truncate">{lastScan}</p>
              </div>
            </div>
          </div>
        )}

        {/* View Modes */}
        {viewMode === "idle" && (
          <div className="space-y-4">
            {/* Quick Actions */}
            <div className="grid grid-cols-2 gap-4">
              <button
                onClick={() => setViewMode("scan")}
                className="p-6 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-md hover:bg-white/10 transition-all group"
              >
                <div className="w-12 h-12 rounded-xl bg-emerald-500/20 flex items-center justify-center mx-auto mb-3 group-hover:scale-110 transition-transform">
                  <svg className="w-6 h-6 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" />
                  </svg>
                </div>
                <p className="text-sm font-medium text-white text-center">Escanear QR</p>
                <p className="text-xs text-white/40 text-center mt-1">Usar cámara del dispositivo</p>
              </button>
              
              <button
                onClick={() => setViewMode("manual")}
                className="p-6 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-md hover:bg-white/10 transition-all group"
              >
                <div className="w-12 h-12 rounded-xl bg-blue-500/20 flex items-center justify-center mx-auto mb-3 group-hover:scale-110 transition-transform">
                  <svg className="w-6 h-6 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                  </svg>
                </div>
                <p className="text-sm font-medium text-white text-center">Entrada Manual</p>
                <p className="text-xs text-white/40 text-center mt-1">Ingresar token de sesión</p>
              </button>
            </div>

            {/* Instructions */}
            <div className="p-4 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-md">
              <h3 className="text-sm font-medium text-white mb-3">¿Cómo funciona?</h3>
              <ol className="space-y-2">
                <li className="flex items-start gap-2 text-xs text-white/60">
                  <span className="w-5 h-5 rounded-full bg-emerald-500/20 flex items-center justify-center text-emerald-400 font-bold flex-shrink-0">1</span>
                  Genera un código QR desde el dashboard
                </li>
                <li className="flex items-start gap-2 text-xs text-white/60">
                  <span className="w-5 h-5 rounded-full bg-emerald-500/20 flex items-center justify-center text-emerald-400 font-bold flex-shrink-0">2</span>
                  Escanea el código con tu dispositivo móvil
                </li>
                <li className="flex items-start gap-2 text-xs text-white/60">
                  <span className="w-5 h-5 rounded-full bg-emerald-500/20 flex items-center justify-center text-emerald-400 font-bold flex-shrink-0">3</span>
                  Sincroniza manifiestos en tiempo real
                </li>
              </ol>
            </div>
          </div>
        )}

        {viewMode === "scan" && (
          <div className="space-y-4">
            <QRScanner
              onScan={handleQRScan}
              onError={(err) => setError(err)}
              onClose={() => setViewMode("idle")}
            />
            
            <button
              onClick={() => setViewMode("idle")}
              className="w-full px-4 py-3 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-white/80 font-medium transition-colors"
            >
              Cancelar
            </button>
          </div>
        )}

        {viewMode === "manual" && (
          <div className="space-y-4">
            <div className="p-4 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-md">
              <label className="block text-sm font-medium text-white mb-2">
                Token de Sesión
              </label>
              <input
                type="text"
                value={manualToken}
                onChange={(e) => setManualToken(e.target.value.toUpperCase())}
                placeholder="Ej: A1B2C3D4E5F6G7H8"
                className="w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-white/30 font-mono text-center tracking-wider focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500/50"
                maxLength={16}
              />
              <p className="mt-2 text-xs text-white/40 text-center">
                Ingresa el código QR de 16 caracteres
              </p>
            </div>
            
            <div className="flex gap-3">
              <button
                onClick={() => setViewMode("idle")}
                className="flex-1 px-4 py-3 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-white/80 font-medium transition-colors"
              >
                Cancelar
              </button>
              <button
                onClick={handleManualEntry}
                disabled={manualToken.length !== 16 || isLoading}
                className="flex-1 px-4 py-3 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-500 text-white font-semibold shadow-lg shadow-emerald-500/30 hover:shadow-emerald-500/50 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                {isLoading ? (
                  <>
                    <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                    Validando...
                  </>
                ) : (
                  "Validar"
                )}
              </button>
            </div>
          </div>
        )}

        {viewMode === "connected" && (
          <div className="space-y-4">
            <p className="text-center text-sm text-white/60">
              Sesión activa. Ya puedes escanear códigos QR.
            </p>
            
            <button
              onClick={() => setViewMode("scan")}
              className="w-full p-6 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-md hover:bg-white/10 transition-all"
            >
              <div className="w-12 h-12 rounded-xl bg-emerald-500/20 flex items-center justify-center mx-auto mb-3">
                <svg className="w-6 h-6 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
              </div>
              <p className="text-sm font-medium text-white text-center">Abrir Escáner</p>
            </button>
          </div>
        )}
      </main>

      {/* Bottom Glass Bar - Fixed */}
      <div className="fixed bottom-0 left-0 right-0 backdrop-blur-xl bg-white/5 border-t border-white/10">
        <div className="max-w-lg mx-auto px-4 py-3 flex justify-around">
          <button
            onClick={() => router.push("/dashboard")}
            className="flex flex-col items-center gap-1 p-2 rounded-xl hover:bg-white/10 transition-colors"
          >
            <svg className="w-5 h-5 text-white/60" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
            </svg>
            <span className="text-xs text-white/60">Dashboard</span>
          </button>
          
          <button
            onClick={() => setViewMode("scan")}
            className={`flex flex-col items-center gap-1 p-2 rounded-xl transition-colors ${viewMode === "scan" ? "bg-emerald-500/20" : "hover:bg-white/10"}`}
          >
            <svg className={`w-5 h-5 ${viewMode === "scan" ? "text-emerald-400" : "text-white/60"}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v1m6 11h2m-6 0h-2v4m0-11v3m0 0h.01M12 12h4.01M16 20h4M4 12h4m12 0h.01M5 8h2a1 1 0 001-1V5a1 1 0 00-1-1H5a1 1 0 00-1 1v2a1 1 0 001 1zm12 0h2a1 1 0 001-1V5a1 1 0 00-1-1h-2a1 1 0 00-1 1v2a1 1 0 001 1zM5 20h2a1 1 0 001-1v-2a1 1 0 00-1-1H5a1 1 0 00-1 1v2a1 1 0 001 1z" />
            </svg>
            <span className={`text-xs ${viewMode === "scan" ? "text-emerald-400" : "text-white/60"}`}>Scan</span>
          </button>
          
          <button
            onClick={() => setViewMode("manual")}
            className={`flex flex-col items-center gap-1 p-2 rounded-xl transition-colors ${viewMode === "manual" ? "bg-blue-500/20" : "hover:bg-white/10"}`}
          >
            <svg className={`w-5 h-5 ${viewMode === "manual" ? "text-blue-400" : "text-white/60"}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
            </svg>
            <span className={`text-xs ${viewMode === "manual" ? "text-blue-400" : "text-white/60"}`}>Manual</span>
          </button>
          
          <button
            onClick={handleSync}
            disabled={effectiveState !== "connected"}
            className={`flex flex-col items-center gap-1 p-2 rounded-xl transition-colors ${effectiveState === "connected" ? "hover:bg-white/10" : "opacity-50"}`}
          >
            <svg className="w-5 h-5 text-white/60" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            <span className="text-xs text-white/60">Sync</span>
          </button>
        </div>
      </div>
      
      {/* Spacer for bottom bar */}
      <div className="h-20" />
    </div>
  );
}

export default function BridgePage() {
  return (
    <ProtectedRoute fallbackPath="/login">
      <BridgeContent />
    </ProtectedRoute>
  );
}
