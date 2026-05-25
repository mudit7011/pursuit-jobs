"use client"
import { motion } from "framer-motion"
import { Globe, Target, FileText, RefreshCw, Bell, UserCircle2 } from "lucide-react"
import { SmokeBackground } from "./spooky-smoke-animation"

const FEATURES = [
  {
    icon: Globe,
    title: "Universal Form Filling",
    desc: "Playwright automation handles Greenhouse, Lever, Workday, Ashby, Microsoft Forms — and any unknown ATS. Not pre-built templates. Actual browser control.",
    accent: true,
  },
  {
    icon: Target,
    title: "Eligibility Checker",
    desc: "Regex for batch year and experience (free, instant). Gemini for skill overlap (only if you pass the first two). Cheapest-first ordering by design.",
  },
  {
    icon: FileText,
    title: "Resume Tailoring",
    desc: "Your LaTeX template, freshly compiled per job. Keywords extracted from the JD, injected into the right sections. Not one-size-fits-all.",
    accent: true,
  },
  {
    icon: RefreshCw,
    title: "Duplicate Prevention",
    desc: "SQLite tracker with COLLATE NOCASE matching. Same company, same role, applied before? Silently skipped. No double-applying ever.",
  },
  {
    icon: Bell,
    title: "Telegram Notifications",
    desc: "Applied: you're notified. CAPTCHA blocked it: you're notified to apply manually. Every outcome surfaces back to where the job came from.",
    accent: true,
  },
  {
    icon: UserCircle2,
    title: "Profile-Driven",
    desc: "One profile.json drives everything — name, skills, graduation year, expected CTC. The bot applies as you, not as a generic template.",
  },
]

export default function Features() {
  return (
    <section
      id="features"
      className="relative py-32 px-8 md:px-14 overflow-hidden"
    >
      <div className="absolute inset-0 pointer-events-none" style={{ opacity: 0.18, mixBlendMode: "screen" }} aria-hidden="true">
        <SmokeBackground smokeColor="#EC4E02" />
      </div>
      <div className="absolute inset-0 pointer-events-none" style={{ background: "linear-gradient(to bottom, var(--bg) 0%, transparent 12%, transparent 88%, var(--bg) 100%)" }} aria-hidden="true" />

      <div className="relative z-10 max-w-6xl mx-auto">

        <motion.p
          className="section-eyebrow mb-6"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
        >
          Capabilities
        </motion.p>

        <motion.h2
          className="section-heading mb-20"
          style={{ fontSize: "clamp(2.8rem, 6vw, 5.5rem)" }}
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
        >
          Built for the<br />
          <span style={{ color: "var(--ink-dim)", fontStyle: "italic" }}>modern hunt.</span>
        </motion.h2>

        <div className="grid md:grid-cols-3">
          {FEATURES.map(({ icon: Icon, title, desc, accent }, i) => (
            <motion.div
              key={title}
              className="p-8 feature-card"
              style={{
                borderTop: "1px solid var(--border)",
                borderRight: i % 3 !== 2 ? "1px solid var(--border)" : "none",
              }}
              initial={{ opacity: 0, y: 8 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.1 }}
              transition={{ duration: 0.18, delay: i * 0.04, ease: "easeOut" }}
            >
              <div
                className="w-9 h-9 rounded-lg flex items-center justify-center mb-6 transition-all duration-300"
                style={{
                  background: accent ? "var(--rust-dim)" : "rgba(240,235,227,0.03)",
                  border: `1px solid ${accent ? "rgba(236,78,2,0.2)" : "var(--border)"}`,
                }}
              >
                <Icon
                  size={15}
                  strokeWidth={1.5}
                  style={{ color: accent ? "var(--rust)" : "var(--ink-dim)" }}
                />
              </div>

              <h3
                className="mb-2.5 leading-snug"
                style={{
                  fontFamily: "var(--font-serif)",
                  fontWeight: 500,
                  fontSize: "1rem",
                  color: "var(--ink)",
                  letterSpacing: "-0.01em",
                }}
              >
                {title}
              </h3>
              <p
                className="text-xs leading-relaxed"
                style={{ color: "var(--ink-dim)", fontFamily: "var(--font-body)", fontWeight: 300 }}
              >
                {desc}
              </p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  )
}
