"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import {
  BarChart3, Inbox, KanbanSquare, LayoutDashboard, LifeBuoy, Moon, Search, Settings, Sun,
} from "lucide-react";
import { DATA_CHANGED, api, useApi, useOnDataChanged, type Application, type Overview } from "@/lib/api";
import { ago, platformLabel } from "@/lib/format";
import { ToastProvider, StatusPill, cx, useToast } from "./ui";

const NAV = [
  { href: "/", label: "Overview", icon: LayoutDashboard, key: "o" },
  { href: "/queue", label: "Review queue", icon: Inbox, key: "q", count: "pending_approval" as const },
  { href: "/applications", label: "Applications", icon: KanbanSquare, key: "a" },
  { href: "/attention", label: "Needs you", icon: LifeBuoy, key: "n", count: "failed" as const },
  { href: "/insights", label: "Insights", icon: BarChart3, key: "i" },
  { href: "/settings", label: "Settings", icon: Settings, key: "s" },
];

export function Shell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { data, reload } = useApi<Overview>("/overview", { poll: 15000 });
  useOnDataChanged(reload);
  const [palette, setPalette] = useState(false);

  // g then a letter jumps between views; ⌘K / Ctrl+K / "/" opens the palette.
  useEffect(() => {
    let gAt = 0;
    const onKey = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement;
      const typing = t.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(t.tagName);
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setPalette((p) => !p);
        return;
      }
      if (typing || e.metaKey || e.ctrlKey || e.altKey) return;
      if (e.key === "/") { e.preventDefault(); setPalette(true); return; }
      if (e.key === "g") { gAt = Date.now(); return; }
      if (Date.now() - gAt < 1200) {
        const item = NAV.find((n) => n.key === e.key);
        if (item) { e.preventDefault(); router.push(item.href); }
        gAt = 0;
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [router]);

  return (
    <ToastProvider>
      <div className="min-h-dvh">
        <header className="sticky top-0 z-30 px-3 pt-3 sm:px-6">
          <div className="mx-auto flex max-w-[1320px] items-center gap-3 rounded-full bg-surface/85 py-1.5 pr-1.5 pl-4 shadow-[var(--shadow-tile)] backdrop-blur-md">
            <Link href="/" className="flex shrink-0 items-center gap-2" aria-label="Pursuit home">
              <Logo />
              <span className="hidden font-display text-[16px] font-semibold tracking-[-0.03em] lg:inline">Pursuit</span>
            </Link>
            <nav aria-label="Main" className="scroll-thin mx-auto flex min-w-0 items-center gap-0.5 overflow-x-auto">
              {NAV.map((n) => {
                const active = n.href === "/" ? pathname === "/" : pathname.startsWith(n.href);
                // "Needs you" counts what you can act on now, not months-old failures.
                const count = !n.count ? 0 : n.count === "failed"
                  ? (data?.focus.needs_answers ?? 0) + (data?.focus.failed_this_week ?? 0)
                  : data?.counts[n.count] ?? 0;
                return (
                  <Link
                    key={n.href}
                    href={n.href}
                    aria-current={active ? "page" : undefined}
                    className={cx(
                      "flex h-9 shrink-0 items-center gap-2 rounded-full px-3.5 text-[13.5px] transition-colors",
                      active ? "bg-tile font-medium text-tile-ink" : "text-dim hover:bg-raised hover:text-ink",
                    )}
                  >
                    <n.icon size={15} className="sm:hidden" aria-hidden />
                    <span className="hidden sm:inline">{n.label}</span>
                    {count > 0 && (
                      <span
                        className={cx(
                          "rounded-full px-1.5 text-[11px] leading-[18px] font-semibold tabular-nums",
                          n.count === "pending_approval" ? "bg-accent text-accent-ink" : active ? "bg-white/15" : "bg-raised text-dim",
                        )}
                      >
                        {count}
                      </span>
                    )}
                  </Link>
                );
              })}
            </nav>
            <div className="flex shrink-0 items-center gap-1">
              <button
                onClick={() => setPalette(true)}
                className="hidden h-9 items-center gap-2 rounded-full px-3 text-[13px] text-faint hover:bg-raised hover:text-dim md:flex"
              >
                <Search size={14} /> <kbd>⌘K</kbd>
              </button>
              <BotStatus bot={data?.bot} />
              <ThemeToggle />
            </div>
          </div>
        </header>
        <main className="mx-auto w-full max-w-[1320px] px-4 pt-8 pb-16 sm:px-6 sm:pt-10">{children}</main>
      </div>
      {palette && <CommandPalette onClose={() => setPalette(false)} />}
    </ToastProvider>
  );
}

