"use client"
import { useCallback, useEffect, useRef, useState } from "react"
import { AnimatePresence, motion, useInView } from "framer-motion"
import { RotateCcw } from "lucide-react"

type Job = { company: string; role: string; where: string; via: string; fit: number; why: string; resume: string }

const JOBS: Job[] = [
  { company: "Kestrel Pay", role: "Backend Engineer", where: "Bengaluru", via: "Google Form", fit: 78, why: "Node.js, PostgreSQL and Redis are all on your resume", resume: "Reused from Halcyon Labs" },
  { company: "Juniper Health", role: "Software Engineer I", where: "Remote", via: "Instahyre", fit: 84, why: "Your billing service project matches their payments team", resume: "Tailored for this job" },
  { company: "Orbit Freight", role: "Full Stack Developer", where: "Pune", via: "Naukri", fit: 71, why: "React and Node.js match. They also want Go, which you don't list", resume: "Tailored for this job" },
  { company: "Tandem Learning", role: "SDE Intern to FTE", where: "Gurugram", via: "Wellfound", fit: 66, why: "Batch matches. Smaller overlap on their Python stack", resume: "Reused from Lumen Analytics" },
  { company: "Quill & Ledger", role: "Associate Engineer", where: "Hyderabad", via: "Lever", fit: 81, why: "Asks for TypeScript and AWS, both in your projects", resume: "Tailored for this job" },
  { company: "Northwind Labs", role: "Product Engineer", where: "Bengaluru", via: "Email", fit: 74, why: "Small team, wants someone who has shipped end to end", resume: "Reused from Kestrel Pay" },
]

type Decision = { job: Job; yes: boolean }

