import React, { useState, useEffect } from 'react';
import {
  ComposedChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend
} from 'recharts';
import {
  Cpu,
  Play,
  Square,
  CheckCircle2,
  Trash2,
  Activity,
  Layers,
  Sparkles,
  ShieldCheck,
  TrendingUp
} from 'lucide-react';
import { api } from '../api/client';
import { ModelRegistryItem } from '../types';

export const ModelLab: React.FC<{ activeModel: any; onRefresh: () => void }> = ({ activeModel, onRefresh }) => {
  const [models, setModels] = useState<ModelRegistryItem[]>([]);
  const [trainingStatus, setTrainingStatus] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [statusPollInterval, setStatusPollInterval] = useState<any>(null);

  // Form config
  const [modelName, setModelName] = useState('ICU-GRU-v2');
  const [modelType, setModelType] = useState('gru');
  const [hiddenDim, setHiddenDim] = useState(64);
  const [numLayers, setNumLayers] = useState(2);
  const [epochs, setEpochs] = useState(8);
  const [lr, setLr] = useState(0.002);
  const [batchSize, setBatchSize] = useState(16);
  const [imputationMethod, setImputationMethod] = useState('masked');
  const [lossType, setLossType] = useState('weighted_bce');
  const [seed, setSeed] = useState(42);
  const [setActiveAfter, setSetActiveAfter] = useState(true);

  const fetchModels = async () => {
    try {
      setLoading(true);
      const list = await api.getModels();
      setModels(list);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const fetchStatus = async () => {
    try {
      const st = await api.getTrainingStatus();
      setTrainingStatus(st);
      if (st.is_running && !statusPollInterval) {
        const interval = setInterval(fetchStatus, 1200);
        setStatusPollInterval(interval);
      } else if (!st.is_running && statusPollInterval) {
        clearInterval(statusPollInterval);
        setStatusPollInterval(null);
        fetchModels();
        onRefresh();
      }
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    fetchModels();
    fetchStatus();
    return () => {
      if (statusPollInterval) clearInterval(statusPollInterval);
    };
  }, []);

  const handleStartTraining = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.trainModel({
        name: modelName,
        model_type: modelType,
        hidden_dim: hiddenDim,
        num_layers: numLayers,
        epochs,
        lr,
        batch_size: batchSize,
        imputation_method: imputationMethod,
        loss_type: lossType,
        seed,
        set_active: setActiveAfter
      });
      // Start polling
      const interval = setInterval(fetchStatus, 1000);
      setStatusPollInterval(interval);
      fetchStatus();
    } catch (err: any) {
      alert('Failed to initiate training: ' + err.message);
    }
  };

  const handleStopTraining = async () => {
    try {
      await api.stopTraining();
      fetchStatus();
    } catch (err: any) {
      alert('Error stopping training: ' + err.message);
    }
  };

  const handleActivateModel = async (id: number) => {
    try {
      await api.activateModel(id);
      fetchModels();
      onRefresh();
    } catch (err: any) {
      alert(err.message);
    }
  };

  const handleDeleteModel = async (id: number) => {
    if (!confirm('Are you sure you want to delete this model?')) return;
    try {
      await api.deleteModel(id);
      fetchModels();
      onRefresh();
    } catch (err: any) {
      alert(err.message);
    }
  };

  const isTraining = trainingStatus?.is_running;

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
          <Cpu className="h-6 w-6 text-teal-400" />
          Model Training Lab & Registry
        </h1>
        <p className="text-xs text-slate-400 mt-1">
          Configure PyTorch rolling sequence models, causal temporal transformers, and windowed baselines with alarm-fatigue calibration.
        </p>
      </div>

      {/* Grid: Form and Live Training Monitor */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Form: 5 cols */}
        <div className="lg:col-span-5 bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold text-white uppercase tracking-wider font-mono flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-teal-400" />
              Model Architecture & Training
            </h3>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-teal-500/20 text-teal-300 border border-teal-500/30">
              CPU-Optimized PyTorch
            </span>
          </div>

          <form onSubmit={handleStartTraining} className="space-y-3.5 text-xs">
            <div>
              <label className="block text-slate-400 mb-1">Model Name</label>
              <input
                type="text"
                id="input-model-name"
                value={modelName}
                onChange={(e) => setModelName(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-slate-200 focus:outline-none focus:border-teal-500 font-mono"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-slate-400 mb-1">Model Architecture</label>
                <select
                  id="select-model-type"
                  value={modelType}
                  onChange={(e) => setModelType(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-slate-200 focus:outline-none focus:border-teal-500"
                >
                  <option value="gru">PyTorch GRU (Recurrent)</option>
                  <option value="lstm">PyTorch LSTM</option>
                  <option value="transformer">Temporal Transformer (Causal)</option>
                  <option value="gbdt">Gradient Boosting (Windowed)</option>
                  <option value="logistic">Logistic Regression (Windowed)</option>
                </select>
              </div>

              <div>
                <label className="block text-slate-400 mb-1">Imputation Strategy</label>
                <select
                  id="select-imputation-method"
                  value={imputationMethod}
                  onChange={(e) => setImputationMethod(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-slate-200 focus:outline-none focus:border-teal-500"
                >
                  <option value="masked">Masked + Elapsed Delta (Default)</option>
                  <option value="locf_decay">LOCF + Exponential Decay</option>
                  <option value="patient_median">Patient Median Baseline</option>
                  <option value="pop_median">Population Median</option>
                </select>
              </div>
            </div>

            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className="block text-slate-400 mb-1">Hidden Dim</label>
                <select
                  value={hiddenDim}
                  onChange={(e) => setHiddenDim(Number(e.target.value))}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-slate-200 font-mono focus:outline-none focus:border-teal-500"
                >
                  <option value={32}>32</option>
                  <option value={48}>48</option>
                  <option value={64}>64</option>
                  <option value={128}>128</option>
                </select>
              </div>

              <div>
                <label className="block text-slate-400 mb-1">Layers</label>
                <select
                  value={numLayers}
                  onChange={(e) => setNumLayers(Number(e.target.value))}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-slate-200 font-mono focus:outline-none focus:border-teal-500"
                >
                  <option value={1}>1</option>
                  <option value={2}>2</option>
                  <option value={3}>3</option>
                </select>
              </div>

              <div>
                <label className="block text-slate-400 mb-1">Epochs</label>
                <input
                  type="number"
                  min={1}
                  max={50}
                  value={epochs}
                  onChange={(e) => setEpochs(Number(e.target.value))}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-slate-200 font-mono focus:outline-none focus:border-teal-500"
                />
              </div>
            </div>

            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className="block text-slate-400 mb-1">Learning Rate</label>
                <input
                  type="number"
                  step="0.0005"
                  value={lr}
                  onChange={(e) => setLr(Number(e.target.value))}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-slate-200 font-mono focus:outline-none focus:border-teal-500"
                />
              </div>

              <div>
                <label className="block text-slate-400 mb-1">Batch Size</label>
                <select
                  value={batchSize}
                  onChange={(e) => setBatchSize(Number(e.target.value))}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-slate-200 font-mono focus:outline-none focus:border-teal-500"
                >
                  <option value={8}>8</option>
                  <option value={16}>16</option>
                  <option value={32}>32</option>
                </select>
              </div>

              <div>
                <label className="block text-slate-400 mb-1">Loss Function</label>
                <select
                  value={lossType}
                  onChange={(e) => setLossType(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-slate-200 focus:outline-none focus:border-teal-500"
                >
                  <option value="weighted_bce">Weighted BCE</option>
                  <option value="focal">Focal Loss</option>
                </select>
              </div>
            </div>

            <div className="flex items-center gap-2 pt-1">
              <input
                type="checkbox"
                id="check-set-active"
                checked={setActiveAfter}
                onChange={(e) => setSetActiveAfter(e.target.checked)}
                className="rounded border-slate-700 text-teal-600 focus:ring-0 bg-slate-950"
              />
              <label htmlFor="check-set-active" className="text-slate-300 text-xs">
                Set as Active Model Upon Completion
              </label>
            </div>

            <div className="pt-2 flex gap-2">
              <button
                type="submit"
                id="btn-start-training"
                disabled={isTraining}
                className="flex-1 py-2.5 rounded-lg bg-teal-600 hover:bg-teal-500 disabled:opacity-50 text-white font-semibold flex items-center justify-center gap-2 transition-colors"
              >
                {isTraining ? <Activity className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
                <span>{isTraining ? 'Training in Progress...' : 'Start Training'}</span>
              </button>

              {isTraining && (
                <button
                  type="button"
                  id="btn-stop-training"
                  onClick={handleStopTraining}
                  className="px-4 py-2.5 rounded-lg bg-rose-600/30 hover:bg-rose-600 text-rose-300 hover:text-white font-semibold flex items-center gap-1.5 transition-colors"
                >
                  <Square className="h-4 w-4" /> Stop
                </button>
              )}
            </div>
          </form>
        </div>

        {/* Right Live Training Curves: 7 cols */}
        <div className="lg:col-span-7 bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-xs font-bold text-white uppercase tracking-wider font-mono">
                Live Training & Validation Convergence
              </h3>
              <p className="text-[11px] text-slate-400">
                {trainingStatus?.status_message || 'Worker ready.'}
              </p>
            </div>

            {isTraining && (
              <div className="flex items-center gap-2">
                <span className="font-mono text-xs font-bold text-teal-300">
                  {trainingStatus?.progress_pct}%
                </span>
                <div className="w-24 h-2 bg-slate-800 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-teal-500 transition-all duration-300"
                    style={{ width: `${trainingStatus?.progress_pct}%` }}
                  />
                </div>
              </div>
            )}
          </div>

          {/* Loss / Metric Chart */}
          <div className="h-72 w-full pt-2">
            {trainingStatus?.history && trainingStatus.history.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={trainingStatus.history} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis dataKey="epoch" stroke="#64748b" tick={{ fontSize: 10 }} unit=" ep" />
                  <YAxis stroke="#64748b" tick={{ fontSize: 10 }} />
                  <Tooltip contentStyle={{ backgroundColor: '#090d16', borderColor: '#334155', fontSize: '11px' }} />
                  <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '8px' }} />
                  <Line type="monotone" dataKey="train_loss" stroke="#f43f5e" strokeWidth={2} name="Train Loss" dot={false} />
                  <Line type="monotone" dataKey="val_loss" stroke="#06b6d4" strokeWidth={2} name="Val Loss" dot={false} />
                  <Line type="monotone" dataKey="val_auprc" stroke="#10b981" strokeWidth={2.5} name="Val AUPRC" activeDot={{ r: 4 }} />
                </ComposedChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex flex-col items-center justify-center text-slate-500 text-xs border border-dashed border-slate-800 rounded-lg">
                <Activity className="h-8 w-8 text-slate-600 mb-2" />
                <span>No active training history. Start training above to observe convergence.</span>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Model Registry Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-sm">
        <div className="p-4 border-b border-slate-800 flex items-center justify-between">
          <h3 className="text-xs font-bold text-white uppercase tracking-wider font-mono flex items-center gap-2">
            <Layers className="h-4 w-4 text-teal-400" />
            Model Registry & Benchmarking
          </h3>
          <span className="text-xs text-slate-400 font-mono">{models.length} Models Registered</span>
        </div>

        <table className="w-full text-left text-xs">
          <thead className="bg-slate-950/80 text-slate-400 uppercase font-mono text-[10px] border-b border-slate-800">
            <tr>
              <th className="p-3">Model Name</th>
              <th className="p-3">Architecture</th>
              <th className="p-3">AUROC (95% CI)</th>
              <th className="p-3">AUPRC</th>
              <th className="p-3">Alerts / Pt-Day</th>
              <th className="p-3">Median Lead</th>
              <th className="p-3">Alert Burden</th>
              <th className="p-3">Operating Threshold</th>
              <th className="p-3">Status</th>
              <th className="p-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60 font-mono">
            {models.map((m) => (
              <tr key={m.id} className="hover:bg-slate-800/40 transition-colors">
                <td className="p-3 font-sans font-semibold text-white">{m.name}</td>
                <td className="p-3 text-slate-400">{m.model_type?.toUpperCase()}</td>
                <td className="p-3 text-teal-300 font-bold">
                  {m.auroc?.toFixed(3)}
                  <span className="text-[10px] text-slate-500 font-normal">
                    {' '}({m.auroc_ci_low?.toFixed(2)}-{m.auroc_ci_high?.toFixed(2)})
                  </span>
                </td>
                <td className="p-3 text-cyan-300 font-bold">{m.auprc?.toFixed(3)}</td>
                <td className="p-3 text-slate-300">{m.alerts_per_patient_day?.toFixed(2)}</td>
                <td className="p-3 text-slate-300">{m.median_lead_time_hours?.toFixed(1)}h</td>
                <td className="p-3 text-emerald-400 font-bold">{m.alert_burden_score?.toFixed(3)}</td>
                <td className="p-3 text-rose-400 font-semibold">{m.operating_threshold?.toFixed(2)}</td>
                <td className="p-3 font-sans">
                  {m.is_active ? (
                    <span className="px-2 py-0.5 rounded text-[10px] bg-teal-950 text-teal-300 border border-teal-500/40 font-bold">
                      ACTIVE
                    </span>
                  ) : (
                    <span className="text-slate-500 text-[10px]">Inactive</span>
                  )}
                </td>
                <td className="p-3 text-right">
                  <div className="flex items-center justify-end gap-2 font-sans">
                    {!m.is_active && (
                      <button
                        onClick={() => handleActivateModel(m.id)}
                        className="px-2.5 py-1 rounded bg-teal-600/30 text-teal-300 hover:bg-teal-600 hover:text-white text-[11px]"
                      >
                        Set Active
                      </button>
                    )}
                    <button
                      onClick={() => handleDeleteModel(m.id)}
                      className="p-1 rounded text-slate-500 hover:text-rose-400 hover:bg-slate-800"
                      title="Delete Model"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
