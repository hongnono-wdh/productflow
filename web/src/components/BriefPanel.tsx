// P1 panel: 产品需求 (confirm-lag state machine) + 市场调研.
// Uses a ref+force model to faithfully reproduce the original imperative reconciliation
// (generating/failed derived from server request-slot presence; local edits never clobbered).
import { useEffect, useReducer, useRef } from 'react'
import { useChannel, toast } from '../store'
import { post } from '../lib'
import { IcSpark } from '../icons'
import type { BriefPayload, BriefQuestion, BriefSummary, BriefVersion, AgentLogPayload, StatePhase } from '../types'

interface PB {
  description: string
  summary: BriefSummary
  ready: boolean
  generating: boolean
  failed: boolean
  request: { kind?: string } | null
  clarify: string
  questions: BriefQuestion[]
  answers: Record<number, string>
  confirmed: boolean
  _serverGen: boolean
  _inited: boolean
  history: BriefVersion[]
  _histLen: number
  openVers: Record<number, boolean>
}

function fold(pb: PB): string {
  const picked = pb.questions.map((q, i) => (pb.answers[i] ? { q: q.q, a: pb.answers[i] } : null)).filter(Boolean) as { q: string; a: string }[]
  let acc = (pb.description || '').trim()
  const clar = (pb.clarify || '').trim()
  if (picked.length || clar) {
    if (acc && !/^用户原始提问[：:]/.test(acc)) acc = '用户原始提问：' + acc
    let qn = (acc.match(/问题澄清\s*\d+/g) || []).length
    let un = (acc.match(/用户澄清\s*\d+/g) || []).length
    const lines: string[] = []
    for (const p of picked) lines.push(`问题澄清${++qn}：${p.q} 用户选择：${p.a}`)
    if (clar) lines.push(`用户澄清${++un}：${clar}`)
    acc = acc + '\n' + lines.join('\n')
  }
  pb.description = acc
  pb.answers = {}
  pb.clarify = ''
  return acc
}