export function QueueDemo() {
  const root = useRef<HTMLDivElement>(null)
  const inView = useInView(root, { amount: 0.4 })
  const [done, setDone] = useState<Decision[]>([])
  const [stamp, setStamp] = useState<"yes" | "no" | null>(null)
  const started = useRef<number | null>(null)
  const [took, setTook] = useState(0)
  const i = done.length
  const job = JOBS[i]
  const finished = i >= JOBS.length

  const decide = useCallback((yes: boolean) => {
    if (finished || stamp) return
    started.current ??= performance.now()
    setStamp(yes ? "yes" : "no")
    setTimeout(() => {
      setStamp(null)
      setDone((d) => [...d, { job: JOBS[d.length], yes }])
    }, 420)
  }, [finished, stamp])

  useEffect(() => {
    if (finished && started.current != null) setTook(Math.max(1, Math.round((performance.now() - started.current) / 1000)))
  }, [finished])

  useEffect(() => {
    if (!inView) return
    const onKey = (e: KeyboardEvent) => {
      if (e.metaKey || e.ctrlKey || e.altKey) return
      if ((e.target as HTMLElement)?.closest("input, textarea")) return
      if (e.key === "a" || e.key === "A") { e.preventDefault(); decide(true) }
      if (e.key === "s" || e.key === "S") { e.preventDefault(); decide(false) }
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [inView, decide])

  const reset = () => { setDone([]); setTook(0); started.current = null }
  const approved = done.filter((d) => d.yes).length

  return (
    <section className="px-5 md:px-14 pb-28">
      <div ref={root} className="max-w-6xl mx-auto grid lg:grid-cols-[minmax(0,1.35fr)_minmax(0,1fr)] gap-4">
        {/* The queue card: the same one the dashboard shows */}
        <div className="day-tile relative overflow-hidden p-6 md:p-9 min-h-[460px] flex flex-col">
          <div className="flex items-center justify-between text-sm" style={{ color: "var(--day-dim)" }}>
            <span>Your review queue</span>
            <span className="tabular-nums" aria-live="polite">{finished ? "All reviewed" : `${i + 1} of ${JOBS.length}`}</span>
          </div>

          <AnimatePresence mode="wait">
            {!finished ? (
              <motion.div
                key={job.company}
                className="relative flex-1 flex flex-col"
                initial={{ opacity: 0, y: 18 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, x: stamp === "no" ? -40 : 40 }}
                transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
              >
                <div className="mt-10">
                  <p className="day-display" style={{ fontSize: "clamp(2.4rem, 5vw, 4.2rem)" }}>{job.company}</p>
                  <p className="mt-2 text-lg" style={{ color: "var(--day-dim)" }}>{job.role}, {job.where}</p>
                </div>
                <dl className="mt-8 grid sm:grid-cols-3 gap-5 text-[15px]">
                  <div><dt className="text-[13px]" style={{ color: "var(--day-faint)" }}>Fit</dt><dd className="mt-1.5"><Fit score={job.fit} /></dd></div>
                  <div><dt className="text-[13px]" style={{ color: "var(--day-faint)" }}>Applies through</dt><dd className="mt-1">{job.via}</dd></div>
                  <div><dt className="text-[13px]" style={{ color: "var(--day-faint)" }}>Resume</dt><dd className="mt-1">{job.resume}</dd></div>
                </dl>
                <p className="mt-6 max-w-lg text-[15px] leading-relaxed" style={{ color: "var(--day-dim)" }}>{job.why}.</p>

                <div className="mt-auto pt-8 flex gap-3">
                  <button
                    onClick={() => decide(true)}
                    className="h-12 px-6 rounded-[14px] font-medium inline-flex items-center gap-3 transition-transform active:translate-y-px"
                    style={{ background: "var(--tile)", color: "var(--tile-ink)" }}
                  >
                    Apply <span className="kbd">A</span>
                  </button>
                  <button
                    onClick={() => decide(false)}
                    className="h-12 px-6 rounded-[14px] font-medium inline-flex items-center gap-3 transition-colors"
                    style={{ border: "1px solid var(--day-line)" }}
                  >
                    Skip <span className="kbd">S</span>
                  </button>
                </div>

                <AnimatePresence>
                  {stamp && (
                    <motion.span
                      className="pointer-events-none absolute right-2 top-16 rounded-xl px-4 py-2 day-display"
                      style={{
                        fontSize: 34,
                        border: "3px solid var(--day-ink)",
                        color: "var(--day-ink)",
                        background: stamp === "yes" ? "var(--hi)" : "var(--day-surface)",
                      }}
                      initial={{ opacity: 0, scale: 1.6, rotate: -14 }}
                      animate={{ opacity: 1, scale: 1, rotate: -8 }}
                      transition={{ type: "spring", stiffness: 500, damping: 22 }}
                    >
                      {stamp === "yes" ? "Applying" : "Skipped"}
                    </motion.span>
                  )}
                </AnimatePresence>
              </motion.div>
            ) : (
              <motion.div key="done" className="flex-1 flex flex-col" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                <p className="mt-10 day-display" style={{ fontSize: "clamp(2.4rem, 5vw, 4.2rem)" }}>
                  That took you {took} {took === 1 ? "second" : "seconds"}.
                </p>
                <p className="mt-4 max-w-md text-lg leading-relaxed" style={{ color: "var(--day-dim)" }}>
                  {approved
                    ? `The bot sends the ${approved === 1 ? "one" : approved} you said yes to now. You'll hear back on Telegram when each goes through.`
                    : "Nothing goes out today. It keeps looking, and tomorrow's jobs land here."}
                </p>
                <button
                  onClick={reset}
                  className="mt-auto self-start h-11 px-5 rounded-[14px] inline-flex items-center gap-2 text-[15px]"
                  style={{ border: "1px solid var(--day-line)" }}
                >
                  <RotateCcw size={15} /> Review them again
                </button>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* What you decided, as it piles up */}
        <div className="flex flex-col gap-4">
          <div className="rounded-[28px] p-6 md:p-8 flex-1" style={{ background: "var(--hi)" }}>
            <p className="text-sm font-medium">Try it</p>
            <p className="mt-3 text-[22px] leading-snug" style={{ fontFamily: "var(--font-day)", fontWeight: 500, letterSpacing: "-0.025em" }}>
              Press A to apply and S to skip, the same keys the dashboard uses. Each job already has its resume and answers ready.
            </p>
          </div>
          <div className="day-tile p-6 md:p-8 min-h-[200px]">
            <p className="text-sm" style={{ color: "var(--day-dim)" }}>Decided so far</p>
            <ul className="mt-4 space-y-2.5 text-[15px]">
              {done.length === 0 && <li style={{ color: "var(--day-faint)" }}>Nothing yet.</li>}
              {done.map((d) => (
                <motion.li key={d.job.company} className="flex justify-between gap-4" initial={{ opacity: 0, x: -6 }} animate={{ opacity: 1, x: 0 }}>
                  <span className="truncate">{d.job.company}</span>
                  <span className="rounded-full px-2.5 py-0.5 text-[13px]" style={d.yes ? { background: "var(--hi)" } : { color: "var(--day-faint)" }}>{d.yes ? "Applying" : "Skipped"}</span>
                </motion.li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </section>
  )
}

export function Fit({ score }: { score: number }) {
  return (
    <span className="inline-flex items-center gap-2" role="img" aria-label={`Fit ${score} out of 100`}>
      <span className="inline-flex gap-[2px]" aria-hidden>
        {Array.from({ length: 10 }, (_, i) => (
          <span key={i} className="h-3 w-1.5 rounded-[1px]" style={{ background: i < Math.round(score / 10) ? "var(--day-ink)" : "var(--day-line)" }} />
        ))}
      </span>
      <span className="font-medium tabular-nums">{score}</span>
    </span>
  )
}
