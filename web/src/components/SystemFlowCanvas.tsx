// 系统流程图·交互画布（React Flow）。两种 mode：
//  pages（页面视图）：画廊态各页面=④真实设计图缩略网格；点某页面→聚焦态（只显它+就地展开的
//    模块→接口→数据表链路，其它隐藏）；再点该页面→收回画廊。
//  overview（接口/数据全览）：所有 模块→接口→数据表 一张图。
// 节点主显中文名、下方灰字英文 id；点模块/接口/数据表 → 弹该节点对话框（表含字段 + 「这个节点要改什么」
// 发给 agent 改，走 design-feedback）；点页面 = 展开/收回。共有：拖拽、缩放/平移、hover 高亮、放大全屏。
import { useEffect, useMemo, useState } from 'react'
import { createPortal } from 'react-dom'
import { ReactFlow, Background, Controls, MiniMap, Handle, Position, useNodesState, useEdgesState } from '@xyflow/react'
import type { Node, Edge, NodeProps } from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { post, PF_BASE } from '../lib'
import { toast } from '../store'
import type { BackendFlow } from '../types'

export type PageCard = { key: string; name: string; thumb: string }

const shortLabel = (id: string) => id.replace(/^(module|api|interface|table):/, '')
const STATUS: Record<string, { bg: string; bd: string }> = {
  done: { bg: '#d7f5dd', bd: '#3aa657' }, doing: { bg: '#dbeafe', bd: '#3b82f6' },
  needfix: { bg: '#fde2e2', bd: '#e0574f' }, todo: { bg: '#ffffff', bd: '#cbd5e1' },
}
const ICON: Record<string, string> = { module: '🧩', interface: '🔌', table: '🗄' }

function PageNode({ data }: NodeProps) {
  const d = data as { label: string; thumb?: string; focused?: boolean; dim?: boolean; onToggle?: () => void }
  return (
    <div
      style={{
        cursor: 'pointer', width: 160, background: '#fff', borderRadius: 10, overflow: 'hidden',
        border: `2px solid ${d.focused ? '#f0a500' : '#d5dbe2'}`, opacity: d.dim ? 0.3 : 1,
        boxShadow: d.focused ? '0 4px 16px rgba(240,165,0,.25)' : '0 2px 8px rgba(0,0,0,.10)', transition: 'opacity .12s, box-shadow .12s',
      }}>
      {d.thumb
        ? <img src={d.thumb} style={{ width: 160, height: 108, objectFit: 'cover', objectPosition: 'top', display: 'block' }} />
        : <div style={{ width: 160, height: 108, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 34, background: '#f3f4f6' }}>📄</div>}
      <div style={{ padding: '5px 8px', fontSize: 12, textAlign: 'center', borderTop: '1px solid #eee', fontWeight: 500 }}>
        {d.label} <span style={{ color: 'var(--dim)', fontWeight: 400 }}>{d.focused ? '· 点收回' : '· 点展开'}</span>
      </div>
      <Handle type="source" position={Position.Right} style={{ opacity: 0 }} />
    </div>
  )
}

