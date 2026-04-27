import axios from 'axios';

const client = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
});

client.interceptors.response.use(
  (res) => res,
  (err) => {
    const msg = err.response?.data?.detail || err.message || '请求失败';
    console.error('[API Error]', msg);
    return Promise.reject(err);
  },
);

export default client;
