"use client"
import { useEffect } from "react"
import { usePathname } from "next/navigation"
import Lenis from "lenis"
import "lenis/dist/lenis.css"

/* Smooth, eased scrolling for the whole site. Off for people who ask for reduced motion. */
export default function SmoothScroll() {
  const path = usePathname()
  useEffect(() => {
    if (matchMedia("(prefers-reduced-motion: reduce)").matches) return
    const lenis = new Lenis({ lerp: 0.085, wheelMultiplier: 0.9, anchors: true })
    let raf = requestAnimationFrame(function loop(t) { lenis.raf(t); raf = requestAnimationFrame(loop) })
    return () => { cancelAnimationFrame(raf); lenis.destroy() }
  }, [])
  // A new page always starts at the top
  useEffect(() => { window.scrollTo(0, 0) }, [path])
  return null
}
