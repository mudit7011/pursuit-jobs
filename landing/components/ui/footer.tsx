"use client"
import { motion } from "framer-motion"
import { GitBranch, Link2, ArrowUpRight } from "lucide-react"

export default function Footer() {
  return (
    <footer
      className="py-16 px-8 md:px-14"
      style={{ borderTop: "1px solid var(--border)" }}
    >
      <motion.div
        className="max-w-6xl mx-auto flex flex-col md:flex-row md:items-end justify-between gap-8"
        initial={{ opacity: 0, y: 16 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.6 }}
      >
        {/* Left */}
        <div>
          <div className="flex items-center gap-2 mb-4">
            <motion.span
              className="w-1.5 h-1.5 rounded-full"
              style={{ background: "var(--rust)" }}
              animate={{ opacity: [1, 0.4, 1] }}
              transition={{ duration: 2.5, repeat: Infinity }}
            />
            <span
              style={{
                fontFamily: "var(--font-serif)",
                fontWeight: 500,
                color: "var(--ink)",
                fontSize: "15px",
                letterSpacing: "0.02em",
              }}
            >
              JobAutopilot
            </span>
          </div>
          <p
            className="text-xs leading-relaxed max-w-xs"
            style={{ color: "var(--ink-dim)", fontFamily: "var(--font-body)", fontWeight: 300 }}
          >
            Made with obsession and too many rejected applications.<br />
            Because the job hunt shouldn&apos;t be a full-time job.
          </p>
        </div>

        {/* Right */}
        <div className="flex flex-col items-start md:items-end gap-4">
          <div className="flex items-center gap-5">
            <a
              href="https://github.com"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1.5 text-xs transition-colors duration-200 group"
              style={{ color: "var(--ink-dim)", fontFamily: "var(--font-mono)" }}
              onMouseEnter={e => (e.currentTarget.style.color = "var(--ink)")}
              onMouseLeave={e => (e.currentTarget.style.color = "var(--ink-dim)")}
            >
              <GitBranch size={12} strokeWidth={1.5} />
              GitHub
              <ArrowUpRight size={10} className="opacity-0 group-hover:opacity-100 transition-opacity" />
            </a>
            <a
              href="https://linkedin.com"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1.5 text-xs transition-colors duration-200 group"
              style={{ color: "var(--ink-dim)", fontFamily: "var(--font-mono)" }}
              onMouseEnter={e => (e.currentTarget.style.color = "var(--ink)")}
              onMouseLeave={e => (e.currentTarget.style.color = "var(--ink-dim)")}
            >
              <Link2 size={12} strokeWidth={1.5} />
              LinkedIn
              <ArrowUpRight size={10} className="opacity-0 group-hover:opacity-100 transition-opacity" />
            </a>
          </div>
          <p
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: "10px",
              letterSpacing: "0.2em",
              color: "var(--ink-muted)",
            }}
          >
            BUILT BY MUDIT KUMAR · MIT · 2024
          </p>
        </div>
      </motion.div>
    </footer>
  )
}
