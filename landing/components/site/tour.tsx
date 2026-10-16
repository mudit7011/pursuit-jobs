"use client"
import { useState } from "react"
import { AnimatePresence, motion } from "framer-motion"
import { Moon, Sun } from "lucide-react"
import Shot from "./shot"

const SCREENS = [
  { id: "overview", label: "Overview", title: "What needs you today, first",
    points: ["The top line says what to do next, in plain words", "Yellow tile: jobs waiting for your yes", "A year of applying at a glance, with your streaks"] },
  { id: "queue", label: "Review queue", title: "One job at a time, decided in a second",
    points: ["Fit score, why it fits and which resume it'll send", "A to apply, S to skip, J and K to move", "Ten seconds to undo before anything goes out"] },
  { id: "board", label: "Applications", title: "Every application, by where it stands",
    points: ["Drag a card when a company replies", "A nudge when one goes quiet for a week", "Open any card to see exactly what the form got"] },
  { id: "attention", label: "Needs you", title: "Only the questions only you can answer",
    points: ["Answer once and it's saved for every form after", "Stuck forms open for you to finish, captcha and all", "Nothing here means nothing is blocked"] },
  { id: "insights", label: "Insights", title: "What's working, from your own numbers",
    points: ["Which boards actually reply", "Why jobs were skipped, so you can widen the net", "Applied versus found, week by week"] },
  { id: "settings", label: "Settings", title: "You decide how bold it gets",
    points: ["Ask first, or apply on its own above a fit score", "Upload a new resume and check the draft first", "Daily limits for every job board"] },
]

export default function Tour() {
  const [i, setI] = useState(0)
  const [dark, setDark] = useState(false)
  const s = SCREENS[i]
  return (
    <section className="px-5 md:px-14 pb-28">
      <div className="mx-auto max-w-6xl">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div role="tablist" aria-label="Dashboard screens" className="flex flex-wrap gap-1 rounded-[20px] p-1.5" style={{ background: "var(--day-surface)" }}>
            {SCREENS.map((x, k) => (
              <button key={x.id} role="tab" aria-selected={k === i} onClick={() => setI(k)}
                className="rounded-[14px] px-4 py-2 text-[14px] transition-colors"
                style={k === i ? { background: "var(--tile)", color: "var(--tile-ink)" } : { color: "var(--day-dim)" }}>
                {x.label}
              </button>
            ))}
          </div>
          <button onClick={() => setDark((d) => !d)} className="inline-flex h-11 items-center gap-2 rounded-[14px] px-4 text-[14px]" style={{ background: "var(--day-surface)" }} aria-pressed={dark}>
            {dark ? <Sun size={16} /> : <Moon size={16} />} {dark ? "Light mode" : "Dark mode"}
          </button>
        </div>

        <div className="mt-8 grid gap-10 lg:grid-cols-[minmax(0,1fr)_19rem] lg:items-start">
          <AnimatePresence mode="wait">
            <motion.div key={s.id + dark} initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }} transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}>
              <Shot src={`/shots/${s.id}-${dark ? "dark" : "light"}.webp`} alt={`${s.label} screen of the Pursuit dashboard`} />
            </motion.div>
          </AnimatePresence>
          <div className="lg:sticky lg:top-28" role="tabpanel">
            <h3 className="text-[28px] leading-tight font-semibold tracking-[-0.035em]" style={{ fontFamily: "var(--font-day)" }}>{s.title}</h3>
            <ul className="mt-6 space-y-4">
              {s.points.map((p) => (
                <li key={p} className="flex gap-3 text-[16px] leading-relaxed" style={{ color: "var(--day-dim)" }}>
                  <span className="mt-2 size-2 shrink-0 rounded-full" style={{ background: "var(--hi)" }} aria-hidden />{p}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </section>
  )
}
