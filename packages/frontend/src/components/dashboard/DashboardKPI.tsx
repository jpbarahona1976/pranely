// DashboardKPI - Componente principal del dashboard glassmorphism
"use client";

import { useEffect, useState, useCallback } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { wasteApi, type WasteStats, type WasteMovement } from "@/lib/waste-api";
import { KpiCard } from "./KpiCard";
import { MovementsTable } from "./MovementsTable";
import { Sidebar } from "./Sidebar";
import { FAB } from "./FAB";

interface RecentActivity {
  id: number;
  action: "created" | "approved" | "rejected" | "updated" | "archived";
  user: string;
  manifest: string;
  timestamp: string;
  details?: string;
}

interface RegulatoryAlert {
  id: number;
  norma: string;
  title: string;
  severity: "low" | "medium" | "high" | "critical";
  description: string;
  due_date?: string;
  status: "open" | "acknowledged" | "resolved";
}

// NOTA: Activity y Alerts requieren endpoints backend que no existen en 6B
// Se muestra empty state controlado hasta que se implemente la integración real
const EMPTY_ACTIVITY: RecentActivity[] = [];
const EMPTY_ALERTS: RegulatoryAlert[] = [];

// Mock data SOLO para demo sin backend corriendo
const mockMovements: WasteMovement[] = [
  { id: 1, organization_id: 1, manifest_number: "MAN-2024-001", date: "2024-01-15", waste_type: "PELIGROSO", quantity: 250, unit: "kg", generator_name: "Industrias del Norte", transporter_name: "Transportes Ecológicos", final_destination: "Centro de Acopio Norte", status: "pending", is_immutable: false, created_at: "2024-01-15T10:00:00Z", updated_at: "2024-01-15T10:00:00Z", confidence_score: 95 },
  { id: 2, organization_id: 1, manifest_number: "MAN-2024-002", date: "2024-01-14", waste_type: "ESPECIAL", quantity: 500, unit: "kg", generator_name: "Plásticos del Centro", transporter_name: "Residuos SA", final_destination: "Planta Tratadora", status: "in_review", is_immutable: false, created_at: "2024-01-14T09:00:00Z", updated_at: "2024-01-14T14:00:00Z", confidence_score: 88 },
  { id: 3, organization_id: 1, manifest_number: "MAN-2024-003", date: "2024-01-13", waste_type: "PELIGROSO", quantity: 120, unit: "kg", generator_name: "Químicos Mex", transporter_name: "Transportes Ecológicos", final_destination: "Centro Especializado", status: "validated", is_immutable: true, created_at: "2024-01-13T08:00:00Z", updated_at: "2024-01-13T16:00:00Z", confidence_score: 99, reviewed_by: "Carlos Ruiz", reviewed_at: "2024-01-13T16:00:00Z" },
  { id: 4, organization_id: 1, manifest_number: "MAN-2024-004", date: "2024-01-12", waste_type: "INERTE", quantity: 1000, unit: "kg", generator_name: "Construcciones ABC", transporter_name: "Volquetes MX", final_destination: "Relleno Sanitario", status: "rejected", is_immutable: false, created_at: "2024-01-12T11:00:00Z", updated_at: "2024-01-12T15:00:00Z", confidence_score: 72, rejection_reason: "Falta manifest number" },
  { id: 5, organization_id: 1, manifest_number: "MAN-2024-005", date: "2024-01-11", waste_type: "RECICLABLE", quantity: 800, unit: "kg", generator_name: "Papelera del Valle", transporter_name: "Reciclajes SA", final_destination: "Planta Recycla", status: "exception", is_immutable: false, created_at: "2024-01-11T10:00:00Z", updated_at: "2024-01-11T14:00:00Z", confidence_score: 45 },
];

