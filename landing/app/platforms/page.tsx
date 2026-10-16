import type { Metadata } from "next"
import PageHero from "@/components/site/page-hero"
import { Where } from "@/components/ui/desk"

export const metadata: Metadata = { title: "Where it applies" }

const CAPS: [string, string, string][] = [
  ["Naukri", "Applies with your logged-in account", "30 a day"],
  ["Instahyre", "Says yes to matching opportunities, skips ones that go to a company site", "30 a day"],
  ["Wellfound", "Applies with your profile and a short note", "20 a day"],
  ["Indeed", "Only jobs marked Easily apply", "30 a day"],
  ["Internshala", "Easy apply jobs and internships", "30 a day"],
  ["LinkedIn", "Being rebuilt. Jobs are found but not sent", "Paused"],
]

export default function Platforms() {
  return (
    <>
      <PageHero
        image="/nature/meadow.webp"
        position="center 60%"
        subInk="light"
        title="Where it applies"
        sub="Job boards, company forms and plain email. Each one is handled the way a careful person would."
      />
      <div className="relative z-10 pt-6"><Where /></div>
      <section className="px-5 md:px-14 pb-24">
        <div className="mx-auto max-w-6xl">
          <h2 className="day-display max-w-3xl" style={{ fontSize: "clamp(2rem, 4.4vw, 3.6rem)" }}>A daily limit for every job board</h2>
          <p className="mt-4 max-w-xl text-lg leading-relaxed" style={{ color: "var(--day-dim)" }}>
            Job boards flag accounts that apply in bulk. You can change each limit in the dashboard&apos;s settings.
          </p>
          <div className="day-tile mt-10 overflow-hidden">
            {CAPS.map(([n, how, cap], i) => (
              <div key={n} className="grid gap-1 px-6 py-5 md:grid-cols-[12rem_1fr_8rem] md:items-center md:gap-6" style={{ borderTop: i ? "1px solid var(--day-line)" : undefined }}>
                <span className="text-[18px] font-medium">{n}</span>
                <span className="text-[15px]" style={{ color: "var(--day-dim)" }}>{how}</span>
                <span className="text-[15px] md:text-right tabular-nums">{cap}</span>
              </div>
            ))}
          </div>
        </div>
      </section>
    </>
  )
}
