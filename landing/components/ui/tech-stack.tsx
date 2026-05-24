"use client"
import { motion } from "framer-motion"

const TECH = [
  { name: "Python", tag: "core" },
  { name: "Playwright", tag: "automation" },
  { name: "Gemini 2.5 Flash", tag: "AI" },
  { name: "SQLite", tag: "storage" },
  { name: "Telegram Bot API", tag: "transport" },
  { name: "LaTeX", tag: "typesetting" },
]

export default function TechStack() {
  return (
    <section
      id="stack"
      className="py-24 px-8 md:px-14"
      style={{ borderTop: "1px solid var(--border)" }}
    >
      <div className="max-w-6xl mx-auto flex flex-col md:flex-row md:items-center gap-10">
        <p
          className="shrink-0 md:w-32"
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: "9px",
            letterSpacing: "0.25em",
            textTransform: "uppercase",
            color: "var(--ink-muted)",
          }}
        >
          Built with
        </p>
        <div className="flex flex-wrap gap-2">
          {TECH.map(({ name, tag }, i) => (
            <motion.div
              key={name}
              className="flex items-center gap-2.5 px-4 py-2 rounded-full transition-all duration-200"
              style={{
                border: "1px solid var(--border-warm)",
                background: "rgba(240,235,227,0.02)",
              }}
              initial={{ opacity: 0, scale: 0.9 }}
              whileInView={{ opacity: 1, scale: 1 }}
              viewport={{ once: true }}
              transition={{ duration: 0.4, delay: i * 0.06 }}
              whileHover={{
                borderColor: "rgba(236,78,2,0.3)",
                background: "rgba(236,78,2,0.06)",
              }}
            >
              <span
                className="text-sm"
                style={{ color: "var(--ink)", fontFamily: "var(--font-body)", fontWeight: 400 }}
              >
                {name}
              </span>
              <span
                className="text-[9px] tracking-widest uppercase px-1.5 py-0.5 rounded"
                style={{
                  color: "var(--rust)",
                  background: "var(--rust-dim)",
                  fontFamily: "var(--font-mono)",
                }}
              >
                {tag}
              </span>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  )
}
