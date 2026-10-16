"use client"
import { useMemo, useState } from "react"
import { AnimatePresence, motion } from "framer-motion"
import { Check, Copy, FileUp } from "lucide-react"

const H2 = ({ children, className = "" }: { children: React.ReactNode; className?: string }) => (
  <h2 className={"day-display max-w-3xl " + className} style={{ fontSize: "clamp(2.4rem, 5.4vw, 4.8rem)" }}>{children}</h2>
)

/* ── The rest of the dashboard ──────────────────────────────────────────── */
export function Desk() {
  return (
    <section className="px-5 md:px-14 pb-32">
      <div className="max-w-6xl mx-auto">
        <H2>The rest of your job hunt, on one page</H2>
        <p className="mt-5 max-w-xl text-lg" style={{ color: "var(--day-dim)" }}>
          The dashboard runs on your laptop next to the bot. These are the parts you&apos;ll use most.
        </p>

        <div className="mt-14 grid grid-cols-12 gap-4">
          <AskOnce />
          <BotSwitch />
          <Activity />
          <ResumeDraft />
          <Board />
        </div>
      </div>
    </section>
  )
}

function AskOnce() {
  const [answer, setAnswer] = useState<string | null>(null)
  return (
    <div className="day-tile col-span-12 lg:col-span-7 p-6 md:p-8 flex flex-col min-h-[320px]">
      <p className="text-sm" style={{ color: "var(--day-dim)" }}>Needs you</p>
      <p className="mt-6 text-[15px]" style={{ color: "var(--day-faint)" }}>Northwind Labs, Product Engineer</p>
      <p className="mt-1 text-[26px] leading-tight" style={{ fontFamily: "var(--font-day)", fontWeight: 500, letterSpacing: "-0.025em" }}>
        Are you open to a walk-in interview in Gurugram?
      </p>
      <p className="mt-3 text-[15px]" style={{ color: "var(--day-dim)" }}>
        The bot won&apos;t guess things only you know. It asks once.
      </p>
      <div className="mt-auto pt-6 min-h-[64px]">
        <AnimatePresence mode="wait">
          {answer == null ? (
            <motion.div key="ask" className="flex gap-2" exit={{ opacity: 0 }}>
              {["Yes", "No"].map((a) => (
                <button key={a} onClick={() => setAnswer(a)}
                  className="h-11 px-6 rounded-[14px] text-[15px] font-medium transition-colors hover:bg-[var(--day-raised)]"
                  style={{ border: "1px solid var(--day-line)" }}>
                  {a}
                </button>
              ))}
            </motion.div>
          ) : (
            <motion.p key="saved" className="flex items-start gap-2.5 text-[15px] leading-relaxed" initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}>
              <Check size={18} className="mt-0.5 shrink-0" style={{ color: "var(--day-ink)" }} />
              <span>Saved &ldquo;{answer}&rdquo;. Northwind&apos;s form goes out now, and the next form that asks gets the same answer.{" "}
                <button className="underline underline-offset-4" style={{ color: "var(--day-dim)" }} onClick={() => setAnswer(null)}>Change it</button>
              </span>
            </motion.p>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}

function BotSwitch() {
  const [on, setOn] = useState(true)
  return (
    <div className="day-tile col-span-12 sm:col-span-6 lg:col-span-5 p-6 md:p-8 flex flex-col min-h-[320px]">
      <p className="text-sm" style={{ color: "var(--day-dim)" }}>The bot</p>
      <button
        onClick={() => setOn((v) => !v)}
        role="switch"
        aria-checked={on}
        aria-label="Bot running"
        className="mt-8 relative h-[88px] w-[176px] rounded-full transition-colors duration-300"
        style={{ background: on ? "var(--hi)" : "var(--day-line)" }}
      >
        <motion.span
          className="absolute top-2 size-[72px] rounded-full"
          style={{ background: on ? "var(--tile)" : "#ffffff", boxShadow: "0 2px 6px rgba(19,19,18,0.18)" }}
          animate={{ left: on ? 96 : 8 }}
          transition={{ type: "spring", stiffness: 500, damping: 34 }}
        />
      </button>
      <p className="mt-auto pt-6 day-display text-[40px]">{on ? "Running" : "Paused"}</p>
      <p className="mt-2 text-[15px]" style={{ color: "var(--day-dim)" }}>
        {on ? "Pause it for an interview week. It won't stop halfway through a form." : "Nothing is sent while it's paused. Start it from the same button."}
      </p>
    </div>
  )
}

function seeded(seed: number) {
  let s = seed
  return () => (s = (s * 16807) % 2147483647) / 2147483647
}

function Activity() {
  // A believable year: quiet start, then a habit forms.
  const days = useMemo(() => {
    const rnd = seeded(7)
    return Array.from({ length: 52 * 7 }, (_, i) => {
      const w = i / 7
      const p = w < 30 ? 0.12 : w < 40 ? 0.45 : 0.78
      return rnd() < p ? Math.ceil(rnd() * 4) : 0
    })
  }, [])
  const fills = ["var(--day-line)", "#f6e39a", "#f3d23f", "#c9a400", "var(--tile)"]
  const total = days.reduce((a, b) => a + b, 0)
  return (
    <div className="day-tile col-span-12 sm:col-span-6 lg:col-span-8 p-6 md:p-8">
      <div className="flex items-baseline justify-between gap-4">
        <p className="text-sm" style={{ color: "var(--day-dim)" }}>Every day you applied</p>
        <p className="text-sm tabular-nums" style={{ color: "var(--day-faint)" }}>{total} in a year</p>
      </div>
      <div className="mt-6 grid grid-flow-col grid-rows-7 gap-[3px]" style={{ gridTemplateColumns: "repeat(52, minmax(0, 1fr))" }} role="img" aria-label="A year of applications, busier in the last few months">
        {days.map((d, i) => <span key={i} className="aspect-square rounded-[2px]" style={{ background: fills[d] }} />)}
      </div>
      <p className="mt-5 text-[15px]" style={{ color: "var(--day-dim)" }}>Streaks, your busiest day and how many replies you got sit right under it.</p>
    </div>
  )
}

function ResumeDraft() {
  return (
    <div className="col-span-12 lg:col-span-4 rounded-[28px] p-6 md:p-8 flex flex-col min-h-[300px]" style={{ background: "var(--hi)" }}>
      <p className="text-sm font-medium">Your resume</p>
      <div className="mt-6 flex items-center gap-3 rounded-2xl p-4" style={{ background: "rgba(255,255,255,0.45)" }}>
        <FileUp size={20} />
        <span className="text-[15px]">resume-october.pdf</span>
      </div>
      <p className="mt-3 rounded-2xl p-4 text-[14px] leading-snug" style={{ background: "rgba(19,19,18,0.08)" }}>
        &ldquo;40%&rdquo; isn&apos;t in your PDF. Check it before you use this draft.
      </p>
      <p className="mt-auto pt-6 text-[15px] leading-relaxed">
        Upload a new one and you see a draft first. Every resume after that is tailored from it.
      </p>
    </div>
  )
}

const COLS: [string, string[]][] = [
  ["Applied", ["Kestrel Pay", "Quill & Ledger", "Orbit Freight", "Juniper Health"]],
  ["Screening", ["Lumen Analytics", "Halcyon Labs"]],
  ["Interview", ["Tandem Learning"]],
  ["Offer", []],
]

function Board() {
  return (
    <div className="day-tile col-span-12 p-6 md:p-8">
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <p className="text-sm" style={{ color: "var(--day-dim)" }}>Every application, by where it stands</p>
        <p className="text-sm" style={{ color: "var(--day-faint)" }}>Quiet for 7 days? It reminds you to follow up.</p>
      </div>
      <div className="mt-6 grid grid-cols-2 md:grid-cols-4 gap-3">
        {COLS.map(([name, cards]) => (
          <div key={name} className="rounded-2xl p-3 min-h-[180px]" style={{ background: "var(--day-raised)" }}>
            <p className="px-1 pb-3 text-[14px] font-medium flex justify-between">{name}<span style={{ color: "var(--day-faint)" }}>{cards.length}</span></p>
            <ul className="space-y-2">
              {cards.map((c) => (
                <li key={c} className="rounded-xl px-3 py-2.5 text-[14px]" style={{ background: "var(--day-surface)", boxShadow: "0 1px 2px rgba(19,19,18,0.06)" }}>{c}</li>
              ))}
              {!cards.length && <li className="px-1 text-[14px]" style={{ color: "var(--day-faint)" }}>Your first one lands here</li>}
            </ul>
          </div>
        ))}
      </div>
    </div>
  )
}

/* ── Where it applies ───────────────────────────────────────────────────── */
const WHERE: { how: string; detail: string; names: string[] }[] = [
  { how: "Applies for you", detail: "Logged in as you, one click per job", names: ["Naukri", "Instahyre", "Wellfound", "Indeed", "Internshala"] },
  { how: "Fills the whole form", detail: "Including the questions at the end", names: ["Google Forms", "Microsoft Forms", "Greenhouse", "Lever", "Ashby", "Zoho Forms", "Keka", "Any careers page"] },
  { how: "Writes the email", detail: "When the post says “send your resume to”", names: ["Gmail"] },
]

export function Where() {
  return (
    <section id="where" className="px-5 md:px-14 pb-24">
      <div className="max-w-6xl mx-auto">
        <H2>Three ways it applies</H2>
        <div className="mt-14">
          {WHERE.map((w) => (
            <div key={w.how} className="grid md:grid-cols-[18rem_1fr] gap-4 md:gap-10 py-8" style={{ borderTop: "1px solid var(--day-line)" }}>
              <div>
                <p className="text-[19px] font-medium">{w.how}</p>
                <p className="mt-1 text-[15px]" style={{ color: "var(--day-dim)" }}>{w.detail}</p>
              </div>
              <p className="day-display flex flex-wrap gap-x-5 gap-y-1" style={{ fontSize: "clamp(1.9rem, 3.6vw, 3.1rem)", fontWeight: 500, letterSpacing: "-0.035em" }}>
                {w.names.map((n, i) => (
                  <span key={n} style={{ color: i % 2 ? "var(--day-dim)" : "var(--day-ink)" }}>{n}</span>
                ))}
              </p>
            </div>
          ))}
          <p className="pt-6 text-[15px]" style={{ color: "var(--day-dim)", borderTop: "1px solid var(--day-line)" }}>
            LinkedIn Easy Apply is being rebuilt after LinkedIn changed its forms. Until then, LinkedIn jobs are found but not sent.
          </p>
        </div>
      </div>
    </section>
  )
}

/* ── Run it ─────────────────────────────────────────────────────────────── */
const SETUP: [string, string][] = [
  ["Get the code", "git clone https://github.com/mudit7011/pursuit-jobs && cd pursuit-jobs"],
  ["Install it", "pip install -r requirements.txt && playwright install chromium"],
  ["Log in to the job sites once", "python setup_sessions.py naukri instahyre wellfound"],
  ["Start the bot", "python -m src.main"],
  ["Open the dashboard", "python -m src.api & (cd dashboard && npm i && npm run dev)"],
]

export function Run() {
  const [copied, setCopied] = useState<number | null>(null)
  const copy = async (i: number, cmd: string) => {
    try { await navigator.clipboard.writeText(cmd); setCopied(i); setTimeout(() => setCopied(null), 1600) } catch {}
  }
  return (
    <section id="run" className="px-5 md:px-14 pb-24">
      <div className="max-w-6xl mx-auto grid lg:grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)] gap-10 lg:gap-16">
        <div>
          <H2>Five commands</H2>
          <p className="mt-5 max-w-md text-lg leading-relaxed" style={{ color: "var(--day-dim)" }}>
            Free and open source. You need Python 3.12, Node 20, a Gemini API key and a Telegram account. Your profile, resume and answers stay in files on your machine.
          </p>
        </div>
        <ol className="day-tile p-3 md:p-4">
          {SETUP.map(([what, cmd], i) => (
            <li key={what} className="rounded-2xl p-4 md:p-5 grid grid-cols-[1.75rem_1fr_auto] gap-x-3 items-start hover:bg-[var(--day-raised)] transition-colors">
              <span className="text-[15px] tabular-nums" style={{ color: "var(--day-faint)" }}>{i + 1}</span>
              <div className="min-w-0">
                <p className="text-[15px] font-medium">{what}</p>
                <code className="mt-1.5 block text-[13px] break-words" style={{ fontFamily: "var(--font-mono)", color: "var(--day-dim)" }}>{cmd}</code>
              </div>
              <button onClick={() => copy(i, cmd)} aria-label={`Copy: ${what}`} className="p-2 rounded-lg hover:bg-[var(--day-line)]" style={{ color: "var(--day-dim)" }}>
                {copied === i ? <Check size={16} style={{ color: "var(--day-ink)" }} /> : <Copy size={16} />}
              </button>
            </li>
          ))}
        </ol>
      </div>
    </section>
  )
}
