"use client"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { useEffect, useState } from "react"
import { GitBranch, Menu, X } from "lucide-react"
import Logo from "./logo"

export const LINKS = [
  { href: "/how-it-works", label: "How it works" },
  { href: "/dashboard", label: "Dashboard" },
  { href: "/platforms", label: "Where it applies" },
  { href: "/get-started", label: "Get started" },
]
export const REPO = "https://github.com/mudit7011/jobcopilot"

/* The same pill nav the dashboard uses: the page you're on is the black pill. */
export default function Nav() {
  const path = usePathname()
  const [open, setOpen] = useState(false)
  const [scrolled, setScrolled] = useState(false)
  useEffect(() => {
    const on = () => setScrolled(window.scrollY > 24)
    on(); window.addEventListener("scroll", on, { passive: true })
    return () => window.removeEventListener("scroll", on)
  }, [])

  return (
    <header className="fixed inset-x-0 top-0 z-50 px-3 pt-3 md:pt-4">
      <div
        className="mx-auto flex max-w-[1080px] items-center gap-2 rounded-[22px] p-2 pl-4 transition-[background,box-shadow] duration-300"
        style={{
          background: scrolled || open ? "rgba(251,251,249,0.88)" : "rgba(251,251,249,0.62)",
          backdropFilter: "blur(18px) saturate(160%)",
          WebkitBackdropFilter: "blur(18px) saturate(160%)",
          boxShadow: scrolled ? "0 10px 40px -16px rgba(19,19,18,0.35)" : "0 1px 0 rgba(255,255,255,0.5) inset",
          color: "var(--day-ink)",
        }}
      >
        <Link href="/" className="flex items-center pr-3" aria-label="Pursuit home">
          <Logo />
        </Link>

        <nav className="mx-auto hidden items-center gap-1 md:flex" aria-label="Main">
          {LINKS.map((l) => {
            const active = path === l.href
            return (
              <Link
                key={l.href}
                href={l.href}
                aria-current={active ? "page" : undefined}
                className="rounded-[14px] px-4 py-2 text-[14px] transition-colors"
                style={active ? { background: "var(--tile)", color: "var(--tile-ink)" } : { color: "var(--day-dim)" }}
                onMouseEnter={(e) => { if (!active) e.currentTarget.style.color = "var(--day-ink)" }}
                onMouseLeave={(e) => { if (!active) e.currentTarget.style.color = "var(--day-dim)" }}
              >
                {l.label}
              </Link>
            )
          })}
        </nav>

        <a
          href={REPO}
          target="_blank"
          rel="noopener noreferrer"
          className="ml-auto hidden h-10 items-center gap-2 rounded-[14px] px-4 text-[14px] font-medium md:ml-0 md:inline-flex"
          style={{ background: "var(--tile)", color: "var(--tile-ink)" }}
        >
          <GitBranch size={15} /> GitHub
        </a>
        <button
          className="ml-auto grid size-10 place-items-center rounded-[14px] md:hidden"
          aria-label={open ? "Close menu" : "Open menu"}
          aria-expanded={open}
          onClick={() => setOpen((v) => !v)}
        >
          {open ? <X size={20} /> : <Menu size={20} />}
        </button>
      </div>

      {open && (
        <nav className="mx-auto mt-2 max-w-[1080px] rounded-[22px] p-2 md:hidden" style={{ background: "rgba(251,251,249,0.96)", color: "var(--day-ink)" }} aria-label="Main">
          {LINKS.map((l) => (
            <Link key={l.href} href={l.href} onClick={() => setOpen(false)} className="block rounded-[14px] px-4 py-3 text-[16px]"
              style={path === l.href ? { background: "var(--tile)", color: "var(--tile-ink)" } : undefined}>
              {l.label}
            </Link>
          ))}
          <a href={REPO} target="_blank" rel="noopener noreferrer" className="mt-1 flex items-center gap-2 rounded-[14px] px-4 py-3 text-[16px]">
            <GitBranch size={16} /> GitHub
          </a>
        </nav>
      )}
    </header>
  )
}
