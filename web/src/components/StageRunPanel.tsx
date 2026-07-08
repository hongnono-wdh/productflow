// ⑤⑥⑦ panel: 让 Agent 做本阶段 (+⑥ iOS/平台预览按钮, +⑦ deploy creds + 分发包文案).
// running/waiting come from the agent-log:stage-N channel (server runtime flags), not the log tail.
import { useState } from 'react'
import { useChannel, toast } from '../store'
import { post } from '../lib'
import { IcSpark } from '../icons'
import { DeployCredsCard } from './DeployCredsCard'
import { PreviewSection } from './PreviewSection'
import { ModuleProgressView } from './ModuleProgressView'
import { TestProgressView } from './TestProgressView'
import { BackendFlowView } from './BackendFlowView'
import { ProductKeysCard } from './ProductKeysCard'
import type { AgentLogPayload, WizardPayload } from '../types'

const NAMES: Record<number, string> = { 5: '功能与数据设计', 6: '前端实现', 7: '后端实现', 8: '测试', 9: '部署上线' }
const HINTS: Record<number, string> = {
  5: '功能模块清单 → ER 图 → 表结构 DDL → API 契约 → 选开发模板。',
  6: '按模板脚手架 → 前端页面 / 交互实现 → 本地预览 + 视觉还原（严格还原 ④ 设计）。',
  7: '后端接口 + 数据实现 → 单元测试 → 接口文档。',
  8: '集成测试 + E2E 端到端旅程 + 回归 + 契约 + 测试报告门禁（真实拼装后产物的完整验证）。',
  9: '选部署目标 → 部署 → 线上冒烟 → 交付报告。',
}
const isMac = navigator.platform.indexOf('Mac') >= 0 // 独立于 wizard.primary 的 OS 嗅探（critic #4）

