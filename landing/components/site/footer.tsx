"use client"
import Link from "next/link"
import { useRef } from "react"
import { motion, useScroll, useTransform } from "framer-motion"
import { GitBranch } from "lucide-react"
import Logo from "./logo"
import { LINKS, REPO } from "./nav"

/* Every page ends at dawn over the forest, with the way back to the bot. */
export default function Footer() {
  const ref = useRef<HTMLElement>(null)
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start end", "end end"] })
  const y = useTransform(scrollYProgress, [0, 1], ["-18%", "0%"])
  return (
    <footer ref={ref} className="relative overflow-hidden pt-[30vh]" style={{ background: "var(--day-bg)" }}>
      <motion.div className="absolute inset-0" style={{ y }}>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src="/nature/golden-fog.webp" alt="" className="h-[118%] w-full object-cover" />
      </motion.div>
      <div className="absolute inset-x-0 top-0 h-[clamp(80px,13vh,150px)]" style={{ background: "linear-gradient(to top, rgba(255,255,255,0), rgba(255,255,255,0.35) 45%, rgba(255,255,255,0.8) 75%, #fff)" }} aria-hidden />

      <div className="relative z-10 px-5 text-center" style={{ color: "#fbfaf4" }}>
        <h2 className="day-display mx-auto max-w-3xl" style={{ fontSize: "clamp(2.4rem, 5.6vw, 4.8rem)", textShadow: "0 2px 30px rgba(0,0,0,0.35)" }}>
          Go back to sleep. It&apos;s watching for the next one.
        </h2>
        <div className="mt-9 flex flex-wrap justify-center gap-3">
          <Link href="/get-started" className="inline-flex h-12 items-center rounded-[16px] px-6 text-[15px] font-medium" style={{ background: "var(--hi)", color: "var(--day-ink)" }}>
            Set it up
          </Link>
          <a href={REPO} target="_blank" rel="noopener noreferrer" className="inline-flex h-12 items-center gap-2 rounded-[16px] px-6 text-[15px] font-medium" style={{ background: "rgba(19,19,18,0.75)", color: "#fbfaf4", backdropFilter: "blur(8px)" }}>
            <GitBranch size={16} /> Star it on GitHub
          </a>
        </div>
      </div>

      <div className="relative z-10 mx-auto mt-[22vh] max-w-6xl px-3 md:px-5">
        <div className="rounded-t-[32px] px-6 pt-10 pb-8 md:px-12" style={{ background: "var(--day-surface)", color: "var(--day-ink)" }}>
          <div className="grid gap-10 md:grid-cols-[1.4fr_1fr_1fr]">
            <div>
              <Logo />
              <p className="mt-4 max-w-sm text-[15px] leading-relaxed" style={{ color: "var(--day-dim)" }}>
                Finds jobs overnight, tailors your resume, fills the form and waits for your yes. Free and open source.
              </p>
            </div>
            <div>
              <p className="text-[15px] font-medium">Pages</p>
              <ul className="mt-3 space-y-2 text-[15px]" style={{ color: "var(--day-dim)" }}>
                <li><Link href="/" className="hover:underline underline-offset-4">Home</Link></li>
                {LINKS.map((l) => <li key={l.href}><Link href={l.href} className="hover:underline underline-offset-4">{l.label}</Link></li>)}
              </ul>
            </div>
            <div>
              <p className="text-[15px] font-medium">Elsewhere</p>
              <ul className="mt-3 space-y-2 text-[15px]" style={{ color: "var(--day-dim)" }}>
                <li><a href={REPO} target="_blank" rel="noopener noreferrer" className="hover:underline underline-offset-4">GitHub</a></li>
                <li><a href="https://linkedin.com/in/mudit-dev" target="_blank" rel="noopener noreferrer" className="hover:underline underline-offset-4">LinkedIn</a></li>
              </ul>
            </div>
          </div>
          <div className="mt-10 flex flex-wrap justify-between gap-3 border-t pt-6 text-[13px]" style={{ borderColor: "var(--day-line)", color: "var(--day-faint)" }}>
            <span>Made by Mudit Kumar. MIT licence, 2026.</span>
            <span>Landscape photos from Pixabay.</span>
          </div>
        </div>
      </div>
    </footer>
  )
}
