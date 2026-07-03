// ⑤⑥ 系统流程图视图：读 backend-flow.json（薄关系层，⑤ 做本阶段时生成）→ React Flow 交互画布。
// 页面视图（画廊 → 点页面聚焦展开链路）/ 接口·数据全览，两态都是可拖 / 缩放 / hover 高亮 / 点表看字段的画布。只读 + 刷新。
import { useEffect, useState } from 'react'
import { PF_BASE, artUrl } from '../lib'
import { useChannel } from '../store'
import { SystemFlowCanvas } from './SystemFlowCanvas'
import type { BackendFlow, PagesPayload, StateChannel } from '../types'

const EMPTY: BackendFlow = { version: 1, nodes: [], edges: [], pageLinks: [], entry: null, layout: {} }

export function BackendFlowView() {
  const [bf, setBf] = useState<BackendFlow>(EMPTY)
  const [nonce, setNonce] = useState(0)
  const [mode, setMode] = useState<'pages' | 'overview'>('pages')
  const pagesCh = useChannel<PagesPayload>('pages')
  const stateCh = useChannel<StateChannel>('state') // 阶段有活动（如重做本阶段重新生成流程图）→ 自动刷新

  useEffect(() => {
    let cancelled = false
    fetch(PF_BASE + '/api/backend-flow')
      .then((r) => r.json())
      .then((d: BackendFlow) => { if (!cancelled) setBf(d && Array.isArray(d.nodes) ? d : EMPTY) })
      .catch(() => {})
    return () => { cancelled = true }
  }, [nonce, stateCh?.log?.length])

  // 有节点在「处理中」时轮询刷新，直到 agent 改完清除 proc
  useEffect(() => {
    if (!bf.nodes.some((n) => n.proc)) return
    const t = setInterval(() => setNonce((n) => n + 1), 2500)
    return () => clearInterval(t)
  }, [bf])

  const pages = pagesCh?.pages || []
  const linkedKeys = [...new Set((bf.pageLinks || []).map((l) => l.page))]
  const pageCards = linkedKeys.map((key) => {
    const p = pages.find((pp) => pp.id === key || pp.name === key)
    const ver = (p?.versions || []).find((v) => v.file)
    return { key, name: p?.name || key, thumb: ver?.file ? artUrl(ver.file) : '' }
  })

  return (
    <div className="card">
      <h2>系统流程图 <span className="hint">页面 → 接口 → 数据（⑤ 按架构图设计时生成，⑥ 叠执行进度）</span></h2>

      {!bf.nodes.length ? (
        <div className="wz-aibox" style={{ marginTop: 12 }}>
          还没有系统流程图。做 ⑤「功能与数据设计」时 Agent 会<b>自动生成</b>——读你设计的模块 / 接口 / 数据 + ④ 页面，画成「页面 → 接口 → 数据」关系图，无需单独触发。
          <br />
          <span style={{ color: 'var(--dim)', fontSize: 12 }}>纯静态 / 原生本地项目无后端，则不生成。</span>
        </div>
      ) : (
        <>
          <div style={{ margin: '10px 0', display: 'flex', gap: 8 }}>
            <button className={'btn' + (mode === 'pages' ? '' : ' ghost')} onClick={() => setMode('pages')}>📄 页面视图</button>
            <button className={'btn' + (mode === 'overview' ? '' : ' ghost')} onClick={() => setMode('overview')}>🗂 接口 / 数据全览</button>
          </div>

          {mode === 'pages' ? (
            pageCards.length ? (
              <>
                <div style={{ fontSize: 13, color: 'var(--dim)', margin: '4px 0 8px' }}>点页面（④ 真实设计图）→ 就地展开它的 模块 → 接口 → 数据；hover 高亮关联；点任一节点 → 看详情 / 发意见让 Agent 改（发后节点「处理中」脉冲、改完自动更新）；⛶ 放大全屏。</div>
                <SystemFlowCanvas bf={bf} pages={pageCards} mode="pages" onChanged={() => setNonce((n) => n + 1)} />
              </>
            ) : (
              <div className="wz-aibox" style={{ marginTop: 12 }}>还没有页面 ↔ 模块关联（agent `backend-flow link-page` 后，页面会作为图上节点出现、可展开）。可先切「接口 / 数据全览」看整体。</div>
            )
          ) : (
            <SystemFlowCanvas bf={bf} pages={pageCards} mode="overview" onChanged={() => setNonce((n) => n + 1)} />
          )}
        </>
      )}
    </div>
  )
}
