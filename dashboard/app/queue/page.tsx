"use client";

import { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Check, CheckCheck, ExternalLink, FileText, Inbox, MapPin, X } from "lucide-react";
import { api, notifyChanged, useApi, useOnDataChanged, type Application } from "@/lib/api";
import { ago, platformLabel } from "@/lib/format";
import { Button, EmptyState, ErrorState, FitMeter, PageHeader, Skeleton, cx, useToast } from "@/components/ui";

export default function QueuePage() {
  return <Suspense><Queue /></Suspense>;
}

function Queue() {
  const params = useSearchParams();
  const { data, error, reload, setData } = useApi<Application[]>("/applications?status=pending_approval", { poll: 20000 });
  useOnDataChanged(reload);
  const toast = useToast();
  const [selId, setSelId] = useState<number | null>(null);
  const [stamp, setStamp] = useState<{ id: number; kind: "approve" | "dismiss" } | null>(null);
  const [bulkMin, setBulkMin] = useState(70);

  const items = useMemo(() => data ?? [], [data]);
  const idx = Math.max(0, items.findIndex((a) => a.id === selId));
  const current = items[idx];

  useEffect(() => {
    const want = Number(params.get("id"));
    if (want && items.some((a) => a.id === want)) setSelId(want);
    else if (selId == null || !items.some((a) => a.id === selId)) setSelId(items[0]?.id ?? null);
  }, [items]); // eslint-disable-line react-hooks/exhaustive-deps

  const decide = useCallback(async (app: Application, kind: "approve" | "dismiss") => {
    const pos = items.findIndex((a) => a.id === app.id);
    setStamp({ id: app.id, kind });
    // Optimistic: drop it from the list and move to the next one after the stamp lands.
    setTimeout(() => {
      setData((list) => list?.filter((a) => a.id !== app.id));
      const next = items[pos + 1] ?? items[pos - 1];
      setSelId(next?.id ?? null);
      setStamp(null);
    }, 360);
    try {
      await api(`/applications/${app.id}/${kind}`, { method: "POST" });
      notifyChanged();
      toast({
        text: kind === "approve" ? `Sending to ${app.company}` : `Skipped ${app.company}`,
        undo: async () => {
          try {
            await api(`/applications/${app.id}`, { method: "PATCH", body: JSON.stringify({ status: "pending_approval" }) });
            reload();
            setSelId(app.id);
            notifyChanged();
          } catch (e) {
            toast({ text: (e as Error).message, tone: "bad" });
          }
        },
      });
    } catch (e) {
      toast({ text: (e as Error).message, tone: "bad" });
      reload();
    }
  }, [items, setData, toast, reload]);

  const bulkApprove = async () => {
    const ids = items.filter((a) => (a.fit_score ?? 0) >= bulkMin).map((a) => a.id);
    if (!ids.length) return;
    const r = await api<{ updated: number }>("/queue/bulk", { method: "POST", body: JSON.stringify({ ids, action: "approve" }) });
    toast({ text: `Sending ${r.updated} applications` });
    reload();
    notifyChanged();
  };

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement;
      if (t.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(t.tagName)) return;
      if (e.metaKey || e.ctrlKey || e.altKey || !current || stamp) return;
      const k = e.key.toLowerCase();
      if (k === "j" || e.key === "ArrowDown") { e.preventDefault(); setSelId(items[Math.min(idx + 1, items.length - 1)].id); }
      else if (k === "k" || e.key === "ArrowUp") { e.preventDefault(); setSelId(items[Math.max(idx - 1, 0)].id); }
      else if (k === "a" || k === "y") { e.preventDefault(); decide(current, "approve"); }
      else if (k === "s" || k === "x") { e.preventDefault(); decide(current, "dismiss"); }
      else if (k === "o" && current.apply_target?.startsWith("http")) window.open(current.apply_target, "_blank", "noopener");
      else if (k === "r" && current.has_resume) window.open(`/api/applications/${current.id}/resume`, "_blank");
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [current, idx, items, decide, stamp]);

  if (error && !data) return <ErrorState error={error} retry={reload} />;

  const bulkCount = items.filter((a) => (a.fit_score ?? 0) >= bulkMin).length;

  return (
    <div>
      <PageHeader
        title="Review queue"
        sub={data ? (items.length ? `${items.length} ${items.length === 1 ? "job" : "jobs"} ready. Resumes are already tailored. Nothing is sent until you say yes.` : "Nothing waiting right now.") : " "}
        actions={items.length > 1 && (
          <div className="flex items-center gap-2 rounded-[var(--radius-m)] border border-line-soft bg-surface p-1 pl-3 text-sm">
            <label htmlFor="bulkmin" className="text-dim">Fit at least</label>
            <select
              id="bulkmin"
              value={bulkMin}
              onChange={(e) => setBulkMin(Number(e.target.value))}
              className="h-8 rounded-md border border-line bg-raised px-1.5 text-sm"
            >
              {[50, 60, 70, 80, 90].map((n) => <option key={n} value={n}>{n}</option>)}
            </select>
            <Button size="sm" variant="outline" onClick={bulkApprove} disabled={!bulkCount}>
              <CheckCheck size={14} />Approve {bulkCount}
            </Button>
          </div>
        )}
      />

      {!data ? (
        <div className="grid gap-6 lg:grid-cols-[20rem_1fr]">
          <div className="space-y-2">{Array.from({ length: 6 }, (_, i) => <Skeleton key={i} className="h-16" />)}</div>
          <Skeleton className="h-[28rem]" />
        </div>
      ) : items.length === 0 ? (
        <div className="rounded-[var(--radius-l)] bg-surface shadow-[var(--shadow-tile)]">
          <EmptyState
            icon={<Inbox size={30} />}
            title="Inbox zero"
            body="New jobs that pass your fit check land here with a tailored resume, ready for a yes or no."
          />
        </div>
      ) : (
        <div className="grid gap-6 lg:grid-cols-[20rem_1fr]">
          <ul className="scroll-thin space-y-1 lg:sticky lg:top-6 lg:max-h-[calc(100dvh-10rem)] lg:overflow-y-auto lg:pr-1" aria-label="Jobs waiting for review">
            {items.map((a) => (
              <li key={a.id}>
                <button
                  onClick={() => setSelId(a.id)}
                  aria-current={a.id === current?.id}
                  className={cx(
                    "w-full rounded-[var(--radius-m)] border px-3.5 py-3 text-left transition-colors",
                    a.id === current?.id ? "border-line bg-surface" : "border-transparent hover:bg-surface/60",
                    stamp?.id === a.id && "opacity-40",
                  )}
                >
                  <span className="flex items-start justify-between gap-3">
                    <span className="min-w-0">
                      <span className="block truncate text-sm font-medium">{a.role}</span>
                      <span className="block truncate text-[13px] text-dim">{a.company}</span>
                    </span>
                    <FitMeter score={a.fit_score} />
                  </span>
                </button>
              </li>
            ))}
          </ul>

          {current && (
            <article key={current.id} className="pop relative overflow-hidden rounded-[var(--radius-l)] bg-surface shadow-[var(--shadow-tile)]" aria-label={`${current.role} at ${current.company}`}>
              {stamp?.id === current.id && <Stamp kind={stamp.kind} />}
              <Decision app={current} onDecide={decide} />
            </article>
          )}
        </div>
      )}
    </div>
  );
}