export function StageRunPanel({ phase, phaseStatus }: { phase: number; phaseStatus: string }) {
  const log = useChannel<AgentLogPayload>('agent-log:stage-' + phase)
  const wizard = useChannel<WizardPayload>('wizard')
  const [instr, setInstr] = useState('')
  const [justClicked, setJustClicked] = useState(false)

  const lines = log?.lines || []
  const last = lines.length ? lines[lines.length - 1] : null
  const running = !!log?.running || justClicked
  const waiting = !!log?.waiting
  const done = phaseStatus === 'done'
  // done 后一律不报警（CLI 接手/续跑完成会标 done → 红条自动消）。
  // 超时(kind=timeout)是「自动续跑到上限暂停」，可继续，不是失败；只有真失败/连续无进展(kind=error)才红条。
  const failed = !running && !done && !!last && last.kind === 'error'
  const paused = !running && !done && !!last && last.kind === 'timeout'
  const prim = wizard?.primary ?? null

  const guard = (act: () => void) => {
    if (running) {
      toast('本阶段 Agent 已在进行中')
      return
    }
    setJustClicked(true)
    setTimeout(() => setJustClicked(false), 2500)
    act()
  }
  const runStage = () =>
    guard(() => {
      post('/api/run-stage', { phase, instruction: instr.trim() })
        .then((r) => {
          if (r.status === 409) toast('本阶段 Agent 已在进行中（服务端拦截了重复触发）')
        })
        .catch(() => {})
      toast(instr.trim() ? '已让 Agent 带要求重做本阶段' : '已让 Agent 做本阶段（进度见下方步骤/产物/日志）')
    })
  const runPreview = () =>
    guard(() => {
      post('/api/run-action', { phase, action: 'preview' })
        .then((r) => {
          if (r.status === 409) toast('本阶段 Agent 已在进行中（服务端拦截了重复触发）')
        })
        .catch(() => {})
      toast('已让 Agent 构建并起预览（进度见下方进展日志；起好后会在屏幕/模拟器看到）')
    })
  const revealCode = () => {
    post('/api/reveal', {})
      .then((r) => r.json())
      .then((j) => toast(j.ok ? '已在文件管理器打开项目代码目录' : '打开失败：' + (j.error || '未知')))
      .catch(() => toast('打开失败'))
  }

  let mainLabel = done ? '重做本阶段' : '让 Agent 做本阶段'
  if (phase === 9 && !done) {
    mainLabel = prim === 'APP' ? '构建并产出上线分发包' : prim === 'PC' ? '构建并部署上线' : prim === 'H5' ? '部署上线' : '让 Agent 做本阶段'
  }
  const previewLabel = prim === 'APP' ? '📱 构建并在模拟器预览' : prim === 'PC' ? '🖥 本地运行预览' : prim === 'H5' ? '🌐 本地预览' : '▶ 构建并预览'
  const disStyle = running ? ({ background: 'var(--dash)', cursor: 'not-allowed' } as const) : undefined

  return (
    <>
      {phase === 9 && <DeployCredsCard primary={prim} />}
      {phase === 6 && <PreviewSection />}
      {phase === 7 && <ModuleProgressView running={running} />}
      {phase === 8 && <TestProgressView running={running} />}
      <div className="card">
        <h2>
          {NAMES[phase]} <span className="hint">交给 Agent 自动完成</span>
        </h2>
        <div className="wz-hint2" style={{ margin: '0 0 12px' }}>
          {HINTS[phase]}
          <br />
          遇到要你拍板的（如选模板、部署目标），Agent 会在页面顶部弹出选项让你点选。产物出现在下方「产物 / 进展日志」。
        </div>
        {done && !running && (
          <input className="wz-input" style={{ maxWidth: 'none', marginBottom: 10 }} value={instr} onChange={(e) => setInstr(e.target.value)} placeholder="重做要求（可选）：写一句你想调整的方向" />
        )}
        <button className="btn" disabled={running} style={disStyle} onClick={runStage}>
          <IcSpark />
          {mainLabel}
        </button>
        {(phase === 6 || phase === 7) && (
          <button className="btn ghost" disabled={running} style={disStyle} onClick={runPreview} title="让 Agent 把当前已实现的产品构建起来、跑到你屏幕/模拟器上实时预览（不重做整个阶段）">
            {previewLabel}
          </button>
        )}
        <button className="btn ghost" onClick={revealCode} title="在系统文件管理器打开项目代码目录">
          📂 {isMac ? '在访达打开代码' : '打开代码目录'}
        </button>
        {running && (
          <div className="wz-aibox" style={{ marginTop: 14, ...(waiting ? { borderColor: '#d8c98a', background: '#fcf8e8', color: '#7a6a1f' } : {}) }}>
            {waiting ? '⏳ Agent 正等你回答上面弹出的选项（回答后会自动继续，别关页面）' : '✦ Agent 进行中…'}
            {last?.text && (
              <>
                <br />
                <span style={{ color: 'var(--dim)', fontSize: 12 }}>{last.text}</span>
              </>
            )}
            <br />
            <span style={{ color: 'var(--dim)', fontSize: 12 }}>进度见下方步骤 / 产物 / 进展日志</span>
          </div>
        )}
        {paused && (
          <div className="wz-aibox" style={{ marginTop: 14, borderColor: '#d8c98a', background: '#fcf8e8', color: '#7a6a1f' }}>
            ⏸ 本阶段已自动续跑多轮仍没全部做完，先暂停了——已完成的步骤都保留，点下面接着做完。
            <br />
            <button className="btn" style={{ marginTop: 10 }} disabled={running} onClick={runStage}>
              <IcSpark />
              继续做完本阶段
            </button>
          </div>
        )}
        {failed && (
          <div className="wz-aibox" style={{ marginTop: 14, borderColor: '#e0b4b4', background: '#fdf4f4', color: '#b3403a' }}>
            ❌ Agent 没能继续（claude 未登录，或连续多轮没有新进展）。点上面按钮重试，或在💬留言补充方向，或在 CLI 里接手本阶段。
          </div>
        )}
      </div>
      {phase === 5 && <BackendFlowView running={running} />}
      {phase === 7 && <ProductKeysCard />}
    </>
  )
}
