"use client"

import { useState, useEffect, useRef } from "react"
import { motion, AnimatePresence, useInView } from "framer-motion"
import { CheckCircle2, Clock, Zap } from "lucide-react"

interface Card {
  id: number
  contentType: 1 | 2 | 3
}

const cardData = {
  1: {
    company: "Stripe",
    role: "Backend Engineer",
    platform: "Greenhouse",
    batch: "2024",
    overlap: "81%",
    time: "0.4s",
    status: "applied",
  },
  2: {
    company: "Linear",
    role: "Software Engineer",
    platform: "Lever",
    batch: "2024",
    overlap: "74%",
    time: "0.7s",
    status: "applied",
  },
  3: {
    company: "Notion",
    role: "Full Stack Engineer",
    platform: "Workday",
    batch: "2024",
    overlap: "68%",
    time: "0.3s",
    status: "applied",
  },
}

const initialCards: Card[] = [
  { id: 1, contentType: 1 },
  { id: 2, contentType: 2 },
  { id: 3, contentType: 3 },
]

const positionStyles = [
  { scale: 1,    y: 12 },
  { scale: 0.95, y: -16 },
  { scale: 0.9,  y: -44 },
]

const exitAnimation  = { y: 340, scale: 1, zIndex: 10 }
const enterAnimation = { y: -16, scale: 0.9 }

function CardContent({ contentType }: { contentType: 1 | 2 | 3 }) {
  const d = cardData[contentType]
  return (
    <div className="flex flex-col w-full h-full" style={{ padding: "20px 20px 16px" }}>
      {/* Top bar */}
      <div className="flex items-start justify-between mb-5">
        <div>
          <p
            style={{
              fontFamily: "var(--font-serif)",
              fontWeight: 500,
              fontSize: "1.25rem",
              color: "var(--ink)",
              letterSpacing: "-0.01em",
              lineHeight: 1.2,
            }}
          >
            {d.company}
          </p>
          <p
            style={{
              fontFamily: "var(--font-body)",
              fontSize: "13px",
              color: "var(--ink-dim)",
              marginTop: "2px",
            }}
          >
            {d.role}
          </p>
        </div>
        <div
          className="flex items-center gap-1.5 px-2.5 py-1 rounded-full"
          style={{
            background: "rgba(110,231,183,0.08)",
            border: "1px solid rgba(110,231,183,0.2)",
          }}
        >
          <CheckCircle2 size={10} style={{ color: "#6ee7b7" }} />
          <span
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: "9px",
              letterSpacing: "0.1em",
              textTransform: "uppercase",
              color: "#6ee7b7",
            }}
          >
            Applied
          </span>
        </div>
      </div>

      {/* Divider */}
      <div style={{ borderTop: "1px solid var(--border)", marginBottom: "14px" }} />

      {/* Stats row */}
      <div className="flex items-center gap-4 flex-1">
        <div>
          <p
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: "9px",
              letterSpacing: "0.18em",
              textTransform: "uppercase",
              color: "var(--ink-muted)",
              marginBottom: "3px",
            }}
          >
            Platform
          </p>
          <p style={{ fontFamily: "var(--font-mono)", fontSize: "12px", color: "var(--ink-dim)" }}>
            {d.platform}
          </p>
        </div>
        <div
          style={{
            width: "1px",
            height: "32px",
            background: "var(--border)",
          }}
        />
        <div>
          <p
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: "9px",
              letterSpacing: "0.18em",
              textTransform: "uppercase",
              color: "var(--ink-muted)",
              marginBottom: "3px",
            }}
          >
            Skill Match
          </p>
          <p style={{ fontFamily: "var(--font-mono)", fontSize: "12px", color: "var(--rust)" }}>
            {d.overlap}
          </p>
        </div>
        <div
          style={{
            width: "1px",
            height: "32px",
            background: "var(--border)",
          }}
        />
        <div>
          <p
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: "9px",
              letterSpacing: "0.18em",
              textTransform: "uppercase",
              color: "var(--ink-muted)",
              marginBottom: "3px",
            }}
          >
            Fill time
          </p>
          <div className="flex items-center gap-1">
            <Zap size={10} style={{ color: "var(--rust)" }} />
            <p style={{ fontFamily: "var(--font-mono)", fontSize: "12px", color: "var(--ink-dim)" }}>
              {d.time}
            </p>
          </div>
        </div>
      </div>

      {/* Bottom: platform badge */}
      <div className="flex items-center justify-between mt-3 pt-3" style={{ borderTop: "1px solid var(--border)" }}>
        <span
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: "9px",
            letterSpacing: "0.15em",
            textTransform: "uppercase",
            color: "var(--ink-muted)",
          }}
        >
          Batch {d.batch} · Eligible
        </span>
        <div className="flex items-center gap-1">
          <Clock size={9} style={{ color: "var(--ink-muted)" }} />
          <span style={{ fontFamily: "var(--font-mono)", fontSize: "9px", color: "var(--ink-muted)" }}>
            just now
          </span>
        </div>
      </div>
    </div>
  )
}

