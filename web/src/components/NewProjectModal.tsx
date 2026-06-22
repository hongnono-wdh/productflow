// New-project wizard: name/slug (autoSlug + CJK random fallback, slugEdited) + platform picker
// (multi-select cards + primary radio + draggable priority) + localStorage draft restore.
import { useEffect, useReducer, useRef } from 'react'
import { useNewModalOpen, closeNewModal, toast } from '../store'
import { IcX } from '../icons'

const PLAT: Record<string, { nm: string; ds: string }> = {
  PC: { nm: 'PC', ds: '面向桌面浏览器的网页应用。' },
  H5: { nm: 'H5', ds: '面向现代浏览器的移动端网页体验。' },
  APP: { nm: 'APP', ds: 'iOS 与 Android 的原生移动应用。' },
}
const KEYS = ['PC', 'H5', 'APP'] as const
const NM_DRAFT_KEY = 'pf-new-project-draft'

interface NM {
  name: string
  slug: string
  slugEdited: boolean
  fb: string
  platforms: Record<string, boolean>
  primary: string
  priority: string[]
}
function freshNm(): NM {
  return { name: '', slug: '', slugEdited: false, fb: 'pf-' + Math.random().toString(36).slice(2, 6), platforms: { PC: true, H5: true, APP: false }, primary: 'PC', priority: ['PC', 'H5', 'APP'] }
}
function loadDraft(): NM | null {
  try {
    const d = JSON.parse(localStorage.getItem(NM_DRAFT_KEY) || 'null')
    if (d && typeof d === 'object') {
      const base = freshNm()
      return Object.assign(base, d, { platforms: Object.assign({ PC: true, H5: true, APP: false }, d.platforms || {}), priority: Array.isArray(d.priority) ? d.priority : base.priority, fb: d.fb || base.fb })
    }
  } catch {
    /* noop */
  }
  return null
}
function autoSlug(s: string): string {
  return String(s || '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '')
}
function deviceIcon(k: string) {
  if (k === 'PC') return <svg width="38" height="38" viewBox="0 0 38 38" fill="none"><rect x="5" y="8" width="28" height="19" rx="2.5" stroke="currentColor" strokeWidth={2} /><path d="M13 32h12M19 27v5" stroke="currentColor" strokeWidth={2} strokeLinecap="round" /></svg>
  if (k === 'H5') return <svg width="38" height="38" viewBox="0 0 38 38" fill="none"><rect x="7" y="6" width="24" height="26" rx="3" stroke="currentColor" strokeWidth={2} /><path d="M7 11h24" stroke="currentColor" strokeWidth={2} /><circle cx="19" cy="28.5" r="1.3" fill="currentColor" /></svg>
  return <svg width="38" height="38" viewBox="0 0 38 38" fill="none"><rect x="11" y="5" width="16" height="28" rx="3" stroke="currentColor" strokeWidth={2} /><path d="M17 29h4" stroke="currentColor" strokeWidth={2} strokeLinecap="round" /></svg>
}

export function NewProjectModal() {
  const open = useNewModalOpen()
  const [, force] = useReducer((x: number) => x + 1, 0)
  const nm = useRef<NM>(freshNm())
  const dragK = useRef<string | null>(null)
  const wasOpen = useRef(false)

  useEffect(() => {
    if (open && !wasOpen.current) {
      const draft = loadDraft()
      nm.current = draft || freshNm()
      force()
      if (draft && (draft.name || draft.slug)) toast('已恢复上次未完成的草稿（可继续填或清空重来）')
    }
    wasOpen.current = open
  }, [open])

  const saveDraft = () => {
    try {
      localStorage.setItem(NM_DRAFT_KEY, JSON.stringify(nm.current))
    } catch {
      /* noop */
    }
  }
  const close = () => {
    saveDraft()
    closeNewModal()
  }
  const reset = () => {
    try {
      localStorage.removeItem(NM_DRAFT_KEY)
    } catch {
      /* noop */
    }
    nm.current = freshNm()
    force()
  }
  const setName = (v: string) => {
    const s = nm.current
    s.name = v
    if (!s.slugEdited) s.slug = autoSlug(v) || (v.trim() ? s.fb : '')
    saveDraft()
    force()
  }
  const setSlug = (v: string) => {
    nm.current.slug = v
    nm.current.slugEdited = true
    saveDraft()
    force()
  }
  const togglePlat = (k: string) => {
    const s = nm.current
    s.platforms[k] = !s.platforms[k]
    if (!s.platforms[s.primary]) s.primary = KEYS.find((x) => s.platforms[x]) || ''
    saveDraft()
    force()
  }
  const setPrimary = (k: string) => {
    nm.current.primary = k
    saveDraft()
    force()
  }
  const onDragOver = (k: string) => {
    const arr = nm.current.priority
    const d = dragK.current
    if (!d || k === d) return
    arr.splice(arr.indexOf(d), 1)
    arr.splice(arr.indexOf(k), 0, d)
    saveDraft()
    force()
  }
  const create = async () => {
    const s = nm.current
    s.priority.sort((a, b) => (a === s.primary ? -1 : b === s.primary ? 1 : 0))
    try {
      const r = await fetch('/api/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: (s.name || '').trim() || '未命名项目', slug: (s.slug || '').trim(), platforms: KEYS.filter((k) => s.platforms[k]), primary: s.primary, priority: s.priority.filter((k) => s.platforms[k]) }),
      })
      const d = await r.json()
      if (d.id) {
        try {
          localStorage.removeItem(NM_DRAFT_KEY)
        } catch {
          /* noop */
        }
        location.href = '/p/' + d.id + '/'
      } else {
        toast('创建失败：' + (d.error || '未知'))
      }
    } catch {
      toast('创建失败')
    }
  }

  if (!open) return null
  const s = nm.current
  const prio = s.priority.filter((k) => s.platforms[k])
  return (
    <div className="modal show" id="new-modal" onClick={(e) => { if (e.target === e.currentTarget) close() }}>
      <div className="box" style={{ maxWidth: 640 }}>
        <div className="bar">
          <span className="mt">新建项目</span>
          <span className="x" onClick={close}>
            <IcX /> 关闭
          </span>
        </div>
        <div id="new-body" style={{ overflow: 'auto', padding: '22px 24px 24px' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            <div>
              <div className="wz-label">项目名称</div>
              <input className="wz-input" id="nm-name" placeholder="例如：咖啡订阅" value={s.name} onChange={(e) => setName(e.target.value)} />
            </div>
            <div>
              <div className="wz-label">项目标识 <span style={{ color: 'var(--dim)', fontWeight: 400 }}>(目录名)</span></div>
              <input className="wz-input" id="nm-slug" placeholder="如 coffee-sub（留空按名生成）" value={s.slug} onChange={(e) => setSlug(e.target.value)} />
              <div className="wz-hint2" style={{ marginTop: 6 }}>作目录名/链接，小写英文/数字/连字符。中文名会自动占位，建议改成有意义的英文名。</div>
            </div>
          </div>
          <div className="wz-sec" style={{ marginTop: 24 }}>
            <div className="wz-label">输出平台</div>
            <div className="wz-hint2">选择平台，可多选。</div>
            <div className="wz-platforms">
              {KEYS.map((k) => (
                <div key={k} className={'wz-pcard' + (s.platforms[k] ? ' on' : '')} onClick={() => togglePlat(k)}>
                  <div className="wz-check">✓</div>
                  <div className="pico">{deviceIcon(k)}</div>
                  <div className="pnm">{PLAT[k].nm}</div>
                  <div className="pds">{PLAT[k].ds}</div>
                </div>
              ))}
            </div>
          </div>
          <div className="wz-sec" style={{ marginTop: 22, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
            <div>
              <div className="wz-label">主平台</div>
              <div className="wz-primary">
                {KEYS.map((k) => {
                  const dis = !s.platforms[k]
                  return (
                    <div key={k} className={'wz-pr' + (s.primary === k ? ' on' : '')} style={dis ? { opacity: 0.4, pointerEvents: 'none' } : undefined} onClick={() => setPrimary(k)}>
                      <span className="rdo" />
                      {k}
                    </div>
                  )
                })}
              </div>
            </div>
            <div>
              <div className="wz-label">优先级</div>
              <div className="wz-prio" id="nm-prio">
                {prio.map((k, i) => (
                  <div
                    key={k}
                    className="wz-prio-item"
                    draggable
                    data-prio={k}
                    onDragStart={(e) => { dragK.current = k; ;(e.currentTarget as HTMLElement).classList.add('dragging') }}
                    onDragEnd={(e) => { ;(e.currentTarget as HTMLElement).classList.remove('dragging'); dragK.current = null }}
                    onDragOver={(e) => { e.preventDefault(); onDragOver(k) }}
                  >
                    <span className="grip">⠿</span>
                    <span className="idx">{i + 1}</span>
                    <span className="pnm2">{k}</span>
                    {s.primary === k && <span className="main-tag">主平台</span>}
                  </div>
                ))}
              </div>
            </div>
          </div>
          <div className="wz-actions" style={{ marginTop: 24, display: 'flex', gap: 12, alignItems: 'center' }}>
            <button className="btn ghost sm" onClick={reset}>清空重填</button>
            <div style={{ marginLeft: 'auto', display: 'flex', gap: 12 }}>
              <button className="btn ghost" onClick={close}>取消</button>
              <button className="btn" onClick={create}>创建项目 →</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
