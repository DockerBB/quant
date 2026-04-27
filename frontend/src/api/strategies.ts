import client from './client';
import type { StrategyConfig, StrategyRunResult, Signal, SignalStats } from '@/types';

export const strategyApi = {
  list: () =>
    client.get<StrategyConfig[]>('/strategies/').then((r) => r.data),

  create: (config: StrategyConfig) =>
    client.post('/strategies/', config).then((r) => r.data),

  get: (id: string) =>
    client.get<StrategyConfig>(`/strategies/${id}`).then((r) => r.data),

  update: (id: string, config: StrategyConfig) =>
    client.put(`/strategies/${id}`, config).then((r) => r.data),

  delete: (id: string) =>
    client.delete(`/strategies/${id}`).then((r) => r.data),

  run: (id: string, tradeDate?: string) =>
    client.post<StrategyRunResult>(`/strategies/${id}/run`, { trade_date: tradeDate }).then((r) => r.data),

  validate: (id: string) =>
    client.post<{ valid: boolean; errors: string[]; warnings: string[] }>(`/strategies/${id}/validate`).then((r) => r.data),

  getSignals: (id: string) =>
    client.get<Signal[]>(`/signals/${id}/current`).then((r) => r.data),

  getSignalSummary: (id: string) =>
    client.get<SignalStats>(`/signals/${id}/summary`).then((r) => r.data),

  getSignalHistory: (id: string, start?: string, end?: string) =>
    client.get<Signal[]>(`/signals/${id}/history`, { params: { start_date: start, end_date: end } }).then((r) => r.data),
};