function Logo() {
  // The Pursuit mark: a P whose bowl holds a yellow point, the thing you're going after.
  return (
    <svg width="28" height="28" viewBox="0 0 32 32" aria-hidden className="shrink-0">
      <rect x="0.5" y="0.5" width="31" height="31" rx="8.5" fill="#131312" stroke="rgba(255,255,255,0.14)" />
      <path d="M11.5 24.5V8h6a6.25 6.25 0 0 1 0 12.5h-6" fill="none" stroke="#fbfaf4" strokeWidth="3.2" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="17.4" cy="14.25" r="2.5" fill="var(--accent)" />
    </svg>
  );
}

function BotStatus({ bot }: { bot?: Overview["bot"] }) {
  const toast = useToast();
  const [busy, setBusy] = useState(false);
  if (!bot) return null;
  const running = bot.online;
  const toggle = async () => {
    setBusy(true);
    try {
      await api(running ? "/bot/stop" : "/bot/start", { method: "POST" });
      toast({ text: running ? "Bot paused. Nothing will be found or sent until you start it." : "Bot starting. It'll show Running in a few seconds." });
      setTimeout(() => window.dispatchEvent(new Event(DATA_CHANGED)), running ? 500 : 8000);
    } catch (e) {
      toast({ text: (e as Error).message, tone: "bad" });
    }
    setBusy(false);
  };
  const label = running ? (bot.mode === "auto" ? "Running, applying automatically" : "Running, asks before applying")
    : bot.heartbeat ? `Paused, last seen ${ago(bot.heartbeat)}` : "Paused";
  return (
    <button
      onClick={toggle}
      disabled={busy}
      title={`${label}. Click to ${running ? "pause" : "start"}.`}
      className="group flex h-9 items-center gap-2 rounded-full px-3 text-[13px] text-dim hover:bg-raised hover:text-ink disabled:opacity-60"
    >
      <span
        className={cx("size-2 rounded-full", running && "animate-pulse")}
        style={{ background: running ? "var(--st-good)" : "var(--st-muted)" }}
        aria-hidden
      />
      <span className="hidden xl:inline group-hover:hidden">{busy ? "…" : running ? "Running" : "Paused"}</span>
      <span className="hidden font-medium group-hover:inline">{running ? "Pause" : "Start"}</span>
      <span className="sr-only">{label}</span>
    </button>
  );
}

