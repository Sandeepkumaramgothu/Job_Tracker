// frontend/src/services/api.js

/**
 * Axios instance shared by all service modules.
 *
 * Rules (from CLAUDE.md):
 *  - Never import axios directly in components — always go through services/
 *  - Base URL comes from VITE_API_BASE_URL env var
 *  - Request interceptor: add Content-Type (omitted for FormData so axios
 *    can set the multipart boundary automatically)
 *  - Response interceptor: normalise errors into a consistent shape so
 *    components never need to inspect raw Axios error objects
 */

import axios from 'axios';
import { supabase } from '../lib/supabase';

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'https://job-tracker-fjd6.onrender.com';

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
  headers: {
    Accept: 'application/json',
  },
});

// ---------------------------------------------------------------------------
// Request interceptor
// ---------------------------------------------------------------------------
api.interceptors.request.use(
  async (config) => {
    // Only set JSON content-type when the body is NOT FormData.
    // For FormData (file uploads) axios sets the correct multipart/form-data
    // boundary automatically — overriding it would break the upload.
    if (!(config.data instanceof FormData)) {
      config.headers['Content-Type'] = 'application/json';
    }
    // Attach the current Supabase access token. getSession() reads from
    // localStorage synchronously after the first hydration so this is cheap.
    const { data } = await supabase.auth.getSession();
    const token = data.session?.access_token;
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error),
);

// ---------------------------------------------------------------------------
// Response interceptor — normalise errors
// ---------------------------------------------------------------------------
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    // 401 means the token is missing, expired, or invalid. Sign the user out
    // so the route guard redirects to the login page on the next render.
    if (error.response?.status === 401) {
      try { await supabase.auth.signOut(); } catch { /* best-effort */ }
    }

    const detail =
      error.response?.data?.detail ||
      error.response?.data?.message ||
      error.message ||
      'An unexpected error occurred.';

    error.userMessage =
      typeof detail === 'string' ? detail : JSON.stringify(detail);

    return Promise.reject(error);
  },
);

export default api;
