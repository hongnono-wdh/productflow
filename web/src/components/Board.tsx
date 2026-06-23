// view-board: health line + steps + artifacts gallery + log. Driven by `state` (+ `health`).
import { useEffect, useRef } from 'react'
import type { ReactNode } from 'react'
import { useChannel, openArtifact } from '../store'
import { artUrl, loadScript } from '../lib'
import type { StateChannel, StatePhase, HealthPayload, Artifact } from '../types'
import { DocIcon } from './DocIcon'

function HealthLine() {
  const h = useChannel<HealthPayload>('health')
  if (!h || !h.url) return null
  const ms = h.ms != null ? ` ${h.ms}ms` : ''
  const at = String(h.checked || '').replace(' ', 'T').slice(11, 16)
  return (
    <div className="health-line" id="health-line">
      线上 <span className={'hdot-d ' + (h.ok ? 'ok' : 'bad')} />
      {ms}
      {at ? ' · 检查于 ' + at : ''}
    </div>
  )
}

type ViewerInst = { view: (i: number) => void; destroy: () => void }
type ViewerCtor = new (el: Element, opts: Record<string, unknown>) => ViewerInst

// 产物区：手风琴折叠（按「第几版」分组，单版时就一个「产物」折叠块）+ 图片用 Viewer.js 放大查阅
// （缩放/平移/上一张下一张，和②找参考一致），文档/导图仍走 modal 预览。
function Gallery({ phase }: { phase: StatePhase }) {
  const arts = phase.artifacts
  const imgs = arts.filter((a) => a.type === 'image')
  const imgIdx = new Map<string, number>()
  imgs.forEach((a, k) => imgIdx.set(a.file, k))

  const galleryRef = useRef<HTMLDivElement>(null)
  const viewerRef = useRef<ViewerInst | null>(null)
  const openFlag = useRef(false)
  const sig = imgs.map((a) => a.file + (a.ts || '')).join(',')
  useEffect(() => {
    if (openFlag.current) return
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
            openFlag.current = true
          },
          hidden() {
            openFlag.current = false
          },
        })
      })
      .catch(() => {})
    return () => {
      cancelled = true
    }
  }, [sig])

  const openArt = (a: Artifact) => {
    if (a.type === 'image') {
      const idx = imgIdx.get(a.file)
      if (idx != null && viewerRef.current) {
        viewerRef.current.view(idx)
        return
      }
    }
    openArtifact(artUrl(a.file, a.ts), a.title, a.type)
  }

  if (!arts.length) return <div className="empty">本阶段还没有产物。</div>

  // 按版本（阶段第几代）分组：单版 → 一个「产物」折叠块；多版 → 第N版各一块（最新展开、旧版收起）
  const byVer = new Map<number, Artifact[]>()
  for (const a of arts) {
    const v = a.version || 1
    const list = byVer.get(v) || []
    list.push(a)
    byVer.set(v, list)
  }
  const versions = [...byVer.keys()].sort((x, y) => y - x)
  const single = versions.length <= 1

  return (
    <>
      {versions.map((v, vi) => {
        const list = byVer.get(v)!
        return (
          <details key={v} className="art-acc" open={vi === 0}>
            <summary>{single ? `产物（${list.length}）` : `第 ${v} 版（${list.length} 个）`}</summary>
            <div className="gallery">
              {list.map((a) => (
                <div key={a.file} className="art" onClick={() => openArt(a)}>
                  {a.type === 'image' ? (
                    <img src={artUrl(a.file, a.ts)} loading="lazy" />
                  ) : (
                    <div className="ic">
                      <DocIcon type={a.type} />
                    </div>
                  )}
                  <div className="cap">{a.title}</div>
                </div>
              ))}
            </div>
          </details>
        )
      })}
      <div className="art-viewer" ref={galleryRef} style={{ display: 'none' }}>
        {imgs.map((a) => (
          <img key={a.file} src={artUrl(a.file, a.ts)} alt={a.title} />
        ))}
      </div>
    </>
  )
}

export function Board({ phase, state, stageExtra }: { phase: StatePhase; state: StateChannel; stageExtra: ReactNode }) {
  return (
    <div id="view-board">
      <HealthLine />
      <div className="wrap">
        <main>
          <div id="stage-extra">{stageExtra}</div>
          <div className="card">
            <h2 id="phase-title">
              {phase.name} <span className="hint">{phase.status === 'done' ? '已完成' : phase.status === 'active' ? '进行中' : '待开始'}</span>
            </h2>
            <ul className="steps" id="steps">
              {phase.steps.map((s) => (
                <li key={s.id}>
                  <span className={'dot ' + s.status} />
                  <span className={'st-title ' + s.status}>{s.title}</span>
                  <span className="hint mono" style={{ marginLeft: 'auto', color: 'var(--faint)', fontSize: 11 }}>
                    {s.id}
                  </span>
                </li>
              ))}
            </ul>
          </div>
          <div className="card">
            <h2>
              产物 <span className="hint">点击预览 · 图片可放大查阅 · 画布可自由布局</span>
            </h2>
            <Gallery phase={phase} />
          </div>
          <div className="card">
            <h2>进展日志</h2>
            <div className="log" id="log">
              {state.log
                .slice(-60)
                .reverse()
                .map((l, i) => (
                  <div key={i} className="row">
                    <span className="ts mono">{l.ts.slice(5, 16)}</span>
                    <span className="m">{l.msg}</span>
                  </div>
                ))}
            </div>
          </div>
        </main>
      </div>
    </div>
  )
}
