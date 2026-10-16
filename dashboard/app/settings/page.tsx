"use client";

import { useEffect, useState } from "react";
import { Copy, FileText, Upload, X } from "lucide-react";
import { api, notifyChanged, useApi, type PlatformHealth, type SavedAnswer, type Settings } from "@/lib/api";
import { ago, platformLabel } from "@/lib/format";
import { Button, ErrorState, PageHeader, Panel, Skeleton, cx, useToast } from "@/components/ui";

type Profile = Record<string, unknown> & {
  name?: string; email?: string; phone?: string; linkedin?: string; github?: string; portfolio?: string;
  expected_ctc?: string; current_ctc?: string; notice_period?: string; location_preference?: string;
  years_of_experience?: number; graduation_year?: number; skills?: string[]; summary?: string;
  job_search?: { keywords?: string[]; locations?: string[]; blacklist_keywords?: string[]; experience_min?: number; experience_max?: number };
};

export default function SettingsPage() {
  return (
    <div>
      <PageHeader title="Settings" sub="How the bot decides, and what it knows about you." />
      <div className="space-y-6">
        <ResumeSettings />
        <AutomationSettings />
        <PlatformSettings />
        <ProfileSettings />
        <SavedAnswers />
        <Panel title="Where your data lives">
          <p className="max-w-2xl px-5 pb-5 text-sm leading-relaxed text-dim">
            Everything stays on this computer: applications in <code className="text-ink">data/applications.db</code>,
            your profile in <code className="text-ink">config/profile.json</code>, tailored resumes in{" "}
            <code className="text-ink">output/</code>. The dashboard API only listens on localhost. The only things sent
            out are job descriptions and your skills to Gemini for fit checks and resume tailoring, and the applications
            you approve to the job sites themselves.
          </p>
        </Panel>
      </div>
    </div>
  );
}

function AutomationSettings() {
  const { data, error, reload, setData } = useApi<Settings>("/settings");
  const toast = useToast();
  if (error && !data) return <ErrorState error={error} retry={reload} />;
  if (!data) return <Skeleton className="h-72" />;

  const save = async (patch: Partial<Settings>) => {
    setData({ ...data, ...patch });
    try {
      setData(await api<Settings>("/settings", { method: "PUT", body: JSON.stringify(patch) }));
      notifyChanged();
      toast({ text: "Saved" });
    } catch (e) {
      toast({ text: (e as Error).message, tone: "bad" });
      reload();
    }
  };

  return (
    <Panel title="Automation">
      <div className="divide-y divide-line-soft border-t border-line-soft">
        <Row title="When a good job is found" body="Ask first is safer: you see every job before anything is sent.">
          <div className="flex rounded-[var(--radius-s)] border border-line p-0.5" role="radiogroup" aria-label="Apply mode">
            {([["approval", "Ask me first"], ["auto", "Apply automatically"]] as const).map(([v, l]) => (
              <button key={v} role="radio" aria-checked={data.apply_mode === v} onClick={() => save({ apply_mode: v })}
                className={cx("h-8 rounded-[4px] px-3 text-[13px]", data.apply_mode === v ? "bg-raised font-medium text-ink" : "text-dim")}>
                {l}
              </button>
            ))}
          </div>
        </Row>
        {data.apply_mode === "approval" && (
          <Row title="Skip the queue for great fits" body="Jobs at or above this fit score are sent without asking. 0 turns this off.">
            <NumberInput value={data.auto_approve_min_fit} onSave={(v) => save({ auto_approve_min_fit: v })} max={100} suffix="fit" />
          </Row>
        )}
        <Row title="Minimum fit" body="Jobs below this skills overlap are skipped. Lower it to see more jobs; raise it for fewer, better ones.">
          <NumberInput value={data.min_fit} onSave={(v) => save({ min_fit: v })} max={100} suffix="fit" />
        </Row>
        <Row title="Follow up after" body="Applications with no update after this many days show up as follow-ups.">
          <NumberInput value={data.followup_days} onSave={(v) => save({ followup_days: v })} min={1} max={60} suffix="days" />
        </Row>
        <Row title="Telegram message for every skipped job" body="Off by default. You'll still get a message for jobs to review and for each application sent.">
          <button role="switch" aria-checked={data.notify_skips} onClick={() => save({ notify_skips: !data.notify_skips })}
            className={cx("relative h-6 w-11 rounded-full transition-colors", data.notify_skips ? "bg-accent" : "bg-line")}>
            <span className={cx("absolute top-0.5 size-5 rounded-full bg-white shadow transition-[left]", data.notify_skips ? "left-[22px]" : "left-0.5")} />
            <span className="sr-only">Telegram message for every skipped job</span>
          </button>
        </Row>
      </div>
    </Panel>
  );
}

