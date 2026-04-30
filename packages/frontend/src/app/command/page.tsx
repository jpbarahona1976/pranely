// Command Center - Admin panel for configuration, operators, quotas, feature flags
// FIX 8B: Director role support, Member read-only access
"use client";

import { useEffect, useState, useCallback } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { ProtectedRoute } from "@/components/ProtectedRoute";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// FIX 8B: Types updated with Director role
type UserRole = "owner" | "admin" | "member" | "viewer" | "director";

interface Operator {
  id: number;
  user_id: number;
  email: string;
  full_name: string | null;
  role: string;
  is_active: boolean;
  created_at: string;
  permissions: string[];
}

interface TenantConfig {
  organization_id: number;
  name: string;
  industry: string | null;
  segment: string | null;
  locale: string;
  timezone: string;
}

interface QuotaInfo {
  plan_code: string;
  plan_name: string;
  doc_limit: number;
  docs_used: number;
  docs_remaining: number;
  period: string;
  status: string;
}

interface FeatureFlag {
  key: string;
  enabled: boolean;
  description: string | null;
}

interface AuditEntry {
  id: number;
  action: string;
  resource_type: string;
  result: string;
  user_email: string | null;
  timestamp: string;
}

interface CommandStats {
  total_operators: number;
  active_operators: number;
  current_plan: string;
  doc_usage_percent: number;
  pending_actions: number;
  recent_changes: number;
}

// FIX 8B: API helper with proper error handling
async function fetchCommand<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const token = localStorage.getItem("pranely_token");
  const response = await fetch(`${API_URL}/api/v1${endpoint}`, {
    ...options,
    headers: {
      Authorization: `Bearer ${token}`,
      ...options?.headers,
    },
  });
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Error" }));
    const message = error.detail?.detail || error.detail || "API Error";
    throw new Error(message);
  }
  
  return response.json();
}

// FIX 8B: Role-based permission helpers
function canViewCommandCenter(role: string): boolean {
  return ["owner", "admin", "director", "member"].includes(role);
}

function canMutateCommandCenter(role: string): boolean {
  return ["owner", "admin", "director"].includes(role);
}

function getRoleLabel(role: string): string {
  const labels: Record<string, string> = {
    owner: "Owner",
    admin: "Admin",
    director: "Director",
    member: "Member",
    viewer: "Viewer",
  };
  return labels[role] || role;
}

// Stats Card Component
function StatCard({ title, value, subtitle, color }: { title: string; value: number | string; subtitle?: string; color: "emerald" | "amber" | "blue" | "violet" | "rose" }) {
  const colorMap: Record<string, { bg: string; border: string; text: string }> = {
    emerald: { bg: "from-emerald-500/20 to-teal-500/10", border: "border-emerald-500/30", text: "text-emerald-400" },
    amber: { bg: "from-amber-500/20 to-orange-500/10", border: "border-amber-500/30", text: "text-amber-400" },
    blue: { bg: "from-blue-500/20 to-indigo-500/10", border: "border-blue-500/30", text: "text-blue-400" },
    violet: { bg: "from-violet-500/20 to-purple-500/10", border: "border-violet-500/30", text: "text-violet-400" },
    rose: { bg: "from-rose-500/20 to-red-500/10", border: "border-rose-500/30", text: "text-rose-400" },
  };
  const styles = colorMap[color];
  
  return (
    <div className={`bg-gradient-to-br ${styles.bg} border ${styles.border} backdrop-blur-xl rounded-2xl p-5 shadow-lg`}>
      <p className="text-white/50 text-sm font-medium mb-1">{title}</p>
      <p className="text-3xl font-bold text-white">{value}</p>
      {subtitle && <p className={`text-xs mt-1 ${styles.text}`}>{subtitle}</p>}
    </div>
  );
}

// Section Header
function SectionHeader({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <div className="mb-6">
      <h3 className="text-lg font-semibold text-white">{title}</h3>
      {subtitle && <p className="text-sm text-white/40 mt-1">{subtitle}</p>}
    </div>
  );
}

