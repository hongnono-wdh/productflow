// Artifact modal: image / text-md-json (<pre>) / mindmap (markmap) + overview grid.
// markmap + overview ported to parity (P4⑥). html opens a new tab (handled in openArtifact).
import { useEffect, useState } from 'react'
import { useModal, useChannel, closeModal, openArtifact } from '../store'
import { PF_BASE, artUrl, loadScript } from '../lib'
import { IcX } from '../icons'
import { DocIcon } from './DocIcon'
import type { StateChannel, BriefPayload, ExplorePayload, PagesPayload } from '../types'

// markmap global (vendored). Palette indexed by node path depth — keep exact (critic).
type MarkmapGlobal = {
  Transformer: new () => { transform: (md: string) => { root: unknown } }
  Markmap: { create: (sel: string, opts: Record<string, unknown>, root: unknown) => void }
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
    for (const a of ph.artifacts || []) cards.push(a.type === 'image' ? <OvImg key={'a' + a.file} file={a.file} label={a.title} /> : <OvDoc key={'a' + a.file} file={a.file} label={a.title} type={a.type} />)
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

export function Modal() {
  const m = useModal()
  const [text, setText] = useState('')
  useEffect(() => {
    setText('')
    if (m?.kind === 'artifact' && m.type !== 'image' && m.type !== 'mindmap') {
      fetch(m.url).then((r) => r.text()).then(setText).catch(() => setText('(加载失败)'))
    }
  }, [m])

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

  if (!m) return null
  const wide = m.kind === 'artifact' && m.type === 'mindmap'
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
          {m.kind === 'artifact' && m.type !== 'image' && m.type !== 'mindmap' && <pre>{text}</pre>}
          {m.kind === 'overview' && <Overview />}
        </div>
      </div>
    </div>
  )
}
