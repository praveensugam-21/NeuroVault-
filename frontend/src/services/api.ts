import axios from 'axios';

export const getApiUrl = () => {
  const customUrl = localStorage.getItem('custom_api_url');
  if (customUrl) {
    return customUrl;
  }
  if (import.meta.env.VITE_API_URL) {
    return import.meta.env.VITE_API_URL;
  }
  // Check if we are running in Capacitor mobile wrapper
  if (window.hasOwnProperty('Capacitor') || (window as any).Capacitor) {
    return 'https://plain-pianos-hammer.loca.lt'; // Secure public tunnel to bypass firewall
  }
  return 'http://localhost:8001';
};

const api = axios.create({
  baseURL: getApiUrl(),
});

// Request interceptor to append JWT token and update baseURL dynamically
api.interceptors.request.use(
  (config) => {
    config.baseURL = getApiUrl();
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor to handle authorization expiration
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      localStorage.removeItem('access_token');
      // If we are in the browser, trigger redirect or store reload
      window.dispatchEvent(new Event('auth_failed'));
    }
    return Promise.reject(error);
  }
);

export default api;
