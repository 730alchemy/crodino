// ── Taxonomy ──────────────────────────────────────────────────────────────────

export interface TaxonomyCategory {
  id: string
  name: string
  description: string
}

export interface TaxonomyElement {
  id: string
  name: string
  category: string
  definition: string
  why_it_matters: string
  subcategory: string | null
}

export interface Taxonomy {
  categories: TaxonomyCategory[]
  elements: TaxonomyElement[]
}

// ── Tasks ─────────────────────────────────────────────────────────────────────

export interface RubricDimension {
  name: string
  weight: number
  criteria: string
  scores: {
    excellent: string
    good: string
    partial: string
    poor: string
  }
}

export interface Task {
  element_id: string
  element_name: string
  category: string
  prompt: string
  success_criteria: string[]
  rubric: RubricDimension[]
  reference_solution: string
  grader_type: string
  tags: string[]
}

// ── Runs ──────────────────────────────────────────────────────────────────────

export interface TaskResult {
  pass_rate: number
  mean_score: number
  std_score: number
  pass_at_k: Record<string, number>
  pass_hat_k: Record<string, number>
  scores: number[]
}

export interface RunSummary {
  run_id: string
  target_model: string
  n_trials: number
  n_tasks: number
  overall_pass_rate: number
  pass_at_k: Record<string, number>
  pass_hat_k: Record<string, number>
  task_results: Record<string, TaskResult>
}

export interface DimensionScore {
  dimension: string
  score: number
  label: string
  reasoning: string
}

export interface ModelGrade {
  overall_score: number
  passed: boolean
  grader_reasoning: string
  dimension_scores: DimensionScore[]
  error: string | null
}

export interface CodeCheck {
  name: string
  passed: boolean
  score: number
  message: string
}

export interface CodeGrade {
  overall_score: number
  passed: boolean
  checks: CodeCheck[]
}

export interface Transcript {
  element_id: string
  trial_index: number
  timestamp: string
  prompt: string
  response: string
  usage: {
    input_tokens?: number
    output_tokens?: number
  }
  model_grade?: ModelGrade
  code_grade?: CodeGrade
}

export interface Run {
  summary: RunSummary
  transcripts: Transcript[]
}
