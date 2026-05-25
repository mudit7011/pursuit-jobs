"use client"
import { useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { X } from "lucide-react"

const ICONS: Record<string, string> = {
  python:     "M14.25.18l.9.2.73.26.59.3.45.32.34.34.25.34.16.33.1.3.04.26.02.2-.01.13V8.5l-.05.63-.13.55-.21.46-.26.38-.3.31-.33.25-.35.19-.35.14-.33.1-.3.07-.26.04-.21.02H8.77l-.69.05-.59.14-.5.22-.41.27-.33.32-.27.35-.2.36-.15.37-.1.35-.07.32-.04.27-.02.21v3.06H3.17l-.21-.03-.28-.07-.32-.12-.35-.18-.36-.26-.36-.36-.35-.46-.32-.59-.28-.73-.21-.88-.14-1.05-.05-1.23.06-1.22.16-1.04.24-.87.32-.71.36-.57.4-.44.42-.33.42-.24.4-.16.36-.1.32-.05.24-.01h.16l.06.01h8.16v-.83H6.18l-.01-2.75-.02-.37.05-.34.11-.31.17-.28.25-.26.31-.23.38-.2.44-.18.51-.15.58-.12.64-.1.71-.06.77-.04.84-.02 1.27.05zm-6.3 1.98l-.23.33-.08.41.08.41.23.34.33.22.41.09.41-.09.33-.22.23-.34.08-.41-.08-.41-.23-.33-.33-.22-.41-.09-.41.09zm13.09 3.95l.28.06.32.12.35.18.36.27.36.35.35.47.32.59.28.73.21.88.14 1.04.05 1.23-.06 1.23-.16 1.04-.24.86-.32.71-.36.57-.4.45-.42.33-.42.24-.4.16-.36.09-.32.05-.24.02-.16-.01h-8.22v.82h5.84l.01 2.76.02.36-.05.34-.11.31-.17.29-.25.25-.31.24-.38.2-.44.17-.51.15-.58.13-.64.09-.71.07-.77.04-.84.01-1.27-.04-1.07-.14-.9-.2-.73-.25-.59-.3-.45-.33-.34-.34-.25-.34-.16-.33-.1-.3-.04-.25-.02-.2.01-.13v-5.34l.05-.64.13-.54.21-.46.26-.38.3-.32.33-.24.35-.2.35-.14.33-.1.3-.06.26-.04.21-.02.13-.01h5.84l.69-.05.59-.14.5-.21.41-.28.33-.32.27-.35.2-.36.15-.36.1-.35.07-.32.04-.28.02-.21V6.07h2.09l.14.01zm-6.47 14.25l-.23.33-.08.41.08.41.23.33.33.23.41.08.41-.08.33-.23.23-.33.08-.41-.08-.41-.23-.33-.33-.23-.41-.08-.41.08z",
  playwright: "M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 14.5v-9l6 4.5-6 4.5z",
  gemini:     "M11.04 19.32Q12 21.51 12 24q0-2.49.93-4.68.96-2.19 2.58-3.81t3.81-2.55Q21.51 12 24 12q-2.49 0-4.68-.93a12.3 12.3 0 0 1-3.81-2.58 12.3 12.3 0 0 1-2.58-3.81Q12 2.49 12 0q0 2.49-.96 4.68-.93 2.19-2.55 3.81a12.3 12.3 0 0 1-3.81 2.58Q2.49 12 0 12q2.49 0 4.68.96 2.19.93 3.81 2.55t2.55 3.81",
  sqlite:     "M21.678.521c-1.032-.92-2.28-.55-3.513.544a8.71 8.71 0 0 0-.547.535c-2.109 2.237-4.066 6.38-4.674 9.544.237.48.422 1.093.544 1.561a13.044 13.044 0 0 1 .164.703s-.019-.071-.096-.296l-.05-.146a1.689 1.689 0 0 0-.033-.08c-.138-.32-.518-.995-.686-1.289-.143.423-.27.818-.376 1.176.484.884.778 2.4.778 2.4s-.025-.099-.147-.442c-.107-.303-.644-1.244-.772-1.464-.217.804-.304 1.346-.226 1.478.152.256.296.698.422 1.186.286 1.1.485 2.44.485 2.44l.017.224a22.41 22.41 0 0 0 .056 2.748c.095 1.146.273 2.13.5 2.657l.155-.084c-.334-1.038-.47-2.399-.41-3.967.09-2.398.642-5.29 1.661-8.304 1.723-4.55 4.113-8.201 6.3-9.945-1.993 1.8-4.692 7.63-5.5 9.788-.904 2.416-1.545 4.684-1.931 6.857.666-2.037 2.821-2.912 2.821-2.912s1.057-1.304 2.292-3.166c-.74.169-1.955.458-2.362.629-.6.251-.762.337-.762.337s1.945-1.184 3.613-1.72C21.695 7.9 24.195 2.767 21.678.521m-18.573.543A1.842 1.842 0 0 0 1.27 2.9v16.608a1.84 1.84 0 0 0 1.835 1.834h9.418a22.953 22.953 0 0 1-.052-2.707c-.006-.062-.011-.141-.016-.2a27.01 27.01 0 0 0-.473-2.378c-.121-.47-.275-.898-.369-1.057-.116-.197-.098-.31-.097-.432 0-.12.015-.245.037-.386a9.98 9.98 0 0 1 .234-1.045l.217-.028c-.017-.035-.014-.065-.031-.097l-.041-.381a32.8 32.8 0 0 1 .382-1.194l.2-.019c-.008-.016-.01-.038-.018-.053l-.043-.316c.63-3.28 2.587-7.443 4.8-9.791.066-.069.133-.128.198-.194Z",
  telegram:   "M11.944 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0a12 12 0 0 0-.056 0zm4.962 7.224c.1-.002.321.023.465.14a.506.506 0 0 1 .171.325c.016.093.036.306.02.472-.18 1.898-.962 6.502-1.36 8.627-.168.9-.499 1.201-.82 1.23-.696.065-1.225-.46-1.9-.902-1.056-.693-1.653-1.124-2.678-1.8-1.185-.78-.417-1.21.258-1.91.177-.184 3.247-2.977 3.307-3.23.007-.032.014-.15-.056-.212s-.174-.041-.249-.024c-.106.024-1.793 1.14-5.061 3.345-.48.33-.913.49-1.302.48-.428-.008-1.252-.241-1.865-.44-.752-.245-1.349-.374-1.297-.789.027-.216.325-.437.893-.663 3.498-1.524 5.83-2.529 6.998-3.014 3.332-1.386 4.025-1.627 4.476-1.635z",
  latex:      "M3 5v3h7v11h4V8h7V5z",
}

const TECH = [
  {
    num: "01", name: "Python", tag: "Core", icon: "python", accent: true,
    desc: "Bot runtime & orchestration",
    why: "Python's async ecosystem — asyncio + Telethon — makes it trivial to hold a persistent Telegram connection while processing jobs concurrently. No threads, no complexity.",
    how: "The entire bot runs as a single asyncio event loop. Telethon listens on a persistent MTProto socket; every new Telegram message fires a coroutine that runs the full pipeline — parse → eligibility → resume → apply — without blocking the listener.",
    snippet: "async def handler(event):\n    job = parse_message(event.raw_text)\n    if check_eligibility(job, profile):\n        await process_job(job)",
  },
  {
    num: "02", name: "Playwright", tag: "Automation", icon: "playwright", accent: false,
    desc: "Headless browser form filling",
    why: "Unlike Selenium, Playwright has first-class async support, auto-waiting, and handles modern SPAs without fragile explicit waits. It's the only tool that can reliably fill Workday forms in 2026.",
    how: "A headless Chromium instance navigates to the ATS URL, extracts every visible input field and its label, sends the field list to Gemini for answer generation, then fills each field programmatically. CAPTCHA detection aborts and pings you on Telegram.",
    snippet: "async with async_playwright() as p:\n    browser = await p.chromium.launch()\n    page = await browser.new_page()\n    await page.goto(url)\n    fields = await extract_fields(page)\n    answers = await generate_answers(fields, profile)",
  },
  {
    num: "03", name: "Gemini 2.5 Flash", tag: "AI", icon: "gemini", accent: true,
    desc: "Eligibility & skill scoring",
    why: "Flash is the sweet spot: fast enough for real-time processing, cheap enough to call on every job post, and smart enough to match skill synonyms ('React' ↔ 'ReactJS', 'ML' ↔ 'machine learning').",
    how: "Used in two places: (1) skill overlap scoring — compares your profile skills against extracted JD keywords, returns a 0–100 match score. (2) form answer generation — given field labels and your profile, generates contextually appropriate answers for every form field.",
    snippet: "# Cheapest-first eligibility\nbatch_ok = check_batch_regex(job, profile)  # free\nexp_ok   = check_experience(job, profile)   # free\nif batch_ok and exp_ok:\n    score = await gemini_skill_score(job, profile)",
  },
  {
    num: "04", name: "SQLite", tag: "Storage", icon: "sqlite", accent: false,
    desc: "Duplicate prevention tracker",
    why: "Zero-config, zero-latency, zero-infrastructure. The bot runs locally or on a single VM — a full Postgres setup would be overkill for a table that stores ~500 application records.",
    how: "Every application is logged with company, role, status, and timestamp. Before processing any job, a COLLATE NOCASE query checks if the same (company, role) pair was applied to before. Applied, skipped, and failed applications are all tracked for audit.",
    snippet: "CREATE TABLE applications (\n  company     TEXT COLLATE NOCASE,\n  role        TEXT COLLATE NOCASE,\n  status      TEXT,\n  skip_reason TEXT,\n  applied_at  DATETIME DEFAULT CURRENT_TIMESTAMP\n);",
  },
  {
    num: "05", name: "Telegram Bot API", tag: "Transport", icon: "telegram", accent: true,
    desc: "Job feed ingestion & alerts",
    why: "Every Indian tech hiring channel already lives on Telegram. MTProto gives us real-time delivery with zero polling latency — the bot sees a job post within milliseconds of it being sent.",
    how: "Telethon connects via MTProto (not the Bot API) so it can read any public channel or group without admin rights. A message handler regex-filters for job posts, then the parsed result enters the pipeline. After apply/fail, a notification fires back to your personal Telegram.",
    snippet: "@client.on(events.NewMessage(chats=CHANNELS))\nasync def on_message(event):\n    if is_job_post(event.raw_text):\n        job = parse_message(event.raw_text)\n        await process_job(job)",
  },
  {
    num: "06", name: "LaTeX", tag: "Typesetting", icon: "latex", accent: false,
    desc: "Per-job resume compilation",
    why: "PDF generation libraries produce inconsistent output across machines. A LaTeX template gives pixel-perfect, ATS-friendly PDFs every time — the same output on macOS, Linux, and Docker.",
    how: "A master .tex template has placeholder tokens for role, company, and JD keywords. For each job, the bot replaces tokens with tailored content extracted from the JD, then shells out to pdflatex to compile. The resulting PDF is uploaded to Google Drive and attached to email applications.",
    snippet: "# In MuditCV.tex\n% ROLE_PLACEHOLDER → Backend Engineer\n% COMPANY_PLACEHOLDER → Stripe\n% KEYWORDS_PLACEHOLDER → distributed systems, Go, gRPC\n\ndef save_pdf(company, role, jd_summary, out_path):\n    tex = template.replace('ROLE', role)\n    subprocess.run(['pdflatex', tex_path])",
  },
]

type Tech = typeof TECH[number]

function TechDialog({ tech, onClose }: { tech: Tech; onClose: () => void }) {
  return (
    <AnimatePresence>
      <motion.div
        className="fixed inset-0 z-[9999] flex items-end md:items-center justify-center"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
        onClick={onClose}
        style={{ background: "rgba(0,0,0,0.7)", backdropFilter: "blur(6px)" }}
      >
        <motion.div
          initial={{ opacity: 0, y: 40, scale: 0.97 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 30, scale: 0.97 }}
          transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
          onClick={e => e.stopPropagation()}
          style={{
            width: "100%", maxWidth: "640px",
            margin: "1rem",
            borderRadius: "20px",
            border: "1px solid var(--border-warm)",
            background: "var(--card)",
            overflow: "hidden",
            maxHeight: "90vh",
            display: "flex", flexDirection: "column",
          }}
        >
          {/* Header */}
          <div style={{
            display: "flex", alignItems: "center", justifyContent: "space-between",
            padding: "1.25rem 1.5rem",
            borderBottom: "1px solid var(--border)",
          }}>
            <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
              <div style={{
                width: "36px", height: "36px", borderRadius: "10px",
                display: "flex", alignItems: "center", justifyContent: "center",
                background: tech.accent ? "rgba(236,78,2,0.09)" : "rgba(240,235,227,0.04)",
                border: `1px solid ${tech.accent ? "rgba(236,78,2,0.22)" : "rgba(240,235,227,0.07)"}`,
                flexShrink: 0,
              }}>
                <svg viewBox="0 0 24 24" width={15} height={15} fill="currentColor"
                  style={{ color: tech.accent ? "var(--rust)" : "var(--ink-dim)" }}>
                  <path d={ICONS[tech.icon]} />
                </svg>
              </div>
              <div>
                <p style={{ fontFamily: "var(--font-body)", fontWeight: 500, fontSize: "1rem", color: "var(--ink)", letterSpacing: "-0.01em" }}>
                  {tech.name}
                </p>
                <p style={{ fontFamily: "var(--font-mono)", fontSize: "9px", letterSpacing: "0.2em", textTransform: "uppercase", color: "var(--rust)" }}>
                  {tech.tag}
                </p>
              </div>
            </div>
            <button onClick={onClose} style={{
              width: "32px", height: "32px", borderRadius: "8px",
              border: "1px solid var(--border)", background: "transparent",
              display: "flex", alignItems: "center", justifyContent: "center",
              color: "var(--ink-dim)", cursor: "pointer",
              transition: "background 0.15s ease, color 0.15s ease",
            }}
              onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = "rgba(240,235,227,0.06)"; (e.currentTarget as HTMLElement).style.color = "var(--ink)"; }}
              onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = "transparent"; (e.currentTarget as HTMLElement).style.color = "var(--ink-dim)"; }}
            >
              <X size={14} strokeWidth={2} />
            </button>
          </div>

          {/* Body */}
          <div style={{ padding: "1.5rem", overflowY: "auto", display: "flex", flexDirection: "column", gap: "1.5rem" }}>

            {/* Why */}
            <div>
              <p style={{ fontFamily: "var(--font-mono)", fontSize: "9px", letterSpacing: "0.22em", textTransform: "uppercase", color: "var(--rust)", marginBottom: "0.6rem" }}>
                Why we chose it
              </p>
              <p style={{ fontFamily: "var(--font-body)", fontSize: "14px", color: "var(--ink-dim)", fontWeight: 300, lineHeight: 1.7 }}>
                {tech.why}
              </p>
            </div>

            {/* How */}
            <div>
              <p style={{ fontFamily: "var(--font-mono)", fontSize: "9px", letterSpacing: "0.22em", textTransform: "uppercase", color: "var(--rust)", marginBottom: "0.6rem" }}>
                How it&apos;s used
              </p>
              <p style={{ fontFamily: "var(--font-body)", fontSize: "14px", color: "var(--ink-dim)", fontWeight: 300, lineHeight: 1.7 }}>
                {tech.how}
              </p>
            </div>

            {/* Code snippet */}
            <div style={{
              borderRadius: "12px",
              border: "1px solid var(--border)",
              background: "rgba(240,235,227,0.02)",
              overflow: "hidden",
            }}>
              <div style={{
                padding: "8px 14px",
                borderBottom: "1px solid var(--border)",
                display: "flex", alignItems: "center", gap: "6px",
              }}>
                <span style={{ width: 7, height: 7, borderRadius: "50%", background: "rgba(240,235,227,0.08)", display: "inline-block" }} />
                <span style={{ width: 7, height: 7, borderRadius: "50%", background: "rgba(240,235,227,0.08)", display: "inline-block" }} />
                <span style={{ width: 7, height: 7, borderRadius: "50%", background: "rgba(236,78,2,0.35)", display: "inline-block" }} />
                <span style={{ fontFamily: "var(--font-mono)", fontSize: "9px", color: "var(--ink-muted)", marginLeft: "6px", letterSpacing: "0.08em" }}>
                  snippet
                </span>
              </div>
              <pre style={{
                fontFamily: "var(--font-mono)", fontSize: "12px",
                color: "var(--ink-dim)", lineHeight: 1.7,
                padding: "1rem 1.25rem",
                margin: 0, overflowX: "auto",
                whiteSpace: "pre",
              }}>
                {tech.snippet}
              </pre>
            </div>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  )
}

