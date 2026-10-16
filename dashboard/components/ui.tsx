"use client";

import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import { X } from "lucide-react";
import type { Status } from "@/lib/api";
import { STATUS_LABEL, STATUS_TONE } from "@/lib/format";

export function cx(...c: (string | false | null | undefined)[]) {
  return c.filter(Boolean).join(" ");
}

const TONE_VAR: Record<string, string> = {
  accent: "var(--st-accent)", info: "var(--st-info)", teal: "var(--st-teal)", good: "var(--st-good)",
  warn: "var(--st-warn)", bad: "var(--st-bad)", muted: "var(--st-muted)",
};
export const toneColor = (s: Status) => TONE_VAR[STATUS_TONE[s]];

export function StatusPill({ status, className }: { status: Status; className?: string }) {
  const c = toneColor(status);
  return (
    <span
      className={cx("inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-medium", className)}
      style={{ color: c, background: `color-mix(in srgb, ${c} 14%, transparent)` }}
    >
      <span
        className={cx("size-1.5 rounded-full", status === "applying" && "animate-pulse")}
        style={{ background: c }}
        aria-hidden
      />
      {STATUS_LABEL[status]}
    </span>
  );
}

/** Fit score as a short segmented meter: easier to compare at a glance than a ring. */
export function FitMeter({ score, size = "sm" }: { score: number | null; size?: "sm" | "lg" }) {
  if (score == null) return <span className="text-xs text-faint">No score</span>;
  const tone = score >= 75 ? "var(--st-good)" : score >= 55 ? "var(--st-accent)" : "var(--st-warn)";
  const segs = 10;
  const filled = Math.round(score / 10);
  return (
    <span className="inline-flex items-center gap-2" aria-label={`Fit ${score} out of 100`} role="img">
      <span className={cx("inline-flex", size === "lg" ? "gap-[3px]" : "gap-[2px]")} aria-hidden>
        {Array.from({ length: segs }, (_, i) => (
          <span
            key={i}
            className={cx(size === "lg" ? "h-3.5 w-2" : "h-2.5 w-1", "rounded-[1px]")}
            style={{ background: i < filled ? tone : "var(--line)" }}
          />
        ))}
      </span>
      <span className={cx("font-medium tabular-nums", size === "lg" ? "text-base" : "text-xs")} style={{ color: tone }}>
        {score}
      </span>
    </span>
  );
}

type BtnProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "ghost" | "outline" | "danger";
  size?: "sm" | "md";
};
export function Button({ variant = "outline", size = "md", className, ...p }: BtnProps) {
  return (
    <button
      {...p}
      className={cx(
        "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-[var(--radius-s)] font-medium",
        "transition-[background,color,border-color,transform] duration-150 active:translate-y-px",
        "disabled:pointer-events-none disabled:opacity-45",
        size === "sm" ? "h-8 px-2.5 text-[13px]" : "h-9 px-3.5 text-sm",
        variant === "primary" && "bg-accent text-accent-ink hover:brightness-105",
        variant === "outline" && "border border-line bg-surface text-ink hover:bg-raised",
        variant === "ghost" && "text-dim hover:bg-raised hover:text-ink",
        variant === "danger" && "border border-line text-bad hover:bg-[color-mix(in_srgb,var(--st-bad)_10%,transparent)]",
        className,
      )}
    />
  );
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={cx("skeleton", className)} aria-hidden />;
}

export function Panel({ title, action, children, className }: {
  title?: ReactNode; action?: ReactNode; children: ReactNode; className?: string;
}) {
  return (
    <section className={cx("rounded-[var(--radius-l)] bg-surface shadow-[var(--shadow-tile)]", className)}>
      {title && (
        <header className="flex items-center justify-between gap-3 px-5 pt-5 pb-2">
          <h2 className="font-display text-[17px] font-semibold tracking-[-0.02em]">{title}</h2>
          {action}
        </header>
      )}
      {children}
    </section>
  );
}

