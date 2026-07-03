// ⑤⑥ 第三方 key 卡片（W6 / REQ-3）：列出 ⑤ 识别登记的产品级第三方 key 需求 + 填写状态，
// 让用户在页面上填值。需求来自 GET /api/product-keys（product-keys.json）；填值复用
// POST /api/deploy-creds（同 ~/.productflow/secrets/ 存储，不进 git）。无需求则整卡不显示。
import { useEffect, useState } from 'react'
import { PF_BASE, post } from '../lib'
import { toast } from '../store'

type PKey = { key: string; desc: string; module?: string | null; filled: boolean; masked: string }

export function ProductKeysCard() {
  const [keys, setKeys] = useState<PKey[]>([])
  const [vals, setVals] = useState<Record<string, string>>({}) // key → 输入中的值；含该键即"正在编辑"
  const [nonce, setNonce] = useState(0)

  useEffect(() => {
    let cancelled = false
    fetch(PF_BASE + '/api/product-keys')
      .then((r) => r.json())
      .then((d) => { if (!cancelled) setKeys(Array.isArray(d.keys) ? d.keys : []) })
      .catch(() => {})
    return () => { cancelled = true }
  }, [nonce])

  const save = (k: string) => {
    const v = (vals[k] || '').trim()
    if (!v) { toast('先填入 key 值'); return }
    post('/api/deploy-creds', { creds: { [k]: v } })
      .then((r) => {
        if (!r.ok) { toast('保存失败，请重试'); return }
        toast(`已保存 ${k}（本机 secrets，不进 git / 不外传）`)
        setVals((s) => { const n = { ...s }; delete n[k]; return n })
        setNonce((n) => n + 1)
      })
      .catch(() => toast('保存失败，请重试'))
  }

  if (!keys.length) return null // ⑤ 未识别到第三方 key 需求 → 整卡不显示
  const doneCount = keys.filter((k) => k.filled).length

  return (
    <div className="card">
      <h2>第三方 key <span className="hint">产品用到的第三方服务凭证（{doneCount}/{keys.length} 已填 · 存本机 secrets、不进 git）</span></h2>
      <div className="wz-hint2" style={{ margin: '0 0 10px' }}>⑤ 从接口 / 数据来源识别、需要你填的第三方 key。值只存本机 <code>~/.productflow/secrets/</code>，Agent 开发时作为环境变量取用。</div>
      {keys.map((k) => {
        const editing = vals[k.key] !== undefined
        return (
          <div key={k.key} style={{ display: 'flex', gap: 10, alignItems: 'center', marginTop: 10, flexWrap: 'wrap' }}>
            <div style={{ minWidth: 200 }}>
              <code>{k.key}</code>{k.module ? <span style={{ color: 'var(--dim)', fontSize: 12 }}> · {k.module}</span> : null}
              {k.desc ? <div style={{ color: 'var(--dim)', fontSize: 12 }}>{k.desc}</div> : null}
            </div>
            {k.filled && !editing ? (
              <span style={{ fontSize: 13, color: '#3a8a4a' }}>
                ✓ 已填 <code>{k.masked}</code>　<a style={{ cursor: 'pointer', color: '#3b82f6' }} onClick={() => setVals((s) => ({ ...s, [k.key]: '' }))}>改</a>
              </span>
            ) : (
              <>
                <input className="wz-input" style={{ flex: 1, minWidth: 220 }} type="password" placeholder={`填入 ${k.key} 的值`}
                  value={vals[k.key] || ''} onChange={(e) => setVals((s) => ({ ...s, [k.key]: e.target.value }))} />
                <button className="btn" onClick={() => save(k.key)}>保存</button>
                {k.filled ? <button className="btn ghost" onClick={() => setVals((s) => { const n = { ...s }; delete n[k.key]; return n })}>取消</button> : null}
              </>
            )}
          </div>
        )
      })}
    </div>
  )
}
