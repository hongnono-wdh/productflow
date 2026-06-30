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
  version?: number
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
export interface BriefVersion {
  ts?: string
  summary?: BriefSummary
  questions?: BriefQuestion[]
  description?: string
}
export interface BriefPayload {
  description?: string
  request?: { kind?: string } | null
  questions?: BriefQuestion[]
  confirmed?: boolean
  summary?: BriefSummary
  ready?: boolean
  history?: BriefVersion[]
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
  desc?: string
}
export interface SearchPlan {
  keywords?: string[]
  basis?: string
  ts?: string
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
  searchPlan?: SearchPlan | null
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
  activeVersion?: string
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
export interface FlowEdge {
  from: string
  to: string
  label?: string
  b1?: number // 三次贝塞尔控制点1 在基线 1/3 处「垂直于基线」的偏移量（弯曲量；0=直，undefined=默认弧）
  b2?: number // 控制点2 在基线 2/3 处的垂直偏移量
}
export interface CanvasCell {
  view: CanvasView | null
  items: Record<string, { x: number; y: number }>
  notes: unknown[]
  flow?: { edges: FlowEdge[]; entry?: string | null } // ④ 页面流程图：边 + 入口页（全局，平台无关）
  flowItems?: Record<string, { x: number; y: number }> // ④ 流程图节点坐标（与平铺 items 分开）
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
