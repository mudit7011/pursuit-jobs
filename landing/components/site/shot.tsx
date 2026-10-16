/* A dashboard screenshot in a soft glass frame, like a window resting on the landscape. */
export default function Shot({ src, alt, className = "", priority = false }: { src: string; alt: string; className?: string; priority?: boolean }) {
  return (
    <div
      className={"rounded-[22px] p-1.5 md:p-2 " + className}
      style={{
        background: "rgba(251,251,249,0.55)",
        backdropFilter: "blur(14px)",
        WebkitBackdropFilter: "blur(14px)",
        boxShadow: "0 40px 90px -30px rgba(19,19,18,0.55), 0 0 0 1px rgba(255,255,255,0.45) inset",
      }}
    >
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={src} alt={alt} width={2880} height={1800} loading={priority ? "eager" : "lazy"} className="block h-auto w-full rounded-[16px]" />
    </div>
  )
}
