import axios from 'axios';

// Construct API Base URL from environment or default to local proxy
const getBaseUrl = () => {
  if (import.meta.env.VITE_API_BASE_URL) {
    // If VITE_API_BASE_URL is just a host like 'my-app.onrender.com', format it
    let baseUrl = import.meta.env.VITE_API_BASE_URL;
    if (!baseUrl.startsWith('http')) {
      baseUrl = `https://${baseUrl}`;
    }
    return `${baseUrl}/api`;
  }
  return '/api'; // local dev proxy or relative path
};

const api = axios.create({
  baseURL: getBaseUrl(),
  headers: { 'Content-Type': 'application/json' },
});

// Request interceptor: attach JWT token
api.interceptors.request.use((config) => {
  const tokens = JSON.parse(localStorage.getItem('tokens') || '{}');
  if (tokens.access) {
    config.headers.Authorization = `Bearer ${tokens.access}`;
  }
  return config;
});

// Response interceptor: auto-refresh on 401
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      const tokens = JSON.parse(localStorage.getItem('tokens') || '{}');
      if (tokens.refresh) {
        try {
          const res = await axios.post('/api/auth/refresh/', { refresh: tokens.refresh });
          const newTokens = { ...tokens, access: res.data.access };
          if (res.data.refresh) newTokens.refresh = res.data.refresh;
          localStorage.setItem('tokens', JSON.stringify(newTokens));
          originalRequest.headers.Authorization = `Bearer ${res.data.access}`;
          return api(originalRequest);
        } catch {
          localStorage.removeItem('tokens');
          localStorage.removeItem('user');
          window.location.href = '/login';
        }
      }
    }
    return Promise.reject(error);
  }
);

export default api;
