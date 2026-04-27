import client from './client';
import type { StockInfo, DailyBar, DataRefreshStatus } from '@/types';

export const dataApi = {
  getStockList: (params?: { status?: string; industry?: string }) =>
    client.get<StockInfo[]>('/data/stock-list', { params }).then((r) => r.data),

  getDaily: (tsCode: string, params?: { start_date?: string; end_date?: string; adjust?: string }) =>
    client.get<DailyBar[]>(`/data/daily/${tsCode}`, { params }).then((r) => r.data),

  getFinancial: (tsCode: string, endDate?: string) =>
    client.get(`/data/financial/${tsCode}`, { params: { end_date: endDate } }).then((r) => r.data),

  getTradeDays: (startDate?: string, endDate?: string) =>
    client.get<string[]>('/data/trade-days', { params: { start_date: startDate, end_date: endDate } }).then((r) => r.data),

  refresh: (payload: { data_type: string; date?: string }) =>
    client.post('/data/refresh', payload).then((r) => r.data),

  getStatus: () =>
    client.get<Record<string, DataRefreshStatus>>('/data/status').then((r) => r.data),
};
