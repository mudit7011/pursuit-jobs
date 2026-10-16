"use client"
import Link from "next/link"
import { useEffect, useRef, useState } from "react"
import { AnimatePresence, motion, useReducedMotion, useScroll, useSpring, useTransform } from "framer-motion"
import Shot from "@/components/site/shot"

const PHRASES = ["sleep better.", "land faster.", "stress less.", "win more."]

/* The ending of the headline swaps every few seconds, sliding up like a ticker. */
function Rotating() {
  const [i, setI] = useState(0)
  useEffect(() => {
    const t = setInterval(() => setI((v) => (v + 1) % PHRASES.length), 2600)
    return () => clearInterval(t)
  }, [])
  return (
    <span className="relative inline-grid overflow-hidden align-bottom pb-[0.08em]" aria-live="polite">
      <AnimatePresence mode="popLayout" initial={false}>
        <motion.span
          key={PHRASES[i]}
          className="col-start-1 row-start-1 whitespace-nowrap px-[0.06em]"
          style={{ background: "linear-gradient(transparent 58%, var(--hi) 58%, var(--hi) 92%, transparent 92%)" }}
          initial={{ y: "100%", opacity: 0 }}
          animate={{ y: "0%", opacity: 1 }}
          exit={{ y: "-100%", opacity: 0 }}
          transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
        >
          {PHRASES[i]}
        </motion.span>
      </AnimatePresence>
    </span>
  )
}

/* Morning on the hills. The dashboard starts small, tucked between the hills, and
   grows as you scroll while the hills slide away beneath it, as if you were walking
   up to it. Three layers: the sky, the dashboard, then the hills and trees (cut out
   of the same photo) in front. */
export default function Hero() {
  const ref = useRef<HTMLElement>(null)
  const reduce = useReducedMotion()
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start start", "end end"] })
  const p = useSpring(scrollYProgress, { stiffness: 160, damping: 32, mass: 0.35 })

  const skyScale = useTransform(p, [0, 1], [1.04, 1.22])
  const hillsY = useTransform(p, [0, 0.85], ["17%", "74%"])
  const hillsScale = useTransform(p, [0, 0.85], [1, 1.5])
  const textY = useTransform(p, [0, 0.4], ["0vh", "-52vh"])
  const textOpacity = useTransform(p, [0.12, 0.36], [1, 0])
  const shotY = useTransform(p, [0, 0.8], ["66vh", "13vh"])
  const shotScale = useTransform(p, [0, 0.8], [0.44, 1])
  // The mist rolls in with it rather than sitting there from the start
  const fogOpacity = useTransform(p, [0.55, 0.9], [0, 1])
  const fogY = useTransform(p, [0.55, 0.9], ["55%", "0%"])

  return (
    <section ref={ref} className="relative h-[190vh] md:h-[250vh]" aria-label="Pursuit">
      <div className="sticky top-0 h-screen overflow-hidden">
        <motion.div className="absolute inset-0 will-change-transform" style={{ scale: reduce ? 1.04 : skyScale }}>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/nature/hills-sky.webp" alt="" className="h-full w-full object-cover object-bottom" />
        </motion.div>

        <motion.div style={{ y: textY, opacity: textOpacity }} className="relative z-10 mx-auto flex max-w-5xl flex-col items-center px-5 pt-[15vh] text-center will-change-transform">
          <h1 className="day-display" style={{ fontSize: "clamp(2.9rem, 7.6vw, 7rem)", color: "var(--day-ink)" }}>
            Apply smarter,<br /><Rotating />
          </h1>
          <p className="mt-6 max-w-xl text-lg md:text-xl leading-relaxed" style={{ color: "rgba(19,19,18,0.78)" }}>
            It reads your Telegram groups and job boards overnight, tailors your resume and fills the form. In the morning you just say yes.
          </p>
          <div className="mt-8 flex flex-wrap justify-center gap-3">
            <Link href="/get-started" className="inline-flex h-12 items-center rounded-[16px] px-6 text-[15px] font-medium" style={{ background: "var(--tile)", color: "var(--tile-ink)" }}>
              Set it up, free
            </Link>
            <Link href="/how-it-works" className="inline-flex h-12 items-center rounded-[16px] px-6 text-[15px] font-medium" style={{ background: "rgba(255,255,255,0.75)", color: "var(--day-ink)", backdropFilter: "blur(10px)" }}>
              See how it works
            </Link>
          </div>
        </motion.div>

        <motion.div
          className="absolute inset-x-0 top-0 z-20 mx-auto w-[min(1180px,94vw)] origin-top will-change-transform"
          style={reduce ? { y: "14vh" } : { y: shotY, scale: shotScale }}
        >
          <Shot src="/shots/overview-light.webp" alt="The Pursuit dashboard: six jobs waiting for review, 171 applications sent, a year of activity" priority />
        </motion.div>

        <motion.div className="pointer-events-none absolute inset-0 z-30 origin-bottom will-change-transform" style={reduce ? { y: "17%" } : { y: hillsY, scale: hillsScale }}>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/nature/hills-front.webp" alt="" className="h-full w-full object-cover object-bottom" />
        </motion.div>

        <motion.div
          className="pointer-events-none absolute inset-x-0 bottom-0 z-40 h-[30vh] will-change-transform"
          style={{ opacity: reduce ? 1 : fogOpacity, y: reduce ? 0 : fogY, background: "linear-gradient(to bottom, rgba(255,255,255,0), rgba(255,255,255,0.3) 35%, rgba(255,255,255,0.78) 68%, #fff)" }}
        />
      </div>
    </section>
  )
}
