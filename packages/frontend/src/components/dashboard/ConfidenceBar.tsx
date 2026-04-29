// ConfidenceBar - Barra visual de confianza glassmorphism
import { wasteApi } from "@/lib/waste-api";

interface ConfidenceBarProps {
  score: number;
  showLabel?: boolean;
  size?: "sm" | "md" | "lg";
}

const sizeConfig = {
  sm: { height: "h-1.5", width: "w-16", text: "text-xs" },
  md: { height: "h-2", width: "w-24", text: "text-xs" },
  lg: { height: "h-3", width: "w-32", text: "text-sm" },
};

export function ConfidenceBar({ score, showLabel = true, size = "md" }: ConfidenceBarProps) {
  const level = wasteApi.getConfidenceLevel(score);
  const config = sizeConfig[size];

  const colorMap: Record<string, { bg: string; fill: string; text: string }> = {
    emerald: { bg: "bg-emerald-400/20", fill: "bg-gradient-to-r from-emerald-500 to-emerald-400", text: "text-emerald-400" },
    blue: { bg: "bg-blue-400/20", fill: "bg-gradient-to-r from-blue-500 to-blue-400", text: "text-blue-400" },
    amber: { bg: "bg-amber-400/20", fill: "bg-gradient-to-r from-amber-500 to-amber-400", text: "text-amber-400" },
    rose: { bg: "bg-rose-400/20", fill: "bg-gradient-to-r from-rose-500 to-rose-400", text: "text-rose-400" },
  };

  const colors = colorMap[level.color] || colorMap.blue;

  return (
    <div className="flex items-center gap-2">
      <div className={`${config.height} ${config.width} ${colors.bg} rounded-full overflow-hidden backdrop-blur-sm border border-white/10`}>
        <div 
          className={`${config.height} ${colors.fill} rounded-full transition-all duration-500`}
          style={{ width: `${Math.min(100, Math.max(0, score))}%` }}
        />
      </div>
      {showLabel && (
        <div className="flex items-center gap-1">
          <span className={`font-semibold ${colors.text} ${config.text}`}>{score}%</span>
          {score < 70 && (
            <svg className={`w-3 h-3 ${colors.text}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          )}
        </div>
      )}
    </div>
  );
}
