// frontend/src/services/applicationService.js

/**
 * All API calls related to job applications.
 * Components must never call api directly — always use these functions.
 *
 * Each function returns the unwrapped data (response.data) so callers
 * work with plain objects, not Axios response wrappers.
 */

import api from './api';

const BASE = '/api/applications';

// ---------------------------------------------------------------------------
// List applications
// Supports optional filters: { status, search }
// ---------------------------------------------------------------------------
export async function listApplications(filters = {}) {
  const params = {};
  if (filters.status) params.status = filters.status;
  if (filters.search) params.search = filters.search;
  const response = await api.get(`${BASE}/`, { params });
  return response.data; // Array<ApplicationResponse>
}

// ---------------------------------------------------------------------------
// Get a single application with full timeline
// ---------------------------------------------------------------------------
export async function getApplication(id) {
  const response = await api.get(`${BASE}/${id}`);
  return response.data; // ApplicationDetail
}

// ---------------------------------------------------------------------------
// Create a new application
// body: { job_title, company, date_applied, source?, location?,
//         salary_range?, job_description?, notes?, status? }
// ---------------------------------------------------------------------------
export async function createApplication(body) {
  const response = await api.post(`${BASE}/`, body);
  return response.data; // ApplicationDetail (201)
}

// ---------------------------------------------------------------------------
// Update an application (partial — only send changed fields)
// body: any subset of ApplicationUpdate fields + optional timeline_event
// ---------------------------------------------------------------------------
export async function updateApplication(id, body) {
  const response = await api.patch(`${BASE}/${id}`, body);
  return response.data; // ApplicationDetail (200)
}

// ---------------------------------------------------------------------------
// Delete an application (204 — no response body)
// ---------------------------------------------------------------------------
export async function deleteApplication(id) {
  await api.delete(`${BASE}/${id}`);
  // 204 No Content — nothing to return
}
