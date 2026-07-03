// Home card wall — faithful port of projCard/ghostCard/renderHome.
// React-keyed by project id so unchanged cards (and their cover <img>) are NOT
// recreated on each push → no flicker / no image reload.
import { useState } from 'react'
import { useChannel, openNewModal, openDelete } from '../store'
import { relTime } from '../lib'
import type { Project, Pending, ProjectsPayload } from '../types'

function ProjectCard({ p }: { p: Project }) {
  const broken = p.missing ? '目录缺失' : p.error ? '状态损坏' : ''
  const phases = p.phases || []
  const firstLetter = (p.name || p.id || '?').trim()[0] || '?'
  return (
    <div className={'pcard' + (broken ? ' broken' : '')} onClick={() => { location.href = `/p/${p.id}/` }}>
      <button
        className="pcard-del"
        title="删除项目"
        onClick={(e) => {
          e.stopPropagation()
          openDelete({ id: p.id, name: p.name || p.id, dir: p.dir_label || '' })
        }}
      >
        🗑
      </button>
      {p.cover ? <img className="cover" src={p.cover} loading="lazy" /> : <div className="cover ph">{firstLetter}</div>}
      <div className="pbody">
        <div className="pname">
          {p.name || p.id}{' '}
          {p.working && <span className="badge-working">进行中</span>}
          {p.health?.url && (
            <span className="hdot">
              <span className={'hdot-d ' + (p.health.ok ? 'ok' : 'bad')} />
              {p.health.ok ? '在线' : '离线'}
              {p.health.ms != null ? ' ' + p.health.ms + 'ms' : ''}
            </span>
          )}
        </div>
        <div className="pdir mono">
          {p.dir_label || ''}
          {broken && (
            <>
              {' · '}
              <span className="warntag">{broken}</span>
            </>
          )}
        </div>
        <div className="segs">
          {phases.map((ph, i) => (
            <span key={i} className={'seg ' + ph.status} />
          ))}
        </div>
        <div className="pmeta">
          {p.done ?? 0}/{phases.length || 8} 阶段 · {relTime(p.updated)}
        </div>
      </div>
    </div>
  )
}

function GhostCard({ g }: { g: Pending }) {
  return (
    <div className="pcard ghost">
      <div className="pbody">
        <div className="pname">{g.name}</div>
        <div className="pdir">{g.brief || ''}</div>
        <div className="gtag">待 CLI 接单</div>
      </div>
    </div>
  )
}

export function Home() {
  const data = useChannel<ProjectsPayload>('projects')
  const [archOpen, setArchOpen] = useState(false)
  const projects = data?.projects || []
  const act = projects.filter((p) => !p.archived)
  const arch = projects.filter((p) => p.archived)
  const pending = data?.pending || []
  return (
    <div className="page on">
      <div className="topbar">
        <span className="ttl">总览</span>
        <div className="right">
          <button className="btn sm" onClick={openNewModal}>
            ＋ 新建项目
          </button>
        </div>
      </div>
      <div id="home-scroll">
        <div className="home-h1">我的项目</div>
        <div className="home-sub">从想法到上线，每个项目的全过程都在这里。</div>
        <div className="grid" id="proj-grid">
          {act.length || pending.length ? (
            <>
              {act.map((p) => (
                <ProjectCard key={p.id} p={p} />
              ))}
              {pending.map((g, i) => (
                <GhostCard key={'g' + i} g={g} />
              ))}
            </>
          ) : (
            <div className="home-empty">还没有项目 — 点「＋ 新建项目」，或在 CLI 里启动 ProductFlow。</div>
          )}
        </div>
        {arch.length > 0 && (
          <div id="arch-sec">
            <div className="arch-toggle" onClick={() => setArchOpen((o) => !o)}>
              已归档 {arch.length} {archOpen ? '▾' : '▸'}
            </div>
            {archOpen && (
              <div className="grid" style={{ marginTop: 14 }}>
                {arch.map((p) => (
                  <ProjectCard key={p.id} p={p} />
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