// 节点：主显中文名（data.name），下方灰字英文 id（data.label）；无中文名则只显英文
function Box({ data }: NodeProps) {
  const d = data as { label: string; name?: string; kind: string; status?: string; dim?: boolean; proc?: boolean; stub?: string; missKey?: boolean; onOpen?: () => void }
  const c = STATUS[d.status || 'todo'] || STATUS.todo
  return (
    <div
      style={{
        position: 'relative', padding: '8px 12px', minWidth: 104, textAlign: 'center', lineHeight: 1.25,
        borderRadius: d.kind === 'table' ? 16 : 8, border: `2px solid ${d.proc ? '#f0a500' : d.stub ? '#e0574f' : d.missKey ? '#e0a800' : c.bd}`, background: d.stub ? '#fdf6f5' : d.missKey ? '#fdf8e8' : c.bg,
        opacity: d.dim ? 0.22 : 1, transition: 'opacity .12s', cursor: 'pointer',
        boxShadow: '0 1px 3px rgba(0,0,0,.08)', ...(d.proc ? { animation: 'pf-pulse 1.1s ease-in-out infinite' } : {}),
      }}>
      <Handle type="target" position={Position.Left} style={{ opacity: 0 }} />
      <div style={{ fontSize: 13 }}>{ICON[d.kind] || ''} {d.name || d.label}{d.kind === 'table' ? ' ▸' : ''}</div>
      {d.name ? <div style={{ fontSize: 11, color: 'var(--dim)', fontFamily: 'monospace' }}>{d.label}</div> : null}
      {(d.stub || d.missKey) ? (
        <div style={{ display: 'flex', gap: 3, justifyContent: 'center', marginTop: 3, flexWrap: 'wrap' }}>
          {d.stub ? <span title={typeof d.stub === 'string' ? d.stub : ''} style={{ fontSize: 9.5, background: '#fde2e2', color: '#b93a32', borderRadius: 5, padding: '0 5px', fontWeight: 700 }}>⚠占位</span> : null}
          {d.missKey ? <span style={{ fontSize: 9.5, background: '#fdeecb', color: '#9a6a08', borderRadius: 5, padding: '0 5px', fontWeight: 700 }}>🔑待key</span> : null}
        </div>
      ) : null}
      {d.proc ? <div style={{ position: 'absolute', top: -9, right: -9, fontSize: 10, background: '#f0a500', color: '#fff', borderRadius: 8, padding: '1px 6px', whiteSpace: 'nowrap' }}>⏳ 处理中</div> : null}
      <Handle type="source" position={Position.Right} style={{ opacity: 0 }} />
    </div>
  )
}
const nodeTypes = { page: PageNode, box: Box }

const RH = 100
const COL = { page: 20, module: 320, interface: 610, table: 910 }
const OCOL = { module: 40, interface: 380, table: 820 }