// Toggle Switch with proper permissions
function Toggle({ enabled, onChange, disabled }: { enabled: boolean; onChange: (v: boolean) => void; disabled?: boolean }) {
  return (
    <button
      onClick={() => !disabled && onChange(!enabled)}
      disabled={disabled}
      className={`relative w-12 h-6 rounded-full transition-colors ${
        enabled ? "bg-emerald-500" : "bg-white/20"
      } ${disabled ? "opacity-50 cursor-not-allowed" : "hover:opacity-80"}`}
      title={disabled ? "Solo owner/admin/director pueden modificar" : "Click para togglear"}
    >
      <span
        className={`absolute top-1 w-4 h-4 bg-white rounded-full shadow transition-transform ${
          enabled ? "left-7" : "left-1"
        }`}
      />
    </button>
  );
}

// Role Badge with Director support
function RoleBadge({ role }: { role: string }) {
  const colors: Record<string, string> = {
    owner: "bg-amber-500/30 text-amber-300",
    admin: "bg-emerald-500/30 text-emerald-300",
    director: "bg-violet-500/30 text-violet-300",  // FIX 8B: Director color
    member: "bg-blue-500/30 text-blue-300",
    viewer: "bg-gray-500/30 text-gray-300",
  };
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-bold uppercase ${colors[role] || colors.viewer}`}>
      {role}
    </span>
  );
}

// Tab Navigation
function TabNav({ tabs, active, onChange }: { tabs: { id: string; label: string }[]; active: string; onChange: (id: string) => void }) {
  return (
    <div className="flex gap-1 p-1 bg-white/5 backdrop-blur-xl rounded-2xl border border-white/10 overflow-x-auto">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          onClick={() => onChange(tab.id)}
          className={`px-4 py-2 rounded-xl text-sm font-medium transition-all whitespace-nowrap ${
            active === tab.id
              ? "bg-white/20 text-white border border-white/20"
              : "text-white/50 hover:text-white/70 hover:bg-white/5"
          }`}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}

// Operators Tab
function OperatorsTab({ operators, loading, onRefresh, canManage }: { operators: Operator[]; loading: boolean; onRefresh: () => void; canManage: boolean }) {
  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <div>
          <p className="text-white/60 text-sm">{operators.length} operadores</p>
        </div>
        {canManage && (
          <button
            onClick={onRefresh}
            className="px-4 py-2 rounded-xl bg-emerald-500/20 border border-emerald-500/30 text-emerald-400 text-sm font-medium hover:bg-emerald-500/30 transition-colors"
          >
            + Invitar operador
          </button>
        )}
      </div>
      
      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-16 rounded-xl bg-white/5 animate-pulse" />
          ))}
        </div>
      ) : (
        <div className="space-y-2">
          {operators.map((op) => (
            <div
              key={op.id}
              className="flex items-center justify-between p-4 bg-white/5 backdrop-blur-md rounded-xl border border-white/10 hover:bg-white/10 transition-colors"
            >
              <div className="flex items-center gap-4">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center text-white font-bold">
                  {op.full_name?.[0]?.toUpperCase() || op.email[0].toUpperCase()}
                </div>
                <div>
                  <p className="text-white font-medium">{op.full_name || op.email}</p>
                  <p className="text-white/40 text-sm">{op.email}</p>
                </div>
              </div>
              <div className="flex items-center gap-4">
                <RoleBadge role={op.role} />
                <span className={`w-2 h-2 rounded-full ${op.is_active ? "bg-emerald-400" : "bg-gray-400"}`} />
                {canManage && op.role !== "owner" && op.role !== "director" && (
                  <button className="text-white/40 hover:text-rose-400 text-sm">✕</button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// Config Tab
function ConfigTab({ config, loading, onSave, canManage }: { config: TenantConfig | null; loading: boolean; onSave: (data: Partial<TenantConfig>) => void; canManage: boolean }) {
  const [name, setName] = useState("");
  const [industry, setIndustry] = useState("");
  const [segment, setSegment] = useState("");
  
  useEffect(() => {
    if (config) {
      setName(config.name);
      setIndustry(config.industry || "");
      setSegment(config.segment || "");
    }
  }, [config]);
  
  const handleSave = () => {
    onSave({ name, industry, segment });
  };
  
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <label className="block text-white/60 text-sm mb-2">Nombre de organización</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            disabled={!canManage}
            className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-white/30 focus:outline-none focus:border-emerald-500/50 disabled:opacity-50"
            placeholder="Nombre de la organización"
          />
        </div>
        <div>
          <label className="block text-white/60 text-sm mb-2">Industria</label>
          <input
            type="text"
            value={industry}
            onChange={(e) => setIndustry(e.target.value)}
            disabled={!canManage}
            className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-white/30 focus:outline-none focus:border-emerald-500/50 disabled:opacity-50"
            placeholder="Ej: Manufactura"
          />
        </div>
        <div>
          <label className="block text-white/60 text-sm mb-2">Segmento</label>
          <select
            value={segment}
            onChange={(e) => setSegment(e.target.value)}
            disabled={!canManage}
            className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white focus:outline-none focus:border-emerald-500/50 disabled:opacity-50"
          >
            <option value="">Seleccionar...</option>
            <option value="generator">Generador</option>
            <option value="gestor">Gestor</option>
            <option value="transportista">Transportista</option>
          </select>
        </div>
        <div>
          <label className="block text-white/60 text-sm mb-2">Zona horaria</label>
          <input
            type="text"
            value="America/Mexico_City"
            disabled
            className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white/40 disabled:opacity-50"
          />
        </div>
      </div>
      
      {canManage ? (
        <button
          onClick={handleSave}
          className="px-6 py-3 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-500 text-white font-semibold shadow-lg shadow-emerald-500/30 hover:shadow-emerald-500/50 transition-all"
        >
          Guardar cambios
        </button>
      ) : (
        <p className="text-sm text-white/40 italic">Solo owner, admin o director pueden modificar la configuración</p>
      )}
    </div>
  );
}

// Quotas Tab
function QuotasTab({ quota, loading }: { quota: QuotaInfo | null; loading: boolean }) {
  if (loading) {
    return <div className="h-48 rounded-xl bg-white/5 animate-pulse" />;
  }
  
  if (!quota) {
    return (
      <div className="text-center py-12 text-white/40">
        No hay información de cuotas disponible
      </div>
    );
  }
  
  const usagePercent = (quota.docs_used / quota.doc_limit) * 100;
  
  return (
    <div className="space-y-6">
      <div className="bg-white/5 backdrop-blur-xl rounded-2xl border border-white/10 p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <p className="text-white/60 text-sm">Plan actual</p>
            <p className="text-2xl font-bold text-white">{quota.plan_name}</p>
          </div>
          <span className={`px-3 py-1 rounded-full text-sm font-medium ${
            quota.status === "active" ? "bg-emerald-500/20 text-emerald-400" : "bg-amber-500/20 text-amber-400"
          }`}>
            {quota.status}
          </span>
        </div>
        
        <div className="space-y-3">
          <div className="flex justify-between text-sm">
            <span className="text-white/60">Documentos usados</span>
            <span className="text-white font-medium">{quota.docs_used} / {quota.doc_limit}</span>
          </div>
          <div className="h-3 bg-white/10 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all ${
                usagePercent > 80 ? "bg-rose-500" : usagePercent > 60 ? "bg-amber-500" : "bg-emerald-500"
              }`}
              style={{ width: `${Math.min(usagePercent, 100)}%` }}
            />
          </div>
          <p className="text-right text-sm text-white/40">{Math.round(usagePercent)}% utilizado</p>
        </div>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white/5 backdrop-blur-md rounded-xl p-4 border border-white/10">
          <p className="text-white/40 text-sm">Restantes</p>
          <p className="text-2xl font-bold text-white">{quota.docs_remaining}</p>
        </div>
        <div className="bg-white/5 backdrop-blur-md rounded-xl p-4 border border-white/10">
          <p className="text-white/40 text-sm">Límite mensual</p>
          <p className="text-2xl font-bold text-white">{quota.doc_limit}</p>
        </div>
        <div className="bg-white/5 backdrop-blur-md rounded-xl p-4 border border-white/10">
          <p className="text-white/40 text-sm">Período</p>
          <p className="text-2xl font-bold text-white capitalize">{quota.period}</p>
        </div>
      </div>
    </div>
  );
}

