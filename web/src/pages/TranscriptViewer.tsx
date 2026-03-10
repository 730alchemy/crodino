import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { ChevronDown, ChevronUp, CheckCircle, XCircle, ChevronLeft, ChevronRight } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { getRun, getTaxonomyElement } from '@/data'
import { formatRunDate, labelColor } from '@/lib/utils'
import type { Transcript } from '@/types'

export function TranscriptViewer() {
  const { runId, elementId, trialIndex } = useParams<{
    runId: string
    elementId: string
    trialIndex: string
  }>()
  const navigate = useNavigate()
  const [reasoningOpen, setReasoningOpen] = useState(true)

  const trialIdx = parseInt(trialIndex ?? '0', 10)
  const run = runId ? getRun(runId) : undefined
  const element = elementId ? getTaxonomyElement(elementId) : undefined

  const transcript: Transcript | undefined = run?.transcripts.find(
    t => t.element_id === elementId && t.trial_index === trialIdx
  )

  const totalTrials = run
    ? run.transcripts.filter(t => t.element_id === elementId).length
    : 0

  useEffect(() => { window.scrollTo(0, 0) }, [runId, elementId, trialIndex])

  if (!run || !element || !transcript) {
    return <div className="p-6 text-zinc-500">Transcript not found.</div>
  }

  const grade = transcript.model_grade
  const codeGrade = transcript.code_grade
  const overallScore = grade?.overall_score ?? codeGrade?.overall_score ?? 0
  const passed = grade?.passed ?? codeGrade?.passed ?? false

  function navigateTrial(delta: number) {
    navigate(`/transcripts/${runId}/${elementId}/${trialIdx + delta}`)
  }

  return (
    <div className="max-w-5xl mx-auto px-6 pb-24">
      {/* Header */}
      <div className="sticky top-14 z-40 bg-zinc-950/95 backdrop-blur border-b border-zinc-800 -mx-6 px-6 py-3 mb-6">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex-1 min-w-0">
            <div className="text-xs text-zinc-500 mb-0.5">
              {run.summary.target_model} · {formatRunDate(run.summary.run_id)}
            </div>
            <div className="text-sm font-semibold text-white truncate">
              {element.name}
              <span className="text-zinc-500 font-normal ml-2">
                Trial {trialIdx + 1} of {totalTrials}
              </span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-lg font-mono font-bold text-white">{overallScore.toFixed(2)}</span>
            <Badge variant={passed ? 'pass' : 'fail'}>{passed ? 'Pass' : 'Fail'}</Badge>
            <span className="text-xs text-zinc-500">{transcript.timestamp}</span>
          </div>
        </div>
      </div>

      {/* Response */}
      <div className="mb-6">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-zinc-500 mb-3">Model Response</h3>
        <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-5 overflow-auto max-h-[60vh]">
          <div className="prose prose-invert prose-sm max-w-none">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {transcript.response}
            </ReactMarkdown>
          </div>
        </div>
      </div>

      {/* Model Grader */}
      {grade && (
        <div className="mb-6">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-zinc-500 mb-3">
            Model Grader — {grade.overall_score.toFixed(2)}
          </h3>
          {grade.error && (
            <div className="text-xs text-red-400 mb-2">Error: {grade.error}</div>
          )}
          <div className="overflow-x-auto rounded-lg border border-zinc-800">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-zinc-800 bg-zinc-900">
                  <th className="px-4 py-2 text-left text-zinc-400 font-medium">Dimension</th>
                  <th className="px-4 py-2 text-right text-zinc-400 font-medium">Score</th>
                  <th className="px-4 py-2 text-left text-zinc-400 font-medium">Label</th>
                  <th className="px-4 py-2 text-left text-zinc-400 font-medium">Reasoning</th>
                </tr>
              </thead>
              <tbody>
                {grade.dimension_scores.map(dim => (
                  <tr key={dim.dimension} className="border-b border-zinc-800/30">
                    <td className="px-4 py-2 text-zinc-300 capitalize">{dim.dimension.replace(/_/g, ' ')}</td>
                    <td className="px-4 py-2 text-right font-mono text-zinc-300">{dim.score.toFixed(2)}</td>
                    <td className={`px-4 py-2 font-medium capitalize ${labelColor(dim.label)}`}>{dim.label}</td>
                    <td className="px-4 py-2 text-zinc-400 text-xs max-w-md">{dim.reasoning}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Code Grader */}
      {codeGrade && (
        <div className="mb-6">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-zinc-500 mb-3">
            Code Grader — {codeGrade.overall_score.toFixed(2)}
          </h3>
          <div className="rounded-lg border border-zinc-800 divide-y divide-zinc-800/50">
            {codeGrade.checks.map(check => (
              <div key={check.name} className="flex items-center gap-3 px-4 py-2">
                {check.passed
                  ? <CheckCircle className="h-4 w-4 text-green-400 shrink-0" />
                  : <XCircle className="h-4 w-4 text-red-400 shrink-0" />
                }
                <span className="text-sm text-zinc-300">{check.name}</span>
                <span className="text-xs text-zinc-500">{check.message}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Grader Reasoning */}
      {grade?.grader_reasoning && (
        <div className="mb-6">
          <button
            onClick={() => setReasoningOpen(o => !o)}
            className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-zinc-500 hover:text-zinc-300 transition-colors mb-2"
          >
            {reasoningOpen ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
            Grader Reasoning
          </button>
          {reasoningOpen && (
            <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-4 text-sm text-zinc-300 leading-relaxed">
              {grade.grader_reasoning}
            </div>
          )}
        </div>
      )}

      {/* Token usage footer */}
      {(transcript.usage?.input_tokens !== undefined || transcript.usage?.output_tokens !== undefined) && (
        <div className="text-xs text-zinc-600 mb-6">
          Tokens: {transcript.usage.input_tokens ?? '?'} in / {transcript.usage.output_tokens ?? '?'} out
        </div>
      )}

      {/* Prev / Next navigation */}
      <div className="fixed bottom-0 left-0 right-0 z-50 flex justify-between px-6 py-4 bg-zinc-950/95 border-t border-zinc-800">
        <Button
          variant="outline"
          size="sm"
          disabled={trialIdx <= 0}
          onClick={() => navigateTrial(-1)}
          className="border-zinc-700 text-zinc-300"
        >
          <ChevronLeft className="h-4 w-4 mr-1" />
          Previous Trial
        </Button>
        <Button
          variant="outline"
          size="sm"
          disabled={trialIdx >= totalTrials - 1}
          onClick={() => navigateTrial(1)}
          className="border-zinc-700 text-zinc-300"
        >
          Next Trial
          <ChevronRight className="h-4 w-4 ml-1" />
        </Button>
      </div>
    </div>
  )
}
