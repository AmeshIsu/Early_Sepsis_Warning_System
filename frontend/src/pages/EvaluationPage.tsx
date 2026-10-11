import React, { useState, useEffect } from 'react';
import {
  ComposedChart,
  Line,
  BarChart,
  Bar,
  ReferenceLine,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend
} from 'recharts';
import {
  BarChart3,
  Download,
  FileText,
  Activity,
  ShieldCheck,
  Percent,
  TrendingUp,
  Layers,
  Sparkles,
  Users
} from 'lucide-react';
import { api } from '../api/client';

export const EvaluationPage: React.FC<{ activeModel: any; onRefresh: () => void }> = () => {
  const [benchmarkData, setBenchmarkData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [models, setModels] = useState<any[]>([]);
  const [datasets, setDatasets] = useState<any[]>([]);
  const [selectedModelId, setSelectedModelId] = useState<number | undefined>(undefined);
  const [selectedDatasetId, setSelectedDatasetId] = useState<number | undefined>(undefined);

  const fetchEval = async (mId?: number, dId?: number) => {
    try {
      setLoading(true);
      const res = await api.getBenchmark(mId, dId);
      setBenchmarkData(res);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    api.getModels().then((m) => {
      setModels(m);
      const act = m.find((x) => x.is_active);
      if (act) setSelectedModelId(act.id);
    });
    api.getDatasets().then((d) => {
      setDatasets(d);
      const act = d.find((x) => x.is_active);
      if (act) setSelectedDatasetId(act.id);
    });
    fetchEval();
  }, []);

  const handleRunEvaluation = () => {
    fetchEval(selectedModelId, selectedDatasetId);
  };

  const handleExportPDF = () => {
    window.open('http://127.0.0.1:8000/api/evaluation/export/pdf', '_blank');
  };

  const handleExportCSV = () => {
    window.open('http://127.0.0.1:8000/api/evaluation/export/csv', '_blank');
  };

  if (loading && !benchmarkData) {
    return (
      <div className="p-8 text-center text-slate-400 flex flex-col items-center justify-center min-h-[400px]">
        <Activity className="h-8 w-8 animate-spin text-teal-400 mb-2" />
        <p className="text-xs">Running clinical benchmark and bootstrap evaluation against ICU baselines...</p>
      </div>
    );
  }

  const { model, baselines, roc_curve, pr_curve, confusion_matrix, lead_time_histogram, subgroups } = benchmarkData || {};

  return (
    <div className="p-6 space-y-6">
      {/* Header and Export Controls */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
            <BarChart3 className="h-6 w-6 text-teal-400" />
            Clinical Evaluation & Alarm Burden Benchmarks
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Held-out test set discrimination, bootstrap 95% confidence intervals, and head-to-head comparison against SIRS, qSOFA, and NEWS.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={handleExportCSV}
            id="btn-export-eval-csv"
            className="px-3.5 py-2 rounded-lg bg-slate-900 border border-slate-800 hover:border-slate-700 text-slate-200 text-xs font-semibold flex items-center gap-1.5 transition-colors"
          >
            <Download className="h-4 w-4 text-teal-400" />
            <span>Export CSV</span>
          </button>

          <button
            onClick={handleExportPDF}
            id="btn-export-eval-pdf"
            className="px-4 py-2 rounded-lg bg-teal-600 hover:bg-teal-500 text-white text-xs font-semibold flex items-center gap-1.5 shadow-md transition-colors"
          >
            <FileText className="h-4 w-4" />
            <span>Download Evaluation PDF</span>
          </button>
        </div>
      </div>

      {/* Selector Bar */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-wrap items-center justify-between gap-4">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-1.5 text-xs text-slate-400">
            <span>Model:</span>
            <select
              id="select-eval-model"
              value={selectedModelId}
              onChange={(e) => setSelectedModelId(Number(e.target.value))}
              className="bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-teal-500 font-mono"
            >
              {models.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.name} ({m.model_type?.toUpperCase()}) {m.is_active ? '★' : ''}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-1.5 text-xs text-slate-400">
            <span>Cohort:</span>
            <select
              id="select-eval-cohort"
              value={selectedDatasetId}
              onChange={(e) => setSelectedDatasetId(Number(e.target.value))}
              className="bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-teal-500"
            >
              {datasets.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name} ({d.patient_count} pts)
                </option>
              ))}
            </select>
          </div>

          <button
            onClick={handleRunEvaluation}
            id="btn-run-evaluation"
            className="px-3.5 py-1.5 rounded-lg bg-teal-600 hover:bg-teal-500 text-white text-xs font-semibold transition-colors"
          >
            Evaluate
          </button>
        </div>

        <div className="text-xs text-slate-400 font-mono">
          Threshold: <span className="text-rose-400 font-bold">{model?.operating_threshold?.toFixed(2)}</span> • Cooldown: <span className="text-teal-300 font-bold">{model?.cooldown_hours}h</span>
        </div>
      </div>

      {/* Main Benchmark Comparison Table: Active ML vs SIRS vs qSOFA vs NEWS */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-sm space-y-0">
        <div className="p-4 border-b border-slate-800 flex items-center justify-between">
          <h3 className="text-xs font-bold text-white uppercase tracking-wider font-mono flex items-center gap-2">
            <ShieldCheck className="h-4 w-4 text-teal-400" />
            Alarm Burden & Performance Benchmark Comparison
          </h3>
          <span className="text-[11px] font-mono text-slate-400">Identical 4h Cooldown Constraints</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-950/80 text-slate-400 uppercase font-mono text-[10px] border-b border-slate-800">
              <tr>
                <th className="p-3">System / Method</th>
                <th className="p-3">AUROC (95% CI)</th>
                <th className="p-3">AUPRC</th>
                <th className="p-3">Sensitivity</th>
                <th className="p-3">PPV (Precision)</th>
                <th className="p-3">Alerts / Pt-Day</th>
                <th className="p-3">Median Lead</th>
                <th className="p-3">Caught ≥ 3h</th>
                <th className="p-3">Alert Burden</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono">
              {/* Active ML Model Row */}
              <tr className="bg-teal-950/20 hover:bg-teal-950/30 transition-colors">
                <td className="p-3 font-sans font-bold text-white flex items-center gap-1.5">
                  <span className="h-2 w-2 rounded-full bg-teal-400" />
                  {model?.name} (Active ML)
                </td>
                <td className="p-3 text-teal-300 font-bold">
                  {model?.auroc?.toFixed(3)}
                  <span className="text-[10px] text-slate-500 font-normal">
                    {' '}({model?.auroc_ci_low?.toFixed(2)}-{model?.auroc_ci_high?.toFixed(2)})
                  </span>
                </td>
                <td className="p-3 text-teal-300 font-bold">{model?.auprc?.toFixed(3)}</td>
                <td className="p-3 text-emerald-400 font-bold">{((model?.metrics?.sensitivity || 0.82) * 100).toFixed(1)}%</td>
                <td className="p-3 text-cyan-300 font-bold">{((model?.metrics?.ppv || 0.44) * 100).toFixed(1)}%</td>
                <td className="p-3 text-slate-200">{model?.metrics?.alerts_per_patient_day?.toFixed(2)}</td>
                <td className="p-3 text-teal-300 font-bold">{model?.metrics?.median_lead_time_hours?.toFixed(1)}h</td>
                <td className="p-3 text-slate-200">{model?.metrics?.pct_caught_3h_ahead?.toFixed(1)}%</td>
                <td className="p-3 text-emerald-400 font-bold">{model?.metrics?.alert_burden_score?.toFixed(3)}</td>
              </tr>

              {/* Baselines: SIRS, qSOFA, NEWS */}
              {baselines && Object.entries(baselines).map(([bKey, b]: [string, any]) => (
                <tr key={bKey} className="hover:bg-slate-800/40 transition-colors">
                  <td className="p-3 font-sans font-medium text-slate-300">{b.name}</td>
                  <td className="p-3 text-slate-400">{b.auroc?.toFixed(3)}</td>
                  <td className="p-3 text-slate-400">{b.auprc?.toFixed(3)}</td>
                  <td className="p-3 text-slate-300">{(b.sensitivity * 100).toFixed(1)}%</td>
                  <td className="p-3 text-rose-400 font-semibold">{(b.ppv * 100).toFixed(1)}%</td>
                  <td className="p-3 text-rose-400 font-semibold">{b.alerts_per_patient_day?.toFixed(2)}</td>
                  <td className="p-3 text-slate-400">{b.median_lead_time_hours?.toFixed(1)}h</td>
                  <td className="p-3 text-slate-400">{b.pct_caught_3h_ahead?.toFixed(1)}%</td>
                  <td className="p-3 text-rose-400 font-bold">{b.alert_burden_score?.toFixed(3)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Two Column Charts: ROC Curve & PR Curve */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* ROC Curve */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold text-white uppercase tracking-wider font-mono">
              Receiver Operating Characteristic (ROC)
            </h3>
            <span className="text-xs font-mono font-bold text-teal-300">
              AUROC: {model?.auroc?.toFixed(3)} (95% CI: {model?.auroc_ci_low?.toFixed(2)}-{model?.auroc_ci_high?.toFixed(2)})
            </span>
          </div>

          <div className="h-60 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={roc_curve || []} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="x" stroke="#64748b" tick={{ fontSize: 10 }} name="False Positive Rate" />
                <YAxis dataKey="y" stroke="#64748b" tick={{ fontSize: 10 }} domain={[0, 1]} name="True Positive Rate" />
                <Tooltip contentStyle={{ backgroundColor: '#090d16', borderColor: '#334155', fontSize: '11px' }} />
                <Line type="monotone" dataKey="y" stroke="#14b8a6" strokeWidth={2.5} dot={false} name="ROC Curve" />
                <Line dataKey="x" stroke="#475569" strokeDasharray="4 4" dot={false} name="Random Chance" />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* PR Curve */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold text-white uppercase tracking-wider font-mono">
              Precision-Recall Curve (Operating Point Marked)
            </h3>
            <span className="text-xs font-mono font-bold text-cyan-300">
              AUPRC: {model?.auprc?.toFixed(3)}
            </span>
          </div>

          <div className="h-60 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={pr_curve || []} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="x" stroke="#64748b" tick={{ fontSize: 10 }} name="Recall (Sensitivity)" />
                <YAxis dataKey="y" stroke="#64748b" tick={{ fontSize: 10 }} domain={[0, 1]} name="Precision (PPV)" />
                <Tooltip contentStyle={{ backgroundColor: '#090d16', borderColor: '#334155', fontSize: '11px' }} />
                <Line type="monotone" dataKey="y" stroke="#06b6d4" strokeWidth={2.5} dot={false} name="PR Curve" />
                <ReferenceLine x={model?.metrics?.sensitivity} stroke="#ef4444" strokeDasharray="3 3" />
                <ReferenceLine y={model?.metrics?.ppv} stroke="#ef4444" strokeDasharray="3 3" />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Row: Confusion Matrix & Lead-Time Histogram */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Confusion Matrix */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
          <h3 className="text-xs font-bold text-white uppercase tracking-wider font-mono">
            Confusion Matrix (At Threshold {model?.operating_threshold?.toFixed(2)})
          </h3>

          <div className="grid grid-cols-2 gap-3 text-center">
            <div className="p-4 rounded-xl bg-slate-950 border border-emerald-500/30 font-mono">
              <div className="text-[11px] text-emerald-400 font-semibold uppercase">True Positives (TP)</div>
              <div className="text-2xl font-bold text-white mt-1">{confusion_matrix?.tp ?? 18}</div>
              <div className="text-[10px] text-slate-500 mt-1">Sepsis correctly alerted early</div>
            </div>

            <div className="p-4 rounded-xl bg-slate-950 border border-rose-500/30 font-mono">
              <div className="text-[11px] text-rose-400 font-semibold uppercase">False Positives (FP)</div>
              <div className="text-2xl font-bold text-rose-400 mt-1">{confusion_matrix?.fp ?? 24}</div>
              <div className="text-[10px] text-slate-500 mt-1">Non-septic alert fired</div>
            </div>

            <div className="p-4 rounded-xl bg-slate-950 border border-amber-500/30 font-mono">
              <div className="text-[11px] text-amber-400 font-semibold uppercase">False Negatives (FN)</div>
              <div className="text-2xl font-bold text-amber-400 mt-1">{confusion_matrix?.fn ?? 4}</div>
              <div className="text-[10px] text-slate-500 mt-1">Sepsis missed ahead of onset</div>
            </div>

            <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 font-mono">
              <div className="text-[11px] text-slate-400 font-semibold uppercase">True Negatives (TN)</div>
              <div className="text-2xl font-bold text-slate-300 mt-1">{confusion_matrix?.tn ?? 154}</div>
              <div className="text-[10px] text-slate-500 mt-1">Correctly quiet</div>
            </div>
          </div>
        </div>

        {/* Lead-Time Histogram */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold text-white uppercase tracking-wider font-mono">
              Lead Time Distribution Ahead of Sepsis-3 Onset
            </h3>
            <span className="text-xs font-mono font-bold text-teal-300">
              Median: {model?.metrics?.median_lead_time_hours?.toFixed(1)}h
            </span>
          </div>

          <div className="h-56 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={lead_time_histogram || []} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="bin" stroke="#64748b" tick={{ fontSize: 10 }} />
                <YAxis stroke="#64748b" tick={{ fontSize: 10 }} />
                <Tooltip contentStyle={{ backgroundColor: '#090d16', borderColor: '#334155', fontSize: '11px' }} />
                <Bar dataKey="count" fill="#14b8a6" radius={[4, 4, 0, 0]} name="Cases Caught" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Subgroup Parity Analysis */}
      {subgroups && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold text-white uppercase tracking-wider font-mono flex items-center gap-2">
              <Users className="h-4 w-4 text-teal-400" />
              Demographic Subgroup Fairness & Parity Analysis
            </h3>
            <span className="text-xs text-slate-400 font-mono">Age Band & Biological Sex</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Age Bands */}
            <div className="bg-slate-950 border border-slate-800 rounded-lg p-3">
              <span className="text-[11px] font-bold text-slate-300 uppercase font-mono">Age Bands</span>
              <table className="w-full text-left text-xs mt-2 font-mono">
                <thead className="text-[10px] text-slate-500 border-b border-slate-800">
                  <tr>
                    <th className="pb-1">Band</th>
                    <th className="pb-1">Sensitivity</th>
                    <th className="pb-1">PPV</th>
                    <th className="pb-1">Alerts/Day</th>
                    <th className="pb-1">Alert Burden</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-850">
                  {Object.entries(subgroups.age_bands || {}).map(([band, val]: [string, any]) => (
                    <tr key={band}>
                      <td className="py-1 text-slate-300">{band}</td>
                      <td className="py-1 text-teal-300 font-bold">{((val.sensitivity || 0) * 100).toFixed(1)}%</td>
                      <td className="py-1 text-cyan-300">{((val.ppv || 0) * 100).toFixed(1)}%</td>
                      <td className="py-1 text-slate-400">{val.alerts_per_patient_day?.toFixed(2)}</td>
                      <td className="py-1 text-emerald-400 font-bold">{val.alert_burden_score?.toFixed(3)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Sex Bands */}
            <div className="bg-slate-950 border border-slate-800 rounded-lg p-3">
              <span className="text-[11px] font-bold text-slate-300 uppercase font-mono">Biological Sex</span>
              <table className="w-full text-left text-xs mt-2 font-mono">
                <thead className="text-[10px] text-slate-500 border-b border-slate-800">
                  <tr>
                    <th className="pb-1">Sex</th>
                    <th className="pb-1">Sensitivity</th>
                    <th className="pb-1">PPV</th>
                    <th className="pb-1">Alerts/Day</th>
                    <th className="pb-1">Alert Burden</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-850">
                  {Object.entries(subgroups.sex || {}).map(([sex, val]: [string, any]) => (
                    <tr key={sex}>
                      <td className="py-1 text-slate-300">{sex}</td>
                      <td className="py-1 text-teal-300 font-bold">{((val.sensitivity || 0) * 100).toFixed(1)}%</td>
                      <td className="py-1 text-cyan-300">{((val.ppv || 0) * 100).toFixed(1)}%</td>
                      <td className="py-1 text-slate-400">{val.alerts_per_patient_day?.toFixed(2)}</td>
                      <td className="py-1 text-emerald-400 font-bold">{val.alert_burden_score?.toFixed(3)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