function Row({ title, body, children }: { title: string; body: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-4 px-5 py-4">
      <div className="max-w-lg">
        <p className="text-sm font-medium">{title}</p>
        <p className="mt-0.5 text-[13px] text-dim">{body}</p>
      </div>
      {children}
    </div>
  );
}

function NumberInput({ value, onSave, min = 0, max, suffix }: { value: number; onSave: (v: number) => void; min?: number; max: number; suffix: string }) {
  const [v, setV] = useState(String(value));
  useEffect(() => setV(String(value)), [value]);
  const commit = () => {
    const n = Math.round(Number(v));
    if (Number.isFinite(n) && n >= min && n <= max && n !== value) onSave(n);
    else setV(String(value));
  };
  return (
    <label className="flex items-center gap-2 text-sm text-dim">
      <input type="number" value={v} min={min} max={max} onChange={(e) => setV(e.target.value)} onBlur={commit}
        onKeyDown={(e) => e.key === "Enter" && (e.target as HTMLInputElement).blur()}
        className="h-9 w-20 rounded-[var(--radius-s)] border border-line bg-raised px-2.5 text-right text-ink tabular-nums" />
      {suffix}
    </label>
  );
}

const FIELDS: [keyof Profile, string][] = [
  ["name", "Full name"], ["email", "Email"], ["phone", "Phone"], ["linkedin", "LinkedIn"], ["github", "GitHub"],
  ["portfolio", "Portfolio"], ["expected_ctc", "Expected CTC"], ["current_ctc", "Current CTC"],
  ["notice_period", "Notice period"], ["location_preference", "Preferred locations"],
];

function ProfileSettings() {
  const { data, error, reload } = useApi<Profile>("/profile");
  const toast = useToast();
  const [p, setP] = useState<Profile | null>(null);
  const [saving, setSaving] = useState(false);
  useEffect(() => { if (data) setP(data); }, [data]);
  if (error && !data) return <ErrorState error={error} retry={reload} />;
  if (!p) return <Skeleton className="h-96" />;

  const dirty = JSON.stringify(p) !== JSON.stringify(data);
  const js = p.job_search ?? {};
  const setJs = (k: keyof NonNullable<Profile["job_search"]>, v: unknown) => setP({ ...p, job_search: { ...js, [k]: v } });

  const save = async () => {
    setSaving(true);
    try {
      await api("/profile", { method: "PUT", body: JSON.stringify(p) });
      toast({ text: "Profile saved. The bot uses it from its next restart." });
      reload();
    } catch (e) {
      toast({ text: (e as Error).message, tone: "bad" });
    }
    setSaving(false);
  };

  return (
    <Panel title="Your profile" action={dirty && (
      <div className="flex gap-2">
        <Button size="sm" variant="ghost" onClick={() => setP(data!)}>Discard</Button>
        <Button size="sm" variant="primary" disabled={saving} onClick={save}>Save profile</Button>
      </div>
    )}>
      <div className="grid gap-x-5 gap-y-4 border-t border-line-soft px-5 py-5 sm:grid-cols-2">
        {FIELDS.map(([k, label]) => (
          <label key={k} className="block text-sm">
            <span className="mb-1 block text-[13px] text-dim">{label}</span>
            <input value={(p[k] as string) ?? ""} onChange={(e) => setP({ ...p, [k]: e.target.value })}
              className="h-9 w-full rounded-[var(--radius-s)] border border-line bg-raised px-3 outline-none focus:border-[var(--dim)]" />
          </label>
        ))}
        <label className="block text-sm">
          <span className="mb-1 block text-[13px] text-dim">Years of experience</span>
          <input type="number" min={0} value={p.years_of_experience ?? 0} onChange={(e) => setP({ ...p, years_of_experience: Number(e.target.value) })}
            className="h-9 w-full rounded-[var(--radius-s)] border border-line bg-raised px-3" />
        </label>
        <label className="block text-sm">
          <span className="mb-1 block text-[13px] text-dim">Graduation year</span>
          <input type="number" value={p.graduation_year ?? ""} onChange={(e) => setP({ ...p, graduation_year: Number(e.target.value) })}
            className="h-9 w-full rounded-[var(--radius-s)] border border-line bg-raised px-3" />
        </label>
        <div className="sm:col-span-2"><Chips label="Skills" values={p.skills ?? []} onChange={(v) => setP({ ...p, skills: v })} /></div>
        <div className="sm:col-span-2"><Chips label="Job titles to search" values={js.keywords ?? []} onChange={(v) => setJs("keywords", v)} /></div>
        <div className="sm:col-span-2"><Chips label="Locations to search" values={js.locations ?? []} onChange={(v) => setJs("locations", v)} /></div>
        <div className="sm:col-span-2"><Chips label="Ignore titles containing" values={js.blacklist_keywords ?? []} onChange={(v) => setJs("blacklist_keywords", v)} /></div>
        <label className="block text-sm sm:col-span-2">
          <span className="mb-1 block text-[13px] text-dim">Summary</span>
          <textarea rows={3} value={p.summary ?? ""} onChange={(e) => setP({ ...p, summary: e.target.value })}
            className="w-full rounded-[var(--radius-s)] border border-line bg-raised px-3 py-2 leading-relaxed" />
        </label>
      </div>
    </Panel>
  );
}

