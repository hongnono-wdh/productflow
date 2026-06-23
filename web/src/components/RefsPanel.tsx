// P2 panel: 找参考. Style tags + ref grid + Viewer.js zoom + collect/search/more-like.
// ref+force model mirrors the original imperative pExplore reconciliation.
import { useEffect, useReducer, useRef, useState } from 'react'
import { useChannel, toast } from '../store'
import { PF_BASE, post, loadScript } from '../lib'
import type { ExplorePayload, ExploreRef, ExploreHero, AgentLogPayload, SearchPlan } from '../types'

const STAGE_TAGS = ['极简', '现代', '玻璃拟态', '暗色', '暖色调', '编辑风', '科技感', '大胆活力', '柔和未来', '瑞士国际']

interface PE {
  stylePrefs: string[]
  request: Record<string, unknown>
  refs: ExploreRef[]
  selectedRefs: string[]
  styleSummary: string
  heroes: ExploreHero[]
  selectedHero: string
  heroGenFailed: boolean
  heroGenLog: unknown[]
  searchPlan: SearchPlan | null
}
type ViewerInst = { view: (i: number) => void; destroy: () => void }
type ViewerCtor = new (el: Element, opts: Record<string, unknown>) => ViewerInst

function refUrl(file: string) {
  return PF_BASE + '/artifacts/' + file.replace(/^artifacts\//, '')
}

export function RefsPanel() {
  const e = useChannel<ExplorePayload>('explore')
  const searchLog = useChannel<AgentLogPayload>('agent-log:search-refs')
  const [, force] = useReducer((x: number) => x + 1, 0)
  const peRef = useRef<PE>({ stylePrefs: [], request: {}, refs: [], selectedRefs: [], styleSummary: '', heroes: [], selectedHero: '', heroGenFailed: false, heroGenLog: [], searchPlan: null })
  const [collectUrl, setCollectUrl] = useState('')
  const [dragOver, setDragOver] = useState(false)
  const [kwInput, setKwInput] = useState('')
  const suggestedRef = useRef(false)

  // 粘贴/拖入图片 → 直接存盘 + 登记成参考（人工加速、注入品味）；结果经 WS 回流刷新
  const uploadFiles = (files: File[]) => {
    const imgs = files.filter((f) => f.type.startsWith('image/'))
    if (!imgs.length) return
    imgs.forEach((f) => {
      const rd = new FileReader()
      rd.onload = () => post('/api/explore', { uploadRef: { dataUrl: String(rd.result), title: (f.name || '').replace(/\.[^.]+$/, '') || '我加的参考' } })
      rd.readAsDataURL(f)
    })
    toast(`已添加 ${imgs.length} 张参考`)
  }
  // 全局粘贴：在找参考页 ⌘/Ctrl+V 直接贴图（忽略输入框里的粘贴）
  useEffect(() => {
    const onPaste = (ev: ClipboardEvent) => {
      const t = ev.target as HTMLElement | null
      if (t && /^(INPUT|TEXTAREA)$/.test(t.tagName)) return
      const fs = Array.from(ev.clipboardData?.files || []).filter((f) => f.type.startsWith('image/'))
      if (fs.length) {
        ev.preventDefault()
        uploadFiles(fs)
      }
    }
    document.addEventListener('paste', onPaste)
    return () => document.removeEventListener('paste', onPaste)
  }, [])

  useEffect(() => {
    if (!e) return
    const pe = peRef.current
    pe.refs = e.refs || []
    pe.heroes = e.heroes || []
    pe.selectedRefs = e.selectedRefs || []
    pe.selectedHero = e.selectedHero || ''
    pe.styleSummary = e.styleSummary || ''
    pe.heroGenFailed = !!e.heroGenFailed
    pe.heroGenLog = e.heroGenLog || []
    pe.searchPlan = e.searchPlan || null
    let req: Record<string, unknown> = (e.request as Record<string, unknown>) || {}
    if (req.kind) req = { [req.kind as string]: req }
    pe.request = req
    if (!pe.stylePrefs.length && Array.isArray(e.stylePrefs)) pe.stylePrefs = e.stylePrefs
    // 进入②若还没关键词、也没参考 → 自动请 agent 据市场调研拟几个预设关键词（只触发一次）
    if (!suggestedRef.current && !(pe.searchPlan?.keywords?.length) && !pe.refs.length
        && !pe.request['suggest-keywords'] && !pe.request['search-refs']) {
      suggestedRef.current = true
      post('/api/explore', { request: { kind: 'suggest-keywords' } })
    }
    force()
  }, [e])

  const pe = peRef.current
  const planKw = pe.searchPlan?.keywords || []
  const suggesting = !!pe.request['suggest-keywords']
  const saveKw = (kws: string[]) => {
    pe.searchPlan = { ...(pe.searchPlan || {}), keywords: kws }
    force()
    post('/api/explore', { setSearchPlan: { keywords: kws } })
  }
  const addKw = (w: string) => {
    const v = w.trim()
    setKwInput('')
    if (!v || planKw.includes(v)) return
    saveKw([...planKw, v])
  }
  const removeKw = (w: string) => saveKw(planKw.filter((k) => k !== w))
  const searching = !!pe.request['search-refs']
  const collecting = !!pe.request['collect-ref']
  const slines = searchLog?.lines || []
  const searchFailed = slines.length > 0 && slines[slines.length - 1].kind === 'error' && !searching

  // Viewer.js on the hidden gallery; recreate when refs identity changes (skip while open).
  const galleryRef = useRef<HTMLDivElement>(null)
  const viewerRef = useRef<ViewerInst | null>(null)
  const openRef = useRef(false)
  const refsSig = pe.refs.map((r) => r.id).join(',')
  useEffect(() => {
    if (openRef.current) return
    let cancelled = false
    loadScript('/vendor/viewer.min.js')
      .then(() => {
        if (cancelled || !galleryRef.current) return
        const W = window as unknown as { Viewer?: ViewerCtor }
        if (!W.Viewer) return
        if (viewerRef.current) {
          try {
            viewerRef.current.destroy()
          } catch {
            /* noop */
          }
          viewerRef.current = null
        }
        viewerRef.current = new W.Viewer(galleryRef.current, {
          navbar: true,
          title: false,
          transition: false,
          keyboard: true,
          shown() {
            openRef.current = true
          },
          hidden() {
            openRef.current = false
          },
        })
      })
      .catch(() => {})
    return () => {
      cancelled = true
    }
  }, [refsSig])

  const toggleRef = (id: string) => {
    const i = pe.selectedRefs.indexOf(id)
    if (i >= 0) pe.selectedRefs.splice(i, 1)
    else pe.selectedRefs.push(id)
    post('/api/explore', { selectedRefs: pe.selectedRefs })
    force()
  }
  const removeRef = (id: string) => {
    pe.refs = pe.refs.filter((r) => r.id !== id)
    pe.selectedRefs = pe.selectedRefs.filter((x) => x !== id)
    post('/api/explore', { removeRef: id })
    toast('已删除该参考')
    force()
  }
  const searchRefs = () => {
    pe.request = { ...pe.request, 'search-refs': { kind: 'search-refs' } }
    const kws = pe.searchPlan?.keywords?.length ? pe.searchPlan.keywords : pe.stylePrefs
    post('/api/explore', { request: { kind: 'search-refs', keywords: kws, product: '' } })
    toast(pe.stylePrefs.length ? '已请 Agent 去 Dribbble 找参考（累积）' : '已请 Agent 按产品需求自己定方向找参考')
    force()
  }
  const collectRef = () => {
    const u = collectUrl.trim()
    if (!u) {
      toast('先贴一个参考链接')
      return
    }
    pe.request = { ...pe.request, 'collect-ref': { kind: 'collect-ref' } }
    post('/api/explore', { request: { kind: 'collect-ref', url: u } })
    toast('已让 Agent 采集这个链接的参考')
    force()
  }
  const moreLikeRef = (id: string) => {
    const r = pe.refs.find((x) => x.id === id)
    if (!r) return
    if (pe.request['search-refs']) {
      toast('正在找参考，等这轮结束再来')
      return
    }
    pe.request = { ...pe.request, 'search-refs': { kind: 'search-refs' } }
    post('/api/explore', { request: { kind: 'search-refs', keywords: pe.stylePrefs, product: '', seedRef: { file: r.file, title: r.title || '', source: r.source || '' } } })
    toast('已让 Agent 找更多类似这张风格的参考')
    force()
  }
  const zoomRef = (id: string) => {
    const idx = pe.refs.findIndex((r) => r.id === id)
    if (idx < 0 || !viewerRef.current) {
      toast('图片查看器未就绪，稍后再试')
      return
    }
    viewerRef.current.view(idx)
  }
  const disStyle = (b: boolean) => (b ? ({ background: 'var(--dash)', cursor: 'not-allowed' } as const) : undefined)

  return (
    <div className="card">
      <h2>
        找参考 <span className="hint">Agent 找 / 你贴链接 → 挑选（喂给③首图）</span>
      </h2>
      {/* 搜索关键词：始终可见、可编辑；进入②时 AI 据市场调研自动拟几个预设，用户可增删 */}
      <div className="kw-box">
        <div className="kw-head">
          <b>搜索关键词</b>
          <span className="hint">据市场调研生成、可自由增删——就是用来找参考的词；不知填啥就等 AI 自动拟</span>
        </div>
        <div className="kw-chips">
          {planKw.map((k) => (
            <span key={k} className="kw-chip">{k}<i onClick={() => removeKw(k)} title="移除">×</i></span>
          ))}
          <input
            className="kw-input"
            value={kwInput}
            onChange={(ev) => setKwInput(ev.target.value)}
            onKeyDown={(ev) => { if (ev.key === 'Enter') { ev.preventDefault(); addKw(kwInput) } }}
            onBlur={() => addKw(kwInput)}
            placeholder={planKw.length ? '+ 加关键词，回车' : (suggesting ? 'AI 正在据调研拟关键词…' : '+ 输入关键词，回车（或等 AI 据调研自动拟）')}
          />
        </div>
        {pe.searchPlan?.basis && <div className="kw-basis">依据：{pe.searchPlan.basis}</div>}
        <div className="wz-tags" style={{ marginTop: 8 }}>
          {STAGE_TAGS.map((t) => (
            <span key={t} className={'wz-tag' + (planKw.includes(t) ? ' on' : '')} onClick={() => (planKw.includes(t) ? removeKw(t) : addKw(t))}>
              {t}
            </span>
          ))}
        </div>
      </div>
      <button className="btn" style={{ marginTop: 14, ...(disStyle(searching) || {}) }} disabled={searching} onClick={searchRefs}>
        🔍 {pe.refs.length ? '按这些关键词再找一批' : '按这些关键词找参考'}
      </button>
      {pe.refs.length > 0 && (
        <span className="hint" style={{ marginLeft: 10 }}>已选 {pe.selectedRefs.length}</span>
      )}
      <div style={{ marginTop: 12, display: 'flex', gap: 8, alignItems: 'center' }}>
        <input
          className="wz-input"
          style={{ flex: 1, maxWidth: 'none' }}
          value={collectUrl}
          onChange={(ev) => setCollectUrl(ev.target.value)}
          placeholder="或贴一个参考链接（Dribbble/作品页/图片），Agent 抠出里面的设计图采集进来（普通网站则整页截图）"
        />
        <button className="btn ghost" style={{ whiteSpace: 'nowrap', ...(disStyle(collecting) || {}) }} disabled={collecting} onClick={collectRef}>
          ＋ 采集链接
        </button>
      </div>
      <div
        className={'wz-drop' + (dragOver ? ' over' : '')}
        onDragOver={(ev) => { ev.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(ev) => { ev.preventDefault(); setDragOver(false); uploadFiles(Array.from(ev.dataTransfer.files)) }}
      >
        🖼️ 把图片拖到这里，或在本页 ⌘/Ctrl+V 粘贴 —— 手动加参考（加速 & 注入你的品味）
      </div>
      {collecting && <div className="wz-aibox" style={{ marginTop: 10 }}>✦ Agent 正在打开并采集你贴的链接…</div>}
      {searchFailed && (
        <div className="wz-aibox" style={{ marginTop: 12, borderColor: '#e0b4b4', background: '#fdf4f4', color: '#b3403a' }}>
          ❌ 访问失败 / 没拿到参考（可能 Dribbble 打不开或被拦截）。点上面「找参考」重试即可。
        </div>
      )}
      {pe.refs.length ? (
        <>
          <div className="wz-refgrid" style={{ marginTop: 14 }}>
            {pe.refs.map((r) => {
              const on = pe.selectedRefs.includes(r.id)
              return (
                <div key={r.id} className={'wz-ref' + (on ? ' on' : '')} onClick={() => toggleRef(r.id)}>
                  {on && <div className="rpick on" title="已选（点卡片可取消）">✓ 已选</div>}
                  <div className="wz-del" title="删除这张参考" onClick={(ev) => { ev.stopPropagation(); removeRef(r.id) }}>✕</div>
                  <div className="rthumb">
                    <img src={refUrl(r.file)} loading="lazy" />
                  </div>
                  <div className="rbar">
                    <span className="rcap" title={r.desc || r.title || ''}>{r.title || '参考'}</span>
                    {r.desc && <span className="rdesc" title={r.desc}>{r.desc}</span>}
                    <span className="ract">
                      <button className="rbtn" title="放大查阅（缩放 / 平移 / 上一张下一张）" onClick={(ev) => { ev.stopPropagation(); zoomRef(r.id) }}>
                        🔍 放大
                      </button>
                      {r.source && (
                        <a className="rbtn" title="打开源链接看原帖" href={r.source} target="_blank" rel="noopener" onClick={(ev) => ev.stopPropagation()}>
                          🔗 源
                        </a>
                      )}
                      <button className="rbtn" title="结合需求，找更多类似这张风格的参考" onClick={(ev) => { ev.stopPropagation(); moreLikeRef(r.id) }}>
                        ＋ 类似
                      </button>
                    </span>
                  </div>
                </div>
              )
            })}
          </div>
          <div id="refs-viewer" ref={galleryRef} style={{ display: 'none' }}>
            {pe.refs.map((r) => (
              <img key={r.id} src={refUrl(r.file)} alt={r.title || '参考'} />
            ))}
          </div>
        </>
      ) : searching ? (
        <div className="wz-aibox" style={{ marginTop: 14 }}>✦ Agent 正在 Dribbble 找参考、下载高清原图，完成后自动出现…</div>
      ) : (
        <div className="wz-aibox" style={{ marginTop: 14 }}>选好风格方向点「找参考」，Agent 去 Dribbble 找图、下载高清原图放进项目。<b>不选也行（零输入）</b>，Agent 会读产品需求自己推断方向。</div>
      )}
    </div>
  )
}
