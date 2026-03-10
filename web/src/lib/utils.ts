import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function scoreColor(score: number): string {
  if (score >= 0.90) return 'text-green-400'
  if (score >= 0.75) return 'text-green-600'
  if (score >= 0.60) return 'text-yellow-400'
  if (score >= 0.40) return 'text-orange-400'
  return 'text-red-400'
}

export function scoreBg(score: number): string {
  if (score >= 0.90) return 'bg-green-500/20 text-green-300 border-green-500/40'
  if (score >= 0.75) return 'bg-green-700/20 text-green-400 border-green-700/40'
  if (score >= 0.60) return 'bg-yellow-500/20 text-yellow-300 border-yellow-500/40'
  if (score >= 0.40) return 'bg-orange-500/20 text-orange-300 border-orange-500/40'
  return 'bg-red-500/20 text-red-300 border-red-500/40'
}

export function scoreHeatBg(score: number): string {
  if (score >= 0.90) return 'bg-green-500/40 hover:bg-green-500/60'
  if (score >= 0.75) return 'bg-green-700/30 hover:bg-green-700/50'
  if (score >= 0.60) return 'bg-yellow-600/30 hover:bg-yellow-600/50'
  if (score >= 0.40) return 'bg-orange-500/30 hover:bg-orange-500/50'
  return 'bg-red-500/30 hover:bg-red-500/50'
}

export function labelColor(label: string): string {
  switch (label) {
    case 'excellent': return 'text-green-400'
    case 'good': return 'text-yellow-300'
    case 'partial': return 'text-orange-400'
    case 'poor': return 'text-red-400'
    default: return 'text-zinc-400'
  }
}

export function formatRunDate(runId: string): string {
  // run_id format: YYYYMMDD_HHMMSS
  const m = runId.match(/^(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})$/)
  if (!m) return runId
  const [, year, month, day, hour, minute] = m
  return `${year}-${month}-${day} ${hour}:${minute}`
}

export function formatPct(rate: number): string {
  return `${(rate * 100).toFixed(1)}%`
}
