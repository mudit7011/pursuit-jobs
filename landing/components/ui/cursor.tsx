"use client"
import { useEffect, useRef } from "react"

export default function Cursor() {
  const dotRef  = useRef<HTMLDivElement>(null)
  const ringRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const dot  = dotRef.current
    const ring = ringRef.current
    if (!dot || !ring) return

    let mx = window.innerWidth / 2
    let my = window.innerHeight / 2
    let rx = mx, ry = my
    let rafId: number

    const moveDot = (x: number, y: number) => {
      dot.style.transform = `translate(${x}px, ${y}px)`
    }
    const moveRing = (x: number, y: number) => {
      ring.style.transform = `translate(${x}px, ${y}px)`
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
    }
    const onLeave = () => {
      ring.classList.remove("cursor-ring--hover")
      dot.classList.remove("cursor-dot--hover")
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
    </>
  )
}
