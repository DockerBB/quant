import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { strategyApi } from '@/api/strategies';

export function useStrategyList() {
  return useQuery({ queryKey: ['strategies'], queryFn: strategyApi.list });
}

export function useStrategy(id: string) {
  return useQuery({ queryKey: ['strategy', id], queryFn: () => strategyApi.get(id), enabled: !!id });
}

export function useCreateStrategy() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: strategyApi.create,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['strategies'] }); },
  });
}

export function useDeleteStrategy() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: strategyApi.delete,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['strategies'] }); },
  });
}

export function useRunStrategy() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, date }: { id: string; date?: string }) => strategyApi.run(id, date),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['signals'] }); },
  });
}

export function useCurrentSignals(id: string) {
  return useQuery({
    queryKey: ['signals', id],
    queryFn: () => strategyApi.getSignals(id),
    enabled: !!id,
  });
}

export function useSignalSummary(id: string) {
  return useQuery({
    queryKey: ['signalSummary', id],
    queryFn: () => strategyApi.getSignalSummary(id),
    enabled: !!id,
  });
}