// Features Tab with proper permissions
function FeaturesTab({ flags, loading, onToggle, canManage }: { flags: FeatureFlag[]; loading: boolean; onToggle: (key: string, enabled: boolean) => void; canManage: boolean }) {
  return (
    <div className="space-y-3">
      {loading ? (
        [1, 2, 3].map((i) => <div key={i} className="h-16 rounded-xl bg-white/5 animate-pulse" />)
      ) : (
        flags.map((flag) => (
          <div
            key={flag.key}
            className="flex items-center justify-between p-4 bg-white/5 backdrop-blur-md rounded-xl border border-white/10"
          >
            <div>
              <p className="text-white font-medium capitalize">{flag.key.replace(/_/g, " ")}</p>
              <p className="text-white/40 text-sm">{flag.description || "Sin descripción"}</p>
            </div>
            <Toggle
              enabled={flag.enabled}
              onChange={(v) => onToggle(flag.key, v)}
              disabled={!canManage}
            />
          </div>
        ))
      )}
      
      {!canManage && (
        <p className="text-sm text-white/40 italic mt-4">Solo owner, admin o director pueden modificar las funciones</p>
      )}
    </div>
  );
}

// Audit Tab
function AuditTab({ logs, loading }: { logs: AuditEntry[]; loading: boolean }) {
  return (
    <div className="space-y-2">
      {loading ? (
        [1, 2, 3].map((i) => <div key={i} className="h-12 rounded-xl bg-white/5 animate-pulse" />)
      ) : logs.length === 0 ? (
        <div className="text-center py-12 text-white/40">Sin registros de auditoría</div>
      ) : (
        logs.map((log) => (
          <div
            key={log.id}
            className="flex items-center gap-4 p-3 bg-white/5 rounded-xl border border-white/10"
          >
            <span className={`w-2 h-2 rounded-full ${log.result === "success" ? "bg-emerald-400" : "bg-rose-400"}`} />
            <div className="flex-1 min-w-0">
              <p className="text-white text-sm truncate">
                <span className="font-medium">{log.action}</span>
                <span className="text-white/40"> — {log.resource_type}</span>
              </p>
            </div>
            <span className="text-white/40 text-xs">{log.user_email || "Sistema"}</span>
            <span className="text-white/30 text-xs">
              {new Date(log.timestamp).toLocaleString("es-MX")}
            </span>
          </div>
        ))
      )}
    </div>
  );
}

