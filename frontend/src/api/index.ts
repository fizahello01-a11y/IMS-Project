// src/api/client.ts
import axios from 'axios';

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const apiClient = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
  timeout: 10_000,
});

// src/api/incidents.ts
import { Incident, IncidentStatus, RCA, RCACreateForm, Signal } from '../types';

export const incidentsApi = {
  list: async (status?: string): Promise<Incident[]> => {
    const params = status ? { status } : {};
    const res = await apiClient.get('/incidents', { params });
    return res.data;
  },

  get: async (id: string): Promise<Incident> => {
    const res = await apiClient.get(`/incidents/${id}`);
    return res.data;
  },

  transitionStatus: async (id: string, status: IncidentStatus): Promise<Incident> => {
    const res = await apiClient.patch(`/incidents/${id}/status`, { status });
    return res.data;
  },

  submitRCA: async (id: string, data: RCACreateForm): Promise<RCA> => {
    const payload = {
      ...data,
      incident_start: data.incident_start.toISOString(),
      incident_end:   data.incident_end.toISOString(),
    };
    const res = await apiClient.post(`/incidents/${id}/rca`, payload);
    return res.data;
  },

  getRawSignals: async (workItemId: string): Promise<{ signals: Signal[]; count: number }> => {
    const res = await apiClient.get(`/signals/raw/${workItemId}`);
    return res.data;
  },
};

export const healthApi = {
  get: async () => {
    const res = await apiClient.get('/health');
    return res.data;
  },
  metrics: async () => {
    const res = await apiClient.get('/metrics');
    return res.data;
  },
};
