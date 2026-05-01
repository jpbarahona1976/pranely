// 8A MOBILE BRIDGE - QR Scanner Component
// Live scanner using getUserMedia + jsqr

"use client";

import { useEffect, useRef, useState, useCallback } from "react";

interface QRScannerProps {
  onScan: (data: string) => void;
  onError?: (error: string) => void;
  onClose?: () => void;
  disabled?: boolean;
}

export function QRScanner({ onScan, onError, onClose, disabled }: QRScannerProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [isScanning, setIsScanning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [permissionDenied, setPermissionDenied] = useState(false);

  const stopCamera = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    setIsScanning(false);
  }, []);

  const startCamera = useCallback(async () => {
    try {
      setError(null);
      
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: "environment", // Prefer back camera on mobile
          width: { ideal: 1280 },
          height: { ideal: 720 },
        },
      });
      
      streamRef.current = stream;
      
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
        setIsScanning(true);
      }
    } catch (err: any) {
      if (err.name === "NotAllowedError" || err.name === "PermissionDeniedError") {
        setPermissionDenied(true);
        setError("Permiso de cámara denegado. Por favor permite el acceso a la cámara.");
      } else {
        setError(`Error al iniciar cámara: ${err.message}`);
      }
      onError?.(error || "Error de cámara");
    }
  }, [onError, error]);

  useEffect(() => {
    if (!disabled) {
      startCamera();
    }
    
    return () => {
      stopCamera();
    };
  }, [disabled, startCamera, stopCamera]);

  // QR scanning loop with jsqr
  useEffect(() => {
    if (!isScanning || !videoRef.current || !canvasRef.current) return;

    const video = videoRef.current;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    
    if (!ctx) return;

    let scanning = true;
    
    const scan = async () => {
      if (!scanning || !video || video.readyState !== video.HAVE_ENOUGH_DATA) {
        requestAnimationFrame(scan);
        return;
      }
      
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
      
      const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
      
      try {
        // Dynamic import jsqr
        const jsQR = await import("jsqr").then(m => m.default);
        const code = jsQR(imageData.data, imageData.width, imageData.height);
        
        if (code) {
          // Found a QR code!
          onScan(code.data);
          // Brief pause after successful scan
          await new Promise(r => setTimeout(r, 1000));
        }
      } catch (e) {
        // jsqr decode failed, continue scanning
      }
      
      if (scanning) {
        requestAnimationFrame(scan);
      }
    };

    requestAnimationFrame(scan);

    return () => {
      scanning = false;
    };
  }, [isScanning, onScan]);

  if (permissionDenied) {
    return (
      <div className="flex flex-col items-center justify-center p-8 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-md">
        <div className="w-16 h-16 rounded-2xl bg-rose-500/20 flex items-center justify-center mb-4">
          <svg className="w-8 h-8 text-rose-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
          </svg>
        </div>
        <h3 className="text-lg font-medium text-white mb-2">Cámara no disponible</h3>
        <p className="text-sm text-white/60 text-center mb-4 max-w-xs">
          Por favor permite el acceso a la cámara en la configuración de tu navegador para escanear códigos QR.
        </p>
        <button
          onClick={() => {
            setPermissionDenied(false);
            setError(null);
            startCamera();
          }}
          className="px-4 py-2 rounded-xl bg-white/10 hover:bg-white/20 border border-white/10 text-white text-sm font-medium transition-colors"
        >
          Reintentar
        </button>
      </div>
    );
  }

  return (
    <div className="relative rounded-2xl overflow-hidden bg-black/50 border border-white/10 backdrop-blur-md">
      {/* Video feed */}
      <video
        ref={videoRef}
        className="w-full aspect-square object-cover"
        playsInline
        muted
      />
      
      {/* Hidden canvas for QR processing */}
      <canvas ref={canvasRef} className="hidden" />
      
      {/* Scanning overlay */}
      {isScanning && (
        <div className="absolute inset-0 flex items-center justify-center">
          {/* Scan frame */}
          <div className="relative w-48 h-48">
            {/* Corner brackets */}
            <div className="absolute top-0 left-0 w-8 h-8 border-t-2 border-l-2 border-emerald-400" />
            <div className="absolute top-0 right-0 w-8 h-8 border-t-2 border-r-2 border-emerald-400" />
            <div className="absolute bottom-0 left-0 w-8 h-8 border-b-2 border-l-2 border-emerald-400" />
            <div className="absolute bottom-0 right-0 w-8 h-8 border-b-2 border-r-2 border-emerald-400" />
            
            {/* Scanning line animation */}
            <div className="absolute left-2 right-2 h-0.5 bg-emerald-400/80 animate-pulse"
              style={{ top: "50%" }}
            />
          </div>
        </div>
      )}
      
      {/* Status indicator */}
      <div className="absolute top-4 left-4 flex items-center gap-2 px-3 py-1.5 rounded-full bg-black/50 backdrop-blur-md">
        <div className={`w-2 h-2 rounded-full ${isScanning ? "bg-emerald-400 animate-pulse" : "bg-white/40"}`} />
        <span className="text-xs text-white/80 font-medium">
          {isScanning ? "Escaneando..." : "Iniciando cámara..."}
        </span>
      </div>
      
      {/* Close button */}
      {onClose && (
        <button
          onClick={stopCamera}
          className="absolute top-4 right-4 p-2 rounded-xl bg-black/50 backdrop-blur-md hover:bg-black/70 transition-colors"
        >
          <svg className="w-5 h-5 text-white/80" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      )}
      
      {/* Error message */}
      {error && (
        <div className="absolute bottom-4 left-4 right-4 p-3 rounded-xl bg-rose-500/20 border border-rose-500/30 backdrop-blur-md">
          <p className="text-sm text-rose-300 text-center">{error}</p>
        </div>
      )}
    </div>
  );
}