function ThemeToggle() {
  const [theme, setTheme] = useState<"light" | "dark" | null>(null);
  useEffect(() => {
    setTheme((document.documentElement.dataset.theme as "light" | "dark") ?? "light");
  }, []);
  const flip = () => {
    const next = theme === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    try { localStorage.setItem("theme", next); } catch {}
    setTheme(next);
  };
  return (
    <button
      onClick={flip}
      className="grid size-9 place-items-center rounded-full bg-raised text-dim hover:text-ink"
      aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} theme`}
    >
      {theme === "dark" ? <Sun size={15} /> : <Moon size={15} />}
    </button>
  );
}

/* ── ⌘K palette ──────────────────────────────────────────────────────────── */
type Cmd = { id: string; label: string; hint?: ReactNode; run: () => void; group: string };

function CommandPalette({ onClose }: { onClose: () => void }) {
  const router = useRouter();
  const [q, setQ] = useState("");
  const [sel, setSel] = useState(0);
  const [results, setResults] = useState<Application[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLUListElement>(null);

  useEffect(() => { inputRef.current?.focus(); }, []);
  useEffect(() => {
    if (q.trim().length < 2) { setResults([]); return; }
    const t = setTimeout(() => {
      api<Application[]>(`/applications?q=${encodeURIComponent(q.trim())}&limit=8`).then(setResults).catch(() => {});
    }, 140);
    return () => clearTimeout(t);
  }, [q]);

  const go = useCallback((href: string) => { router.push(href); onClose(); }, [router, onClose]);

  const cmds: Cmd[] = useMemo(() => {
    const nav: Cmd[] = NAV.map((n) => ({
      id: n.href, group: "Go to", label: n.label, hint: <><kbd>g</kbd> <kbd>{n.key}</kbd></>, run: () => go(n.href),
    }));
    const actions: Cmd[] = [
      { id: "theme", group: "Actions", label: "Switch theme", run: () => {
        const next = document.documentElement.dataset.theme === "light" ? "dark" : "light";
        document.documentElement.dataset.theme = next;
        try { localStorage.setItem("theme", next); } catch {}
        onClose();
      } },
      { id: "export", group: "Actions", label: "Export applications as CSV", run: () => { exportCsv(); onClose(); } },
    ];
    const ql = q.toLowerCase();
    const filtered = [...nav, ...actions].filter((c) => !ql || c.label.toLowerCase().includes(ql));
    const apps: Cmd[] = results.map((a) => ({
      id: `app-${a.id}`, group: "Applications", label: `${a.role} · ${a.company}`,
      hint: <StatusPill status={a.status} />,
      run: () => go(a.status === "pending_approval" ? `/queue?id=${a.id}` : `/applications?id=${a.id}`),
    }));
    return [...apps, ...filtered];
  }, [q, results, go, onClose]);

  useEffect(() => { setSel(0); }, [q, results.length]);
  useEffect(() => {
    listRef.current?.querySelector(`[data-idx="${sel}"]`)?.scrollIntoView({ block: "nearest" });
  }, [sel]);

  const onKey = (e: React.KeyboardEvent) => {
    if (e.key === "Escape") onClose();
    else if (e.key === "ArrowDown") { e.preventDefault(); setSel((s) => Math.min(s + 1, cmds.length - 1)); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setSel((s) => Math.max(s - 1, 0)); }
    else if (e.key === "Enter") { e.preventDefault(); cmds[sel]?.run(); }
  };

  let lastGroup = "";
  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center bg-black/45 px-4 pt-[12vh]" onClick={onClose}>
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Command palette"
        className="pop w-full max-w-lg overflow-hidden rounded-[var(--radius-l)] bg-surface shadow-[var(--shadow-pop)]"
        onClick={(e) => e.stopPropagation()}
        onKeyDown={onKey}
      >
        <div className="flex items-center gap-3 border-b border-line-soft px-4">
          <Search size={16} className="text-faint" />
          <input
            ref={inputRef}
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search companies, roles, or type a command"
            className="h-12 flex-1 bg-transparent text-[15px] outline-none placeholder:text-faint"
            role="combobox"
            aria-expanded="true"
            aria-controls="palette-list"
            aria-activedescendant={cmds[sel] ? `cmd-${cmds[sel].id}` : undefined}
          />
          <kbd>esc</kbd>
        </div>
        <ul ref={listRef} id="palette-list" role="listbox" className="scroll-thin max-h-[52vh] overflow-y-auto p-2">
          {cmds.length === 0 && <li className="px-3 py-8 text-center text-sm text-faint">No matches for “{q}”</li>}
          {cmds.map((c, i) => {
            const header = c.group !== lastGroup ? (lastGroup = c.group) : null;
            return (
              <li key={c.id} role="presentation">
                {header && <div className="px-3 pt-2.5 pb-1 text-xs text-faint">{header}</div>}
                <div
                  id={`cmd-${c.id}`}
                  role="option"
                  aria-selected={i === sel}
                  data-idx={i}
                  onMouseMove={() => setSel(i)}
                  onClick={c.run}
                  className={cx(
                    "flex cursor-pointer items-center justify-between gap-3 rounded-[var(--radius-s)] px-3 py-2 text-sm",
                    i === sel ? "bg-raised text-ink" : "text-dim",
                  )}
                >
                  <span className="truncate">{c.label}</span>
                  {c.hint && <span className="shrink-0 text-xs">{c.hint}</span>}
                </div>
              </li>
            );
          })}
        </ul>
      </div>
    </div>
  );
}

export async function exportCsv() {
  const rows = await api<Application[]>("/applications?limit=2000");
  const cols: (keyof Application)[] = [
    "id", "company", "role", "status", "platform", "location", "fit_score", "apply_target",
    "skip_reason", "created_at", "submitted_at", "notes",
  ];
  const esc = (v: unknown) => {
    const s = v == null ? "" : String(v);
    // Leading =,+,-,@ would run as a formula in Excel/Sheets.
    const safe = /^[=+\-@]/.test(s) ? `'${s}` : s;
    return /[",\n]/.test(safe) ? `"${safe.replace(/"/g, '""')}"` : safe;
  };
  const csv = [cols.join(","), ...rows.map((r) => cols.map((c) => esc(c === "platform" ? platformLabel(r.platform) : r[c])).join(","))].join("\n");
  const url = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
  const a = Object.assign(document.createElement("a"), { href: url, download: `applications-${new Date().toISOString().slice(0, 10)}.csv` });
  a.click();
  URL.revokeObjectURL(url);
}
