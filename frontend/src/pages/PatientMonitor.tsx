import React, { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import {
  ComposedChart,
  Line,
  ReferenceLine,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  Area
} from 'recharts';
import {
  Activity,
  AlertTriangle,
  Clock,
  CheckCircle2,
  FileText,
  VolumeX,
  XCircle,
  HelpCircle,
  Send,
  ArrowLeft,
  ChevronDown
} from 'lucide-react';
import { api } from '../api/client';
import { ExplainabilityData } from '../types';

export const PatientMonitor: React.FC<{ simState: any; onRefresh: () => void }> = ({ simState, onRefresh }) => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const [patientId, setPatientId] = useState<number | string>(searchParams.get('patient') || 1);
  const [data, setData] = useState<any>(null);
  const [explainData, setExplainData] = useState<ExplainabilityData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Action form state
  const [actionModalOpen, setActionModalOpen] = useState(false);
  const [selectedAction, setSelectedAction] = useState<'acknowledge' | 'snooze' | 'false_alarm' | 'add_note'>('acknowledge');
  const [snoozeHours, setSnoozeHours] = useState(2);
  const [actionNote, setActionNote] = useState('');
  const [actionStatusMsg, setActionStatusMsg] = useState<string | null>(null);

  const fetchPatientData = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.getPatientDetails(patientId);
      setData(res);
      const exp = await api.getPatientExplainability(patientId);
      setExplainData(exp);
    } catch (err: any) {
      setError(err.message || 'Failed to load patient data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPatientData();
  }, [patientId, simState?.current_hour]);

  const handleActionSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.postPatientAction(patientId, {
        action: selectedAction,
        snooze_hours: snoozeHours,
        note_content: actionNote,
        author: 'Dr. ICU Attending'
      });
      setActionStatusMsg(`Action successfully recorded: ${selectedAction.toUpperCase()}`);
      setActionNote('');
      fetchPatientData();
      onRefresh();
      setTimeout(() => {
        setActionStatusMsg(null);
        setActionModalOpen(false);
      }, 1500);
    } catch (err: any) {
      alert('Error submitting action: ' + err.message);
    }
  };

  if (loading && !data) {
    return (
      <div className="p-8 text-center text-slate-400 flex flex-col items-center justify-center min-h-[400px]">
        <Activity className="h-8 w-8 animate-spin text-teal-400 mb-2" />
        <p className="text-xs">Streaming patient telemetry from SQLite database...</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-8 text-center text-rose-400">
        <AlertTriangle className="h-8 w-8 mx-auto mb-2" />
        <p className="text-sm font-semibold">{error || 'Patient not found'}</p>
        <button
          onClick={() => navigate('/')}
          className="mt-4 px-4 py-2 bg-slate-800 text-white rounded text-xs"
        >
          Return to Command Center
        </button>
      </div>
    );
  }

  const { patient, operating_threshold, current_vitals, timeline, labs_history, alerts, notes } = data;
  const isHigh = patient.current_risk_level === 'HIGH';
  const isMod = patient.current_risk_level === 'MODERATE';

  return (
    <div className="p-6 space-y-6">
      {/* Top Header Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-slate-900 border border-slate-800 rounded-xl p-4">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate('/')}
            className="p-2 rounded-lg bg-slate-950 border border-slate-800 text-slate-400 hover:text-white"
            title="Back to Bed Grid"
          >
            <ArrowLeft className="h-4 w-4" />
          </button>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold text-white font-mono">{patient.bed}</h1>
              <span className="text-sm text-slate-400 font-mono">({patient.patient_id})</span>
              <span className="text-xs px-2 py-0.5 rounded bg-teal-500/20 text-teal-300 border border-teal-500/30 font-mono">
                {patient.unit}
              </span>
            </div>
            <div className="text-xs text-slate-400 mt-0.5">
              {patient.age}y {patient.gender} • Admitted: {patient.current_sim_hour}h ago • Status: {patient.alert_status}
            </div>
          </div>
        </div>

        {/* Current Risk Level & Quick Actions */}
        <div className="flex items-center gap-3">
          <div className="text-right">
            <div className="text-[10px] text-slate-400 uppercase font-mono">Current 6h Risk</div>
            <div
              className={`text-2xl font-bold font-mono ${
                isHigh ? 'text-rose-400' : isMod ? 'text-amber-400' : 'text-emerald-400'
              }`}
            >
              {(patient.current_risk_score * 100).toFixed(1)}%
            </div>
          </div>

          <button
            onClick={() => setActionModalOpen(true)}
            id="btn-open-action-modal"
            className="px-4 py-2 rounded-lg bg-teal-600 hover:bg-teal-500 text-white font-semibold text-xs shadow-md transition-colors flex items-center gap-1.5"
          >
            <Activity className="h-4 w-4" />
            <span>Clinical Action</span>
          </button>
        </div>
      </div>

      {/* Main Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: 6h Sepsis Risk Timeline & Multi-panel Vitals */}
        <div className="lg:col-span-2 space-y-6">
          {/* Risk Score Timeline Chart */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
            <div className="flex items-center justify-between mb-2">
              <div>
                <h3 className="text-xs font-bold text-slate-200 uppercase tracking-wider font-mono">
                  Continuous 6h Sepsis Risk Trajectory
                </h3>
                <p className="text-[11px] text-slate-500">
                  Model probability output overlaid with alert operating threshold ({operating_threshold?.toFixed(2)})
                </p>
              </div>
              <div className="text-[10px] font-mono flex items-center gap-3">
                <span className="flex items-center gap-1 text-teal-400">
                  <span className="h-2 w-2 rounded-full bg-teal-400" /> Risk Score
                </span>
                <span className="flex items-center gap-1 text-rose-400">
                  <span className="h-2 w-2 rounded-full bg-rose-400" /> Threshold ({operating_threshold?.toFixed(2)})
                </span>
              </div>
            </div>

            <div className="h-56 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={timeline} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis dataKey="hour" stroke="#64748b" tick={{ fontSize: 10 }} unit="h" />
                  <YAxis stroke="#64748b" tick={{ fontSize: 10 }} domain={[0, 1]} tickFormatter={(v) => `${(v * 100).toFixed(0)}%`} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#090d16', borderColor: '#334155', fontSize: '11px' }}
                    formatter={(val: any) => [`${(Number(val) * 100).toFixed(1)}%`, 'Risk Score']}
                    labelFormatter={(h) => `Hour ${h}:00`}
                  />
                  <ReferenceLine
                    y={operating_threshold}
                    stroke="#ef4444"
                    strokeDasharray="4 4"
                    label={{ value: 'Alert Cutoff', fill: '#ef4444', fontSize: 10, position: 'insideTopRight' }}
                  />
                  {patient.sepsis_onset_hour !== null && (
                    <ReferenceLine
                      x={patient.sepsis_onset_hour}
                      stroke="#f59e0b"
                      strokeWidth={2}
                      label={{ value: 'Sepsis-3 Onset', fill: '#f59e0b', fontSize: 10, position: 'insideTopLeft' }}
                    />
                  )}
                  <Area type="monotone" dataKey="predicted_risk" fill="#0d9488" fillOpacity={0.15} stroke="none" />
                  <Line type="monotone" dataKey="predicted_risk" stroke="#14b8a6" strokeWidth={2.5} dot={false} activeDot={{ r: 4 }} />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Physiological Vitals Stream (HR, MAP, RR, Temp) */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
            <div className="flex items-center justify-between mb-2">
              <div>
                <h3 className="text-xs font-bold text-slate-200 uppercase tracking-wider font-mono">
                  Physiological Monitor Vitals (Hourly Replay)
                </h3>
                <p className="text-[11px] text-slate-500">
                  Heart Rate (bpm), Mean Arterial Pressure (mmHg), and Respiratory Rate (/min)
                </p>
              </div>
              <div className="flex items-center gap-3 text-[10px] font-mono">
                <span className="text-rose-400">● HR</span>
                <span className="text-cyan-400">● MAP</span>
                <span className="text-emerald-400">● Resp</span>
              </div>
            </div>

            <div className="h-60 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={timeline} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis dataKey="hour" stroke="#64748b" tick={{ fontSize: 10 }} unit="h" />
                  <YAxis stroke="#64748b" tick={{ fontSize: 10 }} domain={[30, 160]} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#090d16', borderColor: '#334155', fontSize: '11px' }}
                    labelFormatter={(h) => `Hour ${h}:00`}
                  />
                  <Line type="monotone" dataKey="hr" stroke="#f43f5e" strokeWidth={1.8} dot={false} name="Heart Rate" />
                  <Line type="monotone" dataKey="map" stroke="#06b6d4" strokeWidth={1.8} dot={false} name="MAP" />
                  <Line type="monotone" dataKey="resp" stroke="#10b981" strokeWidth={1.8} dot={false} name="Respiratory Rate" />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {/* Right Col: Explainability Drivers & Clinical Summary */}
        <div className="space-y-6">
          {/* Explainability Breakdown Card */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
            <h3 className="text-xs font-bold text-slate-200 uppercase tracking-wider font-mono flex items-center gap-1.5">
              <HelpCircle className="h-3.5 w-3.5 text-teal-400" />
              Sepsis Risk Attribution Drivers
            </h3>
            <p className="text-[11px] text-slate-400 mt-1">
              Top physiological drivers contributing to current elevation:
            </p>

            <div className="mt-4 space-y-3">
              {explainData?.drivers?.map((d, i) => (
                <div key={i} className="bg-slate-950 border border-slate-800/80 rounded-lg p-2.5">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-semibold text-slate-200">{d.name}</span>
                    <span className="font-mono text-teal-300 font-bold">+{d.contribution_pct}%</span>
                  </div>
                  <div className="flex items-center justify-between text-[11px] text-slate-400 mt-1 font-mono">
                    <span>
                      Observed: {d.current_value} {d.unit} ({d.direction})
                    </span>
                    <span className="text-[10px] text-slate-500">Ref: {d.normal_range}</span>
                  </div>
                  <div className="w-full h-1.5 bg-slate-800 rounded-full mt-2 overflow-hidden">
                    <div
                      className={`h-full ${d.direction === 'elevated' ? 'bg-rose-500' : 'bg-cyan-500'}`}
                      style={{ width: `${Math.min(100, d.contribution_pct * 1.5)}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>

            {/* Plain language clinical narrative */}
            <div className="mt-4 p-3 rounded-lg bg-teal-950/30 border border-teal-500/20 text-xs text-slate-300 leading-relaxed">
              <span className="font-semibold text-teal-300">Clinical Narrative: </span>
              {explainData?.clinical_summary}
            </div>
          </div>

          {/* SOFA Score & Lab Panel */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-xs font-bold text-slate-200 uppercase tracking-wider font-mono">
                Organ Dysfunction (SOFA)
              </h3>
              <span className="text-xs font-mono font-bold text-teal-300">
                Score: {current_vitals.sofa_score?.toFixed(0)} / 24
              </span>
            </div>

            <div className="grid grid-cols-2 gap-2 text-xs">
              <div className="p-2 rounded bg-slate-950 border border-slate-800 font-mono">
                <div className="text-[10px] text-slate-500">Lactate</div>
                <div className="text-slate-200 font-semibold">{current_vitals.lactate || '--'} mmol/L</div>
              </div>
              <div className="p-2 rounded bg-slate-950 border border-slate-800 font-mono">
                <div className="text-[10px] text-slate-500">WBC</div>
                <div className="text-slate-200 font-semibold">{current_vitals.wbc || '--'} x10^9/L</div>
              </div>
              <div className="p-2 rounded bg-slate-950 border border-slate-800 font-mono">
                <div className="text-[10px] text-slate-500">Creatinine</div>
                <div className="text-slate-200 font-semibold">{current_vitals.creatinine || '--'} mg/dL</div>
              </div>
              <div className="p-2 rounded bg-slate-950 border border-slate-800 font-mono">
                <div className="text-[10px] text-slate-500">Bilirubin</div>
                <div className="text-slate-200 font-semibold">{current_vitals.bilirubin || '--'} mg/dL</div>
              </div>
            </div>

            {/* Sepsis-3 Criteria Status */}
            <div className="mt-4 pt-3 border-t border-slate-800 text-[11px] space-y-1">
              <div className="flex justify-between">
                <span className="text-slate-400">SIRS Score:</span>
                <span className="font-mono text-slate-200">{current_vitals.sirs_score} / 4</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">qSOFA Score:</span>
                <span className="font-mono text-slate-200">{current_vitals.qsofa_score} / 3</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">NEWS Score:</span>
                <span className="font-mono text-slate-200">{current_vitals.news_score} / 20</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Clinical Action Modal */}
      {actionModalOpen && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 max-w-md w-full shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <Activity className="h-5 w-5 text-teal-400" />
                Bedside Clinical Action
              </h3>
              <button
                onClick={() => setActionModalOpen(false)}
                className="text-slate-400 hover:text-white"
              >
                ✕
              </button>
            </div>

            {actionStatusMsg && (
              <div className="p-3 rounded-lg bg-emerald-950/40 border border-emerald-500/40 text-emerald-300 text-xs flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4" />
                <span>{actionStatusMsg}</span>
              </div>
            )}

            <form onSubmit={handleActionSubmit} className="space-y-4 text-xs">
              <div>
                <label className="block text-slate-400 mb-1">Select Action Type</label>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => setSelectedAction('acknowledge')}
                    className={`p-2.5 rounded-lg border text-left flex items-center gap-2 ${
                      selectedAction === 'acknowledge'
                        ? 'bg-teal-600/20 border-teal-500 text-teal-300 font-semibold'
                        : 'bg-slate-950 border-slate-800 text-slate-400 hover:border-slate-700'
                    }`}
                  >
                    <CheckCircle2 className="h-4 w-4" /> Acknowledge
                  </button>

                  <button
                    type="button"
                    onClick={() => setSelectedAction('snooze')}
                    className={`p-2.5 rounded-lg border text-left flex items-center gap-2 ${
                      selectedAction === 'snooze'
                        ? 'bg-amber-600/20 border-amber-500 text-amber-300 font-semibold'
                        : 'bg-slate-950 border-slate-800 text-slate-400 hover:border-slate-700'
                    }`}
                  >
                    <VolumeX className="h-4 w-4" /> Snooze
                  </button>

                  <button
                    type="button"
                    onClick={() => setSelectedAction('false_alarm')}
                    className={`p-2.5 rounded-lg border text-left flex items-center gap-2 ${
                      selectedAction === 'false_alarm'
                        ? 'bg-rose-600/20 border-rose-500 text-rose-300 font-semibold'
                        : 'bg-slate-950 border-slate-800 text-slate-400 hover:border-slate-700'
                    }`}
                  >
                    <XCircle className="h-4 w-4" /> False Alarm
                  </button>

                  <button
                    type="button"
                    onClick={() => setSelectedAction('add_note')}
                    className={`p-2.5 rounded-lg border text-left flex items-center gap-2 ${
                      selectedAction === 'add_note'
                        ? 'bg-cyan-600/20 border-cyan-500 text-cyan-300 font-semibold'
                        : 'bg-slate-950 border-slate-800 text-slate-400 hover:border-slate-700'
                    }`}
                  >
                    <FileText className="h-4 w-4" /> Clinical Note
                  </button>
                </div>
              </div>

              {selectedAction === 'snooze' && (
                <div>
                  <label className="block text-slate-400 mb-1">Snooze Duration</label>
                  <div className="flex gap-2">
                    {[1, 2, 4].map((h) => (
                      <button
                        type="button"
                        key={h}
                        onClick={() => setSnoozeHours(h)}
                        className={`flex-1 py-1.5 rounded-md border text-center font-mono ${
                          snoozeHours === h
                            ? 'bg-amber-500 text-slate-950 font-bold border-amber-400'
                            : 'bg-slate-950 border-slate-800 text-slate-300'
                        }`}
                      >
                        {h} Hour{h > 1 ? 's' : ''}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              <div>
                <label className="block text-slate-400 mb-1">Clinical Note / Reason</label>
                <textarea
                  id="textarea-action-note"
                  rows={3}
                  value={actionNote}
                  onChange={(e) => setActionNote(e.target.value)}
                  placeholder="Enter reason or clinical observation..."
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-teal-500"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setActionModalOpen(false)}
                  className="px-4 py-2 rounded-lg bg-slate-800 text-slate-300 hover:bg-slate-700"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  id="btn-submit-action"
                  className="px-4 py-2 rounded-lg bg-teal-600 hover:bg-teal-500 text-white font-semibold flex items-center gap-1.5"
                >
                  <Send className="h-3.5 w-3.5" /> Submit Action
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
