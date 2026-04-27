import { useQuery } from '@tanstack/react-query';
import { factorApi } from '@/api/factors';

export function useFactorList(category?: string) {
  return useQuery({ queryKey: ['factors', category], queryFn: () => factorApi.list(category) });
}

export function useFactorValues(name: string, date?: string) {
  return useQuery({
    queryKey: ['factorValues', name, date],
    queryFn: () => factorApi.getValues(name, { trade_date: date, limit: 50 }),
    enabled: !!name,
  });
}
