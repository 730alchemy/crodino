import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { NavBar } from '@/components/NavBar'
import { Dashboard } from '@/pages/Dashboard'
import { RunsList } from '@/pages/RunsList'
import { RunDetail } from '@/pages/RunDetail'
import { RunComparison } from '@/pages/RunComparison'
import { TaxonomyBrowser } from '@/pages/TaxonomyBrowser'
import { TaskDetail } from '@/pages/TaskDetail'
import { TranscriptViewer } from '@/pages/TranscriptViewer'

export default function App() {
  return (
    <BrowserRouter>
      <NavBar />
      <main className="pt-14 min-h-screen bg-zinc-950 text-zinc-100">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/runs" element={<RunsList />} />
          <Route path="/runs/compare" element={<RunComparison />} />
          <Route path="/runs/:runId" element={<RunDetail />} />
          <Route path="/taxonomy" element={<TaxonomyBrowser />} />
          <Route path="/tasks/:elementId" element={<TaskDetail />} />
          <Route path="/transcripts/:runId/:elementId/:trialIndex" element={<TranscriptViewer />} />
        </Routes>
      </main>
    </BrowserRouter>
  )
}
