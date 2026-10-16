"use client";

import { useCallback, useEffect, useRef, useState } from "react";

export type Status =
  | "skipped" | "dismissed" | "failed"
  | "pending_approval" | "approved" | "applying"
  | "applied" | "screening" | "interview" | "offer" | "rejected" | "ghosted";

export type Application = {
  id: number;
  company: string;
  role: string;
  apply_target: string | null;
  apply_type: string | null;
  status: Status;
  skip_reason: string | null;
  location: string | null;
  source: string | null;
  platform: string;
  fit_score: number | null;
  fit_reason: string | null;
  has_resume: boolean;
  notes: string | null;
  created_at: string | null;
  updated_at: string | null;
  submitted_at: string | null;
  followup_at: string | null;
  resume_source: string | null;
  missing_questions?: string[];
  answers_used?: [string, string | string[], string][];
  jd_summary?: string | null;
  events?: { at: string; kind: string; message: string | null }[];
};

export type Overview = {
  counts: Partial<Record<Status, number>>;
  kpis: {
    applied_this_week: number; applied_last_week: number; submitted_total: number;
    response_rate: number | null; interviews: number; offers: number;
    avg_fit: number | null; minutes_saved: number; jobs_seen: number;
    resumes: { tailored: number; reused: number };
  };
  focus: { pending_approval: number; failed: number; needs_answers: number; failed_this_week: number;
           followups_due: number; in_flight: number };
  funnel: { stage: string; count: number }[];
  heatmap: { date: string; applied: number; found: number }[];
  recent: Application[];
  bot: { heartbeat: string | null; online: boolean; mode: "approval" | "auto" };
};

export type Insights = {
  skip_reasons: { reason: string; count: number }[];
  failure_reasons: { reason: string; count: number }[];
  platforms: { platform: string; found: number; applied?: number; failed?: number; responses?: number;
    success_rate: number | null; response_rate: number | null }[];
  fit_distribution: { bucket: string; count: number }[];
  weekly: { week: string; found?: number; applied?: number; failed?: number }[];
};

export type Settings = {
  apply_mode: "approval" | "auto";
  auto_approve_min_fit: number;
  min_fit: number;
  notify_skips: boolean;
  followup_days: number;
  daily_caps: Record<string, number>;
  bot_heartbeat?: string;
};

export type PlatformHealth = {
  platform: string;
  status: "connected" | "expired" | "missing" | "unknown";
  saved_at: string | null;
  expires_at: string | null;
  applied_today: number;
  daily_cap: number | null;
  queued: number;
  refresh_command: string;
};

export class ApiError extends Error {
  constructor(message: string, public status: number) { super(message); }
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`/api${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...init?.headers },
    });
  } catch {
    throw new ApiError("Can't reach the local API. Start it with: python -m src.api", 0);
  }
  if (!res.ok) {
    let detail = res.statusText;
    try { detail = (await res.json()).detail ?? detail; } catch {}
    if (res.status >= 500 && res.status < 600 && /ECONNREFUSED|Internal/i.test(detail || "")) {
      detail = "Can't reach the local API. Start it with: python -m src.api";
    }
    throw new ApiError(typeof detail === "string" ? detail : JSON.stringify(detail), res.status);
  }
  return res.json();
}

/** Tiny fetch-and-revalidate hook. Polls while the tab is visible. */
export function useApi<T>(path: string | null, { poll = 0 }: { poll?: number } = {}) {
  const [data, setData] = useState<T | undefined>(undefined);
  const [error, setError] = useState<ApiError | null>(null);
  const [loading, setLoading] = useState(true);
  const pathRef = useRef(path);
  pathRef.current = path;

  const reload = useCallback(async () => {
    const p = pathRef.current;
    if (!p) return;
    try {
      const d = await api<T>(p);
      if (pathRef.current === p) { setData(d); setError(null); }
    } catch (e) {
      if (pathRef.current === p) setError(e as ApiError);
    } finally {
      if (pathRef.current === p) setLoading(false);
    }
  }, []);

  useEffect(() => {
    setLoading(true);
    reload();
    if (!poll) return;
    const t = setInterval(() => { if (!document.hidden) reload(); }, poll);
    return () => clearInterval(t);
  }, [path, poll, reload]);

  return { data, error, loading, reload, setData };
}

// Broadcast so other mounted views (sidebar counts, overview) refresh after a mutation.
export const DATA_CHANGED = "jac:data-changed";
export function notifyChanged() {
  window.dispatchEvent(new Event(DATA_CHANGED));
}
export function useOnDataChanged(fn: () => void) {
  useEffect(() => {
    window.addEventListener(DATA_CHANGED, fn);
    return () => window.removeEventListener(DATA_CHANGED, fn);
  }, [fn]);
}

export type SavedAnswer = { id: number; question: string; answer: string; times_used: number; updated_at: string };
