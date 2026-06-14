// frontend/src/hooks/useAuth.js

/**
 * Auth context + hook.
 *
 * Wraps the Supabase auth lifecycle:
 *   - On mount, restore any existing session from localStorage
 *   - Subscribe to onAuthStateChange so signin/signout reflect immediately
 *   - Expose signUp / signInWithPassword / signInWithGoogle / signOut
 *
 * Consumers:
 *   const { session, user, loading, signIn, signOut, ... } = useAuth();
 */

import { createContext, useContext, useEffect, useState } from 'react';
import { supabase } from '../lib/supabase';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;

    supabase.auth.getSession().then(({ data }) => {
      if (!mounted) return;
      setSession(data.session);
      setLoading(false);
    });

    const { data: sub } = supabase.auth.onAuthStateChange((_event, next) => {
      setSession(next);
    });

    return () => {
      mounted = false;
      sub.subscription.unsubscribe();
    };
  }, []);

  const signUpWithEmail = (email, password) =>
    supabase.auth.signUp({ email, password });

  const signInWithEmail = (email, password) =>
    supabase.auth.signInWithPassword({ email, password });

  const signOut = () => supabase.auth.signOut();

  const value = {
    session,
    user: session?.user ?? null,
    loading,
    signUpWithEmail,
    signInWithEmail,
    signOut,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth() {
  const ctx = useContext(AuthContext);
  if (ctx === null) {
    throw new Error('useAuth must be used inside <AuthProvider>.');
  }
  return ctx;
}