function build(bf: BackendFlow, pages: PageCard[], focusPage: string | null, mode: 'pages' | 'overview' | 'progress', onToggle: (k: string) => void, onNode: (id: string) => void, missKeyMods?: Set<string>) {
  const nodes: Node[] = []
  const edges: Edge[] = []
  const byId = new Map(bf.nodes.map((n) => [n.id, n]))
  const mkE = (s: string, t: string, label?: string) => edges.push({ id: `${s}->${t}->${label || ''}`, source: s, target: t, label })
  const boxData = (id: string) => { const n = byId.get(id); return { kind: n?.type || 'module', label: shortLabel(id), name: n?.name, status: n?.status, proc: n?.proc, stub: n?.stub, missKey: missKeyMods?.has(id), onOpen: () => onNode(id) } }
  const mkBox = (id: string, x: number, y: number) => nodes.push({ id, type: 'box', position: { x, y }, data: boxData(id), draggable: true })

  // 模块 id 归一化：接口的 module 字段可能是裸名(auth)或带前缀(module:auth)，统一到节点 id
  const modId = (m: string) => (m.startsWith('module:') ? m : 'module:' + m)

  if (mode === 'overview') {
    // 按模块分「带」：每个模块 + 它的接口排同一水平带 → calls 边短、不交叉
    const mods = bf.nodes.filter((n) => n.type === 'module')
    const allIfc = bf.nodes.filter((n) => n.type === 'interface')
    // 接口归属：优先 module→interface 的 calls 边；再补 n.module 属性（归一化后匹配，裸名/带前缀都认）
    const ownIds = new Map<string, string[]>(mods.map((m) => [m.id, []]))
    for (const e of bf.edges || []) if (e.type === 'calls' && ownIds.has(e.from) && byId.get(e.to)?.type === 'interface' && !ownIds.get(e.from)!.includes(e.to)) ownIds.get(e.from)!.push(e.to)
    for (const n of allIfc) { const mid = n.module ? modId(n.module) : ''; if (ownIds.has(mid) && !ownIds.get(mid)!.includes(n.id)) ownIds.get(mid)!.push(n.id) }
    const claimed = new Set<string>([...ownIds.values()].flat())
    const ifcY = new Map<string, number>()
    let y = 20
    for (const m of mods) {
      const own = ownIds.get(m.id)!.map((id) => byId.get(id)).filter(Boolean) as { id: string }[]
      const rows = Math.max(1, own.length)
      const top = y
      mkBox(m.id, OCOL.module, top + ((rows - 1) * RH) / 2) // 模块居其带纵向中点
      own.forEach((n, i) => { mkBox(n.id, OCOL.interface, top + i * RH); ifcY.set(n.id, top + i * RH) })
      y += rows * RH + 28
    }
    allIfc.filter((n) => !claimed.has(n.id)).forEach((n) => { mkBox(n.id, OCOL.interface, y); ifcY.set(n.id, y); y += RH }) // 无归属接口堆下面
    // 表按重心（连它的接口平均 y）排序减少读/写边交叉；并在内容总高内均匀铺开——表比接口少时纵向拉开、不挤顶部
    const bary = (t: string) => { const ys = (bf.edges || []).filter((e) => e.to === t && ifcY.has(e.from)).map((e) => ifcY.get(e.from) as number); return ys.length ? ys.reduce((a, b) => a + b, 0) / ys.length : 1e9 }
    const tbls = [...bf.nodes.filter((n) => n.type === 'table')].sort((a, b) => bary(a.id) - bary(b.id))
    const spanH = Math.max(y - 28, tbls.length * RH) // 内容总高（模块带累计）
    tbls.forEach((n, i) => mkBox(n.id, OCOL.table, tbls.length > 1 ? (i + 0.5) * (spanH / tbls.length) : spanH / 2))
    for (const e of bf.edges || []) mkE(e.from, e.to, e.type === 'writes_to' ? '写' : e.type === 'reads_from' ? '读' : undefined)
    const adj = new Map<string, Set<string>>()
    nodes.forEach((n) => adj.set(n.id, new Set()))
    edges.forEach((e) => { adj.get(e.source)?.add(e.target); adj.get(e.target)?.add(e.source) })
    return { nodes, edges, adj }
  }

  if (mode === 'progress') {
    // ⑦ 成品预览：两层「模块 → 接口」（复用 overview 的模块带布局，去掉数据表层）
    const mods = bf.nodes.filter((n) => n.type === 'module')
    const allIfc = bf.nodes.filter((n) => n.type === 'interface')
    const ownIds = new Map<string, string[]>(mods.map((m) => [m.id, []]))
    for (const e of bf.edges || []) if (e.type === 'calls' && ownIds.has(e.from) && byId.get(e.to)?.type === 'interface' && !ownIds.get(e.from)!.includes(e.to)) ownIds.get(e.from)!.push(e.to)
    for (const n of allIfc) { const mid = n.module ? modId(n.module) : ''; if (ownIds.has(mid) && !ownIds.get(mid)!.includes(n.id)) ownIds.get(mid)!.push(n.id) }
    const claimed = new Set<string>([...ownIds.values()].flat())
    let y = 20
    for (const m of mods) {
      const own = ownIds.get(m.id)!.map((id) => byId.get(id)).filter(Boolean) as { id: string }[]
      const rows = Math.max(1, own.length)
      const top = y
      mkBox(m.id, OCOL.module, top + ((rows - 1) * RH) / 2)
      own.forEach((n, i) => { mkBox(n.id, OCOL.interface, top + i * RH); mkE(m.id, n.id) })
      y += rows * RH + 28
    }
    allIfc.filter((n) => !claimed.has(n.id)).forEach((n) => { mkBox(n.id, OCOL.interface, y); y += RH })
    const adj = new Map<string, Set<string>>()
    nodes.forEach((n) => adj.set(n.id, new Set()))
    edges.forEach((e) => { adj.get(e.source)?.add(e.target); adj.get(e.target)?.add(e.source) })
    return { nodes, edges, adj }
  }

  if (!focusPage) {
    const perRow = Math.min(4, Math.max(1, Math.ceil(Math.sqrt(pages.length))))
    pages.forEach((pg, i) => nodes.push({
      id: 'page:' + pg.key, type: 'page', draggable: true,
      position: { x: (i % perRow) * 210, y: Math.floor(i / perRow) * 185 },
      data: { label: pg.name, thumb: pg.thumb, focused: false, onToggle: () => onToggle(pg.key) },
    }))
    return { nodes, edges, adj: new Map(nodes.map((n) => [n.id, new Set<string>()])) }
  }

  // 聚焦某页面：页面 → 它的模块 → 各模块接口 → 数据表；按模块分带（同全览），短列铺满全高、不挤顶
  const pg = pages.find((p) => p.key === focusPage)
  const pid = 'page:' + focusPage
  const modIds = [...new Set((bf.pageLinks || []).filter((l) => l.page === focusPage).map((l) => modId(l.module)))]
  const ownIds = new Map<string, string[]>(modIds.map((m) => [m, []]))
  for (const e of bf.edges || []) if (e.type === 'calls' && ownIds.has(e.from) && byId.get(e.to)?.type === 'interface' && !ownIds.get(e.from)!.includes(e.to)) ownIds.get(e.from)!.push(e.to)
  for (const n of bf.nodes) if (n.type === 'interface' && n.module) { const mid = modId(n.module); if (ownIds.has(mid) && !ownIds.get(mid)!.includes(n.id)) ownIds.get(mid)!.push(n.id) }
  const ifcY = new Map<string, number>()
  let y = 20
  for (const mid of modIds) {
    const own = ownIds.get(mid)!.map((id) => byId.get(id)).filter(Boolean) as { id: string }[]
    const rows = Math.max(1, own.length)
    const top = y
    mkBox(mid, COL.module, top + ((rows - 1) * RH) / 2) // 模块居其带纵向中点
    own.forEach((n, i) => { mkBox(n.id, COL.interface, top + i * RH); ifcY.set(n.id, top + i * RH) })
    mkE(pid, mid)
    own.forEach((n) => mkE(mid, n.id))
    y += rows * RH + 28
  }
  const totalH = Math.max(y - 28, RH)
  nodes.push({ id: pid, type: 'page', draggable: true, position: { x: COL.page, y: Math.max(0, totalH / 2 - 70) }, data: { label: pg?.name || focusPage, thumb: pg?.thumb, focused: true, onToggle: () => onToggle(focusPage) } })
  // 表：这些接口读写的表，右列按重心排序 + 在总高内铺满
  const tblEdges = (bf.edges || []).filter((e) => ifcY.has(e.from) && (e.type === 'reads_from' || e.type === 'writes_to'))
  const tbls = [...new Set(tblEdges.map((e) => e.to))].map((id) => byId.get(id)).filter(Boolean) as { id: string }[]
  const tbary = (t: string) => { const ys = tblEdges.filter((e) => e.to === t).map((e) => ifcY.get(e.from) as number); return ys.length ? ys.reduce((a, b) => a + b, 0) / ys.length : 1e9 }
  tbls.sort((a, b) => tbary(a.id) - tbary(b.id))
  tbls.forEach((n, i) => mkBox(n.id, COL.table, tbls.length > 1 ? (i + 0.5) * (totalH / tbls.length) : totalH / 2))
  tblEdges.forEach((e) => mkE(e.from, e.to, e.type === 'writes_to' ? '写' : '读'))
  const adj = new Map<string, Set<string>>()
  nodes.forEach((n) => adj.set(n.id, new Set()))
  edges.forEach((e) => { adj.get(e.source)?.add(e.target); adj.get(e.target)?.add(e.source) })
  return { nodes, edges, adj }
}