function AnimatedCard({
  card,
  index,
  isAnimating,
}: {
  card: Card
  index: number
  isAnimating: boolean
}) {
  const { scale, y } = positionStyles[index] ?? positionStyles[2]
  const zIndex = index === 0 && isAnimating ? 10 : 3 - index
  const exitAnim  = index === 0 ? exitAnimation  : undefined
  const initialAnim = index === 2 ? enterAnimation : undefined

  return (
    <motion.div
      key={card.id}
      initial={initialAnim}
      animate={{ y, scale }}
      exit={exitAnim}
      transition={{ type: "spring", duration: 1, bounce: 0 }}
      style={{
        zIndex,
        left: "50%",
        x: "-50%",
        bottom: 0,
        position: "absolute",
        width: "100%",
        maxWidth: "420px",
        height: "200px",
        borderRadius: "16px 16px 0 0",
        border: "1px solid var(--border-warm)",
        borderBottom: "none",
        background: "var(--card)",
        boxShadow: "0 -8px 40px rgba(0,0,0,0.4)",
        willChange: "transform",
        overflow: "hidden",
      }}
    >
      <CardContent contentType={card.contentType} />
    </motion.div>
  )
}

export default function AnimatedCardStack() {
  const ref = useRef(null)
  const inView = useInView(ref, { once: false, margin: "-100px" })
  const [cards, setCards] = useState(initialCards)
  const [nextId, setNextId] = useState(4)

  useEffect(() => {
    if (!inView) return
    const interval = setInterval(() => {
      setCards(prev => {
        const nextContentType = ((prev[2].contentType % 3) + 1) as 1 | 2 | 3
        return [...prev.slice(1), { id: nextId, contentType: nextContentType }]
      })
      setNextId(n => n + 1)
    }, 2200)
    return () => clearInterval(interval)
  }, [inView, nextId])

  return (
    <div ref={ref} className="flex flex-col items-center justify-end w-full">
      <div
        style={{
          position: "relative",
          height: "280px",
          width: "100%",
          maxWidth: "420px",
          overflow: "hidden",
        }}
      >
        <AnimatePresence initial={false}>
          {cards.slice(0, 3).map((card, index) => (
            <AnimatedCard key={card.id} card={card} index={index} isAnimating={false} />
          ))}
        </AnimatePresence>
      </div>

      {/* Bottom strip */}
      <div
        style={{
          width: "100%",
          maxWidth: "420px",
          borderTop: "1px solid var(--border-warm)",
          padding: "12px 0",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          gap: "6px",
        }}
      >
        <motion.div
          className="w-1.5 h-1.5 rounded-full"
          style={{ background: "var(--rust)" }}
          animate={{ opacity: [1, 0.3, 1] }}
          transition={{ duration: 1.8, repeat: Infinity }}
        />
        <span
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: "9px",
            letterSpacing: "0.2em",
            textTransform: "uppercase",
            color: "var(--ink-muted)",
          }}
        >
          Simulated · not live
        </span>
      </div>
    </div>
  )
}
