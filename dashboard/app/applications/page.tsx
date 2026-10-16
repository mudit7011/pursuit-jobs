"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Download, KanbanSquare, Rows3, Search } from "lucide-react";
import { api, notifyChanged, useApi, useOnDataChanged, type Application, type Status } from "@/lib/api";
import { PIPELINE, STATUS_LABEL, ago, platformLabel } from "@/lib/format";
import { ApplicationDrawer } from "@/components/app-drawer";
import { exportCsv } from "@/components/shell";
import { Button, EmptyState, ErrorState, FitMeter, PageHeader, Skeleton, StatusPill, cx, toneColor, useToast } from "@/components/ui";

type View = "board" | "table";

export default function ApplicationsPage() {
  return <Suspense><Applications /></Suspense>;
}

function Applications() {
  const params = useSearchParams();
  const router = useRouter();
  const toast = useToast();
  const { data, error, reload, setData } = useApi<Application[]>("/applications?limit=2000", { poll: 30000 });
  const { data: followups } = useApi<Application[]>("/followups");
  useOnDataChanged(reload);

  const [view, setView] = useState<View>("board");
  const [q, setQ] = useState("");
  const [platform, setPlatform] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("");
  const followupOnly = params.get("filter") === "followup";
  const openId = Number(params.get("id")) || null;

  useEffect(() => {
    try { const v = localStorage.getItem("apps-view"); if (v === "table" || v === "board") setView(v); } catch {}
  }, []);
  const switchView = (v: View) => { setView(v); try { localStorage.setItem("apps-view", v); } catch {} };

  const setOpen = (id: number | null) => {
    const sp = new URLSearchParams(params.toString());
    if (id) sp.set("id", String(id)); else sp.delete("id");
    router.replace(`/applications${sp.size ? `?${sp}` : ""}`, { scroll: false });
  };

  const followIds = useMemo(() => new Set(followups?.map((f) => f.id)), [followups]);
  const platforms = useMemo(() => [...new Set((data ?? []).map((a) => a.platform))].sort(), [data]);

  const filtered = useMemo(() => {
    const ql = q.trim().toLowerCase();
    return (data ?? []).filter((a) =>
      (!ql || `${a.company} ${a.role} ${a.location ?? ""}`.toLowerCase().includes(ql)) &&
      (!platform || a.platform === platform) &&
      (!statusFilter || a.status === statusFilter) &&
      (!followupOnly || followIds.has(a.id)),
    );
  }, [data, q, platform, statusFilter, followupOnly, followIds]);

  const move = async (id: number, status: Status) => {
    const before = data?.find((a) => a.id === id);
    if (!before || before.status === status) return;
    setData((list) => list?.map((a) => (a.id === id ? { ...a, status } : a)));
    try {
      await api(`/applications/${id}`, { method: "PATCH", body: JSON.stringify({ status }) });
      notifyChanged();
      toast({
        text: status === "offer" ? `An offer from ${before.company}. Well earned.` : `${before.company} moved to ${STATUS_LABEL[status]}`,
        undo: async () => {
          await api(`/applications/${id}`, { method: "PATCH", body: JSON.stringify({ status: before.status }) });
          reload();
        },
      });
    } catch (e) {
      toast({ text: (e as Error).message, tone: "bad" });
      reload();
    }
  };

  if (error && !data) return <ErrorState error={error} retry={reload} />;

  return (
    <div>
      <PageHeader
        title={followupOnly ? "Follow-ups due" : "Applications"}
        sub={followupOnly
          ? "Applied over a week ago with no update. A short, polite nudge often gets a reply."
          : "Everything you've sent and where it stands. Drag a card when something changes."}
        actions={
          <>
            <Button size="sm" variant="ghost" onClick={() => exportCsv()}><Download size={14} />Export CSV</Button>
            <div className="flex rounded-[var(--radius-s)] border border-line p-0.5" role="tablist" aria-label="View">
              {(["board", "table"] as View[]).map((v) => (
                <button
                  key={v}
                  role="tab"
                  aria-selected={view === v}
                  onClick={() => switchView(v)}
                  className={cx("flex h-7 items-center gap-1.5 rounded-[4px] px-2.5 text-[13px]", view === v ? "bg-raised text-ink" : "text-dim")}
                >
                  {v === "board" ? <KanbanSquare size={14} /> : <Rows3 size={14} />}
                  {v === "board" ? "Board" : "Table"}
                </button>
              ))}
            </div>
          </>
        }
      />

      <div className="mb-5 flex flex-wrap items-center gap-2">
        <div className="relative">
          <Search size={15} className="absolute top-1/2 left-2.5 -translate-y-1/2 text-faint" />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Filter by company or role"
            aria-label="Filter by company or role"
            className="h-9 w-64 rounded-[var(--radius-s)] border border-line bg-surface pr-3 pl-8 text-sm outline-none placeholder:text-faint focus:border-[var(--dim)]"
          />
        </div>
        <select value={platform} onChange={(e) => setPlatform(e.target.value)} aria-label="Platform"
                className="h-9 rounded-[var(--radius-s)] border border-line bg-surface px-2 text-sm">
          <option value="">All platforms</option>
          {platforms.map((p) => <option key={p} value={p}>{platformLabel(p)}</option>)}
        </select>
        {view === "table" && (
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} aria-label="Status"
                  className="h-9 rounded-[var(--radius-s)] border border-line bg-surface px-2 text-sm">
            <option value="">Every status</option>
            {(Object.keys(STATUS_LABEL) as Status[]).map((s) => <option key={s} value={s}>{STATUS_LABEL[s]}</option>)}
          </select>
        )}
        {followupOnly && (
          <Button size="sm" variant="ghost" onClick={() => router.replace("/applications")}>Show all</Button>
        )}
      </div>

      {!data ? (
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-6">
          {Array.from({ length: 6 }, (_, i) => <Skeleton key={i} className="h-80" />)}
        </div>
      ) : view === "board" ? (
        <Board items={filtered} onMove={move} onOpen={setOpen} followIds={followIds} />
      ) : (
        <Table items={filtered} onOpen={setOpen} />
      )}

      <ApplicationDrawer id={openId} onClose={() => setOpen(null)} />
    </div>
  );
}

