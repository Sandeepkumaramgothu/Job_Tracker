// frontend/src/pages/Login.jsx

/**
 * Login / signup screen.
 *
 * Toggleable between Sign In and Sign Up modes for email + password.
 * Also offers Google OAuth as a single-click alternative.
 *
 * On successful signup with email confirmation enabled in Supabase, the user
 * gets a confirmation email and must click the link before they can sign in.
 * We surface that as a friendly message instead of a generic error.
 */

import { useState } from 'react';
import { useAuth } from '../hooks/useAuth';

export default function Login() {
  const { signUpWithEmail, signInWithEmail, signInWithGoogle } = useAuth();

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

  const handleGoogle = async () => {
    setError(null);
    setInfo(null);
    const { error: err } = await signInWithGoogle();
    if (err) setError(err.message);
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

          {/* Divider */}
          <div className="my-5 flex items-center gap-3 text-xs text-slate-500">
            <div className="flex-1 h-px bg-slate-800" />
            or
            <div className="flex-1 h-px bg-slate-800" />
          </div>

          {/* Google */}
          <button
            type="button"
            onClick={handleGoogle}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-white
                       hover:bg-slate-100 text-slate-900 text-sm font-semibold rounded-xl
                       transition-colors"
          >
            <svg className="w-4 h-4" viewBox="0 0 24 24" aria-hidden="true">
              <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
              <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.99.66-2.25 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
              <path fill="#FBBC05" d="M5.84 14.1c-.22-.66-.35-1.36-.35-2.1s.13-1.44.35-2.1V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l3.66-2.84z"/>
              <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84C6.71 7.31 9.14 5.38 12 5.38z"/>
            </svg>
            Continue with Google
          </button>
        </div>

        <p className="text-center text-xs text-slate-600 mt-6">
          By signing in you agree to keep being awesome.
        </p>
      </div>
    </div>
  );
}