function StackRow({ tech, delay }: { tech: Tech; delay: number }) {
  const [open, setOpen] = useState(false)
  const { num, name, tag, desc, icon, accent } = tech

  return (
    <>
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, amount: 0.3 }}
        transition={{ duration: 0.35, delay, ease: "easeOut" }}
        onClick={() => setOpen(true)}
        className="stack-row-hover"
        style={{
          borderTop: "1px solid var(--border)",
          display: "flex",
          alignItems: "center",
          gap: "1.5rem",
          padding: "1.25rem 0.5rem",
          transition: "background-color 0.2s ease",
          borderRadius: "4px",
          cursor: "pointer",
        }}
      >
        <span className="stack-num-hover" style={{
          fontFamily: "var(--font-serif)", fontWeight: 500, fontSize: "1rem",
          color: "var(--border-warm)", letterSpacing: "-0.01em",
          minWidth: "2rem", transition: "color 0.2s ease",
        }}>
          {num}
        </span>

        <div style={{
          width: "32px", height: "32px", flexShrink: 0,
          borderRadius: "9px", display: "flex", alignItems: "center", justifyContent: "center",
          background: accent ? "rgba(236,78,2,0.09)" : "rgba(240,235,227,0.04)",
          border: `1px solid ${accent ? "rgba(236,78,2,0.22)" : "rgba(240,235,227,0.07)"}`,
        }}>
          <svg viewBox="0 0 24 24" width={14} height={14} fill="currentColor"
            style={{ color: accent ? "var(--rust)" : "var(--ink-dim)" }}>
            <path d={ICONS[icon]} />
          </svg>
        </div>

        <span style={{
          fontFamily: "var(--font-body)", fontWeight: 500, fontSize: "1rem",
          color: "var(--ink)", letterSpacing: "-0.02em",
          flex: "0 0 180px", minWidth: 0,
        }}>
          {name}
        </span>

        <span style={{
          fontFamily: "var(--font-mono)", fontSize: "9px",
          letterSpacing: "0.2em", textTransform: "uppercase",
          color: "var(--rust)", flex: "0 0 110px",
        }}>
          {tag}
        </span>

        <span style={{
          fontFamily: "var(--font-body)", fontSize: "13px",
          color: "var(--ink-muted)", fontWeight: 300, flex: 1,
        }}>
          {desc}
        </span>

        <span className="stack-arrow-hover" style={{
          fontFamily: "var(--font-mono)", fontSize: "13px",
          color: "var(--border-warm)",
          transition: "color 0.2s ease, transform 0.2s ease",
          display: "inline-block", flexShrink: 0,
        }}>
          →
        </span>
      </motion.div>

      {open && <TechDialog tech={tech} onClose={() => setOpen(false)} />}
    </>
  )
}

export default function TechStack() {
  return (
    <section id="stack" className="py-28 px-8 md:px-14" style={{ borderTop: "1px solid var(--border)" }}>
      <div className="max-w-6xl mx-auto">

        <motion.p className="section-eyebrow mb-4"
          initial={{ opacity: 0 }} whileInView={{ opacity: 1 }} viewport={{ once: true }}>
          Built with
        </motion.p>

        <motion.h2 className="section-heading mb-20"
          style={{ fontSize: "clamp(2.4rem, 4vw, 4rem)" }}
          initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }} transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}>
          The stack.<br />
          <span style={{ color: "var(--ink-dim)", fontStyle: "italic" }}>No fluff.</span>
        </motion.h2>

        <div>
          {TECH.map((tech, i) => (
            <StackRow key={tech.name} tech={tech} delay={i * 0.06} />
          ))}
          <div style={{ borderTop: "1px solid var(--border)" }} />
        </div>
      </div>
    </section>
  )
}
