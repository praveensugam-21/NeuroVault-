import { create } from 'zustand';
import api from '../services/api';

interface AuthState {
  token: string | null;
  isAuthenticated: boolean;
  pinVerified: boolean;
  pinConfigured: boolean;
  error: string | null;
  loading: boolean;
  
  login: (email: string, password: string) => Promise<boolean>;
  register: (email: string, password: string) => Promise<boolean>;
  logout: () => void;
  setupPin: (pin: string) => Promise<boolean>;
  verifyPin: (pin: string) => Promise<boolean>;
  clearError: () => void;
  setPinVerified: (verified: boolean) => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  token: localStorage.getItem('access_token'),
  isAuthenticated: !!localStorage.getItem('access_token'),
  pinVerified: false,
  pinConfigured: false,
  error: null,
  loading: false,

  login: async (email, password) => {
    set({ loading: true, error: null });
    try {
      const formData = new FormData();
      formData.append('username', email);
      formData.append('password', password);

      const response = await api.post('/api/auth/login', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      const { access_token } = response.data;
      localStorage.setItem('access_token', access_token);
      set({ token: access_token, isAuthenticated: true, loading: false });
      return true;
    } catch (err: any) {
      set({
        error: err.response?.data?.detail || 'Authentication failed. Please verify credentials.',
        loading: false,
      });
      return false;
    }
  },

  register: async (email, password) => {
    set({ loading: true, error: null });
    try {
      await api.post('/api/auth/register', { email, password });
      set({ loading: false });
      return true;
    } catch (err: any) {
      set({
        error: err.response?.data?.detail || 'Account registration failed.',
        loading: false,
      });
      return false;
    }
  },

  logout: () => {
    localStorage.removeItem('access_token');
    set({ token: null, isAuthenticated: false, pinVerified: false });
  },

  setupPin: async (pin) => {
    try {
      await api.post('/api/auth/pin/setup', { pin });
      set({ pinConfigured: true });
      return true;
    } catch (err: any) {
      set({ error: err.response?.data?.detail || 'Failed to configure PIN.' });
      return false;
    }
  },

  verifyPin: async (pin) => {
    try {
      await api.post('/api/auth/pin/verify', { pin });
      set({ pinVerified: true });
      return true;
    } catch (err: any) {
      set({ pinVerified: false, error: 'Incorrect security PIN.' });
      return false;
    }
  },

  clearError: () => set({ error: null }),
  
  setPinVerified: (verified) => set({ pinVerified: verified }),
}));

// Listen for global auth failure events
if (typeof window !== 'undefined') {
  window.addEventListener('auth_failed', () => {
    useAuthStore.getState().logout();
  });
}
