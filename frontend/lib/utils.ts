import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatScore(score: number | undefined | null): string {
  if (score === undefined || score === null) return "0.00";
  return score.toFixed(2);
}

export function formatPercent(val: number | undefined | null): string {
  if (val === undefined || val === null) return "0%";
  return `${Math.round(val * 100)}%`;
}

export function truncateText(text: string, maxLength: number): string {
  if (!text) return "";
  if (text.length <= maxLength) return text;
  return text.slice(0, maxLength) + "...";
}
