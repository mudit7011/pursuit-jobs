"use client"
import { useState, Suspense, lazy, useEffect } from "react"
import { motion } from "framer-motion"
import { ArrowRight } from "lucide-react"

const Dithering = lazy(() =>
  import("@paper-design/shaders-react").then((mod) => ({ default: mod.Dithering }))
)

const PHRASES = ["sleep better.", "land faster.", "stress less.", "win more."]

function TypewriterCycler() {
  const [phraseIdx, setPhraseIdx] = useState(0)
  const [displayed, setDisplayed] = useState("")
  const [deleting, setDeleting] = useState(false)
  const [cursorOn, setCursorOn] = useState(true)

  useEffect(() => {
    const t = setInterval(() => setCursorOn(v => !v), 530)
    return () => clearInterval(t)
  }, [])

  useEffect(() => {
    const phrase = PHRASES[phraseIdx]
    let timeout: ReturnType<typeof setTimeout>
    if (!deleting) {
      if (displayed.length < phrase.length) {
        timeout = setTimeout(() => setDisplayed(phrase.slice(0, displayed.length + 1)), 65)
      } else {
        timeout = setTimeout(() => setDeleting(true), 2000)
      }
    } else {
      if (displayed.length > 0) {
        timeout = setTimeout(() => setDisplayed(displayed.slice(0, -1)), 38)
      } else {
        setDeleting(false)
        setPhraseIdx(i => (i + 1) % PHRASES.length)
      }
    }
    return () => clearTimeout(timeout)
  }, [displayed, deleting, phraseIdx])

  return (
    <span style={{ color: "rgba(240,235,227,0.6)", fontStyle: "italic" }}>
      {displayed}
      <span
        className="inline-block w-[0.12em] h-[0.85em] ml-1.5 align-middle"
        style={{ background: cursorOn ? "rgba(240,235,227,0.6)" : "transparent", borderRadius: "1px", verticalAlign: "middle" }}
      />
    </span>
  )
}

