"use client"
import { useEffect, useRef, useState } from "react"
import { AnimatePresence, motion, useInView } from "framer-motion"
import { Check, Minus } from "lucide-react"

/* One job, followed from the moment it's posted to the moment it waits for you.
   The text scrolls; the job on the right changes with it. */

const STEPS = [
  {
    time: "02:14",
    title: "A job gets posted while you sleep.",
    body: "Someone drops it in one of your Telegram groups. The bot also checks Naukri, Instahyre, Wellfound, Indeed and Internshala every few hours.",
  },
  {
    time: "02:14",
    title: "It reads the post the way you would.",
    body: "Company, role, batch, experience asked, and where to apply: a form, a careers page or an email address. The link is copied exactly as it was posted.",
  },
  {
    time: "02:15",
    title: "It checks you'd actually qualify.",
    body: "Wrong batch, or three years asked when you have one? Skipped, and the reason is written down. Otherwise it scores how well your skills fit, out of 100.",
  },
  {
    time: "02:15",
    title: "It picks your resume.",
    body: "If it already tailored one for a similar role, it reuses it. If not, it rewrites your LaTeX resume around this job, using only what's already true about you.",
  },
  {
    time: "02:16",
    title: "It fills in the form.",
    body: "Name, links, notice period, even “tell us about a bug you fixed”, written from your real projects. A question only you can answer gets asked once on Telegram, then remembered.",
  },
  {
    time: "02:16",
    title: "Then it waits for you.",
    body: "Nothing is sent until you say yes. If you'd rather not review everything, let it send anything above a fit score you pick.",
  },
]

export default function Night() {
  const [active, setActive] = useState(0)
  return (
    <section id="night" className="relative px-5 md:px-14 pt-4 pb-32" style={{
      // This section used to be night-themed; it now reads on white like the rest of the site
      ["--bg" as string]: "#ffffff", ["--card" as string]: "#f6f6f3", ["--ink" as string]: "#131312", ["--ink-dim" as string]: "#5a5a55",
      ["--rust" as string]: "#131312", ["--border" as string]: "#e2e2dc", ["--border-warm" as string]: "#d6d6d0",
      background: "var(--bg)", color: "var(--ink)" }}>
      <div className="max-w-6xl mx-auto">
        <div className="grid md:grid-cols-[minmax(0,1fr)_minmax(0,1.05fr)] gap-10 md:gap-20">
          {/* The job, pinned while the steps scroll past */}
          <div className="hidden md:block md:order-2">
            <div className="sticky top-[18vh] z-10">
              <JobVisual step={active} />
              <ol className="mt-5 flex gap-1.5" aria-hidden>
                {STEPS.map((_, i) => (
                  <li
                    key={i}
                    className="h-[3px] flex-1 rounded-full transition-colors duration-500"
                    style={{ background: i <= active ? "var(--rust)" : "var(--border-warm)" }}
                  />
                ))}
              </ol>
            </div>
          </div>

          <ol className="md:order-1">
            {STEPS.map((s, i) => (
              <Step key={i} index={i} {...s} active={active === i} onActive={setActive} />
            ))}
          </ol>
        </div>
      </div>
    </section>
  )
}

function Step({ index, time, title, body, active, onActive }: {
  index: number; time: string; title: string; body: string; active: boolean; onActive: (i: number) => void
}) {
  const ref = useRef<HTMLLIElement>(null)
  const inView = useInView(ref, { margin: "-45% 0px -45% 0px" })
  useEffect(() => { if (inView) onActive(index) }, [inView, index, onActive])
  return (
    <li
      ref={ref}
      className="md:min-h-[62vh] flex flex-col justify-center py-10 transition-opacity duration-500"
      style={{ opacity: active ? 1 : 0.28 }}
    >
      <time className="self-start rounded-full px-3 py-1 text-sm font-medium tabular-nums" style={{ background: "var(--hi)", color: "#131312" }}>
        {time} am
      </time>
      <h3
        className="mt-3"
        style={{ fontFamily: "var(--font-serif)", fontWeight: 600, fontSize: "clamp(1.7rem, 2.6vw, 2.3rem)", lineHeight: 1.08, letterSpacing: "-0.035em" }}
      >
        {title}
      </h3>
      <p className="mt-4 max-w-md text-base leading-relaxed" style={{ color: "var(--ink-dim)", fontWeight: 300 }}>
        {body}
      </p>
      {/* On phones there's no room to pin the job beside the text, so each step shows its own */}
      <div className="md:hidden mt-8"><JobVisual step={index} /></div>
    </li>
  )
}

/* ── The job card in its six states ─────────────────────────────────────── */

const swap = {
  initial: { opacity: 0, y: 14, filter: "blur(4px)" },
  animate: { opacity: 1, y: 0, filter: "blur(0px)" },
  exit: { opacity: 0, y: -10, filter: "blur(4px)" },
  transition: { duration: 0.45, ease: [0.22, 1, 0.36, 1] as const },
}

