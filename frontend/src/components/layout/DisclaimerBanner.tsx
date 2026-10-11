import React from 'react';
import { AlertTriangle, Loader2, CheckCircle2 } from 'lucide-react';

interface SeedBannerProps {
  seedStatus: {
    is_seeding: boolean;
    progress_pct: number;
    message: string;
    completed: boolean;
  };
}

export const DisclaimerBanner: React.FC = () => {
  return (
    <div className="bg-slate-900 border-b border-slate-800/80 px-4 py-1 text-[11px] text-slate-400 flex items-center justify-between">
      <div className="flex items-center gap-2">
        <span className="h-1.5 w-1.5 rounded-full bg-teal-400 animate-ping" />
        <span className="text-slate-300 font-medium">Research Prototype.</span>
        <span>Adult ICU only (Sepsis-3 6-hour prediction horizon). Not for clinical diagnostic use.</span>
      </div>
      <div className="font-mono text-[10px] text-slate-500">
        ALARM FATIGUE OPTIMIZATION ACTIVE
      </div>
    </div>
  );
};

export const SeedProgressBanner: React.FC<SeedBannerProps> = ({ seedStatus }) => {
  if (!seedStatus?.is_seeding) return null;

  return (
    <div className="bg-teal-950 border-b border-teal-500/40 px-4 py-2 text-xs text-teal-200 flex items-center justify-between">
      <div className="flex items-center gap-3">
        <Loader2 className="h-4 w-4 animate-spin text-teal-400 shrink-0" />
        <div>
          <span className="font-semibold text-white">System Auto-Seeding: </span>
          <span>{seedStatus.message}</span>
        </div>
      </div>
      <div className="flex items-center gap-3">
        <div className="w-36 h-2 bg-slate-800 rounded-full overflow-hidden border border-teal-500/20">
          <div
            className="h-full bg-teal-400 transition-all duration-300"
            style={{ width: `${seedStatus.progress_pct}%` }}
          />
        </div>
        <span className="font-mono text-xs text-teal-300 font-bold">{seedStatus.progress_pct}%</span>
      </div>
    </div>
  );
};
