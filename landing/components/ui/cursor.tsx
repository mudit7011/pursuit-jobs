"use client"
import { useEffect, useRef } from "react"

export default function Cursor() {
  const dotRef   = useRef<HTMLDivElement>(null)
  const ringRef  = useRef<HTMLDivElement>(null)
  const badgeRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const dot   = dotRef.current
    const ring  = ringRef.current
    const badge = badgeRef.current
    if (!dot || !ring || !badge) return

    let mx = window.innerWidth / 2
    let my = window.innerHeight / 2
    let rx = mx, ry = my
    let rafId: number

    const moveDot = (x: number, y: number) => {
      dot.style.transform = `translate(${x}px, ${y}px)`
    }
    const moveRing = (x: number, y: number) => {
      ring.style.transform  = `translate(${x}px, ${y}px)`
      badge.style.transform = `translate(${x}px, ${y}px)`
    }

    moveDot(mx, my)
    moveRing(rx, ry)

    const onMove = (e: MouseEvent) => {
      mx = e.clientX
      my = e.clientY
      moveDot(mx, my)
    }

    const loop = () => {
      rx += (mx - rx) * 0.1
      ry += (my - ry) * 0.1
      moveRing(rx, ry)
      rafId = requestAnimationFrame(loop)
    }
    rafId = requestAnimationFrame(loop)

    const onEnter = () => {
      ring.classList.add("cursor-ring--hover")
      dot.classList.add("cursor-dot--hover")
      badge.classList.add("cursor-badge--hover")
    }
    const onLeave = () => {
      ring.classList.remove("cursor-ring--hover")
      dot.classList.remove("cursor-dot--hover")
      badge.classList.remove("cursor-badge--hover")
    }

    const bindTargets = () => {
      document.querySelectorAll("a, button").forEach(el => {
        el.removeEventListener("mouseenter", onEnter)
        el.removeEventListener("mouseleave", onLeave)
        el.addEventListener("mouseenter", onEnter)
        el.addEventListener("mouseleave", onLeave)
      })
    }
    bindTargets()

    window.addEventListener("mousemove", onMove)

    return () => {
      window.removeEventListener("mousemove", onMove)
      cancelAnimationFrame(rafId)
      document.querySelectorAll("a, button").forEach(el => {
        el.removeEventListener("mouseenter", onEnter)
        el.removeEventListener("mouseleave", onLeave)
      })
    }
  }, [])

  return (
    <>
      <div ref={dotRef}  className="cursor-dot" />
      <div ref={ringRef} className="cursor-ring" />
      <div ref={badgeRef} className="cursor-badge">
        <svg viewBox="0 0 100 100" className="cursor-badge-svg">
          <defs>
            <path id="cbp" d="M 50,50 m -36,0 a 36,36 0 1,1 72,0 a 36,36 0 1,1 -72,0" />
          </defs>
          <text style={{ fontFamily: "var(--font-mono)", fontSize: "6.5px", fill: "rgba(240,235,227,0.28)", letterSpacing: "2.5px" }}>
            <textPath href="#cbp">JOB AUTOPILOT · FREE · OPEN SOURCE · </textPath>
          </text>
        </svg>
      </div>
    </>
  )
}
