import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Play,
  Pause,
  RotateCcw,
  FastForward,
  Bell,
  Search,
  Cpu,
  Clock,
  CheckCircle2,
  AlertTriangle
} from 'lucide-react';
import { api } from '../../api/client';

interface TopBarProps {
  simState: any;
  onRefresh: () => void;
  activeModel: any;
}

export const TopBar: React.FC<TopBarProps> = ({ simState, onRefresh, activeModel }) => {
  const navigate = useNavigate();
  const [searchVal, setSearchVal] = useState('');
  const [speed, setSpeed] = useState<number>(simState?.speed || 5);
  const [isChangingSpeed, setIsChangingSpeed] = useState(false);

  useEffect(() => {
    if (simState?.speed) setSpeed(simState.speed);
  }, [simState?.speed]);

  const handleTogglePlay = async () => {
    try {
      if (simState?.is_running) {
        await api.pauseSimulation();
      } else {
        await api.startSimulation();
      }
      onRefresh();
    } catch (err) {
      console.error(err);
    }
  };

  const handleReset = async () => {
    try {
      await api.resetSimulation();
      onRefresh();
    } catch (err) {
      console.error(err);
    }
  };

  const handleStep = async () => {
    try {
      await api.stepSimulation();
      onRefresh();
    } catch (err) {
      console.error(err);
    }
  };

  const handleSpeedChange = async (newSpeed: number) => {
    setSpeed(newSpeed);
    setIsChangingSpeed(true);
    try {
      await api.setSimulationSpeed(newSpeed);
      onRefresh();
    } catch (err) {
      console.error(err);
    } finally {
      setIsChangingSpeed(false);
    }
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchVal.trim()) {
      navigate(`/?search=${encodeURIComponent(searchVal.trim())}`);
    }
  };

  const activeAlertsCount = simState?.kpi?.active_alerts || 0;

  return (
    <header className="h-16 bg-slate-900/90 backdrop-blur border-b border-slate-800 px-6 flex items-center justify-between sticky top-0 z-40">
      {/* Left: Simulation Replay Controls */}
      <div className="flex items-center gap-3">
        <div className="flex items-center bg-slate-950 border border-slate-800 rounded-lg p-1">
          <button
            onClick={handleTogglePlay}
            id="btn-play-pause"
            className={`p-1.5 rounded-md text-xs font-medium flex items-center gap-1.5 transition-colors ${
              simState?.is_running
                ? 'bg-amber-500/20 text-amber-300 hover:bg-amber-500/30'
                : 'bg-teal-500/20 text-teal-300 hover:bg-teal-500/30'
            }`}
            title={simState?.is_running ? 'Pause Simulation' : 'Start Simulation'}
          >
            {simState?.is_running ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
            <span>{simState?.is_running ? 'Pause' : 'Stream'}</span>
          </button>

          <button
            onClick={handleStep}
            id="btn-sim-step"
            className="p-1.5 text-slate-400 hover:text-white rounded-md transition-colors"
            title="Step 1 Hour Ahead"
          >
            <FastForward className="h-4 w-4" />
          </button>

          <button
            onClick={handleReset}
            id="btn-sim-reset"
            className="p-1.5 text-slate-400 hover:text-rose-400 rounded-md transition-colors"
            title="Reset Simulation to Hour 0"
          >
            <RotateCcw className="h-4 w-4" />
          </button>
        </div>

        {/* Speed Selector */}
        <div className="flex items-center gap-1 bg-slate-950 border border-slate-800 rounded-lg p-1 text-xs">
          <span className="text-[10px] text-slate-500 font-mono px-1">SPEED</span>
          {[1, 5, 15, 60].map((s) => (
            <button
              key={s}
              id={`btn-speed-${s}x`}
              onClick={() => handleSpeedChange(s)}
              className={`px-2 py-0.5 rounded text-[11px] font-mono transition-colors ${
                speed === s
                  ? 'bg-teal-600 text-white font-bold'
                  : 'text-slate-400 hover:text-white hover:bg-slate-800'
              }`}
            >
              {s}x
            </button>
          ))}
        </div>

        {/* Simulation Hour Clock */}
        <div className="flex items-center gap-1.5 px-3 py-1 rounded-lg bg-slate-950 border border-slate-800 text-xs font-mono text-slate-300">
          <Clock className="h-3.5 w-3.5 text-teal-400" />
          <span>Sim Hour:</span>
          <span className="font-bold text-teal-300">{simState?.current_hour ?? 0}h</span>
        </div>
      </div>

      {/* Center: Global Patient Quick Search */}
      <form onSubmit={handleSearchSubmit} className="relative w-72">
        <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-500" />
        <input
          type="text"
          id="input-global-search"
          value={searchVal}
          onChange={(e) => setSearchVal(e.target.value)}
          placeholder="Search patient ID or bed..."
          className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-9 pr-3 py-1.5 text-xs text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-teal-500 transition-colors"
        />
      </form>

      {/* Right: Active Model Badge & Alerts Bell */}
      <div className="flex items-center gap-3">
        {/* Active Model Badge */}
        {activeModel ? (
          <div
            onClick={() => navigate('/models')}
            className="cursor-pointer flex items-center gap-2 px-3 py-1.5 rounded-lg bg-teal-950/40 border border-teal-500/30 text-teal-300 hover:bg-teal-900/40 transition-colors text-xs"
            title="Click to view Model Lab"
          >
            <Cpu className="h-3.5 w-3.5 text-teal-400" />
            <span className="font-medium">{activeModel.name}</span>
            <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-teal-500/20 text-teal-200 border border-teal-500/40">
              Thresh: {activeModel.operating_threshold?.toFixed(2)}
            </span>
          </div>
        ) : (
          <div className="text-xs text-slate-400 flex items-center gap-1.5">
            <Cpu className="h-3.5 w-3.5" />
            <span>Default Rule Baseline</span>
          </div>
        )}

        {/* Live Alerts Bell */}
        <button
          onClick={() => navigate('/alerts')}
          id="btn-nav-alerts"
          className="relative p-2 rounded-lg bg-slate-950 border border-slate-800 text-slate-300 hover:text-white hover:border-slate-700 transition-colors"
          title="View Active Alerts"
        >
          <Bell className="h-4 w-4" />
          {activeAlertsCount > 0 && (
            <span className="absolute -top-1 -right-1 bg-rose-500 text-white font-bold text-[10px] h-4 min-w-[16px] px-1 rounded-full flex items-center justify-center animate-pulse">
              {activeAlertsCount}
            </span>
          )}
        </button>
      </div>
    </header>
  );
};