function Chips({ label, values, onChange }: { label: string; values: string[]; onChange: (v: string[]) => void }) {
  const [draft, setDraft] = useState("");
  const add = () => {
    const parts = draft.split(",").map((s) => s.trim()).filter((s) => s && !values.includes(s));
    if (parts.length) onChange([...values, ...parts]);
    setDraft("");
  };
  return (
    <div className="text-sm">
      <span className="mb-1 block text-[13px] text-dim">{label}</span>
      <div className="flex flex-wrap items-center gap-1.5 rounded-[var(--radius-s)] border border-line bg-raised p-1.5">
        {values.map((v) => (
          <span key={v} className="inline-flex items-center gap-1 rounded-[4px] bg-surface py-0.5 pr-1 pl-2 text-[13px]">
            {v}
            <button aria-label={`Remove ${v}`} onClick={() => onChange(values.filter((x) => x !== v))} className="rounded p-0.5 text-faint hover:text-ink"><X size={12} /></button>
          </span>
        ))}
        <input value={draft} onChange={(e) => setDraft(e.target.value)} onBlur={add} placeholder="Add, then Enter"
          onKeyDown={(e) => { if (e.key === "Enter" || e.key === ",") { e.preventDefault(); add(); } else if (e.key === "Backspace" && !draft && values.length) onChange(values.slice(0, -1)); }}
          className="h-7 min-w-32 flex-1 bg-transparent px-1.5 outline-none placeholder:text-faint" aria-label={`Add to ${label}`} />
      </div>
    </div>
  );
}

const SESSION_TEXT: Record<PlatformHealth["status"], { label: string; color: string }> = {
  connected: { label: "Logged in", color: "var(--st-good)" },
  expired: { label: "Login expired", color: "var(--st-warn)" },
  missing: { label: "Not set up", color: "var(--st-muted)" },
  unknown: { label: "Saved", color: "var(--st-info)" },
};

