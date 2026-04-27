// ---- Data ----
export interface StockInfo {
  ts_code: string;
  symbol: string;
  name: string;
  area: string | null;
  industry: string | null;
  market: string | null;
  list_date: string | null;
  status: string;
}

export interface DailyBar {
  ts_code: string;
  trade_date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  pre_close: number | null;
  change: number | null;
  pct_chg: number | null;
  vol: number | null;
  amount: number | null;
  turnover_rate: number | null;
}

export interface DataRefreshStatus {
  data_type: string;
  last_updated: string | null;
  record_count: number;
  status: string;
}

// ---- Factors ----
export interface FactorMeta {
  name: string;
  category: string;
  direction: string;
  description: string;
  params: Record<string, unknown>;
}

export interface FactorValue {
  ts_code: string;
  value: number;
}

// ---- Strategies ----
export interface StrategyConfig {
  id: string;
  name: string;
  description?: string;
  is_active?: boolean;
  config_yaml: string;
}

export interface StrategyRunResult {
  strategy_id: string;
  trade_date: string;
  signals_count: number;
  buy_count: number;
  sell_count: number;
  status: string;
}

// ---- Signals ----
export interface Signal {
  strategy_id: string;
  date: string;
  ts_code: string;
  signal_type: 'buy' | 'sell' | 'hold';
  score: number | null;
  percentile: number | null;
  detail: Record<string, unknown> | null;
}

export interface SignalSummary {
  date: string | null;
  buys: Signal[];
  sells: Signal[];
  holds: Signal[];
}

export interface SignalStats {
  strategy_id: string;
  date: string | null;
  buy_count: number;
  sell_count: number;
  hold_count: number;
}

// ---- Scheduler ----
export interface ScheduledTask {
  id: string;
  name: string;
  task_type: string;
  cron_expr: string | null;
  is_active: boolean;
  last_run: string | null;
  next_run: string | null;
  config: Record<string, unknown>;
}

// ---- Health ----
export interface HealthCheck {
  status: string;
  version: string;
  timestamp: string;
}
