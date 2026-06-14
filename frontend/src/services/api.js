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
  (config) => {
    // Only set JSON content-type when the body is NOT FormData.
    // For FormData (file uploads) axios sets the correct multipart/form-data
    // boundary automatically — overriding it would break the upload.
    if (!(config.data instanceof FormData)) {
      config.headers['Content-Type'] = 'application/json';
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
  (error) => {
    // Build a consistent error message for callers to display
    const detail =
      error.response?.data?.detail ||        // FastAPI HTTPException detail
      error.response?.data?.message ||       // generic JSON message
      error.message ||                        // axios network error
      'An unexpected error occurred.';

    // Attach a human-readable message to the error so components can do:
    //   error.userMessage
    error.userMessage =
      typeof detail === 'string'
        ? detail
        : JSON.stringify(detail); // FastAPI sometimes returns detail as array

    return Promise.reject(error);
  },
);

export default api;
