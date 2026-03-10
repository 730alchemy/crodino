import { useNavigate } from 'react-router-dom'
import { Card, CardContent } from '@/components/ui/card'
import { runs, taxonomy } from '@/data'
import { formatPct, formatRunDate, scoreHeatBg } from '@/lib/utils'

export function Dashboard() {
  const navigate = useNavigate()
  const mostRecent = runs[0]

  return (
    <div className="p-6 max-w-screen-xl mx-auto space-y-8">
      <h1 className="text-2xl font-bold text-white">Dashboard</h1>

      {/* Run Summary Cards */}
      <div className="flex flex-wrap gap-4">
        {runs.map(run => (
          <Card
            key={run.summary.run_id}
            className="cursor-pointer border-zinc-800 bg-zinc-900 hover:bg-zinc-800 transition-colors min-w-[200px]"
            onClick={() => navigate(`/runs/${run.summary.run_id}`)}
          >
            <CardContent className="p-5">
              <div className="text-xs text-zinc-500 mb-1">{formatRunDate(run.summary.run_id)}</div>
              <div className="text-sm font-medium text-zinc-300 mb-3 truncate">{run.summary.target_model}</div>
              <div className="text-4xl font-bold text-white mb-3">
                {formatPct(run.summary.overall_pass_rate)}
              </div>
              <div className="flex gap-4 text-xs text-zinc-500">
                <span>{run.summary.n_trials} trial{run.summary.n_trials !== 1 ? 's' : ''}</span>
                <span>{run.summary.n_tasks} tasks</span>
              </div>
            </CardContent>
          </Card>
        ))}
        {runs.length === 0 && (
          <div className="text-zinc-500 text-sm">No runs available yet.</div>
        )}
      </div>

      {/* Heatmap for most recent run */}
      {mostRecent && (
        <div>
          <h2 className="text-lg font-semibold text-zinc-300 mb-4">
            Element Heatmap — {mostRecent.summary.target_model}
          </h2>
          <div className="space-y-2">
            {taxonomy.categories.map(cat => {
              const elements = taxonomy.elements.filter(e => e.category === cat.id)
              return (
                <div key={cat.id} className="flex items-start gap-3">
                  <div className="w-52 shrink-0 text-right text-xs font-medium text-zinc-400 pt-2 leading-tight">
                    {cat.name}
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {elements.map(el => {
                      const result = mostRecent.summary.task_results[el.id]
                      const score = result?.mean_score ?? 0
                      return (
                        <button
                          key={el.id}
                          onClick={() => navigate(`/tasks/${el.id}`)}
                          title={`${el.name}: ${score.toFixed(2)}`}
                          className={`h-12 w-28 rounded border border-zinc-700/50 text-xs font-medium text-white transition-colors text-center px-1 leading-tight ${scoreHeatBg(score)}`}
                        >
                          <span className="line-clamp-2">{el.name}</span>
                          <span className="block text-[10px] opacity-80">{score.toFixed(2)}</span>
                        </button>
                      )
                    })}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
