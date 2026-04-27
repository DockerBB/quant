import client from './client';
import type { ScheduledTask } from '@/types';

export const schedulerApi = {
  listTasks: () =>
    client.get<ScheduledTask[]>('/scheduler/tasks').then((r) => r.data),

  runNow: (taskId: string) =>
    client.post(`/scheduler/tasks/${taskId}/run-now`).then((r) => r.data),

  toggle: (taskId: string) =>
    client.post(`/scheduler/tasks/${taskId}/toggle`).then((r) => r.data),
};
