import { createContext, useContext, useMemo, useState, type ReactNode } from 'react';

interface AppContextValue {
  sessionId: string | null;
  setSessionId: (id: string) => void;
  devMode: boolean;
  setDevMode: (v: boolean) => void;
  lastDebug: Record<string, unknown>;
  setLastDebug: (d: Record<string, unknown>) => void;
}

const AppCtx = createContext<AppContextValue | null>(null);

export function AppProvider({ children }: { children: ReactNode }) {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [devMode, setDevMode] = useState(false);
  const [lastDebug, setLastDebug] = useState<Record<string, unknown>>({});

  const value = useMemo(
    () => ({ sessionId, setSessionId, devMode, setDevMode, lastDebug, setLastDebug }),
    [sessionId, devMode, lastDebug],
  );

  return <AppCtx.Provider value={value}>{children}</AppCtx.Provider>;
}

export function useApp() {
  const ctx = useContext(AppCtx);
  if (!ctx) throw new Error('useApp outside provider');
  return ctx;
}
