// Upload page - Glassmorphism drag & drop PDF upload with RQ processing
"use client";

import { useState, useCallback, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { DropZoneGlass } from "@/components/upload/DropZoneGlass";
import { UploadProgress, type UploadFile, type UploadStatus } from "@/components/upload/UploadProgress";

interface ProcessingJob {
  id: string;
  fileId: string;
  status: "queued" | "processing" | "completed" | "error";
  progress: number;
}

// Mock API simulation - replace with real RQ/API integration
async function simulateUpload(file: File): Promise<{ jobId: string }> {
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve({ jobId: `job_${Date.now()}_${Math.random().toString(36).slice(2, 8)}` });
    }, 800);
  });
}

async function simulateProcessing(jobId: string): Promise<void> {
  // Simulate RQ queue → worker → DeepInfra processing
  return new Promise((resolve) => {
    setTimeout(resolve, 3000);
  });
}

function UploadContent() {
  const router = useRouter();
  const { user, organization, logout, token, permissions } = useAuth();
  const [files, setFiles] = useState<UploadFile[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [jobs, setJobs] = useState<Map<string, ProcessingJob>>(new Map());
  const [showSuccessToast, setShowSuccessToast] = useState(false);
  const [completedFiles, setCompletedFiles] = useState<string[]>([]);

  // Process files after selection
  const handleFilesSelected = useCallback(async (selectedFiles: File[]) => {
    // Add files to state with initial status
    const newFiles: UploadFile[] = selectedFiles.map((file) => ({
      id: `file_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
      name: file.name,
      size: file.size,
      status: "uploading",
      progress: 0,
    }));

    setFiles((prev) => [...prev, ...newFiles]);
    setIsUploading(true);

    // Simulate upload for each file
    for (const file of newFiles) {
      try {
        // Simulate upload progress
        for (let i = 0; i <= 100; i += 20) {
          await new Promise((r) => setTimeout(r, 100));
          setFiles((prev) =>
            prev.map((f) => (f.id === file.id ? { ...f, progress: i } : f))
          );
        }

        // Upload complete, get job ID from RQ
        const { jobId } = await simulateUpload(selectedFiles.find(f => f.name === file.name)!);
        
        // Add to RQ queue
        setFiles((prev) =>
          prev.map((f) =>
            f.id === file.id
              ? { ...f, status: "queued", progress: 100, jobId }
              : f
          )
        );

        // Add job to tracking
        setJobs((prev) => {
          const newJobs = new Map(prev);
          newJobs.set(jobId, { id: jobId, fileId: file.id, status: "queued", progress: 0 });
          return newJobs;
        });

        // Process job (RQ → Worker → DeepInfra)
        setFiles((prev) =>
          prev.map((f) =>
            f.id === file.id ? { ...f, status: "processing", progress: 0 } : f
          )
        );

        setJobs((prev) => {
          const newJobs = new Map(prev);
          newJobs.set(jobId, { ...newJobs.get(jobId)!, status: "processing", progress: 50 });
          return newJobs;
        });

        // Simulate AI processing
        await simulateProcessing(jobId);

        // Complete
        setFiles((prev) =>
          prev.map((f) =>
            f.id === file.id
              ? {
                  ...f,
                  status: "completed",
                  progress: 100,
                  result: {
                    confidence: 0.85 + Math.random() * 0.14,
                    manifestNumber: `NOM-${Date.now().toString().slice(-6)}`,
                  },
                }
              : f
          )
        );

        // Show success toast
        setCompletedFiles((prev) => [...prev, file.name]);
        setShowSuccessToast(true);
        setTimeout(() => setShowSuccessToast(false), 4000);

        setJobs((prev) => {
          const newJobs = new Map(prev);
          newJobs.set(jobId, { ...newJobs.get(jobId)!, status: "completed", progress: 100 });
          return newJobs;
        });
      } catch (error) {
        setFiles((prev) =>
          prev.map((f) =>
            f.id === file.id
              ? {
                  ...f,
                  status: "error",
                  error: error instanceof Error ? error.message : "Error desconocido",
                }
              : f
          )
        );
      }
    }

    setIsUploading(false);
  }, []);

  // Cancel upload
  const handleCancel = useCallback((id: string) => {
    setFiles((prev) => prev.filter((f) => f.id !== id));
  }, []);

  // Retry failed upload
  const handleRetry = useCallback((id: string) => {
    const file = files.find((f) => f.id === id);
    if (file) {
      setFiles((prev) =>
        prev.map((f) =>
          f.id === id ? { ...f, status: "uploading", progress: 0, error: undefined } : f
        )
      );
      // Re-trigger upload simulation
      handleFilesSelected([new File([], file.name)]);
    }
  }, [files, handleFilesSelected]);

  // Remove completed file
  const handleRemove = useCallback((id: string) => {
    setFiles((prev) => prev.filter((f) => f.id !== id));
  }, []);

  // Stats
  const stats = {
    total: files.length,
    completed: files.filter((f) => f.status === "completed").length,
    processing: files.filter((f) => ["uploading", "queued", "processing"].includes(f.status)).length,
    error: files.filter((f) => f.status === "error").length,
  };

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
        <div className="max-w-7xl mx-auto px-6 py-4 flex justify-between items-center">
          <div className="flex items-center gap-4">
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
              <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-emerald-400 via-teal-500 to-emerald-600 flex items-center justify-center shadow-lg shadow-emerald-500/30">
                <span className="text-white font-black text-xl">P</span>
              </div>
            </div>
            <div>
              <h1 className="text-xl font-bold text-white tracking-tight">PRANELY</h1>
              <p className="text-xs text-white/40">Subir Documentos</p>
            </div>
          </div>
          
          <div className="flex items-center gap-4">
            {/* Role Badge */}
            <div className="px-4 py-2 rounded-2xl bg-white/10 backdrop-blur-md border border-white/10">
              <span className="text-sm font-medium text-white/80">{organization?.name || 'Organización'}</span>
              <span className={`
                ml-2 px-2 py-0.5 rounded-full text-xs font-bold uppercase
                ${permissions.role === 'owner' ? 'bg-amber-500/30 text-amber-300' : ''}
                ${permissions.role === 'admin' ? 'bg-emerald-500/30 text-emerald-300' : ''}
                ${permissions.role === 'member' ? 'bg-blue-500/30 text-blue-300' : ''}
              `}>
                {permissions.role}
              </span>
            </div>
            
            {/* User */}
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-2xl bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center text-white font-bold shadow-lg">
                {user?.email?.[0]?.toUpperCase() || 'U'}
              </div>
              <div className="hidden md:block">
                <p className="text-sm font-medium text-white">{user?.full_name || user?.email || 'Usuario'}</p>
                <p className="text-xs text-white/40">{user?.email}</p>
              </div>
            </div>
            
            {/* Logout */}
            <button
              onClick={logout}
              className="p-3 rounded-2xl bg-white/5 hover:bg-white/10 border border-white/10 backdrop-blur-md transition-all group"
            >
              <svg className="w-5 h-5 text-white/60 group-hover:text-rose-400 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
              </svg>
            </button>
          </div>

          {/* Success Toast */}
          {showSuccessToast && (
            <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-4 px-6 py-3 rounded-2xl bg-emerald-500/90 backdrop-blur-md border border-emerald-400/30 shadow-lg shadow-emerald-500/20 flex items-center gap-3 animate-bounce">
              <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              <span className="text-white font-medium">
                {completedFiles.length > 1 
                  ? `${completedFiles.length} documentos procesados` 
                  : `${completedFiles[0]} listo para revisión`
                }
              </span>
              <button
                onClick={() => router.push("/review")}
                className="ml-2 px-3 py-1 rounded-lg bg-white/20 hover:bg-white/30 text-white text-sm font-medium transition-colors"
              >
                Ver ahora
              </button>
            </div>
          )}
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-4xl mx-auto px-6 py-8">
        {/* Page Header */}
        <div className="text-center mb-8">
          <h2 className="text-3xl font-bold text-white mb-2">
            Subir Manifiestos
          </h2>
          <p className="text-white/50 max-w-xl mx-auto">
            Arrastra tus archivos PDF para que la IA los procese y extraiga los datos 
            según la NOM-052-SEMARNAT-2005
          </p>
        </div>

        {/* Drop Zone */}
        <DropZoneGlass
          onFilesSelected={handleFilesSelected}
          disabled={isUploading}
          accept=".pdf"
          maxSizeMB={10}
        />

        {/* Stats Bar */}
        {files.length > 0 && (
          <div className="mt-6 p-4 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-md">
            <div className="flex items-center justify-between flex-wrap gap-4">
              <div className="flex items-center gap-6">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 bg-white/20 rounded-full" />
                  <span className="text-sm text-white/60">
                    {stats.total} archivo{stats.total !== 1 ? "s" : ""}
                  </span>
                </div>
                
                {stats.completed > 0 && (
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 bg-emerald-500 rounded-full" />
                    <span className="text-sm text-emerald-400">
                      {stats.completed} completado{stats.completed !== 1 ? "s" : ""}
                    </span>
                  </div>
                )}
                
                {stats.processing > 0 && (
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 bg-blue-500 rounded-full animate-pulse" />
                    <span className="text-sm text-blue-400">
                      {stats.processing} procesando
                    </span>
                  </div>
                )}
                
                {stats.error > 0 && (
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 bg-rose-500 rounded-full" />
                    <span className="text-sm text-rose-400">
                      {stats.error} error{stats.error !== 1 ? "es" : ""}
                    </span>
                  </div>
                )}
              </div>

              {/* Action Buttons */}
              <div className="flex items-center gap-3">
                {stats.completed > 0 && (
                  <button
                    onClick={() => router.push("/review")}
                    className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-500 text-white font-semibold shadow-lg shadow-emerald-500/30 hover:shadow-emerald-500/50 transition-all flex items-center gap-2"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                    </svg>
                    Revisar {stats.completed > 1 ? "documentos" : "documento"}
                  </button>
                )}
                
                <button className="px-5 py-2.5 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-white/80 font-medium transition-all flex items-center gap-2">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 10h16M4 14h16M4 18h16" />
                  </svg>
                  Ver cola RQ
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Upload Progress */}
        <div className="mt-6 space-y-4">
          <UploadProgress
            files={files}
            onCancel={handleCancel}
            onRetry={handleRetry}
            onRemove={handleRemove}
          />
        </div>

        {/* Empty State */}
        {files.length === 0 && (
          <div className="mt-12 text-center">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-white/5 mb-4">
              <svg className="w-8 h-8 text-white/30" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 13h6m-3-3v6m5 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <h3 className="text-lg font-medium text-white/60 mb-2">
              Sin documentos pendientes
            </h3>
            <p className="text-sm text-white/40 max-w-sm mx-auto">
              Sube tus manifiestos de residuos peligrosos para que la IA los procese 
              y valide automáticamente.
            </p>
          </div>
        )}

        {/* Info Cards */}
        <div className="mt-12 grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="p-4 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-md">
            <div className="flex items-center gap-3 mb-2">
              <div className="p-2 rounded-xl bg-blue-500/20">
                <svg className="w-5 h-5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              <h4 className="text-sm font-medium text-white">Formatos</h4>
            </div>
            <p className="text-xs text-white/40">
              Acepta archivos PDF de manifiestos de transporte de residuos peligrosos
            </p>
          </div>

          <div className="p-4 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-md">
            <div className="flex items-center gap-3 mb-2">
              <div className="p-2 rounded-xl bg-emerald-500/20">
                <svg className="w-5 h-5 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                </svg>
              </div>
              <h4 className="text-sm font-medium text-white">IA DeepInfra</h4>
            </div>
            <p className="text-xs text-white/40">
              Extracción automática de datos usando modelos de visión y lenguaje
            </p>
          </div>

          <div className="p-4 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-md">
            <div className="flex items-center gap-3 mb-2">
              <div className="p-2 rounded-xl bg-amber-500/20">
                <svg className="w-5 h-5 text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                </svg>
              </div>
              <h4 className="text-sm font-medium text-white">NOM-052</h4>
            </div>
            <p className="text-xs text-white/40">
              Validación contra la normatividad SEMARNAT para residuos peligrosos
            </p>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-white/5 py-6 mt-8">
        <div className="max-w-7xl mx-auto px-6 flex flex-col md:flex-row justify-between items-center gap-4 text-sm text-white/30">
          <span>© 2024 PRANELY. Sistema Documental Maestro para Gestión de Residuos.</span>
          <div className="flex items-center gap-6">
            <span>•</span>
            <span>NOM-052-SEMARNAT-2005</span>
            <span>•</span>
            <span>México</span>
          </div>
        </div>
      </footer>
    </div>
  );
}

export function UploadPage() {
  return (
    <ProtectedRoute fallbackPath="/login">
      <UploadContent />
    </ProtectedRoute>
  );
}

export default UploadPage;
