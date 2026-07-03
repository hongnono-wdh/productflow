// P4④ infinite canvas (stage 3 heroes / stage 4 pages). Verbatim transform math from console.html.
// Pan/drag/wheel via addEventListener (wheel passive:false). Drag mutates DOM imperatively,
// commits to layout on pointerup. Layout is per-stage, user-owned: GET on mount, debounced POST,
// flush on stage-change/unmount/beforeunload (the last is NEW — fixes the old drag-then-close loss).
import { useEffect, useReducer, useRef, useState } from 'react'
import { useChannel, toast, openArtifact, openRedraw } from '../store'
import { PF_BASE, post, artUrl, loadScript } from '../lib'
import { IcSpark } from '../icons'
import type { ExplorePayload, ExploreRef, ExploreHero, PagesPayload, Page, PageVersion, CanvasCell, HeroGenLogEntry, AgentLogPayload, WizardPayload } from '../types'

const ITEM_W = 320, CARD_GAP = 44, GRID_COLS = 4, ROW_GAP = 500
const defView = () => ({ x: 60, y: 80, z: 0.7 })
const heroImg = (file: string) => PF_BASE + '/artifacts/' + String(file).replace(/^artifacts\//, '')
// ④ 业务模块架构图（只读树）产物的固定路径——agent 写这里，前端「架构图」模式取它渲染。
const ARCH_MD = 'phase-4/module-arch.mm.md'
// ④ 架构图节点「按类型」配色（非按深度——同类型同色，页面可在任意深度）：
// 产品根 / 一级Tab·入口页(🗂) / 子页面(📄) / 业务模块(🧩) / 功能点(叶子)
const ARCH_TYPE_COLOR: Record<string, string> = {
  root: '#111111', tab: '#1e4fb8', page: '#3a6cc4', module: '#9a5e14', feature: '#7a7a7a',
}
// 类型背景色（浅底胶囊，渲染后在节点文字后插圆角 rect）——结构节点上底更醒目；功能点(叶子)不加底免杂乱
const ARCH_BG: Record<string, string> = {
  root: '#ece9e4', tab: '#dbe6fb', page: '#eaf1fd', module: '#f7ead2', feature: '',
}
// 类型字重（渲染后直接 inline 设到文字 div 上，不靠 markmap color 回调/CSS——它们只作用于连线/圆点，管不到 foreignObject 里的文字）
const ARCH_WEIGHT: Record<string, string> = {
  root: '800', tab: '700', page: '650', module: '550', feature: '400',
}

interface Card {
  id: string
  kind: 'hero' | 'page' | 'ref'
  img?: string
  title?: string
  file?: string
  base?: boolean
  pg?: Page
}

// markmap 全局（vendored，与 Modal.tsx 同源）——④ 业务架构图用它渲染只读树。
type MarkmapGlobal = {
  Transformer: new () => { transform: (md: string) => { root: unknown } }
  Markmap: { create: (el: SVGElement, opts: Record<string, unknown>, root: unknown) => void }
}

// ④「架构图」模式：只读渲染 module-arch.mm.md 为树状思维导图。
// 缩放/平移不交给 markmap，改用和设计稿画板一致的自控 transform（滚轮=以光标为中心缩放、拖动=平移）：
// 在**捕获阶段**拦截滚轮/指针并 stopPropagation，markmap 完全不参与交互，行为与 ③④ 画布统一。
function ArchTree({ nonce }: { nonce: number }) {
  const svgRef = useRef<SVGSVGElement>(null)
  const worldRef = useRef<HTMLDivElement>(null)
  const boxRef = useRef<HTMLDivElement>(null)
  const view = useRef({ x: 0, y: 0, z: 1 })
  const [state, setState] = useState<'loading' | 'empty' | 'ready'>('loading')

  const applyT = () => {
    const v = view.current
    if (worldRef.current) worldRef.current.style.transform = `translate(${v.x}px, ${v.y}px) scale(${v.z})`
  }

  // 渲染 markmap（自带缩放/平移关掉，交给下面自控 transform）
  useEffect(() => {
    let cancelled = false
    ;(async () => {
      setState('loading')
      try {
        const r = await fetch(PF_BASE + '/artifacts/' + ARCH_MD + '?t=' + nonce)
        if (!r.ok) { if (!cancelled) setState('empty'); return }
        const md = (await r.text()).trim()
        if (!md) { if (!cancelled) setState('empty'); return }
        await loadScript('/vendor/d3.min.js')
        await loadScript('/vendor/markmap-lib.js')
        await loadScript('/vendor/markmap-view.js')
        if (cancelled || !svgRef.current) return
        const mm = (window as unknown as { markmap: MarkmapGlobal }).markmap
        const { root } = new mm.Transformer().transform(md)
        svgRef.current.innerHTML = ''
        // 按「类型」分类（不是按深度——一个页面可在任意深度，故靠图标标记）：
        // 🗂=一级Tab/入口页 · 📄=子页面 · 🧩=业务模块 · 无图标叶子=功能点 · 深度0=产品根
        const typeOf = (n: { content?: string; state?: { path?: string } }) => {
          const c = String(n?.content ?? '')
          if (c.includes('🗂')) return 'tab'
          if (c.includes('📄')) return 'page'
          if (c.includes('🧩')) return 'module'
          return String(n?.state?.path ?? '').split('.').length <= 1 ? 'root' : 'feature'
        }
        mm.Markmap.create(
          svgRef.current,
          {
            duration: 0,
            maxWidth: 340,
            paddingX: 18,
            autoFit: true,
            initialExpandLevel: -1,
            zoom: false,
            pan: false,
            color: (n: { content?: string; state?: { path?: string } }) => ARCH_TYPE_COLOR[typeOf(n)],
          },
          root,
        )
        // 再按类型给节点 <g> 打 class（字重）+ 在文字后插圆角背景 rect（醒目的类型底色）。
        // rect 尺寸取 foreignObject 的 x/y/w/h + 内边距，插在 foreignObject 前=垫在文字底下；best-effort。
        try {
          const NS = 'http://www.w3.org/2000/svg'
          svgRef.current.querySelectorAll('g.markmap-node').forEach((g) => {
            const t = g.textContent || ''
            const type = t.includes('🗂') ? 'tab' : t.includes('📄') ? 'page' : t.includes('🧩') ? 'module'
              : g.getAttribute('data-depth') === '0' ? 'root' : 'feature'
            g.classList.add('arch-' + type)
            const fo = g.querySelector('foreignObject')
            if (fo) {
              // 文字配色 + 字重：直接 inline !important 写到 foreignObject 里的文字元素上
              // （markmap 的 color 回调/自带样式只作用于连线和圆点，管不到这里的文字）
              fo.querySelectorAll('div, p, span, a, code').forEach((el) => {
                const s = (el as HTMLElement).style
                s.setProperty('color', ARCH_TYPE_COLOR[type], 'important')
                s.setProperty('font-weight', ARCH_WEIGHT[type], 'important')
              })
              // 背景胶囊：在文字后插圆角 rect（结构节点才上底；功能点无底）
              const bg = ARCH_BG[type]
              if (bg) {
                const x = parseFloat(fo.getAttribute('x') || '0'), y = parseFloat(fo.getAttribute('y') || '0')
                const w = parseFloat(fo.getAttribute('width') || '0'), h = parseFloat(fo.getAttribute('height') || '0')
                const px = 7, py = 1.5
                const rect = document.createElementNS(NS, 'rect')
                rect.setAttribute('x', String(x - px)); rect.setAttribute('y', String(y - py))
                rect.setAttribute('width', String(w + px * 2)); rect.setAttribute('height', String(h + py * 2))
                rect.setAttribute('rx', '7'); rect.setAttribute('fill', bg)
                g.insertBefore(rect, fo)
              }
            }
          })
        } catch { /* noop */ }
        view.current = { x: 0, y: 0, z: 1 }
        applyT()
        if (!cancelled) setState('ready')
      } catch {
        if (!cancelled) setState('empty')
      }
    })()
    return () => { cancelled = true }
  }, [nonce])

  // 自控滚轮缩放 + 拖动平移（与设计稿画板同款手感）；捕获阶段拦截，markmap 不参与
  useEffect(() => {
    const box = boxRef.current
    if (!box) return
    let panning = false, sx = 0, sy = 0, ox = 0, oy = 0, captured = false
    const onWheel = (e: WheelEvent) => {
      e.preventDefault(); e.stopPropagation()
      const r = box.getBoundingClientRect()
      const cx = e.clientX - r.left, cy = e.clientY - r.top
      const v = view.current
      const z2 = Math.min(4, Math.max(0.1, v.z * Math.exp(-e.deltaY * 0.0018)))
      const k = z2 / v.z
      v.x = cx - (cx - v.x) * k
      v.y = cy - (cy - v.y) * k
      v.z = z2
      applyT()
    }
    const onDown = (e: PointerEvent) => {
      if (e.button !== 0) return
      e.stopPropagation()
      panning = true; captured = false
      sx = e.clientX; sy = e.clientY; ox = view.current.x; oy = view.current.y
      box.style.cursor = 'grabbing'
    }
    const onMove = (e: PointerEvent) => {
      if (!panning) return
      if (!captured) { try { box.setPointerCapture(e.pointerId) } catch { /* noop */ } captured = true }
      view.current.x = ox + (e.clientX - sx)
      view.current.y = oy + (e.clientY - sy)
      applyT()
    }
    const onUp = () => { panning = false; box.style.cursor = 'grab' }
    box.addEventListener('wheel', onWheel, { passive: false, capture: true })
    box.addEventListener('pointerdown', onDown, { capture: true })
    box.addEventListener('pointermove', onMove)
    box.addEventListener('pointerup', onUp)
    return () => {
      box.removeEventListener('wheel', onWheel, { capture: true } as EventListenerOptions)
      box.removeEventListener('pointerdown', onDown, { capture: true } as EventListenerOptions)
      box.removeEventListener('pointermove', onMove)
      box.removeEventListener('pointerup', onUp)
    }
  }, [])

  return (
    <div ref={boxRef} className="cv-arch" style={{ position: 'absolute', inset: 0, overflow: 'hidden', cursor: 'grab' }}>
      <div ref={worldRef} style={{ position: 'absolute', left: 0, top: 0, width: '100%', height: '100%', transformOrigin: '0 0' }}>
        <svg ref={svgRef} style={{ width: '100%', height: '100%', display: state === 'ready' ? 'block' : 'none' }} />
      </div>
      {state !== 'ready' && (
        <div className="cv-arch-empty" style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', textAlign: 'center', padding: 40, color: 'var(--dim)' }}>
          {state === 'loading'
            ? '加载业务架构…'
            : '还没有业务架构图 —— 点上方「让 Agent 生成业务架构」，Agent 会读页面地图，按页面视角把每页的功能模块层层拆成一棵只读的树。'}
        </div>
      )}
      {state === 'ready' && (
        <div className="cv-arch-legend">
          {([['tab', '🗂 一级页面'], ['page', '📄 子页面'], ['module', '🧩 业务模块'], ['feature', '· 功能点']] as const).map(([k, label]) => (
            <span key={k} style={{ color: ARCH_TYPE_COLOR[k] }}><i style={{ background: ARCH_BG[k] || '#fff', borderColor: ARCH_TYPE_COLOR[k] }} />{label}</span>
          ))}
        </div>
      )}
    </div>
  )
}

export function Canvas({ stage, product }: { stage: number; product: string }) {
  const explore = useChannel<ExplorePayload>('explore')
  const pagesCh = useChannel<PagesPayload>('pages')
  const stage4Log = useChannel<AgentLogPayload>('agent-log:stage-4')
  const [, force] = useReducer((x: number) => x + 1, 0)
  const [selVer, setSelVer] = useState<Record<string, string>>({}) // 每页当前显示的版本 file（多版本切换，不入库）
  const wizard = useChannel<WizardPayload>('wizard')
  const [platform, setPlatform] = useState<string>('') // ④ 当前查看平台（空=用 wizard.primary）
  const [mode, setMode] = useState<'design' | 'arch'>('design') // ④ 设计稿 / 业务架构图（只读树）模式
  const [archNonce, setArchNonce] = useState(0) // 架构图重取信号（切到架构图 / agent 生成完成时 +1）
  const [pending, setPending] = useState<'pagemap' | 'genall' | 'arch' | null>(null) // 哪个 ④ 按钮触发了本次 stage-4 运行 → loading 显在对的按钮上
  const [genPending, setGenPending] = useState(false) // ③「生成首图」乐观 loading：POST 成功才置，服务端 gen-heroes 槽消失/新首图落地时清

  const cv = useRef<CanvasCell & { loaded: boolean; stage: number }>({ view: defView(), items: {}, notes: [], loaded: false, stage })
  const [isLoaded, setIsLoaded] = useState(false)
  const dirty = useRef(false)
  const saveTimer = useRef<number | null>(null)
  const interacting = useRef(false)
  const vpRef = useRef<HTMLDivElement>(null)
  const worldRef = useRef<HTMLDivElement>(null)
  const hdText = useRef<HTMLTextAreaElement>(null)
  const hdCollapsed = useRef(false)
  const archViewRef = useRef(false) // 供 imperative pan/drag/wheel 读：当前是否 ④架构图视图（是则不做画布平移/拖动）

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
  const pages: Page[] = pagesCh?.pages || []
  const genHero = !!exReq['gen-heroes']
  const genBusy = genHero || genPending   // 服务端在生成 或 刚点了生成（乐观）→ 按钮置「生成中」

  // ② 选中的参考（摆到首图画布上 + 作为「本次参考」默认候选）
  const selRefList: ExploreRef[] = (() => {
    const byId: Record<string, ExploreRef> = {}
    refs.forEach((r) => (byId[r.id] = r))
    return selectedRefs.map((id) => byId[id]).filter(Boolean) as ExploreRef[]
  })()
  // 「本次参考」= 画布上点选、要喂给本次生成的图（文件路径集合）；默认 = ② 选中的参考
  const roundRef = useRef<Set<string> | null>(null)
  if (roundRef.current === null && selRefList.length) roundRef.current = new Set(selRefList.map((r) => r.file))
  const roundSet = roundRef.current || new Set<string>()
  const toggleRound = (file: string) => {
    if (!file) return
    if (!roundRef.current) roundRef.current = new Set()
    if (roundRef.current.has(file)) roundRef.current.delete(file)
    else roundRef.current.add(file)
    force()
  }
  const roundRefCards = (): { file: string; img: string; title: string }[] =>
    Array.from(roundSet).map((file) => {
      const r = refs.find((x) => x.file === file)
      if (r) return { file, img: heroImg(file), title: r.title || '参考' }
      const h = heroes.find((x) => x.file === file)
      return { file, img: heroImg(file), title: h ? h.style || '首图' : '图' }
    })

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
      ? [
          ...selRefList.map((r) => ({ id: 'ref:' + r.id, kind: 'ref' as const, img: heroImg(r.file), title: r.title || '参考', file: r.file })),
          ...heroes.map((h) => ({ id: 'hero:' + h.id, kind: 'hero' as const, img: heroImg(h.file), title: h.style || '首图', file: h.file, base: selectedHero === h.file })),
        ]
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

  // ④ 生成完成（stage4 从「跑」→「停」）→ 让架构图重取一次
  const prevRunning = useRef(false)
  useEffect(() => {
    const running = !!stage4Log?.running
    if (prevRunning.current && !running) { setArchNonce((n) => n + 1); setPending(null) } // 跑完：架构图重取 + 清 loading 归属
    prevRunning.current = running
  }, [stage4Log?.running])

  // ③ 生成首图收尾：服务端 gen-heroes 槽 true→false（完成/失败/超时）或有新首图落地 → 清乐观 loading
  const prevGenHero = useRef(false)
  const prevHeroCount = useRef(heroes.length)
  useEffect(() => {
    if ((prevGenHero.current && !genHero) || heroes.length > prevHeroCount.current) setGenPending(false)
    prevGenHero.current = genHero
    prevHeroCount.current = heroes.length
  }, [genHero, heroes.length])

  // ---- pan / drag / wheel ----
  useEffect(() => {
    const vp = vpRef.current
    if (!vp) return
    let mode: 'pan' | 'item' | null = null
    let sx = 0, sy = 0, ox = 0, oy = 0, dragEl: HTMLElement | null = null, dragId = '', moved = false, captured = false

    const onDown = (e: PointerEvent) => {
      if (e.button !== 0) return
      if (archViewRef.current) return // ④架构图视图：markmap 自管交互，画布不平移/拖动
      const t = e.target as Element
      if (t.closest('textarea') || t.closest('.cv-base') || t.closest('.cv-roundref') || t.closest('.cv-page-del') || t.closest('.cv-del') || t.closest('.cv-plat') || t.closest('.cv-verrow') || t.closest('.cv-regen') || t.closest('.cv-controls') || t.closest('#cv-stagebar') || t.closest('#hero-dialog')) return
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
      if (archViewRef.current) return // ④架构图视图：交给 markmap 自己缩放
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
  // 删整个页面（占位符）—— 连带删全部版本 + 清画布位置
  const removePage = (pg: Page) => {
    const n = (pg.versions || []).filter((v) => v && v.file).length
    if (!confirm(`删除整个页面「${pg.name}」？` + (n ? `将一并删掉它的 ${n} 个设计版本，` : '') + '不可恢复。')) return
    delete cv.current.items['page:' + pg.id]
    post('/api/pages', { action: 'remove', id: pg.id }).then(() => toast('已删除页面「' + pg.name + '」')).catch(() => {})
    force()
  }
  // 删单个设计版本（保留页面占位）
  const delVersion = (pg: Page, v: PageVersion) => {
    if (!confirm(`删除「${pg.name}」的这一版设计稿？页面占位会保留，可以再出新版本。`)) return
    post('/api/pages', { action: 'remove-version', id: pg.id, file: v.file, platform: v.platform || null })
      .then(() => toast('已删除该版本（页面占位保留）'))
      .catch(() => {})
    setSelVer((m) => {
      if (m[pg.id] !== v.file) return m
      const next = { ...m }
      delete next[pg.id]
      return next
    })
  }
  // 点版本 = 切换显示 + 持久为该页当前版本（⑥开发取用）
  const setActive = (pg: Page, file: string) => {
    post('/api/pages', { action: 'set-active', id: pg.id, file }).catch(() => {})
  }
  const dblEdit = (c: Card) => {
    // ③④ 双击 → 改图 overlay（框选=局部重绘 / 不框写一句=整图改）
    if (c.kind === 'hero' && c.file) openRedraw(c.file, c.title || '设计稿', 3, null, '')
    else if (c.kind === 'page' && c.pg) {
      const pg = c.pg
      const all = (pg.versions || []).filter((x) => x && x.file)
      const vs = stage === 4 ? all.filter((x) => (x.platform || 'APP') === plat) : all // 只编辑当前平台正在显示的那一版
      const af = selVer[pg.id] && vs.some((x) => x.file === selVer[pg.id]) ? selVer[pg.id] : vs[0]?.file
      const v = vs.find((x) => x.file === af) || vs[0]
      if (v && v.file) openRedraw(v.file, pg.name, 4, pg.id, v.platform || plat)
    }
  }

  // ---- stagebar actions ----
  const stage4Running = !!stage4Log?.running
  const s4last = (stage4Log?.lines || []).slice(-1)[0]
  const stage4Fail = !stage4Running && !!s4last && s4last.kind === 'error'
  const busy = stage4Running || pending !== null // 有 stage-4 agent 在跑 / 刚点了某按钮（乐观锁）→ 三个按钮都禁用
  const runPageMap = () => {
    if (busy) { toast('Agent 正在跑，稍等'); return }
    setPending('pagemap')
    post('/api/run-stage', { phase: 4, instruction: '重点先做第一步 page-map：读 brief.json / replicate-notes 推断本产品应有的所有页面，逐个 page add 占位（带 --note 写依据，按当前主平台）。先不急着出设计图——用户会逐页点平台格让你生成对应平台版本。' })
      .then((r) => { if (!r.ok) { if (r.status === 409) toast('Agent 已在进行中'); else if (r.status === 428) toast('④ 出图需先配置生图 key（OPENAI_API_KEY），配置后重试'); setPending(null) } }).catch(() => setPending(null))
    toast('已让 Agent 按需求列出页面（完成后页面卡会出现在画布）')
  }
  const genAllPages = () => {
    if (busy) { toast('Agent 正在跑，稍等'); return }
    if (!pages.length) { toast('先「让 Agent 列出页面」'); return }
    if (!confirm(`批量生成全部 ${pages.length} 个页面 ×「所有选定平台」的设计稿（按优先级逐平台，沿用③首图基调）？Agent 会逐平台逐页生成，较花时间。`)) return
    setPending('genall')
    post('/api/run-stage', { phase: 4, instruction: "批量**并发**出图，**覆盖所有选定平台**（别只出主平台、别一页一页串行——openai-image-gen 支持并发 20）：① 读 `.productflow/wizard.json` 的 `platforms`（所有选定平台）与 `priority`（优先级顺序）；**按 priority 逐平台**处理（主平台先，如 APP→PC→H5）。② 对**当前平台**：把页面地图里**每一个还没有该平台设计稿的页面**各写一个 prompt——每页 = 该页内容/功能 + ③ 选定首图的视觉基调（配色/字体气质/质感）+ **该平台**界面描述 + 纯 UI 约束（pure UI, fills the frame edge-to-edge, no background scene, no device frame, front view）。③ 用**一条 gen.py 命令并发生成该平台全部页面**：每页一个 `--prompt`，整条带 `--size <该平台尺寸: APP/H5=1080x2340, PC=1440x1080>` `--concurrency 20` `--model gpt-image-2 --out-dir artifacts/phase-4`。④ 生成完按 gen.py 写的 prompts.json 把每张图映射回对应页面，逐个 `page set <pg-id> --add-version <文件> --platform <该平台>` 关联。⑤ 一个平台出完再做下一个平台，直到所有选定平台都出齐。前端实时显示进度。" })
      .then((r) => { if (!r.ok) { if (r.status === 409) toast('Agent 已在进行中'); else if (r.status === 428) toast('④ 出图需先配置生图 key（OPENAI_API_KEY），配置后重试'); setPending(null) } }).catch(() => setPending(null))
    toast(`已让 Agent 按优先级逐平台批量生成 ${pages.length} 个页面（逐平台逐页完成后平台格变亮）`)
  }
  const genArch = () => {
    if (busy) { toast('Agent 正在跑，稍等'); return }
    if (!pages.length) { toast('先「让 Agent 列出页面」'); return }
    setPending('arch')
    // 专职 agent（服务端 _auto_arch）：判定页面父子 + 模块 → 写 arch.json → `pf_state arch build` 由代码组装带图标+嵌套的树。
    // 不走 run-stage 大 agent，避免规则被稀释；prompt 在服务端。
    post('/api/run-action', { phase: 4, action: 'gen-arch' })
      .then((r) => { if (!r.ok) { if (r.status === 409) toast('Agent 已在进行中'); setPending(null) } }).catch(() => setPending(null))
    toast('已让 Agent 生成业务架构（完成后在「架构图」里看到树）')
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
    if (genBusy) { toast('正在生成，稍等'); return }
    const instruction = (hdText.current?.value || '').trim()
    const usedFiles = Array.from(roundSet)
    const req: Record<string, unknown> = { kind: 'gen-heroes', selectedRefs }
    if (usedFiles.length) req.refFiles = usedFiles
    if (instruction) req.instruction = instruction
    setGenPending(true)   // 乐观：按钮立刻置「生成中」
    post('/api/explore', { selectedRefs, request: req }).then((r) => {
      if (r.ok) {
        if (hdText.current) hdText.current.value = ''   // 成功才清输入框
        toast('已请 Agent 生成首图')
      } else {
        setGenPending(false)   // 没下发成功 → 回滚按钮，别假装在生成
        if (r.status === 428) toast('还没配置生图 key（OPENAI_API_KEY），无法生成首图——配置后重试')
        else toast(`生成请求被拒（HTTP ${r.status}），请重试`)
      }
    }).catch(() => { setGenPending(false); toast('网络错误，生成请求没发出去') })
  }

  const platforms = wizard?.platforms?.length ? wizard.platforms : ['APP']
  const plat = platform || wizard?.primary || platforms[0] || 'APP' // ④ 当前查看平台
  const archView = stage === 4 && mode === 'arch' // ④架构图（只读树）视图
  archViewRef.current = archView // 同步给 imperative pan/drag/wheel
  const empty = cards.length === 0
  const hint =
    stage === 3
      ? '拖拽平移 · 滚轮缩放 · 拖动摆位 · 双击图编辑（框选某块=局部重绘 / 不框写一句=整图改）· 设为基调定方向'
      : archView
        ? '业务模块架构图（只读）· 拖拽/滚轮由导图自带缩放平移 · 内容随「让 Agent 生成业务架构」更新'
        : '拖拽平移 · 滚轮缩放 · 拖动摆位 · 点平台徽章生成/查看该端 · 双击设计稿编辑（框选=局部重绘 / 不框=整图改）'

  return (
    <div id="view-canvas" ref={vpRef} style={{ display: 'block' }}>
      {archView ? (
        <ArchTree nonce={archNonce} />
      ) : (
        <div id="cv-world" ref={worldRef} style={{ transform: `translate(${cv.current.view?.x ?? 60}px, ${cv.current.view?.y ?? 80}px) scale(${cv.current.view?.z ?? 0.7})` }}>
          {cards.map((c) => {
            const pos = cv.current.items[c.id]
            if (!pos) return null
            if (c.kind === 'ref') {
              const on = !!c.file && roundSet.has(c.file)
              return (
                <div key={c.id} className="cv-item ref" data-id={c.id} style={{ left: pos.x, top: pos.y }}>
                  <img src={c.img} loading="lazy" />
                  <div className={'cv-roundref' + (on ? ' on' : '')} title="加入/移出『本次参考』（喂给生成首图）" onClick={() => toggleRound(c.file!)}>
                    {on ? '✓ 本次参考' : '+ 本次参考'}
                  </div>
                  <div className="bar">
                    <span className="ti">参考 · {c.title}</span>
                  </div>
                </div>
              )
            }
            if (c.kind === 'hero') {
              const on = !!c.file && roundSet.has(c.file)
              return (
                <div key={c.id} className={'cv-item' + (c.base ? ' base' : '')} data-id={c.id} style={{ left: pos.x, top: pos.y }} onDoubleClick={() => dblEdit(c)}>
                  <img src={c.img} loading="lazy" />
                  <div className="cv-del" title="删除这张首图" onClick={() => removeHero(c.id.replace(/^hero:/, ''))}>✕</div>
                  <div className={'cv-roundref' + (on ? ' on' : '')} title="把这张已生成首图加入『本次参考』生成变体" onClick={() => toggleRound(c.file!)}>
                    {on ? '✓ 本次参考' : '+ 本次参考'}
                  </div>
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
            const allVersions = (pg.versions || []).filter((v) => v && v.file)
            const versions = stage === 4 ? allVersions.filter((v) => (v.platform || 'APP') === plat) : allVersions // ④按当前平台过滤；缺该平台→占位
            const activeFile = selVer[pg.id] && versions.some((v) => v.file === selVer[pg.id]) ? selVer[pg.id] : versions[0]?.file // 当前显示的版本（限当前平台）
            const shown = versions.find((v) => v.file === activeFile) || versions[0]
            return (
              <div key={c.id} className={'cv-item page-card' + (plat === 'PC' ? ' plat-pc' : '')} data-id={c.id} data-pgid={pg.id} style={{ left: pos.x, top: pos.y }}>
                <div className="cv-page-del" title="删除整个页面（含全部版本）" onClick={() => removePage(pg)}>×</div>
                {shown ? (
                  <div className="pthumb" title="双击编辑这版（框选=局部重绘 / 不框=整图改，结果作新版本）" onDoubleClick={() => dblEdit(c)}>
                    <img src={artUrl(shown.file!)} loading="lazy" />
                  </div>
                ) : (
                  <div className="pthumb ph">{pg.status === 'designing' ? '设计中…' : `${plat} 待设计`}</div>
                )}
                <div className="bar col">
                  <div className="pn">
                    <span className={'pdot ' + (pg.status || 'placeholder')} />
                    {pg.name} <span className="pg-g">{pg.group || ''}</span>
                  </div>
                  {versions.length > 1 && (
                    <div className="cv-verrow">
                      {versions.map((v, i) => {
                        const sel = v.file === activeFile
                        return (
                          <span key={v.file} className={'cv-ver' + (sel ? ' sel' : '')} title={`版本 v${i + 1}（点切换 · 双击放大）`} onClick={() => { setSelVer((m) => ({ ...m, [pg.id]: v.file! })); setActive(pg, v.file!) }} onDoubleClick={(e) => { e.stopPropagation(); openArtifact(artUrl(v.file!), `${pg.name} v${i + 1}`, 'image') }}>
                            v{i + 1}
                            <span className="cv-ver-x" title="删除这一版设计稿（保留页面占位）" onClick={(e) => { e.stopPropagation(); delVersion(pg, v) }}>✕</span>
                          </span>
                        )
                      })}
                    </div>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}

      <div id="cv-stagebar" style={stage === 3 ? { display: 'none' } : undefined}>
        {stage === 3 ? null : (
          <>
            <button className="btn" disabled={busy} style={busy ? { background: 'var(--dash)', cursor: 'not-allowed' } : undefined} onClick={runPageMap}>
              <IcSpark />
              {pending === 'pagemap' || (stage4Running && pending === null) ? 'Agent 设计中…' : '让 Agent 列出页面'}
            </button>
            {pages.length > 0 && mode === 'design' && (
              <button className="btn ghost" disabled={busy} style={busy ? { cursor: 'not-allowed' } : undefined} onClick={genAllPages}>
                <IcSpark />{pending === 'genall' ? '生成中…' : `批量生成全部（${pages.length} 页）`}
              </button>
            )}
            {pages.length > 0 && mode === 'arch' && (
              <button className="btn ghost" disabled={busy} style={busy ? { cursor: 'not-allowed' } : undefined} onClick={genArch} title="让 Agent 读页面地图，按页面视角把每页的功能模块层层拆成一棵只读的业务架构树">
                <IcSpark />{pending === 'arch' ? '生成中…' : '让 Agent 生成业务架构'}
              </button>
            )}
            {pages.length > 0 && mode === 'design' && (
              <button className="btn ghost" onClick={tidyPages} title="按模块分组重新铺成不重叠的整齐网格">
                整理排布
              </button>
            )}
            {pages.length > 0 && (
              <span style={{ display: 'inline-flex', gap: 4, marginLeft: 8, alignItems: 'center' }} title="设计稿：看各页设计稿；架构图：看业务模块架构（只读树）">
                {(['design', 'arch'] as const).map((m) => (
                  <button key={m} className="btn ghost sm" style={m === mode ? { background: 'var(--ink)', color: '#fff' } : undefined} onClick={() => { setMode(m); if (m === 'arch') setArchNonce((n) => n + 1) }}>
                    {m === 'design' ? '设计稿' : '架构图'}
                  </button>
                ))}
              </span>
            )}
            {pages.length > 0 && mode === 'design' && platforms.length > 1 && (
              <span style={{ display: 'inline-flex', gap: 4, marginLeft: 8, alignItems: 'center' }} title="切换查看不同平台的设计稿（缺该平台版本的页面显示占位）">
                <span style={{ color: 'var(--dim)', fontSize: 12 }}>平台</span>
                {platforms.map((p) => (
                  <button key={p} className="btn ghost sm" style={p === plat ? { background: 'var(--ink)', color: '#fff' } : undefined} onClick={() => setPlatform(p)}>
                    {p}
                  </button>
                ))}
              </span>
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

      {empty && !archView && <div id="cv-empty">画布还是空的 — 产物登记后会自动出现在这里</div>}

      {stage === 3 && <HeroDialog roundRefs={roundRefCards()} toggleRound={toggleRound} hdText={hdText} hdCollapsed={hdCollapsed} gen={genBusy} genFailed={!!explore?.heroGenFailed} log={(explore?.heroGenLog as HeroGenLogEntry[]) || []} insertRefCode={insertRefCode} dialogGenerate={dialogGenerate} force={force} />}

      <div className="cv-hint">{hint}</div>
      {!archView && (
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
      )}
    </div>
  )
}

// ---- ③ hero-generation dialog (right-docked) ----
type ViewerInst = { view: (i: number) => void; destroy: () => void }
type ViewerCtor = new (el: Element, opts: Record<string, unknown>) => ViewerInst

function HeroDialog(props: {
  roundRefs: { file: string; img: string; title: string }[]
  toggleRound: (file: string) => void
  hdText: React.RefObject<HTMLTextAreaElement | null>
  hdCollapsed: React.MutableRefObject<boolean>
  gen: boolean
  genFailed: boolean
  log: HeroGenLogEntry[]
  insertRefCode: (code: string) => void
  dialogGenerate: () => void
  force: () => void
}) {
  const { roundRefs, toggleRound, hdText, hdCollapsed, gen, genFailed, log, insertRefCode, dialogGenerate, force } = props
  // Viewer.js on a hidden gallery → 缩略图「🔍 放大」缩放/平移/翻页
  const galleryRef = useRef<HTMLDivElement>(null)
  const viewerRef = useRef<ViewerInst | null>(null)
  const openRef = useRef(false)
  const sig = roundRefs.map((r) => r.file).join(',')
  useEffect(() => {
    if (openRef.current) return
    let cancelled = false
    loadScript('/vendor/viewer.min.js').then(() => {
      if (cancelled || !galleryRef.current) return
      const W = window as unknown as { Viewer?: ViewerCtor }
      if (!W.Viewer) return
      if (viewerRef.current) { try { viewerRef.current.destroy() } catch { /* noop */ } viewerRef.current = null }
      viewerRef.current = new W.Viewer(galleryRef.current, { navbar: true, title: false, transition: false, keyboard: true, shown() { openRef.current = true }, hidden() { openRef.current = false } })
    }).catch(() => {})
    return () => { cancelled = true }
  }, [sig])
  return (
    <div id="hero-dialog" className={'on' + (hdCollapsed.current ? ' collapsed' : '')}>
      <div className="hd-head" onClick={() => { hdCollapsed.current = !hdCollapsed.current; force() }}>
        <IcSpark /> 生成首图 <button className="hd-x" title="折叠/展开">—</button>
      </div>
      <div className="hd-body">
        <div className="hd-sec-t">本次参考 <span className="hd-sec-hint">在画布点图片的「+ 本次参考」加入</span></div>
        <div className="hd-refs">
          {roundRefs.length ? (
            roundRefs.map((r, i) => {
              const code = '图' + (i + 1)
              return (
                <div key={r.file} className="hd-ref">
                  <img src={r.img} title={'点把「' + code + '」插进文字（×移出 / 🔍放大）'} onClick={() => insertRefCode(code)} />
                  <span className="hd-rcode">{code}</span>
                  <span className="hd-rzoom" title="放大查看（缩放/平移/翻页）" onClick={(ev) => { ev.stopPropagation(); viewerRef.current?.view(i) }}>🔍</span>
                  <span className="hd-rdel" title="移出本次参考" onClick={(ev) => { ev.stopPropagation(); toggleRound(r.file) }}>×</span>
                </div>
              )
            })
          ) : (
            <span className="none">在画布上点图片的「+ 本次参考」加入（② 选的参考已自动摆到画布）；不选也能直接生成（按产品需求）</span>
          )}
        </div>
        {roundRefs.length > 0 && <div className="hd-hint">点缩略图把代号插进下面文字（例：主色参考 图1，布局参考 图2）；🔍 放大看、× 移出本次参考</div>}
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
      <div ref={galleryRef} style={{ display: 'none' }}>
        {roundRefs.map((r) => (
          <img key={r.file} src={r.img} alt={r.title} />
        ))}
      </div>
    </div>
  )
}
