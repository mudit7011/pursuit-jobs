"use client"
import { motion } from "framer-motion"

const LINES = [
  { t: "cmd",     v: "python -m src.main" },
  { t: "muted",   v: "→  Watching Telegram..." },
  { t: "blank",   v: "" },
  { t: "rust",    v: "[+] Job detected  ·  SynthioLabs — Software Engineer" },
  { t: "muted",   v: "    parsing with Gemini 2.5 Flash..." },
  { t: "ok",      v: "✓   role: SWE   batch: 2024   type: web_form" },
  { t: "blank",   v: "" },
  { t: "rust",    v: "[>] Eligibility check" },
  { t: "ok",      v: "✓   batch 2024 → match" },
  { t: "ok",      v: "✓   experience: 0–1 yrs required, you have 2" },
  { t: "ok",      v: "✓   skills overlap: 74%  →  eligible" },
  { t: "blank",   v: "" },
  { t: "rust",    v: "[>] Compiling resume..." },
  { t: "ok",      v: "✓   SynthioLabs_SWE.pdf  (tailored)" },
  { t: "blank",   v: "" },
  { t: "rust",    v: "[>] Opening Greenhouse form via Playwright" },
  { t: "muted",   v: "    12 fields extracted  ·  generating answers..." },
  { t: "muted",   v: "    name  email  phone  linkedin  resume  ✓ ✓ ✓ ✓ ✓" },
  { t: "ok",      v: "✓   submitted" },
  { t: "blank",   v: "" },
  { t: "success", v: ">> Applied: SynthioLabs — SWE  →  logged  →  notified" },
]

const C: Record<string, string> = {
  cmd:     "#f0ebe3",
  muted:   "#3a3632",
  rust:    "#EC4E02",
  ok:      "#6ee7b7",
  success: "#6ee7b7",
  blank:   "",
}

export default function Terminal() {
  return (
    <section className="py-32 px-8 md:px-14">
      <div className="max-w-6xl mx-auto">

        <motion.p
          className="section-eyebrow mb-6"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
        >
          Live output
        </motion.p>

        <motion.h2
          className="section-heading mb-16"
          style={{ fontSize: "clamp(2.8rem, 6vw, 5.5rem)" }}
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
        >
          Watch it<br />
          <span style={{ color: "var(--ink-dim)", fontStyle: "italic" }}>work.</span>
        </motion.h2>

        <motion.div
          className="rounded-2xl overflow-hidden"
          style={{ border: "1px solid var(--border)", background: "#0a0806" }}
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.7, delay: 0.1 }}
        >
          {/* Header bar */}
          <div
            className="flex items-center gap-2 px-5 py-4"
            style={{ borderBottom: "1px solid var(--border)", background: "rgba(240,235,227,0.02)" }}
          >
            <div className="w-3 h-3 rounded-full" style={{ background: "#ff5f57" }} />
            <div className="w-3 h-3 rounded-full" style={{ background: "#ffbd2e" }} />
            <div className="w-3 h-3 rounded-full" style={{ background: "#28ca42" }} />
            <span
              className="text-xs ml-4"
              style={{ color: "var(--ink-muted)", fontFamily: "var(--font-mono)" }}
            >
              job-autopilot — python -m src.main
            </span>
            <div className="ml-auto flex items-center gap-1.5">
              <motion.div
                className="w-1.5 h-1.5 rounded-full"
                style={{ background: "var(--rust)" }}
                animate={{ opacity: [1, 0.3, 1] }}
                transition={{ duration: 2, repeat: Infinity }}
              />
              <span
                className="text-[10px] tracking-widest uppercase"
                style={{ color: "var(--rust)", fontFamily: "var(--font-mono)" }}
              >
                running
              </span>
            </div>
          </div>

          {/* Output */}
          <div
            className="p-8"
            style={{ fontFamily: "var(--font-mono)", fontSize: "12.5px", lineHeight: "2.1" }}
          >
            {LINES.map((line, i) => (
              <motion.div
                key={i}
                style={{ color: C[line.t] }}
                initial={{ opacity: 0, x: -4 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.25, delay: 0.04 + i * 0.04 }}
              >
                {line.t === "cmd"
                  ? <><span style={{ color: "var(--ink-muted)" }}>$ </span>{line.v}</>
                  : line.v || <>&nbsp;</>}
              </motion.div>
            ))}
          </div>
        </motion.div>
      </div>
    </section>
  )
}
