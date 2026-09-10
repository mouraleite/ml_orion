import axios from 'axios';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export const api = axios.create({
  baseURL: API_URL,
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Interceptador para injetar o token em todas as requisições
api.interceptors.request.use((config) => {
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('access_token');
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    const headers = config.headers;
    const headerDepto = headers?.["X-Department-Id"] ?? headers?.["x-department-id"];
    const jaTemDepto = headerDepto !== undefined && headerDepto !== null && headerDepto !== "";
    if (!jaTemDepto) {
      const dept = localStorage.getItem("departamento_id");
      if (dept != null && dept !== "" && headers) {
        headers["X-Department-Id"] = dept;
      }
    }
  }
  return config;
}, (error) => {
  return Promise.reject(error);
});
