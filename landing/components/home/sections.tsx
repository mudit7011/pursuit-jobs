"use client"
import Link from "next/link"
import { ArrowUpRight } from "lucide-react"
import PhotoBand from "@/components/site/photo-band"
import Shot from "@/components/site/shot"
import { QueueDemo } from "@/components/ui/morning"

const H2 = ({ children, className = "", style }: { children: React.ReactNode; className?: string; style?: React.CSSProperties }) => (
  <h2 className={"day-display " + className} style={{ fontSize: "clamp(2.4rem, 5.4vw, 4.8rem)", ...style }}>{children}</h2>
)

const More = ({ href, children }: { href: string; children: React.ReactNode }) => (
  <Link href={href} className="group inline-flex items-center gap-2 text-[15px] font-medium underline decoration-[var(--day-line)] decoration-2 underline-offset-[6px] hover:decoration-[var(--day-ink)]">
    {children}<ArrowUpRight size={16} className="transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
  </Link>
)

const NAMES = ["Naukri", "Instahyre", "Wellfound", "Indeed", "Internshala", "Google Forms", "Microsoft Forms", "Greenhouse", "Lever", "Ashby", "Zoho Forms", "Keka", "Email"]

export function PlatformStrip() {
  return (
    <section id="after-hero" className="px-5 pt-10 pb-24">
      <p className="text-center text-[15px]" style={{ color: "var(--day-dim)" }}>Applies on the job boards and forms you already use</p>
      <div className="relative mx-auto mt-6 max-w-6xl overflow-hidden" style={{ maskImage: "linear-gradient(90deg, transparent, #000 10%, #000 90%, transparent)" }}>
        <div className="footer-marquee-track flex w-max gap-12 py-2">
          {[...NAMES, ...NAMES].map((n, i) => (
            <span key={i} className="whitespace-nowrap text-[26px] font-semibold tracking-[-0.03em]" style={{ fontFamily: "var(--font-day)", color: i % 2 ? "var(--day-faint)" : "var(--day-dim)" }}>{n}</span>
          ))}
        </div>
      </div>
    </section>
  )
}

const STEPS = [
  ["2:14 am", "A job is posted in your Telegram group, or turns up on Naukri, Instahyre or Wellfound."],
  ["2:15 am", "It checks you qualify, scores the fit and picks or tailors your resume."],
  ["2:16 am", "It fills the whole form, then stops and waits for you."],
]

export function Journey() {
  return (
    <section className="px-5 md:px-14 pb-28">
      <div className="mx-auto grid max-w-6xl gap-12 lg:grid-cols-[1fr_1.1fr] lg:items-end">
        <div>
          <H2>While you sleep, it does the boring part</H2>
          <p className="mt-5 max-w-md text-lg leading-relaxed" style={{ color: "var(--day-dim)" }}>
            Every job takes about two minutes from the post to a filled-in form. You only see the ones that fit.
          </p>
          <div className="mt-7"><More href="/how-it-works">Follow one job through the night</More></div>
        </div>
        <ol className="day-tile p-3">
          {STEPS.map(([t, d]) => (
            <li key={t} className="grid grid-cols-[6.5rem_1fr] gap-4 rounded-[20px] p-5">
              <span className="text-[15px] font-medium tabular-nums">{t}</span>
              <span className="text-[16px] leading-relaxed" style={{ color: "var(--day-dim)" }}>{d}</span>
            </li>
          ))}
          <li className="grid grid-cols-[6.5rem_1fr] gap-4 rounded-[20px] p-5" style={{ background: "var(--hi)" }}>
            <span className="text-[15px] font-medium tabular-nums">8:40 am</span>
            <span className="text-[16px] leading-relaxed font-medium">You press A or S with your first coffee.</span>
          </li>
        </ol>
      </div>
    </section>
  )
}

export function Morning() {
  return (
    <PhotoBand image="/nature/meadow.webp" position="center 70%" className="pt-24 pb-40">
      <div className="px-5 md:px-14">
        <div className="mx-auto max-w-6xl">
          <p className="text-lg" style={{ color: "var(--day-ink)" }}>8:40 am, with your first coffee</p>
          <H2 className="mt-3 max-w-3xl">Six jobs are waiting for a yes</H2>
        </div>
      </div>
      <div className="mt-12"><QueueDemo /></div>
    </PhotoBand>
  )
}

export function DeskTeaser() {
  return (
    <section className="px-5 md:px-14 pb-32">
      <div className="mx-auto max-w-6xl">
        <div className="flex flex-wrap items-end justify-between gap-6">
          <H2 className="max-w-2xl">Everything else, on one calm page</H2>
          <More href="/dashboard">Tour the dashboard</More>
        </div>
        <div className="mt-12 grid gap-5 md:grid-cols-2">
          <figure>
            <Shot src="/shots/attention-light.webp" alt="Needs you: two forms waiting on an answer only you know" />
            <figcaption className="mt-4 text-[16px] leading-relaxed" style={{ color: "var(--day-dim)" }}>
              <span className="font-medium" style={{ color: "var(--day-ink)" }}>Needs you.</span> Questions only you can answer, asked once and remembered for every form after.
            </figcaption>
          </figure>
          <figure>
            <Shot src="/shots/board-light.webp" alt="Applications board, grouped by where each one stands" />
            <figcaption className="mt-4 text-[16px] leading-relaxed" style={{ color: "var(--day-dim)" }}>
              <span className="font-medium" style={{ color: "var(--day-ink)" }}>Every application.</span> From applied to offer, with a nudge when one goes quiet for a week.
            </figcaption>
          </figure>
        </div>
      </div>
    </section>
  )
}

const RULES = [
  ["It never makes up a fact.", "No invented employers, dates or numbers. Answers come from your resume and the answers you saved."],
  ["It never solves a captcha.", "It fills everything else, then opens the tab for you to finish."],
  ["It never guesses what only you know.", "Walk-ins, relocation, your current company. It asks once and remembers."],
  ["It never sends without you.", "Every job waits for your yes, unless you pick a fit score it can send above on its own."],
]

export function Rules() {
  return (
    // On white, so the only landscape near the end of the page is the footer's
    <section className="px-5 md:px-14 pb-10">
      <div>
        <div className="day-tile mx-auto max-w-6xl p-7 md:p-14">
          <H2>Four things it won&apos;t do</H2>
          <div className="mt-12 grid gap-x-14 gap-y-10 md:grid-cols-2">
            {RULES.map(([t, b]) => (
              <div key={t}>
                <p className="text-[24px] leading-tight font-medium tracking-[-0.025em]" style={{ fontFamily: "var(--font-day)" }}>
                  <span className="mr-3 inline-block size-3 rounded-full align-middle" style={{ background: "var(--hi)" }} aria-hidden />{t}
                </p>
                <p className="mt-3 max-w-md text-[16px] leading-relaxed" style={{ color: "var(--day-dim)" }}>{b}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}