export function SystemFlowCanvas({ bf, pages, mode, onChanged, missKeyMods, onRerun }: { bf: BackendFlow; pages: PageCard[]; mode: 'pages' | 'overview' | 'progress'; onChanged?: () => void; missKeyMods?: Set<string>; onRerun?: (id: string) => void }) {
  const [focusPage, setFocusPage] = useState<string | null>(mode === 'pages' && pages.length === 1 ? pages[0].key : null)
  const [selId, setSelId] = useState<string | null>(null)
  const [msg, setMsg] = useState('')
  const toggle = (k: string) => setFocusPage((f) => (f === k ? null : k))
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const built = useMemo(() => build(bf, pages, focusPage, mode, toggle, setSelId, missKeyMods), [bf, pages, focusPage, mode, missKeyMods])
  const procIds = useMemo(() => new Set(bf.nodes.filter((n) => n.proc).map((n) => n.id)), [bf]) // 处理中的节点（改动传播动效用）
  const [nodes, setNodes, onNodesChange] = useNodesState(built.nodes)
  const [edges, setEdges, onEdgesChange] = useEdgesState(built.edges)
  const [hover, setHover] = useState<string | null>(null)
  const [full, setFull] = useState(false)
  const [procLog, setProcLog] = useState<{ text?: string }[]>([])

  useEffect(() => { setNodes(built.nodes); setEdges(built.edges) }, [built, setNodes, setEdges])
  useEffect(() => {
    setNodes((nds) => nds.map((n) => ({ ...n, data: { ...n.data, dim: hover ? n.id !== hover && !built.adj.get(hover)?.has(n.id) : false } })))
    setEdges((eds) => eds.map((e) => {
      const procOn = procIds.has(e.source) || procIds.has(e.target) // 连着处理中节点 → 橙色流动（改动沿连线跑）
      const hoverRel = !hover || e.source === hover || e.target === hover
      return { ...e, animated: procOn || (!!hover && hoverRel), style: { opacity: hover && !hoverRel ? 0.12 : 1, strokeWidth: procOn ? 2.5 : hover && hoverRel ? 2 : 1, ...(procOn ? { stroke: '#f0a500' } : {}) } }
    }))
  }, [hover, built, procIds, setNodes, setEdges])

  const sel = selId ? bf.nodes.find((n) => n.id === selId) : null
  const closeDialog = () => { setSelId(null); setMsg('') }
  // 节点处理中 → 轮询 node-change agent 进度日志（对话框里实时看）
  useEffect(() => {
    if (!sel?.proc) { setProcLog([]); return }
    let stop = false
    const tick = () => fetch(PF_BASE + '/api/agent-log?phase=node-change').then((r) => r.json()).then((d) => { if (!stop) setProcLog(Array.isArray(d.lines) ? d.lines : []) }).catch(() => {})
    tick()
    const t = setInterval(tick, 1500)
    return () => { stop = true; clearInterval(t) }
  }, [sel?.proc, sel?.id])
  const sendNodeChange = () => {
    const t = msg.trim()
    if (!sel || !t) { toast('先写一句这个节点要怎么改'); return }
    // → /api/node-change：记留言 + 标处理中 + 后台真拉起 agent 去改（改完自动清 proc + set-status）
    post('/api/node-change', { node: sel.id, text: t })
      .then((r) => {
        if (!r.ok) { toast('提交失败，请重试'); return }
        toast('已发给 Agent，节点进入「处理中」')
        setMsg('')
        onChanged?.() // 刷新拿到 proc=true → 对话框切进度视图
      })
      .catch(() => toast('提交失败，请重试'))
  }

  const flow = (
    <ReactFlow
      key={mode + ':' + (focusPage || '_gallery')}
      nodes={nodes} edges={edges} onNodesChange={onNodesChange} onEdgesChange={onEdgesChange}
      nodeTypes={nodeTypes} fitView fitViewOptions={{ padding: 0.15 }} minZoom={0.2} maxZoom={2}
      onNodeMouseEnter={(_, n) => setHover(n.id)} onNodeMouseLeave={() => setHover(null)}
      onNodeClick={(_, n) => (n.type === 'page' ? toggle(n.id.replace(/^page:/, '')) : setSelId(n.id))}
      nodeDragThreshold={4}
      proOptions={{ hideAttribution: true }}
    >
      <Background gap={16} color="#e5e7eb" />
      <Controls showInteractive={false} />
      <MiniMap pannable zoomable nodeStrokeWidth={2} />
    </ReactFlow>
  )

  // 点节点 → 该节点对话框：中文名 + 英文 id +（表）字段 + 「这个节点要改什么」发给 agent
  const nodeDialog = sel && createPortal(
    <div onClick={closeDialog} style={{ position: 'fixed', inset: 0, zIndex: 10000, background: 'rgba(0,0,0,.35)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div onClick={(e) => e.stopPropagation()} style={{ width: 420, maxWidth: '92vw', maxHeight: '86vh', overflow: 'auto', background: '#fff', borderRadius: 12, boxShadow: '0 12px 40px rgba(0,0,0,.28)' }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10, padding: '14px 16px', borderBottom: '1px solid var(--line)' }}>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 16, fontWeight: 600 }}>{ICON[sel.type] || ''} {sel.name || shortLabel(sel.id)}</div>
            <div style={{ fontSize: 12, color: 'var(--dim)', fontFamily: 'monospace' }}>{shortLabel(sel.id)}　·　{sel.type}{sel.status ? '　·　' + sel.status : ''}</div>
          </div>
          <span onClick={closeDialog} style={{ cursor: 'pointer', color: 'var(--dim)', fontSize: 18 }}>✕</span>
        </div>
        {sel.type === 'table' && (
          <div style={{ padding: '10px 16px', borderBottom: '1px solid var(--line)' }}>
            <div style={{ fontSize: 12, color: 'var(--dim)', marginBottom: 4 }}>字段结构</div>
            {sel.fields && sel.fields.length
              ? sel.fields.map((f, i) => {
                  const idx = f.search(/\s[—–-]\s|\s{2,}/)   // 「列名+类型」与「中文备注」分隔：空格+—/–/-+空格，或连续空格
                  const col = idx >= 0 ? f.slice(0, idx).trim() : f.trim()
                  const note = idx >= 0 ? f.slice(idx).replace(/^[\s—–-]+/, '').trim() : ''
                  return (
                    <div key={i} style={{ padding: '2px 0', display: 'flex', gap: 8, alignItems: 'baseline', flexWrap: 'wrap' }}>
                      <span style={{ fontFamily: 'monospace', fontSize: 13, whiteSpace: 'nowrap' }}>{col}</span>
                      {note ? <span style={{ color: 'var(--dim)', fontSize: 12 }}>{note}</span> : null}
                    </div>
                  )
                })
              : <span style={{ color: 'var(--dim)', fontSize: 13 }}>该表未附字段摘要——见 ⑤ ER 图 / schema.sql 产物。</span>}
          </div>
        )}
        {sel.proc ? (
          <div style={{ padding: '12px 16px' }}>
            <div style={{ fontSize: 13, marginBottom: 6, color: '#c47f00' }}>⏳ Agent 正在处理这个节点…（改完自动更新；可关闭后台继续）</div>
            <div style={{ maxHeight: 200, overflow: 'auto', background: '#f7f8fa', border: '1px solid var(--line)', borderRadius: 8, padding: '8px 10px', fontSize: 12, lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>
              {procLog.length ? procLog.map((l, i) => <div key={i}>{l.text || ''}</div>) : <span style={{ color: 'var(--dim)' }}>正在启动 Agent…</span>}
            </div>
            <div style={{ fontSize: 13, margin: '12px 0 6px' }}>继续追加指令：</div>
            <textarea className="wz-input" style={{ width: '100%', minHeight: 56, resize: 'vertical' }} value={msg} onChange={(e) => setMsg(e.target.value)} placeholder="如：顺便把返回值也加上 avatar …" />
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 10 }}>
              <button className="btn ghost" onClick={closeDialog}>关闭（后台继续）</button>
              <button className="btn" onClick={sendNodeChange}>追加指令</button>
            </div>
          </div>
        ) : (
          <div style={{ padding: '12px 16px' }}>
            <div style={{ fontSize: 13, marginBottom: 6 }}>这个节点要改什么？</div>
            <textarea className="wz-input" style={{ width: '100%', minHeight: 72, resize: 'vertical' }} value={msg} onChange={(e) => setMsg(e.target.value)}
              placeholder={sel.type === 'table' ? '如：加一个 phone 字段、email 改成必填唯一…' : sel.type === 'interface' ? '如：加分页参数、返回值加 avatar 字段、限流…' : '如：拆成两个子模块、并入权限校验…'} />
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 10 }}>
              {onRerun && sel.type === 'module' ? <button className="btn ghost" style={{ marginRight: 'auto', color: '#b93a32', borderColor: '#f0b8b4' }} onClick={() => { onRerun(sel.id); closeDialog() }}>↻ 重做本模块</button> : null}
              <button className="btn ghost" onClick={closeDialog}>取消</button>
              <button className="btn" onClick={sendNodeChange}>发给 Agent 改</button>
            </div>
          </div>
        )}
      </div>
    </div>,
    document.body,
  )

  if (full) {
    return createPortal(
      <div style={{ position: 'fixed', inset: 0, zIndex: 9999, background: '#fff', display: 'flex', flexDirection: 'column' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '10px 16px', borderBottom: '1px solid var(--line)' }}>
          <b>系统流程图</b>
          <span style={{ color: 'var(--dim)', fontSize: 12 }}>{mode === 'pages' ? '点页面展开/收回 · ' : ''}点节点改它 · 拖动 · 缩放 · hover 高亮</span>
          <button className="btn ghost" style={{ marginLeft: 'auto' }} onClick={() => setFull(false)}>✕ 关闭</button>
        </div>
        <div style={{ flex: 1, minHeight: 0 }}>{flow}</div>
        {nodeDialog}
      </div>,
      document.body,
    )
  }

  return (
    <div style={{ height: 520, border: '1px solid var(--line)', borderRadius: 8, background: '#fafbfc', position: 'relative' }}>
      <button className="btn ghost sm" style={{ position: 'absolute', top: 8, right: 8, zIndex: 7 }} onClick={() => setFull(true)}>⛶ 放大</button>
      {flow}
      {nodeDialog}
    </div>
  )
}
