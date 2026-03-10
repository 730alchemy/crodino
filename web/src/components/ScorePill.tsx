import { cn, scoreBg } from '@/lib/utils'

interface ScorePillProps {
  score: number
  onClick?: () => void
  className?: string
}

export function ScorePill({ score, onClick, className }: ScorePillProps) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'inline-flex items-center justify-center rounded-full border px-2 py-0.5 text-xs font-mono font-semibold transition-opacity',
        scoreBg(score),
        onClick ? 'cursor-pointer hover:opacity-80' : 'cursor-default',
        className
      )}
    >
      {score.toFixed(2)}
    </button>
  )
}
