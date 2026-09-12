export interface BackendConfig {
  baseUrl: string;
  apiKey: string;
  useLiveBackend: boolean;
  timeoutMs: number;
}

const STORAGE_KEY = 'drishti_backend_config';

export const getBackendConfig = (): BackendConfig => {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      return JSON.parse(raw);
    }
  } catch {
    // ignore parse error
  }
  return {
    baseUrl: 'http://localhost:8000/api',
    apiKey: '',
    useLiveBackend: true,
    timeoutMs: 30000,
  };
};

export const saveBackendConfig = (config: BackendConfig) => {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(config));
};

export interface BackendHealthResult {
  ok: boolean;
  statusText: string;
  latencyMs: number;
}

export const checkBackendHealth = async (baseUrl: string): Promise<BackendHealthResult> => {
  const start = performance.now();
  const cleanUrl = baseUrl.replace(/\/+$/, '');
  const testEndpoints = [`${cleanUrl}/health`, `${cleanUrl}`, cleanUrl.replace(/\/api$/, '') + '/health'];

  for (const endpoint of testEndpoints) {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 2500);
      const res = await fetch(endpoint, {
        method: 'GET',
        signal: controller.signal,
        headers: { Accept: 'application/json' },
      });
      clearTimeout(timeoutId);
      const latencyMs = Math.round(performance.now() - start);
      if (res.ok || res.status === 404 || res.status === 401) {
        return {
          ok: true,
          statusText: `Connected (${res.status})`,
          latencyMs,
        };
      }
    } catch {
      // try next endpoint
    }
  }

  const latencyMs = Math.round(performance.now() - start);
  return {
    ok: false,
    statusText: 'No server responding at address',
    latencyMs,
  };
};

export interface BackendDataset {
  dataset_id: string;
  dataset_name: string;
  original_filename: string;
  table_name: string;
  file_type: string;
  row_count: number;
  column_count: number;
  quality_report?: any[];
  dataset_status: string;
  created_at: string;
}

export const fetchDatasets = async (config: BackendConfig): Promise<BackendDataset[]> => {
  const cleanUrl = config.baseUrl.replace(/\/+$/, '');
  const endpoint = `${cleanUrl}/datasets`;

  try {
    const res = await fetch(endpoint, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
        ...(config.apiKey ? { Authorization: `Bearer ${config.apiKey}` } : {}),
      },
    });
    if (res.ok) {
      return await res.json();
    }
  } catch (err) {
    console.warn('Failed to fetch datasets:', err);
  }
  return [];
};

export const uploadDataset = async (file: File, config: BackendConfig): Promise<any> => {
  const cleanUrl = config.baseUrl.replace(/\/+$/, '');
  const endpoint = `${cleanUrl}/upload`;

  const formData = new FormData();
  formData.append('file', file);

  const res = await fetch(endpoint, {
    method: 'POST',
    headers: {
      ...(config.apiKey ? { Authorization: `Bearer ${config.apiKey}` } : {}),
    },
    body: formData,
  });

  if (!res.ok) {
    throw new Error(`Upload failed with status ${res.status}`);
  }

  const data = await res.json();
  if (!data.success) {
    throw new Error(data.error || "Upload failed on the backend");
  }
  return data;
};

export interface BackendAnalysisResponse {
  query: string;
  sql?: string;
  results?: unknown[];
  summary?: string;
  stagesCompleted?: string[];
  executionTimeMs?: number;
}

export const dispatchQueryToBackend = async (
  query: string,
  config: BackendConfig,
  datasetId: string = 'default',
  conversationId?: string
): Promise<BackendAnalysisResponse | null> => {
  const cleanUrl = config.baseUrl.replace(/\/+$/, '');
  const endpoint = `${cleanUrl}/analyze`;

  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), config.timeoutMs || 30000);
    const res = await fetch(endpoint, {
      method: 'POST',
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
        ...(config.apiKey ? { Authorization: `Bearer ${config.apiKey}` } : {}),
      },
      body: JSON.stringify({ question: query, dataset_id: datasetId, conversation_id: conversationId }),
    });
    clearTimeout(timeoutId);

    if (res.ok) {
      return await res.json();
    }
  } catch (err) {
    console.warn('Live backend query dispatch failed, falling back to local verification sandbox:', err);
  }

  return null;
};

export interface HistorySummary {
  analysis_id: string;
  conversation_id?: string;
  dataset_id?: string;
  dataset_name: string;
  question: string;
  rows_returned: number;
  attempts: number;
  execution_time_ms: number;
  status: string;
  error_message?: string;
  created_at: string;
}

export interface HistoryListResponse {
  items: HistorySummary[];
  total: number;
}

export const fetchHistory = async (config: BackendConfig, datasetId?: string, status?: string, search?: string, limit = 20, offset = 0): Promise<HistoryListResponse | null> => {
  const cleanUrl = config.baseUrl.replace(/\/+$/, '');
  const params = new URLSearchParams({ limit: limit.toString(), offset: offset.toString() });
  if (datasetId) params.append('dataset_id', datasetId);
  if (status) params.append('status', status);
  if (search) params.append('search', search);

  const endpoint = `${cleanUrl}/history?${params.toString()}`;

  try {
    const res = await fetch(endpoint, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
        ...(config.apiKey ? { Authorization: `Bearer ${config.apiKey}` } : {}),
      },
    });
    if (res.ok) {
      return await res.json();
    }
  } catch (err) {
    console.warn('Failed to fetch history:', err);
  }
  return null;
};

export const fetchHistoryItem = async (config: BackendConfig, analysisId: string): Promise<any | null> => {
  const cleanUrl = config.baseUrl.replace(/\/+$/, '');
  const endpoint = `${cleanUrl}/history/${analysisId}`;

  try {
    const res = await fetch(endpoint, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
        ...(config.apiKey ? { Authorization: `Bearer ${config.apiKey}` } : {}),
      },
    });
    if (res.ok) {
      return await res.json();
    }
  } catch (err) {
    console.warn('Failed to fetch history item:', err);
  }
  return null;
};

export const deleteHistoryItem = async (config: BackendConfig, analysisId: string): Promise<boolean> => {
  const cleanUrl = config.baseUrl.replace(/\/+$/, '');
  const endpoint = `${cleanUrl}/history/${analysisId}`;

  try {
    const res = await fetch(endpoint, {
      method: 'DELETE',
      headers: {
        ...(config.apiKey ? { Authorization: `Bearer ${config.apiKey}` } : {}),
      },
    });
    return res.ok;
  } catch (err) {
    console.warn('Failed to delete history item:', err);
  }
  return false;
};
