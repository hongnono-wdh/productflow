// P4④ infinite canvas (stage 3 heroes / stage 4 pages). Verbatim transform math from console.html.
// Pan/drag/wheel via addEventListener (wheel passive:false). Drag mutates DOM imperatively,
// commits to layout on pointerup. Layout is per-stage, user-owned: GET on mount, debounced POST,
// flush on stage-change/unmount/beforeunload (the last is NEW — fixes the old drag-then-close loss).
import { useEffect, useReducer, useRef, useState } from 'react'
import { useChannel, toast, openArtifact, openRedraw } from '../store'
import { PF_BASE, post, artUrl } from '../lib'
import { IcSpark } from '../icons'
import type { ExplorePayload, ExploreRef, ExploreHero, PagesPayload, Page, CanvasCell, HeroGenLogEntry, AgentLogPayload } from '../types'

const ITEM_W = 320, CARD_GAP = 44, GRID_COLS = 4, ROW_GAP = 500
const PLAT_LIST = ['PC', 'H5', 'APP']
const defView = () => ({ x: 60, y: 80, z: 0.7 })
const heroImg = (file: string) => PF_BASE + '/artifacts/' + String(file).replace(/^artifacts\//, '')

interface Card {
  id: string
  kind: 'hero' | 'page'
  img?: string
  title?: string
  file?: string
  base?: boolean
  pg?: Page
}

export function Canvas({ stage, product }: { stage: number; product: string }) {
  const explore = useChannel<ExplorePayload>('explore')
  const pagesCh = useChannel<PagesPayload>('pages')
  const stage4Log = useChannel<AgentLogPayload>('agent-log:stage-4')
  const [, force] = useReducer((x: number) => x + 1, 0)

  const cv = useRef<CanvasCell & { loaded: boolean; stage: number }>({ view: defView(), items: {}, notes: [], loaded: false, stage })
  const [isLoaded, setIsLoaded] = useState(false)
  const dirty = useRef(false)
  const saveTimer = useRef<number | null>(null)
  const interacting = useRef(false)
  const vpRef = useRef<HTMLDivElement>(null)
  const worldRef = useRef<HTMLDivElement>(null)
  const heroRefOff = useRef<Record<string, boolean>>({})
  const hdText = useRef<HTMLTextAreaElement>(null)
  const hdCollapsed = useRef(false)

  // ---- explore request normalize (single-slot → per-kind) ----
  const exReq: Record<string, unknown> = (() => {
    let r: Record<string, unknown> = (explore?.request as Record<string, unknown>) || {}
    if (r.kind) r = { [r.kind as string]: r }
    return r
  })()
  const heroes: ExploreHero[] = explore?.heroes || []
  const selectedRefs = explore?.selectedRefs || []
  const refs: ExploreRef[] = explore?.refs || []
  const selectedHero = explore?.selectedHero || ''
  const styleSummary = explore?.styleSummary || ''
  const heroGenFailed = !!explore?.heroGenFailed
  const pages: Page[] = pagesCh?.pages || []
  const genHero = !!exReq['gen-heroes']

  // ---- persistence ----
  const apply = () => {
    const v = cv.current.view || defView()
    if (worldRef.current) worldRef.current.style.transform = `translate(${v.x}px, ${v.y}px) scale(${v.z})`
    const z = document.getElementById('cv-zoom')
    if (z) z.textContent = Math.round(v.z * 100) + '%'
  }
  const doSave = () => {
    const st = cv.current.stage
    post('/api/canvas', { stage: String(st), view: cv.current.view, items: cv.current.items, notes: cv.current.notes }).catch(() => {})
  }
  const save = () => {
    dirty.current = true
    if (saveTimer.current) clearTimeout(saveTimer.current)
    saveTimer.current = window.setTimeout(() => {
      dirty.current = false
      doSave()
    }, 600)
  }
  const flush = () => {
    if (!dirty.current) return
    if (saveTimer.current) clearTimeout(saveTimer.current)
    dirty.current = false
    doSave()
  }

  // load layout when stage changes
  useEffect(() => {
    cv.current = { view: defView(), items: {}, notes: [], loaded: false, stage }
    setIsLoaded(false)
    let cancelled = false
    fetch(PF_BASE + '/api/canvas?stage=' + stage)
      .then((r) => (r.ok ? r.json() : {}))
      .then((d: Partial<CanvasCell>) => {
        if (cancelled) return
        cv.current.view = d && d.view ? d.view : defView()
        cv.current.items = (d && typeof d.items === 'object' && d.items) || {}
        cv.current.notes = (d && Array.isArray(d.notes) ? d.notes : []) as unknown[]
        cv.current.loaded = true
        apply()
        setIsLoaded(true) // triggers auto-place once layout is loaded (fixes card-placement race)
      })
      .catch(() => {
        cv.current.loaded = true
        setIsLoaded(true)
      })
    return () => {
      cancelled = true
      flush() // flush layout of the leaving stage
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stage])

  // beforeunload flush (NEW: old code lost a drag if you closed within the 600ms debounce)
  useEffect(() => {
    const h = () => flush()
    window.addEventListener('beforeunload', h)
    return () => window.removeEventListener('beforeunload', h)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // ---- cards ----
  const cards: Card[] =
    stage === 3
      ? heroes.map((h) => ({ id: 'hero:' + h.id, kind: 'hero' as const, img: heroImg(h.file), title: h.style || '首图', file: h.file, base: selectedHero === h.file }))
      : pages.map((pg) => ({ id: 'page:' + pg.id, kind: 'page' as const, pg }))

  // auto-place new cards (after layout loaded; skip while dragging)
  useEffect(() => {
    if (!isLoaded || interacting.current) return
    let placed = cards.filter((c) => cv.current.items[c.id]).length
    let changed = false
    for (const c of cards) {
      if (cv.current.items[c.id]) continue
      const col = placed % GRID_COLS, row = Math.floor(placed / GRID_COLS)
      cv.current.items[c.id] = { x: 40 + col * (ITEM_W + CARD_GAP), y: 40 + row * ROW_GAP }
      placed++
      changed = true
    }
    if (changed) {
      save()
      force()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cards.map((c) => c.id).join(','), isLoaded])

  // apply transform after each render
  useEffect(apply)

  // ---- pan / drag / wheel ----
  useEffect(() => {
    const vp = vpRef.current
    if (!vp) return
    let mode: 'pan' | 'item' | null = null
    let sx = 0, sy = 0, ox = 0, oy = 0, dragEl: HTMLElement | null = null, dragId = '', moved = false, captured = false

    const onDown = (e: PointerEvent) => {
      if (e.button !== 0) return
      const t = e.target as Element
      if (t.closest('textarea') || t.closest('.cv-base') || t.closest('.cv-page-del') || t.closest('.cv-del') || t.closest('.cv-plat') || t.closest('.cv-controls') || t.closest('#cv-stagebar') || t.closest('#hero-dialog')) return
      const item = t.closest('.cv-item') as HTMLElement | null
      sx = e.clientX; sy = e.clientY; moved = false
      if (item) {
        const id = item.dataset.id || ''
        const p = cv.current.items[id]
        if (!p) { mode = null; return }
        mode = 'item'; dragEl = item; dragId = id; ox = p.x; oy = p.y
        item.classList.add('dragging')
        interacting.current = true
      } else {
        mode = 'pan'; ox = cv.current.view!.x; oy = cv.current.view!.y
        vp.classList.add('panning')
        interacting.current = true
      }
    }
    const onMove = (e: PointerEvent) => {
      if (!mode) return
      const dx = e.clientX - sx, dy = e.clientY - sy
      if (Math.abs(dx) + Math.abs(dy) > 3) moved = true
      if (moved && !captured) { try { vp.setPointerCapture(e.pointerId) } catch { /* noop */ } captured = true }
      if (mode === 'pan') { cv.current.view!.x = ox + dx; cv.current.view!.y = oy + dy; apply() }
      else {
        const p = cv.current.items[dragId]
        p.x = ox + dx / cv.current.view!.z; p.y = oy + dy / cv.current.view!.z
        if (dragEl) { dragEl.style.left = p.x + 'px'; dragEl.style.top = p.y + 'px' }
      }
    }
    const onUp = () => {
      if (mode) save()
      if (dragEl) dragEl.classList.remove('dragging')
      vp.classList.remove('panning')
      mode = null; dragEl = null; captured = false; interacting.current = false
      force()
    }
    const onWheel = (e: WheelEvent) => {
      e.preventDefault()
      const r = vp.getBoundingClientRect()
      if (e.ctrlKey || e.metaKey || Math.abs(e.deltaY) > Math.abs(e.deltaX)) {
        zoomAt(e.clientX - r.left, e.clientY - r.top, Math.exp(-e.deltaY * 0.0018))
      } else {
        cv.current.view!.x -= e.deltaX
        apply(); save()
      }
    }
    vp.addEventListener('pointerdown', onDown)
    vp.addEventListener('pointermove', onMove)
    vp.addEventListener('pointerup', onUp)
    vp.addEventListener('wheel', onWheel, { passive: false })
    return () => {
      vp.removeEventListener('pointerdown', onDown)
      vp.removeEventListener('pointermove', onMove)
      vp.removeEventListener('pointerup', onUp)
      vp.removeEventListener('wheel', onWheel)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const zoomAt = (cx: number, cy: number, factor: number) => {
    const v = cv.current.view!
    const z2 = Math.min(3, Math.max(0.08, v.z * factor))
    const k = z2 / v.z
    v.x = cx - (cx - v.x) * k
    v.y = cy - (cy - v.y) * k
    v.z = z2
    apply(); save()
  }
  const zoomBy = (f: number) => {
    const vp = vpRef.current!.getBoundingClientRect()
    zoomAt(vp.width / 2, vp.height / 2, f)
  }
  const fit = () => {
    const pts = Object.values(cv.current.items).filter((p) => p && typeof p.x === 'number')
    if (!pts.length) return
    let x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9
    for (const p of pts) {
      x0 = Math.min(x0, p.x); y0 = Math.min(y0, p.y - 40)
      x1 = Math.max(x1, p.x + ITEM_W); y1 = Math.max(y1, p.y + 320)
    }
    const vp = vpRef.current!.getBoundingClientRect()
    const z = Math.min(2, Math.max(0.08, Math.min(vp.width / (x1 - x0 + 120), vp.height / (y1 - y0 + 120))))
    cv.current.view = { z, x: (vp.width - (x1 - x0) * z) / 2 - x0 * z, y: (vp.height - (y1 - y0) * z) / 2 - y0 * z }
    apply(); save()
  }

  // ---- click actions ----
  const setHeroBase = (file: string) => {
    post('/api/explore', { selectedHero: file })
    toast('已设为视觉基调')
  }
  const removeHero = (hid: string) => {
    if (!hid) return
    delete cv.current.items['hero:' + hid]
    post('/api/explore', { removeHero: hid })
    toast('已删除该首图')
    force()
  }
  const removePage = (id: string) => {
    post('/api/pages', { action: 'remove', id }).then(() => toast('已删除页面')).catch(() => {})
  }
  const platClick = (pg: Page, plat: string, v?: { file?: string }) => {
    if (v && v.file) {
      openArtifact(artUrl(v.file), plat + ' 版', 'image')
      return
    }
    if (confirm(`让 Agent 生成「${pg.name}」的 ${plat} 版设计？`)) {
      post('/api/pages', { action: 'gen-version', id: pg.id, platform: plat })
      toast(`已让 Agent 生成「${pg.name}」的 ${plat} 版（完成后版本徽章会变亮）`)
    }
  }
  const dblEdit = (c: Card) => {
    // ③④ 双击 → 改图 overlay（框选=局部重绘 / 不框写一句=整图改）
    if (c.kind === 'hero' && c.file) openRedraw(c.file, c.title || '设计稿', 3, null, '')
    else if (c.kind === 'page' && c.pg) {
      const v = (c.pg.versions || []).find((x) => x && x.file)
      if (v && v.file) openRedraw(v.file, c.pg.name, 4, c.pg.id, v.platform || '')
    }
  }

  // ---- stagebar actions ----
  const genHeroes = () => {
    post('/api/explore', { selectedRefs, request: { kind: 'gen-heroes', selectedRefs } })
    toast(selectedRefs.length ? '已请 Agent 按选中参考生成首图（累积）' : '已请 Agent 按产品需求生成首图（累积）')
  }
  const stage4Running = !!stage4Log?.running
  const s4last = (stage4Log?.lines || []).slice(-1)[0]
  const stage4Fail = !stage4Running && !!s4last && s4last.kind === 'error'
  const runPageMap = () => {
    if (stage4Running) { toast('Agent 正在铺页面，稍等'); return }
    post('/api/run-stage', { phase: 4, instruction: '重点先做第一步 page-map：读 brief.json / replicate-notes 推断本产品应有的所有页面，逐个 page add 占位（带 --note 写依据，按当前主平台）。先不急着出设计图——用户会逐页点平台格让你生成对应平台版本。' })
    toast('已让 Agent 按需求列出页面（完成后页面卡会出现在画布）')
  }
  const genAllPages = () => {
    if (stage4Running) { toast('Agent 正在跑，稍等'); return }
    if (!pages.length) { toast('先「让 Agent 列出页面」'); return }
    if (!confirm(`批量生成全部 ${pages.length} 个页面的设计稿（按主平台、各一版，沿用③首图基调）？Agent 会逐页生成，较花时间。其它平台版本可之后点平台格单独生成。`)) return
    post('/api/run-stage', { phase: 4, instruction: "批量**并发**出图（**别一页一页串行**——openai-image-gen 支持并发 20，要一次并发出全部）：① 先把页面地图里**每一个还没有设计稿的页面**各自的 prompt 一次性写好——每页 = 该页内容/功能 + ③ 选定首图的视觉基调（配色/字体气质/质感）+ 主平台界面描述 + 纯 UI 约束（pure UI, fills the frame edge-to-edge, no background scene, no device frame, front view）；主平台读 .productflow/wizard.json 的 primary（缺则从产品定位判断）。② 用**一条 gen.py 命令并发生成**：每页一个 `--prompt`，整条带 `--size <主平台尺寸: APP/H5=1080x2340, PC=1440x1080>` `--concurrency 20` `--model gpt-image-2 --out-dir artifacts/phase-4`。③ 生成完按 gen.py 写的 prompts.json 把每张图映射回对应页面，逐个 `page set <pg-id> --add-version <文件> --platform <主平台>` 关联（登记串行没关系，耗时的生图已并发）。前端实时显示进度。" })
    toast(`已让 Agent 批量生成 ${pages.length} 个页面（逐页完成后平台格会变亮）`)
  }
  const tidyPages = () => {
    const cs = cards.filter((c) => c.kind === 'page')
    if (!cs.length) { toast('还没有页面，先「让 Agent 列出页面」'); return }
    const live = new Set(cs.map((c) => c.id))
    for (const k of Object.keys(cv.current.items)) if (k.startsWith('page:') && !live.has(k)) delete cv.current.items[k]
    const sorted = cs.slice().sort((a, b) => String(a.pg!.group || '').localeCompare(String(b.pg!.group || '')) || String(a.pg!.name || '').localeCompare(String(b.pg!.name || '')))
    sorted.forEach((c, i) => {
      const col = i % GRID_COLS, row = Math.floor(i / GRID_COLS)
      cv.current.items[c.id] = Object.assign(cv.current.items[c.id] || {}, { x: 40 + col * (ITEM_W + CARD_GAP), y: 40 + row * ROW_GAP })
    })
    save(); force(); fit()
    toast(`已整理 ${sorted.length} 个页面（按模块铺成整齐网格）`)
  }
  const addPagePrompt = () => {
    const name = (prompt('页面名称（如 首页 / 定价 / 关于）：') || '').trim()
    if (!name) return
    const group = (prompt('分组（如 核心 / 营销，可留空）：') || '').trim() || '未分组'
    post('/api/pages', { action: 'add', name, group }).then(() => toast('已添加页面占位')).catch(() => {})
  }

  // ---- hero dialog ----
  const selectedRefCards = (): ExploreRef[] => {
    const byId: Record<string, ExploreRef> = {}
    refs.forEach((r) => (byId[r.id] = r))
    return selectedRefs.map((id) => byId[id]).filter(Boolean)
  }
  const insertRefCode = (code: string) => {
    const ta = hdText.current
    if (!ta) return
    const s = ta.selectionStart, e = ta.selectionEnd, v = ta.value
    const needSp = s > 0 && !/[\s，,、。：:（(]$/.test(v.slice(0, s))
    const ins = (needSp ? ' ' : '') + code + ' '
    ta.value = v.slice(0, s) + ins + v.slice(e)
    const pos = s + ins.length
    ta.focus(); ta.setSelectionRange(pos, pos)
  }
  const dialogGenerate = () => {
    if (genHero) { toast('正在生成，稍等'); return }
    const instruction = (hdText.current?.value || '').trim()
    const usedFiles = selectedRefCards().filter((r) => !heroRefOff.current[r.id]).map((r) => r.file)
    const req: Record<string, unknown> = { kind: 'gen-heroes', selectedRefs }
    if (usedFiles.length) req.refFiles = usedFiles
    if (instruction) req.instruction = instruction
    if (hdText.current) hdText.current.value = ''
    post('/api/explore', { selectedRefs, request: req })
    toast('已请 Agent 生成首图')
  }

  const empty = cards.length === 0
  const hint =
    stage === 3
      ? '拖拽平移 · 滚轮缩放 · 拖动摆位 · 双击图编辑（框选某块=局部重绘 / 不框写一句=整图改）· 设为基调定方向'
      : '拖拽平移 · 滚轮缩放 · 拖动摆位 · 点平台徽章生成/查看该端 · 双击设计稿编辑（框选=局部重绘 / 不框=整图改）'

  return (
    <div id="view-canvas" ref={vpRef} style={{ display: 'block' }}>
      <div id="cv-world" ref={worldRef} style={{ transform: `translate(${cv.current.view?.x ?? 60}px, ${cv.current.view?.y ?? 80}px) scale(${cv.current.view?.z ?? 0.7})` }}>
        {cards.map((c) => {
          const pos = cv.current.items[c.id]
          if (!pos) return null
          if (c.kind === 'hero') {
            return (
              <div key={c.id} className={'cv-item' + (c.base ? ' base' : '')} data-id={c.id} style={{ left: pos.x, top: pos.y }} onDoubleClick={() => dblEdit(c)}>
                <img src={c.img} loading="lazy" />
                <div className="cv-del" title="删除这张首图" onClick={() => removeHero(c.id.replace(/^hero:/, ''))}>✕</div>
                <div className="cv-base" title="设为视觉基调" onClick={() => c.file && setHeroBase(c.file)}>
                  {c.base ? '★ 基调' : '设为基调'}
                </div>
                <div className="bar">
                  <span className="ti">{c.title}</span>
                </div>
              </div>
            )
          }
          const pg = c.pg!
          const byPlat: Record<string, { file?: string }> = {}
          for (const v of pg.versions || []) if (v && v.platform) byPlat[v.platform] = v
          const primary = (pg.versions || []).find((v) => v && v.file)
          const platClass = primary && primary.platform === 'PC' ? ' plat-pc' : ''
          return (
            <div key={c.id} className={'cv-item page-card' + platClass} data-id={c.id} data-pgid={pg.id} style={{ left: pos.x, top: pos.y }} onDoubleClick={() => dblEdit(c)}>
              <div className="cv-page-del" title="删除" onClick={() => removePage(pg.id)}>×</div>
              {primary ? (
                <div className="pthumb">
                  <img src={artUrl(primary.file!)} loading="lazy" />
                </div>
              ) : (
                <div className="pthumb ph">{pg.status === 'designing' ? '设计中…' : '待设计'}</div>
              )}
              <div className="bar col">
                <div className="pn">
                  <span className={'pdot ' + (pg.status || 'placeholder')} />
                  {pg.name} <span className="pg-g">{pg.group || ''}</span>
                </div>
                <div className="cv-platrow">
                  {PLAT_LIST.map((p) => {
                    const has = byPlat[p]
                    return (
                      <span key={p} className={'cv-plat' + (has ? ' on' : '')} title={has ? undefined : `点击让 Agent 生成 ${p} 版`} onClick={() => platClick(pg, p, has)}>
                        {p}
                      </span>
                    )
                  })}
                </div>
              </div>
            </div>
          )
        })}
      </div>

      <div id="cv-stagebar">
        {stage === 3 ? (
          <>
            <button className="btn" disabled={genHero} style={genHero ? { background: 'var(--dash)', cursor: 'not-allowed' } : undefined} onClick={genHeroes}>
              <IcSpark />
              {genHero ? 'Agent 正在生成首图…' : heroes.length ? '再生成一批首图（累积）' : '生成首图'}
            </button>
            {genHero ? (
              <span className="sb-guide">✦ Agent 正在生成首图，约 1–2 分钟（期间别重启操作台，会中断生成）…</span>
            ) : heroGenFailed && !heroes.length ? (
              <span className="sb-guide" style={{ color: '#b3403a' }}>❌ 上次生成未完成（被中断或失败），点上面「生成首图」重试</span>
            ) : selectedRefs.length ? (
              <span className="sb-sum">依据 {selectedRefs.length} 张选中参考{styleSummary ? '　·　风格：' + styleSummary : ''}</span>
            ) : (
              <span className="sb-guide">
                没选参考也能生成（Agent 按产品需求来）；想更贴合就去 ② 选几张{' '}
                <button className="btn ghost sm" onClick={() => { location.hash = '#s2' }}>去 ② 找参考</button>
              </span>
            )}
          </>
        ) : (
          <>
            <button className="btn" disabled={stage4Running} style={stage4Running ? { background: 'var(--dash)', cursor: 'not-allowed' } : undefined} onClick={runPageMap}>
              <IcSpark />
              {stage4Running ? 'Agent 设计中…' : '让 Agent 列出页面'}
            </button>
            {pages.length > 0 && (
              <button className="btn ghost" disabled={stage4Running} onClick={genAllPages}>
                <IcSpark />批量生成全部（{pages.length} 页）
              </button>
            )}
            {pages.length > 0 && (
              <button className="btn ghost" onClick={tidyPages} title="按模块分组重新铺成不重叠的整齐网格">
                整理排布
              </button>
            )}
            <button className="btn ghost" onClick={addPagePrompt}>
              ＋ 手动添加
            </button>
            {!selectedHero && (
              <span className="sb-guide">
                建议先在 ③ 定首图基调{' '}
                <button className="btn ghost sm" onClick={() => { location.hash = '#s3' }}>跳到 ③ 首图</button>
              </span>
            )}
            {stage4Fail && <span className="sb-guide" style={{ color: '#b3403a' }}>❌ Agent 中断，点上面重试</span>}
          </>
        )}
      </div>

      {empty && <div id="cv-empty">画布还是空的 — 产物登记后会自动出现在这里</div>}

      {stage === 3 && <HeroDialog refsCards={selectedRefCards()} heroRefOff={heroRefOff} hdText={hdText} hdCollapsed={hdCollapsed} gen={genHero} genFailed={!!explore?.heroGenFailed} log={(explore?.heroGenLog as HeroGenLogEntry[]) || []} insertRefCode={insertRefCode} dialogGenerate={dialogGenerate} force={force} />}

      <div className="cv-hint">{hint}</div>
      <div className="cv-controls">
        <button onClick={() => zoomBy(1.25)} title="放大">
          <svg className="zi" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14" /><path d="M12 5v14" /></svg>
        </button>
        <button onClick={() => zoomBy(0.8)} title="缩小">
          <svg className="zi" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14" /></svg>
        </button>
        <button onClick={fit} title="适配全部">
          <svg className="zi" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round"><path d="M8 3H5a2 2 0 0 0-2 2v3" /><path d="M21 8V5a2 2 0 0 0-2-2h-3" /><path d="M3 16v3a2 2 0 0 0 2 2h3" /><path d="M16 21h3a2 2 0 0 0 2-2v-3" /></svg>
        </button>
        <div id="cv-zoom">{Math.round((cv.current.view?.z ?? 0.7) * 100)}%</div>
      </div>
    </div>
  )
}

// ---- ③ hero-generation dialog (right-docked) ----
function HeroDialog(props: {
  refsCards: ExploreRef[]
  heroRefOff: React.MutableRefObject<Record<string, boolean>>
  hdText: React.RefObject<HTMLTextAreaElement | null>
  hdCollapsed: React.MutableRefObject<boolean>
  gen: boolean
  genFailed: boolean
  log: HeroGenLogEntry[]
  insertRefCode: (code: string) => void
  dialogGenerate: () => void
  force: () => void
}) {
  const { refsCards, heroRefOff, hdText, hdCollapsed, gen, genFailed, log, insertRefCode, dialogGenerate, force } = props
  let codeN = 0
  return (
    <div id="hero-dialog" className={'on' + (hdCollapsed.current ? ' collapsed' : '')}>
      <div className="hd-head" onClick={() => { hdCollapsed.current = !hdCollapsed.current; force() }}>
        <IcSpark /> 生成首图 <button className="hd-x" title="折叠/展开">—</button>
      </div>
      <div className="hd-body">
        <div className="hd-sec-t">本次参考</div>
        <div className="hd-refs">
          {refsCards.length ? (
            refsCards.map((r) => {
              const off = !!heroRefOff.current[r.id]
              const code = off ? '' : '图' + ++codeN
              return (
                <div key={r.id} className={'hd-ref' + (off ? ' off' : '')}>
                  <img src={PF_BASE + '/artifacts/' + r.file.replace(/^artifacts\//, '')} title={off ? '已排除·点右上勾选框加回本次' : '点把「' + code + '」插进文字'} onClick={off ? undefined : () => insertRefCode(code)} />
                  <span className="hd-rcode">{off ? '排除' : code}</span>
                  <span className="hd-rck" title="是否参与本次生成" onClick={() => { if (heroRefOff.current[r.id]) delete heroRefOff.current[r.id]; else heroRefOff.current[r.id] = true; force() }}>
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
                      <rect width="18" height="18" x="3" y="3" rx="2" />
                      {!off && <path d="m9 12 2 2 4-4" />}
                    </svg>
                  </span>
                </div>
              )
            })
          ) : (
            <span className="none">还没选参考——可去 ② 选几张，或直接生成（按产品需求）</span>
          )}
        </div>
        {refsCards.length > 0 && <div className="hd-hint">点缩略图把代号插进下面文字（例：主色参考 图1，布局参考 图2）；点缩略图右上的勾选框切换是否参与本次</div>}
        <div className="hd-sec-t">生成记录</div>
        <div className="hd-log">
          {gen && <div className="hd-gen">✦ Agent 正在生成…（约 1–2 分钟，期间别重启操作台）</div>}
          {!log.length && !gen && (
            <div className="hd-empty">
              {genFailed ? '上次生成未完成，可重试。' : '还没有生成记录。'}
              <br />在下面写想要的首图、点「生成」；每次生成会在这里记下<b>用了哪些参考 + 发了什么文字</b>。
            </div>
          )}
          {log
            .slice()
            .reverse()
            .map((e, i) => (
              <div key={i} className="hd-entry">
                <div className="hd-meta">
                  <span className={'hd-mode' + (e.mode === 'edit' ? ' edit' : '')}>{e.mode === 'edit' ? '改图' : '生成'}</span>
                  <span>{String(e.ts || '').slice(5, 16)}</span>
                  <span>· {(e.refs || []).length} 参考 → {(e.results || []).length} 张</span>
                </div>
                <div className="hd-thumbs">
                  {(e.results || []).slice(0, 6).map((f, j) => (
                    <img key={j} src={PF_BASE + '/artifacts/phase-3/heroes/' + String(f).replace(/^.*\//, '')} />
                  ))}
                </div>
                <div className="hd-prompt">{e.prompt || ''}</div>
              </div>
            ))}
        </div>
      </div>
      <div className="hd-input">
        <textarea ref={hdText} placeholder="描述想要的首图（点上方参考插入 图1/图2，如：主色参考 图1，布局参考 图2）；点中画布某张图=改那张…" />
        <button className="btn hd-go" disabled={gen} style={gen ? { background: 'var(--dash)', cursor: 'not-allowed' } : undefined} onClick={dialogGenerate}>
          <IcSpark />
          {gen ? 'Agent 生成中…' : '生成首图'}
        </button>
      </div>
    </div>
  )
}
