import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { api } from './api/client';
import { Sidebar } from './components/layout/Sidebar';
import { TopBar } from './components/layout/TopBar';
import { DisclaimerBanner, SeedProgressBanner } from './components/layout/DisclaimerBanner';
import { CommandCenter } from './pages/CommandCenter';
import { PatientMonitor } from './pages/PatientMonitor';
import { AlertsCenter } from './pages/AlertsCenter';
import { DataManager } from './pages/DataManager';
import { ModelLab } from './pages/ModelLab';
import { CalibrationThresholds } from './pages/CalibrationThresholds';
import { EvaluationPage } from './pages/EvaluationPage';
import { SettingsPage } from './pages/SettingsPage';

export const App: React.FC = () => {
  const [simState, setSimState] = useState<any>(null);
  const [activeModel, setActiveModel] = useState<any>(null);
  const [seedStatus, setSeedStatus] = useState<any>({ is_seeding: false, progress_pct: 0, message: '', completed: false });

  const refreshGlobalState = async () => {
    try {
      const [st, mod, sd] = await Promise.all([
        api.getSimulationStatus(),
        api.getActiveModel(),
        api.getSeedStatus()
      ]);
      setSimState(st);
      setActiveModel(mod);
      setSeedStatus(sd);
    } catch (err) {
      console.error('Failed to sync global state:', err);
    }
  };

  useEffect(() => {
    refreshGlobalState();

    // Setup WebSocket for streaming replay
    let ws: WebSocket | null = null;
    let fallbackInterval: any = null;

    try {
      ws = new WebSocket('ws://127.0.0.1:8000/ws/simulation');
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          setSimState(data);
        } catch (e) {
          console.error(e);
        }
      };
      ws.onerror = () => {
        // Fallback to polling every 2s
        fallbackInterval = setInterval(refreshGlobalState, 2000);
      };
    } catch (err) {
      fallbackInterval = setInterval(refreshGlobalState, 2000);
    }

    // Refresh model & seed status periodically
    const metaInterval = setInterval(async () => {
      try {
        const [mod, sd] = await Promise.all([
          api.getActiveModel(),
          api.getSeedStatus()
        ]);
        setActiveModel(mod);
        setSeedStatus(sd);
      } catch {}
    }, 4000);

    return () => {
      if (ws) ws.close();
      if (fallbackInterval) clearInterval(fallbackInterval);
      clearInterval(metaInterval);
    };
  }, []);

  return (
    <Router>
      <div className="flex h-screen bg-slate-950 text-slate-100 overflow-hidden font-sans">
        {/* Left Sidebar */}
        <Sidebar />

        {/* Main Content Area */}
        <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
          {/* Clinical Disclaimer Banner */}
          <DisclaimerBanner />

          {/* Auto-seeding Progress Banner */}
          <SeedProgressBanner seedStatus={seedStatus} />

          {/* Top Navigation & Simulation Stream Controls */}
          <TopBar
            simState={simState}
            onRefresh={refreshGlobalState}
            activeModel={activeModel}
          />

          {/* Scrollable Page Outlet */}
          <main className="flex-1 overflow-y-auto bg-slate-950">
            <Routes>
              <Route
                path="/"
                element={
                  <CommandCenter
                    simState={simState}
                    onRefresh={refreshGlobalState}
                    activeModel={activeModel}
                  />
                }
              />
              <Route
                path="/monitor"
                element={
                  <PatientMonitor
                    simState={simState}
                    onRefresh={refreshGlobalState}
                  />
                }
              />
              <Route
                path="/alerts"
                element={
                  <AlertsCenter
                    simState={simState}
                    onRefresh={refreshGlobalState}
                  />
                }
              />
              <Route
                path="/data"
                element={<DataManager onRefresh={refreshGlobalState} />}
              />
              <Route
                path="/models"
                element={
                  <ModelLab
                    activeModel={activeModel}
                    onRefresh={refreshGlobalState}
                  />
                }
              />
              <Route
                path="/calibration"
                element={
                  <CalibrationThresholds
                    activeModel={activeModel}
                    onRefresh={refreshGlobalState}
                  />
                }
              />
              <Route
                path="/evaluation"
                element={
                  <EvaluationPage
                    activeModel={activeModel}
                    onRefresh={refreshGlobalState}
                  />
                }
              />
              <Route
                path="/settings"
                element={<SettingsPage onRefresh={refreshGlobalState} />}
              />
            </Routes>
          </main>
        </div>
      </div>
    </Router>
  );
};

export default App;
