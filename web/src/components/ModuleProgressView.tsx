// ⑦ 后端实现 的「成品预览」= 按模块显示后端开发进度（接口实现 X/N + 数据表）。刻意区别于 ⑧ TestProgressView（测试红绿灯）。
// 侧重「开发到哪了」：顶部总接口完成度大进度条 + 每模块接口实现进度条 + 展开看接口/数据表。节点「处理中」脉冲 + 轮询实时刷。
import { useEffect, useMemo, useState } from 'react'
import { PF_BASE, post } from '../lib'
import { useChannel, toast } from '../store'
import type { BackendFlow, BFNode, StateChannel } from '../types'
import { SystemFlowCanvas } from './SystemFlowCanvas'

const EMPTY: BackendFlow = { version: 1, nodes: [], edges: [], pageLinks: [], entry: null, layout: {} }

const ST: Record<string, { label: string; cls: string; dot: string }> = {
  done: { label: '完成', cls: 'done', dot: '#3aa657' },
  doing: { label: '进行中', cls: 'doing', dot: '#3b82f6' },
  needfix: { label: '待修', cls: 'needfix', dot: '#e0574f' },
  todo: { label: '待做', cls: 'todo', dot: '#c4c8cf' },
}
const st = (s?: string) => ST[s || 'todo'] || ST.todo
// 单独重做一个模块：复用 node-change 通道，发一条预设指令让 agent 只重做这一个模块（补真实对接 / 补 key 后真验证 / 复查）
const RERUN_TEXT = (id: string) => `【重做本模块】把「${id}」这个模块重新做一遍并更新状态：①若它有「⚠占位」（真实对接是 dev 占位 / TODO）——补齐真实第三方对接、按官方 API 写完整真适配器，然后 backend-flow set-stub --id ${id} --clear 清占位；②若它「🔑待 key」且 key 现已填——切到真 provider 做真实验证（真发 / 真调）；③复查该模块代码与单元测试。只做这一个模块、别动别的，改完 backend-flow set-status --id ${id} --status done。`
const modId = (m?: string) => (m ? (m.startsWith('module:') ? m : 'module:' + m) : '')
const strip = (id: string, p: string) => (id.startsWith(p) ? id.slice(p.length) : id)

