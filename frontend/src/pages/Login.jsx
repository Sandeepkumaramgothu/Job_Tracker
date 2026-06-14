// frontend/src/pages/Login.jsx

/**
 * Login / signup screen.
 *
 * Toggleable between Sign In and Sign Up modes for email + password.
 *
 * On successful signup with email confirmation enabled in Supabase, the user
 * gets a confirmation email and must click the link before they can sign in.
 * We surface that as a friendly message instead of a generic error.
 */

import { useState } from 'react';
import { useAuth } from '../hooks/useAuth';

export default function Login() {
  const { signUpWithEmail, signInWithEmail } = useAuth();

  const [mode, setMode] = useState('signin'); // 'signin' | 'signup'
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [info, setInfo] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setInfo(null);
    setSubmitting(true);
    try {
      const fn = mode === 'signup' ? signUpWithEmail : signInWithEmail;
      const { data, error: err } = await fn(email, password);
      if (err) {
        setError(err.message);
      } else if (mode === 'signup' && !data.session) {
        // Email confirmation is on; signup succeeds but no session yet.
        setInfo('Check your email to confirm your account, then sign in.');
        setMode('signin');
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center px-4">
      <div className="w-full max-w-md">
        {/* Brand */}
        <div className="flex flex-col items-center mb-8">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-blue-500 to-violet-600
                          flex items-center justify-center shadow-lg shadow-blue-500/30 mb-4">
            <span className="text-xl">💼</span>
          </div>
          <h1 className="text-2xl font-bold text-white">Job Tracker</h1>
          <p className="text-sm text-slate-400 mt-1">Your job-search command center</p>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-7 shadow-2xl">
          {/* Tabs */}
          <div className="grid grid-cols-2 gap-1 p-1 bg-slate-800/60 border border-slate-700/50 rounded-xl mb-6">
            {['signin', 'signup'].map((m) => (
              <button
                key={m}
                type="button"
                onClick={() => { setMode(m); setError(null); setInfo(null); }}
                className={`text-sm font-semibold py-2 rounded-lg transition-colors
                            ${mode === m
                              ? 'bg-slate-900 text-white shadow border border-slate-700'
                              : 'text-slate-400 hover:text-slate-200'}`}
              >
                {m === 'signin' ? 'Sign In' : 'Sign Up'}
              </button>
            ))}
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="login-email" className="block text-xs font-semibold text-slate-400 mb-1.5">
                Email
              </label>
              <input
                id="login-email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="email"
                placeholder="you@example.com"
                className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3.5 py-2.5
                           text-sm text-slate-100 placeholder-slate-500
                           focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500
                           transition-colors"
              />
            </div>
            <div>
              <label htmlFor="login-password" className="block text-xs font-semibold text-slate-400 mb-1.5">
                Password
              </label>
              <input
                id="login-password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={6}
                autoComplete={mode === 'signup' ? 'new-password' : 'current-password'}
                placeholder={mode === 'signup' ? 'At least 6 characters' : ''}
                className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3.5 py-2.5
                           text-sm text-slate-100 placeholder-slate-500
                           focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500
                           transition-colors"
              />
            </div>

            {error && (
              <div className="text-red-400 text-sm bg-red-500/10 border border-red-500/20 rounded-xl p-3">
                {error}
              </div>
            )}
            {info && (
              <div className="text-emerald-400 text-sm bg-emerald-500/10 border border-emerald-500/20 rounded-xl p-3">
                {info}
              </div>
            )}

            <button
              type="submit"
              disabled={submitting}
              className="w-full px-4 py-2.5 bg-blue-600 hover:bg-blue-500 text-white text-sm
                         font-semibold rounded-xl transition-colors shadow-lg shadow-blue-600/20
                         disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {submitting
                ? (mode === 'signup' ? 'Creating account…' : 'Signing in…')
                : (mode === 'signup' ? 'Create account' : 'Sign in')}
            </button>
          </form>
        </div>

        <p className="text-center text-xs text-slate-600 mt-6">
          By signing in you agree to keep being awesome.
        </p>
      </div>
    </div>
  );
}
