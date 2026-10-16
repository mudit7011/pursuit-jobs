"use client";

import { useApi, type Insights } from "@/lib/api";
import { platformLabel } from "@/lib/format";
import { BarList, WeeklyColumns } from "@/components/charts";
import { ErrorState, PageHeader, Panel, Skeleton } from "@/components/ui";

export default function InsightsPage() {
  const { data, error, reload } = useApi<Insights>("/insights");

  if (error && !data) return <ErrorState error={error} retry={reload} />;
  if (!data) {
    return (
      <div>
        <PageHeader title="Insights" />
        <div className="grid gap-6 lg:grid-cols-2">{Array.from({ length: 4 }, (_, i) => <Skeleton key={i} className="h-64" />)}</div>
      </div>
    );
  }

  const skipped = data.skip_reasons.reduce((s, r) => s + r.count, 0);
  const top = data.skip_reasons[0];
  const scored = data.fit_distribution.reduce((s, b) => s + b.count, 0);

  return (
    <div className="rise">
      <PageHeader title="Insights" sub="What's working, what isn't, and where to adjust." />

      {top && (
        <p className="mb-8 max-w-3xl font-display text-[clamp(1.25rem,2.1vw,1.6rem)] leading-[1.3] font-semibold tracking-[-0.02em]">
          {Math.round((top.count / skipped) * 100)}% of skipped jobs were skipped for “{top.reason.toLowerCase()}”.{" "}
          <span className="text-dim">
            {/batch/i.test(top.reason)
              ? "If you're open to roles asking for other graduation years, widen the batch rule in Settings."
              : /skills/i.test(top.reason)
                ? "Adding missing skills you actually have to your profile will let more of these through."
                : "Check your profile and thresholds in Settings."}
          </span>
        </p>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <Panel title="Why jobs were skipped">
          <div className="px-5 pt-1 pb-5">
            <BarList items={data.skip_reasons.map((r) => ({ label: r.reason, value: r.count }))} color="var(--st-muted)" empty="No jobs skipped yet" />
          </div>
        </Panel>
        <Panel title="Why applications failed">
          <div className="px-5 pt-1 pb-5">
            <BarList items={data.failure_reasons.map((r) => ({ label: r.reason, value: r.count }))} color="var(--st-warn)" empty="No failures. Nice." />
          </div>
        </Panel>

        <Panel title="Week by week" className="lg:col-span-2">
          <div className="px-5 pt-1 pb-5"><WeeklyColumns weeks={data.weekly} /></div>
        </Panel>

        <Panel title="Platforms" className="lg:col-span-2">
          <div className="scroll-thin overflow-x-auto">
            <table className="w-full min-w-[620px] text-sm">
              <thead>
                <tr className="border-y border-line-soft text-left text-xs text-faint">
                  <th className="px-5 py-2.5 font-normal">Platform</th>
                  <th className="px-3 py-2.5 text-right font-normal">Found</th>
                  <th className="px-3 py-2.5 text-right font-normal">Applied</th>
                  <th className="px-3 py-2.5 text-right font-normal">Failed</th>
                  <th className="px-3 py-2.5 font-normal">Bot success rate</th>
                  <th className="px-5 py-2.5 text-right font-normal">Replies</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line-soft">
                {data.platforms.map((p) => (
                  <tr key={p.platform}>
                    <td className="px-5 py-2.5 font-medium">{platformLabel(p.platform)}</td>
                    <td className="px-3 py-2.5 text-right tabular-nums">{p.found}</td>
                    <td className="px-3 py-2.5 text-right tabular-nums">{p.applied ?? 0}</td>
                    <td className="px-3 py-2.5 text-right tabular-nums">{p.failed ?? 0}</td>
                    <td className="px-3 py-2.5">
                      {p.success_rate == null ? <span className="text-faint">Not tried</span> : (
                        <span className="flex items-center gap-2">
                          <span className="h-1.5 w-24 overflow-hidden rounded-full bg-line-soft">
                            <span className="block h-full rounded-full" style={{
                              width: `${p.success_rate}%`,
                              background: p.success_rate >= 70 ? "var(--st-good)" : p.success_rate >= 35 ? "var(--st-accent)" : "var(--st-warn)",
                            }} />
                          </span>
                          <span className="tabular-nums">{p.success_rate}%</span>
                        </span>
                      )}
                    </td>
                    <td className="px-5 py-2.5 text-right tabular-nums">{p.response_rate == null ? "—" : `${p.response_rate}%`}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>

        <Panel title="Fit scores of jobs found" className="lg:col-span-2">
          <div className="px-5 pt-1 pb-5">
            {scored === 0 ? (
              <p className="py-6 text-center text-sm text-faint">Fit scores are recorded for new jobs from now on.</p>
            ) : (
              <div className="flex h-36 items-end gap-2">
                {data.fit_distribution.map((b, i) => {
                  const max = Math.max(...data.fit_distribution.map((x) => x.count), 1);
                  return (
                    <div key={b.bucket} className="flex flex-1 flex-col items-center gap-1.5">
                      <span className="text-[11px] text-faint tabular-nums">{b.count || ""}</span>
                      <div className="w-full rounded-t-[3px]" style={{
                        height: `${(b.count / max) * 100}px`,
                        background: i >= 7 ? "var(--st-good)" : i >= 4 ? "var(--accent)" : "var(--line)",
                      }} />
                      <span className="text-[11px] text-faint">{i * 10}</span>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </Panel>
      </div>
    </div>
  );
}
