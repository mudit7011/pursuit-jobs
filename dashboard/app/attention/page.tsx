"use client";

import { useMemo, useState } from "react";
import { CheckCircle2, ExternalLink, Mail, RotateCcw } from "lucide-react";
import { api, notifyChanged, useApi, useOnDataChanged, type Application } from "@/lib/api";
import { ago, platformLabel } from "@/lib/format";
import { ApplicationDrawer } from "@/components/app-drawer";
import { Button, EmptyState, ErrorState, PageHeader, Panel, Skeleton, useToast } from "@/components/ui";

// What each kind of failure means for the user, and what to do about it.
const GROUPS: { match: RegExp; title: string; advice: string; retry: boolean }[] = [
  { match: /needs your answers/i, title: "Needs a few answers from you", advice: "These forms ask things your profile doesn't cover. Answer once — the bot saves it and fills the same question on every future form.", retry: false },
  { match: /captcha/i, title: "Blocked by a CAPTCHA", advice: "The site wants a human. Press “Fill and let me finish”: a window opens with everything filled in, you solve the check and press Submit, and it's marked applied.", retry: false },
  { match: /sync api|asyncio/i, title: "Hit a bot bug (now fixed)", advice: "These failed because of a bug in how the browser was started. It's fixed, so a retry should go through.", retry: true },
  { match: /no form fields|form structure/i, title: "Old Google Form failures", advice: "These failed under the old filler, which couldn't open sign-in-only forms. The new form engine can, so Retry should get most of them through. Some forms will have closed since.", retry: true },
  { match: /\b55\d\b|recipient/i, title: "Email bounced", advice: "The address in the post was malformed. Multi-address posts are now split correctly, so a retry should work.", retry: true },
  { match: /did not reach submission|stuck/i, title: "Portal flow got stuck", advice: "A step in the portal needed something unusual. Open it and finish the last step.", retry: true },
  { match: /interrupted/i, title: "Interrupted mid-apply", advice: "The bot stopped while applying. Check the site first so you don't apply twice.", retry: false },
];
const OTHER = { title: "Something else went wrong", advice: "Open the posting and finish by hand, or retry.", retry: true };

export default function AttentionPage() {
  const { data, error, reload, setData } = useApi<Application[]>("/applications?status=failed", { poll: 30000 });
  useOnDataChanged(reload);
  const toast = useToast();
  const [open, setOpen] = useState<number | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const groups = useMemo(() => {
    const out = new Map<string, { meta: typeof OTHER; items: Application[] }>();
    for (const a of data ?? []) {
      const meta = GROUPS.find((g) => g.match.test(a.skip_reason ?? "")) ?? OTHER;
      if (!out.has(meta.title)) out.set(meta.title, { meta, items: [] });
      out.get(meta.title)!.items.push(a);
    }
    // Things only you can unblock come first, then the newest problems.
    const newest = (g: { items: Application[] }) => Math.max(...g.items.map((a) => Date.parse(a.updated_at ?? "") || 0));
    return [...out.values()].sort((a, b) =>
      Number(b.items.some((x) => x.missing_questions?.length)) - Number(a.items.some((x) => x.missing_questions?.length))
      || newest(b) - newest(a));
  }, [data]);

  const act = async (a: Application, action: "retry" | "mark-applied" | "dismiss" | "assist") => {
    setData((list) => list?.filter((x) => x.id !== a.id));
    try {
      await api(`/applications/${a.id}/${action}`, { method: "POST" });
      notifyChanged();
      toast({
        text: action === "assist" ? `A window will open with ${a.company}'s form filled in. Solve the check and press Submit.`
          : action === "retry" ? `Retrying ${a.company}` : action === "mark-applied" ? `${a.company} marked as applied` : `Dropped ${a.company}`,
      });
    } catch (e) {
      toast({ text: (e as Error).message, tone: "bad" });
      reload();
    }
  };

  const bulk = async (items: Application[], action: "retry" | "dismiss", key: string) => {
    setBusy(key);
    for (const a of items) await api(`/applications/${a.id}/${action}`, { method: "POST" }).catch(() => {});
    setBusy(null);
    toast({ text: action === "retry" ? `Retrying ${items.length}` : `Dropped ${items.length}` });
    reload();
    notifyChanged();
  };

  if (error && !data) return <ErrorState error={error} retry={reload} />;

  return (
    <div>
      <PageHeader
        title="Needs you"
        sub="Applications the bot couldn't finish on its own, grouped by what went wrong."
      />
      {!data ? (
        <div className="space-y-4"><Skeleton className="h-48" /><Skeleton className="h-48" /></div>
      ) : groups.length === 0 ? (
        <div className="rounded-[var(--radius-l)] bg-surface shadow-[var(--shadow-tile)]">
          <EmptyState icon={<CheckCircle2 size={30} />} title="Nothing stuck" body="When an application can't be finished automatically, it lands here with the reason and a one-click way to finish it." />
        </div>
      ) : (
        <div className="space-y-6">
          {groups.map(({ meta, items }) => (
            <Panel
              key={meta.title}
              title={<>{meta.title} <span className="ml-1.5 font-sans text-sm font-normal text-faint">{items.length}</span></>}
              action={
                <div className="flex gap-1">
                  {meta.retry && (
                    <Button size="sm" variant="ghost" disabled={!!busy} onClick={() => bulk(items, "retry", meta.title + "r")}>
                      <RotateCcw size={14} />Retry all
                    </Button>
                  )}
                  <Button size="sm" variant="ghost" disabled={!!busy} onClick={() => bulk(items, "dismiss", meta.title + "d")}>Drop all</Button>
                </div>
              }
            >
              <p className="max-w-2xl px-5 pb-3 text-sm text-dim">{meta.advice}</p>
              <ul className="divide-y divide-line-soft border-t border-line-soft">
                {items.slice(0, 50).map((a) => a.missing_questions?.length ? (
                  <AnswerCard key={a.id} app={a} onDone={() => { reload(); notifyChanged(); }} onOpen={() => setOpen(a.id)} />
                ) : (() => {
                  const email = a.apply_type === "email";
                  const href = email ? `mailto:${(a.apply_target ?? "").split(/[,;\s]+/)[0]}` : a.apply_target ?? "";
                  return (
                    <li key={a.id} className="flex flex-wrap items-center gap-x-4 gap-y-2 px-5 py-3">
                      <button className="min-w-0 flex-1 text-left" onClick={() => setOpen(a.id)}>
                        <span className="block truncate text-sm font-medium">{a.role}</span>
                        <span className="block truncate text-[13px] text-dim">{a.company} on {platformLabel(a.platform)}, {ago(a.updated_at)}</span>
                      </button>
                      <div className="flex flex-wrap gap-1.5">
                        {(a.apply_type === "web_form" || a.apply_type === "form") ? (
                          <Button size="sm" variant="primary" onClick={() => act(a, "assist")}
                                  title="The bot fills the form in a window; you solve the check and press Submit">
                            Fill and let me finish
                          </Button>
                        ) : href && (
                          <a href={href} target="_blank" rel="noreferrer noopener">
                            <Button size="sm">{email ? <Mail size={14} /> : <ExternalLink size={14} />}Finish by hand</Button>
                          </a>
                        )}
                        <Button size="sm" variant="ghost" onClick={() => act(a, "mark-applied")}>I applied</Button>
                        {meta.retry && <Button size="sm" variant="ghost" onClick={() => act(a, "retry")}>Retry</Button>}
                        <Button size="sm" variant="ghost" onClick={() => act(a, "dismiss")}>Drop</Button>
                      </div>
                    </li>
                  );
                })())}
              </ul>
              {items.length > 50 && <p className="px-5 py-3 text-xs text-faint">And {items.length - 50} more</p>}
            </Panel>
          ))}
        </div>
      )}
      <ApplicationDrawer id={open} onClose={() => setOpen(null)} />
    </div>
  );
}

