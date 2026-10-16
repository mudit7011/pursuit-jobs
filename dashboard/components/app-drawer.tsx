"use client";

import { useEffect, useState } from "react";
import { ExternalLink, FileText, Mail } from "lucide-react";
import { api, notifyChanged, useApi, type Application, type Status } from "@/lib/api";
import { PIPELINE, STATUS_LABEL, ago, fullDate, platformLabel } from "@/lib/format";
import { Button, Drawer, FitMeter, Skeleton, StatusPill, useToast, cx, toneColor } from "./ui";

export function ApplicationDrawer({ id, onClose }: { id: number | null; onClose: () => void }) {
  return (
    <Drawer open={id != null} onClose={onClose} label="Application details">
      {id != null && <DrawerBody id={id} />}
    </Drawer>
  );
}

function DrawerBody({ id }: { id: number }) {
  const { data: app, setData, error } = useApi<Application>(`/applications/${id}`);
  const toast = useToast();
  const [notes, setNotes] = useState("");
  const [saving, setSaving] = useState(false);
  useEffect(() => { if (app) setNotes(app.notes ?? ""); }, [app?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  if (error) return <p className="p-8 text-sm text-bad">{error.message}</p>;
  if (!app) {
    return (
      <div className="space-y-4 p-8">
        <Skeleton className="h-7 w-2/3" />
        <Skeleton className="h-4 w-1/3" />
        <Skeleton className="h-40 w-full" />
      </div>
    );
  }

  const patch = async (body: Partial<Pick<Application, "status" | "notes" | "followup_at">>, msg?: string) => {
    const prev = app;
    try {
      const updated = await api<Application>(`/applications/${app.id}`, { method: "PATCH", body: JSON.stringify(body) });
      setData(updated);
      notifyChanged();
      if (msg) {
        toast({
          text: msg,
          undo: body.status ? () => patch({ status: prev.status }) : undefined,
        });
      }
    } catch (e) {
      toast({ text: (e as Error).message, tone: "bad" });
    }
  };

  const isEmail = app.apply_type === "email";
  const target = app.apply_target ?? "";
  const canMoveInPipeline = (PIPELINE as string[]).includes(app.status);

  return (
    <div className="px-7 pt-7 pb-10">
      <div className="pr-10">
        <StatusPill status={app.status} />
        <h2 className="mt-3 font-display text-2xl leading-tight font-semibold tracking-[-0.02em]">{app.role}</h2>
        <p className="mt-1 text-dim">
          {app.company}
          {app.location ? `, ${app.location}` : ""}
        </p>
      </div>

      <dl className="mt-6 grid grid-cols-2 gap-x-6 gap-y-4 border-y border-line-soft py-5 text-sm">
        <Field label="Fit"><FitMeter score={app.fit_score} /></Field>
        <Field label="Found on">{platformLabel(app.platform)}</Field>
        <Field label="Applied">{app.submitted_at ? fullDate(app.submitted_at) : "Not yet"}</Field>
        <Field label="Follow up on">
          <input
            type="date"
            value={app.followup_at?.slice(0, 10) ?? ""}
            onChange={(e) => patch({ followup_at: e.target.value }, e.target.value ? "Follow-up date set" : "Follow-up cleared")}
            className="h-7 rounded-md border border-line bg-raised px-2 text-sm text-ink"
            aria-label="Follow-up date"
          />
        </Field>
      </dl>

      <div className="mt-5 flex flex-wrap gap-2">
        {target && (
          <a href={isEmail ? `mailto:${target.split(/[,;\s]+/)[0]}` : target} target="_blank" rel="noreferrer noopener">
            <Button size="sm">{isEmail ? <Mail size={14} /> : <ExternalLink size={14} />}{isEmail ? "Email recruiter" : "Open posting"}</Button>
          </a>
        )}
        {app.has_resume && (
          <a href={`/api/applications/${app.id}/resume`} target="_blank" rel="noreferrer">
            <Button size="sm"><FileText size={14} />Tailored resume</Button>
          </a>
        )}
      </div>

      {app.has_resume && (
        <p className="mt-3 text-[13px] text-dim">
          {app.resume_source
            ? <>Resume reused from {app.resume_source}, so no new one had to be made.</>
            : <>Resume tailored for this job.</>}
        </p>
      )}

      {canMoveInPipeline && (
        <section className="mt-7">
          <h3 className="mb-2.5 text-sm font-medium">Where is it now?</h3>
          <div className="flex flex-wrap gap-1.5" role="radiogroup" aria-label="Application stage">
            {PIPELINE.map((s) => {
              const on = app.status === s;
              return (
                <button
                  key={s}
                  role="radio"
                  aria-checked={on}
                  onClick={() => !on && patch({ status: s as Status }, `Moved to ${STATUS_LABEL[s]}`)}
                  className={cx(
                    "rounded-full border px-3 py-1 text-[13px] transition-colors",
                    on ? "border-transparent font-medium" : "border-line text-dim hover:text-ink",
                  )}
                  style={on ? { background: `color-mix(in srgb, ${toneColor(s)} 18%, transparent)`, color: toneColor(s) } : undefined}
                >
                  {STATUS_LABEL[s]}
                </button>
              );
            })}
          </div>
        </section>
      )}

      {(app.status === "failed" || app.status === "skipped") && app.skip_reason && (
        <section className="mt-7 rounded-[var(--radius-m)] border border-line-soft bg-raised px-4 py-3 text-sm">
          <p className="font-medium">{app.status === "failed" ? "Why it didn't go through" : "Why it was skipped"}</p>
          <p className="mt-1 text-dim">{app.skip_reason}</p>
        </section>
      )}

      {app.fit_reason && (
        <section className="mt-7">
          <h3 className="mb-1.5 text-sm font-medium">Fit check</h3>
          <p className="text-sm leading-relaxed text-dim">{app.fit_reason}</p>
        </section>
      )}

      <section className="mt-7">
        <label htmlFor="notes" className="mb-1.5 block text-sm font-medium">Notes</label>
        <textarea
          id="notes"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          rows={3}
          placeholder="Recruiter name, interview date, what they asked…"
          className="w-full resize-y rounded-[var(--radius-m)] border border-line bg-raised px-3 py-2 text-sm outline-none placeholder:text-faint focus:border-[var(--dim)]"
        />
        {notes !== (app.notes ?? "") && (
          <Button
            size="sm"
            variant="primary"
            className="mt-2"
            disabled={saving}
            onClick={async () => { setSaving(true); await patch({ notes }, "Notes saved"); setSaving(false); }}
          >
            Save notes
          </Button>
        )}
      </section>

      {!!app.answers_used?.length && (
        <section className="mt-7">
          <h3 className="mb-2 text-sm font-medium">What the form got</h3>
          <dl className="divide-y divide-line-soft rounded-[var(--radius-m)] border border-line-soft text-[13px]">
            {app.answers_used.map(([q, v, src], i) => (
              <div key={i} className="grid gap-1 px-3 py-2 sm:grid-cols-[minmax(0,14rem)_1fr]">
                <dt className="text-dim">{q}</dt>
                <dd className="whitespace-pre-wrap">
                  {Array.isArray(v) ? v.join(", ") : v}
                  {src === "gemini" && <span className="ml-2 text-xs text-faint">written by AI</span>}
                  {src === "bank" && <span className="ml-2 text-xs text-faint">your saved answer</span>}
                </dd>
              </div>
            ))}
          </dl>
        </section>
      )}

      {app.jd_summary && (
        <section className="mt-7">
          <h3 className="mb-1.5 text-sm font-medium">Job description</h3>
          <div className="scroll-thin max-h-72 overflow-y-auto rounded-[var(--radius-m)] border border-line-soft bg-raised px-4 py-3 text-[13px] leading-relaxed whitespace-pre-wrap text-dim">
            {app.jd_summary}
          </div>
        </section>
      )}

      {!!app.events?.length && (
        <section className="mt-7">
          <h3 className="mb-3 text-sm font-medium">Timeline</h3>
          <ol className="relative ml-1.5 border-l border-line pl-5">
            {app.events.map((e, i) => (
              <li key={i} className="relative pb-4 last:pb-0">
                <span
                  className="absolute top-1.5 -left-[25px] size-2 rounded-full ring-4 ring-[var(--surface)]"
                  style={{ background: e.kind in STATUS_LABEL ? toneColor(e.kind as Status) : "var(--faint)" }}
                />
                <p className="text-sm">
                  {e.kind in STATUS_LABEL ? STATUS_LABEL[e.kind as Status] : e.kind === "note" ? "Notes edited" : e.kind}
                  <span className="ml-2 text-xs text-faint" title={fullDate(e.at)}>{ago(e.at)}</span>
                </p>
                {e.message && e.kind !== "note" && <p className="mt-0.5 text-[13px] text-dim">{e.message}</p>}
              </li>
            ))}
          </ol>
        </section>
      )}
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <dt className="mb-1 text-xs text-faint">{label}</dt>
      <dd>{children}</dd>
    </div>
  );
}
