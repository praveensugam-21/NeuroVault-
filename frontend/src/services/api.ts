import axios from 'axios';

const API_URL = 'http://localhost:8001';

const api = axios.create({
  baseURL: API_URL,
});

// Request interceptor to append JWT token
api.interceptors.request.use(
  (config) => {
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
