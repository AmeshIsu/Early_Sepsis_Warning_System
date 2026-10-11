const API_BASE = "http://127.0.0.1:8000";

export async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${url}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options?.headers || {})
    }
  });
  if (!res.ok) {
    let errorMsg = `HTTP Error ${res.status}: ${res.statusText}`;
    try {
      const errObj = await res.json();
      if (errObj.detail) errorMsg = errObj.detail;
    } catch {}
    throw new Error(errorMsg);
  }
  return res.json();
}

// Patients API
export const api = {
  getPatients: (params?: { risk_level?: string; unit?: string; alert_status?: string; search?: string; page?: number }) => {
    const sp = new URLSearchParams();
    if (params?.risk_level) sp.append("risk_level", params.risk_level);
    if (params?.unit) sp.append("unit", params.unit);
    if (params?.alert_status) sp.append("alert_status", params.alert_status);
    if (params?.search) sp.append("search", params.search);
    if (params?.page) sp.append("page", params.page.toString());
    return fetchJson<{ items: any[]; total: number; page: number; page_size: number }>(`/api/patients?${sp.toString()}`);
  },

  getPatientDetails: (id: number | string) => fetchJson<any>(`/api/patients/${id}`),
  getPatientExplainability: (id: number | string) => fetchJson<any>(`/api/patients/${id}/explain`),
  postPatientAction: (id: number | string, data: { action: string; snooze_hours?: number; note_content?: string; author?: string }) =>
    fetchJson<any>(`/api/patients/${id}/actions`, { method: "POST", body: JSON.stringify(data) }),

  // Alerts API
  getAlerts: (params?: { status?: string; unit?: string; search?: string; page?: number; page_size?: number }) => {
    const sp = new URLSearchParams();
    if (params?.status) sp.append("status", params.status);
    if (params?.unit) sp.append("unit", params.unit);
    if (params?.search) sp.append("search", params.search);
    if (params?.page) sp.append("page", params.page.toString());
    if (params?.page_size) sp.append("page_size", params.page_size.toString());
    return fetchJson<{ items: any[]; total: number; page: number; page_size: number }>(`/api/alerts?${sp.toString()}`);
  },
  postAlertAction: (id: number, data: { action: string; snooze_hours?: number; note?: string }) =>
    fetchJson<any>(`/api/alerts/${id}/action`, { method: "POST", body: JSON.stringify(data) }),
  postBulkAlertAction: (data: { alert_ids: number[]; action: string; snooze_hours?: number; note?: string }) =>
    fetchJson<any>(`/api/alerts/bulk-action`, { method: "POST", body: JSON.stringify(data) }),

  // Data API
  getDatasets: () => fetchJson<any[]>(`/api/data/datasets`),
  activateDataset: (id: number) => fetchJson<any>(`/api/data/datasets/${id}/activate`, { method: "POST" }),
  deleteDataset: (id: number) => fetchJson<any>(`/api/data/datasets/${id}`, { method: "DELETE" }),
  previewDataset: (id: number) => fetchJson<any>(`/api/data/datasets/${id}/preview`),
  generateCohort: (data: { name: string; num_patients: number; sepsis_prevalence: number; seed: number; set_active: boolean }) =>
    fetchJson<any>(`/api/data/generate`, { method: "POST", body: JSON.stringify(data) }),
  getDataQualityReport: () => fetchJson<any>(`/api/data/quality-report`),
  getMimicNote: () => fetchJson<{ note: string }>(`/api/data/mimic-note`),

  // Models API
  getModels: () => fetchJson<any[]>(`/api/models`),
  getActiveModel: () => fetchJson<any>(`/api/models/active`),
  activateModel: (id: number) => fetchJson<any>(`/api/models/${id}/activate`, { method: "POST" }),
  deleteModel: (id: number) => fetchJson<any>(`/api/models/${id}`, { method: "DELETE" }),
  trainModel: (data: any) => fetchJson<any>(`/api/models/train`, { method: "POST", body: JSON.stringify(data) }),
  stopTraining: () => fetchJson<any>(`/api/models/train/stop`, { method: "POST" }),
  getTrainingStatus: () => fetchJson<any>(`/api/models/train/status`),

  // Calibration API
  getCalibration: () => fetchJson<any>(`/api/calibration/current`),
  optimizeThreshold: (data: any) => fetchJson<any>(`/api/calibration/optimize`, { method: "POST", body: JSON.stringify(data) }),
  applyCalibration: (data: any) => fetchJson<any>(`/api/calibration/apply`, { method: "POST", body: JSON.stringify(data) }),

  // Evaluation API
  getBenchmark: (modelId?: number, datasetId?: number) => {
    const sp = new URLSearchParams();
    if (modelId) sp.append("model_id", modelId.toString());
    if (datasetId) sp.append("dataset_id", datasetId.toString());
    return fetchJson<any>(`/api/evaluation/benchmark?${sp.toString()}`);
  },
  getSubgroups: () => fetchJson<any>(`/api/evaluation/subgroups`),

  // Simulation API
  getSimulationStatus: () => fetchJson<any>(`/api/simulation/status`),
  startSimulation: () => fetchJson<any>(`/api/simulation/start`, { method: "POST" }),
  pauseSimulation: () => fetchJson<any>(`/api/simulation/pause`, { method: "POST" }),
  resetSimulation: () => fetchJson<any>(`/api/simulation/reset`, { method: "POST" }),
  stepSimulation: () => fetchJson<any>(`/api/simulation/step`, { method: "POST" }),
  setSimulationSpeed: (speed: number) => fetchJson<any>(`/api/simulation/speed`, { method: "POST", body: JSON.stringify({ speed }) }),
  getSeedStatus: () => fetchJson<any>(`/api/seed/status`),

  // Settings API
  getSettings: () => fetchJson<any>(`/api/settings`),
  updateSettings: (data: any) => fetchJson<any>(`/api/settings`, { method: "POST", body: JSON.stringify(data) }),
  resetApp: () => fetchJson<any>(`/api/settings/reset`, { method: "POST", body: JSON.stringify({ confirm_reset: true }) }),
  getAbout: () => fetchJson<any>(`/api/settings/about`),
};
