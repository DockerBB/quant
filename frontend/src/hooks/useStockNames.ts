import { useMemo } from 'react';
import { useStockList } from './useDataApi';

function classifySector(code: string): string {
  const num = code.split('.')[0];
  if (num.startsWith('300')) return '创业板';
  if (num.startsWith('688')) return '科创板';
  if (num.startsWith('00') || num.startsWith('001') || num.startsWith('002')) return '深市主板';
  if (num.startsWith('60')) return '沪市主板';
  if (num.startsWith('8')) return '北交所';
  if (num.startsWith('4')) return '三板';
  return '其他';
}

export function useStockNameMap() {
  const { data: stocks } = useStockList();
  return useMemo(() => {
    const map: Record<string, string> = {};
    if (stocks) {
      (stocks as Record<string, unknown>[]).forEach((s) => {
        map[s.ts_code as string] = (s.name as string) || s.ts_code as string;
      });
    }
    return map;
  }, [stocks]);
}

export function useStockSectorMap() {
  const { data: stocks } = useStockList();
  return useMemo(() => {
    const map: Record<string, string> = {};
    if (stocks) {
      (stocks as Record<string, unknown>[]).forEach((s) => {
        map[s.ts_code as string] = classifySector(s.ts_code as string);
      });
    }
    return map;
  }, [stocks]);
}
