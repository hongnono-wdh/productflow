// ⑦ deploy creds. Request/response (NOT a WS channel — never push plaintext);
// GET on mount + after each mutation. Server returns masked values only.
import { useEffect, useState } from 'react'
import { PF_BASE, post } from '../lib'
import { toast } from '../store'
import type { DeployCredKey } from '../types'

const empty = { host: '', user: '', port: '', target: '', extra: '' }

export function DeployCredsCard() {
  const [keys, setKeys] = useState<DeployCredKey[]>([])
  const [d, setD] = useState({ ...empty })
  const refetch = () => {
    fetch(PF_BASE + '/api/deploy-creds')
      .then((r) => r.json())
      .then((j) => setKeys(j.keys || []))
      .catch(() => {})
  }
  useEffect(refetch, [])

  const removeCred = (key: string) => {
    post('/api/deploy-creds', { remove: key }).then(() => {
      toast('已删除凭证 ' + key)
      refetch()
    })
  }
  const clearCreds = () => {
    if (!confirm('清空本项目的全部部署凭证？')) return
    post('/api/deploy-creds', { clear: true }).then(() => {
      toast('已清空全部凭证')
      refetch()
    })
  }
  const save = () => {
    const creds: Record<string, string> = {}
    if (d.host.trim()) creds.PF_SSH_HOST = d.host.trim()
    if (d.user.trim()) creds.PF_SSH_USER = d.user.trim()
    if (d.port.trim()) creds.PF_SSH_PORT = d.port.trim()
    if (d.target.trim()) creds.PF_DEPLOY_TARGET = d.target.trim()
    d.extra.split('\n').forEach((l) => {
      const m = l.match(/^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$/)
      if (m && m[2].trim()) creds[m[1]] = m[2].trim()
    })
    if (!Object.keys(creds).length) {
      toast('先填至少一项凭证')
      return
    }
    post('/api/deploy-creds', { creds })
      .then((r) => r.json())
      .then((j) => {
        toast(`已保存，共 ${j.count || 0} 项凭证（本机 600，不进 git）`)
        setD({ ...empty })
        refetch()
      })
      .catch(() => {})
  }

  return (
    <div className="card">
      <h2>
        部署凭证 <span className="hint">填一次，Agent 部署时直接用</span>
      </h2>
      <div className="wz-hint2" style={{ margin: '0 0 12px' }}>
        存在本机 <code>~/.productflow/secrets/</code>（600 权限），<b>不进 git、不进留言</b>。Agent 部署时作为环境变量 <code>$PF_SSH_HOST</code> 等取用；只填要改的项即可（与已存的合并）。
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
        <input className="wz-input" value={d.host} onChange={(e) => setD({ ...d, host: e.target.value })} placeholder="服务器地址 PF_SSH_HOST（如 1.2.3.4）" />
        <input className="wz-input" value={d.user} onChange={(e) => setD({ ...d, user: e.target.value })} placeholder="用户 PF_SSH_USER（如 root）" />
        <input className="wz-input" value={d.port} onChange={(e) => setD({ ...d, port: e.target.value })} placeholder="端口 PF_SSH_PORT（如 22）" />
        <input className="wz-input" value={d.target} onChange={(e) => setD({ ...d, target: e.target.value })} placeholder="部署目标 PF_DEPLOY_TARGET（可选）" />
      </div>
      <textarea
        className="wz-textarea"
        value={d.extra}
        onChange={(e) => setD({ ...d, extra: e.target.value })}
        style={{ height: 58, marginTop: 10 }}
        placeholder="其他凭证，每行一条 KEY=VALUE（如 CF_API_TOKEN=xxxx）"
      />
      {keys.length ? (
        <>
          <div className="wz-hint2" style={{ marginTop: 8 }}>已存储 {keys.length} 项（点 ✕ 删单条）：</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 6 }}>
            {keys.map((k) => (
              <span key={k.key} style={{ display: 'inline-flex', alignItems: 'center', gap: 6, background: 'var(--fill)', borderRadius: 8, padding: '3px 6px 3px 10px', fontSize: 12 }}>
                <code>
                  {k.key}={k.masked}
                </code>
                <span onClick={() => removeCred(k.key)} title="删除这条凭证" style={{ cursor: 'pointer', color: 'var(--dim)', borderRadius: 5, padding: '0 5px' }}>
                  ✕
                </span>
              </span>
            ))}
            <button className="btn ghost sm" onClick={clearCreds}>
              清空全部
            </button>
          </div>
        </>
      ) : (
        <div className="wz-hint2" style={{ marginTop: 8 }}>还没存任何凭证。</div>
      )}
      <button className="btn" style={{ marginTop: 12 }} onClick={save}>
        💾 保存凭证
      </button>
    </div>
  )
}
