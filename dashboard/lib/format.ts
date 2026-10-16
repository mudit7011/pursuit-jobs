import type { Status } from "./api";

export const STATUS_LABEL: Record<Status, string> = {
  skipped: "Skipped",
  dismissed: "Dismissed",
  failed: "Needs you",
  pending_approval: "Waiting for you",
  approved: "Queued to apply",
  applying: "Applying now",
  applied: "Applied",
  screening: "Screening",
  interview: "Interview",
  offer: "Offer",
  rejected: "Rejected",
  ghosted: "No reply",
};

// Maps a status to its CSS token (see globals.css --st-*)
export const STATUS_TONE: Record<Status, string> = {
  skipped: "muted", dismissed: "muted", failed: "warn",
  pending_approval: "accent", approved: "info", applying: "info",
  applied: "info", screening: "teal", interview: "teal", offer: "good",
  rejected: "bad", ghosted: "muted",
};

export const PIPELINE: Status[] = ["applied", "screening", "interview", "offer", "rejected", "ghosted"];

const PLATFORM_LABEL: Record<string, string> = {
  linkedin: "LinkedIn", naukri: "Naukri", indeed: "Indeed", wellfound: "Wellfound",
  internshala: "Internshala", instahyre: "Instahyre", email: "Email", "google form": "Google Form", "web form": "Company site",
  telegram: "Telegram",
};
export const platformLabel = (p: string) => PLATFORM_LABEL[p] ?? p.replace(/\b\w/g, (c) => c.toUpperCase());

const rtf = new Intl.RelativeTimeFormat("en", { numeric: "auto" });
export function ago(iso: string | null | undefined): string {
  if (!iso) return "—";
  const diff = (new Date(iso).getTime() - Date.now()) / 1000;
  const abs = Math.abs(diff);
  if (abs < 60) return "just now";
  if (abs < 3600) return rtf.format(Math.round(diff / 60), "minute");
  if (abs < 86400) return rtf.format(Math.round(diff / 3600), "hour");
  if (abs < 86400 * 30) return rtf.format(Math.round(diff / 86400), "day");
  return new Date(iso).toLocaleDateString("en-IN", { day: "numeric", month: "short" });
}

export function fullDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("en-IN", {
    day: "numeric", month: "short", hour: "numeric", minute: "2-digit",
  });
}

export const nf = new Intl.NumberFormat("en-IN");

export function hoursSaved(minutes: number): string {
  if (minutes < 60) return `${minutes} min`;
  const h = minutes / 60;
  return `${h >= 10 ? Math.round(h) : h.toFixed(1)} h`;
}

export function greeting(): string {
  const h = new Date().getHours();
  if (h < 5) return "Late night";
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  return "Good evening";
}
