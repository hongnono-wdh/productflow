// Artifact modal: image / text-md-json (<pre>) / mindmap (markmap) + overview grid.
// markmap + overview ported to parity (P4⑥). html opens a new tab (handled in openArtifact).
import { useEffect, useMemo, useState } from 'react'
import { marked } from 'marked'
import { useModal, useChannel, closeModal, openArtifact, toast } from '../store'
import { PF_BASE, artUrl, loadScript, post } from '../lib'
import { IcX } from '../icons'
import { DocIcon } from './DocIcon'
import type { StateChannel, BriefPayload, ExplorePayload, PagesPayload } from '../types'

// markmap global (vendored). Palette indexed by node path depth — keep exact (critic).
type MarkmapGlobal = {
  Transformer: new () => { transform: (md: string) => { root: unknown } }
  Markmap: { create: (sel: string, opts: Record<string, unknown>, root: unknown) => void }
}

// mermaid global (vendored UMD). Used to render ```mermaid blocks in .md 产物（尤其 ⑤ er.md 的 ER 图）为真图。
type MermaidGlobal = {
  initialize: (opts: Record<string, unknown>) => void
  render: (id: string, code: string) => Promise<{ svg: string }>
}
// 抽出 markdown 里所有 ```mermaid 代码块的源码
function extractMermaid(md: string): string[] {
  const out: string[] = []
  const re = /```mermaid\s*\n([\s\S]*?)```/g
  let mch: RegExpExecArray | null
  while ((mch = re.exec(md))) out.push(mch[1].trim())
  return out
}

