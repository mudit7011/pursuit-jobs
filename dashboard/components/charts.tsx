"use client";

import { useState } from "react";
import { nf } from "@/lib/format";

/** GitHub-style grid that fills its tile: one column per week, Monday on top. */
export function Heatmap({ days }: { days: { date: string; applied: number; found: number }[] }) {
  const [hover, setHover] = useState<{ date: string; applied: number; found: number } | null>(null);
  if (!days.length) return null;
  const first = new Date(days[0].date);
  const lead = (first.getDay() + 6) % 7;
  const cells: (typeof days[number] | null)[] = [...Array(lead).fill(null), ...days];
  const weeks: (typeof cells)[] = [];
  for (let i = 0; i < cells.length; i += 7) weeks.push(cells.slice(i, i + 7));
  const max = Math.max(1, ...days.map((d) => d.applied));
  const level = (n: number) => (n === 0 ? 0 : Math.min(4, Math.ceil((n / max) * 4)));
  const fills = [
    "var(--line-soft)",
    "color-mix(in srgb, var(--accent) 35%, var(--line-soft))",
    "color-mix(in srgb, var(--accent) 65%, var(--line-soft))",
    "var(--accent)",
    "var(--tile-dark)",
  ];
  const monthOf = (w: (typeof cells)) => { const d = w.find(Boolean); return d ? new Date(d.date).toLocaleString("en", { month: "short" }) : ""; };
  const total = days.reduce((s, d) => s + d.applied, 0);
  const activeDays = days.filter((d) => d.applied).length;
  const month = new Date().toISOString().slice(0, 7);
  const thisMonth = days.filter((d) => d.date.startsWith(month)).reduce((s, d) => s + d.applied, 0);
  let streak = 0, run = 0;
  for (const d of days) { run = d.applied ? run + 1 : 0; streak = Math.max(streak, run); }
  const best = days.reduce((b, d) => (d.applied > b.applied ? d : b), days[0]);
  const cols = { gridTemplateColumns: `repeat(${weeks.length}, minmax(0, 1fr))` };

  return (
    <div>
      <div className="mb-1.5 grid gap-[2px] text-[11px] text-faint" style={cols} aria-hidden>
        {weeks.map((w, i) => <span key={i} className="overflow-visible whitespace-nowrap">{i === 0 || monthOf(w) !== monthOf(weeks[i - 1]) ? monthOf(w) : ""}</span>)}
      </div>
      <div className="grid gap-[2px]" style={cols} role="img" aria-label={`${total} applications over the last 12 months`}>
        {weeks.map((w, i) => (
          <div key={i} className="grid gap-[2px]">
            {Array.from({ length: 7 }, (_, j) => {
              const d = w[j];
              return (
                <div
                  key={j}
                  className="aspect-square rounded-[2px] transition-transform hover:scale-125"
                  style={{ background: d ? fills[level(d.applied)] : "transparent" }}
                  onMouseEnter={() => d && setHover(d)}
                  onMouseLeave={() => setHover(null)}
                />
              );
            })}
          </div>
        ))}
      </div>
      <dl className="mt-6 grid grid-cols-3 gap-4 border-t border-line-soft pt-5">
        {[
          ["This month", nf.format(thisMonth)],
          ["Longest streak", `${streak} ${streak === 1 ? "day" : "days"}`],
          ["Busiest day", best.applied ? `${best.applied} on ${new Date(best.date).toLocaleDateString("en-IN", { day: "numeric", month: "short" })}` : "None yet"],
        ].map(([k, v]) => (
          <div key={k}>
            <dt className="text-xs text-faint">{k}</dt>
            <dd className="numeral mt-1.5 text-[28px]">{v}</dd>
          </div>
        ))}
      </dl>
      <p className="mt-4 h-5 text-[13px] text-dim">
        {hover ? (
          <>
            <span className="font-medium text-ink">
              {new Date(hover.date).toLocaleDateString("en-IN", { weekday: "long", day: "numeric", month: "short" })}
            </span>
            {": "}{hover.applied} applied, {hover.found} found
          </>
        ) : (
          <>{nf.format(total)} applications across {activeDays} days in the last 12 months</>
        )}
      </p>
    </div>
  );
}

