import axios from 'axios';

const api = axios.create({
  // Vite 프록시(`/api`)를 이용하거나 환경변수 지정
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
});

// 요청 인터셉터: X-User-Id 헤더 자동 탑재
api.interceptors.request.use((config) => {
  const userId = localStorage.getItem('user_id') || 'kr_user_01';
  if (userId) {
    config.headers['X-User-Id'] = userId;
  }
  return config;
});

export default api;