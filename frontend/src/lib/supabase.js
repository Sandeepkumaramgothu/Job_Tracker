// frontend/src/lib/supabase.js

/**
 * Single shared Supabase client.
 *
 * Uses VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY at build time. The anon
 * key is safe to ship to the browser — Row Level Security and our backend's
 * JWT verification are what actually enforce authorization.
 *
 * If either env var is missing, every Supabase call will throw immediately,
 * which surfaces in the Login page and is easier to debug than a silent
 * "session is null" state.
 */

import { createClient } from '@supabase/supabase-js';

const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL;
const SUPABASE_ANON_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY;

if (!SUPABASE_URL || !SUPABASE_ANON_KEY) {
  console.error(
    'VITE_SUPABASE_URL / VITE_SUPABASE_ANON_KEY missing — auth will not work. ' +
    'Set both in the Pages build env (GitHub Actions vars) and your local .env.'
  );
}

export const supabase = createClient(SUPABASE_URL ?? '', SUPABASE_ANON_KEY ?? '', {
  auth: {
    persistSession: true,
    autoRefreshToken: true,
    detectSessionInUrl: true,
  },
});
