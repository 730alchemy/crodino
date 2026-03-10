import { useState, useEffect } from 'react'
import { useParams, useSearchParams, useNavigate, Link } from 'react-router-dom'
import { ChevronDown, ChevronUp } from 'lucide-react'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { ScorePill } from '@/components/ScorePill'
import { getTask, getTaxonomyElement, getTaxonomyCategory, runs } from '@/data'
import { formatRunDate } from '@/lib/utils'

export function TaskDetail() {
  const { elementId } = useParams<{ elementId: string }>()
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const [showRef, setShowRef] = useState(false)
  const [expandedDims, setExpandedDims] = useState<Set<string>>(new Set())
  const tabParam = searchParams.get('tab')
  const defaultTab = tabParam === 'results' ? 'results' : 'prompt'
  const [activeTab, setActiveTab] = useState(defaultTab)

  useEffect(() => {
    if (tabParam === 'results') setActiveTab('results')
  }, [tabParam])

  const task = elementId ? getTask(elementId) : undefined
  const element = elementId ? getTaxonomyElement(elementId) : undefined

  if (!task || !element) {
    return <div className="p-6 text-zinc-500">Task not found.</div>
  }

  const category = getTaxonomyCategory(element.category)

  // Runs that have this element
  const relevantRuns = runs.filter(r => r.summary.task_results[element.id])

  function toggleDim(name: string) {
    setExpandedDims(prev => {
      const next = new Set(prev)
      if (next.has(name)) next.delete(name)
      else next.add(name)
      return next
    })
  }

  return (
    <div className="p-6 max-w-screen-xl mx-auto">
      {/* Breadcrumb */}
      <div className="text-xs text-zinc-500 mb-4">
        <Link to="/taxonomy" className="hover:text-zinc-300">Taxonomy</Link>
        {' / '}
        <span>{category?.name}</span>
        {element.subcategory && <span> / {element.subcategory.replace(/_/g, ' ')}</span>}
        {' / '}
        <span className="text-zinc-300">{element.name}</span>
      </div>

      <h1 className="text-2xl font-bold text-white mb-6">{element.name}</h1>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="mb-6">
          <TabsTrigger value="prompt">Prompt</TabsTrigger>
          <TabsTrigger value="rubric">Rubric</TabsTrigger>
          <TabsTrigger value="reference">Reference Solution</TabsTrigger>
          <TabsTrigger value="results">Results</TabsTrigger>
        </TabsList>

        {/* Prompt Tab */}
        <TabsContent value="prompt">
          <div className="space-y-6">
            <div>
              <h3 className="text-xs font-semibold uppercase tracking-wider text-zinc-500 mb-3">Task Prompt</h3>
              <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
                <pre className="text-sm text-zinc-300 whitespace-pre-wrap font-sans">{task.prompt}</pre>
              </div>
            </div>
            {task.success_criteria.length > 0 && (
              <div>
                <h3 className="text-xs font-semibold uppercase tracking-wider text-zinc-500 mb-3">Success Criteria</h3>
                <ul className="space-y-2">
                  {task.success_criteria.map((crit, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-zinc-300">
                      <span className="mt-0.5 h-4 w-4 shrink-0 rounded border border-zinc-600 flex items-center justify-center text-[10px] text-zinc-500">
                        {i + 1}
                      </span>
                      {crit}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </TabsContent>

        {/* Rubric Tab */}
        <TabsContent value="rubric">
          <div className="overflow-x-auto rounded-lg border border-zinc-800">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-zinc-800 bg-zinc-900">
                  <th className="px-4 py-3 text-left text-zinc-400 font-medium">Dimension</th>
                  <th className="px-4 py-3 text-right text-zinc-400 font-medium">Weight</th>
                  <th className="px-4 py-3 text-left text-zinc-400 font-medium">Criteria</th>
                  <th className="px-4 py-3 w-10"></th>
                </tr>
              </thead>
              <tbody>
                {task.rubric.map(dim => (
                  <>
                    <tr
                      key={dim.name}
                      className="border-b border-zinc-800/30 hover:bg-zinc-900/30 cursor-pointer transition-colors"
                      onClick={() => toggleDim(dim.name)}
                    >
                      <td className="px-4 py-2 font-medium text-zinc-300 capitalize">
                        {dim.name.replace(/_/g, ' ')}
                      </td>
                      <td className="px-4 py-2 text-right text-zinc-400">
                        {(dim.weight * 100).toFixed(0)}%
                      </td>
                      <td className="px-4 py-2 text-zinc-400 text-xs max-w-md">{dim.criteria}</td>
                      <td className="px-4 py-2 text-zinc-600">
                        {expandedDims.has(dim.name) ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                      </td>
                    </tr>
                    {expandedDims.has(dim.name) && (
                      <tr key={`${dim.name}-expanded`} className="border-b border-zinc-800/30 bg-zinc-900/20">
                        <td colSpan={4} className="px-6 py-3">
                          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
                            {Object.entries(dim.scores).map(([level, desc]) => (
                              <div key={level} className="space-y-1">
                                <div className={`font-semibold capitalize ${
                                  level === 'excellent' ? 'text-green-400' :
                                  level === 'good' ? 'text-yellow-300' :
                                  level === 'partial' ? 'text-orange-400' : 'text-red-400'
                                }`}>{level}</div>
                                <div className="text-zinc-400 leading-relaxed">{desc}</div>
                              </div>
                            ))}
                          </div>
                        </td>
                      </tr>
                    )}
                  </>
                ))}
              </tbody>
            </table>
          </div>
        </TabsContent>

        {/* Reference Solution Tab */}
        <TabsContent value="reference">
          <div>
            <button
              onClick={() => setShowRef(r => !r)}
              className="flex items-center gap-2 text-sm font-medium text-zinc-400 hover:text-white transition-colors mb-4"
            >
              {showRef ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
              {showRef ? 'Hide' : 'Show'} Reference Solution
            </button>
            {showRef && (
              <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
                <pre className="text-sm text-zinc-300 whitespace-pre-wrap font-sans">{task.reference_solution}</pre>
              </div>
            )}
          </div>
        </TabsContent>

        {/* Results Tab */}
        <TabsContent value="results">
          <div className="overflow-x-auto rounded-lg border border-zinc-800">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-zinc-800 bg-zinc-900">
                  <th className="px-4 py-3 text-left text-zinc-400 font-medium">Run</th>
                  <th className="px-4 py-3 text-left text-zinc-400 font-medium">Model</th>
                  <th className="px-4 py-3 text-left text-zinc-400 font-medium">Trials</th>
                  <th className="px-4 py-3 text-right text-zinc-400 font-medium">Mean Score</th>
                </tr>
              </thead>
              <tbody>
                {relevantRuns.map(run => {
                  const result = run.summary.task_results[element.id]
                  return (
                    <tr key={run.summary.run_id} className="border-b border-zinc-800/30 hover:bg-zinc-900/30 transition-colors">
                      <td className="px-4 py-2">
                        <Link
                          to={`/runs/${run.summary.run_id}`}
                          className="font-mono text-xs text-blue-400 hover:underline"
                        >
                          {run.summary.run_id}
                        </Link>
                        <div className="text-[10px] text-zinc-600">{formatRunDate(run.summary.run_id)}</div>
                      </td>
                      <td className="px-4 py-2 text-zinc-300">{run.summary.target_model}</td>
                      <td className="px-4 py-2">
                        <div className="flex items-center gap-1 flex-wrap">
                          {result.scores.map((score, i) => (
                            <ScorePill
                              key={i}
                              score={score}
                              onClick={() => navigate(`/transcripts/${run.summary.run_id}/${element.id}/${i}`)}
                            />
                          ))}
                        </div>
                      </td>
                      <td className="px-4 py-2 text-right text-zinc-300">{result.mean_score.toFixed(3)}</td>
                    </tr>
                  )
                })}
                {relevantRuns.length === 0 && (
                  <tr>
                    <td colSpan={4} className="px-4 py-8 text-center text-zinc-500">No results yet.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}
