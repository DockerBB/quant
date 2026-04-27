/** Technical indicator calculations for OHLCV data. */

export interface OHLCV {
  trade_date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  vol: number;
  amount: number;
}

export interface IndicatorData {
  dates: string[];
  values: number[][];
  series: { name: string; type: string; color?: string; yAxisIndex?: number }[];
  dif?: (number | null)[];
  dea?: (number | null)[];
  macd?: (number | null)[];
}

/** Volume bars (red=up, green=down). */
export function calcVolume(data: OHLCV[]): IndicatorData {
  const dates: string[] = [];
  const values: number[][] = [];
  let prevClose = data[0]?.close;
  data.forEach((d) => {
    dates.push(d.trade_date);
    const up = d.close >= (prevClose ?? d.close);
    values.push([d.vol, up ? 1 : 0]);
    prevClose = d.close;
  });
  return {
    dates,
    values,
    series: [
      { name: '成交量', type: 'bar', color: '#ef5350' },
    ],
  };
}

/** RSI-14. */
export function calcRSI(data: OHLCV[], period = 14): IndicatorData {
  const closes = data.map((d) => d.close);
  const rsi: (number | null)[] = new Array(closes.length).fill(null);
  if (closes.length > period) {
    let gainSum = 0;
    let lossSum = 0;
    for (let i = 1; i <= period; i++) {
      const diff = closes[i] - closes[i - 1];
      if (diff > 0) gainSum += diff;
      else lossSum -= diff;
    }
    rsi[period] = 100 - 100 / (1 + gainSum / (lossSum || 1));
    for (let i = period + 1; i < closes.length; i++) {
      const diff = closes[i] - closes[i - 1];
      gainSum = (gainSum * (period - 1) + (diff > 0 ? diff : 0)) / period;
      lossSum = (lossSum * (period - 1) + (diff < 0 ? -diff : 0)) / period;
      rsi[i] = 100 - 100 / (1 + gainSum / (lossSum || 1));
    }
  }
  return {
    dates: data.map((d) => d.trade_date),
    values: rsi.map((v) => [v ?? '-']),
    series: [{ name: 'RSI(14)', type: 'line', color: '#7c4dff' }],
  };
}

/** MACD (12, 26, 9). */
export function calcMACD(data: OHLCV[]): IndicatorData {
  const closes = data.map((d) => d.close);
  const ema = (vals: number[], period: number) => {
    const k = 2 / (period + 1);
    const result: (number | null)[] = new Array(vals.length).fill(null);
    let emaVal = vals[period - 1] || 0;
    result[period - 1] = emaVal;
    for (let i = period; i < vals.length; i++) {
      emaVal = vals[i] * k + emaVal * (1 - k);
      result[i] = emaVal;
    }
    return result;
  };

  const ema12 = ema(closes, 12);
  const ema26 = ema(closes, 26);
  const dif: (number | null)[] = new Array(closes.length).fill(null);
  const dea: (number | null)[] = new Array(closes.length).fill(null);
  const macdBar: (number | null)[] = new Array(closes.length).fill(null);

  for (let i = 26; i < closes.length; i++) {
    if (ema12[i] != null && ema26[i] != null) {
      dif[i] = ema12[i]! - ema26[i]!;
    }
  }

  // Signal line = 9-period EMA of DIF
  let difSum = 0;
  let difCount = 0;
  const startIdx = dif.findIndex((v) => v != null) + 9;
  for (let i = startIdx; i >= startIdx - 8; i--) {
    if (dif[i] != null) { difSum += dif[i]!; difCount++; }
  }
  if (difCount > 0) dea[startIdx] = difSum / difCount;
  for (let i = startIdx + 1; i < closes.length; i++) {
    dea[i] = (dif[i] ?? 0) * (2 / 10) + (dea[i - 1] ?? 0) * (8 / 10);
  }

  for (let i = 0; i < closes.length; i++) {
    if (dif[i] != null && dea[i] != null) {
      macdBar[i] = (dif[i]! - dea[i]!) * 2;
    }
  }

  const dates = data.map((d) => d.trade_date);
  return {
    dates,
    values: [] as number[][],
    series: [
      { name: 'DIF', type: 'line', color: '#2196f3' },
      { name: 'DEA', type: 'line', color: '#ff9800' },
      { name: 'MACD', type: 'bar', color: '#e91e63' },
    ],
    dif,
    dea,
    macd: macdBar,
  };
}
