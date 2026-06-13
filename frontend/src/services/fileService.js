// frontend/src/services/fileService.js

/**
 * File upload and download service.
 *
 * Upload workflow (from CLAUDE.md):
 *  1. User selects a file in the FileUploadZone component
 *  2. Component calls uploadFile(file) → receives { filename, path }
 *  3. Component calls updateApplication(id, { resume_path: path })
 *     to link the file to the application
 *
 * Never import api directly in components — use these functions.
 */

import api from './api';

const BASE = '/api/files';

// ---------------------------------------------------------------------------
// Upload a file (resume or cover letter)
// Accepts a native File object from an <input type="file"> or drag-and-drop.
// Returns { filename: string, path: string }
//
// WARN: Only PDF and DOCX files are accepted by the backend (max 5 MB).
// Validate on the client before calling this to give immediate feedback,
// but the backend always enforces the limit independently.
// ---------------------------------------------------------------------------
export async function uploadFile(file) {
  const formData = new FormData();
  formData.append('file', file);
  // Content-Type is intentionally NOT set here — axios sets it automatically
  // with the correct multipart/form-data boundary for FormData payloads.
  const response = await api.post(`${BASE}/upload`, formData);
  return response.data; // { filename, path }
}

// ---------------------------------------------------------------------------
// Get the public download URL for a stored file.
// Returns a string URL that can be used as an <a href> or window.open target.
// The URL triggers an attachment download (Content-Disposition: attachment).
// ---------------------------------------------------------------------------
export function getFileDownloadUrl(filename) {
  const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
  return `${baseUrl}${BASE}/${encodeURIComponent(filename)}`;
}

// ---------------------------------------------------------------------------
// Client-side file validation — call before uploadFile() to give
// instant feedback without a network round-trip.
// Returns { valid: bool, error: string | null }
// ---------------------------------------------------------------------------
const ALLOWED_TYPES = [
  'application/pdf',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
];
const MAX_SIZE_BYTES = 5 * 1024 * 1024; // 5 MB

export function validateFile(file) {
  if (!file) {
    return { valid: false, error: 'No file selected.' };
  }
  const ext = file.name.split('.').pop().toLowerCase();
  if (!['pdf', 'docx'].includes(ext)) {
    return { valid: false, error: 'Only PDF and DOCX files are allowed.' };
  }
  if (!ALLOWED_TYPES.includes(file.type) && file.type !== '') {
    // Allow empty type — some browsers don't report MIME for .docx
    return { valid: false, error: 'Only PDF and DOCX files are allowed.' };
  }
  if (file.size > MAX_SIZE_BYTES) {
    const sizeMB = (file.size / 1024 / 1024).toFixed(1);
    return { valid: false, error: `File is ${sizeMB} MB. Maximum allowed size is 5 MB.` };
  }
  return { valid: true, error: null };
}
