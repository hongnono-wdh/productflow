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
