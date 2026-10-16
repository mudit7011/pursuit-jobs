"use client"
import { useState } from "react"
import { Plus } from "lucide-react"

const QA: [string, string][] = [
  ["Does it send applications without asking me?", "Not unless you tell it to. By default every job waits in your review queue. You can let it send jobs above a fit score you choose."],
  ["Will it make things up on my applications?", "No. It writes answers only from your resume, your profile and the answers you saved. When a form asks something only you know, it asks you on Telegram and waits."],
  ["What happens when a form has a captcha?", "It fills in everything it can, then opens the page for you. You solve the captcha and press submit."],
  ["Can my job board account get flagged?", "Each board has a daily limit, 20 to 30 applications by default, so it never applies in bulk. You can lower them in settings."],
  ["What leaves my laptop?", "Job posts and your resume text go to Google's Gemini to read posts and write answers. Applications go to the sites you apply on. Your data, resumes and answers stay in files on your machine."],
  ["What does it cost?", "Nothing. It's MIT licensed. You need your own Gemini API key, which has a free tier."],
]

export default function Faq() {
  const [open, setOpen] = useState<number | null>(0)
  return (
    <section className="px-5 md:px-14 pb-24">
      <div className="mx-auto grid max-w-6xl gap-10 lg:grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)] lg:gap-16">
        <h2 className="day-display" style={{ fontSize: "clamp(2.2rem, 4.8vw, 4rem)" }}>Questions people ask first</h2>
        <ul className="day-tile p-2">
          {QA.map(([q, a], i) => (
            <li key={q} className="rounded-[20px]" style={{ background: open === i ? "var(--day-raised)" : undefined }}>
              <button className="flex w-full items-center justify-between gap-4 px-5 py-5 text-left text-[17px] font-medium" aria-expanded={open === i} onClick={() => setOpen(open === i ? null : i)}>
                {q}
                <Plus size={18} className="shrink-0 transition-transform duration-300" style={{ transform: open === i ? "rotate(45deg)" : undefined }} />
              </button>
              <div className="grid transition-[grid-template-rows] duration-300" style={{ gridTemplateRows: open === i ? "1fr" : "0fr" }}>
                <p className="overflow-hidden px-5 text-[16px] leading-relaxed" style={{ color: "var(--day-dim)", paddingBottom: open === i ? 20 : 0 }}>{a}</p>
              </div>
            </li>
          ))}
        </ul>
      </div>
    </section>
  )
}
