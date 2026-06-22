// Payload types mirroring server.py channel/GET shapes. Expanded as screens are ported.

export interface Phase {
  id?: number
  status: string
}

export interface Health {
  url?: string
  ok?: boolean
  ms?: number | null
  checked?: string
  status?: number | null
}

export interface Project {
  id: string
  name: string
  dir_label?: string
  cover?: string | null
  phases?: Phase[]
  done?: number
  current_phase?: number
  updated?: string
  working?: boolean
  missing?: boolean
  error?: boolean
  archived?: boolean
  health?: Health | null
}

export interface Pending {
  id?: string
  name: string
  brief?: string
}

export interface ProjectsPayload {
  version: string
  projects: Project[]
  pending: Pending[]
}

export interface SystemPayload {
  current: string
  latest: string | null
  update_available: boolean
  repo?: string
  git?: boolean
}

// ── state channel ──
export interface Step {
  id: string
  title: string
  status: string
}
export interface Artifact {
  file: string
  title: string
  type: string
  ts?: string | number
}
export interface StatePhase {
  id: number
  name: string
  status: string
  steps: Step[]
  artifacts: Artifact[]
}
export interface LogRow {
  ts: string
  msg: string
}
export interface StateChannel {
  product: string
  phases: StatePhase[]
  current_phase: number
  log: LogRow[]
}

// ── choices channel ──
export interface Choice {
  id: string
  question: string
  options?: string[]
  stage?: number
  answer?: string | null
}
export interface ChoicesPayload {
  choices: Choice[]
}

// ── inbox channel ──
export interface InboxMessage {
  from?: string
  text: string
  ts: string
  type?: string
  liked?: unknown[]
  comments?: unknown[]
  regions?: unknown[]
}
export interface InboxPayload {
  messages: InboxMessage[]
}

// ── health channel ──
export interface HealthPayload {
  url?: string
  ok?: boolean
  ms?: number | null
  checked?: string
}

// ── agent-log:* channels ──
export interface AgentLogLine {
  text?: string
  kind?: string
}
export interface AgentLogPayload {
  lines: AgentLogLine[]
  running: boolean
  waiting: boolean
}

// ── brief channel ──
export interface BriefQuestion {
  q: string
  options?: string[]
}
export interface BriefSummary {
  goal?: string
  users?: string
  need?: string
  scope?: string
}
export interface BriefPayload {
  description?: string
  request?: { kind?: string } | null
  questions?: BriefQuestion[]
  confirmed?: boolean
  summary?: BriefSummary
  ready?: boolean
}

// ── wizard channel ──
export interface WizardPayload {
  brief?: string
  platforms?: string[]
  primary?: string | null
  priority?: string[]
  stylePrefs?: string[]
}

// ── explore channel ──
export interface ExploreRef {
  id: string
  file: string
  title?: string
  source?: string
}
export interface ExploreHero {
  id: string
  file: string
  style?: string
}
export type ExploreRequest = ({ kind?: string } & Record<string, unknown>) | null
export interface ExplorePayload {
  stylePrefs?: string[]
  request?: ExploreRequest
  refs?: ExploreRef[]
  selectedRefs?: string[]
  styleSummary?: string
  heroes?: ExploreHero[]
  selectedHero?: string
  heroGenFailed?: boolean
  heroGenLog?: unknown[]
}

// ── pages channel ──
export interface PageVersion {
  file?: string
  platform?: string | null
}
export interface Page {
  id: string
  name: string
  group?: string
  status?: string
  versions?: PageVersion[]
}
export interface PagesPayload {
  pages: Page[]
}

// ── canvas (request/response, per-stage layout, user-owned — not a channel) ──
export interface CanvasView {
  x: number
  y: number
  z: number
}
export interface CanvasCell {
  view: CanvasView | null
  items: Record<string, { x: number; y: number }>
  notes: unknown[]
}
export interface HeroGenLogEntry {
  mode?: string
  ts?: string
  refs?: unknown[]
  results?: string[]
  prompt?: string
}

// ── deploy-creds (request/response, not a channel) ──
export interface DeployCredKey {
  key: string
  masked: string
}
export interface DeployCredsPayload {
  keys: DeployCredKey[]
}
