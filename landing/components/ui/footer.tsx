"use client"
import { motion } from "framer-motion"
import { GitBranch, ArrowUpRight, Link2 } from "lucide-react"

export default function Footer() {
  return (
    <footer style={{ borderTop: "1px solid var(--border)", overflow: "hidden" }}>

      {/* ── Main content ──────────────────────────────── */}
      <div className="max-w-6xl mx-auto px-8 md:px-14 pt-24 pb-20 grid md:grid-cols-2 gap-16 items-end">

        {/* Left — statement */}
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
        >
          <p style={{
            fontFamily: "var(--font-mono)",
            fontSize: "9px",
            letterSpacing: "0.28em",
            textTransform: "uppercase",
            color: "var(--rust)",
            marginBottom: "1.5rem",
          }}>
            Open Source · Free Forever
          </p>

          <h2 style={{
            fontFamily: "var(--font-serif)",
            fontWeight: 500,
            fontSize: "clamp(2.4rem, 4.5vw, 4.2rem)",
            lineHeight: 1.08,
            letterSpacing: "-0.025em",
            color: "var(--ink)",
            marginBottom: "2.5rem",
          }}>
            Because the job hunt<br />
            <span style={{ color: "var(--ink-dim)", fontStyle: "italic" }}>
              shouldn&apos;t be work.
            </span>
          </h2>

          <motion.a
            href="https://github.com"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2.5 px-6 py-3 rounded-full text-sm font-medium"
            style={{
              background: "var(--ink)",
              color: "var(--bg)",
              fontFamily: "var(--font-body)",
              textDecoration: "none",
            }}
            whileHover={{ scale: 1.04 }}
            whileTap={{ scale: 0.97 }}
            transition={{ type: "tween", duration: 0.15 }}
          >
            <GitBranch size={13} strokeWidth={2} />
            Star on GitHub
            <ArrowUpRight size={13} />
          </motion.a>
        </motion.div>

        {/* Right — terminal card */}
        <motion.div
          className="flex flex-col gap-8 md:items-end"
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8, delay: 0.15, ease: [0.22, 1, 0.36, 1] }}
        >
          {/* Terminal log card */}
          <div style={{
            width: "100%",
            maxWidth: "360px",
            borderRadius: "14px",
            border: "1px solid var(--border-warm)",
            background: "rgba(22,18,16,0.7)",
            overflow: "hidden",
          }}>
            {/* Title bar */}
            <div style={{
              display: "flex",
              alignItems: "center",
              gap: "6px",
              padding: "10px 14px",
              borderBottom: "1px solid var(--border)",
              background: "rgba(240,235,227,0.02)",
            }}>
              <span style={{ width: 9, height: 9, borderRadius: "50%", background: "rgba(240,235,227,0.08)", display: "inline-block" }} />
              <span style={{ width: 9, height: 9, borderRadius: "50%", background: "rgba(240,235,227,0.08)", display: "inline-block" }} />
              <span style={{ width: 9, height: 9, borderRadius: "50%", background: "rgba(236,78,2,0.4)", display: "inline-block" }} />
              <span style={{ fontFamily: "var(--font-mono)", fontSize: "10px", color: "var(--ink-muted)", marginLeft: "6px", letterSpacing: "0.08em" }}>
                bot.log
              </span>
            </div>
            {/* Log lines */}
            <div style={{ padding: "14px 16px", display: "flex", flexDirection: "column", gap: "7px" }}>
              {[
                { t: "10:24:01", c: "var(--ink-muted)", txt: "Watching 12 Telegram groups..." },
                { t: "10:25:18", c: "var(--ink-dim)",   txt: "New post → Stripe · Backend Eng" },
                { t: "10:25:18", c: "var(--rust)",      txt: "Eligible · 81% skill match" },
                { t: "10:25:19", c: "var(--ink-dim)",   txt: "Resume compiled → MuditKumar_Stripe.pdf" },
                { t: "10:25:22", c: "#6ee7b7",          txt: "✓ Applied · Greenhouse form filled" },
              ].map(({ t, c, txt }) => (
                <div key={t+txt} style={{ display: "flex", gap: "10px", alignItems: "baseline" }}>
                  <span style={{ fontFamily: "var(--font-mono)", fontSize: "9px", color: "var(--ink-muted)", flexShrink: 0 }}>{t}</span>
                  <span style={{ fontFamily: "var(--font-mono)", fontSize: "10px", color: c, lineHeight: 1.5 }}>{txt}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Social + copyright */}
          <div className="flex flex-col md:items-end gap-3">
            <div className="flex items-center gap-5">
              <a href="https://github.com" target="_blank" rel="noopener noreferrer" className="footer-social-link">
                <GitBranch size={11} strokeWidth={1.5} />
                GitHub
              </a>
              <a href="https://linkedin.com/in/mudit-dev" target="_blank" rel="noopener noreferrer" className="footer-social-link">
                <Link2 size={11} strokeWidth={1.5} />
                LinkedIn
              </a>
            </div>
            <p style={{ fontFamily: "var(--font-mono)", fontSize: "9px", letterSpacing: "0.18em", color: "var(--ink-muted)", textTransform: "uppercase" }}>
              Mudit Kumar · MIT · 2026
            </p>
          </div>
        </motion.div>
      </div>

      {/* ── Marquee strip ─────────────────────────────── */}
      <div
        className="footer-marquee-wrap"
        style={{
          borderTop: "1px solid var(--border)",
          borderBottom: "1px solid var(--border)",
          overflow: "hidden",
          padding: "0",
          position: "relative",
        }}
      >
        {/* left/right fade masks */}
        <div style={{
          position: "absolute", inset: 0, zIndex: 2, pointerEvents: "none",
          background: "linear-gradient(to right, var(--bg) 0%, transparent 8%, transparent 92%, var(--bg) 100%)",
        }} />
        <div className="footer-marquee-track" style={{ display: "flex", width: "max-content" }}>
          {Array.from({ length: 10 }).map((_, i) => (
            <span key={i} className="footer-marquee-word">
              AUTOPILOT&nbsp;&nbsp;·&nbsp;&nbsp;
            </span>
          ))}
        </div>
      </div>

    </footer>
  )
}
