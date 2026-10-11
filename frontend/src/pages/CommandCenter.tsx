import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  Users,
  AlertCircle,
  Clock,
  ShieldAlert,
  TrendingUp,
  Filter,
  ArrowUpDown,
  Search,
  ChevronLeft,
  ChevronRight,
  ExternalLink,
  Activity,
  Flame,
  CheckCircle2
} from 'lucide-react';
import { api } from '../api/client';
import { PatientOverview } from '../types';

interface CommandCenterProps {
  simState: any;
  onRefresh: () => void;
  activeModel: any;
}

export const CommandCenter: React.FC<CommandCenterProps> = ({ simState, onRefresh, activeModel }) => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const [patients, setPatients] = useState<PatientOverview[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(18);

  const [riskFilter, setRiskFilter] = useState('ALL');
  const [unitFilter, setUnitFilter] = useState('ALL');
  const [alertFilter, setAlertFilter] = useState('ALL');
  const [searchQuery, setSearchQuery] = useState(searchParams.get('search') || '');
  const [sortBy, setSortBy] = useState<'risk' | 'bed' | 'unit'>('risk');

  useEffect(() => {
    const q = searchParams.get('search');
    if (q !== null) setSearchQuery(q);
  }, [searchParams]);

  const fetchPatientsList = async () => {
    try {
      const res = await api.getPatients({
        risk_level: riskFilter !== 'ALL' ? riskFilter : undefined,
        unit: unitFilter !== 'ALL' ? unitFilter : undefined,
        alert_status: alertFilter !== 'ALL' ? alertFilter : undefined,
        search: searchQuery.trim() || undefined,
        page
      });
      setPatients(res.items);
      setTotal(res.total);
    } catch (err) {
      console.error('Failed to fetch patients', err);
    }
  };

  useEffect(() => {
    fetchPatientsList();
  }, [riskFilter, unitFilter, alertFilter, searchQuery, page, simState?.current_hour]);

  // Sort local page items if requested
  const sortedPatients = [...patients].sort((a, b) => {
    if (sortBy === 'risk') return b.current_risk_score - a.current_risk_score;
    if (sortBy === 'bed') return a.bed.localeCompare(b.bed);
    if (sortBy === 'unit') return a.unit.localeCompare(b.unit);
    return 0;
  });

  const kpi = simState?.kpi || {
    total_patients: total || 200,
    active_alerts: 0,
    alerts_today: 0,
    avg_lead_time: 4.8,
    alert_burden: 0.42
  };

  return (
    <div className="p-6 space-y-6">
      {/* Top Header & Overview */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
            ICU Command Center
            <span className="text-xs font-mono font-normal px-2 py-0.5 rounded bg-teal-500/20 text-teal-300 border border-teal-500/30">
              Live Monitor Bed Grid
            </span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Real-time multi-patient sepsis surveillance and 6-hour ahead trajectory tracking.
          </p>
        </div>

        {/* Status Indicator */}
        <div className="flex items-center gap-2 text-xs">
          <span className="flex h-2.5 w-2.5 relative">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-teal-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-teal-500"></span>
          </span>
          <span className="text-slate-300 font-medium">Replay Engine:</span>
          <span className={`font-mono font-bold ${simState?.is_running ? 'text-teal-400' : 'text-amber-400'}`}>
            {simState?.is_running ? `RUNNING (${simState?.speed}x)` : 'PAUSED'}
          </span>
        </div>
      </div>

      {/* KPI Cards Row */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        {/* Card 1 */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-sm">
          <div className="flex items-center justify-between text-slate-400 text-xs">
            <span>Patients Monitored</span>
            <Users className="h-4 w-4 text-teal-400" />
          </div>
          <div className="text-2xl font-bold text-white mt-2 font-mono" id="kpi-total-pts">
            {kpi.total_patients}
          </div>
          <div className="text-[11px] text-slate-500 mt-1">Adult ICU census</div>
        </div>

        {/* Card 2 */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-sm">
          <div className="flex items-center justify-between text-slate-400 text-xs">
            <span>Active Alerts</span>
            <AlertCircle className="h-4 w-4 text-rose-400" />
          </div>
          <div className="text-2xl font-bold text-rose-400 mt-2 font-mono" id="kpi-active-alerts">
            {kpi.active_alerts}
          </div>
          <div className="text-[11px] text-slate-500 mt-1">Requiring acknowledgment</div>
        </div>

        {/* Card 3 */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-sm">
          <div className="flex items-center justify-between text-slate-400 text-xs">
            <span>Total Alerts Fired</span>
            <Flame className="h-4 w-4 text-amber-400" />
          </div>
          <div className="text-2xl font-bold text-white mt-2 font-mono" id="kpi-alerts-today">
            {kpi.alerts_today}
          </div>
          <div className="text-[11px] text-slate-500 mt-1">Cumulative simulation events</div>
        </div>

        {/* Card 4 */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-sm">
          <div className="flex items-center justify-between text-slate-400 text-xs">
            <span>Median Lead Time</span>
            <Clock className="h-4 w-4 text-cyan-400" />
          </div>
          <div className="text-2xl font-bold text-cyan-400 mt-2 font-mono" id="kpi-lead-time">
            {kpi.avg_lead_time?.toFixed(1)}h
          </div>
          <div className="text-[11px] text-slate-500 mt-1">Ahead of Sepsis-3 onset</div>
        </div>

        {/* Card 5 */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-sm">
          <div className="flex items-center justify-between text-slate-400 text-xs">
            <span>Alert Burden Score</span>
            <ShieldAlert className="h-4 w-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-emerald-400 mt-2 font-mono" id="kpi-alert-burden">
            {kpi.alert_burden?.toFixed(2)}
          </div>
          <div className="text-[11px] text-slate-500 mt-1">Alerts/pt-day × (1 - PPV)</div>
        </div>
      </div>

      {/* Filter and Control Bar */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-wrap items-center justify-between gap-4">
        <div className="flex flex-wrap items-center gap-3">
          {/* Risk Level Filter */}
          <div className="flex items-center gap-1.5 text-xs text-slate-400">
            <Filter className="h-3.5 w-3.5 text-slate-500" />
            <span>Risk:</span>
            <select
              id="select-risk-filter"
              value={riskFilter}
              onChange={(e) => { setRiskFilter(e.target.value); setPage(1); }}
              className="bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-teal-500"
            >
              <option value="ALL">All Risk Levels</option>
              <option value="HIGH">High Risk</option>
              <option value="MODERATE">Moderate Risk</option>
              <option value="LOW">Low Risk</option>
            </select>
          </div>

          {/* Unit Filter */}
          <div className="flex items-center gap-1.5 text-xs text-slate-400">
            <span>Unit:</span>
            <select
              id="select-unit-filter"
              value={unitFilter}
              onChange={(e) => { setUnitFilter(e.target.value); setPage(1); }}
              className="bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-teal-500"
            >
              <option value="ALL">All ICU Units</option>
              <option value="MICU">MICU (Medical)</option>
              <option value="SICU">SICU (Surgical)</option>
              <option value="CCU">CCU (Coronary)</option>
              <option value="CTICU">CTICU (Cardiothoracic)</option>
            </select>
          </div>

          {/* Alert Status Filter */}
          <div className="flex items-center gap-1.5 text-xs text-slate-400">
            <span>Alerts:</span>
            <select
              id="select-alert-filter"
              value={alertFilter}
              onChange={(e) => { setAlertFilter(e.target.value); setPage(1); }}
              className="bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-teal-500"
            >
              <option value="ALL">All Alert States</option>
              <option value="ACTIVE">Active Alerts</option>
              <option value="ACKNOWLEDGED">Acknowledged</option>
              <option value="SNOOZED">Snoozed</option>
              <option value="NONE">No Alert</option>
            </select>
          </div>
        </div>

        {/* Sort & Pagination info */}
        <div className="flex items-center gap-3 text-xs">
          <div className="flex items-center gap-1.5 text-slate-400">
            <ArrowUpDown className="h-3.5 w-3.5 text-slate-500" />
            <span>Sort:</span>
            <select
              id="select-sort-by"
              value={sortBy}
              onChange={(e: any) => setSortBy(e.target.value)}
              className="bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-teal-500"
            >
              <option value="risk">Highest Risk First</option>
              <option value="bed">Bed Number</option>
              <option value="unit">ICU Unit</option>
            </select>
          </div>

          <div className="text-slate-400 font-mono text-[11px]">
            Showing {(page - 1) * pageSize + 1}-{Math.min(page * pageSize, total)} of {total}
          </div>
        </div>
      </div>

      {/* Bed Grid Display */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {sortedPatients.map((pt) => {
          const isHigh = pt.current_risk_level === 'HIGH';
          const isMod = pt.current_risk_level === 'MODERATE';
          const hasActiveAlert = pt.alert_status === 'ACTIVE';

          return (
            <div
              key={pt.id}
              onClick={() => navigate(`/monitor?patient=${pt.id}`)}
              className={`cursor-pointer rounded-xl p-4 transition-all duration-200 border ${
                isHigh
                  ? 'bg-rose-950/20 border-rose-500/50 hover:border-rose-400 hover:shadow-lg hover:shadow-rose-950/40'
                  : isMod
                  ? 'bg-amber-950/20 border-amber-500/40 hover:border-amber-400'
                  : 'bg-slate-900 border-slate-800 hover:border-slate-700 hover:bg-slate-850'
              }`}
            >
              {/* Header: Bed & Patient ID & Status Chip */}
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-bold text-white font-mono">{pt.bed}</span>
                    <span className="text-xs text-slate-400 font-mono">({pt.patient_id})</span>
                    <span className="text-[10px] px-1.5 py-0.2 rounded bg-slate-800 text-slate-300 font-mono">
                      {pt.unit}
                    </span>
                  </div>
                  <div className="text-[11px] text-slate-400 mt-0.5">
                    {pt.age?.toFixed(0)}y {pt.gender} • Stay: {pt.current_sim_hour}h
                  </div>
                </div>

                {/* Risk Level Badge */}
                <div className="flex flex-col items-end gap-1">
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] uppercase font-bold tracking-wider ${
                      isHigh
                        ? 'risk-chip-high'
                        : isMod
                        ? 'risk-chip-moderate'
                        : 'risk-chip-low'
                    }`}
                  >
                    {pt.current_risk_level}
                  </span>
                  {hasActiveAlert && (
                    <span className="text-[9px] font-mono px-1.5 py-0.2 rounded bg-rose-500 text-white font-bold animate-pulse">
                      ALERT FIRED
                    </span>
                  )}
                </div>
              </div>

              {/* Main Metric: 6h Predicted Risk Score & Sparkline */}
              <div className="mt-4 flex items-center justify-between">
                <div>
                  <div className="text-[10px] uppercase font-mono text-slate-400">
                    6h Sepsis Risk
                  </div>
                  <div
                    className={`text-2xl font-bold font-mono ${
                      isHigh ? 'text-rose-400' : isMod ? 'text-amber-400' : 'text-emerald-400'
                    }`}
                  >
                    {(pt.current_risk_score * 100).toFixed(1)}%
                  </div>
                </div>

                {/* Sparkline Visual */}
                <div className="flex items-end gap-1 h-9 px-2 py-1 rounded bg-slate-950 border border-slate-800/80">
                  {pt.sparkline?.map((val, idx) => {
                    const hPct = Math.max(15, Math.min(100, val * 100));
                    return (
                      <div
                        key={idx}
                        className={`w-1.5 rounded-t transition-all ${
                          val >= 0.5 ? 'bg-rose-500' : val >= 0.3 ? 'bg-amber-400' : 'bg-teal-500'
                        }`}
                        style={{ height: `${hPct}%` }}
                        title={`Hour -${7 - idx}: ${(val * 100).toFixed(0)}%`}
                      />
                    );
                  })}
                </div>
              </div>

              {/* Latest Vitals Bar */}
              <div className="mt-4 pt-3 border-t border-slate-800/80 grid grid-cols-4 gap-2 text-center text-xs">
                <div>
                  <div className="text-[10px] text-slate-500 font-mono">HR</div>
                  <div className="font-mono text-slate-200">{pt.vitals.hr?.toFixed(0) || '--'}</div>
                </div>
                <div>
                  <div className="text-[10px] text-slate-500 font-mono">MAP</div>
                  <div className="font-mono text-slate-200">{pt.vitals.map?.toFixed(0) || '--'}</div>
                </div>
                <div>
                  <div className="text-[10px] text-slate-500 font-mono">TEMP</div>
                  <div className="font-mono text-slate-200">{pt.vitals.temp?.toFixed(1) || '--'}°</div>
                </div>
                <div>
                  <div className="text-[10px] text-slate-500 font-mono">SOFA</div>
                  <div className="font-mono text-teal-300 font-semibold">{pt.vitals.sofa_score?.toFixed(0)}</div>
                </div>
              </div>

              {/* Sepsis-3 Ground Truth indicator (portfolio transparent research tool) */}
              {pt.is_septic && (
                <div className="mt-2 text-[10px] text-slate-500 flex items-center justify-between font-mono">
                  <span>True Sepsis-3 Onset:</span>
                  <span className="text-amber-400 font-bold">Hour {pt.sepsis_onset_hour}</span>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Pagination Footer */}
      {total > pageSize && (
        <div className="flex items-center justify-between pt-4 border-t border-slate-800 text-xs">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            id="btn-prev-page"
            className="px-3 py-1.5 rounded bg-slate-900 border border-slate-800 text-slate-300 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-800 flex items-center gap-1"
          >
            <ChevronLeft className="h-4 w-4" /> Previous
          </button>
          <span className="text-slate-400 font-mono">
            Page {page} of {Math.ceil(total / pageSize)}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(Math.ceil(total / pageSize), p + 1))}
            disabled={page >= Math.ceil(total / pageSize)}
            id="btn-next-page"
            className="px-3 py-1.5 rounded bg-slate-900 border border-slate-800 text-slate-300 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-800 flex items-center gap-1"
          >
            Next <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      )}
    </div>
  );
};
