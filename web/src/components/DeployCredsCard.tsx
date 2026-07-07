// ⑦ deploy creds. Request/response (NOT a WS channel — never push plaintext);
// GET on mount + after each mutation. Server returns masked values only.
// 主入口是「一个粘贴框」：把手头任意凭证/配置（KEY=VALUE / export / TOML / 整段 .p8 私钥）
// 整段粘进来，前端确定性解析后保存；按平台必填清单算出还缺哪条、就地提示。结构化字段保留作手动兜底。
import { useEffect, useMemo, useState } from 'react'
import { PF_BASE, parsePaste, post } from '../lib'
import { toast } from '../store'
import type { DeployCredKey } from '../types'

const empty = { host: '', user: '', port: '', target: '', extra: '' }

type Recipe = { key: string; label: string; need: string[]; tips: Record<string, string>; oneOf?: string[] }
const R: Record<string, Recipe> = {
  ios: {
    key: 'ios',
    label: 'iOS · TestFlight',
    need: ['ASC_KEY_ID', 'ASC_ISSUER_ID', 'ASC_KEY_PATH'],
    tips: {
      ASC_KEY_ID: 'App Store Connect → 用户和访问 → 集成 → App Store Connect API，新建密钥后的 Key ID',
      ASC_ISSUER_ID: '同一页顶部的 Issuer ID（UUID 格式）',
      ASC_KEY_PATH: '把下载的 AuthKey_xxx.p8 整段内容粘到上面的框，会自动落成文件',
    },
  },
  android: {
    key: 'android',
    label: 'Android · Google Play 内测',
    need: ['PLAY_SERVICE_ACCOUNT_JSON', 'ANDROID_KEYSTORE', 'ANDROID_KEYSTORE_PASSWORD', 'ANDROID_KEY_ALIAS', 'ANDROID_KEY_PASSWORD'],
    tips: {
      PLAY_SERVICE_ACCOUNT_JSON: 'Google Play Console 服务账号 JSON 文件的本机路径',
      ANDROID_KEYSTORE: '上传密钥库 .jks/.keystore 文件的本机路径',
      ANDROID_KEYSTORE_PASSWORD: '密钥库口令——生成 .jks 时设置的 store password',
      ANDROID_KEY_ALIAS: '密钥别名——生成 .jks 时给签名密钥起的 alias 名',
      ANDROID_KEY_PASSWORD: '密钥口令——该 alias 的密码（生成时设置，常与库口令相同）',
    },
  },
  pgyer: {
    key: 'pgyer',
    label: 'App · 蒲公英内测分发',
    need: ['PGYER_API_KEY'],
    tips: { PGYER_API_KEY: '蒲公英后台 → 账户设置 → API 信息（www.pgyer.com/account/api），复制 API Key（账号级，一个就够；上传 .ipa/.apk 即生成扫码安装链接）' },
  },
  cf: {
    key: 'cf',
    label: 'Web · Cloudflare',
    need: ['CF_API_TOKEN'],
    tips: { CF_API_TOKEN: 'Cloudflare → My Profile → API Tokens，建一个带 Pages/Workers 权限的 token' },
  },
  ssh: {
    key: 'ssh',
    label: 'Web · 单机服务器',
    need: ['PF_SSH_HOST', 'PF_SSH_USER'],
    oneOf: ['PF_SSH_PASSWORD', 'PF_SSH_KEY_PATH'],
    tips: {
      PF_SSH_HOST: '服务器 IP 或域名',
      PF_SSH_USER: '登录用户名（如 root）',
      PF_SSH_PASSWORD: '登录密码，和密钥二选一',
      PF_SSH_KEY_PATH: 'SSH 私钥文件路径，和密码二选一、更安全',
      PF_SSH_PORT: '端口，默认 22、可选',
    },
  },
}

// 按已填凭证嗅探目标平台；都没填时按 wizard.primary 给出该填哪套的提示
function detectRecipes(have: Set<string>, primary?: string | null): Recipe[] {
  const ks = [...have]
  const out: Recipe[] = []
  if (ks.some((k) => k.startsWith('ASC_'))) out.push(R.ios)
  if (ks.some((k) => k.startsWith('ANDROID_') || k.startsWith('PLAY_'))) out.push(R.android)
  if (ks.some((k) => k.startsWith('PGYER_'))) out.push(R.pgyer)
  if (have.has('CF_API_TOKEN') || have.has('CF_ACCOUNT_ID')) out.push(R.cf)
  if (ks.some((k) => k.startsWith('PF_SSH_'))) out.push(R.ssh)
  if (out.length) return out
  return (primary || '').toUpperCase() === 'APP' ? [R.ios, R.android, R.pgyer] : [R.cf, R.ssh]
}

