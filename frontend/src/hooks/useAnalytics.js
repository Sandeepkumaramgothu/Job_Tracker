// frontend/src/hooks/useAnalytics.js

/**
 * TanStack Query hook for the analytics summary.
 * Query key: ['analytics']
 */

import { useQuery } from '@tanstack/react-query';
import api from '../services/api';

async function fetchAnalyticsSummary() {
  const res = await api.get('/api/analytics/summary');
  return res.data;
}

export function useAnalytics() {
  return useQuery({
    queryKey: ['analytics'],
    queryFn: fetchAnalyticsSummary,
    staleTime: 60_000, // analytics are expensive; keep fresh for 1 minute
    retry: 2,
  });
}
