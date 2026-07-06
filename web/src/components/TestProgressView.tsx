// ⑧ 测试进度：各模块的「测试状态」（通过 / 挂 / 回修 / 待测）——刻意区别于 ⑦「成品预览」的开发进度（接口实现 X/N 进度条）。
// 侧重「测过了吗、哪挂了」：顶部 pass/fail 分段条 + 每模块状态徽章（色 + 文字双指标，挂的整行标红醒目）。
// 数据同 backend-flow.json：module.status（done=测过通过 / needfix=挂 / todo|doing=待测）+ module.proc（回修中脉冲）。
import { useEffect, useMemo, useState } from 'react'
import { PF_BASE } from '../lib'
import { useChannel } from '../store'
import type { BackendFlow, BFNode, StateChannel } from '../types'

const EMPTY: BackendFlow = { version: 1, nodes: [], edges: [], pageLinks: [], entry: null, layout: {} }

type TState = 'pass' | 'fail' | 'fixing' | 'pending'
const TST: Record<TState, { label: string; dot: string }> = {
  pass: { label: '通过', dot: '#3aa657' },
  fail: { label: '挂了', dot: '#e0574f' },
  fixing: { label: '回修中', dot: '#f0a500' },
  pending: { label: '待测', dot: '#c4c8cf' },
}
// 测试态从独立的 test 字段派生（不复用 status = ⑦ 开发态）：proc → 回修中；test=pass → 通过；test=fail → 挂；未设 → 待测
const tstate = (n: BFNode): TState => (n.proc ? 'fixing' : n.test === 'pass' ? 'pass' : n.test === 'fail' ? 'fail' : 'pending')
const modId = (m?: string) => (m ? (m.startsWith('module:') ? m : 'module:' + m) : '')
const strip = (id: string, p: string) => (id.startsWith(p) ? id.slice(p.length) : id)

export function TestProgressView({ running }: { running?: boolean }) {
  const [bf, setBf] = useState<BackendFlow>(EMPTY)
  const [nonce, setNonce] = useState(0)
  const [open, setOpen] = useState<Record<string, boolean>>({})
  const stateCh = useChannel<StateChannel>('state')

  useEffect(() => {
    let cancelled = false
    fetch(PF_BASE + '/api/backend-flow')
      .then((r) => r.json())
      .then((d: BackendFlow) => { if (!cancelled) setBf(d && Array.isArray(d.nodes) ? d : EMPTY) })
      .catch(() => {})
    return () => { cancelled = true }
  }, [nonce, stateCh?.log?.length])

  // 回修中（proc）或本阶段在跑时轮询刷新
  useEffect(() => {
    if (!running && !bf.nodes.some((n) => n.proc)) return
    const t = setInterval(() => setNonce((n) => n + 1), 2500)
    return () => clearInterval(t)
  }, [bf, running])

  const mods = useMemo(() => {
    const modules = bf.nodes.filter((n) => n.type === 'module')
    const ifaces = bf.nodes.filter((n) => n.type === 'interface')
    return modules.map((m) => ({ m, its: ifaces.filter((i) => modId(i.module) === m.id), ts: tstate(m) }))
  }, [bf])

  if (!bf.nodes.length || !mods.length) return null // 无后端流程图 → 不渲染（无后端项目在此展示前端 E2E 时另说）

  const cnt: Record<TState, number> = { pass: 0, fail: 0, fixing: 0, pending: 0 }
  mods.forEach((x) => cnt[x.ts]++)
  const total = mods.length
  const order: TState[] = ['pass', 'fail', 'fixing', 'pending']

  return (
    <div className="card">
      <h2>
        测试进度 <span className="hint">各模块测试状态 · 通过 / 挂 / 回修 / 待测</span>
      </h2>
      {running && <div className="tp-banner">⏳ ⑧ 测试进行中…挂掉的模块标红，回修完转绿</div>}

      {/* pass/fail 分段总览条——测试特有的"红绿灯"总览，区别于 ⑦ 的实现完成度进度条 */}
      <div className="tp-overbar" title={`通过 ${cnt.pass} · 挂 ${cnt.fail} · 回修 ${cnt.fixing} · 待测 ${cnt.pending}`}>
        {order.map((k) => (cnt[k] > 0 ? <div key={k} className={'tp-seg ' + k} style={{ width: (cnt[k] / total) * 100 + '%' }} /> : null))}
      </div>
      <div className="tp-sum">
        {total} 个模块 · <b className="pass">{cnt.pass}</b> 通过
        {cnt.fail > 0 && <> · <b className="fail">{cnt.fail}</b> 挂</>}
        {cnt.fixing > 0 && <> · <b className="fixing">{cnt.fixing}</b> 回修中</>}
        {cnt.pending > 0 && <> · <b className="pending">{cnt.pending}</b> 待测</>}
      </div>

      <div className="tp-list">
        {mods.map(({ m, its, ts }) => {
          const s = TST[ts]
          const isOpen = !!open[m.id]
          const passN = its.filter((i) => i.status === 'done').length
          return (
            <div key={m.id} className={'tp-row ' + ts + (m.proc ? ' proc' : '')}>
              <div className="tp-head" onClick={() => setOpen((o) => ({ ...o, [m.id]: !o[m.id] }))}>
                <span className="tp-dot" style={{ background: s.dot }} />
                <span className="tp-name">{m.name || strip(m.id, 'module:')}</span>
                <span className="tp-id">{strip(m.id, 'module:')}</span>
                <span className={'tp-badge ' + ts}>{m.proc ? '回修中' : s.label}</span>
                {its.length > 0 && <span className="tp-count">接口 {passN}/{its.length} 通过</span>}
                {its.length > 0 && <span className="tp-caret">{isOpen ? '▾' : '▸'}</span>}
              </div>
              {isOpen && its.length > 0 && (
                <ul className="tp-ifaces">
                  {its.map((i) => {
                    const it = tstate(i)
                    return (
                      <li key={i.id} className={it}>
                        <span className="tp-dot sm" style={{ background: TST[it].dot }} />
                        <span className="tp-if-name">{i.name || strip(i.id, 'api:')}</span>
                        <span className={'tp-if-st ' + it}>{TST[it].label}</span>
                      </li>
                    )
                  })}
                </ul>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