export function DeployCredsCard({ primary }: { primary?: string | null }) {
  const [keys, setKeys] = useState<DeployCredKey[]>([])
  const [paste, setPaste] = useState('')
  const [showManual, setShowManual] = useState(false)
  const [d, setD] = useState({ ...empty })
  const [devKeys, setDevKeys] = useState<{ key: string; provider?: string | null; filled: boolean }[]>([])
  const [showReuse, setShowReuse] = useState(false)
  const refetch = () => {
    fetch(PF_BASE + '/api/deploy-creds')
      .then((r) => r.json())
      .then((j) => setKeys(j.keys || []))
      .catch(() => {})
  }
  useEffect(refetch, [])
  // 开发阶段（⑤⑦）在 product-keys 卡配好的第三方 key——和部署凭证同一份 secrets，部署可直接复用
  useEffect(() => {
    fetch(PF_BASE + '/api/product-keys')
      .then((r) => r.json())
      .then((j) => setDevKeys((j.keys || []).filter((k: { filled?: boolean }) => k.filled)))
      .catch(() => {})
  }, [keys])

  const have = useMemo(() => new Set(keys.map((k) => k.key)), [keys])
  const recipes = useMemo(() => detectRecipes(have, primary), [have, primary])

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
  const smartSave = () => {
    const { creds, p8 } = parsePaste(paste)
    const n = Object.keys(creds).length + (p8 ? 1 : 0)
    if (!n) {
      toast('没识别到 KEY=VALUE 或 .p8 私钥——检查下粘贴内容')
      return
    }
    post('/api/deploy-creds', { creds, p8 })
      .then((r) => r.json())
      .then((j) => {
        if (j.error) {
          toast('保存失败：' + j.error)
          return
        }
        toast(`已识别并保存 ${j.count || n} 项凭证${p8 ? '（含 .p8 私钥已落文件）' : ''}`)
        setPaste('')
        refetch()
      })
      .catch(() => toast('保存失败'))
  }
  const saveManual = () => {
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
        部署凭证 <span className="hint">粘一段，自动分拣并保存</span>
      </h2>
      <div className="wz-hint2" style={{ margin: '0 0 10px' }}>
        把手头任意凭证/配置整段粘进下面的框——支持 <code>KEY=VALUE</code>、<code>export …</code>、TOML <code>key = "值"</code>、JSON、以及整段 <code>.p8</code> 私钥。
        存在本机 <code>~/.productflow/secrets/</code>（600 权限），<b>不进 git、不进留言</b>；Agent 部署时作为环境变量取用。
      </div>

      {devKeys.length > 0 && (
        <div className="dc-reuse">
          <div className="dc-reuse-head">
            <span>🔗 开发环境已配 <b>{devKeys.length}</b> 个第三方密钥（邮件 / 短信 / 支付等）——部署<b>直接复用</b>、不用在这重填</span>
            <button className="btn ghost sm" onClick={() => setShowReuse((s) => !s)}>{showReuse ? '收起' : '↺ 复用开发环境密钥'}</button>
          </div>
          {showReuse && (
            <div className="dc-reuse-list">
              {devKeys.map((k) => (
                <span key={k.key} className="dc-reuse-item"><code>{k.key}</code>{k.provider ? ' · ' + k.provider : ''} ✓</span>
              ))}
              <div className="wz-hint2" style={{ marginTop: 6, width: '100%' }}>这些密钥和部署凭证存在<b>同一份 secrets</b>，Agent 部署时会自动注入生产环境，不必在上方重复粘贴。若生产要用<b>不同</b>的密钥（如正式邮箱账号 / 生产短信签名），在上方粘贴同名 <code>KEY=新值</code> 覆盖即可。</div>
            </div>
          )}
        </div>
      )}

      <textarea
        className="wz-textarea"
        value={paste}
        onChange={(e) => setPaste(e.target.value)}
        style={{ height: 120 }}
        placeholder={'把凭证粘这里，例如：\nASC_KEY_ID=ABC123XYZ\nASC_ISSUER_ID=69a6de70-…-…\n-----BEGIN PRIVATE KEY-----\n…AuthKey_ABC123.p8 的整段内容…\n-----END PRIVATE KEY-----'}
      />
      <button className="btn" style={{ marginTop: 10 }} onClick={smartSave}>
        🪄 智能识别并保存
      </button>

      {/* 必填检查：按平台 / 已填凭证算出还缺哪条 —— 这就是「缺什么才提示」 */}
      <div style={{ marginTop: 14, paddingTop: 12, borderTop: '1px solid var(--line)' }}>
        {recipes.map((rc) => {
          const missing = rc.need.filter((k) => !have.has(k))
          const oneOfUnmet = !!rc.oneOf && !rc.oneOf.some((k) => have.has(k))
          const missCount = missing.length + (oneOfUnmet ? 1 : 0)
          return (
            <div key={rc.key} style={{ marginBottom: 8 }}>
              <div className="wz-hint2">
                <b>{rc.label}</b>{' '}
                {missCount ? <span style={{ color: '#b3793a' }}>· 还缺 {missCount} 项</span> : <span style={{ color: '#3a8a4a' }}>· ✓ 必填已齐</span>}
              </div>
              {missing.map((k) => (
                <div key={k} className="wz-hint2" style={{ marginLeft: 10, marginTop: 2 }}>
                  ✗ <code>{k}</code> — {rc.tips[k] || `在上面框里补一行 ${k}=…`}
                </div>
              ))}
              {oneOfUnmet && rc.oneOf && (
                <div className="wz-hint2" style={{ marginLeft: 10, marginTop: 2 }}>
                  ✗ 认证（二选一） —{' '}
                  {rc.oneOf.map((k, i) => (
                    <span key={k}>
                      {i > 0 && ' 或 '}
                      <code>{k}</code>
                      {rc.tips[k] ? `（${rc.tips[k]}）` : ''}
                    </span>
                  ))}
                </div>
              )}
            </div>
          )
        })}
      </div>

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

      {/* 手动精填（兜底）：SSH 四件套 + 自由 KEY=VALUE */}
      <div style={{ marginTop: 12 }}>
        <button className="btn ghost sm" onClick={() => setShowManual((s) => !s)}>
          {showManual ? '收起手动精填' : '手动精填（SSH / 自定义）'}
        </button>
      </div>
      {showManual && (
        <div style={{ marginTop: 10 }}>
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
          <button className="btn" style={{ marginTop: 10 }} onClick={saveManual}>
            💾 保存手动填写
          </button>
        </div>
      )}
    </div>
  )
}
