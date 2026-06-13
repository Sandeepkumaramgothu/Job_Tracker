// frontend/src/hooks/useApplications.js

/**
 * TanStack Query hooks for all server state related to job applications.
 *
 * Rules (from CLAUDE.md):
 *  - All server state goes through TanStack Query — no raw fetch/useEffect
 *  - Every hook that fetches handles loading, error, and empty states
 *  - Mutations invalidate the relevant query keys so lists/details refresh
 *
 * Query key convention:
 *  ['applications']              — list (with optional filters)
 *  ['applications', id]          — single application detail
 *  ['analytics']                 — analytics summary
 *  ['notifications', 'settings'] — notification settings
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  createApplication,
  deleteApplication,
  getApplication,
  listApplications,
  updateApplication,
} from '../services/applicationService';
import { uploadFile } from '../services/fileService';

// ---------------------------------------------------------------------------
// useApplications — list with optional filters
// filters: { status?: string, search?: string }
// ---------------------------------------------------------------------------
export function useApplications(filters = {}) {
  return useQuery({
    queryKey: ['applications', filters],
    queryFn: () => listApplications(filters),
    staleTime: 30_000,       // treat data as fresh for 30s
    retry: 2,
  });
}

// ---------------------------------------------------------------------------
// useApplication — single application with full timeline
// ---------------------------------------------------------------------------
export function useApplication(id) {
  return useQuery({
    queryKey: ['applications', id],
    queryFn: () => getApplication(id),
    enabled: Boolean(id),    // don't fire until we have a real id
    staleTime: 15_000,
    retry: 2,
  });
}

// ---------------------------------------------------------------------------
// useCreateApplication
// On success: invalidates the list so the new entry appears immediately
// ---------------------------------------------------------------------------
export function useCreateApplication() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (body) => createApplication(body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['applications'] });
      queryClient.invalidateQueries({ queryKey: ['analytics'] });
    },
  });
}

// ---------------------------------------------------------------------------
// useUpdateApplication
// On success: invalidates both the list and the specific detail entry
// ---------------------------------------------------------------------------
export function useUpdateApplication() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, body }) => updateApplication(id, body),
    onSuccess: (data) => {
      // Update the cached detail entry directly (avoids an extra network request)
      queryClient.setQueryData(['applications', data.id], data);
      // Invalidate the list so status/company changes are reflected there too
      queryClient.invalidateQueries({ queryKey: ['applications'] });
      queryClient.invalidateQueries({ queryKey: ['analytics'] });
    },
  });
}

// ---------------------------------------------------------------------------
// useDeleteApplication
// On success: removes detail from cache and invalidates the list
// ---------------------------------------------------------------------------
export function useDeleteApplication() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id) => deleteApplication(id),
    onSuccess: (_, id) => {
      queryClient.removeQueries({ queryKey: ['applications', id] });
      queryClient.invalidateQueries({ queryKey: ['applications'] });
      queryClient.invalidateQueries({ queryKey: ['analytics'] });
    },
  });
}

// ---------------------------------------------------------------------------
// useUploadFile
// Returns { filename, path } on success.
// Callers should then call useUpdateApplication to link the path to an app.
// ---------------------------------------------------------------------------
export function useUploadFile() {
  return useMutation({
    mutationFn: (file) => uploadFile(file),
    // No cache invalidation needed — file upload doesn't change query data
    // until the caller links the path to an application via updateApplication.
  });
}