const BEHAVIORAL = /(a|one) time (when |that )?you|tell us about (a|an|your) (time|situation|mistake|failure|conflict|challenge)|(bug|outage|downtime|incident|mistake|failure)s? (or [a-z ]+ )?(you|that you) (caused|made|faced|handled)|you('d| would) (reverse|change|do differently)|biggest (mistake|failure|challenge|regret)|(describe|share) (a|an) (situation|conflict|disagreement|failure|mistake)/i;

function AnswerCard({ app, onDone, onOpen }: { app: Application; onDone: () => void; onOpen: () => void }) {
  const toast = useToast();
  const qs = app.missing_questions ?? [];
  const [vals, setVals] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  // Behavioral questions the bot can write from the resume if left blank.
  const botCanWrite = (q: string) => BEHAVIORAL.test(q);
  const ready = qs.every((q) => botCanWrite(q) || (vals[q] ?? "").trim());
  const submit = async () => {
    setBusy(true);
    try {
      await api(`/applications/${app.id}/answers`, { method: "POST", body: JSON.stringify({ answers: vals }) });
      toast({ text: `Saved. Applying to ${app.company} again.` });
      onDone();
    } catch (e) {
      toast({ text: (e as Error).message, tone: "bad" });
    }
    setBusy(false);
  };
  return (
    <li className="px-5 py-4">
      <button className="text-left" onClick={onOpen}>
        <span className="block text-sm font-medium">{app.role}</span>
        <span className="block text-[13px] text-dim">{app.company} on {platformLabel(app.platform)}</span>
      </button>
      <div className="mt-3 grid gap-3 sm:grid-cols-2">
        {qs.map((q) => (
          <label key={q} className="block text-sm">
            <span className="mb-1 block text-[13px] text-dim">{q}</span>
            {botCanWrite(q) && <span className="mb-1 block text-xs text-faint">Optional. Leave blank and the bot writes it from your resume.</span>}
            <input
              value={vals[q] ?? ""}
              onChange={(e) => setVals({ ...vals, [q]: e.target.value })}
              onKeyDown={(e) => e.key === "Enter" && ready && submit()}
              className="h-9 w-full rounded-[var(--radius-s)] border border-line bg-raised px-3 outline-none focus:border-[var(--dim)]"
            />
          </label>
        ))}
      </div>
      <div className="mt-3 flex items-center gap-2">
        <Button size="sm" variant="primary" disabled={!ready || busy} onClick={submit}>Save and apply</Button>
        <span className="text-xs text-faint">Saved answers are reused on every future form.</span>
      </div>
    </li>
  );
}