export default function Hero() {
  const [hovered, setHovered] = useState(false)

  return (
    <section className="min-h-screen flex flex-col items-center justify-center py-28 px-4 md:px-8">

      {/* The Card — exactly matching reference */}
      <motion.div
        className="w-full max-w-6xl"
        initial={{ opacity: 0, y: 40 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 1, ease: [0.22, 1, 0.36, 1] }}
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
      >
        <div
          className="relative overflow-hidden flex flex-col items-center justify-center"
          style={{
            borderRadius: "48px",
            border: "1px solid var(--border)",
            background: "var(--card)",
            minHeight: "600px",
          }}
        >
          {/* Dithering — orange/rust exactly like reference */}
          <Suspense fallback={<div className="absolute inset-0" />}>
            <div
              className="absolute inset-0 z-0 pointer-events-none"
              style={{
                opacity: hovered ? 0.45 : 0.28,
                transition: "opacity 0.7s ease",
                mixBlendMode: "screen",
              }}
            >
              <Dithering
                colorBack="#00000000"
                colorFront="#EC4E02"
                shape="warp"
                type="4x4"
                speed={hovered ? 0.6 : 0.18}
                style={{ width: "100%", height: "100%" }}
                minPixelRatio={1}
              />
            </div>
          </Suspense>

          {/* Content */}
          <div className="relative z-10 px-6 md:px-16 text-center flex flex-col items-center max-w-4xl mx-auto py-20">

            {/* Badge — matching reference pill exactly */}
            <motion.div
              className="mb-8 inline-flex items-center gap-2 rounded-full px-4 py-1.5 text-sm font-medium backdrop-blur-sm"
              style={{
                border: "1px solid rgba(236,78,2,0.2)",
                background: "rgba(236,78,2,0.06)",
                color: "var(--rust)",
                fontFamily: "var(--font-body)",
              }}
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.3 }}
            >
              <span className="relative flex h-2 w-2">
                <motion.span
                  className="absolute inline-flex h-full w-full rounded-full"
                  style={{ background: "var(--rust)" }}
                  animate={{ scale: [1, 2.2, 1], opacity: [0.7, 0, 0.7] }}
                  transition={{ duration: 1.8, repeat: Infinity }}
                />
                <span className="relative inline-flex h-2 w-2 rounded-full" style={{ background: "var(--rust)" }} />
              </span>
              Open Source · Free Forever
            </motion.div>

            {/* Main headline — large serif like reference */}
            <motion.h1
              style={{
                fontFamily: "var(--font-serif)",
                fontWeight: 500,
                color: "var(--ink)",
                fontSize: "clamp(3rem, 8vw, 7.5rem)",
                lineHeight: 1.05,
                letterSpacing: "-0.02em",
                marginBottom: "1.5rem",
              }}
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.9, delay: 0.42, ease: [0.22, 1, 0.36, 1] }}
            >
              Apply smarter,<br />
              <TypewriterCycler />
            </motion.h1>

            {/* Sub */}
            <motion.p
              className="text-lg md:text-xl leading-relaxed max-w-2xl mb-12"
              style={{ color: "var(--ink-dim)", fontFamily: "var(--font-body)", fontWeight: 300 }}
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.7, delay: 0.62 }}
            >
              Watches your Telegram groups, checks eligibility, tailors your resume, and fills every Greenhouse, Lever, or Workday form — automatically.
            </motion.p>

            {/* Buttons — white pill primary, ghost secondary (like reference) */}
            <motion.div
              className="flex items-center gap-3 flex-wrap justify-center"
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.8 }}
            >
              <motion.a
                href="https://github.com" target="_blank"
                className="group inline-flex items-center gap-3 h-14 px-12 rounded-full font-medium text-base transition-all duration-300"
                style={{ background: "var(--ink)", color: "var(--bg)", fontFamily: "var(--font-body)" }}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.96 }}
              >
                View on GitHub
                <ArrowRight size={18} className="group-hover:translate-x-1 transition-transform duration-300" />
              </motion.a>

              <motion.a
                href="#how-it-works"
                className="inline-flex items-center h-14 px-10 rounded-full text-base transition-all duration-200"
                style={{
                  border: "1px solid var(--border-warm)",
                  color: "var(--ink-dim)",
                  fontFamily: "var(--font-body)",
                }}
                whileHover={{ scale: 1.02, color: "var(--ink)" }}
                whileTap={{ scale: 0.97 }}
              >
                How it works
              </motion.a>
            </motion.div>
          </div>

          {/* Rotating badge bottom-right */}
          <div className="absolute bottom-7 right-8 z-20 w-20 h-20 flex items-center justify-center">
            <div className="absolute w-8 h-8 rounded-full flex items-center justify-center"
              style={{ border: "1px solid rgba(236,78,2,0.3)", background: "rgba(236,78,2,0.06)" }}>
              <div className="w-2 h-2 rounded-full" style={{ background: "var(--rust)" }} />
            </div>
            <motion.svg viewBox="0 0 100 100" className="absolute w-full h-full"
              animate={{ rotate: 360 }}
              transition={{ duration: 22, repeat: Infinity, ease: "linear" }}>
              <defs><path id="rc" d="M 50,50 m -36,0 a 36,36 0 1,1 72,0 a 36,36 0 1,1 -72,0" /></defs>
              <text style={{ fontFamily: "var(--font-mono)", fontSize: "6.5px", fill: "rgba(240,235,227,0.3)", letterSpacing: "2.5px" }}>
                <textPath href="#rc">JOB AUTOPILOT · FREE · OPEN SOURCE · </textPath>
              </text>
            </motion.svg>
          </div>
        </div>
      </motion.div>

      {/* Scroll hint */}
      <motion.div className="flex flex-col items-center gap-2 mt-10 z-10"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 1.3 }}>
        <span style={{ fontFamily: "var(--font-mono)", fontSize: "9px", letterSpacing: "0.28em", textTransform: "uppercase", color: "var(--ink-muted)" }}>
          Scroll
        </span>
        <motion.div className="w-px h-8"
          style={{ background: "linear-gradient(to bottom, var(--ink-muted), transparent)" }}
          animate={{ scaleY: [1, 0.25, 1], originY: "0%" }}
          transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }} />
      </motion.div>
    </section>
  )
}