function Decision({ app, onDecide }: { app: Application; onDecide: (a: Application, k: "approve" | "dismiss") => void }) {
  const { data: full } = useApi<Application>(`/applications/${app.id}`);
  const jd = full?.jd_summary ?? "";
  const isUrl = app.apply_target?.startsWith("http");

  return (
    <div className="flex h-full flex-col">
      <div className="px-6 pt-6 pb-5 sm:px-8 sm:pt-8">
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-[13px] text-dim">
          <span>{platformLabel(app.platform)}</span>
          {app.location && <span className="inline-flex items-center gap-1"><MapPin size={13} />{app.location}</span>}
          <span>Found {ago(app.created_at)}</span>
        </div>
        <h2 className="mt-3 font-display text-[clamp(1.5rem,2.4vw,2rem)] leading-[1.12] font-semibold tracking-[-0.025em]">{app.role}</h2>
        <p className="mt-1 text-lg text-dim">{app.company}</p>

        <div className="mt-6 flex flex-wrap items-center gap-x-8 gap-y-4">
          <div>
            <p className="mb-1.5 text-xs text-faint">How well you fit</p>
            <FitMeter score={app.fit_score} size="lg" />
          </div>
          {app.fit_reason && <p className="max-w-md flex-1 text-sm leading-relaxed text-dim">{app.fit_reason}</p>}
        </div>
      </div>

      <div className="mx-6 border-t border-line-soft sm:mx-8" />

      <div className="flex-1 px-6 py-5 sm:px-8">
        <h3 className="mb-2 text-sm font-medium">About the role</h3>
        {full ? (
          jd ? (
            <div className="scroll-thin max-h-[22rem] overflow-y-auto pr-2 text-[14px] leading-[1.65] whitespace-pre-wrap text-dim">{jd}</div>
          ) : (
            <p className="text-sm text-faint">No description was captured for this post. Open it to read the full listing.</p>
          )
        ) : (
          <div className="space-y-2"><Skeleton className="h-4 w-full" /><Skeleton className="h-4 w-11/12" /><Skeleton className="h-4 w-4/5" /></div>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-2 border-t border-line-soft bg-raised/40 px-6 py-4 sm:px-8">
        <Button variant="primary" onClick={() => onDecide(app, "approve")}>
          <Check size={16} />Apply <kbd className="ml-1 border-accent-ink/20 bg-transparent text-accent-ink/70">A</kbd>
        </Button>
        <Button onClick={() => onDecide(app, "dismiss")}>
          <X size={16} />Skip <kbd className="ml-1">S</kbd>
        </Button>
        <span className="flex-1" />
        {app.has_resume && (
          <a href={`/api/applications/${app.id}/resume`} target="_blank" rel="noreferrer"
             title={app.resume_source ? `Reused the resume made for ${app.resume_source}` : "Tailored for this job"}>
            <Button variant="ghost" size="sm">
              <FileText size={14} />{app.resume_source ? "Reused resume" : "Tailored resume"} <kbd>R</kbd>
            </Button>
          </a>
        )}
        {isUrl && (
          <a href={app.apply_target!} target="_blank" rel="noreferrer noopener">
            <Button variant="ghost" size="sm"><ExternalLink size={14} />Posting <kbd>O</kbd></Button>
          </a>
        )}
        <span className="hidden text-xs text-faint xl:inline"><kbd>J</kbd> <kbd>K</kbd> to move</span>
      </div>
    </div>
  );
}

function Stamp({ kind }: { kind: "approve" | "dismiss" }) {
  const c = kind === "approve" ? "var(--st-good)" : "var(--st-muted)";
  return (
    <div className="pointer-events-none absolute inset-0 z-10 flex items-center justify-center bg-surface/40" aria-hidden>
      <span
        className="stamp rounded-[10px] border-[3px] px-5 py-2 font-display text-3xl font-bold tracking-[-0.01em]"
        style={{ color: c, borderColor: c }}
      >
        {kind === "approve" ? "Applying" : "Skipped"}
      </span>
    </div>
  );
}