function JobVisual({ step }: { step: number }) {
  return (
    <div
      className="relative overflow-hidden h-[440px] md:h-[480px]"
      style={{ borderRadius: 32, background: "var(--card)", border: "1px solid var(--border)" }}
    >
      <AnimatePresence mode="wait">
        <motion.div key={step} {...swap} className="absolute inset-0 p-5 md:p-9 flex flex-col">
          {[Posted, Parsed, Checked, Resume, Form, Waiting][step]()}
        </motion.div>
      </AnimatePresence>
    </div>
  )
}

const label = "text-[13px]"
const dim = { color: "var(--ink-dim)" }

function Posted() {
  return (
    <>
      <div className="flex items-center gap-3">
        <span className="size-10 rounded-full grid place-items-center text-sm font-medium" style={{ background: "var(--hi)", color: "#131312" }}>OC</span>
        <div>
          <p className="text-[15px] font-medium">Off-campus drives, 2024 batch</p>
          <p className={label} style={dim}>4,812 members</p>
        </div>
      </div>
      <div className="mt-auto max-w-[92%] rounded-2xl rounded-bl-md p-4 md:p-5" style={{ background: "#ffffff", color: "#131312", border: "1px solid var(--border-warm)" }}>
        <p className="text-[13px] font-medium" style={{ color: "var(--ink-dim)" }}>Riya, admin</p>
        <p className="mt-2 text-[15px] leading-relaxed">
          Kestrel Pay is hiring<br />
          Role: Backend Engineer<br />
          Batch: 2023 / 2024 / 2025<br />
          Experience: 0 to 2 years<br />
          Location: Bengaluru<br />
          Apply: <span className="underline underline-offset-2">forms.gle/kP7xQ2</span>
        </p>
        <p className="mt-2 text-right text-[11px]" style={{ color: "#8b8b84" }}>2:14 AM</p>
      </div>
    </>
  )
}

function Parsed() {
  const rows = [
    ["Company", "Kestrel Pay"],
    ["Role", "Backend Engineer"],
    ["Batch", "2023 to 2025"],
    ["Experience", "0 to 2 years"],
    ["Where to apply", "Google Form"],
    ["Link", "forms.gle/kP7xQ2"],
  ]
  return (
    <>
      <p className={label} style={dim}>What it took from the post</p>
      <dl className="mt-6 flex-1 flex flex-col justify-center">
        {rows.map(([k, v], i) => (
          <motion.div
            key={k}
            className="flex items-baseline justify-between gap-6 py-3"
            style={{ borderTop: "1px solid var(--border)" }}
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.12 + i * 0.07 }}
          >
            <dt className="text-sm" style={dim}>{k}</dt>
            <dd className="text-[17px] text-right" style={{ fontSize: k === "Link" ? 15 : undefined }}>{v}</dd>
          </motion.div>
        ))}
      </dl>
    </>
  )
}

function Checked() {
  const fit = 78
  return (
    <>
      <p className={label} style={dim}>Do you qualify?</p>
      <ul className="mt-6 space-y-3 text-[15px]">
        {["You graduated in 2024. They want 2023 to 2025.", "You have 1 year. They ask 0 to 2."].map((t, i) => (
          <motion.li key={t} className="flex items-start gap-3" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.15 + i * 0.15 }}>
            <Check size={18} className="mt-0.5 shrink-0" style={{ color: "#131312" }} />{t}
          </motion.li>
        ))}
      </ul>
      <div className="mt-auto">
        <div className="flex items-end justify-between">
          <span className={label} style={dim}>How well your skills fit</span>
          <span style={{ fontFamily: "var(--font-serif)", fontWeight: 600, fontSize: 72, lineHeight: 0.8, letterSpacing: "-0.045em" }}>{fit}</span>
        </div>
        <div className="mt-4 flex gap-[3px]">
          {Array.from({ length: 20 }, (_, i) => (
            <motion.span
              key={i}
              className="h-5 flex-1 rounded-[2px]"
              initial={{ background: "rgba(19,19,18,0.08)" }}
              animate={{ background: i < fit / 5 ? "#131312" : "rgba(19,19,18,0.08)" }}
              transition={{ delay: 0.3 + i * 0.03 }}
            />
          ))}
        </div>
        <div className="mt-5 flex flex-wrap gap-2 text-[13px]">
          {["Node.js", "PostgreSQL", "Redis", "AWS"].map((s) => (
            <span key={s} className="rounded-full px-3 py-1" style={{ background: "var(--hi)", color: "#131312" }}>{s}</span>
          ))}
          <span className="rounded-full px-3 py-1 inline-flex items-center gap-1" style={{ background: "rgba(19,19,18,0.05)", color: "var(--ink-dim)" }}>
            <Minus size={12} /> Kafka
          </span>
        </div>
      </div>
    </>
  )
}

