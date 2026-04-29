// Sidebar - Panel lateral glassmorphism con Recent Activity y Alerts
"use client";

import { useState } from "react";

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

interface SidebarProps {
  recentActivity: RecentActivity[];
  alerts: RegulatoryAlert[];
  loading?: boolean;
  collapsed?: boolean;
  onToggle?: () => void;
}

const activityIcons = {
  created: { icon: "➕", bg: "bg-emerald-500/20", color: "text-emerald-400" },
  approved: { icon: "✅", bg: "bg-blue-500/20", color: "text-blue-400" },
  rejected: { icon: "❌", bg: "bg-rose-500/20", color: "text-rose-400" },
  updated: { icon: "📝", bg: "bg-amber-500/20", color: "text-amber-400" },
  archived: { icon: "📦", bg: "bg-violet-500/20", color: "text-violet-400" },
};

const severityColors = {
  low: { bg: "bg-emerald-500/20", border: "border-emerald-500/30", text: "text-emerald-400", label: "Bajo" },
  medium: { bg: "bg-amber-500/20", border: "border-amber-500/30", text: "text-amber-400", label: "Medio" },
  high: { bg: "bg-orange-500/20", border: "border-orange-500/30", text: "text-orange-400", label: "Alto" },
  critical: { bg: "bg-rose-500/20", border: "border-rose-500/30", text: "text-rose-400", label: "Crítico" },
};

function ActivityItem({ activity }: { activity: RecentActivity }) {
  const styles = activityIcons[activity.action];
  
  return (
    <div className="flex items-start gap-3 p-3 rounded-xl hover:bg-white/5 transition-colors group">
      <div className={`w-8 h-8 rounded-lg ${styles.bg} flex items-center justify-center text-sm flex-shrink-0`}>
        {styles.icon}
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm text-white/80">
          <span className="font-medium">{activity.user}</span>
          <span className="text-white/50"> {activity.action === 'created' ? 'creó' : activity.action === 'approved' ? 'aprobó' : activity.action === 'rejected' ? 'rechazó' : activity.action === 'updated' ? 'actualizó' : 'archivó'}</span>
        </p>
        <p className="text-xs text-white/40 truncate">{activity.manifest}</p>
        {activity.details && (
          <p className="text-xs text-white/30 mt-0.5 truncate">{activity.details}</p>
        )}
      </div>
      <span className="text-xs text-white/30 flex-shrink-0">
        {formatTimeAgo(activity.timestamp)}
      </span>
    </div>
  );
}

function AlertItem({ alert }: { alert: RegulatoryAlert }) {
  const styles = severityColors[alert.severity];
  
  return (
    <div className={`p-3 rounded-xl ${styles.bg} border ${styles.border} backdrop-blur-md`}>
      <div className="flex items-start justify-between gap-2 mb-2">
        <span className={`text-xs font-bold ${styles.text} uppercase`}>
          {alert.norma}
        </span>
        <span className={`text-xs font-medium ${styles.text}`}>
          {styles.label}
        </span>
      </div>
      <h4 className="text-sm font-semibold text-white mb-1">{alert.title}</h4>
      <p className="text-xs text-white/50 line-clamp-2 mb-2">{alert.description}</p>
      {alert.due_date && (
        <div className="flex items-center gap-1 text-xs text-white/40">
          <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
          <span>Vence: {new Date(alert.due_date).toLocaleDateString("es-MX")}</span>
        </div>
      )}
      {alert.status === "open" && (
        <button className={`mt-2 text-xs font-medium ${styles.text} hover:underline`}>
          Ver detalles →
        </button>
      )}
    </div>
  );
}

function formatTimeAgo(timestamp: string): string {
  const now = new Date();
  const then = new Date(timestamp);
  const diffMs = now.getTime() - then.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffMins < 1) return "ahora";
  if (diffMins < 60) return `${diffMins}m`;
  if (diffHours < 24) return `${diffHours}h`;
  if (diffDays < 7) return `${diffDays}d`;
  return then.toLocaleDateString("es-MX", { day: "numeric", month: "short" });
}

function SkeletonActivity() {
  return (
    <div className="flex items-start gap-3 p-3">
      <div className="w-8 h-8 rounded-lg bg-white/10 animate-pulse" />
      <div className="flex-1 space-y-2">
        <div className="h-4 w-24 rounded bg-white/10 animate-pulse" />
        <div className="h-3 w-16 rounded bg-white/10 animate-pulse" />
      </div>
    </div>
  );
}

