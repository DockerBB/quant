import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { dataApi } from '@/api/data';

export function useStockList(status?: string) {
  return useQuery({ queryKey: ['stockList', status], queryFn: () => dataApi.getStockList({ status }) });
}

export function useDailyData(tsCode: string, start?: string, end?: string) {
  return useQuery({
    queryKey: ['daily', tsCode, start, end],
    queryFn: () => dataApi.getDaily(tsCode, { start_date: start, end_date: end, adjust: 'bwd' }),
    enabled: !!tsCode,
  });
}

export function useDataStatus() {
  return useQuery({ queryKey: ['dataStatus'], queryFn: dataApi.getStatus, refetchInterval: 60000 });
}

export function useDataRefresh() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (dataType: string) => dataApi.refresh({ data_type: dataType }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['dataStatus'] }); },
  });
}
