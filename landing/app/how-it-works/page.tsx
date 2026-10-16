import type { Metadata } from "next"
import Link from "next/link"
import PageHero from "@/components/site/page-hero"
import Night from "@/components/ui/night"

export const metadata: Metadata = { title: "How it works" }

export default function HowItWorks() {
  return (
    <>
      <PageHero
        image="/nature/night-lake.webp"
        ink="light"
        fadeTo="var(--day-bg)"
        title="What happens between 2 and 3 in the morning"
        sub="Follow one job from the moment it's posted to the moment it waits for you."
      />
      <Night />
            <section className="px-5 pt-16 pb-10 text-center">
        <p className="mx-auto max-w-2xl day-display" style={{ fontSize: "clamp(2.2rem, 5vw, 4.2rem)", color: "var(--day-ink)" }}>
          By breakfast, every job that fits is waiting for one key press.
        </p>
        <Link href="/dashboard" className="mt-9 inline-flex h-12 items-center rounded-[16px] px-6 text-[15px] font-medium" style={{ background: "var(--tile)", color: "var(--tile-ink)" }}>
          See the dashboard
        </Link>
      </section>
    </>
  )
}