function DashboardContent() {
  const { user, organization, logout, token, permissions, isLoading: authLoading } = useAuth();
  const [stats, setStats] = useState<WasteStats | null>(null);
  const [movements, setMovements] = useState<WasteMovement[]>([]);
  const [activity, setActivity] = useState<RecentActivity[]>(EMPTY_ACTIVITY);
  const [alerts, setAlerts] = useState<RegulatoryAlert[]>(EMPTY_ALERTS);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());
  const [pollingIndicator, setPollingIndicator] = useState(false);
  const [dataSource, setDataSource] = useState<"api" | "mock">("api");

  const fetchData = useCallback(async () => {
    try {
      setError(null);
      
      // Intentar obtener datos de API real
      if (token) {
        try {
          const [statsData, movementsData] = await Promise.all([
            wasteApi.stats(),
            wasteApi.list({ page: 1, page_size: 50 }),
          ]);
          setStats(statsData);
          setMovements(movementsData.items);
          setDataSource("api");
          
          // TODO: Activity y Alerts - requieren endpoints que no existen en 6B
          // Por ahora permanecen vacíos hasta Fase 6C o posterior
          setActivity(EMPTY_ACTIVITY);
          setAlerts(EMPTY_ALERTS);
        } catch {
          // API no disponible, usar mock para demo
          setStats({ total: 24, pending: 7, in_review: 5, validated: 10, rejected: 1, exception: 1 });
          setMovements(mockMovements);
          setDataSource("mock");
          setActivity(EMPTY_ACTIVITY);
          setAlerts(EMPTY_ALERTS);
        }
      } else {
        // No hay token, usar mock
        setStats({ total: 24, pending: 7, in_review: 5, validated: 10, rejected: 1, exception: 1 });
        setMovements(mockMovements);
        setDataSource("mock");
      }
      
      setLastRefresh(new Date());
      setPollingIndicator(false);
    } catch (err) {
      console.error("Error fetching data:", err);
      setError(err instanceof Error ? err.message : "Error al cargar datos");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    if (!authLoading) {
      fetchData();
    }
  }, [authLoading, fetchData]);

  // Polling 30s con indicador visual
  useEffect(() => {
    if (!token) return;
    
    const interval = setInterval(() => {
      setPollingIndicator(true);
      fetchData();
    }, 30000);

    return () => clearInterval(interval);
  }, [fetchData, token]);

  const handleApprove = async (id: number) => {
    // Actualización optimista
    setMovements(prev => prev.map(m => 
      m.id === id ? { ...m, status: "validated" as const, is_immutable: true } : m
    ));
    
    // Llamar API real
    try {
      await wasteApi.approve(id);
    } catch (err) {
      // Revertir en caso de error
      setMovements(prev => prev.map(m => 
        m.id === id ? { ...m, status: "in_review" as const, is_immutable: false } : m
      ));
      setError(`Error al aprobar: ${err instanceof Error ? err.message : "Unknown error"}`);
    }
  };

  const handleReject = async (id: number, reason: string) => {
    // Actualización optimista
    setMovements(prev => prev.map(m => 
      m.id === id ? { ...m, status: "rejected" as const, rejection_reason: reason } : m
    ));
    
    // Llamar API real
    try {
      await wasteApi.reject(id, reason);
    } catch (err) {
      // Revertir en caso de error
      setMovements(prev => prev.map(m => 
        m.id === id ? { ...m, status: "in_review" as const } : m
      ));
      setError(`Error al rechazar: ${err instanceof Error ? err.message : "Unknown error"}`);
    }
  };

  return (
    <div className="min-h-screen relative overflow-hidden">
      {/* Animated Background */}
      <div className="fixed inset-0 -z-10">
        <div className="absolute inset-0 bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900" />
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-emerald-500/20 rounded-full blur-3xl animate-pulse" />
        <div className="absolute top-1/3 right-1/4 w-80 h-80 bg-violet-500/15 rounded-full blur-3xl animate-pulse" style={{ animationDelay: '1s' }} />
        <div className="absolute bottom-1/4 left-1/3 w-72 h-72 bg-blue-500/15 rounded-full blur-3xl animate-pulse" style={{ animationDelay: '2s' }} />
        <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHZpZXdCb3g9IjAgMCA2MCA2MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48ZyBmaWxsPSJub25lIiBmaWxsLXJ1bGU9ImV2ZW5vZGQiPjxnIGZpbGw9IiNmZmZmZmYiIGZpbGwtb3BhY2l0eT0iMC4wMyI+PGNpcmNsZSBjeD0iMzAiIGN5PSIzMCIgcj0iMS41Ii8+PC9nPjwvZz48L3N2Zz4=')] opacity-30" />
      </div>

      {/* Header */}
      <header className="sticky top-0 z-50 backdrop-blur-xl bg-white/5 border-b border-white/10">
        <div className="max-w-[1920px] mx-auto px-6 py-4 flex justify-between items-center">
          <div className="flex items-center gap-4">
            <div className="relative group">
              <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-emerald-400 via-teal-500 to-emerald-600 flex items-center justify-center shadow-lg shadow-emerald-500/30">
                <span className="text-white font-black text-xl">P</span>
              </div>
              <div className="absolute inset-0 rounded-2xl bg-gradient-to-br from-emerald-400 to-emerald-600 blur-lg opacity-40 group-hover:opacity-60 transition-opacity" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-white tracking-tight">PRANELY</h1>
              <p className="text-xs text-white/40">Sistema Documental Maestro</p>
            </div>
          </div>
          
          <div className="flex items-center gap-4">
            {/* Search */}
            <div className="hidden md:flex items-center gap-2 px-4 py-2 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-md">
              <svg className="w-4 h-4 text-white/40" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
              <input 
                type="text" 
                placeholder="Buscar movimiento..." 
                className="bg-transparent text-white/70 placeholder-white/40 text-sm focus:outline-none w-48"
              />
              <kbd className="hidden lg:inline px-1.5 py-0.5 text-xs text-white/30 bg-white/5 rounded">⌘K</kbd>
            </div>

            {/* Notifications */}
            <button className="relative p-3 rounded-2xl bg-white/5 hover:bg-white/10 border border-white/10 backdrop-blur-md transition-colors">
              <svg className="w-5 h-5 text-white/60" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
              </svg>
              {alerts.filter(a => a.status === "open").length > 0 && (
                <span className="absolute -top-1 -right-1 w-5 h-5 bg-rose-500 rounded-full text-xs flex items-center justify-center text-white font-bold">
                  {alerts.filter(a => a.status === "open").length}
                </span>
              )}
            </button>

            {/* Role Badge - USANDO PERMISOS REALES */}
            <div className="px-4 py-2 rounded-2xl bg-white/10 backdrop-blur-md border border-white/10">
              <span className="text-sm font-medium text-white/80">{organization?.name || 'Organización'}</span>
              <span className={`
                ml-2 px-2 py-0.5 rounded-full text-xs font-bold uppercase
                ${permissions.role === 'owner' ? 'bg-amber-500/30 text-amber-300' : ''}
                ${permissions.role === 'admin' ? 'bg-emerald-500/30 text-emerald-300' : ''}
                ${permissions.role === 'member' ? 'bg-blue-500/30 text-blue-300' : ''}
                ${permissions.role === 'viewer' ? 'bg-gray-500/30 text-gray-300' : ''}
              `}>
                {permissions.role}
              </span>
            </div>
            
            {/* User */}
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-2xl bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center text-white font-bold shadow-lg">
                {user?.full_name?.[0]?.toUpperCase() || user?.email?.[0]?.toUpperCase() || 'U'}
              </div>
              <div className="hidden md:block">
                <p className="text-sm font-medium text-white">
                  {user?.full_name || user?.email || 'Usuario'}
                </p>
                <p className="text-xs text-white/40">
                  {user?.email || `Usuario #${user?.id || '?'}`}
                </p>
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
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-[1920px] mx-auto px-6 py-8">
        {/* Page Header */}
        <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4 mb-8">
          <div>
            <h2 className="text-3xl font-bold text-white mb-1">
              Bienvenido{user?.full_name ? `, ${user.full_name}` : ""} 👋
            </h2>
            <div className="flex items-center gap-3 text-white/50 flex-wrap">
              <span>Dashboard de residuos</span>
              <span className="w-1 h-1 bg-white/30 rounded-full" />
              <span>Actualizado {lastRefresh.toLocaleTimeString("es-MX", { hour: '2-digit', minute: '2-digit' })}</span>
              {pollingIndicator && (
                <span className="flex items-center gap-1 text-emerald-400">
                  <div className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse" />
                  Sincronizando...
                </span>
              )}
              {dataSource === "mock" && (
                <span className="flex items-center gap-1 text-amber-400/60">
                  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  Demo
                </span>
              )}
            </div>
          </div>
          
          <div className="flex items-center gap-3">
            <button
              onClick={fetchData}
              className="group px-5 py-3 rounded-2xl bg-white/5 hover:bg-white/10 border border-white/10 backdrop-blur-md transition-all"
            >
              <div className="flex items-center gap-3">
                <svg className={`w-5 h-5 text-white/60 ${loading ? 'animate-spin' : 'group-hover:rotate-180 transition-transform duration-500'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                <span className="text-sm font-medium text-white/80">Actualizar</span>
              </div>
            </button>
            
            {permissions.canReview && (
              <button className="hidden md:flex px-5 py-3 rounded-2xl bg-gradient-to-r from-emerald-500 to-teal-500 text-white font-semibold shadow-lg shadow-emerald-500/30 hover:shadow-emerald-500/50 transition-all">
                <div className="flex items-center gap-3">
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  <span>Exportar</span>
                </div>
              </button>
            )}
          </div>
        </div>

        {/* Error State */}
        {error && (
          <div className="mb-6 p-4 rounded-2xl bg-rose-500/10 border border-rose-500/20 backdrop-blur-md flex items-center gap-4">
            <div className="p-2 rounded-xl bg-rose-500/20">
              <svg className="w-6 h-6 text-rose-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div>
              <p className="font-semibold text-rose-300">Error al cargar datos</p>
              <p className="text-sm text-rose-400/80">{error}</p>
            </div>
          </div>
        )}

        {/* Main Grid: KPIs + Table + Sidebar */}
        <div className="flex flex-col xl:flex-row gap-8">
          {/* Main Column */}
          <div className="flex-1 min-w-0 space-y-8">
            {/* KPI Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
              <KpiCard
                title="Total Movimientos"
                value={stats?.total || 0}
                subtitle="este mes"
                color="emerald"
                trend={12}
                loading={loading}
                icon={
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                }
              />
              <KpiCard
                title="Pendientes"
                value={stats?.pending || 0}
                subtitle="por revisar"
                color="amber"
                trend={-5}
                loading={loading}
                icon={
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                }
              />
              <KpiCard
                title="En Revisión"
                value={stats?.in_review || 0}
                subtitle="procesando"
                color="blue"
                trend={8}
                loading={loading}
                icon={
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                  </svg>
                }
              />
              <KpiCard
                title="Validados"
                value={stats?.validated || 0}
                subtitle="completados"
                color="violet"
                trend={23}
                loading={loading}
                icon={
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                }
              />
            </div>

            {/* Movements Table - USANDO PERMISOS REALES */}
            <MovementsTable
              movements={movements}
              loading={loading}
              permissions={permissions}
              onRefresh={fetchData}
              onApprove={handleApprove}
              onReject={handleReject}
              onView={(m) => console.log("View:", m)}
              onEdit={(m) => console.log("Edit:", m)}
              onArchive={(id) => console.log("Archive:", id)}
            />
          </div>

          {/* Sidebar */}
          <Sidebar
            recentActivity={activity}
            alerts={alerts}
            loading={loading}
          />
        </div>

        {/* Polling Indicator */}
        <div className="mt-8 flex items-center justify-center gap-3 text-white/30 text-sm">
          <div className="relative">
            <div className="w-2 h-2 bg-emerald-400 rounded-full animate-ping" />
            <div className="absolute inset-0 w-2 h-2 bg-emerald-400 rounded-full" />
          </div>
          <span>Actualización automática cada 30 segundos</span>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-white/5 py-6 mt-8">
        <div className="max-w-[1920px] mx-auto px-6 flex flex-col md:flex-row justify-between items-center gap-4 text-sm text-white/30">
          <span>© 2024 PRANELY. Sistema Documental Maestro para Gestión de Residuos.</span>
          <div className="flex items-center gap-6">
            <span>Versión 1.19.0</span>
            <span>•</span>
            <span>NOM-052-SEMARNAT-2005</span>
            <span>•</span>
            <span>México</span>
          </div>
        </div>
      </footer>

      {/* FAB */}
      <FAB
        canCreate={permissions.canEdit}
        onAddMovement={() => console.log("Add movement")}
        onUploadDocument={() => console.log("Upload document")}
      />
    </div>
  );
}

export function DashboardKPI() {
  return (
    <ProtectedRoute fallbackPath="/login">
      <DashboardContent />
    </ProtectedRoute>
  );
}

export default DashboardKPI;
