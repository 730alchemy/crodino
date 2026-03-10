import { useState } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { Badge } from '@/components/ui/badge'
import { ScorePill } from '@/components/ScorePill'
import { getRun, taxonomy } from '@/data'
import { formatPct, formatRunDate } from '@/lib/utils'

type Filter = 'all' | 'pass' | 'fail'
type GroupBy = 'category' | 'score'

export function RunDetail() {
  const { runId } = useParams<{ runId: string }>()
  const navigate = useNavigate()
  const [filter, setFilter] = useState<Filter>('all')
  const [groupBy, setGroupBy] = useState<GroupBy>('category')

  const run = runId ? getRun(runId) : undefined
  if (!run) {
    return <div className="p-6 text-zinc-500">Run not found.</div>
  }

  const { summary } = run

  // Build element rows
  const allElements = taxonomy.elements.map(el => {
    const result = summary.task_results[el.id]
    return { el, result }
  }).filter(({ result }) => {
    if (!result) return false
    if (filter === 'pass') return result.pass_rate >= 0.5
    if (filter === 'fail') return result.pass_rate < 0.5
    return true
  })

  const filterBtn = (f: Filter, label: string) => (
    <button
      onClick={() => setFilter(f)}
      className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
        filter === f ? 'bg-zinc-700 text-white' : 'text-zinc-400 hover:text-white hover:bg-zinc-800'
      }`}
    >
      {label}
    </button>
  )

  function renderTable(rows: typeof allElements) {
    if (rows.length === 0) return <div className="px-4 py-3 text-xs text-zinc-500">No elements.</div>
    return (
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-zinc-800 bg-zinc-900/50">
              <th className="px-4 py-2 text-left text-zinc-400 font-medium">Element</th>
              <th className="px-4 py-2 text-right text-zinc-400 font-medium">Pass Rate</th>
              <th className="px-4 py-2 text-right text-zinc-400 font-medium">Mean Score</th>
              <th className="px-4 py-2 text-left text-zinc-400 font-medium">Trials</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(({ el, result }) => (
              <tr key={el.id} className="border-b border-zinc-800/30 hover:bg-zinc-900/30 transition-colors">
                <td className="px-4 py-2">
                  <Link
                    to={`/tasks/${el.id}`}
                    className="text-blue-400 hover:text-blue-300 hover:underline"
                  >
                    {el.name}
                  </Link>
                </td>
                <td className="px-4 py-2 text-right text-zinc-300">{formatPct(result.pass_rate)}</td>
                <td className="px-4 py-2 text-right text-zinc-300">{result.mean_score.toFixed(3)}</td>
                <td className="px-4 py-2">
                  <div className="flex items-center gap-1 flex-wrap">
                    {result.scores.map((score, i) => (
                      <ScorePill
                        key={i}
                        score={score}
                        onClick={() => navigate(`/transcripts/${runId}/${el.id}/${i}`)}
                      />
                    ))}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    )
  }

  return (
    <div className="p-6 max-w-screen-xl mx-auto">
      {/* Header */}
      <div className="flex flex-wrap items-start gap-4 mb-6">
        <div>
          <div className="text-xs text-zinc-500 mb-1">{formatRunDate(summary.run_id)}</div>
          <h1 className="text-xl font-bold text-white">{summary.target_model}</h1>
          <div className="flex items-center gap-3 mt-2 text-sm text-zinc-400">
            <span>{summary.n_trials} trials</span>
            <span>{summary.n_tasks} tasks</span>
            <Badge variant={summary.overall_pass_rate >= 0.6 ? 'pass' : 'fail'}>
              {formatPct(summary.overall_pass_rate)} pass rate
            </Badge>
          </div>
        </div>
      </div>

      {/* Filter / Group toolbar */}
      <div className="flex flex-wrap items-center gap-4 mb-6">
        <div className="flex items-center gap-1">
          {filterBtn('all', 'All')}
          {filterBtn('pass', 'Pass Only')}
          {filterBtn('fail', 'Fail Only')}
        </div>
        <div className="flex items-center gap-2 text-sm">
          <span className="text-zinc-500">Group by:</span>
          <select
            value={groupBy}
            onChange={e => setGroupBy(e.target.value as GroupBy)}
            className="bg-zinc-800 border border-zinc-700 rounded-md px-2 py-1 text-zinc-300 text-sm"
          >
            <option value="category">Category</option>
            <option value="score">Score</option>
          </select>
        </div>
      </div>

      {/* Content */}
      {groupBy === 'category' ? (
        <div className="space-y-6">
          {taxonomy.categories.map(cat => {
            const rows = allElements.filter(({ el }) => el.category === cat.id)
            if (rows.length === 0) return null
            return (
              <div key={cat.id} className="rounded-lg border border-zinc-800">
                <div className="px-4 py-3 bg-zinc-900 rounded-t-lg border-b border-zinc-800">
                  <h3 className="text-sm font-semibold text-zinc-300">{cat.name}</h3>
                </div>
                {renderTable(rows)}
              </div>
            )
          })}
        </div>
      ) : (
        <div className="rounded-lg border border-zinc-800">
          {renderTable(
            [...allElements].sort((a, b) => (a.result?.mean_score ?? 0) - (b.result?.mean_score ?? 0))
          )}
        </div>
      )}
    </div>
  )
}
