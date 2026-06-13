// frontend/src/hooks/useNotifications.js

/**
 * TanStack Query hooks for notification settings.
 *
 * Query key: ['notifications', 'settings']
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import api from '../services/api';

// ---------------------------------------------------------------------------
// Service functions (inline — notifications has only 3 endpoints)
// ---------------------------------------------------------------------------
async function getSettings() {
  const res = await api.get('/api/notifications/settings');
  return res.data;
}

async function saveSettings(body) {
  const res = await api.put('/api/notifications/settings', body);
  return res.data;
}

async function sendTestEmail() {
  const res = await api.post('/api/notifications/test');
  return res.data;
}

// ---------------------------------------------------------------------------
// useNotificationSettings — fetch current preferences
// Returns 404 (null) when not yet configured
// ---------------------------------------------------------------------------
export function useNotificationSettings() {
  return useQuery({
    queryKey: ['notifications', 'settings'],
    queryFn: getSettings,
    retry: (failureCount, error) => {
      // Don't retry on 404 — it just means settings haven't been configured yet
      if (error?.response?.status === 404) return false;
      return failureCount < 2;
    },
    staleTime: 60_000,
  });
}

// ---------------------------------------------------------------------------
// useSaveNotificationSettings — upsert preferences
// ---------------------------------------------------------------------------
export function useSaveNotificationSettings() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body) => saveSettings(body),
    onSuccess: (data) => {
      queryClient.setQueryData(['notifications', 'settings'], data);
    },
  });
}

// ---------------------------------------------------------------------------
// useSendTestEmail — trigger test notification
// ---------------------------------------------------------------------------
export function useSendTestEmail() {
  return useMutation({
    mutationFn: sendTestEmail,
  });
}
