import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Bell,
  Download,
  Filter,
  Search,
  CheckCircle2,
  VolumeX,
  XCircle,
  ShieldCheck,
  ChevronLeft,
  ChevronRight,
  ExternalLink
} from 'lucide-react';
import { api } from '../api/client';
import { AlertRecord } from '../types';

export const AlertsCenter: React.FC<{ simState: any; onRefresh: () => void }> = ({ simState, onRefresh }) => {
  const navigate = useNavigate();
  const [alerts, setAlerts] = useState<AlertRecord[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);

  const [statusFilter, setStatusFilter] = useState('ALL');
  const [unitFilter, setUnitFilter] = useState('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedAlertIds, setSelectedAlertIds] = useState<number[]>([]);
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  const fetchAlerts = async () => {
    try {
      setLoading(true);
      const res = await api.getAlerts({
        status: statusFilter !== 'ALL' ? statusFilter : undefined,
        unit: unitFilter !== 'ALL' ? unitFilter : undefined,
        search: searchQuery.trim() || undefined,
        page,
        page_size: pageSize
      });
      setAlerts(res.items);
      setTotal(res.total);
    } catch (err) {
      console.error('Failed to load alerts', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAlerts();
  }, [statusFilter, unitFilter, searchQuery, page, simState?.current_hour]);

  const handleSelectAll = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.checked) {
      setSelectedAlertIds(alerts.map((a) => a.id));
    } else {
      setSelectedAlertIds([]);
    }
  };

  const handleToggleSelect = (id: number) => {
    setSelectedAlertIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  };

  const handleSingleAction = async (id: number, action: string) => {
    try {
      await api.postAlertAction(id, { action });
      setMsg(`Alert #${id} updated to ${action.toUpperCase()}`);
      fetchAlerts();
      onRefresh();
      setTimeout(() => setMsg(null), 2000);
    } catch (err: any) {
      alert('Error updating alert: ' + err.message);
    }
  };

  const handleBulkAction = async (action: string) => {
    if (selectedAlertIds.length === 0) return;
    try {
      await api.postBulkAlertAction({ alert_ids: selectedAlertIds, action });
      setMsg(`Bulk action ${action.toUpperCase()} applied to ${selectedAlertIds.length} alerts.`);
      setSelectedAlertIds([]);
      fetchAlerts();
      onRefresh();
      setTimeout(() => setMsg(null), 2500);
    } catch (err: any) {
      alert('Bulk action error: ' + err.message);
    }
  };

  const handleExportCSV = () => {
    window.open('http://127.0.0.1:8000/api/alerts/export/csv', '_blank');
  };

  return (
    <div className="p-6 space-y-6">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
            <Bell className="h-6 w-6 text-rose-400" />
            Alerts Center & Surveillance Log
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Clinical notification history, audit trail, and alarm fatigue suppression oversight.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleExportCSV}
            id="btn-export-alerts-csv"
            className="px-3.5 py-2 rounded-lg bg-slate-900 border border-slate-800 hover:border-slate-700 text-slate-200 text-xs font-semibold flex items-center gap-1.5 transition-colors"
          >
            <Download className="h-4 w-4 text-teal-400" />
            <span>Export CSV</span>
          </button>
        </div>
      </div>

      {msg && (
        <div className="p-3 rounded-lg bg-teal-950/60 border border-teal-500/40 text-teal-200 text-xs flex items-center gap-2">
          <CheckCircle2 className="h-4 w-4" />
          <span>{msg}</span>
        </div>
      )}

      {/* Filter and Bulk Bar */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-wrap items-center justify-between gap-4">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-1.5 text-xs text-slate-400">
            <Filter className="h-3.5 w-3.5 text-slate-500" />
            <span>Status:</span>
            <select
              id="select-alert-status-filter"
              value={statusFilter}
              onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
              className="bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-teal-500"
            >
              <option value="ALL">All Statuses</option>
              <option value="NEW">New (Active)</option>
              <option value="ACKNOWLEDGED">Acknowledged</option>
              <option value="SNOOZED">Snoozed</option>
              <option value="FALSE_ALARM">False Alarm</option>
              <option value="CONFIRMED">Confirmed</option>
            </select>
          </div>

          <div className="flex items-center gap-1.5 text-xs text-slate-400">
            <span>Unit:</span>
            <select
              id="select-alert-unit-filter"
              value={unitFilter}
              onChange={(e) => { setUnitFilter(e.target.value); setPage(1); }}
              className="bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-teal-500"
            >
              <option value="ALL">All Units</option>
              <option value="MICU">MICU</option>
              <option value="SICU">SICU</option>
              <option value="CCU">CCU</option>
              <option value="CTICU">CTICU</option>
            </select>
          </div>

          {/* Search */}
          <div className="relative">
            <Search className="absolute left-2.5 top-2 h-3.5 w-3.5 text-slate-500" />
            <input
              type="text"
              id="input-alert-search"
              placeholder="Search patient or bed..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="bg-slate-950 border border-slate-800 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-teal-500 w-44"
            />
          </div>
        </div>

        {/* Bulk Action Controls */}
        {selectedAlertIds.length > 0 && (
          <div className="flex items-center gap-2 bg-slate-950 border border-teal-500/30 rounded-lg p-1 px-3 text-xs">
            <span className="text-teal-300 font-semibold">{selectedAlertIds.length} selected:</span>
            <button
              onClick={() => handleBulkAction('acknowledge')}
              id="btn-bulk-ack"
              className="px-2 py-1 rounded bg-teal-600 text-white font-medium hover:bg-teal-500"
            >
              Acknowledge
            </button>
            <button
              onClick={() => handleBulkAction('snooze')}
              id="btn-bulk-snooze"
              className="px-2 py-1 rounded bg-amber-600 text-white font-medium hover:bg-amber-500"
            >
              Snooze 2h
            </button>
            <button
              onClick={() => handleBulkAction('false_alarm')}
              id="btn-bulk-false"
              className="px-2 py-1 rounded bg-slate-800 text-rose-300 font-medium hover:bg-slate-700"
            >
              False Alarm
            </button>
          </div>
        )}
      </div>

      {/* Alerts Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-sm">
        <table className="w-full text-left text-xs">
          <thead className="bg-slate-950/80 text-slate-400 uppercase font-mono text-[10px] border-b border-slate-800">
            <tr>
              <th className="p-3 w-8">
                <input
                  type="checkbox"
                  onChange={handleSelectAll}
                  checked={alerts.length > 0 && selectedAlertIds.length === alerts.length}
                  className="rounded border-slate-700 text-teal-600 focus:ring-0 bg-slate-900"
                />
              </th>
              <th className="p-3">Alert ID</th>
              <th className="p-3">Bed & Patient</th>
              <th className="p-3">Unit</th>
              <th className="p-3">Sim Hour</th>
              <th className="p-3">Risk / Threshold</th>
              <th className="p-3">Status</th>
              <th className="p-3">Audit Note</th>
              <th className="p-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60 font-mono">
            {alerts.length === 0 ? (
              <tr>
                <td colSpan={9} className="p-8 text-center text-slate-500 font-sans">
                  No alerts match the selected criteria.
                </td>
              </tr>
            ) : (
              alerts.map((a) => {
                const isSelected = selectedAlertIds.includes(a.id);
                const isNew = a.status === 'NEW';
                return (
                  <tr
                    key={a.id}
                    className={`hover:bg-slate-800/40 transition-colors ${
                      isSelected ? 'bg-teal-950/20' : ''
                    }`}
                  >
                    <td className="p-3">
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => handleToggleSelect(a.id)}
                        className="rounded border-slate-700 text-teal-600 focus:ring-0 bg-slate-900"
                      />
                    </td>
                    <td className="p-3 text-slate-400">#{a.id}</td>
                    <td className="p-3">
                      <button
                        onClick={() => navigate(`/monitor?patient=${a.patient_db_id || 1}`)}
                        className="text-left group"
                      >
                        <div className="font-bold text-white group-hover:text-teal-400 flex items-center gap-1 font-mono">
                          {a.bed} <ExternalLink className="h-3 w-3 opacity-0 group-hover:opacity-100" />
                        </div>
                        <div className="text-[10px] text-slate-400 font-mono">{a.patient_id}</div>
                      </button>
                    </td>
                    <td className="p-3 text-slate-300">{a.unit}</td>
                    <td className="p-3 text-slate-300">Hour {a.hour}</td>
                    <td className="p-3">
                      <span className="text-rose-400 font-bold">{(a.risk_score * 100).toFixed(1)}%</span>
                      <span className="text-slate-500 text-[10px]"> / {(a.threshold * 100).toFixed(0)}%</span>
                    </td>
                    <td className="p-3">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-sans font-bold uppercase ${
                          a.status === 'NEW'
                            ? 'bg-rose-950/80 text-rose-300 border border-rose-500/40 animate-pulse'
                            : a.status === 'ACKNOWLEDGED'
                            ? 'bg-teal-950/80 text-teal-300 border border-teal-500/30'
                            : a.status === 'SNOOZED'
                            ? 'bg-amber-950/80 text-amber-300 border border-amber-500/30'
                            : 'bg-slate-800 text-slate-400'
                        }`}
                      >
                        {a.status}
                      </span>
                    </td>
                    <td className="p-3 text-slate-400 max-w-xs truncate font-sans text-[11px]">
                      {a.action_note || '--'}
                    </td>
                    <td className="p-3 text-right">
                      <div className="flex items-center justify-end gap-1.5 font-sans">
                        <button
                          onClick={() => handleSingleAction(a.id, 'acknowledge')}
                          className="p-1 rounded hover:bg-slate-800 text-slate-400 hover:text-teal-400"
                          title="Acknowledge Alert"
                        >
                          <CheckCircle2 className="h-4 w-4" />
                        </button>
                        <button
                          onClick={() => handleSingleAction(a.id, 'snooze')}
                          className="p-1 rounded hover:bg-slate-800 text-slate-400 hover:text-amber-400"
                          title="Snooze Alert (2 Hours)"
                        >
                          <VolumeX className="h-4 w-4" />
                        </button>
                        <button
                          onClick={() => handleSingleAction(a.id, 'false_alarm')}
                          className="p-1 rounded hover:bg-slate-800 text-slate-400 hover:text-rose-400"
                          title="Mark as False Alarm"
                        >
                          <XCircle className="h-4 w-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination Footer */}
      {total > pageSize && (
        <div className="flex items-center justify-between text-xs text-slate-400">
          <div>
            Showing {(page - 1) * pageSize + 1} to {Math.min(page * pageSize, total)} of {total} alerts
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="px-3 py-1.5 rounded bg-slate-900 border border-slate-800 disabled:opacity-40"
            >
              Previous
            </button>
            <span className="font-mono text-xs">Page {page} of {Math.ceil(total / pageSize)}</span>
            <button
              onClick={() => setPage((p) => Math.min(Math.ceil(total / pageSize), p + 1))}
              disabled={page >= Math.ceil(total / pageSize)}
              className="px-3 py-1.5 rounded bg-slate-900 border border-slate-800 disabled:opacity-40"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
