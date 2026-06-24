// Project view shell: topbar (back/product/Stepper/chat/overview/meta/next) + compat banner
// + choices bar + board|canvas + chat drawer. Driven by `state` (+ inbox/choices/health channels).
import { useEffect, useState } from 'react'
import { useChannel, toast, openOverview } from '../store'
import { Stepper } from './Stepper'
import { Board } from './Board'
import { ChoicesBar } from './ChoicesBar'
import { ChatDrawer } from './ChatDrawer'
import { StageRunPanel } from './StageRunPanel'
import { BriefPanel } from './BriefPanel'
import { RefsPanel } from './RefsPanel'
import { Canvas } from './Canvas'
import { IcBack } from '../icons'
import { post } from '../lib'
import type { StateChannel, InboxPayload } from '../types'

const CANVAS_STAGES = [3, 4]

export function Project() {
  const state = useChannel<StateChannel>('state')
  const inbox = useChannel<InboxPayload>('inbox')
  const [selected, setSelected] = useState<number | null>(null)
  const [chatOpen, setChatOpen] = useState(false)
  const [seen, setSeen] = useState(0)

  useEffect(() => {
    if (state && selected === null) {
      const hs = parseInt((location.hash.match(/s(\d+)/) || [])[1])
      const valid = hs >= 1 && state.phases.some((p) => p.id === hs)
      setSelected(valid ? hs : state.current_phase)
    }
  }, [state, selected])

  useEffect(() => {
    const onHash = () => {
      const hs = parseInt((location.hash.match(/s(\d+)/) || [])[1])
      if (hs >= 1) setSelected(hs)
    }
    window.addEventListener('hashchange', onHash)
    return () => window.removeEventListener('hashchange', onHash)
  }, [])

  // keep 'seen' synced while the drawer is open, so messages arriving during
  // an open drawer don't resurface the unread dot after it closes (parity w/ pollInbox).
  useEffect(() => {
    if (chatOpen) setSeen(inbox?.messages.length || 0)
  }, [chatOpen, inbox])

  const selectStage = (id: number) => {
    setSelected(id)
    try {
      history.replaceState(null, '', '#s' + id)
    } catch {
      /* noop */
    }
  }

  const nMsg = inbox?.messages.length || 0
  const unread = nMsg > seen && !chatOpen
  const toggleChat = () => {
    setChatOpen((o) => {
      const no = !o
      if (no) setSeen(nMsg)
      return no
    })
  }

  if (!state) {
    return (
      <div className="page on">
        <div style={{ margin: 'auto', color: 'var(--dim)' }}>（等待初始化…）</div>
      </div>
    )
  }

  const phases = state.phases || []
  const phase = phases.find((p) => p.id === selected) || phases.find((p) => p.id === state.current_phase) || phases[0]
  const sel = phase ? phase.id : null
  const ni = phases.findIndex((p) => p.id === sel)
  const nextPh = phases[ni + 1]
  const done = phases.filter((p) => p.status === 'done').length
  const isCanvas = sel != null && CANVAS_STAGES.includes(sel)

  const stageExtra =
    sel === 1 ? (
      <BriefPanel phase={phase} />
    ) : sel === 2 ? (
      <RefsPanel />
    ) : sel === 5 || sel === 6 || sel === 7 ? (
      <StageRunPanel phase={sel} phaseStatus={phase.status} />
    ) : (
      <div style={{ color: 'var(--dim)', fontSize: 13, padding: '4px 0 14px' }} />
    )

  return (
    <div className="page on">
      <div className="topbar">
        <a className="back" href="/">
          <IcBack /> 全部项目
        </a>
        <span className="ttl">
          <span className="prod" id="product">
            {state.product}
          </span>
        </span>
        <Stepper phases={phases} selected={sel} onSelect={selectStage} />
        <div className="right">
          <button className={'btn ghost sm' + (unread ? ' has-unread' : '')} id="chat-btn" onClick={toggleChat} title="给 Agent 留言（任何阶段都可用）">
            💬 留言
          </button>
          <button className="btn ghost sm" onClick={openOverview} title="一屏看全项目所有产物">
            📋 全部产物
          </button>
          <span className="meta" id="meta">
            {done}/{phases.length} 完成
          </span>
          {nextPh ? (
            <button
              className="btn sm"
              id="next-stage-btn"
              title="完成本阶段（顶部打勾）并进入下一步"
              onClick={() => {
                if (sel != null) { post('/api/stage', { n: sel, status: 'done' }); toast('已完成「' + phase.name + '」') }
                selectStage(nextPh.id)
              }}
            >
              完成 · 下一步
            </button>
          ) : (
            phase.status !== 'done' && (
              <button className="btn sm" title="标记本阶段完成（顶部打勾）" onClick={() => { if (sel != null) { post('/api/stage', { n: sel, status: 'done' }); toast('已完成「' + phase.name + '」') } }}>
                ✓ 完成本阶段
              </button>
            )
          )}
        </div>
      </div>

      {phases.length !== 7 && (
        <div id="compat-banner">
          <div className="compat-warn">
            ⚠️ 此项目是<b>旧版数据（{phases.length} 阶段）</b>，与当前 7 阶段流程不兼容，下面的步骤/按钮会显示异常。请回 <a href="/">全部项目</a> 点「＋ 新建项目」重新开始（旧项目可在总览页删除）。当前 7
            阶段：市场调研 → 找参考 → 首图设计 → 页面设计 → 功能与数据设计 → 开发实现 → 部署上线。
          </div>
        </div>
      )}

      <ChoicesBar />

      {isCanvas ? (
        <Canvas key={sel} stage={sel} product={state.product} />
      ) : (
        phase && <Board phase={phase} state={state} stageExtra={stageExtra} />
      )}

      <ChatDrawer open={chatOpen} onClose={toggleChat} />
    </div>
  )
}
