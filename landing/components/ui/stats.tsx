"use client"
import { useEffect, useRef, useState } from "react"
import { motion, useInView } from "framer-motion"

const STATS = [
  { value: 44,  suffix: "+", label: "Tests Passing", sub: "fully covered" },
  { value: 8,   suffix: "",  label: "ATS Platforms", sub: "greenhouse · lever · workday" },
  { value: 0,   suffix: "",  label: "Manual Steps",  sub: "zero human input" },
  { value: 100, suffix: "%", label: "Open Source",   sub: "MIT license" },
]

function CountUp({ target, suffix }: { target: number; suffix: string }) {
  const [n, setN] = useState(0)
  const ref = useRef(null)
  const inView = useInView(ref, { once: true })
  useEffect(() => {
    if (!inView || target === 0) { setN(target); return }
    let cur = 0
    const step = target / (1400 / 16)
    const t = setInterval(() => {
      cur = Math.min(cur + step, target)
      setN(Math.floor(cur))
      if (cur >= target) clearInterval(t)
    }, 16)
    return () => clearInterval(t)
  }, [inView, target])
  return <span ref={ref}>{n}{suffix}</span>
}

export default function Stats() {
  return (
    <div style={{ borderTop: "1px solid var(--border)", borderBottom: "1px solid var(--border)" }}>
      <div className="max-w-6xl mx-auto grid grid-cols-2 md:grid-cols-4">
        {STATS.map(({ value, suffix, label, sub }, i) => (
          <motion.div
            key={label}
            className="flex flex-col gap-1 py-10 px-10"
            style={{ borderRight: i < 3 ? "1px solid var(--border)" : "none" }}
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: i * 0.08 }}
          >
            <span
              className="leading-none"
              style={{
                fontSize: "clamp(2.2rem, 4vw, 3.5rem)",
                color: "var(--ink)",
                fontFamily: "var(--font-serif)",
                fontWeight: 500,
                letterSpacing: "-0.02em",
              }}
            >
              <CountUp target={value} suffix={suffix} />
            </span>
            <span
              className="text-xs mt-1"
              style={{
                color: "var(--rust)",
                fontFamily: "var(--font-mono)",
                fontSize: "9px",
                letterSpacing: "0.22em",
                textTransform: "uppercase",
              }}
            >
              {label}
            </span>
            <span className="text-xs" style={{ color: "var(--ink-dim)", fontFamily: "var(--font-mono)" }}>
              {sub}
            </span>
          </motion.div>
        ))}
      </div>
    </div>
  )
}