/** Horizontal bars with labels on the left. Good for reasons and categories. */
export function BarList({ items, color = "var(--st-info)", empty = "Nothing yet" }: {
  items: { label: string; value: number; hint?: string }[]; color?: string; empty?: string;
}) {
  if (!items.length) return <p className="py-6 text-center text-sm text-faint">{empty}</p>;
  const max = Math.max(...items.map((i) => i.value), 1);
  return (
    <ul className="space-y-2.5">
      {items.map((it) => (
        <li key={it.label} className="grid grid-cols-[minmax(0,11rem)_1fr_auto] items-center gap-3 text-sm">
          <span className="truncate text-dim" title={it.label}>{it.label}</span>
          <span className="h-2 overflow-hidden rounded-full bg-line-soft">
            <span className="block h-full rounded-full" style={{ width: `${(it.value / max) * 100}%`, background: color }} />
          </span>
          <span className="w-10 text-right tabular-nums">{nf.format(it.value)}</span>
        </li>
      ))}
    </ul>
  );
}

/** Funnel as stepped bars, each with conversion from the previous stage. */
export function Funnel({ stages }: { stages: { stage: string; count: number }[] }) {
  const top = Math.max(stages[0]?.count ?? 0, 1);
  return (
    <ol className="space-y-2.5">
      {stages.map((s, i) => {
        const prev = i ? stages[i - 1].count : null;
        const conv = prev ? Math.round((s.count / prev) * 100) : null;
        const w = Math.max((s.count / top) * 100, s.count ? 3 : 0);
        const late = i >= 3;
        return (
          <li key={s.stage}>
            <div className="mb-1 flex items-baseline justify-between text-[13px]">
              <span className="text-dim">{s.stage}</span>
              <span className="tabular-nums">
                <span className="font-semibold">{nf.format(s.count)}</span>
                {conv != null && <span className="ml-2 text-xs text-faint">{conv}%</span>}
              </span>
            </div>
            <div className="h-2.5 overflow-hidden rounded-full bg-line-soft">
              <div className="h-full rounded-full" style={{ width: `${w}%`, background: late ? "var(--accent)" : "var(--tile-dark)" }} />
            </div>
          </li>
        );
      })}
    </ol>
  );
}

/** Weekly stacked columns: applied vs failed out of found. */
export function WeeklyColumns({ weeks }: { weeks: { week: string; found?: number; applied?: number; failed?: number }[] }) {
  if (!weeks.length) return <p className="py-6 text-center text-sm text-faint">No weeks recorded yet</p>;
  const max = Math.max(1, ...weeks.map((w) => w.found ?? 0));
  return (
    <div>
      <div className="flex h-40 items-end gap-1.5" role="img" aria-label="Jobs found, applied and failed per week">
        {weeks.map((w) => {
          const f = w.found ?? 0, a = w.applied ?? 0, x = w.failed ?? 0;
          return (
            <div key={w.week} className="group relative flex h-full flex-1 flex-col justify-end" title={`Week of ${w.week}: ${f} found, ${a} applied, ${x} failed`}>
              <div className="flex flex-col justify-end overflow-hidden rounded-t-[3px] bg-line-soft" style={{ height: `${(f / max) * 100}%` }}>
                <div style={{ height: f ? `${(x / f) * 100}%` : 0, background: "var(--st-warn)" }} />
                <div style={{ height: f ? `${(a / f) * 100}%` : 0, background: "var(--st-info)" }} />
              </div>
            </div>
          );
        })}
      </div>
      <div className="mt-2 flex justify-between text-[11px] text-faint">
        <span>{new Date(weeks[0].week).toLocaleDateString("en-IN", { day: "numeric", month: "short" })}</span>
        <span>This week</span>
      </div>
      <div className="mt-3 flex gap-4 text-xs text-dim">
        <Legend color="var(--line)" label="Found" />
        <Legend color="var(--st-info)" label="Applied" />
        <Legend color="var(--st-warn)" label="Failed" />
      </div>
    </div>
  );
}

function Legend({ color, label }: { color: string; label: string }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span className="size-2.5 rounded-[2px]" style={{ background: color }} />
      {label}
    </span>
  );
}
