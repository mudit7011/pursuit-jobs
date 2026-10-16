/* The Pursuit mark: a P whose bowl holds a yellow point, the thing you're going after. */
export function Mark({ size = 32 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden className="shrink-0">
      <rect width="32" height="32" rx="9" fill="#131312" />
      <path d="M11.5 24.5V8h6a6.25 6.25 0 0 1 0 12.5h-6" fill="none" stroke="#fbfaf4" strokeWidth="3.2" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="17.4" cy="14.25" r="2.5" fill="#f3d23f" />
    </svg>
  )
}

export default function Logo({ size = 32 }: { size?: number }) {
  return (
    <span className="inline-flex items-center gap-2.5">
      <Mark size={size} />
      <span className="text-[17px] font-semibold tracking-[-0.035em]" style={{ fontFamily: "var(--font-day)" }}>Pursuit</span>
    </span>
  )
}