function OvImg({ file, label }: { file: string; label: string }) {
  const u = artUrl(file)
  return (
    <div style={{ cursor: 'pointer' }} onClick={() => openArtifact(u, label, 'image')}>
      <img src={u} loading="lazy" style={{ width: '100%', height: 108, objectFit: 'cover', borderRadius: 8, boxShadow: 'var(--block-sh)' }} />
      <div style={{ fontSize: 11.5, color: 'var(--ink-2)', marginTop: 5, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{label}</div>
    </div>
  )
}
function OvDoc({ file, label, type }: { file: string; label: string; type: string }) {
  const u = artUrl(file)
  return (
    <div style={{ cursor: 'pointer' }} onClick={() => openArtifact(u, label, type)}>
      <div style={{ height: 108, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--dim)', borderRadius: 8, background: 'var(--fill)' }}>
        <DocIcon type={type} />
      </div>
      <div style={{ fontSize: 11.5, color: 'var(--ink-2)', marginTop: 5, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{label}</div>
    </div>
  )
}

function Overview() {
  const state = useChannel<StateChannel>('state')
  const [data, setData] = useState<{ brief: BriefPayload | null; ex: ExplorePayload | null; pgs: PagesPayload | null } | null>(null)
  useEffect(() => {
    Promise.all([
      fetch(PF_BASE + '/api/brief').then((r) => (r.ok ? r.json() : null)).catch(() => null),
      fetch(PF_BASE + '/api/explore').then((r) => (r.ok ? r.json() : null)).catch(() => null),
      fetch(PF_BASE + '/api/pages').then((r) => (r.ok ? r.json() : null)).catch(() => null),
    ]).then(([brief, ex, pgs]) => setData({ brief, ex, pgs }))
  }, [])
  if (!data || !state) return <div style={{ padding: 42, textAlign: 'center', color: 'var(--dim)' }}>加载中…</div>
  const { brief, ex, pgs } = data
  const blocks: React.ReactNode[] = []
  for (const ph of state.phases || []) {
    const cards: React.ReactNode[] = []
    if (ph.id === 1 && brief && brief.ready) {
      const s = brief.summary || {}
      const parts = [s.goal, s.users, s.need, s.scope].filter(Boolean).join('　·　')
      if (parts) cards.push(<div key="b" style={{ gridColumn: '1/-1', borderRadius: 8, padding: '12px 14px', background: 'var(--fill)' }}>
        <div style={{ fontWeight: 700, fontSize: 12.5, marginBottom: 4 }}>产品需求摘要</div>
        <div style={{ fontSize: 12, color: 'var(--ink-2)', lineHeight: 1.6 }}>{parts}</div>
      </div>)
    }
    if (ph.id === 2 && ex) for (const r of ex.refs || []) cards.push(<OvImg key={'r' + r.id} file={r.file} label={r.title || '参考'} />)
    if (ph.id === 3 && ex) for (const h of ex.heroes || []) cards.push(<OvImg key={'h' + h.id} file={h.file} label={(h.style || '首图') + (ex.selectedHero === h.file ? ' ★基调' : '')} />)
    if (ph.id === 4 && pgs) for (const pg of pgs.pages || []) for (const v of pg.versions || []) if (v.file) cards.push(<OvImg key={'p' + pg.id + (v.platform || '')} file={v.file} label={`${pg.name}·${v.platform || ''}`} />)
    for (const a of ph.artifacts || []) {
      const lbl = `${a.title} · v${a.version || 1}`
      cards.push(a.type === 'image'
        ? <OvImg key={'a' + a.file} file={a.file} label={lbl} />
        : <OvDoc key={'a' + a.file} file={a.file} label={lbl} type={a.type} />)
    }
    if (!cards.length) continue
    blocks.push(
      <div key={ph.id}>
        <div style={{ fontWeight: 800, fontSize: 13, margin: '16px 0 9px' }}>
          P{ph.id} {ph.name} <span style={{ color: 'var(--dim)', fontWeight: 500 }}>· {cards.length}</span>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(150px,1fr))', gap: 12 }}>{cards}</div>
      </div>,
    )
  }
  return (
    <div style={{ width: '100%', maxWidth: 1100, padding: '6px 4px' }}>
      {blocks.length ? blocks : <div className="empty" style={{ padding: 36, textAlign: 'center', color: 'var(--dim)' }}>还没有任何产物——各阶段产出后会在这里汇总。</div>}
    </div>
  )
}

// 产物修改意见（⑤ 设计产物交互）：选中一段自动引用 + 写意见 → POST /api/inbox（design-feedback）
// 复用 preview-feedback 同一投递路径；agent 检查点读 inbox 后定向改该产物，不必纯对话。
function ArtifactFeedback({ url, title }: { url: string; title: string }) {
  const [open, setOpen] = useState(false)
  const [quote, setQuote] = useState('')
  const [comment, setComment] = useState('')
  const rel = 'artifacts/' + ((url.split('/artifacts/')[1] || '').split('?')[0])
  const grab = () => {
    const s = (window.getSelection?.()?.toString() || '').trim()
    if (!s) { toast('先在上面的产物里选中一段文字，再点「引用选中」'); return }
    setQuote(s.length > 240 ? s.slice(0, 240) + '…' : s)
  }
  const submit = () => {
    const c = comment.trim()
    if (!c) { toast('先写一句要怎么改'); return }
    const text = `设计产物修改意见 @ ${title}（${rel}）` + (quote ? `\n选中：「${quote}」` : '') + `\n意见：${c}`
    post('/api/inbox', { text, type: 'design-feedback', file: rel })
      .then((r) => { if (r.ok) { toast('已提交，Agent 会在检查点读到并定向改这处'); setComment(''); setQuote(''); setOpen(false) } else toast('提交失败，请重试') })
      .catch(() => toast('提交失败，请重试'))
  }
  if (!open) return <button className="btn ghost" onClick={() => setOpen(true)}>✍️ 对这份产物提修改意见（选中一段更精准）</button>
  return (
    <div style={{ borderTop: '1px solid var(--line)', paddingTop: 10, display: 'flex', flexDirection: 'column', gap: 8, textAlign: 'left' }}>
      <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
        <button className="btn ghost sm" onClick={grab}>引用选中</button>
        {quote && <span style={{ fontSize: 12, color: 'var(--dim)' }}>已引用：「{quote.length > 40 ? quote.slice(0, 40) + '…' : quote}」 <span style={{ cursor: 'pointer', color: '#3b82f6' }} onClick={() => setQuote('')}>×</span></span>}
      </div>
      <textarea className="wz-textarea" value={comment} onChange={(e) => setComment(e.target.value)} style={{ height: 68 }} placeholder="这里要怎么改？例：users 表加 phone 字段 / 这个接口改成分页返回 / 删掉这个模块" />
      <div style={{ display: 'flex', gap: 8 }}>
        <button className="btn" onClick={submit}>提交给 Agent 改</button>
        <button className="btn ghost" onClick={() => { setOpen(false); setComment(''); setQuote('') }}>取消</button>
      </div>
    </div>
  )
}

export function Modal() {
  const m = useModal()
  const [text, setText] = useState('')
  const [mmSvgs, setMmSvgs] = useState<string[] | null>(null)  // 渲染好的 mermaid 图（null=无/纯文本）
  const [showSrc, setShowSrc] = useState(false)
  useEffect(() => {
    setText(''); setMmSvgs(null); setShowSrc(false)
    if (m?.kind === 'artifact' && m.type !== 'image' && m.type !== 'mindmap') {
      fetch(m.url).then((r) => r.text()).then(setText).catch(() => setText('(加载失败)'))
    }
  }, [m])

  // mermaid render：文本产物里若含 ```mermaid 块（如 ⑤ er.md 的 ER 图），渲染成真图
  useEffect(() => {
    if (m?.kind !== 'artifact' || m.type === 'image' || m.type === 'mindmap') return
    const blocks = extractMermaid(text)
    if (!blocks.length) { setMmSvgs(null); return }
    let cancelled = false
    ;(async () => {
      await loadScript('/vendor/mermaid.min.js')
      if (cancelled) return
      const mermaid = (window as unknown as { mermaid: MermaidGlobal }).mermaid
      mermaid.initialize({ startOnLoad: false, theme: 'neutral', securityLevel: 'loose', er: { useMaxWidth: false } })
      const svgs: string[] = []
      for (let i = 0; i < blocks.length; i++) {
        try {
          const { svg } = await mermaid.render(`mmd-${i}-${text.length}`, blocks[i])
          svgs.push(svg)
        } catch { /* 单个块解析失败就跳过，不阻断其它块 */ }
      }
      if (!cancelled) setMmSvgs(svgs.length ? svgs : null)
    })()
    return () => { cancelled = true }
  }, [m, text])

  // markmap render
  useEffect(() => {
    if (m?.kind !== 'artifact' || m.type !== 'mindmap') return
    let cancelled = false
    ;(async () => {
      await loadScript('/vendor/d3.min.js')
      await loadScript('/vendor/markmap-lib.js')
      await loadScript('/vendor/markmap-view.js')
      if (cancelled) return
      const md = await (await fetch(m.url)).text()
      if (cancelled) return
      const mm = (window as unknown as { markmap: MarkmapGlobal }).markmap
      const { root } = new mm.Transformer().transform(md)
      const palette = ['#111111', '#444444', '#777777', '#999999', '#555555', '#333333']
      mm.Markmap.create(
        '#mm-svg',
        {
          duration: 300,
          maxWidth: 340,
          paddingX: 18,
          autoFit: true,
          initialExpandLevel: -1,
          color: (n: { state?: { path?: string } }) => palette[(parseInt((n.state?.path || '0.0').split('.')[1]) || 0) % palette.length],
        },
        root,
      )
    })()
    return () => {
      cancelled = true
    }
  }, [m])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') closeModal()
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [])

  // .md 产物：正文按 markdown 渲染（mermaid 块另渲成图，这里剥掉）
  const isMd = !!m && m.kind === 'artifact' && /\.md(\?|$)/.test(m.url || '')
  const mdBody = useMemo(() => (isMd ? (marked.parse(text.replace(/```mermaid\s*\n[\s\S]*?```/g, ''), { async: false }) as string) : ''), [isMd, text])
  if (!m) return null
  const wide = m.kind === 'artifact' && (m.type === 'mindmap' || !!mmSvgs)
  return (
    <div className="modal show" id="modal" onClick={(e) => { if (e.target === e.currentTarget) closeModal() }}>
      <div className={'box' + (wide ? ' wide' : '')}>
        <div className="bar">
          <span className="mt" id="modal-title">{m.kind === 'artifact' ? m.title : '全部产物 · 项目总览'}</span>
          <span className="x" onClick={closeModal}>
            <IcX /> 关闭
          </span>
        </div>
        <div id="modal-body" style={{ overflow: 'auto', display: 'flex', justifyContent: 'center' }}>
          {m.kind === 'artifact' && m.type === 'image' && <img className="full" src={m.url} />}
          {m.kind === 'artifact' && m.type === 'mindmap' && <svg id="mm-svg" />}
          {m.kind === 'artifact' && m.type !== 'image' && m.type !== 'mindmap' && (
            <div style={{ width: '100%', maxWidth: 1100 }}>
              {mmSvgs && !showSrc && mmSvgs.map((svg, i) => (
                <div key={i} className="mermaid-box" style={{ display: 'flex', justifyContent: 'center', padding: '8px 0', overflow: 'auto' }}
                  dangerouslySetInnerHTML={{ __html: svg }} />
              ))}
              {isMd && !showSrc
                ? <div className="md-body" dangerouslySetInnerHTML={{ __html: mdBody }} />
                : <pre>{text}</pre>}
              {(isMd || mmSvgs) && (
                <div style={{ textAlign: 'center', margin: '12px 0 2px' }}>
                  <button className="btn ghost" onClick={() => setShowSrc((s) => !s)}>{showSrc ? '看渲染' : '查看源码'}</button>
                </div>
              )}
            </div>
          )}
          {m.kind === 'overview' && <Overview />}
        </div>
        {m.kind === 'artifact' && m.type !== 'image' && m.type !== 'mindmap' && (
          <div style={{ padding: '0 16px 14px' }}>
            <ArtifactFeedback url={m.url} title={m.title} />
          </div>
        )}
      </div>
    </div>
  )
}