export function Sidebar({ recentActivity, alerts, loading = false, collapsed = false }: SidebarProps) {
  const [activeTab, setActiveTab] = useState<"activity" | "alerts">("activity");

  if (collapsed) {
    return (
      <div className="hidden xl:flex flex-col gap-4 w-16">
        <button 
          onClick={() => setActiveTab("activity")}
          className={`p-3 rounded-xl backdrop-blur-md transition-all ${activeTab === "activity" ? "bg-white/20 border border-white/20" : "bg-white/5 border border-transparent hover:bg-white/10"}`}
          title="Actividad"
        >
          <svg className="w-5 h-5 text-white/70" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </button>
        <button 
          onClick={() => setActiveTab("alerts")}
          className={`p-3 rounded-xl backdrop-blur-md transition-all relative ${activeTab === "alerts" ? "bg-white/20 border border-white/20" : "bg-white/5 border border-transparent hover:bg-white/10"}`}
          title="Alertas"
        >
          <svg className="w-5 h-5 text-white/70" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
          </svg>
          {alerts.filter(a => a.status === "open").length > 0 && (
            <span className="absolute -top-1 -right-1 w-4 h-4 bg-rose-500 rounded-full text-xs flex items-center justify-center text-white font-bold">
              {alerts.filter(a => a.status === "open").length}
            </span>
          )}
        </button>
      </div>
    );
  }

  return (
    <aside className="hidden lg:block w-80 xl:w-96 flex-shrink-0">
      <div className="sticky top-24 space-y-6">
        {/* Activity & Alerts Tabs */}
        <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-3xl overflow-hidden shadow-2xl">
          {/* Tab Headers */}
          <div className="flex border-b border-white/10">
            <button
              onClick={() => setActiveTab("activity")}
              className={`flex-1 px-4 py-4 text-sm font-medium transition-all ${
                activeTab === "activity" 
                  ? "text-white bg-white/10 border-b-2 border-emerald-400" 
                  : "text-white/50 hover:text-white/70"
              }`}
            >
              <div className="flex items-center justify-center gap-2">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                Actividad
              </div>
            </button>
            <button
              onClick={() => setActiveTab("alerts")}
              className={`flex-1 px-4 py-4 text-sm font-medium transition-all relative ${
                activeTab === "alerts" 
                  ? "text-white bg-white/10 border-b-2 border-amber-400" 
                  : "text-white/50 hover:text-white/70"
              }`}
            >
              <div className="flex items-center justify-center gap-2">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
                </svg>
                Alertas
                {alerts.filter(a => a.status === "open").length > 0 && (
                  <span className="w-5 h-5 bg-rose-500 rounded-full text-xs flex items-center justify-center text-white font-bold">
                    {alerts.filter(a => a.status === "open").length}
                  </span>
                )}
              </div>
            </button>
          </div>

          {/* Tab Content */}
          <div className="p-4 max-h-[500px] overflow-y-auto">
            {activeTab === "activity" && (
              <div className="space-y-1">
                {loading ? (
                  [...Array(5)].map((_, i) => <SkeletonActivity key={i} />)
                ) : recentActivity.length > 0 ? (
                  recentActivity.map((activity) => (
                    <ActivityItem key={activity.id} activity={activity} />
                  ))
                ) : (
                  <div className="text-center py-8">
                    <p className="text-white/40">Sin actividad reciente</p>
                  </div>
                )}
              </div>
            )}

            {activeTab === "alerts" && (
              <div className="space-y-3">
                {loading ? (
                  [...Array(3)].map((_, i) => (
                    <div key={i} className="h-24 rounded-xl bg-white/10 animate-pulse" />
                  ))
                ) : alerts.length > 0 ? (
                  alerts.map((alert) => (
                    <AlertItem key={alert.id} alert={alert} />
                  ))
                ) : (
                  <div className="text-center py-8">
                    <p className="text-white/40">Sin alertas pendientes</p>
                    <span className="text-3xl mt-2 block">✨</span>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Quick Stats Card */}
        <div className="bg-gradient-to-br from-violet-500/20 to-purple-500/10 backdrop-blur-xl border border-violet-500/30 rounded-3xl p-6 shadow-2xl">
          <h4 className="text-sm font-semibold text-white/50 uppercase tracking-wider mb-4">
            Resumen rápido
          </h4>
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-white/60 text-sm">Docs este mes</span>
              <span className="text-white font-bold">24</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-white/60 text-sm">Pendientes</span>
              <span className="text-amber-400 font-bold">7</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-white/60 text-sm">Vencen pronto</span>
              <span className="text-rose-400 font-bold">2</span>
            </div>
          </div>
        </div>
      </div>
    </aside>
  );
}
