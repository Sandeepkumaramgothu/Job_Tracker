// frontend/src/services/aiService.js

/**
 * AI extraction service.
 *
 * Backend at POST /api/ai/extract expects { job_description }, returns
 * { job_title, company, location, salary_range, source, notes } where
 * any unparseable field is null.
 */

import api from './api';

export async function extractJobDescription(jobDescription) {
  const response = await api.post('/api/ai/extract', {
    job_description: jobDescription,
  });
  return response.data;
}