function Resume() {
  return (
    <>
      <p className={label} style={dim}>Your resume for this job</p>
      <div className="mt-6 flex-1 flex gap-5 md:gap-7 min-h-0">
        <div className="w-[44%] shrink-0 rounded-md p-4 flex flex-col gap-2" style={{ background: "#ffffff", border: "1px solid var(--border-warm)" }} aria-hidden>
          <span className="h-2.5 w-2/3 rounded-sm" style={{ background: "#131312" }} />
          <span className="h-1.5 w-1/2 rounded-sm" style={{ background: "#8b8b84" }} />
          {[92, 80, 86, 70, 88, 64, 90, 76, 58, 84].map((w, i) => (
            <span
              key={i}
              className="h-1.5 rounded-sm mt-1"
              style={{ width: `${w}%`, background: i === 2 || i === 5 ? "#f3d23f" : "#d6d6d0" }}
            />
          ))}
        </div>
        <div className="flex flex-col justify-center gap-5">
          <div>
            <p className="text-[13px]" style={{ color: "var(--rust)" }}>Reused</p>
            <p className="mt-1 text-[19px] leading-snug" style={{ fontFamily: "var(--font-serif)" }}>
              The one it made for Halcyon Labs&apos; Backend Engineer post
            </p>
          </div>
          <p className="text-sm leading-relaxed" style={dim}>
            Same kind of role, and it already covers 86% of the skills this post asks for. No new resume needed.
          </p>
        </div>
      </div>
    </>
  )
}

function Typed({ text, delay = 0, speed = 28 }: { text: string; delay?: number; speed?: number }) {
  const [n, setN] = useState(() =>
    typeof window !== "undefined" && matchMedia("(prefers-reduced-motion: reduce)").matches ? text.length : 0)
  useEffect(() => {
    if (matchMedia("(prefers-reduced-motion: reduce)").matches) return
    let i = 0, t: ReturnType<typeof setInterval>
    const d = setTimeout(() => { t = setInterval(() => { i++; setN(i); if (i >= text.length) clearInterval(t) }, speed) }, delay)
    return () => { clearTimeout(d); clearInterval(t) }
  }, [text, delay, speed])
  return <>{text.slice(0, n)}</>
}

function Form() {
  const field = "rounded-xl px-3.5 py-2.5 text-[14px] min-h-[42px]"
  const box = { background: "#ffffff", border: "1px solid var(--border-warm)" }
  return (
    <>
      <p className={label} style={dim}>Kestrel Pay application, on Google Forms</p>
      <div className="mt-5 grid grid-cols-2 gap-3">
        <label className="text-[12px]" style={dim}>Full name<div className={field} style={box}><Typed text="Aarav Sharma" /></div></label>
        <label className="text-[12px]" style={dim}>Notice period<div className={field} style={box}><Typed text="Immediate" delay={350} /></div></label>
      </div>
      <label className="mt-3 block text-[12px]" style={dim}>
        Tell us about a production bug you fixed
        <div className={field + " leading-relaxed"} style={box}>
          <Typed delay={700} speed={14} text="Payment webhooks were retried twice when our queue restarted, so some orders were marked paid twice. I added an idempotency key per event and…" />
        </div>
      </label>
      <label className="mt-3 block text-[12px]" style={dim}>
        Can you come for a walk-in on Saturday?
        <div className={field} style={{ background: "rgba(243,210,63,0.18)", border: "1px dashed #c9a400", color: "#131312" }}>
          Only you know this. Asked you on Telegram.
        </div>
      </label>
      <p className="mt-auto pt-3 text-[13px]" style={dim}>Resume attached: Aarav_KestrelPay_Backend.pdf</p>
    </>
  )
}

function Waiting() {
  return (
    <div className="flex-1 -m-5 md:-m-9 p-5 md:p-9 flex flex-col" style={{ background: "#f3d23f", color: "#131312" }}>
      <p className="text-[15px] font-medium" style={{ fontFamily: "var(--font-plex)" }}>Waiting for your yes</p>
      <div className="mt-auto">
        <p style={{ fontFamily: "var(--font-day)", fontWeight: 600, fontSize: "clamp(2.4rem,4.4vw,3.6rem)", letterSpacing: "-0.045em", lineHeight: 0.95 }}>
          Kestrel Pay
        </p>
        <p className="mt-2 text-lg" style={{ fontFamily: "var(--font-plex)" }}>Backend Engineer, Bengaluru</p>
        <div className="mt-8 flex items-center gap-5 text-[15px]" style={{ fontFamily: "var(--font-plex)" }}>
          <span className="inline-flex items-center gap-2"><span className="kbd">A</span> apply</span>
          <span className="inline-flex items-center gap-2"><span className="kbd">S</span> skip</span>
          <span className="ml-auto">Fit 78</span>
        </div>
      </div>
    </div>
  )
}
