import React, { useState, useEffect } from 'react';
import {
  Settings,
  ShieldAlert,
  RotateCcw,
  CheckCircle2,
  AlertTriangle,
  Info,
  Sliders,
  Scale,
  BookOpen
} from 'lucide-react';
import { api } from '../api/client';

export const SettingsPage: React.FC<{ onRefresh: () => void }> = ({ onRefresh }) => {
  const [settings, setSettings] = useState<any>({
    cooldown_hours: 4.0,
    consecutive_hours: 1,
    escalation_delta: 0.15,
    simulation_speed: 5.0,
    temperature_unit: 'C',
    blood_pressure_unit: 'mmHg'
  });
  const [aboutDoc, setAboutDoc] = useState<any>(null);
  const [saveMsg, setSaveMsg] = useState<string | null>(null);
  const [resetModalOpen, setResetModalOpen] = useState(false);
  const [isResetting, setIsResetting] = useState(false);

  useEffect(() => {
    api.getSettings().then(setSettings).catch(console.error);
    api.getAbout().then(setAboutDoc).catch(console.error);
  }, []);

  const handleSaveSettings = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.updateSettings(settings);
      setSaveMsg('System settings successfully saved and applied to active surveillance pipeline.');
      onRefresh();
      setTimeout(() => setSaveMsg(null), 3000);
    } catch (err: any) {
      alert('Error saving settings: ' + err.message);
    }
  };

  const handleResetApplication = async () => {
    setIsResetting(true);
    try {
      await api.resetApp();
      setResetModalOpen(false);
      setSaveMsg('Application database successfully wiped, re-seeded with demo cohort, and baseline model trained.');
      onRefresh();
      setTimeout(() => setSaveMsg(null), 4000);
    } catch (err: any) {
      alert('Reset error: ' + err.message);
    } finally {
      setIsResetting(false);
    }
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
          <Settings className="h-6 w-6 text-teal-400" />
          Settings & Clinical Methodology
        </h1>
        <p className="text-xs text-slate-400 mt-1">
          Global alert suppression rules, clinical unit standards, Sepsis-3 label definition, and application reset.
        </p>
      </div>

      {saveMsg && (
        <div className="p-3 rounded-lg bg-emerald-950/60 border border-emerald-500/40 text-emerald-200 text-xs flex items-center gap-2">
          <CheckCircle2 className="h-4 w-4" />
          <span>{saveMsg}</span>
        </div>
      )}

      {/* Grid: Settings Form & About/Methodology */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Settings Controls: 5 cols */}
        <div className="lg:col-span-5 space-y-6">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
            <h3 className="text-xs font-bold text-white uppercase tracking-wider font-mono flex items-center gap-2">
              <Sliders className="h-4 w-4 text-teal-400" />
              Surveillance & Suppression Rules
            </h3>

            <form onSubmit={handleSaveSettings} className="space-y-4 text-xs">
              <div>
                <label className="block text-slate-400 mb-1">
                  Default Alert Cooldown Window ({settings.cooldown_hours} Hours)
                </label>
                <select
                  value={settings.cooldown_hours}
                  onChange={(e) => setSettings({ ...settings, cooldown_hours: Number(e.target.value) })}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-slate-200 font-mono focus:outline-none focus:border-teal-500"
                >
                  <option value={2.0}>2.0 Hours</option>
                  <option value={4.0}>4.0 Hours (Standard Clinical Practice)</option>
                  <option value={6.0}>6.0 Hours</option>
                  <option value={8.0}>8.0 Hours</option>
                </select>
                <p className="text-[10px] text-slate-500 mt-1">
                  Prevents re-alerting for the same patient unless risk score escalates significantly.
                </p>
              </div>

              <div>
                <label className="block text-slate-400 mb-1">
                  Alert Escalation Risk Delta (+{(settings.escalation_delta * 100).toFixed(0)}%)
                </label>
                <select
                  value={settings.escalation_delta}
                  onChange={(e) => setSettings({ ...settings, escalation_delta: Number(e.target.value) })}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-slate-200 font-mono focus:outline-none focus:border-teal-500"
                >
                  <option value={0.10}>+10% Risk Rise</option>
                  <option value={0.15}>+15% Risk Rise (Standard)</option>
                  <option value={0.20}>+20% Risk Rise</option>
                </select>
              </div>

              <div>
                <label className="block text-slate-400 mb-1">Persistence Rule</label>
                <select
                  value={settings.consecutive_hours}
                  onChange={(e) => setSettings({ ...settings, consecutive_hours: Number(e.target.value) })}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-slate-200 font-mono focus:outline-none focus:border-teal-500"
                >
                  <option value={1}>1 Hour (Instant Trigger)</option>
                  <option value={2}>2 Consecutive Hours (Suppresses Spurious Spikes)</option>
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3 pt-1">
                <div>
                  <label className="block text-slate-400 mb-1">Temperature Unit</label>
                  <select
                    value={settings.temperature_unit}
                    onChange={(e) => setSettings({ ...settings, temperature_unit: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-slate-200 focus:outline-none focus:border-teal-500"
                  >
                    <option value="C">Celsius (°C)</option>
                    <option value="F">Fahrenheit (°F)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-slate-400 mb-1">Pressure Unit</label>
                  <select
                    value={settings.blood_pressure_unit}
                    onChange={(e) => setSettings({ ...settings, blood_pressure_unit: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-slate-200 focus:outline-none focus:border-teal-500"
                  >
                    <option value="mmHg">mmHg</option>
                    <option value="kPa">kPa</option>
                  </select>
                </div>
              </div>

              <button
                type="submit"
                id="btn-save-settings"
                className="w-full py-2.5 rounded-lg bg-teal-600 hover:bg-teal-500 text-white font-semibold text-xs shadow-md transition-colors"
              >
                Save Global Settings
              </button>
            </form>
          </div>

          {/* Reset Application Card */}
          <div className="bg-slate-900 border border-rose-500/30 rounded-xl p-5 shadow-sm space-y-3">
            <h3 className="text-xs font-bold text-rose-400 uppercase tracking-wider font-mono flex items-center gap-2">
              <RotateCcw className="h-4 w-4 text-rose-400" />
              Reset Application & Database
            </h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Wipes all ingested cohorts, trained models, alerts, and audit notes. Re-initializes a clean synthetic ICU cohort and trains a fresh baseline model.
            </p>
            <button
              type="button"
              id="btn-reset-app-modal"
              onClick={() => setResetModalOpen(true)}
              className="w-full py-2 rounded-lg bg-rose-600/20 hover:bg-rose-600 text-rose-300 hover:text-white border border-rose-500/30 font-semibold text-xs transition-colors"
            >
              Reset Entire Application...
            </button>
          </div>
        </div>

        {/* Right About & Methodology Documentation: 7 cols */}
        <div className="lg:col-span-7 bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-sm space-y-5 text-xs text-slate-300 leading-relaxed">
          <div className="flex items-center gap-2 text-white font-semibold text-sm border-b border-slate-800 pb-3">
            <BookOpen className="h-4 w-4 text-teal-400" />
            <span>Clinical Methodology & Research Foundations</span>
          </div>

          <div className="space-y-2">
            <h4 className="font-bold text-slate-100 font-mono text-xs uppercase tracking-wider">
              1. Sepsis-3 Label Operationalization
            </h4>
            <p className="text-slate-400">
              {aboutDoc?.sepsis_3_definition || 'Sepsis is defined under Sepsis-3 as life-threatening organ dysfunction caused by a dysregulated host response to infection, operationalized as an acute SOFA increase >= 2 points.'}
            </p>
          </div>

          <div className="space-y-2">
            <h4 className="font-bold text-slate-100 font-mono text-xs uppercase tracking-wider">
              2. 6-Hour Early Warning Horizon
            </h4>
            <p className="text-slate-400">
              {aboutDoc?.prediction_horizon || 'The target variable is defined as sepsis onset occurring within the forward window (t, t + 6h]. Features at time t strictly use observations at or prior to t.'}
            </p>
          </div>

          <div className="space-y-2">
            <h4 className="font-bold text-slate-100 font-mono text-xs uppercase tracking-wider">
              3. Alarm Fatigue as a First-Class Metric
            </h4>
            <p className="text-slate-400">
              {aboutDoc?.alarm_fatigue_philosophy || 'Unlike static binary classification models, clinical monitors are alerting systems. Unconstrained alerting leads to clinical alarm fatigue, desensitization, and patient harm.'}
            </p>
          </div>

          <div className="space-y-2">
            <h4 className="font-bold text-slate-100 font-mono text-xs uppercase tracking-wider">
              4. Scope & Intended Use Limitations
            </h4>
            <ul className="list-disc pl-5 space-y-1 text-slate-400">
              {aboutDoc?.scope_limitations?.map((item: string, i: number) => (
                <li key={i}>{item}</li>
              ))}
            </ul>
          </div>
        </div>
      </div>

      {/* Confirmation Modal for Reset */}
      {resetModalOpen && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 max-w-md w-full shadow-2xl space-y-4">
            <div className="flex items-center gap-3 text-rose-400">
              <AlertTriangle className="h-6 w-6" />
              <h3 className="text-base font-bold text-white">Confirm Full System Reset</h3>
            </div>
            <p className="text-xs text-slate-300 leading-relaxed">
              This will completely drop all database tables, wipe all patient records, alerts, and trained models, and re-generate a clean benchmark cohort. This action cannot be undone.
            </p>
            <div className="flex justify-end gap-2 pt-2 text-xs">
              <button
                type="button"
                onClick={() => setResetModalOpen(false)}
                className="px-4 py-2 rounded-lg bg-slate-800 text-slate-300 hover:bg-slate-700"
              >
                Cancel
              </button>
              <button
                type="button"
                id="btn-confirm-reset"
                disabled={isResetting}
                onClick={handleResetApplication}
                className="px-4 py-2 rounded-lg bg-rose-600 hover:bg-rose-500 text-white font-semibold flex items-center gap-1.5"
              >
                {isResetting ? 'Resetting...' : 'Yes, Reset Application'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
