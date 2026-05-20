"use client";

// Client-side auth context. Subscribes to Supabase's auth state once
// in the root layout and exposes the current user + session to every
// component below via ``useUser()`` / ``useSession()``.
//
// We do NOT call ``supabase.auth.getUser()`` on every render - the
// middleware already validated the session and refreshed cookies.
// This provider just mirrors the result into React state so the UI
// can react to login / logout in the same tab.

import { createContext, useContext, useEffect, useState } from "react";
import type { ReactNode } from "react";
import type { Session, User } from "@supabase/supabase-js";
import { supabase } from "@/lib/supabase";

type AuthContextValue = {
  user: User | null;
  session: Session | null;
  loading: boolean;
  signOut: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

type Props = {
  children: ReactNode;
  initialSession: Session | null;
};

export function AuthProvider({ children, initialSession }: Props) {
  const [session, setSession] = useState<Session | null>(initialSession);
  const [loading, setLoading] = useState(!initialSession);

  useEffect(() => {
    // Pull the current session once on mount in case the initialSession
    // prop was stale (e.g. token rotated during navigation).
    let cancelled = false;
    supabase.auth.getSession().then(({ data }) => {
      if (cancelled) return;
      setSession(data.session ?? null);
      setLoading(false);
    });

    const { data: subscription } = supabase.auth.onAuthStateChange((_event, newSession) => {
      setSession(newSession);
      setLoading(false);
    });

    return () => {
      cancelled = true;
      subscription.subscription.unsubscribe();
    };
  }, []);

  const value: AuthContextValue = {
    user: session?.user ?? null,
    session,
    loading,
    signOut: async () => {
      await supabase.auth.signOut();
    },
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth() must be called inside <AuthProvider>");
  }
  return ctx;
}

export function useUser(): User | null {
  return useAuth().user;
}

export function useSession(): Session | null {
  return useAuth().session;
}
