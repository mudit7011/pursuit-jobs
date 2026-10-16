"use client"
import { useRef, type ReactNode } from "react"
import { motion, useScroll, useTransform } from "framer-motion"

/* A landscape that opens each page. It drifts slower than the page and melts into
   the page colour at the bottom, so the content below seems to sit in the valley. */
export default function PageHero({ image, title, sub, ink = "dark", subInk, fadeTo = "var(--day-bg)", position = "center", children }: {
  image: string; title: ReactNode; sub?: ReactNode; ink?: "dark" | "light"; subInk?: "dark" | "light"; fadeTo?: string; position?: string; children?: ReactNode
}) {
  const subLight = (subInk ?? ink) === "light"
  const ref = useRef<HTMLElement>(null)
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start start", "end start"] })
  const y = useTransform(scrollYProgress, [0, 1], ["0%", "22%"])
  const scale = useTransform(scrollYProgress, [0, 1], [1.06, 1.16])
  const textY = useTransform(scrollYProgress, [0, 1], [0, -90])
  const fade = useTransform(scrollYProgress, [0, 0.6], [1, 0])
  const color = ink === "dark" ? "var(--day-ink)" : "#f6f5ef"
  return (
    <section ref={ref} className="relative min-h-[86vh] overflow-hidden">
      <motion.div className="absolute inset-0" style={{ y, scale }}>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={image} alt="" className="h-full w-full object-cover" style={{ objectPosition: position }} />
      </motion.div>
      {/* A soft pool of light (or shade) behind the words so they read on any photo */}
      <div className="absolute inset-0" aria-hidden style={{ background: ink === "dark"
        ? "radial-gradient(ellipse 55% 42% at 50% 38%, rgba(255,255,255,0.42), rgba(255,255,255,0) 70%)"
        : "radial-gradient(ellipse 60% 46% at 50% 38%, rgba(0,0,0,0.32), rgba(0,0,0,0) 70%)" }} />
      <div className="absolute inset-x-0 bottom-0 h-[clamp(90px,15vh,170px)]" style={{ background: `linear-gradient(to bottom, transparent, color-mix(in srgb, ${fadeTo} 35%, transparent) 45%, color-mix(in srgb, ${fadeTo} 80%, transparent) 75%, ${fadeTo})` }} aria-hidden />
      <motion.div style={{ y: textY, opacity: fade, color }} className="relative z-10 mx-auto flex max-w-4xl flex-col items-center px-5 pt-[24vh] text-center">
        <h1 className="day-display" style={{ fontSize: "clamp(2.8rem, 7vw, 6.2rem)", textShadow: ink === "light" ? "0 2px 30px rgba(0,0,0,0.35)" : undefined }}>{title}</h1>
        {sub && <p className="mt-6 max-w-xl text-lg md:text-xl leading-relaxed font-medium" style={{ color: subLight ? "#ffffff" : undefined, opacity: subLight ? 1 : 0.86, textShadow: subLight ? "0 1px 3px rgba(0,0,0,0.45), 0 2px 18px rgba(0,0,0,0.45)" : undefined }}>{sub}</p>}
        {children}
      </motion.div>
    </section>
  )
}
