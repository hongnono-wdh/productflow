// Routing + small helpers ported verbatim from console.html.

const _m = location.pathname.match(/^\/p\/([a-z0-9-]{1,64})\/?$/)
export const PF_BASE = _m ? '/p/' + _m[1] : ''
export const IS_PROJECT = !!_m
export const PF_ID = _m ? _m[1] : ''

export function artUrl(file: string, ts?: string | number): string {
  return PF_BASE + '/artifacts/' + file.replace(/^artifacts\//, '') + (ts ? '?t=' + encodeURIComponent(String(ts)) : '')
}

// relTime: humanize a "YYYY-MM-DD HH:MM:SS" timestamp (verbatim from console.html)
export function relTime(s?: string): string {
  if (!s) return ''
  const t = new Date(String(s).replace(' ', 'T'))
  if (isNaN(t.getTime())) return s
  const d = (Date.now() - t.getTime()) / 1000
  if (d < 60) return '刚刚'
  if (d < 3600) return Math.floor(d / 60) + ' 分钟前'
  if (d < 86400) return Math.floor(d / 3600) + ' 小时前'
  return Math.floor(d / 86400) + ' 天前'
}

// Load a vendor script once (d3/markmap/viewer stay on /vendor, version-locked).
const _scripts = new Map<string, Promise<void>>()
export function loadScript(src: string): Promise<void> {
  let p = _scripts.get(src)
  if (!p) {
    p = new Promise<void>((res, rej) => {
      const s = document.createElement('script')
      s.src = src
      s.onload = () => res()
      s.onerror = () => rej(new Error('load failed: ' + src))
      document.head.appendChild(s)
    })
    _scripts.set(src, p)
  }
  return p
}

// POST helper (client->server stays POST; PF_BASE-prefixed for project scope)
export async function post(path: string, body: unknown): Promise<Response> {
  return fetch(PF_BASE + path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body ?? {}),
  })
}

// 确定性解析粘贴的凭证：抽 .p8 PEM 块 + 逐行 KEY=VALUE / export KEY=v / TOML key="v" / "KEY":"v" / KEY: v。
// ⑤⑦ 第三方 key 卡和 ⑨ 部署凭证卡共用——前端直接解析、不调 agent（快）。
export function parsePaste(raw: string): { creds: Record<string, string>; p8: string } {
  const creds: Record<string, string> = {}
  let text = raw
  let p8 = ''
  const pem = text.match(/-----BEGIN[^-]*PRIVATE KEY-----[\s\S]*?-----END[^-]*PRIVATE KEY-----/)
  if (pem) {
    p8 = pem[0]
    text = text.replace(pem[0], '\n')
  }
  for (const line of text.split('\n')) {
    let l = line.trim()
    if (!l || l.startsWith('#') || l.startsWith('//')) continue
    l = l.replace(/^export\s+/, '')
    const m = l.match(/^["']?([A-Za-z_][A-Za-z0-9_]*)["']?\s*[=:]\s*(.+)$/)
    if (!m) continue
    let v = m[2].trim().replace(/[,;]\s*$/, '').trim()
    if ((v.startsWith('"') && v.endsWith('"')) || (v.startsWith("'") && v.endsWith("'"))) v = v.slice(1, -1)
    if (v) creds[m[1]] = v
  }
  return { creds, p8 }
}
