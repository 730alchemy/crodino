import * as fs from 'fs'
import * as path from 'path'
import { fileURLToPath } from 'url'
import * as yaml from 'js-yaml'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

const ROOT = path.resolve(__dirname, '../..')
const DATA_DIR = path.resolve(__dirname, '../src/data')

function readYaml(filePath: string): unknown {
  return yaml.load(fs.readFileSync(filePath, 'utf-8'))
}

// ── Taxonomy ─────────────────────────────────────────────────────────────────

function prepareTaxonomy() {
  const taxonomyPath = path.join(ROOT, 'taxonomy/cognitive_elements.yaml')
  const raw = readYaml(taxonomyPath) as {
    categories: Array<{ id: string; name: string; description: string }>
    elements: Array<{
      id: string
      name: string
      category: string
      definition: string
      why_it_matters: string
      subcategory: string | null
    }>
  }

  const out = {
    categories: raw.categories,
    elements: raw.elements,
  }

  fs.writeFileSync(path.join(DATA_DIR, 'taxonomy.json'), JSON.stringify(out, null, 2))
  console.log(`taxonomy.json: ${raw.categories.length} categories, ${raw.elements.length} elements`)
}

// ── Tasks ─────────────────────────────────────────────────────────────────────

function prepareTasks() {
  const tasksRoot = path.join(ROOT, 'tasks')
  const tasks: unknown[] = []

  if (!fs.existsSync(tasksRoot)) {
    fs.writeFileSync(path.join(DATA_DIR, 'tasks.json'), JSON.stringify([], null, 2))
    console.log('tasks.json: 0 tasks (no tasks/ directory)')
    return
  }

  // Walk subdirs one level deep
  for (const subdir of fs.readdirSync(tasksRoot)) {
    const subdirPath = path.join(tasksRoot, subdir)
    if (!fs.statSync(subdirPath).isDirectory()) continue

    for (const file of fs.readdirSync(subdirPath)) {
      if (!file.endsWith('.yaml') && !file.endsWith('.yml')) continue

      const raw = readYaml(path.join(subdirPath, file)) as {
        element_id: string
        element_name: string
        category: string
        prompt: string
        success_criteria: string[]
        rubric: Record<string, {
          weight: number
          criteria: string
          scores: Record<string, string>
        }>
        reference_solution: string
        grader_type: string
        tags: string[]
      }

      // Transform rubric into typed array
      const rubric = Object.entries(raw.rubric || {}).map(([name, dim]) => ({
        name,
        weight: dim.weight,
        criteria: dim.criteria,
        scores: dim.scores,
      }))

      tasks.push({
        element_id: raw.element_id,
        element_name: raw.element_name,
        category: raw.category,
        prompt: raw.prompt,
        success_criteria: raw.success_criteria || [],
        rubric,
        reference_solution: raw.reference_solution || '',
        grader_type: raw.grader_type || 'model',
        tags: raw.tags || [],
      })
    }
  }

  fs.writeFileSync(path.join(DATA_DIR, 'tasks.json'), JSON.stringify(tasks, null, 2))
  console.log(`tasks.json: ${tasks.length} tasks`)
}

// ── Runs ──────────────────────────────────────────────────────────────────────

function prepareRuns() {
  const resultsDir = path.join(ROOT, 'results')
  const runs: unknown[] = []

  if (!fs.existsSync(resultsDir)) {
    fs.writeFileSync(path.join(DATA_DIR, 'runs.json'), JSON.stringify([], null, 2))
    console.log('runs.json: 0 runs (no results/ directory)')
    return
  }

  const files = fs.readdirSync(resultsDir)
  const summaryFiles = files.filter(f => f.startsWith('summary_') && f.endsWith('.json'))

  for (const summaryFile of summaryFiles) {
    const runId = summaryFile.replace('summary_', '').replace('.json', '')
    const transcriptsFile = `transcripts_${runId}.json`

    const summaryPath = path.join(resultsDir, summaryFile)
    const transcriptsPath = path.join(resultsDir, transcriptsFile)

    if (!fs.existsSync(summaryPath)) continue

    const summary = JSON.parse(fs.readFileSync(summaryPath, 'utf-8'))

    let transcripts: unknown[] = []
    if (fs.existsSync(transcriptsPath)) {
      transcripts = JSON.parse(fs.readFileSync(transcriptsPath, 'utf-8'))
    }

    runs.push({ summary, transcripts })
  }

  // Sort newest first (run_id is a timestamp string like 20260309_220106)
  runs.sort((a: unknown, b: unknown) => {
    const aId = (a as { summary: { run_id: string } }).summary.run_id
    const bId = (b as { summary: { run_id: string } }).summary.run_id
    return bId.localeCompare(aId)
  })

  fs.writeFileSync(path.join(DATA_DIR, 'runs.json'), JSON.stringify(runs, null, 2))
  console.log(`runs.json: ${runs.length} runs`)
}

// ── Main ──────────────────────────────────────────────────────────────────────

fs.mkdirSync(DATA_DIR, { recursive: true })
prepareTaxonomy()
prepareTasks()
prepareRuns()
console.log('Data preparation complete.')
