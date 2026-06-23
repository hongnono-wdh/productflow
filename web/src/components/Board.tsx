// view-board: health line + steps + artifacts gallery + log. Driven by `state` (+ `health`).
import type { ReactNode } from 'react'
import { useChannel, openArtifact } from '../store'
import { artUrl } from '../lib'
import type { StateChannel, StatePhase, HealthPayload } from '../types'
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
              产物 <span className="hint">点击预览 · 画布可自由布局</span>
            </h2>
            <div className="gallery" id="gallery">
              {phase.artifacts.length ? (
                phase.artifacts.map((a, i) => (
                  <div key={i} className="art" onClick={() => openArtifact(artUrl(a.file, a.ts), a.title, a.type)}>
                    <span className="art-ver" title={`第 ${a.version || 1} 版（每次重做本阶段 +1）`}>v{a.version || 1}</span>
                    {a.type === 'image' ? (
                      <img src={artUrl(a.file, a.ts)} loading="lazy" />
                    ) : (
                      <div className="ic">
                        <DocIcon type={a.type} />
                      </div>
                    )}
                    <div className="cap">{a.title}</div>
                  </div>
                ))
              ) : (
                <div className="empty">本阶段还没有产物。</div>
              )}
            </div>
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
