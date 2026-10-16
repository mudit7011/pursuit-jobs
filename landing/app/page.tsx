import Hero from "@/components/home/hero"
import { DeskTeaser, Journey, Morning, PlatformStrip, Rules } from "@/components/home/sections"

export default function Home() {
  return (
    <>
      <Hero />
      <PlatformStrip />
      <Journey />
      <Morning />
      <DeskTeaser />
      <Rules />
    </>
  )
}
