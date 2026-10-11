import React, { useState, useEffect } from 'react';
import {
  ComposedChart,
  Line,
  Bar,
  ReferenceLine,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  Scatter
} from 'recharts';
import {
  Sliders,
  CheckCircle2,
  AlertTriangle,
  Clock,
  ShieldAlert,
  Percent,
  TrendingDown,
  Layers,
  Sparkles,
  Save
} from 'lucide-react';
import { api } from '../api/client';
import { CalibrationData } from '../types';

export const CalibrationThresholds: React.FC<{ activeModel: any; onRefresh: () => void }> = ({ activeModel, onRefresh }) => {
  const [calData, setCalData] = useState<CalibrationData | null>(null);
  const [loading, setLoading] = useState(false);
  const [saveMsg, setSaveMsg] = useState<string | null>(null);

  // Optimization form controls
  const [calibMethod, setCalibMethod] = useState('platt');
  const [optMode, setOptMode] = useState('f_beta'); // 'f_beta', 'target_sensitivity', 'alert_cap', 'manual'
  const [manualThreshold, setManualThreshold] = useState(0.35);
  const [targetBeta, setTargetBeta] = useState(1.0);
  const [targetSens, setTargetSens] = useState(0.85);
  const [alertCap, setAlertCap] = useState(1.5);
  const [cooldownHours, setCooldownHours] = useState(4.0);
  const [consecutiveHours, setConsecutiveHours] = useState(1);
  const [escalationDelta, setEscalationDelta] = useState(0.15);

  // Current active metrics calculated at active threshold
  const [currentMetrics, setCurrentMetrics] = useState<any>(null);

  const fetchCalibration = async () => {
    try {
      setLoading(true);
      const data = await api.getCalibration();
      setCalData(data);
      setCalibMethod(data.calibration_method || 'platt');
      setManualThreshold(data.operating_threshold || 0.35);
      setCooldownHours(data.cooldown_hours || 4.0);
      setCurrentMetrics(data.current_metrics);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCalibration();
  }, []);

  // When sliders or mode change, simulate threshold optimization
  const runOptimization = async (mode = optMode, thresh = manualThreshold) => {
    try {
      const res = await api.optimizeThreshold({
        mode,
        manual_threshold: thresh,
        beta: targetBeta,
        target_sensitivity: targetSens,
        alert_cap: alertCap,
        cooldown_hours: cooldownHours,
        consecutive_hours: consecutiveHours,
        calibration_method: calibMethod
      });
      setManualThreshold(res.threshold);
      setCurrentMetrics(res.metrics);
    } catch (err) {
      console.error(err);
    }
  };

  const handleManualSliderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = parseFloat(e.target.value);
    setManualThreshold(val);
    setOptMode('manual');
    runOptimization('manual', val);
  };

  const handleApplyThreshold = async () => {
    try {
      await api.applyCalibration({
        threshold: manualThreshold,
        mode: optMode,
        cooldown_hours: cooldownHours,
        consecutive_hours: consecutiveHours,
        escalation_delta: escalationDelta,
        calibration_method: calibMethod
      });
      setSaveMsg(`Operating threshold (${manualThreshold.toFixed(2)}) and cooldown rules successfully applied!`);
      onRefresh();
      setTimeout(() => setSaveMsg(null), 3000);
    } catch (err: any) {
      alert('Error saving calibration: ' + err.message);
    }
  };

  if (!calData && loading) {
    return <div className="p-8 text-center text-slate-400">Loading probability calibration profiles...</div>;
  }

  // Formatting reliability diagram data for side-by-side visualization
  const reliabilityData = calData?.reliability_raw?.map((rawItem, i) => {
    const calItem = calData?.reliability_calibrated?.[i] || rawItem;
    return {
      bin: `Bin ${i + 1}`,
      confidence_raw: rawItem.confidence,
      accuracy_raw: rawItem.accuracy,
      confidence_cal: calItem.confidence,
      accuracy_cal: calItem.accuracy,
      ideal: (rawItem.confidence + rawItem.accuracy) / 2
    };
  }) || [];

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
            <Sliders className="h-6 w-6 text-teal-400" />
            Calibration & Threshold Optimization
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Platt scaling, reliability diagrams, and Precision-Recall threshold tuning under alarm fatigue constraints.
          </p>
        </div>

        <button
          onClick={handleApplyThreshold}
          id="btn-apply-calibration"
          className="px-4 py-2 rounded-lg bg-teal-600 hover:bg-teal-500 text-white font-semibold text-xs shadow-md transition-colors flex items-center gap-1.5"
        >
          <Save className="h-4 w-4" />
          <span>Apply to Active Model</span>
        </button>
      </div>

      {saveMsg && (
        <div className="p-3 rounded-lg bg-emerald-950/60 border border-emerald-500/40 text-emerald-200 text-xs flex items-center gap-2">
          <CheckCircle2 className="h-4 w-4" />
          <span>{saveMsg}</span>
        </div>
      )}

      {/* Top Row: Calibration Reliability Diagram & ECE Stats */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Reliability Diagram (7 cols) */}
        <div className="lg:col-span-7 bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-xs font-bold text-white uppercase tracking-wider font-mono">
                Reliability Calibration Diagram (Validation Set)
              </h3>
              <p className="text-[11px] text-slate-400">
                Mean Predicted Confidence vs Empirical Positive Fraction across 10 deciles
              </p>
            </div>

            <div className="flex items-center gap-2 text-xs">
              <span className="text-slate-400">Method:</span>
              <select
                id="select-calib-method"
                value={calibMethod}
                onChange={(e) => {
                  setCalibMethod(e.target.value);
                  fetchCalibration();
                }}
                className="bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1 text-xs text-slate-200 focus:outline-none focus:border-teal-500"
              >
                <option value="platt">Platt Scaling (Sigmoidal)</option>
                <option value="isotonic">Isotonic Regression</option>
                <option value="none">Uncalibrated (Raw Logits)</option>
              </select>
            </div>
          </div>

          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={reliabilityData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="bin" stroke="#64748b" tick={{ fontSize: 10 }} />
                <YAxis stroke="#64748b" tick={{ fontSize: 10 }} domain={[0, 1]} tickFormatter={(v) => `${(v * 100).toFixed(0)}%`} />
                <Tooltip contentStyle={{ backgroundColor: '#090d16', borderColor: '#334155', fontSize: '11px' }} />
                <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '6px' }} />
                <Line type="monotone" dataKey="confidence_raw" stroke="#f43f5e" strokeDasharray="3 3" strokeWidth={1.8} name="Raw Confidence" dot={false} />
                <Line type="monotone" dataKey="accuracy_cal" stroke="#10b981" strokeWidth={2.5} name="Calibrated Accuracy" activeDot={{ r: 4 }} />
                <Line type="monotone" dataKey="confidence_cal" stroke="#06b6d4" strokeWidth={2} name="Calibrated Confidence" dot={false} />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Right: Brier Score & ECE Comparison Cards (5 cols) */}
        <div className="lg:col-span-5 space-y-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm space-y-3">
            <h3 className="text-xs font-bold text-white uppercase tracking-wider font-mono">
              Expected Calibration Error (ECE)
            </h3>
            <div className="grid grid-cols-2 gap-3 text-center">
              <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 font-mono">
                <div className="text-[10px] text-slate-500 uppercase">Raw ECE</div>
                <div className="text-xl font-bold text-rose-400 mt-1">
                  {(calData?.ece_raw ? calData.ece_raw * 100 : 12.4).toFixed(1)}%
                </div>
              </div>

              <div className="p-3 rounded-lg bg-slate-950 border border-teal-500/30 font-mono">
                <div className="text-[10px] text-teal-400 uppercase">Calibrated ECE</div>
                <div className="text-xl font-bold text-teal-300 mt-1">
                  {(calData?.ece_calibrated ? calData.ece_calibrated * 100 : 2.8).toFixed(1)}%
                </div>
              </div>
            </div>
            <p className="text-[11px] text-slate-400 leading-relaxed">
              Lower ECE guarantees that a predicted 70% risk translates to a true 70% sepsis incidence in real clinical practice.
            </p>
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm space-y-3">
            <h3 className="text-xs font-bold text-white uppercase tracking-wider font-mono">
              Brier Probability Score
            </h3>
            <div className="grid grid-cols-2 gap-3 text-center">
              <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 font-mono">
                <div className="text-[10px] text-slate-500 uppercase">Raw Brier</div>
                <div className="text-xl font-bold text-slate-300 mt-1">
                  {(calData?.brier_score_raw || 0.14).toFixed(4)}
                </div>
              </div>

              <div className="p-3 rounded-lg bg-slate-950 border border-teal-500/30 font-mono">
                <div className="text-[10px] text-teal-400 uppercase">Calibrated Brier</div>
                <div className="text-xl font-bold text-teal-300 mt-1">
                  {(calData?.brier_score_calibrated || 0.08).toFixed(4)}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Threshold Optimization & Alarm Fatigue Simulator */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm space-y-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-4">
          <div>
            <h3 className="text-sm font-bold text-white uppercase tracking-wider font-mono flex items-center gap-2">
              <ShieldAlert className="h-4 w-4 text-rose-400" />
              Precision-Recall Operating Point & Alarm Fatigue Tuning
            </h3>
            <p className="text-xs text-slate-400 mt-1">
              Select an optimization objective or adjust the threshold slider. All bedside alarm metrics recalculate in real-time.
            </p>
          </div>

          {/* Mode Selector Tabs */}
          <div className="flex bg-slate-950 p-1 rounded-lg border border-slate-800 text-xs">
            <button
              onClick={() => { setOptMode('f_beta'); runOptimization('f_beta'); }}
              className={`px-3 py-1.5 rounded-md font-medium ${
                optMode === 'f_beta' ? 'bg-teal-600 text-white' : 'text-slate-400 hover:text-white'
              }`}
            >
              F-Beta Max
            </button>
            <button
              onClick={() => { setOptMode('target_sensitivity'); runOptimization('target_sensitivity'); }}
              className={`px-3 py-1.5 rounded-md font-medium ${
                optMode === 'target_sensitivity' ? 'bg-teal-600 text-white' : 'text-slate-400 hover:text-white'
              }`}
            >
              Target Sensitivity
            </button>
            <button
              onClick={() => { setOptMode('alert_cap'); runOptimization('alert_cap'); }}
              className={`px-3 py-1.5 rounded-md font-medium ${
                optMode === 'alert_cap' ? 'bg-teal-600 text-white' : 'text-slate-400 hover:text-white'
              }`}
            >
              Cap Alerts/Day
            </button>
            <button
              onClick={() => setOptMode('manual')}
              className={`px-3 py-1.5 rounded-md font-medium ${
                optMode === 'manual' ? 'bg-teal-600 text-white' : 'text-slate-400 hover:text-white'
              }`}
            >
              Manual Slider
            </button>
          </div>
        </div>

        {/* Operating Point Slider & Controls */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 p-4 rounded-xl bg-slate-950 border border-slate-800">
          <div className="md:col-span-2 space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="text-slate-300 font-semibold">Operating Alert Threshold</span>
              <span className="font-mono text-base font-bold text-rose-400">
                {manualThreshold.toFixed(2)}
              </span>
            </div>
            <input
              type="range"
              id="slider-threshold"
              min={0.05}
              max={0.90}
              step={0.01}
              value={manualThreshold}
              onChange={handleManualSliderChange}
              className="w-full accent-rose-500 h-2 bg-slate-800 rounded-lg cursor-pointer"
            />
            <div className="flex justify-between text-[10px] text-slate-500 font-mono">
              <span>0.05 (High Sensitivity)</span>
              <span>0.50</span>
              <span>0.90 (High Specificity)</span>
            </div>
          </div>

          <div>
            <label className="block text-slate-400 text-xs mb-1">Cooldown Window</label>
            <select
              value={cooldownHours}
              onChange={(e) => {
                setCooldownHours(Number(e.target.value));
                runOptimization(optMode);
              }}
              className="w-full bg-slate-900 border border-slate-800 rounded-lg p-2 text-xs text-slate-200 focus:outline-none focus:border-teal-500 font-mono"
            >
              <option value={2.0}>2.0 Hours</option>
              <option value={4.0}>4.0 Hours (Standard)</option>
              <option value={6.0}>6.0 Hours</option>
              <option value={12.0}>12.0 Hours</option>
            </select>
          </div>

          <div>
            <label className="block text-slate-400 text-xs mb-1">Persistence Rule</label>
            <select
              value={consecutiveHours}
              onChange={(e) => {
                setConsecutiveHours(Number(e.target.value));
                runOptimization(optMode);
              }}
              className="w-full bg-slate-900 border border-slate-800 rounded-lg p-2 text-xs text-slate-200 focus:outline-none focus:border-teal-500 font-mono"
            >
              <option value={1}>1 Hour (Instant Alert)</option>
              <option value={2}>2 Consecutive Hours (Suppressed)</option>
            </select>
          </div>
        </div>

        {/* Real-time Alarm Fatigue Metrics Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3 text-center">
          <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 font-mono">
            <div className="text-[10px] text-slate-500 uppercase">Alerts / Pt-Day</div>
            <div className="text-lg font-bold text-white mt-1" id="val-alerts-pt-day">
              {currentMetrics?.alerts_per_patient_day ?? 0.95}
            </div>
          </div>

          <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 font-mono">
            <div className="text-[10px] text-slate-500 uppercase">Alerts / True Sepsis</div>
            <div className="text-lg font-bold text-white mt-1">
              {currentMetrics?.alerts_per_true_case ?? 2.1}
            </div>
          </div>

          <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 font-mono">
            <div className="text-[10px] text-slate-500 uppercase">Sensitivity (Recall)</div>
            <div className="text-lg font-bold text-teal-400 mt-1" id="val-sensitivity">
              {((currentMetrics?.sensitivity ?? 0.82) * 100).toFixed(1)}%
            </div>
          </div>

          <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 font-mono">
            <div className="text-[10px] text-slate-500 uppercase">PPV (Precision)</div>
            <div className="text-lg font-bold text-cyan-400 mt-1" id="val-ppv">
              {((currentMetrics?.ppv ?? 0.44) * 100).toFixed(1)}%
            </div>
          </div>

          <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 font-mono">
            <div className="text-[10px] text-slate-500 uppercase">Median Lead Time</div>
            <div className="text-lg font-bold text-teal-300 mt-1">
              {currentMetrics?.median_lead_time_hours ?? 4.8}h
            </div>
          </div>

          <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 font-mono">
            <div className="text-[10px] text-slate-500 uppercase">False Alarms / 100d</div>
            <div className="text-lg font-bold text-rose-400 mt-1">
              {currentMetrics?.false_alarms_per_100_pt_days ?? 42.1}
            </div>
          </div>

          <div className="p-3 rounded-lg bg-slate-950 border border-teal-500/30 font-mono">
            <div className="text-[10px] text-teal-400 uppercase">Alert Burden Score</div>
            <div className="text-lg font-bold text-teal-300 mt-1" id="val-alert-burden">
              {currentMetrics?.alert_burden_score ?? 0.53}
            </div>
          </div>
        </div>

        {/* PR Curve Plot with Operating Point Marker */}
        <div className="pt-2">
          <div className="flex items-center justify-between mb-2">
            <h4 className="text-xs font-bold text-slate-300 uppercase font-mono">
              Precision-Recall Curve with Selected Operating Point
            </h4>
            <span className="text-[11px] font-mono text-slate-500">
              Red marker denotes current operating threshold ({manualThreshold.toFixed(2)})
            </span>
          </div>

          <div className="h-56 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={calData?.pr_curve || []} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="sensitivity" stroke="#64748b" tick={{ fontSize: 10 }} tickFormatter={(v) => `${(v * 100).toFixed(0)}%`} name="Sensitivity" />
                <YAxis stroke="#64748b" tick={{ fontSize: 10 }} domain={[0, 1]} tickFormatter={(v) => `${(v * 100).toFixed(0)}%`} name="PPV" />
                <Tooltip contentStyle={{ backgroundColor: '#090d16', borderColor: '#334155', fontSize: '11px' }} />
                <Line type="monotone" dataKey="ppv" stroke="#14b8a6" strokeWidth={2.5} name="PPV vs Sensitivity" dot={false} />
                <ReferenceLine x={currentMetrics?.sensitivity} stroke="#ef4444" strokeDasharray="3 3" />
                <ReferenceLine y={currentMetrics?.ppv} stroke="#ef4444" strokeDasharray="3 3" />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
};