// Access Denied Component
function AccessDenied() {
  return (
    <div className="min-h-screen relative overflow-hidden flex items-center justify-center">
      <div className="absolute inset-0 -z-10">
        <div className="absolute inset-0 bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900" />
      </div>
      
      <div className="text-center p-8 bg-white/5 backdrop-blur-xl rounded-3xl border border-white/10">
        <div className="w-20 h-20 rounded-full bg-rose-500/20 flex items-center justify-center mx-auto mb-6">
          <svg className="w-10 h-10 text-rose-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m0 0v2m0-2h2m-2 0H10m4-8V5a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2h8a2 2 0 002-2v-3" />
          </svg>
        </div>
        <h2 className="text-2xl font-bold text-white mb-2">Acceso Denegado</h2>
        <p className="text-white/60 mb-4">
          Tu rol no tiene permisos para acceder al Command Center.
        </p>
        <p className="text-sm text-white/40">
          Roles permitidos: Owner, Admin, Director, Member (solo lectura)
        </p>
      </div>
    </div>
  );
}

// Main Content
function CommandCenterContent() {
  const { permissions } = useAuth();
  const [activeTab, setActiveTab] = useState("operators");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // FIX 8B: Determine permissions based on role
  const userRole = permissions.role;
  const canView = canViewCommandCenter(userRole);
  const canManage = canMutateCommandCenter(userRole);
  
  // Data states
  const [operators, setOperators] = useState<Operator[]>([]);
  const [config, setConfig] = useState<TenantConfig | null>(null);
  const [quota, setQuota] = useState<QuotaInfo | null>(null);
  const [flags, setFlags] = useState<FeatureFlag[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditEntry[]>([]);
  const [stats, setStats] = useState<CommandStats | null>(null);
  
  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [opsData, configData, quotaData, flagsData, auditData, statsData] = await Promise.all([
        fetchCommand<{ operators: Operator[]; total: number }>("/command/operators"),
        fetchCommand<TenantConfig>("/command/config"),
        fetchCommand<QuotaInfo>("/command/quotas"),
        fetchCommand<{ flags: FeatureFlag[]; total: number }>("/command/features"),
        fetchCommand<{ entries: AuditEntry[]; total: number }>("/command/audit?page=1&page_size=20"),
        fetchCommand<CommandStats>("/command/stats"),
      ]);
      setOperators(opsData.operators);
      setConfig(configData);
      setQuota(quotaData);
      setFlags(flagsData.flags);
      setAuditLogs(auditData.entries);
      setStats(statsData);
    } catch (err) {
      console.error("Error loading command center:", err);
      setError(err instanceof Error ? err.message : "Error al cargar datos");
    } finally {
      setLoading(false);
    }
  }, []);
  
  useEffect(() => {
    if (canView) {
      loadData();
    }
  }, [canView, loadData]);
  
  const handleToggleFeature = async (key: string, enabled: boolean) => {
    try {
      await fetchCommand(`/command/features/${key}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled }),
      });
      setFlags((prev) => prev.map((f) => (f.key === key ? { ...f, enabled } : f)));
    } catch (err) {
      console.error("Error toggling feature:", err);
    }
  };
  
  const handleSaveConfig = async (data: Partial<TenantConfig>) => {
    try {
      const response = await fetch(`${API_URL}/api/v1/command/config`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${localStorage.getItem("pranely_token")}`,
        },
        body: JSON.stringify(data),
      });
      if (response.ok) {
        loadData();
      }
    } catch (err) {
      console.error("Error saving config:", err);
    }
  };
  
  // FIX 8B: Show access denied for viewer
  if (!canView) {
    return <AccessDenied />;
  }
  
  const tabs = [
    { id: "operators", label: "Operadores" },
    { id: "config", label: "Configuración" },
    { id: "quotas", label: "Cuotas" },
    { id: "features", label: "Funciones" },
    { id: "audit", label: "Auditoría" },
  ];
  
  return (
    <div className="min-h-screen relative overflow-hidden">
      {/* Animated Background */}
      <div className="fixed inset-0 -z-10">
        <div className="absolute inset-0 bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900" />
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-violet-500/15 rounded-full blur-3xl animate-pulse" />
        <div className="absolute top-1/3 right-1/4 w-80 h-80 bg-emerald-500/10 rounded-full blur-3xl animate-pulse" style={{ animationDelay: '1s' }} />
        <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHZpZXdCb3g9IjAgMCA2MCA2MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48ZyBmaWxsPSJub25lIiBmaWxsLXJ1bGU9ImV2ZW5vZGQiPjxnIGZpbGw9IiNmZmZmZmYiIGZpbGwtb3BhY2l0eT0iMC4wMyI+PGNpcmNsZSBjeD0iMzAiIGN5PSIzMCIgcj0iMS41Ii8+PC9nPjwvZz48L3N2Zz4=')] opacity-30" />
      </div>
      
      {/* Header */}
      <header className="sticky top-0 z-50 backdrop-blur-xl bg-white/5 border-b border-white/10">
        <div className="max-w-[1920px] mx-auto px-6 py-4 flex justify-between items-center">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-violet-500 via-purple-600 to-violet-700 flex items-center justify-center shadow-lg shadow-violet-500/30">
              <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
            </div>
            <div>
              <h1 className="text-xl font-bold text-white tracking-tight">Command Center</h1>
              <p className="text-xs text-white/40">Panel de administración</p>
            </div>
          </div>
          
          {/* FIX 8B: Show role badge */}
          <div className="flex items-center gap-4">
            <span className={`px-3 py-1 rounded-full text-sm font-medium ${
              userRole === "owner" ? "bg-amber-500/30 text-amber-300" :
              userRole === "admin" ? "bg-emerald-500/30 text-emerald-300" :
              userRole === "director" ? "bg-violet-500/30 text-violet-300" :
              "bg-blue-500/30 text-blue-300"
            }`}>
              {getRoleLabel(userRole)} {canManage ? "(lectura/escritura)" : "(solo lectura)"}
            </span>
            
            <button
              onClick={loadData}
              className="p-3 rounded-2xl bg-white/5 hover:bg-white/10 border border-white/10 backdrop-blur-md transition-all"
              title="Actualizar"
            >
              <svg className={`w-5 h-5 text-white/60 ${loading ? "animate-spin" : ""}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            </button>
          </div>
        </div>
      </header>
      
      {/* Main Content */}
      <main className="max-w-[1920px] mx-auto px-6 py-8">
        {/* Error State */}
        {error && (
          <div className="mb-6 p-4 rounded-2xl bg-rose-500/10 border border-rose-500/20 backdrop-blur-md flex items-center gap-4">
            <svg className="w-6 h-6 text-rose-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p className="text-rose-300 font-medium">{error}</p>
          </div>
        )}
        
        {/* Stats Grid */}
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-8">
            <StatCard title="Operadores" value={stats.total_operators} subtitle={`${stats.active_operators} activos`} color="blue" />
            <StatCard title="Plan" value={stats.current_plan.toUpperCase()} color="violet" />
            <StatCard title="Uso docs" value={`${stats.doc_usage_percent}%`} color={stats.doc_usage_percent > 80 ? "rose" : "emerald"} />
            <StatCard title="Pendientes" value={stats.pending_actions} color="amber" />
            <StatCard title="Cambios" value={stats.recent_changes} subtitle="esta semana" color="blue" />
            <StatCard title="Acceso" value={getRoleLabel(userRole)} color="violet" />
          </div>
        )}
        
        {/* Tab Navigation */}
        <TabNav tabs={tabs} active={activeTab} onChange={setActiveTab} />
        
        {/* Tab Content */}
        <div className="mt-6">
          {activeTab === "operators" && (
            <OperatorsTab operators={operators} loading={loading} onRefresh={loadData} canManage={canManage} />
          )}
          {activeTab === "config" && (
            <ConfigTab config={config} loading={loading} onSave={handleSaveConfig} canManage={canManage} />
          )}
          {activeTab === "quotas" && (
            <QuotasTab quota={quota} loading={loading} />
          )}
          {activeTab === "features" && (
            <FeaturesTab flags={flags} loading={loading} onToggle={handleToggleFeature} canManage={canManage} />
          )}
          {activeTab === "audit" && (
            <AuditTab logs={auditLogs} loading={loading} />
          )}
        </div>
      </main>
      
      {/* Footer */}
      <footer className="border-t border-white/5 py-6 mt-8">
        <div className="max-w-[1920px] mx-auto px-6 flex justify-between items-center text-sm text-white/30">
          <span>© 2024 PRANELY — Command Center</span>
          <div className="flex items-center gap-4">
            <span>•</span>
            <span>Owner/Admin/Director: lectura/escritura | Member: solo lectura</span>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default function CommandCenterPage() {
  return (
    <ProtectedRoute fallbackPath="/login">
      <CommandCenterContent />
    </ProtectedRoute>
  );
}

export { CommandCenterContent };