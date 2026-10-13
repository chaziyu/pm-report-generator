const API_BASE = 'http://localhost:8000/api';

export const createSession = async () => {
  const response = await fetch(`${API_BASE}/sessions/`, {
    method: 'POST',
  });
  if (!response.ok) throw new Error('Failed to create session');
  return response.json();
};

export const getSession = async (sessionId: string) => {
  const response = await fetch(`${API_BASE}/sessions/${sessionId}`);
  if (!response.ok) throw new Error('Failed to fetch session');
  return response.json();
};

export const uploadScreenshot = async (sessionId: string, file: File) => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${API_BASE}/sessions/${sessionId}/screenshots`, {
    method: 'POST',
    body: formData,
  });
  if (!response.ok) throw new Error('Failed to upload screenshot');
  return response.json();
};

export const runAnalysis = async (sessionId: string) => {
  const response = await fetch(`${API_BASE}/sessions/${sessionId}/analyze`, {
    method: 'POST',
  });
  if (!response.ok) throw new Error('Analysis failed');
  return response.json();
};

export const updateField = async (sessionId: string, fieldPath: string, value: any) => {
  const response = await fetch(`${API_BASE}/sessions/${sessionId}/fields`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ field_path: fieldPath, value }),
  });
  if (!response.ok) throw new Error('Failed to update field');
  return response.json();
};

export const updateScreenshotCategory = async (sessionId: string, screenshotId: string, assignedCategory: string) => {
  const response = await fetch(`${API_BASE}/sessions/${sessionId}/screenshots/${screenshotId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ assigned_category: assignedCategory }),
  });
  if (!response.ok) throw new Error('Failed to update screenshot category');
  return response.json();
};

export const updateAppendix = async (sessionId: string, appendixNum: number, data: any) => {
  const response = await fetch(`${API_BASE}/sessions/${sessionId}/appendices/${appendixNum}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!response.ok) throw new Error('Failed to update appendix');
  return response.json();
};

export const validateSession = async (sessionId: string) => {
  const response = await fetch(`${API_BASE}/sessions/${sessionId}/validate`, {
    method: 'POST',
  });
  if (!response.ok) throw new Error('Validation failed');
  return response.json();
};

export const generateReport = async (sessionId: string) => {
  const response = await fetch(`${API_BASE}/sessions/${sessionId}/reports`, {
    method: 'POST',
  });
  if (!response.ok) {
    const err = await response.json();
    throw new Error(err.detail || 'Failed to generate report');
  }
  return response.json();
};

export const getDownloadUrl = (sessionId: string) => `${API_BASE}/sessions/${sessionId}/reports/download`;

export const getAiStatus = async () => {
  const response = await fetch(`${API_BASE}/ai/status`);
  if (!response.ok) throw new Error('Failed to fetch AI status');
  return response.json();
};

export const startAiDownload = async () => {
  const response = await fetch(`${API_BASE}/ai/download`, { method: 'POST' });
  if (!response.ok) throw new Error('Failed to trigger AI download');
  return response.json();
};

export const cancelAiDownload = async () => {
  const response = await fetch(`${API_BASE}/ai/cancel-download`, { method: 'POST' });
  if (!response.ok) throw new Error('Failed to cancel AI download');
  return response.json();
};

export const startAiSetup = async () => {
  const response = await fetch(`${API_BASE}/ai/setup`, { method: 'POST' });
  if (!response.ok) throw new Error('Failed to initiate Local AI setup');
  return response.json();
};

export const startRuntimeInstall = async () => {
  const response = await fetch(`${API_BASE}/ai/runtime/install`, { method: 'POST' });
  if (!response.ok) throw new Error('Failed to start runtime installation');
  return response.json();
};

export const cancelRuntimeInstall = async () => {
  const response = await fetch(`${API_BASE}/ai/runtime/cancel-install`, { method: 'POST' });
  if (!response.ok) throw new Error('Failed to cancel runtime installation');
  return response.json();
};