export function BriefPanel({ phase }: { phase: StatePhase }) {
  const brief = useChannel<BriefPayload>('brief')
  const research = useChannel<AgentLogPayload>('agent-log:research')
  const [, force] = useReducer((x: number) => x + 1, 0)
  const pbRef = useRef<PB>({
    description: '', summary: { goal: '', users: '', need: '', scope: '' }, ready: false, generating: false,
    failed: false, request: {}, clarify: '', questions: [], answers: {}, confirmed: false, _serverGen: false, _inited: false,
    history: [], _histLen: -1, openVers: {},
  })
  const researchInstrRef = useRef('')
  const focusedRef = useRef(false)

  // reconcile incoming brief channel into pb (mirrors pollBrief)
  useEffect(() => {
    if (!brief) return
    const pb = pbRef.current
    if (!focusedRef.current && !pb.description) pb.description = brief.description || ''
    pb.summary = brief.summary || pb.summary
    pb.ready = !!brief.ready
    pb.request = brief.request || {}
    if (pb.confirmed && !brief.confirmed) {
      /* keep local confirmed until server catches up */
    } else {
      if (Array.isArray(brief.questions)) pb.questions = brief.questions
      pb.confirmed = !!brief.confirmed
    }
    const serverGen = !!(brief.request && brief.request.kind === 'gen-summary')
    if (pb._serverGen && !serverGen && !brief.ready) pb.failed = true
    if (serverGen) pb.failed = false
    pb._serverGen = serverGen
    if (!serverGen) pb.generating = false
    // 版本历史：history 变长 = 新一版落地 → 兜底强制刷新摘要 + 恢复按钮（保证每轮都更新、按钮不卡）
    const hist = Array.isArray(brief.history) ? brief.history : pb.history
    const prevLen = pb._histLen
    pb.history = hist
    pb._histLen = hist.length
    if (prevLen >= 0 && hist.length > prevLen) {
      pb.ready = true
      pb.generating = false
      pb.failed = false
      pb.request = {}
    }
    force()
  }, [brief])

  const pb = pbRef.current
  const running = pb.generating || pb.request?.kind === 'gen-summary'

  // 安全兜底：生成态卡住超过 ~3.5 分钟（后端 180s + 余量）仍无结果 → 解卡、恢复按钮、提示可重试
  useEffect(() => {
    if (!running) return
    const t = setTimeout(() => {
      const p = pbRef.current
      if (p.generating || p.request?.kind === 'gen-summary') {
        p.generating = false
        p.request = {}
        p.failed = true
        force()
      }
    }, 215000)
    return () => clearTimeout(t)
  }, [running])

  const genSummary = () => {
    const acc = fold(pb)
    if (!acc.trim()) {
      toast('先描述一下你的产品')
      return
    }
    pb.confirmed = false
    pb.questions = []
    pb.ready = false
    pb.generating = true
    pb.failed = false
    force()
    post('/api/brief', { description: acc, confirmed: false, request: { kind: 'gen-summary', description: acc } })
    toast('已交给本地 Agent 生成摘要')
  }
  const confirmBrief = () => {
    const acc = fold(pb)
    if (!acc.trim()) {
      toast('先描述一下你的产品')
      return
    }
    pb.questions = []
    pb.confirmed = true
    force()
    post('/api/brief', { description: acc, questions: [], confirmed: true })
    toast('已确认产品需求，可往下走')
  }

  // research card state (derived from agent-log:research tail, like pollResearch)
  const rlines = research?.lines || []
  const rlast = rlines.length ? rlines[rlines.length - 1] : null
  const rRunning = !!rlast && !['done', 'error'].includes(rlast.kind || '')
  const rFailed = rlast?.kind === 'error'
  const doneSteps = phase.steps.filter((s) => s.id !== 'define-product' && s.status === 'done').length
  const doResearch = () => {
    const instr = researchInstrRef.current.trim()
    researchInstrRef.current = ''
    post('/api/research', { instruction: instr })
    toast(instr ? '已让 Agent 带要求重做市场调研' : '已让 Agent 开始市场调研（进度见下方步骤/产物/日志）')
    force()
  }

  const dis = running ? ({ background: 'var(--dash)', cursor: 'not-allowed' } as const) : undefined
  const rows: [string, string | undefined][] = [
    ['产品目标', pb.summary.goal],
    ['目标用户', pb.summary.users],
    ['核心需求', pb.summary.need],
    ['输出范围', pb.summary.scope],
  ]
  const hasQs = pb.ready && pb.questions.length > 0
  const accHint = /问题澄清|用户澄清/.test(pb.description || '')

  return (
    <>
      <div className="card">
        <h2>
          产品需求 <span className="hint">描述产品 → Agent 生成理解摘要 → 点选/补充后「确认」或「重新生成」</span>
        </h2>
        {accHint && (
          <span style={{ color: 'var(--dim)', fontSize: 11.5 }}>下方已累积你的原始描述 + 历次澄清，可直接编辑，重新生成时整段一起发给 Agent。</span>
        )}
        <textarea
          className="wz-textarea"
          style={{ minHeight: 120 }}
          value={pb.description}
          onFocus={() => (focusedRef.current = true)}
          onBlur={() => (focusedRef.current = false)}
          onChange={(e) => {
            pb.description = e.target.value
            force()
          }}
          placeholder="例如：一个每月寄到家的精品手冲咖啡订阅，帮上班族在家喝到新鲜烘焙。"
        />
        <div style={{ marginTop: 16 }}>
          {pb.ready ? (
            <div>
              {rows.map(([k, v]) => (
                <div className="wz-airow" key={k}>
                  <span className="ak">{k}</span>
                  <span className="av">{v || '—'}</span>
                </div>
              ))}
            </div>
          ) : running ? (
            <div className="wz-aibox">✦ 本地 Agent 正在理解你的产品、生成摘要…完成后自动回填。</div>
          ) : pb.failed ? (
            <div className="wz-aibox" style={{ borderColor: '#e0b4b4', background: '#fdf4f4', color: '#b3403a' }}>
              ❌ 上次生成没成功（可能 claude 未登录 / 超时）。点下面「生成摘要」重试，或在 CLI 里让 agent 直接登记。
            </div>
          ) : (
            <div className="wz-aibox">填好描述点「✦ 生成摘要」，本地 Agent 会生成产品理解摘要回填这里。</div>
          )}
        </div>
        {hasQs && (
          <div style={{ marginTop: 16, border: '1px solid #f0e2c8', borderRadius: 12, padding: '14px 16px', background: '#fdfaf2' }}>
            <div className="wz-label" style={{ fontSize: 13, color: '#9a6a1a' }}>⚠ 还有几点需要你确认（点选即可）</div>
            {pb.questions.map((q, i) => (
              <div style={{ marginTop: 10 }} key={i}>
                <div style={{ fontSize: 12.5, fontWeight: 600 }}>{q.q}</div>
                <div className="wz-tags" style={{ marginTop: 6 }}>
                  {(q.options || []).map((o) => (
                    <span
                      key={o}
                      className={'wz-tag' + (pb.answers[i] === o ? ' on' : '')}
                      onClick={() => {
                        pb.answers[i] = o
                        force()
                      }}
                    >
                      {o}
                    </span>
                  ))}
                </div>
              </div>
            ))}
            <div style={{ marginTop: 12 }}>
              <div className="wz-label" style={{ fontSize: 12, color: 'var(--dim)' }}>都不合适？补充说明：</div>
              <textarea className="wz-textarea" style={{ height: 60, marginTop: 6 }} value={pb.clarify} onChange={(e) => { pb.clarify = e.target.value; force() }} placeholder="例如：其实是给开发者的支付 SDK 接入工具…" />
            </div>
          </div>
        )}
        {pb.ready && !hasQs && (
          <div style={{ marginTop: 16 }}>
            <div className="wz-label" style={{ fontSize: 13 }}>补充 / 修正（可选）</div>
            <textarea className="wz-textarea" style={{ height: 60, marginTop: 6 }} value={pb.clarify} onChange={(e) => { pb.clarify = e.target.value; force() }} placeholder="想调整哪个方向，写一句，点重新生成。" />
          </div>
        )}
        {hasQs ? (
          <div style={{ marginTop: 14, display: 'flex', gap: 10, alignItems: 'center' }}>
            <button className="btn ghost" disabled={running} style={dis} onClick={genSummary}>
              ↻ 重新生成一版
            </button>
            <button className="btn" disabled={running} style={dis} onClick={confirmBrief}>
              ✓ 确认需求
            </button>
            <span className="hint" style={{ fontSize: 11.5, color: 'var(--dim)' }}>选完点「确认」即可定稿，不必再让 AI 跑；想让 AI 据答复refine就点「重新生成」</span>
          </div>
        ) : (
          <>
            <button className="btn" style={{ marginTop: 14, ...(dis || {}) }} disabled={running} onClick={genSummary}>
              {pb.ready ? '↻ 重新生成一版' : '✦ 生成摘要'}
            </button>
            {pb.confirmed && <span className="hint" style={{ marginLeft: 10, color: '#2e7d52' }}>✓ 已确认产品需求</span>}
          </>
        )}
        {pb.history.length > 0 && (
          <div style={{ marginTop: 18, borderTop: '1px dashed var(--line)', paddingTop: 12 }}>
            <div className="wz-label" style={{ fontSize: 12.5, color: 'var(--dim)' }}>历史版本（{pb.history.length}）—— 每次重新生成留一版，可展开对比</div>
            {pb.history.map((v, i) => {
              const open = !!pb.openVers[i]
              const cur = i === pb.history.length - 1
              return (
                <div key={i} style={{ border: '1px solid var(--line)', borderRadius: 8, marginTop: 8, overflow: 'hidden' }}>
                  <div
                    onClick={() => { pb.openVers[i] = !open; force() }}
                    style={{ padding: '9px 12px', cursor: 'pointer', display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 12.5, background: cur ? '#f3f8f4' : '#fafafa' }}
                  >
                    <span style={{ fontWeight: 600 }}>第 {i + 1} 版本{cur ? ' · 当前' : ''}</span>
                    <span style={{ color: 'var(--dim)', fontSize: 11.5 }}>{v.ts || ''} &nbsp;{open ? '▲' : '▼'}</span>
                  </div>
                  {open && (
                    <div style={{ padding: '4px 12px 10px' }}>
                      {([['产品目标', v.summary?.goal], ['目标用户', v.summary?.users], ['核心需求', v.summary?.need], ['输出范围', v.summary?.scope]] as [string, string | undefined][]).map(([k, val]) => (
                        <div className="wz-airow" key={k}>
                          <span className="ak">{k}</span>
                          <span className="av">{val || '—'}</span>
                        </div>
                      ))}
                      {v.description && <div style={{ marginTop: 6, fontSize: 11.5, color: 'var(--dim)', whiteSpace: 'pre-wrap' }}>输入：{v.description}</div>}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>

      <div className="card">
        <h2>
          市场调研 <span className="hint">让 Agent 自动竞品调研</span>
        </h2>
        <div className="wz-hint2" style={{ margin: '0 0 12px' }}>
          Agent 自动：竞品搜索 → 整页截图 → 风格/卖点分析 → 核心矛盾分析 → 复刻要点报告。产物出现在下方「产物」与画布。
          {!pb.ready && <><br />建议先在上方生成产品需求摘要，调研更聚焦。</>}
        </div>
        {doneSteps > 0 && !rRunning && (
          <input className="wz-input" style={{ maxWidth: 'none', marginBottom: 10 }} defaultValue="" onChange={(e) => (researchInstrRef.current = e.target.value)} placeholder="重做要求（可选）：如竞品换成 stripe/square 这类、核心矛盾往 X 方向想" />
        )}
        <button className="btn" disabled={rRunning} style={rRunning ? { background: 'var(--dash)', cursor: 'not-allowed' } : undefined} onClick={doResearch}>
          <IcSpark />
          {doneSteps ? '重新做市场调研' : '让 Agent 做市场调研'}
        </button>
        {rRunning && (
          <div className="wz-aibox" style={{ marginTop: 14 }}>
            ✦ Agent 调研中…
            {rlast?.text && <><br /><span style={{ color: 'var(--dim)', fontSize: 12 }}>{rlast.text}</span></>}
            <br />
            <span style={{ color: 'var(--dim)', fontSize: 12 }}>进度见下方「阶段步骤 / 产物 / 进展日志」</span>
          </div>
        )}
        {rFailed && (
          <div className="wz-aibox" style={{ marginTop: 14, borderColor: '#e0b4b4', background: '#fdf4f4', color: '#b3403a' }}>
            ❌ Agent 中断了（可能 claude 未登录 / 超时 / 中途报错）。点上面按钮重试，或在💬留言说明、或在 CLI 里接手。
          </div>
        )}
      </div>
    </>
  )
}