function Board({ items, onMove, onOpen, followIds }: {
  items: Application[]; onMove: (id: number, s: Status) => void; onOpen: (id: number) => void; followIds: Set<number>;
}) {
  const [over, setOver] = useState<Status | null>(null);
  const [dragging, setDragging] = useState<number | null>(null);
  const cols = PIPELINE.map((s) => ({ status: s, items: items.filter((a) => a.status === s) }));
  const total = cols.reduce((n, c) => n + c.items.length, 0);

  if (total === 0) {
    return (
      <div className="rounded-[var(--radius-l)] bg-surface shadow-[var(--shadow-tile)]">
        <EmptyState title="No sent applications match" body="Approve a few jobs from the review queue and they'll show up here as they go out." />
      </div>
    );
  }

  return (
    <div className="scroll-thin -mx-4 overflow-x-auto px-4 pb-3 sm:-mx-8 sm:px-8">
      <div className="grid min-w-[1080px] grid-cols-6 gap-3">
        {cols.map((c) => (
          <section
            key={c.status}
            aria-label={STATUS_LABEL[c.status]}
            onDragOver={(e) => { e.preventDefault(); setOver(c.status); }}
            onDragLeave={() => setOver((o) => (o === c.status ? null : o))}
            onDrop={(e) => {
              e.preventDefault();
              setOver(null);
              const id = Number(e.dataTransfer.getData("text/plain"));
              if (id) onMove(id, c.status);
            }}
            className={cx(
              "flex min-h-[24rem] flex-col rounded-[var(--radius-m)] border p-2 transition-colors",
              over === c.status ? "border-[var(--dim)] bg-raised/60" : "border-line-soft bg-surface/50",
            )}
          >
            <header className="flex items-center gap-2 px-1.5 pt-1 pb-2.5 text-[13px]">
              <span className="size-2 rounded-full" style={{ background: toneColor(c.status) }} />
              <span className="font-medium">{STATUS_LABEL[c.status]}</span>
              <span className="ml-auto text-faint tabular-nums">{c.items.length}</span>
            </header>
            <ul className="scroll-thin flex max-h-[62vh] flex-col gap-2 overflow-y-auto">
              {c.items.map((a) => (
                <li
                  key={a.id}
                  draggable
                  onDragStart={(e) => { e.dataTransfer.setData("text/plain", String(a.id)); e.dataTransfer.effectAllowed = "move"; setDragging(a.id); }}
                  onDragEnd={() => setDragging(null)}
                  className={cx(
                    "cursor-grab rounded-[var(--radius-s)] border border-line-soft bg-surface transition-[transform,box-shadow,opacity] duration-150 hover:-translate-y-px hover:shadow-[0_6px_18px_-8px_rgba(0,0,0,0.4)] active:cursor-grabbing",
                    dragging === a.id && "opacity-40",
                  )}
                >
                  <button onClick={() => onOpen(a.id)} className="w-full p-3 text-left">
                    <span className="block text-[13px] leading-snug font-medium">{a.role}</span>
                    <span className="mt-0.5 block truncate text-xs text-dim">{a.company}</span>
                    <span className="mt-2.5 flex items-center justify-between gap-2 text-[11px] text-faint">
                      <span>{platformLabel(a.platform)}</span>
                      {followIds.has(a.id)
                        ? <span style={{ color: "var(--st-warn)" }}>Follow up</span>
                        : <span>{ago(a.submitted_at ?? a.updated_at)}</span>}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </section>
        ))}
      </div>
    </div>
  );
}

const PAGE = 50;

function Table({ items, onOpen }: { items: Application[]; onOpen: (id: number) => void }) {
  const [page, setPage] = useState(0);
  useEffect(() => setPage(0), [items.length]);
  if (!items.length) {
    return (
      <div className="rounded-[var(--radius-l)] bg-surface shadow-[var(--shadow-tile)]">
        <EmptyState title="Nothing matches these filters" body="Try clearing the search or picking every status." />
      </div>
    );
  }
  const rows = items.slice(page * PAGE, page * PAGE + PAGE);
  const pages = Math.ceil(items.length / PAGE);
  return (
    <div className="overflow-hidden rounded-[var(--radius-l)] bg-surface shadow-[var(--shadow-tile)]">
      <div className="scroll-thin overflow-x-auto">
        <table className="w-full min-w-[760px] text-sm">
          <thead>
            <tr className="border-b border-line-soft text-left text-xs text-faint">
              <th className="px-5 py-3 font-normal">Role</th>
              <th className="px-3 py-3 font-normal">Platform</th>
              <th className="px-3 py-3 font-normal">Fit</th>
              <th className="px-3 py-3 font-normal">Status</th>
              <th className="px-5 py-3 text-right font-normal">Updated</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line-soft">
            {rows.map((a) => (
              <tr key={a.id} className="cursor-pointer hover:bg-raised/50" onClick={() => onOpen(a.id)}>
                <td className="max-w-[22rem] px-5 py-2.5">
                  <button className="block w-full text-left" onClick={(e) => { e.stopPropagation(); onOpen(a.id); }}>
                    <span className="block truncate font-medium">{a.role}</span>
                    <span className="block truncate text-[13px] text-dim">{a.company}</span>
                  </button>
                </td>
                <td className="px-3 py-2.5 text-dim">{platformLabel(a.platform)}</td>
                <td className="px-3 py-2.5"><FitMeter score={a.fit_score} /></td>
                <td className="px-3 py-2.5">
                  <StatusPill status={a.status} />
                  {a.status === "skipped" && a.skip_reason && (
                    <span className="mt-0.5 block max-w-[16rem] truncate text-xs text-faint" title={a.skip_reason}>{a.skip_reason}</span>
                  )}
                </td>
                <td className="px-5 py-2.5 text-right text-xs text-faint">{ago(a.updated_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {pages > 1 && (
        <div className="flex items-center justify-between border-t border-line-soft px-5 py-2.5 text-xs text-dim">
          <span>{page * PAGE + 1}–{Math.min(items.length, (page + 1) * PAGE)} of {items.length}</span>
          <div className="flex gap-1">
            <Button size="sm" variant="ghost" disabled={page === 0} onClick={() => setPage(page - 1)}>Previous</Button>
            <Button size="sm" variant="ghost" disabled={page >= pages - 1} onClick={() => setPage(page + 1)}>Next</Button>
          </div>
        </div>
      )}
    </div>
  );
}
