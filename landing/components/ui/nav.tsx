"use client"
import { useScroll, useTransform, useMotionTemplate, motion } from "framer-motion"
import { GitBranch } from "lucide-react"

const LINKS = [
  ["How it works", "#how-it-works"],
  ["Features",     "#features"],
  ["Stack",        "#stack"],
]

export default function Nav() {
  const { scrollY } = useScroll()

  // Layout — both in px so Framer can interpolate
  const maxWidthNum  = useTransform(scrollY, [0, 80], [1440, 900])
  const maxWidth     = useMotionTemplate`${maxWidthNum}px`

  const paddingXNum  = useTransform(scrollY, [0, 80], [32, 20])
  const paddingX     = useMotionTemplate`${paddingXNum}px`

  const paddingYNum  = useTransform(scrollY, [0, 80], [20, 7])
  const paddingY     = useMotionTemplate`${paddingYNum}px`

  const marginTopNum = useTransform(scrollY, [0, 80], [0, 12])
  const marginTop    = useMotionTemplate`${marginTopNum}px`

  const radiusNum    = useTransform(scrollY, [0, 80], [0, 9999])
  const borderRadius = useMotionTemplate`${radiusNum}px`

  // Visual only
  const bgAlpha     = useTransform(scrollY, [0, 80], [0, 0.78])
  const bg          = useMotionTemplate`rgba(13,11,9,${bgAlpha})`

  const blurPx      = useTransform(scrollY, [0, 80], [0, 20])
  const blur        = useMotionTemplate`blur(${blurPx}px) saturate(160%)`

  const borderAlpha = useTransform(scrollY, [0, 80], [0, 0.1])
  const border      = useMotionTemplate`1px solid rgba(240,235,227,${borderAlpha})`

  const shadowAlpha = useTransform(scrollY, [0, 80], [0, 0.5])
  const shadow      = useMotionTemplate`0 8px 40px rgba(0,0,0,${shadowAlpha}), inset 0 1px 0 rgba(240,235,227,0.05)`

  return (
    <motion.header
      className="fixed top-0 left-0 right-0 z-50 flex justify-center"
      initial={{ opacity: 0, y: -12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
    >
      <motion.div
        className="flex items-center justify-between w-full"
        style={{
          maxWidth,
          marginTop,
          marginLeft:           "auto",
          marginRight:          "auto",
          borderRadius,
          paddingLeft:          paddingX,
          paddingRight:         paddingX,
          paddingTop:           paddingY,
          paddingBottom:        paddingY,
          backgroundColor:      bg,
          backdropFilter:       blur,
          WebkitBackdropFilter: blur,
          border,
          boxShadow:            shadow,
        }}
      >
        {/* Logo */}
        <div className="flex items-center gap-2.5 shrink-0">
          <motion.span
            className="w-1.5 h-1.5 rounded-full"
            style={{ background: "var(--rust)" }}
            animate={{ opacity: [1, 0.4, 1] }}
            transition={{ duration: 2.5, repeat: Infinity }}
          />
          <span style={{
            fontFamily: "var(--font-serif)",
            fontWeight: 500,
            color: "var(--ink)",
            fontSize: "15px",
            letterSpacing: "0.02em",
            whiteSpace: "nowrap",
          }}>
            JobAutopilot
          </span>
        </div>

        {/* Nav links */}
        <nav className="hidden md:flex items-center gap-7" style={{ margin: "0 auto", padding: "0 2rem" }}>
          {LINKS.map(([label, href]) => (
            <a
              key={label}
              href={href}
              style={{
                fontFamily: "var(--font-body)",
                fontSize: "13px",
                color: "var(--ink-dim)",
                letterSpacing: "0.01em",
                whiteSpace: "nowrap",
                transition: "color 0.2s ease",
              }}
              onMouseEnter={e => (e.currentTarget.style.color = "var(--ink)")}
              onMouseLeave={e => (e.currentTarget.style.color = "var(--ink-dim)")}
            >
              {label}
            </a>
          ))}
        </nav>

        {/* GitHub CTA */}
        <motion.a
          href="https://github.com"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-2 text-xs font-medium px-4 py-2 rounded-full shrink-0"
          style={{
            background: "var(--ink)",
            color: "var(--bg)",
            fontFamily: "var(--font-body)",
          }}
          whileHover={{ scale: 1.04 }}
          whileTap={{ scale: 0.97 }}
          transition={{ type: "tween", duration: 0.15 }}
        >
          <GitBranch size={11} strokeWidth={2.5} />
          GitHub
        </motion.a>
      </motion.div>
    </motion.header>
  )
}
