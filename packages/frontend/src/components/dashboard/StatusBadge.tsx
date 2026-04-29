// StatusBadge - Badges de estado glassmorphism
import { wasteApi } from "@/lib/waste-api";

interface StatusBadgeProps {
  status: string;
  size?: "sm" | "md" | "lg";
}

const sizeClasses = {
  sm: "px-2 py-0.5 text-xs",
  md: "px-3 py-1 text-xs",
  lg: "px-4 py-1.5 text-sm",
};

export function StatusBadge({ status, size = "md" }: StatusBadgeProps) {
  const badge = wasteApi.getStatusBadge(status);
  
  const colorMap: Record<string, { bg: string; text: string; border: string; glow: string }> = {
    emerald: { 
      bg: "bg-emerald-400/20", 
      text: "text-emerald-300", 
      border: "border-emerald-400/30",
      glow: "shadow-emerald-500/20"
    },
    amber: { 
      bg: "bg-amber-400/20", 
      text: "text-amber-300", 
      border: "border-amber-400/30",
      glow: "shadow-amber-500/20"
    },
    blue: { 
      bg: "bg-blue-400/20", 
      text: "text-blue-300", 
      border: "border-blue-400/30",
      glow: "shadow-blue-500/20"
    },
    rose: { 
      bg: "bg-rose-400/20", 
      text: "text-rose-300", 
      border: "border-rose-400/30",
      glow: "shadow-rose-500/20"
    },
    gray: { 
      bg: "bg-white/10", 
      text: "text-white/70", 
      border: "border-white/20",
      glow: ""
    },
  };

  const colors = colorMap[badge.color] || colorMap.gray;

  return (
    <span 
      className={`
        inline-flex items-center rounded-full font-semibold border backdrop-blur-md
        shadow-lg ${colors.bg} ${colors.text} ${colors.border} ${colors.glow}
        ${sizeClasses[size]}
      `}
    >
      <span className={`w-1.5 h-1.5 rounded-full mr-1.5 ${colors.text.replace('text-', 'bg-')}`} />
      {badge.label}
    </span>
  );
}
