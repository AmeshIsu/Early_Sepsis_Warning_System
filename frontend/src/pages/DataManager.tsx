import React, { useState, useEffect } from 'react';
import {
  Database,
  UploadCloud,
  PlusCircle,
  Trash2,
  CheckCircle2,
  AlertTriangle,
  Eye,
  FileSpreadsheet,
  Activity,
  Layers,
  Info
} from 'lucide-react';
import { api } from '../api/client';
import { DatasetMetaItem } from '../types';

export const DataManager: React.FC<{ onRefresh: () => void }> = ({ onRefresh }) => {
  const [datasets, setDatasets] = useState<DatasetMetaItem[]>([]);
  const [qualityReport, setQualityReport] = useState<any>(null);
  const [mimicNote, setMimicNote] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState<{ text: string; type: 'success' | 'error' } | null>(null);

  // Cohort generation form state
  const [genName, setGenName] = useState('ICU-Cohort-Synthetic');
  const [genCount, setGenCount] = useState(250);
  const [genPrev, setGenPrev] = useState(12);
  const [genSeed, setGenSeed] = useState(42);
  const [genActive, setGenActive] = useState(true);
  const [isGenerating, setIsGenerating] = useState(false);

  // File upload state
  const [uploadMode, setUploadMode] = useState<'psv' | 'csv'>('psv');
  const [psvFiles, setPsvFiles] = useState<FileList | null>(null);
  const [csvFile, setCsvFile] = useState<File | null>(null);
  const [csvDatasetName, setCsvDatasetName] = useState('PhysioNet-Ingested-Cohort');
  const [colMap, setColMap] = useState({
    patient_id: 'patient_id',
    hour: 'hour',
    hr: 'hr',
    sbp: 'sbp',
    dbp: 'dbp',
    map: 'map',
    resp: 'resp',
    temp: 'temp',
    spo2: 'spo2',
    lactate: 'lactate',
    wbc: 'wbc',
    creatinine: 'creatinine',
    bilirubin: 'bilirubin',
    sepsis_label: 'sepsis_label'
  });
  const [isUploading, setIsUploading] = useState(false);

  // Preview modal state
  const [previewDataset, setPreviewDataset] = useState<any | null>(null);
  const [previewModalOpen, setPreviewModalOpen] = useState(false);

  const fetchAllData = async () => {
    try {
      setLoading(true);
      const ds = await api.getDatasets();
      setDatasets(ds);
      const qr = await api.getDataQualityReport();
      setQualityReport(qr);
      const mn = await api.getMimicNote();
      setMimicNote(mn.note);
    } catch (err: any) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAllData();
  }, []);

  const handleGenerateCohort = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsGenerating(true);
    setMsg(null);
    try {
      const res = await api.generateCohort({
        name: genName,
        num_patients: genCount,
        sepsis_prevalence: genPrev / 100.0,
        seed: genSeed,
        set_active: genActive
      });
      setMsg({ text: `Cohort "${res.name}" with ${res.patient_count} patients generated successfully!`, type: 'success' });
      fetchAllData();
      onRefresh();
    } catch (err: any) {
      setMsg({ text: err.message || 'Failed to generate cohort', type: 'error' });
    } finally {
      setIsGenerating(false);
    }
  };

  const handlePsvUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!psvFiles || psvFiles.length === 0) return;
    setIsUploading(true);
    setMsg(null);

    const formData = new FormData();
    for (let i = 0; i < psvFiles.length; i++) {
      formData.append('files', psvFiles[i]);
    }
    formData.append('dataset_name', csvDatasetName);

    try {
      const res = await fetch('http://127.0.0.1:8000/api/data/upload-psv', {
        method: 'POST',
        body: formData
      });
      if (!res.ok) throw new Error((await res.json()).detail || 'Upload failed');
      const data = await res.json();
      setMsg({ text: `Uploaded and ingested ${data.patient_count} patient trajectories in PhysioNet format!`, type: 'success' });
      fetchAllData();
      onRefresh();
    } catch (err: any) {
      setMsg({ text: err.message, type: 'error' });
    } finally {
      setIsUploading(false);
    }
  };

  const handleCsvUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!csvFile) return;
    setIsUploading(true);
    setMsg(null);

    const formData = new FormData();
    formData.append('file', csvFile);
    formData.append('column_mapping_json', JSON.stringify(colMap));
    formData.append('dataset_name', csvDatasetName);

    try {
      const res = await fetch('http://127.0.0.1:8000/api/data/upload-csv', {
        method: 'POST',
        body: formData
      });
      if (!res.ok) throw new Error((await res.json()).detail || 'CSV upload failed');
      const data = await res.json();
      setMsg({ text: `Successfully mapped and loaded ${data.summary.total_parsed} patients from CSV!`, type: 'success' });
      fetchAllData();
      onRefresh();
    } catch (err: any) {
      setMsg({ text: err.message, type: 'error' });
    } finally {
      setIsUploading(false);
    }
  };

  const handleActivateDataset = async (id: number) => {
    try {
      await api.activateDataset(id);
      fetchAllData();
      onRefresh();
    } catch (err: any) {
      alert('Error activating dataset: ' + err.message);
    }
  };

  const handleDeleteDataset = async (id: number) => {
    if (!confirm('Are you sure you want to delete this dataset?')) return;
    try {
      await api.deleteDataset(id);
      fetchAllData();
      onRefresh();
    } catch (err: any) {
      alert(err.message);
    }
  };

  const handlePreviewDataset = async (id: number) => {
    try {
      const res = await api.previewDataset(id);
      setPreviewDataset(res);
      setPreviewModalOpen(true);
    } catch (err: any) {
      alert(err.message);
    }
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
          <Database className="h-6 w-6 text-teal-400" />
          ICU Data Manager & Cohort Ingestion
        </h1>
        <p className="text-xs text-slate-400 mt-1">
          Synthetic ICU cohort generation, PhysioNet 2019 PSV ingestion, and time-series quality reporting.
        </p>
      </div>

      {/* Prominent MIMIC Credentialing Notice */}
      <div className="p-4 rounded-xl bg-slate-900 border border-amber-500/30 flex items-start gap-3">
        <Info className="h-5 w-5 text-amber-400 shrink-0 mt-0.5" />
        <div className="text-xs text-slate-300 leading-relaxed">
          <strong className="text-amber-300">PhysioNet & MIMIC Compliance Notice: </strong>
          {mimicNote || 'MIMIC-III, MIMIC-IV, and PhysioNet Challenge 2019 datasets are protected health research assets requiring credentialing and signed Data Use Agreements. They cannot be redistributed publicly.'}
        </div>
      </div>

      {msg && (
        <div
          className={`p-3 rounded-lg text-xs flex items-center gap-2 border ${
            msg.type === 'success'
              ? 'bg-emerald-950/60 border-emerald-500/40 text-emerald-200'
              : 'bg-rose-950/60 border-rose-500/40 text-rose-200'
          }`}
        >
          {msg.type === 'success' ? <CheckCircle2 className="h-4 w-4" /> : <AlertTriangle className="h-4 w-4" />}
          <span>{msg.text}</span>
        </div>
      )}

      {/* 2 Forms Row: Synthetic Generator & File Upload */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Synthetic Generator Card */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
          <div className="flex items-center gap-2 text-white font-semibold text-sm">
            <PlusCircle className="h-4 w-4 text-teal-400" />
            <span>Built-in Synthetic Cohort Generator</span>
          </div>
          <p className="text-xs text-slate-400">
            Generates realistic adult ICU patients with hourly irregular vitals, sparse labs, per-patient baseline drift, and Sepsis-3 labels.
          </p>

          <form onSubmit={handleGenerateCohort} className="space-y-4 text-xs">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-slate-400 mb-1">Cohort Name</label>
                <input
                  type="text"
                  id="input-gen-name"
                  value={genName}
                  onChange={(e) => setGenName(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-slate-200 focus:outline-none focus:border-teal-500"
                />
              </div>

              <div>
                <label className="block text-slate-400 mb-1">Number of Patients (N)</label>
                <input
                  type="number"
                  id="input-gen-count"
                  min={20}
                  max={5000}
                  value={genCount}
                  onChange={(e) => setGenCount(Number(e.target.value))}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-slate-200 font-mono focus:outline-none focus:border-teal-500"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-slate-400 mb-1">Sepsis Prevalence ({genPrev}%)</label>
                <input
                  type="range"
                  id="slider-gen-prev"
                  min={5}
                  max={30}
                  value={genPrev}
                  onChange={(e) => setGenPrev(Number(e.target.value))}
                  className="w-full accent-teal-500"
                />
              </div>

              <div>
                <label className="block text-slate-400 mb-1">Random Seed</label>
                <input
                  type="number"
                  id="input-gen-seed"
                  value={genSeed}
                  onChange={(e) => setGenSeed(Number(e.target.value))}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-slate-200 font-mono focus:outline-none focus:border-teal-500"
                />
              </div>
            </div>

            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="checkbox-gen-active"
                checked={genActive}
                onChange={(e) => setGenActive(e.target.checked)}
                className="rounded border-slate-700 text-teal-600 focus:ring-0 bg-slate-950"
              />
              <label htmlFor="checkbox-gen-active" className="text-slate-300">
                Set as Active Cohort for Monitoring & Training
              </label>
            </div>

            <button
              type="submit"
              id="btn-generate-cohort"
              disabled={isGenerating}
              className="w-full py-2.5 rounded-lg bg-teal-600 hover:bg-teal-500 disabled:opacity-50 text-white font-semibold flex items-center justify-center gap-2 transition-colors"
            >
              {isGenerating ? <Activity className="h-4 w-4 animate-spin" /> : <PlusCircle className="h-4 w-4" />}
              <span>{isGenerating ? 'Synthesizing Cohort Trajectories...' : 'Generate Synthetic Cohort'}</span>
            </button>
          </form>
        </div>

        {/* Data Importer Card */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-white font-semibold text-sm">
              <UploadCloud className="h-4 w-4 text-cyan-400" />
              <span>Real-World Data Importer</span>
            </div>

            <div className="flex bg-slate-950 p-0.5 rounded-lg border border-slate-800 text-[11px]">
              <button
                type="button"
                onClick={() => setUploadMode('psv')}
                className={`px-2.5 py-1 rounded-md font-medium ${
                  uploadMode === 'psv' ? 'bg-teal-600 text-white' : 'text-slate-400 hover:text-white'
                }`}
              >
                PhysioNet .psv / .zip
              </button>
              <button
                type="button"
                onClick={() => setUploadMode('csv')}
                className={`px-2.5 py-1 rounded-md font-medium ${
                  uploadMode === 'csv' ? 'bg-teal-600 text-white' : 'text-slate-400 hover:text-white'
                }`}
              >
                Generic CSV Mapping
              </button>
            </div>
          </div>

          {uploadMode === 'psv' ? (
            <form onSubmit={handlePsvUpload} className="space-y-4 text-xs">
              <div>
                <label className="block text-slate-400 mb-1">Dataset Name</label>
                <input
                  type="text"
                  value={csvDatasetName}
                  onChange={(e) => setCsvDatasetName(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-slate-200 focus:outline-none focus:border-teal-500"
                />
              </div>

              <div>
                <label className="block text-slate-400 mb-1">Select .psv files or .zip archive</label>
                <input
                  type="file"
                  id="input-file-psv"
                  multiple
                  accept=".psv,.txt,.zip"
                  onChange={(e) => setPsvFiles(e.target.files)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-slate-400 file:mr-3 file:py-1 file:px-3 file:rounded-md file:border-0 file:text-xs file:font-semibold file:bg-teal-600 file:text-white hover:file:bg-teal-500"
                />
              </div>

              <button
                type="submit"
                id="btn-upload-psv"
                disabled={isUploading || !psvFiles}
                className="w-full py-2.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-white font-semibold flex items-center justify-center gap-2 transition-colors"
              >
                {isUploading ? <Activity className="h-4 w-4 animate-spin" /> : <UploadCloud className="h-4 w-4" />}
                <span>{isUploading ? 'Parsing & Ingesting PSV Files...' : 'Ingest PhysioNet Files'}</span>
              </button>
            </form>
          ) : (
            <form onSubmit={handleCsvUpload} className="space-y-4 text-xs">
              <div>
                <label className="block text-slate-400 mb-1">Dataset Name</label>
                <input
                  type="text"
                  value={csvDatasetName}
                  onChange={(e) => setCsvDatasetName(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-slate-200 focus:outline-none focus:border-teal-500"
                />
              </div>

              <div>
                <label className="block text-slate-400 mb-1">Upload CSV File</label>
                <input
                  type="file"
                  accept=".csv"
                  onChange={(e) => setCsvFile(e.target.files ? e.target.files[0] : null)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-slate-400 file:mr-3 file:py-1 file:px-3 file:rounded-md file:border-0 file:text-xs file:font-semibold file:bg-cyan-600 file:text-white hover:file:bg-cyan-500"
                />
              </div>

              <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-800 space-y-2">
                <span className="text-[11px] font-semibold text-slate-300">Column Mapping:</span>
                <div className="grid grid-cols-2 gap-2 text-[10px] font-mono">
                  <div>
                    <span className="text-slate-500">Patient ID: </span>
                    <input
                      type="text"
                      value={colMap.patient_id}
                      onChange={(e) => setColMap({ ...colMap, patient_id: e.target.value })}
                      className="bg-slate-900 border border-slate-800 rounded px-1.5 py-0.5 w-full text-slate-200"
                    />
                  </div>
                  <div>
                    <span className="text-slate-500">Hour / Time: </span>
                    <input
                      type="text"
                      value={colMap.hour}
                      onChange={(e) => setColMap({ ...colMap, hour: e.target.value })}
                      className="bg-slate-900 border border-slate-800 rounded px-1.5 py-0.5 w-full text-slate-200"
                    />
                  </div>
                  <div>
                    <span className="text-slate-500">HR: </span>
                    <input
                      type="text"
                      value={colMap.hr}
                      onChange={(e) => setColMap({ ...colMap, hr: e.target.value })}
                      className="bg-slate-900 border border-slate-800 rounded px-1.5 py-0.5 w-full text-slate-200"
                    />
                  </div>
                  <div>
                    <span className="text-slate-500">Sepsis Label: </span>
                    <input
                      type="text"
                      value={colMap.sepsis_label}
                      onChange={(e) => setColMap({ ...colMap, sepsis_label: e.target.value })}
                      className="bg-slate-900 border border-slate-800 rounded px-1.5 py-0.5 w-full text-slate-200"
                    />
                  </div>
                </div>
              </div>

              <button
                type="submit"
                id="btn-upload-csv"
                disabled={isUploading || !csvFile}
                className="w-full py-2.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-white font-semibold flex items-center justify-center gap-2 transition-colors"
              >
                {isUploading ? <Activity className="h-4 w-4 animate-spin" /> : <UploadCloud className="h-4 w-4" />}
                <span>{isUploading ? 'Ingesting CSV Records...' : 'Map & Ingest CSV Cohort'}</span>
              </button>
            </form>
          )}
        </div>
      </div>

      {/* Datasets Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-sm">
        <div className="p-4 border-b border-slate-800 flex items-center justify-between">
          <h3 className="text-xs font-bold text-white uppercase tracking-wider font-mono flex items-center gap-2">
            <Layers className="h-4 w-4 text-teal-400" />
            Registered Cohort Datasets
          </h3>
          <span className="text-xs text-slate-400 font-mono">{datasets.length} Cohorts Ingested</span>
        </div>

        <table className="w-full text-left text-xs">
          <thead className="bg-slate-950/80 text-slate-400 uppercase font-mono text-[10px] border-b border-slate-800">
            <tr>
              <th className="p-3">Cohort Name</th>
              <th className="p-3">Source</th>
              <th className="p-3">Patients</th>
              <th className="p-3">Septic Cases</th>
              <th className="p-3">Total Hours</th>
              <th className="p-3">Created</th>
              <th className="p-3">Status</th>
              <th className="p-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60 font-mono">
            {datasets.map((d) => (
              <tr key={d.id} className="hover:bg-slate-800/40 transition-colors">
                <td className="p-3 font-sans font-semibold text-white">{d.name}</td>
                <td className="p-3 text-slate-400">{d.source_type}</td>
                <td className="p-3 text-teal-300 font-bold">{d.patient_count}</td>
                <td className="p-3 text-rose-400 font-bold">
                  {d.septic_count} ({((d.septic_count / Math.max(1, d.patient_count)) * 100).toFixed(1)}%)
                </td>
                <td className="p-3 text-slate-300">{d.total_hours}h</td>
                <td className="p-3 text-slate-400 font-sans text-[11px]">{d.created_at}</td>
                <td className="p-3 font-sans">
                  {d.is_active ? (
                    <span className="px-2 py-0.5 rounded text-[10px] bg-teal-950 text-teal-300 border border-teal-500/40 font-bold">
                      ACTIVE COHORT
                    </span>
                  ) : (
                    <span className="text-slate-500 text-[10px]">Inactive</span>
                  )}
                </td>
                <td className="p-3 text-right">
                  <div className="flex items-center justify-end gap-2 font-sans">
                    <button
                      onClick={() => handlePreviewDataset(d.id)}
                      className="p-1 rounded text-slate-400 hover:text-cyan-400 hover:bg-slate-800"
                      title="Preview Patient Rows"
                    >
                      <Eye className="h-4 w-4" />
                    </button>
                    {!d.is_active && (
                      <button
                        onClick={() => handleActivateDataset(d.id)}
                        className="px-2 py-1 rounded bg-teal-600/30 text-teal-300 hover:bg-teal-600 hover:text-white text-[11px]"
                      >
                        Set Active
                      </button>
                    )}
                    <button
                      onClick={() => handleDeleteDataset(d.id)}
                      className="p-1 rounded text-slate-500 hover:text-rose-400 hover:bg-slate-800"
                      title="Delete Dataset"
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

      {/* Time-Series Quality Report: Missingness Heatmap */}
      {qualityReport && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold text-white uppercase tracking-wider font-mono flex items-center gap-2">
              <FileSpreadsheet className="h-4 w-4 text-teal-400" />
              ICU Data Quality & Missingness Profile ({qualityReport.dataset_name})
            </h3>
            <span className="text-[11px] font-mono text-slate-400">
              Total Monitored Hours: {qualityReport.total_patient_hours}h
            </span>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
            {qualityReport.missingness?.map((m: any, i: number) => {
              const isHighMissing = m.missingness_pct >= 60;
              return (
                <div key={i} className="p-3 rounded-lg bg-slate-950 border border-slate-800 space-y-1">
                  <div className="flex items-center justify-between text-xs font-mono">
                    <span className="font-bold text-slate-200">{m.feature}</span>
                    <span className={`font-bold ${isHighMissing ? 'text-amber-400' : 'text-teal-400'}`}>
                      {m.missingness_pct}%
                    </span>
                  </div>
                  <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
                    <div
                      className={`h-full ${isHighMissing ? 'bg-amber-500' : 'bg-teal-500'}`}
                      style={{ width: `${100 - m.missingness_pct}%` }}
                    />
                  </div>
                  <div className="text-[9px] text-slate-500 font-mono pt-1">
                    Draw interval: ~{m.avg_sampling_interval_hours}h
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Preview Modal */}
      {previewModalOpen && previewDataset && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 max-w-3xl w-full shadow-2xl space-y-4 max-h-[85vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <Eye className="h-5 w-5 text-teal-400" />
                Dataset Rows Preview ({previewDataset.dataset})
              </h3>
              <button onClick={() => setPreviewModalOpen(false)} className="text-slate-400 hover:text-white">
                ✕
              </button>
            </div>

            <div className="space-y-4">
              {previewDataset.preview?.map((pt: any, i: number) => (
                <div key={i} className="p-3 rounded-lg bg-slate-950 border border-slate-800 text-xs space-y-2">
                  <div className="flex items-center justify-between font-mono">
                    <span className="font-bold text-teal-300">{pt.bed} ({pt.patient_id})</span>
                    <span className="text-slate-400">{pt.age}y {pt.gender} • Sepsis: {pt.is_septic ? `Yes (Hour ${pt.onset_hour})` : 'No'}</span>
                  </div>
                  <div className="overflow-x-auto">
                    <table className="w-full text-[10px] font-mono text-left text-slate-300">
                      <thead className="text-slate-500 border-b border-slate-800">
                        <tr>
                          <th className="p-1">Hour</th>
                          <th className="p-1">HR</th>
                          <th className="p-1">MAP</th>
                          <th className="p-1">Resp</th>
                          <th className="p-1">Temp</th>
                          <th className="p-1">Lactate</th>
                          <th className="p-1">WBC</th>
                          <th className="p-1">SOFA</th>
                        </tr>
                      </thead>
                      <tbody>
                        {pt.vitals_sample?.map((v: any, vi: number) => (
                          <tr key={vi} className="border-b border-slate-900">
                            <td className="p-1">{v.hour}h</td>
                            <td className="p-1">{v.hr ?? '--'}</td>
                            <td className="p-1">{v.map ?? '--'}</td>
                            <td className="p-1">{v.resp ?? '--'}</td>
                            <td className="p-1">{v.temp ?? '--'}</td>
                            <td className="p-1">{v.lactate ?? '--'}</td>
                            <td className="p-1">{v.wbc ?? '--'}</td>
                            <td className="p-1 text-teal-400">{v.sofa}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              ))}
            </div>

            <div className="flex justify-end">
              <button
                onClick={() => setPreviewModalOpen(false)}
                className="px-4 py-2 rounded-lg bg-slate-800 text-white text-xs hover:bg-slate-700"
              >
                Close Preview
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
