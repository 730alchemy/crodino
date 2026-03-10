import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { runs } from '@/data'
import { formatPct, formatRunDate } from '@/lib/utils'

export function RunsList() {
  const navigate = useNavigate()
  const [selected, setSelected] = useState<Set<string>>(new Set())

  function toggleSelect(runId: string, e: React.ChangeEvent<HTMLInputElement>) {
    e.stopPropagation()
    setSelected(prev => {
      const next = new Set(prev)
      if (next.has(runId)) next.delete(runId)
      else next.add(runId)
      return next
    })
  }

  function handleCompare() {
    const ids = Array.from(selected)
    navigate(`/runs/compare?ids=${ids.join(',')}`)
  }

  return (
    <div className="p-6 max-w-screen-xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-white">Runs</h1>
        <Button
          onClick={handleCompare}
          disabled={selected.size !== 2}
          variant="outline"
          className="border-zinc-700 text-zinc-300"
        >
          Compare Selected ({selected.size}/2)
        </Button>
      </div>

      <div className="overflow-x-auto rounded-lg border border-zinc-800">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-zinc-800 bg-zinc-900">
              <th className="w-10 px-4 py-3 text-left"></th>
              <th className="px-4 py-3 text-left text-zinc-400 font-medium">Run ID</th>
              <th className="px-4 py-3 text-left text-zinc-400 font-medium">Model</th>
              <th className="px-4 py-3 text-right text-zinc-400 font-medium">Trials</th>
              <th className="px-4 py-3 text-right text-zinc-400 font-medium">Tasks</th>
              <th className="px-4 py-3 text-right text-zinc-400 font-medium">Pass Rate</th>
              <th className="px-4 py-3 text-left text-zinc-400 font-medium">Date</th>
            </tr>
          </thead>
          <tbody>
            {runs.map(run => (
              <tr
                key={run.summary.run_id}
                className="border-b border-zinc-800/50 hover:bg-zinc-900 cursor-pointer transition-colors"
                onClick={() => navigate(`/runs/${run.summary.run_id}`)}
              >
                <td className="px-4 py-3" onClick={e => e.stopPropagation()}>
                  <input
                    type="checkbox"
                    checked={selected.has(run.summary.run_id)}
                    onChange={e => toggleSelect(run.summary.run_id, e)}
                    className="rounded border-zinc-600"
                  />
                </td>
                <td className="px-4 py-3 font-mono text-xs text-zinc-400">{run.summary.run_id}</td>
                <td className="px-4 py-3 text-zinc-300">{run.summary.target_model}</td>
                <td className="px-4 py-3 text-right text-zinc-400">{run.summary.n_trials}</td>
                <td className="px-4 py-3 text-right text-zinc-400">{run.summary.n_tasks}</td>
                <td className="px-4 py-3 text-right font-semibold text-white">
                  {formatPct(run.summary.overall_pass_rate)}
                </td>
                <td className="px-4 py-3 text-zinc-400">{formatRunDate(run.summary.run_id)}</td>
              </tr>
            ))}
            {runs.length === 0 && (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-zinc-500">
                  No runs found.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
