import { create } from 'zustand';
import api from '../services/api';
import type { DocumentBrief, DocumentDetail, DashboardStats, TimelineItem, ExpiryAlert, GraphResponse } from '../types';


interface VaultState {
  documents: DocumentBrief[];
  stats: DashboardStats | null;
  timelines: { academic: TimelineItem[]; career: TimelineItem[] } | null;
  alerts: ExpiryAlert[];
  graph: GraphResponse | null;
  activeCategory: string | null;
  loading: boolean;
  error: string | null;

  fetchDocuments: () => Promise<void>;
  fetchStats: () => Promise<void>;
  fetchTimelines: () => Promise<void>;
  fetchAlerts: () => Promise<void>;
  fetchGraph: () => Promise<void>;
  setActiveCategory: (category: string | null) => void;
  uploadDocument: (file: File, customName?: string) => Promise<boolean>;
  deleteDocument: (id: string) => Promise<boolean>;
  lockDocument: (id: string) => Promise<boolean>;
  unlockDocument: (id: string) => Promise<boolean>;
  fetchDocumentDetail: (id: string, pin?: string) => Promise<DocumentDetail | null>;
  reextractDocument: (id: string) => Promise<DocumentDetail | null>;
}

export const useVaultStore = create<VaultState>((set, get) => ({
  documents: [],
  stats: null,
  timelines: null,
  alerts: [],
  graph: null,
  activeCategory: null,
  loading: false,
  error: null,

  fetchDocuments: async () => {
    set({ loading: true, error: null });
    try {
      const category = get().activeCategory;
      const url = category ? `/api/documents/?category=${encodeURIComponent(category)}` : '/api/documents/';
      const response = await api.get(url);
      set({ documents: response.data, loading: false });
    } catch (err: any) {
      set({ error: 'Failed to retrieve document vault.', loading: false });
    }
  },

  fetchStats: async () => {
    try {
      const response = await api.get('/api/dashboard/stats');
      set({ stats: response.data });
    } catch (err) {}
  },

  fetchTimelines: async () => {
    try {
      const response = await api.get('/api/dashboard/timelines');
      set({ timelines: response.data });
    } catch (err) {}
  },

  fetchAlerts: async () => {
    try {
      const response = await api.get('/api/dashboard/expiry-alerts');
      set({ alerts: response.data });
    } catch (err) {}
  },

  fetchGraph: async () => {
    try {
      const response = await api.get('/api/graph/');
      set({ graph: response.data });
    } catch (err) {}
  },

  setActiveCategory: (category) => {
    set({ activeCategory: category });
    get().fetchDocuments();
  },

  uploadDocument: async (file, customName) => {
    set({ loading: true, error: null });
    try {
      const formData = new FormData();
      formData.append('file', file);
      if (customName) {
        formData.append('name', customName);
      }
      await api.post('/api/documents/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      
      // Refresh statistics and list
      await get().fetchDocuments();
      await get().fetchStats();
      set({ loading: false });
      return true;
    } catch (err: any) {
      set({ error: err.response?.data?.detail || 'Document upload failed.', loading: false });
      return false;
    }
  },

  deleteDocument: async (id) => {
    try {
      await api.delete(`/api/documents/${id}`);
      // Refresh state
      await get().fetchDocuments();
      await get().fetchStats();
      await get().fetchTimelines();
      await get().fetchAlerts();
      await get().fetchGraph();
      return true;
    } catch (err) {
      return false;
    }
  },

  lockDocument: async (id) => {
    try {
      await api.post(`/api/documents/${id}/lock`);
      await get().fetchDocuments();
      return true;
    } catch (err) {
      return false;
    }
  },

  unlockDocument: async (id) => {
    try {
      await api.post(`/api/documents/${id}/unlock`);
      await get().fetchDocuments();
      return true;
    } catch (err) {
      return false;
    }
  },

  fetchDocumentDetail: async (id, pin) => {
    try {
      const url = pin ? `/api/documents/${id}?pin=${encodeURIComponent(pin)}` : `/api/documents/${id}`;
      const response = await api.get(url);
      return response.data;
    } catch (err: any) {
      set({ error: err.response?.data?.detail || 'Failed to open document detail.' });
      return null;
    }
  },

  reextractDocument: async (id) => {
    set({ loading: true, error: null });
    try {
      await api.post(`/api/documents/${id}/reextract`);
      await get().fetchDocuments();
      await get().fetchStats();
      await get().fetchTimelines();
      await get().fetchAlerts();
      await get().fetchGraph();
      set({ loading: false });
      const freshDetail = await get().fetchDocumentDetail(id);
      return freshDetail;
    } catch (err: any) {
      set({ error: err.response?.data?.detail || 'Re-extraction failed.', loading: false });
      return null;
    }
  },
}));
