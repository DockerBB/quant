import client from './client';
import type { FactorMeta, FactorValue } from '@/types';

export const factorApi = {
  list: (category?: string) =>
    client.get<FactorMeta[]>('/factors/', { params: { category } }).then((r) => r.data),

  get: (name: string) =>
    client.get<FactorMeta>(`/factors/${name}`).then((r) => r.data),

  getValues: (name: string, params?: { trade_date?: string; limit?: number }) =>
    client.get<FactorValue[]>(`/factors/${name}/values`, { params }).then((r) => r.data),
};
