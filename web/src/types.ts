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
  pageId?: string // ⑥ 实现截图关联的 ④ 页面 id（pg-xxx），用于「设计图↔实现图」按页配对
  platform?: string // ⑥ 实现截图对应平台（PC/H5/APP）
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
  implSkip?: string // ⑥ 显式声明本阶段不实现的原因（有值 → 覆盖校验豁免、占位显示「本阶段不实现」而非「待补」）
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

// ── backend-flow（⑥ 后端流程图，backend-flow.json；薄关系层，直接 GET 非 channel）──
export interface BFNode {
  id: string
  type: 'module' | 'interface' | 'table'
  module?: string
  status?: string
  name?: string // 中文显示名（图上主显中文、英文 id 灰字副显）
  fields?: string[] // 数据表字段（点表查看用；仍以 ⑤ er/schema 为准，此处只存摘要）
  proc?: boolean // agent 正在处理这个节点的改动（操作台显示「处理中」脉冲）
  stub?: string | null // 占位·真实对接未实现（dev/mock 占位、真实第三方对接还是 TODO）；字符串为占位说明
}
export interface BFEdge {
  from: string
  to: string
  type: string
  label?: string
}
export interface BackendFlow {
  version: number
  nodes: BFNode[]
  edges: BFEdge[]
  pageLinks: { page: string; module: string }[]
  entry: string | null
  layout: Record<string, unknown>
}

// ── deploy-creds (request/response, not a channel) ──
export interface DeployCredKey {
  key: string
  masked: string
}
export interface DeployCredsPayload {
  keys: DeployCredKey[]
}
