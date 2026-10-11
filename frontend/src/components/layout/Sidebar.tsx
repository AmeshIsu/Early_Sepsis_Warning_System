import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  Activity,
  UserCheck,
  Bell,
  Database,
  Cpu,
  Sliders,
  BarChart3,
  Settings,
  ShieldAlert,
  HeartPulse
} from 'lucide-react';

const NAV_ITEMS = [
  { path: '/', label: 'Command Center', icon: Activity },
  { path: '/monitor', label: 'Patient Monitor', icon: HeartPulse },
  { path: '/alerts', label: 'Alerts Center', icon: Bell },
  { path: '/data', label: 'Data Manager', icon: Database },
  { path: '/models', label: 'Model Lab', icon: Cpu },
  { path: '/calibration', label: 'Calibration & Thresholds', icon: Sliders },
  { path: '/evaluation', label: 'Evaluation & Benchmarks', icon: BarChart3 },
  { path: '/settings', label: 'Settings & Methodology', icon: Settings },
];

export const Sidebar: React.FC = () => {
  return (
    <aside className="w-64 bg-slate-900 border-r border-slate-800 flex flex-col h-screen sticky top-0 shrink-0 select-none">
      {/* Brand Header */}
      <div className="p-4 border-b border-slate-800 flex items-center space-x-3 bg-slate-950/40">
        <div className="h-10 w-10 rounded-xl bg-teal-500/10 border border-teal-500/30 flex items-center justify-center text-teal-400">
          <Activity className="h-6 w-6" />
        </div>
        <div>
          <div className="font-bold text-base tracking-tight text-white flex items-center gap-1.5">
            SepsisWatch
            <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-teal-500/20 text-teal-300 border border-teal-500/30">
              ICU EWS
            </span>
          </div>
          <div className="text-[11px] text-slate-400 font-mono">6h Early Warning System</div>
        </div>
      </div>

      {/* Navigation Links */}
      <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
        <div className="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-slate-400">
          Clinical Operations
        </div>
        {NAV_ITEMS.slice(0, 3).map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-medium transition-all ${
                  isActive
                    ? 'bg-teal-600 text-white shadow-lg shadow-teal-900/30 font-semibold'
                    : 'text-slate-300 hover:text-white hover:bg-slate-800/60'
                }`
              }
            >
              <Icon className="h-4 w-4 shrink-0" />
              <span>{item.label}</span>
            </NavLink>
          );
        })}

        <div className="px-3 pt-4 pb-1.5 text-[10px] font-semibold uppercase tracking-wider text-slate-400">
          Research & Calibration
        </div>
        {NAV_ITEMS.slice(3).map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-medium transition-all ${
                  isActive
                    ? 'bg-teal-600 text-white shadow-lg shadow-teal-900/30 font-semibold'
                    : 'text-slate-300 hover:text-white hover:bg-slate-800/60'
                }`
              }
            >
              <Icon className="h-4 w-4 shrink-0" />
              <span>{item.label}</span>
            </NavLink>
          );
        })}
      </nav>

      {/* Clinical Disclaimer footer */}
      <div className="p-3 border-t border-slate-800 bg-slate-950/60 text-[11px] text-slate-400">
        <div className="flex items-start gap-2 p-2 rounded bg-amber-500/10 border border-amber-500/20 text-amber-300">
          <ShieldAlert className="h-4 w-4 shrink-0 text-amber-400 mt-0.5" />
          <p className="leading-tight text-[10px]">
            <strong>Research Prototype.</strong> Not for diagnostic or treatment use.
          </p>
        </div>
      </div>
    </aside>
  );
};
