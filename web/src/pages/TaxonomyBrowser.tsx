import { useState } from 'react'
import { Link } from 'react-router-dom'
import { ChevronDown, ChevronRight } from 'lucide-react'
import { taxonomy } from '@/data'
import type { TaxonomyElement } from '@/types'

export function TaxonomyBrowser() {
  const [expanded, setExpanded] = useState<Set<string>>(new Set(taxonomy.categories.map(c => c.id)))
  const [selected, setSelected] = useState<TaxonomyElement | null>(null)

  function toggleCategory(id: string) {
    setExpanded(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  return (
    <div className="flex h-[calc(100vh-56px)] overflow-hidden">
      {/* Left sidebar */}
      <div className="w-72 shrink-0 border-r border-zinc-800 overflow-y-auto bg-zinc-950">
        <div className="p-4">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-zinc-500 mb-3">
            Taxonomy
          </h2>
          {taxonomy.categories.map(cat => {
            const elements = taxonomy.elements.filter(e => e.category === cat.id)
            const isExpanded = expanded.has(cat.id)
            return (
              <div key={cat.id} className="mb-2">
                <button
                  onClick={() => toggleCategory(cat.id)}
                  className="flex items-center justify-between w-full px-2 py-2 rounded-md text-sm font-medium text-zinc-300 hover:bg-zinc-800 transition-colors"
                >
                  <span>{cat.name}</span>
                  <span className="flex items-center gap-1 text-xs text-zinc-500">
                    {elements.length}
                    {isExpanded ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
                  </span>
                </button>
                {isExpanded && (
                  <div className="ml-3 mt-1 space-y-0.5">
                    {elements.map(el => (
                      <button
                        key={el.id}
                        onClick={() => setSelected(el)}
                        className={`w-full text-left px-2 py-1.5 rounded text-sm transition-colors ${
                          selected?.id === el.id
                            ? 'bg-zinc-700 text-white'
                            : 'text-zinc-400 hover:text-white hover:bg-zinc-800/50'
                        }`}
                      >
                        {el.name}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </div>

      {/* Right detail panel */}
      <div className="flex-1 overflow-y-auto">
        {selected ? (
          <div className="p-6 max-w-3xl">
            {/* Breadcrumb */}
            <div className="text-xs text-zinc-500 mb-4">
              {taxonomy.categories.find(c => c.id === selected.category)?.name}
              {selected.subcategory && ` > ${selected.subcategory.replace(/_/g, ' ')}`}
              {' > '}{selected.name}
            </div>

            <h2 className="text-2xl font-bold text-white mb-1">{selected.name}</h2>

            <div className="flex gap-2 mb-6">
              <span className="inline-flex items-center rounded-full bg-zinc-800 px-2.5 py-0.5 text-xs font-medium text-zinc-400">
                {taxonomy.categories.find(c => c.id === selected.category)?.name}
              </span>
              {selected.subcategory && (
                <span className="inline-flex items-center rounded-full bg-zinc-800 px-2.5 py-0.5 text-xs font-medium text-zinc-400">
                  {selected.subcategory.replace(/_/g, ' ')}
                </span>
              )}
            </div>

            <div className="space-y-5">
              <div>
                <h3 className="text-xs font-semibold uppercase tracking-wider text-zinc-500 mb-2">Definition</h3>
                <p className="text-zinc-300 text-sm leading-relaxed">{selected.definition}</p>
              </div>
              <div>
                <h3 className="text-xs font-semibold uppercase tracking-wider text-zinc-500 mb-2">Why It Matters</h3>
                <p className="text-zinc-300 text-sm leading-relaxed">{selected.why_it_matters}</p>
              </div>
            </div>

            <div className="flex gap-3 mt-8">
              <Link
                to={`/tasks/${selected.id}`}
                className="inline-flex items-center rounded-md bg-zinc-800 hover:bg-zinc-700 px-4 py-2 text-sm font-medium text-white transition-colors"
              >
                View Task
              </Link>
              <Link
                to={`/tasks/${selected.id}?tab=results`}
                className="inline-flex items-center rounded-md border border-zinc-700 hover:bg-zinc-800 px-4 py-2 text-sm font-medium text-zinc-300 transition-colors"
              >
                View Results
              </Link>
            </div>
          </div>
        ) : (
          <div className="flex h-full items-center justify-center text-zinc-600 text-sm">
            Select an element from the sidebar
          </div>
        )}
      </div>
    </div>
  )
}