export function ModuleProgressView({ running }: { running?: boolean }) {
  const [bf, setBf] = useState<BackendFlow>(EMPTY)
  const [nonce, setNonce] = useState(0)
  const [missKeyMods, setMissKeyMods] = useState<Set<string>>(new Set())
  const stateCh = useChannel<StateChannel>('state')

  // 拉第三方 key 填写状态：算出「依赖未填 key」的模块——这些模块即便代码完成，真实调用路径（如真发短信）也没验证过
  useEffect(() => {
    let cancelled = false
    fetch(PF_BASE + '/api/product-keys')
      .then((r) => r.json())
      .then((d) => {
        if (cancelled) return
        const s = new Set<string>()
        for (const k of d?.keys || []) {
          if (k.filled) continue
          const kmods = Array.isArray(k.module) ? k.module : k.module ? [k.module] : []
          for (const m of kmods) s.add(String(m).startsWith('module:') ? m : 'module:' + m)
        }
        setMissKeyMods(s)
      })
      .catch(() => {})
    return () => { cancelled = true }
  }, [nonce, stateCh?.log?.length])

  useEffect(() => {
    let cancelled = false
    fetch(PF_BASE + '/api/backend-flow')
      .then((r) => r.json())
      .then((d: BackendFlow) => { if (!cancelled) setBf(d && Array.isArray(d.nodes) ? d : EMPTY) })
      .catch(() => {})
    return () => { cancelled = true }
  }, [nonce, stateCh?.log?.length])

  // 有节点「处理中」或本阶段（⑦）在跑（重做/续跑）时轮询刷新
  useEffect(() => {
    if (!running && !bf.nodes.some((n) => n.proc)) return
    const t = setInterval(() => setNonce((n) => n + 1), 2500)
    return () => clearInterval(t)
  }, [bf, running])

  const mods = useMemo(() => {
    const modules = bf.nodes.filter((n) => n.type === 'module')
    const ifaces = bf.nodes.filter((n) => n.type === 'interface')
    const tables = new Map(bf.nodes.filter((n) => n.type === 'table').map((t) => [t.id, t]))
    const ifTables: Record<string, Set<string>> = {} // 接口 → 它读写的表
    for (const e of bf.edges) {
      if (e.type === 'reads_from' || e.type === 'writes_to') (ifTables[e.from] ||= new Set()).add(e.to)
    }
    return modules.map((m) => {
      const its = ifaces.filter((i) => modId(i.module) === m.id)
      const doneN = its.filter((i) => i.status === 'done').length
      const tset = new Set<string>()
      for (const i of its) for (const t of ifTables[i.id] || []) tset.add(t)
      const tbls = [...tset].map((id) => tables.get(id)).filter((t): t is BFNode => !!t)
      return { m, its, doneN, total: its.length, tbls }
    })
  }, [bf])

  const rerunModule = (id: string) => {
    const n = bf.nodes.find((x) => x.id === id)
    const name = n?.name || strip(id, 'module:')
    if (n?.proc) { toast('该模块正在处理中'); return }
    if (!confirm(`单独重做「${name}」模块？\nAgent 会重新做这一个模块（补真实对接 / 补 key 后真验证 / 复查代码），不动其它模块。`)) return
    post('/api/node-change', { node: id, text: RERUN_TEXT(id) })
      .then((r) => { if (r.ok) { toast(`已让 Agent 重做「${name}」`); setNonce((v) => v + 1) } else toast('触发失败，请重试') })
      .catch(() => toast('触发失败，请重试'))
  }

  if (!bf.nodes.length || !mods.length) return null // 无后端流程图（无后端 ⑦ 本就隐藏）→ 不渲染

  const modDone = mods.filter((x) => x.m.status === 'done').length
  const modDoing = mods.filter((x) => x.m.status === 'doing').length
  const modFix = mods.filter((x) => x.m.status === 'needfix').length
  const ifDone = mods.reduce((s, x) => s + x.doneN, 0)
  const ifTotal = mods.reduce((s, x) => s + x.total, 0)
  const pct = ifTotal ? Math.round((ifDone / ifTotal) * 100) : modDone === mods.length ? 100 : 0
  const keyPendN = mods.filter((x) => missKeyMods.has(x.m.id)).length
  const stubN = mods.filter((x) => x.m.stub).length

  return (
    <div className="card">
      <h2>
        成品预览 <span className="hint">后端各模块开发进度 · 接口实现 + 数据</span>
      </h2>
      {running && <div className="mp-rerun">⏳ ⑦ Agent 处理中…各模块状态实时刷新</div>}

      {/* 顶部总览：整体开发完成度——接口实现 X/N 大进度环带（区别于 ⑧ 的 pass/fail 分段条） */}
      <div className="mp-top">
        <div className="mp-top-row">
          <span className="mp-top-pct">{pct}<i>%</i></span>
          <div className="mp-top-meta">
            <div className="mp-top-lbl">接口实现 {ifDone}/{ifTotal}</div>
            <div className="mp-sum">
              {mods.length} 个模块 · <b className="done">{modDone}</b> 完成
              {modDoing > 0 && <> · <b className="doing">{modDoing}</b> 进行中</>}
              {modFix > 0 && <> · <b className="needfix">{modFix}</b> 待修</>}
              {keyPendN > 0 && <span className="mp-keypend"> · 🔑 {keyPendN} 个模块真发路径待 key 验证</span>}
              {stubN > 0 && <span className="mp-stubwarn"> · ⚠ {stubN} 个模块是占位实现（真实对接未完成）</span>}
            </div>
          </div>
        </div>
        <div className="mp-top-bar"><div className="mp-top-fill" style={{ width: pct + '%' }} /></div>
      </div>

      {/* 两层画布：模块 → 接口。节点按状态/异常着色（done绿/doing蓝/needfix红/占位红/待key橙 + 处理中脉冲），点节点弹窗可「重做本模块」或对话说怎么改 */}
      <SystemFlowCanvas bf={bf} pages={[]} mode="progress" missKeyMods={missKeyMods} onRerun={rerunModule} onChanged={() => setNonce((v) => v + 1)} />
    </div>
  )
}
