import type { Metadata } from "next"
import PageHero from "@/components/site/page-hero"
import Tour from "@/components/site/tour"
import { Desk } from "@/components/ui/desk"

export const metadata: Metadata = { title: "Dashboard" }

export default function Dashboard() {
  return (
    <>
      <PageHero
        image="/nature/dolomites.webp"
        position="center 40%"
        title="Your whole job hunt, on one calm page"
        sub="It runs on your laptop next to the bot. These screens use made-up jobs."
      />
      <div className="-mt-[22vh] relative z-10"><Tour /></div>
      <Desk />
    </>
  )
}