export function EmptyState({ icon, title, body, action }: {
  icon?: ReactNode; title: string; body?: ReactNode; action?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center px-6 py-14 text-center">
      {icon && <div className="mb-4 text-faint">{icon}</div>}
      <p className="font-display text-lg font-semibold">{title}</p>
      {body && <p className="mt-1.5 max-w-sm text-sm text-dim">{body}</p>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}

export function ErrorState({ error, retry }: { error: Error; retry?: () => void }) {
  return (
    <div role="alert" className="rounded-[var(--radius-m)] border border-line bg-surface px-5 py-4 text-sm">
      <p className="font-medium text-bad">Couldn&apos;t load this</p>
      <p className="mt-1 text-dim">{error.message}</p>
      {retry && <Button size="sm" className="mt-3" onClick={retry}>Try again</Button>}
    </div>
  );
}

export function PageHeader({ title, sub, actions }: { title: ReactNode; sub?: ReactNode; actions?: ReactNode }) {
  return (
    <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="font-display text-[clamp(2rem,3.4vw,2.9rem)] leading-[1.02] font-semibold tracking-[-0.04em]">{title}</h1>
        {sub && <p className="mt-1 text-sm text-dim">{sub}</p>}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  );
}

/* ── Drawer ──────────────────────────────────────────────────────────────── */
export function Drawer({ open, onClose, children, label }: {
  open: boolean; onClose: () => void; children: ReactNode; label: string;
}) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const prev = document.activeElement as HTMLElement | null;
    ref.current?.focus();
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") { e.stopPropagation(); onClose(); } };
    window.addEventListener("keydown", onKey, true);
    return () => { window.removeEventListener("keydown", onKey, true); prev?.focus(); };
  }, [open, onClose]);
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-40">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} aria-hidden />
      <div
        ref={ref}
        tabIndex={-1}
        role="dialog"
        aria-modal="true"
        aria-label={label}
        className="slide-in scroll-thin absolute inset-y-0 right-0 w-full max-w-xl overflow-y-auto border-l border-line bg-surface shadow-[var(--shadow-pop)] outline-none"
      >
        <button
          onClick={onClose}
          aria-label="Close"
          className="absolute top-4 right-4 rounded-md p-1.5 text-dim hover:bg-raised hover:text-ink"
        >
          <X size={18} />
        </button>
        {children}
      </div>
    </div>
  );
}

/* ── Toasts with undo ────────────────────────────────────────────────────── */
type Toast = { id: number; text: string; undo?: () => void; tone?: "good" | "bad" };
const ToastCtx = createContext<(t: Omit<Toast, "id">) => void>(() => {});
export const useToast = () => useContext(ToastCtx);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const push = useCallback((t: Omit<Toast, "id">) => {
    const id = Date.now() + Math.random();
    setToasts((ts) => [...ts.slice(-2), { ...t, id }]);
    setTimeout(() => setToasts((ts) => ts.filter((x) => x.id !== id)), t.undo ? 6000 : 3500);
  }, []);
  return (
    <ToastCtx.Provider value={push}>
      {children}
      <div className="pointer-events-none fixed bottom-5 left-1/2 z-50 flex -translate-x-1/2 flex-col items-center gap-2" aria-live="polite">
        {toasts.map((t) => (
          <div key={t.id} className="pop pointer-events-auto flex items-center gap-4 rounded-[var(--radius-m)] bg-ink px-4 py-2.5 text-sm text-bg shadow-[var(--shadow-pop)]">
            <span>{t.text}</span>
            {t.undo && (
              <button
                className="font-semibold text-accent underline-offset-2 hover:underline"
                style={{ color: "var(--accent)" }}
                onClick={() => { t.undo!(); setToasts((ts) => ts.filter((x) => x.id !== t.id)); }}
              >
                Undo
              </button>
            )}
          </div>
        ))}
      </div>
    </ToastCtx.Provider>
  );
}

/** Count up from 0 on first render. Respects reduced motion. */
export function CountUp({ value, format = (n: number) => String(n) }: { value: number; format?: (n: number) => string }) {
  const [shown, setShown] = useState(value);
  const first = useRef(true);
  useEffect(() => {
    if (!first.current || matchMedia("(prefers-reduced-motion: reduce)").matches || value === 0) {
      setShown(value);
      return;
    }
    first.current = false;
    const start = performance.now();
    const dur = 700;
    let raf = 0;
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / dur);
      setShown(Math.round(value * (1 - Math.pow(1 - t, 3))));
      if (t < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [value]);
  return <>{format(shown)}</>;
}
