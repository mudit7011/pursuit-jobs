import type { Metadata } from "next"
import PageHero from "@/components/site/page-hero"
import { Run } from "@/components/ui/desk"
import Faq from "@/components/site/faq"

export const metadata: Metadata = { title: "Get started" }

export default function GetStarted() {
  return (
    <>
      <PageHero
        image="/nature/sea-of-clouds.webp"
        ink="light"
        title="Set it up on your laptop"
        sub="Free and open source. It runs next to you, not on someone else's server."
      />
      <div className="relative z-10 pt-6"><Run /></div>
      <Faq />
    </>
  )
}
