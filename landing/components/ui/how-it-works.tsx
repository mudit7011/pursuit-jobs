"use client"
import { motion } from "framer-motion"
import { MessageSquare, ScanSearch, CheckCircle2 } from "lucide-react"
import AnimatedCardStack from "./animate-card-animation"
import { SmokeBackground } from "./spooky-smoke-animation"

const STEPS = [
  {
    icon: MessageSquare,
    n: "01",
    title: "Telegram drops a job",
    desc: "The bot watches your groups 24/7. The instant a job post appears, it's intercepted, parsed, and queued — no human in the loop.",
  },
  {
    icon: ScanSearch,
    n: "02",
    title: "Eligibility checked, resume compiled",
    desc: "Batch year and experience verified by regex. Skills overlap scored by Gemini. If you qualify, your LaTeX template is recompiled with targeted keywords.",
  },
  {
    icon: CheckCircle2,
    n: "03",
    title: "Form filled, application sent",
    desc: "Playwright opens the form — Greenhouse, Lever, Workday, anything — extracts every field, generates answers, uploads your PDF, and submits.",
  },
]

export default function HowItWorks() {
  return (
    <section id="how-it-works" className="relative py-32 px-8 md:px-14 overflow-hidden">
      {/* Smoke canvas */}
      <div className="absolute inset-0 pointer-events-none" style={{ opacity: 0.18, mixBlendMode: "screen" }} aria-hidden="true">
        <SmokeBackground smokeColor="#EC4E02" />
      </div>
      {/* Gradient fade — top & bottom bleed into bg so no hard edge */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background: "linear-gradient(to bottom, var(--bg) 0%, transparent 8%, transparent 88%, var(--bg) 100%)",
        }}
        aria-hidden="true"
      />
      <div className="relative z-10 max-w-6xl mx-auto">

        <motion.p
          className="section-eyebrow mb-6"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
        >
          Process
        </motion.p>

        <motion.h2
          className="section-heading mb-16"
          style={{ fontSize: "clamp(2.8rem, 5vw, 5rem)" }}
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
        >
          Three steps.<br />
          <span style={{ color: "var(--ink-dim)", fontStyle: "italic" }}>Zero effort.</span>
        </motion.h2>

        {/* 2-col layout: steps left, animated card right */}
        <div className="grid md:grid-cols-2 gap-16 md:gap-24 items-start">

          {/* Left: steps */}
          <div className="flex flex-col">
            {STEPS.map(({ icon: Icon, n, title, desc }, i) => (
              <motion.div
                key={n}
                className="py-8 flex gap-6"
                style={{ borderTop: "1px solid var(--border)" }}
                initial={{ opacity: 0, x: -20 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.55, delay: i * 0.1, ease: [0.22, 1, 0.36, 1] }}
              >
                {/* Step number */}
                <span
                  style={{
                    fontFamily: "var(--font-serif)",
                    fontWeight: 500,
                    fontSize: "1.5rem",
                    color: "var(--border-warm)",
                    lineHeight: 1,
                    minWidth: "2.5rem",
                    paddingTop: "2px",
                  }}
                >
                  {n}
                </span>

                <div className="flex-1">
                  {/* Icon */}
                  <div
                    className="w-8 h-8 rounded-lg flex items-center justify-center mb-4"
                    style={{
                      background: "var(--rust-dim)",
                      border: "1px solid rgba(236,78,2,0.2)",
                    }}
                  >
                    <Icon size={15} strokeWidth={1.5} style={{ color: "var(--rust)" }} />
                  </div>

                  <h3
                    className="mb-2 leading-snug"
                    style={{
                      fontFamily: "var(--font-serif)",
                      fontWeight: 500,
                      fontSize: "1.05rem",
                      color: "var(--ink)",
                      letterSpacing: "-0.01em",
                    }}
                  >
                    {title}
                  </h3>
                  <p
                    className="text-sm leading-relaxed"
                    style={{ color: "var(--ink-dim)", fontFamily: "var(--font-body)", fontWeight: 300 }}
                  >
                    {desc}
                  </p>
                </div>
              </motion.div>
            ))}
          </div>

          {/* Right: animated live card stack */}
          <motion.div
            className="flex flex-col items-center justify-start pt-4 md:pt-0 md:sticky md:top-28"
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8, delay: 0.2, ease: [0.22, 1, 0.36, 1] }}
          >
            {/* Label above */}
            <div className="flex items-center gap-2 mb-6 self-start">
              <motion.div
                className="w-1.5 h-1.5 rounded-full"
                style={{ background: "var(--rust)" }}
                animate={{ opacity: [1, 0.3, 1] }}
                transition={{ duration: 2, repeat: Infinity }}
              />
              <span
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: "9px",
                  letterSpacing: "0.2em",
                  textTransform: "uppercase",
                  color: "var(--ink-dim)",
                }}
              >
                Live applications
              </span>
            </div>

            <AnimatedCardStack />
          </motion.div>
        </div>
      </div>
    </section>
  )
}