function PlatformSettings() {
  const { data, error, reload } = useApi<PlatformHealth[]>("/platforms", { poll: 30000 });
  const toast = useToast();
  if (error && !data) return <ErrorState error={error} retry={reload} />;
  if (!data) return <Skeleton className="h-80" />;

  const saveCap = async (platform: string, n: number) => {
    try {
      await api("/settings", { method: "PUT", body: JSON.stringify({ daily_caps: { [platform]: n } }) });
      toast({ text: `${platformLabel(platform)}: up to ${n} a day` });
      reload();
    } catch (e) {
      toast({ text: (e as Error).message, tone: "bad" });
    }
  };
  const copy = async (cmd: string) => {
    try { await navigator.clipboard.writeText(cmd); toast({ text: "Command copied. Run it in the project folder." }); }
    catch { toast({ text: cmd }); }
  };

  return (
    <section id="platforms">
      <Panel title="Platforms">
        <p className="max-w-2xl px-5 pb-4 text-sm text-dim">
          The bot applies through your own logged-in accounts. When a login expires, run the command shown, log in in the
          window that opens, then press Enter. Daily limits keep your accounts from looking like a bot.
        </p>
        <ul className="divide-y divide-line-soft border-t border-line-soft">
          {data.map((p) => {
            const st = SESSION_TEXT[p.status];
            const needsLogin = p.status === "expired" || p.status === "missing";
            const capReached = p.daily_cap != null && p.applied_today >= p.daily_cap;
            return (
              <li key={p.platform} className="grid items-center gap-x-6 gap-y-3 px-5 py-4 sm:grid-cols-[10rem_1fr_auto]">
                <div>
                  <p className="text-sm font-medium">{platformLabel(p.platform)}</p>
                  <p className="mt-0.5 inline-flex items-center gap-1.5 text-[13px]" style={{ color: st.color }}>
                    <span className="size-1.5 rounded-full" style={{ background: st.color }} aria-hidden />
                    {st.label}
                  </p>
                </div>
                <div className="text-[13px] text-dim">
                  {needsLogin ? (
                    <button onClick={() => copy(p.refresh_command)}
                      className="inline-flex items-center gap-2 rounded-[var(--radius-s)] border border-line bg-raised px-2.5 py-1.5 text-ink hover:border-[var(--dim)]">
                      <code className="text-[12px]">{p.refresh_command}</code>
                      <Copy size={13} className="text-faint" />
                    </button>
                  ) : (
                    <>
                      {p.expires_at ? `Login good until ${new Date(p.expires_at).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" })}` : p.saved_at ? `Login saved ${ago(p.saved_at)}` : ""}
                      {p.queued > 0 && <span className="ml-3 text-faint">{p.queued} in queue</span>}
                    </>
                  )}
                  {needsLogin && p.queued > 0 && <p className="mt-1.5 text-faint">{p.queued} queued jobs will wait until you log in again.</p>}
                </div>
                <div className="flex items-center gap-3 text-[13px] text-dim">
                  <span className={capReached ? "text-warn" : ""} style={capReached ? { color: "var(--st-warn)" } : undefined}>
                    {p.applied_today} today
                  </span>
                  <NumberInput value={p.daily_cap ?? 0} onSave={(n) => saveCap(p.platform, n)} max={200} suffix="max / day" />
                </div>
              </li>
            );
          })}
        </ul>
      </Panel>
    </section>
  );
}

function SavedAnswers() {
  const { data, error, reload, setData } = useApi<SavedAnswer[]>("/answers");
  const toast = useToast();
  const [q, setQ] = useState("");
  const [a, setA] = useState("");
  if (error && !data) return <ErrorState error={error} retry={reload} />;
  if (!data) return <Skeleton className="h-48" />;
  const save = async (question: string, answer: string) => {
    try {
      setData(await api<SavedAnswer[]>("/answers", { method: "PUT", body: JSON.stringify({ question, answer }) }));
      toast({ text: "Answer saved" });
    } catch (e) { toast({ text: (e as Error).message, tone: "bad" }); }
  };
  const remove = async (id: number) => {
    setData(await api<SavedAnswer[]>(`/answers/${id}`, { method: "DELETE" }));
    toast({ text: "Answer removed" });
  };
  return (
    <Panel title="Saved answers">
      <p className="max-w-2xl px-5 pb-4 text-sm text-dim">
        Things forms ask that your resume doesn&apos;t say, like 10th marks or date of birth. The bot uses these word
        for word and never guesses them.
      </p>
      <ul className="divide-y divide-line-soft border-t border-line-soft">
        {data.length === 0 && <li className="px-5 py-6 text-sm text-faint">No saved answers yet. They appear here when you answer a form&apos;s question in Needs you.</li>}
        {data.map((x) => <AnswerRow key={x.id} x={x} onSave={save} onRemove={remove} />)}
        <li className="grid gap-2 px-5 py-4 sm:grid-cols-[1fr_1fr_auto]">
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Question, e.g. Date of birth"
            className="h-9 rounded-[var(--radius-s)] border border-line bg-raised px-3 text-sm" aria-label="New question" />
          <input value={a} onChange={(e) => setA(e.target.value)} placeholder="Your answer"
            className="h-9 rounded-[var(--radius-s)] border border-line bg-raised px-3 text-sm" aria-label="New answer" />
          <Button size="sm" disabled={!q.trim() || !a.trim()} onClick={() => { save(q, a); setQ(""); setA(""); }}>Add</Button>
        </li>
      </ul>
    </Panel>
  );
}

