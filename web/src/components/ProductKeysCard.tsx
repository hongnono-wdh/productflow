// ⑤⑦ 第三方 key 卡：富文本粘贴 → Agent 解析填入（唯一填写方式）；下方纯展示所有 key 的列表（平台分组 + 状态点 + 已配置/待填），不带填写/修改按钮、不弹窗。
import { useEffect, useState } from 'react'
import { PF_BASE, post } from '../lib'
import { toast } from '../store'

type PKey = { key: string; desc: string; module?: string | string[] | null; provider?: string | null; url?: string | null; filled: boolean; masked: string }

export function ProductKeysCard() {
  const [keys, setKeys] = useState<PKey[]>([])
  const [paste, setPaste] = useState('')
  const [parsing, setParsing] = useState(false)
  const [nonce, setNonce] = useState(0)

  useEffect(() => {
    let cancelled = false
    fetch(PF_BASE + '/api/product-keys')
      .then((r) => r.json())
      .then((d) => { if (!cancelled) setKeys(Array.isArray(d.keys) ? d.keys : []) })
      .catch(() => {})
    return () => { cancelled = true }
  }, [nonce])

  // 唯一填写方式：把贴的凭证发给 Agent 解析、自动填入识别出的 key（值不经页面存储，走 secrets）
  const parseKeys = () => {
    const t = paste.trim()
    if (!t) { toast('先把凭证文本贴进来'); return }
    setParsing(true)
    post('/api/parse-keys', { text: t })
      .then((r) => {
        if (!r.ok) { toast('触发失败，请重试'); setParsing(false); return }
        toast('已让 Agent 解析…识别出的 key 会自动填入（下方状态几秒后刷新）')
        setPaste('')
        let n = 0
        const timer = setInterval(() => { setNonce((x) => x + 1); if (++n >= 8) { clearInterval(timer); setParsing(false) } }, 2500)
      })
      .catch(() => { toast('触发失败，请重试'); setParsing(false) })
  }

  if (!keys.length) return null // ⑤ 未识别到第三方 key 需求 → 整卡不显示
  const doneCount = keys.filter((k) => k.filled).length

  return (
    <div className="card">
      <h2>第三方 key <span className="hint">产品用到的第三方服务凭证（{doneCount}/{keys.length} 已配置 · 存本机 secrets、不进 git）</span></h2>
      <div className="wz-hint2" style={{ margin: '0 0 10px' }}>把从服务商后台复制的凭证整段贴到下面、点「Agent 解析填入」自动识别入库（唯一填写方式）。下方列出所有需要的 key 及状态，值只存本机、不进 git。</div>
      <div className="pk-paste">
        <textarea className="wz-input pk-paste-ta" placeholder="把从服务商后台复制的凭证整段贴这里（任意格式，如 “AccessKey ID: LTAI…、Secret: xxx、商户号 1620…”），Agent 会自动识别并填入对应 key" value={paste} onChange={(e) => setPaste(e.target.value)} />
        <button className="btn" disabled={parsing} onClick={parseKeys} style={parsing ? { background: 'var(--dash)', cursor: 'not-allowed' } : undefined}>{parsing ? '解析中…' : '🤖 Agent 解析填入'}</button>
      </div>

      <div className="pk-list">
        {keys.map((k) => (
          <div key={k.key} className={'pk-line' + (k.filled ? ' done' : '')} title={k.desc || k.key}>
            <span className={'pk-dot' + (k.filled ? ' done' : '')} />
            <code className="pk-line-name">{k.key}</code>
            {k.provider ? (k.url
              ? <a className="pk-line-prov" href={k.url} target="_blank" rel="noreferrer">{k.provider} ↗</a>
              : <span className="pk-line-prov">{k.provider}</span>) : null}
            <span className={'pk-line-status' + (k.filled ? ' done' : '')}>{k.filled ? '已配置' : '待填'}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
