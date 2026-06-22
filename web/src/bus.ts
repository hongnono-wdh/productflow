// Global WebSocket bus: one connection per page (home: /api/ws, project: /p/<id>/api/ws).
// Server pushes {channel,data} frames (change-gated). Auto-reconnect with backoff.
// Replaces every setInterval poll in the old console.
import { PF_BASE } from './lib'
import { dispatch } from './store'

let started = false

export function startBus(): void {
  if (started) return
  started = true
  let backoff = 500
  const connect = () => {
    const proto = location.protocol === 'https:' ? 'wss://' : 'ws://'
    let ws: WebSocket
    try {
      ws = new WebSocket(proto + location.host + PF_BASE + '/api/ws')
    } catch {
      setTimeout(connect, backoff)
      backoff = Math.min(backoff * 2, 8000)
      return
    }
    ws.onopen = () => {
      backoff = 500
    }
    ws.onmessage = (e: MessageEvent) => {
      try {
        const msg = JSON.parse(e.data as string)
        if (msg && typeof msg.channel === 'string') dispatch(msg.channel, msg.data)
      } catch {
        /* ignore malformed frame */
      }
    }
    ws.onclose = () => {
      setTimeout(connect, backoff)
      backoff = Math.min(backoff * 2, 8000)
    }
    ws.onerror = () => {
      try {
        ws.close()
      } catch {
        /* noop */
      }
    }
  }
  connect()
}