function AnswerRow({ x, onSave, onRemove }: { x: SavedAnswer; onSave: (q: string, a: string) => void; onRemove: (id: number) => void }) {
  const [v, setV] = useState(x.answer);
  return (
    <li className="grid items-center gap-2 px-5 py-3 sm:grid-cols-[1fr_1fr_auto]">
      <span className="text-sm">{x.question}<span className="ml-2 text-xs text-faint">used {x.times_used}×</span></span>
      <input value={v} onChange={(e) => setV(e.target.value)} onBlur={() => v.trim() && v !== x.answer && onSave(x.question, v)}
        className="h-9 rounded-[var(--radius-s)] border border-line bg-raised px-3 text-sm" aria-label={`Answer to ${x.question}`} />
      <Button size="sm" variant="ghost" onClick={() => onRemove(x.id)}>Remove</Button>
    </li>
  );
}

type ResumeInfo = { version: string; updated_at: string | null; has_pdf: boolean };
type Draft = { id: string; warnings: string[] };

function ResumeSettings() {
  const { data, reload } = useApi<ResumeInfo>("/resume");
  const toast = useToast();
  const [busy, setBusy] = useState(false);
  const [draft, setDraft] = useState<Draft | null>(null);

  const upload = async (file: File) => {
    setBusy(true);
    try {
      const buf = new Uint8Array(await file.arrayBuffer());
      let bin = "";
      for (let i = 0; i < buf.length; i += 0x8000) bin += String.fromCharCode(...buf.subarray(i, i + 0x8000));
      setDraft(await api<Draft>("/resume/draft", { method: "POST", body: JSON.stringify({ filename: file.name, data_b64: btoa(bin) }) }));
    } catch (e) {
      toast({ text: (e as Error).message, tone: "bad" });
    }
    setBusy(false);
  };
  const use = async () => {
    if (!draft) return;
    await api(`/resume/draft/${draft.id}/use`, { method: "POST" });
    setDraft(null);
    reload();
    toast({ text: "New resume in use. Every new job gets a resume tailored from it." });
  };
  const discard = async () => {
    if (draft) await api(`/resume/draft/${draft.id}`, { method: "DELETE" }).catch(() => {});
    setDraft(null);
  };

  return (
    <Panel title="Your resume">
      <p className="max-w-2xl px-5 pb-4 text-sm text-dim">
        The bot tailors this resume for every job. Upload a newer one and all future jobs start from it; tailored
        resumes made from the old one stop being reused. Your current resume is kept as a backup.
      </p>
      <div className="flex flex-wrap items-center gap-3 border-t border-line-soft px-5 py-4">
        {data?.has_pdf && (
          <a href="/api/resume/pdf" target="_blank" rel="noreferrer">
            <Button size="sm"><FileText size={14} />Current resume</Button>
          </a>
        )}
        <span className="text-xs text-faint">{data?.updated_at ? `Updated ${ago(data.updated_at)}` : ""}</span>
        <span className="flex-1" />
        <label className={cx("inline-flex h-8 cursor-pointer items-center gap-2 rounded-[var(--radius-s)] bg-tile px-3 text-[13px] font-medium text-tile-ink",
                             busy && "pointer-events-none opacity-60")}>
          <Upload size={14} />{busy ? "Reading your resume…" : "Upload new resume"}
          <input type="file" accept=".pdf,.tex" className="sr-only"
                 onChange={(e) => { const f = e.target.files?.[0]; if (f) upload(f); e.target.value = ""; }} />
        </label>
      </div>
      {draft && (
        <div className="border-t border-line-soft px-5 py-5">
          <p className="text-sm font-medium">Check the new resume before using it</p>
          <p className="mt-1 text-[13px] text-dim">PDFs are copied into your resume template. Everything should match your file word for word.</p>
          {draft.warnings.map((w) => (
            <p key={w} className="mt-3 rounded-[var(--radius-s)] px-3 py-2 text-[13px]"
               style={{ background: "color-mix(in srgb, var(--st-warn) 14%, transparent)", color: "var(--st-warn)" }}>{w}</p>
          ))}
          <iframe src={`/api/resume/draft/${draft.id}/pdf`} title="New resume preview"
                  className="mt-4 h-[520px] w-full rounded-[var(--radius-m)] border border-line bg-white" />
          <div className="mt-4 flex gap-2">
            <Button variant="primary" size="sm" onClick={use}>Use this resume</Button>
            <Button size="sm" variant="ghost" onClick={discard}>Discard</Button>
          </div>
        </div>
      )}
    </Panel>
  );
}
