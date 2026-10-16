"use client";

import Link from "next/link";
import { useState } from "react";
import { ArrowUpRight, Radar } from "lucide-react";
import { useApi, useOnDataChanged, type Overview } from "@/lib/api";
import { ago, greeting, hoursSaved, nf, platformLabel } from "@/lib/format";
import { ApplicationDrawer } from "@/components/app-drawer";
import { Funnel, Heatmap } from "@/components/charts";
import { CountUp, EmptyState, ErrorState, FitMeter, Skeleton, StatusPill, cx } from "@/components/ui";

const tile = "rounded-[var(--radius-l)] bg-surface shadow-[var(--shadow-tile)]";

export default function OverviewPage() {
  const { data, error, reload } = useApi<Overview>("/overview", { poll: 15000 });
  const { data: profile } = useApi<{ name?: string }>("/profile");
  useOnDataChanged(reload);
  const [open, setOpen] = useState<number | null>(null);

  if (error && !data) return <ErrorState error={error} retry={reload} />;
  if (!data) return <OverviewSkeleton />;

  const first = profile?.name?.split(" ")[0];
  const { kpis, focus } = data;
  const delta = kpis.applied_this_week - kpis.applied_last_week;

  return (
    <div className="rise grid grid-cols-12 gap-4">
      {/* Today */}
      <section className="col-span-12 flex flex-col justify-between py-2 lg:col-span-7 lg:pr-8">
        <p className="text-sm text-dim">{greeting()}{first ? `, ${first}` : ""}</p>
        <Today focus={focus} />
      </section>

      {/* The one decision waiting: the yellow tile */}
      <Link
        href="/queue"
        className="group col-span-12 flex min-h-56 flex-col justify-between rounded-[var(--radius-l)] bg-accent p-6 text-accent-ink transition-transform hover:-translate-y-0.5 sm:col-span-6 lg:col-span-5"
      >
        <div className="flex items-start justify-between">
          <span className="text-sm font-medium">Waiting for your yes</span>
          <ArrowUpRight size={20} className="transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
        </div>
        <div className="flex items-end justify-between gap-4">
          <span className="numeral text-[clamp(5rem,9vw,8.5rem)]"><CountUp value={focus.pending_approval} /></span>
          <span className="max-w-[12rem] pb-3 text-right text-sm leading-snug">
            {focus.pending_approval ? "Resumes tailored. Press A to apply, S to skip." : "All reviewed. New matches land here."}
          </span>
        </div>
      </Link>

      {/* Applied: the charcoal tile */}
      <div className="col-span-12 flex min-h-48 flex-col justify-between rounded-[var(--radius-l)] bg-tile p-6 text-tile-ink sm:col-span-6 lg:col-span-5">
        <div className="flex items-center justify-between text-sm">
          <span>Applications sent</span>
          <span className="text-tile-dim">{nf.format(kpis.jobs_seen)} jobs looked at</span>
        </div>
        <div className="flex items-end gap-8">
          <div>
            <span className="numeral block text-[clamp(4rem,7vw,6.5rem)]"><CountUp value={kpis.submitted_total} /></span>
            <span className="text-sm text-tile-dim">in total</span>
          </div>
          <div className="pb-1">
            <span className="numeral block text-[44px]"><CountUp value={kpis.applied_this_week} /></span>
            <span className="text-sm text-tile-dim">
              this week{delta !== 0 && <>, {delta > 0 ? "+" : ""}{delta} vs last</>}
            </span>
          </div>
        </div>
      </div>

      <Stat className="col-span-6 sm:col-span-4 lg:col-span-2" label="Reply rate"
            value={kpis.response_rate ?? 0} suffix="%" note={kpis.response_rate == null ? "Nothing sent yet" : "Screening or beyond"} />
      <Stat className="col-span-6 sm:col-span-4 lg:col-span-2" label="Interviews"
            value={kpis.interviews} note={kpis.offers ? `${kpis.offers} offer${kpis.offers > 1 ? "s" : ""}` : "Log them on the board"} />
      <Stat className="col-span-12 sm:col-span-4 lg:col-span-3" label="Time saved"
            value={kpis.minutes_saved} format={hoursSaved}
            note={kpis.resumes.reused ? `${kpis.resumes.reused} resumes reused, ${kpis.resumes.tailored} made` : "About 15 minutes per form"} />

      <section className={cx(tile, "col-span-12 p-6 lg:col-span-8")}>
        <h2 className="mb-5 font-display text-[17px] font-semibold tracking-[-0.02em]">Every day you applied</h2>
        <Heatmap days={data.heatmap} />
      </section>

      <section className={cx(tile, "col-span-12 p-6 lg:col-span-4")}>
        <h2 className="mb-5 font-display text-[17px] font-semibold tracking-[-0.02em]">Found to offer</h2>
        <Funnel stages={data.funnel} />
      </section>

      <section className={cx(tile, "col-span-12 overflow-hidden")}>
        <header className="flex items-center justify-between px-6 pt-5 pb-3">
          <h2 className="font-display text-[17px] font-semibold tracking-[-0.02em]">Latest activity</h2>
          <Link href="/applications" className="text-sm text-dim hover:text-ink">All applications</Link>
        </header>
        {data.recent.length === 0 ? (
          <EmptyState icon={<Radar size={28} />} title="Nothing here yet"
            body="Once the bot finds a job that fits you, it shows up here and in your review queue." />
        ) : (
          <ul>
            {data.recent.map((a) => (
              <li key={a.id} className="border-t border-line-soft">
                <button
                  onClick={() => setOpen(a.id)}
                  className="grid w-full grid-cols-[1fr_auto] items-center gap-4 px-6 py-3.5 text-left hover:bg-raised/60 sm:grid-cols-[1fr_9rem_9rem_6rem]"
                >
                  <span className="min-w-0">
                    <span className="block truncate text-[15px] font-medium">{a.company}</span>
                    <span className="block truncate text-[13px] text-dim">{a.role} · {platformLabel(a.platform)}</span>
                  </span>
                  <span className="hidden sm:block"><FitMeter score={a.fit_score} /></span>
                  <span><StatusPill status={a.status} /></span>
                  <span className="hidden text-right text-xs text-faint sm:block">{ago(a.updated_at)}</span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      <ApplicationDrawer id={open} onClose={() => setOpen(null)} />
    </div>
  );
}

function Today({ focus }: { focus: Overview["focus"] }) {
  const parts: { text: React.ReactNode; href: string }[] = [];
  if (focus.needs_answers) {
    parts.push({ href: "/attention", text: <>{focus.needs_answers} {focus.needs_answers === 1 ? "form needs" : "forms need"} an answer only you know.</> });
  }
  if (focus.failed_this_week) {
    parts.push({ href: "/attention", text: <>{focus.failed_this_week} got stuck this week and need a quick finish.</> });
  }
  if (focus.followups_due) {
    parts.push({ href: "/applications?filter=followup", text: <>{focus.followups_due} went quiet for a week. Worth a nudge.</> });
  }
  if (focus.in_flight) {
    parts.push({ href: "/applications", text: <>{focus.in_flight} approved and going out now.</> });
  }
  if (!parts.length) {
    return (
      <h1 className="mt-4 font-display text-[clamp(2rem,3.6vw,3.1rem)] leading-[1.02] font-semibold tracking-[-0.04em]">
        Nothing needs you. The bot keeps looking.
      </h1>
    );
  }
  return (
    <ul className="mt-4 space-y-3">
      {parts.map((p, i) => (
        <li key={i}>
          <Link
            href={p.href}
            className={cx(
              "font-display leading-[1.04] font-semibold tracking-[-0.035em] decoration-2 underline-offset-[7px] hover:underline",
              i === 0 ? "text-[clamp(2rem,3.6vw,3.1rem)]" : "text-[clamp(1.25rem,2vw,1.6rem)] text-dim hover:text-ink",
            )}
          >
            {p.text}
          </Link>
        </li>
      ))}
    </ul>
  );
}

function Stat({ label, value, note, suffix = "", format, className }: {
  label: string; value: number; note?: string; suffix?: string; format?: (n: number) => string; className?: string;
}) {
  return (
    <div className={cx(tile, "flex min-h-48 flex-col justify-between p-5", className)}>
      <span className="text-sm text-dim">{label}</span>
      <div>
        <span className="numeral block text-[52px]">
          <CountUp value={value} format={format ?? ((n) => nf.format(n))} />{suffix}
        </span>
        {note && <span className="mt-2 block text-xs text-faint">{note}</span>}
      </div>
    </div>
  );
}

function OverviewSkeleton() {
  return (
    <div className="grid grid-cols-12 gap-4" aria-busy="true" aria-label="Loading overview">
      <div className="col-span-12 space-y-3 lg:col-span-7"><Skeleton className="h-4 w-32" /><Skeleton className="h-12 w-4/5" /><Skeleton className="h-8 w-3/5" /></div>
      <Skeleton className="col-span-12 h-56 rounded-[var(--radius-l)] lg:col-span-5" />
      <Skeleton className="col-span-12 h-48 rounded-[var(--radius-l)] lg:col-span-5" />
      {["lg:col-span-2", "lg:col-span-2", "lg:col-span-3"].map((c, i) => <Skeleton key={i} className={`col-span-4 h-48 rounded-[var(--radius-l)] ${c}`} />)}
      <Skeleton className="col-span-12 h-64 rounded-[var(--radius-l)] lg:col-span-8" />
      <Skeleton className="col-span-12 h-64 rounded-[var(--radius-l)] lg:col-span-4" />
    </div>
  );
}
