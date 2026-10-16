"use client"
import { useRef, type ReactNode } from "react"
import { motion, useScroll, useTransform } from "framer-motion"

/* A landscape the content floats over. The photo moves slower than the page and
   fades into the page colour at both edges, so there's never a hard seam. */
export default function PhotoBand({ image, children, className = "", position = "center", id }: {
  image: string; children: ReactNode; className?: string; position?: string; id?: string
}) {
  const ref = useRef<HTMLElement>(null)
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start end", "end start"] })
  const y = useTransform(scrollYProgress, [0, 1], ["-12%", "12%"])
  return (
    <section ref={ref} id={id} className={"relative overflow-hidden " + className}>
      <motion.div className="absolute inset-x-0 -inset-y-[14%]" style={{ y }}>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={image} alt="" loading="lazy" className="h-full w-full object-cover" style={{ objectPosition: position }} />
      </motion.div>
      <div className="absolute inset-x-0 top-0 h-[clamp(80px,13vh,150px)]" aria-hidden style={{ background: "linear-gradient(to top, rgba(255,255,255,0), rgba(255,255,255,0.35) 45%, rgba(255,255,255,0.8) 75%, #fff)" }} />
      <div className="absolute inset-x-0 bottom-0 h-[clamp(80px,13vh,150px)]" aria-hidden style={{ background: "linear-gradient(to bottom, rgba(255,255,255,0), rgba(255,255,255,0.35) 45%, rgba(255,255,255,0.8) 75%, #fff)" }} />
      <div className="relative z-10">{children}</div>
    </section>
  )
}
