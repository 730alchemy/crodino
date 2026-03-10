import { useState, useMemo } from 'react'
import { useSearchParams, Link } from 'react-router-dom'
import { getRun, taxonomy } from '@/data'
import { formatPct, formatRunDate } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'

type CompareFilter = 'all' | 'inversions' | 'regressions' | 'gains'
type SortKey = 'element' | 'a' | 'b' | 'delta'
type SortDir = 'asc' | 'desc'

export function RunComparison() {
  const [searchParams] = useSearchParams()
  const ids = searchParams.get('ids')?.split(',') ?? []
  const [filter, setFilter] = useState<CompareFilter>('all')
  const [sortKey, setSortKey] = useState<SortKey>('delta')
  const [sortDir, setSortDir] = useState<SortDir>('desc')

  const runA = getRun(ids[0] ?? '')
  const runB = getRun(ids[1] ?? '')

  function handleSort(key: SortKey) {
    if (sortKey === key) setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    else { setSortKey(key); setSortDir('desc') }
  }

  const rows = useMemo(() => {
    if (!runA || !runB) return []
    return taxonomy.elements.map(el => {
      const a = runA.summary.task_results[el.id]?.mean_score ?? 0
      const b = runB.summary.task_results[el.id]?.mean_score ?? 0
      const delta = b - a
      return { el, a, b, delta }
    })
  }, [runA, runB])

  const filtered = rows.filter(({ a, b, delta }) => {
    if (filter === 'inversions') {
      return (a >= 0.6 && b < 0.6) || (a < 0.6 && b >= 0.6)
    }
    if (filter === 'regressions') return delta < 0
    if (filter === 'gains') return delta > 0
    return true
  })

  const sorted = [...filtered].sort((x, y) => {
    let cmp = 0
    if (sortKey === 'element') cmp = x.el.name.localeCompare(y.el.name)
    else if (sortKey === 'a') cmp = x.a - y.a
    else if (sortKey === 'b') cmp = x.b - y.b
    else cmp = Math.abs(x.delta) - Math.abs(y.delta)
    return sortDir === 'asc' ? cmp : -cmp
  })

  if (!runA || !runB) {
    return <div className="p-6 text-zinc-500">Select exactly 2 runs to compare.</div>
  }

  function SortTh({ k, label }: { k: SortKey; label: string }) {
    return (
      <th
        className="px-4 py-3 text-left text-zinc-400 font-medium cursor-pointer hover:text-white select-none"
        onClick={() => handleSort(k)}
      >
        {label} {sortKey === k ? (sortDir === 'asc' ? '↑' : '↓') : ''}
      </th>
    )
  }

  const filterBtn = (f: CompareFilter, label: string) => (
    <button
      key={f}
      onClick={() => setFilter(f)}
      className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
        filter === f ? 'bg-zinc-700 text-white' : 'text-zinc-400 hover:text-white hover:bg-zinc-800'
      }`}
    >
      {label}
    </button>
  )

  return (
    <div className="p-6 max-w-screen-xl mx-auto">
      {/* Header */}
      <div className="flex flex-wrap gap-8 mb-6">
        {[runA, runB].map((run, i) => (
          <div key={i}>
            <div className="text-xs text-zinc-500 mb-1">Run {String.fromCharCode(65 + i)} — {formatRunDate(run.summary.run_id)}</div>
            <div className="text-lg font-semibold text-white">{run.summary.target_model}</div>
            <Badge variant={run.summary.overall_pass_rate >= 0.6 ? 'pass' : 'fail'}>
              {formatPct(run.summary.overall_pass_rate)}
            </Badge>
          </div>
        ))}
      </div>

      {/* Filter */}
      <div className="flex flex-wrap items-center gap-1 mb-6">
        {filterBtn('all', 'All')}
        {filterBtn('inversions', 'Inversions Only')}
        {filterBtn('regressions', 'Regressions')}
        {filterBtn('gains', 'Gains')}
      </div>

      {/* Table */}
      <div className="overflow-x-auto rounded-lg border border-zinc-800">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-zinc-800 bg-zinc-900">
              <SortTh k="element" label="Element" />
              <SortTh k="a" label={`Run A (${runA.summary.target_model})`} />
              <SortTh k="b" label={`Run B (${runB.summary.target_model})`} />
              <SortTh k="delta" label="Delta" />
            </tr>
          </thead>
          <tbody>
            {sorted.map(({ el, a, b, delta }) => (
              <tr key={el.id} className="border-b border-zinc-800/30 hover:bg-zinc-900/30 transition-colors">
                <td className="px-4 py-2">
                  <Link to={`/tasks/${el.id}`} className="text-blue-400 hover:underline">
                    {el.name}
                  </Link>
                </td>
                <td className="px-4 py-2 font-mono text-zinc-300">{a.toFixed(3)}</td>
                <td className="px-4 py-2 font-mono text-zinc-300">{b.toFixed(3)}</td>
                <td className={`px-4 py-2 font-mono font-semibold ${
                  delta > 0.001 ? 'text-green-400' : delta < -0.001 ? 'text-red-400' : 'text-zinc-500'
                }`}>
                  {delta > 0.001 ? '↑' : delta < -0.001 ? '↓' : ''} {delta >= 0 ? '+' : ''}{delta.toFixed(3)}
                </td>
              </tr>
            ))}
            {sorted.length === 0 && (
              <tr>
                <td colSpan={4} className="px-4 py-8 text-center text-zinc-500">
                  No elements match the current filter.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
