// ⑤⑦ 第三方 key 卡：粘贴 KEY=VALUE / export → 前端确定性解析、直接存 secrets（和 ⑨ 部署凭证同一套 /api/deploy-creds，不调 agent、瞬间完成）；下方纯展示所有 key 状态（已配置 / 待填）。
import { useEffect, useState } from 'react'
import { PF_BASE, parsePaste, post } from '../lib'
import { toast } from '../store'

type PKey = { key: string; desc: string; module?: string | string[] | null; provider?: string | null; url?: string | null; filled: boolean; masked: string }

export function ProductKeysCard() {
  const [keys, setKeys] = useState<PKey[]>([])
  const [paste, setPaste] = useState('')
  const [nonce, setNonce] = useState(0)

  useEffect(() => {
    let cancelled = false
    fetch(PF_BASE + '/api/product-keys')
      .then((r) => r.json())
      .then((d) => { if (!cancelled) setKeys(Array.isArray(d.keys) ? d.keys : []) })
      .catch(() => {})
    return () => { cancelled = true }
  }, [nonce])

  // 前端确定性解析（KEY=VALUE / export / TOML），直接 POST 存 secrets——和 ⑨ 部署凭证同一个 /api/deploy-creds，不调 agent（秒存）
  const parseKeys = () => {
    const { creds, p8 } = parsePaste(paste)
    const n = Object.keys(creds).length + (p8 ? 1 : 0)
    if (!n) { toast('没识别到 KEY=VALUE——每行写成 KEY=值 或 export KEY=值（值可带引号）'); return }
    post('/api/deploy-creds', { creds, p8 })
      .then((r) => r.json())
      .then((j) => {
        if (j.error) { toast('保存失败：' + j.error); return }
        toast(`已识别并保存 ${j.count || n} 项密钥（下方状态已刷新）`)
        setPaste('')
        setNonce((x) => x + 1)
      })
      .catch(() => toast('保存失败'))
  }

  // 删除某 key 的值（清 secrets、变回「待填」；不删登记的需求）——和部署凭证卡的删除同一个 API
  const removeKey = (key: string) => {
    post('/api/deploy-creds', { remove: key }).then(() => { toast('已清除 ' + key + '（变回待填）'); setNonce((x) => x + 1) }).catch(() => toast('删除失败'))
  }

  if (!keys.length) return null // ⑤ 未识别到第三方 key 需求 → 整卡不显示
  const doneCount = keys.filter((k) => k.filled).length

  return (
    <div className="card">
      <h2>第三方 key <span className="hint">产品用到的第三方服务凭证（{doneCount}/{keys.length} 已配置 · 存本机 secrets、不进 git）</span></h2>
      <div className="wz-hint2" style={{ margin: '0 0 10px' }}>把从服务商后台复制的凭证按 <code>KEY=值</code> 每行一条贴进下面（支持 <code>export KEY=值</code>、带引号、整段 .env），点「识别并保存」即入库——<b>前端直接解析、不调 Agent，秒存</b>。值只存本机、不进 git。</div>
      <textarea className="wz-textarea" value={paste} onChange={(e) => setPaste(e.target.value)} style={{ height: 120 }} placeholder={'每行一条 KEY=值，例如：\nMAIL_USER=you@gmail.com\nMAIL_PASS=xxxx xxxx xxxx xxxx\nSMS_ACCESS_KEY=LTAI...'} />
      <button className="btn" style={{ marginTop: 10 }} onClick={parseKeys}>🪄 智能识别并保存</button>

      <div className="wz-hint2" style={{ marginTop: 12 }}>需要的 key（{doneCount}/{keys.length} 已配置 · 点 ✕ 清除单条变回待填）：</div>
      <div className="pk-chips">
        {keys.map((k) => (
          <span key={k.key} className={'pk-chip' + (k.filled ? ' done' : '')} title={k.desc || k.key}>
            <span className={'pk-dot' + (k.filled ? ' done' : '')} />
            <code>{k.key}{k.filled ? '=' + k.masked : ''}</code>
            {k.provider ? (k.url
              ? <a className="pk-chip-prov" href={k.url} target="_blank" rel="noreferrer">{k.provider} ↗</a>
              : <span className="pk-chip-prov">{k.provider}</span>) : null}
            {k.filled
              ? <span className="pk-chip-x" onClick={() => removeKey(k.key)} title="清除这条（变回待填）">✕</span>
              : <span className="pk-chip-todo">待填</span>}
          </span>
        ))}
      </div>
    </div>
  )
}
