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
 *  ['applications', 'list', filters] — list (with optional filters)
 *  ['applications', 'detail', id]    — single application detail
 *  ['analytics']                     — analytics summary
 *  ['notifications', 'settings']     — notification settings
 *
 * Separating 'list' and 'detail' segments prevents an invalidation of one
 * from cascading to the other (e.g. an update should refresh the list but
 * not throw away the freshly-set detail data).
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

const LIST_KEY   = ['applications', 'list'];
const DETAIL_KEY = (id) => ['applications', 'detail', id];

// ---------------------------------------------------------------------------
// useApplications — list with optional filters
// filters: { status?: string, search?: string }
// ---------------------------------------------------------------------------
export function useApplications(filters = {}) {
  return useQuery({
    queryKey: [...LIST_KEY, filters],
    queryFn: () => listApplications(filters),
    staleTime: 30_000,
    retry: 2,
  });
}

// ---------------------------------------------------------------------------
// useApplication — single application with full timeline
// ---------------------------------------------------------------------------
export function useApplication(id) {
  return useQuery({
    queryKey: DETAIL_KEY(id),
    queryFn: () => getApplication(id),
    enabled: Boolean(id),
    staleTime: 15_000,
    retry: 2,
  });
}

// ---------------------------------------------------------------------------
// useCreateApplication
// ---------------------------------------------------------------------------
export function useCreateApplication() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (body) => createApplication(body),
    onSuccess: (data) => {
      queryClient.setQueryData(DETAIL_KEY(data.id), data);
      queryClient.invalidateQueries({ queryKey: LIST_KEY });
      queryClient.invalidateQueries({ queryKey: ['analytics'] });
    },
  });
}

// ---------------------------------------------------------------------------
// useUpdateApplication
// ---------------------------------------------------------------------------
export function useUpdateApplication() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, body }) => updateApplication(id, body),
    onSuccess: (data) => {
      queryClient.setQueryData(DETAIL_KEY(data.id), data);
      queryClient.invalidateQueries({ queryKey: LIST_KEY });
      queryClient.invalidateQueries({ queryKey: ['analytics'] });
    },
  });
}

// ---------------------------------------------------------------------------
// useDeleteApplication
// ---------------------------------------------------------------------------
export function useDeleteApplication() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id) => deleteApplication(id),
    onSuccess: (_, id) => {
      queryClient.removeQueries({ queryKey: DETAIL_KEY(id) });
      queryClient.invalidateQueries({ queryKey: LIST_KEY });
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
