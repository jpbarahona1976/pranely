// KpiCard - Cards de métricas glassmorphism premium
import { ReactNode } from "react";

interface KpiCardProps {
  title: string;
  value: number;
  subtitle?: string;
  icon: ReactNode;
  color: "emerald" | "amber" | "blue" | "violet" | "rose";
  trend?: number;
  loading?: boolean;
  onClick?: () => void;
}

export function KpiCard({ 
  title, 
  value, 
  subtitle, 
  icon, 
  color, 
  trend, 
  loading = false,
  onClick 
}: KpiCardProps) {
  const colorMap = {
    emerald: { 
      gradient: "from-emerald-500/30 to-teal-500/10", 
      border: "border-emerald-500/40",
      glow: "hover:shadow-emerald-500/30",
      icon: "text-emerald-400",
      iconBg: "bg-emerald-500/20",
      orb: "from-emerald-500/40",
      trendUp: "text-emerald-400",
      trendDown: "text-rose-400",
    },
    amber: { 
      gradient: "from-amber-500/30 to-orange-500/10", 
      border: "border-amber-500/40",
      glow: "hover:shadow-amber-500/30",
      icon: "text-amber-400",
      iconBg: "bg-amber-500/20",
      orb: "from-amber-500/40",
      trendUp: "text-emerald-400",
      trendDown: "text-rose-400",
    },
    blue: { 
      gradient: "from-blue-500/30 to-indigo-500/10", 
      border: "border-blue-500/40",
      glow: "hover:shadow-blue-500/30",
      icon: "text-blue-400",
      iconBg: "bg-blue-500/20",
      orb: "from-blue-500/40",
      trendUp: "text-emerald-400",
      trendDown: "text-rose-400",
    },
    violet: { 
      gradient: "from-violet-500/30 to-purple-500/10", 
      border: "border-violet-500/40",
      glow: "hover:shadow-violet-500/30",
      icon: "text-violet-400",
      iconBg: "bg-violet-500/20",
      orb: "from-violet-500/40",
      trendUp: "text-emerald-400",
      trendDown: "text-rose-400",
    },
    rose: { 
      gradient: "from-rose-500/30 to-red-500/10", 
      border: "border-rose-500/40",
      glow: "hover:shadow-rose-500/30",
      icon: "text-rose-400",
      iconBg: "bg-rose-500/20",
      orb: "from-rose-500/40",
      trendUp: "text-emerald-400",
      trendDown: "text-rose-400",
    },
  };

  const styles = colorMap[color];

  if (loading) {
    return (
      <div className={`
        bg-gradient-to-br ${styles.gradient}
        border ${styles.border}
        backdrop-blur-xl
        rounded-3xl p-6
        shadow-2xl ${styles.glow}
      `}>
        <div className="animate-pulse space-y-4">
          <div className="flex justify-between">
            <div className="w-12 h-12 rounded-2xl bg-white/10" />
            <div className="w-12 h-4 rounded bg-white/10" />
          </div>
          <div className="space-y-2">
            <div className="h-4 w-20 rounded bg-white/10" />
            <div className="h-8 w-16 rounded bg-white/10" />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div 
      onClick={onClick}
      className={`
        relative overflow-hidden cursor-pointer
        bg-gradient-to-br ${styles.gradient}
        border ${styles.border}
        backdrop-blur-xl
        rounded-3xl p-6
        shadow-2xl ${styles.glow}
        transition-all duration-300
        hover:scale-[1.02] hover:shadow-3xl
        active:scale-[0.98]
        group
      `}>
      {/* Glow orb */}
      <div className={`absolute -top-16 -right-16 w-32 h-32 rounded-full bg-gradient-to-r ${styles.orb} blur-3xl opacity-50 group-hover:opacity-75 transition-opacity`} />
      
      <div className="relative z-10">
        {/* Header */}
        <div className="flex items-start justify-between mb-4">
          <div className={`p-3 rounded-2xl ${styles.iconBg} backdrop-blur-md border border-white/10`}>
            <div className={styles.icon}>{icon}</div>
          </div>
          
          {trend !== undefined && (
            <div className={`flex items-center gap-1 ${trend >= 0 ? styles.trendUp : styles.trendDown}`}>
              <svg 
                className={`w-4 h-4 ${trend < 0 ? 'rotate-180' : ''}`} 
                fill="none" 
                stroke="currentColor" 
                viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 10l7-7m0 0l7 7m-7-7v18" />
              </svg>
              <span className="text-sm font-semibold">{Math.abs(trend)}%</span>
            </div>
          )}
        </div>

        {/* Content */}
        <p className="text-white/50 text-sm font-medium mb-1">{title}</p>
        <div className="flex items-baseline gap-2">
          <p className="text-4xl font-bold text-white">{value.toLocaleString()}</p>
          {subtitle && (
            <span className="text-sm text-white/40">{subtitle}</span>
          )}
        </div>
      </div>

      {/* Hover indicator */}
      {onClick && (
        <div className="absolute bottom-3 right-3 opacity-0 group-hover:opacity-100 transition-opacity">
          <svg className="w-4 h-4 text-white/40" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
        </div>
      )}
    </div>
  );
}
