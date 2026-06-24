// ⑤ 圈选/改图 overlay. Draw normalized 0-1 boxes; feedback mode (per-box prompt → inbox + optional ⑥ rerun)
// vs redraw mode (shared instr; box=inpaint, no-box+stage3=gen-heroes baseImage, no-box+else=/api/redraw).
// The feedback string format + 3 redraw routing paths are kept byte-identical (critic risk).
import { useEffect, useReducer, useRef, useState } from 'react'
import { usePreview, closePreview, useChannel, toast } from '../store'
import { post, artUrl } from '../lib'
import { IcX } from '../icons'
import type { ExplorePayload } from '../types'

interface Box {
  x: number
  y: number
  w: number
  h: number
  text: string
}

export function PreviewOverlay() {
  const pv = usePreview()
  const explore = useChannel<ExplorePayload>('explore')
  const [, force] = useReducer((x: number) => x + 1, 0)
  const boxes = useRef<Box[]>([])
  const [instr, setInstr] = useState('')
  const stageRef = useRef<HTMLDivElement>(null)
  const draftRef = useRef<HTMLDivElement>(null)

  // reset on open / target change
  useEffect(() => {
    boxes.current = []
    setInstr('')
    force()
  }, [pv?.file, pv?.mode])

  // Esc closes
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') closePreview()
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [])

  // box drawing (normalized 0-1, toFixed(4) on wire; <0.02 = mis-tap)
  useEffect(() => {
    const stage = stageRef.current
    if (!stage || !pv) return
    let drawing = false, sx = 0, sy = 0
    const frac = (e: PointerEvent) => {
      const r = stage.getBoundingClientRect()
      return { x: Math.min(1, Math.max(0, (e.clientX - r.left) / r.width)), y: Math.min(1, Math.max(0, (e.clientY - r.top) / r.height)) }
    }
    const draftStyle = (x: number, y: number, w: number, h: number) => {
      const d = draftRef.current
      if (!d) return
      d.style.left = x * 100 + '%'; d.style.top = y * 100 + '%'; d.style.width = w * 100 + '%'; d.style.height = h * 100 + '%'
    }
    const onDown = (e: PointerEvent) => {
      if ((e.target as Element).closest('.pvx')) return
      e.preventDefault()
      const p = frac(e); sx = p.x; sy = p.y; drawing = true
      try { stage.setPointerCapture(e.pointerId) } catch { /* noop */ }
      if (draftRef.current) draftRef.current.style.display = 'block'
      draftStyle(sx, sy, 0, 0)
    }
    const onMove = (e: PointerEvent) => {
      if (!drawing) return
      const p = frac(e)
      draftStyle(Math.min(sx, p.x), Math.min(sy, p.y), Math.abs(p.x - sx), Math.abs(p.y - sy))
    }
    const onUp = (e: PointerEvent) => {
      if (!drawing) return
      drawing = false
      if (draftRef.current) draftRef.current.style.display = 'none'
      const p = frac(e)
      const x = Math.min(sx, p.x), y = Math.min(sy, p.y), w = Math.abs(p.x - sx), h = Math.abs(p.y - sy)
      if (w < 0.02 || h < 0.02) return
      if (pv.mode === 'redraw') {
        const t = (prompt('这块区域要改成什么？（留空＝用下面那句通用描述）') || '').trim()
        boxes.current.push({ x, y, w, h, text: t })
      } else {
        const t = prompt('这块区域有什么问题 / 想怎么改？')
        if (!t || !t.trim()) return
        boxes.current.push({ x, y, w, h, text: t.trim() })
      }
      force()
    }
    stage.addEventListener('pointerdown', onDown)
    stage.addEventListener('pointermove', onMove)
    stage.addEventListener('pointerup', onUp)
    return () => {
      stage.removeEventListener('pointerdown', onDown)
      stage.removeEventListener('pointermove', onMove)
      stage.removeEventListener('pointerup', onUp)
    }
  }, [pv])

  if (!pv) return null

  const postRedraw = (body: Record<string, unknown>, okToast: string) => {
    post('/api/redraw', body)
      .then((r) => r.json())
      .then((j) => {
        if (!j || !j.ok) {
          toast('重绘请求被拒：' + ((j && j.error) || '未知'))
          return
        }
        closePreview()
        toast(okToast)
      })
      .catch(() => toast('重绘请求发送失败，请重试'))
  }

  const doEditImage = () => {
    if (pv.mode !== 'redraw') return
    const { file, stage, pageId, platform } = pv
    const text = instr.trim()
    if (boxes.current.length) {
      // 每个框可带独立描述（按区域分别改）；某框没写就用下面那句通用描述兜底
      const regions = boxes.current.map((b) => ({ x: +b.x.toFixed(4), y: +b.y.toFixed(4), w: +b.w.toFixed(4), h: +b.h.toFixed(4), text: (b.text || '').trim() }))
      if (regions.some((r) => !r.text && !text)) {
        toast('每个框写一句要改成什么（点框上的序号编辑），或在下面写一句通用的')
        return
      }
      const distinct = new Set(regions.map((r) => r.text || text)).size
      postRedraw(
        { stage, file, regions, prompt: text, pageId, platform },
        distinct > 1 ? `🎨 正在按区域逐块重绘（${distinct} 种改法）…完成后作为新版本（原图保留）` : '🎨 正在局部重绘选中区域…完成后作为新版本（原图保留）',
      )
    } else if (stage === 3) {
      if (!text) { toast('写一句要改成什么'); return }
      const selectedRefs = explore?.selectedRefs || []
      post('/api/explore', { selectedRefs, request: { kind: 'gen-heroes', baseImage: file, instruction: text } })
      closePreview()
      toast('🎨 已请 Agent 按这句整图改这张（新版本累积，原图保留）')
    } else {
      if (!text) { toast('写一句要改成什么'); return }
      postRedraw({ stage, file, regions: [], prompt: text, pageId, platform }, '🎨 正在整图按这句改…完成后作为新版本出现在画布（原图保留）')
    }
  }

  const sendFeedback = () => {
    if (!boxes.current.length) {
      toast('先在图上框选区域并写一句意见')
      return
    }
    const regions = boxes.current.map((b, i) => ({ n: i + 1, x: +b.x.toFixed(4), y: +b.y.toFixed(4), w: +b.w.toFixed(4), h: +b.h.toFixed(4), text: b.text }))
    const text =
      `成品预览反馈 @ ${pv.title}（${pv.file}），${regions.length} 处：\n` +
      regions.map((r) => `${r.n}. 区域(左${Math.round(r.x * 100)}% 上${Math.round(r.y * 100)}% 宽${Math.round(r.w * 100)}% 高${Math.round(r.h * 100)}%)：${r.text}`).join('\n')
    post('/api/inbox', { text, type: 'preview-feedback', file: pv.file, regions })
      .then(() => {
        closePreview()
        if (confirm(`已记录 ${regions.length} 处圈选意见。让 Agent 现在就针对性修复这些区域吗？\n（重跑 ⑥ 开发实现、带上你的圈选；⑥ 面板会显示「Agent 进行中」。选"取消"=只进收件箱，Agent 下个检查点再读。）`)) {
          const fixInstr = `用户在成品预览上圈选了以下要改的区域，**针对性只改这些点**（不是从头重做整个阶段），改完跑测试确认无回归：\n${text}`
          post('/api/run-stage', { phase: 6, instruction: fixInstr })
            .then((r) => {
              if (r.status === 409) toast('⑥ Agent 已在进行中——你的圈选已进收件箱，它会读到')
            })
            .catch(() => {})
          toast('已让 Agent 处理你的圈选意见（见 ⑥ 面板「Agent 进行中」）')
        } else {
          toast(`已记 ${regions.length} 处圈选意见进收件箱，Agent 下个检查点会读到`)
        }
      })
      .catch(() => toast('发送失败，请重试'))
  }

  const pvSend = () => (pv.mode === 'redraw' ? doEditImage() : sendFeedback())
  const actionLabel = pv.mode === 'redraw' ? (boxes.current.length ? '🎨 重绘选中区域' : '🎨 整图按这句改') : '发送给 Agent'
  const hint =
    pv.mode === 'redraw'
      ? '框选要改的局部，每个框可单独写一句（框上序号点一下可编辑）；多块不同诉求会按区域逐块改。不框、只写下面一句 = 整图按这句改。结果作为新版本，原图保留。'
      : '拖拽框选有问题的区域 → 填一句意见（可框多处）。发送后 Agent 知道是「哪张图、哪块区域、什么问题」。'

  return (
    <div id="pv-overlay" className="show">
      <div className="pv-head">
        <span id="pv-title">{(pv.mode === 'redraw' ? '编辑这张 · ' : '圈选反馈 · ') + pv.title}</span>
        <span className="x" onClick={closePreview}>
          <IcX /> 关闭
        </span>
      </div>
      <div className="pv-wrap">
        <div className="pv-stage" id="pv-stage" ref={stageRef}>
          <img id="pv-img" src={artUrl(pv.file)} alt="" />
          <div id="pv-boxes">
            {boxes.current.map((b, i) => {
              const short = b.text.length > 18 ? b.text.slice(0, 18) + '…' : b.text
              return (
                <div key={i} className="pv-box" style={{ left: b.x * 100 + '%', top: b.y * 100 + '%', width: b.w * 100 + '%', height: b.h * 100 + '%' }}>
                  <span className="pvn" title={b.text || '点这里给这块写诉求'} onClick={() => { const t = prompt('这块区域要改成什么？', b.text || ''); if (t !== null) { boxes.current[i].text = t.trim(); force() } }}>{b.text ? `${i + 1}. ${short}` : `${i + 1} ✎`}</span>
                  <span className="pvx" title="删除" onClick={() => { boxes.current.splice(i, 1); force() }}>✕</span>
                </div>
              )
            })}
          </div>
          <div id="pv-draft" className="pv-draft" ref={draftRef} />
        </div>
      </div>
      <div className="pv-foot">
        <textarea id="pv-instr" className={'pv-instr' + (pv.mode === 'redraw' ? ' show' : '')} placeholder="写一句要改成什么…" value={instr} onChange={(e) => setInstr(e.target.value)} />
        <button className="btn pv-go" id="pv-action-btn" onClick={pvSend}>{actionLabel}</button>
      </div>
      <div className="pv-hint" id="pv-hint">{hint}</div>
    </div>
  )
}
